"""
Wonderland Online Trade & Stall Action Handler (AC 25 / AC 40)
Ported from C# Src/Network/ActionCodes/AC29.cs and AC56.cs
"""

import logging
from server.network import PacketWriter
from server.trade_system import GLOBAL_TRADE_SYSTEM
from server.stall_system import GLOBAL_STALL_MANAGER, StallItem

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [25, 40]


async def handle(server, session, reader):
    """Handles P2P Trade (AC 25) and Player Stalls (AC 40)."""
    opcode = reader.data[0] if len(reader.data) > 0 else 25

    if opcode == 25:
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC25 Trade Sub={sub}")

        if sub == 1:  # Request Trade
            target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            target_session = server.sessions.get(target_id)
            if target_session:
                await GLOBAL_TRADE_SYSTEM.request_trade(session, target_session)

        elif sub == 2:  # Accept Trade Request
            await GLOBAL_TRADE_SYSTEM.accept_trade(server, session)

        elif sub == 3:  # Offer Item
            slot = reader.read_8()
            item_id = reader.read_16()
            count = reader.read_8()
            await GLOBAL_TRADE_SYSTEM.add_item_to_trade(session, slot, item_id, count)

        elif sub == 4:  # Set Gold
            gold_amt = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            await GLOBAL_TRADE_SYSTEM.set_gold(session, gold_amt)

        elif sub == 5:  # Lock Offer
            await GLOBAL_TRADE_SYSTEM.lock_trade(session)

        elif sub == 6:  # Confirm / Accept Exchange
            await GLOBAL_TRADE_SYSTEM.confirm_trade(server, session)

        elif sub == 7:  # Cancel Trade
            await GLOBAL_TRADE_SYSTEM.cancel_trade(session)

    elif opcode == 40:
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC40 Stall Sub={sub}")

        if sub == 1:  # Open Stall
            stall_name = reader.read_string()
            count = reader.read_16()
            items = []
            for _ in range(count):
                if reader.remaining_bytes() >= 8:
                    slot = reader.read_8()
                    item_id = reader.read_16()
                    price = reader.read_32()
                    amt = reader.read_8()
                    items.append(StallItem(slot, item_id, price, amt))

            await GLOBAL_STALL_MANAGER.open_stall(server, session, stall_name, items)

        elif sub == 2:  # Close Stall
            await GLOBAL_STALL_MANAGER.close_stall(server, session)

        elif sub == 3:  # View Stall
            seller_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            await GLOBAL_STALL_MANAGER.view_stall(session, seller_id)

        elif sub == 4:  # Buy Item from Stall
            seller_id = reader.read_32()
            slot = reader.read_8()
            amt = reader.read_8()
            await GLOBAL_STALL_MANAGER.buy_item(server, session, seller_id, slot, amt)
