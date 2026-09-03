# First Quest Animations & Cutscene Protocol Specification

## Overview

This specification documents the cutscene, dynamic actor spawning, camera waypoint movements, and quest journal progression observed during the introductory quest line on the Ocean Star passenger liner and subsequent rescue on Kelan Beach.
The protocol was analyzed and verified directly from packet capture `ilkgorevinanimasyonlukisimlari.pcapng` (69 decrypted packets).

---

## 1. Intro Cutscene Dialogue Progression

The initial conversation occurs on board the Ocean Star liner between the player character and Captain (NPC ID `0x000A` = 10).

1. **Step 1 Dialogue (`Talk ID 95660` / `0x0175AC`)**:
   - Client sends AC 20 Sub 1: `14 01 0a 00` (Click Captain).
   - Server locks facing direction: AC 6 Sub 2: `06 02 01`.
   - Server delivers dialog step 1: `14 01 00 00 00 01 01 03 0a 00 01 00 00 00 00 ac 75 01`.
   - Text in `Talk.dat`: *"Hello, I'm captain here. Welcome to Ocean Star. We are to pass by South Ocean islands."*
   - Character plays animation / gesture: AC 183 Sub 11 (`b7 0b 09 02`).

2. **Step 2 Dialogue (`Talk ID 95661` / `0x0175AD`)**:
   - Server delivers dialog step 2: `14 01 00 00 00 02 01 03 0a 00 01 00 00 00 00 ad 75 01`.
   - Text in `Talk.dat`: *"Contact our service staff anytime if you have any question or suggestion. Wish you a pleasant journey."*

---

## 2. Dynamic Cinematic Actor Spawning & Camera Control

During cutscenes, temporary non-player actors are spawned dynamically on the client's screen, and the camera is decoupled from the player character.

### 2.1 Spawning Dynamic Scene Actor (AC 3 Sub 123 / 0x7B)
```
[0x03] [0x7B] [actor_id: 4B LE] [header: 2B] [x: 2B LE] [y: 2B LE] ... [name: PascalString] [flag: 0xFF] ...
Pkt #1913: 03 7b e2 03 00 04 ... Talia191 ...
```
- Accompanied by **AC 5 Sub 0** (`05 00 [actor_id] ...`) to synchronize equipment, hair color, and visual model.
- Camera is constrained via **AC 186 Sub 12** (`ba 0c 01 00 00 00 00`), triggering letterbox borders.
- Client confirms cutscene state with **AC 186 Sub 9** (`ba 09 01 00`).

### 2.2 Camera Waypoint & Actor Movement (AC 22 Sub 4 / 0x04)
The camera and cinematic actors move across predefined waypoint tracks.
Packet `16 04` contains sequential waypoint nodes:
```
[0x16] [0x04]
[point_1: index(2B) unk(2B) x(2B) y(2B) speed(2B) delay(2B)]
[point_2: ...]
...
Total 8 waypoints leading along the deck/shore.
```
- **AC 22 Sub 11** (`16 0b 06 00 ff ff`): Defines pan transition interpolation.
- **AC 22 Sub 12** (`16 0c 02 0b 00 05`): Configures camera dwell duration and zoom focal length.

---

## 3. Quest Journal & Step Progression (AC 24 / 0x18)

When the quest stage triggers, the server issues quest updates via Action Code 24:

| Action Code | Sub | Payload (Hex) | Meaning |
| :--- | :--- | :--- | :--- |
| **24 (0x18)** | **1 (0x01)** | `18 01 08 2f 01` | **Quest Accepted**: Quest ID `0x2F08` (12040), Step 1. |
| **24 (0x18)** | **5 (0x05)** | `18 05 61 00 01` | **Quest Log Journal Updated**: Journal Index `0x0061` (97), Active (State 1). |

---

## 4. Cutscene Conclusion & Control Restoration

1. The stage animation completes with **AC 22 Sub 12** (`16 0c 01 01 00 06`).
2. Server dispatches **AC 20 Sub 8** (`14 08`) to terminate dialogue state.
3. Server dispatches **AC 5 Sub 4** (`05 04`) to restore full player control and release camera lock.
