"""
Wonderland Online PreEvent Bytecode Interpreter & Dynamic Actor Visibility
Ported from C# wlo.pserver.core/Game/QuestRelated/PreEventInterpreter.cs
"""

import os
import struct
import logging
from typing import Dict, List, Optional, Any

from server.network import PacketWriter
from server.quests import GLOBAL_QUEST_ENGINE, QuestState

logger = logging.getLogger("WLO_Server")


class PreEventInterpreter:
    """Evaluates eve.Emg PreEvents bytecode conditions and controls dynamic per-player actor visibility."""

    def __init__(self):
        self._map_preevents: Dict[int, List[Dict[str, Any]]] = {}
        self._loaded = False

    def load_preevents(self, eve_dat_path: str):
        """Loads and parses PreEvents bytecode structures across all maps from eve.Emg."""
        if not os.path.exists(eve_dat_path):
            return

        try:
            with open(eve_dat_path, "rb") as f:
                d = f.read()

            if len(d) < 100:
                return

            num_maps = struct.unpack_from("<H", d, 0)[0]
            ptr = 2
            map_headers = []
            for _ in range(num_maps):
                if ptr + 14 > len(d):
                    break
                map_id = struct.unpack_from("<H", d, ptr)[0]
                data_ptr = struct.unpack_from("<I", d, ptr + 2)[0]
                data_len = struct.unpack_from("<I", d, ptr + 6)[0]
                map_headers.append({"map_id": map_id, "dataptr": data_ptr, "datalen": data_len})
                ptr += 14

            loaded_preevents_count = 0
            for m in map_headers:
                map_id = m["map_id"]
                off_ptr = m["dataptr"] + 6
                if off_ptr + 44 > len(d):
                    continue

                offsets = struct.unpack_from("<IIIIIIIIIII", d, off_ptr)
                preevent_offset = offsets[1]  # Offset 1 is PreEvents table
                preevent_ptr = m["dataptr"] + preevent_offset

                if preevent_ptr + 2 > len(d):
                    continue

                pe_count = struct.unpack_from("<H", d, preevent_ptr)[0]
                if pe_count == 0:
                    continue

                cur_ptr = preevent_ptr + 2
                preevent_list = []

                for _ in range(pe_count):
                    if cur_ptr + 2 > len(d):
                        break
                    sub_count = struct.unpack_from("<H", d, cur_ptr)[0]
                    cur_ptr += 2

                    subentries = []
                    for _ in range(sub_count):
                        if cur_ptr + 21 > len(d):
                            break
                        cond_data = d[cur_ptr : cur_ptr + 21]
                        cur_ptr += 21

                        if cur_ptr + 2 > len(d):
                            break
                        act_count = struct.unpack_from("<H", d, cur_ptr)[0]
                        cur_ptr += 2

                        actions = []
                        for _ in range(act_count):
                            if cur_ptr + 10 > len(d):
                                break
                            act_data = d[cur_ptr : cur_ptr + 10]
                            actions.append(act_data)
                            cur_ptr += 10

                        subentries.append({
                            "condition": cond_data,
                            "actions": actions
                        })

                    preevent_list.append(subentries)
                    loaded_preevents_count += 1

                self._map_preevents[map_id] = preevent_list

            self._loaded = True
            logger.info(f"[PreEventInterpreter] Loaded {loaded_preevents_count} PreEvents across {len(self._map_preevents)} maps from eve.Emg.")
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error parsing PreEvents from eve.Emg: {e}", exc_info=True)

    async def evaluate_map_preevents(self, session, map_id: int):
        """Evaluates all PreEvents for target map against the player's quest marks and flags."""
        if not session or map_id not in self._map_preevents:
            return

        try:
            preevents = self._map_preevents[map_id]
            for subentries in preevents:
                for sub in subentries:
                    cond_data = sub.get("condition")
                    if self._evaluate_condition_block(session, cond_data):
                        # Condition matched! Execute action blocks
                        for act_data in sub.get("actions", []):
                            await self._execute_action_block(session, act_data)
                        break  # First valid branch matched for this PreEvent
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error evaluating PreEvents for map {map_id}: {e}", exc_info=True)

    def _evaluate_condition_block(self, session, data: bytes) -> bool:
        if not data or len(data) == 0:
            return True

        # Iterate over all 7-byte condition chunks in the 21-byte condition buffer
        offset = 0
        while offset + 7 <= len(data):
            op = data[offset]
            if op == 0x00:
                break

            # Opcode 0x05: Quest Mark / Flag Condition
            if op == 0x05:
                flag_id = struct.unpack_from("<H", data, offset + 1)[0]
                req_value = struct.unpack_from("<H", data, offset + 3)[0]
                comp_type = struct.unpack_from("<H", data, offset + 5)[0]

                player_val = self._get_player_flag_value(session, flag_id)

                if comp_type == 1: match = (player_val == req_value)
                elif comp_type == 2: match = (player_val >= req_value)
                elif comp_type == 3: match = (player_val <= req_value)
                elif comp_type == 4: match = (player_val != req_value)
                elif comp_type == 5: match = (player_val > req_value)
                elif comp_type == 6: match = (player_val < req_value)
                else: match = (player_val == req_value)

                if not match:
                    return False

            # Opcode 0x01: Unconditional / Always True
            elif op == 0x01:
                pass

            # Opcode 0x02: Companion / Pet Recruitment Check
            elif op == 0x02:
                sub_type = struct.unpack_from("<H", data, offset + 1)[0]
                count = struct.unpack_from("<H", data, offset + 3)[0]
                pet_id = struct.unpack_from("<H", data, offset + 5)[0]

                if sub_type == 2 and pet_id > 0:
                    has_pet = any(
                        p.get("pet_id") == pet_id or
                        (pet_id == 12178 and p.get("pet_id") == 12032) or
                        (pet_id == 12032 and p.get("pet_id") == 12178)
                        for p in getattr(session, "pets", [])
                    )
                    if not has_pet:
                        return False

            offset += 7

        return True

    async def _execute_action_block(self, session, data: bytes):
        if not session or not data or len(data) < 10:
            return

        action_op = data[0]

        # Opcode 0x02: Actor Visibility / State Control
        if action_op == 0x02:
            click_id = struct.unpack_from("<H", data, 1)[0]
            state1 = data[8]
            state2 = data[9]

            act_pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(state1).write_8(state2)
            await session.send_packet(act_pkt)

    def _get_player_flag_value(self, session, flag_id: int) -> int:
        if not session or flag_id == 0:
            return 0

        p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
        if flag_id in p_map:
            pq = p_map[flag_id]
            if pq.state == QuestState.IN_PROGRESS:
                return max(1, pq.step)
            elif pq.state == QuestState.COMPLETED:
                return 2
            return 0

        return 0

    async def sync_per_player_npc_visibility(self, server, session, map_id: int):
        """Synchronizes personal client-side NPC visibility based on dynamic Eve.emg PreEvents and quest state."""
        if not session:
            return

        try:
            # 1. Evaluate dynamic PreEvents bytecode from eve.Emg
            await self.evaluate_map_preevents(session, map_id)

            # 2. Evaluate dynamic database NPC visibility rules from game_npc_visibility
            try:
                from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
                vis_rules = GLOBAL_DYNAMIC_DATA.get_npc_visibility_rules(map_id)
                p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
                pets = getattr(session, "pets", [])

                for rule in vis_rules:
                    click_id = rule["click_id"]
                    npc_id = rule["npc_id"]
                    default_vis = rule.get("default_visible", 1)
                    req_q_id = rule.get("required_quest_id", 0)
                    req_q_state = rule.get("required_quest_state", 0)
                    hide_q_comp = rule.get("hide_if_quest_completed", 0)
                    hide_comp_rec = rule.get("hide_if_companion_recruited", 0)

                    should_be_visible = bool(default_vis)

                    # Quest requirement check
                    if req_q_id > 0:
                        pq = p_map.get(req_q_id)
                        if req_q_state == 1:  # In Progress
                            should_be_visible = (pq is not None and pq.state == QuestState.IN_PROGRESS)
                        elif req_q_state == 2:  # Completed
                            should_be_visible = (pq is not None and pq.state == QuestState.COMPLETED)
                        else:
                            should_be_visible = (pq is not None)

                    # Hide if quest completed
                    if hide_q_comp:
                        # Check specific quest or any quest where this NPC was involved
                        if req_q_id > 0 and req_q_id in p_map and p_map[req_q_id].state == QuestState.COMPLETED:
                            should_be_visible = False

                    # Hide if companion recruited
                    if hide_comp_rec and pets:
                        has_pet = any(
                            p.get("pet_id") == npc_id or
                            (npc_id == 12032 and p.get("pet_id") in (12032, 12178))
                            for p in pets
                        )
                        if has_pet:
                            should_be_visible = False

                    # Send client state packet
                    if not should_be_visible:
                        hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0xFF).write_8(0xFF)
                        await session.send_packet(hide_pkt)
                    else:
                        show_pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0x00).write_8(0x00)
                        await session.send_packet(show_pkt)
            except Exception as e:
                logger.warning(f"[PreEventInterpreter] Dynamic DB visibility error: {e}")

            # 3. Hide completed/recruited quest NPCs from registered definitions
            p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
            for q_id, pq in p_map.items():
                if pq.state == QuestState.COMPLETED:
                    quest = GLOBAL_QUEST_ENGINE.get_quest(q_id)
                    if quest and quest.map_id == map_id and quest.despawn_npc_click_ids:
                        for click_id in quest.despawn_npc_click_ids:
                            hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0xFF).write_8(0xFF)
                            await session.send_packet(hide_pkt)
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error syncing per-player NPC visibility: {e}", exc_info=True)

    async def replay_actor_visibility(self, server, session, map_id: int):
        """Rebuilds the correct visible quest phase and actor states for the player on map entry."""
        if not session:
            return

        try:
            # 1. Despawn recruited companions from map if in player party/pets
            pets = getattr(session, "pets", [])
            if pets:
                for pet in pets:
                    pet_id = pet.get("pet_id", 0)
                    pet_name = (pet.get("name") or "").lower()

                    for npc in server.map_npcs.get(map_id, []):
                        npc_name = (npc.get("name") or "").lower()
                        npc_id = npc.get("npc_id", 0)

                        if (pet_id > 0 and npc_id == pet_id) or (pet_name and pet_name == npc_name):
                            hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(npc["click_id"]).write_8(0xFF).write_8(0xFF)
                            await session.send_packet(hide_pkt)
                            logger.info(f"[ActorVisibility] Despawned companion NPC '{npc['name']}' (ClickID {npc['click_id']}) for {session.char_name}")
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error in replay_actor_visibility: {e}", exc_info=True)


# Global singleton instance
GLOBAL_PREEVENT_INTERPRETER = PreEventInterpreter()
