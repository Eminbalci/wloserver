import unittest
import struct
import asyncio
from typing import List, Dict, Any

from server.network import PacketWriter, PacketReader
import server.handlers.handle_23_items as handle_23


class MockServer:
    def __init__(self):
        self.sessions = {}
        self.items = {}
        self.map_ground_items = {}
        self._COMPOUND_RECIPES = {
            1: {
                "result_item": 43002,
                "result_amount": 1,
                "materials": [{"item_id": 45001, "amount": 1}, {"item_id": 43002, "amount": 1}]
            }
        }
        self.item_mix_recipes = {}
        self.item_properties = {}

    def save_player_to_db(self, player):
        pass

    def broadcast_to_map(self, map_id, packet, exclude_session=None):
        pass

    def build_inventory_packet(self, player):
        return PacketWriter().write_8(23).write_8(2).write_8(len(player.inventory))


class MockSession:
    def __init__(self, char_name="AlchemyHero", char_id=7777):
        self.char_name = char_name
        self.char_id = char_id
        self.map_id = 10001
        self.gold = 1000
        self.inventory: List[Dict[str, Any]] = []
        self.equipments = [0] * 6
        self.skills = {}
        self.sent_packets: List[bytes] = []

    async def send_packet(self, packet: PacketWriter):
        self.sent_packets.append(packet.to_bytes())


class TestGroundAndCompound(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.server = MockServer()
        self.session = MockSession()
        self.server.sessions[self.session.char_id] = self.session
        self.server.map_ground_items[self.session.map_id] = [None] * 256

    async def test_ground_item_pickup_authentic(self):
        """Tests authentic ground item pickup (AC 23 Sub 2 -> AC 23:2 despawn + AC 23:6 item delivery)."""
        # Place item 45001 on ground at index 1
        ground_idx = 1
        self.server.map_ground_items[self.session.map_id][ground_idx - 1] = {
            "item_id": 45001,
            "amount": 1,
            "is_gold": False
        }

        # Client sends AC 23 Sub 2 with 2-byte ground index: [23, 2, 1, 0]
        c2s_pkt = PacketWriter().write_8(2).write_16(ground_idx)
        reader = PacketReader(c2s_pkt.to_bytes())

        await handle_23.handle(self.server, self.session, reader)

        # 1. Ground slot cleared
        self.assertIsNone(self.server.map_ground_items[self.session.map_id][ground_idx - 1])

        # 2. Item added to inventory
        self.assertEqual(len(self.session.inventory), 1)
        self.assertEqual(self.session.inventory[0]["item_id"], 45001)

        # 3. Authentic AC 23 Sub 6 Item Delivery packet sent to player (33 bytes)
        p6_list = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 6]
        self.assertTrue(len(p6_list) > 0)
        self.assertEqual(len(p6_list[0]), 33)
        delivered_id = struct.unpack_from('<H', p6_list[0], 2)[0]
        delivered_count = struct.unpack_from('<H', p6_list[0], 4)[0]
        self.assertEqual(delivered_id, 45001)
        self.assertEqual(delivered_count, 1)

    async def test_compounding_two_items_authentic(self):
        """Tests authentic compounding of two items (AC 23 Sub 14 -> AC 23:9 x2 + AC 23:8 + AC 23:13)."""
        # Place material 1 in slot 18, material 2 in slot 19
        self.session.inventory.append({"slot": 18, "item_id": 43002, "amount": 1})
        self.session.inventory.append({"slot": 19, "item_id": 45001, "amount": 1})

        # Client sends: [23, 14, 2, 19, 18]
        c2s_pkt = PacketWriter().write_8(14).write_8(2).write_8(19).write_8(18)
        reader = PacketReader(c2s_pkt.to_bytes())

        await handle_23.handle(self.server, self.session, reader)

        # 1. Verify AC 23 Sub 9 deduct packets: [23, 9, slot, 1]
        p9_list = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 9]
        self.assertEqual(len(p9_list), 2)
        slots_deducted = [p[2] for p in p9_list]
        self.assertIn(19, slots_deducted)
        self.assertIn(18, slots_deducted)
        for p in p9_list:
            self.assertEqual(p[3], 1)  # 1 item deducted

        # 2. Verify AC 23 Sub 8 outcome packet (33 bytes): [23, 8, slot, result_item, result_count, 27 zeros]
        p8_list = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 8]
        self.assertTrue(len(p8_list) > 0)
        self.assertEqual(len(p8_list[0]), 33)
        res_slot = p8_list[0][2]
        res_item = struct.unpack_from('<H', p8_list[0], 3)[0]
        res_count = p8_list[0][5]
        self.assertEqual(res_item, 43002)
        self.assertEqual(res_count, 1)

        # 3. Verify AC 23 Sub 13 outcome window packet (6 bytes): [23, 13, item_id (2B), count (1B), slot (1B)]
        p13_list = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 13]
        self.assertTrue(len(p13_list) > 0)
        self.assertEqual(len(p13_list[0]), 6)
        anim_item = struct.unpack_from('<H', p13_list[0], 2)[0]
        anim_count = p13_list[0][4]
        anim_slot = p13_list[0][5]
        self.assertEqual(anim_item, 43002)
        self.assertEqual(anim_count, 1)
        self.assertEqual(anim_slot, res_slot)


if __name__ == '__main__':
    unittest.main()
