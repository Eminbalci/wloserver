import unittest
import struct
import asyncio
from typing import List, Dict, Any

from server.network import PacketWriter, PacketReader
from server.sustenance_system import GLOBAL_SUSTENANCE_MANAGER
from server.minigames_system import GLOBAL_LUCKY_DRAW
import server.handlers.handle_23_items as handle_23
import server.handlers.handle_104_minigame as handle_104


class MockServer:
    def __init__(self):
        self.sessions = {}
        self.items = {}
        self.map_ground_items = {}

    def save_player_to_db(self, player):
        pass

    def broadcast_to_map(self, map_id, packet, exclude_session=None):
        pass

    def build_inventory_packet(self, player):
        return PacketWriter().write_8(23).write_8(2).write_8(len(player.inventory))


class MockSession:
    def __init__(self, char_name="TestHero", char_id=1001):
        self.char_name = char_name
        self.char_id = char_id
        self.map_id = 10001
        self.hp = 100
        self.max_hp = 300
        self.sp = 50
        self.max_sp = 200
        self.gold = 50000
        self.sustenance_hp = 5000
        self.sustenance_sp = 3000
        self.im_tokens = 0
        self.inventory: List[Dict[str, Any]] = []
        self.equipments = [0] * 6
        self.pets: List[Dict[str, Any]] = [
            {
                "id": 12001,
                "name": "TestPet",
                "hp": 80,
                "max_hp": 250,
                "sp": 30,
                "max_sp": 150,
            }
        ]
        self.sent_packets: List[bytes] = []

    async def send_packet(self, packet: PacketWriter):
        self.sent_packets.append(packet.to_bytes())


class TestHpMpAndLuckyDraw(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.server = MockServer()
        self.session = MockSession()
        self.server.sessions[self.session.char_id] = self.session

    async def test_hp_autofill_player(self):
        """Tests clicking HP auto-fill button (AC 23 Sub 15, stat_type=8, slot=0)."""
        self.session.hp = 120
        self.session.max_hp = 300
        self.session.sustenance_hp = 500

        # Build client packet: [23, 15, stat_type=8, target_type=1, slot=0 (2 bytes LE)]
        pkt = PacketWriter().write_8(15).write_8(8).write_8(1).write_16(0)
        reader = PacketReader(pkt.to_bytes())

        await handle_23.handle(self.server, self.session, reader)

        # Needed HP was 180. Sustenance was 500.
        self.assertEqual(self.session.hp, 300)
        self.assertEqual(self.session.sustenance_hp, 320)

        # Verify AC 8 Sub 1 HP update: [8, 1, 0x19, 0x01, hp (4B LE)]
        ac8_pkts = [p for p in self.session.sent_packets if p[0] == 8 and p[1] == 1]
        self.assertTrue(len(ac8_pkts) > 0)
        stat_id = struct.unpack_from('<H', ac8_pkts[0], 2)[0]
        stat_val = struct.unpack_from('<I', ac8_pkts[0], 4)[0]
        self.assertEqual(stat_id, 0x0119)
        self.assertEqual(stat_val, 300)

        # Verify AC 23 Sub 208 Sustenance update: [23, 208, 1, 8, rem (4B LE)]
        ac23_208_pkts = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 208]
        self.assertTrue(len(ac23_208_pkts) > 0)
        rem_pool = struct.unpack_from('<I', ac23_208_pkts[0], 4)[0]
        self.assertEqual(rem_pool, 320)

    async def test_sp_autofill_player(self):
        """Tests clicking SP auto-fill button (AC 23 Sub 15, stat_type=9, slot=0)."""
        self.session.sp = 40
        self.session.max_sp = 200
        self.session.sustenance_sp = 250

        # Build client packet: [23, 15, stat_type=9, target_type=1, slot=0 (2 bytes LE)]
        pkt = PacketWriter().write_8(15).write_8(9).write_8(1).write_16(0)
        reader = PacketReader(pkt.to_bytes())

        await handle_23.handle(self.server, self.session, reader)

        # Needed SP was 160. Sustenance was 250.
        self.assertEqual(self.session.sp, 200)
        self.assertEqual(self.session.sustenance_sp, 90)

        # Verify AC 8 Sub 1 SP update: [8, 1, 0x1a, 0x01, sp (4B LE)]
        ac8_pkts = [p for p in self.session.sent_packets if p[0] == 8 and p[1] == 1]
        self.assertTrue(len(ac8_pkts) > 0)
        stat_id = struct.unpack_from('<H', ac8_pkts[0], 2)[0]
        stat_val = struct.unpack_from('<I', ac8_pkts[0], 4)[0]
        self.assertEqual(stat_id, 0x011a)
        self.assertEqual(stat_val, 200)

        # Verify AC 23 Sub 208: [23, 208, 1, 9, rem (4B LE)]
        ac23_208_pkts = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 208]
        self.assertTrue(len(ac23_208_pkts) > 0)
        rem_pool = struct.unpack_from('<I', ac23_208_pkts[0], 4)[0]
        self.assertEqual(rem_pool, 90)

    async def test_pet_hp_and_sp_autofill(self):
        """Tests clicking pet quick fill (AC 23 Sub 15, slot=1)."""
        pet = self.session.pets[0]
        pet["hp"] = 100
        pet["max_hp"] = 250
        pet["sp"] = 50
        pet["max_sp"] = 150
        self.session.sustenance_hp = 1000
        self.session.sustenance_sp = 1000

        # Pet HP fill
        pkt_hp = PacketWriter().write_8(15).write_8(8).write_8(1).write_16(1)
        await handle_23.handle(self.server, self.session, PacketReader(pkt_hp.to_bytes()))
        self.assertEqual(pet["hp"], 250)
        self.assertEqual(self.session.sustenance_hp, 850)

        # Verify AC 8 Sub 2 pet packet: [8, 2, 4, 1, 0, 0x19, 0x01, hp (4B)]
        ac8_pet_pkts = [p for p in self.session.sent_packets if p[0] == 8 and p[1] == 2]
        self.assertTrue(len(ac8_pet_pkts) > 0)
        self.assertEqual(ac8_pet_pkts[0][3], 1)  # slot 1

        # Pet SP fill
        pkt_sp = PacketWriter().write_8(15).write_8(9).write_8(1).write_16(1)
        await handle_23.handle(self.server, self.session, PacketReader(pkt_sp.to_bytes()))
        self.assertEqual(pet["sp"], 150)
        self.assertEqual(self.session.sustenance_sp, 900)

    async def test_use_rice_ball_syncs_ac23_sub208(self):
        """Tests that consuming a sustenance rice ball syncs AC 23 Sub 208 for both HP and SP pools."""
        self.session.inventory.append({"slot": 1, "item_id": 30025, "count": 1})
        self.session.sustenance_hp = 100
        self.session.sustenance_sp = 100

        ok = await GLOBAL_SUSTENANCE_MANAGER.use_sustenance_item(self.server, self.session, 1, 30025)
        self.assertTrue(ok)
        self.assertGreater(self.session.sustenance_hp, 100)

        # Verify AC 23 Sub 208 was sent for both 8 (HP) and 9 (SP)
        sus_pkts = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 208]
        self.assertTrue(len(sus_pkts) >= 2)
        stat_types = [p[3] for p in sus_pkts]
        self.assertIn(8, stat_types)
        self.assertIn(9, stat_types)

    async def test_lucky_draw_authentic_packets(self):
        """Tests authentic wheel spin generating AC 104 Sub 1 stop packet and AC 23 Sub 6 item delivery."""
        self.session.gold = 50000
        prize = await GLOBAL_LUCKY_DRAW.spin_wheel(self.server, self.session)
        self.assertIsNotNone(prize)

        # 1. Authentic Stop Packet: [104, 1, 2, category, slot_index] (5 bytes)
        stop_pkts = [p for p in self.session.sent_packets if p[0] == 104 and p[1] == 1]
        self.assertTrue(len(stop_pkts) > 0)
        self.assertEqual(len(stop_pkts[0]), 5)
        self.assertEqual(stop_pkts[0][2], 2)
        self.assertEqual(stop_pkts[0][3], prize["category"])
        self.assertEqual(stop_pkts[0][4], prize["slot_index"])

        # 2. Authentic Item Delivery: [23, 6, item_id (2B), count (2B), 27 zero bytes] (33 bytes)
        item_pkts = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 6]
        self.assertTrue(len(item_pkts) > 0)
        self.assertEqual(len(item_pkts[0]), 33)
        delivered_id = struct.unpack_from('<H', item_pkts[0], 2)[0]
        delivered_count = struct.unpack_from('<H', item_pkts[0], 4)[0]
        self.assertEqual(delivered_id, prize["item_id"])
        self.assertEqual(delivered_count, prize["count"])

    async def test_lucky_draw_inventory_full(self):
        """Tests that Lucky Draw blocks spin when inventory is full (50 slots)."""
        for i in range(1, 51):
            self.session.inventory.append({"slot": i, "item_id": 27001, "count": 1})

        res = await GLOBAL_LUCKY_DRAW.spin_wheel(self.server, self.session)
        self.assertIsNone(res)

        # Check error message received
        msg_pkts = [p for p in self.session.sent_packets if p[0] == 23 and p[1] == 57]
        self.assertTrue(len(msg_pkts) > 0)
        self.assertIn(b"Inventory full", msg_pkts[0])


if __name__ == '__main__':
    unittest.main()
