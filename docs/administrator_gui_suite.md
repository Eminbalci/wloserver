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
- Table of all characters across all accounts with instant name/ID search filter.
- Delete Character, Refresh Characters, Open Full Character Data Editor.

### Tab 6: 🏰 Guilds Management (`tab_guilds`)
- Inspect and manage all guilds from `guilds` and `guild_members`.
- Search filter by guild name or leader ID.
- Real-time rules & announcement editor with database persistence.
- Guild roster table, Change Leader (`action_guild_change_leader`), Kick Member (`action_guild_kick_member`), and Disband Guild (`action_disband_guild`).

### Tab 7: 📬 In-Game Mail & System Gift Dispatcher (`tab_mail`)
- Dispatch gifts and messages to a Single Character, All Online Players, or All Characters in the database.
- Attached Gold and Items (quantity spinner with live display name preview).
- Automatic AC 30 Sub 1 network packet dispatch to trigger online players' envelope notification icon.
- Sent mail inspector and database deletion.

### Tab 8: 🛡️ Security & IP Bans Manager (`tab_security`)
- Dual-pane layout separating IP ban enforcement from user account status.
- Banned IP Addresses table (`tree_banned_ips`) with Add IP Ban and Unban IP; automatically kicks active connections via `game_server.kick_ip`.
- Banned User Accounts table (`tree_banned_users`) with Manual Ban and Unban Account; immediately kicks sessions via `game_server.kick_user`.
- Built-in loopback/localhost protection.

### Tab 9: ⚔️ Live Battles Monitor (`tab_battles`)
- Real-time inspection of active PvE and PvP combat instances from `game_server.active_battles`.
- Combat details console showing turn, elapsed duration, fighter HP/SP, and monster matrix positions.
- GM battle overrides: Force End / Abort Battle (`action_force_end_battle`) and Grant Instant Victory (`action_force_win_battle`).

### Tab 10: 💍 Marriage Registry (`tab_marriage`)
- Couples registry from `charmarriage` with real-time search.
- Administrative Annulment / Divorce (`action_divorce_marriage`) with `GLOBAL_MARRIAGE_MANAGER` sync.
- Teleport Spouses Together (`action_teleport_spouses`) warping partner directly to spouse coordinates.

### Tab 11: 🧙 Deep Character Data Editor Modal (`CharacterDataEditorDialog`)
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

---

## 4. Responsive Flow & Dynamic Wrapping Architecture (`ResponsiveFlowFrame`)

To support smaller displays, laptop resolutions, and half-screen snapping without horizontal clipping, button squishing, or truncated text, all toolbars and button strips employ `ResponsiveFlowFrame`:

- **Adaptive Reflow Container (`ResponsiveFlowFrame`)**:
  - Automatically observes geometry changes via `<Configure>` events with debounced scheduling.
  - Measures the natural requested width (`winfo_reqwidth()`) plus padding for each child widget.
  - Flow algorithm calculates `cur_row_width + item_total_w > avail_width` and dynamically breaks overflowing elements into subsequent rows (`cur_row + 1`, `cur_col = 0`).
  - Container height expands naturally downwards without clipping or hardcoded fixed constraints.
- **Lifecycle Destruction Safety**:
  - Automatically captures `<Destroy>` events to cancel pending `after` debounced timers (`after_cancel`).
  - Guards all layout calculations with `self.winfo_exists()` checks to eliminate dangling Tkinter callbacks during rapid modal destruction.
- **Optimized Window Minimum Dimensions**:
  - `ModernServerGUI`: lowered minimum constraint from `(1200, 780)` to `(800, 520)`.
  - `CharacterDataEditorDialog`: lowered minimum constraint from `(850, 600)` to `(650, 480)`.
- **Integrated Toolbars & Control Strips**:
  - **Header Bar**: Server title, live status badge, session count badge, uptime timer badge, Launch Client (F5), Hot-Reload, and Save All buttons.
  - **Character Editor Dialog**: Stats tab booster strip, Quests toolbar, Pets companion toolbar, Inventory item toolbar, Skills magic toolbar, NPC Visibility toolbar, and dialog bottom action bar.
  - **ModernServerGUI Tabs**: Live Cheats top target bar & bottom booster strip, Users & Accounts top toolbar, Characters Manager top toolbar, Portals & Warps top toolbar, Map NPC Studio top toolbar, Monster Drops Studio top toolbar, Chest Drops Studio top toolbar, Item Mall Manager top toolbar, Starter Items Pack Manager top toolbar, NPC Resolver top toolbar, Talk Resolver top toolbar, Guilds Manager top toolbar & action strip, Security & IP Bans toolbars & action strips, Live Battles top toolbar, Marriage Registry top toolbar & bottom action strip.

