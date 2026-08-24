"""
Unit Test Suite for Dynamic Data Systems and DAT Loader Integrations:
- Hot-reloads all dynamic game data across all 18 subsystems
- Verifies binary DAT loaders (eve.Emg, Npc.dat, Talk.dat, Compound.dat, SceneData.dat)
"""

import os
import unittest
from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
from server.battle_engine import GLOBAL_BATTLE_ENGINE
from server.alchemy_system import GLOBAL_ALCHEMY_MANAGER
from server.tent_manufacture import GLOBAL_TENT_MANUFACTURE
from server.chest_system import GLOBAL_CHEST_SYSTEM
from server.gathering_system import GLOBAL_GATHERING_MANAGER
from server.forging_system import GLOBAL_FORGING_MANAGER
from server.instance_system import GLOBAL_INSTANCE_MANAGER
from server.title_system import GLOBAL_TITLE_MANAGER
from server.vehicle_system import GLOBAL_VEHICLE_MANAGER
from server.minigames_system import GLOBAL_LUCKY_DRAW
from server.pet_amity_system import GLOBAL_PET_AMITY
from server.reborn_system import GLOBAL_REBORN_MANAGER, RebornJob
from server.sustenance_system import GLOBAL_SUSTENANCE_MANAGER
from server.morph_system import GLOBAL_MORPH_MANAGER
from server.pet_ride_system import GLOBAL_PET_RIDE_MANAGER
from server.recycle_system import GLOBAL_RECYCLE_MANAGER
from server.death_system import GLOBAL_DEATH_MANAGER
from server.weather_system import GLOBAL_WEATHER_MANAGER
from server.dat_loaders import NpcDatLoader, TalkDatLoader, CompoundDatLoader, SceneDataLoader
from server.eve_loader import EveManager


class TestDynamicSystemsIntegration(unittest.TestCase):
    def test_dynamic_reload_all(self):
        """Verifies that full live reload runs across all 18 subsystems without exception."""
        GLOBAL_DYNAMIC_DATA.reload_all_dynamic_data()
        self.assertGreater(len(GLOBAL_ALCHEMY_MANAGER.recipes), 0)
        self.assertGreater(len(GLOBAL_TENT_MANUFACTURE._recipes), 0)
        self.assertGreater(len(GLOBAL_CHEST_SYSTEM.map_loot_tables), 0)
        self.assertGreater(len(GLOBAL_INSTANCE_MANAGER.TEMPLATES), 0)
        self.assertGreater(len(GLOBAL_TITLE_MANAGER.TITLES), 0)
        self.assertGreater(len(GLOBAL_VEHICLE_MANAGER._templates), 0)
        self.assertGreater(len(GLOBAL_LUCKY_DRAW.prizes), 0)
        self.assertGreater(len(GLOBAL_PET_AMITY._cached_foods), 0)
        self.assertGreater(len(GLOBAL_REBORN_MANAGER._cached_jobs), 0)
        self.assertGreater(len(GLOBAL_SUSTENANCE_MANAGER._cached_items), 0)
        self.assertGreater(len(GLOBAL_MORPH_MANAGER.MORPH_ITEMS), 0)
        self.assertGreater(len(GLOBAL_PET_RIDE_MANAGER._cached_saddles), 0)
        self.assertGreater(len(GLOBAL_RECYCLE_MANAGER._cached_materials), 0)
        self.assertGreater(len(GLOBAL_DEATH_MANAGER._cached_altars), 0)
        self.assertGreater(len(GLOBAL_WEATHER_MANAGER.map_weather), 0)

        # Test individual dynamic queries
        self.assertEqual(GLOBAL_REBORN_MANAGER.get_reborn_cape_item(RebornJob.KILLER), 23001)
        self.assertEqual(GLOBAL_SUSTENANCE_MANAGER.get_pool_amount(30025), 50000)
        self.assertEqual(GLOBAL_PET_RIDE_MANAGER.get_saddle_multiplier(38020), 1.40)
        self.assertEqual(GLOBAL_DEATH_MANAGER.get_revive_location(10001), (10010, 450, 380))

    def test_dat_loaders_exist(self):
        """Verifies binary parsers against authentic game data files."""
        if os.path.exists("data/eve.Emg"):
            em = EveManager("data/eve.Emg")
            self.assertGreater(len(em.maps), 1000)

        if os.path.exists("data/Npc.dat"):
            nl = NpcDatLoader("data/Npc.dat")
            self.assertGreater(len(nl.npcs), 1000)

        if os.path.exists("data/Talk.dat"):
            tl = TalkDatLoader("data/Talk.dat")
            self.assertGreater(len(tl.dialogues), 10000)

        if os.path.exists("data/Compound.dat"):
            cl = CompoundDatLoader("data/Compound.dat")
            self.assertGreater(len(cl.recipes), 100)

        if os.path.exists("data/SceneData.dat"):
            sl = SceneDataLoader("data/SceneData.dat")
            self.assertGreater(len(sl.map_names), 500)


if __name__ == "__main__":
    unittest.main()
