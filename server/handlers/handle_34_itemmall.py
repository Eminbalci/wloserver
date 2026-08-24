"""
Wonderland Online - Action Code 34 (Item Mall / Nesne Market) Handler
Handles in-game client Item Mall window requests, category configuration, and purchases.
"""

import logging
from server.network import PacketWriter
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [34]


async def handle(server, session, reader):
    """Handles Item Mall (Nesne Market) requests (AC 34)."""
    sub = reader.read_8()

    if sub == 1:
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Requesting Item Mall opening (AC 34 Sub 1)")

        # 1. Send Item Mall Categories/Config: AC 54 (0x36) Sub 201 (0xC9)
        # Binary catalog payload from ItemMallServer
        from server.item_mall import ItemMallServer
        cat_pkt = PacketWriter().write_8(54).write_8(201)
        cat_payload = ItemMallServer().build_catalog_payload()
        cat_pkt.write_bytes(cat_payload)
        await session.send_packet(cat_pkt)

        # 2. Send Wallet Balances: AC 35 (0x23) Sub 4
        points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
        wallet_pkt = PacketWriter().write_8(35).write_8(4)
        wallet_pkt.write_32(points)
        wallet_pkt.write_32(getattr(session, 'im_bonus_points', 1000))
        wallet_pkt.write_32(getattr(session, 'im_tokens', 50))
        wallet_pkt.write_32(0)  # Padding
        await session.send_packet(wallet_pkt)

        # 3. Send End of Mall Data Signal: AC 35 (0x23) Sub 11 (0x0B)
        end_pkt = PacketWriter().write_8(35).write_8(11)
        await session.send_packet(end_pkt)

    elif sub == 2:
        # In-game Item Mall Purchase: [34, 2, ItemID(uint16), Quantity(uint8)]
        if len(reader.data) >= 4:
            item_id = reader.read_16()
            quantity = reader.read_8()
            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Purchasing {quantity}x Item #{item_id} (AC 34 Sub 2)")
            success = await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_id, quantity)

            # Re-send wallet balance
            points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
            wallet_pkt = PacketWriter().write_8(35).write_8(4)
            wallet_pkt.write_32(points)
            wallet_pkt.write_32(getattr(session, 'im_bonus_points', 1000))
            wallet_pkt.write_32(getattr(session, 'im_tokens', 50))
            wallet_pkt.write_32(0)
            await session.send_packet(wallet_pkt)

            # End of mall data signal
            await session.send_packet(PacketWriter().write_8(35).write_8(11))
        else:
            logger.warning(f"[{getattr(session, 'char_name', 'Player')}] Malformed AC 34 Sub 2 packet: {reader.data.hex()}")

    else:
        logger.info(f"Unhandled AC 34 Sub-Code: {sub}, payload: {reader.data.hex()}")
