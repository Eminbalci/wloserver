# Wonderland Online - Remaining Systems & Technical Audit

## 1. Executive Summary
This document outlines the final, comprehensive set of remaining Wonderland Online subsystems extracted from deep decompilation analysis of `aLogin.exe.1.c`, the C# core server architecture (`wlo.pserver.core`), and official game data protocols.

---

## 2. Master System Inventory Table

| System | Action Codes / Protocol | C# / Client Source | Description |
| :--- | :--- | :--- | :--- |
| **1. PvP Duels, Arena & PK Engine** | `AC 11:1/2`, `AC 27`, `AC 32` | [`PvPManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/Battle/PvPManager.cs) | 1v1 duels, 4v4 arena rankings (Rank 1-4), PK red-name status, PK points, and Jail map prison. |
| **2. Transformation & Morphs** | `AC 21:10` | `client_game_systems_extended.md` | Monster disguise morphs (Jelly, Wolf, Siren), appearance replacement, duration timers, stat buffs. |
| **3. Barber, Hair & Dyeing** | `AC 21:1/2` | `AC21.cs` | Hair styling, hair dye color changes, clothing and skin color alterations. |
| **4. Bank Vault & Bag Expansion** | `AC 13:10`, `AC 34` | `Equip.cs`, `Character.cs` | Town bank gold deposits/withdrawals, vault item storage, and inventory slot expansion bags (`38001`). |
| **5. Pet Riding & Saddle Speed** | `AC 82`, `AC 85` | `AdjustRidePetPos.txt` | Pet saddle (`38020`) mounting, +30%..+50% movement speed multipliers, riding sprite offset synchronization. |
| **6. Item Recycle & Smelting** | `AC 64:10` | `TentManufactureManager.cs` | Smelting unused equipment and armor into base raw ores, wood, and refined materials. |
| **7. Death Penalty & Ghost Mode** | `AC 11:9`, `AC 12` | `PvEBattleManager.cs` | Combat knockout EXP penalty (-1..-5%), ghost state, and automatic hospital/temple revive coordinates. |
| **8. Character Deletion Security** | `AC 35:1/2` | `AC35.cs` | Character deletion verification using the 4-6 character delete code generated during registration. |
| **9. Server Events & Double EXP** | `AC 23:57`, `AC 57` | `client_advanced_systems.md` | Scheduled Double EXP hours, Dragon Boat festival, and voyage sailing speed events. |
| **10. GM Console & Command Suite** | In-Game Chat (`:cmd`) | [`GmManager.cs`](file:///d:/GitHub/Wonderland-Private-Server/wlo.pserver.core/Game/PlayerRelated/GmManager.cs) | Comprehensive admin commands: `:item`, `:gold`, `:warp`, `:kick`, `:ban`, `:spawn`, `:speed`, `:godmode`. |

---

## 3. In-Depth Technical Specifications

### 3.1. PvP Duel, Arena & PK Engine
- **Duel Flow (`AC 11`)**:
  - `AC 11 Sub 1`: Target player receives duel invite modal `[11, 1, challenger_id (4B)]`.
  - `AC 11 Sub 2`: Target accepts/declines `[11, 2, accept (1B)]`.
  - `AC 27`: Initiates 1v1 PvP combat instance without exp loss on defeat.
- **PK System (`AC 32`)**:
  - Toggling PK mode changes player character name to Yellow/Red.
  - Defeating white-name players accumulates PK points (+1 per kill).
  - Players with PK $\ge 3$ are teleported to Jail Map (`60001`) upon death or town guard proximity.

---

### 3.2. Transformation & Morphs (`AC 21:10`)
- **Mechanics**:
  - Consuming Transformation Pills or Monster Disguises (e.g. Jelly `41001`, Wolf `41002`, Siren `41003`) temporarily replaces character sprite with the monster's `npc_id`.
  - Sets active duration timer (e.g. 15 minutes).
  - Grants temporary passive combat stats (e.g. +10% SPD, +15% MATK).
  - Automatically dismounts stalls, mounts, and hot spring bathing.

---

### 3.3. Barber, Hair Styling & Color Dyeing (`AC 21:1`)
- **Mechanics**:
  - Interacting with Barber NPC opens styling interface.
  - Updates character `hair_style` (0..15), `hair_color` (RGB 16-bit packed), and `body_dye`.
  - Deducts gold or Dye item and broadcasts updated visual appearance to map.

---

### 3.4. Bank Vault & Inventory Expansion (`AC 13:10`)
- **Mechanics**:
  - **Town Bank**: Bank NPC allows depositing/withdrawing gold safely beyond player wallet limit.
  - **Item Storage**: Bank vault provides up to 50 additional item slots per character.
  - **Bag Expansion**: Consuming Expansion Bags (`38001`) permanently unlocks +5 inventory slots (up to max 50 slots).

---

### 3.5. Pet Riding & Saddle Speed (`AC 82 / AC 85`)
- **Mechanics**:
  - Equipping Pet Saddle (`38020`) on rideable companions (e.g. Horse, Tiger, Dragon, Kangaroo, Wolf).
  - Player mounts pet; server broadcasts `AC 82 Sub 1` with ride sprite offsets from `AdjustRidePetPos.txt`.
  - Applies a +30% to +50% movement speed multiplier across all overworld maps.

---

### 3.6. Item Recycle & Smelting Furnace (`AC 64:10`)
- **Mechanics**:
  - Interacting with Tent Smelting Furnace allows dismantling unused weapons, armor, and tools.
  - Yields recycled base materials: Iron Ore (`27020`), Copper Ore (`27021`), Coal (`27022`), and Ordinary Wood (`27001`).

---

### 3.7. Death Penalty, Ghost State & Revive Points
- **Mechanics**:
  - Player party defeat in PvE combat incurs a 1% to 5% current level EXP loss.
  - Enters Ghost state and warps character to the map's designated Temple/Hospital altar (e.g. Kelan Village Altar Map 10010: X=450, Y=380).
  - Restores HP to 1 and SP to 1.

---

### 3.8. Character Deletion Security (`AC 35`)
- **Mechanics**:
  - When user requests character deletion in slot selection screen, server prompts for the 4-6 digit `char_delete_code`.
  - Verifies code against SQLite `users` table. If valid, deletes character records and frees name.

---

### 3.9. Scheduled Server Events & Double EXP Engine
- **Mechanics**:
  - Server-side event scheduler enabling global `Double EXP` multipliers (2.0x combat exp).
  - Broadcasts system marquee announcements to all online sessions.
  - Voyage/Sailing events with 50% discount on vehicle repair and double fishing drops.

---

### 3.10. GM Console & Command Suite (`:cmd`)
- **Mechanics**:
  - Restricted to accounts with `is_gm = 1`.
  - Available commands:
    - `:item <id> <count>`: Adds item directly to inventory.
    - `:gold <amount>`: Grants gold.
    - `:warp <map_id> <x> <y>`: Instantly teleports to coordinates.
    - `:speed <multiplier>`: Sets movement speed.
    - `:level <lv>`: Sets character level and recalculates stats.
    - `:kick <char_name>`: Disconnects target player.
    - `:ban <char_name>`: Permanently bans target account.
    - `:broadcast <msg>`: Global server marquee announcement.
    - `:godmode`: Invincibility in battle.
    - `:heal`: Restores 100% HP/SP.
