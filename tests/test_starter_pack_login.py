import os
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from server.network import PacketWriter, PacketReader
from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER, StarterItemEntry
from server.gameserver import PlayerSession, GameServer


class TestStarterPackLogin(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        GLOBAL_STARTER_PACK_MANAGER.reload_from_db()

    def test_authentic_starter_item_definitions(self):
        """Verifies canonical starter item counts (Notepad=1, Remote Control=1, etc.)."""
        items = {entry.item_id: entry for entry in GLOBAL_STARTER_PACK_MANAGER.get_items()}
        
        # Verify Notepad is 1
        self.assertIn(34038, items, "Notepad (34038) must be in starter items.")
        self.assertEqual(items[34038].count, 1, "Notepad count must be 1, not 2.")

        # Verify Remote Control is 1
        self.assertIn(34058, items, "Remote Control (34058) must be in starter items.")
        self.assertEqual(items[34058].count, 1, "Remote Control count must be 1, not 2.")

        # Verify Bamboo Dragonfly is 1
        self.assertIn(34169, items, "Bamboo Dragonfly (34169) must be in starter items.")
        self.assertEqual(items[34169].count, 1)

        # Verify 10X Holy EXP Potion is 3
        self.assertIn(34190, items)
        self.assertEqual(items[34190].count, 3)

        # Verify Training Ticket is 5
        self.assertIn(34253, items)
        self.assertEqual(items[34253].count, 5)

        # Verify Fugu Hot Pot is 50
        self.assertIn(32176, items)
        self.assertEqual(items[32176].count, 50)

        # Verify Tao Rice Ball is 10
        self.assertIn(34014, items)
        self.assertEqual(items[34014].count, 10)

        # Verify Protective EXP Pill is 5
        self.assertIn(34026, items)
        self.assertEqual(items[34026].count, 5)

    def test_deliver_to_player_initial_inventory(self):
        """Tests that deliver_to_player grants starter items with authentic quantities."""
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        session = PlayerSession(MagicMock(), mock_writer)
        session.inventory = []

        count = GLOBAL_STARTER_PACK_MANAGER.deliver_to_player(session, send_packets=False)
        self.assertEqual(count, 8)

        inv_by_id = {item["item_id"]: item["amount"] for item in session.inventory}
        self.assertEqual(inv_by_id[34038], 1, "Notepad must have amount 1 in inventory")
        self.assertEqual(inv_by_id[34058], 1, "Remote Control must have amount 1 in inventory")
        self.assertEqual(inv_by_id[34169], 1, "Bamboo Dragonfly must have amount 1 in inventory")
        self.assertEqual(inv_by_id[34190], 3, "10X Holy EXP Potion must have amount 3 in inventory")
        self.assertEqual(inv_by_id[34253], 5, "Training Ticket must have amount 5 in inventory")
        self.assertEqual(inv_by_id[32176], 50, "Fugu Hot Pot must have amount 50 in inventory")
        self.assertEqual(inv_by_id[34014], 10, "Tao Rice Ball must have amount 10 in inventory")
        self.assertEqual(inv_by_id[34026], 5, "Protective EXP Pill must have amount 5 in inventory")

    async def test_commence_login_sends_inventory_packet_exactly_once(self):
        """
        Regression test: Verifies commence_login dispatches build_inventory_packet
        (AC 23 Sub 5) exactly ONCE to prevent client-side slot quantity doubling.
        """
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        session = PlayerSession(MagicMock(), mock_writer)
        session.char_id = 99
        session.char_name = "LoginTester"
        session.level = 1
        session.map_id = 10017
        session.x = 100
        session.y = 100
        session.inventory = []
        session.equipments = [0] * 6
        session.skills = []
        session.gold = 500

        # Deliver starter items
        GLOBAL_STARTER_PACK_MANAGER.deliver_to_player(session, send_packets=False)

        sent_packets = []
        async def mock_send(pkt):
            if isinstance(pkt, PacketWriter):
                sent_packets.append(bytes(pkt.buffer))
            elif isinstance(pkt, (bytes, bytearray)):
                sent_packets.append(bytes(pkt))
        session.send_packet = mock_send

        server = MagicMock(spec=GameServer)
        server.map_players = {}
        server.db = MagicMock()
        server.save_player_to_db = MagicMock()
        server.send_friend_list = AsyncMock()
        server.send_map_info = AsyncMock()
        server.send_ground_items = AsyncMock()
        server.send_5_3_login = AsyncMock()
        server.send_stats_update = AsyncMock()
        server.send_pet_list = AsyncMock()
        server.spawn_player_companion = AsyncMock()
        server.add_player_to_map = MagicMock()

        # Bind real implementations of packet builder methods from GameServer
        server.build_local_char_spawn = lambda s: GameServer.build_local_char_spawn(server, s)
        server.build_inventory_packet = lambda s: GameServer.build_inventory_packet(server, s)
        server.build_equipments_packet = lambda s: GameServer.build_equipments_packet(server, s)

        # Call real commence_login
        await GameServer.commence_login(server, session)

        # Count how many AC 23 Sub 5 packets were dispatched
        ac23_sub5_packets = [
            pkt for pkt in sent_packets
            if len(pkt) >= 2 and pkt[0] == 23 and pkt[1] == 5
        ]

        self.assertEqual(
            len(ac23_sub5_packets),
            1,
            f"AC 23 Sub 5 (inventory sync) must be sent exactly once during login! Sent {len(ac23_sub5_packets)} times."
        )

        # Parse the single AC 23 Sub 5 packet to verify Notepad and Remote Control counts are 1
        inv_pkt = ac23_sub5_packets[0]
        # Layout per occupied slot: [slot(uint8), item_id(uint16_le), count(uint8), damage(uint8), padding(26B)] = 31 bytes
        # Header is 2 bytes (23, 5)
        offset = 2
        slot_data = {}
        while offset + 5 <= len(inv_pkt):
            slot_idx = inv_pkt[offset]
            item_id = int.from_bytes(inv_pkt[offset+1:offset+3], "little")
            count = inv_pkt[offset+3]
            damage = inv_pkt[offset+4]
            slot_data[item_id] = count
            offset += 31

        self.assertEqual(slot_data.get(34038), 1, "Notepad amount in AC 23 Sub 5 must be 1")
        self.assertEqual(slot_data.get(34058), 1, "Remote Control amount in AC 23 Sub 5 must be 1")
        self.assertEqual(slot_data.get(34169), 1, "Bamboo Dragonfly amount in AC 23 Sub 5 must be 1")
        self.assertEqual(slot_data.get(34190), 3, "10X Holy EXP Potion amount in AC 23 Sub 5 must be 3")
        self.assertEqual(slot_data.get(34253), 5, "Training Ticket amount in AC 23 Sub 5 must be 5")
        self.assertEqual(slot_data.get(32176), 50, "Fugu Hot Pot amount in AC 23 Sub 5 must be 50")
        self.assertEqual(slot_data.get(34014), 10, "Tao Rice Ball amount in AC 23 Sub 5 must be 10")
        self.assertEqual(slot_data.get(34026), 5, "Protective EXP Pill amount in AC 23 Sub 5 must be 5")

    async def test_commence_login_fallback_delivers_and_syncs_once(self):
        """
        Verifies that for a Level 1 player missing starter items, fallback delivery
        populates starter items before sending the inventory packet exactly once.
        """
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
        session = PlayerSession(MagicMock(), mock_writer)
        session.char_id = 100
        session.char_name = "NewbieNoItems"
        session.level = 1
        session.map_id = 10017
        session.x = 100
        session.y = 100
        session.inventory = []  # No items initially
        session.equipments = [0] * 6
        session.skills = []
        session.gold = 0

        sent_packets = []
        async def mock_send(pkt):
            if isinstance(pkt, PacketWriter):
                sent_packets.append(bytes(pkt.buffer))
            elif isinstance(pkt, (bytes, bytearray)):
                sent_packets.append(bytes(pkt))
        session.send_packet = mock_send

        server = MagicMock(spec=GameServer)
        server.map_players = {}
        server.db = MagicMock()
        server.save_player_to_db = MagicMock()
        server.send_friend_list = AsyncMock()
        server.send_map_info = AsyncMock()
        server.send_ground_items = AsyncMock()
        server.send_5_3_login = AsyncMock()
        server.send_stats_update = AsyncMock()
        server.send_pet_list = AsyncMock()
        server.spawn_player_companion = AsyncMock()
        server.add_player_to_map = MagicMock()

        server.build_local_char_spawn = lambda s: GameServer.build_local_char_spawn(server, s)
        server.build_inventory_packet = lambda s: GameServer.build_inventory_packet(server, s)
        server.build_equipments_packet = lambda s: GameServer.build_equipments_packet(server, s)

        await GameServer.commence_login(server, session)

        # Fallback must have delivered starter items
        self.assertEqual(len(session.inventory), 8, "Fallback should have delivered 8 starter items.")
        server.save_player_to_db.assert_called_once_with(session)

        # AC 23 Sub 5 must be sent exactly once
        ac23_sub5_packets = [
            pkt for pkt in sent_packets
            if len(pkt) >= 2 and pkt[0] == 23 and pkt[1] == 5
        ]
        self.assertEqual(len(ac23_sub5_packets), 1, "AC 23 Sub 5 must be sent exactly once.")


if __name__ == "__main__":
    unittest.main()
