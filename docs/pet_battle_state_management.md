# Pet Battle State Management System

This document outlines the server-side companion state transitions (BATTLE vs REST), map spawning protocols, map despawning broadcasts, and visual overlay updates implemented in `server/handlers/handle_19_action.py` and `server/handlers/handle_15_companion.py`.

---

## 1. Entering Battle State (Sub-opcode 1)

When a player requests their companion pet to assist them in combat, the client sends **Opcode 19, Sub-opcode 1** along with the target `pet_id` (4 bytes).

### A. Battle Toggling Flow
1. **Deduplication**: The server sweeps all other pets in the session, resetting their `in_battle` and `riding` flags to `False` (only one pet can be active at a time).
2. **Flag Modification**: Marks the selected companion's state as `in_battle = True`.
3. **Owner Confirmation Packet**:
   - Sends confirmation containing the active `pet_id`.
   - Payload: `[19, 1, pet_id (4 bytes)]`.

### B. Companion Spawning Broadcast (Opcode 15, Sub-opcode 4)
To render the summoned pet sprite next to the owner on other players' screens:
- **Broadcast**: The server dispatches Opcode 15, Sub-opcode 4 to the current map:
  - Payload: `[15, 4, char_id (4), pet_id (4), 0 (1), 1 (1), pet_name_string, weapon_id (2)]`.

### C. Visual Overlays Refresh
- **Broadcast**: Forces a refresh of the owner's appearance map nodes using **Opcode 5, Sub-opcode 8** carrying the owner's character ID.

---

## 2. Entering Rest State (Sub-opcode 2)

When a player recalls their companion pet, the client sends **Opcode 19, Sub-opcode 2**.

### A. Rest Toggling Flow
1. **Flag Modification**: Searches the companion array and resets the active pet's `in_battle` state to `False`.
2. **Owner Confirmation Packet**:
   - Sends confirmation: `[19, 2]`.

### B. Companion Despawning Broadcast (Opcode 19, Sub-opcode 7)
To remove the pet sprite from the map for all nearby players:
- **Broadcast**: The server transmits Opcode 19, Sub-opcode 7:
  - Payload: `[19, 7, char_id (4 bytes)]`.

### C. Visual Overlays Refresh
- **Broadcast**: Refreshes player visual state overlays using **Opcode 5, Sub-opcode 8**.
