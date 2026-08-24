"""
Wonderland Online Mailbox Action Handler (AC 30)
Ported from C# Src/Network/ActionCodes/AC30.cs
"""

import logging
from server.network import PacketWriter
from server.mail_system import GLOBAL_MAIL_SYSTEM

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [30]


async def handle(server, session, reader):
    """Processes Mailbox interactions (AC 30)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC30 Mail Handler. Sub={sub}")

    if sub == 1:  # Get Inbox List
        await GLOBAL_MAIL_SYSTEM.send_inbox_list(session)

    elif sub == 2:  # Send Mail
        receiver_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        subject = reader.read_string()
        content = reader.read_string()
        gold = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        item_count = reader.read_8() if reader.remaining_bytes() >= 1 else 0

        await GLOBAL_MAIL_SYSTEM.send_mail(
            server, session, receiver_id, subject, content, gold, item_id, item_count
        )

    elif sub == 3:  # Claim Attachment
        mail_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        await GLOBAL_MAIL_SYSTEM.claim_attachment(server, session, mail_id)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
