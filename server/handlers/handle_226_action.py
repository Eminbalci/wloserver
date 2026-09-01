"""
Wonderland Online - Action Code 226 (Item Mall Matrix & State Sync) Handler
Ported from C# Src/Network/ActionCodes/AC226.cs
Handles:
- AC 226 Sub 255: Authentic WLO Item Mall Matrix (238:183) & State Sync (225:252)
"""

import logging
from server.network import PacketWriter

from server.security_pin import GLOBAL_SECURITY_PIN_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [226]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 1:
        # Set 6-digit Security PIN (AC 226 Sub 1)
        pin_str = reader.read_string() if reader.remaining_bytes() >= 2 else ""
        await GLOBAL_SECURITY_PIN_MANAGER.set_pin(session, pin_str)

    elif sub == 2:
        # Verify 6-digit Security PIN (AC 226 Sub 2)
        pin_str = reader.read_string() if reader.remaining_bytes() >= 2 else ""
        await GLOBAL_SECURITY_PIN_MANAGER.verify_pin(session, pin_str)

    elif sub == 255:
        # Authentic WLO Catalog Matrix (Packet #124, #141, #155 in itemmall.pcapng)
        s1 = PacketWriter()
        s1.write_8(238)
        s1.write_8(183)
        s1.write_8(0)
        s1.write_8(255)
        s1.write_16(27)
        s1.write_8(1)
        s1.write_16(29)
        s1.write_8(2)
        s1.write_16(24)
        s1.write_8(0)
        await session.send_packet(s1)

        # Authentic WLO Mall State / Claim Sync
        s2 = PacketWriter()
        s2.write_8(225)
        s2.write_8(252)
        s2.write_bytes(bytes(10))
        await session.send_packet(s2)

        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Dispatched Item Mall Matrix (238:183) & State (225:252)")
    else:
        logger.info(f"[AC226] Unhandled SubAction: {sub} from {getattr(session, 'char_name', 'Player')}")
