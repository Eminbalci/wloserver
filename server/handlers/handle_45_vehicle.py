"""
Wonderland Online Rail Track & Vehicle Navigation Handler (AC 45)
Reverse-engineered from client decompile (aLogin.exe.1.c line 236908 rail_H3, line 392213).
Handles minecart rail mounting, railway route progression, and vehicle travel state.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter
from server.vehicle_system import GLOBAL_VEHICLE_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [45]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Vehicle Rail & Travel Navigation packets (AC 45)."""
    try:
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 45 Vehicle Rail packet. Sub={sub}")

        if sub == 4:  # Mount / Dismount railway minecart (rail_H3)
            track_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            state = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            logger.info(f"[{session.char_name}] AC 45:4 Railway mount state: TrackID={track_id}, State={state}")

            if state == 1:
                # Board minecart
                session.active_vehicle_id = 36010
                mount_pkt = PacketWriter().write_8(15).write_8(10).write_32(session.char_id).write_16(36010)
                server.broadcast_to_map(session.map_id, mount_pkt)
            else:
                session.active_vehicle_id = 0
                dismount_pkt = PacketWriter().write_8(15).write_8(10).write_32(session.char_id).write_16(0)
                server.broadcast_to_map(session.map_id, dismount_pkt)

            # Response ACK (AC 45 Sub 4)
            resp = PacketWriter().write_8(45).write_8(4).write_16(track_id).write_8(state)
            await session.send_packet(resp)

        elif sub == 8:  # Railway travel waypoint ACK
            logger.debug(f"[{session.char_name}] AC 45:8 Railway waypoint ACK")
            resp = PacketWriter().write_8(45).write_8(8).write_8(1)
            await session.send_packet(resp)

        else:
            logger.info(f"[{session.char_name}] Unhandled AC 45 Sub-Code: {sub}")
            await session.send_packet(PacketWriter().write_8(45).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling AC 45: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
