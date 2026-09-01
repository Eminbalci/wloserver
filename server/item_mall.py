"""
Wonderland Online - Complete Item Mall System & Port 6416 Dedicated TCP Server
Ported from C# Src/Server/ItemMallServer.cs & wlo.pserver.core/Game/PlayerRelated/ItemMallManager.cs

Features:
- Dedicated TCP Item Mall Service listening on Port 6416 (dispatches binary catalog payload to aLogin.exe)
- In-Game AC 75 Item Mall Protocol on Port 6414:
  - AC 75 Sub 1: In-game Item Mall catalog matrix (10-byte binary item structures, categories, prices, hot tags, stock)
  - AC 75 Sub 3: Personal IM Point balance synchronization
  - AC 75 Sub 2: In-game purchasing with points or gold, atomic inventory item grant (AC 23:6, AC 23:8, AC 23:5), and balance update
- 100% Dynamic Database Driven (backed by SQLite table `game_item_mall` and `server/data/item_mall.json`)
- Live hot-reload support via DynamicDataManager
"""

import os
import json
import struct
import sqlite3
import logging
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union

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
    """Maps any category representation (int 1..7, string '1'..'7', or text name) to valid Item Mall Category ID (1..7)."""
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
    on_sale: int = 0
    subcategory_id: int = 1


class ItemMallManager:
    def __init__(self):
        self._catalog: List[MallItemEntry] = []
        self._catalog_map: Dict[int, MallItemEntry] = {}
        self.reload_from_db()

    def reload_from_db(self, dynamic_data_mgr=None):
        """Reloads Item Mall catalog from dynamic SQLite database or JSON fallback."""
        try:
            if dynamic_data_mgr is None:
                from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
                dynamic_data_mgr = GLOBAL_DYNAMIC_DATA

            raw_items = dynamic_data_mgr.get_item_mall_catalog()
            self._catalog.clear()
            self._catalog_map.clear()

            for row in raw_items:
                point_cost = int(row.get("point_cost", 100) or 0)
                orig_price = int(row.get("original_price", 0) or 0)
                is_hot_val = int(row.get("is_hot", 0) or 0)
                is_new_val = int(row.get("is_new", 0) or 0)
                on_sale_val = int(row.get("on_sale", 0) or 0)
                subcat_val = int(row.get("subcategory_id", 1) or 1)

                entry = MallItemEntry(
                    item_id=int(row["item_id"]),
                    item_name=str(row["item_name"]),
                    category=str(row.get("category", "Hot")),
                    point_cost=point_cost,
                    original_price=orig_price,
                    gold_cost=int(row.get("gold_cost", 0) or 0),
                    count=int(row.get("count", 1) or 1),
                    is_hot=is_hot_val,
                    is_new=is_new_val,
                    on_sale=on_sale_val,
                    subcategory_id=subcat_val
                )
                self._catalog.append(entry)
                self._catalog_map[entry.item_id] = entry

            logger.info(f"[ItemMallManager] Loaded {len(self._catalog)} Mall items from dynamic database.")
        except Exception as e:
            logger.error(f"[ItemMallManager] Error reloading catalog: {e}", exc_info=True)

    def get_catalog(self) -> List[MallItemEntry]:
        return list(self._catalog)

    def get_item(self, item_id: int) -> Optional[MallItemEntry]:
        return self._catalog_map.get(item_id)

    # -------------------------------------------------------------
    # User IM Points Management
    # -------------------------------------------------------------
    def get_user_points(self, session, db_path: str = "wlo_server.db") -> int:
        if not session:
            return 0
        if hasattr(session, "im_points"):
            return session.im_points

        acc_id = getattr(session, "account_id", 0)
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
        acc_id = getattr(session, "account_id", 0)
        if acc_id:
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("UPDATE accounts SET im_points = ? WHERE id = ?", (session.im_points, acc_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[ItemMallManager] Error saving points to DB: {e}")

    def add_user_points(self, session, points: int, db_path: str = "wlo_server.db"):
        cur = self.get_user_points(session, db_path)
        self.set_user_points(session, cur + points, db_path)

    # -------------------------------------------------------------
    # Protocol Packets (Port 6414)
    # -------------------------------------------------------------
    async def send_point_balance(self, session):
        """Native Client Mall Points Packet: S->C AC 75 Sub 3 [Points(uint32), Extra(uint32), Item(uint16), Count(uint8)]"""
        if not session:
            return
        points = self.get_user_points(session)
        # 13 bytes total: Opcode 75, Sub 3, Points (4B), Extra (4B), ItemID (2B), Count (1B)
        pkt = PacketWriter().write_8(75).write_8(3).write_32(points).write_32(0).write_16(0).write_8(0)
        await session.send_packet(pkt)
        logger.debug(f"[ItemMall] Sent AC 75:3 Points ({points} IM) to {getattr(session, 'char_name', 'Player')}")

    async def send_catalog(self, session):
        """
        Native In-Game Client Item Mall Packet: S->C AC 75 Sub 1
        Header: [75, 1, count(uint16_LE)]
        Per-item (10 bytes):
          [0-1] ItemID (uint16_LE)
          [2]   SubCategoryID / Flag (uint8: default 1)
          [3-4] Normal / Base Price (uint16_LE: if sale, original price)
          [5]   Discount Percentage (uint8: 100 = Regular Price / No Sale, <100 = On Sale % multiplier)
          [6]   Badge Tag (uint8: 1 = NEW starburst badge, 2 = HOT badge, 0 = Normal)
          [7]   CategoryID (uint8: 1=Hot, 2=Armory, 3=Weaponry, 4=Grocery, 5=Furniture, 6=Slot Machine, 7=Forging Room)
          [8-9] Point Cost / Base Price (uint16_LE: base price in Points)
        """
        if not session:
            return
        try:
            catalog = self.get_catalog()
            pkt = PacketWriter().write_8(75).write_8(1).write_16(len(catalog))

            for item in catalog:
                # Category ID Mapping (1..7)
                cat_id = resolve_category_id(item.category)

                # Badge Tag: 1 = NEW, 2 = HOT, 0 = Normal
                if item.is_new:
                    tag = 1
                elif item.is_hot:
                    tag = 2
                else:
                    tag = 0

                # Sale & Discount Percentage (Offset 5): 100 = 100% (No discount), <100 = Sale percentage
                is_sale = bool(item.on_sale and (item.original_price > item.point_cost > 0))
                if is_sale:
                    base_price = item.original_price
                    discount_pct = max(1, min(99, int(item.point_cost * 100 / item.original_price)))
                elif item.on_sale and item.point_cost > 0:
                    base_price = item.point_cost
                    discount_pct = 80  # Default 20% discount if marked on_sale without custom original_price
                else:
                    base_price = item.point_cost
                    discount_pct = 100  # 100% of price (No strike-through, no red sale banner)

                # Byte 0..1: ItemID (uint16_LE)
                pkt.write_16(item.item_id)
                # Byte 2: SubCategory / Flag (uint8)
                pkt.write_8(item.subcategory_id or 1)
                # Byte 3..4: Base / Normal Price (uint16_LE)
                pkt.write_16(min(65535, max(0, base_price)))
                # Byte 5: Discount Percentage (uint8: 100 = Normal, <100 = Sale)
                pkt.write_8(discount_pct)
                # Byte 6: Badge Tag (uint8: 1=NEW, 2=HOT, 0=Normal)
                pkt.write_8(tag)
                # Byte 7: CategoryID (uint8: 1..7)
                pkt.write_8(cat_id)
                # Byte 8..9: Point Cost / Base Price (uint16_LE: used by client as price register)
                pkt.write_16(min(65535, max(0, base_price)))

            await session.send_packet(pkt)
            logger.info(f"[ItemMall] Dispatched AC 75:1 Catalog ({len(catalog)} items) to {getattr(session, 'char_name', 'Player')}")

            # Also synchronize point balance
            await self.send_point_balance(session)
        except Exception as e:
            logger.error(f"[ItemMall] Error sending catalog packet: {e}", exc_info=True)

    # -------------------------------------------------------------
    # Purchasing Logic
    # -------------------------------------------------------------
    async def purchase_item(self, server, session, item_id: int, quantity: int = 1) -> bool:
        if not session:
            return False
        if quantity <= 0:
            quantity = 1

        entry = self.get_item(item_id)
        if not entry:
            await self._send_system_notice(session, "The selected item is no longer available in the Item Mall.")
            return False

        total_cost = entry.point_cost * quantity
        user_points = self.get_user_points(session)

        if user_points < total_cost:
            await self._send_system_notice(session, f"Insufficient IM Points! Required: {total_cost} Points (Current: {user_points} Points).")
            return False

        # Deduct Points
        self.set_user_points(session, user_points - total_cost)

        # Grant Item to Inventory via atomic server.grant_item (dispatches AC 23:6, AC 23:8, AC 23:5, saves DB)
        total_items_to_add = entry.count * quantity
        if server and hasattr(server, "grant_item"):
            res = server.grant_item(session, entry.item_id, total_items_to_add)
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
        await self._send_system_notice(session, f"🎉 Successfully purchased {total_items_to_add}x {entry.item_name} for {total_cost} IM Points! Remaining: {session.im_points} Pts.")
        logger.info(f"[ItemMall] Player {char_name} purchased {quantity}x #{item_id} ({entry.item_name}) for {total_cost} IM Points.")
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
        """
        Authentic binary format confirmed by yeniitemmall.pcapng:
        [0xC9, 0x00, 0x01, ...[ItemID(uint16_LE), val(uint8)]...]
        val: 2 = Special/Hot, 3 = Standard
        """
        catalog = GLOBAL_ITEM_MALL_MANAGER.get_catalog()
        payload = bytearray()
        payload.append(0xC9)  # Opcode
        payload.append(0x00)  # Header byte 0
        payload.append(0x01)  # Header byte 1

        for item in catalog:
            payload.extend(struct.pack("<H", item.item_id))
            cat_id = resolve_category_id(item.category)
            val = 2 if (item.is_hot or cat_id == 1) else 3
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
