"""
Wonderland Online Item Mall Bonus Action Handler (Action Code 91 / 0x5B).
Reverse-engineered from authentic PCAP capture:
- itemmallvebonuskismi.pcapng (C2S: 5b 01 b0 de 00 -> S2C: 5b 02 b0 de 01 ...)

Protocol:
- AC 91 Sub 1 (C->S): Query bonus reward catalog: [0x5B, 0x01, category_id (2B LE), page (1B)]
- AC 91 Sub 2 (S->C): Bonus catalog response: [0x5B, 0x02, category_id (2B LE), page (1B), entries...]
  Each entry is 3 bytes: [item_id: uint16 LE, count: uint8]
- AC 91 Sub 3 (C->S): Claim bonus reward item: [0x5B, 0x03, item_id (2B LE)]
"""

import logging
from typing import Any
from server.network import PacketWriter, PacketReader

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [91]

# Authentic bonus items from PCAP capture
AUTHENTIC_BONUS_ITEMS = [
    (35135, 1),  # 0x893f
    (35136, 1),  # 0x8940
    (34029, 1),  # 0x84ed
    (34181, 1),  # 0x8585
    (33031, 1),  # 0x8107
    (34116, 1),  # 0x8544
    (34011, 1),  # 0x84db
    (34105, 1),  # 0x8539
    (34167, 1),  # 0x8577
    (30556, 1),  # 0x775c
    (22884, 1),  # 0x5964
]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Item Mall Bonus catalog and claims (AC 91)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC91 Item Mall Bonus. Sub={sub} (0x{sub:02X}), data={reader.data.hex()}")

    # Sub 1: Request Bonus Reward Catalog
    if sub == 1:
        cat_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0xDEB0
        page = reader.read_8() if reader.remaining_bytes() >= 1 else 0

        # Build authentic AC 91 Sub 2 response
        p = PacketWriter()
        p.write_8(91).write_8(2).write_16(cat_id).write_8(page if page > 0 else 1)
        for item_id, count in AUTHENTIC_BONUS_ITEMS:
            p.write_16(item_id)
            p.write_8(count)

        await session.send_packet(p)
        logger.info(f"[{session.char_name}] Sent AC 91 Sub 2 bonus list ({len(AUTHENTIC_BONUS_ITEMS)} items) for cat 0x{cat_id:04X}.")

    # Sub 3: Claim Bonus Item
    elif sub == 3:
        item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        bonus_pts = getattr(session, "im_bonus_points", 0)
        cost = 100  # Default 100 bonus points per claim

        if bonus_pts >= cost and item_id > 0:
            session.im_bonus_points -= cost
            from server.gameserver import add_item_to_inventory
            slot = add_item_to_inventory(session, item_id, 1)
            if slot is not None:
                # AC 23 Sub 6 acquisition popup
                p6 = PacketWriter().write_8(23).write_8(6).write_16(item_id).write_8(1).write_bytes(bytes(28))
                await session.send_packet(p6)
                await session.send_packet(server.build_inventory_packet(session))
                server.save_player_to_db(session)

                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"Claimed bonus item! Remaining Bonus Points: {session.im_bonus_points}"
                )
                await session.send_packet(sys_msg)
            else:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Inventory full! Cannot claim bonus item.")
                await session.send_packet(sys_msg)
        else:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Not enough Bonus Points to claim this reward.")
            await session.send_packet(sys_msg)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
