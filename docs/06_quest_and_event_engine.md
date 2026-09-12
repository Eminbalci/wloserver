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

In Wonderland Online, certain NPCs or cutscene actors are conditionally visible based on quest progress (e.g. ship passengers before shipwreck vs Robinson on Kelan beach).

Located in `server/preevent_interpreter.py`:
- Parses map PreEvent offsets in `eve.Emg`.
- Evaluates client condition flags (completed quest IDs, current step).
- If condition fails, server omits spawning the actor in `AC 22:2` / `AC 5:3` spawn broadcasts, preventing spoilers and sequence breaking.

## Multi-Step Dialogue Queue & `Talk.dat` Resolver

`Talk.dat` holds 17,494 encoded dialogues:
- Decoded using `Big5` / `CP950` with fallback to `latin1`.
- When a dialogue involves multiple lines or branching decisions:
  1. Server sends initial step via `AC 20 Sub 1` (`[20, 1, step, portrait, talk_id_16]`).
  2. Client confirms with `AC 20 Sub 8` or option selection (`AC 20 Sub 1`).
  3. Server pops next dialogue node from `session.dialogue_queue` and dispatches next text frame.
  4. On conversation conclusion, sends `[20, 8]` to unlock client control.

## Introductory Quest & Cutscenes (`AC 186`)

1. **Ocean Star Shipwreck Sequence**:
   - Character created on luxury liner (Map 10017).
   - Captain dialogue triggers storm cutscene (`AC 186 Sub 1`).
   - Screen flashes, thunder SFX plays (`AC 184`), and player is warped to Kelan Beach (Map 10035).
2. **Robinson Rescue Sequence**:
   - Unconscious player is found on beach by Robinson.
   - Dynamic actor spawning (`AC 3:123`), camera panning (`AC 22:4`), and quest award of starter tent (`Item #32101`).
