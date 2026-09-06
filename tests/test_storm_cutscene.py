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

        # First step is dispatched: Dialogue Step 1 (TalkID 30124) + Captain intro packets (AC 6:2 lock facing, AC 183:11 gesture, AC 35:12 SFX)
        self.assertEqual(len(session.sent_packets), 5)
        self.assertEqual(session.sent_packets[0][0], 20)
        self.assertEqual(session.sent_packets[0][1], 1)
        self.assertEqual(session.sent_packets[2][0], 6)
        self.assertEqual(session.sent_packets[2][1], 2)
        self.assertEqual(session.sent_packets[3][0], 183)
        self.assertEqual(session.sent_packets[3][1], 11)
        self.assertEqual(session.sent_packets[4][0], 35)
        self.assertEqual(session.sent_packets[4][1], 12)

        # Verify dialogue queue contains Step 2 and Step 3 (Storm Cutscene)
        self.assertEqual(len(session.dialogue_queue), 2)
        self.assertEqual(session.dialogue_queue[0]["talk_id"], 30125)
        self.assertEqual(session.dialogue_queue[1]["type"], "storm_cutscene")

        # Step 2: Client advances dialogue (AC 20 Sub 6) -> Step 2 Dialogue (TalkID 30125) + Talia spawn (AC 3:123, AC 5:0) + Pre-arm Movie 1 (AC 186:12)
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        self.assertEqual(len(session.sent_packets), 5)  # AC 20:1 + AC 23:57 + AC 3:123 + AC 5:0 + AC 186:12
        self.assertEqual(session.sent_packets[0][0], 20)
        self.assertEqual(session.sent_packets[0][1], 1)
        self.assertEqual(session.sent_packets[2][0], 3)
        self.assertEqual(session.sent_packets[2][1], 123)
        self.assertEqual(session.sent_packets[3][0], 5)
        self.assertEqual(session.sent_packets[3][1], 0)
        self.assertEqual(session.sent_packets[4][0], 186)
        self.assertEqual(session.sent_packets[4][1], 12)
        self.assertEqual(len(session.dialogue_queue), 1)
        self.assertEqual(session.dialogue_queue[0]["type"], "storm_cutscene")

        # Step 3: Client advances dialogue (AC 20 Sub 6) -> Dispatches Storm Cutscene Video & Thunder Sequence
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        self.assertTrue(getattr(session, "playing_storm_cutscene", False))
        # Packets: AC 10:6 shock, AC 35:12 scream, AC 186:9 play movie, AC 20:1 18-byte thunder event, AC 5:8 faint, AC 35:12 thunder, AC 35:12 creak
        self.assertEqual(len(session.sent_packets), 7)
        self.assertEqual(session.sent_packets[0][0], 10)
        self.assertEqual(session.sent_packets[0][1], 6)
        self.assertEqual(session.sent_packets[2][0], 186)
        self.assertEqual(session.sent_packets[2][1], 9)
        self.assertEqual(session.sent_packets[3][0], 20)
        self.assertEqual(session.sent_packets[3][1], 1)
        self.assertEqual(len(session.sent_packets[3]), 18)  # Exact authentic 18-byte packet

        # Step 4: Client acknowledges cutscene readiness (AC 186 Sub 9) -> Server replies with Playback ACK
        session.sent_packets.clear()
        reader_186_9 = PacketReader(b"\x09\x01\x00")
        await handle_186.handle(server, session, reader_186_9)
        self.assertTrue(getattr(session, "cutscene_ready", False))
        self.assertEqual(len(session.sent_packets), 1)
        self.assertEqual(session.sent_packets[0][0], 186)
        self.assertEqual(session.sent_packets[0][1], 9)

        # Step 5: Cutscene movie finishes on client -> Client sends AC 20 Sub 6
        session.storm_cutscene_start_time = 0  # Simulate cutscene duration elapsed (> 1.0s)
        session.sent_packets.clear()
        reader_sub6 = PacketReader(b"\x06")
        await handle_20.handle(server, session, reader_sub6)

        # Should send AC 20:7 Warp Out, and teleport to Beach (Map 10035 pos 1038, 2235)
        self.assertFalse(getattr(session, "playing_storm_cutscene", False))
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

        # Should initialize Beach Cutscene: Pose 9 + AC 5:30 (immobilize) + beach_cutscene_active + stage 1
        self.assertEqual(session.emote, 9)
        self.assertTrue(getattr(session, "beach_cutscene_active", False))
        self.assertEqual(getattr(session, "beach_cutscene_stage", 0), 1)
        has_emote_9 = any(p[0] == 32 and p[1] == 2 and p[-1] == 9 for p in session.sent_packets)
        self.assertTrue(has_emote_9)
        has_immob = any(p[0] == 5 and p[1] == 30 for p in session.sent_packets)
        self.assertTrue(has_immob)
        has_pan = any(p[0] == 22 and p[1] == 11 for p in session.sent_packets)
        self.assertTrue(has_pan)
        has_cinema = any(p[0] == 6 and p[1] == 2 for p in session.sent_packets)
        self.assertTrue(has_cinema)

        # Step 7 (Stage 1 -> 2): Camera pan complete -> Robinson approaches
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 2)
        has_approach = any(p[0] == 22 and p[1] == 12 for p in session.sent_packets)
        self.assertTrue(has_approach)

        # Step 8 (Stage 2 -> 3): Robinson arrives -> Robinson speaks TalkID 12008 "(Gurgh? Gurgh?)"
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 3)
        has_gurgh = any(p[0] == 20 and p[1] == 1 for p in session.sent_packets)
        self.assertTrue(has_gurgh)

        # Step 9 (Stage 3 -> 4): Player clicked Next on dialogue -> Accept Quest 12040 Step 1
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 4)
        has_quest_grant = any(p[0] == 24 and p[1] == 1 for p in session.sent_packets)
        self.assertTrue(has_quest_grant)

        # Step 10 (Stage 4 -> 5): Sync step
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 5)

        # Step 11 (Stage 5 -> 6): Set Quest Flag 97 (Active)
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 6)
        has_flag_97 = any(p[0] == 24 and p[1] == 5 for p in session.sent_packets)
        self.assertTrue(has_flag_97)

        # Step 12 (Stage 6 -> 7): Robinson stands up / walks back
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertEqual(session.beach_cutscene_stage, 7)
        has_stand = any(p[0] == 22 and p[1] == 12 for p in session.sent_packets)
        self.assertTrue(has_stand)

        # Step 13 (Stage 7 -> Conclude): Release controls, unlock cinema, player stands up, quest persisted
        session.sent_packets.clear()
        await handle_20.handle(server, session, PacketReader(b"\x06"))
        self.assertFalse(session.beach_cutscene_active)
        self.assertEqual(session.beach_cutscene_stage, 0)
        self.assertEqual(session.emote, 0)
        self.assertEqual(get_session_quest_state(session, 12040), 1)
        has_dialogue_close = any(p[0] == 20 and p[1] == 8 for p in session.sent_packets)
        self.assertTrue(has_dialogue_close)
        has_unlock_ctrl = any(p[0] == 5 and p[1] == 4 for p in session.sent_packets)
        self.assertTrue(has_unlock_ctrl)
        has_cinema_off = any(p[0] == 6 and p[1] == 2 and p[2] == 0 for p in session.sent_packets)
        self.assertTrue(has_cinema_off)
        has_emote_reset = any(p[0] == 32 and p[1] == 2 and p[-1] == 0 for p in session.sent_packets)
        self.assertTrue(has_emote_reset)


if __name__ == "__main__":
    unittest.main()
