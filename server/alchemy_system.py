"""
Wonderland Online Multi-Tier Alchemy Skill Engine
Supports:
1. Primary Alchemy (Skill ID: 10001, Max Lv 10, 2 Item Slots)
2. Junior Alchemy (Skill ID: 10002, Max Lv 20, 3 Item Slots, Alchemy Books I-II)
3. Senior Alchemy (Skill ID: 10003, Max Lv 30, 4 Item Slots, Alchemy Books I-IV)
"""

import random
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class AlchemySkillTier(IntEnum):
    NONE = 0
    PRIMARY = 1   # Skill ID 10001 (Lv 1-10, 2 slots)
    JUNIOR = 2    # Skill ID 10002 (Lv 1-20, 3 slots)
    SENIOR = 3    # Skill ID 10003 (Lv 1-30, 4 slots)


@dataclass
class AlchemyRecipe:
    inputs: List[int]
    output_item_id: int
    output_name: str
    base_rate: float = 80.0
    min_tier: AlchemySkillTier = AlchemySkillTier.PRIMARY


class AlchemyManager:
    """Manages multi-tier Alchemy skills (Primary, Junior, Senior), multi-ingredient compounding, and Alchemy Books."""

    SKILL_TIER_IDS: Dict[int, AlchemySkillTier] = {
        10001: AlchemySkillTier.PRIMARY,
        10002: AlchemySkillTier.JUNIOR,
        10003: AlchemySkillTier.SENIOR,
    }

    ALCHEMY_BOOKS: Dict[int, int] = {
        30010: 1,  # Alchemy Book I (+1 rank)
        30011: 2,  # Alchemy Book II (+2 ranks)
        30012: 3,  # Alchemy Book III (+3 ranks)
        30013: 4,  # Alchemy Book IV (+4 ranks)
    }

    SCRAP_ITEMS: List[int] = [27001, 28001, 28014, 27020]

    def __init__(self):
        self.recipes: List[AlchemyRecipe] = []
        self._init_recipes()

    def _init_recipes(self):
        self.recipes.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_recipes = GLOBAL_DYNAMIC_DATA.get_alchemy_recipes()
            for r in db_recipes:
                self.recipes.append(AlchemyRecipe(
                    inputs=r["input_items"],
                    output_item_id=r["output_item_id"],
                    output_name=r["output_name"],
                    base_rate=float(r.get("base_rate", 80.0)),
                    min_tier=AlchemySkillTier(r.get("min_tier", 1))
                ))
            logger.info(f"[AlchemyManager] Loaded {len(self.recipes)} dynamic alchemy recipes from database.")
        except Exception as e:
            logger.warning(f"[AlchemyManager] DB load fallback: {e}")
            # Baseline fallbacks
            self.recipes.append(AlchemyRecipe([27001, 27001], 48001, "Wooden Plank", 90.0, AlchemySkillTier.PRIMARY))
            self.recipes.append(AlchemyRecipe([46005, 27002, 27023], 21025, "Knight Bastard Sword", 60.0, AlchemySkillTier.JUNIOR))
            self.recipes.append(AlchemyRecipe([46005, 27024, 27023, 27002], 21050, "Dragon Slayer Greatsword", 50.0, AlchemySkillTier.SENIOR))

    def reload_from_db(self, dynamic_mgr=None):
        self._init_recipes()

    def get_player_alchemy_tier(self, player) -> Tuple[AlchemySkillTier, int]:
        """Detects the highest Alchemy skill tier (Primary, Junior, Senior) and level learned by player."""
        if not player:
            return AlchemySkillTier.PRIMARY, 1

        # Check learned skills list
        learned_skills = getattr(player, "skills", {})
        highest_tier = AlchemySkillTier.PRIMARY
        highest_lv = getattr(player, "alchemy_level", 1)

        for skill_id, skill_data in learned_skills.items():
            if skill_id in self.SKILL_TIER_IDS:
                tier = self.SKILL_TIER_IDS[skill_id]
                tier_lv = skill_data.get("level", 1) if isinstance(skill_data, dict) else int(skill_data)
                if tier > highest_tier:
                    highest_tier = tier
                    highest_lv = tier_lv

        # Fallback to player attribute
        if hasattr(player, "alchemy_tier") and player.alchemy_tier > int(highest_tier):
            highest_tier = AlchemySkillTier(player.alchemy_tier)
            highest_lv = getattr(player, "alchemy_level", 1)

        return AlchemySkillTier(highest_tier), highest_lv

    def get_max_slots_for_tier(self, tier: AlchemySkillTier) -> int:
        if tier == AlchemySkillTier.SENIOR:
            return 4
        elif tier == AlchemySkillTier.JUNIOR:
            return 3
        return 2

    async def compound_ingredients(
        self,
        server,
        player,
        ingredient_slots: List[int],
        book_slot: Optional[int] = None
    ) -> bool:
        if not player or not getattr(player, "inventory", None) or len(ingredient_slots) < 2:
            return False

        tier, tier_lv = self.get_player_alchemy_tier(player)
        max_slots = self.get_max_slots_for_tier(tier)

        if len(ingredient_slots) > max_slots:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Your {tier.name} Alchemy only supports up to {max_slots} materials! Learn higher Alchemy to use more slots."
            )
            await player.send_packet(sys_msg)
            return False

        from server.gameserver import remove_item_at_slot, add_item_to_inventory

        # Locate ingredients
        ingredient_items = []
        for slot in ingredient_slots:
            it = next((i for i in player.inventory if i.get("slot") == slot), None)
            if not it:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Invalid item slot in compounding!")
                await player.send_packet(sys_msg)
                return False
            ingredient_items.append(it)

        # Check alchemy book
        book_bonus = 0
        book_item = None
        if book_slot is not None:
            book_item = next((i for i in player.inventory if i.get("slot") == book_slot), None)
            if book_item:
                book_id = book_item.get("item_id", 0)
                book_bonus = self.ALCHEMY_BOOKS.get(book_id, 0)
                if book_bonus > 0:
                    # Senior allows books I-IV, Junior allows books I-II, Primary allows none
                    if tier == AlchemySkillTier.PRIMARY:
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            "Primary Alchemy cannot utilize Alchemy Books! Upgrade to Junior or Senior Alchemy."
                        )
                        await player.send_packet(sys_msg)
                        return False
                    elif tier == AlchemySkillTier.JUNIOR and book_bonus > 2:
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            "Junior Alchemy can only use Alchemy Books I and II! Learn Senior Alchemy for Books III & IV."
                        )
                        await player.send_packet(sys_msg)
                        return False

                    remove_item_at_slot(player, book_slot, 1)

        # Consume ingredients
        input_ids = [it.get("item_id", 0) for it in ingredient_items]
        for slot in ingredient_slots:
            remove_item_at_slot(player, slot, 1)

        # Match recipe
        sorted_inputs = sorted(input_ids)
        matched_recipe = None
        for r in self.recipes:
            if sorted(r.inputs) == sorted_inputs and tier >= r.min_tier:
                matched_recipe = r
                break

        # Calculate success chance based on Tier & Level & Book
        base_rate = matched_recipe.base_rate if matched_recipe else 60.0
        tier_multiplier = {
            AlchemySkillTier.PRIMARY: 1.0,
            AlchemySkillTier.JUNIOR: 1.15,
            AlchemySkillTier.SENIOR: 1.30
        }.get(tier, 1.0)

        success_chance = (base_rate * tier_multiplier) + (tier_lv * 0.5) + (book_bonus * 10.0)
        success_chance = min(95.0, max(10.0, success_chance))

        # Play compounding animation (AC 5:5: 60050)
        fx_pkt = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
        server.broadcast_to_map(player.map_id, fx_pkt)

        roll = random.random() * 100.0
        is_success = roll <= success_chance

        if is_success:
            if matched_recipe:
                out_id = matched_recipe.output_item_id
                out_name = matched_recipe.output_name
            else:
                out_id = input_ids[0] + 10 if input_ids[0] < 50000 else input_ids[0]
                out_name = f"Synthesized Item #{out_id}"

            add_item_to_inventory(player, out_id, 1)

            # Award Alchemy EXP
            exp_gain = 10 * int(tier)
            player.alchemy_exp = getattr(player, "alchemy_exp", 0) + exp_gain
            max_cap = 10 if tier == AlchemySkillTier.PRIMARY else (20 if tier == AlchemySkillTier.JUNIOR else 30)

            cur_lv = getattr(player, "alchemy_level", 1)
            if cur_lv < max_cap and player.alchemy_exp >= (cur_lv * 100):
                player.alchemy_exp = 0
                player.alchemy_level = cur_lv + 1
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"[{tier.name} Alchemy Level Up!] Your Alchemy Skill is now Lv {player.alchemy_level}!"
                )
                await player.send_packet(sys_msg)

            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Compounding Success!] ({tier.name} Alchemy) Created {out_name} (Rate: {success_chance:.1f}%)!"
            )
            await player.send_packet(sys_msg)
        else:
            scrap_id = random.choice(self.SCRAP_ITEMS)
            add_item_to_inventory(player, scrap_id, 1)
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Compounding Failed] Materials failed to synthesize and yielded Scrap #{scrap_id}."
            )
            await player.send_packet(sys_msg)

        await player.send_packet(server.build_inventory_packet(player))
        server.save_player_to_db(player)
        logger.info(f"[AlchemyManager] Player {player.char_name} compounded {input_ids} with {tier.name} Alchemy (Lv {tier_lv}) -> Success: {is_success}.")
        return is_success


GLOBAL_ALCHEMY_MANAGER = AlchemyManager()
