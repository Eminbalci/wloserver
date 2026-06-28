import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [65]

async def handle(server, session, reader):
    """Handles Tent Actions (AC 65)."""
    sub = reader.read_8()
    
    if sub == 1:
        char_id = reader.read_32()
        logger.info(f"[{session.char_name}] Tent action [65, 1] for Char ID: {char_id}")
        
        # Depending on context, this could be closing the tent or confirming enter.
        # Currently, the server handles entering via AC 62 Sub 61, but the client sends this too.
        # We can just ignore it or echo it if necessary.
        pass
    else:
        logger.info(f"Unhandled AC 65 Sub-Code: {sub}, payload: {reader.data.hex()}")
