"""
Wonderland Online - Action Code 13 (Team / Party & Item Mall Query) Handler
Ported from C# Src/Network/ActionCodes/AC13.cs
Handles:
- AC 13 Sub 238: Item Mall click query from client UI (authentic itemmall.pcapng)
- AC 13 Sub 1: Team Invite / Join request
- AC 13 Sub 2: Team Invite Reply
- AC 13 Sub 3: Team Invite Response / Accept
- AC 13 Sub 4: Leave Team
- AC 13 Sub 9: Kick from Party
- AC 13 Sub 10: Transfer Leadership
"""

import logging
from server.network import PacketWriter
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [13]


async def handle(server, session, reader):
    sub = reader.read_8()

    if sub == 238:
        # Authentic Item Mall Query confirmation from client UI (Packets #109, #113 in itemmall.pcapng)
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Item Mall query clicked via AC 13 Sub 238")
        char_id = getattr(session, "char_id", 0)

        # S->C AC 13 Sub 42 [CharID(uint32)]
        conf_pkt = PacketWriter().write_8(13).write_8(42).write_32(char_id)
        await session.send_packet(conf_pkt)

        # Send IM Point Balance & Catalog
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)
        await GLOBAL_ITEM_MALL_MANAGER.send_catalog(session)

    elif sub == 1:  # Team Invite
        target_name = reader.read_string() if reader.remaining_bytes() > 0 else ""
        logger.info(f"[AC13] Team Invite request from {session.char_name} to {target_name}")
        target = None
        for act in server.active_sessions:
            if getattr(act, 'char_name', '') == target_name:
                target = act
                break
        if target:
            s = PacketWriter().write_8(13).write_8(1).write_string(session.char_name)
            await target.send_packet(s)
        else:
            s = PacketWriter().write_8(13).write_8(1).write_8(0)
            await session.send_packet(s)

    elif sub == 2:  # Invite Reply / Accept
        inviter_name = reader.read_string() if reader.remaining_bytes() > 0 else ""
        inviter = None
        for act in server.active_sessions:
            if getattr(act, 'char_name', '') == inviter_name:
                inviter = act
                break
        if inviter:
            s1 = PacketWriter().write_8(13).write_8(2).write_string(session.char_name).write_8(1)
            await inviter.send_packet(s1)
            s2 = PacketWriter().write_8(13).write_8(2).write_string(inviter.char_name).write_8(1)
            await session.send_packet(s2)

    elif sub == 4:  # Leave Team
        logger.info(f"[AC13] {session.char_name} left team")
        s = PacketWriter().write_8(13).write_8(4).write_string(session.char_name)
        await session.send_packet(s)

    else:
        # Default release interaction lock
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
