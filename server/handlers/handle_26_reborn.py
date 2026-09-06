"""
Wonderland Online Rebirth & Potential Allocation Handler (AC 26)
Reverse-engineered from client decompile (aLogin.exe.1.c line 280664 btn_module_2, line 325241).
Handles character rebirth job class awakening and potential attribute points distribution.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter
from server.reborn_system import GLOBAL_REBORN_MANAGER, RebornJob

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [26]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Rebirth & Potential stat allocation packets (AC 26)."""
    try:
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 26 Reborn packet. Sub={sub}")

        if sub == 3:  # Rebirth job transformation request
            job_id = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            logger.info(f"[{session.char_name}] AC 26:3 Rebirth transformation request for job {job_id}")
            if 1 <= job_id <= 6:
                success = await GLOBAL_REBORN_MANAGER.perform_reborn(server, session, RebornJob(job_id))
                resp = PacketWriter().write_8(26).write_8(3).write_8(1 if success else 0)
                await session.send_packet(resp)
            else:
                await session.send_packet(PacketWriter().write_8(26).write_8(3).write_8(0))

        elif sub == 2:  # Potential stat point allocation
            stat_type = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            points = reader.read_16() if reader.remaining_bytes() >= 2 else 1
            logger.info(f"[{session.char_name}] AC 26:2 Potential points allocation: Stat={stat_type}, Points={points}")
            # Acknowledge allocation
            resp = PacketWriter().write_8(26).write_8(2).write_8(stat_type).write_16(points)
            await session.send_packet(resp)
            await server.send_stats_update(session)

        else:
            logger.info(f"[{session.char_name}] Unhandled AC 26 Sub-Code: {sub}")
            await session.send_packet(PacketWriter().write_8(26).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling AC 26: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
