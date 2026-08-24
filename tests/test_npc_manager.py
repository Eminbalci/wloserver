"""
Unit tests for Wonderland Online NPC Manager and Blinking Prevention System
Direct parity verification against C# QuestNpc.cs and Map.cs
"""

import time
import unittest
from server.npc_manager import QuestNpc, NpcManager, GLOBAL_NPC_MANAGER
from server.network import PacketWriter


class TestNpcManager(unittest.TestCase):

    def test_static_prop_and_chest_filtering(self):
        """Validates that props, chests, trees, and domestic animals are strictly identified as static."""
        # Chest
        chest_npc = QuestNpc(map_id=10035, click_id=6, name="Chest", npc_id=12001, x=100, y=200)
        self.assertTrue(chest_npc.is_static_npc())
        self.assertFalse(chest_npc.is_wild_monster())

        # Village Pen Pig (TID 17400)
        pig_npc = QuestNpc(map_id=10010, click_id=15, name="Pig", npc_id=17400, x=500, y=600)
        self.assertTrue(pig_npc.is_static_npc())
        self.assertFalse(pig_npc.is_wild_monster())

        # Gathering Tree / Rock
        tree_npc = QuestNpc(map_id=11016, click_id=20, name="Pine Tree", npc_id=19100, x=400, y=800)
        self.assertTrue(tree_npc.is_static_npc())

        # Static Prop Mechanism (TID 25000+)
        mechanism = QuestNpc(map_id=12000, click_id=8, name="Switch", npc_id=26000, x=300, y=300)
        self.assertTrue(mechanism.is_static_npc())

    def test_human_npc_and_townspeople_preservation(self):
        """Validates that human villagers and companions are preserved and not classified as roaming monsters."""
        villager = QuestNpc(map_id=10010, click_id=5, name="Kelan Villager", npc_id=14013, x=1200, y=1500)
        self.assertTrue(villager.is_human_npc())
        self.assertFalse(villager.is_wild_monster())

        captain = QuestNpc(map_id=10017, click_id=10, name="Captain", npc_id=14003, x=1042, y=1075)
        self.assertTrue(captain.is_human_npc())
        self.assertFalse(captain.is_wild_monster())

        robinson = QuestNpc(map_id=10035, click_id=1, name="Robinson", npc_id=12032, x=1038, y=2235)
        self.assertTrue(robinson.is_human_npc())
        self.assertFalse(robinson.is_wild_monster())

    def test_wild_monster_identification_and_town_safeguards(self):
        """Validates roaming monsters on field maps vs town safeguards."""
        # Outdoor wild monster on field map (Map 60000 / North Island)
        field_mob = QuestNpc(map_id=60000, click_id=12, name="Wolf", npc_id=17010, x=800, y=900, walk_behavior=4)
        self.assertTrue(field_mob.is_wild_monster())
        self.assertFalse(field_mob.is_static_npc())
        self.assertFalse(QuestNpc.is_village_or_town_map(60000))

        # Monster in town/village map (Map 10010 / Kelan) should never roam
        town_mob = QuestNpc(map_id=10010, click_id=12, name="Wolf", npc_id=17010, x=800, y=900, walk_behavior=4)
        self.assertTrue(QuestNpc.is_village_or_town_map(10010))

        broadcasts = []
        def mock_broadcast(m_id, pkt):
            broadcasts.append((m_id, pkt.buffer))

        # Update town mob -> should NOT generate AC 22:2 movement broadcasts
        town_mob.next_walk_time = 0
        town_mob.update(now=time.time(), map_player_count=1, broadcast_fn=mock_broadcast)
        self.assertEqual(len(broadcasts), 0)
        self.assertGreater(town_mob.next_walk_time, time.time() + 100)

    def test_scripted_waypoint_movement(self):
        """Validates that native eve.Emg NPCs do not receive unsolicited AC 22:2 broadcasts, preserving client animation."""
        walksteps = [
            {"x": 100, "y": 200, "delay": 4000},
            {"x": 150, "y": 250, "delay": 5000}
        ]
        patrol_npc = QuestNpc(
            map_id=60000,
            click_id=30,
            name="Patrol Guard",
            npc_id=14050,
            x=100,
            y=200,
            walksteps=walksteps
        )
        patrol_npc.next_walk_time = 0

        broadcasts = []
        def mock_broadcast(m_id, pkt):
            broadcasts.append((m_id, pkt.buffer))

        patrol_npc.update(now=time.time(), map_player_count=1, broadcast_fn=mock_broadcast)
        # 0 broadcasts ensures native client animation loop runs without frame resetting / blinking
        self.assertEqual(len(broadcasts), 0)

    def test_gathering_node_respawn(self):
        """Validates gathering node broken state and AC 22:10 respawn broadcast."""
        node = QuestNpc(map_id=10035, click_id=25, name="Coconut Tree", npc_id=19050, x=500, y=500)
        node.is_broken = True
        node.respawn_time = time.time() - 1.0  # Ready to respawn

        broadcasts = []
        def mock_broadcast(m_id, pkt):
            broadcasts.append((m_id, pkt.buffer))

        node.update(now=time.time(), map_player_count=1, broadcast_fn=mock_broadcast)
        self.assertFalse(node.is_broken)
        self.assertEqual(len(broadcasts), 1)
        pkt_bytes = broadcasts[0][1]
        self.assertEqual(pkt_bytes[0], 22)
        self.assertEqual(pkt_bytes[1], 10)
        # click_id = 25 (0x19, 0x00), state = 0, 0
        self.assertEqual(pkt_bytes[2], 25)
        self.assertEqual(pkt_bytes[3], 0)
        self.assertEqual(pkt_bytes[4], 0)
        self.assertEqual(pkt_bytes[5], 0)


if __name__ == "__main__":
    unittest.main()
