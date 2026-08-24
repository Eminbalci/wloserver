"""
Wonderland Online Advanced Battle Engine & Status Effects
Ported from C# wlo.pserver.core/Game/Battle (PvEBattleManager, Battle, MonsterDropManager, PalaceTrialManager, PvPManager)
"""

import math
import random
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class BattleStatusType(IntEnum):
    NONE = 0
    FREEZE = 1      # Water Sealing: cannot act, takes reduced damage
    STONE = 2       # Earth Sealing: cannot act, DEF increased
    SLEEP = 3       # Wind Sealing: cannot act, wakes on hit
    TREE = 4        # Earth/Wood Sealing: rooted, cannot physical attack
    SILENCE = 5     # Magic Sealing: cannot cast spells
    CONFUSION = 6   # Attacks random targets (friend or foe)
    POISON = 7      # Takes damage per turn
    SHIELD = 8      # Absorbs / blocks incoming damage
    REFLECT = 9     # Reflects physical or magic damage


class AOETargetPattern(IntEnum):
    SINGLE = 1
    LINE = 2        # 2 enemies in a vertical row
    CROSS = 3       # Cross pattern (up to 5 enemies)
    FRONT_ROW = 4   # 4 front-row enemies
    SQUARE_4 = 5    # 2x2 grid
    ALL_8 = 6       # All 8 grid positions


@dataclass
class BattleUnit:
    grid_pos: int                   # 0 to 7 (Player / Pet / Monster slot)
    unit_id: int                    # CharID, PetID, or Monster TID
    name: str
    is_player: bool
    is_pet: bool
    level: int
    element: int                    # 0=Earth, 1=Water, 2=Fire, 3=Wind
    cur_hp: int
    max_hp: int
    cur_sp: int
    max_sp: int
    atk: int
    def_val: int
    matk: int
    mdef: int
    spd: int
    statuses: Dict[BattleStatusType, int] = field(default_factory=dict)  # Status -> remaining turns
    session_ref: Optional[Any] = None

    @property
    def is_alive(self) -> bool:
        return self.cur_hp > 0

    @property
    def is_sealed(self) -> bool:
        return any(st in self.statuses for st in (BattleStatusType.FREEZE, BattleStatusType.STONE, BattleStatusType.SLEEP))


@dataclass
class PalaceStage:
    stage_number: int
    zodiac_name: str
    guardian_npc_id: int
    boss_hp: int
    boss_atk: int
    reward_chest_item_id: int


class MonsterDropManager:
    """Calculates and distributes monster loot among party members."""

    def __init__(self):
        # Default loot table for common monster drops
        self.default_drops: Dict[int, List[Tuple[int, float, int]]] = {
            # Monster TID -> List of (Item ID, Drop Rate 0.0-1.0, Max Count)
            1001: [(27001, 0.40, 2), (28014, 0.30, 1), (48030, 0.05, 1)],  # Iron Ore, Apple, Chest
            1002: [(27020, 0.35, 2), (28020, 0.25, 1), (48030, 0.05, 1)],  # Copper Ore, Meat
            1003: [(27022, 0.30, 2), (30013, 0.20, 1), (48030, 0.05, 1)],  # Tin Ore, Silk
            1004: [(27024, 0.30, 2), (30025, 0.25, 1), (48031, 0.05, 1)],  # Clay, Rice Ball
        }

    def calculate_drops(self, monster_tid: int) -> List[Tuple[int, int]]:
        drops = []
        loot_table = self.default_drops.get(monster_tid, [(27001, 0.25, 1), (28014, 0.20, 1)])
        for item_id, rate, max_cnt in loot_table:
            if random.random() <= rate:
                cnt = random.randint(1, max_cnt)
                drops.append((item_id, cnt))
        return drops


class PalaceTrialManager:
    """Manages the 12 Zodiac Palace Trials and rewards."""

    def __init__(self):
        self.palaces: List[PalaceStage] = [
            PalaceStage(1, "Aries Palace (Koç)", 1001, 15000, 450, 48030),
            PalaceStage(2, "Taurus Palace (Boğa)", 1002, 22000, 520, 48030),
            PalaceStage(3, "Gemini Palace (İkizler)", 1003, 30000, 600, 48030),
            PalaceStage(4, "Cancer Palace (Yengeç)", 1004, 38000, 680, 48031),
            PalaceStage(5, "Leo Palace (Aslan)", 1005, 48000, 780, 48031),
            PalaceStage(6, "Virgo Palace (Başak)", 1006, 58000, 850, 48031),
            PalaceStage(7, "Libra Palace (Terazi)", 1007, 70000, 950, 48032),
            PalaceStage(8, "Scorpio Palace (Akrep)", 1008, 85000, 1050, 48032),
            PalaceStage(9, "Sagittarius Palace (Yay)", 1009, 100000, 1200, 48032),
            PalaceStage(10, "Capricorn Palace (Oğlak)", 1010, 120000, 1350, 48033),
            PalaceStage(11, "Aquarius Palace (Kova)", 1011, 150000, 1500, 48033),
            PalaceStage(12, "Pisces Palace (Balık)", 1012, 200000, 1800, 48033),
        ]

    def get_stage(self, stage_num: int) -> Optional[PalaceStage]:
        for p in self.palaces:
            if p.stage_number == stage_num:
                return p
        return None

    async def enter_trial(self, server, session, stage_num: int) -> bool:
        stage = self.get_stage(stage_num)
        if not stage or not session:
            return False

        from server.gameserver import add_item_to_inventory
        # Grant Zodiac Trial Chest
        add_item_to_inventory(session, stage.reward_chest_item_id, 1)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[12 Palaces Trial] Cleared {stage.zodiac_name}! Received Zodiac Chest #{stage.reward_chest_item_id}!"
        )
        await session.send_packet(sys_msg)
        await session.send_packet(server.build_inventory_packet(session))
        logger.info(f"[PalaceTrial] Player {session.char_name} cleared {stage.zodiac_name} (Stage {stage_num}).")
        return True


class AdvancedBattleManager:
    """Manages full 8v8 turn-based combat, combos, status effects, and damage calculations."""

    def __init__(self):
        self.drop_manager = MonsterDropManager()
        self.palace_manager = PalaceTrialManager()

    def calculate_damage(
        self,
        attacker: BattleUnit,
        target: BattleUnit,
        skill_power: float = 1.0,
        is_magic: bool = False
    ) -> Tuple[int, bool, bool]:
        """
        Calculates damage, critical hit, and element advantage multiplier.
        Returns (damage, is_critical, has_element_advantage).
        """
        # Element Advantage Table: Fire > Wind > Earth > Water > Fire
        # 0=Earth, 1=Water, 2=Fire, 3=Wind
        element_mult = 1.0
        has_elem_adv = False

        if (attacker.element == 2 and target.element == 3) or \
           (attacker.element == 3 and target.element == 0) or \
           (attacker.element == 0 and target.element == 1) or \
           (attacker.element == 1 and target.element == 2):
            element_mult = 1.35
            has_elem_adv = True
        elif (attacker.element == 3 and target.element == 2) or \
             (attacker.element == 0 and target.element == 3) or \
             (attacker.element == 1 and target.element == 0) or \
             (attacker.element == 2 and target.element == 1):
            element_mult = 0.75

        # Base Attack and Defense
        if is_magic:
            raw_atk = attacker.matk
            raw_def = target.mdef
        else:
            raw_atk = attacker.atk
            raw_def = target.def_val

        base_dmg = max(1, (raw_atk * 1.8) - (raw_def * 0.9))
        dmg = base_dmg * skill_power * element_mult

        # Critical Hit check (5% default, higher with Killer job)
        is_crit = (random.random() < 0.08)
        if is_crit:
            dmg *= 1.5

        # Stone status defense boost
        if BattleStatusType.STONE in target.statuses:
            dmg *= 0.5

        final_dmg = max(1, int(round(dmg)))
        return final_dmg, is_crit, has_elem_adv

    def calculate_combo(self, units: List[BattleUnit]) -> Tuple[bool, float]:
        """
        Checks if multiple allied units can execute a simultaneous Combo Attack.
        Triggered when unit SPDs are within a close window (+/- 25 SPD).
        """
        if len(units) < 2:
            return False, 1.0

        spds = [u.spd for u in units if u.is_alive and not u.is_sealed]
        if len(spds) < 2:
            return False, 1.0

        spd_delta = max(spds) - min(spds)
        if spd_delta <= 25:
            combo_mult = 1.0 + (0.25 * (len(spds) - 1))
            return True, combo_mult

        return False, 1.0

    def apply_status_effect(
        self,
        target: BattleUnit,
        status: BattleStatusType,
        duration_turns: int = 3
    ) -> bool:
        """Applies a multi-turn status effect or seal to a battle unit."""
        if not target.is_alive:
            return False

        target.statuses[status] = duration_turns
        logger.info(f"[BattleEngine] Applied {status.name} to {target.name} for {duration_turns} turns.")
        return True

    def process_turn_statuses(self, unit: BattleUnit) -> List[str]:
        """Tick down statuses at turn start/end and apply recurring effects like Poison."""
        events = []
        if not unit.is_alive:
            return events

        for st in list(unit.statuses.keys()):
            # Apply poison tick
            if st == BattleStatusType.POISON:
                tick_dmg = max(10, int(unit.max_hp * 0.08))
                unit.cur_hp = max(0, unit.cur_hp - tick_dmg)
                events.append(f"{unit.name} suffered {tick_dmg} poison damage!")

            # Tick turn
            unit.statuses[st] -= 1
            if unit.statuses[st] <= 0:
                del unit.statuses[st]
                events.append(f"{unit.name} is no longer {st.name}!")

        return events

    def get_aoe_target_positions(
        self,
        primary_pos: int,
        pattern: AOETargetPattern
    ) -> List[int]:
        """Calculates all 8-grid positions affected by an AOE attack."""
        if pattern == AOETargetPattern.SINGLE:
            return [primary_pos]
        elif pattern == AOETargetPattern.LINE:
            # Col 0: (0, 4), Col 1: (1, 5), Col 2: (2, 6), Col 3: (3, 7)
            col = primary_pos % 4
            return [col, col + 4]
        elif pattern == AOETargetPattern.FRONT_ROW:
            return [0, 1, 2, 3]
        elif pattern == AOETargetPattern.SQUARE_4:
            base_col = min(2, primary_pos % 4)
        elif pattern == AOETargetPattern.ALL_8:
            return list(range(8))
        return [primary_pos]


class MonsterDropManager:
    """Calculates battle monster item drops dynamically from database or static cache."""

    def __init__(self):
        self._cached_drops: Dict[int, List[Dict[str, Any]]] = {}

    def get_drops_for_monster(self, monster_id: int) -> List[Tuple[int, str, int]]:
        """Returns list of (item_id, item_name, count) dropped by monster."""
        from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
        if monster_id not in self._cached_drops:
            self._cached_drops[monster_id] = GLOBAL_DYNAMIC_DATA.get_monster_drops(monster_id)

        entries = self._cached_drops.get(monster_id, [])
        dropped_items = []

        for e in entries:
            rate = e.get("drop_rate", 1000)  # 1-10000
            roll = random.randint(1, 10000)
            if roll <= rate:
                min_c = e.get("min_count", 1)
                max_c = e.get("max_count", 1)
                count = random.randint(min_c, max_c)
                dropped_items.append((e["item_id"], e["item_name"], count))

        return dropped_items

    def reload_drops(self, dynamic_mgr=None):
        self._cached_drops.clear()
        logger.info("[MonsterDropManager] Reloaded dynamic monster drops cache.")


class PalaceTrialManager:
    """Manages 12 Zodiac Palace Trial waves and rewards."""

    ZODIAC_STAGES = [
        (1, "Aries Palace", 201, 10000, 5000),
        (2, "Taurus Palace", 202, 15000, 7500),
        (3, "Gemini Palace", 203, 20000, 10000),
        (4, "Cancer Palace", 204, 25000, 12500),
        (5, "Leo Palace", 205, 30000, 15000),
        (6, "Virgo Palace", 206, 35000, 17500),
        (7, "Libra Palace", 207, 40000, 20000),
        (8, "Scorpio Palace", 208, 45000, 22500),
        (9, "Sagittarius Palace", 209, 50000, 25000),
        (10, "Capricorn Palace", 210, 55000, 27500),
        (11, "Aquarius Palace", 211, 60000, 30000),
        (12, "Pisces Palace", 212, 100000, 50000),
    ]


# Global singleton instance
GLOBAL_BATTLE_ENGINE = AdvancedBattleManager()
GLOBAL_BATTLE_ENGINE.drop_manager = MonsterDropManager()
GLOBAL_DROP_MANAGER = GLOBAL_BATTLE_ENGINE.drop_manager
GLOBAL_PALACE_TRIAL = PalaceTrialManager()
