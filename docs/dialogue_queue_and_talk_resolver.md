# Multi-Step Dialogue Queue, Talk.dat Resolver & Action Code 32 Emotes

## Technical Specification

### 1. Talk.dat Multi-Index Dialogue Resolver
* **File Source**: `data/Talk.dat` containing 17,494 records (292 bytes each with reversed Big5 strings).
* **Index Structures**:
  * `self._by_index`: 0-indexed record positions (`0..17,494`).
  * `self._by_offset`: Direct byte offsets (`r * 292` and `text_start`).
  * `self.dialogues`: Direct TalkID headers.
* **Resolution Pipeline**:
  1. **System / Interactive Objects (`11000..11100`)**: `recordIdx = lookupId - 11000`.
  2. **Storyline & Companions (`20000..29999`)**: `recordIdx = lookupId - 18904`.
  3. **World, Towns & Villages (`30000..49999`)**: `recordIdx = lookupId - 23105`.
  4. **Direct Byte Offset**: `talk_id // 292`.
  5. **Direct Record / Header Match**: `self.dialogues[talk_id]`.
  6. **Chapter Bases**: Checks base offsets `60000, 50000, 40000, 30000, 20000`.
  7. **Token Sanitization**: Regex stripping of sound cues (`#s.../#s`), portraits (`#f.../#f`), colors (`#[RGBY]`), and `#n` replacement with the active player's name.

---

### 2. Multi-Step Dialogue Queuing Engine
* **Execution Flow (`server/eve_event_interpreter.py`)**:
  * During native event execution, dialogue opcodes (Dptr 0, 2, 4) and choice questions (`dptr == 2, d2 == 6`) are parsed sequentially and collected into `dialogue_steps`.
  * **Step 1** is immediately dispatched to the client via `AC 20 Sub 1` and `AC 23 Sub 57` subtitle text.
  * **Steps 2..N** are enqueued into `session.dialogue_queue = [step_dict, ...]`.
* **Choice Prompt Packet Format (`AC 20 Sub 1 Type 6`)**:
  * Sent when `dptr == 2 && d2 == 6`.
  * Byte layout: `[20, 1, 0, 0, 0, stepNum, 6, portrait, speakerClickId, 0, 0, 0, 0, 0, 0, (questionId & 0xFF), ((questionId >> 8) & 0xFF), (layout or 1)]`.
  * The client displays the authentic animated choice prompt buttons with the hand cursor.
* **Option Selection Pipeline (`AC 20 Sub 2` / `AC 20 Sub 9`)**:
  * Upon receiving client option click, `EveEventInterpreter.handle_choice_selection` matches the choice value (`30 + branch_idx`) against `unkb1 == 7` sub-branches in `eve.Emg`.
  * Executes the selected branch opcodes (quest rewards, quest flag sets, failure dialogues) and cascades to outcome branches.
* **Advancement Pipeline (`server/handlers/handle_20_interaction.py`)**:
  * Upon receiving `AC 20 Sub 6` (Client "Next" / Continue action):
    * If `session.dialogue_queue` contains pending steps, the next dialogue step is popped and transmitted.
    * When the queue is exhausted, `AC 20 Sub 8` (close dialogue) and `AC 5 Sub 4` (movement unlock) are sent.

---

### 3. Action Code 32: Player Emotes & Character Animations
* **Sub-Code 1 (`AC 32:1`)**: Triggers standard emote animations (Wave, Bow, Cheer, Laugh, Cry). Broadcasts `[32, 1, CharID(4B), emote(1B)]` to all players on the current map.
* **Sub-Code 2 (`AC 32:2`)**: Triggers character poses (Sit, Rest, Special action poses). Broadcasts `[32, 2, CharID(4B), actionCode(1B)]`.
* **Sub-Code 3 (`AC 32:3`)**: Resets/cancels active emote or stance. Broadcasts `[32, 3, CharID(4B)]`.
