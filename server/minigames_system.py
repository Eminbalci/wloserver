"""
Wonderland Online Mini-Games & Lucky Draw Wheel System (AC 70 / AC 75 / AC 104)
Ported from C# Src/Network/ActionCodes/AC75.cs, AC104.cs and Gobang engine
"""

import random
import logging
from typing import Dict, List, Optional, Tuple, Any

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class LuckyDrawPrize(tuple):
    """Hybrid prize class supporting both tuple indexing and dict key access."""
    def __new__(cls, name: str, item_id: int, count: int = 1, weight: int = 100, is_jackpot: int = 0, category: int = 2, slot_index: int = 1):
        instance = super().__new__(cls, (name, item_id, count, weight))
        instance.name = name
        instance.item_id = item_id
        instance.count = count
        instance.weight = weight
        instance.is_jackpot = is_jackpot
        instance.category = category
        instance.slot_index = slot_index
        return instance

    def __getitem__(self, item):
        if isinstance(item, str):
            return getattr(self, item)
        return super().__getitem__(item)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class LuckyDrawManager:
    """Manages the Lucky Draw Wheel spins, prize weights, and server broadcasts."""

    def __init__(self):
        self.prizes: List[LuckyDrawPrize] = []
        self._load_prizes()

    def _load_prizes(self):
        self.prizes.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_prizes = GLOBAL_DYNAMIC_DATA.get_luckydraw_prizes()
            for p in db_prizes:
                cat = p.get("category", 2)
                slot = p.get("slot_index", (len(self.prizes) % 8) + 1)
                self.prizes.append(LuckyDrawPrize(
                    name=p["item_name"],
                    item_id=p["item_id"],
                    count=p.get("count", 1),
                    weight=p.get("weight", 100),
                    is_jackpot=p.get("is_jackpot", 0),
                    category=cat,
                    slot_index=slot,
                ))
            logger.info(f"[LuckyDrawManager] Loaded {len(self.prizes)} dynamic prizes from database.")
        except Exception as e:
            logger.warning(f"[LuckyDrawManager] Fallback prizes: {e}")

        # Ensure base fallbacks matching authentic client and pcaps
        if not self.prizes:
            self.prizes = [
                LuckyDrawPrize("Zodiac Crystal Chest", 48033, 1, 10, 1, 2, 3),
                LuckyDrawPrize("Space UFO", 48013, 1, 5, 1, 3, 4),
                LuckyDrawPrize("Reborn Hero Cape", 23001, 1, 20, 1, 2, 5),
                LuckyDrawPrize("Spar Crystal (+24 ATK)", 34124, 1, 80, 0, 3, 2),
                LuckyDrawPrize("Lucky Draw Gift Box", 34147, 1, 150, 0, 2, 1),
                LuckyDrawPrize("Refined Iron Ingot", 46005, 5, 120, 0, 2, 2),
                LuckyDrawPrize("Rice Ball Snack", 30025, 10, 300, 0, 2, 6),
                LuckyDrawPrize("Iron Ore Bundle", 27001, 10, 350, 0, 2, 7),
            ]

    def reload_from_db(self, dynamic_mgr=None):
        self._load_prizes()

    async def spin_wheel(self, server, player) -> Optional[Dict[str, Any]]:
        if not player:
            return None

        # 1. Check Inventory Space (Must have at least 1 empty slot)
        occupied = len([it for it in getattr(player, "inventory", []) if it.get("slot", 0) > 0])
        if occupied >= 50:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "Inventory full. Cannot use Lucky Draw."
            )
            await player.send_packet(sys_msg)
            return None

        from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

        # 2. Check Currency (20 IM Points, 1 Token, or 10,000 Gold)
        user_points = GLOBAL_ITEM_MALL_MANAGER.get_user_points(player)
        tokens = getattr(player, "im_tokens", 0)

        if user_points >= 20:
            rem_points = user_points - 20
            GLOBAL_ITEM_MALL_MANAGER.set_user_points(player, rem_points)
            p34 = PacketWriter().write_8(34).write_8(1).write_16(min(65535, rem_points))
            await player.send_packet(p34)
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(player)
        elif tokens >= 1:
            player.im_tokens -= 1
        elif player.gold >= 10000:
            player.gold -= 10000
            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
        else:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "You need at least 20 IM Points, 1 IM Token, or 10,000 Gold to play!"
            )
            await player.send_packet(sys_msg)
            return None

        # 3. Calculate weighted prize
        total_weight = sum(p["weight"] for p in self.prizes)
        roll = random.randint(1, total_weight)
        cur = 0
        selected = self.prizes[-1]

        for p in self.prizes:
            cur += p["weight"]
            if roll <= cur:
                selected = p
                break

        name = selected["name"]
        item_id = selected["item_id"]
        count = selected["count"]
        category = selected.get("category", 2)
        slot_index = selected.get("slot_index", 1)

        # 4. Add item to player inventory
        from server.gameserver import add_item_to_inventory
        if item_id > 0:
            add_item_to_inventory(player, item_id, count)
        else:
            player.gold += count
            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))

        # 5. Send authentic Lucky Draw Stop Packet (AC 104 Sub 1)
        # S->C [104, 1, 2, category (uint8), slot_index (uint8)] (5 bytes total, verified from pcap)
        stop_pkt = PacketWriter().write_8(104).write_8(1).write_8(2).write_8(category).write_8(slot_index)
        await player.send_packet(stop_pkt)

        # 6. Send authentic Item Delivery Packet (AC 23 Sub 6)
        # S->C [23, 6, item_id (uint16_LE), count (uint8), 28 zero bytes] (33 bytes total, verified from pcap)
        if item_id > 0:
            item_delivery_pkt = PacketWriter().write_8(23).write_8(6).write_16(item_id).write_8(min(255, int(count))).write_bytes(bytes(28))
            await player.send_packet(item_delivery_pkt)
            await player.send_packet(server.build_inventory_packet(player))

        # 7. Play celebration fireworks and map broadcast for jackpot
        if selected.get("is_jackpot") or item_id in (48013, 48033, 23001):
            player_map = getattr(player, "map_id", 0)
            if player_map and hasattr(server, "broadcast_to_map"):
                firework = PacketWriter().write_8(5).write_8(5).write_32(getattr(player, "char_id", 0)).write_16(60050)
                server.broadcast_to_map(player_map, firework)

                broadcast_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"[Lucky Draw Jackpot] Congratulations to {getattr(player, 'char_name', 'Player')} for winning '{name}' on the Lucky Wheel!"
                )
                server.broadcast_to_map(player_map, broadcast_msg)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Lucky Draw] You won {count}x {name}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[LuckyDraw] Player {player.char_name} won {name} (ID: {item_id} x{count}, Category: {category}, Slot: {slot_index}).")
        return selected


class GobangGame:
    """15x15 Gobang (Five in a Row) match between two players."""

    def __init__(self, p1, p2):
        self.player1 = p1  # Black (plays 1st)
        self.player2 = p2  # White
        self.board = [[0] * 15 for _ in range(15)]
        self.turn = p1.char_id
        self.winner: Optional[int] = None

    def make_move(self, char_id: int, r: int, c: int) -> Tuple[bool, bool]:
        """Returns (valid_move, is_win)."""
        if char_id != self.turn or not (0 <= r < 15 and 0 <= c < 15) or self.board[r][c] != 0:
            return False, False

        piece = 1 if char_id == self.player1.char_id else 2
        self.board[r][c] = piece

        if self._check_win(r, c, piece):
            self.winner = char_id
            return True, True

        # Switch turn
        self.turn = self.player2.char_id if char_id == self.player1.char_id else self.player1.char_id
        return True, False

    def _check_win(self, r: int, c: int, p: int) -> bool:
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            consecutive = 1
            # Forward
            for step in range(1, 5):
                nr, nc = r + dr * step, c + dc * step
                if 0 <= nr < 15 and 0 <= nc < 15 and self.board[nr][nc] == p:
                    consecutive += 1
                else:
                    break
            # Backward
            for step in range(1, 5):
                nr, nc = r - dr * step, c - dc * step
                if 0 <= nr < 15 and 0 <= nc < 15 and self.board[nr][nc] == p:
                    consecutive += 1
                else:
                    break

            if consecutive >= 5:
                return True
        return False


class GobangManager:
    """Manages active multiplayer Gobang board games."""

    def __init__(self):
        self.active_games: Dict[int, GobangGame] = {}  # CharID -> GobangGame

    def start_game(self, p1, p2) -> GobangGame:
        game = GobangGame(p1, p2)
        self.active_games[p1.char_id] = game
        self.active_games[p2.char_id] = game
        return game

    async def handle_move(self, server, player, row: int, col: int):
        if player.char_id not in self.active_games:
            return

        game = self.active_games[player.char_id]
        valid, won = game.make_move(player.char_id, row, col)
        if not valid:
            return

        partner = game.player2 if player == game.player1 else game.player1

        # Broadcast move (AC 104 Sub 2)
        move_pkt = PacketWriter().write_8(104).write_8(2).write_32(player.char_id).write_8(row).write_8(col)
        await player.send_packet(move_pkt)
        await partner.send_packet(move_pkt)

        if won:
            # Winner celebration
            win_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Gobang Match] {player.char_name} has achieved Five in a Row and won the match!"
            )
            await player.send_packet(win_msg)
            await partner.send_packet(win_msg)

            # Award winner 5,000 gold
            player.gold += 5000
            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))

            del self.active_games[player.char_id]
            del self.active_games[partner.char_id]


GLOBAL_LUCKY_DRAW = LuckyDrawManager()
GLOBAL_LUCKY_DRAW_MANAGER = GLOBAL_LUCKY_DRAW
GLOBAL_GOBANG_MANAGER = GobangManager()
