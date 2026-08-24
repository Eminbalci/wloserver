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
  - Dispatches `AC 75 Sub 1` with count (uint16) and 10 bytes per entry:
    `[item_id(2B), flag=0(1B), point_cost(2B), tag=1(1B), category_id(1B), subcat=1(1B), stock=999(2B)]`.
  - Dispatches `AC 75 Sub 3` with user points.
- **Sub 4 & Sub 5 (Category Switch)**:
  - Client sends `[75, sub, category_id]`.
  - Server replies with `AC 57 Sub 1` category ACK: `[57, 1, category_id, 0, 0, 0]` and re-sends catalog.
- **Sub 4 & Sub 5 (Item Purchase)**:
  - Client sends `[75, sub, item_id (2 bytes), quantity (1 byte)]`.
  - Server deducts points, grants inventory item, sends inventory update (`AC 23`), sends `AC 75 Sub 3` point update, and sends authentic buy response:
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
