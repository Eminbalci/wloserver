import unittest
import asyncio
import os
import sqlite3
from server.database import DatabaseManager as Database
from server.gameserver import GameServer, PlayerSession
from server.handlers.handle_63_login import handle as handle_63_login
from server.network import PacketReader, xor_crypt

class MockWriter:
    def __init__(self):
        self.closed = False
        self.packets = []

    def write(self, data):
        self.packets.append(data)

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass

    def get_extra_info(self, key):
        if key == 'peername':
            return ('198.51.100.45', 54321)
        return None

import uuid

class TestUserAndIPBanSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_db_path = f"test_ban_{uuid.uuid4().hex}.db"
        self.db = Database(self.test_db_path)
        self.server = GameServer()
        self.server.db = self.db
        self.server.version_validator = None

        # Seed test accounts
        with self.db.get_connection() as conn:
            cur1 = conn.execute("INSERT INTO users (username, password) VALUES ('alice', 'pass123')")
            self.u1_id = cur1.lastrowid
            cur2 = conn.execute("INSERT INTO users (username, password) VALUES ('bob', 'pass456')")
            self.u2_id = cur2.lastrowid
            cur3 = conn.execute("INSERT INTO users (username, password) VALUES ('charlie', 'pass789')")
            self.u3_id = cur3.lastrowid
            conn.commit()

        # Create test characters
        with self.db.get_connection() as conn:
            conn.execute("INSERT INTO characters (id, user_id, name, level, slot) VALUES (101, ?, 'SuperAlice', 50, 1)", (self.u1_id,))
            conn.execute("INSERT INTO characters (id, user_id, name, level, slot) VALUES (102, ?, 'BobTheSlayer', 35, 1)", (self.u2_id,))
            conn.execute("INSERT INTO characters (id, user_id, name, level, slot) VALUES (103, ?, 'ShadowNinja', 80, 1)", (self.u3_id,))
            conn.commit()

    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
        except Exception:
            pass

    def test_user_ban_and_unban(self):
        # Initial check
        self.assertFalse(self.db.is_user_banned(self.u1_id))

        # Ban user
        self.db.ban_user(self.u1_id, "Cheating with speedhack", banned=1)
        self.assertTrue(self.db.is_user_banned(self.u1_id))

        with self.db.get_connection() as conn:
            row = conn.execute("SELECT ban_reason FROM users WHERE id = ?", (self.u1_id,)).fetchone()
            self.assertEqual(row["ban_reason"], "Cheating with speedhack")

        # Unban user
        self.db.ban_user(self.u1_id, "", banned=0)
        self.assertFalse(self.db.is_user_banned(self.u1_id))

    def test_ip_ban_and_unban(self):
        bad_ip = "203.0.113.195"
        self.assertFalse(self.db.is_ip_banned(bad_ip))

        # Ban IP
        self.db.ban_ip(bad_ip, "DDoS flood attempt", "admin")
        self.assertTrue(self.db.is_ip_banned(bad_ip))

        # Loopback safety check
        self.assertFalse(self.db.is_ip_banned("127.0.0.1"))
        self.assertFalse(self.db.is_ip_banned("localhost"))

        # List banned IPs
        banned_list = self.db.get_banned_ips()
        self.assertEqual(len(banned_list), 1)
        self.assertEqual(banned_list[0]["ip"], bad_ip)
        self.assertEqual(banned_list[0]["reason"], "DDoS flood attempt")

        # Unban IP
        self.db.unban_ip(bad_ip)
        self.assertFalse(self.db.is_ip_banned(bad_ip))
        self.assertEqual(len(self.db.get_banned_ips()), 0)

    def test_last_ip_and_login_tracking(self):
        player_ip = "198.51.100.77"
        self.db.update_user_last_login(self.u2_id, player_ip)

        with self.db.get_connection() as conn:
            row = conn.execute("SELECT last_ip, last_login FROM users WHERE id = ?", (self.u2_id,)).fetchone()
            self.assertEqual(row["last_ip"], player_ip)
            self.assertIsNotNone(row["last_login"])

    def test_search_accounts_by_multiple_fields(self):
        self.db.update_user_last_login(self.u1_id, "192.168.1.55")
        self.db.update_user_last_login(self.u2_id, "10.0.0.99")
        self.db.update_user_last_login(self.u3_id, "172.16.5.20")
        self.db.ban_ip("172.16.5.20", "Bot net")

        # 1. Search by IP
        res_ip = self.db.search_accounts("192.168.1.55")
        self.assertEqual(len(res_ip), 1)
        self.assertEqual(res_ip[0]["username"], "alice")

        # 2. Search by Character Name
        res_char = self.db.search_accounts("BobTheSlayer")
        self.assertEqual(len(res_char), 1)
        self.assertEqual(res_char[0]["username"], "bob")

        # 3. Search by Username
        res_user = self.db.search_accounts("charlie")
        self.assertEqual(len(res_user), 1)
        self.assertEqual(res_user[0]["id"], self.u3_id)
        self.assertTrue(res_user[0]["is_ip_banned"])

        # 4. Search by User ID
        res_id = self.db.search_accounts(str(self.u1_id))
        self.assertTrue(any(u["id"] == self.u1_id for u in res_id))

        # 5. Search by Character ID
        res_cid = self.db.search_accounts("103")
        self.assertTrue(any(u["id"] == self.u3_id for u in res_cid))

    async def test_login_rejection_for_banned_ip(self):
        writer = MockWriter()
        session = PlayerSession(None, writer)
        session.ip = "203.0.113.88"
        self.db.ban_ip(session.ip, "Malicious")

        # Construct login packet payload: sub=4, version=0 (2B), len=5 "alice", len=7 "pass123"
        payload = bytearray([4, 0, 0, 5]) + b"alice" + bytearray([7]) + b"pass123"
        reader = PacketReader(payload)
        await handle_63_login(self.server, session, reader)

        # Should be rejected with AC 63 Sub 4
        self.assertTrue(len(writer.packets) > 0)
        decrypted_payload = xor_crypt(writer.packets[0][4:])
        self.assertEqual(decrypted_payload[0], 63)
        self.assertEqual(decrypted_payload[1], 4)

    async def test_login_rejection_for_banned_user(self):
        writer = MockWriter()
        session = PlayerSession(None, writer)
        session.ip = "192.168.1.80"
        self.db.ban_user(self.u1_id, "Cheating", banned=1)

        payload = bytearray([4, 0, 0, 5]) + b"alice" + bytearray([7]) + b"pass123"
        reader = PacketReader(payload)
        await handle_63_login(self.server, session, reader)

        self.assertTrue(len(writer.packets) > 0)
        decrypted_payload = xor_crypt(writer.packets[0][4:])
        self.assertEqual(decrypted_payload[0], 63)
        self.assertEqual(decrypted_payload[1], 4)

    async def test_live_kick_and_ban(self):
        writer = MockWriter()
        session = PlayerSession(None, writer)
        session.ip = "198.51.100.99"
        session.user_id = self.u2_id
        session.username = "bob"
        session.char_name = "BobTheSlayer"
        self.server.active_sessions.add(session)

        # Ban user live
        await self.server.ban_user(self.u2_id, "Inappropriate conduct")
        is_banned = self.db.is_user_banned(self.u2_id)
        self.assertTrue(is_banned)
        self.assertTrue(writer.closed)

if __name__ == "__main__":
    unittest.main()
