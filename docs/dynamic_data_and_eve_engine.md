# Wonderland Online - Dynamic Data Engine & `eve.Emg` Binary Loader

## 1. Overview
The Wonderland Online server integrates a purely data-driven, zero-hardcoding dynamic configuration architecture. All game mechanics (monster item drops, quests, crafting recipes, alchemy compounding formulas, world map chests, gathering resource nodes, forging gems, instances, and player titles) are stored in queryable SQLite database tables and can be loaded directly from authentic client binary files (`eve.Emg`, `Mark.dat`, `Compound.dat`, `PlayerTitleData.txt`).

---

## 2. Dynamic Database Schema Reference (20 Dynamic Subsystems)

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| **`game_monster_drops`** | Dynamic monster battle item drop tables | `monster_id`, `item_id`, `item_name`, `drop_rate` (1-10000), `min_count`, `max_count`, `quest_only` |
| **`game_crafting_recipes`** | Worktable, forge, loom, kitchen, and furnace recipes | `station_type`, `output_item_id`, `output_name`, `output_count`, `required_materials` (JSON), `craft_time_sec` |
| **`game_alchemy_recipes`** | Multi-tier alchemy synthesis combinations | `input_items` (JSON), `output_item_id`, `output_name`, `base_rate`, `min_tier` (1: Primary, 2: Junior, 3: Senior) |
| **`game_chest_pools`** | World map interactive treasure chests | `map_id`, `chest_id`, `item_id`, `item_name`, `count`, `weight`, `required_key_id` |
| **`game_gathering_pools`** | Fishing, mining, and woodcutting resource pools | `gather_type` (1: Fishing, 2: Mining, 3: Woodcutting), `map_id`, `item_id`, `item_name`, `weight` |
| **`game_forging_materials`** | Spar gems and sockets | `material_id`, `name`, `stat_boosts` (JSON), `success_rate` |
| **`game_instances`** | Multi-stage party dungeons | `instance_id`, `name`, `min_level`, `map_id`, `total_rooms`, `reward_gold`, `reward_exp`, `reward_item_id` |
| **`game_titles`** | Player titles and achievement buffs | `title_id`, `title_name`, `description`, `stat_bonuses` (JSON) |
| **`game_vehicles`** | Land, sea, and air vehicle templates and speeds | `vehicle_id`, `name`, `speed_mult`, `sea_only`, `air_only`, `land_only` |
| **`game_luckydraw_prizes`** | Lucky Draw Wheel prize weights and jackpots | `prize_id`, `item_id`, `item_name`, `count`, `weight`, `is_jackpot` |
| **`game_pet_foods`** | Companion pet amity restoration foods | `item_id`, `name`, `amity_gain`, `min_amity`, `max_amity` |
| **`game_reborn_jobs`** | Rebirth 6 advanced job classes and stat multipliers | `job_type`, `job_name`, `min_level`, `cape_item_id`, `atk_mult`, `def_mult`, `spd_mult`, etc. |
| **`game_sustenance_items`** | Auto-recovery Rice Ball and potion HP/SP buffers | `item_id`, `name`, `hp_buffer`, `sp_buffer` |
| **`game_morph_items`** | Monster disguise morphs, durations, and combat buffs | `item_id`, `morph_npc_id`, `name`, `duration_sec`, `stat_bonuses` (JSON) |
| **`game_saddles`** | Pet mount saddles and movement speed multipliers | `item_id`, `name`, `speed_mult`, `required_pet_level` |
| **`game_recycle_materials`** | Smelting furnace dismantled raw material yields | `material_id`, `name`, `weight` |
| **`game_revive_altars`** | Sacred altar respawns and EXP penalty per map | `map_id`, `respawn_map_id`, `respawn_x`, `respawn_y`, `exp_loss_percent` |
| **`game_map_weather`** | Environmental weather type and intensity per map | `map_id`, `weather_type` (Rain, Snow, Sakura, Fog, Storm), `intensity` |
| **`game_npc_visibility`** | Conditional NPC visibility and quest dependencies | `map_id`, `click_id`, `npc_id`, `default_visible`, `required_quest_id`, `hide_if_quest_completed` |
| **`game_item_mall`** | Item Mall in-game store catalog & pricing | `item_id`, `item_name`, `category`, `point_cost`, `gold_cost`, `count`, `is_hot`, `stock` |

---

## 3. Authentic `eve.Emg` Binary Parser ([`server/eve_loader.py`](file:///d:/GitHub/Wonderland%20Online/server/eve_loader.py))

Ported 1:1 from C# [`wlo.pserver.core/DataFiles/EveLoader.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/DataFiles/EveLoader.cs), the binary parser parses all 1,119 Wonderland Online maps across 11 category offsets:

1. **Header & Map Index**: Reads `entrylen` (1,119 maps) and maps each to `data_ptr` and `data_len`.
2. **Category Offsets** (44 bytes trailer):
   - `NPC` (Offset 0): All static and dynamic NPCs with walking patterns.
   - `Entry` (Offset 4): Map entry/exit spawn points.
   - `Mining` (Offset 8): Authentic fishing/mining/woodcutting resource coordinates.
   - `Items` (Offset 12): World map treasure chests and interactive ground items.
   - `Events` (Offset 16): Bytecode event scripts (dialogues, choices, shops, quests).
   - `Groups` (Offset 20): Monster encounter battle formations.
   - `Warp` (Offset 24): Map transition portals (`dst_map`, `dst_x`, `dst_y`).
   - `Interactiveinfo` (Offset 28): Interactive objects.
   - `Battleinfo` (Offset 32): Extended combat metadata.
   - `PreEvent` (Offset 36): Player-state dependent NPC visibility conditions.
   - `groupext` (Offset 40): Extended monster groups.

---

## 4. EveEventInterpreter Bytecode Engine ([`server/eve_event_interpreter.py`](file:///d:/GitHub/Wonderland%20Online/server/eve_event_interpreter.py))

Directly ported from C# [`EveEventInterpreter.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Maps/Code/EveEventInterpreter.cs):
- Loads and parses all 10,644 bytecode event trees across 1,119 maps in `eve.Emg`.
- Executes official opcodes at top priority during NPC/Prop interaction:
  - **Opcode 1**: Item grants, item consumes, gold, and scene transitions (e.g. Map 10017 Shipwreck -> Beach Map 10035).
  - **Opcode 2 / 0 / 4**: Character and NPC dialogue windows via authentic `AC 20 Sub 1` packets.
  - **Opcode 3**: Companion Pet Recruitment (Robinson, Niss, S.Monkey).
  - **Opcode 5**: Quest flag state updates (`AC 24 Sub 5`).
  - **Opcode 6**: Sound effects & fanfare audio (`AC 20 Sub 10`).
  - **Opcode 9**: Map teleports and geometric warps.

---

## 5. NPC Click & Wild Monster Classification Architecture ([`server/handlers/handle_20_interaction.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_20_interaction.py))

When a player clicks an NPC on any map (`AC 20 Sub 1`), the server uses a multi-tier classification check (`is_wild_monster`):

1. **Template ID Classification**:
   - `10000-12999`: Story Characters, Recruitable Companions, Sailors (Never wild monsters).
   - `13000-13999`: Shops (Props Shop, Weapon Shop, Armor Shop).
   - `14000-14999`: Human Villagers, Townspeople, Passengers, Guards, Elders (e.g. Ashley `14013`).
   - `15000-16999`: Story / Quest Actors.
   - `17000-17999`: Authentic wild roaming field monsters (e.g. Jellyfish, Spiders, Wolves).
   - `19000-24999`: Props, Gathering nodes, Chests, Furniture.
   - `25000+`: Cutscene actors.
2. **Peaceful Keyword & Domestic Animal Guards**:
   - Word-boundary matching for human titles, services, and domestic animals (e.g. `17400` Kelan pigs).
3. **Dialogue & Quest Dispatch**:
   - Sends authentic in-game dialogue window packets (`AC 20 Sub 1`) containing TalkIDs from `Talk.dat` (e.g. `39378` for Welling Villagers, `51155` for Clinics, `41232` for Casino, `41916` for Robinson).
   - Keeps client dialogue state open until the player presses Enter/clicks, where the client sends `AC 20 Sub 6` (Continue).
   - On `AC 20 Sub 6`, dispatches `AC 20 Sub 8` + `AC 5 Sub 4` to cleanly close the dialogue window and unlock client movement.

---

## 5. Live Hot-Reload Engine ([`server/dynamic_data_manager.py`](file:///d:/GitHub/Wonderland%20Online/server/dynamic_data_manager.py))

Administrators can modify any recipe, monster drop, or chest reward in SQLite or external JSON files and trigger an immediate hot-reload without restarting the game server:

```python
from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA

# Triggers live reload across battle engine, alchemy, gathering, forging, and instances
GLOBAL_DYNAMIC_DATA.reload_all_dynamic_data()
```
