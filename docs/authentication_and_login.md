# Authentication & Login System

This document outlines the server-side login credential validations, account ban checks, slot allocation structures, and character select redirects implemented in `server/handlers/handle_63_login.py`.

---

## 1. Credentials Authentication (Opcode 63)

Player sessions begin by sending credentials via **Opcode 63, Sub-opcode 4**.

### A. Database Verification
- **Verifying User**: Server queries the SQLite database matching the username and password strings.
- **Failures & Rejections**:
  - If mismatch occurs: Server sends a login failure response `[63, 2]` followed by socket connection termination command `[1, 6]`.
- **Banned Accounts Check**:
  - If `banned = 1` is set in the database: Server rejects the request, alerts the client using warning overlay string `"This account has been banned."`, and terminates connection via `[1, 6]`.

### B. Client Version & File Integrity Verification
Before database authentication, the server inspects the 16-bit client build version and file integrity tokens:
- **Version Check**: Evaluates if the received `client_version` is within `server.version_validator` allowed list.
- **Failures & Rejections**:
  - If version mismatch or file error occurs: Server transmits Opcode 0 with the authentic disconnect reason code (e.g., `[0, 65]` for `"Wrong Version"`, `[0, 69]` for `"Item.dat File Error"`) followed by `[1, 6]` socket termination. See [docs/client_version_and_integrity_validation.md](client_version_and_integrity_validation.md).

### C. Character List Refresh (Sub-opcode 1)
Upon successful credential checks, the server writes and pushes character availability arrays using **Opcode 63, Sub-opcode 1**:
- **Character Slot 1**: If active, writes slot serialization block. If empty, writes placeholder bytes `[1, 0]`.
- **Character Slot 2**: If active, writes slot serialization block. If empty, writes placeholder bytes `[2, 0]`.

---

## 2. Character Slot Selection (Sub-opcode 2)

After viewing the list, the player chooses a character slot (1 or 2) to log into.

### A. Slot Redirection & Creation Trigger
If the selected slot does not contain character database records:
- **Redirection**: The server commands the client to open the character creator overlay by sending **Opcode 1, Sub-opcode 3**.
- **Cipher Parameter**: Pushes a boolean indicating if a security code password is set: `[1, 3, has_cipher]`.

### B. Login Confirmation & Map Entry
If the selected slot contains a valid character:
- **Confirmation**: The server acknowledges character select by transmitting **Opcode 63, Sub-opcode 2** along with the character ID:
  - Payload: `[63, 2, char_id (4 bytes)]`.
- **Commence Login**: Triggers state initialization, loading saved location variables (MapID, X, Y), and spawns the character on the target map.
