# Quest System Architecture & Protocol Reference

## 1. Overview
The Wonderland Online Quest System in the Python server is a dual-layer architecture ported directly from the high-performance C# server implementation (`wlo.pserver.core/Game/QuestRelated`). It combines:
1. **Authentic Binary `Mark.dat` Parsing**: Dynamic ingestion of all 2,154 official quest records, automated stage aggregation (`#01`..`#99`), and paired Master Quest registration.
2. **Multi-Stage Step Progression Engine**: Data-driven runtime state machine handling dialogues, item requirements/consumption, battle triggers, companion rewards, and per-player NPC visibility.
3. **PreEvent Bytecode Interpreter**: Real-time evaluation of `eve.Emg` condition opcodes to dynamically control actor visibility (`AC 22:10`) on map entry and quest completion.

---

## 2. Core Data Models (`server/quests.py`)

### `QuestState` Enum
- `NOT_STARTED = 0`: Available or locked by prerequisites.
- `IN_PROGRESS = 1`: Currently accepted and active on a specific step.
- `COMPLETED = 2`: Rewards delivered; dialogues updated.
- `FAILED = 3`: Abandoned or timed out.

### `QuestType` Enum
- `DIALOGUE = 0`: Completed by NPC dialogue.
- `ITEM_COLLECTION = 1`: Requires specific items in player inventory.
- `MONSTER_BATTLE = 2`: Triggers a scripted combat encounter.
- `DELIVERY = 3`: Requires delivering an item from NPC A to NPC B.
- `EXPLORATION = 4`: Location or entrance discovery.

### `QuestDefinition`
- `quest_id`: Unique identifier (1..2154).
- `title`: Extracted title string.
- `npc_name_pattern` / `npc_template_id`: Starting and target NPC matching.
- `map_id` / `area_name`: Geographic location context.
- `category`: Grouping ("👥 Companion & Rebirth", "🛠️ Crafting & Vehicles", "🐉 Dungeons & Instances", "🎯 Minigames & Challenges", "🏝️ Storyline & Area").
- `steps`: Array of `QuestStep` entries.
- `reward`: `QuestReward` (Gold, EXP, Companion Pet ID, Items list).
- `prerequisite_quest_ids`: Required completed quests before this quest unlocks.
- `despawn_npc_click_ids`: NPCs hidden from the player upon completion.

---

## 3. Network Protocol (AC 24, AC 39, AC 22, AC 15)

### AC 24: Quest State & Journal Flags
- **AC 24 Sub 4 (Full Journal Response)**:
  - Format: `[24, 4, count (2B), ... {quest_id (2B), flag1 (1B), flag2 (1B)}]`
  - Sent on login and when the player opens the F6 Quest Journal.
- **AC 24 Sub 1 (Accept / Step Sync)**:
  - Format: `[24, 1, quest_id (2B), step (1B)]`
- **AC 24 Sub 2 (Step Advance)**:
  - Format: `[24, 2, quest_id (2B), step (1B)]`
- **AC 24 Sub 5 (Quest Completed)**:
  - Format: `[24, 5, quest_id (2B), 1 (1B)]`
- **AC 24 Sub 3 (Quest Abandoned / Reset)**:
  - Format: `[24, 3, quest_id (2B)]`

### AC 39: Quest Journal Interaction
- **AC 39 Sub 1**: Client requests full Quest Journal -> Server sends AC 24:4.
- **AC 39 Sub 7**: Client requests to abandon quest -> Server calls `reset_quest` and echoes `[39, 7, 1]`.

### AC 15: Companion Recruitment Reward
- **AC 15 Sub 1 (54-Byte Authentic Packet)**:
  - Format: `[15, 1, char_id (4B), pet_id (4B), slot (1B), STR (2B), CON (2B), INT (2B), WIS (2B), AGI (2B), element (1B), level (4B), cur_hp (4B), max_hp (4B), exp (4B), amity (1B), reborn (1B), job (1B), reserved (11B)]`
  - Immediately unlocks companion skills (`AC 8:2 stat 110` and `stat 367`) and spawns companion appearance (`AC 15:4`).

### AC 22: Dynamic Actor Visibility
- **AC 22 Sub 10**: `[22, 10, click_id (2B), 0xFF, 0xFF]` to hide despawned/recruited actors.

---

## 4. PreEvent Bytecode Interpreter (`server/preevent_interpreter.py`)
Parses `eve.Emg` PreEvents data tables per map:
- **Condition Opcode 0x05**: Evaluates player quest flag vs required value using operators (`==`, `>=`, `<=`, `!=`, `>`, `<`).
- **Condition Opcode 0x02**: Validates companion pet presence in party/pets.
- **Action Opcode 0x02**: Dispatches `AC 22:10` actor visibility packets.
