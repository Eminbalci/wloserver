"""
Wonderland Online Central Dynamic Data Management Engine
Manages hot-reloadable dynamic configuration and SQLite persistence for:
1. Monster Item Drops (game_monster_drops)
2. Quests & Dialogue Trees (game_quests)
3. Crafting & Manufacturing Recipes (game_crafting_recipes)
4. Alchemy Compounding Formulas (game_alchemy_recipes)
5. World Map Treasure Chests & Keys (game_chest_pools)
6. Gathering Resource Pools (game_gathering_pools)
7. Forging Spars & Gems (game_forging_materials)
8. Instance Dungeons (game_instances)
9. Player Titles & Achievements (game_titles)
"""

import os
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple, Set, Union

logger = logging.getLogger("WLO_Server")


class DynamicDataManager:
    """Central hub for loading, persisting, querying, and hot-reloading all game configurations dynamically."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._ensure_tables()
        self._seed_default_dynamic_data()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        try:
            with self.get_connection() as conn:
                # 1. Monster Drops
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_monster_drops (
                        drop_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        monster_id INTEGER NOT NULL,
                        item_id INTEGER NOT NULL,
                        item_name VARCHAR(100) NOT NULL,
                        drop_rate INTEGER NOT NULL DEFAULT 1000, -- 1-10000 (0.01% - 100%)
                        min_count INTEGER NOT NULL DEFAULT 1,
                        max_count INTEGER NOT NULL DEFAULT 1,
                        quest_only INTEGER DEFAULT 0
                    )
                """)

                # 2. Crafting Recipes
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_crafting_recipes (
                        recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        station_type VARCHAR(50) NOT NULL, -- worktable, forge, loom, kitchen, sawmill, furnace
                        output_item_id INTEGER NOT NULL,
                        output_name VARCHAR(100) NOT NULL,
                        output_count INTEGER NOT NULL DEFAULT 1,
                        required_materials TEXT NOT NULL, -- JSON list of {"item_id": id, "count": count}
                        craft_time_sec INTEGER DEFAULT 0,
                        required_level INTEGER DEFAULT 1
                    )
                """)

                # 3. Alchemy Recipes
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_alchemy_recipes (
                        recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        input_items TEXT NOT NULL, -- JSON list of item_ids
                        output_item_id INTEGER NOT NULL,
                        output_name VARCHAR(100) NOT NULL,
                        base_rate REAL DEFAULT 80.0,
                        min_tier INTEGER DEFAULT 1, -- 1: Primary, 2: Junior, 3: Senior
                        min_level INTEGER DEFAULT 1
                    )
                """)

                # 4. Treasure Chest Pools
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

                # 5. Gathering Pools
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_gathering_pools (
                        pool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        gather_type INTEGER NOT NULL, -- 1: Fishing, 2: Mining, 3: Woodcutting
                        map_id INTEGER DEFAULT 0,
                        item_id INTEGER NOT NULL,
                        item_name VARCHAR(100) NOT NULL,
                        weight INTEGER DEFAULT 100,
                        min_level INTEGER DEFAULT 1
                    )
                """)

                # 6. Forging Materials
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_forging_materials (
                        material_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        stat_boosts TEXT NOT NULL, -- JSON dict of {"atk": 24, "def": 24, ...}
                        success_rate REAL DEFAULT 100.0
                    )
                """)

                # 7. Instances
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_instances (
                        instance_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        min_level INTEGER DEFAULT 10,
                        map_id INTEGER NOT NULL,
                        total_rooms INTEGER DEFAULT 3,
                        reward_gold INTEGER DEFAULT 10000,
                        reward_exp INTEGER DEFAULT 5000,
                        reward_item_id INTEGER DEFAULT 0
                    )
                """)

                # 8. Titles
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_titles (
                        title_id INTEGER PRIMARY KEY,
                        title_name VARCHAR(100) NOT NULL,
                        description TEXT DEFAULT '',
                        stat_bonuses TEXT NOT NULL -- JSON dict of {"max_hp": 100, "atk": 20, ...}
                    )
                """)

                # 9. Vehicles
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_vehicles (
                        vehicle_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        speed_mult REAL DEFAULT 1.5,
                        sea_only INTEGER DEFAULT 0,
                        air_only INTEGER DEFAULT 0,
                        land_only INTEGER DEFAULT 0
                    )
                """)

                # 10. Lucky Draw Prizes
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_luckydraw_prizes (
                        prize_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_id INTEGER NOT NULL,
                        item_name VARCHAR(100) NOT NULL,
                        count INTEGER DEFAULT 1,
                        weight INTEGER DEFAULT 100,
                        is_jackpot INTEGER DEFAULT 0
                    )
                """)

                # 11. Pet Foods
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_pet_foods (
                        item_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        amity_gain INTEGER DEFAULT 2,
                        min_amity INTEGER DEFAULT 0,
                        max_amity INTEGER DEFAULT 100
                    )
                """)

                # 12. Reborn Jobs
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_reborn_jobs (
                        job_type INTEGER PRIMARY KEY,
                        job_name VARCHAR(50) NOT NULL,
                        min_level INTEGER DEFAULT 100,
                        cape_item_id INTEGER DEFAULT 0,
                        atk_mult REAL DEFAULT 1.0,
                        def_mult REAL DEFAULT 1.0,
                        matk_mult REAL DEFAULT 1.0,
                        mdef_mult REAL DEFAULT 1.0,
                        spd_mult REAL DEFAULT 1.0,
                        hp_mult REAL DEFAULT 1.0,
                        sp_mult REAL DEFAULT 1.0
                    )
                """)

                # 13. Sustenance Items
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_sustenance_items (
                        item_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        hp_buffer INTEGER DEFAULT 0,
                        sp_buffer INTEGER DEFAULT 0
                    )
                """)

                # 14. Morph Items
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_morph_items (
                        item_id INTEGER PRIMARY KEY,
                        morph_npc_id INTEGER NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        duration_sec REAL DEFAULT 900.0,
                        stat_bonuses TEXT NOT NULL -- JSON dict
                    )
                """)

                # 15. Saddles
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_saddles (
                        item_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        speed_mult REAL DEFAULT 1.4,
                        required_pet_level INTEGER DEFAULT 1
                    )
                """)

                # 16. Recycle Materials
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_recycle_materials (
                        material_id INTEGER PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        weight INTEGER DEFAULT 100
                    )
                """)

                # 17. Revive Altars
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_revive_altars (
                        map_id INTEGER PRIMARY KEY,
                        respawn_map_id INTEGER NOT NULL,
                        respawn_x INTEGER NOT NULL,
                        respawn_y INTEGER NOT NULL,
                        exp_loss_percent REAL DEFAULT 0.02
                    )
                """)

                # 18. Weather Engine Maps
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_map_weather (
                        map_id INTEGER PRIMARY KEY,
                        weather_type INTEGER NOT NULL, -- 0: None, 1: Rain, 2: Snow, 3: Sakura, 4: Fog, 5: Storm
                        intensity INTEGER DEFAULT 1
                    )
                """)

                # 19. NPC Default Visibility & Quest Conditions
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_npc_visibility (
                        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        map_id INTEGER NOT NULL,
                        click_id INTEGER NOT NULL,
                        npc_id INTEGER NOT NULL,
                        npc_name VARCHAR(100) NOT NULL,
                        default_visible INTEGER DEFAULT 1, -- 1: Visible, 0: Hidden
                        required_quest_id INTEGER DEFAULT 0,
                        required_quest_state INTEGER DEFAULT 0, -- 0: Any, 1: In Progress, 2: Completed
                        hide_if_quest_completed INTEGER DEFAULT 0,
                        hide_if_companion_recruited INTEGER DEFAULT 0
                    )
                """)

                # 20. Item Mall Catalog
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_item_mall (
                        item_id INTEGER NOT NULL,
                        item_name VARCHAR(100) NOT NULL,
                        category VARCHAR(50) DEFAULT 'Grocery',
                        point_cost INTEGER DEFAULT 100,
                        original_price INTEGER DEFAULT 0,
                        gold_cost INTEGER DEFAULT 0,
                        count INTEGER DEFAULT 1,
                        is_hot INTEGER DEFAULT 0,
                        is_new INTEGER DEFAULT 0,
                        is_limited INTEGER DEFAULT 0,
                        on_sale INTEGER DEFAULT 0,
                        discount INTEGER DEFAULT 100,
                        badge INTEGER DEFAULT 0,
                        category_id INTEGER DEFAULT 3,
                        order_idx INTEGER DEFAULT 0,
                        is_bonus INTEGER DEFAULT 0,
                        subcategory_id INTEGER DEFAULT 1,
                        PRIMARY KEY (item_id, count, is_bonus)
                    )
                """)

                # 21. Starter Items (Free starter gifts for new characters)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_starter_items (
                        item_id INTEGER PRIMARY KEY,
                        item_name VARCHAR(100) NOT NULL,
                        count INTEGER NOT NULL DEFAULT 1,
                        order_idx INTEGER DEFAULT 0,
                        description VARCHAR(255) DEFAULT ''
                    )
                """)

                # Dynamic column migrations
                for col_name, col_type in [
                    ("original_price", "INTEGER DEFAULT 0"),
                    ("is_new", "INTEGER DEFAULT 0"),
                    ("is_limited", "INTEGER DEFAULT 0"),
                    ("on_sale", "INTEGER DEFAULT 0"),
                    ("discount", "INTEGER DEFAULT 100"),
                    ("badge", "INTEGER DEFAULT 0"),
                    ("category_id", "INTEGER DEFAULT 3"),
                    ("order_idx", "INTEGER DEFAULT 0"),
                    ("is_bonus", "INTEGER DEFAULT 0"),
                    ("subcategory_id", "INTEGER DEFAULT 1"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE game_item_mall ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

                conn.commit()
                logger.info("[DynamicDataManager] All dynamic data schema tables initialized.")
        except Exception as e:
            logger.error(f"[DynamicDataManager] DB Init Error: {e}", exc_info=True)

    def _seed_default_dynamic_data(self):
        """Populates dynamic tables with official baseline defaults if empty."""
        try:
            with self.get_connection() as conn:
                # 1. Seed Monster Drops (from Npc.dat if available, else baseline)
                drop_count = conn.execute("SELECT count(*) FROM game_monster_drops").fetchone()[0]
                if drop_count == 0:
                    try:
                        from server.dat_loaders import NpcDatLoader
                        npc_file = os.path.join(os.getcwd(), "data", "Npc.dat")
                        if os.path.exists(npc_file):
                            nl = NpcDatLoader(npc_file)
                            drops_to_add = []
                            for n_id, n_info in nl.npcs.items():
                                for it_id in n_info.drop_item_ids:
                                    drops_to_add.append((n_id, it_id, f"Drop #{it_id}", 3000, 1, 1, 0))
                            if drops_to_add:
                                conn.executemany("""
                                    INSERT INTO game_monster_drops (monster_id, item_id, item_name, drop_rate, min_count, max_count, quest_only)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, drops_to_add)
                                logger.info(f"[DynamicDataManager] Seeded {len(drops_to_add)} authentic drops from Npc.dat.")
                    except Exception as e:
                        logger.warning(f"[DynamicDataManager] Fallback Npc.dat drops: {e}")

                    # Ensure baseline drops present
                    if conn.execute("SELECT count(*) FROM game_monster_drops").fetchone()[0] == 0:
                        drops = [
                            (1001, 28014, "Fresh Fruit", 4000, 1, 2, 0),
                            (1001, 28006, "Red Apple", 3000, 1, 1, 0),
                            (1001, 27001, "Ordinary Wood", 2000, 1, 1, 0),
                            (1002, 27020, "Iron Ore", 3500, 1, 2, 0),
                            (1002, 27021, "Copper Ore", 2500, 1, 1, 0),
                            (1002, 46005, "Refined Metal", 500, 1, 1, 0),
                            (1003, 30001, "Herb Potion", 5000, 1, 2, 0),
                            (1003, 30025, "Rice Ball", 3000, 1, 1, 0),
                            (1004, 30014, "Fine Silk", 2500, 1, 2, 0),
                            (1004, 48033, "Zodiac Crystal Chest", 100, 1, 1, 0),
                        ]
                        conn.executemany("""
                            INSERT INTO game_monster_drops (monster_id, item_id, item_name, drop_rate, min_count, max_count, quest_only)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, drops)

                # 2. Seed Crafting Recipes
                recipe_count = conn.execute("SELECT count(*) FROM game_crafting_recipes").fetchone()[0]
                if recipe_count == 0:
                    recipes = [
                        ("worktable", 38027, "Simple Wooden Chair", 1, json.dumps([{"item_id": 27001, "count": 2}]), 0, 1),
                        ("worktable", 38049, "Wooden Desk", 1, json.dumps([{"item_id": 27001, "count": 4}]), 0, 1),
                        ("worktable", 38030, "Spanner Tool", 1, json.dumps([{"item_id": 27020, "count": 2}, {"item_id": 27001, "count": 1}]), 0, 1),
                        ("forge", 46005, "Refined Iron Ingot", 1, json.dumps([{"item_id": 27020, "count": 2}, {"item_id": 27022, "count": 1}]), 0, 1),
                        ("forge", 21001, "Bronze Sword", 1, json.dumps([{"item_id": 46005, "count": 2}, {"item_id": 27001, "count": 1}]), 0, 5),
                        ("loom", 30014, "Fine Silk Cloth", 1, json.dumps([{"item_id": 30015, "count": 2}]), 0, 1),
                        ("kitchen", 28020, "Roast Meat", 1, json.dumps([{"item_id": 30001, "count": 1}, {"item_id": 27001, "count": 1}]), 0, 1),
                        ("kitchen", 30025, "Rice Ball Snack", 1, json.dumps([{"item_id": 28015, "count": 2}, {"item_id": 28003, "count": 1}]), 0, 1),
                    ]
                    conn.executemany("""
                        INSERT INTO game_crafting_recipes (station_type, output_item_id, output_name, output_count, required_materials, craft_time_sec, required_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, recipes)

                # 3. Seed Alchemy Recipes (from Compound.dat / Compound2.dat if available, else baseline)
                alchemy_count = conn.execute("SELECT count(*) FROM game_alchemy_recipes").fetchone()[0]
                if alchemy_count == 0:
                    try:
                        from server.dat_loaders import CompoundDatLoader
                        c_file1 = os.path.join(os.getcwd(), "data", "Compound.dat")
                        c_file2 = os.path.join(os.getcwd(), "data", "Compound2.dat")
                        cl = CompoundDatLoader()
                        if os.path.exists(c_file1):
                            cl.load(c_file1, clear=True)
                        if os.path.exists(c_file2):
                            cl.load(c_file2, clear=False)
                        alch_to_add = []
                        for cr in cl.recipes:
                            inputs = [m[0] for m in cr.materials]
                            alch_to_add.append((json.dumps(inputs), cr.result_item_id, f"Item #{cr.result_item_id}", 80.0, 1, 1))
                        if alch_to_add:
                            conn.executemany("""
                                INSERT INTO game_alchemy_recipes (input_items, output_item_id, output_name, base_rate, min_tier, min_level)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, alch_to_add)
                            logger.info(f"[DynamicDataManager] Seeded {len(alch_to_add)} authentic recipes from Compound.dat / Compound2.dat.")
                    except Exception as e:
                        logger.warning(f"[DynamicDataManager] Fallback Compound recipes: {e}")

                    # Fallback if still empty
                    if conn.execute("SELECT count(*) FROM game_alchemy_recipes").fetchone()[0] == 0:
                        alch = [
                            (json.dumps([27001, 27001]), 48001, "Wooden Plank", 90.0, 1, 1),
                            (json.dumps([27002, 27001]), 48002, "Hardwood Plank", 85.0, 1, 1),
                            (json.dumps([27005, 27001]), 27015, "Wooden Bow", 75.0, 1, 1),
                            (json.dumps([27020, 27001]), 46005, "Refined Metal", 75.0, 1, 1),
                            (json.dumps([46005, 27001]), 21001, "Bronze Sword", 70.0, 1, 1),
                            (json.dumps([46005, 46005]), 21010, "Iron Armor", 65.0, 1, 1),
                            (json.dumps([46005, 27002, 27023]), 21025, "Knight Bastard Sword", 60.0, 2, 10),
                            (json.dumps([30015, 30016, 27022]), 22015, "Reinforced Leather Vest", 65.0, 2, 10),
                            (json.dumps([30202, 28015, 27024]), 30204, "Grand Elixir of Life", 70.0, 2, 15),
                            (json.dumps([46005, 27024, 27023, 27002]), 21050, "Dragon Slayer Greatsword", 50.0, 3, 20),
                            (json.dumps([30018, 30013, 27024, 46005]), 22030, "Celestial Robes", 50.0, 3, 20),
                        ]
                        conn.executemany("""
                            INSERT INTO game_alchemy_recipes (input_items, output_item_id, output_name, base_rate, min_tier, min_level)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, alch)

                # 4. Seed Chest Pools from eve.Emg if available
                chest_count = conn.execute("SELECT count(*) FROM game_chest_pools").fetchone()[0]
                if chest_count == 0:
                    try:
                        from server.eve_loader import EveManager
                        eve_file = os.path.join(os.getcwd(), "data", "eve.Emg")
                        if os.path.exists(eve_file):
                            em = EveManager(eve_file)
                            chests_to_add = []
                            for m_id, map_obj in em.maps.items():
                                for it in map_obj.item_nodes:
                                    if it.item_id > 0:
                                        chests_to_add.append((m_id, it.click_id, it.item_id, it.name or f"Chest #{it.item_id}", 1, 100, 0))
                            if chests_to_add:
                                conn.executemany("""
                                    INSERT INTO game_chest_pools (map_id, chest_id, item_id, item_name, count, weight, required_key_id)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, chests_to_add)
                                logger.info(f"[DynamicDataManager] Extracted {len(chests_to_add)} dynamic chests/items from eve.Emg into game_chest_pools.")
                    except Exception as ex:
                        logger.warning(f"[DynamicDataManager] Could not seed chests from eve.Emg: {ex}")

                # 5. Seed Gathering Pools
                gather_count = conn.execute("SELECT count(*) FROM game_gathering_pools").fetchone()[0]
                if gather_count == 0:
                    g_data = [
                        # Fishing (Type 1)
                        (1, 0, 30003, "Crab", 100, 1),
                        (1, 0, 30004, "Trout", 90, 1),
                        (1, 0, 30005, "Salmon", 80, 5),
                        (1, 0, 30006, "Eel", 60, 10),
                        (1, 0, 30007, "Seaweed", 120, 1),
                        # Mining (Type 2)
                        (2, 0, 27020, "Iron Ore", 120, 1),
                        (2, 0, 27021, "Copper Ore", 100, 1),
                        (2, 0, 27022, "Coal", 100, 1),
                        (2, 0, 27023, "Silver Ore", 50, 10),
                        (2, 0, 27024, "Gold Ore", 30, 15),
                        # Woodcutting (Type 3)
                        (3, 0, 27001, "Ordinary Wood", 150, 1),
                        (3, 0, 27002, "Pine Wood", 100, 5),
                        (3, 0, 27003, "Cypress Wood", 80, 10),
                        (3, 0, 27004, "Willow Wood", 60, 15),
                        (3, 0, 27005, "Vine", 100, 1),
                    ]
                    conn.executemany("""
                        INSERT INTO game_gathering_pools (gather_type, map_id, item_id, item_name, weight, min_level)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, g_data)

                # 5. Seed Forging Materials
                forge_count = conn.execute("SELECT count(*) FROM game_forging_materials").fetchone()[0]
                if forge_count == 0:
                    f_data = [
                        (47001, "+24 ATK Spar", json.dumps({"atk": 24}), 100.0),
                        (47002, "+24 DEF Spar", json.dumps({"def": 24}), 100.0),
                        (47003, "+24 MATK Spar", json.dumps({"matk": 24}), 100.0),
                        (47004, "+24 MDEF Spar", json.dumps({"mdef": 24}), 100.0),
                        (47005, "+24 SPD Spar", json.dumps({"spd": 24}), 100.0),
                        (47010, "Brilliant Diamond (+42 Stats)", json.dumps({"atk": 42, "def": 42, "matk": 42, "mdef": 42, "spd": 42}), 100.0),
                    ]
                    conn.executemany("""
                        INSERT INTO game_forging_materials (material_id, name, stat_boosts, success_rate)
                        VALUES (?, ?, ?, ?)
                    """, f_data)

                # 6. Seed Instances
                inst_count = conn.execute("SELECT count(*) FROM game_instances").fetchone()[0]
                if inst_count == 0:
                    i_data = [
                        (1, "Haunted Ghost Ship", 40, 16001, 3, 20000, 10000, 48033),
                        (2, "Maya Alien Pyramid", 60, 18001, 4, 40000, 25000, 48033),
                        (3, "Sunken Pirate Cove", 80, 19001, 5, 80000, 50000, 48033),
                    ]
                    conn.executemany("""
                        INSERT INTO game_instances (instance_id, name, min_level, map_id, total_rooms, reward_gold, reward_exp, reward_item_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, i_data)

                # 7. Seed Titles
                title_count = conn.execute("SELECT count(*) FROM game_titles").fetchone()[0]
                if title_count == 0:
                    t_data = [
                        (1, "Novice Adventurer", "Completed Island Tutorial", json.dumps({"max_hp": 100})),
                        (2, "Island Explorer", "Traveled 10,000 steps", json.dumps({"spd": 10})),
                        (3, "Master Alchemist", "Synthesized 50 items", json.dumps({"matk": 20})),
                        (4, "Palace Conqueror", "Cleared 12 Zodiac Trials", json.dumps({"atk": 30, "def": 30})),
                        (5, "Reborn Legend", "Awakened as Reborn Champion", json.dumps({"atk": 50, "def": 50, "matk": 50, "mdef": 50, "spd": 30})),
                    ]
                    conn.executemany("""
                        INSERT INTO game_titles (title_id, title_name, description, stat_bonuses)
                        VALUES (?, ?, ?, ?)
                    """, t_data)

                # 8. Seed Vehicles
                v_count = conn.execute("SELECT count(*) FROM game_vehicles").fetchone()[0]
                if v_count == 0:
                    v_data = [
                        (36001, "Wooden Raft", 1.2, 1, 0, 0),
                        (36002, "Canoe", 1.35, 1, 0, 0),
                        (36003, "Sailboat", 1.5, 1, 0, 0),
                        (36004, "Steamboat", 1.7, 1, 0, 0),
                        (36005, "Yellow Submarine", 1.6, 1, 0, 0),
                        (36006, "Hot-Air Balloon", 1.5, 0, 1, 0),
                        (36007, "Steam Airship", 1.8, 0, 1, 0),
                        (36008, "Alien UFO", 2.2, 0, 1, 0),
                        (36009, "Bicycle", 1.3, 0, 0, 1),
                        (36010, "Motorcycle", 1.8, 0, 0, 1),
                        (36011, "Sports Car", 2.0, 0, 0, 1),
                    ]
                    conn.executemany("INSERT INTO game_vehicles VALUES (?, ?, ?, ?, ?, ?)", v_data)

                # 9. Seed Lucky Draw Prizes
                ld_count = conn.execute("SELECT count(*) FROM game_luckydraw_prizes").fetchone()[0]
                if ld_count == 0:
                    ld_data = [
                        (48033, "Zodiac Crystal Chest", 1, 5, 1),
                        (47010, "Brilliant Diamond (+42)", 1, 10, 1),
                        (47001, "+24 ATK Spar", 1, 20, 0),
                        (47002, "+24 DEF Spar", 1, 20, 0),
                        (47005, "+24 SPD Spar", 1, 20, 0),
                        (46005, "Refined Iron Ingot", 5, 50, 0),
                        (30025, "Rice Ball Buffer (50k HP/SP)", 2, 80, 0),
                        (27001, "Iron Ore Bundle", 10, 120, 0),
                    ]
                    conn.executemany("INSERT INTO game_luckydraw_prizes (item_id, item_name, count, weight, is_jackpot) VALUES (?, ?, ?, ?, ?)", ld_data)

                # 10. Seed Pet Foods
                pf_count = conn.execute("SELECT count(*) FROM game_pet_foods").fetchone()[0]
                if pf_count == 0:
                    pf_data = [
                        (28006, "Red Apple", 1, 0, 100),
                        (28014, "Fresh Fruit", 1, 0, 100),
                        (28020, "Roast Meat", 2, 0, 100),
                        (30025, "Rice Ball Snack", 3, 0, 100),
                        (30204, "Grand Pet Elixir", 5, 0, 100),
                    ]
                    conn.executemany("INSERT INTO game_pet_foods VALUES (?, ?, ?, ?, ?)", pf_data)

                # 11. Seed Reborn Jobs
                rb_count = conn.execute("SELECT count(*) FROM game_reborn_jobs").fetchone()[0]
                if rb_count == 0:
                    rb_data = [
                        (1, "Killer", 100, 23001, 1.45, 1.0, 1.0, 1.0, 1.25, 1.2, 1.0),
                        (2, "Warrior", 100, 23002, 1.2, 1.45, 1.0, 1.1, 1.0, 1.4, 1.0),
                        (3, "Knight", 100, 23003, 1.1, 1.25, 1.0, 1.25, 1.4, 1.3, 1.0),
                        (4, "Wit", 100, 23004, 1.0, 1.0, 1.45, 1.2, 1.15, 1.1, 1.4),
                        (5, "Priest", 100, 23005, 1.0, 1.2, 1.2, 1.45, 1.0, 1.35, 1.35),
                        (6, "Seer", 100, 23006, 1.0, 1.15, 1.25, 1.2, 1.45, 1.15, 1.35),
                    ]
                    conn.executemany("INSERT INTO game_reborn_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rb_data)

                # 12. Seed Sustenance Items
                sus_count = conn.execute("SELECT count(*) FROM game_sustenance_items").fetchone()[0]
                if sus_count == 0:
                    sus_data = [
                        (30025, "Rice Ball", 50000, 50000),
                        (30001, "Herb Potion Jar", 10000, 5000),
                        (30204, "Grand Elixir Buffer", 100000, 100000),
                    ]
                    conn.executemany("INSERT INTO game_sustenance_items VALUES (?, ?, ?, ?)", sus_data)

                # 13. Seed Morph Items
                morph_count = conn.execute("SELECT count(*) FROM game_morph_items").fetchone()[0]
                if morph_count == 0:
                    m_data = [
                        (41001, 1001, "Green Jelly Disguise", 900.0, json.dumps({"spd": 10, "def": 15})),
                        (41002, 1002, "Dire Wolf Disguise", 900.0, json.dumps({"atk": 25, "spd": 15})),
                        (41003, 1003, "Haunted Ghost Disguise", 900.0, json.dumps({"matk": 30, "mdef": 20})),
                        (41004, 1004, "Ocean Siren Disguise", 900.0, json.dumps({"matk": 20, "max_sp": 100})),
                    ]
                    conn.executemany("INSERT INTO game_morph_items VALUES (?, ?, ?, ?, ?)", m_data)

                # 14. Seed Saddles
                sad_count = conn.execute("SELECT count(*) FROM game_saddles").fetchone()[0]
                if sad_count == 0:
                    s_data = [
                        (38020, "Pet Saddle", 1.40, 1),
                        (38021, "Grand Golden Saddle", 1.60, 20),
                    ]
                    conn.executemany("INSERT INTO game_saddles VALUES (?, ?, ?, ?)", s_data)

                # 15. Seed Recycle Base Materials
                rec_count = conn.execute("SELECT count(*) FROM game_recycle_materials").fetchone()[0]
                if rec_count == 0:
                    r_data = [
                        (27020, "Iron Ore", 100),
                        (27021, "Copper Ore", 100),
                        (27022, "Coal", 100),
                        (27001, "Ordinary Wood", 120),
                        (27002, "Pine Wood", 80),
                    ]
                    conn.executemany("INSERT INTO game_recycle_materials VALUES (?, ?, ?)", r_data)

                # 16. Seed Revive Altars
                alt_count = conn.execute("SELECT count(*) FROM game_revive_altars").fetchone()[0]
                if alt_count == 0:
                    alt_data = [
                        (10001, 10010, 450, 380, 0.02),
                        (10036, 10010, 450, 380, 0.02),
                        (10010, 10010, 450, 380, 0.02),
                        (12000, 10010, 450, 380, 0.02),
                        (15000, 15000, 300, 300, 0.02),
                        (16000, 10010, 450, 380, 0.02),
                    ]
                    conn.executemany("INSERT INTO game_revive_altars VALUES (?, ?, ?, ?, ?)", alt_data)

                # 17. Seed Map Weather
                wth_count = conn.execute("SELECT count(*) FROM game_map_weather").fetchone()[0]
                if wth_count == 0:
                    wth_data = [
                        (10001, 1, 3),  # Kelan Woods -> Rain
                        (10036, 1, 2),  # Shipwreck Beach -> Rain
                        (14000, 2, 5),  # South Pole -> Snow
                        (15000, 3, 4),  # Kyoto -> Sakura
                        (16000, 4, 6),  # Ghost Ship -> Dense Fog
                        (12000, 5, 8),  # Open Ocean -> Thunderstorm
                    ]
                    conn.executemany("INSERT INTO game_map_weather VALUES (?, ?, ?)", wth_data)

                # 18. Seed NPC Visibility Rules
                vis_count = conn.execute("SELECT count(*) FROM game_npc_visibility").fetchone()[0]
                if vis_count == 0:
                    vis_data = [
                        (10036, 1, 12032, "Robinson Crusoe", 1, 0, 0, 1, 1), # Hide once recruited/completed
                        (10001, 5, 12005, "Lost Traveler", 1, 0, 0, 1, 0),
                        (10010, 12, 12010, "Secret Merchant", 0, 102, 1, 0, 0), # Hidden by default, visible during quest 102
                    ]
                    conn.executemany("""
                        INSERT INTO game_npc_visibility (map_id, click_id, npc_id, npc_name, default_visible, required_quest_id, required_quest_state, hide_if_quest_completed, hide_if_companion_recruited)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, vis_data)

                # 19. Seed Item Mall Catalog
                mall_count = conn.execute("SELECT count(*) FROM game_item_mall").fetchone()[0]
                if mall_count == 0:
                    loaded_json = False
                    for json_candidate in [
                        os.path.join(os.getcwd(), "server", "data", "item_mall.json"),
                        os.path.join(os.getcwd(), "data", "item_mall.json")
                    ]:
                        if os.path.exists(json_candidate):
                            try:
                                with open(json_candidate, "r", encoding="utf-8") as f:
                                    j_items = json.load(f)
                                mall_rows = []
                                for it in j_items:
                                    mall_rows.append((
                                        int(it["item_id"]),
                                        str(it["item_name"]),
                                        str(it.get("category", "Hot")),
                                        int(it.get("point_cost", 100)),
                                        int(it.get("original_price", 0)),
                                        int(it.get("gold_cost", 0)),
                                        int(it.get("count", 1)),
                                        int(it.get("is_hot", 0)),
                                        int(it.get("is_new", 0)),
                                        int(it.get("on_sale", 0)),
                                        int(it.get("subcategory_id", 1))
                                    ))
                                if mall_rows:
                                    conn.executemany("""
                                        INSERT INTO game_item_mall (item_id, item_name, category, point_cost, original_price, gold_cost, count, is_hot, is_new, on_sale, subcategory_id)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, mall_rows)
                                    loaded_json = True
                                    logger.info(f"[DynamicDataManager] Loaded {len(mall_rows)} Item Mall items from {json_candidate}.")
                                    break
                            except Exception as je:
                                logger.warning(f"[DynamicDataManager] Could not load item_mall.json: {je}")

                    if not loaded_json:
                        mall_data = [
                            (48050, "Mecha Dragon (Mount)", "Hot", 60, 80, 0, 1, 1, 1, 1, 1),
                            (48013, "Alien UFO (Mount)", "Hot", 500, 0, 0, 1, 1, 0, 0, 1),
                            (48033, "Submarine Capsule", "Hot", 249, 300, 0, 1, 1, 1, 1, 1),
                            (36005, "Yellow Submarine", "Hot", 400, 0, 0, 1, 1, 0, 0, 1),
                            (47010, "Brilliant Diamond (+42)", "Hot", 200, 250, 0, 1, 1, 0, 1, 1),
                            (28001, "Forgotten Scroll", "Hot", 150, 0, 0, 1, 1, 0, 0, 1),
                            (22030, "Celestial Robes", "Armory", 280, 350, 0, 1, 0, 1, 1, 1),
                            (22050, "Dragonscale Helm", "Armory", 250, 0, 0, 1, 1, 0, 0, 1),
                            (21010, "Knight Bastard Armor", "Armory", 300, 0, 0, 1, 0, 0, 0, 1),
                            (21050, "Dragon Slayer Greatsword", "Weaponry", 350, 400, 0, 1, 1, 1, 1, 1),
                            (21060, "Celestial Magic Wand", "Weaponry", 320, 0, 0, 1, 1, 0, 0, 1),
                            (28002, "Potential Water", "Grocery", 120, 150, 0, 1, 1, 0, 1, 1),
                            (28003, "Pet Return Scroll", "Grocery", 150, 0, 0, 1, 0, 0, 0, 1),
                            (30025, "Golden Rice Ball x10", "Grocery", 50, 0, 0, 10, 1, 0, 0, 1),
                            (28004, "Double EXP Potion", "Grocery", 80, 100, 0, 1, 1, 0, 1, 1),
                            (36007, "Luxury Airship Ticket", "Furniture", 450, 600, 0, 1, 1, 1, 1, 1),
                            (36008, "Space UFO Ticket", "Furniture", 650, 0, 0, 1, 1, 0, 0, 1),
                            (38027, "Alchemy Stove Station", "Furniture", 80, 0, 0, 1, 0, 0, 0, 1),
                            (48020, "Lucky Draw Ticket x5", "Slot Machine", 50, 0, 0, 5, 1, 1, 0, 1),
                            (48021, "Gacha Capsule Coin x5", "Slot Machine", 60, 0, 0, 5, 1, 0, 0, 1),
                            (47001, "+24 ATK Spar Crystal", "Forging Room", 100, 120, 0, 1, 1, 0, 1, 1),
                            (47002, "+24 DEF Spar Crystal", "Forging Room", 100, 120, 0, 1, 0, 0, 1, 1),
                            (47003, "+24 MATK Spar Crystal", "Forging Room", 100, 120, 0, 1, 1, 0, 1, 1),
                            (47005, "+24 SPD Spar Crystal", "Forging Room", 110, 0, 0, 1, 1, 1, 0, 1),
                            (49001, "Alchemy Book I", "Forging Room", 80, 0, 0, 1, 0, 0, 0, 1),
                        ]
                        conn.executemany("""
                            INSERT INTO game_item_mall (item_id, item_name, category, point_cost, original_price, gold_cost, count, is_hot, is_new, on_sale, subcategory_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, mall_data)

                # 20. Seed Starter Items
                starter_count = conn.execute("SELECT count(*) FROM game_starter_items").fetchone()[0]
                if starter_count == 0:
                    loaded_starter_json = False
                    for json_candidate in [
                        os.path.join(os.getcwd(), "server", "data", "starter_items.json"),
                        os.path.join(os.getcwd(), "data", "starter_items.json")
                    ]:
                        if os.path.exists(json_candidate):
                            try:
                                with open(json_candidate, "r", encoding="utf-8") as f:
                                    j_items = json.load(f)
                                st_rows = []
                                for idx, it in enumerate(j_items):
                                    st_rows.append((
                                        int(it["item_id"]),
                                        str(it.get("item_name", f"Item #{it['item_id']}")),
                                        int(it.get("count", 1)),
                                        int(it.get("order_idx", idx + 1)),
                                        str(it.get("description", ""))
                                    ))
                                if st_rows:
                                    conn.executemany("""
                                        INSERT INTO game_starter_items (item_id, item_name, count, order_idx, description)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, st_rows)
                                    loaded_starter_json = True
                                    logger.info(f"[DynamicDataManager] Loaded {len(st_rows)} starter items from {json_candidate}.")
                                    break
                            except Exception as je:
                                logger.warning(f"[DynamicDataManager] Could not load starter_items.json: {je}")

                    if not loaded_starter_json:
                        default_starters = [
                            (34038, "Starter Gift 1", 1, 1, "Beginner gift package"),
                            (34058, "Remote Control", 1, 2, "Auto-combat and assistant remote control"),
                            (34332, "Mini Dragonfly", 1, 3, "Starter flying mount vehicle"),
                            (32176, "Spicy Hot Pot", 50, 4, "Full recovery food"),
                            (34026, "Protective Exp Pill", 1, 5, "Prevents EXP loss upon death"),
                            (34542, "Substitute Doll", 1, 6, "Prevents companion amity drop upon death"),
                            (21742, "Goddess Robe", 1, 7, "Starter protective equipment"),
                            (34330, "Mini HP Potion", 50, 8, "Starter HP healing potions"),
                            (34190, "10x Holy EXP Potion", 1, 9, "Boosts experience gain"),
                            (34258, "Training Ticket", 1, 10, "Instant training island pass"),
                        ]
                        conn.executemany("""
                            INSERT INTO game_starter_items (item_id, item_name, count, order_idx, description)
                            VALUES (?, ?, ?, ?, ?)
                        """, default_starters)

                conn.commit()
                logger.info("[DynamicDataManager] Default baseline dynamic configuration seeded successfully.")
        except Exception as e:
            logger.error(f"[DynamicDataManager] Seeding Error: {e}", exc_info=True)

    # --- Query Methods for Dynamic Data ---

    def get_monster_drops(self, monster_id: int) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_monster_drops WHERE monster_id = ?", (monster_id,)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting monster drops: {e}")
            return []

    def get_crafting_recipes_by_station(self, station_type: str) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_crafting_recipes WHERE station_type = ?", (station_type,)).fetchall()
                res = []
                for r in rows:
                    d = dict(r)
                    d["required_materials"] = json.loads(d["required_materials"])
                    res.append(d)
                return res
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting crafting recipes: {e}")
            return []

    def get_alchemy_recipes(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_alchemy_recipes").fetchall()
                res = []
                for r in rows:
                    d = dict(r)
                    d["input_items"] = json.loads(d["input_items"])
                    res.append(d)
                return res
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting alchemy recipes: {e}")
            return []

    def get_gathering_pool(self, gather_type: int) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_gathering_pools WHERE gather_type = ?", (gather_type,)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting gathering pool: {e}")
            return []

    def get_forging_materials(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_forging_materials").fetchall()
                res = {}
                for r in rows:
                    d = dict(r)
                    d["stat_boosts"] = json.loads(d["stat_boosts"])
                    res[d["material_id"]] = d
                return res
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting forging materials: {e}")
            return {}

    def get_instances(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_instances").fetchall()
                return {r["instance_id"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting instances: {e}")
            return {}

    def get_titles(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_titles").fetchall()
                res = {}
                for r in rows:
                    d = dict(r)
                    d["stat_bonuses"] = json.loads(d["stat_bonuses"])
                    res[d["title_id"]] = d
                return res
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting titles: {e}")
            return {}

    def get_vehicles(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_vehicles").fetchall()
                return {r["vehicle_id"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting vehicles: {e}")
            return {}

    def get_luckydraw_prizes(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_luckydraw_prizes").fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting luckydraw prizes: {e}")
            return []

    def get_pet_foods(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_pet_foods").fetchall()
                return {r["item_id"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting pet foods: {e}")
            return {}

    def get_reborn_jobs(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_reborn_jobs").fetchall()
                return {r["job_type"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting reborn jobs: {e}")
            return {}

    def get_sustenance_items(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_sustenance_items").fetchall()
                return {r["item_id"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting sustenance items: {e}")
            return {}

    def get_morph_items(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_morph_items").fetchall()
                res = {}
                for r in rows:
                    d = dict(r)
                    d["stat_bonuses"] = json.loads(d["stat_bonuses"])
                    res[d["item_id"]] = d
                return res
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting morph items: {e}")
            return {}

    def get_saddles(self) -> Dict[int, Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_saddles").fetchall()
                return {r["item_id"]: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting saddles: {e}")
            return {}

    def get_recycle_materials(self) -> List[int]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT material_id FROM game_recycle_materials").fetchall()
                return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting recycle materials: {e}")
            return [27020, 27021, 27022, 27001, 27002]

    def get_revive_altars(self) -> Dict[int, Tuple[int, int, int]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT map_id, respawn_map_id, respawn_x, respawn_y FROM game_revive_altars").fetchall()
                return {r["map_id"]: (r["respawn_map_id"], r["respawn_x"], r["respawn_y"]) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting revive altars: {e}")
            return {}

    def get_map_weather(self) -> Dict[int, Tuple[int, int]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT map_id, weather_type, intensity FROM game_map_weather").fetchall()
                return {r["map_id"]: (r["weather_type"], r["intensity"]) for r in rows}
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting map weather: {e}")
            return {}

    def get_npc_visibility_rules(self, map_id: int) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_npc_visibility WHERE map_id = ?", (map_id,)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting NPC visibility rules: {e}")
            return []

    def get_item_mall_catalog(self, is_bonus: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                if is_bonus is not None:
                    rows = conn.execute("SELECT * FROM game_item_mall WHERE is_bonus = ? ORDER BY order_idx, item_id", (is_bonus,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM game_item_mall ORDER BY is_bonus ASC, order_idx ASC, item_id ASC").fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting Item Mall catalog: {e}")
            return []

    def add_or_update_item_mall_item(
        self,
        item_id: int,
        name: str,
        category: str,
        point_cost: int,
        original_price: int = 0,
        gold_cost: int = 0,
        count: int = 1,
        is_hot: int = 0,
        is_new: int = 0,
        is_limited: int = 0,
        on_sale: int = 0,
        discount: int = 100,
        badge: int = 0,
        category_id: int = 3,
        order_idx: int = 0,
        is_bonus: int = 0,
        subcategory_id: int = 1
    ) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO game_item_mall (
                        item_id, item_name, category, point_cost, original_price, gold_cost, count,
                        is_hot, is_new, is_limited, on_sale, discount, badge, category_id, order_idx, is_bonus, subcategory_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(item_id, count, is_bonus) DO UPDATE SET
                        item_name = excluded.item_name,
                        category = excluded.category,
                        point_cost = excluded.point_cost,
                        original_price = excluded.original_price,
                        gold_cost = excluded.gold_cost,
                        is_hot = excluded.is_hot,
                        is_new = excluded.is_new,
                        is_limited = excluded.is_limited,
                        on_sale = excluded.on_sale,
                        discount = excluded.discount,
                        badge = excluded.badge,
                        category_id = excluded.category_id,
                        order_idx = excluded.order_idx,
                        subcategory_id = excluded.subcategory_id
                """, (
                    item_id, name, category, point_cost, original_price, gold_cost, count,
                    is_hot, is_new, is_limited, on_sale, discount, badge, category_id, order_idx, is_bonus, subcategory_id
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error saving Item Mall item: {e}")
            return False

    def export_item_mall_json(self, file_path: str = "server/data/item_mall.json") -> bool:
        """Exports the active SQLite Item Mall catalog to a clean, human-editable JSON file."""
        try:
            items = self.get_item_mall_catalog()
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            logger.info(f"[DynamicDataManager] Exported {len(items)} Item Mall items to {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error exporting Item Mall JSON: {e}")
            return False

    def import_item_mall_json(self, file_path: str = "server/data/item_mall.json", clear_existing: bool = True) -> bool:
        """Imports Item Mall items from JSON into the SQLite dynamic database and hot-reloads Item Mall."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"[DynamicDataManager] JSON file not found: {file_path}")
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)

            if not isinstance(items, list):
                logger.error(f"[DynamicDataManager] Invalid JSON format in {file_path}")
                return False

            with self.get_connection() as conn:
                if clear_existing:
                    conn.execute("DELETE FROM game_item_mall")

                for it in items:
                    conn.execute("""
                        INSERT INTO game_item_mall (
                            item_id, item_name, category, point_cost, original_price, gold_cost, count,
                            is_hot, is_new, is_limited, on_sale, discount, badge, category_id, order_idx, is_bonus, subcategory_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(item_id, count, is_bonus) DO UPDATE SET
                            item_name = excluded.item_name,
                            category = excluded.category,
                            point_cost = excluded.point_cost,
                            original_price = excluded.original_price,
                            gold_cost = excluded.gold_cost,
                            is_hot = excluded.is_hot,
                            is_new = excluded.is_new,
                            is_limited = excluded.is_limited,
                            on_sale = excluded.on_sale,
                            discount = excluded.discount,
                            badge = excluded.badge,
                            category_id = excluded.category_id,
                            order_idx = excluded.order_idx,
                            subcategory_id = excluded.subcategory_id
                    """, (
                        int(it["item_id"]),
                        str(it.get("item_name", f"Item_{it['item_id']}")),
                        str(it.get("category", "Grocery")),
                        int(it.get("point_cost", 100) or 0),
                        int(it.get("original_price", 0) or 0),
                        int(it.get("gold_cost", 0) or 0),
                        int(it.get("count", 1) or 1),
                        int(it.get("is_hot", 0) or 0),
                        int(it.get("is_new", 0) or 0),
                        int(it.get("is_limited", 0) or 0),
                        int(it.get("on_sale", 0) or 0),
                        int(it.get("discount", 100) or 100),
                        int(it.get("badge", 0) or 0),
                        int(it.get("category_id", 3) or 3),
                        int(it.get("order_idx", 0) or 0),
                        int(it.get("is_bonus", 0) or 0),
                        int(it.get("subcategory_id", 1) or 1)
                    ))
                conn.commit()

            from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
            GLOBAL_ITEM_MALL_MANAGER.reload_from_db(self)
            logger.info(f"[DynamicDataManager] Successfully imported {len(items)} Item Mall items from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error importing Item Mall JSON: {e}")
            return False

    # --- Starter Items Management Methods ---

    def get_starter_items(self) -> List[Dict[str, Any]]:
        """Retrieves all starter items ordered by order_idx."""
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT * FROM game_starter_items ORDER BY order_idx ASC, item_id ASC").fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error getting starter items: {e}")
            return []

    def add_or_update_starter_item(self, item_id: int, item_name: str, count: int = 1, order_idx: int = 0, description: str = "") -> bool:
        """Adds or updates a starter item entry."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO game_starter_items (item_id, item_name, count, order_idx, description)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(item_id) DO UPDATE SET
                        item_name = excluded.item_name,
                        count = excluded.count,
                        order_idx = excluded.order_idx,
                        description = excluded.description
                """, (int(item_id), str(item_name), max(1, int(count)), int(order_idx), str(description)))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error saving starter item: {e}")
            return False

    def delete_starter_item(self, item_id: int) -> bool:
        """Deletes a starter item by its item_id."""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM game_starter_items WHERE item_id = ?", (int(item_id),))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error deleting starter item: {e}")
            return False

    def export_starter_items_json(self, file_path: str = "server/data/starter_items.json") -> bool:
        """Exports the active SQLite starter items to JSON."""
        try:
            items = self.get_starter_items()
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            logger.info(f"[DynamicDataManager] Exported {len(items)} starter items to {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error exporting starter items JSON: {e}")
            return False

    def import_starter_items_json(self, file_path: str = "server/data/starter_items.json", clear_existing: bool = True) -> bool:
        """Imports starter items from JSON into the SQLite dynamic database."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"[DynamicDataManager] Starter items JSON not found: {file_path}")
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                items = json.load(f)

            if not isinstance(items, list):
                logger.error(f"[DynamicDataManager] Invalid JSON format in {file_path}")
                return False

            with self.get_connection() as conn:
                if clear_existing:
                    conn.execute("DELETE FROM game_starter_items")

                for idx, it in enumerate(items):
                    conn.execute("""
                        INSERT INTO game_starter_items (item_id, item_name, count, order_idx, description)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(item_id) DO UPDATE SET
                            item_name = excluded.item_name,
                            count = excluded.count,
                            order_idx = excluded.order_idx,
                            description = excluded.description
                    """, (
                        int(it["item_id"]),
                        str(it.get("item_name", f"Item_{it['item_id']}")),
                        int(it.get("count", 1) or 1),
                        int(it.get("order_idx", idx + 1)),
                        str(it.get("description", ""))
                    ))
                conn.commit()

            from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
            GLOBAL_STARTER_PACK_MANAGER.reload_from_db(self)
            logger.info(f"[DynamicDataManager] Successfully imported {len(items)} starter items from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[DynamicDataManager] Error importing starter items JSON: {e}")
            return False

    # --- Live Hot Reload Method ---

    def reload_all_dynamic_data(self):
        """Forces runtime synchronization across all subsystem managers."""
        logger.info("[DynamicDataManager] Executing full live reload across all subsystems...")
        # 1. Battle drops
        from server.battle_engine import GLOBAL_BATTLE_ENGINE
        if hasattr(GLOBAL_BATTLE_ENGINE, "drop_manager"):
            GLOBAL_BATTLE_ENGINE.drop_manager.reload_drops(self)

        # 2. Alchemy
        from server.alchemy_system import GLOBAL_ALCHEMY_MANAGER
        GLOBAL_ALCHEMY_MANAGER.reload_from_db(self)

        # 3. Gathering
        from server.gathering_system import GLOBAL_GATHERING_MANAGER
        GLOBAL_GATHERING_MANAGER.reload_from_db(self)

        # 4. Forging
        from server.forging_system import GLOBAL_FORGING_MANAGER
        GLOBAL_FORGING_MANAGER.reload_from_db(self)

        # 5. Instances
        from server.instance_system import GLOBAL_INSTANCE_MANAGER
        GLOBAL_INSTANCE_MANAGER.reload_from_db(self)

        # 6. Titles
        from server.title_system import GLOBAL_TITLE_MANAGER
        GLOBAL_TITLE_MANAGER.reload_from_db(self)

        # 7. World Map Chests
        from server.chest_system import GLOBAL_CHEST_SYSTEM
        GLOBAL_CHEST_SYSTEM.reload_from_db(self)

        # 8. Tent Crafting Stations
        from server.tent_manufacture import GLOBAL_TENT_MANUFACTURE
        GLOBAL_TENT_MANUFACTURE.reload_from_db(self)

        # 9. Vehicles
        from server.vehicle_system import GLOBAL_VEHICLE_MANAGER
        GLOBAL_VEHICLE_MANAGER.reload_from_db(self)

        # 10. Lucky Draw Mini-games
        from server.minigames_system import GLOBAL_LUCKY_DRAW_MANAGER
        GLOBAL_LUCKY_DRAW_MANAGER.reload_from_db(self)

        # 11. Pet Amity Foods
        from server.pet_amity_system import GLOBAL_PET_AMITY_MANAGER
        GLOBAL_PET_AMITY_MANAGER.reload_from_db(self)

        # 12. Reborn Jobs
        from server.reborn_system import GLOBAL_REBORN_MANAGER
        GLOBAL_REBORN_MANAGER.reload_from_db(self)

        # 13. Sustenance
        from server.sustenance_system import GLOBAL_SUSTENANCE_MANAGER
        GLOBAL_SUSTENANCE_MANAGER.reload_from_db(self)

        # 14. Morphs
        from server.morph_system import GLOBAL_MORPH_MANAGER
        GLOBAL_MORPH_MANAGER.reload_from_db(self)

        # 15. Saddles
        from server.pet_ride_system import GLOBAL_PET_RIDE_MANAGER
        GLOBAL_PET_RIDE_MANAGER.reload_from_db(self)

        # 16. Recycle materials
        from server.recycle_system import GLOBAL_RECYCLE_MANAGER
        GLOBAL_RECYCLE_MANAGER.reload_from_db(self)

        # 17. Death Revive Altars
        from server.death_system import GLOBAL_DEATH_MANAGER
        GLOBAL_DEATH_MANAGER.reload_from_db(self)

        # 18. Weather Engine
        from server.weather_system import GLOBAL_WEATHER_MANAGER
        GLOBAL_WEATHER_MANAGER.reload_from_db(self)

        # 19. Item Mall
        from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
        GLOBAL_ITEM_MALL_MANAGER.reload_from_db(self)

        # 20. Starter Items Pack
        from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
        GLOBAL_STARTER_PACK_MANAGER.reload_from_db(self)

        logger.info("[DynamicDataManager] Full live reload successfully applied across all 20 subsystems.")


GLOBAL_DYNAMIC_DATA = DynamicDataManager()
