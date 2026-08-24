"""
Automated Event Script Interpreter for Wonderland Online.
Directly parses and executes native event opcodes from eve.Emg, eliminating manual quest hardcoding.
Ported and enhanced from authentic WLO C# EveEventInterpreter.cs.
"""

import struct
import os
import logging
from typing import Dict, List, Any, Optional, Tuple

from server.network import PacketWriter
from server.dat_loaders import GLOBAL_NPC_DAT, GLOBAL_TALK_DAT

logger = logging.getLogger("EveInterpreter")


def get_session_quest_state(session: Any, quest_id: Any) -> int:
    """Safely retrieves quest state (0=not started, 1=in progress, 2=completed) across dict and list representations."""
    quests = getattr(session, "quests", None)
    if not quests:
        return 0
    str_qid = str(quest_id)
    if isinstance(quests, dict):
        return int(quests.get(str_qid, quests.get(quest_id, 0)) or 0)
    elif isinstance(quests, list):
        for q in quests:
            if isinstance(q, dict):
                if str(q.get("quest_id", q.get("id", ""))) == str_qid:
                    return int(q.get("state", 1) or 1)
            elif isinstance(q, (int, str)) and str(q) == str_qid:
                return 1
    return 0


def set_session_quest_state(session: Any, quest_id: Any, state: int):
    """Safely sets quest state on session, supporting both dict and list structures."""
    if not hasattr(session, "quests") or session.quests is None:
        session.quests = {}
    str_qid = str(quest_id)
    if isinstance(session.quests, dict):
        session.quests[str_qid] = state
    elif isinstance(session.quests, list):
        found = False
        for q in session.quests:
            if isinstance(q, dict) and str(q.get("quest_id", q.get("id", ""))) == str_qid:
                q["state"] = state
                found = True
                break
        if not found:
            session.quests.append({"quest_id": int(quest_id) if str_qid.isdigit() else quest_id, "state": state})


class EveEventInterpreter:
    """Parses and executes official bytecode events from eve.Emg across all game maps."""

    def __init__(self, eve_path: Optional[str] = None):
        self.map_events: Dict[int, Dict[int, Any]] = {}
        if not eve_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "eve.Emg")
            if os.path.exists(default_path):
                eve_path = default_path

        if eve_path and os.path.exists(eve_path):
            self.load(eve_path)

    def load(self, eve_path: str) -> bool:
        if not os.path.exists(eve_path):
            logger.warning(f"[EveInterpreter] eve.Emg not found at {eve_path}")
            return False

        try:
            with open(eve_path, "rb") as f:
                d = f.read()

            entrylen = struct.unpack_from("<I", d, 8)[0]
            ptr = 12
            maps = {}
            for _ in range(entrylen):
                map_id, scene_id, data_ptr, data_len = struct.unpack_from("<HHIH", d, ptr)
                ptr += 10
                maps[map_id] = {
                    "dataptr": data_ptr,
                    "datalen": data_len
                }

            self.map_events.clear()
            total_events = 0

            for map_id, m in maps.items():
                off_ptr = m["dataptr"] + m["datalen"] - 44
                if off_ptr + 44 > len(d):
                    continue

                offsets = struct.unpack_from("<IIIIIIIIIII", d, off_ptr)
                events_offset = offsets[4]
                ev_ptr = m["dataptr"] + events_offset
                if ev_ptr + 2 > len(d):
                    continue

                elen = struct.unpack_from("<H", d, ev_ptr)[0]
                cur_ptr = ev_ptr + 2
                map_events: Dict[int, Any] = {}

                for _ in range(elen):
                    if cur_ptr + 24 > len(d):
                        break
                    ev_cid = struct.unpack_from("<H", d, cur_ptr)[0]
                    cur_ptr += 2
                    unk1 = d[cur_ptr]
                    cur_ptr += 1
                    name_bytes = d[cur_ptr : cur_ptr + 20]
                    name = name_bytes.decode("cp950", errors="ignore").strip("\x00").strip()
                    cur_ptr += 20
                    blen = d[cur_ptr]
                    cur_ptr += 1
                    subs = []

                    for _ in range(blen):
                        if cur_ptr + 22 > len(d):
                            break
                        sub_idx = d[cur_ptr]
                        cur_ptr += 1
                        unkb1 = d[cur_ptr]
                        cur_ptr += 1
                        w1, w2, w3, w4, w5, w6 = struct.unpack_from("<HHHHHH", d, cur_ptr)
                        cur_ptr += 12
                        dw1, dw2 = struct.unpack_from("<II", d, cur_ptr)
                        cur_ptr += 8

                        blen2 = d[cur_ptr]
                        cur_ptr += 1
                        opcodes = []

                        for _ in range(blen2):
                            if cur_ptr + 22 > len(d):
                                break
                            ss_idx = d[cur_ptr]
                            dptr = d[cur_ptr + 1]
                            d1, d2, d3, d4 = struct.unpack_from("<HHHH", d, cur_ptr + 2)
                            odw1, odw2, odw3 = struct.unpack_from("<III", d, cur_ptr + 10)
                            cur_ptr += 22
                            opcodes.append({
                                "ss_idx": ss_idx,
                                "dptr": dptr,
                                "d1": d1, "d2": d2, "d3": d3, "d4": d4,
                                "dw1": odw1, "dw2": odw2, "dw3": odw3
                            })
                        subs.append({
                            "sub_idx": sub_idx,
                            "unkb1": unkb1,
                            "w1": w1, "w2": w2, "w3": w3, "w4": w4, "w5": w5, "w6": w6,
                            "dw1": dw1, "dw2": dw2,
                            "opcodes": opcodes
                        })

                    map_events[ev_cid] = {
                        "click_id": ev_cid,
                        "name": name,
                        "subs": subs
                    }
                    total_events += 1

                self.map_events[map_id] = map_events

            logger.info(f"[EveInterpreter] Loaded {total_events} native event trees across {len(self.map_events)} maps from {eve_path}.")
            return True
        except Exception as e:
            logger.error(f"[EveInterpreter] Error parsing eve.Emg: {e}")
            return False

    def select_matching_branch(self, session: Any, event_entry: Dict[str, Any], exclude_sub: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluates quest conditions and player state to choose the authentic branch from eve.Emg.
        Ported directly from C# EveEventInterpreter.SelectMatchingBranch.
        """
        subs = event_entry.get("subs", [])
        if not subs:
            return None
        if len(subs) == 1:
            return subs[0]

        # 0. Treasure Chests / Map Props (unkb1 == 3)
        chest_subs = [s for s in subs if s.get("unkb1") == 3]
        if chest_subs:
            chest_key = session.map_id * 1000 + event_entry.get("click_id", 1)
            is_opened = (get_session_quest_state(session, chest_key) >= 2)
            if is_opened:
                empty_branch = next((s for s in chest_subs if s.get("w4") == 261 or any(o["dptr"] == 1 and o["d1"] == 2 for o in s.get("opcodes", []))), None)
                if empty_branch:
                    return empty_branch
            else:
                loot_branch = next((s for s in chest_subs if s.get("w4") == 5 or any(o["dptr"] == 1 and o["d1"] == 1 for o in s.get("opcodes", []))), None)
                if loot_branch:
                    return loot_branch

        # 1. Evaluate Quests & Flags (unkb1 == 1, 2, 4, 15, etc.)
        for s in subs:
            if s == exclude_sub:
                continue
            unkb1 = s.get("unkb1", 0)
            if unkb1 == 7:  # Choice outcome branch, skip during initial branch selection
                continue

            q_id = s.get("w1", 0)
            req_state = s.get("w2", 0)
            req_step = s.get("w3", 0)

            if q_id > 0:
                current_state = get_session_quest_state(session, q_id)
                # If player already completed this quest step, check if sub matches completed state
                if req_state == 2 and current_state >= 2:
                    if s.get("opcodes"):
                        return s
                elif req_state == 1 and current_state == 1:
                    if s.get("opcodes"):
                        return s
                elif current_state == 0 and req_state == 0:
                    if s.get("opcodes"):
                        return s

        # 2. Fallback to first available root branch (excluding choice branches)
        for s in subs:
            if s != exclude_sub and s.get("unkb1") != 7 and s.get("opcodes"):
                return s

        return subs[0] if subs else None

    async def try_execute(self, server: Any, session: Any, click_id: int) -> bool:
        """
        Executes native eve.Emg event sequence for the clicked NPC or map object.
        Returns True if handled, False otherwise.
        """
        if not session or not session.map_id or click_id <= 0:
            return False

        map_events = self.map_events.get(session.map_id, {})
        if not map_events:
            return False

        # Find NPC in map_npcs
        map_npcs = server.map_npcs.get(session.map_id, [])
        npc = None
        for n in map_npcs:
            if n.get("click_id") == click_id:
                npc = n
                break

        event_entry = None
        if npc and npc.get("events"):
            for ev_id in npc["events"]:
                if ev_id in map_events:
                    event_entry = map_events[ev_id]
                    break

        if not event_entry and click_id in map_events:
            event_entry = map_events[click_id]

        if not event_entry or not event_entry.get("subs"):
            return False

        npc_tid = npc.get("npc_id", 0) if npc else 0
        raw_name = (npc.get("name") if npc else "").strip("\x00").strip()
        if not raw_name or raw_name.lower() in ("npc", "none") or raw_name.startswith("NPC #") or raw_name.startswith("unknown"):
            npc_name = GLOBAL_NPC_DAT.get_npc_name(npc_tid)
        else:
            npc_name = raw_name

        # Select matching branch
        selected_sub = self.select_matching_branch(session, event_entry)
        if not selected_sub or not selected_sub.get("opcodes"):
            logger.info(f"[EveInterpreter] Map #{session.map_id}, NPC #{click_id} '{npc_name}' -> No executable branch found.")
            return False

        logger.info(f"[EveInterpreter] Executing Map #{session.map_id}, NPC #{click_id} '{npc_name}' (TID: {npc_tid}) -> Event #{event_entry['click_id']} ('{event_entry.get('name', '')}'), Sub #{selected_sub.get('sub_idx')}")

        return await self.execute_sub_opcodes(server, session, click_id, event_entry, selected_sub)

    async def execute_sub_opcodes(self, server: Any, session: Any, click_id: int, event_entry: Dict[str, Any], sub: Dict[str, Any]) -> bool:
        """Executes opcodes of a given event sub-branch with multi-step dialogue and choice queuing."""
        opcodes = sub.get("opcodes", [])
        if not opcodes:
            return False

        executed_any = False
        dialogue_steps = []
        pending_choice = None
        post_dialogue_opcodes = []

        for op in opcodes:
            dptr = op.get("dptr", 0)
            d1, d2, d3, d4 = op.get("d1", 0), op.get("d2", 0), op.get("d3", 0), op.get("d4", 0)

            # Opcode 1: Item Grant / Take / Scene Transition / Player Speech Line
            if dptr == 1:
                # 1. Player Speech Line (dialog1 == 2, dialog2 >= 10000)
                if d1 == 2 and d2 >= 10000:
                    talk_id = d2
                    dialogue_text = GLOBAL_TALK_DAT.get(talk_id, "", player_name=session.char_name)
                    dialogue_steps.append({
                        "type": "dialogue",
                        "click_id": click_id,
                        "talk_id": talk_id,
                        "step": len(dialogue_steps) + 1,
                        "portrait": 7,  # Player portrait
                        "text": dialogue_text
                    })
                    executed_any = True
                elif d1 == 1 and d3 > 0:  # Item grant / take
                    item_id = d3
                    count = max(1, d2)
                    if d4 == 65280 or (d4 & 0xFF00) == 0xFF00:
                        # Consume / Remove item
                        from server.gameserver import remove_item_from_inventory
                        if remove_item_from_inventory(session, item_id, count):
                            item_name = server.items.get(str(item_id), f"Item #{item_id}")
                            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Lost {item_name}"))
                            executed_any = True
                    else:
                        # Grant item
                        from server.gameserver import add_item_to_inventory
                        if add_item_to_inventory(session, item_id, count):
                            item_name = server.items.get(str(item_id), f"Item #{item_id}")
                            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Obtained {item_name}!"))
                            await session.send_packet(PacketWriter().write_8(20).write_8(10))  # Fanfare SFX
                            executed_any = True
                elif d1 == 3:  # Scene Transition (Defer until interaction completes)
                    if session.map_id == 10017 or (10024 <= session.map_id <= 10028):
                        session.on_interaction_complete = {
                            "map_id": 10035,
                            "x": 1038,
                            "y": 2235,
                            "pending_beach": True
                        }
                        executed_any = True
                    elif session.map_id == 10035:
                        session.on_interaction_complete = {
                            "map_id": 11016,
                            "x": 402,
                            "y": 1035
                        }
                        executed_any = True

            # Opcode 2 / 0 / 4: Dialogue window or Choice Prompt
            elif dptr in (0, 2, 4):
                # 1. Choice Prompt (dialog2 == 6)
                if dptr == 2 and d2 == 6:
                    question_id = d3
                    layout = d1 if d1 > 0 else 1
                    portrait = 3
                    dialogue_steps.append({
                        "type": "choice",
                        "click_id": click_id,
                        "question_id": question_id,
                        "layout": layout,
                        "step": len(dialogue_steps) + 1,
                        "portrait": portrait,
                        "text": ""
                    })
                    pending_choice = {
                        "event_entry": event_entry,
                        "cur_sub": sub,
                        "question_id": question_id,
                        "click_id": click_id
                    }
                    executed_any = True
                else:
                    talk_id = 0
                    portrait = 3
                    if d3 >= 10000:
                        talk_id = d3
                        portrait = 7 if d2 == 2 else 3
                    elif d2 >= 10000:
                        talk_id = d2
                        portrait = 7 if d1 == 2 else 3

                    if talk_id > 0:
                        dialogue_text = GLOBAL_TALK_DAT.get(talk_id, "", player_name=session.char_name)
                        speaker_id = d1 if (dptr == 2 and d1 > 0 and d1 < 50) else click_id
                        dialogue_steps.append({
                            "type": "dialogue",
                            "click_id": speaker_id,
                            "talk_id": talk_id,
                            "step": len(dialogue_steps) + 1,
                            "portrait": portrait,
                            "text": dialogue_text
                        })
                        executed_any = True

            # Opcode 3: Companion Pet Recruitment
            elif dptr == 3:
                if d2 > 0:
                    companion_id = d2
                    pet_name = "Robinson" if companion_id == 12178 else f"Companion #{companion_id}"
                    from server.quests import GLOBAL_QUEST_ENGINE
                    await GLOBAL_QUEST_ENGINE.send_companion_reward(server, session, companion_id, pet_name)
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"{pet_name} has joined your party!"))
                    executed_any = True

            # Opcode 5: Quest Flag State Update
            elif dptr == 5:
                if d1 > 0:
                    quest_id = d1
                    step = max(1, d3 if d3 > 0 else (d4 >> 8 if d4 >> 8 > 0 else 1))
                    state = 2 if (d2 == 2 or step >= 250) else 1
                    set_session_quest_state(session, quest_id, state)
                    await server._send_quest_flag(session, quest_id, state)
                    executed_any = True

            # Opcode 6: Sound effect / Fanfare
            elif dptr == 6:
                await session.send_packet(PacketWriter().write_8(20).write_8(10))
                executed_any = True

            # Opcode 7: System Action / Storage / Clinic / Save Point / Shop
            elif dptr == 7:
                action_code = d1
                if action_code < 1000:
                    executed_any = await self._handle_system_action(server, session, click_id, action_code)

            # Opcode 8: Sound Effect / Thunder SFX / Storm Cutscene Trigger
            elif dptr == 8:
                if d4 == 31488 or (d4 & 0xFF00) == 0x7B00 or d1 == 2:
                    # Thunder / Storm Cutscene Movie Step
                    dialogue_steps.append({
                        "type": "storm_cutscene",
                        "step": len(dialogue_steps) + 1,
                        "d4": d4
                    })
                    executed_any = True
                else:
                    await session.send_packet(PacketWriter().write_8(20).write_8(10))
                    executed_any = True

            # Opcode 13 / 186: Cinematic Movie Trigger
            elif dptr in (13, 186):
                dialogue_steps.append({
                    "type": "storm_cutscene",
                    "step": len(dialogue_steps) + 1,
                    "d4": 31488
                })
                executed_any = True

            # Opcode 9: Warp / Teleport
            elif dptr == 9:
                if d1 > 0:
                    dst_map = d1
                    dst_x = op.get("dw1", 200)
                    dst_y = op.get("dw2", 300)
                    await server.warp_player(session, dst_map, dst_x, dst_y)
                    executed_any = True

            # Opcode 10: Gold Grant
            elif dptr == 10:
                gold_amount = d1
                if gold_amount > 0:
                    session.gold = getattr(session, "gold", 0) + gold_amount
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Obtained {gold_amount} Gold!"))
                    executed_any = True

            # Opcode 11: EXP Grant
            elif dptr == 11:
                exp_amount = d1
                if exp_amount > 0:
                    session.exp = getattr(session, "exp", 0) + exp_amount
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Obtained {exp_amount} EXP!"))
                    executed_any = True

        # Attach pending choice context to session
        session.pending_dialogue_choice = pending_choice

        # Dispatch dialogue steps
        if dialogue_steps:
            session.dialogue_queue = dialogue_steps[1:]  # Queue remaining steps
            first_step = dialogue_steps[0]
            await self._dispatch_step(server, session, first_step)
            executed_any = True

        return executed_any

    async def _dispatch_step(self, server: Any, session: Any, step_info: Dict[str, Any]):
        """Dispatches a dialogue, choice prompt, or cinematic cutscene step to the client."""
        step_type = step_info.get("type", "dialogue")
        step_num = step_info.get("step", 1)
        portrait = step_info.get("portrait", 3)
        speaker_id = step_info.get("click_id", 0)

        if step_type == "storm_cutscene":
            logger.info(f"[EveInterpreter] Starting Storm Cutscene Video (AC 186:9 & AC 20:1 Step {step_num}) for {session.char_name}")
            session.playing_storm_cutscene = True
            
            # 1. AC 186:9 Cutscene playback start signal (matching PCAP [017])
            await session.send_packet(
                PacketWriter()
                .write_8(186)
                .write_8(9)
                .write_16(1)  # cutscene_id = 1
                .write_8(1)   # active / playing
                .write_32(0)  # padding
            )
            
            # 2. AC 20:1 Step 3 Event Trigger with Thunder SFX (matching PCAP [018])
            pkt = (
                PacketWriter()
                .write_8(20)
                .write_8(1)
                .write_8(0).write_8(0).write_8(0)
                .write_8(step_num)
                .write_8(5)  # Type 5: Special Cinematic Event
                .write_8(0).write_8(0).write_8(0)
                .write_8(2)  # Param 2
                .write_8(0x7B).write_8(0x00) # Thunder SFX (0x7B00)
                .write_32(0) # 4 zero padding bytes
            )
            await session.send_packet(pkt)

            # 3. SFX Packets (matching PCAP [020]-[021])
            await session.send_packet(PacketWriter().write_8(35).write_8(12).write_8(0x16).write_8(0x19).write_8(1).write_8(0).write_8(0))
            await session.send_packet(PacketWriter().write_8(35).write_8(12).write_8(0xA0).write_8(0xE2).write_8(3).write_8(0).write_8(0))
        elif step_type == "choice":
            question_id = step_info.get("question_id", 1)
            layout = step_info.get("layout", 1)
            logger.info(f"[EveInterpreter] Sending Choice Prompt Step {step_num} (Question #{question_id}) to {session.char_name}")
            # Choice Packet: [20, 1, 0, 0, 0, step, 6, portrait, speaker, 0, 0, 0, 0, 0, 0, qLSB, qMSB, layout]
            pkt = (
                PacketWriter()
                .write_8(20)
                .write_8(1)
                .write_8(0).write_8(0).write_8(0)
                .write_8(step_num)
                .write_8(6)  # Choice flag
                .write_8(portrait)
                .write_8(speaker_id)
                .write_8(0)
                .write_32(0)  # 4-byte zeroes
                .write_8(0)
                .write_8(question_id & 0xFF)
                .write_8((question_id >> 8) & 0xFF)
                .write_8(layout if layout > 0 else 1)
            )
            await session.send_packet(pkt)
        else:
            talk_id = step_info.get("talk_id", 0)
            text = step_info.get("text", "")
            logger.info(f"[EveInterpreter] Sending Dialogue Step {step_num} (TalkID: {talk_id}, Portrait: {portrait}): '{text[:60]}'")
            await server.send_dialogue(session, speaker_id, talk_id, step=step_num, portrait_type=portrait)
            if text:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(text))

            # If the upcoming step is storm cutscene, pre-arm the client movie player with AC 186:12 (matching PCAP [012])
            queue = getattr(session, 'dialogue_queue', None)
            if queue and len(queue) > 0 and queue[0].get("type") == "storm_cutscene":
                logger.info(f"[EveInterpreter] Pre-arming client for Storm Movie with AC 186:12")
                await session.send_packet(PacketWriter().write_8(186).write_8(12).write_8(1).write_8(0).write_8(0).write_8(0).write_8(0))

    async def handle_choice_selection(self, server: Any, session: Any, choice_val: int) -> bool:
        """
        Executes the choice branch corresponding to the player's selected option in AC 20 Sub 2 / Sub 9.
        Ported directly from C# EveEventInterpreter.OnDialogueChoice.
        """
        pending = getattr(session, "pending_dialogue_choice", None)
        if not pending:
            return False

        session.pending_dialogue_choice = None
        event_entry = pending.get("event_entry", {})
        cur_question_id = pending.get("question_id", 0)
        click_id = pending.get("click_id", 0)

        branch_idx = (choice_val - 0x28) if choice_val >= 0x28 else ((choice_val - 0x1E) if choice_val >= 0x1E else max(0, choice_val - 1))
        target_choice_val = 30 + branch_idx

        logger.info(f"[EveInterpreter] Player {session.char_name} chose option 0x{choice_val:X} ({choice_val}) -> branch index {branch_idx} (target: {target_choice_val}) for Question #{cur_question_id}")

        subs = event_entry.get("subs", [])
        choice_sub = None

        # 1. Exact match on question ID and choice value (unkb1 == 7)
        for s in subs:
            if s.get("unkb1") == 7:
                w1 = s.get("w1", 0)
                w2 = s.get("w2", 0)
                if (cur_question_id == 0 or w1 == cur_question_id or w1 == 0) and (w2 == target_choice_val or w2 == choice_val):
                    choice_sub = s
                    break

        # 2. Fallback: match by relative index among choice branches
        if not choice_sub:
            choice_subs = [s for s in subs if s.get("unkb1") == 7 and (cur_question_id == 0 or s.get("w1") == cur_question_id or s.get("w1") == 0)]
            if 0 <= branch_idx < len(choice_subs):
                choice_sub = choice_subs[branch_idx]

        if not choice_sub:
            logger.warning(f"[EveInterpreter] No matching choice sub-branch found for option {choice_val} in Event #{event_entry.get('click_id')}")
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            return True

        logger.info(f"[EveInterpreter] Executing choice branch Sub #{choice_sub.get('sub_idx')} for {session.char_name}")
        await self.execute_sub_opcodes(server, session, click_id, event_entry, choice_sub)
        return True

    async def _handle_system_action(self, server: Any, session: Any, click_id: int, action_code: int) -> bool:
        """Handles Opcode 7 system action codes (1=Weapon Shop, 2=Props Shop, 4=Storage, 5=Save Point, 7=Clinic)."""
        if action_code in (1, 2, 3):
            catalog_id = 0x0001FB84 if action_code == 1 else (0x0001FB83 if action_code == 3 else 0x0001FB85)
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(35).write_8(12).write_32(catalog_id).write_8(0))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            return True
        elif action_code in (4, 9):
            # Storage / Props Keeper
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Storage opened."))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            return True
        elif action_code == 5:
            # Save Respawn Memory Point
            save_text = GLOBAL_TALK_DAT.get(0x0379B6, "Memory point saved!")
            await server.send_dialogue(session, click_id, 0x0379B6, step=1, portrait_type=3)
            await session.send_packet(PacketWriter().write_8(5).write_8(21).write_8(1))
            await session.send_packet(PacketWriter().write_8(20).write_8(10))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            return True
        elif action_code in (6, 7):
            # Clinic Doctor Full HP / SP Restore
            max_hp = getattr(session, "max_hp", 200)
            max_sp = getattr(session, "max_sp", 100)
            session.hp = max_hp
            session.sp = max_sp
            await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x0119).write_32(max_hp).write_32(0))
            await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x011a).write_32(max_sp).write_32(0))
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("HP and SP fully restored!"))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            return True
        return False


# Global singleton
GLOBAL_EVE_INTERPRETER = EveEventInterpreter()
