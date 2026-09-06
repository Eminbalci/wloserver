# New Client Handlers Integration & Technical Specifications

## 1. Overview
This document specifies the architecture, packet payloads, subcodes, error handling, and parameter mappings for the 10 new protocol handlers created to cover 100% of client-sent Action Codes from `decompiled/aLogin.exe.1.c`.

---

## 2. Handler Technical Specifications

### 2.1 `handle_24_quest.py` (AC 24)
* **File:** [`server/handlers/handle_24_quest.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_24_quest.py)
* **Action Code:** 24 (`0x18`)
* **Subcodes:**
  * `Sub 5`: Quest State / Status synchronization from client.
    * **Parameters:** `quest_id (uint16)`, `req_state (uint8)`.
    * **Returns:** AC 24 Sub 5 `[24, 5, quest_id (2B), state (1B)]`.
  * `Sub 1 / 2`: Quest Step update acknowledgment.
    * **Returns:** AC 24 `[24, sub, quest_id (2B), step (1B)]`.
  * `Sub 6`: Pinned Quest tracker HUD update.
* **Exceptions & Edge Cases:** Fallback to global journal refresh if `quest_id == 0`.

### 2.2 `handle_85_instance.py` (AC 85)
* **File:** [`server/handlers/handle_85_instance.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_85_instance.py)
* **Action Code:** 85 (`0x55`)
* **Subcodes:**
  * `Sub 1`: Enter multiplayer dungeon instance (`instance_id uint16`).
    * **Returns:** Warps player to instance map and sends AC 89 Sub 1 / AC 85 Sub 1.
  * `Sub 2`: Leave / Abandon instance.
    * **Returns:** AC 85 Sub 2 `[85, 2, 1]` and warps player back to Kelan Village (Map 10000).
  * `Sub 4`: Ready check state acknowledgment.
  * `Sub 10`: Countdown timer & heartbeat synchronization.
  * `Sub 11`: Claim instance completion rewards (Gold, EXP, and rare reward items).

### 2.3 `handle_82_marriage.py` (AC 82 & AC 68)
* **File:** [`server/handlers/handle_82_marriage.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_82_marriage.py)
* **Action Codes:** 82 (`0x52`), 68 (`0x44`)
* **Subcodes:**
  * `AC 82 Sub 10`: Church altar wedding ceremony execution (`btn_Marry_1`).
    * **Returns:** Map-wide fireworks and bell celebration animation (`AC 5:5: 60050`) and AC 82 Sub 10 confirmation.
  * `AC 82 Sub 3`: Proposal to target player (`target_id uint32`).
  * `AC 82 Sub 4`: Proposal acceptance or rejection.
  * `AC 82 Sub 8`: Couple action / Ring exchange acknowledgment.
  * `AC 68 Sub 1`: Couple teleportation directly to spouse coordinates.
  * `AC 68 Sub 2 / 3`: Couple heart affinity emote and status synchronization.

### 2.4 `handle_26_reborn.py` (AC 26)
* **File:** [`server/handlers/handle_26_reborn.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_26_reborn.py)
* **Action Code:** 26 (`0x1A`)
* **Subcodes:**
  * `Sub 3`: Rebirth job class awakening (Killer, Warrior, Knight, Wit, Priest, Seer).
    * **Parameters:** `job_id (uint8)` (1–6).
    * **Returns:** Rebirth Cape, visual ascension effect (`AC 5:5: 60050`), and AC 26 Sub 3 `[26, 3, success (1B)]`.
  * `Sub 2`: Potential attribute stat points allocation (`stat_type uint8`, `points uint16`).

### 2.5 `handle_45_vehicle.py` (AC 45)
* **File:** [`server/handlers/handle_45_vehicle.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_45_vehicle.py)
* **Action Code:** 45 (`0x2D`)
* **Subcodes:**
  * `Sub 4`: Railway track minecart boarding / dismounting (`rail_H3`).
    * **Parameters:** `track_id (uint16)`, `state (uint8)`.
    * **Returns:** AC 15 Sub 10 mount broadcast and AC 45 Sub 4 ACK.
  * `Sub 8`: Railway route navigation waypoint ACK.

### 2.6 `handle_184_audio.py` (AC 184)
* **File:** [`server/handlers/handle_184_audio.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_184_audio.py)
* **Action Code:** 184 (`0xB8`)
* **Subcodes:**
  * `Sub 1`: Interactive object sound playback (`sound\\wav0150.wav`).
    * **Parameters:** `sound_id (uint16)`.
    * **Returns:** Broadcasts AC 184 Sub 1 to all players on the current map.

### 2.7 `handle_16_settings.py` (AC 16 & AC 55)
* **File:** [`server/handlers/handle_16_settings.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_16_settings.py)
* **Action Codes:** 16 (`0x10`), 55 (`0x37`)
* **Subcodes:**
  * `AC 16 Sub 2 / 3 / 4`: BGM volume, SFX volume, and graphics display sliders.
  * `AC 55 Sub 1`: Modal dialog confirmation (`btn_ok_1`, `btn_cancel`).

### 2.8 `handle_84_viewport.py` (AC 84)
* **File:** [`server/handlers/handle_84_viewport.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_84_viewport.py)
* **Action Code:** 84 (`0x54`)
* **Subcodes:**
  * `Sub 1`: Viewport entity visibility matrix refresh query.

### 2.9 `handle_74_action.py` (AC 61, 69, 70, 74)
* **File:** [`server/handlers/handle_74_action.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_74_action.py)
* **Action Codes:** 61 (`0x3D`), 69 (`0x45`), 70 (`0x46`), 74 (`0x4A`)
* **Subcodes:**
  * `AC 74 Sub 2`: Minimap target waypoint pin (`map_x uint16`, `map_y uint16`).
  * `AC 70 Sub 7`: Target lock focus indicator (`target_id uint32`).
  * `AC 69`: Entity tooltip inspection query (`entity_id uint32`).
  * `AC 61 Sub 1`: Window idle / background focus state (`state uint8`).

### 2.10 `handle_auxiliary_actions.py` (AC 7, 28, 51, 66, 90, 199)
* **File:** [`server/handlers/handle_auxiliary_actions.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_auxiliary_actions.py)
* **Action Codes:** 7 (`0x07`), 28 (`0x1C`), 51 (`0x33`), 66 (`0x42`), 90 (`0x5A`), 199 (`0xC7`)
* **Subcodes:**
  * `AC 7 Sub 0`: Client keepalive heartbeat ping ACK.
  * `AC 28 Sub 1`: Crafting recipe progress query.
  * `AC 51 Sub 1`: Quick action bar hotkey slot binding.
  * `AC 66 Sub 11`: Guild / Group war challenge invitation.
  * `AC 90 Sub 1`: Extended inventory / Storage tab switch.
  * `AC 199 Sub 3`: Custom client macro hotkey bindings.
