"""
Wonderland Online Activity / Online Rewards Handler (AC 183)
Verified against authentic network captures (AC 183 Sub 17).
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [183]

async def handle(server, session, reader):
    """Handles Online Activity / Event sync packets (AC 183)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name or session.ip}] AC 183 Activity Sub={sub}")
    
    if sub == 17:  # Heartbeat / Activity Status sync (Authentic: b7 11 00 -> Response: b7 11 00)
        status = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        resp = PacketWriter().write_8(183).write_8(17).write_8(status)
        await session.send_packet(resp)
    else:
        logger.info(f"Unhandled AC 183 Sub: {sub}")
