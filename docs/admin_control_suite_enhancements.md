# Administrator Control Suite Enhancements & Protocol Management

Technical specification and architectural reference for the expanded 19-tab administration environment in [`server/gui_app.py`](file:///D:/GitHub/Wonderland%20Online/server/gui_app.py).

---

## 1. Overview & Architectural Scope

The Wonderland Online Administrator Suite ([`ModernServerGUI`](file:///D:/GitHub/Wonderland%20Online/server/gui_app.py)) provides complete real-time telemetry, database manipulation, GM commands, and live game-world synchronization. It interfaces with SQLite (`wlo_server.db`) and the active [`GameServer`](file:///D:/GitHub/Wonderland%20Online/server/gameserver.py) asynchronous event loop via thread-safe coroutine dispatching.

### Complete 19-Tab Structure
1. `tab_dash` (📊 Dashboard & Server Console)
2. `tab_cheats` (⚡ Cheats & 4-Column Browser)
3. `tab_players` (👥 Online Sessions Manager)
4. `tab_users` (🗄️ Accounts Manager)
5. `tab_chars` (🧙 Characters Manager)
6. `tab_guilds` (🏰 Guilds & Clan Management) *[NEW]*
7. `tab_mail` (📬 In-Game Mail & System Gifts) *[NEW]*
8. `tab_security` (🛡️ Security & IP Bans) *[NEW]*
9. `tab_battles` (⚔️ Live Battles Monitor) *[NEW]*
10. `tab_marriage` (💍 Marriages Registry) *[NEW]*
11. `tab_portals` (🚪 Portals & Warps Manager)
12. `tab_maps` (🗺️ Map NPC & Scene Event Studio)
13. `tab_drops` (🐉 Monster Drops Studio)
14. `tab_chests` (📦 Chest Drops & Respawn Studio)
15. `tab_mall` (💎 Item Mall Catalog Manager)
16. `tab_npc_res` (🧙 NPC Name Resolver & Directory)
17. `tab_talk` (📜 Talk Dialogue Resolver)
18. `tab_settings` (⚙️ Global Rates & Dynamic Settings)
19. `CharacterDataEditorDialog` (Deep Character Data Editor Modal)

---

## 2. New Systems & Protocol Management Tabs

### 2.1 Tab: Guilds Management (`tab_guilds`)
Provides full lifecycle management for guilds (`guilds` table) and guild rosters (`guild_members` table).

- **UI Controls**:
  - `ent_guild_search`: Real-time text search filtering guilds by Name or Leader ID.
  - `tree_guilds`: Roster table listing Guild ID, Name, Level, Leader Name, Leader ID, Member Count, and Creation Date.
  - `txt_guild_rules`: Multiline text editor for guild announcements and rulebooks.
  - `tree_guild_members`: Secondary table displaying Member Char ID, Member Name, Level, and Guild Rank.
- **Methods**:
  - `action_refresh_guilds()`: Refreshes guild list and recalculates member counts from `guild_members`.
  - `_on_guild_selected(event)`: Populates rules editor and member roster for the selected guild.
  - `action_guild_save_notice()`: Writes edited rules and announcements directly to SQLite with live feedback.
  - `action_guild_change_leader()`: Reassigns guild leadership to a specified character ID, updating both `guilds.leader_id` and rank entries.
  - `action_guild_kick_member()`: Removes a selected member from the guild roster.
  - `action_disband_guild()`: Permanently disbands the selected guild, deleting all associated rows from `guilds` and `guild_members`.
- **Edge Cases Handled**:
  - Validates leader membership before leadership transfer.
  - Confirmation dialogs protect against accidental guild disbandment.

### 2.2 Tab: In-Game Mail & System Gift Dispatcher (`tab_mail`)
Enables administrators to broadcast messages, compensatory gifts, and starter rewards directly to character mailboxes.

- **UI Controls**:
  - `cmb_mail_recipient_type`: Scope selector (`Single Character`, `All Online Players`, `All Characters in DB`).
  - `ent_mail_char_id`: Recipient character ID (enabled for single recipient).
  - `ent_mail_sender`: Sender name (default: `"System GM"`).
  - `ent_mail_title`, `txt_mail_body`: Subject header and message payload.
  - `ent_mail_gold`: Attached gold amount (default: `0`).
  - `ent_mail_item_id`, `ent_mail_item_qty`: Attached item ID and quantity with dynamic name preview (`lbl_mail_item_preview`).
  - `tree_mail`: Inspection table of sent messages (Mail ID, Recipient ID, Sender, Title, Gold, Attached Item ID/Qty, Date).
- **Methods**:
  - `action_dispatch_mail()`: Resolves recipients based on selected mode, inserts records into `charmail`, and sends live packet notifications.
  - `action_refresh_mail()`: Loads sent mail history ordered by `mail_id DESC`.
  - `action_delete_mail()`: Removes selected mail entry from SQLite.
- **Network Synchronization**:
  - If a recipient is currently online, dispatches **AC 30 Sub 1** (`write_8(30).write_8(1)`) to immediately trigger the blinking mail envelope client notification icon.

### 2.3 Tab: Security & IP Bans Manager (`tab_security`)
Dual-pane security center separating IP ban enforcement from user account status.

- **UI Controls**:
  - Left Panel: Banned IP Addresses (`tree_banned_ips`) with columns `IP Address`, `Reason`, `Banned At`, and `Banned By`.
  - Right Panel: Banned User Accounts (`tree_banned_users`) with columns `User ID`, `Username`, `Reason`, `Last IP`, and `Last Login`.
- **Methods**:
  - `action_refresh_banned_ips()`: Queries `banned_ips` table.
  - `action_ban_ip_manual()`: Adds an IP to `banned_ips` and terminates any active connections from that address via `game_server.kick_ip`.
  - `action_unban_ip()`: Deletes the IP from `banned_ips`.
  - `action_refresh_banned_accounts()`: Queries `users WHERE banned = 1`.
  - `action_ban_account_manual()`: Sets `banned = 1` in `users` table and kicks the account session via `game_server.kick_user`.
  - `action_unban_account_manual()`: Sets `banned = 0` in `users` table.
- **Edge Cases Handled**:
  - Protects loopback and local addresses (`127.0.0.1`, `0.0.0.0`, `localhost`) from being banned.

### 2.4 Tab: Live Battles Monitor (`tab_battles`)
Provides real-time inspection and administrative control over active PvE and PvP combat instances.

- **UI Controls**:
  - `tree_battles`: Active combat table displaying Battle ID, Encounter Type (`PvE` / `PvP`), Map ID, Turn Number, Elapsed Duration, and Participant Summary.
  - `txt_battle_details`: Detailed fighter readout displaying player HP/SP, companion data, and monster matrix positions/HP.
- **Methods**:
  - `action_refresh_battles()`: Reads all instances from `game_server.active_battles`.
  - `_on_battle_selected(event)`: Formats and prints structured combatant metadata into the details box.
  - `action_force_end_battle()`: Terminate / abort battle. Calls `game_server._end_pvp_battle(challenger_won=False)` for PvP or `game_server._end_battle(won=False, fled=True)` for PvE.
  - `action_force_win_battle()`: Grants instant victory to players. Calls `game_server._end_pvp_battle(challenger_won=True)` or `game_server._end_battle(won=True)`.
- **Edge Cases Handled**:
  - Handles already concluded battles gracefully.
  - Clears `session.in_battle` flags and cleans up combat memory leaks.

### 2.5 Tab: Marriage Registry (`tab_marriage`)
Couples registry interface for Wonderland Online marriage mechanics (`charmarriage` table).

- **UI Controls**:
  - `ent_marriage_search`: Search filter matching husband or wife character names.
  - `tree_marriages`: Table displaying Husband ID, Husband Name, Wife ID, Wife Name, Marriage Date, and Status.
  - `lbl_marriages_stats`: Metrics badge indicating total active marriages.
- **Methods**:
  - `action_refresh_marriages()`: Queries `charmarriage` with name search filtering.
  - `action_divorce_marriage()`: Annuls the marriage in SQLite and notifies `GLOBAL_MARRIAGE_MANAGER.divorce(husband_id)`.
  - `action_teleport_spouses()`: If both spouses are online, warps the wife directly to the husband's map and coordinates using `game_server.warp_player`.

---

## 3. Live Usability & Cheat Command Enhancements

### 3.1 Selection Preservation Across Refresh Cycles
Previously, `_refresh_metrics()` cleared and rebuilt `tree_players` every 3 seconds, deselecting whichever player the administrator was editing.
- **Improvement**: Caches the selected Character ID prior to table repopulation and automatically reselects the corresponding Treeview row once the refresh completes.

### 3.2 Real-time Search Filters
- **Online Sessions (`ent_search_players`)**: Filters online players by Character Name, Account Name, Character ID, or IP Address without disconnecting the session.
- **Characters Manager (`ent_char_search`)**: Live text search matching character name, character ID, or account ID across the SQLite `characters` table.

### 3.3 Functional Cheats Implementation
Replaced placeholder alert dialogs with live session mutating commands:
- `action_heal_player()`: Sets `hp = max_hp`, `sp = max_sp`, and dispatches `send_stats_update`.
- `action_god_mode()`: Toggles invincibility, setting HP and SP to 99,999.
- `action_kick_player()`: Disconnects target player session via `game_server.kick_user`.
- `action_cheat_warp_map()`: Warps player to selected destination map and persists coordinates to SQLite.
- `action_cheat_spawn_item()`: Adds items via `add_item_to_inventory` and updates client inventory via `build_inventory_packet`.
- `action_cheat_battle_npc()`: Instantly launches combat encounter against selected NPC via `game_server.enter_battle`.
- `action_cheat_recruit_npc()`: Adds NPC to player's companion roster (`pets` JSON) and syncs `send_pet_list_packet`.
- `action_give_stat_points()` & `action_reset_stats()`: Modifies available attributes and base stats with full stat packet synchronization.
- `_quick_give_gold_amount()`, `_quick_give_im_points()`, `_quick_add_levels()`: Adds currency and levels with live stat and packet updates.

### 3.4 Asynchronous Thread Safety Helper
The helper function `safe_run_coroutine(coro, loop)` validates that:
1. `coro` is an actual coroutine (`asyncio.iscoroutine(coro)`), avoiding `TypeError` exceptions when mocked during unit tests.
2. `loop` exists and is active (`not loop.is_closed()`).
3. Dispatches execution via `asyncio.run_coroutine_threadsafe(coro, loop)` with debug logging on failures.

---

## 4. Verification & Testing

The test suite in [`tests/test_gui_app.py`](file:///D:/GitHub/Wonderland%20Online/tests/test_gui_app.py) asserts:
1. Complete initialization of all 19 tabs without null references.
2. Initialization and sub-tabs of [`CharacterDataEditorDialog`](file:///D:/GitHub/Wonderland%20Online/server/gui_app.py#L48).
3. `test_admin_suite_new_tabs_and_actions`:
   - Execution of `action_refresh_guilds`, `action_refresh_mail`, `action_refresh_banned_ips`, `action_refresh_banned_accounts`, `action_refresh_battles`, `action_refresh_marriages`, and `action_refresh_characters`.
   - Selection of battle instances in `tree_battles` and text extraction from `txt_battle_details`.
   - Player targeting and state mutation for `action_heal_player` and `action_god_mode`.
