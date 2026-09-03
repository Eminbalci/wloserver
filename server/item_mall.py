"""
Wonderland Online - Complete Item Mall System & Port 6416 Dedicated TCP Server
Ported from C# Src/Server/ItemMallServer.cs & wlo.pserver.core/Game/PlayerRelated/ItemMallManager.cs
Enhanced with 100% authentic live packet captures from Rhodes Island client (itemmalldatalari.pcapng):
- Points Mall (AC 75 Sub 1): 152 authentic catalog items across Weaponry, Armory, 11-page Grocery, Furniture
- Bonus Mall (AC 75 Sub 10): 71 authentic catalog items
- State synchronization: AC 75:8, AC 75:7, and AC 75:3 dual points sync (IM Points + Bonus Points)
"""

import os
import json
import struct
import sqlite3
import logging
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union, Tuple

from server.network import PacketWriter

logger = logging.getLogger("ItemMall")


CATEGORY_ID_TO_NAME: Dict[int, str] = {
    1: "Hot",
    2: "Armory",
    3: "Weaponry",
    4: "Grocery",
    5: "Furniture",
    6: "Slot Machine",
    7: "Forging Room"
}

CATEGORY_NAME_TO_ID: Dict[str, int] = {
    "hot": 1,
    "armory": 2,
    "armor": 2,
    "armors": 2,
    "weaponry": 3,
    "weapon": 3,
    "weapons": 3,
    "grocery": 4,
    "groceries": 4,
    "consumable": 4,
    "consumables": 4,
    "furniture": 5,
    "furn": 5,
    "tent": 5,
    "slot machine": 6,
    "slot": 6,
    "slots": 6,
    "gacha": 6,
    "minigame": 6,
    "forging room": 7,
    "forging": 7,
    "forge": 7,
    "refining": 7,
    "crystal": 7
}


def resolve_category_id(category: Union[int, str]) -> int:
    """Maps category representation to GUI Tab ID (1..7)."""
    if isinstance(category, int):
        return max(1, min(7, category))
    cat_str = str(category or "").strip().lower()
    if cat_str in ("1", "2", "3", "4", "5", "6", "7"):
        return int(cat_str)
    if cat_str in CATEGORY_NAME_TO_ID:
        return CATEGORY_NAME_TO_ID[cat_str]
    # Heuristics
    if any(w in cat_str for w in ("armor", "cloth", "gear", "shield", "head", "boot", "robe", "helm", "vest")):
        return 2
    elif any(w in cat_str for w in ("weapon", "sword", "gun", "bow", "wand", "staff", "axe", "spear", "dagger", "hammer")):
        return 3
    elif any(w in cat_str for w in ("groc", "gem", "spar", "oil", "star", "diamond", "consum", "pot", "scroll", "food", "rice", "water", "pill")):
        return 4
    elif any(w in cat_str for w in ("furn", "tent", "house", "desk", "bed", "chair", "cabinet", "shelf", "stove", "sawmill", "loom", "table")):
        return 5
    elif any(w in cat_str for w in ("machine", "wheel", "token", "pass", "ticket", "coin")):
        return 6
    elif any(w in cat_str for w in ("refin", "room", "book", "spar")):
        return 7
    return 1


@dataclass
class MallItemEntry:
    item_id: int
    item_name: str
    category: str
    point_cost: int
    original_price: int = 0
    gold_cost: int = 0
    count: int = 1
    is_hot: int = 0
    is_new: int = 0
    is_limited: int = 0
    on_sale: int = 0
    discount: int = 100
    badge: int = 0
    category_id: int = 0
    order_idx: int = 0
    is_bonus: int = 0
    subcategory_id: int = 1


class ItemMallManager:
    def __init__(self):
        self._points_catalog: List[MallItemEntry] = []
        self._bonus_catalog: List[MallItemEntry] = []
        self._catalog_map: Dict[int, MallItemEntry] = {}
        self._composite_map: Dict[Tuple[int, int, int], MallItemEntry] = {}
        self.reload_from_db()

    @property
    def _catalog(self) -> List[MallItemEntry]:
        return self._points_catalog

    @_catalog.setter
    def _catalog(self, val: List[MallItemEntry]):
        self._points_catalog = list(val)
        self._catalog_map.clear()
        for it in self._points_catalog:
            self._catalog_map[it.item_id] = it

    def reload_from_db(self, dynamic_data_mgr=None):
        """Reloads Item Mall catalog from dynamic SQLite database or JSON fallback."""
        try:
            if dynamic_data_mgr is None:
                from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
                dynamic_data_mgr = GLOBAL_DYNAMIC_DATA

            raw_items = dynamic_data_mgr.get_item_mall_catalog()
            self._points_catalog.clear()
            self._bonus_catalog.clear()
            self._catalog_map.clear()
            self._composite_map.clear()

            for row in raw_items:
                point_cost = int(row.get("point_cost", 100) or 0)
                orig_price = int(row.get("original_price", 0) or 0)
                if orig_price <= 0:
                    orig_price = point_cost
                count_val = int(row.get("count", 1) or 1)
                is_hot_val = int(row.get("is_hot", 0) or 0)
                is_new_val = int(row.get("is_new", 0) or 0)
                is_limited_val = int(row.get("is_limited", 0) or 0)
                on_sale_val = int(row.get("on_sale", 0) or 0)
                discount_val = int(row.get("discount", 100) or 100)
                badge_val = int(row.get("badge", 0) or 0)
                cat_id_val = int(row.get("category_id", 3) or 3)
                order_val = int(row.get("order_idx", 0) or 0)
                is_bonus_val = int(row.get("is_bonus", 0) or 0)
                subcat_val = int(row.get("subcategory_id", 1) or 1)

                entry = MallItemEntry(
                    item_id=int(row["item_id"]),
                    item_name=str(row.get("item_name", f"Item_{row['item_id']}")),
                    category=str(row.get("category", "Grocery")),
                    point_cost=point_cost,
                    original_price=orig_price,
                    gold_cost=int(row.get("gold_cost", 0) or 0),
                    count=count_val,
                    is_hot=is_hot_val,
                    is_new=is_new_val,
                    is_limited=is_limited_val,
                    on_sale=on_sale_val,
                    discount=discount_val,
                    badge=badge_val,
                    category_id=cat_id_val,
                    order_idx=order_val,
                    is_bonus=is_bonus_val,
                    subcategory_id=subcat_val
                )

                if is_bonus_val:
                    self._bonus_catalog.append(entry)
                else:
                    self._points_catalog.append(entry)

                self._catalog_map[entry.item_id] = entry
                self._composite_map[(entry.item_id, entry.count, entry.is_bonus)] = entry

            # Sort catalogs by order_idx
            self._points_catalog.sort(key=lambda x: (x.order_idx, x.item_id))
            self._bonus_catalog.sort(key=lambda x: (x.order_idx, x.item_id))

            logger.info(
                f"[ItemMallManager] Loaded {len(self._points_catalog)} Points Mall items and "
                f"{len(self._bonus_catalog)} Bonus Mall items from dynamic database."
            )
        except Exception as e:
            logger.error(f"[ItemMallManager] Error reloading catalog: {e}", exc_info=True)

    def get_catalog(self, is_bonus: bool = False) -> List[MallItemEntry]:
        """Returns the requested catalog list (Points Mall or Bonus Mall)."""
        return list(self._bonus_catalog if is_bonus else self._points_catalog)

    def get_item(self, item_id: int, count: int = 1, is_bonus: int = 0) -> Optional[MallItemEntry]:
        """Queries an item entry by (item_id, count, is_bonus) with fallback to item_id."""
        key = (item_id, count, is_bonus)
        if key in self._composite_map:
            return self._composite_map[key]
        return self._catalog_map.get(item_id)

    # -------------------------------------------------------------
    # User IM Points & Bonus Points Management
    # -------------------------------------------------------------
    def get_user_points(self, session, db_path: str = "wlo_server.db") -> int:
        if not session:
            return 0
        if hasattr(session, "im_points"):
            return session.im_points

        acc_id = getattr(session, "account_id", 0) or getattr(session, "user_id", 0)
        if not acc_id:
            return 0

        try:
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute("SELECT im_points FROM accounts WHERE id = ?", (acc_id,)).fetchone()
                points = row[0] if row and row[0] is not None else 500
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE accounts ADD COLUMN im_points INTEGER DEFAULT 500")
                conn.commit()
                points = 500
            conn.close()
            session.im_points = points
            return points
        except Exception as e:
            logger.error(f"[ItemMallManager] Error getting points for account {acc_id}: {e}")
            return getattr(session, "im_points", 500)

    def set_user_points(self, session, points: int, db_path: str = "wlo_server.db"):
        if not session:
            return
        session.im_points = max(0, points)
        acc_id = getattr(session, "account_id", 0) or getattr(session, "user_id", 0)
        if acc_id:
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE accounts SET im_points = ? WHERE id = ?", (session.im_points, acc_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[ItemMallManager] Error saving points to DB: {e}")

    def get_user_bonus_points(self, session, db_path: str = "wlo_server.db") -> int:
        if not session:
            return 0
        if hasattr(session, "im_bonus_points"):
            return session.im_bonus_points

        acc_id = getattr(session, "account_id", 0) or getattr(session, "user_id", 0)
        if not acc_id:
            return 0

        try:
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute("SELECT im_bonus_points FROM accounts WHERE id = ?", (acc_id,)).fetchone()
                bonus_points = row[0] if row and row[0] is not None else 0
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE accounts ADD COLUMN im_bonus_points INTEGER DEFAULT 0")
                conn.commit()
                bonus_points = 0
            conn.close()
            session.im_bonus_points = bonus_points
            return bonus_points
        except Exception as e:
            return getattr(session, "im_bonus_points", 0)

    def set_user_bonus_points(self, session, bonus_points: int, db_path: str = "wlo_server.db"):
        if not session:
            return
        session.im_bonus_points = max(0, bonus_points)
        acc_id = getattr(session, "account_id", 0) or getattr(session, "user_id", 0)
        if acc_id:
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE accounts SET im_bonus_points = ? WHERE id = ?", (session.im_bonus_points, acc_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[ItemMallManager] Error saving bonus points to DB: {e}")

    def add_user_points(self, session, points: int, db_path: str = "wlo_server.db"):
        cur = self.get_user_points(session, db_path)
        self.set_user_points(session, cur + points, db_path)

    def add_user_bonus_points(self, session, bonus_points: int, db_path: str = "wlo_server.db"):
        cur = self.get_user_bonus_points(session, db_path)
        self.set_user_bonus_points(session, cur + bonus_points, db_path)

    # -------------------------------------------------------------
    # Protocol Packets (Port 6414)
    # -------------------------------------------------------------
    async def send_point_balance(self, session):
        """
        Native Client Mall Points Packet: S->C AC 75 Sub 3
        Payload: [75, 3, im_points(uint32), bonus_points(uint32), 0(uint16), 0(uint8)]
        Total length: 13 bytes.
        """
        if not session:
            return
        points = self.get_user_points(session)
        bonus_points = self.get_user_bonus_points(session)
        pkt = PacketWriter().write_8(75).write_8(3).write_32(points).write_32(bonus_points).write_16(0).write_8(0)
        await session.send_packet(pkt)
        logger.debug(f"[ItemMall] Sent AC 75:3 Points ({points} IM, {bonus_points} Bonus) to {getattr(session, 'char_name', 'Player')}")

    async def send_catalog(self, session, is_bonus: bool = False):
        """
        Dispatches authentic Item Mall catalog:
        - Points Mall: S->C AC 75 Sub 1 (152 items)
        - Bonus Mall:  S->C AC 75 Sub 10 (71 items)
        Each item is exactly 10 bytes:
          [0-1] item_id (uint16_LE)
          [2]   count (uint8: 1 for single, 5/20/50 for bundle)
          [3-4] base_price / original_price (uint16_LE)
          [5]   discount percentage (uint8: 100=no sale, 80=20% off)
          [6]   badge tag (uint8: 0=normal, 1=NEW, 2=HOT, 3=LIMITED)
          [7]   category_id (uint8: 1=Weaponry, 2=Armory, 3=Grocery single, 4=Grocery pack, 5=Furniture)
          [8-9] order_idx (uint16_LE: display ordering index)
        """
        if not session:
            return
        try:
            catalog = self.get_catalog(is_bonus=is_bonus)
            sub_code = 10 if is_bonus else 1
            pkt = PacketWriter().write_8(75).write_8(sub_code).write_16(len(catalog))

            for item in catalog:
                pkt.write_16(item.item_id)
                pkt.write_8(min(255, max(1, item.count)))
                base_price = item.original_price if item.original_price > 0 else item.point_cost
                pkt.write_16(min(65535, max(0, base_price)))

                # Resolve discount percentage
                disc = item.discount
                if disc >= 100 and item.on_sale and item.original_price > item.point_cost > 0:
                    disc = max(1, min(99, int(item.point_cost * 100 / item.original_price)))
                pkt.write_8(min(255, max(1, disc)))

                # Resolve badge tag
                badge = item.badge
                if badge == 0:
                    if item.is_new:
                        badge = 1
                    elif item.is_hot:
                        badge = 2
                    elif item.is_limited:
                        badge = 3
                pkt.write_8(min(255, max(0, badge)))

                # Resolve authentic category byte
                if item.category_id in (1, 2, 3, 4, 5):
                    cat_byte = item.category_id
                else:
                    cat_byte = resolve_category_id(item.category)
                pkt.write_8(min(255, max(1, cat_byte)))
                order_val = item.order_idx if item.order_idx > 0 else base_price
                pkt.write_16(min(65535, max(0, order_val)))

            await session.send_packet(pkt)
            logger.info(
                f"[ItemMall] Dispatched AC 75:{sub_code} ({'Bonus' if is_bonus else 'Points'} Mall, {len(catalog)} items) "
                f"to {getattr(session, 'char_name', 'Player')}"
            )
        except Exception as e:
            logger.error(f"[ItemMall] Error sending catalog packet: {e}", exc_info=True)

    async def send_initial_mall_sync(self, session):
        """
        Sends the complete official map-entry / mall initialization sequence:
        1. AC 75 Sub 1 (Points Mall catalog: 152 items)
        2. AC 75 Sub 10 (Bonus Mall catalog: 71 items)
        3. AC 75 Sub 8 (Mall settings: [75, 8, 0, 0])
        4. AC 75 Sub 7 (Mall status: [75, 7, 1])
        5. AC 75 Sub 3 (Points & Bonus Points balance)
        """
        if not session:
            return
        # 1. Points Mall
        await self.send_catalog(session, is_bonus=False)
        # 2. Bonus Mall
        await self.send_catalog(session, is_bonus=True)
        # 3. Mall sync AC 75:8
        await session.send_packet(PacketWriter().write_8(75).write_8(8).write_8(0).write_8(0))
        # 4. Mall status AC 75:7
        await session.send_packet(PacketWriter().write_8(75).write_8(7).write_8(1))
        # 5. Points balance AC 75:3
        await self.send_point_balance(session)

    # -------------------------------------------------------------
    # Purchasing Logic
    # -------------------------------------------------------------
    async def purchase_item(
        self,
        server,
        session,
        item_id: int,
        quantity: int = 1,
        is_bonus: bool = False
    ) -> bool:
        if not session:
            return False
        if quantity <= 0:
            quantity = 1

        entry = self.get_item(item_id, is_bonus=1 if is_bonus else 0)
        if not entry:
            await self._send_system_notice(session, "The selected item is no longer available in the Item Mall.")
            return False

        total_cost = entry.point_cost * quantity
        if is_bonus:
            user_points = self.get_user_bonus_points(session)
            point_label = "Bonus Points"
        else:
            user_points = self.get_user_points(session)
            point_label = "IM Points"

        if user_points < total_cost:
            await self._send_system_notice(session, f"Insufficient {point_label}! Required: {total_cost} (Current: {user_points}).")
            return False

        # Deduct Points
        if is_bonus:
            self.set_user_bonus_points(session, user_points - total_cost)
        else:
            self.set_user_points(session, user_points - total_cost)

        # Grant Item to Inventory
        total_items_to_add = entry.count * quantity
        if server and hasattr(server, "grant_item"):
            res = server.grant_item(session, entry.item_id, total_items_to_add, send_acquire_notice=False)
            if asyncio.iscoroutine(res):
                await res
        else:
            from server.gameserver import add_item_to_inventory
            add_item_to_inventory(session, entry.item_id, total_items_to_add)
            if server and hasattr(server, "build_inventory_packet"):
                inv_pkt = server.build_inventory_packet(session)
                await session.send_packet(inv_pkt)
            if server and hasattr(server, "save_player_to_db"):
                server.save_player_to_db(session)

        # Send Point Balance Update (AC 75:3)
        await self.send_point_balance(session)

        # Send Purchase Success System Message
        char_name = getattr(session, "char_name", "Player")
        rem = self.get_user_bonus_points(session) if is_bonus else self.get_user_points(session)
        await self._send_system_notice(
            session,
            f"🎉 Successfully purchased {total_items_to_add}x {entry.item_name} for {total_cost} {point_label}! Remaining: {rem}."
        )
        logger.info(f"[ItemMall] Player {char_name} purchased {quantity}x #{item_id} ({entry.item_name}) for {total_cost} {point_label}.")
        return True

    async def _send_system_notice(self, session, msg: str):
        if not session:
            return
        pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(pkt)


# =================================================================
# Dedicated Port 6416 TCP Item Mall Catalog Server
# =================================================================
class ItemMallServer:
    """
    Dedicated TCP Server listening on Port 6416 (WLO Item Mall Catalog Service).
    Dispatches authentic binary catalog payload expected by aLogin.exe (FUN_0025a684) and closes socket.
    """
    def __init__(self, port: int = 6416):
        self.port = port
        self.server = None
        self._is_running = False

    def build_catalog_payload(self) -> bytes:
        catalog = GLOBAL_ITEM_MALL_MANAGER.get_catalog(is_bonus=False)
        payload = bytearray()
        payload.append(0xC9)  # Opcode
        payload.append(0x00)  # Header byte 0
        payload.append(0x01)  # Header byte 1

        for item in catalog:
            payload.extend(struct.pack("<H", item.item_id))
            val = 2 if (item.is_hot or item.badge == 2) else 3
            payload.append(val)

        return bytes(payload)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        try:
            catalog_bytes = self.build_catalog_payload()
            writer.write(catalog_bytes)
            await writer.drain()
            logger.info(f"[ItemMallServer:6416] Dispatched {len(catalog_bytes)}B catalog to client {addr}")
        except Exception as e:
            logger.warning(f"[ItemMallServer:6416] Client error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self, host: str = "0.0.0.0"):
        try:
            self.server = await asyncio.start_server(self.handle_client, host, self.port)
            self._is_running = True
            display_host = "127.0.0.1" if host == "0.0.0.0" else host
            logger.info(f"[ItemMallServer] Dedicated Item Mall TCP Service active on {display_host}:{self.port}")
        except Exception as e:
            logger.warning(f"[ItemMallServer] Could not bind port {self.port}: {e}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._is_running = False
            logger.info("[ItemMallServer] Stopped.")


# Global Singleton Instance
GLOBAL_ITEM_MALL_MANAGER = ItemMallManager()
