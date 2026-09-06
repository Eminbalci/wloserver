# Robinson Beach Rescue Cutscene Protocol (Map 10035)

## Overview
When a player arrives on Rhode Island Beach (`Map 10035`) following the shipwreck cutscene without having started Quest `12040` (Robinson Rescue), an authentic client-driven 7-stage cutscene state machine is executed. This eliminates the race conditions and animation locks caused by asynchronous sleep timers.

---

## Technical Specifications

### 1. Trigger Conditions
- **Handler**: `server/handlers/handle_12_warp.py` (`handle_12_warp`)
- **Condition**: `session.pending_beach_cutscene == True` or (`session.map_id == 10035` and `get_session_quest_state(session, 12040) == 0`).
- **State Initialization**:
  - `session.pending_beach_cutscene = False`
  - `session.beach_cutscene_active = True`
  - `session.beach_cutscene_stage = 1`
  - `session.dialogue_queue = []`
  - `session.emote = 9` (lying unconscious on sand)

### 2. Scene Setup Packets (PCAP Packets 31–45)
Upon receiving `AC 12 Sub 1` on beach landing, the server dispatches:
- `AC 23:138` (`17 8a`): Scene initialization.
- `AC 23:122` (`17 7a [char_id]`): Local character camera focus.
- `AC 23:221` (`17 dd 00`): Scene environment flags.
- `AC 22:4` (`16 04 ...`): 114-byte waypoint path table for NPC route coordination.
- `AC 23:4` (`17 04 ...`): 32-byte dynamic scene boundary descriptor.
- `AC 32:2` (`20 02 [char_id] 09`): Player posture set to lying unconscious (broadcast to map).
- `AC 23:76` (`17 4c [char_id]`): Actor positioning handshake.
- `AC 23:102` (`17 66`): Actor collision group flag.
- `AC 5:30` (`05 1e 01 [char_id] 00`): Client control immobilize lock.
- `AC 20:8` (`14 08`): Dialogue & UI window clear.
- `AC 22:11` (`16 0b 06 00 ff ff`): Camera pan initiation.
- `AC 6:2` (`06 02 01`): Letterbox cinematic mode enabled.
- `AC 20:11` (`14 0b`): Camera timeline synchronizer.
- `AC 20:10` (`14 0a`): Camera timeline advance signal.

---

## 7-Stage Client-Driven State Machine (`server/handlers/handle_20_interaction.py`)

The WLO client engine notifies the server of local animation and camera track completion via `AC 20 Sub 6` (`14 06`). The server deterministically steps through the 7 stages:

| Stage | Triggering Input | Actions / Packets Dispatched | Next Stage |
|---|---|---|---|
| **1: Robinson Approach** | `AC 20:6` (Camera pan completed) | Dispatches Robinson walk `AC 22:12 [16 0c 02 0b 00 05]` (broadcast to map) + sync tick `AC 20:10` | Stage 2 |
| **2: Robinson Dialogue** | `AC 20:6` (Robinson arrival) | Dispatches Robinson TalkID 12008 `(Gurgh? Gurgh?)` via `AC 20:1` (`14 01 00 00 00 01 05 00 00 00 01 e8 2e 00 00 00 00 00`) + Voice SFX `23 0c da 80 03 00 00` and `23 0c 77 8e 03 00 00` | Stage 3 |
| **3: Quest Acceptance** | `AC 20:6` (Player clicks Next) | Dispatches Quest 12040 Step 1 acceptance `AC 24:1 [18 01 08 2f 01]` + sync tick `AC 20:10` | Stage 4 |
| **4: Sync Tick** | `AC 20:6` (Client ACK) | Dispatches sync tick `AC 20:10` | Stage 5 |
| **5: Quest Flag 97** | `AC 20:6` (Client ACK) | Dispatches Quest Flag 97 active `AC 24:5 [18 05 61 00 01]` + sync tick `AC 20:10` | Stage 6 |
| **6: Robinson Return** | `AC 20:6` (Client ACK) | Dispatches Robinson stand and return walk `AC 22:12 [16 0c 01 01 00 06]` (broadcast to map) + sync tick `AC 20:10` | Stage 7 |
| **7: Conclusion** | `AC 20:6` (Robinson returned) | Closes UI `AC 20:8`, unlocks movement `AC 5:4`, disables cinema mode `AC 6:2 [0]`, resets player pose to 0 `AC 32:2 [char_id, 0]`, sets Quest 12040 Step 1 in session and database, clears cutscene active flag | Stage 0 (Idle) |

---

## Error Handling & Edge Cases

1. **Premature Input Protection**:
   - Client packets arriving during stage transitions are processed sequentially; out-of-order stages default safely to conclusion.
2. **Re-Entry & Persistence**:
   - `session.beach_cutscene_active` is reset to `False` and `beach_cutscene_stage = 0` upon Stage 7 completion.
   - Re-entering Rhode Island Beach with Quest 12040 state > 0 bypasses the cutscene entirely, immediately unlocking controls and UI via `handle_12_warp.py`.
3. **Database Consistency**:
   - `server.save_player_to_db(session)` is called immediately in Stage 7 to guarantee quest step persistence across server restarts and reconnections.
