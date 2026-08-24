# Crafting & Production Systems

This document outlines the server-side crafting validations, material deduction, progress indicators, timers, and asynchronous production routines implemented in `server/handlers/handle_64_crafting.py`.

---

## 1. Crafting Flow & Validations (Opcode 64)

Manufacturing is managed through **Opcode 64** (0x40).

### A. Bathing State Check
Before starting a craft, the server checks if the player is currently bathing:
- **If Bathing**: The action is blocked. The server notifies the player using a system warning message: `"Bathing, unable to make"`.

### B. Craft Request Parsing (Sub-opcode 1)
When starting a recipe, the client transmits:
- `recipe_id` (2 bytes)
- `craft_amount` (2 bytes)
- `materials` (5 slots of 2 bytes each: 1 byte slot index, 1 byte quantity)

### C. Material Consumption & Deductions
For each non-zero material slot, the server:
1. Calls `remove_item_at_slot` to deduct item amounts.
2. Sends the inventory deduction packet (**Opcode 23, Sub-opcode 9**) to update slot quantities on the client:
   - Deduct: `[23, 9, slot_index (1 byte), quantity (1 byte)]`.

### D. Progress Indicator & Timer Controls
To animate the client's crafting progress wheel, the server returns two packets:

1. **Crafting Confirmation (Opcode 64, Sub-opcode 1)**:
   - Starts the progress bar wheel.
   - Payload: `[64, 1, 1, 0x948B (2 bytes), 0 (4 bytes), 1 (1 byte)]`.
2. **Timer Packet (Opcode 64, Sub-opcode 10)**:
   - Tells the client how long to run the crafting wheel animation.
   - Payload: `[64, 10, 0, 0 (4 bytes)]`.

---

## 2. Asynchronous Production Completion

The server spawns an asynchronous `finish_crafting` background task to handle recipe processing:

1. **Delay Sleep**: The task yields execution (`asyncio.sleep(delay)`) for the duration of the recipe's craft time.
2. **Inventory Insertion**: Adds the finished items into the character's inventory slot.
3. **Completion Signal (Opcode 64, Sub-opcode 2)**:
   - Closes the progress wheel UI.
   - Payload: `[64, 2, 1]`.
