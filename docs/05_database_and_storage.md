# Database Schema & Data Persistence

This document details the SQLite data architecture, table schemas, JSON serialization structures, and dynamic data management mechanisms.

## Database Overview

Wonderland Online Server utilizes two decoupled SQLite databases:
1. **`wlo_server.db` (Runtime Store)**: Stores dynamic player state, user accounts, character inventory, bank storage, guild rosters, marriage registries, and security tables.
2. **`ServerDataBase.db` (Static Game Store)**: Holds static NPC definitions, portal coordinates, map names, and base monster templates extracted from official game archives.

## Table Schemas (`wlo_server.db`)

### 1. `users` Table
Stores player account authentication and permission details.

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(32) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    banned INTEGER DEFAULT 0,
    ban_reason TEXT DEFAULT '',
    is_admin INTEGER DEFAULT 0
);
```

### 2. `characters` Table
Main character state table with embedded JSON columns for complex structures:

```sql
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    name VARCHAR(32) UNIQUE NOT NULL,
    level INTEGER DEFAULT 1,
    element INTEGER DEFAULT 0,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    sp INTEGER DEFAULT 100,
    max_sp INTEGER DEFAULT 100,
    gold INTEGER DEFAULT 0,
    map_id INTEGER DEFAULT 10017,
    x INTEGER DEFAULT 1042,
    y INTEGER DEFAULT 1075,
    body INTEGER DEFAULT 1,
    head INTEGER DEFAULT 1,
    hair_color INTEGER DEFAULT 0,
    skin_color INTEGER DEFAULT 0,
    clothing_color INTEGER DEFAULT 0,
    eye_color INTEGER DEFAULT 0,
    reborn INTEGER DEFAULT 0,
    job INTEGER DEFAULT 0,
    str_val INTEGER DEFAULT 10,
    con_val INTEGER DEFAULT 10,
    int_val INTEGER DEFAULT 10,
    wis_val INTEGER DEFAULT 10,
    agi_val INTEGER DEFAULT 10,
    points INTEGER DEFAULT 0,
    potential INTEGER DEFAULT 0,
    inventory TEXT DEFAULT '[]',   -- JSON list of items
    equipments TEXT DEFAULT '[]',  -- JSON list of 6 equipped item IDs
    skills TEXT DEFAULT '[]',      -- JSON list of skill dictionaries
    quests TEXT DEFAULT '[]',      -- JSON list of quest progress dictionaries
    pets TEXT DEFAULT '[]',        -- JSON list of active companions
    bank_gold INTEGER DEFAULT 0,
    im_points INTEGER DEFAULT 5000,
    im_bonus_points INTEGER DEFAULT 1000,
    im_tokens INTEGER DEFAULT 50,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 3. `char_chests` Table
Tracks world map interactive chests opened by each character to guarantee permanent one-time looting:

```sql
CREATE TABLE IF NOT EXISTS char_chests (
    char_id INTEGER NOT NULL,
    map_id INTEGER NOT NULL,
    click_id INTEGER NOT NULL,
    opened_at REAL NOT NULL,
    PRIMARY KEY (char_id, map_id, click_id)
);
```

### 4. `guilds` Table
Guild management and shared item storage:

```sql
CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_name VARCHAR(50) UNIQUE NOT NULL,
    leader_id INTEGER NOT NULL,
    leader_name VARCHAR(50) NOT NULL,
    icon INTEGER DEFAULT 3402,
    rules TEXT DEFAULT '',
    storage TEXT DEFAULT '[]',
    created_at REAL NOT NULL
);
```

### 5. `charmarriage` Table
Tracks relationship pairings and wedding timestamps:

```sql
CREATE TABLE IF NOT EXISTS charmarriage (
    husband_id INTEGER PRIMARY KEY,
    husband_name VARCHAR(50) NOT NULL,
    wife_id INTEGER NOT NULL UNIQUE,
    wife_name VARCHAR(50) NOT NULL,
    marriage_date REAL NOT NULL
);
```

### 6. `charmail` Table
Asynchronous offline mail with parcel delivery:

```sql
CREATE TABLE IF NOT EXISTS charmail (
    mail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    sender_name VARCHAR(50) NOT NULL,
    receiver_id INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    body TEXT NOT NULL,
    gold INTEGER DEFAULT 0,
    item_id INTEGER DEFAULT 0,
    item_count INTEGER DEFAULT 0,
    is_read INTEGER DEFAULT 0,
    claimed INTEGER DEFAULT 0,
    sent_at REAL NOT NULL
);
```

### 7. Security Tables (`banned_ips` & `banned_users`)
Network firewall and administrative restriction tables:

```sql
CREATE TABLE IF NOT EXISTS banned_ips (
    ip VARCHAR(45) PRIMARY KEY,
    reason TEXT DEFAULT '',
    banned_at REAL,
    banned_by VARCHAR(50) DEFAULT 'admin'
);

CREATE TABLE IF NOT EXISTS banned_users (
    user_id INTEGER PRIMARY KEY,
    reason TEXT DEFAULT '',
    banned_at REAL
);
```

## JSON Column Serialization Formats

### 1. `inventory` Format
Array of item dictionaries:
```json
[
  { "slot": 1, "item_id": 27001, "amount": 50, "damage": 0 },
  { "slot": 2, "item_id": 48030, "amount": 1, "damage": 0 }
]
```

### 2. `skills` Format
Array of skill records:
```json
[
  { "skill_id": 15003, "grade": 1, "exp": 0 },
  { "skill_id": 11075, "grade": 5, "exp": 450 }
]
```

### 3. `pets` Format
Array of companion records:
```json
[
  {
    "pet_id": 11058,
    "name": "Shasha",
    "level": 15,
    "exp": 1250,
    "hp": 450,
    "max_hp": 450,
    "sp": 300,
    "max_sp": 300,
    "amity": 85,
    "slot": 1
  }
]
```

## Dynamic Data Engine (`DynamicDataManager`)

The `server/dynamic_data_manager.py` module acts as a central registry for game rules, allowing administrators to modify configurations via the Desktop GUI and execute instant hot-reloads without disconnecting players or restarting the server.

### 20 Dynamically Reloaded Subsystems:
1. **Monster Drops**: Monster drop tables and probability rates (`drop_table`).
2. **Alchemy Synthesis**: Material mixing and compound tiers (`alchemy_recipes`).
3. **AFK Gathering**: Fishing, Mining, and Woodcutting loot tables (`gathering_pools`).
4. **Forging & Sockets**: Equipment spar crystal slotting rules (`forging_materials`).
5. **Party Instances**: Multi-stage dungeon configurations (`instances`).
6. **Player Titles**: Passive achievement stat buffs (`titles`).
7. **Treasure Chests**: Map chest loot mappings (`map_chests`).
8. **Tent Crafting**: Furniture and workbench recipes (`tent_recipes`).
9. **Vehicles**: Ship and aircraft speed/fuel parameters (`vehicles`).
10. **Lucky Draw**: Wheel prize pool and weight factors (`lucky_draw_prizes`).
11. **Pet Food**: Companion amity gain foods (`pet_foods`).
12. **Reborn Jobs**: Capes, stat multipliers, and reborn requirements (`reborn_jobs`).
13. **Sustenance Items**: Rice Ball HP/SP auto-refill buffers (`sustenance_items`).
14. **Morph Masks**: Disguise transformation timers (`morph_items`).
15. **Saddles**: Mount speed modifiers (`saddles`).
16. **Recycling**: Smelting furnace salvage rates (`recycle_recipes`).
17. **Revive Altars**: Sacred respawn coordinates on player death (`revive_altars`).
18. **Weather Engine**: Atmospheric effects per map (`map_weather`).
19. **Item Mall**: Points Mall and Bonus Mall item catalogs (`item_mall_catalog`).
20. **Starter Packs**: Beginner gift item bundles (`starter_items`).
