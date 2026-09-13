"""
Unit and integration tests for dynamic NPC visibility, PreEvent bytecode evaluation,
quest state transitions, and interaction filtering (AC 20 Sub 1).
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from server.network import PacketReader, PacketWriter
from server.preevent_interpreter import PreEventInterpreter, GLOBAL_PREEVENT_INTERPRETER
from server.eve_event_interpreter import get_session_quest_state, set_session_quest_state
from server.quests import QuestState, PlayerQuest, GLOBAL_QUEST_ENGINE


class MockSession:
    def __init__(self, char_id=999999, char_name="TestHero", map_id=12000, x=1560, y=1610):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = map_id
        self.x = x
        self.y = y
        self.quests = []
        self.pets = []
        self.sent_packets = []
        self._actor_visibility = {}
        self.server = None

    async def send_packet(self, pkt):
        raw = pkt.buffer if hasattr(pkt, 'buffer') else bytes(pkt)
        self.sent_packets.append(raw.hex())


class MockServer:
    def __init__(self):
        self.map_npcs = {
            12000: [
                {"click_id": 28, "npc_id": 11003, "template_id": 11003, "name": "Shiba Inu", "x": 1562, "y": 1615},
                {"click_id": 20, "npc_id": 11003, "template_id": 11003, "name": "Shiba Inu", "x": 1200, "y": 1400},
            ]
        }
        self.quest_scripts = {}

    def broadcast_to_map(self, map_id, pkt, exclude_session=None):
        pass

    def save_player_to_db(self, session):
        pass


class TestNpcVisibilityPreevent(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        GLOBAL_PREEVENT_INTERPRETER.load_preevents("data/eve.Emg")
        self.server = MockServer()
        self.session = MockSession()
        self.session.server = self.server

    async def test_session_quest_state_dict_and_list_support(self):
        s = MockSession()
        # Test list format
        set_session_quest_state(s, 13046, 1, step=1)
        self.assertEqual(get_session_quest_state(s, 13046), 1)

        set_session_quest_state(s, 13046, 2, step=2)
        self.assertEqual(get_session_quest_state(s, 13046), 2)

        # Test dict format
        s.quests = {"13046": {"state": 1, "step": 1}}
        self.assertEqual(get_session_quest_state(s, 13046), 1)

        set_session_quest_state(s, 13046, 2, step=2)
        self.assertEqual(get_session_quest_state(s, 13046), 2)

    async def test_is_npc_visible_to_player_tracking(self):
        s = MockSession()
        # Permanent dog 29 is visible by default
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 29))
        # Lost dog 28 is hidden by default when quest not started
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))

        # Explicitly show
        s._actor_visibility[28] = True
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))

        # Explicitly hide
        s._actor_visibility[28] = False
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))

    async def test_kelan_village_shiba_inu_lifecycle(self):
        """Validates the complete 3-phase lifecycle of Shiba Inu (Click 28 & 20) on Map 12000."""
        s = self.session
        srv = self.server

        # --- Phase 1: No Quest Started ---
        s.quests = []
        s.sent_packets.clear()
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(srv, s, 12000)

        # Both Click 28 and Click 20 must be hidden
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 20))
        # Verify hide packet was sent: 22 (0x16), 10 (0x0a), click_id 28 (0x1c 0x00), ff ff
        self.assertTrue(any("160a1c00ffff" in pkt for pkt in s.sent_packets))

        # --- Phase 2: Quest 13046 In Progress (Dog lost in village) ---
        s.quests = [{"quest_id": 13046, "state": 1, "step": 1}]
        s.sent_packets.clear()
        if hasattr(s, "_player_quests_map"):
            delattr(s, "_player_quests_map")
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(srv, s, 12000)

        # Dog beside Lina (28) is hidden; Dog in village (20) is shown!
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 20))
        # Verify show packet for 20: 22, 10, click_id 20 (0x14 0x00), 00 00
        self.assertTrue(any("160a14000000" in pkt for pkt in s.sent_packets))

        # --- Phase 3: Quest 13046 Completed (Dog returned to Lina) ---
        s.quests = [{"quest_id": 13046, "state": 2, "step": 2}, {"quest_id": 13047, "state": 1, "step": 1}]
        s.sent_packets.clear()
        if hasattr(s, "_player_quests_map"):
            delattr(s, "_player_quests_map")
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(srv, s, 12000)

        # Dog beside Lina (28) is shown; Dog in village (20) is hidden!
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 20))
        self.assertTrue(any("160a1c000000" in pkt for pkt in s.sent_packets))
        self.assertTrue(any("160a1400ffff" in pkt for pkt in s.sent_packets))

    async def test_interaction_blocking_on_hidden_npc(self):
        """Verifies that handle_20_interaction blocks click attempts on hidden NPCs."""
        from server.handlers.handle_20_interaction import handle
        s = self.session
        srv = self.server
        s._actor_visibility[28] = False  # Shiba Inu hidden

        # Simulate client click packet on Click 28: AC 20 Sub 1
        reader = PacketReader(bytes([1, 0, 0, 0, 28]))
        s.sent_packets.clear()

        await handle(srv, s, reader)

        # Interaction must be blocked: hide confirmation packet and unlock client lock packet sent
        # 22 10 28 00 ff ff -> 160a1c00ffff
        # 20 8 -> 1408
        self.assertTrue(any("160a1c00ffff" in pkt for pkt in s.sent_packets))
        self.assertTrue(any("1408" in pkt for pkt in s.sent_packets))

    async def test_get_player_preevent_state_lifecycle_mapping(self):
        """Verifies PreEvent bytecode quest state mapping: 0=NotStarted, 1=InProgress, 2=Completed."""
        s = MockSession()
        # Unstarted quest defaults to 0
        self.assertEqual(GLOBAL_PREEVENT_INTERPRETER._get_player_preevent_state(s, 13046), 0)
        self.assertEqual(GLOBAL_PREEVENT_INTERPRETER._get_player_preevent_state(s, 12020), 0)
        self.assertEqual(GLOBAL_PREEVENT_INTERPRETER._get_player_preevent_state(s, 13098), 0)

        # InProgress quest maps to 1
        s.quests = [{"quest_id": 13046, "state": 1, "step": 1}]
        self.assertEqual(GLOBAL_PREEVENT_INTERPRETER._get_player_preevent_state(s, 13046), 1)

        # Completed quest maps to 2
        s.quests = [{"quest_id": 13046, "state": 2, "step": 2}]
        self.assertEqual(GLOBAL_PREEVENT_INTERPRETER._get_player_preevent_state(s, 13046), 2)

    async def test_fresh_player_native_preevent_hiding(self):
        """
        Verifies that a fresh player entering Map 12000 has all staged quest NPCs hidden
        natively via eve.Emg PreEvent bytecode without needing database fallback rules.
        """
        s = MockSession()
        s.quests = []
        s.sent_packets.clear()

        # Run evaluate_map_preevents directly
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)

        # All staged NPCs on Map 12000 must be hidden natively
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 14))  # Pig 14 (Q12020)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 15))  # Pig 15 (Q12020)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 16))  # Pig 16 (Q13020)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 20))  # Dog 20 (Q13046)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 28))  # Dog 28 (Q13046)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 33))  # Father's Statue 33 (Q13098)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 35))  # Iron Sword 35 (Q13098)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 36))  # Grave Roca 36 (Q13052)

    async def test_quest_completion_unhides_preevent_actors(self):
        """
        Verifies that completing a quest (e.g. Q12020 or Q13098) correctly unhides its actors
        via eve.Emg PreEvent completion branches (0 action chunks).
        """
        s = MockSession()
        # First, simulate entering map as fresh player (staged entities hidden)
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 14))
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 33))

        # During Step 1: Pig 15 is loose (visible), Pig 14 in pen is hidden
        s.quests = [{"quest_id": 12020, "state": 1, "step": 1}]
        s.sent_packets.clear()
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 14))
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 15))

        # Now complete Quest 12020 (flag 12021 = 1)
        s.quests = [{"quest_id": 12020, "state": 2, "step": 2}, {"quest_id": 12021, "state": 1, "step": 1}]
        s.sent_packets.clear()
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)

        # Pig 14 (returned to pen) must now be unhidden (visible), Pig 15 (loose) is hidden
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 14))
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 15))

    async def test_roca_visibility_map_12000_and_submaps(self):
        """
        Verifies that Roca NEVER appears in the Kelan Village outdoor square (Map 12000, Click 32),
        is only visible at the grave (Click 34) during the mourning quest,
        and IS VISIBLE in the Chief's House (Map 12001, Click 2) until recruited.
        """
        s = MockSession()

        # 1. Fresh player on Map 12000 (Village outdoors)
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 32))  # Village Roca: NEVER visible
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 34))  # Grave mourning Roca: hidden
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 36))  # Grave standing Roca: hidden

        # 2. Fresh player enters Map 12001 (Chief's House)
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12001)
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12001, 2))    # Roca in Chief's house: VISIBLE
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12001, 3))   # Staged copy: hidden

        # 3. Quest 13052 in progress (Death of Roca's Father mourning cutscene)
        s.quests = [{"quest_id": 13052, "state": 1, "step": 1}]
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 32))  # Still hidden outdoors
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 34))   # Mourning at grave: VISIBLE
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 36))  # Standing copy: hidden

        # 4. Player recruits Roca into party (either as pet or completing recruitment quest)
        s.quests = [{"quest_id": 13052, "state": 2, "step": 2}, {"quest_id": 13098, "state": 1, "step": 1}]
        s.pets = [{"pet_id": 14162, "name": "Roca"}]
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12000)
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(s, 12001)

        # Both village and house copies must now be hidden
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 32))  # Village: hidden
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12000, 34))  # Grave: hidden
        self.assertFalse(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 12001, 2))   # Chief's house: hidden (recruited)



if __name__ == "__main__":
    unittest.main()
