"""
Wonderland Online Manufacturing & Crafting Handler (AC 64)
Ported from C# Src/Network/ActionCodes/AC64.cs and wlo.pserver.core/Game/Crafting/TentManufactureManager.cs
"""

import logging
import asyncio
from server.network import PacketWriter
from server.gameserver import remove_item_at_slot, add_item_to_inventory
from server.tent_manufacture import GLOBAL_TENT_MANUFACTURE

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [64]

TEMP_RECIPE_MAP = {
    511: {"target_item": 47222, "time_seconds": 0},  # Coconut Basin
    38049: {"target_item": 38049, "time_seconds": 1},  # Work Platform
    46005: {"target_item": 46005, "time_seconds": 1},  # Refined Iron Ingot
    21001: {"target_item": 21001, "time_seconds": 2},  # Iron Longsword
    21010: {"target_item": 21010, "time_seconds": 2},  # Heavy Iron Armor
    30014: {"target_item": 30014, "time_seconds": 1},  # Fine Silk Cloth
    22005: {"target_item": 22005, "time_seconds": 2},  # Mage Robe
    48010: {"target_item": 48010, "time_seconds": 1},  # Ceramic Vase
    48011: {"target_item": 48011, "time_seconds": 1},  # Refined Brick
}


async def handle(server, session, reader):
    """Handles Crafting/Manufacturing (AC 64)."""
    sub = reader.read_8()

    if sub == 1:  # Craft Request
        if getattr(session, "bathing", False):
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Bathing, unable to make"))
            return

        unk1 = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        recipe_id_raw = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        craft_amount = reader.read_16() if reader.remaining_bytes() >= 2 else 1
        unk2 = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        num_materials = reader.read_16() if reader.remaining_bytes() >= 2 else 0

        # Read 5 material slots (10 bytes)
        materials = []
        for _ in range(5):
            if reader.remaining_bytes() >= 2:
                slot = reader.read_8()
                amount = reader.read_8()
                if slot != 0 or amount != 0:
                    materials.append({"slot": slot, "amount": amount})

        logger.info(f"[{session.char_name}] Craft Request -> Recipe: {recipe_id_raw}, Amt: {craft_amount}, Mats: {materials}")

        # 1. Deduct materials
        for mat in materials:
            remove_item_at_slot(session, mat["slot"], mat["amount"])
            deduct_pkt = PacketWriter().write_8(23).write_8(9).write_8(mat["slot"]).write_8(mat["amount"])
            await session.send_packet(deduct_pkt)

        # Get recipe info
        recipe_info = TEMP_RECIPE_MAP.get(recipe_id_raw, {"target_item": 0, "time_seconds": 0})
        target_item = recipe_info["target_item"]
        delay = recipe_info["time_seconds"]

        if target_item == 0:
            if hasattr(server, "get_compound_recipe"):
                c_recipe = server.get_compound_recipe(recipe_id_raw)
                if c_recipe:
                    target_item = c_recipe["result_item"]

            if target_item == 0:
                target_item = 47222  # Default to Coconut Basin
                delay = 0

        # 2. Start progress bar: AC 64 Sub 1
        start_ack = PacketWriter().write_8(64).write_8(1)
        start_ack.write_8(1).write_16(0x948B).write_32(0).write_8(1)
        await session.send_packet(start_ack)

        # AC 64 Sub 10 (Timer)
        timer_pkt = PacketWriter().write_8(64).write_8(10).write_8(0).write_32(0)
        await session.send_packet(timer_pkt)

        # 3. Asynchronously finish craft
        asyncio.create_task(finish_crafting(server, session, target_item, craft_amount, max(0.2, float(delay))))

    elif sub in (2, 3):  # Stop / continue craft
        await session.send_packet(PacketWriter().write_8(64).write_8(sub).write_8(1))
    else:
        logger.info(f"Unhandled AC 64 Sub-Code: {sub}, payload: {reader.data.hex()}")


async def finish_crafting(server, session, target_item: int, amount: int, delay: float):
    await asyncio.sleep(delay)
    add_item_to_inventory(session, target_item, amount)

    # Broadcast crafting sparkles animation
    sparkle_pkt = PacketWriter().write_8(5).write_8(5).write_32(session.char_id).write_16(60018)
    server.broadcast_to_map(session.map_id, sparkle_pkt)

    # AC 64 Sub 2 Finish
    finish_pkt = PacketWriter().write_8(64).write_8(2).write_8(1)
    await session.send_packet(finish_pkt)

    # Refresh inventory
    await session.send_packet(server.build_inventory_packet(session))
    logger.info(f"[{session.char_name}] Crafting completed. Added Item {target_item} x{amount}.")
