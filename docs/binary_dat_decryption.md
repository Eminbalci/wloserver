# Binary Data File Decryption

This document outlines the client-side binary data files (`.dat`) XOR decryption formulas, recipe record formats, compounding multipliers, and database-level stats/element decoding rules implemented in `server/gameserver.py`.

---

## 1. XOR Decryption Formulas

Client data files (e.g., `Compound.dat`, `Compound2.dat`, `Formula.dat`) are obfuscated using arithmetic-shifting XOR algorithms. The server implements two decrypters:

### A. 8-Bit Byte Decrypter (`_xor_byte`)
To decrypt an obfuscated single byte `v`:
$$\text{Decrypted} = ((v \oplus 0\text{xD3}) - 3) \pmod{256}$$

### B. 16-Bit Word Decrypter (`_xor_word`)
To decrypt an obfuscated 16-bit word (two combined bytes) `v`:
$$\text{Decrypted} = ((v \oplus 0\text{xFBBC}) - 3) \pmod{65536}$$

---

## 2. Compound Recipes File Parsers

The game uses two compound data files to store alchemy recipes: `Compound.dat` and `Compound2.dat`.

### A. Record Formatting
- **Header**: `Compound.dat` starts with an **8-byte header** which is skipped. `Compound2.dat` has no header.
- **Record Size**: Both files store data in fixed **65-byte records**.
- **Field Layout**:
  - `result_id` (Bytes 0-1): `_xor_word` decrypted.
  - `plan_id` (Bytes 2-3): `_xor_word` decrypted.
  - `_` (Byte 4): `_xor_byte` decrypted.
  - `tool_id` (Bytes 5-6): `_xor_word` decrypted.
  - `result_amount` (Byte 7): `_xor_byte` decrypted.
  - *Padding* (Bytes 8-10): Unused.
  - `materials` (Bytes 11-64): 5 slots of **3 bytes each**:
    - `item_id` (2 bytes): `_xor_word` decrypted.
    - `amount` (1 byte): `_xor_byte` decrypted.

---

## 3. Compounding Formula Multipliers (`Formula.dat`)

The multipliers database controls success modifiers in alchemy level calculations.
- **Header**: Starts with a **1-byte header** which is skipped.
- **Payload**: Reads consecutive **8-byte double-precision floats** (Little Endian `struct.unpack('<d')`). These values represent multiplier constants.

---

## 4. Database Stats & Element Decryption

Within the SQLite `npc_data` table, certain statistics are offset to prevent easy editing:

### A. Level Decryption
- **Validation**:
  - If the database `raw_level >= 92`:
    $$\text{Actual Level} = \max(1, \text{raw\_level} - 92)$$
  - Otherwise:
    $$\text{Actual Level} = \text{raw\_level}$$

### B. Element Decryption
- **Validation**:
  - If the database `raw_element \in [88, 92]`:
    $$\text{Actual Element} = (\text{raw\_element} - 88) \pmod 5$$
  - Otherwise:
    $$\text{Actual Element} = \text{raw\_element} \pmod 5$$
- **Element Mapping**: `0`: None/Physical, `1`: Earth, `2`: Water, `3`: Fire, `4`: Wind.

---

## 5. Authentic `Npc.dat` Parser (`NpcDatLoader`)
- **Record Size**: Exactly **138 bytes per record** (4,930 total records in `data/Npc.dat`).
- **Template ID**: Read 16-bit word at offset 12: `npc_id = ((raw_id ^ 0x5209) - 1) & 0xFFFF`.
- **NPC Name**: Stored in bytes 2 through 11 as reversed ASCII / Big5 bytes.
- **Auto-Discovery**: `GLOBAL_NPC_DAT` automatically resolves `data/Npc.dat` on initialization, indexing 4,916+ authentic NPC names (Captain, Robinson, Zhenghe, Magellan, etc.) for live logging and dialogue resolution.

