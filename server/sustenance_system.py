"""
Wonderland Online Auto-Recovery Sustenance & Rice Ball System
Ported from C# wlo.pserver.core/Game/PlayerRelated/RiceBall.cs
"""

import logging
from typing import Dict, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class SustenanceManager:
    """Manages player HP/SP auto-recovery pools and post-combat healing."""

    _cached_items: Dict[int, int] = {}

    @classmethod
    def get_pool_amount(cls, item_id: int) -> Optional[int]:
        if not cls._cached_items:
            cls.reload_from_db()
        return cls._cached_items.get(item_id)

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_items.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_sus = GLOBAL_DYNAMIC_DATA.get_sustenance_items()
            for it_id, d in db_sus.items():
                cls._cached_items[it_id] = d.get("hp_buffer", 50000)
            logger.info(f"[SustenanceManager] Loaded {len(cls._cached_items)} dynamic sustenance items from database.")
        except Exception as e:
            logger.warning(f"[SustenanceManager] Fallback sustenance: {e}")
            cls._cached_items = {
                30025: 50000,
                30026: 100000,
                30001: 5000,
            }

    @classmethod
    async def use_sustenance_item(
        cls,
        server,
        player,
        slot: int,
        item_id: int
    ) -> bool:
        pool_amount = cls.get_pool_amount(item_id)
        if not player or pool_amount is None:
            return False

        from server.gameserver import remove_item_at_slot

        remove_item_at_slot(player, slot, 1)

        player.sustenance_hp = getattr(player, "sustenance_hp", 0) + pool_amount
        player.sustenance_sp = getattr(player, "sustenance_sp", 0) + pool_amount

        # Send animation & message (AC 5:5: 60012)
        love_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60012)
        server.broadcast_to_map(player.map_id, love_pkt)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Auto-Recovery] Consumed Rice Ball! Added +{pool_amount} HP/SP to Auto-Heal Pool (Total: {player.sustenance_hp} HP / {player.sustenance_sp} SP)!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[SustenanceManager] {player.char_name} charged auto-heal pool +{pool_amount}.")
        return True

    @classmethod
    async def trigger_post_battle_recovery(cls, server, player):
        """Automatically heals player and active battle pets to maximum HP/SP."""
        if not player:
            return

        cur_hp_pool = getattr(player, "sustenance_hp", 0)
        cur_sp_pool = getattr(player, "sustenance_sp", 0)

        if cur_hp_pool <= 0 and cur_sp_pool <= 0:
            return

        needed_hp = max(0, player.max_hp - player.hp)
        needed_sp = max(0, player.max_sp - player.sp)

        if needed_hp > 0:
            heal_hp = min(needed_hp, cur_hp_pool)
            player.hp += heal_hp
            player.sustenance_hp = cur_hp_pool - heal_hp

        if needed_sp > 0:
            heal_sp = min(needed_sp, cur_sp_pool)
            player.sp += heal_sp
            player.sustenance_sp = cur_sp_pool - heal_sp

        # Also heal active pets
        if getattr(player, "pets", None):
            for p in player.pets:
                p_max_hp = p.get("max_hp", 500)
                p_cur_hp = p.get("hp", p_max_hp)
                p_need_hp = max(0, p_max_hp - p_cur_hp)
                if p_need_hp > 0 and player.sustenance_hp > 0:
                    p_heal = min(p_need_hp, player.sustenance_hp)
                    p["hp"] = p_cur_hp + p_heal
                    player.sustenance_hp -= p_heal

        await server.send_stats_update(player)
        await server.send_pet_list(player)
        server.save_player_to_db(player)


GLOBAL_SUSTENANCE_MANAGER = SustenanceManager()
