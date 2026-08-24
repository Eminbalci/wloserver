"""
Wonderland Online - Action Code 92 Handler
Ported from C# Src/Network/ActionCodes/AC92.cs
Handles:
- AC 92 Sub 1: Map Scene Finalization ACK -> Triggers Login MOTD dispatch if not sent yet
"""

import logging

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [92]


async def handle(server, session, reader):
    sub = reader.read_8()

    logger.info(f"[{getattr(session, 'char_name', 'Player')}] Handled Map Scene Finalization AC 92 Sub {sub}")

    if not getattr(session, "motd_sent", False):
        session.motd_sent = True
        if hasattr(server, "dispatch_login_motd"):
            await server.dispatch_login_motd(session)
