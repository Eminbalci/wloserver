# Quest System, Dialogue Engine & Event Bytecode

This document details the quest management engine, `Mark.dat` parser, `eve.Emg` binary event tree interpreter, PreEvent conditional actor visibility, and multi-step dialogue flows.

## Architecture Overview

Wonderland Online features a data-driven narrative engine driven by binary asset files and bytecode scripts:
- **`Mark.dat`**: Defines master quest headers, objectives, descriptions, reward items, and state requirements.
- **`eve.Emg`**: Contains compiled bytecode event trees attached to world entities, scene triggers, and dialogues across 1,119 maps.
- **`Talk.dat`**: Database of 17,494 dialogue strings and NPC portraits.
- **`QuestManager` & `QuestEngine`**: Maintains player quest journals and dispatches progression packets (`AC 24`).
- **`EveEventInterpreter`**: Decodes and executes bytecode opcodes for interactive dialogue, reward grants, and cinematic scene transitions.

```
+-------------------------------------------------------------+
|                 Player Action (AC 20:1 / AC 24)             |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|               EveEventInterpreter (eve.Emg)                 |
|  - Reads binary event bytecode tree for target click_id     |
|  - Evaluates player prerequisites & quest status flags      |
+--------------+---------------+---------------+--------------+
               |               |               |
               v               v               v
        [Dialogue Step]   [Battle Encounter] [Item / Warp]
          Talk.dat            AC 11 / 50       AC 23 / 12
               |
               v
     PreEventInterpreter (Dynamic Actor Visibility)
```

## `Mark.dat` Binary Format

`server/quests.py` parses `data/Mark.dat` to index all game quests:

```
+-------------------------------------------------------------+
| Offset | Size | Type     | Field Name                       |
+-------------------------------------------------------------+
| 0      | 2 B  | uint16   | Quest ID (1 .. 65535)            |
| 2      | 20 B | big5/str | Quest Title                      |
| 22     | 2 B  | uint16   | Required Level                   |
| 24     | 2 B  | uint16   | Start NPC Template ID            |
| 26     | 2 B  | uint16   | Start Map ID                     |
| 28     | 4 B  | uint32   | Target Objective / Item ID       |
| 32     | 4 B  | uint32   | Reward EXP                       |
| 36     | 4 B  | uint32   | Reward Gold                      |
| 40     | 4 B  | uint32   | Reward Item ID                   |
+-------------------------------------------------------------+
```

## `eve.Emg` Event Bytecode Interpreter

Each map entry in `data/eve.Emg` contains a category table pointing to bytecode event blocks (`dataptr + offset`). `EveEventInterpreter` sequentially reads instructions:

### Bytecode Instruction Opcodes

| Opcode | Mnemonic | Parameters | Operational Description |
| :--- | :--- | :--- | :--- |
| **0x01** | `TALK / CHEST` | `[talk_id_16, portrait_8, step_8]` | Displays dialogue box with NPC portrait from `Talk.dat`. Also triggers chest loot. |
| **0x02** | `BATTLE` | `[battle_group_16, bg_id_8]` | Initiates turn-based combat with authentic monster formation. |
| **0x03** | `ACTOR_SPAWN` | `[actor_id_16, x_16, y_16, state_8]`| Spawns or hides dynamic quest actors in map scene. |
| **0x04** | `WARP` | `[dst_map_16, dst_x_32, dst_y_32]` | Teleports player to destination coordinates (`AC 12`). |
| **0x05** | `CHOICE_BRANCH`| `[question_id, option_count, ...]` | Presents branching dialogue options to player. |
| **0x06** | `ITEM_CHECK` | `[item_id_16, required_count_16]` | Conditional jump based on player inventory contents. |
| **0x07** | `QUEST_SET` | `[quest_id_16, new_state_8]` | Advances player quest journal state (`AC 24 Sub 1`). |
| **0x08** | `ITEM_GIVE` | `[item_id_16, count_16]` | Grants reward item to player inventory (`AC 23 Sub 6`).|
| **0x09** | `ITEM_TAKE` | `[item_id_16, count_16]` | Deducts quest requirement item from player inventory. |

## PreEvent Interpreter & Dynamic Visibility

In Wonderland Online, world entities and NPCs are conditionally rendered or hidden based on active player quest state and progression flags (e.g. Ocean Star ship passengers before shipwreck, Robinson stranded on Kelan beach, or Lina's lost Shiba Inu in Kelan Village).

Located in [`server/preevent_interpreter.py`](file:///D:/GitHub/Wonderland%20Online/server/preevent_interpreter.py):
- **Native Data Source**: Parses native map PreEvent bytecode structures from `data/eve.Emg` (Offset 9 in `CategoryOffset` table across 657 maps, 1,391 PreEvents, 8,900+ actions).
- **Binary PreEvent Structure**:
  - **Header (24 bytes)**: `ev_id` (uint16 LE), `unk1` (uint8), `name_bytes` (20 bytes Big5), `sub_count` (uint8).
  - **Sub-entries (Condition block - 22 bytes)**:
    - 1-byte `sub_idx` followed by three 7-byte condition chunks (`[op, w1, w2, w3]`):
      - `op` (uint8): `0x01` (Unconditional True), `0x02` (Companion recruitment check), `0x05` (Quest / Flag comparator).
      - `w1` (uint16 LE): Quest ID or secondary comparator value.
      - `w2` (uint16 LE): Required target value / state.
      - `w3` (uint16 LE): Comparison operator (`1`: `==`, `2`: `>=`, `3`: `<=`, `4`: `!=`, `5`: `>`, `6`: `<`).
  - **Action Block**: 1-byte `act_count` followed by 22-byte action chunks:
    - `ss_idx` (uint8), `action_op` (uint8: `0x02` for Actor Visibility / State Control), `click_id` (uint16 LE), `d2` (uint16), `d3` (uint16), `d4` (uint16), `state` (bytes 9-10).

### PreEvent Lifecycle State Mapping & Default Invisibility
In `data/eve.Emg` PreEvent bytecode, quest comparator conditions (`Opcode 0x05`) evaluate player progression according to the authentic WLO bytecode lifecycle states:
- **`1` = InProgress**: The quest has been accepted and is actively being pursued.
- **`2` = NotStarted**: The default state for unregistered or unaccepted quests. Across all 1,119 maps in `eve.Emg`, when `w2 == 2`, the associated action is almost exclusively `[action_op=0x02, state=(0xFF, 0xFF)]` (Hide Actor). This enforces authentic default invisibility for staged NPCs (e.g. Pig Click 14/15/16, Lost Dog Click 20, Lina's Dog Click 28, Father's Statue Click 33, Iron Sword Click 35, Grave Roca Click 36) upon scene entry.
- **`3` = Completed**: The quest has concluded. Sub-branches specifying `w1 = quest_id + 1, w2 = 1` or `w2 = 3` with 0 action chunks represent unhide/show overrides restoring actor visibility.

### Per-NPC Action Dispatch & Override Resolution
PreEvents often govern multiple related entities within a single multi-branch record (e.g. PreEvent #7 on Map 12000 controlling Statue Click 33, Sword Click 35, and Grave Roca Click 36).
- `PreEventInterpreter.evaluate_map_preevents` maintains a `handled_npcs: Set[int]` collection during map evaluation.
- When an action chunk (`action_op = 0x02`) targets a specific `click_id`, it executes and commits that NPC to `handled_npcs`.
- Matching completion branches with 0 action chunks derive target entity IDs and clear previously cached hide states (`session._actor_visibility[click_id] = True`), dispatching `AC 22:10 [click_id, 0x00, 0x00]` if the actor was previously concealed.
- Scenery props on Map 12000 (Guideposts 10, 31 and Honeycomb 17) are preserved to prevent permanent world fixtures from being mistakenly despawned.

### Multi-Chunk Condition Resolution & Authentic Quest Lifecycle States
Each condition block contains up to 3 evaluation chunks:
1. **Chunk 0 (`ci == 0`)**: Evaluates primary quest or flag state against player quest journal (`_get_player_preevent_state`).
   - `0 = NotStarted`: Default state for unaccepted / unopened quests and chests. Unopened chests have flag value `0`.
   - `1 = InProgress`: Active quest state set during storylines.
   - `2 = Completed`: Finished quest state set by Opcode 5 (`dptr == 5, d2 == 2`). When a chest is opened, its quest flag is updated to `2`, satisfying condition `req_value == 2` to render the opened chest sprite (`state1 = 1, state2 = 0`).
2. **Secondary Chunks (`ci > 0`)**:
   - If $w_1 \ge 1000$: Evaluated as a secondary quest/flag ID.
   - If $0 < w_1 < 1000$: Evaluated as the required quest `step` for the quest ID specified in Chunk 0 (`_get_player_quest_step`). This prevents false-positive comparisons where step numbers were misread as flag IDs.

### Dual Protocol Visibility Packets (`AC 22 Sub 10` & `AC 22 Sub 11`)
To ensure clean actor despawning without ghost sprites or interaction desync across different Wonderland Online client versions, actor visibility operations follow strict protocol boundaries:
- **Hide Actor (`send_actor_hide`)**:
  - `[22, 10, click_id_16, 0xFF, 0xFF]` (`160a<cid>ffff`): Official actor despawn frame.
  - `[22, 11, click_id_16, 0xFF, 0xFF]` (`160b<cid>ffff`): Scene isolation frame suppressing residual interaction hitboxes.
- **Show Actor (`send_actor_show`)**:
  - `[22, 10, click_id_16, 0x00, 0x00]` (`160a<cid>0000`): Official actor spawn frame for living NPCs.
  - `[22, 11, click_id_16, 0x00, 0x00]` (`160b<cid>0000`): Scene integration frame restoring interaction state for living NPCs.
- **Actor State / Animation Frame Updates (`_execute_action_block`)**:
  - For non-concealment actions (`state1 != 0xFF or state2 != 0xFF`, such as opened chest sprite frames `0x01, 0x00`), the server dispatches **`AC 22:10 click_id state1 state2` ONLY**.
  - `AC 22:11` is strictly omitted during state/frame updates. In WLO client architecture, sending `AC 22:11` to static scenery props, casks, or chests triggers scene isolation that despawns and corrupts the entities from client memory.
- **Delta Packet Suppression**: To prevent client sprite flickering and animation resetting on static chests and decorative props (template IDs `19000 .. 35000` and `12000 .. 12999`), redundant show packets are suppressed if the entity is already marked visible.

### Companion Isolation Architecture & Multi-Map Lifecycle
Story companions possess separate actor representations (`click_id`) across villages and submaps:
- **Roca (`template_id: 14162`, aliases: `14001, 14161, 14162`)**:
  - **Map 12000 (Kelan Village Outdoors)**:
    - `CID 32` (Village Square): Strictly hidden at all times. Canonical WLO never places Roca in the outdoor square during normal gameplay.
    - `CID 34` (Grave Mourning): Dynamic quest cutscene actor for Quest 13052 ("Death of Roca's Father"). Visible ONLY while Quest 13052 is InProgress (`state == 1`) and Roca has not been recruited.
    - `CID 36` (Grave Standing): Auxiliary staged copy, permanently hidden.
  - **Map 12001 (Chief's House / Kelan Leader's House)**:
    - `CID 2`: Canonical initial station for Roca beside the Village Chief (`CID 1`). Visible by default for all players until recruited.
    - `CID 3`: Secondary cutscene actor, permanently hidden.
- **Recruitment Evaluation (`has_recruited_companion`)**:
  - Checks active pet roster (`session.pets`) by template ID and name aliases.
  - Checks currently active pet ID (`session.active_pet_id`).
  - Checks companion recruitment quest states (e.g. Roca: Quest 13052 `state == 2` or Quest 13098 `state in (1, 2)`; Robinson: Quest 15283 or 12040 `state in (1, 2)`; S.Monkey: Quest 12018 `state in (1, 2)`).
  - Once recruited, both Map 12001 `CID 2` and Map 12000 `CID 34` are automatically concealed.

### Staged Quest Entity Lifecycles (Map 12000)
- **Father's Statue (`CID 33`) & Iron Sword (`CID 35`)**: Controlled by Quest 13098 ("Remembering Father"). Visible only during InProgress (`state == 1`); hidden while NotStarted (`state == 0`) or Completed (`state == 2`).
- **Lina's Lost Shiba Inus (`CID 28 & 20`)**: Controlled by Quest 13046. `CID 29` is the permanent sitting dog. `CID 28` is hidden until returned. `CID 20` (roaming in village) is visible ONLY during Step 1.
- **Quest Pigs (`CID 14, 15, 16`)**:
  - `CID 14` (Pig returned to pen): Visible during Quest 12020 Step 2, Quest 12020 Completed (`state == 2`), or Flag 12021 Completed (`state == 1`).
  - `CID 15` (Pig roaming outside pen): Visible ONLY during Quest 12020 Step 1 (`state == 1 and step == 1`); hidden otherwise.
  - `CID 16` (Staged Pig): Hidden when Quest 13020 is NotStarted (`state == 0`) or Completed (`state == 2`) or Flag 13021 Completed (`state == 1`).

### Runtime Interaction Gating
In [`server/handlers/handle_20_interaction.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_20_interaction.py), NPC clicks (`AC 20 Sub 1`) verify visibility via `GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(session, map_id, click_id)`. If an NPC is currently hidden for the player:
1. Server dispatches `AC 22:10 [click_id, 0xFF, 0xFF]` to re-enforce client-side despawn.
2. Server dispatches `AC 20:8` to unlock client input without initiating dialogue or event triggers.

### Real-Time Synchronization Triggers
Dynamic actor visibility is evaluated and pushed in real-time across four lifecycle events:
1. **Map Entry & Warp**: [`GameServer.send_map_info`](file:///D:/GitHub/Wonderland%20Online/server/gameserver.py) executes `sync_per_player_npc_visibility` and `replay_actor_visibility`.
2. **Dialogue Conclusion**: [`handle_20_interaction.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_20_interaction.py) triggers synchronization upon dialogue completion and quest script termination (`AC 20 Sub 8`).
3. **Quest Engine State Transitions**: [`QuestEngine.send_quest_update`](file:///D:/GitHub/Wonderland%20Online/server/quests.py) and `complete_quest` invalidate `_player_quests_map` and synchronize visibility.
4. **Bytecode Event Opcode Execution**: [`EveEventInterpreter.execute_sub_opcodes`](file:///D:/GitHub/Wonderland%20Online/server/eve_event_interpreter.py) triggers synchronization on Opcode 5 (Quest Flag Update) and Opcode 3 (Companion Recruitment).

## Multi-Step Dialogue Queue & `Talk.dat` Resolver

`Talk.dat` holds 17,494 encoded dialogues:
- Decoded using `Big5` / `CP950` with fallback to `latin1`.
- When a dialogue involves multiple lines or branching decisions:
  1. Server sends initial step via `AC 20 Sub 1` (`[20, 1, step, portrait, talk_id_16]`).
  2. Client confirms with `AC 20 Sub 8` or option selection (`AC 20 Sub 1`).
  3. Server pops next dialogue node from `session.dialogue_queue` and dispatches next text frame.
  4. On conversation conclusion, sends `[20, 8]` to unlock client control.

## Event Branch Cascading & Chest State Persistence

Certain world interactions in Wonderland Online—such as the Robinson Raft Chest (`Map 10035`, Chest `ClickID 7`, Event `19` `老魯加入`)—chain multiple bytecode sub-branches across single player actions:

### 1. Branch Cascading & Post-Dialogue Follow-Up
- When an event sub-branch completes without yielding any dialogues (e.g. Sub 0 granting Robinson's Raft `Item #48016` and setting Quest Flag `12046 = 1`), [`EveEventInterpreter.execute_sub_opcodes`](file:///D:/GitHub/Wonderland%20Online/server/eve_event_interpreter.py) checks if quest flags were updated.
- If flags changed and no dialogue was queued, the interpreter automatically cascades to re-evaluate the event tree's sub-branches against the updated player quest state.
- For Event 19, the freshly set Quest Flag `12046 == 1` immediately qualifies Sub 2 (Talk `20355`, Robinson speech line, speaker `ClickID 1`, portrait `3`, followed by player dialogue chain), advancing Quest Flag `12046` to `2` (Completed) and `12047` to `1` (InProgress).
- **Post-Dialogue Action Cascading (`handle_20_interaction.py`)**: When the dialogue queue is exhausted (player clicks Next on the final dialogue step), the interaction handler evaluates follow-up action branches via `select_matching_branch(session, diag_event, exclude_sub=diag_sub)` (matching authentic C# `EveEventInterpreter.cs` lines 597-610). For Event 19, this activates Sub 4 (`w1 = 12047, w2 = 1, w4 = 261`), which executes Opcode 3 (`dptr == 3, d2 == 12178`) to recruit Robinson as a pet, dispatches `AC 15:1` and `AC 15:8` (companion list update), despawns Robinson NPC (`AC 22:10` hide packet), and sets Quest Flags `15282 = 2` (Completed) and `15283 = 1` (InProgress).
- **Map 10035 Robinson Catch-Up**: If a player whose dialogue was interrupted or completed earlier interacts directly with Robinson (`ClickID 1`) on Map 10035 with Quest Flag `12047 == 1`, the interpreter intercepts the interaction to execute Event 19 Sub 4, immediately finalizing companion recruitment.

### 2. Fallback Filtering & Chest Anti-Duplication
- Candidate events matching the clicked entity are evaluated first. If no branch matches current quest flags, [`EveEventInterpreter.select_matching_branch`](file:///D:/GitHub/Wonderland%20Online/server/eve_event_interpreter.py) filters candidate branches to exclude any whose quest flags are already completed (`state >= 2` or paired state `> 0`).
- If all candidate branches are completed and no fallback branch is valid, the interpreter checks [`ChestSystem.is_perm_chest`](file:///D:/GitHub/Wonderland%20Online/server/chest_system.py) / `has_opened_chest`. If the chest has already been claimed by the player, it dispatches the authentic notification (`"You have already claimed this treasure."`) via `AC 20 Sub 8` / `AC 1:1`, preventing item duplication while unlocking player interaction.

### 3. Map Entry Opened Chest Synchronization
- To ensure looted chests render in their opened/broken sprite frame (`AC 22:10 [click_id, 0x01, 0x00]`) across server restarts, relogins, and map warps, [`GameServer.send_map_info`](file:///D:/GitHub/Wonderland%20Online/server/gameserver.py) executes `GLOBAL_CHEST_SYSTEM.sync_opened_chests_on_map(session, session.map_id)` upon map entry.
- Concurrently, PreEvent rules with condition `QuestFlag == 2` (such as PreEvent 5 on Map 10035 for Quest `12046 == 2`) evaluate true once the cascading dialogue concludes, persistently locking the opened chest appearance.

## Item & Level Condition Verification (`unkb1 == 1, 2, 15`)

Wonderland Online extensively validates player inventory items, level thresholds, and bag capacity directly in `eve.Emg` sub-entries prior to executing dialogue branches or quest progression:

### 1. Item Verification (`unkb1 == 2`)
- **Scale**: 5,749 sub-branches across 1,438 events utilize item condition checks.
- **Parameters**:
  - `req_item`: `sub.w1` (if $10000 \le w_1 \le 65000$) or `sub.w3`.
  - `req_count`: $\max(1, \text{sub.w2})$.
  - `req_have`: Defined by `sub.w4` (`w4 == 2 or w4 == 5 or (w4 & 0x01) != 0`).
    - When `req_have == True`: Branch triggers ONLY if player possesses $\ge$ `req_count` of `req_item`.
    - When `req_have == False`: Branch triggers ONLY if player lacks the item (e.g. Natasha warning player they need a ticket).
- **Branch Resolution**: If the sub-entry contains no direct opcodes (5,236 condition headers), [`EveEventInterpreter.get_executable_branch`](file:///D:/GitHub/Wonderland%20Online/server/eve_event_interpreter.py) resolves the immediately succeeding executable sub-branch.

### 2. Item Deduction / Consumption (Opcode 1)
- When quest conditions are met, Opcode 1 (`dptr == 1, d1 == 1, d3 == item_id`) consumes the quest item if `d4` contains a signed negative quantity (`d4 == 65280 or (d4 & 0xFF00) == 0xFF00`).
- [`remove_item_from_inventory`](file:///D:/GitHub/Wonderland%20Online/server/gameserver.py) deducts the required amount across inventory stacks, pushes `AC 23:57 "Lost [Item]"`, and resynchronizes player inventory via `AC 23:5`.

### 3. Level & Inventory Capacity Checks (`unkb1 == 1, 15`)
- **Level Conditions (`unkb1 == 1`)**: 5,669 sub-branches check `session.level >= sub.w1` before granting advanced questlines or job promotions.
- **Inventory Capacity (`unkb1 == 15`)**: 3,382 sub-branches verify free inventory slots, redirecting players to "Inventory is full" prompts if unable to receive rewards.

## Quest Protocol (`AC 24`) & Dual Engine Coordination

Wonderland Online coordinates quest progression across two symbiotic engines:
1. **Primary: Native `eve.Emg` Event Bytecode Interpreter (`EveEventInterpreter`)**:
   - Executes authentic map bytecode triggers, dialogues (`Talk.dat`), choice branches, combat triggers, item rewards, and Opcode 5 quest flag updates.
   - Authoritative for all official storyline events and map cutscenes.
2. **Secondary: Master Quest Engine (`QuestEngine` / `Mark.dat`)**:
   - Indexes 1,050+ authentic quests from `data/Mark.dat`.
   - Manages player quest journals, multi-stage step progressions, item collection requirements, and reward delivery for quests without compiled event trees.
   - Synchronizes quest state via `AC 24` protocol and maintains persistent storage in `characters` and `charquest` database tables.

### `AC 24` Protocol Handlers Catalog (`server/handlers/handle_24_quest.py`)

| Sub-Opcode | Direction | Description & Wire Format |
| :--- | :--- | :--- |
| **`AC 24 Sub 1`** | Server <-> Client | **Quest Step Progress ACK**: Dispatches `[24, 1, quest_id_16, step_8]` when advancing quest steps. |
| **`AC 24 Sub 2`** | Server <-> Client | **Step Synchronization**: Dispatches `[24, 2, quest_id_16, step_8]` on login/map entry to set active step indicators. |
| **`AC 24 Sub 3`** | Server -> Client | **Quest Failure / Reset**: Dispatches `[24, 3, quest_id_16]` to clear active quest state upon failure or reset. |
| **`AC 24 Sub 4`** | Server -> Client | **Quest Journal Synchronization**: Dispatches full quest journal `[24, 4, total_quests_16, {quest_id_16, flag_8, state_8}...]` on login and status queries. |
| **`AC 24 Sub 5`** | Server <-> Client | **Quest Status / Accept**: Dispatches `[24, 5, quest_id_16, state_8]` for real-time quest acceptance and completion flags (`state 2` = Completed). Queries invoke `GLOBAL_QUEST_ENGINE.get_quest_state`. |
| **`AC 24 Sub 6`** | Server <-> Client | **Pinned Quest Tracker Sync**: Client requests tracking synchronization, server returns `[24, 6, 1]` ACK. |

## Introductory Quest & Cutscenes (`AC 186`)

1. **Ocean Star Shipwreck Sequence**:
   - Character created on luxury liner (Map 10017).
   - Captain dialogue triggers storm cutscene (`AC 186 Sub 1`).
   - Screen flashes, thunder SFX plays (`AC 184`), and player is warped to Kelan Beach (Map 10035).
2. **Robinson Rescue Sequence**:
   - Unconscious player is found on beach by Robinson.
   - Dynamic actor spawning (`AC 3:123`), camera panning (`AC 22:4`), and quest award of starter tent (`Item #32101`).
3. **Robinson Recruitment & Raft Award (`Event #19` / `Mark.dat Quest 902/903`)**:
   - Chest 7 on Map 10035 grants Robinson's Raft (`Item #48016`) and triggers the dialogue with Robinson.
   - Player progresses through dialogue using `AC 20 Sub 2` / `Sub 6` / `Sub 9` with `option_id = 0`.
   - On dialogue completion, `_advance_dialogue_or_cascade` automatically triggers Event 19 Sub 4, which executes Opcode 3 companion recruitment (`12032` Robinson).
   - Server delivers Robinson (`AC 15 Sub 1` 54-byte recruitment frame), skill learning (`AC 8 Sub 2`), companion list (`AC 15 Sub 8`), and hides Robinson's world entity using dual despawn frames (`AC 22 Sub 10` and `AC 22 Sub 11`).
   - Server marks `Mark.dat` Quests 902 & 903 and event flags 12040 & 12047 as Completed (`state = 2`), dispatching `AC 24 Sub 5 [24, 5, quest_id, 2]` to immediately clear the yellow exclamation mark (`!`) from the beach map and mini-map radar.
