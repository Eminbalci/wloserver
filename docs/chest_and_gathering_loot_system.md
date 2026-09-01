# Dynamic Treasure Chests & Gathering Node Loot System

## Overview
Ported 1:1 from C# `wlo.pserver.core/Game/Maps/ChestDropManager.cs` and `wlo.pserver.core/Game/Maps/Code/QuestNpc.cs`.
Provides dynamic world treasure chest looting, gathering node harvesting (coconut trees, ores, wood), authentic 3-stage item delivery to bag, open animations via `AC 22 Sub 1`, and persistence via SQLite `charchests` and `game_chest_pools`.

## Protocol & Packet Flow
1. **Interaction Initiation (`AC 20 Sub 1`)**:
   - Player clicks static chest or gathering prop (template `>= 19000` or classified as static prop).
   - If node is currently broken/empty:
     - Sends `AC 23 Sub 57` ("This node/chest is currently empty and will respawn soon.").
     - Sends `AC 20 Sub 8` + `AC 5 Sub 4` dialog close packets.
2. **Chest Opening & 3-Stage Loot Delivery**:
   - Dispatches `AC 22 Sub 1` (`[22, 1, click_id (2B), 1 (1B)]`) open animation to clicking player and broadcasts to map players.
   - Sets `npc.is_broken = True` and sets `npc.respawn_time = time.time() + 60.0`.
   - Executes atomic `server.grant_item(player, item_id, count)`:
     1. **`AC 23 Sub 6` (Item Acquisition Notification)**: `[23, 6, item_id (4B_LE), amount (1B), 26 zeros]`. Renders the client-side item sprite pop-up and sound.
     2. **`AC 23 Sub 8` (Slot Delta Update)**: `[23, 8, slot (1B), item_id (2B_LE), amount (1B), damage (1B), 24 zeros]`. Updates the specific inventory slot.
     3. **`AC 23 Sub 5` (Full Inventory Sync)**: 1452-byte serialized state of all 50 slots.
   - Dispatches `AC 23 Sub 57` ("Obtained {item_name}!") and `AC 20 Sub 10` (fanfare sound effect).
   - Closes dialog interaction with `AC 20 Sub 8` and `AC 5 Sub 4`.
   - Persists updated inventory and character state to SQLite database immediately.

## Dynamic Respawn & Node Harvesting
- Nodes and chests store `opened_at` timestamp in SQLite `charchests`.
- If `(current_time - opened_at) >= default_respawn_seconds` (60s), the node automatically unlocks and becomes harvestable again.
- Eve Opcode 1 chests executed via `GLOBAL_EVE_INTERPRETER` also utilize `server.grant_item()` for atomic visual and database synchronization.
