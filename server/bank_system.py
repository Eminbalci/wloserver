"""
Wonderland Online Bank Vault & Inventory Expansion System
Ported from C# Equip.cs and Character.cs bank/storage handlers
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class BankManager:
    """Manages player bank gold deposits/withdrawals, vault item storage, and inventory expansion."""

    MAX_INVENTORY_SLOTS: int = 50
    EXPANSION_BAG_ID: int = 38001

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_bank_gold (
                    char_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_bank_items (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    vault_slot INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    extra_data TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[BankManager] DB Init Error: {e}")

    def get_bank_gold(self, char_id: int) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute("SELECT gold FROM char_bank_gold WHERE char_id = ?", (char_id,)).fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception:
            return 0

    async def deposit_gold(self, server, player, amount: int) -> bool:
        if not player or amount <= 0 or player.gold < amount:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Invalid gold deposit amount!")
            await player.send_packet(sys_msg)
            return False

        player.gold -= amount
        current_bank = self.get_bank_gold(player.char_id)
        new_bank = current_bank + amount

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO char_bank_gold (char_id, gold)
                VALUES (?, ?)
            """, (player.char_id, new_bank))
            conn.commit()
            conn.close()

            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Bank Deposit] Deposited {amount} Gold. (Bank Balance: {new_bank} Gold)!"
            )
            await player.send_packet(sys_msg)
            server.save_player_to_db(player)
            return True
        except Exception as e:
            logger.error(f"[BankManager] Error depositing gold: {e}")
            return False

    async def withdraw_gold(self, server, player, amount: int) -> bool:
        if not player or amount <= 0:
            return False

        current_bank = self.get_bank_gold(player.char_id)
        if current_bank < amount:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Insufficient bank funds!")
            await player.send_packet(sys_msg)
            return False

        new_bank = current_bank - amount
        player.gold += amount

        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE char_bank_gold SET gold = ? WHERE char_id = ?", (new_bank, player.char_id))
            conn.commit()
            conn.close()

            await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Bank Withdrawal] Withdrew {amount} Gold. (Remaining Bank: {new_bank} Gold)!"
            )
            await player.send_packet(sys_msg)
            server.save_player_to_db(player)
            return True
        except Exception as e:
            logger.error(f"[BankManager] Error withdrawing gold: {e}")
            return False

    async def expand_inventory(self, server, player, bag_slot: int) -> bool:
        if not player:
            return False

        from server.gameserver import remove_item_at_slot

        cur_max = getattr(player, "max_inventory_slots", 25)
        if cur_max >= self.MAX_INVENTORY_SLOTS:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Your inventory is already at maximum capacity ({self.MAX_INVENTORY_SLOTS} slots)!"
            )
            await player.send_packet(sys_msg)
            return False

        # Consume Expansion Bag
        remove_item_at_slot(player, bag_slot, 1)

        player.max_inventory_slots = min(self.MAX_INVENTORY_SLOTS, cur_max + 5)

        # Broadcast spark effect (AC 5:5: 60050)
        spark = PacketWriter().write_8(5).write_8(5).write_32(player.char_id).write_16(60050)
        server.broadcast_to_map(player.map_id, spark)

        await player.send_packet(server.build_inventory_packet(player))
        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Inventory Expanded!] Maximum bag capacity increased to {player.max_inventory_slots} slots!"
        )
        await player.send_packet(sys_msg)
        server.save_player_to_db(player)
        return True


GLOBAL_BANK_MANAGER = BankManager()
