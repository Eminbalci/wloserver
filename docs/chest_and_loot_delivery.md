# Wonderland Online - Chest Loot & Item Delivery Protocol

## Overview
This document specifies the server-client interaction protocol for looting world chests, gathering nodes, and event-based item rewards.

## Protocol Flow

### 1. Interaction Initiation
- Client sends `AC 20 Sub 1` (`[20, 1, 0, 0, 0, click_id]` or `[20, 1, click_id]`).
- Server validates distance ($d \le 169\text{ px}$) and checks for active event script in `eve.Emg`.

### 2. Item Grant & Serialization
- Server executes item addition via `add_item_to_inventory(session, item_id, count)`.
- Server sends:
  1. `AC 23 Sub 57`: System notification text prompt (`[23, 57, 0, "Obtained <item_name>!"]`).
  2. `AC 20 Sub 10`: Treasure Fanfare audio trigger (`[20, 10]`).
  3. `AC 23 Sub 5`: Full 50-slot serialized inventory array (`1452 bytes`).
  4. `AC 22 Sub 1`: Object state change animation (`[22, 1, click_id (2B_LE), 1]`).

### 3. Immediate Interaction Lock Release
- If the event sequence contains **no further dialogue steps**, the server immediately releases the client interaction lock:
  1. `AC 20 Sub 8`: Closes modal dialogue state (`[20, 8]`).
  2. `AC 5 Sub 4`: Unfreezes player movement and restores controls (`[5, 4]`).
- This allows the client's inventory UI to immediately process and render the new item without hanging in a modal state.
