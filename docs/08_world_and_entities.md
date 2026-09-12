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
  - If unlooted: Dispenses dynamic items from `DynamicDataManager`, commits record to `char_chests`, and broadcasts `AC 22:10` to render the chest as permanently opened for the player.

### 2. Gathering Nodes & Respawn Cycle
- Nodes (e.g. Coconut Palms `19039`, Iron Veins) switch to `is_broken = True` when harvested.
- Broadcasts `AC 22:10 [click_id, state=1, 0]` to visually despawn or fell the tree.
- When `respawn_time` expires (default: 300 seconds), server broadcasts `AC 22:10 [click_id, state=0, 0]` to seamlessly restore the resource.
