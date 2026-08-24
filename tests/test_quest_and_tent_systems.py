"""
Unit and Integration Tests for Wonderland Online Quest and Tent Systems
"""

import os
import tempfile
import unittest
from server.network import PacketWriter
from server.quests import (
    GLOBAL_QUEST_ENGINE,
    QuestEngine,
    QuestDefinition,
    QuestStep,
    QuestRequirementItem,
    QuestReward,
    QuestState,
    QuestType,
    PlayerQuest,
)
from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER, PreEventInterpreter
from server.tent import GLOBAL_TENT_MANAGER, Tent, TentItem, TentManager
from server.tent_manufacture import GLOBAL_TENT_MANUFACTURE, TentManufactureManager


class DummySession:
    def __init__(self, char_id=1, char_name="Hero"):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = 10001
        self.x = 500
        self.y = 500
        self.gold = 1000
        self.exp = 0
        self.level = 10
        self.inventory = []
        self.pets = []
        self.quests = []
        self.sent_packets = []
        self.in_tent = False

    async def send_packet(self, pkt):
        self.sent_packets.append(pkt)


class DummyServer:
    def __init__(self):
        self.broadcasted_packets = []

    def broadcast_to_map(self, map_id, pkt, exclude_session=None):
        self.broadcasted_packets.append((map_id, pkt))

    def save_player_to_db(self, session):
        pass

    async def give_exp(self, session, amount):
        session.exp += amount

    def build_inventory_packet(self, session):
        return PacketWriter().write_8(23).write_8(1)


class TestQuestSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = QuestEngine()
        self.server = DummyServer()
        self.session = DummySession()

    def test_mark_dat_parsing(self):
        """Tests that authentic Mark.dat loads into Master Quests."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mark_path = os.path.join(base_dir, "data", "Mark.dat")
        if os.path.exists(mark_path):
            self.engine.load_authentic_quests_from_mark_dat(mark_path)
            self.assertGreater(len(self.engine.all_quests), 100, "Should load authentic quests from Mark.dat")
            self.assertGreater(len(self.engine.master_quests), 50, "Should aggregate into Master Quests")

    async def test_quest_step_progression_and_rewards(self):
        """Tests multi-stage quest progression, item consumption, and reward granting."""
        # Create a sample multi-stage quest
        quest = QuestDefinition(
            quest_id=9999,
            title="Lost Artifact",
            npc_name_pattern="Villager",
            npc_template_id=10101,
            intro_dialogue="Please bring me 2 Iron Ores.",
            complete_dialogue="Thank you for the iron ores!",
            reward=QuestReward(gold=500, exp=200).add_item(21001, 1),
        )
        quest.add_step(QuestStep(
            step_index=1,
            target_npc_template_id=10101,
            target_npc_pattern="Villager",
            step_type=QuestType.ITEM_COLLECTION,
            required_items=[QuestRequirementItem(item_id=27001, amount=2, item_name="Iron Ore")],
            prompt_dialogue="Please bring me 2 Iron Ores.",
            complete_dialogue="Thank you for the iron ores!",
        ))

        self.engine.register_quest(quest)

        # 1. First interaction: start quest
        handled, text = await self.engine.try_handle_npc_quest(self.server, self.session, "Villager", 10101)
        self.assertTrue(handled)
        self.assertEqual(text, "Please bring me 2 Iron Ores.")

        p_map = self.engine.get_player_quests_dict(self.session)
        self.assertIn(9999, p_map)
        self.assertEqual(p_map[9999].state, QuestState.IN_PROGRESS)

        # 2. Second interaction without items: should not complete
        handled, text = await self.engine.try_handle_npc_quest(self.server, self.session, "Villager", 10101)
        self.assertTrue(handled)
        self.assertEqual(p_map[9999].state, QuestState.IN_PROGRESS)

        # 3. Add items to inventory and interact again: should complete & reward
        self.session.inventory.append({"item_id": 27001, "amount": 2, "slot": 1})
        handled, text = await self.engine.try_handle_npc_quest(self.server, self.session, "Villager", 10101)
        self.assertTrue(handled)
        self.assertEqual(text, "Thank you for the iron ores!")
        self.assertEqual(p_map[9999].state, QuestState.COMPLETED)
        self.assertEqual(self.session.gold, 1500)
        self.assertEqual(self.session.exp, 200)

    async def test_companion_recruitment_reward(self):
        """Tests authentic companion recruitment packet (AC 15:1) generation."""
        await self.engine.send_companion_reward(self.server, self.session, 12032, "Robinson")
        self.assertEqual(len(self.session.pets), 1)
        self.assertEqual(self.session.pets[0]["name"], "Robinson")
        self.assertEqual(self.session.pets[0]["pet_id"], 12032)
        # Check that AC 15:1 and AC 8:2 were sent
        sent_opcodes = [p.buffer[0] for p in self.session.sent_packets]
        self.assertIn(15, sent_opcodes)
        self.assertIn(8, sent_opcodes)

    def test_npc_matching_tid_and_pattern(self):
        """Tests NPC matching by template ID and name substring."""
        self.assertTrue(self.engine._is_npc_match("Ashley", 14013, "Ashley", 14013))
        self.assertTrue(self.engine._is_npc_match("Ashley", 0, "Ashley", 14013))
        self.assertTrue(self.engine._is_npc_match("Robinson", 12032, "Robinson", 0))
        self.assertTrue(self.engine._is_npc_match("Villager", 0, "Welling Villager", 14144))
        self.assertFalse(self.engine._is_npc_match("Robinson", 12032, "Ashley", 14013))


class TestTentSystem(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.tent_mgr = TentManager(db_path=self.temp_db.name)
        self.server = DummyServer()
        self.session = DummySession(char_id=42, char_name="Explorer")

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except Exception:
                pass

    def test_tent_default_items(self):
        """Tests default starter items: Coconut Basin (38027) & Low Workbench (38049)."""
        tent = self.tent_mgr.get_or_create_tent(42)
        self.assertEqual(len(tent.items), 2)
        item_ids = [it.item_id for it in tent.items]
        self.assertIn(38027, item_ids)
        self.assertIn(38049, item_ids)

    def test_furniture_placement_and_movement(self):
        """Tests furniture placement, moving, rotation, and persistence."""
        tent = self.tent_mgr.get_or_create_tent(42)
        initial_count = len(tent.items)

        # Place a bed
        tent.place_item(item_id=38100, x=30, y=30, floor=0, rotation=1)
        self.assertEqual(len(tent.items), initial_count + 1)
        self.assertEqual(tent.items[-1].item_id, 38100)
        self.assertEqual(tent.items[-1].rotate, 1)

        # Move item
        moved = tent.move_item(initial_count, x=35, y=35, floor=0, rotation=2)
        self.assertTrue(moved)
        self.assertEqual(tent.items[-1].x, 35)
        self.assertEqual(tent.items[-1].rotate, 2)

        # Save and reload from DB
        self.tent_mgr.save_tent_to_db(tent)
        reloaded_tent = self.tent_mgr.load_tent_from_db(42)
        self.assertIsNotNone(reloaded_tent)
        self.assertEqual(len(reloaded_tent.items), initial_count + 1)
        self.assertEqual(reloaded_tent.items[-1].x, 35)

    async def test_tent_open_and_send_items(self):
        """Tests entering tent and sending AC 23:3 furniture packets."""
        await self.tent_mgr.open_tent(self.server, self.session)
        self.assertTrue(self.session.in_tent)
        self.assertEqual(self.session.map_id, 12000)

        # Verify AC 12:163, AC 23:3, AC 62:7, AC 62:59 packets were dispatched
        sent_opcodes = [p.buffer[0] for p in self.session.sent_packets]
        self.assertIn(12, sent_opcodes)
        self.assertIn(23, sent_opcodes)
        self.assertIn(62, sent_opcodes)


class TestTentManufacture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mfg = TentManufactureManager()
        self.server = DummyServer()
        self.session = DummySession()

    async def test_manufacturing_recipe_execution(self):
        """Tests manufacturing material validation and crafting."""
        # Add materials for Refined Iron Ingot (Forge: 27020 x2 + 27022 x1)
        self.session.inventory.append({"item_id": 27020, "amount": 5, "slot": 1})
        self.session.inventory.append({"item_id": 27022, "amount": 2, "slot": 2})

        success = await self.mfg.manufacture(self.server, self.session, "Forge", in1=27020, c1=2, in2=27022, c2=1)
        self.assertTrue(success)

        # Verify output item 46005 added
        output_items = [it for it in self.session.inventory if it.get("item_id") == 46005]
        self.assertEqual(len(output_items), 1)


if __name__ == "__main__":
    unittest.main()
