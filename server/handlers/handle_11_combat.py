import logging

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [11]

async def handle(server, session, reader):
    """AC 11: Client request to start combat or flee."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] handle_combat sub={sub}")
    if sub == 1:
        # Flee (escape) request (PvE & PvP)
        escape_type = reader.read_8() if reader.remaining_bytes() > 0 else 0
        logger.info(f"[{session.char_name}] Flee request: escape_type={escape_type}")
        battle_id = getattr(session, 'battle_id', None) or getattr(session, 'pvp_battle_id', None)
        if battle_id and battle_id in server.active_battles:
            battle = server.active_battles[battle_id]
            await server._do_flee(session, battle)
    elif sub == 2:
        # Bathing check
        if getattr(session, 'bathing', False):
            logger.warning(f"[{session.char_name}] Combat blocked: Bathing.")
            from server.network import PacketWriter
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Bathing, can't act"))
            return

        # Client clicked on NPC to start combat
        if reader.remaining_bytes() < 7:
            logger.warning(f"[{session.char_name}] handle_combat sub=2 has too few bytes: {reader.remaining_bytes()}")
            return
        pk_type = reader.read_8()
        raw_target_id = reader.read_32()
        npc_id = raw_target_id & 0xFFFF
        npc_click_id = reader.read_16()
        logger.info(f"[{session.char_name}] Combat request: pk_type={pk_type} npc_id={npc_id} npc_click={npc_click_id}")
        
        # PK / PVP challenge distance verification
        if pk_type == 3:
            target_session = server.players.get(raw_target_id)
            if target_session:
                if target_session.map_id != session.map_id:
                    logger.warning(f"[{session.char_name}] PK blocked: target not on same map")
                    return
                if getattr(session, 'is_stall_active', False):
                    logger.warning(f"[{session.char_name}] PK blocked: Challenger has active stall.")
                    from server.network import PacketWriter
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Close Stall first"))
                    return
                if getattr(target_session, 'is_stall_active', False):
                    logger.warning(f"[{session.char_name}] PK blocked: Target has active stall.")
                    from server.network import PacketWriter
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't PK Stall user"))
                    return
                # Distance check (0x10f = 271 pixels limit)
                if abs(session.x - target_session.x) > 271 or abs(session.y - target_session.y) > 271:
                    logger.warning(f"[{session.char_name}] PK blocked: target too far X={abs(session.x - target_session.x)} Y={abs(session.y - target_session.y)}")
                    return
                logger.info(f"[{session.char_name}] PK challenge verified against {target_session.char_name}")
                await server._start_pvp_battle(session, target_session)
                return
            else:
                logger.warning(f"[{session.char_name}] PK blocked: target player ID {raw_target_id} not found")
                return

        await server._start_pve_battle(session, npc_click_id, npc_id)

    elif sub == 3:  # Combat Target Selection / Target Focus ACK
        target_grid = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        logger.debug(f"[{session.char_name}] AC 11:3 Combat target focus grid={target_grid}")
        from server.network import PacketWriter
        await session.send_packet(PacketWriter().write_8(11).write_8(3).write_8(target_grid))

    elif sub == 4:  # In-Combat Pet Capture Action (Net item / Skill 10008)
        target_grid = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        logger.info(f"[{session.char_name}] AC 11:4 Pet capture attempt on grid={target_grid}")
        battle_id = getattr(session, 'battle_id', None) or getattr(session, 'pvp_battle_id', None)
        if battle_id and battle_id in server.active_battles:
            battle = server.active_battles[battle_id]
            # Buffer capture action in active battle
            if 'pending_actions' not in battle:
                battle['pending_actions'] = {}
            src_coord = (4, 2)
            dst_coord = (target_grid % 4, target_grid // 4) if target_grid > 0 else (0, 2)
            battle['pending_actions'][src_coord] = {
                'action': 'capture',
                'skill_id': 10008,
                'dst_x': dst_coord[0],
                'dst_y': dst_coord[1]
            }
            from server.network import PacketWriter
            # Immediate AC 53:5 ACK
            await session.send_packet(PacketWriter().write_8(53).write_8(5).write_8(src_coord[0]).write_8(src_coord[1]))
