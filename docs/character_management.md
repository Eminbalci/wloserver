# Character Management System

This document outlines the server-side character creation parameters, name uniqueness validations, starting stat check algorithms, and secure deletion packet flows.

---

## 1. Character Creation (Opcode 9)

When a player requests to create a new character, the client dispatches **Opcode 9, Sub-opcode 1** containing style selections and starting attribute allocations.

### A. Name Availability Checks (Sub-opcode 2)
- **Length Constraint**: The character name must be between **4 and 14 characters** long.
- **Uniqueness Check**: The server runs `server.db.is_name_taken(name)` against the SQLite database.
- **Response Packet**:
  - Pushes **Opcode 9, Sub-opcode 3** containing a status byte:
    - `0`: Name is available.
    - `1`: Name is taken or invalid.

### B. Starting Stats Integrity Checks
The starting attributes are received in the following order: `str`, `agi`, `wis`, `int`, and `con`.
- **Validation Rule**:
  $$\text{STR} + \text{AGI} + \text{WIS} + \text{INT} + \text{CON} \le 5$$
- **Hacked Packet Detection**: If the sum exceeds `5`, or if any stat value is negative, the server raises a warning: `"[Char] Hacked packet detected! Stat sum exceeds 5"`. The server immediately drops the request and replies with error code `30` (`[0, 30]`).

### C. Character Slot Determination
Each user account supports up to 2 character slots:
1. Checks if slot 1 is occupied: `SELECT id FROM characters WHERE user_id = ? AND slot = 1`.
2. If slot 1 is free, assigns the new character to **Slot 1**.
3. If slot 1 is occupied, assigns the new character to **Slot 2**.

---

## 2. Character Deletion (Opcode 35)

When deleting a character, the client sends **Opcode 35, Sub-opcode 2** along with the targeted `slot` and `password` string.

### A. Password Verification
- Compares the incoming password against the registered character cipher (`session.cipher`).
- **If Cipher Matches**:
  - Invokes `server.db.delete_character(char_id)` to purge character records.
  - Sends a sequence of UI clean-up packets to refresh client lists.
- **If Cipher Mismatches**:
  - Sends failure response: `[35, 2, 3, slot]`.

### B. UI Deletion Packet Sequence
On successful character deletion, the server must transmit the following packet sequence to clear client interface nodes:

| Packet Bytes | Opcode | Sub-opcode | Parameter | Description |
|---|---|---|---|---|
| `[24, 5, 53, 0, 0]` | `24` | `5` | `53` | Clears character selection slot visuals |
| `[24, 5, 52, 0, 0]` | `24` | `5` | `52` | Clears companion list overlays |
| `[24, 5, 54, 0, 0]` | `24` | `5` | `54` | Clears equipment sprite caches |
| `[24, 5, 183, 0, 0]` | `24` | `5` | `183` | Resets local character options |
| `[20, 8]` | `20` | `8` | - | Releases dialogue interaction locks |
| `[35, 2, 1, slot]` | `35` | `2` | `1` | Confirms successful deletion for slot index |
