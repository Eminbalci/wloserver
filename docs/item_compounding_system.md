# Item Compounding System

This document outlines the server-side general alchemy item mixing, recipe validation, material consumption, and inventory refresh sequences implemented in `server/handlers/handle_54_action.py`.

---

## 1. Item Compounding Requests (Opcode 54)

Mixing multiple items to synthesize new equipment or ingredients uses **Opcode 54, Sub-opcode 30**.

### A. Request Parsing
When a player initiates compounding inside the alchemy UI panel, the client sends:
- `compound_id` (2 bytes): Unique ID of the target recipe.

### B. Material Verification
The server runs validations against the player's active inventory:
1. Loads recipe details from the static database: `server.get_compound_recipe(compound_id)`.
2. Loops through the required materials list:
   - Evaluates if the sum of matching items in the inventory satisfies the recipe requirement:
     $$\sum \text{Quantity}_{\text{Owned}} \ge \text{Quantity}_{\text{Required}}$$
3. **If Ingredients are Missing**: Compounding fails. The server sends a warning alert back to the player:
   - System alert: `"Compound failed! Missing required materials."`.

---

## 2. Recipe Execution & Refresh Flows

If validation succeeds, the server completes the synthesis:

### A. Material Deductions
- Loops through inventory slots containing the required items.
- Decrements quantities or completely deletes the item blocks if the quantities drop to `0`.

### B. Outcome Registration & Client Refreshes
- Adds the synthesized outcome item (`result_item`) to the player's inventory using `add_item_to_inventory`.
- Saves the updated character profile to the SQLite database.
- **Inventory Sync**: Transmits a full inventory refresh packet (`server.build_inventory_packet`) to clean up client slot maps.
- **Success Announcement**: Pushes a green success alert text to the chat log:
  - System alert: `"Compound success! Created {result_amount}x Item {result_item}!"`.
