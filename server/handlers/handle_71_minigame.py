"""
Wonderland Online - Action Code 71 (Mini-Game Play & Prize Protocol) Handler
Handles:
- AC 71 Sub [minigame_id]: Client initiates play for Claw Crane (20), Doll Machine (7), Boxing (9), etc.
- Deducts 20 IM Points, broadcasts result, grants prizes.
"""

import logging
from server.network import PacketWriter
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
from server.minigames_system import GLOBAL_LUCKY_DRAW

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [71]


async def handle(server, session, reader):
    """Processes Mini-Game plays (Claw Crane, Boxing, Dolls)."""
    sub = reader.read_8()
    char_name = getattr(session, "char_name", "Player")
    logger.info(f"[{char_name}] AC 71 Mini-Game Play Request: Sub/GameID={sub}")

    user_points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(session)
    points_cost = 20

    if user_points < points_cost:
        logger.info(f"[{char_name}] Insufficient points for Mini-Game {sub} (has {user_points}, needs {points_cost})")
        # Response 2 = Not enough points
        err_pkt = PacketWriter().write_8(71).write_8(1).write_8(2)
        await session.send_packet(err_pkt)
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)
        return

    # 1. Deduct 20 IM Points
    rem_points = user_points - points_cost
    GLOBAL_ITEM_MALL_MANAGER.set_user_points(session, rem_points)

    # 2. Sync Points Balances (AC 34:1 and AC 75:3)
    p34 = PacketWriter().write_8(34).write_8(1).write_32(rem_points)
    await session.send_packet(p34)
    await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    # 3. Grant Play Permission (Sub 1, Result 1 = Start Game)
    start_pkt = PacketWriter().write_8(71).write_8(1).write_8(1)
    await session.send_packet(start_pkt)

    # 4. Determine Prize
    prizes = GLOBAL_LUCKY_DRAW.prizes
    if prizes:
        import random
        total_weight = sum(p[3] for p in prizes)
        roll = random.randint(1, total_weight)
        cur = 0
        awarded_prize = prizes[0]
        for p in prizes:
            cur += p[3]
            if roll <= cur:
                awarded_prize = p
                break

        prize_name, item_id, count, _ = awarded_prize
        if item_id > 0 and hasattr(session, "inventory"):
            if hasattr(server, "grant_item"):
                import inspect
                res = server.grant_item(session, item_id, count)
                if inspect.isawaitable(res):
                    await res
            logger.info(f"[{char_name}] Mini-Game {sub} won: {prize_name} (#{item_id} x{count})")

        # Send win packet: AC 71 Sub 2 [item_id(uint32), count(uint8)]
        win_pkt = PacketWriter().write_8(71).write_8(2).write_32(item_id).write_8(count)
        await session.send_packet(win_pkt)
