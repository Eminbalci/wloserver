"""
Wonderland Online Rebirth & 6 Advanced Job Classes System
Ported from C# wlo.pserver.core/Game/PlayerRelated/RebornManager.cs
"""

import logging
from enum import IntEnum
from typing import Dict, Tuple

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class RebornJob(IntEnum):
    NONE = 0
    KILLER = 1      # Physical ATK & Critical Specialist
    WARRIOR = 2     # Physical DEF & Tank Specialist
    KNIGHT = 3      # SPD & Mounted Mobility Specialist
    WIT = 4         # Magic ATK Specialist
    PRIEST = 5      # Magic DEF & Healing Specialist
    SEER = 6        # Sealing & Status Control Specialist (Sage)


class RebornManager:
    """Manages player character Rebirth, job class specializations, and cape rewards."""

    @staticmethod
    def can_reborn(player) -> bool:
        if not player:
            return False
        return player.level >= 100 and not getattr(player, "reborn", False)

    _cached_jobs: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_reborn_cape_item(cls, job: RebornJob) -> int:
        if not cls._cached_jobs:
            cls.reload_from_db()
        j_data = cls._cached_jobs.get(int(job))
        return j_data.get("cape_item_id", 0) if j_data else 0

    @classmethod
    def get_job_stat_multipliers(cls, job: RebornJob) -> Dict[str, float]:
        if not cls._cached_jobs:
            cls.reload_from_db()
        j_data = cls._cached_jobs.get(int(job))
        if j_data:
            return {
                "atk": j_data.get("atk_mult", 1.0),
                "def": j_data.get("def_mult", 1.0),
                "matk": j_data.get("matk_mult", 1.0),
                "mdef": j_data.get("mdef_mult", 1.0),
                "spd": j_data.get("spd_mult", 1.0),
            }
        return {"atk": 1.0, "def": 1.0, "matk": 1.0, "mdef": 1.0, "spd": 1.0}

    @classmethod
    def reload_from_db(cls, dynamic_mgr=None):
        cls._cached_jobs.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            cls._cached_jobs = GLOBAL_DYNAMIC_DATA.get_reborn_jobs()
            logger.info(f"[RebornManager] Loaded {len(cls._cached_jobs)} dynamic reborn jobs from database.")
        except Exception as e:
            logger.warning(f"[RebornManager] Fallback reborn jobs: {e}")
            cls._cached_jobs = {
                1: {"job_name": "Killer", "cape_item_id": 23001, "atk_mult": 1.30, "spd_mult": 1.10},
                2: {"job_name": "Warrior", "cape_item_id": 23002, "atk_mult": 1.10, "def_mult": 1.30, "mdef_mult": 1.15},
                3: {"job_name": "Knight", "cape_item_id": 23003, "atk_mult": 1.15, "def_mult": 1.10, "spd_mult": 1.30},
                4: {"job_name": "Wit", "cape_item_id": 23004, "matk_mult": 1.30, "mdef_mult": 1.10, "spd_mult": 1.10},
                5: {"job_name": "Priest", "cape_item_id": 23005, "def_mult": 1.15, "matk_mult": 1.10, "mdef_mult": 1.30},
                6: {"job_name": "Seer", "cape_item_id": 23006, "def_mult": 1.10, "matk_mult": 1.20, "mdef_mult": 1.20, "spd_mult": 1.20},
            }

    async def perform_reborn(self, server, player, job: RebornJob) -> bool:
        if not player:
            return False

        if player.level < 100:
            await self.send_system_msg(player, "You must reach at least Level 100 to undergo Rebirth!")
            return False

        if getattr(player, "reborn", False):
            await self.send_system_msg(player, "You have already undergone Rebirth!")
            return False

        if job == RebornJob.NONE:
            await self.send_system_msg(player, "Please select a valid Rebirth job class!")
            return False

        # Execute Rebirth Transformation
        player.reborn = True
        player.job = int(job)
        player.level = 1
        player.exp = 0

        # Grant Rebirth Class Cape
        from server.gameserver import add_item_to_inventory
        cape_item_id = self.get_reborn_cape_item(job)
        if cape_item_id > 0:
            add_item_to_inventory(player, cape_item_id, 1)

        # Play Rebirth Grand Ascension Visual Animation (AC 5:5: 60050)
        ascend_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
        server.broadcast_to_map(player.map_id, ascend_pkt)

        # Broadcast Server Announcement
        announce_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Rebirth Announcement] Player {player.char_name} has undergone Rebirth and awakened as a glorious {job.name}!"
        )
        server.broadcast_to_map(player.map_id, announce_pkt)

        # Sync Stats & Inventory
        await player.send_packet(server.build_inventory_packet(player))
        await server.send_stats_update(player, levelup=True)
        server.save_player_to_db(player)

        await self.send_system_msg(player, f"Congratulations! You are now a Reborn {job.name} (Lv 1)!")
        logger.info(f"[RebornManager] Player {player.char_name} reborn as {job.name}.")
        return True

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_REBORN_MANAGER = RebornManager()
