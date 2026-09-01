# Mini-Games & Item Mall Systems & Server Branding Configuration

This document outlines the complete network protocol and synchronization flow for the **Item Mall (Nesne Market)**, **Server Branding (Mamiletta / Custom Server Name)** configuration, and **Lucky Draw (Lucky Wheel)** mini-game systems.

---

## 1. Server Branding & Server Name Configuration (Mamiletta)

The server name (default: `Mamiletta`) is transmitted to client during initial connection handshake (**Opcode 0 -> Opcode 1 Subcode 9**).

### A. Live Configuration via Graphical Interface (GUI)
1. **Desktop GUI (Dashboard Tab & Global Settings Tab)**:
   - **Dashboard (Tab 1)**: Features a dedicated `Server Name / Brand` input field and `💾 Save Server Name (Brand)` button. Updating this changes `GameServer.SERVER_VERSION` in real-time and persists the value into SQLite `server_config` table.
   - **Global Settings (Tab 13)**: Features `Server Name / Brand (AC 0)` in the settings editor. Clicking `💾 Save Settings & Apply Live` updates and hot-reloads the name across all active handlers and database.
2. **Database Persistence**:
   - Table: `server_config` (`key TEXT PRIMARY KEY`, `value TEXT`).
   - Row: `('server_name', '<custom_name>')`.

### B. Network Handshake Dispatch
- When a client connects and sends **AC 0**:
  - Server sends **AC 1 Sub 9**: `[1, 9, 101, 0, 1, len, server_name_bytes]`.
  - Server sends **AC 54 Sub 201**: Authentic Item Mall category matrix `[54, 201, 0, 1, 101, 0, 3, 103, 0, 2, 104, 0, 3, 102, 0, 3]`.
  - Server sends **AC 54 Sub 29**: Sub-server configuration bytes.

---

## 2. Item Mall System Network Protocol Parity

Wonderland Online clients open and interact with the Item Mall across several network action codes matching the C# reference server (`Src/Network/ActionCodes/` and `wlo.pserver.core/Game/PlayerRelated/ItemMallManager.cs`):

### A. Top-Right HUD Item Mall Button Click (Action Code 13)
- **Client Request**: `AC 13 Sub 238` (`[13, 238]`).
- **Server Responses**:
  1. `AC 13 Sub 42`: `[13, 42, char_id (4 bytes)]` — confirms HUD button click query.
  2. `AC 75 Sub 3`: `[75, 3, im_points (2 bytes)]` — syncs IM points balance.
  3. `AC 75 Sub 1`: Catalog packet containing all catalog entries (10 bytes per item).

### B. In-Game Shopping Mall & Cart Checkout (Action Code 34)
- **Mode 0 (Open / Query Balance)**:
  - `Client -> Server`: `[34, 1, 0]`.
  - `Server -> Client`:
    1. `AC 34 Sub 1`: `[34, 1, points (uint16)]`.
    2. `AC 75 Sub 1`: Full catalog entries.
    3. `AC 75 Sub 3`: Point balance.
- **Mode >= 1 (Shopping Cart Checkout)**:
  - `Client -> Server`: `[34, 1, slot_mode]`.
  - `Server -> Client`:
    1. Deducts points and adds items to player inventory.
    2. Sends inventory update packet (**AC 23**).
    3. `AC 34 Sub 1`: `[34, 1, remaining_points (uint16)]`.
    4. `AC 75 Sub 3`: `[75, 3, remaining_points (uint16)]`.
    5. `AC 35 Sub 4`: Cart clearance confirmation (16 zero bytes).
    6. `AC 75 Sub 1`: Catalog sync.

### C. Category Switch & Direct Purchase (Action Code 75)
- **Sub 1 (Catalog Request)**:
  - Dispatches `AC 75 Sub 1` with count (uint16_LE) and 10 bytes per catalog entry (`<HBHBBBH`):
    - `[0-1] item_id` (uint16_LE): In-game Item ID.
    - `[2]   subcat_id` (uint8): Subcategory ID (default 1).
    - `[3-4] base_price` (uint16_LE): Base price displayed at `POINTS`.
    - `[5]   discount_percent` (uint8): **100 = 100% of price (No strike-through, regular price)**; `<100` = Sale percentage (triggers red strike-through and calculates `discount_percent * price / 100` for `On Sale`).
    - `[6]   badge_tag` (uint8): Badge overlay (**1 = NEW starburst badge, 2 = HOT badge, 0 = Normal**).
    - `[7]   category_id` (uint8): Category ID (**1=Hot, 2=Armory, 3=Weaponry, 4=Grocery, 5=Furniture, 6=Slot Machine, 7=Forging Room**).
    - `[8-9] price` (uint16_LE): Actual point cost / price.
- **Sub 3 (Points Balance)**:
  - `[75, 3, im_points(uint32_LE), extra(uint32_LE), item_id(uint16_LE), count(uint8)]` (13 bytes total).
- **Sub 4 / 5 (Category Switch)**:
  - `Client -> Server`: `[75, 4, category_id]`.
  - `Server -> Client`: `AC 57 Sub 1` ACK `[57, 1, category_id, 0, 0, 0]`, `AC 34 Sub 1` balance, `AC 75 Sub 3` balance, and `AC 75 Sub 1` catalog.
- **Sub 4 & Sub 5 (Item Purchase)**:
  - Client sends `[75, sub, item_id (2 bytes), quantity (1 byte)]`.
  - Server deducts points (`point_cost * quantity`), grants inventory item (`count * quantity`), sends inventory update (`AC 23`), sends `AC 75 Sub 3` point update, and sends authentic buy response:
    `S->C [75, sub, remaining_points (4B), spent_points (4B), item_id (2B), quantity (1B)]`.

### D. Native Form GUI (Action Code 21)
- **Sub 1 (Open Native Mall Window)**:
  - Server sends `AC 75:3` points balance and `AC 21:1 [21, 1, 1, 2, 3, ... 21]`.
- **Sub 2 (Buy from Slot)**:
  - Server executes item purchase for slot item.

### E. Inventory & State Sync (Action Code 23)
- **Sub 25**: Points balance query -> sends `AC 75:3`.
- **Sub 26**: Item purchase -> calls `GLOBAL_ITEM_MALL_MANAGER.purchase_item`.
- **Sub 54**: Warp / map enter ACK -> sends `AC 75:1` catalog and `AC 75:3` points balance.
- **Sub 77**: Request player stall / market -> sends empty stall response `[23, 4, 0]` and `[23, 102]`.

### F. Dedicated TCP Port 6416 Service
- Standalone TCP daemon listening on port 6416.
- On connection, transmits `[0xC9, 0x00, 0x01, ... [ItemID(2B_LE), HotFlag(1B)] ...]` binary payload and closes the socket.

---

## 3. Lucky Draw (Lucky Wheel) System (Opcode 104)

The Lucky Draw system allows players to spin a prize wheel for rewards.

### A. Spin Requests (Sub-opcode 1)
When the client requests a spin:
1. **Inventory Space Validation**: Checks if the player has at least 1 free slot in their inventory. If full, cancels spin and returns alert: `"Inventory full. Cannot use Lucky Draw."`.
2. **Prize Selection**: Randomly selects a reward from the prize pool.

### B. Prize Mappings & Categories
| Item Name | Item ID | Category | Index | Description |
|---|---|---|---|---|
| **Holy Water** | `100653` | `5` | `1` | Common consumable |
| **Tear of Angel** | `100652` | `5` | `2` | Common consumable |
| **Tear of Angel** | `100652` | `4` | `3` | Alternative tier reward |
| **UFO** | `48013` | `3` | `4` | **Jackpot Mount!** |
| **Memory Card** | `100651` | `2` | `5` | Rare consumable |

### C. Spin Result Packets
1. **Item Delivery Packet (Opcode 23, Sub-opcode 6)**: `[23, 6, item_id (4B), quantity (1B), padding (26B)]`.
2. **Lucky Draw Stop Packet (Opcode 104, Sub-opcode 1)**: `[104, 1, 2, category (1B), index (1B)]`.

### D. Jackpot Broadcast
Winning UFO (`48013`) triggers a map-wide announcement: `[23, 57, 0, "Congratulations! {player_name} won a UFO from Lucky Draw!"]`.

---

## 4. Mini-Game Window, Gameplay & Point Synchronization Protocol (Claw Machine / UFO Catcher / Slot Machine)

In Wonderland Online, mini-game forms (`MiniGame_DigHole_Form` / Claw Machine #20, `Doll_Exp_Form` #7, `Boxing_Exp_Form` #9, `TrunEgg_Exp_Form` #22, `Slotmach_Exp_Form` #19) operate through a coordinated packet protocol:

### A. Point Balance & Form Initialization
- When entering the mini-game (via Category 6 "Slot Machine" or props), client initializes points struct offset `+0x70` / `+0x50` to `-1` (`0xffffffff`).
- The client requests / expects active point balances:
  - **`AC 34 Sub 1`**: `[34, 1, points(uint32_LE)]` (updates internal point register).
  - **`AC 75 Sub 3`**: `[75, 3, points(uint32_LE)]` (updates GUI point balance indicator).
- The server automatically dispatches both packets upon switching to Category 6, entering maps, or opening minigames.

### B. Mini-Game Exit & Window Dismissal (Action Code 57)
- When clicking the red **Exit** button (`btn_close_s_1` / `btn_Leave_1`) in the bottom-right corner of the mini-game interface, the client sends:
  - **`Client -> Server`**: `AC 57 Sub 1` (`[57, 1, category_id = 0]`).
- **`Server -> Client` Response Sequence**:
  1. `AC 57 Sub 1 ACK`: `[57, 1, category_id, 0, 0, 0]`.
  2. `AC 34 Sub 1`: `[34, 1, points(uint32_LE)]`.
  3. `AC 75 Sub 3`: `[75, 3, points(uint32_LE)]` balance sync.
  4. **CRITICAL**: Server **does not** send `AC 75 Sub 1` (Catalog) on `category_id == 0`, preventing the client from endlessly reopening the "Game explanation" form after closing.
  5. `AC 5 Sub 4`: Unfreeze and restore player HUD / movement controls.
- This immediately dismisses the mini-game UI and returns the player to the normal game / world state.

### C. Mini-Game Play & Prize Protocol (Action Code 71)
- When the player starts the minigame or grabs a prize, the client sends:
  - **`Client -> Server`**: `AC 71 Sub [minigame_id]` (e.g., `[71, 20, 0]` for Claw Crane).
- **Server Execution**:
  1. Validates player has at least **20 IM Points**.
  2. If sufficient:
     - Deducts 20 IM Points.
     - Sends `AC 34:1` and `AC 75:3` points balance updates (`uint32_LE`).
     - Sends **`AC 71 Sub 1 [1]`** (Start Game / Permission Granted).
     - Rolls random prize from database prize pool, grants item into inventory (`server.grant_item`).
     - Sends **`AC 71 Sub 2`**: `[71, 2, item_id(uint32_LE), count(uint8)]`.
  3. If insufficient points:
     - Sends **`AC 71 Sub 1 [2]`** (Not Enough Points error code).
     - Syncs point balance via `AC 75:3`.

