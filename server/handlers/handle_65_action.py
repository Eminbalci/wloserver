"""
Wonderland Online Tent World Action Handler (AC 65)
Ported from C# Src/Network/ActionCodes/AC65.cs
"""

import logging
from server.network import PacketWriter
from server.tent import GLOBAL_TENT_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [65]


async def handle(server, session, reader):
    """Handles Tent Actions (AC 65)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC65 Tent Handler. Sub={sub}")

    if sub == 1:  # Enter Tent Confirmation
        char_id = reader.read_32() if reader.remaining_bytes() >= 4 else session.char_id
        logger.info(f"[{session.char_name}] Enter Tent request for Char ID: {char_id}")
        await GLOBAL_TENT_MANAGER.open_tent(server, session)

    elif sub == 2:  # Right-click / Pack up tent on world map
        logger.info(f"[{session.char_name}] Packed up / closed tent on world map.")
        GLOBAL_TENT_MANAGER.pack_up_tent(server, session)

    elif sub == 3:  # Exit tent interior -> Warp player back to outside map
        logger.info(f"[{session.char_name}] Exiting tent interior.")
        await GLOBAL_TENT_MANAGER.close_tent(server, session)

    else:
        logger.info(f"Unhandled AC 65 Sub-Code: {sub}, payload: {reader.data.hex()}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
