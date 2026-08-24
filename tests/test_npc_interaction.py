"""
Unit tests for NPC interaction and Wild Monster identification.
Verifies that peaceful town NPCs (such as Ashley 14013, passengers, villagers, companions)
never trigger battle when clicked, and only authentic wild monsters initiate PvE combat.
"""

import unittest
import asyncio
from unittest.mock import MagicMock

from server.handlers.handle_20_interaction import is_wild_monster, handle
from server.network import PacketReader, PacketWriter, xor_crypt


class MockSession:
    def __init__(self, char_id=1, char_name="Player", map_id=12000):
        self.char_id = char_id
        self.char_name = char_name
        self.username = "testuser"
        self.map_id = map_id
        self.x = 200
        self.y = 300
        self.inventory = []
        self.quests = {}
        self.pets = []
        self.gold = 1000
        self.bank_gold = 5000
        self.sent_packets = []

    async def send_packet(self, packet: PacketWriter):
        self.sent_packets.append(packet.build())


class TestNpcInteraction(unittest.TestCase):
    def test_is_wild_monster_classification(self):
        """Verifies template and keyword based wild monster identification."""
        # 1. Ashley (14013) on Cruise Ship (12000) -> NOT a monster
        self.assertFalse(is_wild_monster(14013, "Ashley", map_id=12000))

        # 2. Robinson (12032) -> Companion, NOT a monster
        self.assertFalse(is_wild_monster(12032, "Robinson", map_id=10035))

        # 3. Shopkeeper / Doctor / Banker -> NOT a monster
        self.assertFalse(is_wild_monster(13007, "Props Shop", map_id=10000))
        self.assertFalse(is_wild_monster(14151, "Doctor", map_id=10000))
        self.assertFalse(is_wild_monster(14181, "Bank", map_id=10000))

        # 4. Villagers & Ship Passengers -> NOT a monster
        self.assertFalse(is_wild_monster(14001, "Villager", map_id=10000))
        self.assertFalse(is_wild_monster(14010, "Passenger", map_id=12000))
        self.assertFalse(is_wild_monster(17400, "Pig", map_id=10000))

        # 5. Wild monsters (17000-17999) on outdoor field maps -> IS a monster
        self.assertTrue(is_wild_monster(17001, "Jellyfish", map_id=10035))
        self.assertTrue(is_wild_monster(17015, "Forest Spider", map_id=10011))

    def test_click_ashley_npc_triggers_dialogue_not_battle(self):
        """Verifies that clicking Ashley (ID 5, Template 14013) on Map 12000 sends dialogue packet."""
        server = MagicMock()
        server.map_npcs = {
            12000: [
                {"click_id": 5, "npc_id": 14013, "name": "Ashley", "x": 300, "y": 400}
            ]
        }
        server.quest_manager.get_quest_battle.return_value = None
        server.enter_battle = MagicMock()

        async def mock_send_dialogue(s, cid, tid, step=1, portrait_type=3):
            pkt = PacketWriter().write_8(20).write_8(1).write_8(0).write_8(0).write_8(0)
            pkt.write_8(step).write_8(1).write_8(portrait_type).write_8(cid).write_8(0)
            pkt.write_8(1).write_8(0).write_8(0).write_8(0).write_8(0)
            pkt.write_8(tid & 0xFF).write_8((tid >> 8) & 0xFF).write_8((tid >> 16) & 0xFF)
            await s.send_packet(pkt)

        server.send_dialogue = mock_send_dialogue

        session = MockSession(map_id=12000)

        # Build AC 20 Sub 1 packet with ClickID 5
        reader = PacketReader(PacketWriter().write_8(1).write_16(5).buffer)
        asyncio.run(handle(server, session, reader))

        # Ensure enter_battle was NOT called
        server.enter_battle.assert_not_called()

        # Ensure authentic dialogue packet (AC 20 Sub 1) was sent
        self.assertGreater(len(session.sent_packets), 0)
        decrypted = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted[0], 20)
        self.assertEqual(decrypted[1], 1)

    def test_continue_interaction_sub_6_unlocks_client(self):
        """Verifies AC 20 Sub 6 sends unlock packets 20:8 and 5:4."""
        server = MagicMock()
        session = MockSession(map_id=12000)
        session.active_quest_id = None

        reader = PacketReader(PacketWriter().write_8(6).buffer)
        asyncio.run(handle(server, session, reader))

        self.assertGreaterEqual(len(session.sent_packets), 2)
        pkt1 = xor_crypt(session.sent_packets[0][4:])
        pkt2 = xor_crypt(session.sent_packets[1][4:])
        self.assertEqual((pkt1[0], pkt1[1]), (20, 8))
        self.assertEqual((pkt2[0], pkt2[1]), (5, 4))


if __name__ == "__main__":
    unittest.main()
