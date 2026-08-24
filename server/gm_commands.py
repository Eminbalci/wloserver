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

            else:
                await cls._send_reply(session, f"Unknown command ':{cmd}'. Type ':help' for assistance.")
        except Exception as e:
            logger.error(f"[GmCommand] Error executing ':{cmd}': {e}", exc_info=True)
            await cls._send_reply(session, f"Command error: {e}")

        return True

    @staticmethod
    async def _send_reply(session, msg: str):
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"[GM] {msg}")
        await session.send_packet(sys_msg)


GLOBAL_GM_COMMANDS = GmCommandProcessor()
