import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(0, '.')

from server.network import PacketWriter, PacketReader
from server.gameserver import PlayerSession, remove_item_from_inventory, add_item_to_inventory
from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
from server.npc_manager import GLOBAL_NPC_MANAGER


class MockServer:
    def __init__(self):
        GLOBAL_NPC_MANAGER.load_npcs_from_eve("data/eve.Emg")
        self.map_npcs = GLOBAL_NPC_MANAGER.map_npcs
        self.items = {"30002": "Luxury Cruise Ticket", "30028": "Pig Food"}

    def get_item_name(self, item_id):
        return self.items.get(str(item_id), f"Item #{item_id}")

    def build_inventory_packet(self, session):
        return PacketWriter().write_8(23).write_8(5)

    def save_player_to_db(self, session):
        pass


class TestItemConditionVerification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = MockServer()
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        self.session = PlayerSession(None, mock_writer)
        self.session.char_id = 777
        self.session.char_name = "TestPlayer"
        self.session.map_id = 10002
        self.session.level = 10
        self.session.inventory = []
        self.session.quests = {}
        self.sent_packets = []

        async def mock_send(pkt):
            self.sent_packets.append(bytes(pkt.buffer))
        self.session.send_packet = mock_send

    def test_remove_item_from_inventory_partial_and_full(self):
        """Verifies remove_item_from_inventory properly decrements stacked items and removes depleted slots."""
        self.session.inventory = [
            {"slot": 1, "item_id": 30002, "amount": 3, "damage": 0},
            {"slot": 2, "item_id": 30028, "amount": 1, "damage": 0},
        ]
        # Remove 1 of 30002 -> remaining 2 in slot 1
        res = remove_item_from_inventory(self.session, 30002, 1)
        self.assertTrue(res)
        self.assertEqual(len(self.session.inventory), 2)
        slot1 = next(it for it in self.session.inventory if it["slot"] == 1)
        self.assertEqual(slot1["amount"], 2)

        # Remove entire 30028 -> slot 2 removed
        res2 = remove_item_from_inventory(self.session, 30028, 1)
        self.assertTrue(res2)
        self.assertEqual(len(self.session.inventory), 1)
        self.assertFalse(any(it["item_id"] == 30028 for it in self.session.inventory))

        # Attempt to remove non-existent item -> returns False
        res3 = remove_item_from_inventory(self.session, 99999, 1)
        self.assertFalse(res3)

    async def test_item_condition_natasha_without_ticket(self):
        """Without ticket 30002, Natasha (Map 10002 Event 4) should select Sub 5 (MustHave: False)."""
        ev = GLOBAL_EVE_INTERPRETER.map_events.get(10002, {}).get(4)
        self.assertIsNotNone(ev)

        # Quest in progress, but no ticket in inventory
        self.session.quests = {"50030": 1}
        self.session.inventory = []
        selected = GLOBAL_EVE_INTERPRETER.select_matching_branch(self.session, ev)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.get("sub_idx"), 5)

    async def test_item_condition_natasha_with_ticket(self):
        """With ticket 30002 in inventory, Natasha should select Sub 6 (MustHave: True)."""
        ev = GLOBAL_EVE_INTERPRETER.map_events.get(10002, {}).get(4)
        self.assertIsNotNone(ev)

        # Quest in progress, ticket 30002 present in inventory
        self.session.quests = {"50030": 1}
        self.session.inventory = [
            {"slot": 1, "item_id": 30002, "amount": 1, "damage": 0}
        ]
        selected = GLOBAL_EVE_INTERPRETER.select_matching_branch(self.session, ev)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.get("sub_idx"), 6)


if __name__ == "__main__":
    unittest.main()
