import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.network import PacketReader, PacketWriter
from server.security_pin import GLOBAL_SECURITY_PIN_MANAGER
from server.pet_ride_system import GLOBAL_PET_RIDE_MANAGER
from server.trade_system import GLOBAL_TRADE_SYSTEM
from server.handlers import handle_226_action, handle_39_quest, handle_15_companion


class DummyPlayer:
    def __init__(self, char_id=1, name="Tester", is_gm=False):
        self.char_id = char_id
        self.char_name = name
        self.map_id = 10017
        self.x = 100
        self.y = 100
        self.gold = 1000
        self.level = 100
        self.reborn = False
        self.job = 0
        self.mounted_pet_slot = 0
        self.movement_speed_mult = 1.0
        self.pets = [
            {"slot": 1, "pet_id": 11058, "name": "Shasha", "riding": False, "in_battle": False, "level": 50}
        ]
        self.pinned_quests = set()
        self.sent_packets = []

    async def send_packet(self, writer):
        if isinstance(writer, PacketWriter):
            self.sent_packets.append(writer.to_bytes())
        else:
            self.sent_packets.append(writer)


class DummyServer:
    def __init__(self):
        self.sessions = {}
        self.static_db_path = "test.db"

    def broadcast_to_map(self, map_id, packet, exclude_session=None):
        pass

    def save_player_to_db(self, player):
        pass

    async def send_pet_list(self, session):
        pass


class TestReverseEngineeredFixes(unittest.IsolatedAsyncioTestCase):

    async def test_security_pin_ac226_flow(self):
        server = DummyServer()
        player = DummyPlayer(char_id=999, name="PinHero")
        server.sessions[player.char_id] = player

        # 1. Set PIN (AC 226 Sub 1)
        writer = PacketWriter().write_8(1).write_string("123456")
        reader = PacketReader(writer.to_bytes())
        await handle_226_action.handle(server, player, reader)

        self.assertTrue(GLOBAL_SECURITY_PIN_MANAGER.is_unlocked(player.char_id))

        # 2. Verify PIN (AC 226 Sub 2)
        writer = PacketWriter().write_8(2).write_string("123456")
        reader = PacketReader(writer.to_bytes())
        await handle_226_action.handle(server, player, reader)
        self.assertTrue(GLOBAL_SECURITY_PIN_MANAGER.is_unlocked(player.char_id))

    async def test_pet_riding_and_knight_bonus(self):
        player = DummyPlayer(char_id=101, name="KnightHero")
        player.reborn = True
        player.job = 3  # Knight

        mult = GLOBAL_PET_RIDE_MANAGER.get_saddle_multiplier(38020, player=player)
        self.assertAlmostEqual(mult, 1.60, places=2)  # Base 1.40 + 0.20

    async def test_quest_hud_pin_unpin_ac39(self):
        server = DummyServer()
        player = DummyPlayer(char_id=202, name="QuestHero")
        server.sessions[player.char_id] = player

        # Pin quest #105 (AC 39 Sub 50)
        writer = PacketWriter().write_8(50).write_16(105)
        reader = PacketReader(writer.to_bytes())
        await handle_39_quest.handle(server, player, reader)
        self.assertIn(105, player.pinned_quests)

        # Unpin quest #105 (AC 39 Sub 51)
        writer = PacketWriter().write_8(51).write_16(105)
        reader = PacketReader(writer.to_bytes())
        await handle_39_quest.handle(server, player, reader)
        self.assertNotIn(105, player.pinned_quests)

    async def test_dismiss_mounted_pet_dismounts_cleanly(self):
        server = DummyServer()
        player = DummyPlayer(char_id=303, name="RiderHero")
        player.pets[0]["riding"] = True
        server.sessions[player.char_id] = player

        # Dismiss slot 1 (AC 15 Sub 2)
        writer = PacketWriter().write_8(2).write_8(1)
        reader = PacketReader(writer.to_bytes())
        await handle_15_companion.handle(server, player, reader)
        self.assertEqual(len(player.pets), 0)


if __name__ == '__main__':
    unittest.main()
