# Wonderland Online Server

This repository contains a custom python-based server implementation for Wonderland Online.

## Structure

- `start.bat` / `start.sh` - Launch scripts for the server
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
- `server/pet_amity_system.py` - Pet amity loyalty tracking, runaway threshold, feeding, and pet rebirth
- `server/minigames_system.py` - Lucky Draw wheel spins (AC 75) and Gobang board games (AC 104)
- `server/gathering_system.py` - AFK Gathering loop for Mining, Woodcutting, and Fishing
- `server/chest_system.py` - World Map interactive treasure chests, dynamic loot pools, and keys
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
- `server/dynamic_data_manager.py` - Central dynamic configuration manager (drops, crafting, alchemy, chests, gathering, instances)
- `server/eve_loader.py` - Authentic binary parser for 1,119 maps in `data/eve.Emg` (NPCs, portals, chests, mining, bytecode events)
- `docs/` - Technical Documentation:
  - [Cutscenes &amp; Scene Transition Protocol](docs/cutscene_and_scene_transitions.md)
- [Character Deletion Protocol &amp; GUI](docs/character_deletion_system.md)
  - [dialogue_queue_and_talk_resolver.md](file:///docs/dialogue_queue_and_talk_resolver.md) - Multi-Step Dialogue Queue, 17,494-entry Talk.dat Resolver, and Action Code 32 Emotes
  - [administrator_gui_suite.md](file:///docs/administrator_gui_suite.md) - Modern Desktop Administrator Control Suite (13 Tabs, GM Tools, 4-Column Browser, Character Data Editor)
  - [dynamic_data_and_eve_engine.md](file:///docs/dynamic_data_and_eve_engine.md) - Dynamic SQLite data architecture, live hot-reloads, and `eve.Emg` binary map parser
  - [remaining_systems_and_features.md](file:///docs/remaining_systems_and_features.md) - Deep decompiled audit of remaining systems (PvP duels, Morphs, Barber, Bank, Mount speed, Smelting, Death penalty)
  - [missing_systems_and_roadmap.md](file:///docs/missing_systems_and_roadmap.md) - Exhaustive missing systems audit, Action Codes matrix, and development roadmap
  - [extended_game_systems.md](file:///docs/extended_game_systems.md) - Extended systems technical specifications (Battle, Trade, Stall, Mail, Guild, Marriage, Vehicles, Rebirth, Pet Amity, Mini-Games)
  - [quest_system_architecture.md](file:///docs/quest_system_architecture.md) - Master Quest engine, Mark.dat parsing, PreEvents, and AC 24 protocol
  - [tent_and_furniture_systems.md](file:///docs/tent_and_furniture_systems.md) - Instanced tent map entries, furniture placement/movement (AC 62), world pitching (AC 65), and crafting (AC 64)
  - [database_management.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/database_management.md>) - SQLite DB schemas and data access methods
  - [network_protocol.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/network_protocol.md>) - Custom packet framing, XOR decryption, and helpers
  - [game_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/game_systems.md>) - Battle engine, GM commands, distance rules, and tent mechanics
  - [web_services.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/web_services.md>) - Web Admin panel & Web registration details
  - [character_management.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/character_management.md>) - Character creation stats verify and deletion cleanups
  - [team_and_party_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/team_and_party_systems.md>) - Team invites, accepts and member management
  - [mini_games_and_mall.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/mini_games_and_mall.md>) - Item Mall point validations and Lucky Draw spins
  - [tent_and_furniture_systems.md](<file:///c:/Users/muham/OneDrive/Documents/GitHub/Wonderland%20Online/docs/tent_and_furniture_systems.md>) - Tent interior map entries and furniture moves
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
