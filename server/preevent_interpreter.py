"""
Wonderland Online PreEvent Bytecode Interpreter & Dynamic Actor Visibility
Ported from C# wlo.pserver.core/Game/QuestRelated/PreEventInterpreter.cs
"""

import os
import struct
import logging
from typing import Dict, List, Optional, Any, Set

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

            entrylen = struct.unpack_from("<I", d, 8)[0]
            ptr = 12
            maps = {}
            for _ in range(entrylen):
                if ptr + 10 > len(d):
                    break
                map_id, scene_id, data_ptr, data_len = struct.unpack_from("<HHIH", d, ptr)
                ptr += 10
                maps[map_id] = {"dataptr": data_ptr, "datalen": data_len}

            loaded_preevents_count = 0
            for map_id, m in maps.items():
                off_ptr = m["dataptr"] + m["datalen"] - 44
                if off_ptr + 44 > len(d):
                    continue

                offsets = struct.unpack_from("<11I", d, off_ptr)
                preevent_offset = offsets[9]  # Offset 9 is PreEvents table
                if not preevent_offset:
                    continue

                preevent_ptr = m["dataptr"] + preevent_offset
                pe_end_ptr = m["dataptr"] + offsets[10]
                if preevent_ptr + 2 > len(d) or pe_end_ptr > len(d) or preevent_ptr >= pe_end_ptr:
                    continue

                pe_bytes = d[preevent_ptr:pe_end_ptr]
                pe_count = struct.unpack_from("<H", pe_bytes, 0)[0]
                if pe_count == 0 or pe_count > 500:
                    continue

                cur_ptr = 2
                preevent_list = []

                for _ in range(pe_count):
                    if cur_ptr + 24 > len(pe_bytes):
                        break
                    ev_id = struct.unpack_from("<H", pe_bytes, cur_ptr)[0]
                    cur_ptr += 23  # ev_id (2B) + unk1 (1B) + name_bytes (20B)
                    sub_count = pe_bytes[cur_ptr]
                    cur_ptr += 1

                    subentries = []
                    for _ in range(sub_count):
                        if cur_ptr + 23 > len(pe_bytes):
                            break
                        cond_data = pe_bytes[cur_ptr : cur_ptr + 22]
                        cur_ptr += 22
                        act_count = pe_bytes[cur_ptr]
                        cur_ptr += 1

                        actions = []
                        for _ in range(act_count):
                            if cur_ptr + 22 > len(pe_bytes):
                                break
                            act_data = pe_bytes[cur_ptr : cur_ptr + 22]
                            actions.append(act_data)
                            cur_ptr += 22

                        if actions or cond_data:
                            subentries.append({
                                "condition": cond_data,
                                "actions": actions
                            })

                    if subentries:
                        preevent_list.append({
                            "click_id": ev_id,
                            "subentries": subentries
                        })
                        loaded_preevents_count += 1

                if preevent_list:
                    self._map_preevents[map_id] = preevent_list

            self._loaded = True
            logger.info(f"[PreEventInterpreter] Loaded {loaded_preevents_count} PreEvents across {len(self._map_preevents)} maps from eve.Emg.")
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error parsing PreEvents from eve.Emg: {e}", exc_info=True)

    def is_same_pet_or_companion(self, id1: int, id2: int) -> bool:
        """
        Determines whether two entity IDs represent the same companion across NPC template and pet IDs.
        Direct 1:1 Port from C# Player.IsSamePetOrCompanion.
        """
        if id1 == id2 and id1 > 0:
            return True
        if id1 == 0 or id2 == 0:
            return False

        # Robinson: 12032 (NPC TID) <-> 12178 (Pet TID)
        if (id1 in (12032, 12178)) and (id2 in (12032, 12178)):
            return True
        # S.Monkey: 17162 (NPC TID) <-> 10727 (Pet TID)
        if (id1 in (17162, 10727)) and (id2 in (17162, 10727)):
            return True
        # Roca: 14161 (mourning), 14162 (standard/village), 14001 (companion)
        if (id1 in (14161, 14162, 14001)) and (id2 in (14161, 14162, 14001)):
            return True
        # Niss: 14081 (standard), 14002 (companion), 12003 (quest definition)
        if (id1 in (14081, 14002, 12003)) and (id2 in (14081, 14002, 12003)):
            return True
        # Clive: 14163 (NPC), 14003 (companion), 12002 (quest definition)
        if (id1 in (14163, 14003, 12002)) and (id2 in (14163, 14003, 12002)):
            return True
        # Fred: 14164 (NPC), 14004 (companion), 12004 (quest definition)
        if (id1 in (14164, 14004, 12004)) and (id2 in (14164, 14004, 12004)):
            return True
        # Elin: 14165 (NPC), 14005 (companion), 12006 (quest definition)
        if (id1 in (14165, 14005, 12006)) and (id2 in (14165, 14005, 12006)):
            return True
        # Sam: 14166 (NPC), 14006 (companion), 12005 (quest definition)
        if (id1 in (14166, 14006, 12005)) and (id2 in (14166, 14006, 12005)):
            return True
        # Shizune: 14167 (NPC), 14007 (companion), 12015 (quest definition)
        if (id1 in (14167, 14007, 12015)) and (id2 in (14167, 14007, 12015)):
            return True
        # Suzan: 14168 (NPC), 14008 (companion), 12008 (quest definition)
        if (id1 in (14168, 14008, 12008)) and (id2 in (14168, 14008, 12008)):
            return True

        return False

    def _get_map_npc(self, map_id: int, click_id: int, session=None) -> Optional[Any]:
        if session and hasattr(session, "server") and session.server and hasattr(session.server, "map_npcs"):
            for npc in session.server.map_npcs.get(map_id, []):
                cid = getattr(npc, "click_id", None) or (npc.get("click_id") if isinstance(npc, dict) else None)
                if cid == click_id:
                    return npc

        from server.npc_manager import GLOBAL_NPC_MANAGER
        for npc in GLOBAL_NPC_MANAGER.map_npcs.get(map_id, []):
            cid = getattr(npc, "click_id", None) or (npc.get("click_id") if isinstance(npc, dict) else None)
            if cid == click_id:
                return npc
        return None

    def _get_all_map_npcs(self, map_id: int, session=None) -> List[Any]:
        if session and hasattr(session, "server") and session.server and hasattr(session.server, "map_npcs"):
            npcs = session.server.map_npcs.get(map_id)
            if npcs:
                return npcs
        from server.npc_manager import GLOBAL_NPC_MANAGER
        return GLOBAL_NPC_MANAGER.map_npcs.get(map_id, [])

    async def send_actor_hide(self, session, click_id: int):
        """Dispatches authentic dual hide packets (AC 22:10 despawn frame and AC 22:11 scene isolation frame)."""
        if not session or click_id <= 0:
            return
        pkt10 = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0xFF).write_8(0xFF)
        pkt11 = PacketWriter().write_8(22).write_8(11).write_16(click_id).write_8(0xFF).write_8(0xFF)
        await session.send_packet(pkt10)
        await session.send_packet(pkt11)
        if not hasattr(session, '_actor_visibility') or session._actor_visibility is None:
            session._actor_visibility = {}
        session._actor_visibility[click_id] = False

    async def send_actor_show(self, session, click_id: int):
        """Dispatches authentic dual show packets (AC 22:10 spawn frame and AC 22:11 stage reveal frame)."""
        if not session or click_id <= 0:
            return
        pkt10 = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0x00).write_8(0x00)
        pkt11 = PacketWriter().write_8(22).write_8(11).write_16(click_id).write_8(0x00).write_8(0x00)
        await session.send_packet(pkt10)
        await session.send_packet(pkt11)
        if not hasattr(session, '_actor_visibility') or session._actor_visibility is None:
            session._actor_visibility = {}
        session._actor_visibility[click_id] = True

    def has_recruited_companion(self, session, npc_name: str = "", template_id: int = 0) -> bool:
        """Determines if the player has recruited a companion by ID, alias, name, or quest completion."""
        if not session:
            return False

        COMPANION_ALIASES = {
            14161: 14001, 14162: 14001, 14001: 14001,  # Roca
            12032: 12178, 12178: 12178,                # Robinson
            14081: 14002, 14002: 14002,                # Niss
            14163: 14003, 14003: 14003,                # Clive
            14164: 14004, 14004: 14004,                # Fred
            14165: 14005, 14005: 14005,                # Elin
            14166: 14006, 14006: 14006,                # Sam
            14167: 14007, 14007: 14007,                # Shizune
            14168: 14008, 14008: 14008,                # Suzan
            17162: 10727, 10727: 10727,                # S.Monkey
        }

        alias_id = COMPANION_ALIASES.get(template_id, template_id)
        name_clean = (npc_name or "").lower().strip()

        # 1. Check session.pets / session.companions
        pets = getattr(session, "pets", []) or []
        for p in pets:
            if not isinstance(p, dict):
                continue
            p_id = p.get("pet_id", 0) or p.get("id", 0)
            p_alias = COMPANION_ALIASES.get(p_id, p_id)
            if alias_id > 0 and p_alias == alias_id:
                return True
            if p_id > 0 and template_id > 0 and (p_id == template_id):
                return True
            p_name = (p.get("pet_name") or p.get("name") or "").lower().strip()
            if name_clean and p_name and (name_clean in p_name or p_name in name_clean):
                return True

        # 2. Check active pet ID
        active_id = getattr(session, "active_pet_id", 0)
        if active_id > 0 and (active_id == template_id or COMPANION_ALIASES.get(active_id) == alias_id):
            return True

        # 3. Check quest completion / progress
        # Roca: Quest 13052 (state 2) or Quest 13098 (state 1 or 2)
        if alias_id == 14001 or "roca" in name_clean:
            q13052 = self._get_player_preevent_state(session, 13052)
            q13098 = self._get_player_preevent_state(session, 13098)
            if q13052 == 2 or q13098 in (1, 2):
                return True

        # Robinson: Quest 15283 in (1, 2) or Quest 15282 == 2 or Quest 902 == 2 or Quest 903 == 2 or Quest 12047 == 2
        if alias_id == 12178 or "robinson" in name_clean:
            q15283 = self._get_player_preevent_state(session, 15283)
            q15282 = self._get_player_preevent_state(session, 15282)
            q902 = self._get_player_preevent_state(session, 902)
            q903 = self._get_player_preevent_state(session, 903)
            q12047 = self._get_player_preevent_state(session, 12047)
            if q15283 in (1, 2) or q15282 == 2 or q902 == 2 or q903 == 2 or q12047 == 2:
                return True

        # S.Monkey: Quest 12018 (state 1 or 2)
        if alias_id == 10727 or "monkey" in name_clean:
            q12018 = self._get_player_preevent_state(session, 12018)
            if q12018 in (1, 2):
                return True

        return False

    async def evaluate_map_preevents(self, session, map_id: int):
        """Evaluates all PreEvents for target map against the player's quest marks and flags."""
        if not session:
            return

        try:
            handled_npcs: Set[int] = set()

            # 1. Hide any companions on this map that have already been recruited by this player (C# lines 33-43)
            all_npcs = self._get_all_map_npcs(map_id, session)
            for npc in all_npcs:
                c_id = getattr(npc, "click_id", None) or (npc.get("click_id") if isinstance(npc, dict) else None)
                n_name = getattr(npc, "name", "") or (npc.get("name", "") if isinstance(npc, dict) else "")
                t_id = getattr(npc, "npc_id", 0) or getattr(npc, "template_id", 0) or (npc.get("npc_id", 0) or npc.get("template_id", 0) if isinstance(npc, dict) else 0)
                if c_id and self.has_recruited_companion(session, n_name, t_id):
                    await self.send_actor_hide(session, c_id)
                    handled_npcs.add(c_id)

            # Map 10035 (Kelan Beach): Robinson recruitment lifecycle
            if map_id == 10035:
                has_robinson = self.has_recruited_companion(session, "Robinson", 12032)
                if has_robinson:
                    await self.send_actor_hide(session, 1)
                    handled_npcs.add(1)

            # Map 12000 (Kelan Village outdoors): Exact per-player quest lifecycle isolation matching official WLO
            if map_id == 12000:
                has_roca = self.has_recruited_companion(session, "Roca", 14162)

                # 1. Village Roca (ClickID 32):
                # On Map 12000 outdoors, Roca must strictly NEVER appear.
                # She is canonically located inside the Chief's House (Map 12001, ClickID 2).
                await self.send_actor_hide(session, 32)
                handled_npcs.add(32)

                # 2. Grave Rocas (ClickID 34 & ClickID 36):
                # Staged cutscene actors for Quest 13052 ("Death of Roca's Father").
                # ClickID 34 (mourning Roca) is only visible while Quest 13052 is InProgress (state 1) and not recruited.
                # ClickID 36 (standing Roca) is hidden while Quest 13052 is NotStarted (2) or Completed (3) or recruited.
                q13052_state = self._get_player_preevent_state(session, 13052)
                if q13052_state != 1 or has_roca:
                    await self.send_actor_hide(session, 34)
                else:
                    await self.send_actor_show(session, 34)
                handled_npcs.add(34)

                await self.send_actor_hide(session, 36)
                handled_npcs.add(36)

                # 3. Father's Statue (ClickID 33) & Iron Sword (ClickID 35):
                # Staged quest props for Quest 13098 ("Remembering Father").
                # Hidden while Quest 13098 is NotStarted (state 0) or Completed (state 2).
                if self._get_player_preevent_state(session, 13098) != 1:
                    await self.send_actor_hide(session, 33)
                    await self.send_actor_hide(session, 35)
                else:
                    await self.send_actor_show(session, 33)
                    await self.send_actor_show(session, 35)
                handled_npcs.add(33)
                handled_npcs.add(35)

                # 4. Lina's Shiba Inus (ClickID 28 & ClickID 20):
                # ClickID 29 is permanent dog sitting with Lina (always visible).
                # ClickID 28 is the missing dog next to Lina: hidden while Quest 13046 is NotStarted (0) or InProgress step 1.
                # ClickID 20 is lost dog in village: only visible during Quest 13046 InProgress step 1.
                q13046_state = self._get_player_preevent_state(session, 13046)
                q13046_step = self._get_player_quest_step(session, 13046)
                q13047_done = (self._get_player_preevent_state(session, 13047) == 1)

                if q13046_state == 0 or (q13046_state == 1 and q13046_step < 2 and not q13047_done):
                    await self.send_actor_hide(session, 28)
                else:
                    await self.send_actor_show(session, 28)
                handled_npcs.add(28)
                handled_npcs.add(29)  # Permanent dog always visible

                if q13046_state in (0, 2) or (q13046_state == 1 and q13046_step >= 2) or q13047_done:
                    await self.send_actor_hide(session, 20)
                else:
                    await self.send_actor_show(session, 20)
                handled_npcs.add(20)

                # 5. Baby Bees near Honeycomb (ClickID 18 & 19):
                if self._get_player_preevent_state(session, 13023) != 1:
                    await self.send_actor_hide(session, 18)
                    await self.send_actor_hide(session, 19)
                else:
                    await self.send_actor_show(session, 18)
                    await self.send_actor_show(session, 19)
                handled_npcs.add(18)
                handled_npcs.add(19)

                # 6. Staged Quest Pigs (ClickID 14, 15, 16):
                q12020_state = self._get_player_preevent_state(session, 12020)
                q12020_step = self._get_player_quest_step(session, 12020)
                q12021_done = (self._get_player_preevent_state(session, 12021) == 1)

                if not ((q12020_state == 1 and q12020_step >= 2) or q12020_state == 2 or q12021_done):
                    await self.send_actor_hide(session, 14)
                else:
                    await self.send_actor_show(session, 14)
                handled_npcs.add(14)

                if not (q12020_state == 1 and q12020_step == 1):
                    await self.send_actor_hide(session, 15)
                else:
                    await self.send_actor_show(session, 15)
                handled_npcs.add(15)

                if self._get_player_preevent_state(session, 13020) in (0, 2) or self._get_player_preevent_state(session, 13021) == 1:
                    await self.send_actor_hide(session, 16)
                else:
                    await self.send_actor_show(session, 16)
                handled_npcs.add(16)

                # 7. Permanent guideposts (10, 31) and honeycomb (17)
                handled_npcs.update([10, 17, 31])

            # Map 12001 (Chief's House):
            # ClickID 2 is Roca. Visible unless player has recruited her!
            # ClickID 3 is staged copy, always hidden.
            elif map_id == 12001:
                has_roca = self.has_recruited_companion(session, "Roca", 14162)
                if has_roca:
                    await self.send_actor_hide(session, 2)
                else:
                    await self.send_actor_show(session, 2)
                handled_npcs.add(2)
                await self.send_actor_hide(session, 3)
                handled_npcs.add(3)

            # Evaluate eve.Emg PreEvents for this map
            if map_id in self._map_preevents:
                preevents = self._map_preevents[map_id]
                for pe in preevents:
                    pe_cid = pe.get("click_id", 0) if isinstance(pe, dict) else 0
                    subentries = pe.get("subentries", pe) if isinstance(pe, dict) else pe
                    for sub in subentries:
                        cond_data = sub.get("condition")
                        if self._evaluate_condition_block(session, cond_data):
                            actions = sub.get("actions", [])
                            if actions:
                                for act_data in actions:
                                    action_op = act_data[1] if len(act_data) >= 2 else act_data[0]
                                    if action_op == 0x02:
                                        click_id = struct.unpack_from("<H", act_data, 2)[0] if len(act_data) >= 4 else struct.unpack_from("<H", act_data, 1)[0]
                                        if click_id not in handled_npcs:
                                            handled_npcs.add(click_id)
                                            await self._execute_action_block(session, act_data)
                                    else:
                                        await self._execute_action_block(session, act_data)
                            break

            # Completed one-time despawn events from eve.Emg (C# QuestManager.ReplayActorVisibility)
            from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
            map_evs = GLOBAL_EVE_INTERPRETER.map_events.get(map_id, {})
            for ev_cid, ev in map_evs.items():
                if ev_cid in handled_npcs:
                    continue
                for sub in ev.get("subs", []):
                    q_id = sub.get("w1", 0)
                    if q_id > 0 and self._get_player_preevent_state(session, q_id) == 2:
                        for op in sub.get("opcodes", []):
                            if op.get("dptr") == 2 and op.get("d2") == 2:
                                await self.send_actor_hide(session, ev_cid)
                                handled_npcs.add(ev_cid)
                                break
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error evaluating PreEvents for map {map_id}: {e}", exc_info=True)

    def _evaluate_condition_block(self, session, data: bytes) -> bool:
        if not data or len(data) < 8:
            return True

        chunk0_quest_id = 0

        # Each condition sub-entry contains up to 3 chunks of 7 bytes each starting at byte 1
        for ci in range(3):
            offset = 1 + ci * 7
            if offset + 7 > len(data):
                break
            op = data[offset]
            if op == 0x00:
                break

            # Opcode 0x05: Quest Mark / Flag Condition
            if op == 0x05:
                w1 = struct.unpack_from("<H", data, offset + 1)[0]
                w2 = struct.unpack_from("<H", data, offset + 3)[0]
                w3 = struct.unpack_from("<H", data, offset + 5)[0]

                if ci == 0:
                    chunk0_quest_id = w1
                    player_val = self._get_player_preevent_state(session, w1)
                    req_value = w2
                    comp_type = w3
                else:
                    if w1 == 0:
                        continue  # Empty / trailing chunk padding
                    elif w1 >= 1000:
                        # Secondary quest flag check
                        player_val = self._get_player_preevent_state(session, w1)
                        req_value = w2
                        comp_type = w3
                    else:
                        # Quest step check for chunk0_quest_id
                        player_val = self._get_player_quest_step(session, chunk0_quest_id)
                        req_value = w1
                        comp_type = w3 if w3 > 0 else 1

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

        return True

    async def _execute_action_block(self, session, data: bytes):
        if not session or not data or len(data) < 10:
            return

        action_op = data[1] if len(data) >= 2 else data[0]

        # Opcode 0x02: Actor Visibility / State Control
        if action_op == 0x02:
            click_id = struct.unpack_from("<H", data, 2)[0] if len(data) >= 4 else struct.unpack_from("<H", data, 1)[0]
            if len(data) >= 11 and (data[9] == 0xFF or data[10] == 0xFF):
                state1 = 0xFF
                state2 = 0xFF
            elif len(data) >= 11:
                state1 = data[9]
                state2 = data[10]
            else:
                state1 = data[8] if len(data) > 8 else 0
                state2 = data[9] if len(data) > 9 else 0

            # Only forward valid click IDs
            if 0 < click_id < 500:
                is_hide = (state1 == 0xFF and state2 == 0xFF)
                if is_hide:
                    await self.send_actor_hide(session, click_id)
                else:
                    # Standard actor state / animation frame update (AC 22:10) ONLY - matching C# PreEventInterpreter.cs:595
                    pkt10 = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(state1).write_8(state2)
                    await session.send_packet(pkt10)
                    if not hasattr(session, '_actor_visibility') or session._actor_visibility is None:
                        session._actor_visibility = {}
                    session._actor_visibility[click_id] = True

    def _get_player_preevent_state(self, session, flag_id: int) -> int:
        """
        Retrieves the player's quest lifecycle state matching authentic WLO Eve.emg PreEvent bytecode:
        0 = NotStarted (default for unaccepted / unstarted quests)
        1 = InProgress
        2 = Completed (chest opened, quest finished)
        """
        if not session or flag_id == 0:
            return 0

        from server.eve_event_interpreter import get_session_quest_state
        val = get_session_quest_state(session, flag_id)
        if val == 1:
            return 1
        elif val >= 2:
            return 2

        p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
        if flag_id in p_map:
            pq = p_map[flag_id]
            if pq.state == QuestState.IN_PROGRESS:
                return 1
            elif pq.state == QuestState.COMPLETED:
                return 2
            elif pq.state == QuestState.NOT_STARTED:
                return 0

        return 0

    def _get_player_flag_value(self, session, flag_id: int) -> int:
        """Compatibility alias for _get_player_preevent_state."""
        return self._get_player_preevent_state(session, flag_id)

    def _get_player_quest_step(self, session, quest_id: int) -> int:
        if not session or quest_id == 0:
            return 1
        raw = getattr(session, "quests", [])
        if isinstance(raw, list):
            for q in raw:
                if isinstance(q, dict) and str(q.get("quest_id", q.get("id", ""))) == str(quest_id):
                    return int(q.get("step", 1) or 1)
        elif isinstance(raw, dict):
            val = raw.get(str(quest_id))
            if isinstance(val, dict):
                return int(val.get("step", 1) or 1)
        p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
        if quest_id in p_map:
            return p_map[quest_id].step
        return 1

    def is_npc_visible_to_player(self, session, map_id: int, click_id: int) -> bool:
        """Returns whether a given NPC/object is currently visible to the player."""
        if not session or click_id <= 0:
            return True

        if hasattr(session, "_actor_visibility") and session._actor_visibility is not None:
            if click_id in session._actor_visibility:
                return bool(session._actor_visibility[click_id])

        # Permanent guideposts (10, 31) and honeycomb (17) on Map 12000 are always visible initially
        if map_id == 12000 and click_id in (10, 17, 31):
            return True

        # 1. Check if this map entity is a companion already recruited by the player (all maps)
        npc_obj = self._get_map_npc(map_id, click_id, session)
        if npc_obj is not None:
            n_name = getattr(npc_obj, "name", "") or (npc_obj.get("name", "") if isinstance(npc_obj, dict) else "")
            n_tid = getattr(npc_obj, "npc_id", 0) or getattr(npc_obj, "template_id", 0) or (npc_obj.get("npc_id", 0) or npc_obj.get("template_id", 0) if isinstance(npc_obj, dict) else 0)
            if self.has_recruited_companion(session, n_name, n_tid):
                return False

        # 2. Map 12000 (Kelan Village outdoors): Exact lifecycle visibility rules ported from PreEventInterpreter.cs
        if map_id == 12000:
            # 1. Father's Statue (33) & Iron Sword (35) (Quest 13098)
            if click_id in (33, 35):
                return self._get_player_preevent_state(session, 13098) == 1

            # 2. Grave Rocas (34 & 36)
            has_roca = self.has_recruited_companion(session, "Roca", 14162)
            if click_id == 34:
                q13052 = self._get_player_preevent_state(session, 13052)
                return (q13052 == 1 and not has_roca)
            if click_id == 36:
                return False

            # 3. Village Roca (32): Hidden on Map 12000 per user requirement
            if click_id == 32:
                return False

            # 4. Lina's Permanent Shiba Inu (29)
            if click_id == 29:
                return True

            # 5. Lina's Lost Shiba Inu (28): Hidden while NotStarted (0) or InProgress step 1
            if click_id == 28:
                q13046_state = self._get_player_preevent_state(session, 13046)
                q13046_step = self._get_player_quest_step(session, 13046)
                q13047_done = (self._get_player_preevent_state(session, 13047) == 1)
                if q13046_state == 0 or (q13046_state == 1 and q13046_step < 2 and not q13047_done):
                    return False
                return True

            # 6. Lost Shiba Inu in Village (20): Visible ONLY during InProgress step 1
            if click_id == 20:
                q13046_state = self._get_player_preevent_state(session, 13046)
                q13046_step = self._get_player_quest_step(session, 13046)
                q13047_done = (self._get_player_preevent_state(session, 13047) == 1)
                if q13046_state == 1 and q13046_step < 2 and not q13047_done:
                    return True
                return False

            # 7. Baby Bees (18 & 19)
            if click_id in (18, 19):
                return self._get_player_preevent_state(session, 13023) == 1

            # 8. Staged Pigs (14, 15, 16)
            if click_id == 14:
                q12020_state = self._get_player_preevent_state(session, 12020)
                q12020_step = self._get_player_quest_step(session, 12020)
                q12021_done = (self._get_player_preevent_state(session, 12021) == 1)
                return bool((q12020_state == 1 and q12020_step >= 2) or q12020_state == 2 or q12021_done)
            if click_id == 15:
                q12020_state = self._get_player_preevent_state(session, 12020)
                q12020_step = self._get_player_quest_step(session, 12020)
                return bool(q12020_state == 1 and q12020_step == 1)
            if click_id == 16:
                return not (self._get_player_preevent_state(session, 13020) in (0, 2) or self._get_player_preevent_state(session, 13021) == 1)

        # 3. Map 12001 (Chief's House): Roca ClickID 2 is visible unless recruited
        if map_id == 12001:
            if click_id == 2:
                return not self.has_recruited_companion(session, "Roca", 14162)
            if click_id == 3:
                return False

        # 4. Map 10035 (Kelan Beach): Robinson ClickID 1 is visible unless recruited
        if map_id == 10035 and click_id == 1:
            return not self.has_recruited_companion(session, "Robinson", 12032)

        # 5. Dynamic PreEvents from eve.Emg across all maps (C# ShouldNpcBeVisible)
        if map_id in self._map_preevents:
            preevents = self._map_preevents[map_id]
            for pe in preevents:
                pe_cid = pe.get("click_id", 0) if isinstance(pe, dict) else 0
                subentries = pe.get("subentries", pe) if isinstance(pe, dict) else pe
                for sub in subentries:
                    cond_data = sub.get("condition")
                    if self._evaluate_condition_block(session, cond_data):
                        actions = sub.get("actions", [])
                        targets_this_npc = False
                        if actions:
                            for act_data in actions:
                                action_op = act_data[1] if len(act_data) >= 2 else act_data[0]
                                if action_op == 0x02:
                                    target_click_id = struct.unpack_from("<H", act_data, 2)[0] if len(act_data) >= 4 else struct.unpack_from("<H", act_data, 1)[0]
                                    if target_click_id == click_id:
                                        targets_this_npc = True
                                        s1 = act_data[9] if len(act_data) >= 11 else act_data[8]
                                        s2 = act_data[10] if len(act_data) >= 11 else act_data[9]
                                        if s1 == 0xFF and s2 == 0xFF:
                                            return False
                                        else:
                                            return True
                        if targets_this_npc:
                            break
                        break

        # 6. Completed one-time despawn events from eve.Emg (C# QuestManager.ReplayActorVisibility)
        from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
        map_evs = GLOBAL_EVE_INTERPRETER.map_events.get(map_id, {})
        if click_id in map_evs:
            ev = map_evs[click_id]
            for sub in ev.get("subs", []):
                q_id = sub.get("w1", 0)
                if q_id > 0 and self._get_player_preevent_state(session, q_id) == 2:
                    for op in sub.get("opcodes", []):
                        if op.get("dptr") == 2 and op.get("d2") == 2:
                            return False

        return True

    async def sync_per_player_npc_visibility(self, server, session, map_id: int):
        """Synchronizes personal client-side NPC visibility based on dynamic Eve.emg PreEvents and quest state."""
        if not session or not map_id:
            return

        try:
            if not hasattr(session, "_actor_visibility") or session._actor_visibility is None:
                session._actor_visibility = {}

            # 1. Evaluate dynamic PreEvents bytecode from eve.Emg
            await self.evaluate_map_preevents(session, map_id)

            # 2. Evaluate dynamic database NPC visibility rules from game_npc_visibility
            try:
                from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
                vis_rules = GLOBAL_DYNAMIC_DATA.get_npc_visibility_rules(map_id)
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
                        current_state = self._get_player_flag_value(session, req_q_id)
                        if req_q_state == 1:  # In Progress
                            should_be_visible = (current_state == 1)
                        elif req_q_state in (2, 3):  # Completed
                            should_be_visible = (current_state == 2)
                        else:
                            should_be_visible = (current_state != 0)

                    # Hide if quest completed
                    if hide_q_comp and req_q_id > 0:
                        comp_state = self._get_player_flag_value(session, req_q_id)
                        if comp_state == 2:
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

                    prev_vis = session._actor_visibility.get(click_id)

                    # Send client state packet
                    if not should_be_visible:
                        await self.send_actor_hide(session, click_id)
                    else:
                        if prev_vis is False:
                            # Do NOT send show packet (AC 22:10 0,0) to static props/chests already loaded via AC 22:4
                            # In WLO, AC 22:10 resets sprite frames and causes chests/props to flicker/blink
                            is_static_prop = False
                            map_npcs = server.map_npcs.get(map_id, []) if hasattr(server, 'map_npcs') else []
                            for m_npc in map_npcs:
                                m_cid = m_npc.click_id if hasattr(m_npc, 'click_id') else (m_npc.get('click_id', 0) if isinstance(m_npc, dict) else 0)
                                if m_cid == click_id:
                                    if (hasattr(m_npc, 'is_static_npc') and m_npc.is_static_npc()) or (hasattr(m_npc, 'is_permanent_chest') and m_npc.is_permanent_chest()) or (isinstance(m_npc, dict) and ((19000 <= (m_npc.get('npc_id', 0) or m_npc.get('template_id', 0)) <= 35000) or (12000 <= (m_npc.get('npc_id', 0) or m_npc.get('template_id', 0)) <= 12999))):
                                        is_static_prop = True
                                    break
                            if not is_static_prop:
                                await self.send_actor_show(session, click_id)
                        else:
                            session._actor_visibility[click_id] = True
            except Exception as e:
                logger.warning(f"[PreEventInterpreter] Dynamic DB visibility error: {e}")

            # 3. Hide completed/recruited quest NPCs from registered definitions
            p_map = GLOBAL_QUEST_ENGINE.get_player_quests_dict(session)
            for q_id, pq in p_map.items():
                if pq.state == QuestState.COMPLETED:
                    quest = GLOBAL_QUEST_ENGINE.get_quest(q_id)
                    if quest and quest.map_id == map_id and quest.despawn_npc_click_ids:
                        for click_id in quest.despawn_npc_click_ids:
                            await self.send_actor_hide(session, click_id)
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error syncing per-player NPC visibility: {e}", exc_info=True)

    async def replay_actor_visibility(self, server, session, map_id: int):
        """Rebuilds the correct visible quest phase and actor states for the player on map entry."""
        if not session:
            return

        try:
            if not hasattr(session, "_actor_visibility") or session._actor_visibility is None:
                session._actor_visibility = {}

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
                            await self.send_actor_hide(session, npc["click_id"])
                            logger.info(f"[ActorVisibility] Despawned companion NPC '{npc['name']}' (ClickID {npc['click_id']}) for {session.char_name}")
        except Exception as e:
            logger.error(f"[PreEventInterpreter] Error in replay_actor_visibility: {e}", exc_info=True)


# Global singleton instance
GLOBAL_PREEVENT_INTERPRETER = PreEventInterpreter()
