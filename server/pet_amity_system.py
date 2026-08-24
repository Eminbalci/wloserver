"""
Wonderland Online Pet Amity, Death Penalty & Pet Rebirth System
Ported from C# wlo.pserver.core/Game/PetRelated/PetAmityManager.cs
"""

import logging
from typing import Dict, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class PetAmityManager:
    """Manages Pet loyalty (Amity), battle defeat penalties, runaway mechanics, and Pet Rebirth."""

    @staticmethod
    async def on_pet_death(server, player, pet_slot: int) -> bool:
        """Called when a companion pet is knocked out in combat."""
        if not player or not getattr(player, "pets", []):
            return False

        target_pet = None
        for p in player.pets:
            if p.get("slot") == pet_slot:
                target_pet = p
                break

        if not target_pet:
            return False

        # Deduct 2 Amity on battle death
        cur_amity = target_pet.get("amity", 60)
        new_amity = max(0, cur_amity - 2)
        target_pet["amity"] = new_amity

        pet_name = target_pet.get("name", "Companion")

        # Runaway mechanic: If Amity <= 20, pet runs away from owner
        if new_amity <= 20:
            player.pets.remove(target_pet)
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Pet Runaway] Your companion {pet_name}'s loyalty fell to {new_amity}! {pet_name} has abandoned you and run away!"
            )
            await player.send_packet(sys_msg)
            logger.warning(f"[PetAmity] Pet {pet_name} ran away from {player.char_name} (Amity: {new_amity}).")
        else:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Your companion {pet_name} was defeated in combat! Amity decreased to {new_amity}."
            )
            await player.send_packet(sys_msg)
            logger.info(f"[PetAmity] Pet {pet_name} of {player.char_name} lost 2 amity (now {new_amity}).")

        await server.send_pet_list(player)
        server.save_player_to_db(player)
        return True

    _cached_foods: Dict[int, int] = {}

    @classmethod
    def get_food_amity_gain(cls, food_item_id: int) -> int:
        if not cls._cached_foods:
            cls.reload_from_db()
        return cls._cached_foods.get(food_item_id, 1)

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_foods.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_foods = GLOBAL_DYNAMIC_DATA.get_pet_foods()
            for it_id, d in db_foods.items():
                cls._cached_foods[it_id] = d.get("amity_gain", 2)
            logger.info(f"[PetAmityManager] Loaded {len(cls._cached_foods)} dynamic pet foods from database.")
        except Exception as e:
            logger.warning(f"[PetAmityManager] Fallback pet foods: {e}")
            cls._cached_foods = {
                30025: 3,  # Rice Ball
                28020: 2,  # Roast Meat
                28021: 2,  # Roast Pork
                28014: 1,  # Apple / Fruit
                28006: 1,  # Red Apple
            }

    @classmethod
    async def feed_pet(cls, server, player, pet_slot: int, food_item_id: int) -> bool:
        """Feeds food item to pet to restore Amity."""
        if not player or not getattr(player, "pets", []):
            return False

        target_pet = None
        for p in player.pets:
            if p.get("slot") == pet_slot:
                target_pet = p
                break

        if not target_pet:
            return False

        gain = cls.get_food_amity_gain(food_item_id)

        # Deduct food item from inventory
        from server.gameserver import remove_item_at_slot
        removed = False
        for it in list(player.inventory):
            if it.get("item_id") == food_item_id:
                slot = it.get("slot")
                if slot is not None:
                    remove_item_at_slot(player, slot, 1)
                else:
                    it["amount"] = it.get("amount", 1) - 1
                    if it["amount"] <= 0:
                        player.inventory.remove(it)
                removed = True
                break

        if not removed:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("You do not have that pet food in your inventory!")
            await player.send_packet(sys_msg)
            return False

        # Increase Amity
        old_amity = target_pet.get("amity", 60)
        new_amity = min(100, old_amity + gain)
        target_pet["amity"] = new_amity

        # Play pet love / heart animation (AC 5:5: 60012)
        heart_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60012)
        server.broadcast_to_map(player.map_id, heart_pkt)

        await player.send_packet(server.build_inventory_packet(player))
        await server.send_pet_list(player)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Fed {target_pet.get('name', 'Companion')}! Amity increased by +{gain} (Total: {new_amity}/100)!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[PetAmity] {player.char_name} fed pet {target_pet.get('name')} (+{gain} amity).")
        return True

    @staticmethod
    async def perform_pet_reborn(server, player, pet_slot: int) -> bool:
        """Transforms a companion pet into their Reborn state."""
        if not player or not getattr(player, "pets", []):
            return False

        target_pet = None
        for p in player.pets:
            if p.get("slot") == pet_slot:
                target_pet = p
                break

        if not target_pet or target_pet.get("level", 1) < 100 or target_pet.get("reborn", 0):
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Pet must be at least Level 100 and not already reborn!")
            await player.send_packet(sys_msg)
            return False

        target_pet["reborn"] = 1
        target_pet["level"] = 1
        target_pet["exp"] = 0
        target_pet["str"] = int(target_pet.get("str", 10) * 1.3)
        target_pet["con"] = int(target_pet.get("con", 10) * 1.3)
        target_pet["int"] = int(target_pet.get("int", 10) * 1.3)
        target_pet["wis"] = int(target_pet.get("wis", 10) * 1.3)
        target_pet["agi"] = int(target_pet.get("agi", 10) * 1.3)

        # Play ascension animation
        ascend_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
        server.broadcast_to_map(player.map_id, ascend_pkt)

        await server.send_pet_list(player)
        server.save_player_to_db(player)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Pet Rebirth] Companion {target_pet.get('name')} has achieved Rebirth and attained enhanced potential!"
        )
        await player.send_packet(sys_msg)
        logger.info(f"[PetAmity] Pet {target_pet.get('name')} reborn for {player.char_name}.")
        return True


GLOBAL_PET_AMITY_MANAGER = PetAmityManager()
GLOBAL_PET_AMITY = GLOBAL_PET_AMITY_MANAGER
