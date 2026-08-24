"""
Wonderland Online Mini-Game & Lucky Draw Handler (AC 75 / AC 104)
Ported from C# Src/Network/ActionCodes/AC75.cs and AC104.cs
"""

import logging
from server.network import PacketWriter
from server.minigames_system import GLOBAL_LUCKY_DRAW, GLOBAL_GOBANG_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [104]


async def handle(server, session, reader):
    """Processes Mini-Games and Lucky Draw Wheel (AC 104)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC104 MiniGame Sub={sub}")

    if sub == 1:  # Spin Request or Start Gobang
        if reader.remaining_bytes() >= 4:
            target_id = reader.read_32()
            target = server.sessions.get(target_id)
            if target:
                GLOBAL_GOBANG_MANAGER.start_game(session, target)
                start_pkt = PacketWriter().write_8(104).write_8(1).write_8(1)
                await session.send_packet(start_pkt)
                await target.send_packet(start_pkt)
        else:
            await GLOBAL_LUCKY_DRAW.spin_wheel(server, session)

    elif sub == 2:  # Gobang Move
        row = reader.read_8()
        col = reader.read_8()
        await GLOBAL_GOBANG_MANAGER.handle_move(server, session, row, col)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
