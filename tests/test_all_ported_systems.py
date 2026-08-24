"""
Comprehensive Test Suite for All 9 Ported Wonderland Online Systems:
1. Advanced Battle Engine (Combos, Status Effects, AOE, Drops, 12 Palaces)
2. Secure P2P Trading & Player Street Stalls
3. In-Game Mailbox & Attachment System
4. Guild System & Guild Storage
5. Marriage & Couple System
6. Vehicles, Mounts & Sea Voyage
7. Rebirth & 6 Advanced Job Classes
8. Pet Amity, Death Penalty & Pet Rebirth
9. Mini-Games, Lucky Draw & Gobang
"""

import os
import tempfile
import unittest
from server.network import PacketWriter
from server.battle_engine import (
    GLOBAL_BATTLE_ENGINE,
    BattleUnit,
    BattleStatusType,
    AOETargetPattern,
)
from server.trade_system import TradeSystem, TradeOfferItem
from server.stall_system import StallManager, StallItem
from server.mail_system import MailSystem
from server.guild_system import GuildManager, GuildMemberRank
from server.marriage_system import MarriageManager
from server.vehicle_system import VehicleManager, VehicleType
from server.reborn_system import RebornManager, RebornJob
from server.pet_amity_system import PetAmityManager
from server.minigames_system import LuckyDrawManager, GobangManager


class MockSession:
    def __init__(self, char_id=1, char_name="Player", level=30, gold=100000):
        self.char_id = char_id
        self.char_name = char_name
        self.level = level
        self.gold = gold
        self.exp = 0
        self.map_id = 10001
        self.x = 500
        self.y = 500
        self.reborn = False
        self.job = 0
        self.element = 2  # Fire
        self.inventory = []
        self.pets = []
        self.active_vehicle_id = 0
        self.im_tokens = 5
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


class TestAllPortedSystems(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.server = MockServer()
        self.p1 = MockSession(char_id=101, char_name="HeroOne", level=100, gold=500000)
        self.p2 = MockSession(char_id=102, char_name="HeroTwo", level=100, gold=500000)
        self.server.sessions[101] = self.p1
        self.server.sessions[102] = self.p2

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass

    # --- 1. Battle Engine ---
    def test_battle_engine_damage_and_combo(self):
        u1 = BattleUnit(0, 101, "HeroOne", True, False, 50, 2, 1000, 1000, 200, 200, 300, 150, 100, 100, 100)
        u2 = BattleUnit(1, 102, "HeroTwo", True, False, 50, 2, 1000, 1000, 200, 200, 300, 150, 100, 100, 110)
        enemy = BattleUnit(0, 201, "WindMonster", False, False, 50, 3, 2000, 2000, 100, 100, 200, 100, 50, 50, 80)

        # Damage calculation with Fire vs Wind advantage
        dmg, is_crit, has_adv = GLOBAL_BATTLE_ENGINE.calculate_damage(u1, enemy)
        self.assertGreater(dmg, 100)
        self.assertTrue(has_adv)

        # Combo calculation (SPD delta: 110 - 100 = 10 <= 25)
        has_combo, mult = GLOBAL_BATTLE_ENGINE.calculate_combo([u1, u2])
        self.assertTrue(has_combo)
        self.assertGreater(mult, 1.0)

        # Status effect application and turn ticks
        GLOBAL_BATTLE_ENGINE.apply_status_effect(enemy, BattleStatusType.FREEZE, duration_turns=2)
        self.assertTrue(enemy.is_sealed)
        GLOBAL_BATTLE_ENGINE.process_turn_statuses(enemy)
        self.assertEqual(enemy.statuses[BattleStatusType.FREEZE], 1)

        # AOE Target calculations
        cross_targets = GLOBAL_BATTLE_ENGINE.get_aoe_target_positions(1, AOETargetPattern.CROSS)
        self.assertIn(1, cross_targets)

    # --- 2. P2P Trade & Stalls ---
    async def test_trade_and_stall_system(self):
        trade_sys = TradeSystem()
        await trade_sys.request_trade(self.p1, self.p2)
        await trade_sys.accept_trade(self.server, self.p2)

        # P1 offers an item and gold
        self.p1.inventory.append({"item_id": 27001, "amount": 5, "slot": 1})
        await trade_sys.add_item_to_trade(self.p1, slot=1, item_id=27001, count=2)
        await trade_sys.set_gold(self.p1, 5000)

        await trade_sys.lock_trade(self.p1)
        await trade_sys.lock_trade(self.p2)

        await trade_sys.confirm_trade(self.server, self.p1)
        await trade_sys.confirm_trade(self.server, self.p2)

        # Verify gold & item exchange
        self.assertEqual(self.p1.gold, 495000)
        self.assertEqual(self.p2.gold, 505000)
        p2_items = [it for it in self.p2.inventory if it.get("item_id") == 27001]
        self.assertEqual(len(p2_items), 1)
        self.assertEqual(p2_items[0]["amount"], 2)

        # Test Street Stall
        stall_mgr = StallManager()
        self.p1.inventory.append({"item_id": 46005, "amount": 3, "slot": 2})
        await stall_mgr.open_stall(self.server, self.p1, "Hero Shop", [StallItem(inventory_slot=2, item_id=46005, price=1000, count=2)])
        self.assertTrue(stall_mgr.is_stall_open(self.p1.char_id))

        # P2 buys 1 item
        success = await stall_mgr.buy_item(self.server, self.p2, self.p1.char_id, slot=2, count=1)
        self.assertTrue(success)
        self.assertEqual(self.p2.gold, 504000)
        self.assertEqual(self.p1.gold, 496000)

    # --- 3. Mailbox System ---
    async def test_mail_system(self):
        mail_sys = MailSystem(db_path=self.temp_db.name)
        self.p1.inventory.append({"item_id": 30014, "amount": 2, "slot": 1})

        sent = await mail_sys.send_mail(self.server, self.p1, self.p2.char_id, "Greetings", "Here is a gift", gold=2000, item_id=30014, item_count=1)
        self.assertTrue(sent)

        inbox = mail_sys.get_inbox(self.p2.char_id)
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0].subject, "Greetings")
        self.assertEqual(inbox[0].attached_gold, 2000)

        # Claim attachment
        claimed = await mail_sys.claim_attachment(self.server, self.p2, inbox[0].mail_id)
        self.assertTrue(claimed)
        self.assertEqual(self.p2.gold, 502000)

    # --- 4. Guild System ---
    async def test_guild_system(self):
        guild_mgr = GuildManager(db_path=self.temp_db.name)
        created = await guild_mgr.create_guild(self.server, self.p1, "KnightsOfWonderland")
        self.assertTrue(created)

        guild = guild_mgr.get_player_guild(self.p1.char_id)
        self.assertIsNotNone(guild)
        self.assertEqual(guild.guild_name, "KnightsOfWonderland")
        self.assertEqual(guild.member_count, 1)

        # Invite and accept P2
        await guild_mgr.invite_player(self.p1, self.p2)
        await guild_mgr.accept_invite(self.server, self.p2)
        self.assertEqual(guild.member_count, 2)
        self.assertIn(self.p2.char_id, guild.members)

    # --- 5. Marriage System ---
    async def test_marriage_system(self):
        marriage_mgr = MarriageManager(db_path=self.temp_db.name)
        proposed = await marriage_mgr.propose(self.server, self.p1, self.p2)
        self.assertTrue(proposed)

        accepted = await marriage_mgr.accept_proposal(self.server, self.p2)
        self.assertTrue(accepted)
        self.assertTrue(marriage_mgr.is_married(self.p1.char_id))
        self.assertTrue(marriage_mgr.is_married(self.p2.char_id))

        # Couple teleport
        self.p2.map_id = 15001
        self.p2.x = 800
        self.p2.y = 900
        tp_ok = await marriage_mgr.couple_teleport(self.server, self.p1)
        self.assertTrue(tp_ok)
        self.assertEqual(self.p1.map_id, 15001)

    # --- 6. Vehicle System ---
    async def test_vehicle_system(self):
        vehicle_mgr = VehicleManager()
        mounted = await vehicle_mgr.mount_vehicle(self.server, self.p1, 36003)  # Sailboat
        self.assertTrue(mounted)
        self.assertEqual(self.p1.active_vehicle_id, 36003)

        await vehicle_mgr.dismount_vehicle(self.server, self.p1)
        self.assertEqual(self.p1.active_vehicle_id, 0)

    # --- 7. Rebirth & Jobs ---
    async def test_reborn_system(self):
        reborn_mgr = RebornManager()
        self.assertTrue(reborn_mgr.can_reborn(self.p1))

        reborn_ok = await reborn_mgr.perform_reborn(self.server, self.p1, RebornJob.KILLER)
        self.assertTrue(reborn_ok)
        self.assertTrue(self.p1.reborn)
        self.assertEqual(self.p1.job, int(RebornJob.KILLER))
        self.assertEqual(self.p1.level, 1)

        # Check cape in inventory
        capes = [it for it in self.p1.inventory if it.get("item_id") == 23001]
        self.assertEqual(len(capes), 1)

    # --- 8. Pet Amity & Rebirth ---
    async def test_pet_amity_and_rebirth(self):
        pet_mgr = PetAmityManager()
        pet = {"slot": 1, "pet_id": 12032, "name": "Robinson", "level": 100, "amity": 60, "reborn": 0, "str": 20, "con": 20, "int": 10, "wis": 10, "agi": 15}
        self.p1.pets.append(pet)

        # Death penalty
        await pet_mgr.on_pet_death(self.server, self.p1, pet_slot=1)
        self.assertEqual(pet["amity"], 58)

        # Feeding
        self.p1.inventory.append({"item_id": 30025, "amount": 2, "slot": 1})  # Rice Ball (+3)
        await pet_mgr.feed_pet(self.server, self.p1, pet_slot=1, food_item_id=30025)
        self.assertEqual(pet["amity"], 61)

        # Pet Rebirth
        reborn_ok = await pet_mgr.perform_pet_reborn(self.server, self.p1, pet_slot=1)
        self.assertTrue(reborn_ok)
        self.assertEqual(pet["reborn"], 1)
        self.assertEqual(pet["level"], 1)

    # --- 9. Mini-Games & Lucky Draw ---
    async def test_minigames_and_lucky_draw(self):
        # Lucky Draw
        ld_mgr = LuckyDrawManager()
        prize = await ld_mgr.spin_wheel(self.server, self.p1)
        self.assertIsNotNone(prize)
        self.assertEqual(self.p1.im_tokens, 4)

        # Gobang 5-in-a-row
        gobang_mgr = GobangManager()
        game = gobang_mgr.start_game(self.p1, self.p2)

        # Play moves for P1 horizontally: (0,0), (0,1), (0,2), (0,3), (0,4)
        for c in range(4):
            valid, won = game.make_move(self.p1.char_id, 0, c)
            self.assertTrue(valid)
            self.assertFalse(won)
            # P2 plays in row 1
            valid2, _ = game.make_move(self.p2.char_id, 1, c)
            self.assertTrue(valid2)

        # Winning move for P1
        valid, won = game.make_move(self.p1.char_id, 0, 4)
        self.assertTrue(valid)
        self.assertTrue(won)


if __name__ == "__main__":
    unittest.main()
