"""
Wonderland Online Secondary Security PIN Lock (AC 226)
Ported from C# Security PIN validation handler
"""

import hashlib
import sqlite3
import logging
from typing import Dict, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class SecurityPinManager:
    """Manages secondary 6-digit security PIN passwords and action verification."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._unlocked_sessions: Dict[int, bool] = {}  # CharID -> is_unlocked
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_security (
                    char_id INTEGER PRIMARY KEY,
                    pin_hash VARCHAR(64) NOT NULL,
                    created_at REAL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SecurityPinManager] DB Init Error: {e}")

    def _hash_pin(self, pin: str) -> str:
        return hashlib.sha256(pin.encode("utf-8")).hexdigest()

    def is_pin_set(self, char_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT 1 FROM char_security WHERE char_id = ?", (char_id,)).fetchone()
            conn.close()
            return row is not None
        except Exception:
            return False

    def is_unlocked(self, char_id: int) -> bool:
        # If no PIN is configured, action is unlocked by default
        if not self.is_pin_set(char_id):
            return True
        return self._unlocked_sessions.get(char_id, False)

    async def set_pin(self, session, pin: str) -> bool:
        if not session or not pin or len(pin) != 6 or not pin.isdigit():
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("PIN must be exactly 6 digits!")
            await session.send_packet(sys_msg)
            return False

        pin_hash = self._hash_pin(pin)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO char_security (char_id, pin_hash, created_at)
                VALUES (?, ?, 0)
            """, (session.char_id, pin_hash))
            conn.commit()
            conn.close()

            self._unlocked_sessions[session.char_id] = True
            ack_pkt = PacketWriter().write_8(226).write_8(1).write_8(1)
            await session.send_packet(ack_pkt)
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "[Security] 6-digit Security PIN successfully set and activated!"
            )
            await session.send_packet(sys_msg)
            return True
        except Exception as e:
            logger.error(f"[SecurityPinManager] Error setting PIN: {e}")
            return False

    async def verify_pin(self, session, pin: str) -> bool:
        if not session or not pin:
            return False

        pin_hash = self._hash_pin(pin)
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT pin_hash FROM char_security WHERE char_id = ?", (session.char_id,)).fetchone()
            conn.close()

            if not row or row[0] != pin_hash:
                ack_pkt = PacketWriter().write_8(226).write_8(2).write_8(0)
                await session.send_packet(ack_pkt)
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Incorrect Security PIN!")
                await session.send_packet(sys_msg)
                return False

            self._unlocked_sessions[session.char_id] = True
            ack_pkt = PacketWriter().write_8(226).write_8(2).write_8(1)
            await session.send_packet(ack_pkt)
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "[Security] Security PIN verified! Protection unlocked for this session."
            )
            await session.send_packet(sys_msg)
            return True
        except Exception as e:
            logger.error(f"[SecurityPinManager] Error verifying PIN: {e}")
            return False


GLOBAL_SECURITY_PIN_MANAGER = SecurityPinManager()
