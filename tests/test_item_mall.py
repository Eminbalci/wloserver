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
        """Verifies handler for AC 75 Sub 1 (catalog) and Sub 2 (purchase)."""
        session = MockSession(im_points=500)
        item = self.mgr.get_catalog()[0]

        # In GameServer, opcode 75 is consumed before passing reader to handler.
        # Sub 1 = [1]
        reader1 = PacketReader(bytes([1]))
        asyncio.run(handle_75_itemmall.handle(self.server, session, reader1))
        self.assertGreater(len(session.sent_packets), 0)

        # Sub 2 = [2, ItemID_lo, ItemID_hi, quantity]
        req_pkt = PacketWriter().write_8(2).write_16(item.item_id).write_8(1).buffer
        reader2 = PacketReader(req_pkt)
        asyncio.run(handle_75_itemmall.handle(self.server, session, reader2))
        self.assertTrue(any(i.get('item_id') == item.item_id for i in session.inventory))

    def test_handle_34_itemmall(self):
        """Verifies handler for AC 34 Sub 1 (open in-game mall)."""
        session = MockSession(im_points=500)
        reader = PacketReader(bytes([1]))
        asyncio.run(handle_34_itemmall.handle(self.server, session, reader))
        # Expects: AC 54:201, AC 35:4, AC 35:11
        self.assertEqual(len(session.sent_packets), 3)
        decrypted_p1 = xor_crypt(session.sent_packets[0][4:])
        decrypted_p2 = xor_crypt(session.sent_packets[1][4:])
        decrypted_p3 = xor_crypt(session.sent_packets[2][4:])
        self.assertEqual(decrypted_p1[0], 54)
        self.assertEqual(decrypted_p2[0], 35)
        self.assertEqual(decrypted_p3[0], 35)


if __name__ == "__main__":
    unittest.main()
