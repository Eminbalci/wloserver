"""
Wonderland Online Quest Manager Bridge
Integrates Master Quest Engine, Mark.dat definitions, and ServerDataBase quest battles.
"""

import sqlite3
import logging
from typing import Optional, Dict, Any

from server.quests import GLOBAL_QUEST_ENGINE, QuestEngine
from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER

logger = logging.getLogger("WLO_Server")


class QuestManager:
    def __init__(self, db_path: str = "server/ServerDataBase.db"):
        self.db_path = db_path
        self.engine: QuestEngine = GLOBAL_QUEST_ENGINE

    def initialize(self, base_dir: Optional[str] = None):
        """Initializes the underlying QuestEngine with Mark.dat and PreEvents."""
        self.engine.initialize(base_dir)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_quest_battle(self, npc_template_id: int) -> Optional[Dict[str, Any]]:
        """
        Returns battle details for an NPC if they trigger a quest battle from ServerDataBase.db.
        Returns dict: {'battle_sprite_id', 'bg_id', 'win_map_id', 'win_x', 'win_y'}
        or None if no battle is associated.
        """
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM quest_battles WHERE npc_template_id = ?", 
                    (npc_template_id,)
                ).fetchone()
                
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"[QuestManager] quest_battles lookup notice: {e}")
        return None
