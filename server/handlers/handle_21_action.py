"""
Wonderland Online - Action Code 21 (Official Native Item Mall, Barber & Morph) Handler
Ported from C# Src/Network/ActionCodes/AC21.cs
Handles:
- AC 21 Sub 1: Open / Refresh Item Mall Native GUI Window (or Barber Hair Styling if params present)
- AC 21 Sub 2: Buy item from Native GUI (or Clothing Dye if params present)
- AC 21 Sub 3: Query IM Point balance
- AC 21 Sub 10: Monster Morph / Disguise
"""

import logging
from server.network import PacketWriter
from server.barber_system import GLOBAL_BARBER_MANAGER
from server.morph_system import GLOBAL_MORPH_MANAGER
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [21]


async def handle(server, session, reader):
    """Processes Native Item Mall, Barber, and Morphs (AC 21)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC21 Action Handler. Sub={sub}, rem_bytes={reader.remaining_bytes()}")

    if sub == 1:
        if reader.remaining_bytes() == 0:
            # Native In-Game Item Mall Window (C# AC21.SendMallWindow)
            logger.info(f"[{session.char_name}] Requesting Native Item Mall Window (AC 21 Sub 1)")
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

            # S->C AC 21 Sub 1: [21, 1, 21 slot entries 1..21]
            p = PacketWriter().write_8(21).write_8(1)
            for slot_idx in range(1, 22):
                p.write_8(slot_idx)
            await session.send_packet(p)
            await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)
        else:
            # Barber Hair Styling
            style = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            color = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            await GLOBAL_BARBER_MANAGER.change_hair_style(server, session, style, color)

    elif sub == 2:
        if reader.remaining_bytes() == 1:
            # Native GUI Slot Purchase
            slot = reader.read_8()
            catalog = GLOBAL_ITEM_MALL_MANAGER.get_catalog()
            if 1 <= slot <= len(catalog):
                item = catalog[slot - 1]
                logger.info(f"[{session.char_name}] Native Mall Slot #{slot} purchase: {item.item_name} (#{item.item_id})")
                await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item.item_id, item.count)
        else:
            # Clothing Dye
            slot = reader.read_8() if reader.remaining_bytes() >= 1 else 0
            color = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            await GLOBAL_BARBER_MANAGER.dye_clothing(server, session, slot, color)

    elif sub == 3:
        # Query Item Mall Point balance
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub == 10:  # Monster Morph / Disguise
        item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        if item_id > 0:
            await GLOBAL_MORPH_MANAGER.transform_player(server, session, item_id)
        else:
            await GLOBAL_MORPH_MANAGER.untransform_player(server, session)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
