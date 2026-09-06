"""
Unit tests for ModernServerGUI and CharacterDataEditorDialog.
Verifies all tabs, controls, metric cards, and data loaders initialize without error.
"""

import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from server.gui_app import ModernServerGUI, CharacterDataEditorDialog


class TestServerGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Headless mode

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_gui_app_initialization(self):
        server = MagicMock()
        server.sessions = {}
        app = ModernServerGUI(self.root, server, db_path="wlo_server.db")

        # Verify all tabs exist
        self.assertIsNotNone(app.tab_dash)
        self.assertIsNotNone(app.tab_cheats)
        self.assertIsNotNone(app.tab_players)
        self.assertIsNotNone(app.tab_users)
        self.assertIsNotNone(app.tab_chars)
        self.assertIsNotNone(app.tab_guilds)
        self.assertIsNotNone(app.tab_mail)
        self.assertIsNotNone(app.tab_security)
        self.assertIsNotNone(app.tab_battles)
        self.assertIsNotNone(app.tab_marriage)
        self.assertIsNotNone(app.tab_portals)
        self.assertIsNotNone(app.tab_maps)
        self.assertIsNotNone(app.tab_drops)
        self.assertIsNotNone(app.tab_chests)
        self.assertIsNotNone(app.tab_mall)
        self.assertIsNotNone(app.tab_npc_res)
        self.assertIsNotNone(app.tab_talk)
        self.assertIsNotNone(app.tab_settings)

    def test_character_data_editor_dialog(self):
        server = MagicMock()
        server.sessions = {}
        dlg = CharacterDataEditorDialog(self.root, 1, "Player", db_path="wlo_server.db", game_server=server)

        # Verify sub-tabs
        self.assertIsNotNone(dlg.t_stats)
        self.assertIsNotNone(dlg.t_quests)
        self.assertIsNotNone(dlg.t_pets)
        self.assertIsNotNone(dlg.t_inv)
        self.assertIsNotNone(dlg.t_skills)
        self.assertIsNotNone(dlg.t_vis)
        dlg.destroy()

    @patch("tkinter.messagebox.showinfo")
    @patch("tkinter.messagebox.showwarning")
    @patch("tkinter.messagebox.showerror")
    @patch("tkinter.messagebox.askyesno")
    def test_admin_suite_new_tabs_and_actions(self, mock_ask, mock_err, mock_warn, mock_info):
        server = MagicMock()
        mock_session = MagicMock()
        mock_session.char_id = 1001
        mock_session.char_name = "TestPlayer"
        mock_session.username = "testuser"
        mock_session.level = 50
        mock_session.gold = 50000
        mock_session.map_id = 10001
        mock_session.x = 250
        mock_session.y = 350
        mock_session.ip = "192.168.1.100"
        mock_session.max_hp = 1000
        mock_session.max_sp = 500
        mock_session.hp = 200
        mock_session.sp = 50
        mock_session.stat_points = 10
        mock_session.str = 20
        mock_session.con = 20
        mock_session.int = 10
        mock_session.wis = 10
        mock_session.agi = 10
        mock_session.pets = []
        mock_session.god_mode = False
        server.sessions = {1001: mock_session}
        server.active_battles = {
            999: {
                "id": 999, "type": "pve", "map_id": 10001, "turn": 2, "start_time": 0,
                "player": {"char_name": "TestPlayer", "hp": 500, "max_hp": 1000, "sp": 100, "max_sp": 500, "session": mock_session},
                "monsters": [{"id": 17001, "name": "Jellyfish", "hp": 50, "max_hp": 100, "x": 1, "y": 1}]
            }
        }

        app = ModernServerGUI(self.root, server, db_path="wlo_server.db")

        # Test refresh actions across new tabs
        app.action_refresh_guilds()
        app.action_refresh_mail()
        app.action_refresh_banned_ips()
        app.action_refresh_banned_accounts()
        app.action_refresh_battles()
        app.action_refresh_marriages()
        app.action_refresh_characters()

        # Test battles selection
        self.assertEqual(len(app.tree_battles.get_children()), 1)
        b_item = app.tree_battles.get_children()[0]
        app.tree_battles.selection_set(b_item)
        app._on_battle_selected(None)
        details_txt = app.txt_battle_details.get("1.0", tk.END)
        self.assertIn("Jellyfish", details_txt)

        # Test player action targeting
        app.tree_players.selection_set(app.tree_players.get_children()[0])
        app.action_heal_player()
        self.assertEqual(mock_session.hp, 1000)
        self.assertEqual(mock_session.sp, 500)

        app.action_god_mode()
        self.assertTrue(getattr(mock_session, "god_mode", False))
        self.assertEqual(mock_session.hp, 99999)


if __name__ == "__main__":
    unittest.main()
