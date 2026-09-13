import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [19]

async def handle(server, session, reader):
    """Processes companion action state changes (AC 19)."""
    sub = reader.read_8()
    
    if sub == 1:  # Request Pet State: BATTLE
        pet_id = reader.read_32()
        logger.info(f"[{session.char_name}] Requesting BATTLE state for pet_id={pet_id}")
        
        # Find the pet in the player session
        pet_match = None
        pet_slot = -1
        for idx, p in enumerate(session.pets):
            if p.get("pet_id") == pet_id:
                pet_match = p
                pet_slot = idx + 1
                break
                
        if not pet_match:
            logger.warning(f"[{session.char_name}] Pet ID {pet_id} not found in session companion list")
            return
            
        logger.info(f"[{session.char_name}] Toggling pet {pet_id} at slot {pet_slot} to BATTLE state")
        
        # Rest all other pets (both battle and riding status)
        for p in session.pets:
            p["in_battle"] = False
            p["riding"] = False
        
        # Mark this pet in battle
        pet_match["in_battle"] = True
        
        # 1. Send owner confirmation packet: AC 19 Sub 1 with pet_id (matches official pcap)
        pp = PacketWriter().write_8(19).write_8(1).write_32(pet_id)
        await session.send_packet(pp)
        
        # 2. Broadcast companion spawn to map: AC 15 Sub 4
        spawn = PacketWriter().write_8(15).write_8(4)
        spawn.write_32(session.char_id)
        spawn.write_32(pet_id)
        spawn.write_8(0)
        spawn.write_8(1)
        
        # Look up pet template name or use custom name
        pet_name = pet_match.get("name")
        if not pet_name:
            if hasattr(server, "get_pet_template_info"):
                pet_name, _ = server.get_pet_template_info(pet_id)
            else:
                pet_name = "Companion"
        
        spawn.write_string(pet_name)
        spawn.write_16(0)  # Weapon ID placeholder
        
        server.broadcast_to_map(session.map_id, spawn, exclude_session=session)

        
        # 3. Broadcast force refresh player appearance: AC 5 Sub 8
        refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
        server.broadcast_to_map(session.map_id, refresh)
        
        # Save changes to database
        try:
            server.save_player_to_db(session)
        except Exception as db_err:
            logger.error(f"[Pet Battle Toggle] Error saving to DB: {db_err}")
            
    elif sub == 2:  # Request Pet State: REST
        logger.info(f"[{session.char_name}] Requesting REST state for battle pet")
        
        # Find the pet in battle and rest it
        pet_found = False
        for p in session.pets:
            if p.get("in_battle", False):
                p["in_battle"] = False
                pet_found = True
        
        # 1. Send owner rest confirmation packet: AC 19 Sub 2 (matches official pcap)
        rest_owner = PacketWriter().write_8(19).write_8(2)
        await session.send_packet(rest_owner)
        
        # 2. Broadcast despawn to map: AC 19 Sub 7
        despawn = PacketWriter().write_8(19).write_8(7).write_32(session.char_id)
        server.broadcast_to_map(session.map_id, despawn)
        
        # 3. Broadcast force refresh player appearance: AC 5 Sub 8
        refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
        server.broadcast_to_map(session.map_id, refresh)
        
        # Save changes to database
        try:
            server.save_player_to_db(session)
        except Exception as db_err:
            logger.error(f"[Pet Rest Toggle] Error saving to DB: {db_err}")
