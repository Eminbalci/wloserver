"""
Wonderland Online Minimap, Target Lock, Tooltip & Focus Handler (AC 61, 69, 70, 74)
Reverse-engineered from client decompile (aLogin.exe.1.c line 390101, line 390104, line 390158, line 234706).
Handles map pins, target indicators, tooltip inspection queries, and client window focus states.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [61, 69, 70, 74]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Map Pin, Target Lock, Tooltip & Focus packets (AC 61, 69, 70, 74)."""
    try:
        action_code = reader.data[0] if len(reader.data) > 0 else 74
        sub = reader.read_8()

        if action_code == 74:  # Minimap Target Pin / Waypoint sync
            map_x = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            map_y = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            logger.info(f"[{session.char_name}] AC 74:2 Minimap Waypoint Pin: X={map_x}, Y={map_y}")
            # Broadcast or echo waypoint pin
            resp = PacketWriter().write_8(74).write_8(2).write_16(map_x).write_16(map_y)
            await session.send_packet(resp)

        elif action_code == 70:  # Target Focus / Lock Indicator
            target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            logger.debug(f"[{session.char_name}] AC 70:7 Target focus lock on ID {target_id}")
            resp = PacketWriter().write_8(70).write_8(7).write_32(target_id)
            await session.send_packet(resp)

        elif action_code == 69:  # Tooltip / Entity Hover Inspection
            entity_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            logger.debug(f"[{session.char_name}] AC 69 Tooltip hover inspection for entity {entity_id}")
            resp = PacketWriter().write_8(69).write_8(sub).write_32(entity_id)
            await session.send_packet(resp)

        elif action_code == 61:  # Window Focus / Idle Background State
            state = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            logger.debug(f"[{session.char_name}] AC 61 Window focus state: {state}")
            await session.send_packet(PacketWriter().write_8(61).write_8(1).write_8(state))

    except Exception as e:
        logger.error(f"Error handling AC 61/69/70/74: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
