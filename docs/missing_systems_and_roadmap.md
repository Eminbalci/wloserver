# Wonderland Online - Missing Systems & Development Roadmap

## 1. Executive Summary
This document provides a comprehensive, exhaustive audit comparing the **C# Wonderland Private Server (`wlo.pserver.core`)** and **Decompiled Client Protocols (`decompiled docs/`)** with the active **Python Wonderland Online Server (`server/`)**.

It catalogues all remaining unimplemented features, partially completed subsystems, packet protocol gaps, database schema requirements, and implementation priorities.

---

## 2. System Status Overview Matrix

| Category | Subsystem | C# Reference | Status in Python | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **Crafting & Gathering** | AFK Gathering (Mining, Woodcutting, Fishing) | [`GatheringManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/GatheringManager.cs) | ❌ Missing | High |
| **World Exploration** | Interactive Treasure Chests & Loot Pools | [`ChestDropManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Maps/ChestDropManager.cs) | ❌ Missing | High |
| **Equipment & Gear** | Forging, Spar Gem Embedding & Sockets | [`ForgingManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/ForgingManager.cs) | ❌ Missing | High |
| **Equipment & Gear** | Durability Decay & Tool Repair (Spanner) | [`EquipmentRepairManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/EquipmentRepairManager.cs) | ❌ Missing | Medium |
| **Crafting & Alchemy** | Advanced Alchemy & Alchemy Books (I-IV) | [`AlchemyManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/AlchemyManager.cs) | ⚠️ Partial | Medium |
| **Player Survival** | Auto-Recovery & Sustenance (Rice Ball) | [`RiceBall.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/PlayerRelated/RiceBall.cs) | ❌ Missing | Medium |
| **Progression & Lore** | Player Titles & Passive Stat Buffs | `PlayerTitleData.txt`, `AC 183/186` | ❌ Missing | Medium |
| **Account Security** | Secondary Security PIN Lock | `AC 226` | ❌ Missing | Low |
| **Atmosphere & Map** | Dynamic Map Weather & Night/Day Cycles | `AC 57` | ❌ Missing | Low |
| **Group Content** | Multi-Stage Party Instance Dungeons | `AC 89`, `AC 91`, `AC 92` | ❌ Missing | High |
| **Security & Netcode** | Anti-Cheat & Velocity/Rate Limiting | `wlo.pserver.core/Network` | ⚠️ Partial | High |

---

## 3. Detailed Specifications of Missing Systems

### 3.1. AFK Gathering Engine (Mining, Woodcutting, Fishing)
- **C# Reference**: [`GatheringManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/GatheringManager.cs)
- **Status**: Missing
- **Protocol**: `AC 5 Sub 12` (Fishing action), `AC 5 Sub 14` (Mining/Woodcutting animation), `AC 23 Sub 25` (Fishing bait use).
- **Core Mechanics**:
  1. **Session Tracker**: Tracks active gathering sessions per `char_id`.
  2. **Tick Interval**: Periodic timer (5 to 10 seconds) harvesting resources while player remains stationary.
  3. **Loot Tables**:
     - **Mining**: Iron Ore (`27020`), Copper Ore (`27021`), Coal (`27022`), Silver Ore (`27023`), Gold Ore (`27024`), Quartz, Titanium.
     - **Woodcutting**: Ordinary Wood (`27001`), Pine Wood (`27002`), Cypress Wood (`27003`), Willow Wood (`27004`), Vine (`27005`).
     - **Fishing**: Crab (`30003`), Trout (`30004`), Salmon (`30005`), Eel (`30006`), Seaweed (`30007`), Tuna.
  4. **Tool Requirement**: Validates vacuum cleaner, automatic drill, pickaxe, or fishing rod equipped in player's inventory/tool slots.

---

### 3.2. World Map Treasure Chests & Key System
- **C# Reference**: [`ChestDropManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Maps/ChestDropManager.cs)
- **Status**: Missing
- **Protocol**: `AC 20 Sub 1` (Chest Object Click), `AC 22 Sub 10` (Open/Hide chest visual), `AC 23 Sub 57` (Loot prompt).
- **Core Mechanics**:
  1. **Chest Placement**: Map-specific persistent and respawning chests.
  2. **Key Requirements**:
     - Wooden/Ordinary Chest: No key required.
     - Copper Chest: Requires Bronze/Copper Key (`48001`).
     - Silver Chest: Requires Silver Key (`48002`).
     - Gold Chest: Requires Gold Key (`48003`).
  3. **Per-Player State**: Records opened one-time story chests in SQLite `charchests` table so completed chests stay open.
  4. **Dynamic Map Loot Pools**:
     - *Map 10036 (Shipwreck Beach)*: Coconut (`41066`), Fresh Fruit (`28014`), Sea Water (`28001`), Ordinary Wood (`27001`).
     - *Map 10001 (Kelan Woods)*: Red Apple (`28006`), Mushroom (`28012`), Herb Potion (`30001`), Pine Wood (`27002`).
     - *Map 10010 (Kelan Village)*: Black Medicine (`30259`), Cooking Salt (`28003`), White Rice (`28015`), Fresh Milk (`28007`).
     - *Map 10020 (Maka Cave)*: Iron Ore (`24001`), Copper Ore (`24002`), Coal (`24005`), Gold Sand (`24010`).

---

### 3.3. Equipment Forging, Spar Gem Embedding & Sockets
- **C# Reference**: [`ForgingManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/ForgingManager.cs)
- **Status**: Missing
- **Protocol**: `AC 64 Sub 5` (Forge Gem Request), `AC 5 Sub 5: 60025` (Forging anvil spark effect).
- **Core Mechanics**:
  1. **Spar Types**:
     - `+24 ATK Spar` (`47001`)
     - `+24 DEF Spar` (`47002`)
     - `+24 MATK Spar` (`47003`)
     - `+24 MDF Spar` (`47004`)
     - `+24 SPD Spar` (`47005`)
     - `Brilliant Diamond` (`47010` - Grants +42 to all attributes)
  2. **Socket System**: Adds 1 to 3 gem sockets onto weapons, helmets, armor, boots, and rings.
  3. **Enchantment Levels**: +1 through +12 gear enhancement with progressive failure/break risks without lucky charms.

---

### 3.4. Equipment Durability Decay & Repair System
- **C# Reference**: [`EquipmentRepairManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/EquipmentRepairManager.cs)
- **Status**: Missing
- **Core Mechanics**:
  1. **Durability (Dura)**: Every equipped item has current durability and max durability (e.g. `250/250`).
  2. **Combat Decay**: Weapons lose 1 dura every 10 physical attacks; armor loses 1 dura every 15 hits taken.
  3. **Broken State**: When dura hits 0, item stats are disabled until repaired.
  4. **Repair Tools**:
     - `Spanner` (`38030`): Restores durability directly in tent or inventory.
     - Blacksmith NPC Repair: Costs gold relative to lost durability.

---

### 3.5. Advanced Alchemy & Tiered Compounding
- **C# Reference**: [`AlchemyManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Crafting/AlchemyManager.cs)
- **Status**: Partial (Basic compounding exists; alchemy tiers & books missing)
- **Core Mechanics**:
  1. **Alchemy Ranks**: Primary Alchemy (Lv 1-10), Junior Alchemy (Lv 11-20), Senior Alchemy (Lv 21-30).
  2. **Alchemy Books (I, II, III, IV)**: Items placed in alchemy slots boosting the final compound rank by +1 to +4 levels.
  3. **Compound Formulas**: Combines item rank levels, element affinities, and failure tier tables from `Compound.dat` & `Formula.dat`.

---

### 3.6. Auto-Recovery & Sustenance Engine (Rice Ball System)
- **C# Reference**: [`RiceBall.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/PlayerRelated/RiceBall.cs)
- **Status**: Missing
- **Core Mechanics**:
  1. **Active Sustenance Buffer**: Eating a Rice Ball (`30025`) or Auto-Heal Potion stores an active HP/SP recovery pool (e.g. 50,000 HP / 50,000 SP).
  2. **Post-Battle Trigger**: Immediately restores player and battle pets to 100% HP/SP after every combat encounter without opening inventory.
  3. **Tick Buffer**: Ticks every 10 seconds in overworld travel.

---

### 3.7. Player Titles & Achievement Engine
- **Reference**: `PlayerTitleData.txt`, `AC 183`, `AC 186`
- **Status**: Missing
- **Protocol**: `AC 183 Sub 1` (Send unlocked titles), `AC 186 Sub 1` (Equip active title).
- **Core Mechanics**:
  1. **Title Collection**: Unlocked via storyline quests, reaching level milestones (Lv 50, 100, Reborn), or clearing 12 Zodiac Palaces.
  2. **Title Stat Buffs**: Equipping active titles grants passive bonuses (e.g. "+50 Max HP", "+15 ATK", "+10 SPD").
  3. **Client Title Banner**: Displays title prefix above player character head.

---

### 3.8. Secondary Security PIN Lock
- **Reference**: `AC 226`
- **Status**: Missing
- **Protocol**: `AC 226 Sub 1` (Set PIN), `AC 226 Sub 2` (Verify PIN), `AC 226 Sub 3` (Lock status).
- **Core Mechanics**:
  1. 6-digit cryptographic PIN protecting high-risk actions.
  2. Blocks character deletion, dropping rare gear, and large bank withdrawals until unlocked for the current login session.

---

### 3.9. Map Weather & Environmental Engine
- **Reference**: `AC 57`
- **Status**: Missing
- **Protocol**: `AC 57 Sub 1` (Weather packet: `[57, 1, weather_type (1B), intensity (1B)]`).
- **Core Mechanics**:
  - `0`: Clear Sunny
  - `1`: Rain / Downpour (e.g. Kelan Woods, South Island)
  - `2`: Snow / Blizzard (e.g. South Pole, Iceberg Caves)
  - `3`: Sakura / Cherry Blossom Petals (e.g. Kyoto / Japan)
  - `4`: Dense Fog (e.g. Ghost Ship, Mist Valley)
  - `5`: Thunderstorm

---

### 3.10. Multi-Stage Party Instance Dungeons
- **Reference**: `AC 89`, `AC 91`, `AC 92`
- **Status**: Missing
- **Core Mechanics**:
  1. **Party Entry Gate**: Party leader interacts with instance portal; checks all members meet level requirements and have daily entry tokens.
  2. **Instance Maps**: Isolated temporary map instances for Ghost Ship, Maya Alien Base, and 12 Palaces.
  3. **Wave Progression**: Clears room monsters $\to$ opens barrier $\to$ triggers boss room $\to$ delivers instance chest rewards.
  4. **Reset Timers**: 24-hour daily cooldown timer per character.

---

### 3.11. Netcode Security & Anti-Cheat Engine
- **Reference**: `wlo.pserver.core/Network`
- **Status**: Partial
- **Core Mechanics**:
  1. **Velocity Delta Check**: Validates tile distance walked against elapsed timestamp (`dt`). Flags movements exceeding max possible grid speed (> 3 tiles per 0.2s).
  2. **Packet Flood Gate**: Throttles incoming packets per connection (Max 40 packets/sec).
  3. **Auto Blacklist**: Temporarily bans IP on malicious packet injection.

---

## 4. Action Codes (AC) Master Coverage Table

| Action Code | Description | C# Handler | Python Implementation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **AC 0** | Handshake, Ping, Version Verify | `AC0.cs` | [`handle_0_handshake.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_0_handshake.py) | ✅ Complete |
| **AC 2** | Chat (Local, World, Whisper, Team, Guild) | `AC02.cs` | [`handle_2_chat.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_2_chat.py) | ✅ Complete |
| **AC 5** | Player Actions, Emotes, Visual FX, Level Up | `AC05.cs` | [`server/gameserver.py`](file:///d:/GitHub/Wonderland%20Online/server/gameserver.py) | ✅ Complete |
| **AC 6** | Grid Movement & Position Synchronization | `AC06.cs` | [`handle_6_movement.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_6_movement.py) | ✅ Complete |
| **AC 8** | Stats Update, Skill Learning, Reborn Stat Allocation | `AC08.cs` | [`handle_8_stats.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_8_stats.py) | ✅ Complete |
| **AC 9** | Character Creation & Appearance Selection | `AC09.cs` | [`handle_9_char_creation.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_9_char_creation.py) | ✅ Complete |
| **AC 11** | Combat Action, Skills, Guard, Flee | `AC11.cs` | [`handle_11_combat.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_11_combat.py) | ✅ Complete |
| **AC 12** | Map Warp, Teleportation, Portals | `AC12.cs` | [`handle_12_warp.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_12_warp.py) | ✅ Complete |
| **AC 13** | Inventory Manipulation, Equip, Unequip, Split | `AC13.cs` | [`handle_23_items.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_23_items.py) | ✅ Complete |
| **AC 14** | Friend List, Add/Delete Friend, Friend Status | `AC14.cs` | [`handle_14_friends.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_14_friends.py) | ✅ Complete |
| **AC 15** | Pets, Mounts, Vehicle Boarding (`15:10`), Recruitment (`15:1`) | `AC15.cs` | [`handle_15_companion.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_15_companion.py) | ✅ Complete |
| **AC 20** | NPC Interaction, Dialogues, Scene Triggers, Chests | `AC20.cs` | [`handle_20_interaction.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_20_interaction.py) | ✅ Complete |
| **AC 22** | Dynamic Actor Visibility & Despawn Triggers | `AC22.cs` | [`server/preevent_interpreter.py`](file:///d:/GitHub/Wonderland%20Online/server/preevent_interpreter.py) | ✅ Complete |
| **AC 23** | Consumables, Bathing, Ground Items, Furniture List | `AC23.cs` | [`handle_23_items.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_23_items.py) | ✅ Complete |
| **AC 24** | Master Quest Journal & Step State Flags | `AC24.cs` | [`server/quests.py`](file:///d:/GitHub/Wonderland%20Online/server/quests.py) | ✅ Complete |
| **AC 25** | Secure P2P Trading (Two-Phase Verification) | `AC29.cs` | [`handle_25_trade.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_25_trade.py) | ✅ Complete |
| **AC 30** | Mailbox & Parcel Delivery (Send, List, Claim) | `AC30.cs` | [`handle_30_action.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_30_action.py) | ✅ Complete |
| **AC 31** | Mail Deletion & Cleanup | `AC31.cs` | [`handle_31_action.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_31_action.py) | ✅ Complete |
| **AC 33** | Player Settings, PK Mode, Channel Masks | `AC33.cs` | [`handle_33_settings.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_33_settings.py) | ✅ Complete |
| **AC 34** | Item Mall & Point Purchases | `AC34.cs` | [`handle_34_itemmall.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_34_itemmall.py) | ✅ Complete |
| **AC 35** | Character Deletion & Code Check | `AC35.cs` | [`handle_35_char_deletion.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_35_char_deletion.py) | ✅ Complete |
| **AC 39** | Guild Management (Create, Invite, Storage) & F6 Quest | `AC39.cs` | [`handle_39_quest.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_39_quest.py) | ✅ Complete |
| **AC 40** | Player Street Stalls & Vending Signs (`56:30`) | `AC56.cs` | [`handle_25_trade.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_25_trade.py) | ✅ Complete |
| **AC 43** | Team / Party Management | `AC43.cs` | [`handle_43_team.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_43_team.py) | ✅ Complete |
| **AC 44** | Marriage, Wedding Ceremony & Couple Teleport | `AC44.cs` | [`server/marriage_system.py`](file:///d:/GitHub/Wonderland%20Online/server/marriage_system.py) | ✅ Complete |
| **AC 50** | Battle Turn Order & Synchronization | `AC50.cs` | [`handle_50_battle.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_50_battle.py) | ✅ Complete |
| **AC 54** | Hot Springs & HP/SP Bathing Recovery | `AC54.cs` | [`handle_54_action.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_54_action.py) | ✅ Complete |
| **AC 57** | Map Weather (Rain, Snow, Sakura Petals) | `AC57.cs` | ❌ Pending | ❌ Missing |
| **AC 62** | Tent Interior, Furniture Placement, Move, Styles | `AC62.cs` | [`handle_62_tent.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_62_tent.py) | ✅ Complete |
| **AC 63** | Authentication & Character Slot Selection | `AC63.cs` | [`handle_63_login.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_63_login.py) | ✅ Complete |
| **AC 64** | Workbench Manufacturing, Compounding, Forging | `AC64.cs` | [`handle_64_crafting.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_64_crafting.py) | ✅ Complete |
| **AC 65** | Tent Pitching, Pack-up, Enter/Exit Interior | `AC65.cs` | [`handle_65_action.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_65_action.py) | ✅ Complete |
| **AC 75** | Lucky Draw Wheel & Gacha Machines | `AC75.cs` | [`handle_104_minigame.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_104_minigame.py) | ✅ Complete |
| **AC 89/91/92** | Instance Dungeons (Ghost Ship, Maya Base) | `Instance.cs`| ❌ Pending | ❌ Missing |
| **AC 104** | Multiplayer Gobang (Five in a Row) Board Game | `AC104.cs` | [`handle_104_minigame.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_104_minigame.py) | ✅ Complete |
| **AC 183/186**| Player Titles & Title Stat Buffs | `Title.cs` | ❌ Pending | ❌ Missing |
| **AC 226** | Secondary Security Lock PIN | `Security.cs`| ❌ Pending | ❌ Missing |

---

## 5. Implementation Roadmap

### Phase 1: High Priority (Gameplay & Progression Core)
1. **World Map Interactive Treasure Chests (`server/chest_system.py`)**:
   - Ingest all chest placements from `eve.Emg` and `SceneData.dat`.
   - Implement chest opening animations, key verification, dynamic map loot tables, and `charchests` persistence.
2. **AFK Gathering Engine (`server/gathering_system.py`)**:
   - Implement continuous harvesting loops for mining, woodcutting, and fishing with tool verification and inventory delivery.
3. **Equipment Forging & Spar Gem Sockets (`server/forging_system.py`)**:
   - Enable embedding +24 Spars (`47001`..`47005`) and Diamonds (`47010`) into gear slots with anvil spark effects.
4. **Instance Dungeons (`server/instance_system.py`)**:
   - Multi-room party instances for Ghost Ship, Maya Dungeon, and Pirate Cave with wave spawns and reset timers.

### Phase 2: Medium Priority (Quality of Life & Sustenance)
1. **Auto-Recovery Sustenance (`server/sustenance_system.py`)**:
   - Rice ball HP/SP buffer auto-healer post-combat.
2. **Player Titles & Achievements (`server/title_system.py`)**:
   - Title registry, unlock conditions, client banner, and passive stat bonuses (`AC 183/186`).
3. **Equipment Durability & Repair (`server/repair_system.py`)**:
   - Combat durability degradation and spanner tool repairs.

### Phase 3: Low Priority (Atmosphere & Security)
1. **Map Weather System (`server/weather_system.py`)**:
   - Periodic rain, snow, and sakura petal broadcasting (`AC 57`).
2. **Security PIN Lock (`server/security_pin.py`)**:
   - Secondary PIN verification on character deletion and bank vault access (`AC 226`).
