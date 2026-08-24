"""
Wonderland Online - Action Code 34 (Item Mall / Nesne Market) Handler
Ported from C# Src/Network/ActionCodes/AC34.cs
Protocol:
- AC 34 Sub 1 [0]: Initial points balance query when opening cart/mall
  Server responds with:
    - S->C AC 34 Sub 1 [Points(uint16)]
    - S->C AC 75 Sub 3 [Points(uint16)]
    - S->C AC 75 Sub 1 [Catalog Matrix]
- AC 34 Sub 1 [mode >= 1]: Cart checkout for slot/row mode
  Server responds with:
    - S->C AC 34 Sub 1 [RemainingPoints(uint16)]
    - S->C AC 75 Sub 3 [RemainingPoints(uint16)]
    - S->C AC 35 Sub 4 [16 zero bytes] (authentic pcap packet #142 confirmation)
    - S->C AC 75 Sub 1 [Catalog Matrix]
- AC 34 Sub 2: Direct Item Mall Purchase [34, 2, ItemID(uint16), Quantity(uint8)]
"""

import logging
from server.network import PacketWriter
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [34]


async def handle(server, session, reader):
    """Handles Item Mall / Shopping Cart actions (AC 34)."""
    sub = reader.read_8()

    if sub == 1:
        mode = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)

        if mode == 0:
            # Initial points query on Mall/Cart open
            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Item Mall balance query & open (AC 34 Sub 1 Mode 0)")
            resp = PacketWriter().write_8(34).write_8(1).write_16(min(65535, points))
            await session.send_packet(resp)
            await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)
            return

        # mode >= 1: Shopping Cart Checkout (Confirm button in Form_Cart)
        catalog = GLOBAL_ITEM_MALL_MANAGER.get_catalog()
        cat_index = mode - 1
        item_to_buy = catalog[cat_index] if (0 <= cat_index < len(catalog)) else (catalog[0] if catalog else None)

        if item_to_buy:
            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Cart Checkout Slot #{mode} -> {item_to_buy.item_name} (#{item_to_buy.item_id})")
            success = await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_to_buy.item_id, 1)
            rem_points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)

            # 1. S->C AC 34 Sub 1: [RemainingPoints(2B)] -> Triggers client banner "WLO Point Remain: %04d Pts"
            resp = PacketWriter().write_8(34).write_8(1).write_16(min(65535, rem_points))
            await session.send_packet(resp)

            # 2. S->C AC 75 Sub 3: [RemainingPoints(2B)] -> Updates GUI points counter
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

            # 3. S->C AC 35 Sub 4: [16 zero bytes] -> Authentic pcap #142 Cart Purchase confirmation
            p_cart = PacketWriter().write_8(35).write_8(4).write_bytes(bytes(16))
            await session.send_packet(p_cart)

            # 4. Send updated catalog
            await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)
        else:
            logger.warning(f"[{getattr(session, 'char_name', 'Player')}] No catalog item found for Cart Slot #{mode}")

    elif sub == 2:
        # In-game direct purchase: [34, 2, ItemID(uint16), Quantity(uint8)]
        if reader.remaining_bytes() >= 2:
            item_id = reader.read_16()
            quantity = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            if quantity <= 0:
                quantity = 1

            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Direct Mall Purchase #{item_id} x{quantity} (AC 34 Sub 2)")
            success = await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_id, quantity)
            rem_points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)

            # Sync points and catalog
            resp = PacketWriter().write_8(34).write_8(1).write_16(min(65535, rem_points))
            await session.send_packet(resp)
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

            p_cart = PacketWriter().write_8(35).write_8(4).write_bytes(bytes(16))
            await session.send_packet(p_cart)
            await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)
        else:
            logger.warning(f"[{getattr(session, 'char_name', 'Player')}] Malformed AC 34 Sub 2 packet: {reader.data.hex()}")

    else:
        logger.info(f"Unhandled AC 34 Sub-Code: {sub}, payload: {reader.data.hex()}")
