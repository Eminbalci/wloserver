"""
Wonderland Online Item Recycle & Smelting Furnace System (AC 64:10)
Ported from C# Tent recycling and smelting mechanics
"""

import random
import logging
from typing import Dict, List, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class RecycleManager:
    """Manages smelting and dismantling obsolete weapons and armor into raw materials."""

    _cached_materials: List[int] = []

    @classmethod
    def get_materials(cls) -> List[int]:
        if not cls._cached_materials:
            cls.reload_from_db()
        return cls._cached_materials

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_materials.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            cls._cached_materials = GLOBAL_DYNAMIC_DATA.get_recycle_materials()
            logger.info(f"[RecycleManager] Loaded {len(cls._cached_materials)} dynamic recycle materials from database.")
        except Exception as e:
            logger.warning(f"[RecycleManager] Fallback recycle materials: {e}")
            cls._cached_materials = [27020, 27021, 27022, 27001, 27002]

    @classmethod
    async def smelt_equipment(
        cls,
        server,
        player,
        equip_slot: int
    ) -> bool:
        if not player or not getattr(player, "inventory", None):
            return False

        from server.gameserver import remove_item_at_slot, add_item_to_inventory

        target_item = next((it for it in player.inventory if it.get("slot") == equip_slot), None)
        if not target_item:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Please select an item to smelt!")
            await player.send_packet(sys_msg)
            return False

        item_id = target_item.get("item_id", 0)

        # Remove equipment
        remove_item_at_slot(player, equip_slot, 1)

        # Calculate recycled yield (1 to 3 random base materials)
        yield_mat = random.choice(cls.get_materials())
        yield_count = random.randint(1, 3)
        add_item_to_inventory(player, yield_mat, yield_count)

        # Broadcast smelting furnace spark (AC 5:5: 60025)
        fx_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60025)
        server.broadcast_to_map(player.map_id, fx_pkt)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Smelting Furnace] Dismantled Item #{item_id} into {yield_count}x Raw Material #{yield_mat}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[RecycleManager] Player {player.char_name} smelted #{item_id} -> {yield_count}x #{yield_mat}.")
        return True


GLOBAL_RECYCLE_MANAGER = RecycleManager()
