"""
Wonderland Online PvP Duel, Arena & PK / Jail System (AC 11 / AC 32)
Ported from C# wlo.pserver.core/Game/Battle/PvPManager.cs
"""

import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class DuelSession:
    challenger_id: int
    target_id: int
    started_at: float = 0.0


class PvPManager:
    """Manages 1v1 player duels, PK flags, PK penalties, and Jail sentences."""

    JAIL_MAP_ID: int = 60001
    JAIL_X: int = 400
    JAIL_Y: int = 350

    def __init__(self):
        self._pending_duels: Dict[int, int] = {}       # TargetID -> ChallengerID
        self._active_duels: Dict[int, DuelSession] = {} # CharID -> DuelSession
        self._pk_points: Dict[int, int] = {}           # CharID -> PK Points

    def request_duel(self, challenger, target) -> bool:
        if not challenger or not target or challenger.char_id == target.char_id:
            return False

        if getattr(challenger, "in_battle", False) or getattr(target, "in_battle", False):
            return False

        self._pending_duels[target.char_id] = challenger.char_id

        # Send duel invitation modal (AC 11 Sub 1)
        req_pkt = PacketWriter().write_8(11).write_8(1).write_32(challenger.char_id).write_string(challenger.char_name)
        target.send_packet_sync(req_pkt) if hasattr(target, "send_packet_sync") else None
        return True

    async def accept_duel(self, server, target) -> bool:
        if not target or target.char_id not in self._pending_duels:
            return False

        challenger_id = self._pending_duels.pop(target.char_id)
        challenger = server.sessions.get(challenger_id)
        if not challenger:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Your challenger is no longer online.")
            await target.send_packet(sys_msg)
            return False

        session = DuelSession(challenger_id=challenger.char_id, target_id=target.char_id, started_at=time.time())
        self._active_duels[challenger.char_id] = session
        self._active_duels[target.char_id] = session

        # Start Battle Initialization (AC 27)
        bg_id = challenger.map_id if challenger.map_id < 10000 else 1
        b_pkt1 = PacketWriter().write_8(27).write_16(bg_id).write_8(1).write_32(target.char_id)
        b_pkt2 = PacketWriter().write_8(27).write_16(bg_id).write_8(1).write_32(challenger.char_id)

        await challenger.send_packet(b_pkt1)
        await target.send_packet(b_pkt2)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[PvP Duel] Duel started between {challenger.char_name} and {target.char_name}!"
        )
        server.broadcast_to_map(challenger.map_id, sys_msg)
        logger.info(f"[PvPManager] Duel started: {challenger.char_name} vs {target.char_name}.")
        return True

    async def decline_duel(self, server, target):
        if not target or target.char_id not in self._pending_duels:
            return
        challenger_id = self._pending_duels.pop(target.char_id)
        challenger = server.sessions.get(challenger_id)
        if challenger:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"{target.char_name} declined your duel challenge."
            )
            await challenger.send_packet(sys_msg)

    async def toggle_pk_mode(self, server, player) -> bool:
        if not player:
            return False
        cur = getattr(player, "pk_mode", False)
        player.pk_mode = not cur

        mode_str = "ENABLED (Red Name)" if player.pk_mode else "DISABLED (White Name)"
        # Broadcast PK visual state (AC 32 Sub 1)
        pkt = PacketWriter().write_8(32).write_8(1).write_32(player.char_id).write_bool(player.pk_mode)
        server.broadcast_to_map(player.map_id, pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"[PK Mode] PK is now {mode_str}.")
        await player.send_packet(sys_msg)
        return player.pk_mode

    async def record_pk_kill(self, server, killer, victim):
        if not killer or not victim:
            return
        self._pk_points[killer.char_id] = self._pk_points.get(killer.char_id, 0) + 1
        pts = self._pk_points[killer.char_id]

        announce = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[PK Broadcast] {killer.char_name} has eliminated {victim.char_name} in open combat! (PK Points: {pts})"
        )
        server.broadcast_to_map(killer.map_id, announce)

        # If PK Points >= 3, jail killer
        if pts >= 3:
            await self.jail_player(server, killer)

    async def jail_player(self, server, player):
        if not player:
            return
        await server.warp_player(player, self.JAIL_MAP_ID, self.JAIL_X, self.JAIL_Y)
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            "[Imperial Guard] You have been arrested for excessive PK and sentenced to Jail!"
        )
        await player.send_packet(sys_msg)
        logger.warning(f"[PvPManager] Player {player.char_name} jailed for PK points.")


GLOBAL_PVP_MANAGER = PvPManager()
