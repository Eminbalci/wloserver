"""
Wonderland Online Player Titles & Achievement Engine (AC 183 / AC 186)
Ported from C# PlayerTitleData & AC183/AC186 handlers
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class TitleData:
    title_id: int
    title_name: str
    description: str
    stat_bonuses: Dict[str, int]


class TitleManager:
    """Manages player title unlocks, active title equip, and passive stat bonuses."""

    TITLES: Dict[int, TitleData] = {}

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._load_titles()
        self._ensure_tables()

    def _load_titles(self):
        self.TITLES.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_titles = GLOBAL_DYNAMIC_DATA.get_titles()
            for t_id, d in db_titles.items():
                self.TITLES[t_id] = TitleData(
                    title_id=d["title_id"],
                    title_name=d["title_name"],
                    description=d.get("description", ""),
                    stat_bonuses=d.get("stat_bonuses", {})
                )
            logger.info(f"[TitleManager] Loaded {len(self.TITLES)} dynamic titles from database.")
        except Exception as e:
            logger.warning(f"[TitleManager] Fallback titles: {e}")
            self.TITLES = {
                1: TitleData(1, "Novice Adventurer", "Completed Island Tutorial", {"max_hp": 100}),
                2: TitleData(2, "Island Explorer", "Traveled 10,000 steps", {"spd": 10}),
                3: TitleData(3, "Master Alchemist", "Synthesized 50 items", {"matk": 20}),
                4: TitleData(4, "Palace Conqueror", "Cleared 12 Zodiac Trials", {"atk": 30, "def": 30}),
                5: TitleData(5, "Reborn Legend", "Awakened as Reborn Champion", {"atk": 50, "def": 50, "matk": 50, "mdef": 50, "spd": 30}),
            }

    def reload_from_db(self, dynamic_mgr=None):
        self._load_titles()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_titles (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    title_id INTEGER NOT NULL,
                    unlocked_at REAL,
                    UNIQUE(char_id, title_id)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[TitleManager] DB Init Error: {e}")

    def get_unlocked_titles(self, char_id: int) -> List[int]:
        unlocked = []
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT title_id FROM char_titles WHERE char_id = ?", (char_id,)).fetchall()
            unlocked = [r[0] for r in rows]
            conn.close()
        except Exception as e:
            logger.error(f"[TitleManager] Error fetching titles: {e}")
        return unlocked

    async def unlock_title(self, server, player, title_id: int) -> bool:
        if not player or title_id not in self.TITLES:
            return False

        tdata = self.TITLES[title_id]
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR IGNORE INTO char_titles (char_id, title_id, unlocked_at)
                VALUES (?, ?, ?)
            """, (player.char_id, title_id, 0))
            conn.commit()
            conn.close()

            # Send celebration animation (AC 5:5: 60050)
            fx = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
            server.broadcast_to_map(player.map_id, fx)

            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Achievement Unlocked!] You earned the Title: <{tdata.title_name}>!"
            )
            await player.send_packet(sys_msg)
            await self.send_title_list(player)
            return True
        except Exception as e:
            logger.error(f"[TitleManager] Error unlocking title: {e}")
            return False

    async def equip_title(self, server, player, title_id: int) -> bool:
        if not player:
            return False

        unlocked = self.get_unlocked_titles(player.char_id)
        if title_id != 0 and title_id not in unlocked:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "You have not unlocked this title yet!"
            )
            await player.send_packet(sys_msg)
            return False

        player.active_title_id = title_id

        # Broadcast title change to map (AC 186 Sub 1)
        pkt = PacketWriter().write_8(186).write_8(1).write_32(player.char_id).write_16(title_id)
        server.broadcast_to_map(player.map_id, pkt)

        tname = self.TITLES[title_id].title_name if title_id in self.TITLES else "None"
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Equipped Title: <{tname}>!"
        )
        await player.send_packet(sys_msg)
        await server.send_stats_update(player)
        server.save_player_to_db(player)
        return True

    async def send_title_list(self, session):
        if not session:
            return
        unlocked = self.get_unlocked_titles(session.char_id)
        pkt = PacketWriter().write_8(183).write_8(1).write_16(len(unlocked))
        for tid in unlocked:
            pkt.write_16(tid)
        await session.send_packet(pkt)


GLOBAL_TITLE_MANAGER = TitleManager()
