"""
Wonderland Online Player Street Stall System (AC 40 / AC 56:30)
Ported from C# wlo.pserver.core/Game/PlayerRelated/StallManager.cs
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class StallItem:
    inventory_slot: int
    item_id: int
    price: int
    count: int


@dataclass
class PlayerStall:
    owner: Any
    stall_name: str
    items: List[StallItem] = field(default_factory=list)
    is_open: bool = True


class StallManager:
    """Manages player street shops and map vending banners."""

    def __init__(self):
        self._stalls: Dict[int, PlayerStall] = {}  # CharID -> PlayerStall

    def is_stall_open(self, char_id: int) -> bool:
        return char_id in self._stalls and self._stalls[char_id].is_open

    def get_stall(self, char_id: int) -> Optional[PlayerStall]:
        return self._stalls.get(char_id)

    async def open_stall(self, server, player, stall_name: str, items: List[StallItem]) -> bool:
        if not player or not items:
            return False

        stall = PlayerStall(owner=player, stall_name=stall_name, items=items)
        self._stalls[player.char_id] = stall

        # Broadcast Stall Banner / Sign on World Map (AC 56 Sub 30)
        sign_pkt = PacketWriter().write_8(56).write_8(30).write_32(player.char_id).write_string(stall_name)
        server.broadcast_to_map(player.map_id, sign_pkt)

        # Notify owner (AC 40:1)
        ack_pkt = PacketWriter().write_8(40).write_8(1).write_8(1)
        await player.send_packet(ack_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Your street stall '{stall_name}' is now open for business!"
        )
        await player.send_packet(sys_msg)
        logger.info(f"[StallManager] Player {player.char_name} opened stall '{stall_name}' with {len(items)} items.")
        return True

    async def close_stall(self, server, player):
        if not player or player.char_id not in self._stalls:
            return

        del self._stalls[player.char_id]

        # Remove Stall Banner from Map (AC 56:30 with empty string)
        sign_pkt = PacketWriter().write_8(56).write_8(30).write_32(player.char_id).write_string("")
        server.broadcast_to_map(player.map_id, sign_pkt)

        # Ack owner
        ack_pkt = PacketWriter().write_8(40).write_8(2).write_8(1)
        await player.send_packet(ack_pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Your stall has been closed.")
        await player.send_packet(sys_msg)
        logger.info(f"[StallManager] Player {player.char_name} closed their stall.")

    async def view_stall(self, buyer, seller_char_id: int):
        stall = self.get_stall(seller_char_id)
        if not stall or not stall.is_open:
            return

        # Send stall items list to buyer (AC 40:3)
        view_pkt = PacketWriter().write_8(40).write_8(3).write_32(seller_char_id).write_16(len(stall.items))
        for it in stall.items:
            view_pkt.write_8(it.inventory_slot).write_16(it.item_id).write_32(it.price).write_8(it.count)

        await buyer.send_packet(view_pkt)

    async def buy_item(self, server, buyer, seller_char_id: int, slot: int, count: int) -> bool:
        stall = self.get_stall(seller_char_id)
        if not stall or not stall.is_open:
            return False

        seller = stall.owner
        target_item = None
        for it in stall.items:
            if it.inventory_slot == slot:
                target_item = it
                break

        if not target_item:
            return False

        buy_count = min(count, target_item.count)
        total_price = target_item.price * buy_count

        if buyer.gold < total_price:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Not enough gold to purchase this item!")
            await buyer.send_packet(sys_msg)
            return False

        from server.gameserver import remove_item_at_slot, add_item_to_inventory

        # 1. Deduct Gold & transfer
        buyer.gold -= total_price
        seller.gold += total_price

        # 2. Transfer item
        remove_item_at_slot(seller, slot, buy_count)
        add_item_to_inventory(buyer, target_item.item_id, buy_count)

        target_item.count -= buy_count
        if target_item.count <= 0:
            stall.items.remove(target_item)

        # 3. Send updates
        await buyer.send_packet(server.build_inventory_packet(buyer))
        await buyer.send_packet(PacketWriter().write_8(26).write_8(4).write_32(buyer.gold))

        await seller.send_packet(server.build_inventory_packet(seller))
        await seller.send_packet(PacketWriter().write_8(26).write_8(4).write_32(seller.gold))

        buyer_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"Purchased {buy_count}x Item #{target_item.item_id} for {total_price} gold."
        )
        await buyer.send_packet(buyer_msg)

        seller_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"{buyer.char_name} bought {buy_count}x Item #{target_item.item_id} from your stall (+{total_price} gold)!"
        )
        await seller.send_packet(seller_msg)

        server.save_player_to_db(buyer)
        server.save_player_to_db(seller)
        logger.info(f"[StallManager] {buyer.char_name} bought {buy_count}x item #{target_item.item_id} from {seller.char_name} for {total_price}g.")
        return True


GLOBAL_STALL_MANAGER = StallManager()
