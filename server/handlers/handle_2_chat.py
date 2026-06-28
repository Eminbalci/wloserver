import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [2]

async def handle(server, session, reader):
    """Processes chat messages and GM commands (AC 2)."""
    import time
    sub = reader.read_8()
    if sub == 2:
        msg = reader.read_string_n()
        words = msg.split(' ')
        
        is_gm = getattr(session, 'is_gm', False)
        
        # Mute check for regular players
        mute_until = getattr(session, 'mute_until', 0)
        if time.time() < mute_until:
            rem_sec = int(mute_until - time.time())
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"GM banned you from Local for {rem_sec}s"
            )
            await session.send_packet(sys_msg)
            return

        if words[0].startswith(":"):
            if not is_gm:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    "You do not have GM privileges to use commands."
                )
                await session.send_packet(sys_msg)
                return

            if words[0] == ":warp" and len(words) >= 4:
                try:
                    dst_map = int(words[1])
                    dst_x = int(words[2])
                    dst_y = int(words[3])
                    await server.warp_player(session, dst_map, dst_x, dst_y)
                except ValueError:
                    pass
            elif words[0] == ":kick" and len(words) >= 2:
                target_name = words[1]
                target_session = None
                for sess in server.sessions.values():
                    if getattr(sess, 'char_name', '').lower() == target_name.lower():
                        target_session = sess
                        break
                if target_session:
                    logger.info(f"[GM] Kicking player {target_session.char_name}")
                    # Send overlay message to target first
                    await target_session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("You have been kicked by a GM."))
                    await target_session.writer.aclose()
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Kicked player {target_name}.")
                    await session.send_packet(sys_msg)
                else:
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Player {target_name} not found.")
                    await session.send_packet(sys_msg)
            elif words[0] == ":ban" and len(words) >= 2:
                target_name = words[1]
                # Update DB and kick
                with server.db.get_connection() as conn:
                    # Find user ID from character name
                    row = conn.execute("SELECT user_id FROM characters WHERE name = ?", (target_name,)).fetchone()
                    if row:
                        user_id = row['user_id']
                        conn.execute("UPDATE users SET banned = 1 WHERE id = ?", (user_id,))
                        conn.commit()
                        
                        # Find active session to kick
                        target_session = None
                        for sess in server.sessions.values():
                            if getattr(sess, 'char_name', '').lower() == target_name.lower():
                                target_session = sess
                                break
                        if target_session:
                            logger.info(f"[GM] Banning and kicking player {target_session.char_name}")
                            await target_session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("This account has been banned."))
                            await target_session.writer.aclose()
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Banned player {target_name} successfully.")
                        await session.send_packet(sys_msg)
                    else:
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Character {target_name} not found in database.")
                        await session.send_packet(sys_msg)
            elif words[0] == ":mute" and len(words) >= 3:
                target_name = words[1]
                try:
                    duration = int(words[2])
                    target_session = None
                    for sess in server.sessions.values():
                        if getattr(sess, 'char_name', '').lower() == target_name.lower():
                            target_session = sess
                            break
                    if target_session:
                        target_session.mute_until = time.time() + duration
                        logger.info(f"[GM] Muted player {target_session.char_name} for {duration} seconds")
                        # Send ban alert overlay to client
                        mute_alert = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"GM banned you from Local for {duration}s")
                        await target_session.send_packet(mute_alert)
                        
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Muted player {target_name} for {duration}s.")
                        await session.send_packet(sys_msg)
                    else:
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Player {target_name} is not online.")
                        await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":propshop":
                await session.send_packet(PacketWriter().write_8(27).write_8(3))
            elif words[0] == ":item" and len(words) >= 3 and words[1] == "add":
                try:
                    item_id = int(words[2])
                    amount = int(words[3]) if len(words) >= 4 else 1
                    
                    from server.gameserver import add_item_to_inventory
                    slot = add_item_to_inventory(session, item_id, amount=amount)
                    if slot is not None:
                        server.save_player_to_db(session)
                        
                        item_pkt = PacketWriter()
                        item_pkt.write_8(23).write_8(6).write_32(item_id).write_8(amount).write_bytes(bytes(26))
                        await session.send_packet(item_pkt)
                            
                        # System chat confirmation
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Item {item_id} added to inventory."
                        )
                        await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":level" and len(words) >= 2:
                try:
                    level_num = int(words[1])
                    level_num = max(1, min(199, level_num))
                    session.exp = server.get_cumulative_exp_for_level(level_num, session.reborn)
                    session.level = level_num
                    session.update_max_hp_sp()
                    session.hp = session.max_hp
                    session.sp = session.max_sp
                    
                    await server.send_stats_update(session)
                    server.save_player_to_db(session)
                    
                    # Chat confirmation
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Level set to {session.level}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":stat" and len(words) >= 6:
                try:
                    str_val = int(words[1])
                    con_val = int(words[2])
                    int_val = int(words[3])
                    wis_val = int(words[4])
                    agi_val = int(words[5])
                    
                    session.str_val = max(1, str_val)
                    session.con_val = max(1, con_val)
                    session.int_val = max(1, int_val)
                    session.wis_val = max(1, wis_val)
                    session.agi_val = max(1, agi_val)
                    
                    session.update_max_hp_sp()
                    session.hp = session.max_hp
                    session.sp = session.max_sp
                    
                    await server.send_stats_update(session)
                    server.save_player_to_db(session)
                    
                    # Chat confirmation
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        "Base stats updated successfully."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":gold" and len(words) >= 2:
                try:
                    gold_amt = int(words[1])
                    session.gold = max(0, gold_amt)
                    
                    # Gold update packet (26, 4)
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    server.save_player_to_db(session)
                    
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Gold set to {session.gold}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":heal":
                session.hp = session.max_hp
                session.sp = session.max_sp
                
                await server.send_stats_update(session)
                        
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    "HP and SP fully restored."
                )
                await session.send_packet(sys_msg)
            elif words[0] == ":element" and len(words) >= 2:
                try:
                    element_num = int(words[1])
                    if 0 <= element_num <= 4:
                        session.element = element_num
                        
                        await server.send_stats_update(session)
                        server.save_player_to_db(session)
                        
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Element set to {session.element}."
                        )
                        await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":clear":
                session.inventory = []
                server.save_player_to_db(session)
                
                # Send empty inventory packet
                await session.send_packet(server.build_inventory_packet(session))
                
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    "Inventory cleared."
                )
                await session.send_packet(sys_msg)
            elif words[0] == ":skill" and len(words) >= 2:
                try:
                    skill_id = int(words[1])
                    grade = int(words[2]) if len(words) >= 3 else 1
                    
                    # Element check based on client limitations
                    skill_info = None
                    for sk_entry in getattr(server, 'all_skills_db', []):
                        if sk_entry.get('id') == skill_id:
                            skill_info = sk_entry
                            break
                    if skill_info:
                        sk_elem = skill_info.get('element', 0)
                        if sk_elem != 0 and sk_elem != session.element:
                            err_msg = "Can't learn skill: element mismatch."
                            if sk_elem == 1: err_msg = "Can't learn Earth skill"
                            elif sk_elem == 2: err_msg = "Can't learn Water skill"
                            elif sk_elem == 3: err_msg = "Can't learn Fire skill"
                            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(err_msg))
                            return

                    exists = False
                    for sk in session.skills:
                        if sk['skill_id'] == skill_id:
                            sk['grade'] = grade
                            exists = True
                            break
                    if not exists:
                        session.skills.append({
                            "skill_id": skill_id,
                            "grade": grade,
                            "exp": 0
                        })
                    
                    server.save_player_to_db(session)
                                
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Skill {skill_id} learned/updated to grade {grade}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass

            elif words[0] == ":ride":
                # Force vehicle boarding from server-side, bypassing client "Transports not allowed" check
                # Usage: :ride [vehicle_slot]  (defaults to first vehicle in inventory)
                vehicle_slot = None
                vehicle_item_id = 0
                
                if len(words) >= 2:
                    try:
                        vehicle_slot = int(words[1])
                    except ValueError:
                        pass
                
                if vehicle_slot is None:
                    # Auto-find first vehicle item in inventory (ID range 48000-48999)
                    from server.gameserver import get_item_at_slot
                    for s in range(1, 51):
                        itm = get_item_at_slot(session, s)
                        if itm and 48000 <= itm['item_id'] <= 48999:
                            vehicle_slot = s
                            vehicle_item_id = itm['item_id']
                            break
                
                if vehicle_slot:
                    if vehicle_item_id == 0:
                        from server.gameserver import get_item_at_slot
                        itm = get_item_at_slot(session, vehicle_slot)
                        if itm:
                            vehicle_item_id = itm['item_id']
                    
                    # Determine vehicle type from item ID
                    vehicle_type = 1  # Default: Canoe
                    item_name = server.items.get(str(vehicle_item_id), "").lower()
                    if "ufo" in item_name:
                        vehicle_type = 6
                    elif "balloon" in item_name or "air" in item_name:
                        vehicle_type = 3
                    elif "raft" in item_name:
                        vehicle_type = 2
                    elif "canoe" in item_name:
                        vehicle_type = 1
                    elif "boat" in item_name or "ship" in item_name:
                        vehicle_type = 4
                    
                    session.riding_vehicle = True
                    session.riding_vehicle_type = vehicle_type
                    
                    # Send boarding confirmation to client
                    await session.send_packet(PacketWriter().write_8(23).write_8(51).write_8(vehicle_type))
                    
                    # Broadcast appearance change to map
                    refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(vehicle_type)
                    server.broadcast_to_map(session.map_id, refresh)
                    
                    vname = server.items.get(str(vehicle_item_id), f"Vehicle#{vehicle_item_id}")
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Boarded {vname}"))
                else:
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("No vehicle found in inventory"))

            elif words[0] == ":unride":
                # Force vehicle unboarding from server-side
                session.riding_vehicle = False
                session.riding_vehicle_type = 0
                await session.send_packet(PacketWriter().write_8(23).write_8(52))
                refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                server.broadcast_to_map(session.map_id, refresh)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Unboarded vehicle"))
        else:
            # Regular chat: broadcast to map
            chat_pkt = PacketWriter()
            chat_pkt.write_8(2).write_8(2)
            chat_pkt.write_32(session.char_id)
            chat_pkt.write_string_n(msg)
            server.broadcast_to_map(session.map_id, chat_pkt, exclude_session=session)
