"""
Wonderland Online Mini-Games & Lucky Draw Wheel System (AC 70 / AC 75 / AC 104)
Ported from C# Src/Network/ActionCodes/AC75.cs, AC104.cs and Gobang engine
"""

import random
import logging
from typing import Dict, List, Optional, Tuple

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class LuckyDrawManager:
    """Manages the Lucky Draw Wheel spins, prize weights, and server broadcasts."""

    def __init__(self):
        self.prizes: List[Tuple[str, int, int, int]] = []
        self._load_prizes()

    def _load_prizes(self):
        self.prizes.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_prizes = GLOBAL_DYNAMIC_DATA.get_luckydraw_prizes()
            for p in db_prizes:
                self.prizes.append((p["item_name"], p["item_id"], p.get("count", 1), p.get("weight", 100)))
            logger.info(f"[LuckyDrawManager] Loaded {len(self.prizes)} dynamic prizes from database.")
        except Exception as e:
            logger.warning(f"[LuckyDrawManager] Fallback prizes: {e}")

        # Ensure base fallbacks if empty
        if not self.prizes:
            self.prizes = [
                ("Zodiac Crystal Chest", 48033, 1, 10),
                ("Reborn Hero Cape", 23001, 1, 20),
                ("100,000 Gold Voucher", 0, 100000, 50),
                ("Refined Iron Ingot", 46005, 5, 120),
                ("Fine Silk Cloth", 30014, 5, 150),
                ("Rice Ball Snack", 30025, 10, 300),
                ("Iron Ore Bundle", 27001, 10, 350),
            ]

    def reload_from_db(self, dynamic_mgr=None):
        self._load_prizes()

    async def spin_wheel(self, server, player) -> Optional[Tuple[str, int, int]]:
        if not player:
            return None

        # Check IM tokens or Gold
        tokens = getattr(player, "im_tokens", 0)
        if tokens >= 1:
            player.im_tokens -= 1
        elif player.gold >= 10000:
            player.gold -= 10000
            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
        else:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                "You need at least 1 IM Token or 10,000 Gold to spin the Lucky Draw Wheel!"
            )
            await player.send_packet(sys_msg)
            return None

        # Calculate weighted prize
        total_weight = sum(p[3] for p in self.prizes)
        roll = random.randint(1, total_weight)
        cur = 0
        selected = self.prizes[-1]

        for p in self.prizes:
            cur += p[3]
            if roll <= cur:
                selected = p
                break

        name, item_id, count, _ = selected

        from server.gameserver import add_item_to_inventory
        if item_id > 0:
            add_item_to_inventory(player, item_id, count)
        else:
            player.gold += count
            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))

        # Send wheel spin response (AC 75 Sub 1)
        wheel_pkt = PacketWriter().write_8(75).write_8(1).write_16(item_id).write_16(count)
        await player.send_packet(wheel_pkt)
        await player.send_packet(server.build_inventory_packet(player))

        # Play celebration fireworks for top prizes
        if item_id in (48033, 23001):
            firework = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
            server.broadcast_to_map(player.map_id, firework)

            broadcast_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Lucky Draw Jackpot] Congratulations to {player.char_name} for winning '{name}' on the Lucky Wheel!"
            )
            server.broadcast_to_map(player.map_id, broadcast_msg)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Lucky Draw] You won {count}x {name}!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        logger.info(f"[LuckyDraw] Player {player.char_name} won {name} ({item_id} x{count}).")
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
