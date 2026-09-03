"""
Wonderland Online - Action Code 75 (Item Mall Protocol) Handler
Ported from C# Src/Network/ActionCodes/AC75.cs & wlo.pserver.core/Game/PlayerRelated/ItemMallManager.cs
Handles:
- AC 75 Sub 1: Catalog request (sends AC 75:1 catalog and AC 75:3 balance)
- AC 75 Sub 2: Bonus Catalog request (sends AC 75:1 catalog and AC 75:3 balance)
- AC 75 Sub 3: Balance request (sends AC 75:3 balance)
- AC 75 Sub 4 / 5: Category switch (ACK AC 57:1) or item purchase with authentic S->C AC 75:4/5 response
"""

import logging
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [75]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 1:
        # Client requests Item Mall catalog (Points Mall)
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Requesting Points Mall Catalog (AC 75 Sub 1)")
        await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session, is_bonus=False)
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub == 2:
        # Client requests Bonus Mall catalog
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Requesting Bonus Mall Catalog (AC 75 Sub 2)")
        await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session, is_bonus=True)
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub == 3:
        # Client requests IM Point balance
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub in (4, 5):
        # Sub 4 / 5: Category switch (1 byte payload) OR Purchase (>1 byte payload)
        rem = reader.remaining_bytes()
        if rem == 1:
            category_id = reader.read_8()
            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Switched to Item Mall Category {category_id} (AC 75 Sub {sub})")
            # AC 57 Sub 1: Category ACK (Frame 4497 / 4606: 39 01 [catId] 00 00 00)
            ack = PacketWriter().write_8(57).write_8(1).write_8(category_id).write_8(0).write_8(0).write_8(0)
            await session.send_packet(ack)

            # Sync AC 34:1 Points & AC 75:3 Points for Minigames (Slot Machine / Claw Crane)
            points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
            p34 = PacketWriter().write_8(34).write_8(1).write_32(points)
            await session.send_packet(p34)
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)
            if category_id > 0:
                await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)
        else:
            is_bonus_purchase = (sub == 5)
            item_id = reader.read_16() if rem >= 2 else 0
            quantity = reader.read_8() if rem >= 3 else 1
            if quantity <= 0:
                quantity = 1

            entry = GLOBAL_ITEM_MALL_MANAGER.get_item(item_id, is_bonus=1 if is_bonus_purchase else 0)
            cost = (entry.point_cost * quantity) if entry else 0

            success = await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_id, quantity, is_bonus=is_bonus_purchase)
            if is_bonus_purchase:
                rem_points = GLOBAL_ITEM_MALL_MANAGER.get_user_bonus_points(session)
            else:
                rem_points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
            spent_points = cost if success else 0

            # Authentic Buy Response (aLogin.exe FUN_0025b5ec / 0x25b62f):
            # S->C AC 75 Sub [4 or 5]: [AC=75, Sub=4/5, RemPoints(4B), SpentPoints(4B), ItemID(2B), Quantity(1B)]
            resp = PacketWriter().write_8(75).write_8(sub).write_32(rem_points).write_32(spent_points).write_16(item_id).write_8(quantity)
            await session.send_packet(resp)

    else:
        logger.info(f"Unhandled AC 75 Sub-Code: {sub}, payload: {reader.data.hex()}")
