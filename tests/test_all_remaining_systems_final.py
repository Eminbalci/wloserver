"""
Comprehensive Final Test Suite for All Remaining Wonderland Online Subsystems:
1. PvP Duel, Arena & PK Engine (AC 11, AC 32)
2. Transformation & Monster Disguise Morphs (AC 21:10)
3. Barber, Hair Styling & Color Dyeing (AC 21:1/2)
4. Bank Vault & Inventory Expansion (AC 13:10, AC 34)
5. Pet Riding & Mount Speed Engine (AC 82, AC 85)
6. Item Recycle & Smelting Furnace (AC 64:10)
7. Death Penalty, Ghost State & Revive Altar Points
8. Character Deletion with Security Delete Code (AC 35)
9. Scheduled Server Events & Double EXP Engine
10. Comprehensive GM Command Suite (:item, :gold, :warp, etc.)
"""

import os
import tempfile
import unittest
from server.network import PacketWriter, PacketReader
from server.pvp_system import PvPManager
from server.morph_system import MorphManager
from server.barber_system import BarberManager
from server.bank_system import BankManager
from server.pet_ride_system import PetRideManager
from server.recycle_system import RecycleManager
from server.death_system import DeathManager
from server.events_system import EventManager
from server.gm_commands import GmCommandProcessor


class MockSession:
    def __init__(self, char_id=1, char_name="HeroTester", level=50, gold=100000):
        self.char_id = char_id
        self.char_name = char_name
        self.user_id = 1
        self.username = "testuser"
        self.level = level
        self.gold = gold
        self.exp = 10000
        self.hp = 1500
        self.max_hp = 1500
        self.sp = 800
        self.max_sp = 800
        self.map_id = 10001
        self.x = 500
        self.y = 500
        self.hair_style = 1
        self.hair_color = 0
        self.body_dye = 0
        self.is_gm = True
        self.movement_speed_mult = 1.0
        self.max_inventory_slots = 25
        self.inventory = []
        self.equip = {}
        self.pets = []
        self.sent_packets = []

    async def send_packet(self, pkt):
        self.sent_packets.append(pkt)

    def send_packet_sync(self, pkt):
        self.sent_packets.append(pkt)

    def close(self):
        pass


class MockServer:
    def __init__(self, db_path="wlo_server.db"):
        self.sessions = {}
        self.broadcasted_packets = []
        self.db = type("DB", (), {"db_name": db_path})()

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


class TestAllRemainingSystemsFinal(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.server = MockServer(db_path=self.temp_db.name)
        self.p1 = MockSession(char_id=501, char_name="Duelist1", level=60, gold=200000)
        self.p2 = MockSession(char_id=502, char_name="Duelist2", level=60, gold=200000)
        self.server.sessions[501] = self.p1
        self.server.sessions[502] = self.p2

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass

    # --- 1. PvP Duel & PK Engine ---
    async def test_pvp_system(self):
        pvp_mgr = PvPManager()
        req_ok = pvp_mgr.request_duel(self.p1, self.p2)
        self.assertTrue(req_ok)

        accept_ok = await pvp_mgr.accept_duel(self.server, self.p2)
        self.assertTrue(accept_ok)

        # Toggle PK Mode
        pk_on = await pvp_mgr.toggle_pk_mode(self.server, self.p1)
        self.assertTrue(pk_on)

        # Record PK Kill & Jail check
        for _ in range(3):
            await pvp_mgr.record_pk_kill(self.server, self.p1, self.p2)
        self.assertEqual(self.p1.map_id, PvPManager.JAIL_MAP_ID)

    # --- 2. Transformation & Morphs ---
    async def test_morph_system(self):
        morph_mgr = MorphManager()
        transformed = await morph_mgr.transform_player(self.server, self.p1, item_id=41001)  # Green Jelly
        self.assertTrue(transformed)
        self.assertTrue(morph_mgr.is_morphed(self.p1.char_id))
        self.assertEqual(morph_mgr.get_morph_npc_id(self.p1.char_id), 1001)

        await morph_mgr.untransform_player(self.server, self.p1)
        self.assertFalse(morph_mgr.is_morphed(self.p1.char_id))

    # --- 3. Barber & Dyeing ---
    async def test_barber_system(self):
        styled = await BarberManager.change_hair_style(self.server, self.p1, new_style=5, new_color=0x1F)
        self.assertTrue(styled)
        self.assertEqual(self.p1.hair_style, 5)
        self.assertEqual(self.p1.hair_color, 0x1F)

        # Clothing Dye
        self.p1.inventory.append({"slot": 1, "item_id": 38040, "amount": 1})
        dyed = await BarberManager.dye_clothing(self.server, self.p1, dye_slot=1, clothing_color=0xFF)
        self.assertTrue(dyed)
        self.assertEqual(self.p1.body_dye, 0xFF)

    # --- 4. Bank Vault & Expansion ---
    async def test_bank_system(self):
        bank_mgr = BankManager(db_path=self.temp_db.name)
        dep_ok = await bank_mgr.deposit_gold(self.server, self.p1, amount=50000)
        self.assertTrue(dep_ok)
        self.assertEqual(bank_mgr.get_bank_gold(self.p1.char_id), 50000)
        self.assertEqual(self.p1.gold, 150000)  # 200000 - 50000

        with_ok = await bank_mgr.withdraw_gold(self.server, self.p1, amount=20000)
        self.assertTrue(with_ok)
        self.assertEqual(bank_mgr.get_bank_gold(self.p1.char_id), 30000)

        # Expand Inventory
        self.p1.inventory.append({"slot": 2, "item_id": 38001, "amount": 1})
        exp_ok = await bank_mgr.expand_inventory(self.server, self.p1, bag_slot=2)
        self.assertTrue(exp_ok)
        self.assertEqual(self.p1.max_inventory_slots, 30)

    # --- 5. Pet Riding ---
    async def test_pet_ride_system(self):
        self.p1.pets.append({"slot": 1, "pet_id": 12050, "name": "White Horse"})
        mounted = await PetRideManager.mount_companion_pet(self.server, self.p1, pet_slot=1)
        self.assertTrue(mounted)
        self.assertEqual(self.p1.movement_speed_mult, 1.40)

        await PetRideManager.dismount_companion_pet(self.server, self.p1)
        self.assertEqual(self.p1.movement_speed_mult, 1.0)

    # --- 6. Recycle & Smelting ---
    async def test_recycle_system(self):
        self.p1.inventory.append({"slot": 1, "item_id": 21001, "amount": 1})  # Bronze Sword
        smelted = await RecycleManager.smelt_equipment(self.server, self.p1, equip_slot=1)
        self.assertTrue(smelted)
        self.assertGreater(len(self.p1.inventory), 0)

    # --- 7. Death Penalty & Respawn ---
    async def test_death_system(self):
        old_exp = self.p1.exp
        await DeathManager.process_player_defeat(self.server, self.p1)
        self.assertLess(self.p1.exp, old_exp)
        self.assertEqual(self.p1.hp, 1)
        self.assertEqual(self.p1.map_id, 10010)  # Kelan Village Altar

    # --- 8. Double EXP Events ---
    async def test_events_system(self):
        event_mgr = EventManager()
        self.assertFalse(event_mgr.is_double_exp_active())
        self.assertEqual(event_mgr.get_exp_multiplier(), 1.0)

        await event_mgr.start_double_exp_event(self.server, duration_hours=1.0)
        self.assertTrue(event_mgr.is_double_exp_active())
        self.assertEqual(event_mgr.get_exp_multiplier(), 2.0)

        await event_mgr.stop_double_exp_event(self.server)
        self.assertFalse(event_mgr.is_double_exp_active())

    # --- 9. GM Commands ---
    async def test_gm_commands(self):
        # Test :gold 50000
        cmd1 = await GmCommandProcessor.process_command(self.server, self.p1, ":gold 50000")
        self.assertTrue(cmd1)

        # Test :item 27001 5
        cmd2 = await GmCommandProcessor.process_command(self.server, self.p1, ":item 27001 5")
        self.assertTrue(cmd2)

        # Test :speed 2.5
        cmd3 = await GmCommandProcessor.process_command(self.server, self.p1, ":speed 2.5")
        self.assertTrue(cmd3)
        self.assertEqual(self.p1.movement_speed_mult, 2.5)

        # Test :heal
        self.p1.hp = 100
        cmd4 = await GmCommandProcessor.process_command(self.server, self.p1, ":heal")
        self.assertTrue(cmd4)
        self.assertEqual(self.p1.hp, self.p1.max_hp)


if __name__ == "__main__":
    unittest.main()
