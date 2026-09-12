# Network Protocol & Packet Framing

This document details the binary wire protocol, encryption cipher, framing architecture, serialization helpers, and connection handshake mechanisms used by Wonderland Online.

## Binary Wire Framing

All TCP traffic between the client (`aLogin.exe`) and server is transmitted as length-prefixed binary frames encrypted with a single-byte symmetric XOR stream cipher.

### Packet Structure

```
+-------------------------------------------------------------+
| Byte Offset | Size   | Data Type | Description              |
+-------------------------------------------------------------+
| 0 .. 1      | 2 B    | uint16_le | Signature (0x44F4 = 17652) |
| 2 .. 3      | 2 B    | uint16_le | Payload Length (N bytes) |
| 4 .. 4+N-1  | N B    | bytes     | XOR-173 Encrypted Body   |
+-------------------------------------------------------------+
```

- **Magic Signature**: `0x44F4` (Decimal `17652`). Evaluated by both client and server to frame incoming TCP stream chunks and reject corrupted bytes.
- **Payload Length**: 16-bit little-endian integer indicating the length of the payload immediately following the header.
- **XOR Encryption**: Only bytes from index `4` onwards are encrypted. The 4-byte header (`Signature` + `Payload Length`) is sent in plaintext.

## XOR-173 Symmetric Cipher

The encryption and decryption operations are symmetrical:

$$\text{Decrypted}[i] = \text{Encrypted}[i] \oplus 173$$

$$\text{Encrypted}[i] = \text{Decrypted}[i] \oplus 173$$

Implementation (`server/network.py`):
```python
XOR_KEY = 173
SIGNATURE = 17652  # 0x44F4

def xor_crypt(data: bytes, key: int = XOR_KEY) -> bytes:
    """XORs bytes with the given key."""
    return bytes(b ^ key for b in data)
```

## Serialization Helpers

The network layer provides two core helper classes in `server/network.py`:

### 1. `PacketReader` (Deserializer)

Provides safe sequential reading of binary data types with automatic boundary checking:

| Method | Return Type | Description | Edge Case / Fallback |
| :--- | :--- | :--- | :--- |
| `read_8()` | `int` | Reads 1 unsigned byte (0..255). | Returns `0` if EOF reached. |
| `read_16()` | `int` | Reads 2-byte little-endian unsigned short. | Returns `0` if $<2$ bytes left. |
| `read_32()` | `int` | Reads 4-byte little-endian unsigned int. | Returns `0` if $<4$ bytes left. |
| `read_bool()` | `bool` | Reads 1 byte and returns `True` if non-zero. | Returns `False` on EOF. |
| `read_bytes(n)` | `bytes` | Reads exact slice of `n` bytes. | Returns remaining bytes if $<n$. |
| `read_string()` | `str` | Reads 1-byte length prefix $L$, then $L$ ASCII bytes. | Returns `""` if truncated. |
| `read_string_n()` | `str` | Consumes all remaining bytes as ASCII string. | Returns `""` on empty buffer. |
| `remaining_bytes()` | `int` | Returns count of unread bytes remaining. | Never negative. |

### 2. `PacketWriter` (Serializer)

Fluent builder pattern for constructing outgoing packet payloads:

| Method | Parameter | Description |
| :--- | :--- | :--- |
| `write_8(val)` | `int` | Appends single byte (`val & 0xFF`). Returns `self`. |
| `write_16(val)` | `int` | Appends uint16 in little-endian (`<H`). Clamps $0 \dots 65535$. |
| `write_32(val)` | `int` | Appends uint32 in little-endian (`<I`). |
| `write_64(val)` | `int` | Appends uint64 in little-endian (`<Q`). |
| `write_bool(val)` | `bool` | Appends `1` if `True`, else `0`. |
| `write_string(val)`| `str` | Writes 1-byte length prefix followed by encoded ASCII string. |
| `write_string_n(val)`| `str` | Writes raw encoded ASCII characters without length prefix. |
| `write_bytes(val)` | `bytes` | Appends raw byte array directly to buffer. |
| `to_bytes()` | -- | Returns unencrypted payload buffer. |
| `build()` | -- | Prepends 4-byte header (`0x44F4` + length) and encrypts payload with XOR-173. |

## Multi-Packet Stream Concatenation

In Wonderland Online, multiple sub-packets (such as initial battle actor spawn, stat sync, and equipment lists) are batched together into a single TCP transmission:

```python
async def send_multi_packets(self, packets: list['PacketWriter']):
    combined_payload = bytearray()
    for pkt in packets:
        combined_payload.extend(pkt.buffer)
    multi_pkt = PacketWriter()
    multi_pkt.buffer = combined_payload
    await self.send_packet(multi_pkt)
```

## Handshake & Version Validation (AC 0)

When a client initiates a TCP socket connection, it must first negotiate compatibility with Action Code `0`:

### Client Handshake Payload
- Action Code: `0`
- Sub-code: `1`
- Client Build Version: `uint16_le` (e.g. `1205`, `1206`)
- Integrity Verification: Optional binary hash of `Data\Item.dat`

### Server Handshake Responses
1. **Success**: Server responds with server version branding string:
   - Packet: `[0x00, len, "Mamiletta"...]`
2. **Version Rejection (0x41)**: If client version is unsupported:
   - Packet: `[0x00, 0x41]` (Client displays "Wrong Version" dialog and terminates).
3. **Data Integrity Error (0x45)**: If client file checksum mismatches:
   - Packet: `[0x00, 0x45]` (Client displays "Item.dat File Error").

## System Announcement Protocol (AC 23 Sub 57)

Server-wide announcements, system messages, and feedback prompts are transmitted via AC 23 Sub 57:

```python
async def send_system_msg(session: Any, msg: str) -> None:
    pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
    await session.send_packet(pkt)
```
- Payload format: `[23, 57, 0, len(msg), msg_ascii_bytes...]`
- Renders as system prompt overlay in the client dialog channel.
