"""
Wonderland Online Tent System & Interior Instanced Map
Ported from C# wlo.pserver.core/Game/PlayerRelated/Tent and Src/Network/ActionCodes/AC62.cs, AC65.cs
"""

import sqlite3
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class TentItem:
    item_id: int
    x: int
    y: int
    floor: int = 0  # 0 = 1st Floor, 1 = 2nd Floor
    rotate: int = 0  # 0 to 3


@dataclass
class Tent:
    char_id: int
    locked: bool = False
    enlarged: int = 0
    tent_type: int = 1115  # Default Tent Skin ID
    floor1_color: int = 39062
    floor1_wallpaper: int = 39064
    floor2_color: int = 0
    floor2_wallpaper: int = 0
    items: List[TentItem] = field(default_factory=list)
    orig_map_id: int = 10017
    orig_x: int = 1042
    orig_y: int = 1075
    is_closed: bool = True
    is_dirty: bool = False

    def initialize_default_items(self):
        """Initializes beginner crafting furniture: Coconut Basin (38027) & Low Workbench (38049)."""
        if not self.items:
            self.place_item(38027, 43, 42, 0, 0)
            self.place_item(38049, 45, 42, 0, 0)

    def place_item(self, item_id: int, x: int, y: int, floor: int = 0, rotation: int = 0):
        item = TentItem(item_id=item_id, x=int(x), y=int(y), floor=int(floor), rotate=int(rotation))
        self.items.append(item)
        self.is_dirty = True
        logger.info(f"[Tent] Placed item {item_id} at ({x}, {y}) floor {floor} rot {rotation} for Char {self.char_id}")

    def move_item(self, index: int, x: int, y: int, floor: int = 0, rotation: int = 0) -> bool:
        if 0 <= index < len(self.items):
            item = self.items[index]
            item.x = int(x)
            item.y = int(y)
            item.floor = int(floor)
            item.rotate = int(rotation)
            self.is_dirty = True
            logger.info(f"[Tent] Moved item #{index} ({item.item_id}) to ({x}, {y}) floor {floor} rot {rotation}")
            return True
        return False

    def remove_item(self, x: int, y: int, floor: int = 0) -> Optional[TentItem]:
        for it in list(self.items):
            if it.x == x and it.y == y and it.floor == floor:
                self.items.remove(it)
                self.is_dirty = True
                logger.info(f"[Tent] Removed item {it.item_id} from ({x}, {y}) floor {floor}")
                return it
        return None

    async def send_tent_items_to_player(self, session):
        """Sends all furniture in the tent to the player via authentic AC 23 Sub 3 format."""
        if not session:
            return

        sent_count = 0
        for item in self.items:
            if item.item_id == 0:
                continue

            pkt = PacketWriter()
            pkt.write_8(23).write_8(3)
            pkt.write_16(item.item_id)
            pkt.write_32(item.x)
            pkt.write_32(item.y)
            pkt.write_32(item.floor)
            pkt.write_8(1)
            pkt.write_8(item.rotate)
            pkt.write_16(0)
            await session.send_packet(pkt)
            sent_count += 1

        logger.info(f"[Tent] Sent {sent_count} furniture items via AC 23:3 to {session.char_name}")


class TentManager:
    """Manages player tents, SQLite persistence, and instanced interior maps."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._tents: Dict[int, Tent] = {}

    def get_or_create_tent(self, char_id: int) -> Tent:
        """Retrieves active tent from memory or loads from SQLite."""
        if char_id in self._tents:
            return self._tents[char_id]

        tent = self.load_tent_from_db(char_id)
        if not tent:
            tent = Tent(char_id=char_id)
            tent.initialize_default_items()
            self.save_tent_to_db(tent)

        self._tents[char_id] = tent
        return tent

    def load_tent_from_db(self, char_id: int) -> Optional[Tent]:
        """Loads tent attributes and furniture items from chartent and chartent_items."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Verify schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent (
                    charID INTEGER PRIMARY KEY,
                    locked INTEGER DEFAULT 0,
                    enlarged INTEGER DEFAULT 0,
                    tenttype INTEGER DEFAULT 1115,
                    floor1Color INTEGER DEFAULT 39062,
                    floor1wallpaper INTEGER DEFAULT 39064,
                    floor2Color INTEGER DEFAULT 0,
                    floor2wallpaperr INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent_items (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    charID INTEGER NOT NULL,
                    itemID INTEGER NOT NULL,
                    posX INTEGER NOT NULL,
                    posY INTEGER NOT NULL,
                    floor INTEGER DEFAULT 0,
                    rotate INTEGER DEFAULT 0
                )
            """)

            row = conn.execute("SELECT * FROM chartent WHERE charID = ?", (char_id,)).fetchone()
            if not row:
                conn.close()
                return None

            tent = Tent(
                char_id=char_id,
                locked=bool(row["locked"]),
                enlarged=int(row["enlarged"] or 0),
                tent_type=int(row["tenttype"] or 1115),
                floor1_color=int(row["floor1Color"] or 39062),
                floor1_wallpaper=int(row["floor1wallpaper"] or 39064),
                floor2_color=int(row["floor2Color"] or 0),
                floor2_wallpaper=int(row["floor2wallpaperr"] or 0)
            )

            # Load furniture items
            item_rows = conn.execute("SELECT * FROM chartent_items WHERE charID = ? ORDER BY pri_key ASC", (char_id,)).fetchall()
            for ir in item_rows:
                tent.items.append(TentItem(
                    item_id=int(ir["itemID"]),
                    x=int(ir["posX"]),
                    y=int(ir["posY"]),
                    floor=int(ir["floor"]),
                    rotate=int(ir["rotate"])
                ))

            conn.close()

            if not tent.items:
                tent.initialize_default_items()
                self.save_tent_to_db(tent)

            logger.info(f"[TentManager] Loaded tent for Char {char_id} ({len(tent.items)} items) from DB.")
            return tent
        except Exception as e:
            logger.error(f"[TentManager] Error loading tent from DB for Char {char_id}: {e}", exc_info=True)
            return None

    def save_tent_to_db(self, tent: Tent):
        """Persists tent configuration and furniture items into SQLite."""
        if not tent or not tent.char_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent (
                    charID INTEGER PRIMARY KEY,
                    locked INTEGER DEFAULT 0,
                    enlarged INTEGER DEFAULT 0,
                    tenttype INTEGER DEFAULT 1115,
                    floor1Color INTEGER DEFAULT 39062,
                    floor1wallpaper INTEGER DEFAULT 39064,
                    floor2Color INTEGER DEFAULT 0,
                    floor2wallpaperr INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent_items (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    charID INTEGER NOT NULL,
                    itemID INTEGER NOT NULL,
                    posX INTEGER NOT NULL,
                    posY INTEGER NOT NULL,
                    floor INTEGER DEFAULT 0,
                    rotate INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                INSERT OR REPLACE INTO chartent (
                    charID, locked, enlarged, tenttype, floor1Color, floor1wallpaper, floor2Color, floor2wallpaperr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tent.char_id,
                1 if tent.locked else 0,
                tent.enlarged,
                tent.tent_type,
                tent.floor1_color,
                tent.floor1_wallpaper,
                tent.floor2_color,
                tent.floor2_wallpaper
            ))

            # Delete old items and rewrite current list
            conn.execute("DELETE FROM chartent_items WHERE charID = ?", (tent.char_id,))
            for it in tent.items:
                conn.execute("""
                    INSERT INTO chartent_items (charID, itemID, posX, posY, floor, rotate)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tent.char_id, it.item_id, it.x, it.y, it.floor, it.rotate))

            conn.commit()
            conn.close()
            tent.is_dirty = False
            logger.info(f"[TentManager] Saved tent for Char {tent.char_id} ({len(tent.items)} items) to DB.")
        except Exception as e:
            logger.error(f"[TentManager] Error saving tent to DB for Char {tent.char_id}: {e}", exc_info=True)

    async def open_tent(self, server, session, bgm: str = "BGM0011"):
        """Enters player personal tent interior (Map 12000 / instanced)."""
        if not session or not session.char_id:
            return

        if getattr(session, "is_fishing", False):
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Fishing, can't use tent"))
            return

        tent = self.get_or_create_tent(session.char_id)

        # Store outside coordinates
        if not getattr(session, "in_tent", False):
            tent.orig_map_id = session.map_id
            tent.orig_x = session.x
            tent.orig_y = session.y

        tent.is_closed = False
        session.in_tent = True

        # Assign tent interior coordinates
        session.map_id = 12000
        session.x = 400
        session.y = 400

        # Send full sequence of interior transition packets matching official server
        # 1. AC 12 Sub 163 (Warp to interior)
        warp_pkt = PacketWriter().write_8(12).write_8(163)
        warp_pkt.write_32(session.char_id)
        warp_pkt.write_16(12000)
        warp_pkt.write_16(400)
        warp_pkt.write_16(400)
        warp_pkt.write_32(0)
        await session.send_packet(warp_pkt)

        # 2. AC 62 Sub 7 (Tent Properties)
        await session.send_packet(PacketWriter().write_8(62).write_8(7).write_16(0))

        # 3. AC 23 Sub 3 (Send all furniture items)
        await tent.send_tent_items_to_player(session)

        # 4. AC 62 Sub 4 (Furniture Data summary)
        furn_pkt = PacketWriter().write_8(62).write_8(4).write_32(session.char_id).write_16(len(tent.items))
        await session.send_packet(furn_pkt)

        # 5. AC 62 Sub 59 (BGM Update)
        bgm_pkt = PacketWriter().write_8(62).write_8(59).write_16(257).write_32(0).write_string_n(bgm or "BGM0011")
        await session.send_packet(bgm_pkt)

        # 6. AC 65 Sub 7 (Tent status)
        await session.send_packet(PacketWriter().write_8(65).write_8(7).write_16(0))

        # 7. Ready & Unlock packets
        await session.send_packet(PacketWriter().write_8(23).write_8(102))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

        server.save_player_to_db(session)
        logger.info(f"[{session.char_name}] Successfully entered personal tent interior.")

    async def close_tent(self, server, session):
        """Exits tent interior and warps player back to outside map coordinates."""
        if not session or not session.char_id:
            return

        tent = self.get_or_create_tent(session.char_id)
        tent.is_closed = True
        session.in_tent = False

        dst_map = tent.orig_map_id or 10017
        dst_x = tent.orig_x or 1042
        dst_y = tent.orig_y or 1075

        logger.info(f"[{session.char_name}] Exiting tent interior -> warping to map {dst_map} pos=({dst_x}, {dst_y})")
        self.save_tent_to_db(tent)
        await server.warp_player(session, dst_map, dst_x, dst_y)

    def pitch_tent_on_map(self, server, session, tent_skin_id: int = 1115):
        """Broadcasts tent visual appearance to players on the current map."""
        if not session:
            return

        tent_pkt = PacketWriter().write_8(65).write_8(1)
        tent_pkt.write_32(session.char_id)
        tent_pkt.write_16(session.x)
        tent_pkt.write_16(session.y)
        tent_pkt.write_16(0)
        tent_pkt.write_32(tent_skin_id)
        tent_pkt.write_32(0)

        server.broadcast_to_map(session.map_id, tent_pkt)
        logger.info(f"[{session.char_name}] Pitched tent (Skin: {tent_skin_id}) at {session.map_id} ({session.x}, {session.y})")

    def pack_up_tent(self, server, session):
        """Packs up / removes tent from world map."""
        if not session:
            return

        pack_pkt = PacketWriter().write_8(65).write_8(2).write_32(session.char_id)
        server.broadcast_to_map(session.map_id, pack_pkt)
        logger.info(f"[{session.char_name}] Packed up tent on map {session.map_id}")


# Global singleton instance
GLOBAL_TENT_MANAGER = TentManager()
