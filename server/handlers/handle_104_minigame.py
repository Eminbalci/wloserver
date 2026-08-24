"""
Wonderland Online Mini-Game & Lucky Draw Handler (AC 75 / AC 104)
Ported from C# Src/Network/ActionCodes/AC75.cs and AC104.cs
"""

import logging
from server.network import PacketWriter
from server.minigames_system import GLOBAL_LUCKY_DRAW, GLOBAL_GOBANG_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [75, 104]


async def handle(server, session, reader):
    """Processes Mini-Games and Lucky Draw Wheel (AC 75, AC 104)."""
    opcode = reader.data[0] if len(reader.data) > 0 else 75

    if opcode == 75:  # Lucky Draw Wheel
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC75 Lucky Draw Sub={sub}")
        if sub in (1, 8):  # Spin Request
            await GLOBAL_LUCKY_DRAW.spin_wheel(server, session)
        else:
            await session.send_packet(PacketWriter().write_8(75).write_8(sub).write_8(1))

    elif opcode == 104:  # Gobang Board Game
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] AC104 MiniGame Sub={sub}")
        if sub == 1:  # Start Game Request
            target_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
            target = server.sessions.get(target_id)
            if target:
                GLOBAL_GOBANG_MANAGER.start_game(session, target)
                start_pkt = PacketWriter().write_8(104).write_8(1).write_8(1)
                await session.send_packet(start_pkt)
                await target.send_packet(start_pkt)

        elif sub == 2:  # Make Move
            row = reader.read_8()
            col = reader.read_8()
            await GLOBAL_GOBANG_MANAGER.handle_move(server, session, row, col)

        else:
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
