import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [14]

async def handle(server, session, reader):
    """Handles Friend System (AC 14) actions."""
    sub = reader.read_8()
    logger.info(f"[AC14] handle_action_14 called. SubCmd={sub}")
    
    if sub == 1:  # Add Friend Request (by name)
        target_name = reader.read_string()
        logger.info(f"[AC14] Add Friend Request from {session.char_name} to {target_name}")
        
        # Find target player session
        target = None
        for act in server.sessions.values():
            if getattr(act, 'char_name', '') == target_name:
                target = act
                break
                
        if target:
            logger.info(f"[AC14] Target {target_name} found. Sending friend request...")
            s = PacketWriter()
            s.write_8(14).write_8(1)
            s.write_string(session.char_name)
            await target.send_packet(s)
        else:
            logger.info(f"[AC14] Target {target_name} NOT found")
            s = PacketWriter()
            s.write_8(14).write_8(1)
            s.write_8(0)  # Failure
            await session.send_packet(s)
            
    elif sub == 2:  # Dual purpose - Friend List Request OR Friend Request Send
        flag = reader.read_8()
        target_char_id = reader.read_32()
        ignored_string = reader.read_string()
        
        logger.info(f"[AC14] SubCmd 2. Flag={flag}, TargetCharID={target_char_id}")
        
        if target_char_id == 0:
            await server.send_friend_list(session)
        else:
            # Find target player by CharID
            target = None
            for act in server.sessions.values():
                if getattr(act, 'char_id', 0) == target_char_id:
                    target = act
                    break
                    
            if target:
                logger.info(f"[AC14] Target {target.char_name} (ID:{target_char_id}) found. Sending friend request...")
                s = PacketWriter()
                s.write_8(14).write_8(2)
                s.write_32(session.char_id)
                s.write_string("")
                await target.send_packet(s)
                
    elif sub == 3:  # Friend Accept
        flag = reader.read_8()
        requester_char_id = reader.read_32()
        ignored_string = reader.read_string()
        
        logger.info(f"[AC14] Friend Accept from {session.char_name} for Requester ID: {requester_char_id}")
        
        # Find requester
        requester = None
        for act in server.sessions.values():
            if getattr(act, 'char_id', 0) == requester_char_id:
                requester = act
                break
                
        if not requester:
            logger.info(f"[AC14] Requester CharID {requester_char_id} not online/found")
            return
            
        try:
            smaller = min(session.char_id, requester_char_id)
            larger = max(session.char_id, requester_char_id)
            
            with server.db.get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO friends (CharID1, CharID2, AddedDate) VALUES (?, ?, datetime('now'))",
                    (smaller, larger)
                )
                conn.commit()
                
            logger.info(f"[AC14] Friendship added: {session.char_id} <-> {requester_char_id}")
            
            # Send success to requester
            s = PacketWriter()
            s.write_8(14).write_8(3)
            s.write_8(1)  # Success
            s.write_string(session.char_name)
            await requester.send_packet(s)
            
            # Send success to accepter
            s2 = PacketWriter()
            s2.write_8(14).write_8(3)
            s2.write_8(1)  # Success
            await session.send_packet(s2)
            
            # Auto-refresh lists
            await server.send_friend_list(session)
            await server.send_friend_list(requester)
        except Exception as e:
            logger.error(f"[AC14] Database/Accept error: {e}", exc_info=True)
            
    elif sub == 4:  # Remove Friend OR Friend List Request
        # Check if remaining bytes in packet for friend_char_id (at least 4 bytes)
        if reader.remaining_bytes() >= 4:
            friend_char_id = reader.read_32()
            logger.info(f"[AC14] Friend Remove Request from {session.char_name} for CharID {friend_char_id}")
            try:
                smaller = min(session.char_id, friend_char_id)
                larger = max(session.char_id, friend_char_id)
                
                with server.db.get_connection() as conn:
                    conn.execute(
                        "DELETE FROM friends WHERE CharID1 = ? AND CharID2 = ?",
                        (smaller, larger)
                    )
                    conn.commit()
                    
                logger.info(f"[AC14] Removed friendship: {session.char_id} <-> {friend_char_id}")
                await server.send_friend_list(session)
            except Exception as e:
                logger.error(f"[AC14] Database error removing friend: {e}", exc_info=True)
        else:
            logger.info(f"[AC14] Friend List Request (SubCmd 4) from {session.char_name}")
            await server.send_friend_list(session)
