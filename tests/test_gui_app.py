"""
Unit tests for ModernServerGUI and CharacterDataEditorDialog.
Verifies all tabs, controls, metric cards, and data loaders initialize without error.
"""

import unittest
from unittest.mock import MagicMock
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

        # Verify all 13 tabs exist
        self.assertIsNotNone(app.tab_dash)
        self.assertIsNotNone(app.tab_cheats)
        self.assertIsNotNone(app.tab_players)
        self.assertIsNotNone(app.tab_users)
        self.assertIsNotNone(app.tab_chars)
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


if __name__ == "__main__":
    unittest.main()
