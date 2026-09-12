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
| 5 .. 28     | 24 B | bytes     | Attributes / Spar Sockets  |
+-------------------------------------------------------------+
```

### Full Inventory Synchronization Implementation
Located in `GameServer.build_inventory_packet()`:
- Unoccupied slots can be omitted or zero-padded depending on client handshake version.
- Overfilled non-stackable items trigger auto-drop packets (`AC 23 Sub 2`).

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
