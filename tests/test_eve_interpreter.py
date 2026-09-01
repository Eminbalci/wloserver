"""
Unit tests for EveEventInterpreter.
Verifies loading and execution of native eve.Emg events.
"""

import unittest
import asyncio
from unittest.mock import MagicMock

from server.eve_event_interpreter import EveEventInterpreter
from server.network import PacketWriter, xor_crypt


class MockSession:
    def __init__(self, char_id=1, char_name="Player", map_id=12000):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = map_id
        self.x = 200
        self.y = 300
        self.inventory = []
        self.quests = {}
        self.pets = []
        self.gold = 1000
        self.sent_packets = []

    async def send_packet(self, packet: PacketWriter):
        self.sent_packets.append(packet.build())


class TestEveInterpreter(unittest.TestCase):
    def test_eve_interpreter_load_and_dispatch(self):
        interp = EveEventInterpreter("data/eve.Emg")
        self.assertGreater(len(interp.map_events), 1000)

        # Map 12000 has events
        self.assertIn(12000, interp.map_events)

        server = MagicMock()
        server.map_npcs = {
            12000: [
                {"click_id": 5, "npc_id": 14013, "name": "Ashley", "events": [9, 10]}
            ]
        }
        server.send_dialogue = MagicMock()

        async def mock_send_dialogue(s, cid, tid, step=1, portrait_type=3):
            pkt = PacketWriter().write_8(20).write_8(1).write_8(0).write_8(0).write_8(0)
            pkt.write_8(step).write_8(1).write_8(portrait_type).write_8(cid).write_8(0)
            pkt.write_8(1).write_8(0).write_8(0).write_8(0).write_8(0)
            pkt.write_8(tid & 0xFF).write_8((tid >> 8) & 0xFF).write_8((tid >> 16) & 0xFF)
            await s.send_packet(pkt)

        server.send_dialogue = mock_send_dialogue
        session = MockSession(map_id=12000)

        handled = asyncio.run(interp.try_execute(server, session, 5))
        self.assertTrue(handled)
        self.assertGreater(len(session.sent_packets), 0)

    def test_chest_and_item_grant_opcode1(self):
        interp = EveEventInterpreter("data/eve.Emg")
        from unittest.mock import AsyncMock
        server = MagicMock()
        server.items = {"10001": "Coconut"}
        server.get_item_name = MagicMock(return_value="Coconut")
        server.send_dialogue = AsyncMock()
        
        session = MockSession(map_id=10035)
        # Event for Chest on Beach (Map 10035, ClickID 7, Opcode 1)
        handled = asyncio.run(interp.try_execute(server, session, 7))
        self.assertTrue(handled)


if __name__ == "__main__":
    unittest.main()
