"""
Wonderland Online NPC Shop System Handler (Action Code 27 / 0x1B).
Directly reverse-engineered from authentic shop packet captures:
- shoplarincalismamantigi.pcapng

Protocol Architecture:
- AC 27 Sub 3 (Server -> Client): Opens General / Props Shop Catalog window (1b 03).
- AC 27 Sub 4 (Server -> Client): Opens Weapon / Armor Shop Catalog window (1b 04).
- AC 27 Sub 2 (Client -> Server): Sells item from inventory slot: [0x1B, 0x02, slot_index, quantity].
  - Server updates inventory: AC 23 Sub 9 [0x17, 0x09, slot_index, remaining_quantity].
  - Server updates gold balance: AC 26 Sub 1 [0x1A, 0x01, gold (4 bytes LE)].
  - Server sends confirmation ACK: AC 27 Sub 2 [0x1B, 0x02, status=0].
- AC 27 Sub 1 (Client -> Server): Buys item from NPC merchant: [0x1B, 0x01, item_id (2 bytes LE), quantity].
  - Server checks gold funds and inventory capacity.
  - Server updates gold balance: AC 26 Sub 1 [0x1A, 0x01, gold (4 bytes LE)].
  - Server grants item: AC 23 Sub 6 [0x17, 0x06, item_id, quantity, padding].
  - Server sends confirmation ACK: AC 27 Sub 1 [0x1B, 0x01, status=0].
"""

import logging
from typing import Any
from server.network import PacketWriter, PacketReader

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [27]

# Default item sale prices if not defined in item properties
DEFAULT_ITEM_PRICES = {
    602: 50,    # Consumable
    603: 100,   # Consumable
    701: 200,   # Consumable
    702: 150,   # Consumable
    703: 250,   # Consumable
    27001: 50,  # Mount / Vehicle
    27005: 100, # Mount / Vehicle
}


async def handle(server: Any, session: Any, reader: PacketReader):
    """Dispatches Action Code 27 (0x1B) NPC Shop interactions."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC27 Shop Handler. Sub={sub} (0x{sub:02X}), data={reader.data.hex()}")

    # -------------------------------------------------------------
    # Sub 1: BUY ITEM FROM NPC SHOP
    # -------------------------------------------------------------
    if sub == 1:
        if reader.remaining_bytes() >= 4:
            # Format: [shop_id (1B), tab_id (1B), item_id (2B), amount (1B)] or [item_id (2B), amount (1B)]
            if reader.remaining_bytes() >= 5:
                _shop_id = reader.read_8()
                _tab_id = reader.read_8()
                item_id = reader.read_16()
                amount = max(1, reader.read_8())
            else:
                item_id = reader.read_16()
                amount = max(1, reader.read_8())
        elif reader.remaining_bytes() >= 2:
            item_id = reader.read_16()
            amount = max(1, reader.read_8()) if reader.remaining_bytes() > 0 else 1
        else:
            logger.warning(f"[{session.char_name}] AC27 Sub 1 malformed payload: {reader.data.hex()}")
            return

        # Price verification
        unit_price = DEFAULT_ITEM_PRICES.get(item_id, 100)
        total_price = unit_price * amount

        if getattr(session, "gold", 0) < total_price:
            logger.warning(f"[{session.char_name}] Shop purchase failed: insufficient gold ({session.gold} < {total_price})")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Not enough Gold!"))
            await session.send_packet(PacketWriter().write_8(27).write_8(1).write_8(1))  # Status 1 = Failure
            return

        from server.gameserver import add_item_to_inventory
        slot = add_item_to_inventory(session, item_id, amount=amount)
        if slot is None:
            logger.warning(f"[{session.char_name}] Shop purchase failed: inventory full")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Inventory is full!"))
            await session.send_packet(PacketWriter().write_8(27).write_8(1).write_8(2))  # Status 2 = Full
            return

        # Deduct gold & sync balance
        session.gold -= total_price
        server.save_player_to_db(session)

        # 1. Gold update (AC 26 Sub 1 - matching authentic pcap [Pkt #2365] 1a 01 [gold 4B LE])
        await session.send_packet(PacketWriter().write_8(26).write_8(1).write_32(session.gold))
        # Also send legacy AC 26 Sub 4 for compatibility
        await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))

        # 2. Item Delivery (AC 23 Sub 6)
        item_pkt = PacketWriter().write_8(23).write_8(6).write_16(item_id).write_8(amount).write_bytes(bytes(26))
        await session.send_packet(item_pkt)

        # 3. Buy Confirmation ACK (AC 27 Sub 1 status 0)
        await session.send_packet(PacketWriter().write_8(27).write_8(1).write_8(0))

        item_name = server.get_item_name(item_id) if hasattr(server, "get_item_name") else f"Item #{item_id}"
        logger.info(f"[{session.char_name}] Purchased {amount}x {item_name} for {total_price} Gold. Remaining: {session.gold}")

    # -------------------------------------------------------------
    # Sub 2: SELL ITEM TO NPC SHOP (Authentic Pcap Pkt #2346 / #2365)
    # Client -> Server: 1b 02 [slot_index] [amount] (e.g. 1b 02 18 01)
    # Server -> Client: 17 09 [slot_index] [remaining_amount]
    #                   1a 01 [gold (4B LE)]
    #                   1b 02 00 (ACK success)
    # -------------------------------------------------------------
    elif sub == 2:
        if reader.remaining_bytes() < 2:
            logger.warning(f"[{session.char_name}] AC27 Sub 2 malformed payload: {reader.data.hex()}")
            return

        slot_index = reader.read_8()
        amount_to_sell = max(1, reader.read_8())

        # Locate item in session.inventory by slot_index or sequential index
        target_item = None
        target_idx = None

        for idx, it in enumerate(session.inventory):
            it_slot = it.get("slot", idx + 1)
            if it_slot == slot_index:
                target_item = it
                target_idx = idx
                break

        if not target_item and 1 <= slot_index <= len(session.inventory):
            target_idx = slot_index - 1
            target_item = session.inventory[target_idx]

        if not target_item:
            logger.warning(f"[{session.char_name}] AC27 Sell failed: no item at slot {slot_index}")
            await session.send_packet(PacketWriter().write_8(27).write_8(2).write_8(1))  # Failure
            return

        current_amount = target_item.get("amount", 1)
        if current_amount < amount_to_sell:
            amount_to_sell = current_amount

        item_id = target_item.get("item_id", 0)
        # Authentic selling price calculation (approx 50% buy price or minimum 3 gold as observed in pcap)
        buy_price = DEFAULT_ITEM_PRICES.get(item_id, 10)
        unit_sell_price = max(3, buy_price // 2)
        total_sell_gold = unit_sell_price * amount_to_sell

        # Deduct quantity
        new_amount = current_amount - amount_to_sell
        if new_amount > 0:
            target_item["amount"] = new_amount
        else:
            session.inventory.pop(target_idx)

        # Increment player gold
        session.gold = getattr(session, "gold", 0) + total_sell_gold
        server.save_player_to_db(session)

        # 1. Update inventory slot quantity: AC 23 Sub 9 (matching [Pkt #2365] 17 09 [slot] [amount])
        await session.send_packet(
            PacketWriter()
            .write_8(23)
            .write_8(9)
            .write_8(slot_index)
            .write_8(max(0, new_amount))
        )

        # 2. Update character gold: AC 26 Sub 1 (matching [Pkt #2365] 1a 01 [gold 4B LE])
        await session.send_packet(
            PacketWriter()
            .write_8(26)
            .write_8(1)
            .write_32(session.gold)
        )
        # Also sync AC 26 Sub 4 for compatibility
        await session.send_packet(
            PacketWriter()
            .write_8(26)
            .write_8(4)
            .write_32(session.gold)
        )

        # 3. Sell Confirmation ACK: AC 27 Sub 2 (matching [Pkt #2365] 1b 02 00)
        await session.send_packet(
            PacketWriter()
            .write_8(27)
            .write_8(2)
            .write_8(0)
        )

        item_name = server.get_item_name(item_id) if hasattr(server, "get_item_name") else f"Item #{item_id}"
        logger.info(f"[{session.char_name}] Sold {amount_to_sell}x {item_name} from slot {slot_index} for +{total_sell_gold} Gold. Total: {session.gold}")

    # -------------------------------------------------------------
    # Sub 3: OPEN PROPS SHOP WINDOW (Server -> Client 1b 03)
    # -------------------------------------------------------------
    elif sub == 3:
        # Echo confirmation
        await session.send_packet(PacketWriter().write_8(27).write_8(3))
        await session.send_packet(PacketWriter().write_8(20).write_8(9))

    # -------------------------------------------------------------
    # Sub 4: OPEN WEAPON / EQUIPMENT SHOP WINDOW (Server -> Client 1b 04)
    # -------------------------------------------------------------
    elif sub == 4:
        # Echo confirmation
        await session.send_packet(PacketWriter().write_8(27).write_8(4))
        await session.send_packet(PacketWriter().write_8(20).write_8(9))

    else:
        logger.warning(f"[{session.char_name}] Unhandled AC 27 Sub: {sub}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
