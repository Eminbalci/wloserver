import logging
from typing import TYPE_CHECKING
from server.network import PacketReader, PacketWriter

if TYPE_CHECKING:
    from server.gameserver import GameServer, PlayerSession

logger = logging.getLogger("WLO_Server")
ACTION_CODE = 32


async def handle(server: 'GameServer', session: 'PlayerSession', reader: PacketReader):
    """
    Handles Action Code 32: Player Emotes and Character Animations.
    Sub 1: Standard Emote (Wave, Bow, Cheer, Laugh, Cry, etc.)
    Sub 2: Character Action Pose (Sit, Rest, Special Animation)
    Sub 3: Reset / Cancel Emote
    """
    sub = reader.read_8()  # Sub Code

    if sub == 1:
        emote_id = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        session.emote = emote_id
        logger.info(f"[{session.char_name}] Performed Emote #{emote_id} (AC 32:1)")
        pkt = PacketWriter().write_8(32).write_8(1).write_32(session.char_id).write_8(emote_id)
        server.broadcast_to_map(session.map_id, pkt, exclude_session=session)

    elif sub == 2:
        action_id = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        session.emote = action_id
        logger.debug(f"[{session.char_name}] Performed Action/Pose #{action_id} (AC 32:2)")
        pkt = PacketWriter().write_8(32).write_8(2).write_32(session.char_id).write_8(action_id)
        server.broadcast_to_map(session.map_id, pkt, exclude_session=session)

    elif sub == 3:
        session.emote = 0
        logger.debug(f"[{session.char_name}] Canceled Emote/Pose (AC 32:3)")
        pkt = PacketWriter().write_8(32).write_8(3).write_32(session.char_id)
        server.broadcast_to_map(session.map_id, pkt, exclude_session=session)

    else:
        logger.debug(f"[{session.char_name}] Unhandled AC 32 Sub: {sub}")
