"""
Wonderland Online Netcode Security & Anti-Cheat Engine
Ported from C# Network protection & speedcheck filters
"""

import time
import math
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger("WLO_Server")


class AntiCheatEngine:
    """Monitors packet frequency, movement velocity, and anomaly detection."""

    MAX_PACKETS_PER_SECOND: int = 40
    MAX_TILE_SPEED: float = 25.0  # Max tiles traversed per second (including mounts and lag bursts)

    def __init__(self):
        self._packet_counts: Dict[int, Tuple[float, int]] = {}   # CharID -> (last_reset, count)
        self._last_positions: Dict[int, Tuple[float, int, int]] = {} # CharID -> (timestamp, x, y)
        self._blacklisted_ips: set = set()

    def check_packet_flood(self, char_id: int) -> bool:
        """Returns True if rate is within allowed limits, False if flooding."""
        now = time.time()
        last_time, count = self._packet_counts.get(char_id, (now, 0))

        if (now - last_time) >= 1.0:
            self._packet_counts[char_id] = (now, 1)
            return True

        if count >= self.MAX_PACKETS_PER_SECOND:
            logger.warning(f"[AntiCheat] Char #{char_id} exceeded packet rate limit ({count} p/s)!")
            return False

        self._packet_counts[char_id] = (last_time, count + 1)
        return True

    def validate_movement_velocity(self, char_id: int, new_x: int, new_y: int) -> bool:
        """Checks for teleportation / speedhacking during grid movement."""
        now = time.time()
        if char_id not in self._last_positions:
            self._last_positions[char_id] = (now, new_x, new_y)
            return True

        last_time, old_x, old_y = self._last_positions[char_id]
        dt = max(0.05, now - last_time)

        # Distance in pixels (32px per tile)
        dx = new_x - old_x
        dy = new_y - old_y
        dist_tiles = math.sqrt(dx * dx + dy * dy) / 32.0

        speed = dist_tiles / dt
        self._last_positions[char_id] = (now, new_x, new_y)

        if speed > self.MAX_TILE_SPEED:
            logger.warning(f"[AntiCheat] Char #{char_id} suspicious speed detected: {speed:.1f} tiles/s (dt={dt:.2f}s)!")
            return False

        return True

    def update_position(self, char_id: int, x: int, y: int):
        self._last_positions[char_id] = (time.time(), x, y)


GLOBAL_ANTI_CHEAT = AntiCheatEngine()
