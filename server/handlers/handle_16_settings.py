"""
Wonderland Online Client Settings & Dialog Confirmation Handler (AC 16 & AC 55)
Reverse-engineered from client decompile (aLogin.exe.1.c line 452168, line 269060 btn_ok_1).
Handles BGM/SFX audio volumes, graphic options, and modal dialog confirmation responses.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [16, 55]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes System Settings & Modal Dialog packets (AC 16 & AC 55)."""
    try:
        action_code = reader.data[0] if len(reader.data) > 0 else 16
        sub = reader.read_8()

        if action_code == 16:  # System Options & Audio Settings
            val = reader.read_8() if reader.remaining_bytes() >= 1 else 100
            logger.debug(f"[{session.char_name}] AC 16:{sub} Setting sync: val={val}")
            # Echo ACK to prevent client timeout
            await session.send_packet(PacketWriter().write_8(16).write_8(sub).write_8(val))

        elif action_code == 55:  # Modal Dialog Confirmation (btn_ok_1 / btn_cancel)
            choice = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            dialog_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            logger.info(f"[{session.char_name}] AC 55:1 Modal confirmation: Choice={choice}, DialogID={dialog_id}")
            # Acknowledge dialog resolution
            await session.send_packet(PacketWriter().write_8(55).write_8(1).write_8(choice))

    except Exception as e:
        logger.error(f"Error handling AC 16/55: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
