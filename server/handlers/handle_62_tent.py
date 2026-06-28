import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [62]

async def handle(server, session, reader):
    """Handles Tent interior and furniture actions (AC 62)."""
    sub = reader.read_8()
    
    if sub == 61:  # Enter Tent Request
        # Payload: [62, 61, 01 00 00 00, 'BGM0011']
        unk = reader.read_32()
        bgm = reader.read_string_n()
        logger.info(f"[{session.char_name}] Requesting to enter tent (BGM: {bgm})")
        
        # Warp player to tent interior. 
        # Typically, map 12000 is the tent interior map.
        session.map_id = 12000
        session.x = 400
        session.y = 400
        
        # In a real setup, we would warp the player properly. 
        # For now, we manually send the tent interior data.
        
        # Server responds with:
        # 1. AC 35 Sub 12 (Unknown) - skip for now or send generic
        # 2. AC 12 Sub 163 (Warp to interior)
        # 3. AC 62 Sub 7
        # 4. AC 62 Sub 4 (Furniture data)
        # 5. AC 62 Sub 59 (BGM update)
        
        warp_pkt = PacketWriter().write_8(12).write_8(163)
        warp_pkt.write_32(session.char_id)
        warp_pkt.write_16(12000) # Map ID
        warp_pkt.write_16(session.x)
        warp_pkt.write_16(session.y)
        warp_pkt.write_32(0) # Padding
        await session.send_packet(warp_pkt)
        
        # Tent properties
        await session.send_packet(PacketWriter().write_8(62).write_8(7).write_16(0))
        
        # Furniture data [62, 4]
        # Format: [62, 4, char_id(4), count(2), ...furniture items]
        furn_pkt = PacketWriter().write_8(62).write_8(4)
        furn_pkt.write_32(session.char_id)
        furn_pkt.write_16(0) # 0 furniture for now
        await session.send_packet(furn_pkt)
        
        # BGM Update
        bgm_pkt = PacketWriter().write_8(62).write_8(59)
        bgm_pkt.write_16(257) # Unknown flags
        bgm_pkt.write_32(0)
        bgm_pkt.write_string_n("BGM0011")
        await session.send_packet(bgm_pkt)
        
        # Save state
        server.save_player_to_db(session)
        logger.info(f"[{session.char_name}] Entered tent interior.")

    elif sub == 3:  # Move Furniture
        # Payload: [62, 3, furn_id(2), x(4), y(4), dir(4), unk(1)]
        # Echo back to confirm movement
        furn_id = reader.read_16()
        x = reader.read_32()
        y = reader.read_32()
        direction = reader.read_32()
        unk = reader.read_8()
        
        logger.info(f"[{session.char_name}] Moving furniture {furn_id} to {x},{y} dir {direction}")
        
        resp = PacketWriter().write_8(62).write_8(3)
        resp.write_16(furn_id)
        resp.write_32(x)
        resp.write_32(y)
        resp.write_32(direction)
        resp.write_8(unk)
        await session.send_packet(resp)

    else:
        logger.info(f"Unhandled AC 62 Sub-Code: {sub}, payload: {reader.data.hex()}")
