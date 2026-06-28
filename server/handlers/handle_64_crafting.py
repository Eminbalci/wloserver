import logging
import asyncio
from server.network import PacketWriter
from server.gameserver import remove_item_at_slot, add_item_to_inventory

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [64]

# Temporary mapping from packet recipe ID to game Item ID and craft time
# This allows us to craft items while the Compound2.dat decryption is being perfected.
TEMP_RECIPE_MAP = {
    511: {"target_item": 47222, "time_seconds": 0},  # Coconut Basin
    # Add more here as needed
}

async def handle(server, session, reader):
    """Handles Crafting/Manufacturing (AC 64)."""
    sub = reader.read_8()
    
    if sub == 1:  # Craft Request
        # 40 01 01 00 FF 01 01 00 00 00 00 00 00 01 13 01 00 00 00 00 00 00 00 00
        unk1 = reader.read_8()
        recipe_id_raw = reader.read_16()
        craft_amount = reader.read_16()
        unk2 = reader.read_32()
        num_materials = reader.read_16()  # Or some unknown padding
        
        # In reality the client sends exactly 5 material slots (10 bytes)
        materials = []
        for _ in range(5):
            slot = reader.read_8()
            amount = reader.read_8()
            if slot != 0 or amount != 0:
                materials.append({"slot": slot, "amount": amount})
                
        logger.info(f"[{session.char_name}] Craft Request -> Recipe: {recipe_id_raw}, Amt: {craft_amount}, Mats: {materials}")
        
        # 1. Deduct materials
        for mat in materials:
            # Game uses 1-based or 0-based slots? PCAP sent 0x13 (19)
            remove_item_at_slot(session, mat["slot"], mat["amount"])
            deduct_pkt = PacketWriter().write_8(23).write_8(9).write_8(mat["slot"]).write_8(mat["amount"])
            await session.send_packet(deduct_pkt)
            
        # Get recipe info
        recipe_info = TEMP_RECIPE_MAP.get(recipe_id_raw, {"target_item": 0, "time_seconds": 0})
        target_item = recipe_info["target_item"]
        delay = recipe_info["time_seconds"]
        
        if target_item == 0:
            logger.warning(f"Recipe {recipe_id_raw} not mapped, defaulting to Coconut Basin (47222).")
            target_item = 47222
            delay = 0

        # 2. Start progress bar: AC 64 Sub 1 (Confirm)
        # 40 01 01 8B 94 00 00 00 00 01
        start_ack = PacketWriter().write_8(64).write_8(1)
        start_ack.write_8(1).write_16(0x948B).write_32(0).write_8(1)
        await session.send_packet(start_ack)
        
        # AC 64 Sub 10 (Timer)
        # 40 0A 00 00 00 00 00
        timer_pkt = PacketWriter().write_8(64).write_8(10).write_8(0).write_32(0)
        await session.send_packet(timer_pkt)
        
        # 3. Asynchronously wait for crafting time
        # Even if time is 0, give a tiny delay for network natural flow
        asyncio.create_task(finish_crafting(server, session, target_item, craft_amount, max(0.5, delay)))
        
    else:
        logger.info(f"Unhandled AC 64 Sub-Code: {sub}, payload: {reader.data.hex()}")

async def finish_crafting(server, session, target_item, amount, delay):
    await asyncio.sleep(delay)
    
    # Give the crafted item (using AC 23 Sub 6 to add to inventory)
    from server.gameserver import add_item_to_inventory
    add_item_to_inventory(session, target_item, amount)
    
    # Send Crafting complete: AC 64 Sub 2 [64, 2, 01]
    finish_pkt = PacketWriter().write_8(64).write_8(2).write_8(1)
    await session.send_packet(finish_pkt)
    
    logger.info(f"[{session.char_name}] Crafting completed. Added Item {target_item} x{amount}.")
