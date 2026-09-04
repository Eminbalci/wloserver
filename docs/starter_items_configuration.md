# Starter Items Pack Configuration & Administrator GUI Management

## 1. Overview & Architecture

The Starter Items Pack subsystem manages the authentic introductory welcome gift items granted to new characters upon their first login (`AC 23 Sub 6`) in Wonderland Online.

Previously hardcoded in `server/gameserver.py`, the system is now completely dynamic, database-backed, hot-reloadable, and editable via the Modern Desktop Administrator Control Suite (`server/gui_app.py`).

### Subsystem Flow:
```
[Admin GUI Tab 11: 🎁 Starter Items]
          │ (Add / Edit / Remove / Import / Export)
          ▼
[DynamicDataManager: SQLite game_starter_items] ◄──► [server/data/starter_items.json]
          │
          ▼
[StarterPackManager: GLOBAL_STARTER_PACK_MANAGER]
          │ (Runtime In-Memory Cache & Delivery Tuples)
          ▼
[GameServer: commence_login (AC 23 Sub 6 Delivery)]
```

---

## 2. Dynamic Database Schema (`game_starter_items`)

Stored in `wlo_server.db`:
```sql
CREATE TABLE IF NOT EXISTS game_starter_items (
    item_id INTEGER PRIMARY KEY,
    item_name VARCHAR(100) NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    order_idx INTEGER DEFAULT 0,
    description VARCHAR(255) DEFAULT ''
);
```

### Parameters & Types:
- `item_id` (`INTEGER`, Primary Key): Numeric item ID corresponding to `Item.dat`.
- `item_name` (`VARCHAR(100)`): Display name of the item. Automatically resolved from `Item.dat` when typed in GUI.
- `count` (`INTEGER`, Default `1`): Quantity granted to the new character.
- `order_idx` (`INTEGER`, Default `0`): Sequential ordering of packets delivered during login.
- `description` (`VARCHAR(255)`): Explanatory note/purpose for administrators.

---

## 3. Desktop GUI Suite Integration (`server/gui_app.py`)

### 🎁 Starter Items Tab (Tab 11)
Accessible directly in the Modern Administrator Suite tab view:
1. **Live Treeview Display**:
   - `Order`: Delivery sequence number.
   - `ItemID`: Item identifier.
   - `Name`: Full item display name.
   - `Quantity`: Stack count.
   - `Description`: Item description/notes.
2. **Interactive Controls**:
   - `🔄 Reload Starters`: Reloads data directly from SQLite and updates runtime cache.
   - `➕ Add Starter Item`: Opens `StarterItemEditorDialog` modal to register a new gift item with real-time `Item.dat` name resolution.
   - `✏ Edit Selected`: Opens `StarterItemEditorDialog` modal pre-filled with the selected item. Double-clicking any row also opens this editor.
   - `🗑 Remove Item`: Prompts confirmation and removes the item from database and cache.
   - `📥 Import JSON`: Loads configuration from `server/data/starter_items.json` or custom JSON.
   - `📤 Export JSON`: Exports current SQLite starter pack to JSON for version control and backups.

---

## 4. Default Authentic Baseline (`server/data/starter_items.json`)

Reverse-engineered from authentic network packet capture `oyunailkgirisvebedavaitemverilmesi.pcapng`:

| Order | Item ID | Item Name | Quantity | Description |
|-------|---------|-----------|----------|-------------|
| 1 | 34038 | Starter Gift 1 | 1 | Beginner gift package |
| 2 | 34058 | Remote Control | 1 | Auto-combat and assistant remote control |
| 3 | 34332 | Mini Dragonfly | 1 | Starter flying mount vehicle |
| 4 | 32176 | Spicy Hot Pot | 50 | Full recovery food |
| 5 | 34026 | Protective Exp Pill | 1 | Prevents EXP loss upon death |
| 6 | 34542 | Substitute Doll | 1 | Prevents companion amity drop upon death |
| 7 | 21742 | Goddess Robe | 1 | Starter protective equipment |
| 8 | 34330 | Mini HP Potion | 50 | Starter HP healing potions |
| 9 | 34190 | 10x Holy EXP Potion | 1 | Boosts experience gain |
| 10 | 34258 | Training Ticket | 1 | Instant training island pass |

---

## 5. Network Protocol Verification (AC 23 Sub 6)

When a player logs in with a fresh character, `GameServer.commence_login` delivers each configured item:
```python
starter_gifts = GLOBAL_STARTER_PACK_MANAGER.get_delivery_tuples()
for itm_id, itm_cnt in starter_gifts:
    add_item_to_inventory(session, itm_id, itm_cnt)
    delivery_pkt = PacketWriter().write_8(23).write_8(6).write_16(itm_id).write_16(itm_cnt).write_bytes(bytes(27))
    await session.send_packet(delivery_pkt)
```
- **Opcode**: Action Code 23, Subcode 6 (`17 06`).
- **Header**: Item ID (uint16 LE), Quantity (uint16 LE).
- **Padding**: 27 zero bytes matching official client packet structure (33 bytes total).
