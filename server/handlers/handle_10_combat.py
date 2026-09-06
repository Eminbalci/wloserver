"""
Wonderland Online Combat & Battle State Broadcast Handler (AC 10)
Reverse-engineered from live client gameplay packet captures.
Handles combat state synchronizations, encounter heartbeats, and battle aura broadcasts.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [10]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Combat and Encounter State packets (AC 10)."""
    sub = reader.read_8()
    logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 10 Combat State packet. Sub={sub}")

    if sub == 6:  # Encounter Heartbeat / Combat State Broadcast
        char_id = reader.read_32() if reader.remaining_bytes() >= 4 else getattr(session, "char_id", 0)
        state_flags = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        logger.info(f"[{session.char_name}] AC 10:6 Combat State update: CharID={char_id}, Flags={state_flags}")

        # Broadcast state synchronization to map players
        resp = (
            PacketWriter()
            .write_8(10)
            .write_8(6)
            .write_32(char_id)
            .write_16(state_flags)
        )
        await session.send_packet(resp)

    elif sub == 3:  # Battle Engagement / Aura Broadcast
        char_id = reader.read_32() if reader.remaining_bytes() >= 4 else getattr(session, "char_id", 0)
        aura_val = reader.read_8() if reader.remaining_bytes() >= 1 else 255
        logger.info(f"[{session.char_name}] AC 10:3 Battle Aura: CharID={char_id}, Aura={aura_val}")

        resp = (
            PacketWriter()
            .write_8(10)
            .write_8(3)
            .write_32(char_id)
            .write_8(aura_val)
        )
        if hasattr(server, "broadcast_to_map") and hasattr(session, "map_id"):
            server.broadcast_to_map(session.map_id, resp)
        else:
            await session.send_packet(resp)

    else:
        logger.info(f"[{session.char_name}] Unhandled AC 10 Sub-Code: {sub}, payload: {reader.data.hex()}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
