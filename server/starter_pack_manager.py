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
                # Fallback to default authentic items (matches C# StarterPackManager.SeedDatabase)
                self._items = [
                    StarterItemEntry(34038, "Notepad", 1, 1, "Beginner guide and notepad"),
                    StarterItemEntry(34058, "Remote Control", 1, 2, "Auto-combat assistant controller"),
                    StarterItemEntry(32176, "Fugu Hot Pot", 50, 3, "Full recovery food"),
                    StarterItemEntry(34014, "Tao Rice Ball", 10, 4, "Pet and character food"),
                    StarterItemEntry(34026, "Protective EXP Pill", 5, 5, "Prevents EXP loss upon death"),
                    StarterItemEntry(34169, "Bamboo Dragonfly", 1, 6, "Starter flying mount vehicle"),
                    StarterItemEntry(34190, "10X Holy EXP Potion", 3, 7, "Boosts experience gain"),
                    StarterItemEntry(34253, "Training Ticket", 5, 8, "Training island pass"),
                ]

    def get_items(self) -> List[StarterItemEntry]:
        """Returns the current list of starter item entries."""
        return list(self._items)

    def get_delivery_tuples(self) -> List[Tuple[int, int]]:
        """Returns (item_id, count) pairs for inventory delivery."""
        return [entry.to_tuple() for entry in self._items]

    def has_any_starter_item(self, session: Any) -> bool:
        """Checks if player already possesses any starter item in their inventory."""
        if not hasattr(session, "inventory") or not session.inventory:
            return False
        starter_ids = {item.item_id for item in self._items if item.item_id > 0}
        for inv_entry in session.inventory:
            if isinstance(inv_entry, dict) and inv_entry.get("item_id") in starter_ids:
                return True
        return False

    def deliver_to_player(self, session: Any, send_packets: bool = False) -> int:
        """
        Delivers authentic starter items directly to player inventory.
        Matching C# StarterPackManager.DeliverToPlayer(tp, sendData: false).
        """
        from server.gameserver import add_item_to_inventory
        from server.network import PacketWriter

        count_added = 0
        for entry in sorted(self._items, key=lambda i: i.order_idx):
            if entry.item_id > 0 and entry.count > 0:
                add_item_to_inventory(session, entry.item_id, entry.count)
                count_added += 1
                if send_packets:
                    delivery_pkt = (
                        PacketWriter()
                        .write_8(23)
                        .write_8(6)
                        .write_16(entry.item_id)
                        .write_8(min(255, entry.count))
                        .write_bytes(bytes(28))
                    )
                    if hasattr(session, "send_packet"):
                        import asyncio
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(session.send_packet(delivery_pkt))
                        except RuntimeError:
                            pass
        return count_added


GLOBAL_STARTER_PACK_MANAGER = StarterPackManager()
