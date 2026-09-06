"""
Wonderland Online Client Viewport & Entity Visibility Matrix Handler (AC 84)
Reverse-engineered from client decompile (aLogin.exe.1.c line 404989).
Handles viewport entity queries and map entity visibility refreshing.
"""

from __future__ import annotations

import logging
from typing import Any

from server.network import PacketReader, PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [84]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Processes Viewport & Entity Visibility packets (AC 84)."""
    try:
        sub = reader.read_8()
        logger.debug(f"[{getattr(session, 'char_name', 'Player')}] AC 84 Viewport refresh query. Sub={sub}")

        if sub == 1:
            # Client requesting nearby map entity update
            # Send ACK 84:1
            resp = PacketWriter().write_8(84).write_8(1).write_8(1)
            await session.send_packet(resp)

        else:
            await session.send_packet(PacketWriter().write_8(84).write_8(sub).write_8(1))

    except Exception as e:
        logger.error(f"Error handling AC 84: {e}", exc_info=True)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
