"""
Wonderland Online Audio & Ambient Sound Broadcast Handler (AC 184)
Reverse-engineered from client decompile (aLogin.exe.1.c line 158042 sound\\wav0150.wav).
Handles interactive prop sound effects, bells, chime broadcasts, and environmental audio.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [184]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Sound Effect & Audio Broadcast packets (AC 184)."""
    try:
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 184 Audio packet. Sub={sub}")

        if sub == 1:  # Broadcast interactive sound effect
            sound_id = reader.read_16() if reader.remaining_bytes() >= 2 else 150
            logger.info(f"[{session.char_name}] AC 184:1 Trigger sound effect ID {sound_id}")

            # Broadcast sound packet to nearby players on the same map
            snd_pkt = (
                PacketWriter()
                .write_8(184)
                .write_8(1)
                .write_32(session.char_id)
                .write_16(sound_id)
            )
            if hasattr(server, "broadcast_to_map") and hasattr(session, "map_id"):
                server.broadcast_to_map(session.map_id, snd_pkt)
            else:
                await session.send_packet(snd_pkt)

        else:
            logger.info(f"[{session.char_name}] Unhandled AC 184 Sub-Code: {sub}")
            await session.send_packet(PacketWriter().write_8(184).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling AC 184: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
