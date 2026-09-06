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
- **Permanent Treasure Chests**:
  - Permanently recorded in SQLite `charchests` with `(char_id, map_id, chest_id)`.
  - Once looted, clicking the chest returns prompt `AC 23 Sub 57` ("You have already claimed this treasure.") and closes interaction (`AC 20:8`, `AC 5:4`).
  - No items or animations are ever re-triggered.
  - On map entry (`handle_login` and `warp_player`), the server calls `GLOBAL_CHEST_SYSTEM.sync_opened_chests_on_map(session, map_id)` to dispatch `AC 22 Sub 10` (`[22, 10, chest_id (2B_LE), 0xFF, 0xFF]`), rendering already-looted chests open/broken immediately on the client's screen.
- **Recurring Gathering Nodes** (Coconuts, Wood, Ore):
  - Stored with `opened_at` timestamp.
  - If `(current_time - opened_at) >= default_respawn_seconds` (60s), the node unlocks and becomes harvestable again.
  - While broken/empty, clicks prompt "This node/chest is currently empty and will respawn soon." and unlock client without item grants.

## Inventory Drag, Move & Swap Protocol (AC 23 Sub 10)
- **C2S Request**: `[23, 10, src_slot (1B), amount (1B), dst_slot (1B)]`.
- **Server Mechanics**:
  1. **Move to Empty Slot**: Updates `src_item['slot'] = dst` (or splits stack if `amount < total`), confirmed with `[23, 10, src, amount, dst]`.
  2. **Stack to Same Item**: Increments `dst_item['amount']` and decrements/removes `src_item`, confirmed with `[23, 10, src, amount, dst]`.
  3. **Slot Swap**: When dragging onto an occupied slot with a different item, swaps `src_item['slot'] = dst` and `dst_item['slot'] = src`, preserving all item data with zero loss, confirmed with `[23, 10, src, amount, dst]`.
  4. **Desync Auto-Healing**: If `src_item` is empty on the server, server immediately sends full inventory packet `AC 23 Sub 5` to re-sync the client's UI to the database.
