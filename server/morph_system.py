"""
Wonderland Online Transformation & Monster Disguise Morph System (AC 21:10)
Ported from client disguise & morph handlers
"""

import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class MorphData:
    morph_npc_id: int
    name: str
    duration: float = 900.0  # 15 minutes default
    stat_bonuses: Dict[str, int] = None


class MorphManager:
    """Manages player monster transformations, duration timers, and appearance overrides."""

    MORPH_ITEMS: Dict[int, MorphData] = {}

    def __init__(self):
        self._active_morphs: Dict[int, Tuple[int, float]] = {}  # CharID -> (morph_npc_id, expires_at)
        self._load_morph_items()

    def _load_morph_items(self):
        self.MORPH_ITEMS.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_m = GLOBAL_DYNAMIC_DATA.get_morph_items()
            for it_id, d in db_m.items():
                self.MORPH_ITEMS[it_id] = MorphData(
                    morph_npc_id=d["morph_npc_id"],
                    name=d["name"],
                    duration=float(d.get("duration_sec", 900.0)),
                    stat_bonuses=d.get("stat_bonuses", {})
                )
            logger.info(f"[MorphManager] Loaded {len(self.MORPH_ITEMS)} dynamic morph items from database.")
        except Exception as e:
            logger.warning(f"[MorphManager] Fallback morph items: {e}")
            self.MORPH_ITEMS = {
                41001: MorphData(1001, "Green Jelly Disguise", 900.0, {"spd": 10, "def": 15}),
                41002: MorphData(1002, "Dire Wolf Disguise", 900.0, {"atk": 25, "spd": 15}),
                41003: MorphData(1003, "Haunted Ghost Disguise", 900.0, {"matk": 30, "mdef": 20}),
                41004: MorphData(1004, "Ocean Siren Disguise", 900.0, {"matk": 20, "max_sp": 100}),
            }

    def reload_from_db(self, dynamic_mgr=None):
        self._load_morph_items()

    def is_morphed(self, char_id: int) -> bool:
        if char_id not in self._active_morphs:
            return False
        npc_id, expires = self._active_morphs[char_id]
        if time.time() > expires:
            self._active_morphs.pop(char_id, None)
            return False
        return True

    def get_morph_npc_id(self, char_id: int) -> int:
        if self.is_morphed(char_id):
            return self._active_morphs[char_id][0]
        return 0

    async def transform_player(
        self,
        server,
        player,
        item_id: int
    ) -> bool:
        if not player or item_id not in self.MORPH_ITEMS:
            return False

        morph = self.MORPH_ITEMS[item_id]
        expires_at = time.time() + morph.duration
        self._active_morphs[player.char_id] = (morph.morph_npc_id, expires_at)
        player.morph_npc_id = morph.morph_npc_id

        # Broadcast morph appearance to map (AC 21 Sub 10)
        morph_pkt = PacketWriter().write_8(21).write_8(10).write_32(player.char_id).write_16(morph.morph_npc_id)
        server.broadcast_to_map(player.map_id, morph_pkt)

        # Send celebration spark effect (AC 5:5: 60050)
        fx_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
        server.broadcast_to_map(player.map_id, fx_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Transformation] Disguised as {morph.name}! (Duration: {int(morph.duration//60)} mins)"
        )
        await player.send_packet(sys_msg)
        logger.info(f"[MorphManager] Player {player.char_name} transformed into {morph.name} (#{morph.morph_npc_id}).")
        return True

    async def untransform_player(self, server, player):
        if not player or player.char_id not in self._active_morphs:
            return

        self._active_morphs.pop(player.char_id, None)
        player.morph_npc_id = 0

        # Broadcast revert appearance (AC 21 Sub 10 with 0)
        revert_pkt = PacketWriter().write_8(21).write_8(10).write_32(player.char_id).write_16(0)
        server.broadcast_to_map(player.map_id, revert_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Transformation expired. Reverted to normal form.")
        await player.send_packet(sys_msg)
        logger.info(f"[MorphManager] Player {player.char_name} reverted from morph.")


GLOBAL_MORPH_MANAGER = MorphManager()
