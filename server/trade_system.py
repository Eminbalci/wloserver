"""
Wonderland Online Secure P2P Trading System (AC 25 / AC 29)
Ported from C# wlo.pserver.core/Game/PlayerRelated/Trade.cs
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class TradeOfferItem:
    inventory_slot: int
    item_id: int
    count: int


@dataclass
class TradeSession:
    player1: Any = None
    player2: Any = None
    gold1: int = 0
    gold2: int = 0
    items1: List[TradeOfferItem] = field(default_factory=list)
    items2: List[TradeOfferItem] = field(default_factory=list)
    locked1: bool = False
    locked2: bool = False
    accepted1: bool = False
    accepted2: bool = False

    def get_partner(self, p):
        return self.player2 if p == self.player1 else self.player1

    def get_items(self, p):
        return self.items1 if p == self.player1 else self.items2

    def get_partner_items(self, p):
        return self.items2 if p == self.player1 else self.items1


class TradeSystem:
    """Manages two-phase secure player-to-player trading."""

    def __init__(self):
        self._active_trades: Dict[int, TradeSession] = {}  # CharID -> TradeSession
        self._pending_requests: Dict[int, int] = {}       # TargetID -> RequesterID

    async def request_trade(self, requester, target):
        if not requester or not target or requester.char_id == target.char_id:
            return

        # Security PIN lock check (FUN_001d9f08: "Target uses Secure Lock")
        from server.security_pin import GLOBAL_SECURITY_PIN_MANAGER
        if not GLOBAL_SECURITY_PIN_MANAGER.is_unlocked(requester.char_id):
            await self.send_system_msg(requester, "You must unlock your Secondary Security PIN before trading!")
            return

        if not GLOBAL_SECURITY_PIN_MANAGER.is_unlocked(target.char_id):
            await self.send_system_msg(requester, f"{target.char_name} has Security Lock active!")
            return

        if requester.char_id in self._active_trades or target.char_id in self._active_trades:
            await self.send_system_msg(requester, "Either you or the other player is already trading!")
            return

        self._pending_requests[target.char_id] = requester.char_id

        # Send trade invitation prompt to target (AC 25:1)
        req_pkt = PacketWriter().write_8(25).write_8(1).write_32(requester.char_id)
        await target.send_packet(req_pkt)
        await self.send_system_msg(requester, f"Trade request sent to {target.char_name}.")
        logger.info(f"[Trade] {requester.char_name} requested trade with {target.char_name}.")

    async def accept_trade(self, server, target):
        if not target or target.char_id not in self._pending_requests:
            return

        requester_id = self._pending_requests.pop(target.char_id)
        requester = server.sessions.get(requester_id)
        if not requester:
            await self.send_system_msg(target, "Trading partner is no longer available.")
            return

        # Start active trade session
        session = TradeSession(player1=requester, player2=target)
        self._active_trades[requester.char_id] = session
        self._active_trades[target.char_id] = session

        # Open trade windows (AC 25:2)
        open1 = PacketWriter().write_8(25).write_8(2).write_32(target.char_id)
        open2 = PacketWriter().write_8(25).write_8(2).write_32(requester.char_id)
        await requester.send_packet(open1)
        await target.send_packet(open2)

        logger.info(f"[Trade] Trade session started between {requester.char_name} and {target.char_name}.")

    async def add_item_to_trade(self, player, slot: int, item_id: int, count: int):
        if player.char_id not in self._active_trades:
            return

        trade = self._active_trades[player.char_id]
        if (player == trade.player1 and trade.locked1) or (player == trade.player2 and trade.locked2):
            return

        items = trade.get_items(player)
        items.append(TradeOfferItem(inventory_slot=slot, item_id=item_id, count=count))

        # Sync offer to trading partner (AC 25:3)
        partner = trade.get_partner(player)
        sync_pkt = PacketWriter().write_8(25).write_8(3).write_8(slot).write_16(item_id).write_8(count)
        await partner.send_packet(sync_pkt)

    async def set_gold(self, player, gold_amount: int):
        if player.char_id not in self._active_trades:
            return

        trade = self._active_trades[player.char_id]
        if player == trade.player1:
            trade.gold1 = min(player.gold, max(0, gold_amount))
        else:
            trade.gold2 = min(player.gold, max(0, gold_amount))

        partner = trade.get_partner(player)
        gold_pkt = PacketWriter().write_8(25).write_8(4).write_32(gold_amount)
        await partner.send_packet(gold_pkt)

    async def lock_trade(self, player):
        if player.char_id not in self._active_trades:
            return

        trade = self._active_trades[player.char_id]
        if player == trade.player1:
            trade.locked1 = True
        else:
            trade.locked2 = True

        partner = trade.get_partner(player)
        lock_pkt = PacketWriter().write_8(25).write_8(5).write_8(1)
        await partner.send_packet(lock_pkt)

    async def confirm_trade(self, server, player):
        if player.char_id not in self._active_trades:
            return

        trade = self._active_trades[player.char_id]
        if not (trade.locked1 and trade.locked2):
            await self.send_system_msg(player, "Both players must lock their offers before confirming!")
            return

        if player == trade.player1:
            trade.accepted1 = True
        else:
            trade.accepted2 = True

        if trade.accepted1 and trade.accepted2:
            # Execute exchange!
            await self._finalize_trade(server, trade)

    async def _finalize_trade(self, server, trade: TradeSession):
        p1 = trade.player1
        p2 = trade.player2

        from server.gameserver import remove_item_at_slot, add_item_to_inventory

        # 1. Exchange Gold
        if trade.gold1 > 0:
            p1.gold -= trade.gold1
            p2.gold += trade.gold1
        if trade.gold2 > 0:
            p2.gold -= trade.gold2
            p1.gold += trade.gold2

        # 2. Transfer Player 1's items to Player 2
        for it in trade.items1:
            remove_item_at_slot(p1, it.inventory_slot, it.count)
            add_item_to_inventory(p2, it.item_id, it.count)

        # 3. Transfer Player 2's items to Player 1
        for it in trade.items2:
            remove_item_at_slot(p2, it.inventory_slot, it.count)
            add_item_to_inventory(p1, it.item_id, it.count)

        # 4. Notify both players of success (AC 25:6)
        success_pkt = PacketWriter().write_8(25).write_8(6).write_8(1)
        await p1.send_packet(success_pkt)
        await p2.send_packet(success_pkt)

        # 5. Refresh inventories & gold
        await p1.send_packet(server.build_inventory_packet(p1))
        await p2.send_packet(server.build_inventory_packet(p2))
        await p1.send_packet(PacketWriter().write_8(26).write_8(4).write_32(p1.gold))
        await p2.send_packet(PacketWriter().write_8(26).write_8(4).write_32(p2.gold))

        del self._active_trades[p1.char_id]
        del self._active_trades[p2.char_id]

        server.save_player_to_db(p1)
        server.save_player_to_db(p2)
        logger.info(f"[Trade] Trade finalized successfully between {p1.char_name} and {p2.char_name}.")

    async def cancel_trade(self, player):
        if player.char_id in self._active_trades:
            trade = self._active_trades.pop(player.char_id)
            partner = trade.get_partner(player)
            if partner.char_id in self._active_trades:
                del self._active_trades[partner.char_id]

            cancel_pkt = PacketWriter().write_8(25).write_8(7).write_8(1)
            await player.send_packet(cancel_pkt)
            await partner.send_packet(cancel_pkt)
            logger.info(f"[Trade] Trade cancelled by {player.char_name}.")

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_TRADE_SYSTEM = TradeSystem()
