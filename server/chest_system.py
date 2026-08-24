"""
Wonderland Online World Treasure Chests & Dynamic Loot System
Ported from C# wlo.pserver.core/Game/Maps/ChestDropManager.cs
"""

import time
import random
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class ChestLootEntry:
    item_id: int
    item_name: str
    count: int = 1
    weight: int = 100


class ChestSystem:
    """Manages world treasure chest looting, key verification, and SQLite persistence."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self.map_loot_tables: Dict[int, List[ChestLootEntry]] = {}
        self._init_loot_tables()
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS charchests (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    map_id INTEGER NOT NULL,
                    chest_id INTEGER NOT NULL,
                    opened_at REAL,
                    UNIQUE(char_id, map_id, chest_id)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ChestSystem] DB Init Error: {e}")

    def _init_loot_tables(self):
        self.map_loot_tables.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT map_id, item_id, item_name, count, weight FROM game_chest_pools").fetchall()
            conn.close()
            for r in rows:
                m_id, it_id, it_name, cnt, wt = r
                if m_id not in self.map_loot_tables:
                    self.map_loot_tables[m_id] = []
                self.map_loot_tables[m_id].append(ChestLootEntry(it_id, it_name, cnt, wt))
            logger.info(f"[ChestSystem] Loaded dynamic chests for {len(self.map_loot_tables)} maps from database.")
        except Exception as e:
            logger.warning(f"[ChestSystem] Fallback chest tables: {e}")

        # Ensure default fallbacks if empty
        if not self.map_loot_tables:
            self.map_loot_tables[10036] = [
                ChestLootEntry(41066, "Coconut", 1, 40),
                ChestLootEntry(28014, "Fresh Fruit", 1, 30),
                ChestLootEntry(28001, "Sea Water", 1, 15),
                ChestLootEntry(27001, "Ordinary Wood", 1, 15)
            ]
            self.map_loot_tables[10001] = [
                ChestLootEntry(28006, "Red Apple", 1, 35),
                ChestLootEntry(28012, "Mushroom", 1, 25),
                ChestLootEntry(30001, "Herb Potion", 1, 20),
                ChestLootEntry(27002, "Pine Wood", 1, 20)
            ]
            self.map_loot_tables[10010] = [
                ChestLootEntry(30259, "Black Medicine", 1, 40),
                ChestLootEntry(28003, "Cooking Salt", 1, 20),
                ChestLootEntry(28015, "White Rice", 1, 20),
                ChestLootEntry(28007, "Fresh Milk", 1, 20)
            ]

    def reload_from_db(self, dynamic_mgr=None):
        self._init_loot_tables()

    def is_chest_opened(self, char_id: int, map_id: int, chest_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT 1 FROM charchests WHERE char_id = ? AND map_id = ? AND chest_id = ?",
                (char_id, map_id, chest_id)
            ).fetchone()
            conn.close()
            return row is not None
        except Exception:
            return False

    async def open_chest(
        self,
        server,
        player,
        map_id: int,
        chest_id: int,
        required_key: int = 0
    ) -> bool:
        if not player:
            return False

        if self.is_chest_opened(player.char_id, map_id, chest_id):
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("This chest is already empty!")
            await player.send_packet(sys_msg)
            return False

        # Key verification if required
        from server.gameserver import remove_item_at_slot, add_item_to_inventory
        if required_key > 0:
            has_key = any(it.get("item_id") == required_key for it in player.inventory)
            if not has_key:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"This treasure chest is locked! Requires Key #{required_key}."
                )
                await player.send_packet(sys_msg)
                return False

            # Consume 1 key
            for it in list(player.inventory):
                if it.get("item_id") == required_key:
                    slot = it.get("slot")
                    if slot is not None:
                        remove_item_at_slot(player, slot, 1)
                    break

        # Roll loot
        pool = self.map_loot_tables.get(map_id, [
            ChestLootEntry(28014, "Fresh Fruit", 1, 50),
            ChestLootEntry(27001, "Ordinary Wood", 1, 50)
        ])

        total_weight = sum(e.weight for e in pool)
        roll = random.randint(1, total_weight)
        cur = 0
        selected = pool[-1]
        for e in pool:
            cur += e.weight
            if roll <= cur:
                selected = e
                break

        # Award item
        add_item_to_inventory(player, selected.item_id, selected.count)

        # Record in DB
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO charchests (char_id, map_id, chest_id, opened_at)
                VALUES (?, ?, ?, ?)
            """, (player.char_id, map_id, chest_id, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ChestSystem] DB Error recording chest: {e}")

        # Send opened chest animation (AC 22:10 state 0xFF)
        hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(chest_id).write_8(0xFF).write_8(0xFF)
        await player.send_packet(hide_pkt)

        # Notify
        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Treasure Chest] You found {selected.count}x {selected.item_name}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[ChestSystem] Player {player.char_name} opened chest #{chest_id} on map {map_id} -> {selected.item_name}.")
        return True

    async def sync_opened_chests_on_map(self, player, map_id: int):
        """Sends AC 22:10 to keep already-looted chests open for the player on map entry."""
        if not player:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT chest_id FROM charchests WHERE char_id = ? AND map_id = ?",
                (player.char_id, map_id)
            ).fetchall()
            conn.close()

            for r in rows:
                chest_id = r[0]
                hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(chest_id).write_8(0xFF).write_8(0xFF)
                await player.send_packet(hide_pkt)
        except Exception as e:
            logger.error(f"[ChestSystem] Error syncing opened chests: {e}")


GLOBAL_CHEST_SYSTEM = ChestSystem()
