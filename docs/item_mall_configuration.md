# Wonderland Online - Authentic Item Mall & Bonus Mall Subsystem

## Overview
The Wonderland Online Item Mall subsystem manages point-based and bonus-point merchandise, multi-catalog synchronization across TCP ports (`6416` and `6414`), multi-tab category mapping, 11-page Grocery catalog layout, dual-mall state synchronization, dynamic SQLite/JSON persistence, and administrator GUI configuration.

Reverse engineered and verified against authentic live server captures (`itemmalldatalari.pcapng`) and Rhodes Island client (`C:\Games\WLRI`).

---

## 1. Network Protocol Specifications

### A. Dedicated Port 6416 TCP Catalog Service
- **Purpose**: Feeds initial catalog metadata to client binary `aLogin.exe` (`FUN_0025a684`).
- **Binary Format**:
  - `[0]` Opcode `0xC9`
  - `[1-2]` Header `0x00 0x01`
  - Per item: `[ItemID (uint16_LE), HotFlag (uint8)]` (`2` = Hot/Special, `3` = Standard)

### B. In-Game Port 6414 Packets

#### 1. Initial Mall Handshake Sequence (Map Entry / Login)
On player map join, the server initiates the complete authentic mall sync sequence:
1. **`AC 75 Sub 1`**: Points Mall catalog (152 authentic items)
2. **`AC 75 Sub 10`**: Bonus Mall catalog (71 authentic items)
3. **`AC 75 Sub 8`**: Mall system settings (`[75, 8, 0, 0]`)
4. **`AC 75 Sub 7`**: Mall status indicator (`[75, 7, 1]`)
5. **`AC 75 Sub 3`**: Dual balance synchronization (IM Points + Bonus Points)

#### 2. Catalog Packet Layout (AC 75 Sub 1 & AC 75 Sub 10)
- **Header**: `[75, sub_code, ItemCount (uint16_LE)]` (`sub_code = 1` for Points Mall, `10` for Bonus Mall)
- **Per Item (Exactly 10 Bytes)**:
  - `[0-1]` `item_id (uint16_LE)`: 16-bit numeric item identifier matching `Item.dat`.
  - `[2]` `count (uint8)`: Quantity per pack (1 for single item, 5/8/20/50 for bundle packs).
  - `[3-4]` `base_price (uint16_LE)`: Original/list price in points.
  - `[5]` `discount (uint8)`: Discount percentage (`100` = full price, `80` = 20% off, `30` = 70% off).
  - `[6]` `badge (uint8)`: Badge overlay tag (`0` = Normal, `1` = `NEW`, `2` = `HOT`, `3` = `LIMITED`).
  - `[7]` `category_id (uint8)`: Category selector byte:
    - `1`: Weaponry
    - `2`: Armory
    - `3`: Grocery (Single items)
    - `4`: Grocery (Multi-packs / Bundles)
    - `5`: Furniture
  - `[8-9]` `order_idx (uint16_LE)`: UI sort order index.

#### 3. AC 75 Sub 3 (Dual Balance Synchronization)
- **Payload**: `[75, 3, IMPoints (uint32_LE), BonusPoints (uint32_LE), 0 (uint16_LE), 0 (uint8)]`
- Total Length: 13 bytes.

#### 4. AC 75 Sub 4 & Sub 5 (Tab Switching & Purchases)
- **Category Switch**: Client sends `[75, 4, cat_id]`. Server acknowledges with `AC 57:1` (`[57, 1, cat_id, 0, 0, 0]`), synchronizes `AC 34:1` and `AC 75:3` balances, and re-dispatches the catalog.
- **Purchase**:
  - Points Mall: Client sends `[75, 4, item_id (uint16_LE), quantity (uint8)]`.
  - Bonus Mall: Client sends `[75, 5, item_id (uint16_LE), quantity (uint8)]`.
  - Server validates balance, executes `server.grant_item(...)`, updates DB, and replies with `AC 75 Sub [4/5]`: `[75, sub, RemPoints(4B), SpentPoints(4B), ItemID(2B), Quantity(1B)]`.

---

## 2. 11-Page Grocery Catalog Architecture

The authentic client displays 12 items per page.
In `itemmalldatalari.pcapng`:
- **Category 3 (Grocery Singles)**: 102 items (Single bottles, potions, reset scrolls, sparrows, pills)
- **Category 4 (Grocery Bundles)**: 21 items (Packs of 5x, 8x, 20x, 50x)
- **Total Grocery Items**: 102 + 21 = **123 items**
- **Pages**: `ceil(123 / 12) = 11 pages`! Both Category 3 and Category 4 render under the client's Grocery tab, seamlessly creating the 11 pages of authentic items.

---

## 3. Database Schema (`game_item_mall`)

Items can exist simultaneously in both Points Mall and Bonus Mall at different prices, and can also be sold as both singles and multi-packs (e.g. Potential Pill 1x and 5x, Chaos Crystal 1x and 5x).
The composite primary key is `(item_id, count, is_bonus)`.

```sql
CREATE TABLE game_item_mall (
    item_id INTEGER NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) DEFAULT 'Grocery',
    point_cost INTEGER DEFAULT 100,
    original_price INTEGER DEFAULT 0,
    gold_cost INTEGER DEFAULT 0,
    count INTEGER DEFAULT 1,
    is_hot INTEGER DEFAULT 0,
    is_new INTEGER DEFAULT 0,
    is_limited INTEGER DEFAULT 0,
    on_sale INTEGER DEFAULT 0,
    discount INTEGER DEFAULT 100,
    badge INTEGER DEFAULT 0,
    category_id INTEGER DEFAULT 3,
    order_idx INTEGER DEFAULT 0,
    is_bonus INTEGER DEFAULT 0,
    subcategory_id INTEGER DEFAULT 1,
    PRIMARY KEY (item_id, count, is_bonus)
);
```

---

## 4. Human-Readable JSON Configuration

The catalog is exported to and imported from `server/data/item_mall.json` containing all 224 catalog entries.
Hot-reload is supported at runtime via `GLOBAL_DYNAMIC_DATA.import_item_mall_json()`.

```json
[
  {
    "item_id": 34269,
    "item_name": "Potential Pill",
    "category": "Grocery",
    "category_id": 3,
    "point_cost": 42,
    "original_price": 42,
    "gold_cost": 0,
    "count": 1,
    "is_hot": 0,
    "is_new": 0,
    "is_limited": 0,
    "on_sale": 0,
    "discount": 100,
    "badge": 0,
    "order_idx": 47,
    "is_bonus": 0
  },
  {
    "item_id": 34269,
    "item_name": "Potential Pill",
    "category": "Grocery",
    "category_id": 4,
    "point_cost": 119,
    "original_price": 119,
    "gold_cost": 0,
    "count": 5,
    "is_hot": 1,
    "is_new": 0,
    "is_limited": 0,
    "on_sale": 0,
    "discount": 100,
    "badge": 2,
    "order_idx": 48,
    "is_bonus": 0
  }
]
```
