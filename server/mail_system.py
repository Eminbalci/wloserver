"""
Wonderland Online Mailbox & Attachment System (AC 30 / AC 31)
Ported from C# wlo.pserver.core/Game/PlayerRelated/Mail.cs
"""

import time
import sqlite3
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class MailMessage:
    mail_id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    subject: str
    content: str
    attached_gold: int = 0
    attached_item_id: int = 0
    attached_item_count: int = 0
    sent_date: float = field(default_factory=time.time)
    is_read: bool = False
    is_claimed: bool = False


class MailSystem:
    """Manages player in-game mailbox, attachments, and SQLite persistence."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS charmail (
                    mail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    sender_name VARCHAR(50) NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    content TEXT,
                    attached_gold INTEGER DEFAULT 0,
                    attached_item_id INTEGER DEFAULT 0,
                    attached_item_count INTEGER DEFAULT 0,
                    sent_date REAL,
                    is_read INTEGER DEFAULT 0,
                    is_claimed INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[MailSystem] DB Init Error: {e}")

    async def send_mail(
        self,
        server,
        sender,
        receiver_id: int,
        subject: str,
        content: str,
        gold: int = 0,
        item_id: int = 0,
        item_count: int = 0
    ) -> bool:
        if not sender or not subject or receiver_id == 0:
            return False

        # Validate gold attachment
        if gold > 0:
            if sender.gold < gold:
                await self.send_system_msg(sender, "Not enough gold to attach to mail!")
                return False
            sender.gold -= gold

        # Validate item attachment
        from server.gameserver import remove_item_at_slot, add_item_to_inventory
        if item_id > 0 and item_count > 0:
            rem = item_count
            for it in list(sender.inventory):
                if it.get("item_id") == item_id:
                    take = min(rem, it.get("amount", 1))
                    slot = it.get("slot")
                    if slot is not None:
                        remove_item_at_slot(sender, slot, take)
                    else:
                        it["amount"] = it.get("amount", 1) - take
                        if it["amount"] <= 0:
                            sender.inventory.remove(it)
                    rem -= take
                    if rem <= 0:
                        break
            if rem > 0:
                await self.send_system_msg(sender, "You do not have enough items to attach!")
                return False

        # Save to DB
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO charmail (
                    sender_id, sender_name, receiver_id, subject, content,
                    attached_gold, attached_item_id, attached_item_count,
                    sent_date, is_read, is_claimed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                sender.char_id, sender.char_name, receiver_id, subject, content,
                gold, item_id, item_count, time.time()
            ))
            mail_id = cur.lastrowid
            conn.commit()
            conn.close()

            # Refresh sender inventory/gold
            await sender.send_packet(server.build_inventory_packet(sender))
            await sender.send_packet(PacketWriter().write_8(26).write_8(4).write_32(sender.gold))
            await self.send_system_msg(sender, f"Mail '{subject}' sent successfully!")

            # Notify online recipient
            receiver_session = server.sessions.get(receiver_id)
            if receiver_session:
                notify_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"You have received a new mail from {sender.char_name}: '{subject}'!"
                )
                await receiver_session.send_packet(notify_pkt)

            logger.info(f"[MailSystem] Mail #{mail_id} sent from {sender.char_name} to Char #{receiver_id}.")
            return True
        except Exception as e:
            logger.error(f"[MailSystem] Error sending mail: {e}", exc_info=True)
            return False

    def get_inbox(self, receiver_id: int) -> List[MailMessage]:
        mails = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM charmail WHERE receiver_id = ? ORDER BY mail_id DESC LIMIT 30", (receiver_id,)).fetchall()
            for r in rows:
                mails.append(MailMessage(
                    mail_id=r["mail_id"],
                    sender_id=r["sender_id"],
                    sender_name=r["sender_name"],
                    receiver_id=r["receiver_id"],
                    subject=r["subject"],
                    content=r["content"] or "",
                    attached_gold=r["attached_gold"] or 0,
                    attached_item_id=r["attached_item_id"] or 0,
                    attached_item_count=r["attached_item_count"] or 0,
                    sent_date=r["sent_date"] or 0,
                    is_read=bool(r["is_read"]),
                    is_claimed=bool(r["is_claimed"])
                ))
            conn.close()
        except Exception as e:
            logger.error(f"[MailSystem] Error fetching inbox: {e}")
        return mails

    async def send_inbox_list(self, session):
        if not session:
            return

        mails = self.get_inbox(session.char_id)
        pkt = PacketWriter().write_8(30).write_8(1).write_16(len(mails))
        for m in mails:
            pkt.write_32(m.mail_id)
            pkt.write_string(m.sender_name)
            pkt.write_string(m.subject)
            pkt.write_bool(m.is_read)
            pkt.write_bool(m.is_claimed)
            pkt.write_32(m.attached_gold)
            pkt.write_16(m.attached_item_id)
            pkt.write_8(m.attached_item_count)

        await session.send_packet(pkt)

    async def claim_attachment(self, server, session, mail_id: int) -> bool:
        if not session:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM charmail WHERE mail_id = ? AND receiver_id = ?", (mail_id, session.char_id)).fetchone()
            if not row:
                conn.close()
                return False

            if bool(row["is_claimed"]):
                conn.close()
                await self.send_system_msg(session, "Attachment has already been claimed!")
                return False

            gold = int(row["attached_gold"] or 0)
            item_id = int(row["attached_item_id"] or 0)
            item_count = int(row["attached_item_count"] or 0)

            from server.gameserver import add_item_to_inventory
            if gold > 0:
                session.gold += gold
                await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))

            if item_id > 0 and item_count > 0:
                add_item_to_inventory(session, item_id, item_count)
                await session.send_packet(server.build_inventory_packet(session))

            conn.execute("UPDATE charmail SET is_claimed = 1, is_read = 1 WHERE mail_id = ?", (mail_id,))
            conn.commit()
            conn.close()

            # Ack claim
            ack_pkt = PacketWriter().write_8(30).write_8(3).write_32(mail_id).write_8(1)
            await session.send_packet(ack_pkt)
            await self.send_system_msg(session, f"Claimed attachment: +{gold} Gold, Item #{item_id} x{item_count}!")
            return True
        except Exception as e:
            logger.error(f"[MailSystem] Error claiming mail attachment: {e}", exc_info=True)
            return False

    async def delete_mail(self, session, mail_id: int):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM charmail WHERE mail_id = ? AND receiver_id = ?", (mail_id, session.char_id))
            conn.commit()
            conn.close()

            del_pkt = PacketWriter().write_8(31).write_8(1).write_32(mail_id)
            await session.send_packet(del_pkt)
        except Exception as e:
            logger.error(f"[MailSystem] Error deleting mail: {e}")

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_MAIL_SYSTEM = MailSystem()
