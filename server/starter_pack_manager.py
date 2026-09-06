"""
Wonderland Online Starter Items Pack Manager
Manages dynamically configurable starter gift items granted to new characters upon initial login (AC 23 Sub 6).
Integrated with SQLite dynamic persistence and hot-reloadable via GUI Admin Suite.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("WLO_Server")


class StarterItemEntry:
    """Represents a single starter item configuration entry."""

    def __init__(self, item_id: int, item_name: str, count: int = 1, order_idx: int = 0, description: str = ""):
        self.item_id: int = int(item_id)
        self.item_name: str = str(item_name)
        self.count: int = max(1, int(count))
        self.order_idx: int = int(order_idx)
        self.description: str = str(description)

    def to_tuple(self) -> Tuple[int, int]:
        return (self.item_id, self.count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_name": self.item_name,
            "count": self.count,
            "order_idx": self.order_idx,
            "description": self.description,
        }


class StarterPackManager:
    """Manages starter items cache, dynamic queries, and runtime delivery."""

    def __init__(self):
        self._items: List[StarterItemEntry] = []
        self.reload_from_db()

    def reload_from_db(self, dynamic_manager: Any = None):
        """Loads or reloads starter items from SQLite dynamic database."""
        try:
            if dynamic_manager is None:
                from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
                dynamic_manager = GLOBAL_DYNAMIC_DATA

            rows = dynamic_manager.get_starter_items()
            self._items = [
                StarterItemEntry(
                    item_id=r["item_id"],
                    item_name=r.get("item_name", f"Item #{r['item_id']}"),
                    count=r.get("count", 1),
                    order_idx=r.get("order_idx", idx),
                    description=r.get("description", ""),
                )
                for idx, r in enumerate(rows)
            ]
            logger.info(f"[StarterPackManager] Loaded {len(self._items)} starter items from dynamic database.")
        except Exception as e:
            logger.error(f"[StarterPackManager] Error reloading starter items from DB: {e}")
            if not self._items:
                # Fallback to default authentic items
                self._items = [
                    StarterItemEntry(34038, "Starter Gift 1", 1, 1, "Beginner gift package"),
                    StarterItemEntry(34058, "Remote Control", 1, 2, "Auto-combat and assistant remote control"),
                    StarterItemEntry(34332, "Mini Dragonfly", 5, 3, "Starter flying mount vehicle"),
                    StarterItemEntry(32176, "Spicy Hot Pot", 50, 4, "Full recovery food"),
                    StarterItemEntry(34026, "Protective Exp Pill", 10, 5, "Prevents EXP loss upon death"),
                    StarterItemEntry(34542, "Substitute Doll", 1, 6, "Prevents companion amity drop upon death"),
                    StarterItemEntry(21742, "Goddess Robe", 1, 7, "Starter protective equipment"),
                    StarterItemEntry(34330, "Mini HP Potion", 1, 8, "Starter HP healing potions"),
                    StarterItemEntry(34190, "10x Holy EXP Potion", 5, 9, "Boosts experience gain"),
                    StarterItemEntry(34258, "Training Ticket", 5, 10, "Instant training island pass"),
                ]

    def get_items(self) -> List[StarterItemEntry]:
        """Returns the current list of starter item entries."""
        return list(self._items)

    def get_delivery_tuples(self) -> List[Tuple[int, int]]:
        """Returns (item_id, count) pairs for inventory delivery."""
        return [entry.to_tuple() for entry in self._items]


GLOBAL_STARTER_PACK_MANAGER = StarterPackManager()
