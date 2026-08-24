"""
Wonderland Online - Action Code 89 Handler
Ported from C# Src/Network/ActionCodes/AC89.cs
Handles:
- AC 89 Sub 0: Scene Readiness Acknowledgment -> Responds with AC 90:1 and dispatches MOTD
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [89]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 0:
        # S->C AC 90:1 [90, 1, 0, 1, 1, 3, 2, 3] (from itemmall.pcapng frame #2888 / AC89.cs)
        resp = PacketWriter().write_8(90).write_8(1).write_bytes(bytes([0, 1, 1, 3, 2, 3]))
        await session.send_packet(resp)
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Handled Scene Readiness AC 89 Sub 0 -> Sent AC 90:1")

        if not getattr(session, "motd_sent", False):
            session.motd_sent = True
            if hasattr(server, "dispatch_login_motd"):
                await server.dispatch_login_motd(session)
    else:
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Unhandled AC 89 SubCode: {sub}")
