# User & IP Ban System and Account Search Specification

## Overview
The Wonderland Online Server now features a comprehensive security and ban management system supporting:
1. **User Account Banning**: Account-level ban with custom reason strings.
2. **IP Address Banning**: Network-level ban with subnet/IP tracking and loopback protection.
3. **Last Login IP Tracking**: Recording `last_ip` and `last_login` timestamps in SQLite upon successful authentication.
4. **Universal Multi-Field Search**: Instant query resolution across IP, character name, username, character ID, and user ID.
5. **Real-Time Live Enforcement**: Immediate session termination upon banning online accounts or IP addresses.
6. **Web Admin Dashboard & Desktop GUI Integration**: Visual interfaces with search bars, action buttons, and active banned IP lists.

---

## Database Schema & Migrations

### `banned_ips` Table
```sql
CREATE TABLE IF NOT EXISTS banned_ips (
    ip TEXT PRIMARY KEY,
    reason TEXT DEFAULT '',
    banned_at TEXT,
    banned_by TEXT
);
```

### `users` Table Migrations
- `last_ip TEXT DEFAULT ''`: Records client IP upon successful login.
- `last_login TEXT DEFAULT ''`: ISO 8601 formatted timestamp of the user's last session.
- `ban_reason TEXT DEFAULT ''`: Explanatory message provided when the account was banned.

---

## Core Methods & API

### Database Interface (`server/database.py`)
- `update_user_last_login(user_id: int, ip: str) -> None`: Updates `last_ip` and `last_login` timestamp for the given `user_id`.
- `ban_user(user_id: int, reason: str = "", banned: int = 1) -> None`: Sets `banned` status and `ban_reason`.
- `is_user_banned(user_id: int) -> bool`: Checks if user is banned.
- `ban_ip(ip: str, reason: str = "", banned_by: str = "admin") -> None`: Adds or updates IP entry in `banned_ips`. Loopback IPs (`127.0.0.1`, `localhost`, `0.0.0.0`) are safely rejected.
- `unban_ip(ip: str) -> None`: Removes IP from `banned_ips`.
- `is_ip_banned(ip: str) -> bool`: Checks if IP exists in `banned_ips`. Always returns `False` for localhost/loopback.
- `get_banned_ips() -> List[Dict[str, Any]]`: Returns all active banned IPs with reason, timestamp, and admin info.
- `search_accounts(query: str) -> List[Dict[str, Any]]`: Performs multi-field search against `username`, `last_ip`, `characters.name`, `users.id`, and `characters.id`. Returns enriched account records with associated character summaries, ban status, and IP ban status.

### Game Server Enforcement (`server/gameserver.py`)
- `handle_connection(reader, writer)`: Checks `is_ip_banned(session.ip)`. If banned, sends error code 4 and disconnects socket immediately.
- `kick_user(user_id: int, reason: str)`: Disconnects any active session associated with `user_id`.
- `kick_ip(ip: str, reason: str)`: Terminates all active sessions matching `ip`.
- `ban_user(user_id: int, reason: str)`: Updates database and invokes `kick_user`.
- `unban_user(user_id: int)`: Unbans user in database.
- `ban_ip(ip: str, reason: str, banned_by: str)`: Updates database and invokes `kick_ip`.
- `unban_ip(ip: str)`: Unbans IP in database.

### Login Protocol Handling (`server/handlers/handle_63_login.py`)
- **IP Ban Verification**: Evaluates `server.db.is_ip_banned(session.ip)`. If banned, returns `AC 63 Sub 4` with message `"Your IP address has been banned."`
- **Account Ban Verification**: Evaluates `user_data.get('banned')`. If banned, returns `AC 63 Sub 4` with message `"This account has been banned."`
- **Successful Authentication**: Updates last login info via `server.db.update_user_last_login(session.user_id, session.ip)`.

---

## Web Admin Dashboard Endpoints (`server/web_admin.py`)
- `GET /api/security/search?q=<query>`: Returns accounts matching search query annotated with live online status.
- `GET /api/security/banned_ips`: Returns list of currently banned IPs.
- `POST /api/security/ban_user`: `{"user_id": int, "reason": str}` -> Bans user and kicks active session.
- `POST /api/security/unban_user`: `{"user_id": int}` -> Restores user account.
- `POST /api/security/ban_ip`: `{"ip": str, "reason": str}` -> Bans IP and kicks all matching sessions.
- `POST /api/security/unban_ip`: `{"ip": str}` -> Removes IP ban.

---

## Desktop GUI (`server/gui_app.py`)
- **Users & Accounts Manager (Tab 4)**: Includes a real-time search field supporting IP, Character Name, Username, and ID. Displays columns: `AccountID`, `Username`, `Characters`, `LastIP`, `LastLogin`, `UserBan`, `IPBan`, and `GMLevel`. Action buttons allow instant Ban User, Unban User, Ban IP, and Unban IP.
- **Online Sessions (Tab 3)**: Action panel provides a quick `🌐 Ban Player IP` button to ban the client IP directly from live gameplay.
