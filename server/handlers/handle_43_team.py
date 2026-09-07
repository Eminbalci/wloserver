import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [43]  # Opcode 0x2B

async def handle(server, session, reader):
    """Handles Team System (AC 43) actions."""
    sub = reader.read_8()
    logger.info(f"[AC43] handle_action_43 called. SubCmd={sub}, Raw={reader.data.hex()}")
    
    if sub == 1:  # Invite to Team
        target_name = reader.read_string()
        logger.info(f"[AC43] Team Invite request from {session.char_name} to {target_name}")
        
        # Find target player session
        target = None
        for act in server.active_sessions:
            if act.char_name == target_name:
                target = act
                break
                
        if target:
            s = PacketWriter()
            s.write_8(43).write_8(1)
            s.write_string(session.char_name)
            await target.send_packet(s)
        else:
            # Send team full or player not found failure
            s = PacketWriter()
            s.write_8(43).write_8(1)
            s.write_8(0)
            await session.send_packet(s)
            
    elif sub == 2:  # Accept Team Invite
        inviter_name = reader.read_string()
        logger.info(f"[AC43] Team Invite accept from {session.char_name} for {inviter_name}")
        
        # Find inviter
        inviter = None
        for act in server.active_sessions:
            if act.char_name == inviter_name:
                inviter = act
                break
                
        if inviter:
            # Broadcast joined team to both players
            s1 = PacketWriter()
            s1.write_8(43).write_8(2).write_string(session.char_name).write_8(1) # joined
            await inviter.send_packet(s1)
            
            s2 = PacketWriter()
            s2.write_8(43).write_8(2).write_string(inviter.char_name).write_8(1) # joined
            await session.send_packet(s2)
            
    elif sub in (4, 5):  # Leave / Disband Team (AC 43 Sub 4 from line 410529, Sub 5)
        logger.info(f"[AC43] {session.char_name} is leaving team (sub={sub})")
        s = PacketWriter()
        s.write_8(43).write_8(sub).write_string(session.char_name)
        await session.send_packet(s)
        
    else:
        # Default release interaction lock
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
