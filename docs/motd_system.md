# MOTD (Message of the Day) & Server Branding System

## Overview
The Wonderland Online Server MOTD and Server Branding system provides live runtime customization and persistence for login welcome messages, server name branding, and global announcements.

---

## Technical Specifications

### 1. Server Branding (Mamiletta / Custom Name)
- **Protocol**: Handled during client handshake `AC 0 Sub 0`.
- **Response**: `AC 1 Sub 9` sends the configured server version/brand string.
- **Persistence**: Stored in `server_config` table under key `server_name`.
- **Hot-reload**: `GameServer.set_server_name(name)` updates `server.SERVER_VERSION` in memory and commits to SQLite.

### 2. Message of the Day (MOTD)
- **Triggers**:
  - `AC 89 Sub 0` (Client scene readiness): Responds with `AC 90 Sub 1` ACK and calls `server.dispatch_login_motd(session)`.
  - `AC 92 Sub 1` (Map scene finalization): Calls `server.dispatch_login_motd(session)` if not already sent.
- **Packets Dispatched**:
  - **Popup Dialog**: `AC 23 Sub 57 [23, 57, 0, len, text_bytes]` (Client displays a native modal message box).
  - **GM Chatbox Announcement**: `AC 2 [2, 4, 0, 0, 0, 0, len, text_bytes]` (Chat type 4 = GM Red announcement).
- **Multi-line Support**: Splitting by newline (`\n`) dispatches each line sequentially to the client's chat history.
- **Persistence**: Stored in `server_config` table under key `welcome_message`.

---

## GUI Controls
- **Dashboard (Tab 1)**:
  - Multi-line MOTD Textbox with `💾 Save MOTD` and `📢 Broadcast MOTD` (instant dispatch to all online players).
  - Server Name entry with `💾 Save Server Name (Brand)`.
- **Global Settings (Tab 13)**:
  - Direct parameter configuration with `💾 Save Settings & Apply Live`.
