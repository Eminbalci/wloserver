# Wonderland Online Extended Systems Technical Documentation

## 1. Advanced Turn-Based Battle Engine ([`server/battle_engine.py`](file:///d:/GitHub/Wonderland%20Online/server/battle_engine.py))
- **Status Effects Engine**: Multi-turn duration tracker for `Freeze`, `Stone`, `Sleep`, `Tree`, `Silence`, `Confusion`, `Poison`, `Shield`, and `Reflect`.
- **SPD Combo Attacks**: Calculates synchronized multi-character combo attacks based on SPD delta $\le 25$.
- **AOE Targeting**: Patterns for `Single`, `Line` (vertical column), `Cross` (5 targets), `FrontRow` (4 targets), `Square4` (2x2 grid), and `All8`.
- **Loot Distribution**: Party-wide weighted monster drops via `MonsterDropManager`.
- **12 Palaces Trial**: Sequenced Zodiac boss stages (Aries to Pisces) with chests and trial rewards via `PalaceTrialManager`.

---

## 2. Secure P2P Trading & Street Stalls ([`server/trade_system.py`](file:///d:/GitHub/Wonderland%20Online/server/trade_system.py) & [`server/stall_system.py`](file:///d:/GitHub/Wonderland%20Online/server/stall_system.py))
- **P2P Trade (AC 25 / AC 29)**: Two-phase state machine ensuring atomic item and gold transfers with rollback on disconnection.
- **Street Stalls (AC 40 / AC 56:30)**: World map vending with custom shop signs, price tags, remote browsing, item purchase, and gold remittance.

---

## 3. In-Game Mailbox & Attachment System ([`server/mail_system.py`](file:///d:/GitHub/Wonderland%20Online/server/mail_system.py))
- **Mailing Protocol (AC 30 / AC 31)**: Send/receive letters between characters (online/offline).
- **Attachments**: Gold and inventory items attached to letters.
- **Persistence**: Managed in SQLite `charmail` table.

---

## 4. Guild System & Guild Storage ([`server/guild_system.py`](file:///d:/GitHub/Wonderland%20Online/server/guild_system.py))
- **Guild Management (AC 39 / AC 2:4)**: Guild creation (Level 30+, 100k Gold), member ranks (Leader, ViceLeader, Member), invites, kicks, announcements, and guild chat.
- **Shared Storage**: Deposit/withdraw items with permission validation.
- **Persistence**: Managed in SQLite `guilds`, `guild_members`, and `guild_storage` tables.

---

## 5. Marriage & Couple System ([`server/marriage_system.py`](file:///d:/GitHub/Wonderland%20Online/server/marriage_system.py))
- **Marriage Protocol (AC 44)**: Proposals (Level 30+, 60k Gold), ceremony celebrations with heart fireworks (`AC 5:5: 60012`).
- **Couple Teleport**: Instantly warp to spouse's coordinates across maps.
- **Persistence**: Managed in SQLite `charmarriage` table.

---

## 6. Vehicles, Mounts & Sea Voyage ([`server/vehicle_system.py`](file:///d:/GitHub/Wonderland%20Online/server/vehicle_system.py))
- **Vehicle Fleet (AC 15:10 / AC 59)**: Rafts, Canoes, Sailboats, Steamboats, Submarines, Hot Air Balloons, Airships, UFOs, Motorcycles, Beetle Cars.
- **Mount & Dismount**: Broadcasts vehicle visuals to current map.
- **Sea Voyage**: Encounter chances for ocean monsters during water transit.

---

## 7. Rebirth & 6 Advanced Job Classes ([`server/reborn_system.py`](file:///d:/GitHub/Wonderland%20Online/server/reborn_system.py))
- **Rebirth Engine**: Level 100+ character rebirth, resets to Lv 1 Reborn with stat multipliers.
- **6 Specializations**:
  - `Killer`: ATK +30%, Critical Rate +15%
  - `Warrior`: DEF +30%, Physical Reflect
  - `Knight`: SPD +30%, Mounted boost
  - `Wit`: MATK +30%, Spell power
  - `Priest`: MDEF +30%, Healing potency
  - `Seer`: Status sealing +25%
- **Rebirth Cape & Effects**: Grants class cape (`23001`..`23006`) and plays ascension aura (`AC 5:5: 60050`).

---

## 8. Pet Amity, Death Penalty & Pet Rebirth ([`server/pet_amity_system.py`](file:///d:/GitHub/Wonderland%20Online/server/pet_amity_system.py))
- **Amity Tracking (0..100)**: Deducts 2 Amity on pet knockout in combat.
- **Runaway Threshold**: If Amity $\le 20$, pet permanently leaves the player.
- **Pet Feeding**: Feeds Rice Balls (+3), Roast Meat (+2), or Fruit (+1) with love emotes (`60012`).
- **Pet Rebirth**: Reincarnates Level 100+ companion pets with upgraded base stats and potentials.

---

## 9. Mini-Games & Lucky Draw ([`server/minigames_system.py`](file:///d:/GitHub/Wonderland%20Online/server/minigames_system.py))
- **Lucky Draw Wheel (AC 75)**: Weighted prize pool spinning with IM tokens/gold, rare item fireworks, and server announcements.
- **Gobang Board Game (AC 104)**: Real-time 2-player 15x15 board match with turn validation, five-in-a-row detection, and winner rewards.

---

## 10. AFK Gathering Engine ([`server/gathering_system.py`](file:///d:/GitHub/Wonderland%20Online/server/gathering_system.py))
- **Mining, Woodcutting & Fishing**: Periodic 5-second asynchronous harvesting ticks.
- **Resource Pools**: Iron, Copper, Coal, Silver, Gold Ore; Wood, Pine, Cypress, Willow, Vine; Crab, Trout, Salmon, Eel, Seaweed.
- **Animations**: `AC 5:12` (Fishing action) and `AC 5:14` (Mining / Woodcutting action).

---

## 11. World Map Interactive Treasure Chests ([`server/chest_system.py`](file:///d:/GitHub/Wonderland%20Online/server/chest_system.py))
- **Map Loot Tables**: Custom drop pools per map (Shipwreck Beach, Kelan Woods, Kelan Village, Maka Cave).
- **Key Verification**: Bronze/Copper Key (`48001`), Silver Key (`48002`), Gold Key (`48003`).
- **Persistence**: Player chest completions recorded in SQLite `charchests` table.

---

## 12. Equipment Forging & Spar Gem Sockets ([`server/forging_system.py`](file:///d:/GitHub/Wonderland%20Online/server/forging_system.py))
- **Spar Gems**: +24 ATK Spar (`47001`), +24 DEF Spar (`47002`), +24 MATK Spar (`47003`), +24 MDEF Spar (`47004`), +24 SPD Spar (`47005`), Brilliant Diamond (`47010` +42 Stats).
- **Anvil Effect**: Broadcasts forging spark animation (`AC 5:5: 60025`).

---

## 13. Equipment Durability & Repairs ([`server/repair_system.py`](file:///d:/GitHub/Wonderland%20Online/server/repair_system.py))
- **Combat Decay**: Weapons and armor lose durability during attacks and defense.
- **Spanner Tool (`38030`)**: Restores item durability to max directly in inventory.
- **Blacksmith NPC**: Repairs all equipment for gold.

---

## 14. Advanced Alchemy & Compounding Books ([`server/alchemy_system.py`](file:///d:/GitHub/Wonderland%20Online/server/alchemy_system.py))
- **Alchemy Books (I-IV)**: `30010`..`30013` boosting compound success rank by +1 to +4.
- **Progression**: Alchemy levels (Primary, Junior, Senior) gaining EXP on each synthesis.

---

## 15. Auto-Recovery Sustenance & Rice Balls ([`server/sustenance_system.py`](file:///d:/GitHub/Wonderland%20Online/server/sustenance_system.py))
- **Sustenance Pools**: Consuming Rice Balls (`30025`) or Potions adds to active 50,000 HP/SP buffer.
- **Post-Combat Trigger**: Heals character and active companion pets to 100% HP/SP immediately upon battle victory.

---

## 16. Player Titles & Achievement Engine ([`server/title_system.py`](file:///d:/GitHub/Wonderland%20Online/server/title_system.py))
- **Title Unlocks**: Storyline and milestone title registry with passive stat buffs (HP, ATK, DEF, SPD).
- **Equipping (`AC 186`)**: Broadcasts active title to map; list synchronization (`AC 183`).

---

## 17. Secondary Security PIN Lock ([`server/security_pin.py`](file:///d:/GitHub/Wonderland%20Online/server/security_pin.py))
- **6-Digit Cryptographic PIN**: SHA-256 protected secondary lock (`AC 226`) safeguarding character deletion, trading, and bank access.

---

## 18. Map Weather Engine ([`server/weather_system.py`](file:///d:/GitHub/Wonderland%20Online/server/weather_system.py))
- **Atmospheric Effects (`AC 57`)**: Rain, Snow, Sakura Blossom Petals, Dense Fog, and Thunderstorms per map zone.

---

## 19. Multi-Stage Party Instance Dungeons ([`server/instance_system.py`](file:///d:/GitHub/Wonderland%20Online/server/instance_system.py))
- **Dungeons**: Ghost Ship, Maya Alien Base, Pirate Cove.
- **Wave System**: Multi-room progression, boss encounters, reward chests, and 24-hour daily cooldowns.

---

## 20. Netcode Security & Anti-Cheat Engine ([`server/anti_cheat.py`](file:///d:/GitHub/Wonderland%20Online/server/anti_cheat.py))
- **Velocity Speedhack Check**: Monitors tile traversal speed vs elapsed time.
- **Packet Flood Throttling**: Limits rate to 40 packets/s to prevent DDoS and exploit injections.

---

## 21. PvP Duel, Arena & PK Engine ([`server/pvp_system.py`](file:///d:/GitHub/Wonderland%20Online/server/pvp_system.py))
- **1v1 Duels (`AC 11:1/2`, `AC 27`)**: Safe combat dueling without death penalty.
- **PK System (`AC 32`)**: PK flag toggle (Red Name), PK points tracker, Imperial Guard arrest, and Jail map sentencing (`60001`).

---

## 22. Transformation & Monster Disguise Morphs ([`server/morph_system.py`](file:///d:/GitHub/Wonderland%20Online/server/morph_system.py))
- **Morph Pills (`AC 21:10`)**: Temporary visual transformations (Green Jelly, Wolf, Ghost, Siren) with combat attribute bonuses.

---

## 23. Barber, Hair Styling & Color Dyeing ([`server/barber_system.py`](file:///d:/GitHub/Wonderland%20Online/server/barber_system.py))
- **Hairstyling (`AC 21:1`)**: 16-bit RGB hair color palette, hairstyle options, and gold fee.
- **Clothing Dye (`AC 21:2`)**: Dyes garments and broadcasts appearance changes.

---

## 24. Bank Vault & Inventory Expansion ([`server/bank_system.py`](file:///d:/GitHub/Wonderland%20Online/server/bank_system.py))
- **Town Bank**: Safe deposit and withdrawal of gold in `char_bank_gold`.
- **Bag Expansion**: Expansion Bags (`38001`) adding +5 permanent inventory slots up to 50 max.

---

## 25. Pet Riding & Mount Speed Engine ([`server/pet_ride_system.py`](file:///d:/GitHub/Wonderland%20Online/server/pet_ride_system.py))
- **Pet Saddle (`38020`)**: Mounting rideable companions for +40% movement speed boosts across maps (`AC 82:1/2`).

---

## 26. Item Recycle & Smelting Furnace ([`server/recycle_system.py`](file:///d:/GitHub/Wonderland%20Online/server/recycle_system.py))
- **Smelting Furnace (`AC 64:10`)**: Dismantles obsolete weapons and armor into raw materials (Iron Ore, Copper Ore, Coal, Wood).

---

## 27. Death Penalty, Ghost State & Revive Altars ([`server/death_system.py`](file:///d:/GitHub/Wonderland%20Online/server/death_system.py))
- **Knockout Penalty**: -2% current level EXP loss on battle defeat, ghost visual aura (`AC 5:5: 60010`), and automatic teleportation to nearest sacred altar.

---

## 28. Character Deletion Security ([`server/handlers/handle_35_char_deletion.py`](file:///d:/GitHub/Wonderland%20Online/server/handlers/handle_35_char_deletion.py))
- **Delete Code Verification (`AC 35`)**: Validates 4-6 digit code generated during registration before purging character data.

---

## 29. Scheduled Server Events & Double EXP Engine ([`server/events_system.py`](file:///d:/GitHub/Wonderland%20Online/server/events_system.py))
- **Double EXP**: 2.0x combat experience multiplier, duration timers, and marquee broadcasts.

---

## 30. GM Command Suite & Console ([`server/gm_commands.py`](file:///d:/GitHub/Wonderland%20Online/server/gm_commands.py))
- **In-Game Admin Console**: `:item`, `:gold`, `:warp`, `:speed`, `:kick`, `:ban`, `:level`, `:spawn`, `:broadcast`, `:godmode`, `:heal`.
