# Packet Handlers Catalog & Action Code Dispatcher

This document catalogs all implemented Action Code (AC) handlers within the Wonderland Online server (`server/handlers/`), specifying inbound payloads, response packets, and processing logic.

## Action Code Dispatcher Architecture

When an incoming frame is decrypted, `GameServer.dispatch_packet()` extracts byte `0` as the Action Code and routes the payload to the registered module in `server/handlers/`:

```
+-------------------------------------------------------------+
|               Incoming TCP Stream (Decrypted)               |
+-------------------------------------------------------------+
| Byte 0: Action Code (AC) | Byte 1: Sub-Code | Bytes 2+: Data|
+--------------------------+------------------+---------------+
                               |
                               v
                     GameServer Dispatcher
                               |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
handle_0_handshake.py    handle_2_chat.py      handle_20_interaction.py
```

## Action Code Reference Table

| AC | Handler Module | Primary Functionality | Supported Sub-Codes |
| :--- | :--- | :--- | :--- |
| **0** | `handle_0_handshake.py` | Connection handshake & client version validation | `Sub 1` |
| **2** | `handle_2_chat.py` | Chat channels (Public, Private, Team, Guild) & GM commands | `Sub 1..10` |
| **5** | `handle_5_player.py` | Player status sync & initial login handshake | `Sub 1, 3` |
| **6** | `handle_6_movement.py` | World coordinate movement & pathing broadcast | `Sub 1` |
| **8** | `handle_8_stats.py` | Attribute points distribution (STR, CON, INT, WIS, AGI) | `Sub 1` |
| **9** | `handle_9_char_creation.py` | Character creation & slot selection | `Sub 1, 2` |
| **10**| `handle_10_combat.py` | Combat state broadcast, battle aura, encounter heartbeats | `Sub 3, 6` |
| **11**| `handle_11_combat.py` | Turn-based battle commands (Attack, Skill, Defend, Escape) | `Sub 1..250` |
| **12**| `handle_12_warp.py` | Scene teleportation & portal transitions | `Sub 1, 2` |
| **13**| `handle_13_action.py` | Player actions, sit toggles, Item Mall query trigger | `Sub 1, 238` |
| **14**| `handle_14_friends.py` | Friend list, invitations, delete, and presence sync | `Sub 1..6` |
| **15**| `handle_15_companion.py` | Pet companion summoning, rest mode, riding, amity | `Sub 1..23` |
| **16**| `handle_16_settings.py` | System audio (BGM/SFX) and graphic settings sync | `Sub 1..5` |
| **19**| `handle_19_action.py` | Character mood / status icon display | `Sub 1` |
| **20**| `handle_20_interaction.py` | World interaction: NPC talk, portal touch, chest click | `Sub 1, 2, 8` |
| **21**| `handle_21_action.py` | Channel switch & native Item Mall window display | `Sub 1, 2` |
| **22**| `handle_20_interaction.py` | Dynamic entity broadcasts (NPC patrol, gathering respawn) | `Sub 1, 2, 10` |
| **23**| `handle_23_items.py` | Inventory (Sub 5), items move/use/drop, compounding, food | `Sub 1..208` |
| **24**| `handle_24_quest.py` | Quest journal queries, step tracking, and abandonment | `Sub 1..5` |
| **25**| `handle_25_trade.py` | Two-phase secure P2P player trading | `Sub 1..7` |
| **26**| `handle_26_reborn.py` | Character Rebirth and 6 advanced job classes advancement | `Sub 1..3` |
| **27**| `handle_27_shop.py` | NPC shops (Props, Weapon, Armor) and item selling | `Sub 1..4` |
| **29**| `handle_29_action.py` | Props Keeper warehouse storage (deposit / withdraw) | `Sub 1, 2, 6` |
| **30**| `handle_30_action.py` | In-game mailbox message retrieval | `Sub 1..4` |
| **31**| `handle_31_action.py` | Mail attachment claim and parcel dispatch | `Sub 1..7` |
| **32**| `handle_32_emote.py` | Player emotional expressions & visual emotes | `Sub 1..30` |
| **33**| `handle_33_settings.py` | Client configuration preferences and flags | `Sub 1` |
| **34**| `handle_34_itemmall.py` | Item Mall account balance (IM Points / Bonus Points) | `Sub 1` |
| **35**| `handle_35_char_deletion.py`| Character deletion verification and PIN authorization | `Sub 1, 2` |
| **37**| `handle_37_action.py` | Auxiliary client synchronization ACK | `Sub 1` |
| **39**| `handle_39_quest.py` | Guild creation, roster queries, ranks, and shared vault | `Sub 1..6` |
| **40**| `handle_25_trade.py` | Player street stall setup, browsing, and item purchases | `Sub 1..4` |
| **43**| `handle_43_team.py` | Party creation, member invitation, promote, and kick | `Sub 1..5` |
| **45**| `handle_45_vehicle.py` | Vehicles, mounting, garage, fuel refill, and navigation | `Sub 1..5` |
| **50**| `handle_50_battle.py` | Turn execution cycle, animation sync, and battle menus | `Sub 1..6` |
| **51**| `handle_50_battle.py` | Real-time battle HP / SP value updates | `Sub 1` |
| **52**| `handle_50_battle.py` | Turn combat menu enable / disable commands | `Sub 1` |
| **53**| `handle_50_battle.py` | Turn action acknowledgment (immediate ACK for client) | `Sub 5` |
| **54**| `handle_54_action.py` | Combat defeat resolution, ghost aura, and altar revive | `Sub 1` |
| **55**| `handle_16_settings.py` | Modal dialog button confirmation (OK / Cancel) | `Sub 1` |
| **57**| `handle_57_action.py` | Category switch & Minigame Exit window dismiss | `Sub 1` |
| **62**| `handle_62_tent.py` | Instanced Personal Tent, furniture placement and movement | `Sub 1..6` |
| **63**| `handle_63_login.py` | Account authentication, password hash, character list | `Sub 1..5` |
| **64**| `handle_64_crafting.py` | Tent manufacturing stations (Workbench, Furnace, Loom) | `Sub 1..4` |
| **65**| `handle_65_action.py` | World tent pitching and collapsing | `Sub 1` |
| **68**| `handle_82_marriage.py` | Marriage divorce and relationship termination | `Sub 1` |
| **71**| `handle_71_minigame.py` | Item Mall mini-games gameplay execution | `Sub 1..20` |
| **74**| `handle_74_action.py` | Auxiliary system actions (AC 61, 69, 70, 74) | `Sub 1` |
| **75**| `handle_75_itemmall.py` | Item Mall catalog display, category switch, and purchases | `Sub 1..10` |
| **82**| `handle_82_marriage.py` | Marriage proposals, wedding ceremonies, couple teleport | `Sub 1..4` |
| **84**| `handle_84_viewport.py` | Client viewport boundary sync and entity tracking | `Sub 1` |
| **85**| `handle_85_instance.py` | Multi-stage party instance dungeons (Ghost Ship, Maya) | `Sub 1..3` |
| **89**| `handle_89_action.py` | Auxiliary map synchronization ACK | `Sub 1` |
| **91**| `handle_91_itemmall.py` | Item Mall Bonus reward points redemption | `Sub 1..3` |
| **92**| `handle_92_action.py` | Map scene transition finalization ACK | `Sub 1` |
| **104**|`handle_104_minigame.py`| Lucky Draw wheel spin & Claw Machine session handling | `Sub 1, 2` |
| **183**|`handle_183_activity.py`| Daily check-in and activity reward protocol | `Sub 1` |
| **184**|`handle_184_audio.py` | Map BGM change and sound effects trigger | `Sub 1` |
| **186**|`handle_186_cutscene.py`| Intro shipwreck storm cutscene & scene sequences | `Sub 1..4` |
| **226**|`handle_226_action.py` | 6-digit secondary cryptographic security PIN lock | `Sub 1, 2` |

## Critical Inbound Protocols

### 1. Character Creation (AC 9 Sub 1)
- **Client Payload**: `[9, 1, slot, body, head, hair_color, skin_color, cloth_color, eye_color, element, name_len, name_bytes...]`
- **Validation**:
  - Checks if name already exists in database.
  - Ensures slot index is between `1` and `2`.
  - Grants element-specific starter stunt skill via `DatabaseManager.get_starter_skill_id(body, head)`.
  - Delivers dynamic starter items pack configured in SQLite (`starter_items` table).

### 2. Inventory Drag / Move / Swap (AC 23 Sub 10)
- **Client Payload**: `[23, 10, src_slot, dst_slot]`
- **Logic**:
  - Validates `1 <= src_slot <= 50` and `1 <= dst_slot <= 50`.
  - Performs atomic item swap or merge if item IDs match and are stackable.
  - Broadcasts updated slots via `AC 23 Sub 6` (single slot sync) or `AC 23 Sub 5` (full inventory sync).

### 3. World Interactions (AC 20)
- **Sub 1 (NPC Click)**: Client sends clicked entity ID. Server evaluates whether entity is dialogue NPC, shopkeeper, chest, gathering node, or hostile mob.
- **Sub 2 (Portal Touch)**: Resolves destination map, coordinates, and portal ID via `GameServer.lookup_portal()`, then executes `GameServer.warp_player()`.
- **Sub 8 (Close Interaction)**: Dismisses current NPC conversation or interaction panel.
