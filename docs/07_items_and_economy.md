# Items, Inventory & Economic Systems

This document describes inventory serialization, equipment slots, alchemy compounding formulas, the Item Mall subsystem, player stalls, bank vault storage, and trading mechanics.

## Inventory Architecture & Serialization (AC 23 Sub 5)

Wonderland Online employs fixed-stride binary structures for inventory transmission:
- Total capacity: 50 item slots per character.
- Client expects 29-byte or 31-byte serialized records per occupied slot.

```
+-------------------------------------------------------------+
| Byte Offset | Size | Type      | Field Description          |
+-------------------------------------------------------------+
| 0           | 1 B  | uint8     | Slot Index (1 .. 50)       |
| 1 .. 2      | 2 B  | uint16_le | Item ID (1 .. 65535)       |
| 3           | 1 B  | uint8     | Quantity / Stack Count     |
| 4           | 1 B  | uint8     | Durability Decay / Damage  |
| 5 .. 30     | 26 B | bytes     | Padding / Spar Sockets     |
+-------------------------------------------------------------+
```
Total record size per occupied slot: 31 bytes (`PacketWriter: 1 header byte AC 23, 1 byte Sub 5 + (count * 31 bytes)`), matching C# `Inventory.cs:528-532` (`Pack8(slot), Pack16(ItemID), Pack8(Ammt), Pack8(Damage), PackArray(26 zeros)`).

### Full Inventory Synchronization Implementation
Located in `GameServer.build_inventory_packet()`:
- Encodes occupied slots sequentially, strictly formatting `amount` as `uint8` and preserving the 26-byte trailing padding.
- Unoccupied slots are omitted, allowing the official client to update its visual grid cleanly without packet bloat.

## Authentic Starter Items Pack Architecture

Upon new character creation (`handle_9_char_creation.py` / `AC 9 Sub 1`) or initial login fallback (`gameserver.py:commence_login` for level 1 characters without starter items), the server grants the canonical 8-item starter bundle:

| Order | Item ID | Item Name | Count | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **34038** | Notepad | 1 | Beginner guide and notepad |
| 2 | **34058** | Remote Control | 1 | Auto-combat assistant controller |
| 3 | **32176** | Fugu Hot Pot | 50 | Full recovery food |
| 4 | **34014** | Tao Rice Ball | 10 | Pet and character food |
| 5 | **34026** | Protective EXP Pill | 5 | Prevents EXP loss upon death |
| 6 | **34169** | Bamboo Dragonfly | 1 | Starter flying mount vehicle |
| 7 | **34190** | 10X Holy EXP Potion | 3 | Boosts experience gain |
| 8 | **34253** | Training Ticket | 5 | Training island pass |

### Delivery Protocol & Duplication Prevention
- **Silent Internal Delivery (`send_packets=False`)**: Matching C# `StarterPackManager.DeliverToPlayer(tp, sendData: false)`, starter items are inserted directly into `session.inventory` during character creation without dispatching intermediate `AC 23 Sub 6` ("Item Acquire Notice") frames.
- **Single-Dispatch Invariant for Full Inventory Synchronization (`AC 23 Sub 5`)**: The official WLO game client (`aLogin.exe`) does not wipe existing inventory slots upon receiving `AC 23 Sub 5`; rather, it accumulates and adds incoming item quantities into existing visual slots. If `build_inventory_packet()` is transmitted more than once during the login handshake (e.g. before map warp and after fallback delivery), every item in the player's inventory doubles client-side (e.g. Notepad 1 -> 2, Remote Control 1 -> 2, Fugu Hot Pot 50 -> 100). Therefore, `commence_login()` enforces a strict single-dispatch rule: the fallback starter pack delivery check runs prior to packet serialization, and `AC 23 Sub 5` is transmitted exactly once.
- **Client Desync Elimination**: In the official WLO client, transmitting `AC 23 Sub 6` for items already in the inventory causes client-side double-counting (e.g. quantity 1 rendering as 2) and causes high-count non-stackable or consumable items (such as obsolete item `34330`) to cascade across all 50 slots as individual single items.
- **Obsolete / Invalid Item Purge**: Any legacy starter configurations containing non-authentic or obsolete IDs (`23050, 23051, 48050, 57001, 34542, 21742, 34330, 34258, 34332`) are automatically purged from SQLite (`game_starter_items`) on boot and reseeded with the authentic 8-item roster.


## Equipment Slots & Stat Application (AC 23 Sub 11)

Characters have 6 dedicated equipment slots:
1. **Headgear** (Slot 0)
2. **Armor / Body** (Slot 1)
3. **Backpack / Cape / Wings** (Slot 2)
4. **Gloves / Armguards** (Slot 3)
5. **Boots / Footwear** (Slot 4)
6. **Weapon / Hand** (Slot 5)

Serialized via `AC 23 Sub 11` using 19-byte blocks per equipment:
- Item ID (`uint16_le`) + Damage (`uint8`) + 16 attribute bytes.
- Stats (ATK, DEF, MATK, MDEF, SPD) from equipped items dynamically modify character battle attributes.

## Compounding & Alchemy Synthesis Engine

Compounding synthesizes raw materials into advanced equipment, potions, or components:
- Loaded from `data/Compound.dat` (167 base recipes), `data/Compound2.dat` (773 extended recipes), and `data/Formula.dat`.
- Handled via `AC 23 Sub 14` / `AC 23 Sub 122` (interactive synthesis cycle).

### Compounding Calculation Mechanics
1. **Material Rank Determination**:
   - Each item possesses a material rank ($R \in [1 \dots 50]$) and elemental class (Wood, Iron, Copper, Gold, Leather, Grass, Stone, Crystal).
2. **Formula**:
   $$\text{Result Rank} = \lfloor \frac{R_1 + R_2}{2} \rfloor + \text{AlchemyBonus} + \text{RandomDelta}$$
3. **Alchemy Skill Modifiers**:
   - Primary Alchemy: +1 Rank bonus.
   - Junior Alchemy: +2 Rank bonus.
   - Senior Alchemy: +3 Rank bonus.
   - Alchemy Books (I, II, III, IV): Further reduce failure decay and increase target rank probability.

## Item Mall & Bonus Shop (AC 75 / AC 91)

The in-game Item Mall operates via TCP Port 6414/6416:
- **Points Mall (`AC 75 Sub 1`)**: Requires IM Points purchased with real currency.
- **Bonus Mall (`AC 75 Sub 10`)**: Requires Bonus Points earned from in-game events and mall spending.
- **Dual-Currency Checkout**: Validates player balances in `users` and `characters` tables before debiting points and dispensing items.
- **Bonus Reward Catalog (`AC 91 Sub 1/2/3`)**: Direct point redemption for consumables and exclusive bags.

## Banking & Warehouse Storage

### 1. Props Keeper Warehouse (AC 29 Sub 6/1/2)
- NPC storage keeper in major towns (Kelan, Welling, Holy Village).
- Allows players to deposit and withdraw items without occupying inventory space.
- Max capacity: 50 warehouse slots per character.

### 2. Town Bank Vault (`server/bank_system.py`)
- High-capacity gold storage preventing gold loss upon combat defeat.
- Deposit / withdraw via bank dialogues or direct AC 29 transactions.
- Supports inventory expansion bags (`Item #38001`).

## Player Trading & Street Stalls

### 1. P2P Secure Trade (AC 25)
Two-phase commit trading protocol:
1. `AC 25 Sub 1`: Invitation request & acceptance handshake.
2. `AC 25 Sub 3`: Slot offer updates & item preview.
3. `AC 25 Sub 5`: Trade lock confirmation (prevents item swap exploits).
4. `AC 25 Sub 6`: Final trade confirmation. Server atomically swaps inventories inside a database transaction.

### 2. Player Street Stalls (AC 40)
- Allows players to deploy merchant stalls in public maps.
- Supports selling items for Gold and buying requested items.
- Other players browse stall stock via `AC 40 Sub 1` and purchase directly via `AC 40 Sub 2`.

## Sustenance & Repair Systems

- **Sustenance Buffer (`server/sustenance_system.py`)**: Consuming Rice Balls (`Item #30025`) or specialized sustenance dishes grants an auto-healing reservoir (e.g. 50,000 HP / SP) that instantly replenishes HP/SP after battles without requiring potion clicks.
- **Equipment Durability & Repair (`server/repair_system.py`)**: Items lose durability in battle. Blacksmith NPCs and Spanner tools repair durability decay.
