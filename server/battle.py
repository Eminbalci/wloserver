"""
Wonderland Online Battle Engine Compatibility Module
Re-exports the authentic advanced battle engine from server.battle_engine.
"""

from server.battle_engine import (
    BattleStatusType,
    AOETargetPattern,
    BattleUnit,
    PalaceStage,
    MonsterDropManager,
    PalaceTrialManager,
    PvPManager,
    AdvancedBattleManager,
    GLOBAL_BATTLE_ENGINE,
)

__all__ = [
    "BattleStatusType",
    "AOETargetPattern",
    "BattleUnit",
    "PalaceStage",
    "MonsterDropManager",
    "PalaceTrialManager",
    "PvPManager",
    "AdvancedBattleManager",
    "GLOBAL_BATTLE_ENGINE",
]
