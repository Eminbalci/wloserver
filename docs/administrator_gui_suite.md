# Administrator Control Suite & Desktop GUI (`server/gui_app.py`)

## 1. Overview & Architecture

[`server/gui_app.py`](file:///d:/GitHub/Wonderland%20Online/server/gui_app.py) is a 100% complete, modern CustomTkinter / high-DPI desktop control suite ported directly from the C# server GUI ([`MainForm1.cs`](file:///d:/GitHub/Wonderland-Private-Server/Src/Gui/MainForm1.cs) and [`CharacterDataEditorForm.cs`](file:///d:/GitHub/Wonderland-Private-Server/Src/Gui/CharacterDataEditorForm.cs)).

---

## 2. Complete Tab Breakdown

### Tab 1: 📊 Dashboard & Live Server Console
- **Metrics Cards**: Active Connected Sessions, Total Registered Accounts, Total Characters, Total Loaded Maps (1,119).
- **Server Identity**: Server Name and Welcome Message editors with real-time save.
- **Global Broadcast**: Marquee system notice (`AC 23 Sub 57`) with color coding (System Yellow, Alert Red, Info Blue, Notice Green, GM Purple).
- **Safe Control**: Disconnect All Players, Clear Logs, Safe Server Shutdown.
- **Color Terminal**: Colorized live streaming log output with tag styling (INFO, WARN, ERROR, DEBUG).

### Tab 2: ⚡ Live Cheats & 4-Column Browser
Direct port of the C# 4-column browser with real-time text filter and action buttons:
1. **🗺️ Maps Browser (1,119 Maps)**: Search and teleport player to any map.
2. **🚗 Vehicles Browser**: Ride and unride vehicles (Raft, Canoe, Sailboat, Yacht, Airship, Submarine, Spacecraft, etc.).
3. **🎁 Items Spawner**: Filter all items from `Item.dat` with quantity spinner and spawn directly into inventory.
4. **👾 NPC & Monster Browser (4,916 NPCs)**: Search all NPCs from `Npc.dat` with instant PvE Battle encounter, Companion Recruitment, and Dismiss actions.
- **Bottom Quick Action Strip**:
  - `Give Stat Points` (`ent_give_stat_pts`, `action_give_stat_points`, `action_reset_stats`).
  - `+1,000,000 Gold`, `+2,000 IM Points`, `+10 Levels`.
  - `Full Heal HP/SP (100%)`, `Invincible God Mode toggle`.

### Tab 3: 👥 Online Sessions Manager
- Table of connected sessions (Char ID, Username, Char Name, Map ID, Coordinates (x, y), Level, Gold, IP Address).
- GM Actions: Kick Player, Ban Account, Warp To Player, Summon Player To GM, Full Heal, God Mode.

### Tab 4: 🗄️ Users & Accounts Manager (`tabPageUsers`)
- Table of all accounts from SQLite `users` table.
- Create Account, Delete Account, Change Password, Add IM Points, Ban / Unban.

### Tab 5: 🧙 Characters Manager (`tabPageCharacters`)
- Table of all characters across all accounts.
- Delete Character, Refresh Characters, Open Full Character Data Editor.

### Tab 6: 🧙 Deep Character Data Editor Modal (`CharacterDataEditorDialog`)
Standalone modal ported from `CharacterDataEditorForm.cs`:
- **📊 Stats & Attributes**: Level, Element, Reborn Job (Killer, Warrior, Knight, Mage, Priest, Seer), STR, CON, INT, WIS, AGI, Stat Points, Potential Points, HP, SP, EXP, Gold, Bank Gold with live reload from database and active session synchronization (`send_stats_update`).
- **📜 Quests Manager**: List all quests, Add Quest with ID and State (Not Started, In Progress, Completed), Advance Step, Complete All Quests, Reset All Quests.
- **🐾 Pets & Companions**: All 4 pet slots. Add Preset Companion (Robinson, S.Monkey, Niss, Xaolan, Elin, Shizune, Cliff, Clive, Sam) or custom Pet ID, edit Level, Loyalty/Amity (100%), HP, SP, Delete Pet.
- **🎒 Inventory & Equipment**: View 50 inventory slots + 6 equips. Accurately parses JSON schema (`item_id`, `amount`, `damage`, `slot`) with human-readable name resolution via dynamic starter pack manager, `items.json`, and `Item.dat`. Supports Add Item, Delete Item, Repair Item (0 damage), Clear All 50 Slots, with automatic live session packet dispatch (`AC 23 Sub 5`).
- **✨ Skills & Magic**: View learned skills, Add Skill ID with grade/exp, Learn All Element Skills, Delete Skill, Reset Skills.
- **👁️ NPC Visibility**: Inspect & override pre-event visibility conditions on maps.

### Tab 7: 🚪 Portals & Warps Manager (`tabPagePortals`)
- Table of map portals and geometric warp destinations from `eve.Emg` and database.
- Filter by Map ID or Name, Add custom portal, Edit portal, Delete portal, Test warp on player.

### Tab 8: 🗺️ Map NPC & Scene Event Studio (`SetupMapNpcStudioTab`)
- Map selector dropdown (all 1,119 maps).
- Left: Data table of all NPCs on that map (Click ID, NPC Name, Template ID, Coordinates (x, y), Events / Script Trigger).
- Right: Full formatted Event Sequence Flow Viewer (`FormatNpcEventSequenceFlow`), displaying Event Entries, Sub-Branches, Conditions (Player Level, Has Item, Has Pet, Quest Flag, Choice), and Opcode execution sequence.
- "⚡ Simulate Event on Selected Player" button to trigger the event on an active player in real-time.

### Tab 9: 🐉 Monster Drops Studio (`SetupMonsterDropsTab`)
- Searchable monster list from `Npc.dat` + SQLite `monster_drops`.
- 5 drop slots editor with Item ID, Item Name, Quantity, Drop Chance %, Rare flag.
- Save Monster Drops live to SQLite and hot-reload.

### Tab 10: 📦 Chest Drops & Dynamic Respawn Studio (`tabPageChestDrops`)
- Select Map / Chest ID. View and edit drop table (Item ID, Item Name, Count, Drop Weight / Chance %).
- Edit respawn timer in seconds (`numRespawnSeconds`). Add Drop, Delete Drop, Save Chest Drops live.

### Tab 11: 💎 Item Mall Manager (`SetupItemMallTab`)
- Catalog table of all mall items with search and category filters.
- Add Item, Edit Item, Delete Item, Price in Gold / IM Points, Description, Hot/New/Sale badge, Stock.

### Tab 12: 🧙 NPC Name Resolver & Directory (`SetupNpcResolverTab`)
- Live Template ID resolver (TID -> Name, Category: Companions / Humanoids / Monsters / Props, Hex ID, Stats).
- Directory Table of all 4,916 NPCs with category filter and search bar.
- World Spawn Inspector showing every map and coordinate where this NPC spawns in `eve.Emg`.

### Tab 13: 📜 Talk Dialogue Resolver (`SetupTalkResolverTab`)
- Search 17,489 dialogue lines from `Talk.dat` by Talk ID or text substring.
- Formatted dialogue card preview with speaker portrait and speech bubble.

### Tab 14: ⚙️ Global Rates & Dynamic Settings (`tabPageSettings`)
- Multipliers: Base EXP, Monster Drops, Pet EXP, Gold Drop, Alchemy Compound, Forging, Resource Gathering.
- Hot-Reload button applying changes across all 19 dynamic subsystems.
- Scrollable subsystems status list (`CTkScrollableFrame`).

---

## 3. Integrated Scrolling Architecture
All table views (`ttk.Treeview`), list views (`tk.Listbox`), and multiline text consoles (`tk.Text`) feature native vertical scrollbars:
- **`create_scrolled_treeview(parent, columns, ...)`**: Bundles a `ttk.Treeview` and dock-aligned `ctk.CTkScrollbar` (or `ttk.Scrollbar` fallback) in a transparent frame. Used across Sessions, Accounts, Characters, Portals, Map NPCs, Monster Drops, Chests, Item Mall, Starter Items, NPC Directory, and Talk Dialogues.
- **Cheats 4-Column Browser**: Each column (Maps, Vehicles, Items, NPCs) packs its listbox alongside an integrated vertical scrollbar.
- **Console & Inspectors**: Dashboard Console Log, Event Flow Viewer, and World Spawn Inspector each integrate vertical scrollbars.
- **Character Data Editor Modal**: Full scrollbar coverage on Quests, Pets, Inventory, Skills, and NPC Visibility tables.
