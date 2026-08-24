# NPC Store Transactions System

This document outlines the server-side NPC merchant transaction flows, including item purchases, item sales, gold balance synchronization, and client interface unlocking sequences.

---

## 1. Buying Items from NPC Merchants (Opcode 54)

Purchasing items from NPC shops uses **Opcode 54, Sub-opcode 3**.

### A. Purchase Request Parsing
When a player clicks "Buy" in an NPC merchant window, the client sends:
- `shop_id` (1 byte)
- `tab_id` (1 byte)
- `item_id` (2 bytes)
- `amount` (1 byte)

### B. Price Mapping & Gold Verification
The server defines item pricing constants for default store items:

| Item ID | Item Name / Description | Price (Gold) |
|---|---|---|
| `602` | Consumable | `50` |
| `603` | Consumable | `100` |
| `701` | Consumable | `200` |
| `702` | Consumable | `150` |
| `703` | Consumable | `250` |
| `27001` | Mount / Vehicle | `50` |
| `27005` | Mount / Vehicle | `100` |
| *Default* | Other items | `100` |

- **Verification**: The server verifies if the character has sufficient funds:
  $$\text{Gold}_{\text{Current}} \ge \text{Price} \times \text{Amount}$$

### C. Purchase Confirmation Sequence
If the funds are verified, the server:
1. Deducts the total gold and saves changes to the database.
2. Sends a gold sync packet (**Opcode 26, Sub-opcode 4**):
   - Payload: `[26, 4, gold (4 bytes)]`.
3. Adds the item to the inventory and sends an item addition packet (**Opcode 23, Sub-opcode 6**):
   - Payload: `[23, 6, item_id (2 bytes), amount (1 byte), padding (26 bytes)]`.
4. Sends the buy confirmation packet (**Opcode 54, Sub-opcode 3**):
   - Payload: `[54, 3, shop_id, tab_id, item_id, amount]`.

---

## 2. Selling Items to NPC Merchants (Opcode 30)

Selling inventory items to NPC merchants uses **Opcode 30, Sub-opcode 2**.

### A. Sell Request Parsing
- `slot_index` (1 byte): The inventory slot index (`1` to `50`) of the item.
- `amount` (1 byte): The quantity to sell (defaults to `1`).

### B. Selling Price Mapping
The server evaluates the item's unit value:

| Item ID | Sale Value (Gold) |
|---|---|
| `602` | `10` |
| `603` | `20` |
| `701` | `40` |
| `702` | `30` |
| `703` | `50` |
| *Default* | `10` |

### C. Sell Confirmation Sequence
If the slot contains a valid item:
1. Deducts the quantity sold and deletes the item block if quantity reaches 0.
2. Increments player gold: `session.gold += sell_price`.
3. Sends a gold sync packet (**Opcode 26, Sub-opcode 4**):
   - Payload: `[26, 4, gold (4 bytes)]`.
4. Updates the inventory slot quantity (**Opcode 23, Sub-opcode 9**):
   - Payload: `[23, 9, slot_index (1 byte), remaining_quantity (1 byte)]`.
5. Confirms the sale transaction (**Opcode 30, Sub-opcode 2**):
   - Payload: `[30, 2, total_sell_price (4 bytes), padding (28 bytes)]`.
6. Sends UI unlock packets to restore control to the client interface:
   - **Opcode 30, Sub-opcode 7** (Closes the selling progression dialog).
   - **Opcode 20, Sub-opcode 8** (Releases NPC interaction locks).
