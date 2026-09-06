"""
Wonderland Online Cutscene & CG Movie Synchronization Handler (AC 186)
Ported from C# Src/Network/ActionCodes/AC186.cs
"""

import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [186]


async def handle(server, session, reader):
    """Handles CG Animation / Cutscene playback synchronization (AC 186)."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name or getattr(session, 'username', 'Player')}] AC 186 Cutscene packet. Sub={sub}")

    if sub == 9:  # Cutscene playback / Co-op room query (PCAP / C# AC186.Recv9)
        cutscene_id = reader.read_16() if reader.remaining_bytes() >= 2 else 1
        logger.info(f"[{session.char_name}] Client acknowledged Cutscene/Room #{cutscene_id} readiness -> Sending Playback ACK.")
        session.cutscene_ready = True

        # 1. Server responds with CG playback acknowledgment (Official PCAP Frame 1942 / C# AC186.Recv9):
        # [AC=186 (1B)][Sub=9 (1B)][cutsceneId (2B)][status=1 (1B)][reserved (4B)]
        resp = (
            PacketWriter()
            .write_8(186)
            .write_8(9)
            .write_16(cutscene_id)
            .write_8(1)  # 1 = Active / Playing
            .write_32(0)  # Reserved padding
        )
        await session.send_packet(resp)

    elif sub == 12:  # Co-op Event Room State Query / Sync
        room_id = reader.read_16() if reader.remaining_bytes() >= 2 else 1
        logger.info(f"[{session.char_name}] AC 186 Sub 12 Room Sync for #{room_id}")
        state_pkt = (
            PacketWriter()
            .write_8(186)
            .write_8(12)
            .write_16(room_id)
            .write_8(1)
            .write_8(4)
            .write_8(0)
        )
        await session.send_packet(state_pkt)

    elif sub == 8:  # Co-op Event Room Join / Ready Handshake
        room_id = reader.read_16() if reader.remaining_bytes() >= 2 else 1
        logger.info(f"[{session.char_name}] AC 186 Sub 8 Room Join: #{room_id}")
        ack_pkt = PacketWriter().write_8(186).write_8(8).write_16(room_id).write_8(1)
        await session.send_packet(ack_pkt)

    else:
        logger.info(f"[{session.char_name}] Unhandled AC 186 Subcode: {sub}")
