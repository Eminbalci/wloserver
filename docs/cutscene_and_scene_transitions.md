# Wonderland Online - Cutscene & Scene Transition System (AC 186, AC 20 & Beach Timeline)

## 1. Starter Ship Storm Cutscene Sequence (Map 10017 Event 11, PCAP [001]-[023])
* **Stage 1 (Captain Dialogue 1)**:
  * Cinema mode enabled (`AC 6:2 [1]`).
  * Step 1: TalkID 30124 (Portrait 3) -> `AC 20:1 [14 01 00 00 00 01 01 03 0a 00 01 00 00 00 00 ac 75 01]`.
* **Stage 2 (Captain Dialogue 2 & Movie Pre-Arm)**:
  * Client sends `AC 20:6` to advance.
  * Step 2: TalkID 30125 (Portrait 3) -> `AC 20:1 [14 01 00 00 00 02 01 03 0a 00 01 00 00 00 00 ad 75 01]`.
  * Pre-arms client movie subsystem with `AC 186:12 [ba 0c 01 00 00 00 00]`.
  * Client acknowledges readiness with `AC 186:9 [ba 09 01 00]`.
* **Stage 3 (Movie Playback Start & Thunder Event)**:
  * Client sends `AC 20:6` to close Dialogue 2.
  * Server sends movie start signal `AC 186:9 [ba 09 01 00 01 00 00 00 00]`.
  * Server sends `AC 20:1 Step 3` Thunder cinematic event -> `[14 01 00 00 00 03 05 00 00 00 02 7b 00 00 00 00 00 00]` (18 bytes).
  * Server sends SFX thunder sound packets (`AC 35:12`).
  * `session.playing_storm_cutscene = True`.
* **Stage 4 (Cutscene Finished & Teleport)**:
  * Client plays video for ~22 seconds, then sends `AC 20:6` upon completion.
  * Server responds with `AC 20:7` (Warp Out) and warps player to Rhode Island Beach (Map 10035 pos 1038, 2235).

## 2. Beach Arrival & Robinson Rescue State Machine (Map 10035, PCAP [036]-[066])
* **Step 1 (Map Load - AC 12:1)**:
  * Player lies unconscious on beach (`AC 32:2` Pose 9).
  * Controls immobilized (`AC 5:30 [5, 30, 1, char_id, 0]`).
  * Camera pans to Robinson (`AC 22:11 [6, 0, 0xFF, 0xFF]`), Cinema Mode on (`AC 6:2 [1]`), Sync locks (`AC 20:11`, `AC 20:10`).
* **Step 2 (Client AC 20:6 ACK)**:
  * Robinson approaches player (`AC 22:12 [2, 11, 0, 5]` + `AC 20:10`).
* **Step 3 (Client AC 20:6 ACK)**:
  * Robinson cutscene speech (`AC 20:1` TalkID 12008) + SFX (`AC 35:12`).
* **Step 4 (Client AC 20:6 ACK)**:
  * Add Quest 12040 (`AC 24:1 [8, 0x2F, 1]` + `AC 20:10`).
* **Step 5 (Client AC 20:6 ACK)**:
  * Sync tick (`AC 20:10`).
* **Step 6 (Client AC 20:6 ACK)**:
  * Set Quest Flag 97 (`AC 24:5 [0x61, 0, 1]` + `AC 20:10`).
* **Step 7 (Client AC 20:6 ACK)**:
  * Robinson walks back (`AC 22:12 [1, 1, 0, 6]` + `AC 20:10`).
* **Step 8 (Client AC 20:6 ACK)**:
  * Unlock Cinema & UI (`AC 20:8`).
  * Unlock player movement & stand up (`AC 5:4`).
  * Persist Quest 12040 State 1 to database.

## 3. Anti-Blinking NPC Architecture & Native eve.Emg Simulation (`server/gameserver.py`)
* **Problem**: In the WLO client engine, broadcasting `AC 22 Sub 2` movement packets from a server background loop to native map NPCs causes their sprite animation to reset to frame 0, creating rapid continuous blinking and locking their idle animations.
* **Fix**:
  * Native `eve.Emg` map NPCs are simulated client-side natively (patrol walks, idle animations, facing direction).
  * Disabled server-side `AC 22 Sub 2` background broadcast loop for native NPCs, preventing sprite flicker and restoring authentic client animation flow.

## 4. Player Animation & Emote Action Code 32 Protocol (`server/handlers/handle_32_emote.py`)
* **Protocol**:
  * `AC 32 Sub 1`: Standard Emote (Wave, Bow, Cheer, Laugh, Cry, etc.) -> `[32, 1, char_id (4B), emote_id (1B)]`
  * `AC 32 Sub 2`: Character Action Pose (Sit, Rest, Special Animation) -> `[32, 2, char_id (4B), action_id (1B)]`
  * `AC 32 Sub 3`: Reset / Cancel Emote -> `[32, 3, char_id (4B)]`
* **Fixes**:
  * Resolved double-read offset bug in `handle_32_emote.py`.
  * Added `exclude_session=session` on all `broadcast_to_map` calls for `AC 32:1`, `AC 32:2`, and `AC 32:3` so client micro-poses (turns/head turns) are not echoed back to the sender in an infinite spasm/packet spam loop.

## 5. Quest Flag Persistence & Warp Cutscene Error Handling
* **Fixes**:
  * `server/handlers/handle_12_warp.py`: Replaced unsafe dict access with `get_session_quest_state()` to support both list and dict quest structures without raising `AttributeError`.
  * `server/gameserver.py`: Fixed `_send_quest_flag` to call `self.save_player_to_db(session)` instead of non-existent `self.db.save_player(session)`.
  * `server/handlers/handle_20_interaction.py`: Cleared `on_interaction_complete` upon storm cutscene completion to prevent duplicate map warps.

