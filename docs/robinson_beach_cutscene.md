# Robinson Beach Rescue Cutscene Protocol (Map 10035)

## Overview
When a player arrives on South Island Beach (`Map 10035`) following the shipwreck cutscene without having started Quest `12040` (Robinson Rescue), an asynchronous cinematic timeline sequence is played.

---

## Cinematic Timeline Sequence

1. **Map Loading (AC 12 Sub 1)**:
   - Server sets `session.emote = 9` (lying unconscious on sand).
   - Sends `AC 32:2 [char_id, 9]`.
   - Sends `AC 5:30 [1, char_id, 0]` (immobilize player controls).
   - Sets `session.beach_cutscene_active = True`.
   - Spawns asynchronous timeline task `run_beach_cutscene_timeline`.

2. **Timeline Progression (`run_beach_cutscene_timeline`)**:
   - `+300ms`:
     - Sends `AC 20:8` (screen clear).
     - Sends `AC 22:11 [6, 0, 0xFF, 0xFF]` (camera pan across the beach).
     - Sends `AC 6:2 [1]` (cinema mode letterbox lock).
     - Sends `AC 20:11` & `AC 20:10`.
   - `+1200ms`:
     - Sends `AC 22:12 [2, 11, 0, 5]` (Robinson approaches and bends down over player).
     - Sends `AC 20:10`.
   - `+1500ms`:
     - Sets `session.beach_cutscene_active = False`.
     - Executes native event tree Event 1 on Map 10035 via `GLOBAL_EVE_INTERPRETER.try_execute(server, session, 1)`.

3. **Packet Absorption & Completion**:
   - Any client `AC 20 Sub 6` packets sent during `beach_cutscene_active == True` are absorbed and ignored to prevent premature frame skipping.
   - Upon dialogue tree completion:
     - Robinson returns to standing posture: `AC 22:12 [1, 1, 0, 6]`.
     - Player stands up: `AC 32:2 [char_id, 0]` (`session.emote = 0`).
     - Quest `12040` state is registered as `1` (In Progress).
     - Controls unlocked: `AC 6:2 [0]`, `AC 20:8`, `AC 5:4`.
