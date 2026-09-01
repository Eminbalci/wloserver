"""
Wonderland Online Pet Riding & Mount Speed Engine (AC 82 / AC 85)
Ported from C# Pet ride handlers & AdjustRidePetPos
"""

import logging
from typing import Any, Dict, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class PetRideManager:
    """Manages mounting companion pets with saddles and applying movement speed boosts."""

    _cached_saddles: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_saddle_multiplier(cls, item_id: int = 38020, player=None) -> float:
        if not cls._cached_saddles:
            cls.reload_from_db()
        s_data = cls._cached_saddles.get(item_id)
        base_mult = s_data.get("speed_mult", 1.40) if s_data else 1.40
        # Knight reborn passive: +20% extra mount mobility (FUN_001a3f68)
        if player and getattr(player, "reborn", False) and getattr(player, "job", 0) == 3:
            base_mult += 0.20
        return base_mult

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_saddles.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            cls._cached_saddles = GLOBAL_DYNAMIC_DATA.get_saddles()
            logger.info(f"[PetRideManager] Loaded {len(cls._cached_saddles)} dynamic saddles from database.")
        except Exception as e:
            logger.warning(f"[PetRideManager] Fallback saddles: {e}")
            cls._cached_saddles = {
                38020: {"name": "Pet Saddle", "speed_mult": 1.40},
                38021: {"name": "Grand Golden Saddle", "speed_mult": 1.60},
            }

    @classmethod
    async def mount_companion_pet(
        cls,
        server,
        player,
        pet_slot: int,
        saddle_id: int = 38020
    ) -> bool:
        if not player or not getattr(player, "pets", None):
            return False

        target_pet = next((p for p in player.pets if p.get("slot") == pet_slot), None)
        if not target_pet:
            return False

        # Set player mounted pet
        player.mounted_pet_slot = pet_slot
        player.movement_speed_mult = cls.get_saddle_multiplier(saddle_id)

        pet_id = target_pet.get("pet_id", 0)
        pet_name = target_pet.get("name", "Companion")

        # Broadcast mount appearance to map (AC 82 Sub 1)
        pkt = PacketWriter().write_8(82).write_8(1).write_32(player.char_id).write_16(pet_id)
        server.broadcast_to_map(player.map_id, pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Mounted {pet_name}! Movement speed increased by +40%!"
        )
        await player.send_packet(sys_msg)
        logger.info(f"[PetRideManager] Player {player.char_name} mounted pet {pet_name} (#{pet_id}).")
        return True

    @classmethod
    async def dismount_companion_pet(
        cls,
        server,
        player
    ):
        if not player or not getattr(player, "mounted_pet_slot", None):
            return

        player.mounted_pet_slot = 0
        player.movement_speed_mult = 1.0

        # Broadcast dismount to map (AC 82 Sub 2)
        pkt = PacketWriter().write_8(82).write_8(2).write_32(player.char_id).write_16(0)
        server.broadcast_to_map(player.map_id, pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Dismounted from companion pet.")
        await player.send_packet(sys_msg)
        logger.info(f"[PetRideManager] Player {player.char_name} dismounted pet.")


GLOBAL_PET_RIDE_MANAGER = PetRideManager()
