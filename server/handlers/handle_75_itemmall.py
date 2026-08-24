"""
Wonderland Online - Action Code 75 (Item Mall Protocol) Handler
Handles:
- AC 75 Sub 1: Request in-game Item Mall catalog matrix
- AC 75 Sub 2: Purchase item request (ItemID, Quantity)
- AC 75 Sub 3: Request IM Point balance
"""

import logging
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [75]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 1:
        # Client requests Item Mall catalog
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Requesting Item Mall Catalog (AC 75 Sub 1)")
        await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)

    elif sub == 2:
        # Client requests Item Mall Purchase: [75, 2, ItemID(uint16), Quantity(uint8)]
        if len(reader.data) >= 4:
            item_id = reader.read_16()
            quantity = reader.read_8()
            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Purchasing {quantity}x Item #{item_id} (AC 75 Sub 2)")
            await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_id, quantity)
        else:
            logger.warning(f"[{getattr(session, 'char_name', 'Player')}] Malformed AC 75 Sub 2 packet: {reader.data.hex()}")

    elif sub == 3:
        # Client requests IM Point balance
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    else:
        logger.info(f"Unhandled AC 75 Sub-Code: {sub}, payload: {reader.data.hex()}")
