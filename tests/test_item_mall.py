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
        async def mock_grant_item(session, item_id, amount=1, *args, **kwargs):
            from server.gameserver import add_item_to_inventory
            add_item_to_inventory(session, item_id, amount)
            return True
        self.server.grant_item = mock_grant_item

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

    def test_catalog_packet_structure_and_sale_pricing(self):
        """Verifies 10-byte entry layout with authentic normal price, sale price, and NEW/HOT badge tags."""
        # Manually create mock catalog with sale and new items
        self.mgr._catalog = [
            MallItemEntry(
                item_id=47001,
                item_name="Crude Oil",
                category="Hot",
                point_cost=1,
                original_price=120,
                is_hot=0,
                is_new=1,
                on_sale=1,
                subcategory_id=1
            ),
            MallItemEntry(
                item_id=28001,
                item_name="Forgotten Scroll",
                category="Grocery",
                point_cost=200,
                original_price=0,
                is_hot=1,
                is_new=0,
                on_sale=0,
                subcategory_id=1
            )
        ]
        session = MockSession()
        asyncio.run(self.mgr.send_catalog(session))
        decrypted = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted[0], 75)
        self.assertEqual(decrypted[1], 1)

        import struct
        count = struct.unpack_from("<H", decrypted, 2)[0]
        self.assertEqual(count, 2)

        # First item: Crude oil on sale (1 point sale price, orig 120, NEW tag 1)
        item1_bytes = decrypted[4:14]
        item1_id, item1_subcat, item1_base, item1_disc, item1_tag, item1_cat, item1_price = struct.unpack("<HBHBBBH", item1_bytes)
        self.assertEqual(item1_id, 47001)
        self.assertEqual(item1_subcat, 1)
        self.assertEqual(item1_base, 120)    # Base original price (120)
        self.assertLess(item1_disc, 100)     # Discount % (< 100 = sale active)
        self.assertEqual(item1_tag, 1)       # NEW starburst badge tag
        self.assertEqual(item1_cat, 1)       # Hot category
        self.assertEqual(item1_price, 120)   # Base price

        # Second item: Forgotten scroll (200 points, no discount, HOT tag 2)
        item2_bytes = decrypted[14:24]
        item2_id, item2_subcat, item2_base, item2_disc, item2_tag, item2_cat, item2_price = struct.unpack("<HBHBBBH", item2_bytes)
        self.assertEqual(item2_id, 28001)
        self.assertEqual(item2_subcat, 1)
        self.assertEqual(item2_base, 200)    # Regular price (200)
        self.assertEqual(item2_disc, 100)    # 100% of price (No discount, no strike-through, no On Sale 0)
        self.assertEqual(item2_tag, 2)       # HOT badge tag
        self.assertEqual(item2_cat, 4)       # Grocery category
        self.assertEqual(item2_price, 200)

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
        session = MockSession(im_points=0)
        diamond = self.mgr.get_item(47010)  # 3 or 250 points

        success = asyncio.run(self.mgr.purchase_item(self.server, session, diamond.item_id, quantity=1))
        self.assertFalse(success)
        self.assertEqual(session.im_points, 0)
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
        """Verifies handler for AC 34 Sub 1 Mode 0 (points query) and Mode 1 (cart checkout)."""
        session = MockSession(im_points=500)
        # Sub 1 Mode 0 = [1, 0]
        reader0 = PacketReader(bytes([1, 0]))
        asyncio.run(handle_34_itemmall.handle(self.server, session, reader0))
        # Expects: AC 34:1, AC 75:3 Points (without reopening catalog)
        self.assertEqual(len(session.sent_packets), 2)
        decrypted_p1 = xor_crypt(session.sent_packets[0][4:])
        decrypted_p2 = xor_crypt(session.sent_packets[1][4:])
        self.assertEqual(decrypted_p1[0], 34)
        self.assertEqual(decrypted_p2[0], 75)
        self.assertEqual(decrypted_p2[1], 3)

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

    def test_handle_57_minigame_exit_and_category_switch(self):
        """Verifies AC 57 Sub 1 minigame exit / category switch packet sequence."""
        from server.handlers import handle_57_action
        session = MockSession(char_id=1, im_points=1200)
        # AC 57 Sub 1 [cat_id=0 (Exit Minigame)]
        reader = PacketReader(bytes([1, 0]))
        asyncio.run(handle_57_action.handle(self.server, session, reader))
        self.assertGreater(len(session.sent_packets), 0)

        # First packet must be AC 57:1 ACK
        decrypted_ack = xor_crypt(session.sent_packets[0][4:])
        self.assertEqual(decrypted_ack[0], 57)
        self.assertEqual(decrypted_ack[1], 1)

        # Must include AC 34:1 points sync
        found_34_pts = any(xor_crypt(p[4:])[0] == 34 and xor_crypt(p[4:])[1] == 1 for p in session.sent_packets)
        self.assertTrue(found_34_pts)

        # Must include AC 75:3 points sync
        found_75_pts = any(xor_crypt(p[4:])[0] == 75 and xor_crypt(p[4:])[1] == 3 for p in session.sent_packets)
        self.assertTrue(found_75_pts)

        # Must include AC 5:4 unfreeze / HUD restore
        found_unfreeze = any(xor_crypt(p[4:])[0] == 5 and xor_crypt(p[4:])[1] == 4 for p in session.sent_packets)
        self.assertTrue(found_unfreeze)

    def test_minigame_spin_with_im_points(self):
        """Verifies minigame/lucky draw consumes 20 IM Points and syncs balances."""
        from server.minigames_system import LuckyDrawManager
        mgr = LuckyDrawManager()
        session = MockSession(char_id=1, im_points=100)
        session.gold = 0
        session.im_tokens = 0

        # Run spin
        result = asyncio.run(mgr.spin_wheel(self.server, session))
        self.assertIsNotNone(result)
        # Should have deducted 20 points
        self.assertEqual(session.im_points, 80)
        # Should have sent AC 34:1 and AC 75:3 balance updates
        found_34 = any(xor_crypt(p[4:])[0] == 34 and xor_crypt(p[4:])[1] == 1 for p in session.sent_packets)
        found_75 = any(xor_crypt(p[4:])[0] == 75 and xor_crypt(p[4:])[1] == 3 for p in session.sent_packets)
        self.assertTrue(found_34)
        self.assertTrue(found_75)


    def test_handle_71_minigame_play(self):
        """Verifies AC 71 minigame play deducts points, awards prize, and syncs balances."""
        from server.handlers import handle_71_minigame
        session = MockSession(char_id=1, im_points=100)
        reader = PacketReader(bytes([20]))  # Minigame ID 20 (Claw Crane / DigHole)
        asyncio.run(handle_71_minigame.handle(self.server, session, reader))
        self.assertEqual(session.im_points, 80)
        # Verify AC 71 Sub 1 [1] start game packet
        found_71_start = any(xor_crypt(p[4:])[0] == 71 and xor_crypt(p[4:])[1] == 1 and xor_crypt(p[4:])[2] == 1 for p in session.sent_packets)
        self.assertTrue(found_71_start)
        # Verify AC 71 Sub 2 prize packet
        found_71_prize = any(xor_crypt(p[4:])[0] == 71 and xor_crypt(p[4:])[1] == 2 for p in session.sent_packets)
    def test_category_resolution_all_seven_tabs(self):
        """Verifies resolve_category_id maps both integer IDs and names to 1..7 correctly."""
        from server.item_mall import resolve_category_id
        self.assertEqual(resolve_category_id(1), 1)
        self.assertEqual(resolve_category_id("1"), 1)
        self.assertEqual(resolve_category_id("Hot"), 1)

        self.assertEqual(resolve_category_id(2), 2)
        self.assertEqual(resolve_category_id("2"), 2)
        self.assertEqual(resolve_category_id("Armory"), 2)
        self.assertEqual(resolve_category_id("armor"), 2)

        self.assertEqual(resolve_category_id(3), 3)
        self.assertEqual(resolve_category_id("3"), 3)
        self.assertEqual(resolve_category_id("Weaponry"), 3)
        self.assertEqual(resolve_category_id("weapon"), 3)

        self.assertEqual(resolve_category_id(4), 4)
        self.assertEqual(resolve_category_id("4"), 4)
        self.assertEqual(resolve_category_id("Grocery"), 4)
        self.assertEqual(resolve_category_id("consumable"), 4)

        self.assertEqual(resolve_category_id(5), 5)
        self.assertEqual(resolve_category_id("5"), 5)
        self.assertEqual(resolve_category_id("Furniture"), 5)
        self.assertEqual(resolve_category_id("tent"), 5)

        self.assertEqual(resolve_category_id(6), 6)
        self.assertEqual(resolve_category_id("6"), 6)
        self.assertEqual(resolve_category_id("Slot Machine"), 6)
        self.assertEqual(resolve_category_id("gacha"), 6)

        self.assertEqual(resolve_category_id(7), 7)
        self.assertEqual(resolve_category_id("7"), 7)
        self.assertEqual(resolve_category_id("Forging Room"), 7)
        self.assertEqual(resolve_category_id("forging"), 7)

    def test_json_import_and_export(self):
        """Verifies DynamicDataManager JSON export and import for item mall."""
        from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.close()

        try:
            exp_ok = GLOBAL_DYNAMIC_DATA.export_item_mall_json(tmp_path)
            self.assertTrue(exp_ok)
            self.assertTrue(os.path.exists(tmp_path))

            imp_ok = GLOBAL_DYNAMIC_DATA.import_item_mall_json(tmp_path)
            self.assertTrue(imp_ok)
            catalog = self.mgr.get_catalog()
            self.assertGreater(len(catalog), 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_gameserver_grant_item_packets(self):
        """Verifies gameserver.grant_item dispatches AC 23:6, AC 23:8, and AC 23:5."""
        from server.gameserver import GameServer, PlayerSession
        from unittest.mock import MagicMock
        server = GameServer()
        reader = MagicMock()
        writer = MagicMock()
        writer.get_extra_info = MagicMock(return_value=('127.0.0.1', 1234))
        session = PlayerSession(reader, writer)
        session.char_id = 99
        session.char_name = "TestHero"
        session.inventory = []
        sent_pkts = []

        async def mock_send(pkt):
            sent_pkts.append(pkt.build())

        session.send_packet = mock_send

        # Grant item 48050 x1
        res = asyncio.run(server.grant_item(session, 48050, 1))
        self.assertTrue(res)
        self.assertEqual(len(session.inventory), 1)
        self.assertEqual(session.inventory[0]["item_id"], 48050)

        # Check that AC 23:6 (item arrival), AC 23:8 (slot update), and AC 23:5 (full inv) were sent
        pkt_23_6_raw = next(p for p in sent_pkts if xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 6)
        decrypted_23_6 = xor_crypt(pkt_23_6_raw[4:])
        self.assertEqual(decrypted_23_6[0], 23)
        self.assertEqual(decrypted_23_6[1], 6)
        self.assertEqual(int.from_bytes(decrypted_23_6[2:4], "little"), 48050)
        self.assertEqual(decrypted_23_6[4], 1)  # Amount must be 1, not 0!
        self.assertEqual(len(decrypted_23_6), 31)

        found_23_8 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 8 for p in sent_pkts)
        found_23_5 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 5 for p in sent_pkts)
        self.assertTrue(found_23_8)
        self.assertTrue(found_23_5)

    def test_gameserver_grant_item_suppress_acquire_notice(self):
        """Verifies grant_item with send_acquire_notice=False suppresses AC 23:6 Obtain popup."""
        from server.gameserver import GameServer, PlayerSession
        from unittest.mock import MagicMock
        server = GameServer()
        reader = MagicMock()
        writer = MagicMock()
        writer.get_extra_info = MagicMock(return_value=('127.0.0.1', 1234))
        session = PlayerSession(reader, writer)
        session.char_id = 99
        session.char_name = "TestHero"
        session.inventory = []
        sent_pkts = []

        async def mock_send(pkt):
            sent_pkts.append(pkt.build())

        session.send_packet = mock_send

        # Grant item with send_acquire_notice=False (Item Mall flow)
        res = asyncio.run(server.grant_item(session, 48050, 1, send_acquire_notice=False))
        self.assertTrue(res)
        self.assertEqual(len(session.inventory), 1)

        # AC 23:6 must NOT be sent
        found_23_6 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 6 for p in sent_pkts)
        self.assertFalse(found_23_6, "AC 23:6 must not be sent when send_acquire_notice is False")

        # AC 23:8 and AC 23:5 must still be sent
        found_23_8 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 8 for p in sent_pkts)
        found_23_5 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 5 for p in sent_pkts)
        self.assertTrue(found_23_8)
        self.assertTrue(found_23_5)

    def test_chest_system_open_and_grant_item(self):
        """Verifies ChestSystem.open_chest calls grant_item and dispenses loot."""
        from server.chest_system import ChestSystem
        from server.gameserver import GameServer, PlayerSession
        from unittest.mock import MagicMock
        chest_sys = ChestSystem()
        server = GameServer()
        reader = MagicMock()
        writer = MagicMock()
        writer.get_extra_info = MagicMock(return_value=('127.0.0.1', 1234))
        session = PlayerSession(reader, writer)
        session.char_id = 9999
        session.char_name = "Looter"
        session.inventory = []
        sent_pkts = []

        async def mock_send(pkt):
            sent_pkts.append(pkt.build())

        session.send_packet = mock_send

        # Use clean DB table for chest testing
        import sqlite3
        with sqlite3.connect(chest_sys.db_path) as conn:
            conn.execute("DELETE FROM charchests WHERE char_id = ?", (session.char_id,))
            conn.commit()

        # Open chest #10 on map 10036
        opened = asyncio.run(chest_sys.open_chest(server, session, 10036, 10, prop_name="Chest"))
        self.assertTrue(opened)
        self.assertGreater(len(session.inventory), 0)

        # Verify AC 23:6 item delivery was dispatched
        found_23_6 = any(xor_crypt(p[4:])[0] == 23 and xor_crypt(p[4:])[1] == 6 for p in sent_pkts)
        self.assertTrue(found_23_6)

    def test_authentic_item_mall_11_pages_grocery(self):
        """Verifies authentic Points Mall catalog contains 152 items and 123 Grocery items spanning 11 pages."""
        import math
        self.mgr.reload_from_db()
        points_items = self.mgr.get_catalog(is_bonus=False)
        self.assertGreaterEqual(len(points_items), 152)

        # Grocery singles (cat 3) and packs (cat 4)
        grocery_singles = [it for it in points_items if it.category_id == 3]
        grocery_packs = [it for it in points_items if it.category_id == 4]
        total_grocery = len(grocery_singles) + len(grocery_packs)
        self.assertGreaterEqual(len(grocery_singles), 102)
        self.assertEqual(len(grocery_packs), 21)
        self.assertGreaterEqual(total_grocery, 123)

        # 12 items per client page -> exactly 11 pages of Grocery
        grocery_pages = math.ceil(total_grocery / 12)
        self.assertEqual(grocery_pages, 11)

    def test_bonus_mall_catalog_ac75_sub10(self):
        """Verifies Bonus Mall catalog contains 71 authentic items and dispatches AC 75 Sub 10."""
        self.mgr.reload_from_db()
        bonus_items = self.mgr.get_catalog(is_bonus=True)
        self.assertEqual(len(bonus_items), 71)

        sent_pkts = []
        class MockSession:
            async def send_packet(self, pkt):
                sent_pkts.append(pkt.build())

        session = MockSession()
        asyncio.run(self.mgr.send_catalog(session, is_bonus=True))
        self.assertEqual(len(sent_pkts), 1)
        decrypted = xor_crypt(sent_pkts[0][4:])
        self.assertEqual(decrypted[0], 75)
        self.assertEqual(decrypted[1], 10)  # Sub 10 for Bonus Mall
        import struct
        count = struct.unpack_from("<H", decrypted, 2)[0]
        self.assertEqual(count, 71)

    def test_initial_mall_sync_sequence(self):
        """Verifies full initial mall sync sequence: AC 75:1, AC 75:10, AC 75:8, AC 75:7, AC 75:3."""
        sent_pkts = []
        class MockSession:
            account_id = 999
            char_name = "SyncHero"
            im_points = 500
            im_bonus_points = 100
            async def send_packet(self, pkt):
                sent_pkts.append(pkt.build())

        session = MockSession()
        asyncio.run(self.mgr.send_initial_mall_sync(session))
        self.assertEqual(len(sent_pkts), 5)

        decrypted_pkts = [xor_crypt(p[4:]) for p in sent_pkts]
        # 1. Points Mall (75:1)
        self.assertEqual((decrypted_pkts[0][0], decrypted_pkts[0][1]), (75, 1))
        # 2. Bonus Mall (75:10)
        self.assertEqual((decrypted_pkts[1][0], decrypted_pkts[1][1]), (75, 10))
        # 3. Mall sync settings (75:8)
        self.assertEqual((decrypted_pkts[2][0], decrypted_pkts[2][1]), (75, 8))
        # 4. Mall status (75:7)
        self.assertEqual((decrypted_pkts[3][0], decrypted_pkts[3][1]), (75, 7))
        # 5. Dual balance sync (75:3)
        self.assertEqual((decrypted_pkts[4][0], decrypted_pkts[4][1]), (75, 3))

    def test_bonus_mall_purchase_with_bonus_points(self):
        """Verifies purchase in Bonus Mall deducts bonus points and grants item."""
        self.mgr.reload_from_db()
        from unittest.mock import MagicMock
        server = MagicMock()
        granted = []
        async def mock_grant(session, item_id, count, send_acquire_notice=False):
            granted.append((item_id, count))
        server.grant_item = mock_grant

        class MockSession:
            account_id = 888
            char_name = "BonusBuyer"
            im_points = 1000
            im_bonus_points = 500
            async def send_packet(self, pkt):
                pass

        session = MockSession()
        # Item 57205 in Bonus Mall costs 32 bonus points
        success = asyncio.run(self.mgr.purchase_item(server, session, item_id=57205, quantity=2, is_bonus=True))
        self.assertTrue(success)
        self.assertEqual(session.im_bonus_points, 500 - (32 * 2))
        self.assertEqual(session.im_points, 1000)  # IM points untouched!
        self.assertEqual(granted, [(57205, 2)])


if __name__ == "__main__":
    unittest.main()


