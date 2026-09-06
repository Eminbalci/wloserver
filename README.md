# Wonderland Online Server

This repository contains a custom python-based server implementation for Wonderland Online.

## Structure

- `start.bat` / `start.sh` - Launch scripts for the server
- `start_gap_analyzer.bat` - One-click live packet sniffer and feature gap analyzer for WLRI live gameplay
- `start_new_char_quest_recorder.bat` - Dedicated background recorder for character creation and first quest session
- `server/main.py` - Entry point
- `server/gameserver.py` - Core game server logic
- `server/database.py` - Database interactions
- `server/battle.py` - Battle mechanics and logic
- `server/network.py` - Network handling and packet processing
- `server/quest_manager.py` / `quests.py` - Master Quest engine, Mark.dat parser, and AC 24 quest protocol
- `server/preevent_interpreter.py` - eve.Emg PreEvent bytecode interpreter and dynamic actor visibility
- `server/tent.py` / `tent_manufacture.py` - Instanced personal tent map, furniture placement/movement (AC 62), and crafting stations (AC 64)
- `server/battle_engine.py` - Advanced 8v8 turn-based combat, status effects, combo attacks, and 12 Zodiac Trials
- `server/trade_system.py` / `stall_system.py` - Two-phase P2P trading (AC 25) and Player Street Stalls (AC 40)
- `server/mail_system.py` - In-game mailbox, attachments, and parcel delivery (AC 30/31)
- `server/guild_system.py` - Guild creation, member ranks, shared storage, and guild announcements (AC 39)
- `server/marriage_system.py` - Marriage proposals, wedding ceremonies, and couple teleportation (AC 44)
- `server/vehicle_system.py` - Vehicles, mount broadcasting, and sea voyage navigation (AC 15/59)
- `server/reborn_system.py` - Rebirth transformation, 6 advanced job classes, capes, and stat multipliers
- `server/minigames_system.py` - Lucky Draw wheel spins (AC 75), Claw Machine / UFO Catcher / Gacha (AC 57/104), and Gobang board games (AC 104)
- `server/handlers/handle_57_action.py` - Category switch and Minigame Exit window dismiss packet dispatcher (AC 57)
- `server/gathering_system.py` - AFK Gathering loop for Mining, Woodcutting, and Fishing
- `server/chest_system.py` - World Map interactive treasure chests, dynamic loot pools, and keys ([docs/chest_and_loot_delivery.md](file:///d:/GitHub/Wonderland%20Online/docs/chest_and_loot_delivery.md))
- `server/forging_system.py` - Equipment forging, spar crystal embedding, and gem sockets
- `server/repair_system.py` - Equipment combat durability decay and Spanner tool repairs
- `server/alchemy_system.py` - Advanced alchemy, compounding ranks, and Alchemy Books (I-IV)
- `server/sustenance_system.py` - Rice Ball auto-recovery sustenance buffer and post-combat healing
- `server/title_system.py` - Player title and achievement engine with passive stat buffs
- `server/security_pin.py` - Secondary 6-digit cryptographic security PIN lock (AC 226)
- `server/weather_system.py` - Map atmospheric engine (Rain, Snow, Sakura, Fog, Thunderstorm)
- `server/instance_system.py` - Multi-stage party instance dungeons (Ghost Ship, Maya, Pirate Cove)
- `server/anti_cheat.py` - Netcode security, velocity delta speed checks, and packet rate limiting
- `server/pvp_system.py` - 1v1 PvP duels, PK flags (Red Name), PK point penalty, and Imperial Jail
- `server/morph_system.py` - Monster disguise transformations (Jelly, Wolf, Ghost, Siren) and timers
- `server/barber_system.py` - Barber NPC hair styling, 16-bit RGB dyeing, and clothing colors
- `server/bank_system.py` - Town bank gold vault, storage, and inventory expansion bags (38001)
- `server/pet_ride_system.py` - Companion pet riding (Saddle 38020) and +40% movement speed boosts
- `server/recycle_system.py` - Smelting furnace recycling of obsolete equipment into raw materials
- `server/death_system.py` - Combat defeat EXP loss, ghost state aura, and sacred altar respawns
- `server/events_system.py` - Scheduled server events, Double EXP 2.0x multiplier, and festival notices
- `server/version_validator.py` - Client version validation, Data\\Item.Dat integrity checks, and authentic Opcode 0 disconnect responses (AC 0 0x41 Wrong Version)
- `server/starter_pack_manager.py` - Dynamic starter items pack manager, SQLite persistence, and runtime delivery
- `server/dynamic_data_manager.py` - Central dynamic configuration manager (drops, crafting, alchemy, chests, gathering, instances, starter items)
- `server/npc_manager.py` - Authentic NPC & world entity manager, C# QuestNpc parity, scripted waypoint pacing, and blinking prevention
- `server/eve_loader.py` - Authentic binary parser for 1,119 maps in `data/eve.Emg` (NPCs, portals, chests, mining, bytecode events)
- `server/handlers/handle_10_combat.py` - Combat state broadcasts, encounter heartbeats, and battle auras (AC 10 Sub 6/3)
- `server/handlers/handle_29_action.py` - Props Keeper warehouse & storage deposit/withdrawal engine (AC 29 Sub 6/1/2)
- `server/handlers/handle_91_itemmall.py` - Item Mall Bonus reward catalog & redemption protocol (AC 91 Sub 1/2/3)
- `tools/live_packet_sniffer.py` - Real-time and offline network packet sniffer, XOR-173 decryptor, and Opcode reverse-engineering tool
- `tools/batch_pcap_learner.py` - Automated batch learner and packet structure excavator across recorded gameplay PCAP files
- `tools/live_game_gap_analyzer.py` - Live WLRI game traffic gap analyzer matching packets directly against wloserver handlers
- `data/learned_packets_catalog.json` - Machine-readable database of 1,387 reverse-engineered packet variants with field candidate layouts
- `docs/` - Technical Documentation:
  - [New Client Handlers Integration & Technical Specifications](docs/new_handlers_integration_guide.md) - Specifications and parameter mappings for 10 new protocol handlers achieving 100% client opcode coverage
  - [Client C Code Missing Packets Audit](docs/client_c_code_missing_packets_audit.md) - Exhaustive audit of all 59 client-sent Action Codes from aLogin.exe.1.c vs 37 implemented server handlers, identifying the 20 missing opcodes
  - [Packet Reading & Protocol Verification Audit](docs/packet_verification_and_correctness_audit.md) - Empirical, mathematical, binary, and decompiled code proof verifying 100% accurate packet parsing and opcode dispatching
  - [New Character & First Quest Live Analysis](docs/new_character_and_first_quest_flow.md) - Exact byte-by-byte protocol flow from character creation (AC 9), starter gifts (AC 23:6), Captain dialogue (AC 20), quest acceptance (AC 24:1), to Kelan beach shipwreck
  - [Live Captured Handlers Integration](docs/live_captured_handlers_integration.md) - Technical specifications for AC 10 (combat state), AC 186 (co-op event rooms), AC 35 (currency sync), and AC 62 (tent heartbeat)
  - [WLRI Live Server Feature Gap Report](docs/live_wlri_feature_gaps.md) - Live gap report detecting missing action codes, unhandled sub-codes, and server response discrepancies
  - [Learned Packets Protocol Catalog](docs/learned_packets_catalog.md) - Exhaustive catalog of 1,387 packet variants extracted from 37 gameplay sessions (actions, sizes, hex samples, inferred field structures)
  - [PCAP Handlers & Authentic Inventory Synchronization Protocol](docs/pcap_handlers_and_inventory_sync.md) - Authentic 31-byte occupied-only AC 23 Sub 5 inventory serialization, non-stackable item overflow fix, 33-byte AC 23 Sub 6/8 alignment, Props Keeper (AC 29:6), Props Shop (AC 27:3), Witch Doctor (AC 31:2/7), and Item Mall Bonus (AC 91:2)
  - [Starter Items Pack Configuration & Administrator GUI Management](docs/starter_items_configuration.md) - Dynamic SQLite starter gift items, GUI management (Tab 11), JSON import/export, and AC 23:6 delivery
  - [PCAP Integration: First Login, Mini-Games, Lucky Draw & Vehicles](docs/pcap_integration.md) - Reverse-engineered packet flows, starter gift packs, Lucky Draw stop/delivery, vehicle lifecycle, and AC 5/15/23/104/183 handlers
  - [Client Version & File Integrity Validation](docs/client_version_and_integrity_validation.md) - Client build version checking, Data\\Item.Dat integrity checks, and authentic Opcode 0 reason codes (0x41 Wrong Version, 0x45 Item.dat File Error)
  - [aLogin.exe Master Function Index & Reverse Engineering Catalog](docs/alogin_master_function_index.md)
  - [aLogin.exe Binary Architecture & Function Map](docs/alogin_functions_architecture.md)
  - [aLogin.exe Network Communication & Opcode Protocol](docs/alogin_network_and_packet_protocol.md)
  - [aLogin.exe Authentication, Channel & Character Management](docs/alogin_auth_and_character_functions.md)
  - [aLogin.exe Combat, Battle Engine & Skill Execution](docs/alogin_combat_battle_and_skills.md)
  - [aLogin.exe Pet & Companion AI, Riding & Amity System](docs/alogin_pet_and_companion_system.md)
  - [aLogin.exe Inventory, Forging, Alchemy & Economy](docs/alogin_inventory_item_and_economy.md)
  - [aLogin.exe Quest Journal, Dialogue & PreEvent Engine](docs/alogin_quest_dialogue_and_preevent.md)
  - [aLogin.exe Mini-Games, Lucky Draw & Item Mall](docs/alogin_minigames_events_and_mall.md)
  - [Authentic Combat Engine & Action Protocol](docs/authentic_combat_engine.md) - Turn-based combat cycle, immediate AC 53:5 ACK, Defend (60021), Flee (60041), and Pet Capture (10008 + AC 11:4) reverse-engineered from real pcaps
  - [HP/MP Auto-Recovery & Lucky Draw Protocol](docs/hpmp_autofill_and_luckydraw.md) - Quick HP/MP refill button (AC 23:15 / AC 23:208) and Lucky Draw stop & delivery packets (AC 104:1 / AC 23:6) reverse-engineered from real pcaps
  - [Ground Item Pickup & Compounding Protocol](docs/ground_item_and_compounding_protocol.md) - Ground item interaction & despawn broadcast (AC 23:2 / AC 23:6) and compounding/alchemy synthesis cycle (AC 23:14 / AC 23:122 / AC 23:9 / AC 23:8 / AC 23:13) reverse-engineered from real pcaps
  - [Dynamic Chests & Gathering Node Loot System](docs/chest_and_gathering_loot_system.md) - Permanent chest re-loot prevention, SQLite charchests persistence, map-entry open sync (AC 22:10), and inventory drag/move/swap (AC 23:10)
  - [NPC Blinking Prevention & AI Waypoint Architecture](docs/npc_blinking_and_ai_system.md)
  - [MOTD & Server Branding System](docs/motd_system.md)
  - [Robinson Beach Rescue Cutscene Protocol](docs/robinson_beach_cutscene.md)
  - [Mini-Games & Item Mall Protocol](docs/mini_games_and_mall.md)
  - [Cutscenes & Scene Transition Protocol](docs/cutscene_and_scene_transitions.md)
  - [Character Deletion Protocol & GUI](docs/character_deletion_system.md)
  - [dialogue_queue_and_talk_resolver.md](file:///docs/dialogue_queue_and_talk_resolver.md) - Multi-Step Dialogue Queue, 17,494-entry Talk.dat Resolver, and Action Code 32 Emotes
  - [administrator_gui_suite.md](docs/administrator_gui_suite.md) - Modern Desktop Administrator Control Suite (19 Tabs, GM Tools, 4-Column Browser, Character Data Editor, and ResponsiveFlowFrame Auto-Wrapping Toolbars)
  - [admin_control_suite_enhancements.md](file:///docs/admin_control_suite_enhancements.md) - Deep technical specifications for Guilds, In-Game Mail, Security & IP Bans, Live Battles Monitor, and Marriage Registry administration tabs
  - [dynamic_data_and_eve_engine.md](file:///docs/dynamic_data_and_eve_engine.md) - Dynamic SQLite data architecture, live hot-reloads, and `eve.Emg` binary map parser
  - [remaining_systems_and_features.md](file:///docs/remaining_systems_and_features.md) - Deep decompiled audit of remaining systems (PvP duels, Morphs, Barber, Bank, Mount speed, Smelting, Death penalty)
  - [missing_systems_and_roadmap.md](file:///docs/missing_systems_and_roadmap.md) - Exhaustive missing systems audit, Action Codes matrix, and development roadmap
  - [extended_game_systems.md](file:///docs/extended_game_systems.md) - Extended systems technical specifications (Battle, Trade, Stall, Mail, Guild, Marriage, Vehicles, Rebirth, Pet Amity, Mini-Games)
  - [quest_system_architecture.md](file:///docs/quest_system_architecture.md) - Master Quest engine, Mark.dat parsing, PreEvents, and AC 24 protocol
  - [tent_and_furniture_systems.md](file:///docs/tent_and_furniture_systems.md) - Instanced tent map entries, furniture placement/movement (AC 62), world pitching (AC 65), and crafting (AC 64)
  - [database_management.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/database_management.md>) - SQLite DB schemas and data access methods
  - [network_protocol.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/network_protocol.md>) - Custom packet framing, XOR decryption, and helpers
  - [game_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/game_systems.md>) - Battle engine, GM commands, distance rules, and tent mechanics
  - [web_services.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/web_services.md>) - Web registration service details and Modern Desktop GUI architecture
  - [mini_games_and_mall.md](file:///docs/mini_games_and_mall.md) - Item Mall network protocols (AC 0/13/21/23/34/57/71/75/104/226, TCP 6416), Server Branding (Mamiletta / GUI edit), Claw Crane/Mini-Game gameplay and Exit handling, and Lucky Draw mechanics
  - [item_mall_configuration.md](file:///docs/item_mall_configuration.md) - Authentic Item Mall & Bonus Mall Subsystem, 11-page Grocery catalog architecture, dual-currency checkout, and live packet capture specifications
  - [authentic_shop_system.md](file:///docs/authentic_shop_system.md) - Authentic NPC Shop Protocol (AC 27 / 0x1B), Props Shop (1b 03), Weapon Shop (1b 04), Item Selling (1b 02), Inventory and Gold sync reverse-engineered from packet captures
  - [first_quest_animations_protocol.md](file:///docs/first_quest_animations_protocol.md) - Ocean Star introductory quest line, multi-stage dialogue (Talk IDs 95660/95661), dynamic actor spawning (AC 3:123), camera waypoints (AC 22:4), and quest progression (AC 24:1/5)
  - [friends_and_mailbox_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/friends_and_mailbox_systems.md>) - Friend list pairings and invitation handshakes
  - [crafting_and_production_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/crafting_and_production_systems.md>) - Manufacturing recipe checks and async timers
  - [authentication_and_login.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/authentication_and_login.md>) - Login authentication check, slot lists, and redirects
  - [npc_store_transactions.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/npc_store_transactions.md>) - Store purchases, selling prices, and gold updates
  - [item_compounding_system.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/item_compounding_system.md>) - Alchemy compound recipes and material verification
  - [player_settings_and_handshake.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/player_settings_and_handshake.md>) - Connection handshake versions and client option settings
  - [pet_battle_state_management.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/pet_battle_state_management.md>) - Companion battle/rest toggling and spawn broadcasts
  - [binary_dat_decryption.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/binary_dat_decryption.md>) - XOR dat keys, recipes parsing, and database decryption
  - [winsock_asynchronous_io.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/winsock_asynchronous_io.md>) - Client socket connections, FIONBIO Filer toggles, and async selectors
- `decompiled docs/` - Client-side Decompiled Code Documentation:
  - [client_advanced_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_advanced_systems.md>) - Instances, PVP ranks, mini-games, treasure, titles, voyage, and chaos crystals
  - [client_combat_inventory_economy.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_combat_inventory_economy.md>) - Item mall, crafting, inventory, equipment, NPC, teleport, combat classes, recycle, and auto-walk
  - [client_mini_games_and_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_mini_games_and_systems.md>) - Gacha machine, Gobang board game, gacha/slots, HP recovery, Security Lock, and audio parsing
  - [client_trade_battle_map_server.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_trade_battle_map_server.md>) - Trade, battle, map/minimap, weather, server/channel, login, GM tools, chat channels, anti-cheat, and repair
  - [client_game_systems_extended.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_game_systems_extended.md>) - Stall, marriage, guild, mount, forge, bank, fishing, hot spring, tent, mail, and events
  - [client_launch_and_external_links.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_launch_and_external_links.md>) - Patcher launch validations, ShellExecute redirects, and billing URLs
  - [client_multimedia_and_render_engine.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_multimedia_and_render_engine.md>) - DirectDraw surfaces, DirectSound wrappers, and wave audio lists
  - [client_events_and_ui_handling.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_events_and_ui_handling.md>) - Lucky draw animations, gear equip event handlers, and holiday systems
  - [client_save_and_chat_system.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/client_save_and_chat_system.md>) - Save file XOR loading and chat channel item requirements
  - [network_packet.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/network_packet.md>) - Socket management and packet distribution
  - [login_server.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/login_server.md>) - Authentication & channel parsing
  - [movement_map.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/movement_map.md>) - Grid coordinates, map decryption and range validation
  - [combat_battle.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/combat_battle.md>) - PVE encounter steps and PVP PK duels
  - [quest_journal.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/quest_journal.md>) - Quest UI panels, conversation forms and sub-opcodes
  - [pet_companion.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/pet_companion.md>) - Summon states, Amity lock and rest/combat/stall modes
  - [trade_shop.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/trade_shop.md>) - Secure trade, stall limits, simya compounding and material IDs
  - [item_mall.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/decompiled%20docs/item_mall.md>) - Client shop UI and point/balance validations

## Setup & Installation

The server includes all necessary baseline `data/` files (`eve.Emg`, `Compound2.dat`, `Skill.dat`) required to run out of the box.

1. **Clone this repository** to your local machine.
2. Make sure you have Python 3.8+ installed.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   - On Windows: Double click `start.bat` or run `python -m server.main`
   - On Linux/Mac: `./start.sh` or run `python3 -m server.main`

## Database

The server uses SQLite databases (`wlo_server.db` / `server/ServerDataBase.db`) to store player data, accounts, and static game state.

## Admin Commands

You can type these commands in the game chat to modify your character:

- `:warp <map_id> <x> <y>` - Teleport to a specific map and coordinates.
- `:item add <item_id> [amount]` - Add an item to your inventory.
- `:level <level>` - Set your character's level.
- `:stat <str> <con> <int> <wis> <agi>` - Set your base attributes.
- `:gold <amount>` - Set your gold.
- `:heal` - Fully restore HP and SP.
- `:element <0-4>` - Change your character's element (0: Earth, 1: Water, 2: Fire, 3: Wind, 4: None).
- `:skill <skill_id> [grade]` - Add or level up a skill.
- `:clear` - Clear all items from your inventory.
- `:propshop` - Open the property shop.

#Game version rhode island install : [drive.google.com/file/d/18z5H1w5G9GujMJywRHL-uOac4fFyOTSY](https://drive.google.com/file/d/18z5H1w5G9GujMJywRHL-uOac4fFyOTSY)
