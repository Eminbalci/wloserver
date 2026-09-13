import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.network import PacketReader, PacketWriter
from server.database import DatabaseManager
from server.gameserver import GameServer, PlayerSession
from server.handlers import handle_63_login, handle_2_chat


class TestPetAndSessionPersistence(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        import tempfile
        import os
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_wlo.db")
        self.db = DatabaseManager(self.db_path)
        self.server = GameServer(db_path=self.db_path)
        self.server.db = self.db

        # Create user and character
        with self.db.get_connection() as conn:
            conn.execute("INSERT INTO users (id, username, password) VALUES (1, 'testuser', 'pass123')")
            conn.execute("""
                INSERT INTO characters (id, user_id, slot, name, level, hp, max_hp, sp, max_sp, gold, pets, str, con, int, wis, agi, points)
                VALUES (10, 1, 1, 'HeroTest', 25, 450, 500, 180, 200, 5000, '[]', 30, 25, 10, 15, 20, 12)
            """)
            conn.commit()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _create_mock_session(self, char_id=10, name="HeroTest"):
        reader = MagicMock()
        writer = MagicMock()
        writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        writer.drain = AsyncMock()
        writer.write = MagicMock()
        session = PlayerSession(reader, writer)
        session.user_id = 1
        session.char_id = char_id
        session.char_name = name
        session.level = 25
        session.hp = 450
        session.max_hp = 500
        session.sp = 180
        session.max_sp = 200
        session.gold = 5000
        session.points = 12
        session._str_val = 30
        session._con_val = 25
        session._int_val = 10
        session._wis_val = 15
        session._agi_val = 20
        session.pets = [
            {
                "id": 12178,
                "pet_id": 12178,
                "name": "Robinson",
                "level": 15,
                "hp": 480,
                "max_hp": 520,
                "sp": 150,
                "max_sp": 180,
                "str": 22,
                "con": 18,
                "int": 10,
                "wis": 12,
                "agi": 14,
                "exp": 1200,
                "amity": 100,
                "in_battle": True
            }
        ]
        return session

    def test_player_session_stat_properties(self):
        """Validates property accessors and aliases for PlayerSession stats and points."""
        session = self._create_mock_session()
        
        # Test property setters
        session.str = 88
        session.con = 77
        session.int = 66
        session.wis = 55
        session.agi = 44
        session.stat_points = 250

        self.assertEqual(session._str_val, 88)
        self.assertEqual(session._con_val, 77)
        self.assertEqual(session._int_val, 66)
        self.assertEqual(session._wis_val, 55)
        self.assertEqual(session._agi_val, 44)
        self.assertEqual(session.points, 250)
        self.assertEqual(session.stat_points, 250)

    def test_pet_list_packet_188_bytes_per_pet(self):
        """Ensures build_pet_list_packet emits exact 188-byte records per companion."""
        session = self._create_mock_session()
        pkt = self.server.build_pet_list_packet(session)
        data = pkt.to_bytes()

        # Action code 15, sub 8
        self.assertEqual(data[0], 15)
        self.assertEqual(data[1], 8)

        # Body length = total len - 2 bytes header
        body_len = len(data) - 2
        pet_count = len(session.pets)
        self.assertEqual(body_len, pet_count * 188)

    def test_save_player_to_db_and_reload(self):
        """Verifies session attributes and pets persist cleanly to SQLite database."""
        session = self._create_mock_session()
        session.level = 30
        session.gold = 99999
        session.str = 95
        session.points = 100
        session.pets[0]["level"] = 20
        session.pets[0]["amity"] = 85

        self.server.save_player_to_db(session)

        # Reload directly from database
        char_row = self.server.db.get_character_by_id(10)
        self.assertIsNotNone(char_row)
        self.assertEqual(char_row["level"], 30)
        self.assertEqual(char_row["gold"], 99999)
        self.assertEqual(char_row["str"], 95)
        self.assertEqual(char_row["points"], 100)

        # Verify pets deserialization
        import json
        pets = json.loads(char_row["pets"]) if isinstance(char_row["pets"], str) else char_row["pets"]
        self.assertEqual(len(pets), 1)
        self.assertEqual(pets[0]["pet_id"], 12178)
        self.assertEqual(pets[0]["level"], 20)
        self.assertEqual(pets[0]["amity"], 85)

    def test_save_all_sessions(self):
        """Tests that server.save_all_sessions saves every active connection."""
        s1 = self._create_mock_session(char_id=10, name="HeroTest")
        s1.gold = 7777

        # Insert second character
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO characters (id, user_id, slot, name, level, hp, max_hp, sp, max_sp, gold, pets)
                VALUES (20, 1, 2, 'AltHero', 10, 100, 100, 100, 100, 50, '[]')
            """)
            conn.commit()

        s2 = self._create_mock_session(char_id=20, name="AltHero")
        s2.gold = 8888

        self.server.active_sessions.add(s1)
        self.server.active_sessions.add(s2)

        saved = self.server.save_all_sessions()
        self.assertEqual(saved, 2)

        char1 = self.server.db.get_character_by_id(10)
        char2 = self.server.db.get_character_by_id(20)
        self.assertEqual(char1["gold"], 7777)
        self.assertEqual(char2["gold"], 8888)

    async def test_gm_chat_commands_save_and_pet(self):
        """Tests :save and :pet add/del GM commands in chat handler."""
        session = self._create_mock_session()
        session.is_gm = True
        session.send_packet = AsyncMock()

        # Test :save (sub=2, read_string_n)
        reader_save = PacketReader(b"\x02:save")
        await handle_2_chat.handle(self.server, session, reader_save)
        
        # Test :pet add
        reader_add = PacketReader(b"\x02:pet add 12001 Monkey")
        await handle_2_chat.handle(self.server, session, reader_add)
        self.assertEqual(len(session.pets), 2)
        self.assertEqual(session.pets[1]["pet_id"], 12001)

        # Test :pet del
        reader_del = PacketReader(b"\x02:pet del 2")
        await handle_2_chat.handle(self.server, session, reader_del)
        self.assertEqual(len(session.pets), 1)

    async def test_cancel_char_creation_slot_lookup(self):
        """Tests that sub == 3 correctly queries characters table by user_id and slot."""
        session = self._create_mock_session()
        session.user_id = 1
        session.send_packet = AsyncMock()

        # sub = 3
        reader = PacketReader(b"\x03")
        await handle_63_login.handle(self.server, session, reader)

        # Verify packet sent
        session.send_packet.assert_called()
        calls = session.send_packet.call_args_list
        list_pkt = calls[0][0][0]
        data = list_pkt.to_bytes()
        self.assertEqual(data[0], 63)
        self.assertEqual(data[1], 1)

    def test_rotating_file_logger(self):
        """Validates that setup_logging writes output to persistent log file."""
        import tempfile
        import os
        import logging
        from logging.handlers import RotatingFileHandler
        from server.logger_config import setup_logging

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = setup_logging(log_dir=tmp_dir, log_filename="test_server.log")
            test_logger = logging.getLogger("TestLogger")
            test_logger.info("LOG_PERSISTENCE_VERIFIED_SUCCESS")

            # Flush and close handler so Windows allows tempdir cleanup
            for h in list(logging.getLogger().handlers):
                if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == log_path:
                    h.flush()
                    h.close()
                    logging.getLogger().removeHandler(h)

            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("LOG_PERSISTENCE_VERIFIED_SUCCESS", content)

    async def test_handle_32_emote_execution(self):
        """Validates that AC 32 Emote/Pose handlers execute without NameError/logging defect."""
        from server.handlers import handle_32_emote
        session = self._create_mock_session()

        # Sub 1: Emote
        reader1 = PacketReader(b"\x01\x05")
        await handle_32_emote.handle(self.server, session, reader1)
        self.assertEqual(session.emote, 5)

        # Sub 2: Pose / Sit
        reader2 = PacketReader(b"\x02\x0a")
        await handle_32_emote.handle(self.server, session, reader2)
        self.assertEqual(session.emote, 10)

        # Sub 3: Cancel Emote
        reader3 = PacketReader(b"\x03")
        await handle_32_emote.handle(self.server, session, reader3)
        self.assertEqual(session.emote, 0)

    def test_item_mall_points_persistence(self):
        """Validates that ItemMallManager correctly reads and writes points to SQLite without table errors."""
        from server.item_mall import ItemMallManager
        im_mgr = ItemMallManager()
        session = self._create_mock_session()

        # Test set and get user points
        im_mgr.set_user_points(session, 7500, db_path=self.db_path)
        points = im_mgr.get_user_points(session, db_path=self.db_path)
        self.assertEqual(points, 7500)

        # Test set and get bonus points
        im_mgr.set_user_bonus_points(session, 1500, db_path=self.db_path)
        bonus = im_mgr.get_user_bonus_points(session, db_path=self.db_path)
        self.assertEqual(bonus, 1500)

        # Test add points
        im_mgr.add_user_points(session, 500, db_path=self.db_path)
        self.assertEqual(session.im_points, 8000)
        im_mgr.add_user_bonus_points(session, 200, db_path=self.db_path)
        self.assertEqual(session.im_bonus_points, 1700)



if __name__ == "__main__":
    unittest.main()
