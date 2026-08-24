"""
Wonderland Online Death Penalty, Ghost State & Revive Altar System
Ported from C# PvEBattleManager player knockout and revival handlers
"""

import logging
from typing import Dict, Tuple

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class DeathManager:
    """Manages player battle defeat penalties, EXP loss, and hospital/altar respawns."""

    _cached_altars: Dict[int, Tuple[int, int, int]] = {}
    DEFAULT_REVIVE_POINT: Tuple[int, int, int] = (10010, 450, 380)

    @classmethod
    def get_revive_location(cls, map_id: int) -> Tuple[int, int, int]:
        if not cls._cached_altars:
            cls.reload_from_db()
        return cls._cached_altars.get(map_id, cls.DEFAULT_REVIVE_POINT)

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_altars.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            cls._cached_altars = GLOBAL_DYNAMIC_DATA.get_revive_altars()
            logger.info(f"[DeathManager] Loaded {len(cls._cached_altars)} dynamic revive altars from database.")
        except Exception as e:
            logger.warning(f"[DeathManager] Fallback revive altars: {e}")
            cls._cached_altars = {
                10001: (10010, 450, 380),
                10036: (10010, 450, 380),
                10010: (10010, 450, 380),
                12000: (10010, 450, 380),
                15000: (15000, 300, 300),
                16000: (10010, 450, 380),
            }

    @classmethod
    async def process_player_defeat(cls, server, player):
        """Called when a player is defeated in non-PvP combat."""
        if not player:
            return

        # Deduct 2% current EXP as death penalty
        cur_exp = getattr(player, "exp", 0)
        exp_loss = int(cur_exp * 0.02)
        player.exp = max(0, cur_exp - exp_loss)

        # Restore minimal HP and SP
        player.hp = 1
        player.sp = 1

        # Locate revive altar
        revive_map, rx, ry = cls.get_revive_location(player.map_id)

        # Play ghost / defeat visual effect (AC 5:5: 60010)
        ghost_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60010)
        server.broadcast_to_map(player.map_id, ghost_pkt)

        # Teleport to Revive Altar
        await server.warp_player(player, revive_map, rx, ry)
        await server.send_stats_update(player)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Defeat Penalty] You were defeated! Lost {exp_loss} EXP and respawned at the Sacred Altar."
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[DeathManager] Player {player.char_name} defeated (Lost {exp_loss} exp, respawned at {revive_map}).")


GLOBAL_DEATH_MANAGER = DeathManager()
