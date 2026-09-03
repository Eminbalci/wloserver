# Authentic Wonderland Online NPC Shop Protocol (AC 27 / 0x1B)

## Overview

This specification documents the authentic network protocol for interacting with NPC Merchants, browsing store catalogs, purchasing goods, and selling inventory items in Wonderland Online.
The protocol was extracted and verified directly from packet capture analysis (`shoplarincalismamantigi.pcapng`, 519 decrypted packets).

---

## 1. Action Code Overview

All NPC shop dialog actions and shop window operations utilize **Action Code 27 (0x1B)** and dialogue orchestration via **Action Code 20 (0x14)**.

| Action Code | Sub-Command | Direction | Name | Description |
| :--- | :--- | :--- | :--- | :--- |
| **20 (0x14)** | **1 (0x01)** | C -> S | NPC Interaction Click | Player clicks an NPC merchant (`14 01 [click_id: uint16 LE]`). |
| **20 (0x14)** | **1 (0x01)** | S -> C | Dialogue / Menu Prompt | Server sends menu prompt with options. |
| **20 (0x14)** | **9 / 2** | C -> S | Dialog Choice Selection | Player clicks an option (e.g. `0x1E` shop menu, `0x1F` buy, `0x28` sell). |
| **27 (0x1B)** | **3 (0x03)** | S -> C | Open Props Shop | Opens the General / Consumable Store catalog window (`1b 03`). |
| **27 (0x1B)** | **4 (0x04)** | S -> C | Open Weapon Shop | Opens the Weapon / Armor Store catalog window (`1b 04`). |
| **20 (0x14)** | **9 (0x09)** | S -> C | Release Dialogue Lock | Closes the dialogue box and restores control for shop UI (`14 09`). |
| **27 (0x1B)** | **1 (0x01)** | C -> S | Buy Item Request | Player buys item from opened catalog (`1b 01 [item_id: uint16] [amount: uint8]`). |
| **27 (0x1B)** | **1 (0x01)** | S -> C | Buy ACK | Server confirms purchase (`1b 01 [status: uint8]`, 0 = Success). |
| **27 (0x1B)** | **2 (0x02)** | C -> S | Sell Item Request | Player sells item from inventory (`1b 02 [slot_idx: uint8] [amount: uint8]`). |
| **23 (0x17)** | **9 (0x09)** | S -> C | Inventory Slot Update | Updates slot quantity after sale (`17 09 [slot: uint8] [amount: uint8]`). |
| **26 (0x1A)** | **1 (0x01)** | S -> C | Gold Balance Update | Synchronizes gold after transaction (`1a 01 [gold: uint32 LE]`). |
| **27 (0x1B)** | **2 (0x02)** | S -> C | Sell ACK | Server confirms sale (`1b 02 [status: uint8]`, 0 = Success). |

---

## 2. Interaction Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Player as Game Client
    participant Server as Game Server (handle_20 / handle_27)

    Note over Player,Server: Phase 1: Talking to NPC Merchant
    Player->>Server: AC 20:1 [14 01 17 00] (Click NPC 23)
    Server->>Player: AC 20:1 Menu 1 Prompt (Options: Buy/Sell/Chat)
    Player->>Server: AC 20:9 [14 09 1e] (Select Option 0x1E: Transaction Menu)
    Player->>Server: AC 20:6 [14 06] (Confirm choice)
    Server->>Player: AC 20:1 Menu 2 Prompt [14 01 ... 06 00 02] (Options: 0x1F Buy, 0x28 Sell)

    Note over Player,Server: Phase 2A: Buying Items
    Player->>Server: AC 20:9 [14 09 1f] (Option 0x1F: Buy)
    Player->>Server: AC 20:6 [14 06] (Confirm)
    Server->>Player: AC 27:3 [1b 03] (Open Props Shop) or AC 27:4 [1b 04] (Open Weapon Shop)
    Server->>Player: AC 20:9 [14 09] (Unlock dialog)
    Player->>Server: AC 27:1 [1b 01 5a 02 02] (Buy 2x Herb)
    Server->>Player: AC 26:1 [1a 01 84 03 00 00] (Gold updated: 900)
    Server->>Player: AC 23:6 [17 06 5a 02 02 ...] (Deliver items)
    Server->>Player: AC 27:1 [1b 01 00] (Buy ACK: OK)

    Note over Player,Server: Phase 2B: Selling Items
    Player->>Server: AC 20:9 [14 09 28] (Option 0x28: Sell)
    Player->>Server: AC 20:6 [14 06] (Confirm)
    Server->>Player: AC 20:9 [14 09] (Unlock dialog -> Client displays Sell UI)
    Player->>Server: AC 27:2 [1b 02 18 01] (Sell 1x from slot 24)
    Server->>Player: AC 23:9 [17 09 18 00] (Slot 24 amount = 0)
    Server->>Player: AC 26:1 [1a 01 03 00 00 00] (Gold updated: +3)
    Server->>Player: AC 27:2 [1b 02 00] (Sell ACK: OK)
```

---

## 3. Wire Format Specification

### 3.1 AC 27 Sub 2: Sell Item Request (Client -> Server)
```
[0x1B] [0x02] [slot_index: 1B] [amount: 1B]
Example: 1b 02 18 01 -> Sell 1 item from slot 24 (0x18)
```

### 3.2 AC 27 Sub 2: Sell Confirmation (Server -> Client)
```
[0x1B] [0x02] [status: 1B]
0x00 = Transaction successful
0x01 = Transaction failed / item not found
```

### 3.3 AC 27 Sub 1: Buy Item Request (Client -> Server)
```
[0x1B] [0x01] [item_id: 2B LE] [amount: 1B]
Optionally prefixed by shop_id and tab_id if sent by specific client versions.
```

### 3.4 AC 27 Sub 1: Buy Confirmation (Server -> Client)
```
[0x1B] [0x01] [status: 1B]
0x00 = Purchase successful
0x01 = Insufficient funds (Gold)
0x02 = Inventory full
```
