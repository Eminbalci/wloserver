# System Architecture & Core Engine

This document specifies the software architecture, concurrency model, entry points, session state machine, and error handling of the Wonderland Online Server implementation.

## Overview

The Wonderland Online Server is a high-concurrency, asynchronous game server written in Python 3.8+ utilizing `asyncio`. It faithfully recreates the network protocol, event trees, combat mechanics, and world state of the authentic client executable (`aLogin.exe`).

### Technology Stack
- Language: Python 3.8+ (Strict Type Hints, PEP 484/526)
- Concurrency: `asyncio` Event Loop with Non-blocking Socket I/O
- Transport: Asynchronous TCP Sockets (`asyncio.start_server`)
- Database: SQLite 3 (`sqlite3` with Write-Ahead Logging)
- Data Parsers: Binary stream decoding (`struct`, custom `PacketReader`)
- GUI: Tkinter / CustomTkinter (`server/gui_app.py`)

## Core Components

```
+-------------------------------------------------------------+
|                      server/main.py                         |
|                 Server Process Entry Point                  |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                   server/gameserver.py                      |
|                     GameServer Class                        |
|  - TCP Server Listener (Port 6414)                          |
|  - Dynamic Session Management                               |
|  - Map Player Partitioning                                  |
|  - Packet Dispatcher Router                                 |
+--------------+-------------------------------+--------------+
               |                               |
               v                               v
+-----------------------------+ +-----------------------------+
|     server/database.py      | |   server/dynamic_data_mgr   |
|  - SQLite Persistent Store  | |  - Live Reloadable Rules    |
|  - Auth, Characters, Items  | |  - Drops, Instances, Mall   |
+-----------------------------+ +-----------------------------+
               |                               |
               +---------------+---------------+
                               |
                               v
+-------------------------------------------------------------+
|                      Subsystem Engines                      |
|  - battle_engine.py     : 8v8 Combat & Status Effects       |
|  - npc_manager.py       : 7,500+ World NPCs & AI Patrol     |
|  - eve_loader.py        : Binary Parser for eve.Emg Maps    |
|  - eve_interpreter.py   : Bytecode Event Script Evaluator   |
|  - quest_manager.py     : Mark.dat Quest State Machine      |
|  - tent.py              : Instanced Tent & Manufacturing    |
|  - trade_system.py      : P2P Secure Trade & Stalls         |
|  - mail_system.py       : Offline Mail & Attachments        |
+-------------------------------------------------------------+
```

## Process Entry Points

### 1. Game Server Daemon (`server/main.py`)
- Initializes logger configuration (`logging.INFO` / `logging.DEBUG`).
- Instantiates `GameServer(host="0.0.0.0", port=6414)`.
- Mounts all modular packet handlers from `server/handlers/`.
- Executes `asyncio.run(server.start())`.

### 2. Administrator Control Suite (`server/gui_app.py`)
- Standalone desktop control application providing full visibility into live server state.
- Features 19 management tabs: Characters, Inventory, Item Mall, Drops, Quests, Portals, Bans, Server Logs, and Dynamic Data Editor.

### 3. Standalone Network Utilities (`tools/`)
- `tools/live_packet_sniffer.py`: Passive sniffer and XOR-173 decryptor.
- `tools/batch_pcap_learner.py`: Automated packet structure extractor across PCAP files.
- `tools/live_game_gap_analyzer.py`: Real-time traffic gap detector against server handlers.

## Session Lifecycle State Machine

Each connected client is encapsulated within a `PlayerSession` instance:

```
[TCP Connection Established]
           |
           v
   [State: Connected]
           |
           |---> AC 0: Handshake & Version Validation
           |
           v
  [State: Authenticating]
           |
           |---> AC 63: Login (Credentials Verification)
           |
           v
  [State: Authenticated]
           |
           |---> AC 9: Character Selection / Creation
           |
           v
    [State: In-Game]
           |
           +---> Map Synchronization (AC 23:5 Inventory, AC 5:3 Login Sync)
           +---> Active Gameplay (AC 6 Movement, AC 20 Clicks, AC 23 Items)
           +---> Combat Encounters (AC 11, AC 50 Battle States)
           |
           v
[State: Disconnected] (Socket closed, DB state flushed)
```

### PlayerSession Class Specifications

Located in `server/gameserver.py`:

```python
class PlayerSession:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    ip: str
    user_id: int
    username: str
    char_id: int
    char_name: str
    level: int
    element: int       # 0: Earth, 1: Water, 2: Fire, 3: Wind
    hp: int
    max_hp: int
    sp: int
    max_sp: int
    gold: int
    map_id: int
    x: int
    y: int
    body: int
    head: int
    equipments: List[int]       # 6 slots (Head, Body, Back, Arms, Feet, Hand)
    inventory: List[Dict[str, Any]] # 50 slots (item_id, amount, damage, slot)
    skills: List[Dict[str, Any]]    # skill_id, grade, exp
    pets: List[Dict[str, Any]]      # Companion pet entities
    send_lock: asyncio.Lock     # Guarantees thread-safe socket writes
```

## Concurrency & Thread Safety

1. **Locking Strategy**:
   - `PlayerSession.send_lock`: An `asyncio.Lock` prevents interleaved packet write corruptions on TCP socket writers when multiple async tasks (e.g. battle round timer, chat broadcast, map tick) attempt concurrent transmissions.
2. **Global Game State**:
   - Map occupancy dictionaries (`GameServer.map_players`) are maintained on the single asynchronous event loop, eliminating race conditions without requiring heavyweight OS-level mutexes.
3. **Database Connections**:
   - SQLite queries are executed using scoped context managers (`with self.get_connection() as conn:`) with short-lived connections to prevent locking contention under concurrent player writes.

## Error Handling & Resilience

- **Malformed Packets**: Packet decoders check remaining bytes before every read (`reader.remaining_bytes() >= expected`). Truncated payloads are discarded with warning logs without crashing the session reader.
- **Client Disconnection**: Connection dropouts trigger `GameServer.handle_disconnect(session)`, ensuring the character is evicted from map visibility lists, open trades are aborted, and current character state is persisted to SQLite.
- **Graceful Shutdown**: The main event loop traps `SIGINT` and `SIGTERM`, saves all online player sessions to database, closes open listeners, and exits cleanly.
