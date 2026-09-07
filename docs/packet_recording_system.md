# Wonderland Online - Packet Recording & Session Analysis System

## 1. Overview & Architecture

[`packet_recorder/`](file:///D:/GitHub/Wonderland%20Online/packet_recorder) is an autonomous, standalone network capture and protocol reverse-engineering suite. It is located completely outside the server directory (`server/`) and operates independently.

It enables players to capture 100% of network packets during active gameplay across both local and remote Wonderland Online servers, format them with XOR-173 decryption, attach live context annotations (bookmarks), and export them in machine-readable (`.jsonl`), human-readable (`.log`), binary (`.pcap`), and statistical (`.json`) formats.

---

## 2. Core Components

### 2.1 Protocol Engine (`packet_recorder/wlo_protocol.py`)
- **Cipher**: Fast byte-wise XOR decryption with key `173` (`0xAD`).
- **Framing**: Detects 2-byte signature (`0x44F4` little-endian `[0xF4, 0x44]`, encrypted wire representation `[0x59, 0xE9]`) followed by a 2-byte little-endian payload length $L$.
- **Stream Reassembly (`WLOStreamReassembler`)**:
  - Implements sliding-window stream buffering for fragmented and coalesced TCP segments.
  - Automatically resynchronizes upon packet boundary corruption by scanning forward for the signature sequence.
  - Generates strongly-typed `WLOPacket` dataclasses with parsed opcodes, sub-codes, hex dumps, ASCII previews, and high-level field inferences (coordinates, chat messages, dialogue IDs, item slots).

### 2.2 Recording Engine (`packet_recorder/recorder_engine.py`)
- **`RecordingSession`**:
  - Thread-safe file management handling instantaneous line-buffered output to `session_*.jsonl` and `session_*_readable.log`.
  - Generates Wireshark-compatible synthetic ethernet/IP/TCP frames written via Scapy's `PcapWriter`.
  - Maintains live action code histograms, data volume counters, and tagged bookmark timeline.
- **`ProxyBridgeRecorder`**:
  - Non-blocking `asyncio` bidirectional TCP proxy bridge listening on `listen_host:listen_port` (default `127.0.0.1:6414`) and forwarding upstream to `target_host:target_port`.
  - Requires zero system drivers (e.g. WinPcap/Npcap not required) and runs under standard non-administrative privileges.
- **`SnifferRecorder`**:
  - Alternative passive Scapy sniffer filtering for game ports (`6414, 6415, 6416, 25221, 25620`).

### 2.3 User Interfaces
- **Interactive CLI (`packet_recorder/cli.py`)**: Real-time console logging with one-line packet summaries, live stats, and `tag <text>` console prompt.
- **Modern Desktop GUI (`packet_recorder/gui.py`)**: CustomTkinter dark GUI featuring live packet table, auto-scroll, real-time opcode/text search filter, packet hex/ASCII inspector pane, live tagger, and 1-click folder launcher.
- **Unified Runner (`packet_recorder/main.py`)**: CLI / GUI mode switcher with command-line arguments.

---

## 3. Data Schema Specifications

### 3.1 JSON Lines (`session_*.jsonl`)
Each line contains a standalone JSON object:
```json
{
  "packet_id": 42,
  "timestamp": 1725712800.123,
  "datetime": "2026-09-07 14:40:00.123",
  "direction": "C->S",
  "action_code": 20,
  "sub_code": 1,
  "action_name": "NPC Interaction / Dialogue Trigger",
  "sub_name": "NPC Dialogue Init",
  "length": 8,
  "tag": "Clicked Robinson NPC",
  "hex_payload": "14 01 2A 27 00 00 00 00",
  "ascii_payload": "..*'....",
  "raw_hex": "59 E9 B5 AD 47 AC 87 8A AD AD AD AD",
  "inferred_fields": {
    "click_id": 10026
  },
  "elapsed_sec": 12.45
}
```

### 3.2 Human-Readable Card (`session_*_readable.log`)
```text
[00:00:12.450s] #00042 | C->S | AC 20 (NPC Interaction / Dialogue Trigger) Sub 1 (NPC Dialogue Init) | 8 bytes
  Tag: [Clicked Robinson NPC]
  Fields: click_id=10026
  HEX:   14 01 2A 27 00 00 00 00
  ASCII: ..*'....
```

### 3.3 Session Summary (`session_*_summary.json`)
```json
{
  "session_id": "session_20260907_144000",
  "start_time": 1725712800.0,
  "end_time": 1725712860.0,
  "duration_sec": 60.0,
  "total_packets": 150,
  "client_to_server": 65,
  "server_to_client": 85,
  "total_bytes": 12450,
  "action_code_histogram": {
    "20": 12,
    "23": 25,
    "6": 78
  },
  "tags_count": 3,
  "tags": [
    {
      "timestamp": 1725712812.45,
      "elapsed_sec": 12.45,
      "tag": "Clicked Robinson NPC",
      "packet_idx": 41
    }
  ]
}
```

---

## 4. Edge Cases & Error Handling

1. **TCP Stream Fragmentation**: If a WLO packet is received in chunks (e.g. 2 bytes in chunk 1, 20 bytes in chunk 2), `WLOStreamReassembler` buffers until `len(buffer) >= 4 + payload_len`.
2. **Corrupted Stream Synchronization**: If non-signature bytes are encountered at offset 0, the engine slides through the buffer until finding the next valid signature (`0x44F4` plain or `0x59E9` encrypted).
3. **Abrupt Client Disconnection**: Background tasks catch `asyncio.CancelledError` and socket close events, cleanly finalizing file streams so zero recorded packets are lost.
4. **Scapy Absence Fallback**: If `scapy` is not installed on the system, `RecordingSession` gracefully logs a debug notice and continues writing `.jsonl` and `.log` without failing.
