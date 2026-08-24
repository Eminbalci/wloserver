"""
Wonderland Online Character Appearance, Barber & Morph Handler (AC 21)
Ported from C# Src/Network/ActionCodes/AC21.cs
"""

import logging
from server.network import PacketWriter
from server.barber_system import GLOBAL_BARBER_MANAGER
from server.morph_system import GLOBAL_MORPH_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [21]


async def handle(server, session, reader):
    """Processes hairstyle, dyeing, and monster morphs (AC 21)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC21 Appearance Handler. Sub={sub}")

    if sub == 1:  # Barber Hair Styling
        style = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        color = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        await GLOBAL_BARBER_MANAGER.change_hair_style(server, session, style, color)

    elif sub == 2:  # Clothing Dye
        slot = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        color = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        await GLOBAL_BARBER_MANAGER.dye_clothing(server, session, slot, color)

    elif sub == 10:  # Monster Morph / Disguise
        item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        if item_id > 0:
            await GLOBAL_MORPH_MANAGER.transform_player(server, session, item_id)
        else:
            await GLOBAL_MORPH_MANAGER.untransform_player(server, session)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
