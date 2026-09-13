import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [9]

async def handle(server, session, reader):
    """Processes character creation and name availability (AC 9)."""
    sub = reader.read_8()
    
    if sub == 2:  # Check Name Availability
        name = reader.read_string_n()
        taken = server.db.is_name_taken(name)
        status = 1 if taken or len(name) < 4 or len(name) > 14 else 0
        if status == 0:
            session.char_name = name
        
        resp = PacketWriter()
        resp.write_8(9).write_8(3).write_8(status)
        await session.send_packet(resp)
        
    elif sub == 1:  # Create character
        body = reader.read_16()
        head = reader.read_16()
        hair_color = reader.read_16()
        skin_color = reader.read_16()
        clothing_color = reader.read_16()
        eye_color = reader.read_16()
        element = reader.read_8()
        
        # Stats (read in client-sent order: str, agi, wis, int, con)
        str_val = reader.read_8()  # str
        agi_val = reader.read_8()  # agi
        wis_val = reader.read_8()  # wis
        int_val = reader.read_8()  # int
        con_val = reader.read_8()  # con
        
        # Validate stats distribution (maximum of 5 starting points)
        stat_sum = str_val + agi_val + wis_val + int_val + con_val
        if stat_sum > 5 or any(s < 0 for s in (str_val, agi_val, wis_val, int_val, con_val)):
            logger.warning(f"[Char] Hacked packet detected! Stat sum {stat_sum} exceeds 5.")
            await session.send_packet(PacketWriter().write_8(0).write_8(30))
            return

        # Validate name existence and length
        if not session.char_name or len(session.char_name) < 4 or len(session.char_name) > 14:
            logger.warning(f"[Char] Invalid name length for character creation.")
            await session.send_packet(PacketWriter().write_8(0).write_8(30))
            return
            
        cipher = ""
        if not session.cipher:
            cipher = reader.read_string()
            
        # Determine slot (check which slot is free)
        slot = 1
        with server.db.get_connection() as conn:
            row = conn.execute("SELECT id FROM characters WHERE user_id = ? AND slot = 1", (session.user_id,)).fetchone()
            if row:
                slot = 2
                
        char_id = server.db.create_character(
            session.user_id, slot, session.char_name, body, head,
            hair_color, skin_color, clothing_color, eye_color, element, cipher,
            str_val=str_val, con_val=con_val, int_val=int_val, wis_val=wis_val, agi_val=agi_val
        )

        
        if char_id:
            logger.info(f"[Char] Character '{session.char_name}' created in slot {slot}")
            if cipher:
                session.cipher = cipher
                
            # Load character stats first to populate session.char_id
            server.load_character_into_session(session, char_id)

            # Deliver authentic starter items directly to inventory (matching C# AC09.cs:88)
            from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
            GLOBAL_STARTER_PACK_MANAGER.deliver_to_player(session, send_packets=False)
            server.save_player_to_db(session)
            
            # Commence Map Entry directly (no 63, 2 confirm packet!)
            await server.commence_login(session)
        else:
            # Creation error
            await session.send_packet(PacketWriter().write_8(0).write_8(30))
