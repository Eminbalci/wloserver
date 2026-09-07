"""
Unit tests for Client C Code Compliance and Constraints.
Validates multi-port configuration, static NPC template remapping,
crafting constraints, marriage gender/level rules, and equipment repair checks.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from server.network import PacketReader, PacketWriter
from server.marriage_system import MarriageManager, GLOBAL_MARRIAGE_MANAGER
from server.repair_system import EquipmentRepairManager
from server.handlers import (
    handle_64_crafting,
    handle_20_interaction,
    handle_32_emote,
    handle_8_stats,
    handle_2_chat,
    handle_25_trade,
    handle_35_char_deletion,
    handle_43_team,
    handle_57_action,
    handle_63_login,
    handle_15_companion,
    handle_183_activity,
    handle_23_items,
    handle_62_tent,
    handle_74_action,
    handle_82_marriage,
)


class MockSession:
    def __init__(self, char_id=1001, name="TestHero", level=50, body=1):
        self.char_id = char_id
        self.char_name = name
        self.level = level
        self.body = body  # 1 = male (odd)
        self.gold = 100000
        self.map_id = 10010
        self.x = 200
        self.y = 200
        self.in_battle = False
        self.bathing = False
        self.is_fishing = False
        self.is_remote_control = False
        self.team = None
        self.team_leader = None
        self.unfinished_crafts_count = 0
        self.user_id = 1
        self.username = "TestHero"
        self.cipher = ""
        self.hp = 100
        self.max_hp = 100
        self.sp = 100
        self.max_sp = 100
        self.pets = []
        self.mounted_pet_slot = 0
        self.movement_speed_mult = 1.0
        self.morph_npc_id = 0
        self.max_inventory_slots = 50
        self.title = 0
        self.ip = "127.0.0.1"
        self.skills = {}
        self.inventory = []
        self.equip = {}
        self.sent_packets = []

    async def send_packet(self, pkt):
        if isinstance(pkt, PacketWriter):
            self.sent_packets.append(pkt.to_bytes())
        else:
            self.sent_packets.append(pkt)

    def get_sent_strings(self):
        strings = []
        for p in self.sent_packets:
            try:
                # WLO text packets (AC 23 Sub 57) usually contain ASCII strings
                s = p.decode('ascii', errors='ignore')
                strings.append(s)
            except Exception:
                pass
        return strings


class TestClientCCodeCompliance(unittest.IsolatedAsyncioTestCase):

    async def test_crafting_c_code_constraints(self):
        """Tests that crafting enforces bathing, battle, team, and max 5 crafts limits."""
        server = MagicMock()
        session = MockSession()

        # 1. Bathing constraint
        session.bathing = True
        reader = PacketReader(bytes([1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]))
        await handle_64_crafting.handle(server, session, reader)
        self.assertTrue(any("Bathing, unable to make" in s for s in session.get_sent_strings()))

        # 2. In-battle constraint
        session.bathing = False
        session.in_battle = True
        session.sent_packets.clear()
        reader = PacketReader(bytes([1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]))
        await handle_64_crafting.handle(server, session, reader)
        self.assertTrue(any("Can't act in battle" in s for s in session.get_sent_strings()))

        # 3. In-team constraint
        session.in_battle = False
        session.team = [1001, 1002]
        session.sent_packets.clear()
        reader = PacketReader(bytes([1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]))
        await handle_64_crafting.handle(server, session, reader)
        self.assertTrue(any("Can't do in team" in s for s in session.get_sent_strings()))

        # 4. Max 5 unfinished crafts constraint
        session.team = None
        session.unfinished_crafts_count = 5
        session.sent_packets.clear()
        reader = PacketReader(bytes([1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0]))
        await handle_64_crafting.handle(server, session, reader)
        self.assertTrue(any("Already 5 semi-finished crafts" in s for s in session.get_sent_strings()))

    async def test_marriage_c_code_constraints(self):
        """Tests level, battle, and same-gender marriage constraints."""
        server = MagicMock()
        server.sessions = {}
        manager = MarriageManager(db_path=":memory:")

        p1 = MockSession(char_id=1, name="Romeo", level=25, body=1)  # Lv25 (< 30)
        p2 = MockSession(char_id=2, name="Juliet", level=35, body=2)  # Lv35, female (even)

        # 1. Level 30 check
        res = await manager.propose(server, p1, p2)
        self.assertFalse(res)
        self.assertTrue(any("Requires LV30 to marry" in s for s in p1.get_sent_strings()))

        # 2. Same-gender check (body 1 and body 3 are both male)
        p1.level = 35
        p3 = MockSession(char_id=3, name="Mercutio", level=35, body=3)
        p1.sent_packets.clear()
        res = await manager.propose(server, p1, p3)
        self.assertFalse(res)
        self.assertTrue(any("Can't marry same gender" in s for s in p1.get_sent_strings()))

        # 3. Valid opposite gender proposal
        p1.sent_packets.clear()
        res = await manager.propose(server, p1, p2)
        self.assertTrue(res)

    async def test_repair_c_code_constraints(self):
        """Tests battle repair block and full durability doesn't need repair block."""
        server = MagicMock()
        player = MockSession()
        player.inventory = [
            {"slot": 1, "item_id": 21001, "dura": 250, "max_dura": 250},
            {"slot": 2, "item_id": 38030, "count": 1}  # Spanner
        ]

        # 1. In battle block
        player.in_battle = True
        res = await EquipmentRepairManager.repair_item_with_spanner(server, player, equip_slot=1, spanner_slot=2)
        self.assertFalse(res)
        self.assertTrue(any("Can't fix in battle" in s for s in player.get_sent_strings()))

        # 2. Already full dura block
        player.in_battle = False
        player.sent_packets.clear()
        res = await EquipmentRepairManager.repair_item_with_spanner(server, player, equip_slot=1, spanner_slot=2)
        self.assertFalse(res)
        self.assertTrue(any("Doesn't need repair" in s for s in player.get_sent_strings()))

        # 3. Valid repair when damaged
        player.inventory[0]["dura"] = 100
        player.sent_packets.clear()
        res = await EquipmentRepairManager.repair_item_with_spanner(server, player, equip_slot=1, spanner_slot=2)
        self.assertTrue(res)
        self.assertEqual(player.inventory[0]["dura"], 250)

    def test_emote_action_codes(self):
        """Validates handle_32_emote registers ACTION_CODES = [32]."""
        self.assertEqual(handle_32_emote.ACTION_CODES, [32])
        self.assertEqual(handle_32_emote.ACTION_CODE, 32)

    async def test_stats_sub_2_refresh(self):
        """Validates AC 8 Sub 2 triggers server stats refresh."""
        session = MockSession()
        server = MagicMock()
        server.send_stats_update = AsyncMock()
        await handle_8_stats.handle(server, session, PacketReader(bytes([2])))
        server.send_stats_update.assert_called_once_with(session)

    async def test_chat_team_and_guild_subcodes(self):
        """Validates AC 2 Sub 6 (Team) and Sub 7 (Guild) chat handlers."""
        session = MockSession()
        server = MagicMock()
        server.broadcast_to_map = MagicMock()
        server.active_sessions = [session]
        # Sub 6: team chat
        pkt = PacketWriter().write_8(6).write_string_n("Team msg")
        await handle_2_chat.handle(server, session, PacketReader(pkt.to_bytes()))
        server.broadcast_to_map.assert_called()

        # Sub 7: guild chat
        session.guild_id = 99
        pkt = PacketWriter().write_8(7).write_string_n("Guild msg")
        await handle_2_chat.handle(server, session, PacketReader(pkt.to_bytes()))
        self.assertTrue(len(session.sent_packets) > 0)

    async def test_trade_c_code_subcodes(self):
        """Validates AC 25 authentic subcodes: 21 (accept), 10 (lock), 40 (confirm), 42 (cancel)."""
        session = MockSession()
        server = MagicMock()
        with patch("server.handlers.handle_25_trade.GLOBAL_TRADE_SYSTEM") as mock_trade:
            mock_trade.accept_trade = AsyncMock()
            mock_trade.lock_trade = AsyncMock()
            mock_trade.confirm_trade = AsyncMock()
            mock_trade.cancel_trade = AsyncMock()

            await handle_25_trade.handle(server, session, PacketReader(bytes([25, 21])))
            mock_trade.accept_trade.assert_called_once()

            await handle_25_trade.handle(server, session, PacketReader(bytes([25, 10])))
            mock_trade.lock_trade.assert_called_once()

            await handle_25_trade.handle(server, session, PacketReader(bytes([25, 40])))
            mock_trade.confirm_trade.assert_called_once()

            await handle_25_trade.handle(server, session, PacketReader(bytes([25, 42])))
            mock_trade.cancel_trade.assert_called_once()

    async def test_char_deletion_subcodes(self):
        """Validates AC 35 Sub 3 (code query) and Sub 5 (code validation)."""
        session = MockSession()
        session.cipher = "123456"
        server = MagicMock()

        # Sub 3: status query
        await handle_35_char_deletion.handle(server, session, PacketReader(bytes([3])))
        self.assertTrue(any(p.startswith(bytes([35, 3, 1])) for p in session.sent_packets))

        # Sub 5: set valid deletion code (6-10 chars)
        session.sent_packets.clear()
        conn_mock = MagicMock()
        server.db.get_connection.return_value.__enter__.return_value = conn_mock
        pkt = PacketWriter().write_8(5).write_string("654321")
        await handle_35_char_deletion.handle(server, session, PacketReader(pkt.to_bytes()))
        self.assertEqual(session.cipher, "654321")
        self.assertTrue(any(p.startswith(bytes([35, 5, 1])) for p in session.sent_packets))

    async def test_team_sub_4_leave(self):
        """Validates AC 43 Sub 4 (leave team)."""
        session = MockSession()
        server = MagicMock()
        await handle_43_team.handle(server, session, PacketReader(bytes([4])))
        self.assertTrue(any(p.startswith(bytes([43, 4])) for p in session.sent_packets))

    async def test_minigame_dismiss_subcodes(self):
        """Validates AC 57 Sub 8, 9, 10, 11 dismiss triggers ACK and unfreeze."""
        session = MockSession()
        server = MagicMock()
        for sub in (8, 9, 10, 11):
            session.sent_packets.clear()
            await handle_57_action.handle(server, session, PacketReader(bytes([sub])))
            self.assertTrue(any(p.startswith(bytes([57, sub, 1])) for p in session.sent_packets))
            self.assertTrue(any(p.startswith(bytes([5, 4])) for p in session.sent_packets))

    async def test_login_sub_3_cancel_create(self):
        """Validates AC 63 Sub 3 re-sends character slot list."""
        session = MockSession()
        server = MagicMock()
        conn_mock = MagicMock()
        conn_mock.execute.return_value.fetchone.return_value = {"id": 1, "character1_id": 0, "character2_id": 0}
        server.db.get_connection.return_value.__enter__.return_value = conn_mock
        server.db.get_character_by_id.return_value = None
        await handle_63_login.handle(server, session, PacketReader(bytes([3])))
        self.assertTrue(any(p.startswith(bytes([63, 1])) for p in session.sent_packets))

    async def test_companion_sub_9_ride_toggle(self):
        """Validates AC 15 Sub 9 toggles companion mount/ride."""
        session = MockSession()
        session.pets = [{"slot": 1, "pet_id": 1001, "name": "Npc"}]
        server = MagicMock()
        with patch("server.pet_ride_system.GLOBAL_PET_RIDE_MANAGER") as mock_ride:
            mock_ride.mount_companion_pet = AsyncMock()
            await handle_15_companion.handle(server, session, PacketReader(bytes([9, 1])))
            mock_ride.mount_companion_pet.assert_called_once()

    async def test_activity_subcodes(self):
        """Validates AC 183 Sub 7, 8, 9, 11 activity queries."""
        session = MockSession()
        server = MagicMock()
        for sub in (7, 8):
            session.sent_packets.clear()
            await handle_183_activity.handle(server, session, PacketReader(bytes([sub])))
            self.assertTrue(any(p.startswith(bytes([183, sub, 1])) for p in session.sent_packets))
        for sub in (9, 11):
            session.sent_packets.clear()
            await handle_183_activity.handle(server, session, PacketReader(bytes([sub])))
            self.assertTrue(any(p.startswith(bytes([183, sub, 0])) for p in session.sent_packets))

    async def test_items_c_code_subcodes(self):
        """Validates AC 23 Sub 31 (book), Sub 86 (expansion), Sub 128 (saddle), Sub 133 (title)."""
        session = MockSession()
        server = MagicMock()
        server.item_properties = {}
        server.broadcast_to_map = MagicMock()
        server.build_inventory_packet = MagicMock(return_value=PacketWriter().write_8(23).write_8(5))

        # Sub 31
        await handle_23_items.handle(server, session, PacketReader(bytes([31, 2])))
        self.assertEqual(session.alchemy_book_slot, 2)

        # Sub 86
        session.sent_packets.clear()
        await handle_23_items.handle(server, session, PacketReader(bytes([86, 0])))
        self.assertEqual(session.max_inventory_slots, 60)
        self.assertTrue(any(p.startswith(bytes([23, 86, 1])) for p in session.sent_packets))

        # Sub 128
        session.sent_packets.clear()
        await handle_23_items.handle(server, session, PacketReader(bytes([128, 1])))
        self.assertTrue(any(p.startswith(bytes([23, 128, 1])) for p in session.sent_packets))

        # Sub 133
        session.sent_packets.clear()
        pkt = PacketWriter().write_8(133).write_16(5)
        await handle_23_items.handle(server, session, PacketReader(pkt.to_bytes()))
        self.assertEqual(session.title, 5)
        self.assertTrue(any(p.startswith(bytes([23, 133])) for p in session.sent_packets))

    async def test_tent_subcodes(self):
        """Validates AC 62 Sub 7 styling, Sub 47 door permission."""
        session = MockSession()
        server = MagicMock()
        # Sub 7: styling
        await handle_62_tent.handle(server, session, PacketReader(bytes([7, 10, 0])))
        self.assertTrue(any(p.startswith(bytes([62, 7, 10, 0])) for p in session.sent_packets))

        # Sub 47: permission
        session.sent_packets.clear()
        await handle_62_tent.handle(server, session, PacketReader(bytes([47])))
        self.assertTrue(any(p.startswith(bytes([62, 47, 1])) for p in session.sent_packets))

    async def test_action_70_sub_7_morph_cancel(self):
        """Validates AC 70 Sub 7 triggers untransform_player."""
        session = MockSession()
        session.morph_npc_id = 1001
        server = MagicMock()
        with patch("server.morph_system.GLOBAL_MORPH_MANAGER") as mock_morph:
            mock_morph.is_morphed.return_value = True
            mock_morph.untransform_player = AsyncMock()
            reader = PacketReader(bytes([70, 7]))
            await handle_74_action.handle(server, session, reader)
            mock_morph.untransform_player.assert_called_once()
            self.assertTrue(any(p.startswith(bytes([70, 7])) for p in session.sent_packets))

    async def test_divorce_and_marriage_methods(self):
        """Validates get_spouse_id, teleport_to_spouse, and divorce with 7-day cooldown."""
        import time
        server = MagicMock()
        server.sessions = {}
        manager = MarriageManager(db_path=":memory:")

        p1 = MockSession(char_id=10, name="Romeo", level=40, body=1)
        p2 = MockSession(char_id=20, name="Juliet", level=40, body=2)
        server.sessions[10] = p1
        server.sessions[20] = p2

        # 1. Propose & Accept
        await manager.propose(server, p1, p2)
        await manager.accept_proposal(server, p2)
        self.assertTrue(manager.is_married(10))
        self.assertEqual(manager.get_spouse_id(10), 20)
        self.assertEqual(manager.get_spouse_id(20), 10)

        # 2. Divorce within 7 days is blocked
        res = await manager.divorce(server, p1)
        self.assertFalse(res)
        self.assertTrue(any("Divorced less than 7 days ago" in s for s in p1.get_sent_strings()))

        # 3. Simulate marriage older than 7 days and sufficient gold
        rec = manager.get_marriage(10)
        rec.marriage_date = time.time() - (8 * 86400)
        p1.gold = 100000
        p1.sent_packets.clear()
        res = await manager.divorce(server, p1)
        self.assertTrue(res)
        self.assertFalse(manager.is_married(10))
        self.assertTrue(any("Divorce committed" in s for s in p1.get_sent_strings()))
        self.assertTrue(any("Divorced" in s for s in p2.get_sent_strings()))

    async def test_stall_ac56(self):
        """Validates handle_25_trade handles AC 56 Stall packets."""
        session = MockSession()
        server = MagicMock()
        with patch("server.handlers.handle_25_trade.GLOBAL_STALL_MANAGER") as mock_stall:
            mock_stall.close_stall = AsyncMock()
            await handle_25_trade.handle(server, session, PacketReader(bytes([56, 2])))
            mock_stall.close_stall.assert_called_once()

    async def test_barber_npc_interaction(self):
        """Validates clicking Barber NPC opens Barber styling interface (AC 21 Sub 1)."""
        session = MockSession()
        session.map_id = 10010
        session.x = 200
        session.y = 200
        server = MagicMock()
        server.map_npcs = {
            10010: [{"id": 1001, "click_id": 5, "npc_id": 10022, "template_id": 10022, "name": "Barber Pierre", "x": 200, "y": 200}]
        }
        # AC 20 Sub 1: click NPC with click_id 5
        pkt = PacketWriter().write_8(1).write_8(5)
        await handle_20_interaction.handle(server, session, PacketReader(pkt.to_bytes()))
        self.assertTrue(any(p.startswith(bytes([21, 1])) for p in session.sent_packets))


if __name__ == "__main__":
    unittest.main()
