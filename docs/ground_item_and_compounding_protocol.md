# Authentic Ground Item Pickup & Compounding (Alchemy) Protocol

## 1. Overview
Reverse-engineered from authentic live game captures (`yerdenitemalipcompounddaikiitemikaristirdim.pcapng`).
Covers:
1. Ground item interaction & despawn broadcast (`AC 23 Sub 2`), with direct inventory delivery (`AC 23 Sub 6`).
2. Multi-item compounding request (`AC 23 Sub 14`), map animation broadcast (`AC 23 Sub 122`), ingredient consumption (`AC 23 Sub 9`), result item placement (`AC 23 Sub 8`), and client synthesis window trigger (`AC 23 Sub 13`).

---

## 2. Ground Item Pickup Subsystem

### Client Request: `AC 23 Sub 2`
- **Length**: 4 bytes
- **Direction**: `Client -> Server`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `2` (`0x02`) |
  | 2..3 | Ground Index | `uint16_LE` | 1-based index of the item on map (e.g. `1..256`) |

### Server Response 1: Despawn Broadcast `AC 23 Sub 2`
- **Length**: 5 bytes
- **Direction**: `Server -> Broadcast (Map)`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `2` (`0x02`) |
  | 2..3 | Ground Index | `uint16_LE` | Ground slot being removed |
  | 4 | Status | `uint8` | `1` (Success / Despawn) |

### Server Response 2: Item Delivery `AC 23 Sub 6`
- **Length**: 33 bytes
- **Direction**: `Server -> Player Session`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `6` (`0x06`) |
  | 2..3 | Item ID | `uint16_LE` | ID of the item picked up |
  | 4..5 | Quantity | `uint16_LE` | Stack amount |
  | 6..32 | Reserved | `bytes[27]` | Zero bytes padding |

---

## 3. Compounding / Alchemy Subsystem

### Client Request: `AC 23 Sub 14`
- **Direction**: `Client -> Server`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `14` (`0x0E`) |
  | 2 | Slot Count | `uint8` | Number of ingredients (e.g. `2`) |
  | 3..N | Slots | `uint8[]` | 1-indexed inventory slot numbers (e.g. `[19, 18]`) |

### Server Broadcast: Compounding Animation `AC 23 Sub 122`
- **Length**: 6 bytes
- **Direction**: `Server -> Broadcast (Map)`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `122` (`0x7A`) |
  | 2..5 | Character ID | `uint32_LE` | Character performing the compounding action |

### Server Response 1: Deduct Ingredients `AC 23 Sub 9`
- **Length**: 4 bytes (Dispatched once per input slot)
- **Direction**: `Server -> Player Session`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `9` (`0x09`) |
  | 2 | Slot | `uint8` | Inventory slot being deducted |
  | 3 | Amount | `uint8` | Quantity consumed (`1`) |

### Server Response 2: Outcome Placement `AC 23 Sub 8`
- **Length**: 33 bytes
- **Direction**: `Server -> Player Session`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `8` (`0x08`) |
  | 2 | Slot | `uint8` | Target inventory slot |
  | 3..4 | Item ID | `uint16_LE` | Synthesized item ID |
  | 5 | Quantity | `uint8` | Output quantity (`1`) |
  | 6..32 | Reserved | `bytes[27]` | Zero bytes padding |

### Server Response 3: Synthesis Window Result `AC 23 Sub 13`
- **Length**: 6 bytes
- **Direction**: `Server -> Player Session`
- **Structure**:
  | Offset | Field | Type | Description |
  |---|---|---|---|
  | 0 | Opcode | `uint8` | `23` (`0x17`) |
  | 1 | Subcode | `uint8` | `13` (`0x0D`) |
  | 2..3 | Item ID | `uint16_LE` | Synthesized item ID |
  | 4 | Quantity | `uint8` | Output quantity (`1`) |
  | 5 | Slot | `uint8` | Inventory slot containing output |
