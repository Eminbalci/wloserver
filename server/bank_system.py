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

    def get_vault_items(self, char_id: int) -> list:
        """Retrieves stored vault items for the specified character."""
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT vault_slot, item_id, count, extra_data FROM char_bank_items WHERE char_id = ? ORDER BY vault_slot ASC",
                (char_id,)
            ).fetchall()
            conn.close()
            items = []
            for r in rows:
                items.append({
                    "vault_slot": r[0],
                    "item_id": r[1],
                    "count": r[2],
                    "extra_data": r[3] or ""
                })
            return items
        except Exception as e:
            logger.error(f"[BankManager] Error getting vault items: {e}")
            return []

    async def deposit_item(self, server, player, inv_slot: int, amount: int = 1) -> bool:
        """Deposits an item from player inventory into the Props Keeper vault."""
        if not player or inv_slot <= 0 or amount <= 0:
            return False

        from server.gameserver import get_item_at_slot, remove_item_at_slot

        item = get_item_at_slot(player, inv_slot)
        if not item:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item not found in inventory!")
            await player.send_packet(sys_msg)
            return False

        item_id = item.get("item_id", 0)
        curr_amt = item.get("amount", 1)
        if curr_amt < amount:
            amount = curr_amt

        # Check vault capacity
        vault_items = self.get_vault_items(player.char_id)
        if len(vault_items) >= 50:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Props Keeper storage is full!")
            await player.send_packet(sys_msg)
            return False

        # Find existing stack or next available slot
        target_slot = None
        for v in vault_items:
            if v["item_id"] == item_id and v["count"] + amount <= 999:
                target_slot = v["vault_slot"]
                break

        if target_slot is None:
            used_slots = {v["vault_slot"] for v in vault_items}
            for s in range(1, 51):
                if s not in used_slots:
                    target_slot = s
                    break

        if target_slot is None:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("No free slot in Props Keeper storage!")
            await player.send_packet(sys_msg)
            return False

        # Remove from inventory
        remove_item_at_slot(player, inv_slot, amount)

        # Save to DB
        try:
            conn = sqlite3.connect(self.db_path)
            existing = conn.execute(
                "SELECT count FROM char_bank_items WHERE char_id = ? AND vault_slot = ?",
                (player.char_id, target_slot)
            ).fetchone()

            if existing:
                new_cnt = existing[0] + amount
                conn.execute(
                    "UPDATE char_bank_items SET count = ? WHERE char_id = ? AND vault_slot = ?",
                    (new_cnt, player.char_id, target_slot)
                )
            else:
                conn.execute(
                    "INSERT INTO char_bank_items (char_id, vault_slot, item_id, count, extra_data) VALUES (?, ?, ?, ?, ?)",
                    (player.char_id, target_slot, item_id, amount, "")
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[BankManager] DB error depositing item: {e}")
            return False

        # Sync inventory & vault
        await player.send_packet(server.build_inventory_packet(player))
        await player.send_packet(self.build_vault_packet(player))
        server.save_player_to_db(player)
        logger.info(f"[{player.char_name}] Deposited Item #{item_id} x{amount} into Keeper Slot {target_slot}.")
        return True

    async def withdraw_item(self, server, player, vault_slot: int, amount: int = 1) -> bool:
        """Withdraws an item from Props Keeper vault into player inventory."""
        if not player or vault_slot <= 0 or amount <= 0:
            return False

        from server.gameserver import add_item_to_inventory

        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT item_id, count FROM char_bank_items WHERE char_id = ? AND vault_slot = ?",
                (player.char_id, vault_slot)
            ).fetchone()

            if not row:
                conn.close()
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item not found in Props Keeper!")
                await player.send_packet(sys_msg)
                return False

            item_id, current_cnt = row[0], row[1]
            withdraw_cnt = min(amount, current_cnt)

            actual_slot = add_item_to_inventory(player, item_id, amount=withdraw_cnt)
            if actual_slot is None:
                conn.close()
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Inventory is full!")
                await player.send_packet(sys_msg)
                return False

            if current_cnt <= withdraw_cnt:
                conn.execute(
                    "DELETE FROM char_bank_items WHERE char_id = ? AND vault_slot = ?",
                    (player.char_id, vault_slot)
                )
            else:
                conn.execute(
                    "UPDATE char_bank_items SET count = ? WHERE char_id = ? AND vault_slot = ?",
                    (current_cnt - withdraw_cnt, player.char_id, vault_slot)
                )
            conn.commit()
            conn.close()

            # Sync inventory & vault
            await player.send_packet(server.build_inventory_packet(player))
            await player.send_packet(self.build_vault_packet(player))
            server.save_player_to_db(player)
            logger.info(f"[{player.char_name}] Withdrew Item #{item_id} x{withdraw_cnt} from Keeper Slot {vault_slot}.")
            return True
        except Exception as e:
            logger.error(f"[BankManager] DB error withdrawing item: {e}")
            return False

    def build_vault_packet(self, player) -> PacketWriter:
        """Serializes stored Keeper vault items (AC 29 Sub 6 + Sub 5 items sync)."""
        p = PacketWriter()
        p.write_8(29).write_8(5)
        items = self.get_vault_items(player.char_id)
        p.write_8(len(items))
        for it in items:
            p.write_8(it["vault_slot"])
            p.write_16(it["item_id"])
            p.write_16(it["count"])
            p.write_8(0)  # damage
            p.write_bytes(bytes(25))
        return p


GLOBAL_BANK_MANAGER = BankManager()
