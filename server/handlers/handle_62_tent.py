"""
Wonderland Online Tent Interior & Furniture Action Handler (AC 62)
Ported from C# Src/Network/ActionCodes/AC62.cs
"""

import logging
from server.network import PacketWriter
from server.tent import GLOBAL_TENT_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [62]


async def handle(server, session, reader):
    """Handles Tent interior and furniture actions (AC 62)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC62 Tent Handler. Sub={sub}, payload={reader.data.hex()}")

    tent = GLOBAL_TENT_MANAGER.get_or_create_tent(session.char_id)

    if sub == 61:  # Enter Tent Request
        unk = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        bgm = reader.read_string_n() if reader.remaining_bytes() > 0 else "BGM0011"
        logger.info(f"[{session.char_name}] Entering tent interior (BGM: {bgm})")
        await GLOBAL_TENT_MANAGER.open_tent(server, session, bgm)

    elif sub == 1:  # Place Furniture Item into Tent
        # Format: Bag(1) + Slot(1) + X(4) + Y(4) + Floor(4)
        if reader.remaining_bytes() < 14:
            logger.warning(f"[{session.char_name}] Ignored short AC62:1 packet (remaining: {reader.remaining_bytes()})")
            return

        bag_index = reader.read_8()
        slot_index = reader.read_8()
        x = reader.read_32()
        y = reader.read_32()
        floor = reader.read_32()

        logger.info(f"[{session.char_name}] Place Furniture: Bag={bag_index} Slot={slot_index} Pos=({x}, {y}) Floor={floor}")

        from server.gameserver import remove_item_at_slot, get_item_at_slot
        target_item = get_item_at_slot(session, slot_index)
        place_item_id = target_item.get("item_id", 38027) if target_item else 38027

        if target_item:
            remove_item_at_slot(session, slot_index, 1)

        tent.place_item(place_item_id, x, y, floor, rotation=0)
        GLOBAL_TENT_MANAGER.save_tent_to_db(tent)

        # 1. Send Confirmation [62, 1, 1]
        confirm_pkt = PacketWriter().write_8(62).write_8(1).write_8(1)
        await session.send_packet(confirm_pkt)

        # 2. Resend all tent items
        await tent.send_tent_items_to_player(session)

        # 3. Update inventory UI
        await session.send_packet(server.build_inventory_packet(session))

    elif sub == 3:  # Move / Rotate Furniture
        # Format: Index(2) + X(4) + Y(4) + Floor/Dir(4) + Rotation(1)
        if reader.remaining_bytes() < 14:
            return

        index = reader.read_16()
        x = reader.read_32()
        y = reader.read_32()
        floor_dir = reader.read_32()
        rotation = reader.read_8() if reader.remaining_bytes() > 0 else 0

        logger.info(f"[{session.char_name}] Move Furniture: Index={index} to ({x}, {y}) Floor={floor_dir} Rot={rotation}")

        tent.move_item(index, x, y, floor_dir, rotation)
        GLOBAL_TENT_MANAGER.save_tent_to_db(tent)

        # Echo confirmation
        echo_pkt = PacketWriter().write_8(62).write_8(3)
        echo_pkt.write_16(index).write_32(x).write_32(y).write_32(floor_dir).write_8(rotation)
        await session.send_packet(echo_pkt)

        # Resend items to ensure alignment
        await tent.send_tent_items_to_player(session)

    elif sub == 4:  # Special Item Add / Decor
        await session.send_packet(PacketWriter().write_8(62).write_8(4).write_32(session.char_id).write_16(len(tent.items)))

    elif sub in (7, 14, 15):  # Floor / Wallpaper Styling
        color_val = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        if sub == 14: tent.floor1_color = color_val
        elif sub == 15: tent.floor1_wallpaper = color_val
        GLOBAL_TENT_MANAGER.save_tent_to_db(tent)
        await session.send_packet(PacketWriter().write_8(62).write_8(sub).write_16(color_val))

    elif sub == 45:  # Tent Presence & Furniture Sync Heartbeat
        char_id = reader.read_32() if reader.remaining_bytes() >= 4 else getattr(session, "char_id", 0)
        logger.info(f"[{session.char_name}] AC 62 Sub 45 Tent sync for Char #{char_id}")
        resp = PacketWriter().write_8(62).write_8(45).write_32(char_id)
        await session.send_packet(resp)

    else:
        logger.info(f"Unhandled AC 62 Sub-Code: {sub}, payload: {reader.data.hex()}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
