import sqlite3

class QuestManager:
    def __init__(self, db_path="server/ServerDataBase.db"):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_quest_battle(self, npc_template_id: int):
        """
        Returns battle details for an NPC if they trigger a quest battle.
        Returns a dict: {'battle_sprite_id', 'bg_id', 'win_map_id', 'win_x', 'win_y'}
        or None if no battle is associated.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM quest_battles WHERE npc_template_id = ?", 
                (npc_template_id,)
            ).fetchone()
            
            if row:
                return dict(row)
        return None
