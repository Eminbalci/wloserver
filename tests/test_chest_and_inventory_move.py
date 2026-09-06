import asyncio
import unittest
from unittest.mock import MagicMock
import sys
sys.path.insert(0, '.')

from server.network import PacketWriter, PacketReader
from server.gameserver import PlayerSession
from server.chest_system import GLOBAL_CHEST_SYSTEM
from server.npc_manager import GLOBAL_NPC_MANAGER
from server.handlers import handle_20_interaction, handle_23_items

class MockServer:
    def __init__(self):
        GLOBAL_NPC_MANAGER.load_npcs_from_eve("data/eve.Emg")
        self.map_npcs = GLOBAL_NPC_MANAGER.map_npcs
        self.items = {"32032": "Old Sword", "41066": "Coconut"}
        self.chest_system = GLOBAL_CHEST_SYSTEM
        self.saved = False

    def save_player_to_db(self, session):
        self.saved = True

    def build_inventory_packet(self, session):
        return PacketWriter().write_8(23).write_8(5)

    def get_item_name(self, item_id):
        return self.items.get(str(item_id), f"Item #{item_id}")

    def broadcast_to_map(self, map_id, packet, exclude_session=None):
        pass

class TestChestAndInventoryMove(unittest.TestCase):
    def setUp(self):
        self.server = MockServer()
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        self.session = PlayerSession(None, mock_writer)
        self.session.char_id = 999
        self.session.char_name = "Tester"
        self.session.map_id = 10035
        self.session.x = 1042
        self.session.y = 2115
        for npc in self.server.map_npcs.get(10035, []):
            if npc.click_id == 3:
                self.session.x = npc.x
                self.session.y = npc.y
                break

        self.session.inventory = [
            {"slot": 1, "item_id": 10001, "amount": 1, "damage": 0},
            {"slot": 2, "item_id": 10002, "amount": 1, "damage": 0}
        ]
        self.sent_packets = []
        async def mock_send(pkt):
            self.sent_packets.append(bytes(pkt.buffer))
        self.session.send_packet = mock_send

    def test_inventory_move_swap(self):
        """Verifies AC 23 Sub 10 swaps items between occupied slots without losing items."""
        reader = PacketReader(bytes([10, 1, 1, 2]))
        asyncio.run(handle_23_items.handle(self.server, self.session, reader))
        self.assertEqual(len(self.session.inventory), 2)
        slot1_item = next(it for it in self.session.inventory if it['slot'] == 1)
        slot2_item = next(it for it in self.session.inventory if it['slot'] == 2)
        self.assertEqual(slot1_item['item_id'], 10002)
        self.assertEqual(slot2_item['item_id'], 10001)

    def test_inventory_move_desync_healing(self):
        """Verifies AC 23 Sub 10 sends AC 23 Sub 5 full sync if moving from empty slot."""
        self.sent_packets.clear()
        reader = PacketReader(bytes([10, 5, 1, 6]))
        asyncio.run(handle_23_items.handle(self.server, self.session, reader))
        self.assertTrue(any(p[0] == 23 and p[1] == 5 for p in self.sent_packets))

    def test_broken_chest_cannot_be_relooted(self):
        """Verifies clicking an already-opened chest sends already claimed message and yields no loot."""
        GLOBAL_CHEST_SYSTEM.record_chest_opened(self.session.char_id, 10035, 3)
        self.assertTrue(GLOBAL_CHEST_SYSTEM.is_chest_opened(self.session.char_id, 10035, 3, is_permanent=True))

        self.sent_packets.clear()
        inv_count_before = len(self.session.inventory)
        reader = PacketReader(bytes([1, 3, 0]))
        asyncio.run(handle_20_interaction.handle(self.server, self.session, reader))

        self.assertEqual(len(self.session.inventory), inv_count_before)
        self.assertTrue(any(p[0] == 23 and p[1] == 57 for p in self.sent_packets))
        self.assertTrue(any(p[0] == 20 and p[1] == 8 for p in self.sent_packets))
        self.assertTrue(any(p[0] == 5 and p[1] == 4 for p in self.sent_packets))
        self.assertFalse(any(p[0] == 23 and p[1] == 6 for p in self.sent_packets))

if __name__ == "__main__":
    unittest.main()
