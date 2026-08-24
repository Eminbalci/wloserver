"""
Comprehensive Test Suite for All 11 Newly Implemented Wonderland Online Subsystems:
1. AFK Gathering Engine (Mining, Woodcutting, Fishing)
2. World Map Interactive Treasure Chests & Loot Pools
3. Equipment Forging, Spar Gem Embedding & Sockets
4. Equipment Durability Decay & Spanner / NPC Repairs
5. Advanced Alchemy & Compounding Books (I-IV)
6. Auto-Recovery Sustenance & Rice Ball System
7. Player Title & Achievement Engine
8. Secondary Security PIN Lock
9. Map Weather & Environmental Atmospheric Engine
10. Multi-Stage Party Instance Dungeons
11. Netcode Security & Anti-Cheat Middleware
"""

import os
import tempfile
import unittest
from server.network import PacketWriter
from server.gathering_system import GatheringManager, GatheringType
from server.chest_system import ChestSystem
from server.forging_system import ForgingManager
from server.repair_system import EquipmentRepairManager
from server.alchemy_system import AlchemyManager
from server.sustenance_system import SustenanceManager
from server.title_system import TitleManager
from server.security_pin import SecurityPinManager
from server.weather_system import WeatherManager, WeatherType
from server.instance_system import InstanceManager
from server.anti_cheat import AntiCheatEngine


class MockSession:
    def __init__(self, char_id=1, char_name="Explorer", level=50, gold=100000):
        self.char_id = char_id
        self.char_name = char_name
        self.level = level
        self.gold = gold
        self.exp = 0
        self.hp = 1000
        self.max_hp = 1500
        self.sp = 500
        self.max_sp = 800
        self.map_id = 10001
        self.x = 500
        self.y = 500
        self.reborn = False
        self.job = 0
        self.element = 1
        self.alchemy_level = 5
        self.alchemy_exp = 0
        self.sustenance_hp = 0
        self.sustenance_sp = 0
        self.active_title_id = 0
        self.inventory = []
        self.equip = {}
        self.pets = []
        self.sent_packets = []

    async def send_packet(self, pkt):
        self.sent_packets.append(pkt)


class MockServer:
    def __init__(self):
        self.sessions = {}
        self.broadcasted_packets = []

    def broadcast_to_map(self, map_id, pkt, exclude_session=None):
        self.broadcasted_packets.append((map_id, pkt))

    def save_player_to_db(self, session):
        pass

    async def send_stats_update(self, session, levelup=False):
        pass

    async def send_pet_list(self, session):
        pass

    async def warp_player(self, session, dst_map, dst_x, dst_y):
        session.map_id = dst_map
        session.x = dst_x
        session.y = dst_y

    def build_inventory_packet(self, session):
        return PacketWriter().write_8(23).write_8(1)


class TestAllMissingSystemsExtended(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.server = MockServer()
        self.p1 = MockSession(char_id=301, char_name="AlphaHero", level=80, gold=500000)
        self.server.sessions[301] = self.p1

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass

    # --- 1. Gathering System ---
    async def test_gathering_system(self):
        gather_mgr = GatheringManager()
        started = await gather_mgr.start_gathering(self.server, self.p1, GatheringType.MINING)
        self.assertTrue(started)
        self.assertIn(self.p1.char_id, gather_mgr._sessions)

        # Process a manual tick
        session = gather_mgr._sessions[self.p1.char_id]
        await gather_mgr._process_tick(self.server, session)
        self.assertGreater(len(self.p1.inventory), 0)

        await gather_mgr.stop_gathering(self.p1)
        self.assertNotIn(self.p1.char_id, gather_mgr._sessions)

    # --- 2. World Treasure Chests ---
    async def test_chest_system(self):
        chest_sys = ChestSystem(db_path=self.temp_db.name)
        opened = await chest_sys.open_chest(self.server, self.p1, map_id=10001, chest_id=101)
        self.assertTrue(opened)
        self.assertTrue(chest_sys.is_chest_opened(self.p1.char_id, 10001, 101))

        # Second attempt should fail (already open)
        opened_again = await chest_sys.open_chest(self.server, self.p1, map_id=10001, chest_id=101)
        self.assertFalse(opened_again)

    # --- 3. Forging & Spar Gems ---
    async def test_forging_system(self):
        self.p1.inventory.append({"slot": 1, "item_id": 20001, "extra_atk": 0})  # Sword
        self.p1.inventory.append({"slot": 2, "item_id": 47001, "amount": 1})    # +24 ATK Spar

        forged = await ForgingManager.forge_gem(self.server, self.p1, equip_slot=1, gem_slot=2)
        self.assertTrue(forged)
        sword = next(it for it in self.p1.inventory if it.get("slot") == 1)
        self.assertEqual(sword.get("extra_atk"), 24)

    # --- 4. Durability & Repairs ---
    async def test_repair_system(self):
        self.p1.equip[1] = {"item_id": 20001, "dura": 240, "max_dura": 250}
        EquipmentRepairManager.process_combat_durability(self.p1, is_attacker=True)
        self.assertEqual(self.p1.equip[1]["dura"], 239)

        # Spanner repair
        self.p1.inventory.append({"slot": 1, "item_id": 20001, "dura": 100, "max_dura": 250})
        self.p1.inventory.append({"slot": 2, "item_id": 38030, "amount": 1})  # Spanner
        repaired = await EquipmentRepairManager.repair_item_with_spanner(self.server, self.p1, equip_slot=1, spanner_slot=2)
        self.assertTrue(repaired)
        item = next(it for it in self.p1.inventory if it.get("slot") == 1)
        self.assertEqual(item["dura"], 250)

    # --- 5. Multi-Tier Alchemy (Primary, Junior, Senior) & Books ---
    async def test_alchemy_system(self):
        alchemy_mgr = AlchemyManager()

        # Test 1: Primary Alchemy (2 slots)
        self.p1.alchemy_tier = 1  # Primary
        self.p1.inventory.append({"slot": 1, "item_id": 27001, "amount": 2})  # Wood
        self.p1.inventory.append({"slot": 2, "item_id": 27001, "amount": 2})  # Wood

        res1 = await alchemy_mgr.compound_ingredients(self.server, self.p1, ingredient_slots=[1, 2])
        self.assertIsInstance(res1, bool)

        # Test 2: Junior Alchemy (3 slots + Book II)
        self.p1.alchemy_tier = 2  # Junior
        self.p1.inventory.append({"slot": 3, "item_id": 46005, "amount": 1})  # Refined Metal
        self.p1.inventory.append({"slot": 4, "item_id": 27002, "amount": 1})  # Pine
        self.p1.inventory.append({"slot": 5, "item_id": 27023, "amount": 1})  # Silver
        self.p1.inventory.append({"slot": 6, "item_id": 30011, "amount": 1})  # Book II

        res2 = await alchemy_mgr.compound_ingredients(self.server, self.p1, ingredient_slots=[3, 4, 5], book_slot=6)
        self.assertIsInstance(res2, bool)

        # Test 3: Senior Alchemy (4 slots + Book IV)
        self.p1.alchemy_tier = 3  # Senior
        self.p1.inventory.append({"slot": 7, "item_id": 46005, "amount": 1})   # Metal
        self.p1.inventory.append({"slot": 8, "item_id": 27024, "amount": 1})   # Gold
        self.p1.inventory.append({"slot": 9, "item_id": 27023, "amount": 1})   # Silver
        self.p1.inventory.append({"slot": 10, "item_id": 27002, "amount": 1})  # Pine
        self.p1.inventory.append({"slot": 11, "item_id": 30013, "amount": 1})  # Book IV

        res3 = await alchemy_mgr.compound_ingredients(self.server, self.p1, ingredient_slots=[7, 8, 9, 10], book_slot=11)
        self.assertIsInstance(res3, bool)

    # --- 6. Sustenance & Rice Balls ---
    async def test_sustenance_system(self):
        self.p1.inventory.append({"slot": 1, "item_id": 30025, "amount": 1})  # Rice Ball (50k Pool)
        consumed = await SustenanceManager.use_sustenance_item(self.server, self.p1, slot=1, item_id=30025)
        self.assertTrue(consumed)
        self.assertEqual(self.p1.sustenance_hp, 50000)

        # Trigger auto recovery
        self.p1.hp = 1000  # max 1500 -> needs 500
        await SustenanceManager.trigger_post_battle_recovery(self.server, self.p1)
        self.assertEqual(self.p1.hp, 1500)
        self.assertEqual(self.p1.sustenance_hp, 49500)

    # --- 7. Titles & Achievements ---
    async def test_title_system(self):
        title_mgr = TitleManager(db_path=self.temp_db.name)
        unlocked = await title_mgr.unlock_title(self.server, self.p1, title_id=1)
        self.assertTrue(unlocked)
        self.assertIn(1, title_mgr.get_unlocked_titles(self.p1.char_id))

        equipped = await title_mgr.equip_title(self.server, self.p1, title_id=1)
        self.assertTrue(equipped)
        self.assertEqual(self.p1.active_title_id, 1)

    # --- 8. Security PIN ---
    async def test_security_pin(self):
        sec_mgr = SecurityPinManager(db_path=self.temp_db.name)
        set_ok = await sec_mgr.set_pin(self.p1, "123456")
        self.assertTrue(set_ok)
        self.assertTrue(sec_mgr.is_pin_set(self.p1.char_id))

        # Verify correct
        verify_ok = await sec_mgr.verify_pin(self.p1, "123456")
        self.assertTrue(verify_ok)

        # Verify wrong
        wrong_ok = await sec_mgr.verify_pin(self.p1, "654321")
        self.assertFalse(wrong_ok)

    # --- 9. Weather Engine ---
    async def test_weather_system(self):
        w_mgr = WeatherManager()
        w_type, intensity = w_mgr.get_map_weather(15000)  # Kyoto
        self.assertEqual(w_type, WeatherType.SAKURA)
        self.assertEqual(intensity, 4)
        await w_mgr.send_map_weather(self.p1, 15000)

    # --- 10. Instance Dungeons ---
    async def test_instance_system(self):
        inst_mgr = InstanceManager(db_path=self.temp_db.name)
        entered = await inst_mgr.enter_instance(self.server, self.p1, instance_id=1)
        self.assertTrue(entered)
        self.assertIn(self.p1.char_id, inst_mgr.active_instances)

        # Advance room 1 -> 2
        await inst_mgr.advance_room(self.server, self.p1)
        self.assertEqual(inst_mgr.active_instances[self.p1.char_id].current_room, 2)

        # Complete instance
        cleared = await inst_mgr.complete_instance(self.server, self.p1)
        self.assertTrue(cleared)
        self.assertFalse(inst_mgr.can_enter_today(self.p1.char_id, 1))

    # --- 11. Anti-Cheat Engine ---
    def test_anti_cheat(self):
        ac = AntiCheatEngine()
        # Packet flood check
        for _ in range(10):
            self.assertTrue(ac.check_packet_flood(self.p1.char_id))

        # Velocity check
        ac.update_position(self.p1.char_id, 100, 100)
        valid = ac.validate_movement_velocity(self.p1.char_id, 120, 120)
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
