# Wonderland Online - Item Mall Catalog & Customization System

## Overview
The Wonderland Online Item Mall subsystem manages point-based digital merchandise, catalog synchronization across both TCP ports (`6416` and `6414`), multi-tab category mapping, dynamic SQLite/JSON persistence, and administrator GUI configuration.

---

## 1. Network Protocol Specifications

### A. Dedicated Port 6416 TCP Catalog Service
- **Purpose**: Authenticates and feeds initial catalog metadata to client binary `aLogin.exe` (`FUN_0025a684`).
- **Binary Format**:
  - `[0]` Opcode `0xC9`
  - `[1-2]` Header `0x00 0x01`
  - Per item: `[ItemID (uint16_LE), HotFlag (uint8)]` (`2` = Hot/Special, `3` = Standard)

### B. In-Game Port 6414 Packets

#### 1. AC 75 Sub 1 (Item Catalog Matrix)
- **Header**: `[75, 1, ItemCount (uint16_LE)]`
- **Per Item (10 Bytes)**:
  - `[0-1]` `item_id (uint16_LE)`: 16-bit numeric item identifier matching `Item.dat`.
  - `[2]` `subcategory_id (uint8)`: Tab subcategory index (default `1`).
  - `[3-4]` `base_price (uint16_LE)`: Original/list price in IM Points.
  - `[5]` `discount_percent (uint8)`: `100` = Regular Price (clean, no strikethrough); `<100` = On-Sale multiplier % displaying strike-through discount.
  - `[6]` `badge_tag (uint8)`: `0` = Clean/Normal, `1` = `NEW` starburst badge overlay, `2` = `HOT` flame badge overlay.
  - `[7]` `category_id (uint8)`: Category tab selector (1..7).
  - `[8-9]` `point_cost (uint16_LE)`: Effective purchase cost deducted from balance.

#### 2. AC 75 Sub 3 (Personal IM Balance Sync)
- **Payload**: `[75, 3, Points (uint32_LE), BonusPoints (uint32_LE), ItemID (uint16_LE), Count (uint8)]`

#### 3. AC 75 Sub 4 & Sub 5 (Tab Switching & Purchase)
- Client sends category switch `[75, 4, cat_id]` or buy request `[75, 5, item_id (2B_LE), quantity (1B)]`.
- Server validates points, executes atomic `server.grant_item(...)`, updates DB, and dispatches AC 75:3 and system notice.

---

## 2. Category Tab Mappings (1..7)

| Category ID | Category Name | Description | Example Items |
| :--- | :--- | :--- | :--- |
| **1** | **Hot** | Featured mount vehicles, popular consumables, diamonds | Mecha Dragon (48050), Alien UFO (48013), Submarine (48033) |
| **2** | **Armory** | Defensive gears, armors, robes, shields, helms, boots | Celestial Robes (22030), Dragonscale Helm (22050), Hermes Boots (22070) |
| **3** | **Weaponry** | Weapons across all classes (Swords, Wands, Guns, Bows) | Dragon Slayer Sword (21050), Celestial Wand (21060), Sniper Gun (21070) |
| **4** | **Grocery** | Stat reset scrolls, EXP potions, potential water, food | Forgotten Scroll (28001), Potential Water (28002), 2x EXP Potion (28004) |
| **5** | **Furniture** | Tent crafting stations, luxury tickets, home decor | Luxury Airship Ticket (36007), Alchemy Stove (38027), Worktable (38025) |
| **6** | **Slot Machine** | Lucky draw tickets, gacha tokens, minigame coins | Lucky Draw Ticket (48020), Gacha Coin (48021), UFO Token (48022) |
| **7** | **Forging Room** | Stat spar crystals (+24 ATK/DEF/MATK/SPD), alchemy books | ATK Spar (47001), Alchemy Book I (49001), Refining Crystal (47015) |

---

## 3. Human-Readable JSON Configuration

The catalog is defined in `server/data/item_mall.json`:

```json
[
  {
    "item_id": 48050,
    "item_name": "Mecha Dragon (Mount)",
    "category": "Hot",
    "point_cost": 60,
    "original_price": 80,
    "gold_cost": 0,
    "count": 1,
    "is_hot": 1,
    "is_new": 0,
    "on_sale": 1,
    "subcategory_id": 1
  }
]
```

### JSON Fields:
- `item_id` (*int*): Authentic Item ID from `Item.dat`.
- `item_name` (*string*): Descriptive title shown in tables and notifications.
- `category` (*string or int*): Tab name (`Hot`, `Armory`, `Weaponry`, `Grocery`, `Furniture`, `Slot Machine`, `Forging Room`) or integer (`1`..`7`).
- `point_cost` (*int*): IM Points price required.
- `original_price` (*int*): List price. If `original_price > point_cost > 0` and `on_sale=1`, displays red strike-through price.
- `count` (*int*): Quantity granted per purchase stack.
- `is_hot` (*int 0/1*): Displays `HOT` badge.
- `is_new` (*int 0/1*): Displays `NEW` badge.
- `on_sale` (*int 0/1*): Enables sale calculation.

---

---

## 5. Purchase Notification & Inventory Synchronization Lifecycle

### A. Authentic Client Processing (`aLogin.exe`)
1. **Mall Purchase Handler (`FUN_0025b4a8` / `FUN_0025b7d8`)**:
   - Parses server purchase response `AC 75 Sub 4/5` containing `[RemPoints(4B), SpentPoints(4B), ItemID(2B), Quantity(1B)]`.
   - Plays sound effect `sound\wav0152.wav`.
   - Prints chat notification: `"<ItemName> success. Spent: <SpentPoints>"` and `"IM Points: <RemPoints>"`.
   - Updates GUI item mall points indicator.

2. **Generic Loot Delivery vs. Item Mall (`FUN_0043eb2c`)**:
   - `AC 23 Sub 6` is the generic world drop / quest / chest acquisition packet, which triggers the centered message box popup: `"Obtain X pcs "`.
   - When purchasing from the Item Mall, `server.grant_item(session, item_id, amount, send_acquire_notice=False)` suppresses `AC 23 Sub 6` while dispatching `AC 23 Sub 8` (slot update) and `AC 23 Sub 5` (full bag sync).
   - This ensures clean, authentic Item Mall UI feedback without duplicate or generic `"Obtain 1 pcs "` loot prompts.
