"""
Wonderland Online World Treasure Chests & Dynamic Loot System
Ported 1:1 from C# wlo.pserver.core/Game/Maps/ChestDropManager.cs and QuestNpc.cs
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
    """Manages world treasure chest looting, category matching, key verification, and SQLite persistence."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self.default_respawn_seconds: int = 60
        self.map_loot_tables: Dict[int, List[ChestLootEntry]] = {}
        self.category_loot_tables: Dict[str, List[ChestLootEntry]] = {}
        self._ensure_tables()
        self._init_loot_tables()

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_chest_pools (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    map_id INTEGER NOT NULL,
                    chest_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    item_name VARCHAR(100) NOT NULL,
                    count INTEGER DEFAULT 1,
                    weight INTEGER DEFAULT 100,
                    required_key_id INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[ChestSystem] DB Init Error: {e}")

    def _init_loot_tables(self):
        self.map_loot_tables.clear()
        self.category_loot_tables.clear()

        # 1. Standard Category Tables (1:1 C# ChestDropManager.cs lines 90-120)
        self.category_loot_tables["coconut"] = [
            ChestLootEntry(41066, "Coconut", 1, 80),
            ChestLootEntry(28014, "Fresh Fruit", 1, 20)
        ]
        self.category_loot_tables["medicine"] = [
            ChestLootEntry(30259, "Black Medicine", 1, 70),
            ChestLootEntry(30001, "Herb Potion", 1, 30)
        ]
        self.category_loot_tables["headband"] = [
            ChestLootEntry(22061, "Headband", 1, 100)
        ]
        self.category_loot_tables["ore"] = [
            ChestLootEntry(24001, "Iron Ore", 1, 40),
            ChestLootEntry(24002, "Copper Ore", 1, 30),
            ChestLootEntry(24005, "Coal", 1, 30)
        ]
        self.category_loot_tables["default_chest"] = [
            ChestLootEntry(28014, "Fresh Fruit", 1, 40),
            ChestLootEntry(30001, "Herb Potion", 1, 30),
            ChestLootEntry(27001, "Ordinary Wood", 1, 20),
            ChestLootEntry(28001, "Sea Water", 1, 10)
        ]

        # 2. Standard Map Tables (1:1 C# ChestDropManager.cs lines 53-87)
        self.map_loot_tables[10036] = [
            ChestLootEntry(41066, "Coconut", 1, 40),
            ChestLootEntry(28014, "Fresh Fruit", 1, 30),
            ChestLootEntry(28001, "Sea Water", 1, 15),
            ChestLootEntry(27001, "Ordinary Wood", 1, 15)
        ]
        self.map_loot_tables[10035] = [
            ChestLootEntry(41066, "Coconut", 1, 50),
            ChestLootEntry(28014, "Fresh Fruit", 1, 30),
            ChestLootEntry(27001, "Ordinary Wood", 1, 20)
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
        self.map_loot_tables[10020] = [
            ChestLootEntry(24001, "Iron Ore", 1, 35),
            ChestLootEntry(24002, "Copper Ore", 1, 25),
            ChestLootEntry(24005, "Coal", 1, 25),
            ChestLootEntry(24010, "Gold Sand", 1, 15)
        ]

        # 3. Dynamic Database Overrides from game_chest_pools
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT map_id, item_id, item_name, count, weight FROM game_chest_pools").fetchall()
            conn.close()
            db_maps = set()
            for r in rows:
                m_id, it_id, it_name, cnt, wt = r
                if m_id not in db_maps:
                    self.map_loot_tables[m_id] = []
                    db_maps.add(m_id)
                self.map_loot_tables[m_id].append(ChestLootEntry(it_id, it_name, cnt, wt))
            if db_maps:
                logger.info(f"[ChestSystem] Loaded dynamic chests for {len(db_maps)} maps from database.")
        except Exception as e:
            logger.warning(f"[ChestSystem] Dynamic database chest tables note: {e}")

    def reload_from_db(self, dynamic_mgr=None):
        self._init_loot_tables()

    def roll_drop(self, map_id: int, prop_name: str = "") -> ChestLootEntry:
        """Rolls an authentic drop from category or map loot pool (1:1 C# ChestDropManager.RollDrop)."""
        lower = (prop_name or "").lower().strip()

        # Specific Category Matches
        if "coconut" in lower and "coconut" in self.category_loot_tables:
            return self._pick_random(self.category_loot_tables["coconut"])
        if any(k in lower for k in ["cabinet", "shelf", "bick", "medicine"]) and "medicine" in self.category_loot_tables:
            return self._pick_random(self.category_loot_tables["medicine"])
        if any(k in lower for k in ["headband", "bush"]) and "headband" in self.category_loot_tables:
            return self._pick_random(self.category_loot_tables["headband"])
        if any(k in lower for k in ["mine", "ore", "vein", "mineral"]) and "ore" in self.category_loot_tables:
            return self._pick_random(self.category_loot_tables["ore"])

        # Map-specific Match
        if map_id in self.map_loot_tables and self.map_loot_tables[map_id]:
            return self._pick_random(self.map_loot_tables[map_id])

        # Default Chest Fallback
        if "default_chest" in self.category_loot_tables and self.category_loot_tables["default_chest"]:
            return self._pick_random(self.category_loot_tables["default_chest"])

        return ChestLootEntry(28014, "Fresh Fruit", 1, 100)

    def _pick_random(self, entries: List[ChestLootEntry]) -> ChestLootEntry:
        if not entries:
            return ChestLootEntry(28014, "Fresh Fruit", 1, 100)
        total_weight = sum(e.weight for e in entries)
        if total_weight <= 0:
            return entries[0]
        roll = random.randint(1, total_weight)
        cur = 0
        for entry in entries:
            cur += entry.weight
            if roll <= cur:
                return entry
        return entries[-1]

    def is_chest_opened(self, char_id: int, map_id: int, chest_id: int, is_permanent: bool = False) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            row_match = conn.execute(
                "SELECT opened_at FROM charchests WHERE char_id = ? AND map_id = ? AND chest_id = ?",
                (char_id, map_id, chest_id)
            ).fetchone()
            conn.close()
            if not row_match or row_match[0] is None:
                return False
            if is_permanent:
                return True
            opened_at = float(row_match[0])
            # If respawn time elapsed for gathering node, it is available again
            if self.default_respawn_seconds > 0 and (time.time() - opened_at) >= self.default_respawn_seconds:
                return False
            return True
        except Exception:
            return False

    async def open_chest(
        self,
        server,
        player,
        map_id: int,
        chest_id: int,
        required_key: int = 0,
        prop_name: str = ""
    ) -> bool:
        if not player:
            return False

        if self.is_chest_opened(player.char_id, map_id, chest_id):
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("This node/chest is currently empty and will respawn soon.")
            await player.send_packet(sys_msg)
            await player.send_packet(PacketWriter().write_8(20).write_8(8))
            await player.send_packet(PacketWriter().write_8(5).write_8(4))
            return False

        # Key verification if required
        from server.gameserver import remove_item_at_slot
        if required_key > 0:
            has_key = any(it.get("item_id") == required_key for it in player.inventory)
            if not has_key:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"This treasure chest is locked! Requires Key #{required_key}."
                )
                await player.send_packet(sys_msg)
                await player.send_packet(PacketWriter().write_8(20).write_8(8))
                await player.send_packet(PacketWriter().write_8(5).write_8(4))
                return False

            # Consume 1 key
            for it in list(player.inventory):
                if it.get("item_id") == required_key:
                    slot = it.get("slot")
                    if slot is not None:
                        remove_item_at_slot(player, slot, 1)
                    break

        # Roll dynamic loot
        selected = self.roll_drop(map_id, prop_name)

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

        # Send opened chest animation (AC 22 Sub 1 [22, 1, click_id, 1])
        open_anim = PacketWriter().write_8(22).write_8(1).write_16(chest_id).write_8(1)
        await player.send_packet(open_anim)
        if hasattr(server, 'broadcast_to_map'):
            server.broadcast_to_map(map_id, open_anim, exclude_session=player)

        # Mark broken & set respawn on map NPC
        map_npcs = getattr(server, 'map_npcs', {}).get(map_id, [])
        for m_npc in map_npcs:
            m_cid = m_npc.click_id if hasattr(m_npc, 'click_id') else (m_npc.get('click_id', 0) if isinstance(m_npc, dict) else 0)
            if m_cid == chest_id:
                if hasattr(m_npc, 'is_broken'):
                    m_npc.is_broken = True
                    is_perm = hasattr(m_npc, 'is_permanent_chest') and m_npc.is_permanent_chest()
                    is_gather = hasattr(m_npc, 'is_gathering_node') and m_npc.is_gathering_node()
                    if not is_perm and (is_gather or self.default_respawn_seconds > 0):
                        m_npc.respawn_time = time.time() + self.default_respawn_seconds
                    else:
                        m_npc.respawn_time = 0.0
                elif isinstance(m_npc, dict):
                    m_npc['is_broken'] = True
                break

        # Award item via atomic server.grant_item (dispatches AC 23:6, AC 23:8, AC 23:5, saves DB)
        if hasattr(server, 'grant_item'):
            await server.grant_item(player, selected.item_id, selected.count)
        else:
            from server.gameserver import add_item_to_inventory
            add_item_to_inventory(player, selected.item_id, selected.count)
            if hasattr(server, 'build_inventory_packet'):
                await player.send_packet(server.build_inventory_packet(player))
            if hasattr(server, 'save_player_to_db'):
                server.save_player_to_db(player)

        # Send Prompt (AC 23 Sub 57), Fanfare (AC 20 Sub 10), and Release Interaction Lock
        item_name = server.get_item_name(selected.item_id) if hasattr(server, 'get_item_name') else selected.item_name
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Obtained {item_name}!"
        )
        await player.send_packet(sys_msg)
        await player.send_packet(PacketWriter().write_8(20).write_8(10))  # Fanfare SFX
        await player.send_packet(PacketWriter().write_8(20).write_8(8))   # Interaction End
        await player.send_packet(PacketWriter().write_8(5).write_8(4))    # Restore Control

        logger.info(f"[ChestSystem] Player {player.char_name} opened chest/prop #{chest_id} on map {map_id} ({prop_name}) -> {selected.count}x {item_name} (#{selected.item_id}).")
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
