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

        # Synchronize authentic AC 23 Sub 208 sustenance buffer to client HUD
        sus_hp = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(8).write_32(player.sustenance_hp)
        sus_sp = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(9).write_32(player.sustenance_sp)
        await player.send_packet(sus_hp)
        await player.send_packet(sus_sp)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Auto-Recovery] Consumed Rice Ball! Added +{pool_amount} HP/SP to Auto-Heal Pool (Total: {player.sustenance_hp} HP / {player.sustenance_sp} SP)!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[SustenanceManager] {player.char_name} charged auto-heal pool +{pool_amount}.")
        return True

    @classmethod
    async def sync_sustenance_counters(cls, player):
        """Sends authentic AC 23 Sub 208 HUD sustenance buffers to client."""
        if not player:
            return
        cur_hp = getattr(player, "sustenance_hp", 0)
        cur_sp = getattr(player, "sustenance_sp", 0)
        if cur_hp > 0:
            await player.send_packet(PacketWriter().write_8(23).write_8(208).write_8(1).write_8(8).write_32(cur_hp))
        if cur_sp > 0:
            await player.send_packet(PacketWriter().write_8(23).write_8(208).write_8(1).write_8(9).write_32(cur_sp))

    @classmethod
    async def handle_auto_heal_button(
        cls,
        server,
        player,
        stat_type: int,
        target_type: int,
        slot: int
    ):
        """
        Processes client click on HP/MP refill button (AC 23 Sub 15).
        stat_type: 8 = HP, 9 = SP
        target_type: 1
        slot: 0 = Character, >0 = Companion Pet Slot
        """
        if not player:
            return

        if slot == 0:
            # Character auto-fill
            if stat_type == 8:  # HP
                needed = max(0, player.max_hp - player.hp)
                pool = getattr(player, "sustenance_hp", 0)
                heal = min(needed, pool)
                if heal > 0:
                    player.hp += heal
                    player.sustenance_hp = pool - heal
                # Send AC 8 Sub 1 HP stat update: [8, 1, 0x19, 0x01, hp (4B), 6 zero bytes]
                hp_pkt = PacketWriter().write_8(8).write_8(1).write_16(0x0119).write_32(player.hp).write_bytes(bytes(6))
                await player.send_packet(hp_pkt)
                # Send AC 23 Sub 208 Sustenance buffer remaining
                sus_pkt = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(8).write_32(player.sustenance_hp)
                await player.send_packet(sus_pkt)
                logger.info(f"[Sustenance] {player.char_name} used HP quick-fill (+{heal} HP). New HP: {player.hp}/{player.max_hp}, Remaining Pool: {player.sustenance_hp}")

            elif stat_type == 9:  # SP
                needed = max(0, player.max_sp - player.sp)
                pool = getattr(player, "sustenance_sp", 0)
                heal = min(needed, pool)
                if heal > 0:
                    player.sp += heal
                    player.sustenance_sp = pool - heal
                # Send AC 8 Sub 1 SP stat update: [8, 1, 0x1a, 0x01, sp (4B), 6 zero bytes]
                sp_pkt = PacketWriter().write_8(8).write_8(1).write_16(0x011a).write_32(player.sp).write_bytes(bytes(6))
                await player.send_packet(sp_pkt)
                # Send AC 23 Sub 208 Sustenance buffer remaining
                sus_pkt = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(9).write_32(player.sustenance_sp)
                await player.send_packet(sus_pkt)
                logger.info(f"[Sustenance] {player.char_name} used SP quick-fill (+{heal} SP). New SP: {player.sp}/{player.max_sp}, Remaining Pool: {player.sustenance_sp}")

        else:
            # Companion pet auto-fill (slot is 1-indexed pet slot)
            target_pet = None
            pets = getattr(player, "pets", [])
            if 1 <= slot <= len(pets):
                target_pet = pets[slot - 1]

            if target_pet:
                pet_name = target_pet.get("name", f"Pet#{slot}")
                if stat_type == 8:  # Pet HP
                    p_max_hp = target_pet.get("max_hp", 500)
                    p_cur_hp = target_pet.get("hp", p_max_hp)
                    needed = max(0, p_max_hp - p_cur_hp)
                    pool = target_pet.get("sustenance_hp", getattr(player, "sustenance_hp", 0))
                    heal = min(needed, pool)
                    if heal > 0:
                        target_pet["hp"] = p_cur_hp + heal
                        if "sustenance_hp" in target_pet:
                            target_pet["sustenance_hp"] -= heal
                        else:
                            player.sustenance_hp = pool - heal
                    # Send AC 8 Sub 2 Pet HP update: [8, 2, 4, slot, 0, 0x19, 0x01, hp (4B), 6 zero bytes]
                    pet_hp_pkt = PacketWriter().write_8(8).write_8(2).write_8(4).write_8(slot).write_8(0).write_16(0x0119).write_32(target_pet["hp"]).write_bytes(bytes(6))
                    await player.send_packet(pet_hp_pkt)
                    # Send AC 23 Sub 208
                    rem = target_pet.get("sustenance_hp", getattr(player, "sustenance_hp", 0))
                    sus_pkt = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(8).write_32(rem)
                    await player.send_packet(sus_pkt)
                    logger.info(f"[Sustenance] {player.char_name} quick-filled {pet_name} HP (+{heal} HP). New HP: {target_pet['hp']}/{p_max_hp}, Remaining Pool: {rem}")

                elif stat_type == 9:  # Pet SP
                    p_max_sp = target_pet.get("max_sp", 500)
                    p_cur_sp = target_pet.get("sp", p_max_sp)
                    needed = max(0, p_max_sp - p_cur_sp)
                    pool = target_pet.get("sustenance_sp", getattr(player, "sustenance_sp", 0))
                    heal = min(needed, pool)
                    if heal > 0:
                        target_pet["sp"] = p_cur_sp + heal
                        if "sustenance_sp" in target_pet:
                            target_pet["sustenance_sp"] -= heal
                        else:
                            player.sustenance_sp = pool - heal
                    # Send AC 8 Sub 2 Pet SP update: [8, 2, 4, slot, 0, 0x1a, 0x01, sp (4B), 6 zero bytes]
                    pet_sp_pkt = PacketWriter().write_8(8).write_8(2).write_8(4).write_8(slot).write_8(0).write_16(0x011a).write_32(target_pet["sp"]).write_bytes(bytes(6))
                    await player.send_packet(pet_sp_pkt)
                    # Send AC 23 Sub 208
                    rem = target_pet.get("sustenance_sp", getattr(player, "sustenance_sp", 0))
                    sus_pkt = PacketWriter().write_8(23).write_8(208).write_8(1).write_8(9).write_32(rem)
                    await player.send_packet(sus_pkt)
                    logger.info(f"[Sustenance] {player.char_name} quick-filled {pet_name} SP (+{heal} SP). New SP: {target_pet['sp']}/{p_max_sp}, Remaining Pool: {rem}")

        server.save_player_to_db(player)

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
        await cls.sync_sustenance_counters(player)
        server.save_player_to_db(player)


GLOBAL_SUSTENANCE_MANAGER = SustenanceManager()
