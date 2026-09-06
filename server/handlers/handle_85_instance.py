"""
Wonderland Online Multi-Stage Party Instance Dungeon Handler (AC 85)
Reverse-engineered from client decompile (aLogin.exe.1.c line 176406).
Handles instance entrance, room wave transitions, ready checks, and reward claims.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter
from server.instance_system import GLOBAL_INSTANCE_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [85]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Party Instance Dungeon packets (AC 85)."""
    try:
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 85 Instance packet. Sub={sub}")

        if sub == 1:  # Enter instance request
            instance_id = reader.read_16() if reader.remaining_bytes() >= 2 else 1
            logger.info(f"[{session.char_name}] AC 85:1 Enter instance request for ID {instance_id}")
            success = await GLOBAL_INSTANCE_MANAGER.enter_instance(server, session, instance_id)
            if not success:
                # Send rejection ACK
                await session.send_packet(PacketWriter().write_8(85).write_8(1).write_8(0))

        elif sub == 2:  # Leave / Exit instance
            logger.info(f"[{session.char_name}] AC 85:2 Leave instance request")
            if session.char_id in GLOBAL_INSTANCE_MANAGER.active_instances:
                GLOBAL_INSTANCE_MANAGER.active_instances.pop(session.char_id)
            # Warp player back to Kelan Village
            await server.warp_player(session, 10000, 500, 500)
            await session.send_packet(PacketWriter().write_8(85).write_8(2).write_8(1))

        elif sub == 4:  # Ready check ACK
            status = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            logger.info(f"[{session.char_name}] AC 85:4 Ready check status={status}")
            await session.send_packet(PacketWriter().write_8(85).write_8(4).write_8(status))

        elif sub == 10:  # Countdown / Heartbeat timer ACK
            timer_val = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            logger.debug(f"[{session.char_name}] AC 85:10 Instance timer ACK: {timer_val}")
            await session.send_packet(PacketWriter().write_8(85).write_8(10).write_16(timer_val))

        elif sub == 11:  # Claim instance completion rewards
            logger.info(f"[{session.char_name}] AC 85:11 Claim instance reward request")
            await GLOBAL_INSTANCE_MANAGER.complete_instance(server, session)
            await session.send_packet(PacketWriter().write_8(85).write_8(11).write_8(1))

        else:
            logger.info(f"[{session.char_name}] Unhandled AC 85 Sub-Code: {sub}, payload: {reader.data.hex()}")
            await session.send_packet(PacketWriter().write_8(20).write_8(8))

    except Exception as e:
        logger.error(f"Error handling AC 85: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
