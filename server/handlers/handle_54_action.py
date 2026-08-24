import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [54]

async def handle(server, session, reader):
    """Handles shop purchases, compound/crafting, and other AC 54 events."""
    sub = reader.read_8()
    logger.info(f"[AC54] handle_action_54 called. SubCmd={sub}, data: {reader.data.hex()}")
    
    from server.gameserver import add_item_to_inventory

    if sub == 3:  # Buy item from shop
        shop_id = reader.read_8()
        tab_id  = reader.read_8()
        item_id = reader.read_16()
        amount  = reader.read_8()
        item_prices = {602: 50, 603: 100, 701: 200, 702: 150, 703: 250, 27001: 50, 27005: 100}
        price = item_prices.get(item_id, 100) * amount
        if session.gold >= price:
            slot = add_item_to_inventory(session, item_id, amount=amount)
            if slot is not None:
                session.gold -= price
                server.save_player_to_db(session)
                await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                item_pkt = PacketWriter()
                item_pkt.write_8(23).write_8(6).write_16(item_id).write_8(amount).write_bytes(bytes(26))
                await session.send_packet(item_pkt)
                buy_confirm = PacketWriter()
                buy_confirm.write_8(54).write_8(3).write_8(shop_id).write_8(tab_id).write_16(item_id).write_8(amount)
                await session.send_packet(buy_confirm)
            else:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Sorry, inventory is full!"))
        else:
            logger.warning(f"[AC54] Not enough gold ({session.gold} < {price})")

    elif sub == 30:  # Compound / Crafting request
        compound_id = reader.read_16()
        recipe = server.get_compound_recipe(compound_id)
        if recipe:
            required_items = recipe.get("materials", [])
            result_item    = recipe.get("result_item", 0)
            result_amount  = recipe.get("result_amount", 1)
            can_craft = True
            for mat in required_items:
                total_owned = sum(it.get("amount", 0) for it in session.inventory if it.get("item_id") == mat["item_id"])
                if total_owned < mat["amount"]:
                    can_craft = False
                    break
            if can_craft and result_item > 0:
                for mat in required_items:
                    remaining = mat["amount"]
                    for it in session.inventory[:]:
                        if it.get("item_id") == mat["item_id"] and remaining > 0:
                            owned = it.get("amount", 1)
                            if owned <= remaining:
                                remaining -= owned
                                session.inventory.remove(it)
                            else:
                                it["amount"] = owned - remaining
                                remaining = 0
                add_item_to_inventory(session, result_item, amount=result_amount)
                server.save_player_to_db(session)
                await session.send_packet(server.build_inventory_packet(session))
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Compound success! Created {result_amount}x Item {result_item}!"))
            else:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Compound failed! Missing required materials."))
        else:
            logger.warning(f"[AC54] Unknown compound recipe ID: {compound_id}")
    else:
        logger.info(f"[AC54] Unhandled SubCmd: {sub}")
