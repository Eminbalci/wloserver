# Wonderland Online Server

An asynchronous, production-grade game server implementation for Wonderland Online (WLRI / WLO) written in Python 3.

## Overview

Wonderland Online Server is a complete custom backend re-engineering the authentic protocol, game mechanics, event interpreters, and world systems of the 2D MMORPG Wonderland Online. Built on Python's native `asyncio` event loop, the server provides high-throughput concurrent connection handling, authentic XOR-173 stream cryptography, byte-level packet serialization, a turn-based 8v8 battle engine, an `eve.Emg` bytecode event interpreter, and an administrator desktop control suite.

---

## Technical Documentation Index

Detailed architectural specifications, binary formats, packet catalogs, and subsystem designs are organized in modular technical documents:

- [System Architecture & Concurrency Model](file:///D:/GitHub/Wonderland%20Online/docs/01_system_architecture.md) - Core engine lifecycle, asyncio networking, PlayerSession state machine, subsystem delegation, and error handling.
- [Network Protocol & Stream Cryptography](file:///D:/GitHub/Wonderland%20Online/docs/02_network_protocol.md) - 0x44F4 magic framing, 2-byte big-endian framing, XOR-173 stream cipher, PacketReader/PacketWriter API, multi-packet streaming, and AC 0 connection handshakes.
- [Action Code & Packet Handlers Catalog](file:///D:/GitHub/Wonderland%20Online/docs/03_packet_handlers_catalog.md) - Exhaustive reference of all 50+ implemented Action Codes (AC 0 to AC 226) and sub-opcodes mapped to client functions and server handlers.
- [Turn-Based Combat Engine & Formulas](file:///D:/GitHub/Wonderland%20Online/docs/04_combat_engine.md) - 8v8 turn-based combat cycle, damage formulas, elemental counter cycle, status ailments, Pet capture, Defend/Flee, 12 Zodiac Trials, and PvP duel systems.
- [Database Schemas & Storage Systems](file:///D:/GitHub/Wonderland%20Online/docs/05_database_and_storage.md) - SQLite relational tables, JSON serialization models, account authentication, dynamic subsystems, and hot-reload architecture.
- [Quest Engine & PreEvent Bytecode Interpreter](file:///D:/GitHub/Wonderland%20Online/docs/06_quest_and_event_engine.md) - Master Quest engine, Mark.dat parsing, AC 24 quest protocol, eve.Emg PreEvent bytecode interpreter, authentic quest lifecycle state mapping (`0 = NotStarted`, `1 = InProgress`, `2 = Completed`), item & level condition verification (`unkb1 == 1, 2`), inventory item consumption, dynamic actor visibility & real-time lifecycle synchronization, event branch cascading, dialogue option-0 progression cascade, Robinson recruitment & raft award sequence, and map exclamation mark radar clearance.
- [Items, Compounding & Economy Engine](file:///D:/GitHub/Wonderland%20Online/docs/07_items_and_economy.md) - AC 23:5 inventory serialization, equipment slots, alchemy compounding formulas, Item Mall, bank gold vault, player stalls, and P2P trading.
- [World Entities, NPCs & Map Engine](file:///D:/GitHub/Wonderland%20Online/docs/08_world_and_entities.md) - 7,545 authentic NPCs from eve.Emg, sprite blinking prevention, waypoint patrol AI, map portals, gathering nodes, vehicle boarding & sea navigation (`AC 15 Sub 9, 14, 18, 10`), and persistent treasure chests with single-packet `AC 22:10` frame isolation.
- [Administrator Suite & Tooling](file:///D:/GitHub/Wonderland%20Online/docs/09_admin_suite_and_tools.md) - Modern 19-tab Desktop Administrator Suite, in-game GM chat commands, standalone packet recorder proxy bridge, and live game gap analyzer.
- [Logging & Diagnostics Architecture](file:///D:/GitHub/Wonderland%20Online/docs/10_logging_and_diagnostics.md) - Multi-target rotating file persistence, console streaming, real-time GUI log pipe, and UTF-8 diagnostic formats.
- [NPC Visibility & Companion Isolation](file:///D:/GitHub/Wonderland%20Online/docs/11_npc_visibility_and_companion_isolation.md) - Dynamic actor visibility, dual-packet despawn (AC 22:10 & 22:11), story companion scene isolation across maps (Roca Kelan Village square vs Chief's House, Robinson Kelan Beach recruitment), and quest-state lifecycle mapping.

Decompiled client code references and protocol analysis from `aLogin.exe` are preserved in [decompiled docs/](file:///D:/GitHub/Wonderland%20Online/decompiled%20docs/).

---

## Architecture & Subsystems

### Core Server Components

| Module | Description |
| :--- | :--- |
| `server/main.py` | Server entry point, configuration loading, database initialization, and TCP listener bind. |
| `server/gameserver.py` | Central `GameServer` hub, `PlayerSession` state tracking, packet dispatching, inventory removal, and broadcast routing. |
| `server/network.py` | Protocol framing, XOR-173 encryption/decryption, `PacketReader`, `PacketWriter`, and `send_system_msg`. |
| `server/database.py` | Thread-safe SQLite data access layer for accounts, characters, items, quests, chests, and bans. |
| `server/battle_engine.py` | 8v8 turn-based battle manager, damage calculation, status effects, and 12 Zodiac Trials. |
| `server/battle.py` | Compatibility facade re-exporting symbols (`Fighter`, `BattleManager`) for legacy subsystem imports. |
| `server/npc_manager.py` | Manages 7,545 authentic NPCs, waypoint pacing loops, idle intervals, and sprite blinking prevention. |
| `server/eve_loader.py` | Binary parser for 1,119 maps in `data/eve.Emg` (NPCs, portals, chests, mining nodes, bytecode events). |
| `server/eve_event_interpreter.py` | Bytecode event VM executing dialogs, warp sequences, quest progression, and conditional branch evaluations (`unkb1 == 1, 2, 3, 5, 15`). |
| `server/preevent_interpreter.py` | Virtual machine executing `eve.Emg` PreEvent bytecode conditions, quest lifecycle state mapping (`0 = NotStarted`, `1 = InProgress`, `2 = Completed`), and dynamic actor visibility. |
| `server/quest_manager.py` | Master quest engine, `Mark.dat` binary parser, quest tracking, and AC 24 protocol handling. |
| `server/dynamic_data_manager.py` | Central manager for hot-reloadable dynamic game tables (drops, crafting, alchemy, chests). |
| `server/version_validator.py` | Client version validation, `Data\Item.Dat` file integrity checking, and AC 0 0x41 error handling. |

### Gameplay Subsystems

| Module | Protocol Codes | Feature Set |
| :--- | :--- | :--- |
| `server/tent.py` / `tent_manufacture.py` | AC 62, 64, 65 | Personal tent interior map, furniture positioning, and crafting stations. |
| `server/trade_system.py` | AC 25 | Two-phase lock P2P trade session between players. |
| `server/stall_system.py` | AC 40 | Player street stall vending, pricing, and item transfers. |
| `server/guild_system.py` | AC 39 | Guild creation, rank hierarchy, shared storage vault, and broadcast notices. |
| `server/marriage_system.py` | AC 44 | Marriage proposals, church ceremonies, spouse teleportation, and divorce. |
| `server/mail_system.py` | AC 30, 31 | In-game postal mailbox, text letters, item parcel attachments, and COD. |
| `server/vehicle_system.py` | AC 15, 23, 59 | Vehicle inventory use/mounting (AC 15:9), boarding (AC 15:10), spawning (AC 15:18), dismounting (AC 23:52), and sea voyage navigation. |
| `server/reborn_system.py` | AC 23, 26 | Character rebirth transformation, 6 advanced job classes, and stat bonuses. |
| `server/alchemy_system.py` | AC 23:14 | Item compounding, synthesis ranks, primary material affinity, and Alchemy Books. |
| `server/gathering_system.py` | AC 23, 62 | AFK gathering loops for mining ores, woodcutting lumber, and fishing. |
| `server/chest_system.py` | AC 22:10, 23 | Interactive world chests, key requirements, dynamic loot pools, anti-re-loot, and single-packet `AC 22:10` frame isolation. |
| `server/bank_system.py` | AC 29, 35 | Town bank gold vault deposits/withdrawals and inventory expansion bags. |
| `server/pvp_system.py` | AC 10, 11 | 1v1 PvP duel requests, PK flag system, PK point penalties, and Imperial Jail. |
| `server/minigames_system.py` | AC 57, 75, 104 | Lucky Draw wheel, Claw Machine / UFO Catcher, and Gobang board games. |
| `server/forging_system.py` | AC 23 | Equipment socketing, spar crystal embedding, and attribute enhancement. |
| `server/repair_system.py` | AC 23 | Combat gear durability degradation and Spanner repair tools. |
| `server/pet_ride_system.py` | AC 15 | Companion mount riding with saddle item (38020) and +40% speed boost. |
| `server/morph_system.py` | AC 11, 23 | Monster disguise transformations (Jelly, Wolf, Ghost, Siren) with timers. |
| `server/barber_system.py` | AC 23 | Barber NPC customization, 16-bit RGB hair dyeing, and clothing colors. |
| `server/recycle_system.py` | AC 23 | Smelting furnace recycling of obsolete gear into raw crafting materials. |
| `server/death_system.py` | AC 10, 23 | EXP loss on defeat, ghost death state aura, and Sacred Altar revivals. |
| `server/weather_system.py` | AC 33 | Dynamic map atmosphere (Rain, Snow, Sakura Blossom, Fog, Thunderstorm). |
| `server/instance_system.py` | AC 10, 22 | Multi-stage instanced party dungeons (Ghost Ship, Maya, Pirate Cove). |
| `server/security_pin.py` | AC 226 | Secondary 6-digit cryptographic security PIN lock on sensitive operations. |
| `server/anti_cheat.py` | AC 22 | Velocity vector delta speed checks, teleport bounds, and packet rate limiting. |
| `server/starter_pack_manager.py` | AC 23:5, 23:6 | Authentic 8-item starter bundle delivery, dynamic DB persistence, and single-dispatch inventory sync. |

---

## Installation & Setup

### Prerequisites

- Python 3.8 or newer (tested with Python 3.10, 3.11, 3.12, 3.13, 3.14).
- Windows, Linux, or macOS.

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Eminbalci/wloserver.git
   cd wloserver
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the game server:
   - On Windows: Run `start.bat` or execute:
     ```bash
     python -m server.main
     ```
   - On Linux/macOS: Run `./start.sh` or execute:
     ```bash
     python3 -m server.main
     ```

The server listens on `0.0.0.0:6414` (Game Server) and `0.0.0.0:6416` (Item Mall / Auxiliary Service).

---

## Running the Automated Test Suite

The test suite validates packet serialization, combat formulas, database transactions, event execution, and network framing:

```bash
python -m unittest discover tests
```

---

## In-Game GM Chat Commands

Game Master (GM) commands can be executed in the client chat window:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `:warp` | `<map_id> <x> <y>` | Teleport player to map coordinates. |
| `:item add` | `<item_id> [amount]` | Add item(s) to inventory. |
| `:level` | `<level>` | Set character level directly (1-199). |
| `:stat` | `<str> <con> <int> <wis> <agi>` | Distribute base character attributes. |
| `:gold` | `<amount>` | Set character gold balance. |
| `:heal` | None | Fully restore current HP and SP to maximum. |
| `:element` | `<0-4>` | Set element (0: Earth, 1: Water, 2: Fire, 3: Wind, 4: None). |
| `:skill` | `<skill_id> [grade]` | Unlock or level up specific combat skill. |
| `:propshop` | None | Open the Property / Storage shop interface. |
| `:clear` | None | Wipe all items from character inventory. |
| `:save` | None | Force immediate persistence of player session and pets to SQLite. |
| `:pet add` | `<pet_id> [name]` | Recruit companion directly into party roster. |
| `:pet del` | `<slot>` | Remove companion from party by slot (1-4). |
| `:quest reset` | `[quest_id]` | Reset specific quest or all quests for player. |
| `:quest clear` | None | Clear all quests for player session. |
| `:quest set` | `<id> <state> [step]` | Set quest state and step for testing. |
| `:quest status` | None | View raw quest status list. |

---

## Tooling & Utilities

- `packet_recorder/`: Standalone network capture tool featuring a transparent proxy bridge, passive sniffer, in-game tagging, and JSONL/PCAP export.
- `start_packet_recorder.bat`: 1-Click launcher for the packet recording suite.
- `start_gap_analyzer.bat`: Real-time packet matching against implemented server handlers to identify opcode/sub-opcode coverage gaps.
- `tools/live_packet_sniffer.py`: Network sniffer and real-time XOR-173 stream decryptor.
- `tools/batch_pcap_learner.py`: Automated packet structure extractor across gameplay PCAP captures.
- `tools/live_game_gap_analyzer.py`: Live network traffic validator against server handlers.
