"""
Wonderland Online Map Weather & Environmental Atmospheric Engine (AC 57)
Ported from C# weather engine & AC57 handler
"""

import logging
from enum import IntEnum
from typing import Dict, Optional

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class WeatherType(IntEnum):
    CLEAR = 0
    RAIN = 1
    SNOW = 2
    SAKURA = 3
    FOG = 4
    THUNDERSTORM = 5


class WeatherManager:
    """Manages map-specific atmospheric and weather effects."""

    def __init__(self):
        # MapID -> (WeatherType, Intensity 1-10)
        self.map_weather: Dict[int, tuple] = {}
        self._load_weather()

    def _load_weather(self):
        self.map_weather.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_wth = GLOBAL_DYNAMIC_DATA.get_map_weather()
            for m_id, val in db_wth.items():
                if isinstance(val, tuple):
                    self.map_weather[m_id] = (WeatherType(val[0]), val[1])
                else:
                    self.map_weather[m_id] = (WeatherType(val), 3)
            logger.info(f"[WeatherManager] Loaded {len(self.map_weather)} dynamic weather maps from database.")
        except Exception as e:
            logger.warning(f"[WeatherManager] Fallback map weather: {e}")

        # Ensure baseline fallbacks if empty
        if not self.map_weather:
            self.map_weather = {
                10001: (WeatherType.RAIN, 3),      # Kelan Woods
                10036: (WeatherType.RAIN, 2),      # Shipwreck Beach
                14000: (WeatherType.SNOW, 5),      # South Pole Glaciers
                15000: (WeatherType.SAKURA, 4),    # Kyoto Cherry Blossoms
                16000: (WeatherType.FOG, 6),       # Ghost Ship Waters
                17000: (WeatherType.THUNDERSTORM, 8), # Bermuda Storm
            }

    def reload_from_db(self, dynamic_mgr=None):
        self._load_weather()

    def get_map_weather(self, map_id: int) -> tuple:
        return self.map_weather.get(map_id, (WeatherType.CLEAR, 0))

    async def send_map_weather(self, session, map_id: int):
        if not session:
            return

        w_type, intensity = self.get_map_weather(map_id)
        if w_type == WeatherType.CLEAR:
            return

        pkt = PacketWriter().write_8(57).write_8(1).write_8(int(w_type)).write_8(intensity)
        await session.send_packet(pkt)
        logger.debug(f"[WeatherManager] Sent weather {w_type.name} to {session.char_name} on Map {map_id}.")


GLOBAL_WEATHER_MANAGER = WeatherManager()
