"""
Wonderland Online Quest Journal & Guild Interaction Handler (AC 39)
Ported from C# Src/Network/ActionCodes/AC39.cs and wlo.pserver.core/Game/PlayerRelated/Guild.cs
"""

import logging
from server.network import PacketWriter
from server.quests import GLOBAL_QUEST_ENGINE
from server.guild_system import GLOBAL_GUILD_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [39]


async def handle(server, session, reader):
    """Processes quest journal and guild interactions (AC 39)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC39 Handler. SubCmd={sub}")

    if sub == 1:  # F6 Quest Journal / Guild Info
        # Check if in guild, send guild info too
        guild = GLOBAL_GUILD_MANAGER.get_player_guild(session.char_id)
        if guild:
            await GLOBAL_GUILD_MANAGER.send_guild_info(session)
        await GLOBAL_QUEST_ENGINE.send_quest_journal(session)

    elif sub == 2:  # Create Guild or Guild Invite/Help
        # If payload contains a guild name string -> Create Guild
        if reader.remaining_bytes() >= 2:
            param = reader.read_string()
            if param and len(param) >= 2 and not param.isdigit():
                await GLOBAL_GUILD_MANAGER.create_guild(server, session, param)
                return

        target_char_id = reader.read_32() if reader.remaining_bytes() >= 4 else 0
        target = server.sessions.get(target_char_id)
        if target:
            await GLOBAL_GUILD_MANAGER.invite_player(session, target)
        else:
            await session.send_packet(PacketWriter().write_8(39).write_8(2).write_8(1))

    elif sub == 3:  # Accept Guild Invite
        await GLOBAL_GUILD_MANAGER.accept_invite(server, session)

    elif sub == 7:  # Abandon / Reset Quest
        quest_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        if quest_id > 0:
            await GLOBAL_QUEST_ENGINE.reset_quest(session, quest_id)
        writer = PacketWriter().write_8(39).write_8(7).write_8(1)
        await session.send_packet(writer)

    elif sub == 12:  # Guild Member List Request
        await GLOBAL_GUILD_MANAGER.send_guild_members(session)

    elif sub in (5, 10, 11, 16, 17, 19, 50, 51):
        writer = PacketWriter().write_8(39).write_8(sub).write_8(1)
        await session.send_packet(writer)

    else:
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
