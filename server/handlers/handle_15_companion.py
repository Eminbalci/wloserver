import logging
import sqlite3
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [15]

async def handle(server, session, reader):
    """Processes companion and pet actions (AC 15)."""
    sub = reader.read_8()
    
    if sub == 2:  # Dismiss Pet
        slot = reader.read_8()
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            pet_id = pet.get("pet_id")
            logger.info(f"[{session.char_name}] Dismissing pet {pet_id} from slot {slot}")
            
            # Check if this pet is currently in battle, rest it first
            if pet.get("in_battle", False):
                # Broadcast despawn
                despawn = PacketWriter().write_8(19).write_8(7).write_32(session.char_id)
                server.broadcast_to_map(session.map_id, despawn)
                
                # Broadcast appearance update
                refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                server.broadcast_to_map(session.map_id, refresh)
            
            # Remove pet
            session.pets.pop(slot - 1)
            
            # Save changes
            try:
                server.save_player_to_db(session)
            except Exception as db_err:
                logger.error(f"[Dismiss Pet] Error saving to DB: {db_err}")
            
            # Send dismiss confirmation: AC 15 Sub 2, owner ID, slot index
            dismiss_pkt = PacketWriter().write_8(15).write_8(2).write_32(session.char_id).write_8(slot)
            await session.send_packet(dismiss_pkt)
            
            # Refresh companion list
            await server.send_pet_list(session)
            
    elif sub == 4:  # Toggle Battle/Rest
        slot = reader.read_8()
        state = reader.read_8()
        
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            pet_id = pet.get("pet_id")
            
            if state == 1:  # Bring into battle (spawn on map)
                logger.info(f"[{session.char_name}] Setting pet {pet_id} at slot {slot} to BATTLE state")
                
                # Update pet in_battle state
                for idx, p in enumerate(session.pets):
                    p["in_battle"] = (idx == slot - 1)
                    
                # 1. Send owner packet: AC 19 Sub 4
                pp = PacketWriter().write_8(19).write_8(4).write_32(session.char_id).write_32(pet_id)
                await session.send_packet(pp)
                
                # 2. Broadcast companion spawn to map: AC 15 Sub 4
                spawn = PacketWriter().write_8(15).write_8(4)
                spawn.write_32(session.char_id)
                spawn.write_32(pet_id)
                spawn.write_8(0)
                spawn.write_8(1)
                
                # Look up pet template name
                pet_name = "Companion"
                try:
                    conn = sqlite3.connect(server.static_db_path)
                    conn.row_factory = sqlite3.Row
                    row = conn.execute("SELECT name FROM npc_data WHERE id = ?", (pet_id,)).fetchone()
                    conn.close()
                    if row:
                        pet_name = row['name'].strip('\x00').strip()
                except Exception as e:
                    logger.error(f"[Pet Spawn] Error getting name for pet template {pet_id}: {e}")
                
                spawn.write_string(pet_name)
                spawn.write_16(0)  # Weapon ID placeholder
                
                server.broadcast_to_map(session.map_id, spawn, exclude_session=session)
                
                # 3. Broadcast force refresh player appearance: AC 5 Sub 8
                refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                server.broadcast_to_map(session.map_id, refresh)

                
            else:  # Standby / Rest pet
                logger.info(f"[{session.char_name}] Setting pet {pet_id} at slot {slot} to REST state")
                pet["in_battle"] = False
                
                # 1. Send rest owner confirmation: AC 19 Sub 2
                rest_owner = PacketWriter().write_8(19).write_8(2)
                await session.send_packet(rest_owner)
                
                # 2. Broadcast despawn to map: AC 19 Sub 7
                despawn = PacketWriter().write_8(19).write_8(7).write_32(session.char_id)
                server.broadcast_to_map(session.map_id, despawn)
                
                # 3. Broadcast force refresh player appearance: AC 5 Sub 8
                refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                server.broadcast_to_map(session.map_id, refresh)
                
            # Save changes
            try:
                server.save_player_to_db(session)
            except Exception as db_err:
                logger.error(f"[Pet Battle Toggle] Error saving to DB: {db_err}")
                
    elif sub == 11:  # Request Ride Pet
        slot = reader.read_8()
        pet_id = reader.read_32()
        logger.info(f"[{session.char_name}] Requesting RIDE pet {pet_id} at slot {slot}")
        
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            if pet.get("pet_id") == pet_id:
                # Rest all other pets (and remove battle state)
                for idx, p in enumerate(session.pets):
                    p["riding"] = (idx == slot - 1)
                    p["in_battle"] = False
                
                # Send ride confirmation/broadcast: AC 15 Sub 16
                # Format: [15, 16, slot(1), char_id(4), pet_id(4), 26 zeros]
                ride_pkt = PacketWriter().write_8(15).write_8(16).write_8(slot)
                ride_pkt.write_32(session.char_id).write_32(pet_id)
                ride_pkt.write_bytes(b'\x00' * 26)
                
                # Send to player and broadcast to map
                await session.send_packet(ride_pkt)
                server.broadcast_to_map(session.map_id, ride_pkt, exclude_session=session)
                
                # Save changes
                try:
                    server.save_player_to_db(session)
                except Exception as db_err:
                    logger.error(f"[Pet Ride] Error saving to DB: {db_err}")
                    
    elif sub == 12:  # Request Rest Riding Pet
        slot = reader.read_8()
        pet_id = reader.read_32()
        logger.info(f"[{session.char_name}] Requesting REST RIDING pet {pet_id} at slot {slot}")
        
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            if pet.get("pet_id") == pet_id:
                pet["riding"] = False
                
                # Send confirmation: AC 15 Sub 17
                # Format: [15, 17, char_id(4)]
                confirm = PacketWriter().write_8(15).write_8(17).write_32(session.char_id)
                
                # Send to player and broadcast to map
                await session.send_packet(confirm)
                server.broadcast_to_map(session.map_id, confirm, exclude_session=session)
                
                # Save changes
                try:
                    server.save_player_to_db(session)
                except Exception as db_err:
                    logger.error(f"[Pet Rest Ride] Error saving to DB: {db_err}")

    elif sub == 6:  # Rename Pet
        slot = reader.read_8()
        new_name = reader.read_string_n()
        logger.info(f"[{session.char_name}] Renaming pet in slot {slot} to {new_name}")
        
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            pet["name"] = new_name
            
            # Broadcast to map: AC 15 Sub 9
            confirm = PacketWriter().write_8(15).write_8(9).write_32(session.char_id).write_8(slot).write_string_n(new_name)
            server.broadcast_to_map(session.map_id, confirm)
            
            # Save to DB
            try:
                server.save_player_to_db(session)
            except Exception as db_err:
                logger.error(f"[Pet Rename] Error saving to DB: {db_err}")

    elif sub in [16, 17]:
        logger.info(f"[{session.char_name}] Companion ride action received: sub={sub}")

