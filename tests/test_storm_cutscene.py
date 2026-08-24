import asyncio
import unittest
from typing import Any, Dict, List

from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER, get_session_quest_state, set_session_quest_state
from server.handlers import handle_12_warp as handle_12
from server.handlers import handle_20_interaction as handle_20
from server.handlers import handle_186_cutscene as handle_186
from server.network import PacketReader, PacketWriter


class MockSession:
    def __init__(self):
        self.char_name = "SailorHero"
        self.username = "sailor"
        self.char_id = 1001
        self.map_id = 10017
        self.x = 200
        self.y = 300
        self.emote = 0
        self.quests = []
        self.pets = []
        self.gold = 0
        self.exp = 0
        self.equipments = []
        self.inventory = {}
        self.dialogue_queue = []
        self.pending_dialogue_choice = None
        self.active_quest_id = None
        self.active_quest_step = 0
        self.is_warping = False
        self.in_map = True
        self.last_warp_time = 0
        self.sent_packets = []

    async def send_packet(self, packet_writer: PacketWriter):
        self.sent_packets.append(bytes(packet_writer.buffer))


class MockServer:
    def __init__(self):
        self.sessions = {}
        self.items = {}
        self.quest_scripts = {}
        self.map_npcs = {
            10017: [{"click_id": 10, "npc_id": 14003, "name": "Captain", "events": [11]}]
        }

    def broadcast_to_map(self, map_id: int, packet_writer: PacketWriter, exclude_session=None):
        pass

    def build_remote_char_spawn(self, session):
        return PacketWriter().write_8(3).write_8(24)

    async def send_dialogue(self, session, click_id, talk_id, step=1, portrait_type=3):
        pkt = (
            PacketWriter()
            .write_8(20)
            .write_8(1)
            .write_8(0).write_8(0).write_8(0)
            .write_8(step)
            .write_8(1)
            .write_8(portrait_type)
            .write_16(click_id)
            .write_8(1)
            .write_32(0)
            .write_16(talk_id)
            .write_8(1)
        )
        await session.send_packet(pkt)

    async def warp_player(self, session, map_id, x, y, portal_id=0):
        session.map_id = map_id
        session.x = x
        session.y = y

    def save_player_to_db(self, session):
        pass


class TestStormAndBeachCutscene(unittest.IsolatedAsyncioTestCase):
    async def test_full_storm_and_beach_cutscene_pipeline(self):
        server = MockServer()
        session = MockSession()

        # Step 1: Player clicks Captain (NPC 10) on starter ship deck Map 10017
        executed = await GLOBAL_EVE_INTERPRETER.try_execute(server, session, 10)
        self.assertTrue(executed)

        # First step is dispatched: Dialogue Step 1 (TalkID 30124)
        self.assertEqual(len(session.sent_packets), 2)  # AC 20:1 + text AC 23:57
        self.assertEqual(session.sent_packets[0][0], 20)
        self.assertEqual(session.sent_packets[0][1], 1)

        # Verify dialogue queue contains Step 2 and Step 3 (Storm Cutscene)
        self.assertEqual(len(session.dialogue_queue), 2)
        self.assertEqual(session.dialogue_queue[0]["talk_id"], 30125)
        self.assertEqual(session.dialogue_queue[1]["type"], "storm_cutscene")

        # Step 2: Client advances dialogue (AC 20 Sub 6) -> Step 2 Dialogue (TalkID 30125)
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        self.assertEqual(len(session.sent_packets), 2)  # AC 20:1 + AC 23:57
        self.assertEqual(len(session.dialogue_queue), 1)
        self.assertEqual(session.dialogue_queue[0]["type"], "storm_cutscene")

        # Step 3: Client advances dialogue (AC 20 Sub 6) -> Dispatches Storm Movie (AC 186:12 & AC 20:1 Step 3 + SFX)
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        self.assertTrue(getattr(session, "playing_storm_cutscene", False))
        self.assertEqual(session.sent_packets[0][0], 186)
        self.assertEqual(session.sent_packets[0][1], 12)
        self.assertEqual(session.sent_packets[1][0], 20)
        self.assertEqual(session.sent_packets[1][1], 1)

        # Step 4: Client acknowledges cutscene readiness (AC 186 Sub 9) -> Server replies with Playback ACK
        session.sent_packets.clear()
        reader_186_9 = PacketReader(b"\x09\x01\x00")
        await handle_186.handle(server, session, reader_186_9)
        self.assertTrue(getattr(session, "cutscene_ready", False))
        self.assertEqual(len(session.sent_packets), 1)
        self.assertEqual(session.sent_packets[0][0], 186)
        self.assertEqual(session.sent_packets[0][1], 9)

        # Step 5: Cutscene movie finishes on client -> Client sends AC 20 Sub 6
        session.storm_cutscene_start_time = 0  # Simulate cutscene duration elapsed
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        # Should send AC 20:7 Warp Out, and teleport to Beach (Map 10035 pos 1038, 2235)
        self.assertFalse(getattr(session, "playing_storm_cutscene", False))
        self.assertTrue(getattr(session, "pending_beach_cutscene", False))
        self.assertTrue(getattr(session, "pending_beach_cutscene", False))
        self.assertEqual(session.sent_packets[0][0], 20)
        self.assertEqual(session.sent_packets[0][1], 7)  # AC 20:7
        self.assertEqual(session.map_id, 10035)
        self.assertEqual(session.x, 1038)
        self.assertEqual(session.y, 2235)

        # Step 6: Player arrives on Beach Map 10035 -> Client sends AC 12 Sub 1
        session.sent_packets.clear()
        reader_12_1 = PacketReader(b"\x01")
        await handle_12.handle(server, session, reader_12_1)

        # Should initialize Beach Cutscene: Pose 9 + AC 5:30 (immobilize) + beach_cutscene_active
        self.assertEqual(session.emote, 9)
        self.assertTrue(getattr(session, "beach_cutscene_active", False))
        has_emote_9 = any(p[0] == 32 and p[1] == 2 and p[-1] == 9 for p in session.sent_packets)
        self.assertTrue(has_emote_9)
        has_immob = any(p[0] == 5 and p[1] == 30 for p in session.sent_packets)
        self.assertTrue(has_immob)

        # Step 7: While timeline is active, client AC 20:6 is absorbed
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(len(session.sent_packets), 0)

        # Step 8: When timeline finishes and dialogue ends -> Robinson standing + Player standing + Quest 12040 marked
        session.beach_cutscene_active = False
        session.dialogue_queue = []
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))

        self.assertFalse(getattr(session, "beach_cutscene_active", False))
        self.assertEqual(session.emote, 0)
        self.assertEqual(get_session_quest_state(session, 12040), 1)
        has_robinson_stand = any(p[0] == 22 and p[1] == 12 for p in session.sent_packets)
        self.assertTrue(has_robinson_stand)
        has_unlock_ui = any(p[0] == 20 and p[1] == 8 for p in session.sent_packets)
        self.assertTrue(has_unlock_ui)
        has_unlock_ctrl = any(p[0] == 5 and p[1] == 4 for p in session.sent_packets)
        self.assertTrue(has_unlock_ctrl)


if __name__ == "__main__":
    unittest.main()
