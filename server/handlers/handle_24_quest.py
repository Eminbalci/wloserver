"""
Wonderland Online Quest Protocol & Status Synchronization Handler (AC 24)
Reverse-engineered from client decompile (aLogin.exe.1.c line 291205).
Processes quest state updates, quest acceptance requests, and step acknowledgments.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [24]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Quest State & Synchronization packets (AC 24)."""
    try:
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] AC 24 Quest packet. Sub={sub}")

        if sub == 5:  # Quest State / Accept / Status Request (aLogin.exe line 291205)
            quest_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            req_state = reader.read_8() if reader.remaining_bytes() >= 1 else 1

            logger.info(f"[{session.char_name}] AC 24:5 Quest state request: QuestID={quest_id}, State={req_state}")

            from server.quests import GLOBAL_QUEST_ENGINE
            # If player has active quest state, sync it
            if quest_id > 0:
                current_state = GLOBAL_QUEST_ENGINE.get_quest_state(session, quest_id)
                # Acknowledge quest state to client
                resp = (
                    PacketWriter()
                    .write_8(24)
                    .write_8(5)
                    .write_16(quest_id)
                    .write_8(int(current_state))
                )
                await session.send_packet(resp)
            else:
                # Refresh all active quests
                await GLOBAL_QUEST_ENGINE.send_quest_journal(session)

        elif sub == 1 or sub == 2:  # Step update ACK
            quest_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
            step = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            logger.info(f"[{session.char_name}] AC 24:{sub} Quest Step ACK: QuestID={quest_id}, Step={step}")
            await session.send_packet(PacketWriter().write_8(24).write_8(sub).write_16(quest_id).write_8(step))

        elif sub == 6:  # Pinned quest tracker update
            logger.info(f"[{session.char_name}] AC 24:6 Pinned quest tracker sync")
            # Echo ACK
            await session.send_packet(PacketWriter().write_8(24).write_8(6).write_8(1))

        else:
            logger.info(f"[{session.char_name}] Unhandled AC 24 Sub-Code: {sub}, payload: {reader.data.hex()}")
            await session.send_packet(PacketWriter().write_8(20).write_8(8))

    except Exception as e:
        logger.error(f"Error handling AC 24: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
