"""
Wonderland Online Barber, Hair Styling & Color Dyeing System (AC 21)
Ported from C# Character appearance modification handlers
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class BarberManager:
    """Manages player hair style changes, hair dyeing, and clothing colors."""

    @staticmethod
    async def change_hair_style(
        server,
        player,
        new_style: int,
        new_color: int
    ) -> bool:
        if not player:
            return False

        cost = 1000  # Barber fee
        if player.gold < cost:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Barber styling costs 1,000 Gold!")
            await player.send_packet(sys_msg)
            return False

        player.gold -= cost
        player.hair_style = new_style
        player.hair_color = new_color

        # Broadcast look update to current map (AC 21 Sub 1)
        pkt = PacketWriter().write_8(21).write_8(1).write_32(player.char_id).write_8(new_style).write_16(new_color)
        server.broadcast_to_map(player.map_id, pkt)

        await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Barber] New hairstyle and color applied successfully!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[BarberManager] {player.char_name} updated hair style {new_style}, color {new_color}.")
        return True

    @staticmethod
    async def dye_clothing(
        server,
        player,
        dye_slot: int,
        clothing_color: int
    ) -> bool:
        if not player:
            return False

        from server.gameserver import remove_item_at_slot
        # Consume dye item
        remove_item_at_slot(player, dye_slot, 1)

        player.body_dye = clothing_color

        # Broadcast dye update (AC 21 Sub 2)
        pkt = PacketWriter().write_8(21).write_8(2).write_32(player.char_id).write_16(clothing_color)
        server.broadcast_to_map(player.map_id, pkt)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("[Dye] Clothing color dyed successfully!")
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        return True


GLOBAL_BARBER_MANAGER = BarberManager()
