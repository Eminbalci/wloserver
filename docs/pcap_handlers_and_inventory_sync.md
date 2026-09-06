# Authentic PCAP Handlers & Inventory Synchronization Architecture

## Overview
This document specifies the reverse-engineered packet protocols and handlers derived from real network captures (`C:\Users\muham\OneDrive\Masaüstü\paketler`) resolving the second-login inventory bug and integrating Props Keeper, Props Shop, Witch Doctor, and Item Mall Bonus subsystems.

---

## 1. Inventory Synchronization (AC 23 Sub 5, Sub 6 & Sub 8)

### Root Cause Analysis: The "All Slots Filled with Mini HP Potions" Bug
- **Symptom:** Opening the inventory bag UI displays valid starter items in slots 1–7, but slots 8 through 50 (all 43 remaining slots) are populated with duplicate Mini HP Potions (`34330`), each displaying `amount=1`.
- **Empirical Breakdown (PCAP & Binary Verification):**
  1. **Non-Stackable Item Overflow via `AC 23 Sub 6`:**
     - Item `34330` (Mini HP Potion) has a maximum stack limit of `1` in the game client binary (`Item.Dat`).
     - In `starter_items.json` and fallback definitions, Item #8 (`34330`) was configured with `count = 50`.
     - In authentic official capture (`oyunailkgirisvebedavaitemverilmesi.pcapng`), Item #8 is granted with **`count = 1`**.
     - When the server sent `AC 23 Sub 6` with `count = 50`, the client's internal inventory allocator placed 1 potion in slot 8, and popped the remaining 49 potions one by one across slots 9, 10, 11... through 50 until the 50-slot inventory bag was full! Items 9 and 10 in the starter pack were subsequently rejected because the bag was completely filled.
  2. **`AC 23 Sub 5` (Occupied Slots Only vs Empty Zero-Padding):**
     - Analysis of official PCAP `arkadaseklemeveonlinegozukme.pcapng` packet #19 confirms that authentic `AC 23 Sub 5` serializes **only occupied slots** (`occupied_count * 31 bytes + 2 header bytes`).
     - Empty slots are omitted from the packet entirely.
     - Each occupied entry is strictly 31 bytes:
       `[slot: 1B uint8, item_id: 2B uint16_LE, count: 2B uint16_LE, damage: 1B uint8, padding: 25 zeros]`.
  3. **`AC 23 Sub 6` (Item Delivery Notification):**
     - Exactly 33 bytes across all PCAP captures:
       `[23, 6, item_id: 2B uint16_LE, count: 1B uint8, padding: 28 zeros]`.
     - Standardized across starter item distribution, combat drops, chest rewards, shop purchases, and item mall claims.
  4. **Timing of Full Inventory Sync:**
     - Full inventory sync packet (`AC 23 Sub 5`) is dispatched at the conclusion of character login, guaranteeing that the client UI matches the persistent database state.

### AC 23 Sub 8: Slot State Update (33 bytes)
- **Official Capture Evidence (`yerdenitemalipcompounddaikiitemikaristirdim.pcapng`):**
  - Packet length: exactly 33 bytes (`17 08 [slot: 1B] [item_id: 2B LE] [count: 2B LE] [damage: 1B] [padding: 25 zeros]`).
  - Dispatched upon individual slot modifications, ground pickups, and compounding synthesis (`handle_23_items.py`).

---

## 2. Props Keeper & Vault Storage (AC 29 / 0x1D)

### Official Capture Evidence (`propskeeper.pcapng`)
- **Trigger:** Player interacts with Props Keeper NPC (TID 13012, 13013, 14134, or name containing `keeper`/`storage`).
- **S2C Packets:**
  1. `1d 06`: Opens client warehouse/storage interface.
  2. `29 05 [count: 1B] [entries: 31B each]`: Synchronizes stored items list.
  3. `14 09` / `14 08`: Releases dialogue lock.
- **Client Operations:**
  - `Sub 1`: Deposit item from inventory slot: `[1d, 01, inv_slot: 1B, amount: 2B LE]`.
  - `Sub 2`: Withdraw item from vault slot: `[1d, 02, vault_slot: 1B, amount: 2B LE]`.
- **Database Schema:** `char_bank_items` in `wlo_server.db` storing `(char_id, vault_slot, item_id, count, extra_data)`.

---

## 3. Props & Weapon Shop (AC 27 / 0x1B)

### Official Capture Evidence (`propsshop.pcapng`)
- **Trigger:** Player interacts with Shopkeeper NPCs (TID 13000 - 13999).
- **S2C Packets:**
  - `1b 03`: General / Props / Grocery shop catalog window.
  - `1b 04`: Weapon / Armor shop catalog window.
  - Followed by `14 09` and `14 08`.
- **Client Operations:**
  - `Sub 1`: Buy item `[1b, 01, shop_id: 1B, tab_id: 1B, item_id: 2B, amount: 1B]`.
  - `Sub 2`: Sell item `[1b, 02, slot_index: 1B, amount: 1B]`.

---

## 4. Witch Doctor & Clinic (AC 31 / 0x1F)

### Official Capture Evidence (`witchdoctor.pcapng`)
- **Trigger:** Player interacts with Witch Doctor / Clinic NPC (TID 14151, 14152).
- **S2C Packets:**
  - `1f 02 ff ff ff ff`: Full curse removal, party status cleanse, and HP/SP restoration.
  - `1f 07`: Witch Doctor blessing / purification.
  - `08 01 19 01 ...`: HP restoration broadcast (AC 8 Sub 1).
  - `08 01 1a 01 ...`: SP restoration broadcast (AC 8 Sub 1).

---

## 5. Item Mall Bonus System (AC 91 / 0x5B)

### Official Capture Evidence (`itemmallvebonuskismi.pcapng`)
- **C2S Request (Sub 1):** `5b 01 [category_id: 2B LE] [page: 1B]` (e.g. `5b 01 b0 de 00`).
- **S2C Catalog Response (Sub 2):** `5b 02 [category_id: 2B LE] [page: 1B] [items: 3B each (uint16 LE item_id + uint8 count)]`.
  - Exactly 38 bytes for 11 items.
- **C2S Claim (Sub 3):** `5b 03 [item_id: 2B LE]`. Deducts Bonus Points and delivers item via AC 23 Sub 6 popup.

---

## Edge Cases & Error Handling
1. **Unslotted / Duplicate Items:** `build_inventory_packet` dynamically assigns free slots (1-50) for any unslotted items prior to serialization.
2. **Exceeding Capacity:** Vault deposit prevents insertion past 50 items and informs the player with an in-game notice.
3. **Empty Inventory:** Serializes cleanly as a 2-byte header `[23, 5]` without throwing index or buffer errors.
