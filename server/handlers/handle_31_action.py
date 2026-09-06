"""
Wonderland Online Mail & Witch Doctor Action Handler (Action Code 31 / 0x1F)
Reverse-engineered from authentic PCAP captures:
- witchdoctor.pcapng (S2C: 1f 02 ff ff ff ff, 1f 07)
- Mail deletion protocol
"""

import logging
from typing import Any
from server.network import PacketWriter, PacketReader
from server.mail_system import GLOBAL_MAIL_SYSTEM

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [31]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Mail Deletion and Witch Doctor Actions (AC 31)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC31 Action. Sub={sub} (0x{sub:02X})")

    # Sub 1: Mail Deletion
    if sub == 1:
        mail_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        if mail_id > 0:
            await GLOBAL_MAIL_SYSTEM.delete_mail(session, mail_id)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

    # Sub 2: Witch Doctor Curse Removal & Full Revival (1f 02 ff ff ff ff)
    elif sub == 2:
        max_hp = getattr(session, "max_hp", 200)
        max_sp = getattr(session, "max_sp", 100)
        session.hp = max_hp
        session.sp = max_sp

        # HP / SP Full Recovery packets (AC 8 Sub 1)
        await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x0119).write_32(max_hp).write_32(0))
        await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x011a).write_32(max_sp).write_32(0))

        # Authentic Witch Doctor Cleanse ACK: [31, 2, 0xFF, 0xFF, 0xFF, 0xFF]
        cleanse_pkt = PacketWriter().write_8(31).write_8(2).write_bytes(bytes([0xFF, 0xFF, 0xFF, 0xFF]))
        await session.send_packet(cleanse_pkt)
        await session.send_packet(PacketWriter().write_8(20).write_8(9))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        logger.info(f"[{session.char_name}] Witch Doctor cleanse and HP/SP restored via AC 31 Sub 2.")

    # Sub 7: Witch Doctor Blessing / Purification (1f 07)
    elif sub == 7:
        blessing_pkt = PacketWriter().write_8(31).write_8(7)
        await session.send_packet(blessing_pkt)
        await session.send_packet(PacketWriter().write_8(20).write_8(9))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        logger.info(f"[{session.char_name}] Witch Doctor blessing granted via AC 31 Sub 7.")

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
