"""
Wonderland Online Character Status & Title Sync Handler (AC 5)
Verified against authentic network captures (AC 5 Sub 7: 0x05 0x07 0x00).
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [5]

async def handle(server, session, reader):
    """Handles Player Character Title / Status Requests (AC 5)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name or session.ip}] AC 5 Sub={sub}")

    if sub == 7:  # Client Title / Status Request (PCAP: 05 07 00 -> Response: 05 08 [char_id: 4B] 00)
        mode = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        resp = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
        await session.send_packet(resp)
    elif sub == 4:  # Skill list ACK
        logger.info(f"[{session.char_name}] Skill list acknowledged by client.")
    else:
        logger.info(f"Unhandled AC 5 Sub: {sub}")
