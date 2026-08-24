"""
Wonderland Online Equipment Forging & Spar Gem Embedding System
Ported from C# wlo.pserver.core/Game/Crafting/ForgingManager.cs
"""

import logging
from typing import Dict, Optional, Tuple

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class ForgingManager:
    """Manages forging spar crystals and diamonds into weapon and armor sockets."""

    _cached_materials: Dict[int, Tuple[str, Dict[str, int]]] = {}

    @classmethod
    def get_material_info(cls, material_id: int) -> Optional[Tuple[str, Dict[str, int]]]:
        if not cls._cached_materials:
            cls.reload_from_db()
        return cls._cached_materials.get(material_id)

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_materials.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            mats = GLOBAL_DYNAMIC_DATA.get_forging_materials()
            for m_id, data in mats.items():
                cls._cached_materials[m_id] = (data["name"], data["stat_boosts"])
            logger.info(f"[ForgingManager] Loaded {len(cls._cached_materials)} forging materials from database.")
        except Exception as e:
            logger.warning(f"[ForgingManager] Fallback forging materials: {e}")
            cls._cached_materials = {
                47001: ("+24 ATK Spar", {"atk": 24}),
                47002: ("+24 DEF Spar", {"def": 24}),
                47003: ("+24 MATK Spar", {"matk": 24}),
                47004: ("+24 MDEF Spar", {"mdef": 24}),
                47005: ("+24 SPD Spar", {"spd": 24}),
                47010: ("Brilliant Diamond (+42 Stats)", {"atk": 42, "def": 42, "matk": 42, "mdef": 42, "spd": 42}),
            }

    @classmethod
    async def forge_gem(
        cls,
        server,
        player,
        equip_slot: int,
        gem_slot: int
    ) -> bool:
        if not player or not getattr(player, "inventory", None):
            return False

        from server.gameserver import remove_item_at_slot

        # Locate equip and gem
        equip_item = None
        gem_item = None

        for it in player.inventory:
            if it.get("slot") == equip_slot:
                equip_item = it
            elif it.get("slot") == gem_slot:
                gem_item = it

        if not equip_item or not gem_item:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "Please select both an equipment and a Spar Gem from your inventory!"
            )
            await player.send_packet(sys_msg)
            return False

        gem_id = gem_item.get("item_id", 0)
        spar_info = cls.get_material_info(gem_id)
        if not spar_info:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "The selected material is not a valid Forging Spar or Diamond!"
            )
            await player.send_packet(sys_msg)
            return False

        spar_name, stats_boost = spar_info

        # Remove 1 gem
        remove_item_at_slot(player, gem_slot, 1)

        # Apply stat boosts to equipment item
        for stat, val in stats_boost.items():
            key = f"extra_{stat}"
            equip_item[key] = equip_item.get(key, 0) + val

        # Mark forged gem list
        gems_list = equip_item.setdefault("forged_gems", [])
        gems_list.append(gem_id)

        # Broadcast anvil spark effect (AC 5:5: 60025)
        spark_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60025)
        server.broadcast_to_map(player.map_id, spark_pkt)

        # Send inventory update & success message
        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Forging Success!] Embedded {spar_name} into Item #{equip_item.get('item_id')}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[ForgingManager] Player {player.char_name} forged {spar_name} onto item #{equip_item.get('item_id')}.")
        return True


GLOBAL_FORGING_MANAGER = ForgingManager()
