# Client Version & File Integrity Validation

This document specifies the server-side client version verification, data file integrity checks, and authentic Opcode 0 disconnect error protocols implemented in `server/version_validator.py` and `server/handlers/handle_63_login.py`.

---

## 1. Network Protocol Specifications

During player authentication (**Action Code 63, Sub-opcode 4**), the client transmits a structured binary frame containing build version information and file integrity tokens:

```
[63] [4] [client_version: uint16] [username: string] [password: string] [file_check_payload: bytes]
```

### Protocol Fields
- `Opcode` (`uint8`): `63` (`0x3F`) - Authentication.
- `Sub-opcode` (`uint8`): `4` (`0x04`) - Login credential submission.
- `client_version` (`uint16`, Little-Endian): Client build number (e.g. `1205`, `1209` / `0x04B9`).
- `username` (`string`): Length-prefixed ASCII string (1-byte length).
- `password` (`string`): Length-prefixed ASCII string (1-byte length).
- `file_check_payload` (`bytes`): Checksum verification bytes derived from `Data\Item.Dat` and client executable files.

---

## 2. Server Response on Version / Integrity Mismatch (Opcode 0)

When client build version or file checks fail, official servers reject entry by transmitting an authentic **Opcode 0 Disconnect Reason Packet**:

```
[0] [reason_code: uint8]
```

Payload length is 2 bytes, encapsulated with standard framing signature `0x44F4`.

### Authentic Disconnect Error Codes (`ClientDisconnectReason`)

Directly derived from the 95-case switch jump table in `aLogin.exe` (`FUN_002f21b8`):

| Reason Code (Dec) | Reason Code (Hex) | Client UI Dialog / Behavior | Context |
| :--- | :--- | :--- | :--- |
| **`65`** | `0x41` | `"Wrong Version"` popup & immediate socket termination | Client version does not match allowed server build range. |
| **`69`** | `0x45` | `"Item.dat File Error"` popup & disconnect | `Data\Item.Dat` mismatch or corrupted client table. |
| **`17`** | `0x11` | `"Data Altered"` alert | Modified client binaries or tampered memory. |
| **`16`** | `0x10` | `"Update Game Files"` prompt | Patcher update requirement. |
| **`15`** | `0x0F` | `"Blocked IP Detected"` | Network IP blacklist trigger. |
| **`29`** | `0x1D` | `"Account Lock"` | Account temporary lockout. |
| **`30`** | `0x1E` | `"Login ID Unavailable"` | Name reservation conflict. |
| **`32`** | `0x20` | Character Slot Error | Invalid slot index selected. |

---

## 3. Module Architecture (`server/version_validator.py`)

### `ClientVersionValidator`

#### Constructor
`ClientVersionValidator(db=None)`
- **Parameters**: `db` (optional): Database instance providing access to `server_config`.

#### Methods

##### `validate(client_version: int, verification_payload: bytes = b"") -> Tuple[bool, int, str]`
- **Parameters**:
  - `client_version` (`int`): Unsigned 16-bit integer extracted from login packet.
  - `verification_payload` (`bytes`): Trailing verification tokens from client packet.
- **Returns**: `Tuple[bool, int, str]`:
  - `is_valid` (`bool`): `True` if client is authorized to proceed, `False` otherwise.
  - `reason_code` (`int`): Error code from `ClientDisconnectReason` (e.g. `65`).
  - `message` (`str`): Human-readable diagnostic description.
- **Exceptions**: None (guaranteed safe execution with fallback to safe defaults).

##### `build_disconnect_packet(reason_code: int) -> PacketWriter`
- **Parameters**: `reason_code` (`int`): Disconnect reason byte.
- **Returns**: `PacketWriter` initialized with payload `[0, reason_code]`.

##### `set_allowed_versions(versions: Set[int] | list[int]) -> None`
- Persists allowed client version list to database table `server_config` under key `allowed_client_versions`.

##### `set_enforced(enforced: bool) -> None`
- Toggles version checking on/off, saved to `server_config` under key `enforce_client_version`.

---

## 4. Edge Cases & Resilience

1. **Missing or Corrupted Length Bytes**: Reader offset checks guard against truncated packets.
2. **Missing Database Records**: When `server_config` is empty or missing, defaults safely to standard official client version range `[1205, 1206, 1207, 1208, 1209, 1210]`.
3. **Dual Packet Termination**: Sends disconnect reason packet `[0, 65]` immediately followed by connection close command `[1, 6]` to guarantee both client UI alert display and clean TCP socket teardown.
