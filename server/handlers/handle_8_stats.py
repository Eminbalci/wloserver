import logging

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [8]

async def handle(server, session, reader):
    """Handles stats and potential point allocation (AC 8)."""
    sub = reader.read_8()
    logger.info(f"[AC8] handle_action_8 called. SubCmd={sub}, data: {reader.data.hex()}")
    if sub == 1:
        target_type = reader.read_8()
        target_slot = reader.read_8()
        stat_id = reader.read_8()
        amount = reader.read_32()
        
        logger.info(f"[AC8] Allocating stats: target_type={target_type}, target_slot={target_slot}, stat_id={stat_id}, amount={amount}")
        
        # Verify points
        if target_type == 0: # Player
            if session.points >= amount:
                session.points -= amount
                if stat_id == 28: # STR
                    session._str_val += amount
                elif stat_id == 29: # CON
                    session._con_val += amount
                elif stat_id == 27: # INT
                    session._int_val += amount
                elif stat_id == 33: # WIS
                    session._wis_val += amount
                elif stat_id == 30: # AGI
                    session._agi_val += amount
                
                server.save_player_to_db(session)
                await server.send_stats_update(session, levelup=True)
                logger.info(f"[AC8] Player allocated stat {stat_id} by {amount}. Remaining points: {session.points}")
            else:
                logger.warning(f"[AC8] Player tried to allocate {amount} points but only has {session.points}")
        
        elif target_type == 1: # Pet
            if 1 <= target_slot <= len(session.pets):
                pet = session.pets[target_slot - 1]
                pet_potential = pet.get("potential", 0)
                if pet_potential >= amount:
                    pet["potential"] = pet_potential - amount
                    if stat_id == 28: # STR
                        pet["str"] = pet.get("str", 5) + amount
                    elif stat_id == 29: # CON
                        pet["con"] = pet.get("con", 5) + amount
                    elif stat_id == 27: # INT
                        pet["int"] = pet.get("int", 5) + amount
                    elif stat_id == 33: # WIS
                        pet["wis"] = pet.get("wis", 5) + amount
                    elif stat_id == 30: # AGI
                        pet["agi"] = pet.get("agi", 5) + amount
                    
                    server.save_player_to_db(session)
                    await server.send_pet_stats(session, target_slot)
                    await server.send_pet_list(session)
                    logger.info(f"[AC8] Pet slot {target_slot} allocated stat {stat_id} by {amount}. Remaining potential: {pet['potential']}")
                else:
                    logger.warning(f"[AC8] Pet tried to allocate {amount} points but only has {pet_potential}")

    elif sub == 2:  # Client stats sync / refresh request (from C code line 363337)
        logger.info(f"[AC8] Stats sync/refresh requested by {session.char_name}")
        await server.send_stats_update(session)
