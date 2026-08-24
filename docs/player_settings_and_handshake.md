# Player Settings & Connection Handshake

This document outlines the server-side connection handshake flows, versioning updates, sub-server configuration transmissions, and player options settings implemented in `server/handlers/handle_0_handshake.py` and `server/handlers/handle_33_settings.py`.

---

## 1. Connection Handshake (Opcode 0)

When a client establishes a TCP socket connection, it initiates communication by sending **Opcode 0** (handshake packet).

### A. Handshake Packet Sequence
The server responds to Opcode 0 by returning two configuration packets to authenticate the client:

1. **Server Version Packet (Opcode 1, Sub-opcode 9)**:
   - Synchronizes the server name and version string back to the client.
   - Payload: `[1, 9, padding (3 bytes), server_version_string]`.
2. **Sub-Server Configuration (Opcode 54, Sub-opcode 29)**:
   - Configures connection rules and default sub-server parameters using a static byte configuration array (`SUBSERVER_CONFIG`).
   - Payload: `[54, 29, config_bytes]`.

---

## 2. Player Settings Toggles (Opcode 33)

The settings system maps user options toggled in the system menu using **Opcode 33** (0x21).

### A. Settings Toggling Options (Sub-opcode 1)
- **Request**: Client sends **Opcode 33, Sub-opcode 1** containing:
  - `setting_type` (1 byte)
  - `value` (1 byte)
- **Toggles**:
  - `setting_type = 1` (PK Mode Toggle): Modifies `session.pkable`. Pushes `1` (if enabled) or `2` (if disabled).
  - `setting_type = 2` (Team Invite Toggle): Modifies `session.joinable`. Pushes `1` (if enabled) or `2` (if disabled).
  - `setting_type = 4` (Trade Request Toggle): Modifies `session.tradable`. Pushes `1` (if enabled) or `2` (if disabled).
- **Confirmation Echo**: The server echoes:
  - `[33, 1, setting_type, value_result]`.

### B. Chat Channels Mask (Sub-opcode 3)
- **Request**: Client sends **Opcode 33, Sub-opcode 3** containing:
  - `chat_channels_mask` (1 byte)
- **Outcome**: Server updates `session.chat_channels_mask` and saves the setting to the character's SQLite profile.
- **Confirmation Echo**: The server echoes:
  - `[33, 3, chat_channels_mask]`.
