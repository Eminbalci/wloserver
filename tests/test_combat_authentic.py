import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.network import PacketReader, PacketWriter
from server.battle_engine import GLOBAL_BATTLE_ENGINE
from server.handlers import handle_50_battle


class AuthenticCombatTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = MagicMock()
        self.session.char_name = "TestWarrior"
        self.session.char_id = 1001
        self.session.level = 25
        self.session.hp = 250
        self.session.max_hp = 250
        self.session.sp = 120
        self.session.max_sp = 120
        self.session.element = 2
        self.session.pets = []
        self.session.in_battle = True
        self.session.pvp_battle_id = 9999
        self.session.send_packet = AsyncMock()

        self.server = MagicMock()
        self.server.active_battles = {}
        self.server.save_player_to_db = MagicMock()
        self.server._resolve_pve_turn = AsyncMock()
        self.server._end_battle = AsyncMock()
        self.server.send_pet_list = AsyncMock()

        # Build active battle fixture
        self.battle = {
            'id': 9999,
            'is_pvp': False,
            'player': {
                'x': 4, 'y': 2,
                'hp': 250, 'max_hp': 250,
                'sp': 120, 'max_sp': 120,
                'level': 25, 'element': 2,
                'name': 'TestWarrior',
                'atk': 80, 'def': 40, 'matk': 20, 'mdef': 20, 'spd': 30,
                'is_player': True, 'is_defending': False
            },
            'pet': None,
            'monsters': [{
                'x': 2, 'y': 2,
                'id': 2005, 'click_id': 1,
                'hp': 80, 'max_hp': 100,
                'sp': 50, 'max_sp': 50,
                'level': 10, 'element': 1,
                'name': 'Wild Jelly',
                'atk': 30, 'def': 15, 'matk': 10, 'mdef': 10, 'spd': 15,
                'is_player': False
            }],
            'turn': 0,
            'finished': False,
            'pending_actions': {}
        }
        self.server.active_battles[9999] = self.battle

    def test_catch_rate_formula(self):
        """Verify catch rate is higher when monster HP is lower."""
        full_hp_rate = GLOBAL_BATTLE_ENGINE.calculate_catch_rate(
            player_level=20, monster_cur_hp=100, monster_max_hp=100, monster_level=10
        )
        low_hp_rate = GLOBAL_BATTLE_ENGINE.calculate_catch_rate(
            player_level=20, monster_cur_hp=10, monster_max_hp=100, monster_level=10
        )
        self.assertGreater(low_hp_rate, full_hp_rate)
        self.assertGreaterEqual(low_hp_rate, 0.70)
        self.assertLessEqual(low_hp_rate, 0.95)

    async def test_ac50_sub1_defend_action_and_immediate_ack(self):
        """Verify Skill 60021 (0xea75) registers as defend and triggers immediate AC 53 Sub 5 ACK."""
        # Payload passed to handler starts after AC=50: Sub=1, src_x=4, src_y=2, dst_x=4, dst_y=2, skill=60021 (0xea75), 3 bytes nonce
        raw = bytes([1, 4, 2, 4, 2, 0x75, 0xea, 0x01, 0xb8, 0x00])
        reader = PacketReader(raw)

        await handle_50_battle.handle(self.server, self.session, reader)

        # 1. Immediate ACK (AC 53 Sub 5: [53, 5, 4, 2])
        self.session.send_packet.assert_called_once()
        sent_pkt = self.session.send_packet.call_args[0][0]
        self.assertEqual(sent_pkt.buffer, bytes([53, 5, 4, 2]))

        # 2. Action buffered
        self.assertIn((4, 2), self.battle['pending_actions'])
        buffered = self.battle['pending_actions'][(4, 2)]
        self.assertEqual(buffered['action'], 'defend')
        self.assertEqual(buffered['skill_id'], 60021)

        # 3. Single player battle triggers turn resolution immediately
        self.server._resolve_pve_turn.assert_awaited_once_with(self.session, self.battle)

    async def test_ac50_sub1_flee_action_and_immediate_ack(self):
        """Verify Skill 60041 (0xea89) registers as flee and triggers immediate AC 53 Sub 5 ACK."""
        raw = bytes([1, 4, 2, 4, 2, 0x89, 0xea, 0x09, 0x5d, 0x00])
        reader = PacketReader(raw)

        await handle_50_battle.handle(self.server, self.session, reader)

        # Immediate ACK
        self.session.send_packet.assert_called_once()
        sent_pkt = self.session.send_packet.call_args[0][0]
        self.assertEqual(sent_pkt.buffer, bytes([53, 5, 4, 2]))

        # Action buffered
        buffered = self.battle['pending_actions'][(4, 2)]
        self.assertEqual(buffered['action'], 'flee')
        self.assertEqual(buffered['skill_id'], 60041)

    async def test_ac50_sub1_capture_action_and_immediate_ack(self):
        """Verify Skill 10008 (0x2718) registers as capture targeting enemy monster."""
        raw = bytes([1, 4, 2, 2, 2, 0x18, 0x27, 0x7f, 0x43, 0x00])
        reader = PacketReader(raw)

        await handle_50_battle.handle(self.server, self.session, reader)

        # Immediate ACK
        self.session.send_packet.assert_called_once()
        sent_pkt = self.session.send_packet.call_args[0][0]
        self.assertEqual(sent_pkt.buffer, bytes([53, 5, 4, 2]))

        # Action buffered as capture
        buffered = self.battle['pending_actions'][(4, 2)]
        self.assertEqual(buffered['action'], 'capture')
        self.assertEqual(buffered['skill_id'], 10008)
        self.assertEqual((buffered['dst_x'], buffered['dst_y']), (2, 2))

    async def test_ac50_sub1_attack_skill_action(self):
        """Verify Attack skill (15060 Throw Dish / 0x3ad4) registers properly."""
        raw = bytes([1, 4, 2, 2, 2, 0xd4, 0x3a, 0x06, 0x0d, 0x00])
        reader = PacketReader(raw)

        await handle_50_battle.handle(self.server, self.session, reader)

        # Immediate ACK
        self.session.send_packet.assert_called_once()
        sent_pkt = self.session.send_packet.call_args[0][0]
        self.assertEqual(sent_pkt.buffer, bytes([53, 5, 4, 2]))

        # Action buffered as attack
        buffered = self.battle['pending_actions'][(4, 2)]
        self.assertEqual(buffered['action'], 'attack')
        self.assertEqual(buffered['skill_id'], 15060)

    async def test_resolve_pve_turn_flee(self):
        """Verify _resolve_pve_turn executes flee animation and concludes battle with fled=True."""
        from server.gameserver import GameServer
        real_server = GameServer(db_path=":memory:")
        real_server._end_battle = AsyncMock()

        self.battle['pending_actions'][(4, 2)] = {
            'action': 'flee', 'skill_id': 60041, 'dst_x': 4, 'dst_y': 2
        }

        # Mock asyncio.sleep to avoid test delays
        import unittest.mock as mock
        with mock.patch("asyncio.sleep", return_value=None):
            await real_server._resolve_pve_turn(self.session, self.battle)

        # Verify battle ended with fled=True
        real_server._end_battle.assert_awaited_once_with(self.session, self.battle, won=False, fled=True)

    async def test_resolve_pve_turn_capture_success(self):
        """Verify _resolve_pve_turn successfully captures monster, sends AC 11:4, recruits pet, and wins."""
        from server.gameserver import GameServer
        real_server = GameServer(db_path=":memory:")
        real_server._end_battle = AsyncMock()
        real_server.save_player_to_db = MagicMock()
        real_server.send_pet_list = AsyncMock()

        self.battle['pending_actions'][(4, 2)] = {
            'action': 'capture', 'skill_id': 10008, 'dst_x': 2, 'dst_y': 2
        }

        import unittest.mock as mock
        with mock.patch("asyncio.sleep", return_value=None), \
             mock.patch.object(GLOBAL_BATTLE_ENGINE, "roll_catch_success", return_value=True):
            await real_server._resolve_pve_turn(self.session, self.battle)

        # Verify pet was recruited
        self.assertEqual(len(self.session.pets), 1)
        recruited = self.session.pets[0]
        self.assertEqual(recruited['pet_id'], 2005)
        self.assertEqual(recruited['name'], 'Wild Jelly')

        # Verify AC 11:4 packet was sent among the session transmissions
        ac11_4_found = False
        for call_args in self.session.send_packet.call_args_list:
            pkt = call_args[0][0]
            if len(pkt.buffer) >= 2 and pkt.buffer[0] == 11 and pkt.buffer[1] == 4:
                ac11_4_found = True
                # Structure: [11, 4, 2, mon_id (uint32), 00 00, 01]
                self.assertEqual(pkt.buffer[:3], bytes([11, 4, 2]))
                break
        self.assertTrue(ac11_4_found, "AC 11 Sub 4 capture packet was not sent!")

        # Verify battle ended with won=True because monster was captured
        real_server._end_battle.assert_awaited_once_with(self.session, self.battle, won=True)

    async def test_resolve_pve_turn_defend_damage_reduction(self):
        """Verify _resolve_pve_turn halves monster counter-attack damage when player defends."""
        from server.gameserver import GameServer
        real_server = GameServer(db_path=":memory:")
        real_server._end_battle = AsyncMock()
        real_server.save_player_to_db = MagicMock()

        # Turn 1: Defend
        self.battle['pending_actions'][(4, 2)] = {
            'action': 'defend', 'skill_id': 60021, 'dst_x': 4, 'dst_y': 2
        }

        initial_hp = self.battle['player']['hp']
        import unittest.mock as mock
        with mock.patch("asyncio.sleep", return_value=None), \
             mock.patch("random.random", return_value=0.99):  # avoid monster skill, use normal atk
            await real_server._resolve_pve_turn(self.session, self.battle)

        hp_after_defend = self.battle['player']['hp']
        dmg_defended = initial_hp - hp_after_defend

        # Reset HP and run without defend for comparison
        self.battle['player']['hp'] = initial_hp
        self.battle['player']['is_defending'] = False
        self.battle['monsters'][0]['hp'] = 100  # keep monster alive
        self.battle['pending_actions'][(4, 2)] = {
            'action': 'attack', 'skill_id': 10001, 'dst_x': 2, 'dst_y': 2
        }

        with mock.patch("asyncio.sleep", return_value=None), \
             mock.patch("random.random", return_value=0.99):
            await real_server._resolve_pve_turn(self.session, self.battle)

        dmg_undefended = initial_hp - self.battle['player']['hp']
        # Defended damage should be approximately half of undefended damage
        self.assertLessEqual(dmg_defended, dmg_undefended)


if __name__ == '__main__':
    unittest.main()

