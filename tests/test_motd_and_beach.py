import unittest
import asyncio
from server.network import PacketReader, PacketWriter, xor_crypt
from server.gameserver import GameServer
from server.handlers import handle_89_action, handle_92_action, handle_12_warp, handle_20_interaction


class MockSession:
    def __init__(self, char_id=1, char_name="Hero", map_id=10035):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = map_id
        self.x = 1038
        self.y = 2235
        self.emote = 0
        self.is_warping = False
        self.in_map = True
        self.motd_sent = False
        self.beach_cutscene_active = False
        self.pending_beach_cutscene = False
        self.dialogue_queue = []
        self.quests = []
        self.sent_packets = []

    async def send_packet(self, pkt):
        if hasattr(pkt, 'buffer'):
            self.sent_packets.append(pkt.buffer)
        else:
            self.sent_packets.append(pkt)


class TestMotdAndBeachCutscene(unittest.TestCase):
    def setUp(self):
        self.server = GameServer(db_path=":memory:", static_db_path="server/ServerDataBase.db")

    def test_motd_crud_and_dispatch(self):
        """Verifies MOTD can be read, updated, persisted, and dispatched."""
        # 1. Default MOTD
        default_motd = self.server.get_motd()
        self.assertIn("Wonderland", default_motd)

        # 2. Update MOTD
        custom_motd = "Line 1: Server Event Today!\nLine 2: 2x EXP Active!"
        self.server.set_motd(custom_motd)
        self.assertEqual(self.server.get_motd(), custom_motd)

        # 3. Dispatch to session
        session = MockSession()
        asyncio.run(self.server.dispatch_login_motd(session))
        self.assertGreaterEqual(len(session.sent_packets), 3) # 1 popup + 2 chat lines

        # First packet is popup AC 23:57
        p1 = session.sent_packets[0]
        self.assertEqual(p1[0], 23)
        self.assertEqual(p1[1], 57)

        # Second packet is chat AC 2 with chatType 4 (GM)
        p2 = session.sent_packets[1]
        self.assertEqual(p2[0], 2)
        self.assertEqual(p2[1], 4)

    def test_handle_89_scene_readiness(self):
        """Verifies AC 89 Sub 0 returns AC 90:1 and dispatches MOTD."""
        session = MockSession()
        reader = PacketReader(bytes([0]))
        asyncio.run(handle_89_action.handle(self.server, session, reader))
        self.assertTrue(session.motd_sent)
        self.assertGreater(len(session.sent_packets), 0)
        p1 = session.sent_packets[0]
        self.assertEqual(p1[0], 90)
        self.assertEqual(p1[1], 1)

    def test_handle_92_finalization(self):
        """Verifies AC 92 Sub 1 triggers MOTD dispatch."""
        session = MockSession()
        reader = PacketReader(bytes([1]))
        asyncio.run(handle_92_action.handle(self.server, session, reader))
        self.assertTrue(session.motd_sent)

    def test_beach_cutscene_progression(self):
        """Verifies AC 20:6 advances beach cutscene stages rather than prematurely unlocking controls."""
        session = MockSession(map_id=10035)
        session.beach_cutscene_active = True
        session.beach_cutscene_stage = 1
        reader = PacketReader(bytes([6]))
        asyncio.run(handle_20_interaction.handle(self.server, session, reader))
        # Dispatches Robinson approach (AC 22:12) + sync tick (AC 20:10)
        self.assertEqual(session.beach_cutscene_stage, 2)
        self.assertEqual(len(session.sent_packets), 2)
        self.assertEqual(session.sent_packets[0][0], 22)
        self.assertEqual(session.sent_packets[0][1], 12)
        self.assertEqual(session.sent_packets[1][0], 20)
        self.assertEqual(session.sent_packets[1][1], 10)
        # Verify no premature unlock packets were sent
        has_unlock = any(p[0] == 5 and p[1] == 4 for p in session.sent_packets)
        self.assertFalse(has_unlock)


if __name__ == "__main__":
    unittest.main()
