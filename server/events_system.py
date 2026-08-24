"""
Wonderland Online Scheduled Server Events & Double EXP Engine
Ported from client advanced events & server festival handlers
"""

import time
import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class EventManager:
    """Manages scheduled Double EXP events, Dragon Boat festivals, and server-wide multipliers."""

    def __init__(self):
        self._double_exp_active: bool = False
        self._double_exp_expires_at: float = 0.0

    def is_double_exp_active(self) -> bool:
        if not self._double_exp_active:
            return False
        if time.time() > self._double_exp_expires_at:
            self._double_exp_active = False
            return False
        return True

    def get_exp_multiplier(self) -> float:
        return 2.0 if self.is_double_exp_active() else 1.0

    async def start_double_exp_event(self, server, duration_hours: float = 2.0):
        self._double_exp_active = True
        self._double_exp_expires_at = time.time() + (duration_hours * 3600)

        # Global server marquee broadcast
        msg_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Special Event] Double EXP Event has begun! (Duration: {duration_hours} hours). Enjoy your adventure!"
        )
        for s in server.sessions.values():
            await s.send_packet(msg_pkt)
        logger.info(f"[EventManager] Started Double EXP event for {duration_hours} hours.")

    async def stop_double_exp_event(self, server):
        self._double_exp_active = False
        msg_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            "[Special Event] Double EXP Event has ended. Thank you for participating!"
        )
        for s in server.sessions.values():
            await s.send_packet(msg_pkt)
        logger.info("[EventManager] Stopped Double EXP event.")


GLOBAL_EVENT_MANAGER = EventManager()
