# World Entities, NPCs & Map Architecture

This document specifies the world entity management engine, NPC definitions extracted from `eve.Emg`, sprite blinking prevention, waypoint AI patrol, interactive chests, and gathering nodes.

## World Entity Architecture

The Wonderland Online game world spans over 1,119 distinct maps (villages, interiors, fields, dungeons, oceans, and instanced tents). The server manages world entities via `NpcManager` and `QuestNpc` (`server/npc_manager.py`):

```
+-------------------------------------------------------------+
|                         eve.Emg                             |
|         Binary Archive containing 1,119 Maps                |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                     GLOBAL_NPC_MANAGER                      |
|  - Parses 7,545 authentic NPCs & entities                   |
|  - Partitions entities by map_id                            |
|  - Tracks static props, chests, gathering nodes, & monsters |
+--------------+---------------+---------------+--------------+
               |               |               |
               v               v               v
          [Town NPCs]    [Field Monsters]  [Resource Nodes]
          Idle Pacing      Spawn Leash     Respawn Timing
```

## Entity Classifications (`QuestNpc`)

Every entity loaded from `eve.Emg` is categorized based on template ID ranges, keyword patterns, and interactive capabilities:

| Category | Template ID Range | Behavior & Characteristics |
| :--- | :--- | :--- |
| **Human Villagers** | `14000 .. 14999` | Peaceful townspeople, elders, guards, and companions. Client renders native animations locally. |
| **Story & Quest Actors** | `10000 .. 12999`, `15000 .. 16999`| Story companions and quest-giving NPCs. Protected from wild combat triggers. |
| **Service NPCs** | `13000 .. 13999` | Shopkeepers, Props Keepers, Doctors, Bank tellers. Open interaction windows on click. |
| **Wild Hostile Monsters** | `17000 .. 17999` | Roaming monsters on field maps (Spiders, Wolves, Jellyfish). Trigger combat encounters on proximity or click. |
| **Interactive Props** | `19000 .. 24999` | Static furniture, signposts, doors, barrels, and crates. |
| **Resource Gathering Nodes**| `19039` + Keywords | Trees, mines, clay beds, coconut palms. Harvestable with gathering tools. |
| **Treasure Chests** | `19034, 19035, 16006` | Interactive world chests dispensing dynamic loot. |

## Sprite Blinking Prevention Architecture

### The Blinking Phenomenon
In official Wonderland Online clients, map NPCs from `eve.Emg` possess hardcoded client-side walk routines and idle animations. When early custom servers sent periodic `AC 22 Sub 2` movement packets to simulate NPC movement, the client reset the sprite's animation frame to zero every tick, creating a visually jarring continuous flickering/blinking effect.

### Authentic Prevention Strategy
Implemented in `server/npc_manager.py`:
1. **Suppression of Unsolicited Movement Broadcasts**: Static NPCs, villagers, townspeople, and permanent chests never receive `AC 22:2` position broadcasts.
2. **Local Client Simulation Trust**: The client is allowed to simulate NPC patrol cycles autonomously.
3. **Lazy Coordinate Resolution**: Server tracks entity positions using waypoints only when a player initiates an interaction, validating distance checks without broadcasting sprite resets.

## Waypoint Patrol AI

For field NPCs and roaming guards that require authentic movement:
- Each NPC extracts `walksteps` from `eve.Emg` category offset `0`.
- Ticks at random intervals between $3.5\text{s}$ and $7.5\text{s}$ with speed parameter `2`.
- Field monsters adhere to a 60-pixel radius leash from their initial spawn point to prevent migration across zone borders.

## Portal & Warp Point Resolution

Portals are extracted from category offset `6` in `eve.Emg`:
- Contains click ID, destination map ID, and target $(X, Y)$ coordinates.
- **Gray-Code Decoding Fallback**: In certain client revisions, portal IDs transmitted in `AC 20 Sub 2` are Gray-coded:
  ```python
  def _gray_decode(n: int) -> int:
      mask = n
      while mask:
          mask >>= 1
          n ^= mask
      return n
  ```
  If standard portal lookup fails, `handle_20_interaction.py` decodes the portal ID using the Gray transform before re-attempting lookup.

## Interactive Chests & Gathering Nodes

### 1. Permanent Chest Looting (`server/chest_system.py`)
- Players clicking a chest (`AC 20:1`) trigger `ChestSystem.open_chest()`.
- Checks `char_chests` table in SQLite:
  - If record exists: Sends `AC 23 Sub 57` notification ("You have already looted this chest!").
  - If unlooted: Dispenses dynamic items from `DynamicDataManager`, commits record to `char_chests`, and dispatches `AC 22:10 [click_id, 0x01, 0x00]` to render the chest in its opened sprite frame.
  - **Frame Isolation Rule**: Chest open states (`0x01, 0x00`) and prop frame modifications dispatch single-packet `AC 22:10` ONLY. `AC 22:11` scene isolation frames are strictly avoided for non-concealment updates, preventing client engine despawn cascades across surrounding map chests.
  - **Map Sync (`sync_opened_chests_on_map`)**: When entering a map, previously looted permanent chests are synchronized using `AC 22:10 [click_id, 0x01, 0x00]` so unopened chests remain visible and intact.

### 2. Gathering Nodes & Respawn Cycle
- Nodes (e.g. Coconut Palms `19039`, Iron Veins) switch to `is_broken = True` when harvested.
- Broadcasts `AC 22:10 [click_id, state=1, 0]` to visually despawn or fell the tree.
- When `respawn_time` expires (default: 300 seconds), server broadcasts `AC 22:10 [click_id, state=0, 0]` to seamlessly restore the resource.

## Companion & Mount Map Spawning Lifecycle

### 1. Map Spawning Architecture (`spawn_player_companion`)
When a player enters the game world (`commence_login`) or warps between maps (`warp_player`), their active battle companion and riding mount are summoned to the map grid:
- **Battle Companion**: If an active companion (`in_battle = True`) is present in the player's roster:
  1. `AC 19 Sub 4`: Dispatches companion appearance, coordinates, and entity IDs.
  2. `AC 15 Sub 4`: Attaches companion follow state to the player character.
  3. `AC 5 Sub 8`: Synchronizes companion status icon and amity indicator.
- **Riding Mount**: If a pet is set as mounted (`riding = True`):
  1. `AC 15 Sub 16`: Broadcasts mount attachment to the map viewport with pet model ID.
- **Viewport Catch-Up (`spawn_existing_map_players`)**: When a player transitions to a new map, the server renders all companions and mounts for players already present in that map zone.

---

## Dynamic Actor Visibility & Interaction Gating

Certain world entities (quest NPCs, cutscene actors, recruited companions) change visibility dynamically:
- **PreEvent Integration**: [`PreEventInterpreter`](file:///D:/GitHub/Wonderland%20Online/server/preevent_interpreter.py) evaluates bytecode from `eve.Emg` to determine whether an actor should be rendered (`AC 22:10 0x00 0x00`) or hidden (`AC 22:10 0xFF 0xFF`).
- **Delta Optimization**: Redundant show packets to static props and chests are suppressed to avoid sprite animation frame resets.
- **Client Interaction Gating**: [`handle_20_interaction.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_20_interaction.py) verifies `is_npc_visible_to_player` prior to processing click events. Clicks on hidden entities are rejected with despawn confirmation and interface release (`AC 20:8`).

