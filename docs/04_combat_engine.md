# Authentic Combat Engine & Battle Logic

This document describes the Wonderland Online turn-based combat engine, damage calculation formulas, elemental advantages, status effects, monster loot tables, and PvP mechanics.

## Combat Model Overview

Wonderland Online features a turn-based 8v8 tactical grid battle system:
- **Attacking Side**: Up to 4 players + 4 companion pets (Grid positions `[2..5, 0..3]`).
- **Defending Side**: Up to 8 enemy monsters or opponent players in PvP.
- **Turn Timer**: 20-second countdown for all participants to queue actions.

```
                  +--------------------------------+
                  |       Enemy Grid (0..7)        |
                  | [0] [1] [2] [3]   (Back Row)   |
                  | [4] [5] [6] [7]   (Front Row)  |
                  +--------------------------------+
                                  VS
                  +--------------------------------+
                  |       Player Grid (0..7)       |
                  | [0] [1] [2] [3]   (Front Row)  |
                  | [4] [5] [6] [7]   (Back Row)   |
                  +--------------------------------+
```

## Turn Execution Cycle

Each battle round proceeds through five deterministic phases:

1. **Turn Start (`AC 50:6` & `AC 52:1`)**:
   - Server synchronizes current HP/SP values to client via `AC 51:1`.
   - Client is granted control via `AC 52:1` (displays action ring: Attack, Skill, Item, Defend, Catch, Flee).
2. **Action Queueing & Immediate ACK (`AC 53:5`)**:
   - When participant selects target and action, client sends `AC 11:1` (attack), `AC 11:2` (skill), `AC 11:3` (item), or `AC 11:4` (capture).
   - Server immediately confirms action receipt with `AC 53:5 [x, y]` to unlock the client UI.
3. **Speed Priority Sorting**:
   - When all fighters have queued actions (or turn timeout expires), actions are sorted by Agility/Speed descending:
     $$\text{Priority} = \text{Actor.SPD}$$
4. **Animation Broadcasting (`AC 50:1`)**:
   - Server concatenates all combat skill animations, trajectories, and damage numbers into a single frame:
     - Header: `[50, 1]`
     - Actor sequence: `[0x11, 0x00, actor_x, actor_y, skill_id_16, 0, 1, target_x, target_y, 1, 0, 1, 0x19, damage_32, 1]`
5. **Round Resolution & State Sync (`AC 51:1`)**:
   - Targets' HP and SP are updated and synchronized.
   - Status effects decrement their remaining durations.
   - If all enemies or players are knocked out, battle finishes (`AC 11:0` & `AC 11:250`).

## Damage Formulas & Element Multipliers

### 1. Physical Damage Formula
Implemented in `GameServer.calculate_atk_damage()`:

$$\text{Base Damage} = \text{ATK} \times \left(\frac{\text{ATK}}{\max(1, \text{ATK} + \frac{\text{DEF}}{2})}\right)$$

If $\text{ATK} < 50$:
$$\text{Base Damage} = \text{Base Damage} + (\text{ATK} \times 0.5)$$

Final Damage:
$$\text{Damage} = \max(1, \text{round}(\text{Base Damage} \times \text{ElementCorrection} \times \text{RandomVariance}))$$

Where $\text{RandomVariance} \in [0.90, 1.10]$.

### 2. Elemental Advantage Matrix

Elemental relationships form a closed counter cycle:

$$\text{Fire (2)} \longrightarrow \text{Wind (3)} \longrightarrow \text{Earth (0)} \longrightarrow \text{Water (1)} \longrightarrow \text{Fire (2)}$$

| Attacker Element | Defender Element | Multiplier | Advantage State |
| :--- | :--- | :--- | :--- |
| Fire (2) | Wind (3) | **1.70x** | Dominant Advantage |
| Fire (2) | Water (1) | **0.60x** | Countered Disadvantage |
| Water (1) | Fire (2) | **1.70x** | Dominant Advantage |
| Water (1) | Earth (0) | **0.60x** | Countered Disadvantage |
| Earth (0) | Water (1) | **1.70x** | Dominant Advantage |
| Earth (0) | Wind (3) | **0.60x** | Countered Disadvantage |
| Wind (3) | Earth (0) | **1.70x** | Dominant Advantage |
| Wind (3) | Fire (2) | **0.40x** | Countered Disadvantage |
| None (4) | Any Element | **1.30x** | Neutral Bonus |
| Same Element | Same Element | **1.00x** | Neutral |

## Battle Status Ailments

Managed by `BattleStatusType` in `server/battle_engine.py`:

| Status Type | Value | Effect Description | Cure / Duration |
| :--- | :--- | :--- | :--- |
| **FREEZE** | 1 | Water seal. Cannot act; incoming damage reduced by 25%. | 2 - 3 Turns / Hit |
| **STONE** | 2 | Earth seal. Cannot act; DEF increased by 50%. | 2 - 4 Turns |
| **SLEEP** | 3 | Wind seal. Cannot act; wakes immediately upon receiving damage. | 2 - 3 Turns / Physical hit |
| **TREE** | 4 | Rooted in place. Cannot perform physical attacks or move. | 2 - 3 Turns |
| **SILENCE** | 5 | Magical seal. Cannot cast SP spells or special skills. | 3 Turns |
| **CONFUSION**| 6 | Attacks random targets (friend or foe alike). | 2 Turns |
| **POISON** | 7 | Suffers percentage HP loss at the start of each turn. | 3 - 5 Turns |
| **SHIELD** | 8 | Blocks up to $N$ points of incoming damage. | Until depleted / 3 turns |
| **REFLECT** | 9 | Reflects physical or magical damage back to the attacker. | 2 Turns |

## Special Combat Commands

- **Defend**: Target enters defensive stance. Incoming damage is reduced by 50%:
  $$\text{Damage}_{\text{defending}} = \max(1, \lfloor \text{Damage} / 2 \rfloor)$$
- **Flee (Skill 60041)**: Instant battlefield escape. Non-boss encounters succeed at 100%. Dispatches flee animation and exits encounter cleanly.
- **Pet Capture (Skill 10008)**: Captures enemy monster if eligible and below 50% HP. On success, writes pet record to player's companions list (`session.pets`).

## Monster Drop Engine (`MonsterDropManager`)

- Every monster template maintains an authentic drop table loaded from `server/data/drop_table.json` or fallback dynamic rules in SQLite.
- Party members receive instanced drop rolls upon combat victory.
- Overfilled inventory triggers ground item drop packet (`AC 23 Sub 2`).

## 12 Zodiac Palace Trials & PvP

- **Zodiac Trials (`PalaceTrialManager`)**: Sequential 12-stage boss trials awarding Zodiac Chests and exclusive seals.
- **1v1 PvP Duels**: Challenged via `AC 50 Sub 1`. Death in PK mode incurs PK point penalties; repeated offenses redirect the character to Imperial Jail.
