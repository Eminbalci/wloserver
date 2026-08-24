"""
Wonderland Online Cutscene & CG Movie Synchronization Handler (AC 186)
Ported from C# Src/Network/ActionCodes/AC186.cs
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [186]


async def handle(server, session, reader):
    """Handles CG Animation / Cutscene playback synchronization (AC 186)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name or getattr(session, 'username', 'Player')}] AC 186 Cutscene packet. Sub={sub}")

    if sub == 9:  # Cutscene playback acknowledgment from client (PCAP [013])
        cutscene_id = reader.read_16() if reader.remaining_bytes() >= 2 else 1
        logger.info(f"[{session.char_name}] Client acknowledged Cutscene #{cutscene_id} pre-arm readiness.")
        session.cutscene_ready = True
    else:
        logger.info(f"[{session.char_name}] Unhandled AC 186 Subcode: {sub}")
