"""
Unit tests for authentic NPC Shop System (Action Code 27 / 0x1B).
Reverse-engineered from authentic shoplarincalismamantigi.pcapng capture.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock

from server.network import PacketReader, PacketWriter
from server.handlers.handle_27_shop import handle as handle_shop
from server.handlers.handle_20_interaction import handle as handle_interaction


class DummySession:
    def __init__(self, char_id=1, char_name="TestHero", gold=1000):
        self.char_id = char_id
        self.char_name = char_name
        self.gold = gold
        self.map_id = 10001
        self.x = 100
        self.y = 100
        self.inventory = [
            {"item_id": 602, "amount": 5, "slot": 1},
            {"item_id": 27001, "amount": 1, "slot": 2},
        ]
        self.equipments = []
        self.sent_packets = []
        self.last_clicked_npc_id = 23
        self.username = "test_user"
        self.ip = "127.0.0.1"

    async def send_packet(self, packet):
        self.sent_packets.append(packet.to_bytes() if hasattr(packet, "to_bytes") else bytes(packet))


class DummyServer:
    def __init__(self):
        self.map_npcs = {}
        self.items = {"602": "Herb", "27001": "Boat"}
        self.saved_players = []

    def save_player_to_db(self, session):
        self.saved_players.append(session.char_id)

    def get_item_name(self, item_id):
        return self.items.get(str(item_id), f"Item #{item_id}")


class TestNpcShopAC27(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = DummyServer()
        self.session = DummySession()

    async def test_buy_item_success(self):
        """Tests buying an item with sufficient gold (Sub 1)."""
        # [AC 27, Sub 1, item_id=602 (0x025A LE), amount=2]
        # 602 price is 50 -> 2 * 50 = 100 gold
        pkt = bytes([27, 1, 0x5A, 0x02, 2])
        reader = PacketReader(pkt)
        reader.read_8()  # Consume AC 27
        
        initial_gold = self.session.gold
        await handle_shop(self.server, self.session, reader)

        # Check gold deduction: 1000 - 100 = 900
        self.assertEqual(self.session.gold, initial_gold - 100)
        self.assertIn(self.session.char_id, self.server.saved_players)

        # Verify sent packets: AC 26 (gold), AC 23:6 (delivery), AC 27:1:0 (ACK)
        opcodes = [p[0] for p in self.session.sent_packets]
        self.assertIn(26, opcodes)
        self.assertIn(23, opcodes)
        self.assertIn(27, opcodes)

        # Check ACK packet: [27, 1, 0]
        ack_packets = [p for p in self.session.sent_packets if p[0] == 27 and p[1] == 1]
        self.assertTrue(len(ack_packets) > 0)
        self.assertEqual(ack_packets[0][2], 0)  # Status 0 = Success

    async def test_buy_item_insufficient_gold(self):
        """Tests buying an item without enough gold."""
        self.session.gold = 20  # Needs 100
        pkt = bytes([27, 1, 0x5A, 0x02, 2])
        reader = PacketReader(pkt)
        reader.read_8()

        await handle_shop(self.server, self.session, reader)
        self.assertEqual(self.session.gold, 20)  # Not deducted

        # Check failure ACK: [27, 1, 1]
        ack_packets = [p for p in self.session.sent_packets if p[0] == 27 and p[1] == 1]
        self.assertTrue(len(ack_packets) > 0)
        self.assertEqual(ack_packets[0][2], 1)  # Status 1 = Failure

    async def test_sell_item_success(self):
        """Tests selling an item from inventory (Sub 2 - matching pcap 1b 02 18 01)."""
        # Sell 2x item from slot 1 (602 Herb, 5 owned, buy_price 50, sell_price 25 each -> +50 gold)
        initial_gold = self.session.gold
        pkt = bytes([27, 2, 1, 2])
        reader = PacketReader(pkt)
        reader.read_8()

        await handle_shop(self.server, self.session, reader)

        # Quantity updated: 5 - 2 = 3
        slot1_item = [it for it in self.session.inventory if it.get("slot") == 1][0]
        self.assertEqual(slot1_item["amount"], 3)
        self.assertEqual(self.session.gold, initial_gold + 50)

        # Verify AC 23:9 slot update, AC 26:1 gold sync, AC 27:2:0 ACK
        ack_packets = [p for p in self.session.sent_packets if p[0] == 27 and p[1] == 2]
        self.assertTrue(len(ack_packets) > 0)
        self.assertEqual(ack_packets[0][2], 0)  # Status 0 = Success

        slot_updates = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 9]
        self.assertTrue(len(slot_updates) > 0)
        self.assertEqual(slot_updates[0][2], 1)  # Slot 1
        self.assertEqual(slot_updates[0][3], 3)  # New amount 3

    async def test_sell_entire_stack(self):
        """Tests selling entire item stack resulting in inventory slot removal."""
        initial_gold = self.session.gold
        # Sell 1x slot 2 (Boat, 1 owned, buy_price 50, sell_price 25)
        pkt = bytes([27, 2, 2, 1])
        reader = PacketReader(pkt)
        reader.read_8()

        await handle_shop(self.server, self.session, reader)

        # Slot 2 should be completely removed
        slot2_items = [it for it in self.session.inventory if it.get("slot") == 2]
        self.assertEqual(len(slot2_items), 0)
        self.assertEqual(self.session.gold, initial_gold + 25)

    async def test_open_props_shop_sub3(self):
        """Tests opening Props shop window (Sub 3 -> 1b 03 + 14 09)."""
        pkt = bytes([27, 3])
        reader = PacketReader(pkt)
        reader.read_8()

        await handle_shop(self.server, self.session, reader)
        self.assertEqual(self.session.sent_packets[0], bytes([27, 3]))
        self.assertEqual(self.session.sent_packets[1], bytes([20, 9]))

    async def test_open_weapon_shop_sub4(self):
        """Tests opening Weapon shop window (Sub 4 -> 1b 04 + 14 09)."""
        pkt = bytes([27, 4])
        reader = PacketReader(pkt)
        reader.read_8()

        await handle_shop(self.server, self.session, reader)
        self.assertEqual(self.session.sent_packets[0], bytes([27, 4]))
        self.assertEqual(self.session.sent_packets[1], bytes([20, 9]))

    async def test_interaction_shop_menu_choices(self):
        """Tests dialog option 0x1E (menu 2), 0x1F (buy), 0x28 (sell)."""
        # Option 0x1E (30): Menu 2
        pkt_1e = bytes([20, 9, 0x1E])
        reader_1e = PacketReader(pkt_1e)
        reader_1e.read_8()
        await handle_interaction(self.server, self.session, reader_1e)
        # Menu 2 packet sent
        self.assertTrue(any(p[0] == 20 and p[1] == 1 for p in self.session.sent_packets))

        # Option 0x1F (31): Buy Props (NPC 23)
        self.session.sent_packets.clear()
        self.session.last_clicked_npc_id = 23
        pkt_1f = bytes([20, 9, 0x1F])
        reader_1f = PacketReader(pkt_1f)
        reader_1f.read_8()
        await handle_interaction(self.server, self.session, reader_1f)
        self.assertEqual(self.session.sent_packets[0], bytes([27, 3]))
        self.assertEqual(self.session.sent_packets[1], bytes([20, 9]))

        # Option 0x1F (31): Buy Weapon (NPC 24)
        self.session.sent_packets.clear()
        self.session.last_clicked_npc_id = 24
        reader_1f_w = PacketReader(pkt_1f)
        reader_1f_w.read_8()
        await handle_interaction(self.server, self.session, reader_1f_w)
        self.assertEqual(self.session.sent_packets[0], bytes([27, 4]))
        self.assertEqual(self.session.sent_packets[1], bytes([20, 9]))

        # Option 0x28 (40): Sell
        self.session.sent_packets.clear()
        pkt_28 = bytes([20, 9, 0x28])
        reader_28 = PacketReader(pkt_28)
        reader_28.read_8()
        await handle_interaction(self.server, self.session, reader_28)
        self.assertEqual(self.session.sent_packets[0], bytes([20, 9]))


if __name__ == "__main__":
    unittest.main()
