# Mini-Games & Item Mall Systems

This document outlines the server-side Item Mall (Nesne Market) point validations, Lucky Draw (Lucky Wheel) spin mechanics, categories, and jackpot broadcasts.

---

## 1. Item Mall System (Opcode 34)

The Item Mall allows players to purchase premium items using point balances.

### A. Purchase Validation Flow
1. **Balance Check**: When buying an item, the server compares the player's available point balance against the item point cost:
   $$\text{Points}_{\text{Available}} < \text{Cost}_{\text{Item}}$$
2. **If Insufficient**: The purchase is cancelled, and the server returns a system alert dialog to the client: `"Not enough Points"`.
3. **If Sufficient**:
   - Deducts the item cost from the player's points balance.
   - Triggers item delivery: adds the item to the player's inventory.
   - Saves the updated character profile to the SQLite database.
   - Pushes an inventory update packet (**Opcode 23, Sub-opcode 6**) to register the item on the client side.

---

## 2. Lucky Draw (Lucky Wheel) System (Opcode 104)

The Lucky Draw system allows players to spin a prize wheel for rewards.

### A. Spin Requests (Sub-opcode 1)
When the client requests a spin, the server performs the following actions:
1. **Inventory Space Validation**: Checks if the player has at least 1 free slot in their inventory. If full, cancels spin and returns alert: `"Inventory full. Cannot use Lucky Draw."`.
2. **Prize Selection**: Randomly selects a reward from the prize pool.

### B. Prize Mappings & Categories

The Lucky Draw uses categories and indices to tell the client where the wheel spinner should stop:

| Item Name | Item ID | Category | Index | Description |
|---|---|---|---|---|
| **Holy Water** | `100653` | `5` | `1` | Common consumable |
| **Tear of Angel** | `100652` | `5` | `2` | Common consumable |
| **Tear of Angel** | `100652` | `4` | `3` | Alternative tier reward |
| **UFO** | `48013` | `3` | `4` | **Jackpot Mount!** |
| **Memory Card** | `100651` | `2` | `5` | Rare consumable |

### C. Spin Result Packets
Once a prize is rolled, the server transmits two sequential packets to sync the reward:

1. **Item Delivery Packet (Opcode 23, Sub-opcode 6)**:
   - Registers the item inside the client inventory.
   - Payload: `[23, 6, item_id (4 bytes), quantity (1 byte), padding (26 bytes)]`.
2. **Lucky Draw Stop Packet (Opcode 104, Sub-opcode 1)**:
   - Controls the graphical wheel animation and index stopping.
   - Payload: `[104, 1, 2, category (1 byte), index (1 byte)]`.

### D. Jackpot Broadcast
If a player successfully wins the **UFO** (`48013`) mount, the server triggers a map-wide system announcement to broadcast the victory:
- **System Announcement Packet**: `[23, 57, 0, announcement_string]` containing:
  `"Congratulations! {player_name} won a UFO from Lucky Draw!"`.
