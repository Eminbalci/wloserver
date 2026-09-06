"""
Wonderland Online Auxiliary Client Protocol Handler (AC 7, 28, 51, 66, 90, 199)
Reverse-engineered from client decompile (aLogin.exe.1.c line 396578, line 274455, line 390768, line 442762, line 208524, line 301365).
Handles client keepalive pings, crafting status, hotbar macros, guild war challenges, and storage tabs.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [7, 28, 51, 66, 90, 199]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Auxiliary Protocol packets (AC 7, 28, 51, 66, 90, 199)."""
    try:
        action_code = reader.data[0] if len(reader.data) > 0 else 7
        sub = reader.read_8()

        if action_code == 7:  # Keepalive ping
            logger.debug(f"[{session.char_name}] AC 7 Keepalive Ping ACK")
            await session.send_packet(PacketWriter().write_8(7).write_8(sub).write_8(1))

        elif action_code == 28:  # Crafting / Recipe Progress
            logger.info(f"[{session.char_name}] AC 28:{sub} Recipe progress check")
            await session.send_packet(PacketWriter().write_8(28).write_8(sub).write_8(1))

        elif action_code == 51:  # Hotbar / Quick action bar sync
            slot = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            skill_item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            logger.debug(f"[{session.char_name}] AC 51 Quickbar slot {slot} bound to {skill_item_id}")
            await session.send_packet(PacketWriter().write_8(51).write_8(sub).write_8(slot).write_16(skill_item_id))

        elif action_code == 66:  # Guild War / Group Challenge
            target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            logger.info(f"[{session.char_name}] AC 66:{sub} Challenge issued to TargetID {target_id}")
            await session.send_packet(PacketWriter().write_8(66).write_8(sub).write_32(target_id))

        elif action_code == 90:  # Extended bag tab switch
            tab_index = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            logger.debug(f"[{session.char_name}] AC 90 Bag tab switched to {tab_index}")
            await session.send_packet(PacketWriter().write_8(90).write_8(sub).write_8(tab_index))

        elif action_code == 199:  # Custom macro / Hotkey binding sync
            macro_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            logger.debug(f"[{session.char_name}] AC 199 Macro binding #{macro_id}")
            await session.send_packet(PacketWriter().write_8(199).write_8(sub).write_16(macro_id))

        else:
            await session.send_packet(PacketWriter().write_8(action_code).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling Auxiliary AC {action_code}: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
