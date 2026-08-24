"""
Wonderland Online AFK Gathering System (Mining, Woodcutting & Fishing)
Ported from C# wlo.pserver.core/Game/Crafting/GatheringManager.cs
"""

import time
import random
import asyncio
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class GatheringType(IntEnum):
    NONE = 0
    FISHING = 1
    MINING = 2
    WOODCUTTING = 3


@dataclass
class GatheringSession:
    player: Any
    type: GatheringType
    start_time: float = field(default_factory=time.time)
    last_tick: float = field(default_factory=time.time)
    is_active: bool = True


class GatheringManager:
    """Manages continuous AFK resource gathering and item delivery."""

    def __init__(self):
        self._sessions: Dict[int, GatheringSession] = {}  # CharID -> GatheringSession
        self._fish_pool: List[int] = []
        self._ore_pool: List[int] = []
        self._wood_pool: List[int] = []
        self._worker_task: Optional[asyncio.Task] = None
        self._load_pools()

    def _load_pools(self):
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            f_rows = GLOBAL_DYNAMIC_DATA.get_gathering_pool(1)
            o_rows = GLOBAL_DYNAMIC_DATA.get_gathering_pool(2)
            w_rows = GLOBAL_DYNAMIC_DATA.get_gathering_pool(3)
            self._fish_pool = [r["item_id"] for r in f_rows] if f_rows else [30003, 30004, 30005, 30006, 30007]
            self._ore_pool = [r["item_id"] for r in o_rows] if o_rows else [27020, 27021, 27022, 27023, 27024]
            self._wood_pool = [r["item_id"] for r in w_rows] if w_rows else [27001, 27002, 27003, 27004, 27005]
            logger.info(f"[GatheringManager] Loaded dynamic gathering pools (Fish: {len(self._fish_pool)}, Ore: {len(self._ore_pool)}, Wood: {len(self._wood_pool)}).")
        except Exception as e:
            logger.warning(f"[GatheringManager] Fallback pools: {e}")
            self._fish_pool = [30003, 30004, 30005, 30006, 30007]
            self._ore_pool = [27020, 27021, 27022, 27023, 27024]
            self._wood_pool = [27001, 27002, 27003, 27004, 27005]

    def reload_from_db(self, dynamic_mgr=None):
        self._load_pools()

    def start_service(self, server):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._gather_loop(server))
            logger.info("[GatheringManager] AFK Gathering loop started (5s ticks).")

    async def _gather_loop(self, server):
        while True:
            try:
                await asyncio.sleep(5)
                for char_id, session in list(self._sessions.items()):
                    if not session.is_active or not session.player:
                        self._sessions.pop(char_id, None)
                        continue
                    await self._process_tick(server, session)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[GatheringManager] Error in gather loop: {e}", exc_info=True)

    async def start_gathering(self, server, player, gather_type: GatheringType) -> bool:
        if not player or gather_type == GatheringType.NONE:
            return False

        self.start_service(server)

        session = GatheringSession(player=player, type=gather_type)
        self._sessions[player.char_id] = session

        # Broadcast gathering action animation (AC 5 Sub 12 for Fishing, AC 5 Sub 14 for Mining/Woodcutting)
        anim_sub = 12 if gather_type == GatheringType.FISHING else 14
        action_pkt = PacketWriter().write_8(5).write_8(anim_sub).write_32(player.char_id)
        server.broadcast_to_map(player.map_id, action_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Started AFK {gather_type.name}! You will gather resources every 5 seconds while resting."
        )
        await player.send_packet(sys_msg)
        logger.info(f"[GatheringManager] Player {player.char_name} started {gather_type.name}.")
        return True

    async def stop_gathering(self, player):
        if not player:
            return

        session = self._sessions.pop(player.char_id, None)
        if session:
            session.is_active = False
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Stopped AFK {session.type.name}."
            )
            await player.send_packet(sys_msg)
            logger.info(f"[GatheringManager] Player {player.char_name} stopped gathering.")

    async def _process_tick(self, server, session: GatheringSession):
        player = session.player
        if not player:
            return

        # Select pool
        pool = self._fish_pool
        if session.type == GatheringType.MINING:
            pool = self._ore_pool
        elif session.type == GatheringType.WOODCUTTING:
            pool = self._wood_pool

        item_id = random.choice(pool)
        count = random.randint(1, 2)

        from server.gameserver import add_item_to_inventory
        add_item_to_inventory(player, item_id, count)

        # Notify player
        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[{session.type.name}] Gathered {count}x Item #{item_id}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)


GLOBAL_GATHERING_MANAGER = GatheringManager()
