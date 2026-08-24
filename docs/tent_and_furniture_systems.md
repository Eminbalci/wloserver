# Tent and Furniture Systems Technical Documentation

## 1. Overview
The Wonderland Online Tent System provides each player with a private instanced interior space (`MapID = 12000` or `100000 + CharID`), customized furniture layouts, world map pitching, and interactive crafting stations. Ported directly from the C# server (`wlo.pserver.core/Game/PlayerRelated/Tent` and `Game/Crafting/TentManufactureManager`).

---

## 2. Core Architecture (`server/tent.py`)

### `TentItem`
- `item_id`: Item ID of the furniture (e.g., `38027` Coconut Basin, `38049` Work Platform, beds, rugs).
- `x`: X grid position inside the tent.
- `y`: Y grid position inside the tent.
- `floor`: Floor index (`0` for 1st Floor, `1` for 2nd Floor).
- `rotate`: Orientation angle (`0`..`3`).

### Starter Default Items
Every newly created tent automatically receives:
- **Coconut Basin (`38027`)** placed at `(43, 42)`.
- **Low Workbench (`38049`)** placed at `(45, 42)`.

---

## 3. Database Schema (`chartent` & `chartent_items`)

### `chartent`
```sql
CREATE TABLE IF NOT EXISTS chartent (
    charID INTEGER PRIMARY KEY,
    locked INTEGER DEFAULT 0,
    enlarged INTEGER DEFAULT 0,
    tenttype INTEGER DEFAULT 1115,
    floor1Color INTEGER DEFAULT 39062,
    floor1wallpaper INTEGER DEFAULT 39064,
    floor2Color INTEGER DEFAULT 0,
    floor2wallpaperr INTEGER DEFAULT 0
);
```

### `chartent_items`
```sql
CREATE TABLE IF NOT EXISTS chartent_items (
    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
    charID INTEGER NOT NULL,
    itemID INTEGER NOT NULL,
    posX INTEGER NOT NULL,
    posY INTEGER NOT NULL,
    floor INTEGER DEFAULT 0,
    rotate INTEGER DEFAULT 0
);
```

---

## 4. Network Protocol Specifications

### World Pitching & Despawning (AC 23:15, AC 65:1, AC 65:2)
- **Pitching Tent (AC 23 Sub 15)**: When a player uses a tent item in inventory, the server broadcasts `AC 65 Sub 1` to all players on the current map:
  - Format: `[65, 1, char_id (4B), x (2B), y (2B), 0 (2B), tent_skin_id (4B: 1115), 0 (4B)]`
- **Packing Up Tent (AC 65 Sub 2)**: Right-clicking and packing up the tent broadcasts `[65, 2, char_id (4B)]` to remove the tent visual from the map.

### Entering & Exiting the Tent (AC 62:61, AC 65:1, AC 65:3)
- **Entering Tent Interior (AC 62 Sub 61 / AC 65 Sub 1)**:
  1. `AC 12 Sub 163`: Interior warp packet `[12, 163, char_id (4B), 12000 (2B), 400 (2B), 400 (2B), 0 (4B)]`.
  2. `AC 62 Sub 7`: Tent styling properties `[62, 7, 0, 0]`.
  3. `AC 23 Sub 3`: Furniture items layout packet for every placed item:
     - Format: `[23, 3, item_id (2B), x (4B), y (4B), floor (4B), 1 (1B), rotate (1B), 0 (2B)]`.
  4. `AC 62 Sub 4`: Furniture count header `[62, 4, char_id (4B), count (2B), ...]`.
  5. `AC 62 Sub 59`: Interior BGM `[62, 59, 257 (2B), 0 (4B), "BGM0011"]`.
  6. `AC 65 Sub 7`: Status flag `[65, 7, 0]`.
  7. `AC 23:102` and `AC 20:8`: Interface release signals.
- **Exiting Tent (AC 65 Sub 3)**:
  - Warps the player back to recorded outside coordinates (`orig_map_id`, `orig_x`, `orig_y`) and saves tent layout.

### Furniture Placement & Movement (AC 62 Sub 1, AC 62 Sub 3)
- **Placing Furniture (AC 62 Sub 1)**:
  - Client sends: `[62, 1, bag (1B), slot (1B), x (4B), y (4B), floor (4B)]`.
  - Server removes 1 item from inventory slot, creates `TentItem`, saves to database, and responds with `[62, 1, 1]`, updated AC 23:3 layout, and updated inventory.
- **Moving / Rotating Furniture (AC 62 Sub 3)**:
  - Client sends: `[62, 3, item_index (2B), x (4B), y (4B), floor (4B), rotate (1B)]`.
  - Server updates item coordinates/rotation in DB, echoes `[62, 3, ...]`, and refreshes AC 23:3 layout.

---

## 5. Manufacturing & Crafting Stations (`server/tent_manufacture.py`, AC 64)
Provides manufacturing recipe execution for tent workbenches (Forge, Anvil, Loom, Sewing Machine, Kiln, Potting, Kitchen Stove, Coconut Basin, Low Workbench):
- Material validation and consumption.
- Progress bar and animation: `AC 64 Sub 1` & `AC 64 Sub 10` timer.
- Crafting sparkle animation (`AC 5 Sub 5: 60018`).
- Success confirmation (`AC 64 Sub 2: 1`) and inventory delivery.
