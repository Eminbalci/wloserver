"""
Wonderland Online Vehicle, Mount & Sea Voyage System (AC 15:10 / AC 59)
Ported from C# wlo.pserver.core/Game/PlayerRelated/Vehicle.cs
"""

import random
import logging
from enum import IntEnum
from typing import Dict, Optional
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class VehicleType(IntEnum):
    NONE = 0
    LAND = 1
    WATER = 2
    AIR = 3


@dataclass
class VehicleItem:
    vehicle_id: int
    name: str
    type: VehicleType = VehicleType.LAND
    max_fuel: int = 1000
    current_fuel: int = 1000
    max_hp: int = 1000
    current_hp: int = 1000
    capacity: int = 1


class VehicleManager:
    """Manages player vehicles, sea voyage navigation, and mount broadcasting."""

    def __init__(self):
        self._templates: Dict[int, VehicleItem] = {}
        self._init_templates()

    def _init_templates(self):
        self._templates.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_v = GLOBAL_DYNAMIC_DATA.get_vehicles()
            for v_id, d in db_v.items():
                v_type = VehicleType.WATER if d.get("sea_only") else (VehicleType.AIR if d.get("air_only") else VehicleType.LAND)
                self._register(VehicleItem(v_id, d["name"], v_type))
            logger.info(f"[VehicleManager] Loaded {len(self._templates)} dynamic vehicles from database.")
        except Exception as e:
            logger.warning(f"[VehicleManager] Fallback vehicles: {e}")

        # Ensure base fallbacks if empty
        if not self._templates:
            self._register(VehicleItem(36001, "Raft", VehicleType.WATER, 0, 1))
            self._register(VehicleItem(36002, "Canoe", VehicleType.WATER, 0, 1))
            self._register(VehicleItem(36003, "Sailboat", VehicleType.WATER, 0, 4))
            self._register(VehicleItem(36004, "Steamboat", VehicleType.WATER, 2000, 4))
            self._register(VehicleItem(36005, "Submarine", VehicleType.WATER, 3000, 4))
            self._register(VehicleItem(36006, "Hot Air Balloon", VehicleType.AIR, 1500, 2))
            self._register(VehicleItem(36007, "Airship", VehicleType.AIR, 5000, 4))
            self._register(VehicleItem(36008, "UFO", VehicleType.AIR, 9999, 4))
            self._register(VehicleItem(36010, "Bicycle", VehicleType.LAND, 0, 1))
            self._register(VehicleItem(36011, "Motorcycle", VehicleType.LAND, 1000, 2))
            self._register(VehicleItem(36012, "Beetle Car", VehicleType.LAND, 2000, 4))

    def reload_from_db(self, dynamic_mgr=None):
        self._init_templates()

    def _register(self, v: VehicleItem):
        self._templates[v.vehicle_id] = v

    def get_template(self, vehicle_id: int) -> Optional[VehicleItem]:
        return self._templates.get(vehicle_id)

    async def mount_vehicle(self, server, player, vehicle_id: int) -> bool:
        if not player or vehicle_id == 0:
            return False

        template = self.get_template(vehicle_id)
        if not template:
            return False

        # Set player vehicle
        player.active_vehicle_id = vehicle_id

        # Broadcast mount appearance to map (AC 15 Sub 10)
        mount_pkt = PacketWriter().write_8(15).write_8(10).write_32(player.char_id).write_16(vehicle_id)
        server.broadcast_to_map(player.map_id, mount_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Boarded vehicle: {template.name} ({template.type.name})!"
        )
        await player.send_packet(sys_msg)
        logger.info(f"[VehicleManager] Player {player.char_name} mounted {template.name} (#{vehicle_id}).")
        return True

    async def dismount_vehicle(self, server, player):
        if not player or not getattr(player, "active_vehicle_id", 0):
            return

        player.active_vehicle_id = 0

        # Broadcast dismount to map (AC 15 Sub 10 with 0)
        dismount_pkt = PacketWriter().write_8(15).write_8(10).write_32(player.char_id).write_16(0)
        server.broadcast_to_map(player.map_id, dismount_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Dismounted from vehicle.")
        await player.send_packet(sys_msg)
        logger.info(f"[VehicleManager] Player {player.char_name} dismounted vehicle.")

    def check_sea_encounter(self, player) -> bool:
        """Determines if navigating on ocean/sea map triggers a random sea battle."""
        if not player:
            return False
        # Ocean map IDs in WLO (e.g. 10000 World Map, 12000 Ocean, etc.)
        if getattr(player, "active_vehicle_id", 0) in (36001, 36002, 36003, 36004, 36005):
            # 8% encounter probability per ocean movement chunk
            return random.random() < 0.08
        return False


GLOBAL_VEHICLE_MANAGER = VehicleManager()
