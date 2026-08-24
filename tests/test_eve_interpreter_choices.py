import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
from server.gameserver import GameServer, PlayerSession


class TestEveInterpreterChoices(unittest.TestCase):
    def setUp(self):
        self.server = MagicMock()
        self.server.map_npcs = {}
        self.server.send_dialogue = AsyncMock()
        self.server.warp_player = AsyncMock()
        self.server._send_quest_flag = AsyncMock()
        
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        self.session = PlayerSession(MagicMock(), mock_writer)
        self.session.char_name = "Hero"
        self.session.char_id = 1
        self.session.map_id = 12000
        self.session.x = 1080
        self.session.y = 1513
        self.session.quests = {}
        self.session.send_packet = AsyncMock()

    def test_map12000_event14_doll_question_flow(self):
        """Tests that Event 14 on Map 12000 (Doll) starts with multi-step dialogue and ends with choice prompt."""
        evs = GLOBAL_EVE_INTERPRETER.map_events.get(12000, {})
        self.assertIn(14, evs)
        ev14 = evs[14]
        
        # Test branch selection for fresh player
        sub = GLOBAL_EVE_INTERPRETER.select_matching_branch(self.session, ev14)
        self.assertIsNotNone(sub)
        self.assertEqual(sub["sub_idx"], 1)

        # Run execute_sub_opcodes
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(
            GLOBAL_EVE_INTERPRETER.execute_sub_opcodes(self.server, self.session, 12, ev14, sub)
        )
        self.assertTrue(res)
        
        # Verify dialogue queue was populated
        self.assertTrue(hasattr(self.session, "dialogue_queue"))
        self.assertGreater(len(self.session.dialogue_queue), 0)
        
        # Verify last step in queue is choice prompt (Question ID 1)
        last_step = self.session.dialogue_queue[-1]
        self.assertEqual(last_step["type"], "choice")
        self.assertEqual(last_step["question_id"], 1)

        # Test selecting Choice 1 (Option 1 -> branch 0 / choice 30)
        choice_res = loop.run_until_complete(
            GLOBAL_EVE_INTERPRETER.handle_choice_selection(self.server, self.session, 1)
        )
        self.assertTrue(choice_res)
        
        # Verify quest flag was updated
        self.assertEqual(self.session.quests.get("12018"), 1)
        loop.close()


if __name__ == "__main__":
    unittest.main()
