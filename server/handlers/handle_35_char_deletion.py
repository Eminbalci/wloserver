"""
Wonderland Online Character Deletion Handler (AC 35)
Ported from C# Src/Network/ActionCodes/AC35.cs
"""

import sqlite3
import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [35]


async def handle(server, session, reader):
    """Processes character deletion requests with security delete code (AC 35)."""
    sub = reader.read_8()
    logger.info(f"[{getattr(session, 'username', 'User')}] AC35 Char Deletion. Sub={sub}")

    if sub == 2:  # Official WLO Character Deletion Request (AC 35 Sub 2)
        slot = reader.read_8() if reader.remaining() >= 1 else 1
        uknw = reader.read_string() if reader.remaining() >= 1 else ""
        pw = reader.read_string() if reader.remaining() >= 1 else ""

        user_id = getattr(session, "user_id", 0)
        user_cipher = getattr(session, "cipher", "")

        # Allow deletion if:
        # 1. Cipher is empty/null (not set yet)
        # 2. Cipher matches the provided deletion password
        cipher_matches = not user_cipher or (user_cipher.strip() == pw.strip())

        logger.info(f"[CharDeletion] User #{user_id} slot {slot} requested delete. Cipher match: {cipher_matches}")

        if cipher_matches and user_id:
            try:
                # Delete character in database
                with server.db.get_connection() as conn:
                    char_row = conn.execute("SELECT id FROM characters WHERE user_id = ? AND slot = ?", (user_id, slot)).fetchone()
                    if char_row:
                        char_id = char_row["id"]
                        conn.execute("DELETE FROM characters WHERE id = ?", (char_id,))
                        conn.execute("DELETE FROM chartent WHERE charID = ?", (char_id,))
                        conn.execute("DELETE FROM chartent_items WHERE charID = ?", (char_id,))
                        conn.execute("DELETE FROM charquest WHERE charID = ?", (char_id,))
                        conn.execute("DELETE FROM charchests WHERE char_id = ?", (char_id,))
                        conn.execute("DELETE FROM char_titles WHERE char_id = ?", (char_id,))
                        conn.execute("DELETE FROM char_instances WHERE char_id = ?", (char_id,))
                        conn.commit()

                    # If all characters deleted, clear cipher
                    remaining = conn.execute("SELECT COUNT(*) FROM characters WHERE user_id = ?", (user_id,)).fetchone()[0]
                    if remaining == 0:
                        conn.execute("UPDATE users SET char_delete_code = '' WHERE id = ?", (user_id,))
                        conn.commit()
                        session.cipher = ""

                # Authentic WLO AC24 + AC20 + AC35 Deletion Handshake
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(53).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(52).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(54).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(183).write_8(0))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))

                # AC 35 Sub 2 [1, slot] -> Success
                success_pkt = PacketWriter().write_8(35).write_8(2).write_8(1).write_8(slot)
                await session.send_packet(success_pkt)
                logger.info(f"[CharDeletion] Deleted character slot {slot} for user #{user_id}.")
            except Exception as e:
                logger.error(f"[CharDeletion] Error deleting character: {e}")
                # AC 35 Sub 2 [3, slot] -> Error
                fail_pkt = PacketWriter().write_8(35).write_8(2).write_8(3).write_8(slot)
                await session.send_packet(fail_pkt)
        else:
            # Cipher mismatch / Error
            fail_pkt = PacketWriter().write_8(35).write_8(2).write_8(3).write_8(slot)
            await session.send_packet(fail_pkt)
    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
