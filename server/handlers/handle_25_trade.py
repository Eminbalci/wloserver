"""
Wonderland Online Trade & Stall Action Handler (AC 25 / AC 40)
Ported from C# Src/Network/ActionCodes/AC29.cs and AC56.cs
"""

import logging
from server.network import PacketWriter
from server.trade_system import GLOBAL_TRADE_SYSTEM
from server.stall_system import GLOBAL_STALL_MANAGER, StallItem

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [25, 40, 56]


async def handle(server, session, reader):
    if reader.offset == 0 and len(reader.data) > 0 and reader.data[0] in (25, 40, 56):
        opcode = reader.read_8()
    elif reader.offset > 0 and len(reader.data) > 0:
        opcode = reader.data[0]
    else:
        opcode = 25

    if opcode == 25:
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC25 Trade Sub={sub}")

        if sub == 1:  # Request Trade
            target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            target_session = server.sessions.get(target_id)
            if target_session:
                await GLOBAL_TRADE_SYSTEM.request_trade(session, target_session)

        elif sub in (2, 21):  # Accept Trade Request (0x19:2, 0x19:0x15)
            await GLOBAL_TRADE_SYSTEM.accept_trade(server, session)

        elif sub == 3:  # Offer Item
            slot = reader.read_8()
            item_id = reader.read_16()
            count = reader.read_8()
            await GLOBAL_TRADE_SYSTEM.add_item_to_trade(session, slot, item_id, count)

        elif sub == 4:  # Set Gold
            gold_amt = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            await GLOBAL_TRADE_SYSTEM.set_gold(session, gold_amt)

        elif sub in (5, 10):  # Lock Offer (0x19:5, 0x19:10)
            await GLOBAL_TRADE_SYSTEM.lock_trade(session)

        elif sub in (6, 40):  # Confirm / Accept Exchange (0x19:6, 0x19:0x28)
            await GLOBAL_TRADE_SYSTEM.confirm_trade(server, session)

        elif sub in (7, 12, 42):  # Cancel Trade (0x19:7, 0x19:12, 0x19:0x2A)
            await GLOBAL_TRADE_SYSTEM.cancel_trade(session)

    elif opcode in (40, 56):
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC{opcode} Stall Sub={sub}")

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
