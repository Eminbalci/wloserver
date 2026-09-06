"""
Wonderland Online Marriage Ceremony & Couple Interaction Handler (AC 82 & AC 68)
Reverse-engineered from client decompile (aLogin.exe.1.c line 218810 btn_Marry_1, line 231482).
Handles marriage proposals, wedding ceremony, couple teleportation, and heart affinity.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter
from server.marriage_system import GLOBAL_MARRIAGE_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [82, 68]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Marriage and Couple packets (AC 82 and AC 68)."""
    try:
        action_code = reader.data[0] if len(reader.data) > 0 else 82
        sub = reader.read_8()
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Marriage packet. AC={action_code}, Sub={sub}")

        if action_code == 82:
            if sub == 10:  # Wedding ceremony trigger (btn_Marry_1 at church altar)
                logger.info(f"[{session.char_name}] AC 82:10 Wedding ceremony trigger")
                spouse_id = GLOBAL_MARRIAGE_MANAGER.get_spouse_id(session.char_id)
                spouse_session = server.sessions.get(spouse_id)
                if spouse_session and spouse_session.map_id == session.map_id:
                    # Broadcast wedding fireworks and bell animation (AC 5:5: 60050)
                    fx = PacketWriter().write_8(5).write_8(5).write_32(session.char_id).write_16(60050)
                    server.broadcast_to_map(session.map_id, fx)
                    # Send wedding system announcement
                    ann = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"[Holy Matrimony] {session.char_name} and {spouse_session.char_name} have tied the knot!"
                    )
                    server.broadcast_to_map(session.map_id, ann)
                    # Ceremony ACK (AC 82 Sub 10)
                    await session.send_packet(PacketWriter().write_8(82).write_8(10).write_8(1))
                    await spouse_session.send_packet(PacketWriter().write_8(82).write_8(10).write_8(1))
                else:
                    # Generic ACK
                    await session.send_packet(PacketWriter().write_8(82).write_8(10).write_8(1))

            elif sub == 3:  # Propose marriage
                target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
                logger.info(f"[{session.char_name}] AC 82:3 Proposal to TargetID={target_id}")
                target = server.sessions.get(target_id)
                if target:
                    await GLOBAL_MARRIAGE_MANAGER.propose(server, session, target)
                else:
                    await session.send_packet(PacketWriter().write_8(82).write_8(3).write_8(0))

            elif sub == 4:  # Proposal response (1 = accept, 0 = reject)
                accepted = (reader.read_8() == 1) if reader.remaining_bytes() >= 1 else False
                logger.info(f"[{session.char_name}] AC 82:4 Proposal response: accepted={accepted}")
                if accepted:
                    proposer_id = GLOBAL_MARRIAGE_MANAGER._pending_proposals.get(session.char_id)
                    proposer = server.sessions.get(proposer_id)
                    if proposer:
                        await GLOBAL_MARRIAGE_MANAGER.accept_proposal(server, session, proposer)
                else:
                    GLOBAL_MARRIAGE_MANAGER._pending_proposals.pop(session.char_id, None)
                    await session.send_packet(PacketWriter().write_8(82).write_8(4).write_8(0))

            elif sub == 8:  # Couple Action / Ring exchange ACK
                logger.info(f"[{session.char_name}] AC 82:8 Couple Action / Ring exchange")
                await session.send_packet(PacketWriter().write_8(82).write_8(8).write_8(1))

            else:
                logger.info(f"[{session.char_name}] Unhandled AC 82 Sub-Code: {sub}")
                await session.send_packet(PacketWriter().write_8(82).write_8(sub).write_8(1))

        elif action_code == 68:  # Couple Teleportation & Affinity
            if sub == 1:  # Couple teleport request
                logger.info(f"[{session.char_name}] AC 68:1 Couple teleport request")
                await GLOBAL_MARRIAGE_MANAGER.teleport_to_spouse(server, session)
                await session.send_packet(PacketWriter().write_8(68).write_8(1).write_8(1))

            elif sub == 2 or sub == 3:  # Affinity sync / heart emote
                logger.info(f"[{session.char_name}] AC 68:{sub} Couple affinity / heart animation")
                heart_fx = PacketWriter().write_8(32).write_8(1).write_32(session.char_id).write_8(15)
                server.broadcast_to_map(session.map_id, heart_fx)
                await session.send_packet(PacketWriter().write_8(68).write_8(sub).write_8(1))

            else:
                logger.info(f"[{session.char_name}] Unhandled AC 68 Sub-Code: {sub}")
                await session.send_packet(PacketWriter().write_8(68).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling Marriage AC 82/68: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
