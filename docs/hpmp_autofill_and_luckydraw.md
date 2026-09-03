# HP/MP Auto-Recovery Button & Lucky Draw System Protocol

This document details the reverse-engineered network protocol and system implementation for:
1. **HP/MP Auto-Fill Button (AC 23 Sub 15 / AC 23 Sub 208)**: Live capture `hpmpdoldurmabutonu.pcapng`
2. **Lucky Draw Wheel (AC 104 Sub 1 / AC 23 Sub 6)**: Live capture `luckydrawdatalari.pcapng`

---

## 1. HP/MP Auto-Fill Quick Recovery (Action Code 23, Sub-opcode 15)

In the official client interface, clicking the HP or SP refill icon on the character or pet HUD sends an authentic **AC 23 Sub 15** request to tap into the player's active Rice Ball sustenance pool.

### A. Client Action Command (`C -> S AC 23 Sub 15`)
- **Size**: 6 bytes
- **Structure**:
  ```
  Offset  Type       Description
  -------------------------------------------------------------
  0..1    uint8[2]   Action Code (23), Sub-opcode (15)
  2       uint8      stat_type: 8 = HP, 9 = SP
  3       uint8      target_type: 1 (Self / Companion)
  4..5    uint16_LE  slot: 0 = Character, >0 = Companion Pet Slot
  ```

### B. Server Stat Synchronization (`S -> C AC 8 Sub 1 / Sub 2`)
When the heal amount is deducted from the sustenance pool:
- **Player Recovery (`AC 8 Sub 1`)**:
  - Size: 12 bytes
  - Payload: `[0x08, 0x01, stat_id (uint16_LE), new_val (uint32_LE), 0x00 * 6]`
  - `stat_id = 0x0119` (281) for HP, `0x011a` (282) for SP.
- **Pet Recovery (`AC 8 Sub 2`)**:
  - Size: 15 bytes
  - Payload: `[0x08, 0x02, 0x04, slot (uint8), 0x00, stat_id (uint16_LE), new_val (uint32_LE), 0x00 * 6]`

### C. Sustenance Pool HUD Display (`S -> C AC 23 Sub 208`)
The server immediately informs the client HUD of the remaining sustenance buffer:
- **Size**: 8 bytes
- **Payload**:
  ```
  [0x17, 0xD0, 0x01, stat_type (uint8), remaining_pool (uint32_LE)]
  ```
  - `stat_type = 8`: Remaining HP auto-heal buffer
  - `stat_type = 9`: Remaining SP auto-heal buffer

---

## 2. Lucky Draw Mini-Game & Wheel Spin (Action Code 104, Sub-opcode 1)

Clicking the spin button on the Lucky Draw wheel requests a play from the game server.

### A. Client Spin Request (`C -> S AC 104 Sub 1`)
- **Size**: 2 bytes
- **Payload**: `[0x68, 0x01]` (`[104, 1]`)

### B. Server Validation & Deductions
1. **Inventory Full Check**: The server validates that the player has fewer than 50 occupied slots. If inventory is full, spin is rejected with prompt: `"Inventory full. Cannot use Lucky Draw."`.
2. **Payment Priority**:
   - 20 IM Points (deducted and synchronized via `AC 34:1` and `AC 75:3`).
   - 1 IM Token / Ticket.
   - 10,000 Gold.

### C. Authentic Stop Packet (`S -> C AC 104 Sub 1`)
Informs the client GUI which category and slot index the wheel pointer should decelerate and stop on:
- **Size**: 5 bytes
- **Payload**:
  ```
  Offset  Type   Description
  -------------------------------------------------------------
  0..1    uint8  0x68 (104), 0x01 (Sub 1)
  2       uint8  0x02 (Protocol discriminator)
  3       uint8  category / tier (e.g., 2, 3)
  4       uint8  slot_index (e.g., 1..8)
  ```

### D. Authentic Item Delivery Packet (`S -> C AC 23 Sub 6`)
Immediately grants the won prize into the player's inventory:
- **Size**: 33 bytes
- **Payload**:
  ```
  [0x17, 0x06, item_id (uint16_LE), count (uint16_LE), 0x00 * 27]
  ```

### E. Jackpot Celebration
For top tier prizes (Zodiac Chest `48033`, Space UFO `48013`, Reborn Cape `23001`):
- Plays map-wide fireworks: `AC 5 Sub 5` with skill `60050`.
- Broadcasts announcement: `[Lucky Draw Jackpot] Congratulations to {char_name} for winning '{prize_name}' on the Lucky Wheel!`.
