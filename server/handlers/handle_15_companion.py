import logging
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
            
            # Check if this pet is currently mounted (FUN_0013d794 / FUN_00344974)
            if pet.get("riding", False):
                pet["riding"] = False
                confirm = PacketWriter().write_8(15).write_8(17).write_32(session.char_id)
                await session.send_packet(confirm)
                server.broadcast_to_map(session.map_id, confirm, exclude_session=session)

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
                if hasattr(server, "get_pet_template_info"):
                    pet_name, _ = server.get_pet_template_info(pet_id)
                
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

    elif sub == 9:  # Vehicle Use / Mount / Dismount Request (C line 395444: FUN_002d6994(..., 0xf, 9, 0))
        from server.vehicle_system import GLOBAL_VEHICLE_MANAGER
        if getattr(session, 'riding_vehicle', False):
            logger.info(f"[{session.char_name}] Player requested vehicle dismount via AC 15 Sub 9")
            await GLOBAL_VEHICLE_MANAGER.dismount_vehicle(server, session)
            return

        slot = 0
        item_id_param = 0
        if reader.remaining_bytes() >= 3:
            slot = reader.read_8()
            item_id_param = reader.read_16()
        elif reader.remaining_bytes() == 2:
            item_id_param = reader.read_16()
        elif reader.remaining_bytes() == 1:
            slot = reader.read_8()

        logger.info(f"[{session.char_name}] AC 15 Sub 9 action received: slot={slot}, item_id={item_id_param}")

        vehicle_item_id = 0
        if item_id_param > 0 and ((48000 <= item_id_param <= 48050) or (36000 <= item_id_param <= 36050) or (34100 <= item_id_param <= 34200) or GLOBAL_VEHICLE_MANAGER.get_template(item_id_param)):
            vehicle_item_id = item_id_param

        # 1. Check item at specified inventory slot
        if not vehicle_item_id and slot > 0:
            item = None
            if hasattr(server, 'get_item_at_slot') and callable(getattr(server, 'get_item_at_slot', None)):
                try:
                    res = server.get_item_at_slot(session, slot)
                    if isinstance(res, dict):
                        item = res
                except Exception:
                    pass
            if not item and hasattr(session, 'inventory') and isinstance(session.inventory, list):
                for it in session.inventory:
                    if isinstance(it, dict) and it.get('slot') == slot:
                        item = it
                        break
            if item and isinstance(item, dict):
                iid = item.get('item_id', 0)
                if type(iid) is int:
                    if (48000 <= iid <= 48050) or (36000 <= iid <= 36050) or (34100 <= iid <= 34200) or GLOBAL_VEHICLE_MANAGER.get_template(iid):
                        vehicle_item_id = iid

        # 2. Fallback: Check active vehicle or search inventory for any vehicle item
        if not vehicle_item_id:
            active_v = getattr(session, 'active_vehicle_id', 0)
            if type(active_v) is int and active_v > 0 and GLOBAL_VEHICLE_MANAGER.get_template(active_v):
                vehicle_item_id = active_v
            else:
                inv = getattr(session, 'inventory', [])
                if isinstance(inv, list):
                    for it in inv:
                        if isinstance(it, dict):
                            iid = it.get('item_id', 0)
                            if type(iid) is int:
                                if iid == 48016 or (48000 <= iid <= 48050) or GLOBAL_VEHICLE_MANAGER.get_template(iid):
                                    vehicle_item_id = iid
                                    break

        if vehicle_item_id > 0:
            logger.info(f"[{session.char_name}] Mounting vehicle #{vehicle_item_id} via AC 15 Sub 9")
            await GLOBAL_VEHICLE_MANAGER.mount_vehicle(server, session, vehicle_item_id)
            return

        # 3. Fallback to Pet Mount/Ride Toggle if slot matches a companion pet
        from server.pet_ride_system import GLOBAL_PET_RIDE_MANAGER
        if getattr(session, 'mounted_pet_slot', 0) == slot and slot > 0:
            await GLOBAL_PET_RIDE_MANAGER.dismount_companion_pet(server, session)
        elif 1 <= slot <= len(getattr(session, 'pets', [])):
            await GLOBAL_PET_RIDE_MANAGER.mount_companion_pet(server, session, slot)
        else:
            logger.warning(f"[{session.char_name}] AC 15 Sub 9 unhandled: no vehicle found and slot {slot} is not a valid pet.")

    elif sub == 15:  # Pet Reborn Request
        slot = reader.read_8()
        logger.info(f"[{session.char_name}] Pet Reborn request for slot {slot}")
        if 1 <= slot <= len(session.pets):
            pet = session.pets[slot - 1]
            if pet.get("level", 1) < 70:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Pet must be at least Level 70 to reborn."))
                return
            if pet.get("equipments") and len(pet.get("equipments", [])) > 0:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Remove Pet equip first"))
                return
            if pet.get("reborn", 0) != 0:
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Pet is already reborn."))
                return
                
            pet["reborn"] = 1
            pet["level"] = 1
            pet["exp"] = 0
            pet["str"] = pet.get("str", 5) + 10
            pet["con"] = pet.get("con", 5) + 10
            pet["int"] = pet.get("int", 5) + 10
            pet["wis"] = pet.get("wis", 5) + 10
            pet["agi"] = pet.get("agi", 5) + 10
            pet["hp"] = 180 + pet["con"] * 2 + 1
            pet["sp"] = 94 + pet["wis"] * 2 + 1
            
            try:
                server.save_player_to_db(session)
            except Exception as db_err:
                logger.error(f"[Pet Reborn] Error saving to DB: {db_err}")
                
            await server.send_pet_list(session)
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"{pet.get('name', 'Pet')} has successfully reborn!"))

    elif sub == 14:  # Spawn / Place Vehicle on Map (Authentic AC 15 Sub 14)
        vehicle_item_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        logger.info(f"[{session.char_name}] Spawn vehicle request for item #{vehicle_item_id}")
        session.active_vehicle_id = vehicle_item_id
        session.riding_vehicle = False
        # Server confirms spawn and syncs position to client/map: AC 15 Sub 18
        # Format: [15, 18, 21, char_id(4), item_id(2), x(4), y(4)]
        p18 = (
            PacketWriter()
            .write_8(15)
            .write_8(18)
            .write_8(21)
            .write_32(session.char_id)
            .write_16(vehicle_item_id)
            .write_32(session.x)
            .write_32(session.y)
        )
        await session.send_packet(p18)
        server.broadcast_to_map(session.map_id, p18, exclude_session=session)

    elif sub == 7:  # Board / Enter Placed Vehicle (Authentic AC 15 Sub 7)
        from server.vehicle_system import GLOBAL_VEHICLE_MANAGER
        vehicle_item_id = reader.read_16() if reader.remaining_bytes() >= 2 else getattr(session, 'active_vehicle_id', 0)
        if not vehicle_item_id:
            vehicle_item_id = 48016
        logger.info(f"[{session.char_name}] Board placed vehicle #{vehicle_item_id}")
        await GLOBAL_VEHICLE_MANAGER.mount_vehicle(server, session, vehicle_item_id)

    elif sub == 10:  # Packup / Dismount Placed Vehicle (Authentic AC 15 Sub 10)
        from server.vehicle_system import GLOBAL_VEHICLE_MANAGER
        logger.info(f"[{session.char_name}] Packup/Dismount vehicle")
        await GLOBAL_VEHICLE_MANAGER.dismount_vehicle(server, session)

    elif sub == 13:  # Vehicle Navigation Orientation / Ping
        logger.debug(f"[{session.char_name}] Vehicle navigation sync received (AC 15 Sub 13)")

    elif sub in [16, 17]:
        logger.info(f"[{session.char_name}] Companion ride action received: sub={sub}")



