"""
Wonderland Online Comprehensive GM Command Suite
Ported from C# wlo.pserver.core/Game/PlayerRelated/GmManager.cs
"""

import logging
from typing import List

from server.network import PacketWriter
from server.events_system import GLOBAL_EVENT_MANAGER
from server.weather_system import GLOBAL_WEATHER_MANAGER, WeatherType

logger = logging.getLogger("WLO_Server")


class GmCommandProcessor:
    """Executes administrator in-game chat commands."""

    @classmethod
    async def process_command(cls, server, session, message: str) -> bool:
        if not message.startswith(":"):
            return False

        if not getattr(session, "is_gm", False) and getattr(session, "user_id", 0) != 1:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("You do not have GM privileges!")
            await session.send_packet(sys_msg)
            return True

        tokens = message[1:].strip().split()
        if not tokens:
            return True

        cmd = tokens[0].lower()
        args = tokens[1:]

        try:
            if cmd == "item" and len(args) >= 1:
                item_id = int(args[0])
                count = int(args[1]) if len(args) >= 2 else 1
                from server.gameserver import add_item_to_inventory
                add_item_to_inventory(session, item_id, count)
                await session.send_packet(server.build_inventory_packet(session))
                await cls._send_reply(session, f"Granted {count}x Item #{item_id}.")

            elif cmd == "gold" and len(args) >= 1:
                amt = int(args[0])
                session.gold += amt
                await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                await cls._send_reply(session, f"Granted {amt} Gold (Total: {session.gold}).")

            elif cmd == "warp" and len(args) >= 3:
                map_id = int(args[0])
                x = int(args[1])
                y = int(args[2])
                await server.warp_player(session, map_id, x, y)
                await cls._send_reply(session, f"Warped to Map {map_id} ({x}, {y}).")

            elif cmd == "speed" and len(args) >= 1:
                mult = float(args[0])
                session.movement_speed_mult = mult
                await cls._send_reply(session, f"Movement speed set to {mult}x.")

            elif cmd == "level" and len(args) >= 1:
                session.level = int(args[0])
                await server.send_stats_update(session, levelup=True)
                await cls._send_reply(session, f"Level set to {session.level}.")

            elif cmd == "heal":
                session.hp = session.max_hp
                session.sp = session.max_sp
                await server.send_stats_update(session)
                await cls._send_reply(session, "Healed HP/SP to full.")

            elif cmd == "godmode":
                session.godmode = not getattr(session, "godmode", False)
                await cls._send_reply(session, f"Godmode: {session.godmode}.")

            elif cmd == "broadcast" and len(args) >= 1:
                bcast_text = " ".join(args)
                b_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"[Server Announcement] {bcast_text}")
                for s in server.sessions.values():
                    await s.send_packet(b_pkt)

            elif cmd == "doubleexp" and len(args) >= 1:
                hours = float(args[0])
                await GLOBAL_EVENT_MANAGER.start_double_exp_event(server, hours)

            elif cmd == "kick" and len(args) >= 1:
                target_name = args[0]
                target = next((s for s in server.sessions.values() if s.char_name.lower() == target_name.lower()), None)
                if target:
                    await target.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("You were kicked by GM."))
                    target.close()
                    await cls._send_reply(session, f"Kicked player {target_name}.")
                else:
                    await cls._send_reply(session, f"Player {target_name} not found.")

            elif cmd == "save":
                server.save_player_to_db(session)
                await cls._send_reply(session, "Player session saved to database.")

            elif cmd == "pet" and len(args) >= 2:
                subcmd = args[0].lower()
                if subcmd == "add":
                    pet_id = int(args[1])
                    pet_name = args[2] if len(args) >= 3 else f"Pet #{pet_id}"
                    if not hasattr(session, 'pets') or session.pets is None:
                        session.pets = []
                    if len(session.pets) >= 4:
                        await cls._send_reply(session, "Pet roster full (max 4 pets).")
                        return True
                    new_pet = {
                        "id": pet_id,
                        "pet_id": pet_id,
                        "name": pet_name,
                        "level": 10,
                        "hp": 500,
                        "max_hp": 500,
                        "sp": 200,
                        "max_sp": 200,
                        "amity": 100,
                        "str": 15,
                        "con": 15,
                        "int": 15,
                        "wis": 15,
                        "agi": 15,
                        "exp": 0,
                        "potential": 0,
                        "in_battle": False
                    }
                    session.pets.append(new_pet)
                    server.save_player_to_db(session)
                    await server.send_pet_list(session)
                    await cls._send_reply(session, f"Added pet {pet_name} (ID: {pet_id}) to party.")
                elif subcmd == "del":
                    slot = int(args[1])
                    if not hasattr(session, 'pets') or not session.pets or slot < 1 or slot > len(session.pets):
                        await cls._send_reply(session, f"Invalid pet slot {slot}.")
                        return True
                    removed = session.pets.pop(slot - 1)
                    server.save_player_to_db(session)
                    await server.send_pet_list(session)
                    await cls._send_reply(session, f"Deleted pet in slot {slot} ({removed.get('name', 'Pet')}).")
                else:
                    return False

            elif cmd == "quest":
                if not args:
                    await cls._send_reply(session, "Usage: :quest <reset|clear|set|status> [args]")
                    return True
                subcmd = args[0].lower()
                from server.eve_event_interpreter import get_session_quest_state, set_session_quest_state
                from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER

                if subcmd in ("clear", "reset") and len(args) == 1:
                    session.quests = []
                    if hasattr(session, '_player_quests_map'):
                        session._player_quests_map = None
                    server.save_player_to_db(session)
                    await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(server, session, session.map_id)
                    await cls._send_reply(session, "Cleared all quests for character.")
                elif subcmd == "reset" and len(args) >= 2:
                    qid = int(args[1])
                    if isinstance(session.quests, list):
                        session.quests = [q for q in session.quests if int(q.get("quest_id", q.get("id", 0))) != qid]
                    elif isinstance(session.quests, dict):
                        session.quests.pop(str(qid), None)
                    if hasattr(session, '_player_quests_map'):
                        session._player_quests_map = None
                    server.save_player_to_db(session)
                    await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(server, session, session.map_id)
                    await cls._send_reply(session, f"Reset quest {qid} to NotStarted.")
                elif subcmd == "set" and len(args) >= 3:
                    qid = int(args[1])
                    qst = int(args[2])
                    qstep = int(args[3]) if len(args) >= 4 else 1
                    set_session_quest_state(session, qid, qst, qstep)
                    server.save_player_to_db(session)
                    await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(server, session, session.map_id)
                    await cls._send_reply(session, f"Set quest {qid} to state {qst}, step {qstep}.")
                elif subcmd == "status":
                    qlist_str = str(session.quests)
                    await cls._send_reply(session, f"Quests: {qlist_str[:100]}")
                else:
                    return False

            else:
                return False
        except Exception as e:
            logger.error(f"[GmCommand] Error executing ':{cmd}': {e}", exc_info=True)
            await cls._send_reply(session, f"Command error: {e}")

        return True

    @staticmethod
    async def _send_reply(session, msg: str):
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"[GM] {msg}")
        await session.send_packet(sys_msg)


GLOBAL_GM_COMMANDS = GmCommandProcessor()
