"""
Wonderland Online Tent Manufacturing & Crafting Station Engine
Ported from C# wlo.pserver.core/Game/Crafting/TentManufactureManager.cs
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class ManufactureRecipe:
    workbench_name: str
    input_item1: int
    count1: int
    input_item2: int
    count2: int
    output_item: int
    output_name: str


class TentManufactureManager:
    """Manages recipes, tool validation, and material consumption for tent crafting stations."""

    def __init__(self):
        self._recipes: List[ManufactureRecipe] = []
        self._init_default_recipes()

    def _init_default_recipes(self):
        self._recipes.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            for st in ["worktable", "forge", "loom", "kitchen", "sawmill", "furnace", "anvil", "kiln", "workbench"]:
                db_recipes = GLOBAL_DYNAMIC_DATA.get_crafting_recipes_by_station(st)
                for r in db_recipes:
                    mats = r.get("required_materials", [])
                    in1 = mats[0]["item_id"] if len(mats) > 0 else 0
                    c1 = mats[0]["count"] if len(mats) > 0 else 0
                    in2 = mats[1]["item_id"] if len(mats) > 1 else 0
                    c2 = mats[1]["count"] if len(mats) > 1 else 0
                    self._recipes.append(ManufactureRecipe(
                        workbench_name=st.capitalize(),
                        input_item1=in1,
                        count1=c1,
                        input_item2=in2,
                        count2=c2,
                        output_item=r["output_item_id"],
                        output_name=r["output_name"]
                    ))
            logger.info(f"[TentManufacture] Loaded {len(self._recipes)} dynamic crafting recipes from database.")
        except Exception as e:
            logger.warning(f"[TentManufacture] Fallback crafting recipes: {e}")

        # Ensure base fallbacks if empty
        if not self._recipes:
            self._recipes.append(ManufactureRecipe("Forge", 27020, 2, 27022, 1, 46005, "Refined Iron Ingot"))
            self._recipes.append(ManufactureRecipe("Anvil", 46005, 2, 27001, 1, 21001, "Iron Longsword"))
            self._recipes.append(ManufactureRecipe("Loom", 30013, 3, 0, 0, 30014, "Fine Silk Cloth"))
            self._recipes.append(ManufactureRecipe("Low Workbench", 27001, 1, 0, 0, 47222, "Coconut Basin"))
            self._recipes.append(ManufactureRecipe("Workbench", 27001, 2, 27020, 1, 38049, "Work Platform"))

    def reload_from_db(self, dynamic_mgr=None):
        self._init_default_recipes()

    async def manufacture(
        self,
        server,
        session,
        workbench: str,
        in1: int,
        c1: int,
        in2: int = 0,
        c2: int = 0
    ) -> bool:
        """Executes a recipe at a tent crafting station."""
        if not session:
            return False

        from server.gameserver import remove_item_at_slot, add_item_to_inventory

        match: Optional[ManufactureRecipe] = None
        for r in self._recipes:
            if (r.workbench_name.lower() == workbench.lower() and
                r.input_item1 == in1 and r.count1 <= c1 and
                r.input_item2 == in2 and r.count2 <= c2):
                match = r
                break

        if not match:
            await self.send_system_msg(session, f"No valid {workbench} recipe found for these materials.")
            return False

        # Check and consume input item 1
        mat1_amt = sum(it.get("amount", 1) for it in session.inventory if it.get("item_id") == in1)
        if mat1_amt < match.count1:
            await self.send_system_msg(session, "Not enough materials for first ingredient!")
            return False

        # Check input item 2 if required
        if match.input_item2 > 0 and match.count2 > 0:
            mat2_amt = sum(it.get("amount", 1) for it in session.inventory if it.get("item_id") == in2)
            if mat2_amt < match.count2:
                await self.send_system_msg(session, "Not enough materials for second ingredient!")
                return False

        # Consume materials
        self._consume_item_by_id(session, in1, match.count1)
        if match.input_item2 > 0 and match.count2 > 0:
            self._consume_item_by_id(session, in2, match.count2)

        # Grant output item
        add_item_to_inventory(session, match.output_item, 1)

        # Broadcast crafting sparkles animation (AC 5 Sub 5)
        sparkle_pkt = PacketWriter().write_8(5).write_8(5).write_32(session.char_id).write_16(60018)
        server.broadcast_to_map(session.map_id, sparkle_pkt)

        # Refresh inventory
        await session.send_packet(server.build_inventory_packet(session))

        await self.send_system_msg(session, f"[{workbench} Manufacturing] Crafted 1x {match.output_name}!")
        logger.info(f"[TentManufacture] Player {session.char_name} crafted {match.output_name} at {workbench}.")
        return True

    def _consume_item_by_id(self, session, item_id: int, count: int):
        from server.gameserver import remove_item_at_slot
        rem = count
        for it in list(session.inventory):
            if it.get("item_id") == item_id:
                take = min(rem, it.get("amount", 1))
                slot = it.get("slot")
                if slot is not None:
                    remove_item_at_slot(session, slot, take)
                else:
                    it["amount"] = it.get("amount", 1) - take
                    if it["amount"] <= 0:
                        session.inventory.remove(it)
                rem -= take
                if rem <= 0:
                    break

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_TENT_MANUFACTURE = TentManufactureManager()
