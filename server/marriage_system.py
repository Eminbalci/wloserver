"""
Wonderland Online Marriage & Couple System (AC 44)
Ported from C# wlo.pserver.core/Game/PlayerRelated/MarriageManager.cs
"""

import time
import sqlite3
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class MarriageRecord:
    husband_id: int
    husband_name: str
    wife_id: int
    wife_name: str
    marriage_date: float = field(default_factory=time.time)

    def get_spouse_id(self, char_id: int) -> int:
        return self.wife_id if char_id == self.husband_id else self.husband_id

    def get_spouse_name(self, char_id: int) -> str:
        return self.wife_name if char_id == self.husband_id else self.husband_name


class MarriageManager:
    """Manages player marriage ceremonies, couple teleportation, and SQLite persistence."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._marriages: Dict[int, MarriageRecord] = {}  # CharID -> MarriageRecord
        self._pending_proposals: Dict[int, int] = {}    # TargetID -> ProposerID
        self._ensure_tables()
        self._load_from_db()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS charmarriage (
                    husband_id INTEGER PRIMARY KEY,
                    husband_name VARCHAR(50) NOT NULL,
                    wife_id INTEGER NOT NULL UNIQUE,
                    wife_name VARCHAR(50) NOT NULL,
                    marriage_date REAL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[MarriageManager] DB Init Error: {e}")

    def _load_from_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM charmarriage").fetchall()
            for r in rows:
                rec = MarriageRecord(
                    husband_id=r["husband_id"],
                    husband_name=r["husband_name"],
                    wife_id=r["wife_id"],
                    wife_name=r["wife_name"],
                    marriage_date=r["marriage_date"] or time.time()
                )
                self._marriages[rec.husband_id] = rec
                self._marriages[rec.wife_id] = rec
            conn.close()
            logger.info(f"[MarriageManager] Loaded {len(rows)} marriage records from DB.")
        except Exception as e:
            logger.error(f"[MarriageManager] Error loading marriages: {e}")

    def is_married(self, char_id: int) -> bool:
        return char_id in self._marriages

    def get_marriage(self, char_id: int) -> Optional[MarriageRecord]:
        return self._marriages.get(char_id)

    async def propose(self, server, proposer, target) -> bool:
        if not proposer or not target or proposer.char_id == target.char_id:
            return False

        if proposer.level < 30 or target.level < 30:
            await self.send_system_msg(proposer, "Both players must be at least Level 30 to marry!")
            return False

        if self.is_married(proposer.char_id) or self.is_married(target.char_id):
            await self.send_system_msg(proposer, "Either you or the target is already married!")
            return False

        if proposer.gold < 60000:
            await self.send_system_msg(proposer, "Wedding ceremony requires 60,000 gold!")
            return False

        self._pending_proposals[target.char_id] = proposer.char_id

        # Send proposal prompt to target
        prompt_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"{proposer.char_name} has proposed marriage to you! Type ':marry yes' or click Accept."
        )
        await target.send_packet(prompt_pkt)
        await self.send_system_msg(proposer, f"Marriage proposal sent to {target.char_name}.")
        return True

    async def accept_proposal(self, server, target) -> bool:
        if target.char_id not in self._pending_proposals:
            return False

        proposer_id = self._pending_proposals.pop(target.char_id)
        proposer = server.sessions.get(proposer_id)
        if not proposer:
            await self.send_system_msg(target, "Your partner is no longer online.")
            return False

        if proposer.gold < 60000:
            await self.send_system_msg(target, "Partner does not have enough gold for ceremony!")
            return False

        proposer.gold -= 60000
        await proposer.send_packet(PacketWriter().write_8(26).write_8(4).write_32(proposer.gold))

        # Save to DB
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO charmarriage (husband_id, husband_name, wife_id, wife_name, marriage_date)
                VALUES (?, ?, ?, ?, ?)
            """, (proposer.char_id, proposer.char_name, target.char_id, target.char_name, time.time()))
            conn.commit()
            conn.close()

            rec = MarriageRecord(
                husband_id=proposer.char_id,
                husband_name=proposer.char_name,
                wife_id=target.char_id,
                wife_name=target.char_name,
                marriage_date=time.time()
            )
            self._marriages[proposer.char_id] = rec
            self._marriages[target.char_id] = rec

            # Play wedding heart fireworks animation (AC 5:5: 60012)
            heart1 = PacketWriter().write_8(5).write_8(5).write_32(proposer.char_id).write_16(60012)
            heart2 = PacketWriter().write_8(5).write_8(5).write_32(target.char_id).write_16(60012)
            server.broadcast_to_map(proposer.map_id, heart1)
            server.broadcast_to_map(target.map_id, heart2)

            # Global announcement
            announce = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Wedding Bells] Congratulations to {proposer.char_name} and {target.char_name} on their grand marriage!"
            )
            server.broadcast_to_map(proposer.map_id, announce)
            server.broadcast_to_map(target.map_id, announce)

            logger.info(f"[MarriageManager] {proposer.char_name} and {target.char_name} are now married.")
            return True
        except Exception as e:
            logger.error(f"[MarriageManager] Error recording marriage: {e}", exc_info=True)
            return False

    async def couple_teleport(self, server, player) -> bool:
        rec = self.get_marriage(player.char_id)
        if not rec:
            await self.send_system_msg(player, "You are not married!")
            return False

        spouse_id = rec.get_spouse_id(player.char_id)
        spouse = server.sessions.get(spouse_id)
        if not spouse:
            await self.send_system_msg(player, "Your spouse is currently offline.")
            return False

        # Warp player to spouse's coordinates
        await server.warp_player(player, spouse.map_id, spouse.x, spouse.y)
        await self.send_system_msg(player, f"Teleported directly to your spouse {spouse.char_name}!")
        return True

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_MARRIAGE_MANAGER = MarriageManager()
