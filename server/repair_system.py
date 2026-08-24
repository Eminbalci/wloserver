"""
Wonderland Online Equipment Durability Decay & Repair System
Ported from C# wlo.pserver.core/Game/Crafting/EquipmentRepairManager.cs
"""

import logging
from typing import Dict, Optional, Any

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class EquipmentRepairManager:
    """Manages weapon and armor durability degradation and Spanner / NPC repairs."""

    DEFAULT_MAX_DURA: int = 250
    SPANNER_ITEM_ID: int = 38030

    @classmethod
    def process_combat_durability(cls, player, is_attacker: bool = True):
        """Reduces durability of equipped items during battle."""
        if not player or not getattr(player, "equip", {}):
            return

        for slot, item in player.equip.items():
            if not isinstance(item, dict):
                continue

            cur_dura = item.get("dura", cls.DEFAULT_MAX_DURA)
            max_dura = item.get("max_dura", cls.DEFAULT_MAX_DURA)

            # Weapons decay on attack, armor on defense
            if is_attacker and slot in (1, "weapon", "right_hand"):
                new_dura = max(0, cur_dura - 1)
                item["dura"] = new_dura
            elif not is_attacker and slot in (2, 3, 4, "armor", "helmet", "boots"):
                new_dura = max(0, cur_dura - 1)
                item["dura"] = new_dura

    @classmethod
    async def repair_item_with_spanner(
        cls,
        server,
        player,
        equip_slot: int,
        spanner_slot: int
    ) -> bool:
        if not player:
            return False

        from server.gameserver import remove_item_at_slot

        target_item = None
        spanner_item = None

        for it in player.inventory:
            if it.get("slot") == equip_slot:
                target_item = it
            elif it.get("slot") == spanner_slot:
                spanner_item = it

        if not target_item or not spanner_item or spanner_item.get("item_id") != cls.SPANNER_ITEM_ID:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "Please select an equipment to repair and a Spanner tool!"
            )
            await player.send_packet(sys_msg)
            return False

        # Consume 1 Spanner
        remove_item_at_slot(player, spanner_slot, 1)

        # Restore durability to max
        max_dura = target_item.get("max_dura", cls.DEFAULT_MAX_DURA)
        target_item["dura"] = max_dura

        # Play repair sound & animation (AC 5:5: 60025)
        spark_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60025)
        server.broadcast_to_map(player.map_id, spark_pkt)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Repair] Item #{target_item.get('item_id')} durability restored to {max_dura}/{max_dura}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[RepairManager] Player {player.char_name} repaired item #{target_item.get('item_id')} with spanner.")
        return True

    @classmethod
    async def repair_all_npc(cls, server, player) -> bool:
        """Repairs all inventory and equipped items at Blacksmith NPC for gold."""
        if not player:
            return False

        cost = 500  # Flat repair fee
        if player.gold < cost:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "You do not have enough gold to repair your equipment!"
            )
            await player.send_packet(sys_msg)
            return False

        player.gold -= cost

        for it in player.inventory:
            if "dura" in it:
                it["dura"] = it.get("max_dura", cls.DEFAULT_MAX_DURA)

        if getattr(player, "equip", None):
            for eq in player.equip.values():
                if isinstance(eq, dict) and "dura" in eq:
                    eq["dura"] = eq.get("max_dura", cls.DEFAULT_MAX_DURA)

        await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Blacksmith Repair] All equipment repaired for {cost} Gold!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        return True


GLOBAL_REPAIR_MANAGER = EquipmentRepairManager()
