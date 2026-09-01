"""
Wonderland Online - Action Code 57 (Category Switch / Exit Minigame / Mall Navigation) Handler
Ported from C# Src/Network/ActionCodes/AC57.cs
Handles:
- AC 57 Sub 1: Category Switch / Exit Minigame -> AC 57:1 ACK, AC 34:1 Points, AC 75:1 Catalog, AC 75:3 Points Balance, AC 5:4 Unfreeze
"""

import logging
from server.network import PacketWriter
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [57]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 1:
        category_id = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 57 Sub 1 (Category / Minigame Exit to Cat {category_id})")

        # 1. AC 57 Sub 1 ACK: [57, 1, catId, 0, 0, 0]
        ack = PacketWriter().write_8(57).write_8(1).write_8(category_id).write_8(0).write_8(0).write_8(0)
        await session.send_packet(ack)

        # 2. AC 34 Sub 1 & AC 75 Sub 3 Points Balance
        points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
        p34 = PacketWriter().write_8(34).write_8(1).write_32(points)
        await session.send_packet(p34)
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

        # 3. Only send catalog if navigating to a real mall category (> 0)
        if category_id > 0:
            await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)

        # 4. AC 5 Sub 4: Restore player HUD & control state when exiting minigame
        if category_id == 0:
            unfreeze = PacketWriter().write_8(5).write_8(4)
            await session.send_packet(unfreeze)
    else:
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Unhandled AC 57 SubCode: {sub}")
