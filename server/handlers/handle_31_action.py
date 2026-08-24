"""
Wonderland Online Mail Deletion Action Handler (AC 31)
Ported from C# Src/Network/ActionCodes/AC31.cs
"""

import logging
from server.network import PacketWriter
from server.mail_system import GLOBAL_MAIL_SYSTEM

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [31]


async def handle(server, session, reader):
    """Processes Mail Deletion (AC 31)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC31 Mail Delete. Sub={sub}")

    if sub == 1:  # Delete Mail
        mail_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        if mail_id > 0:
            await GLOBAL_MAIL_SYSTEM.delete_mail(session, mail_id)
    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
