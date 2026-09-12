# Administrator Suite, GM Commands & Tools

This document details the Administrator GUI Suite, in-game Game Master (GM) chat commands, the standalone packet recorder proxy bridge, and live traffic gap analyzers.

## Administrator Desktop Suite (`server/gui_app.py`)

A full-featured desktop control application built with Tkinter / CustomTkinter providing real-time management of the server, players, items, and game rules.

```
+-------------------------------------------------------------+
|               Wonderland Online Admin Suite                 |
|                      (19 Tabs)                              |
+-------------------------------------------------------------+
| [Overview] [Players] [Characters] [Inventory] [Item Mall]   |
| [Dynamic Data] [Starter Items] [Chests] [Quests] [Drops]    |
| [Portals] [Instances] [Titles] [Guilds] [Mail] [Marriages]  |
| [Security & Bans] [Live Battles] [Server Logs]              |
+-------------------------------------------------------------+
```

### Key Features
- **Player & Character Management**: Real-time inspection of connected sessions, kick, teleport, level adjustments, and inventory editing.
- **Dynamic Data Hot-Reload**: Visual editors for Item Mall catalogs, starter packs, monster drops, instance dungeons, and chests with instant database writes and live engine reloads.
- **Security & Ban Center**: Real-time IP and User ID banning with immediate socket disconnect and blacklist persistence.
- **Live Battles Monitor**: Real-time visualization of active PvE and PvP combat grids, participating entities, and round progression.

## In-Game GM Chat Commands

Administrators and Game Masters can execute system commands directly within the in-game chat interface (`handle_2_chat.py` & `server/gm_commands.py`):

| Command Syntax | Parameters | Effect & Description |
| :--- | :--- | :--- |
| `:warp <map> <x> <y>` | `map`: uint16, `x`: int, `y`: int | Teleports player immediately to target map and coordinates. |
| `:item add <id> [amt]`| `id`: uint16, `amt`: int (default 1)| Grants item(s) to player inventory (`AC 23 Sub 6`). |
| `:level <lvl>` | `lvl`: int ($1 \dots 199$) | Sets character level and recalculates HP/SP attributes. |
| `:stat <s> <c> <i> <w> <a>`| STR, CON, INT, WIS, AGI integers | Overrides base character attribute distribution. |
| `:gold <amount>` | `amount`: int | Modifies player wallet gold balance. |
| `:heal` | None | Fully restores character and companion HP and SP to maximum. |
| `:element <0..4>` | `0`: Earth, `1`: Water, `2`: Fire, `3`: Wind, `4`: None | Dynamically changes character elemental affinity. |
| `:skill <id> [grade]` | `id`: uint16, `grade`: int ($1 \dots 10$) | Teaches or levels up a specific skill in character skill book. |
| `:clear` | None | Empties all items from player inventory. |
| `:propshop` | None | Forcefully invokes the native client Props Shop interface. |

## Standalone Packet Recorder (`packet_recorder/`)

A high-performance transparent proxy bridge and passive network packet recording suite for protocol reverse-engineering:

### Architecture
- **Transparent TCP Proxy**: Binds to local port (default: `6415`) and bridges traffic to the live server (port `6414`).
- **Cryptographic Interception**: Decrypts inbound and outbound XOR-173 payloads in real-time.
- **In-Game Tagging**: Allows developers to insert bookmark tags during gameplay to pinpoint exact event sequences.
- **Export Formats**:
  - `JSONL`: Structured machine-readable stream with timestamps, directions, and decoded field layouts.
  - `PCAP`: Standard packet capture files openable in Wireshark.
  - `LOG`: Formatted hex dumps with ASCII decodes.

### Launching the Recorder
```bash
# Via launcher batch script
start_packet_recorder.bat

# Or direct Python invocation
python -m packet_recorder.main --proxy --port 6415 --target-port 6414
```

## Live Traffic Gap Analyzer (`tools/live_game_gap_analyzer.py`)

Compares live packet captures from official servers against the custom server implementation:
- Identifies unhandled Action Codes or unrecognized Sub-codes.
- Validates field stride alignment across inventory, combat, and dialogue packets.
- Generates automated gap reports to pinpoint missing server features.

## Web Registration Service (`server/web_registration.py`)

Built-in lightweight asynchronous HTTP service (`aiohttp`) providing account registration and server status endpoints:
- Port: `8080` (Configurable)
- Endpoints:
  - `GET /`: Clean web registration portal with responsive HTML5 UI.
  - `POST /register`: Account creation with bcrypt/hash validation.
  - `GET /api/status`: JSON endpoint reporting server uptime, online players, and active multipliers.
