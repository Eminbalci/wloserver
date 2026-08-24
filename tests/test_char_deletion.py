import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import tempfile

from server.network import PacketReader, PacketWriter
from server.database import DatabaseManager
from server.handlers.handle_35_char_deletion import handle as handle_ac35
from server.gameserver import PlayerSession


class TestCharDeletion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_char_del.db")
        self.db = DatabaseManager(self.db_file)
        self.db.init_db()

        # Register a test user
        user_id, _ = self.db.register_user("testuser", "password123")
        self.user_id = user_id

        # Set deletion cipher to "1234"
        self.db.update_cipher(self.user_id, "1234")

        # Create 2 characters
        self.char1_id = self.db.create_character(
            self.user_id, 1, "CharOne", 1, 0, 0, 0, 0, 0, 1, "1234"
        )
        self.char2_id = self.db.create_character(
            self.user_id, 2, "CharTwo", 2, 0, 0, 0, 0, 0, 2, "1234"
        )

        self.server = MagicMock()
        self.server.db = self.db

        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        self.session = PlayerSession(MagicMock(), mock_writer)
        self.session.user_id = self.user_id
        self.session.username = "testuser"
        self.session.cipher = "1234"
        self.session.send_packet = AsyncMock()

    def tearDown(self):
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except Exception:
                pass

    def test_delete_character_wrong_cipher(self):
        """Wrong cipher should return failure packet AC 35 Sub 2 [3, slot]."""
        # Build AC 35 Sub 2 request: [Sub: 2, Slot: 1, unkw: "", pw: "wrongpw"]
        pw = PacketWriter()
        pw.write_8(2).write_8(1).write_string("").write_string("wrongpw")
        reader = PacketReader(bytes(pw.buffer))

        loop = asyncio.new_event_loop()
        loop.run_until_complete(handle_ac35(self.server, self.session, reader))
        loop.close()

        # Verify failure packet was sent
        self.session.send_packet.assert_called()
        last_call_pkt = bytes(self.session.send_packet.call_args[0][0].buffer)
        self.assertEqual(last_call_pkt, bytes([35, 2, 3, 1]))

        # Verify character was NOT deleted
        self.assertIsNotNone(self.db.get_character_by_id(self.char1_id))

    def test_delete_character_correct_cipher(self):
        """Correct cipher should delete character and send success packet AC 35 Sub 2 [1, slot]."""
        pw = PacketWriter()
        pw.write_8(2).write_8(1).write_string("").write_string("1234")
        reader = PacketReader(bytes(pw.buffer))

        loop = asyncio.new_event_loop()
        loop.run_until_complete(handle_ac35(self.server, self.session, reader))
        loop.close()

        # Verify success packet was sent
        self.session.send_packet.assert_called()
        last_call_pkt = bytes(self.session.send_packet.call_args[0][0].buffer)
        self.assertEqual(last_call_pkt, bytes([35, 2, 1, 1]))

        # Verify character 1 was deleted
        self.assertIsNone(self.db.get_character_by_id(self.char1_id))
        # Verify character 2 still exists
        self.assertIsNotNone(self.db.get_character_by_id(self.char2_id))


if __name__ == "__main__":
    unittest.main()
