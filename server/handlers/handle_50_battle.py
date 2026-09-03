import logging

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [50]

async def handle(server, session, reader):
    """AC 50: Client request for battle action."""
    raw_data = reader.data
    sub = reader.read_8() if reader.remaining_bytes() > 0 else 0
    extra = raw_data[1:].hex() if len(raw_data) > 1 else ''
    logger.info(f"[{session.char_name}] AC50 sub={sub} extra={extra}")

    battle_id = getattr(session, 'pvp_battle_id', None)
    if battle_id is None or battle_id not in server.active_battles:
        # Handle Spectate (7/8) or Join Battle (1/2) outside active battle state
        from server.network import PacketWriter
        if sub in (7, 8):  # Spectate Battle
            logger.info(f"[{session.char_name}] Spectating request received outside battle.")
            # Echo failure/cancel response to prevent client hang
            writer = PacketWriter().write_8(50).write_8(7).write_8(0)
            await session.send_packet(writer)
            return
        elif sub in (1, 2):  # Join Battle/PK challenge
            logger.info(f"[{session.char_name}] Join Battle/PK challenge received outside battle.")
            writer = PacketWriter().write_8(50).write_8(sub).write_8(0)
            await session.send_packet(writer)
            return
        logger.warning(f"[{session.char_name}] AC50 but not in battle, raw={raw_data.hex()}")
        return

    battle = server.active_battles[battle_id]
    if battle['finished']:
        return

    # Default values
    src_x, src_y = 4, 2  # Default to player
    dst_x, dst_y = 2, 2  # Default target
    action_type = 'attack'
    skill_id = 10001

    if sub == 4:  # Defend (legacy/compat)
        action_type = 'defend'
        skill_id = 60021
        if reader.remaining_bytes() >= 2:
            src_x = reader.read_8()
            src_y = reader.read_8()
            dst_x, dst_y = src_x, src_y
    elif sub == 5:  # Flee (legacy/compat)
        action_type = 'flee'
        skill_id = 60041
        if reader.remaining_bytes() >= 2:
            src_x = reader.read_8()
            src_y = reader.read_8()
            dst_x, dst_y = src_x, src_y
    elif sub in (0, 1, 2, 3, 6, 7):  # Attack/Skill/Defend/Flee/Capture
        if sub == 1 and reader.remaining_bytes() >= 8:
            try:
                src_x = reader.read_8()
                src_y = reader.read_8()
                dst_x = reader.read_8()
                dst_y = reader.read_8()
                skill_id = reader.read_16()
            except Exception as e:
                logger.error(f"Error parsing AC50 sub=1 payload: {e}")
        else:
            if reader.remaining_bytes() >= 2:
                src_x = reader.read_8()
                src_y = reader.read_8()
            if reader.remaining_bytes() >= 2:
                dst_x = reader.read_8()
                dst_y = reader.read_8()

        # Authentic skill ID mapping from real pcaps
        if skill_id == 60021:
            action_type = 'defend'
        elif skill_id == 60041:
            action_type = 'flee'
        elif skill_id == 10008:
            action_type = 'capture'
        else:
            action_type = 'attack'
    else:
        logger.warning(f"[{session.char_name}] AC50 unknown sub={sub}")
        return

    # Real-Pcap: Server IMMEDIATELY acknowledges registered action via AC 53 Sub 5
    from server.network import PacketWriter
    ack_pkt = PacketWriter().write_8(53).write_8(5).write_8(src_x).write_8(src_y)
    await session.send_packet(ack_pkt)
    if battle.get('is_pvp'):
        opp_session = battle['target']['session'] if session == battle['challenger']['session'] else battle['challenger']['session']
        if opp_session:
            await opp_session.send_packet(ack_pkt)

    # Buffer action
    if 'pending_actions' not in battle:
        battle['pending_actions'] = {}

    battle['pending_actions'][(src_x, src_y)] = {
        'action': action_type,
        'skill_id': skill_id,
        'dst_x': dst_x,
        'dst_y': dst_y
    }

    # Expected participants to submit action
    if battle.get('is_pvp'):
        expected_coords = [(4, 2), (2, 2)]
        if battle.get('pet') is not None and battle['pet']['hp'] > 0:
            expected_coords.append((3, 2))
        if battle.get('target_pet') is not None and battle['target_pet']['hp'] > 0:
            expected_coords.append((1, 2))
    else:
        expected_coords = [(4, 2)]
        if battle.get('pet') is not None and battle['pet']['hp'] > 0:
            expected_coords.append((3, 2))

    logger.info(f"[{session.char_name}] Buffered action from ({src_x},{src_y}): {action_type} skill={skill_id}. "
                f"Pending: {list(battle['pending_actions'].keys())}, Expected: {expected_coords}")

    # If all expected actions are collected, resolve the turn
    all_received = all(coord in battle['pending_actions'] for coord in expected_coords)
    if all_received:
        logger.info(f"[{session.char_name}] All actions received. Resolving turn {battle['turn'] + 1}")
        if battle.get('is_pvp'):
            await server._resolve_pvp_turn(session, battle)
        else:
            await server._resolve_pve_turn(session, battle)
