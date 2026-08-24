"""
Unit Test Suite for Wonderland Online Item Mall System
Tests:
- ItemMallManager loading and catalog querying
- Dedicated Port 6416 binary catalog payload generation
- User IM points management (Get, Set, Add)
- Purchasing flow (points deduction, inventory delivery, system notice)
- Packet formatting for AC 75:1, AC 75:3, AC 34:1, AC 34:2
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.item_mall import ItemMallManager, ItemMallServer, GLOBAL_ITEM_MALL_MANAGER, MallItemEntry
from server.network import PacketReader, PacketWriter, xor_crypt
from server.handlers import handle_75_itemmall, handle_34_itemmall


class MockSession:
    def __init__(self, char_id=1, char_name="Hero", account_id=1, im_points=1000):
        self.char_id = char_id
        self.char_name = char_name
        self.username = "testuser"
        self.account_id = account_id
        self.im_points = im_points
        self.im_bonus_points = 200
        self.im_tokens = 10
        self.inventory = []
        self.sent_packets = []

    async def send_packet(self, packet: PacketWriter):
        self.sent_packets.append(packet.build())


class TestItemMallSystem(unittest.TestCase):
    def setUp(self):
        self.mgr = ItemMallManager()
        self.server = MagicMock()
        self.server.build_inventory_packet = MagicMock(return_value=PacketWriter().write_8(23).write_8(1))

    def test_catalog_loaded(self):
        """Verifies catalog is loaded with items from dynamic database."""
        catalog = self.mgr.get_catalog()
        self.assertGreater(len(catalog), 0)
        diamond = self.mgr.get_item(47010)
        self.assertIsNotNone(diamond)
        self.assertEqual(diamond.item_id, 47010)

    def test_binary_catalog_payload(self):
        """Verifies port 6416 binary payload format [0xC9, 0x00, 0x01, ...]."""
        mall_srv = ItemMallServer(port=6416)
        payload = mall_srv.build_catalog_payload()
        self.assertGreater(len(payload), 3)
        self.assertEqual(payload[0], 0xC9)
        self.assertEqual(payload[1], 0x00)
        self.assertEqual(payload[2], 0x01)

    def test_send_catalog_and_balance_packet(self):
        """Verifies AC 75:1 and AC 75:3 packets dispatched to client."""
        session = MockSession()
        asyncio.run(self.mgr.send_catalog(session))
        self.assertGreater(len(session.sent_packets), 0)

        # Decrypt payload (bytes 4 onward)
        decrypted = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted[0], 75)
        self.assertEqual(decrypted[1], 1)

    def test_purchase_item_success(self):
        """Verifies player can purchase an item with sufficient IM points."""
        session = MockSession(im_points=1000)
        item = self.mgr.get_catalog()[0]

        success = asyncio.run(self.mgr.purchase_item(self.server, session, item.item_id, quantity=1))
        self.assertTrue(success)
        self.assertEqual(session.im_points, 1000 - item.point_cost)
        self.assertTrue(any(i.get('item_id') == item.item_id for i in session.inventory))

    def test_purchase_item_insufficient_points(self):
        """Verifies purchase fails gracefully if player has insufficient points."""
        session = MockSession(im_points=10)
        diamond = self.mgr.get_item(47010)  # 250 points

        success = asyncio.run(self.mgr.purchase_item(self.server, session, diamond.item_id, quantity=1))
        self.assertFalse(success)
        self.assertEqual(session.im_points, 10)
        self.assertEqual(len(session.inventory), 0)

    def test_handle_75_itemmall(self):
        """Verifies handler for AC 75 Sub 1 (catalog), Sub 4 (category switch), Sub 5 (buy)."""
        session = MockSession(im_points=500)
        item = self.mgr.get_catalog()[0]

        # Sub 1 = [1] -> sends AC 75:1 and AC 75:3
        reader1 = PacketReader(bytes([1]))
        asyncio.run(handle_75_itemmall.handle(self.server, session, reader1))
        self.assertGreater(len(session.sent_packets), 0)

        # Sub 4 with 1 byte = Category switch [4, cat_id=2] -> AC 57:1 ACK + AC 75:1
        session.sent_packets.clear()
        reader_cat = PacketReader(bytes([4, 2]))
        asyncio.run(handle_75_itemmall.handle(self.server, session, reader_cat))
        self.assertGreater(len(session.sent_packets), 0)
        ack_p = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(ack_p[0], 57)
        self.assertEqual(ack_p[1], 1)

        # Sub 5 with item_id and quantity -> [5, ItemID_lo, ItemID_hi, quantity]
        session.sent_packets.clear()
        req_pkt = PacketWriter().write_8(5).write_16(item.item_id).write_8(1).buffer
        reader5 = PacketReader(req_pkt)
        asyncio.run(handle_75_itemmall.handle(self.server, session, reader5))
        self.assertTrue(any(i.get('item_id') == item.item_id for i in session.inventory))
        # Find buy response packet [75, 5]
        found_buy_resp = any(xor_crypt(p[4:])[0] == 75 and xor_crypt(p[4:])[1] == 5 for p in session.sent_packets)
        self.assertTrue(found_buy_resp)

    def test_handle_34_itemmall(self):
        """Verifies handler for AC 34 Sub 1 Mode 0 (points query & catalog) and Mode 1 (cart checkout)."""
        session = MockSession(im_points=500)
        # Sub 1 Mode 0 = [1, 0]
        reader0 = PacketReader(bytes([1, 0]))
        asyncio.run(handle_34_itemmall.handle(self.server, session, reader0))
        # Expects: AC 34:1, AC 75:1, AC 75:3
        self.assertEqual(len(session.sent_packets), 3)
        decrypted_p1 = xor_crypt(session.sent_packets[0][4:])
        decrypted_p2 = xor_crypt(session.sent_packets[1][4:])
        decrypted_p3 = xor_crypt(session.sent_packets[2][4:])
        self.assertEqual(decrypted_p1[0], 34)
        self.assertEqual(decrypted_p2[0], 75)
        self.assertEqual(decrypted_p3[0], 75)

    def test_handle_13_itemmall_query(self):
        """Verifies AC 13 Sub 238 UI Item Mall click query confirmation."""
        from server.handlers import handle_13_action
        session = MockSession(char_id=42, im_points=800)
        reader = PacketReader(bytes([238]))
        asyncio.run(handle_13_action.handle(self.server, session, reader))
        self.assertGreater(len(session.sent_packets), 0)
        decrypted_p1 = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted_p1[0], 13)
        self.assertEqual(decrypted_p1[1], 42)

    def test_handle_21_native_mall_window(self):
        """Verifies AC 21 Sub 1 native mall GUI window dispatch."""
        from server.handlers import handle_21_action
        session = MockSession(im_points=800)
        reader = PacketReader(bytes([1]))
        asyncio.run(handle_21_action.handle(self.server, session, reader))
        self.assertGreater(len(session.sent_packets), 0)
        decrypted_p1 = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted_p1[0], 75)
        self.assertEqual(decrypted_p1[1], 3)
        decrypted_p2 = xor_crypt(session.sent_packets[1][4:])
        self.assertEqual(decrypted_p2[0], 21)
        self.assertEqual(decrypted_p2[1], 1)

    def test_server_branding_live_update(self):
        """Verifies server name / branding can be modified and read live."""
        from server.gameserver import GameServer
        server = GameServer(db_path=":memory:", static_db_path="server/ServerDataBase.db")
        self.assertEqual(server.get_server_name(), "Mamiletta")
        server.set_server_name("Wonderland 2.0")
        self.assertEqual(server.get_server_name(), "Wonderland 2.0")


if __name__ == "__main__":
    unittest.main()
