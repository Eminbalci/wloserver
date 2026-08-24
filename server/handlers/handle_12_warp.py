import asyncio
import logging
import time
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [12]


async def handle(server, session, reader):
    """Processes map loading complete response from client (AC 12)."""
    sub = reader.read_8()
    if sub == 1:
        session.is_warping = False
        session.in_map = True

        # Set warp cooldown timestamp when warp completes successfully
        session.last_warp_time = time.time()

        # Broadcast our appearance to other players on new map (remote format)
        server.broadcast_to_map(session.map_id, server.build_remote_char_spawn(session), exclude_session=session)

        logger.info(f"[{session.char_name}] Warp completed successfully.")

        # If beach cutscene is already active, ignore duplicate AC 12:1 to avoid sending unlock packets
        if getattr(session, "beach_cutscene_active", False):
            return

        # Check Beach Arrival Cutscene & Robinson Rescue
        from server.eve_event_interpreter import get_session_quest_state
        has_quest_12040 = (get_session_quest_state(session, 12040) > 0)
        is_beach_landing = (
            getattr(session, "pending_beach_cutscene", False)
            or (session.map_id == 10035 and not has_quest_12040)
        )

        if is_beach_landing and not getattr(session, "beach_cutscene_active", False):
            session.pending_beach_cutscene = False
            session.beach_cutscene_active = True
            session.beach_cutscene_step = 1
            session.dialogue_queue = []

            logger.info(f"[{session.char_name}] Triggering Beach Arrival Cutscene (Robinson rescue sequence) on Map 10035...")

            # Frame 1: Player lies unconscious on sand (Emote 9) + immobilize controls (AC 5:30) (PCAP packets [036]-[039])
            session.emote = 9
            emote_pkt = PacketWriter().write_8(32).write_8(2).write_32(session.char_id).write_8(9)
            await session.send_packet(emote_pkt)
            server.broadcast_to_map(session.map_id, emote_pkt, exclude_session=session)

            immob_pkt = PacketWriter().write_8(5).write_8(30).write_8(1).write_32(session.char_id).write_8(0)
            await session.send_packet(immob_pkt)

            # Frame 2: Camera Pan & Cinema Mode (PCAP packets [041]-[045])
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(
                PacketWriter()
                .write_8(22)
                .write_8(11)
                .write_8(6)
                .write_8(0)
                .write_8(0xFF)
                .write_8(0xFF)
            )  # Camera Pan
            await session.send_packet(PacketWriter().write_8(6).write_8(2).write_8(1))  # Cinema lock
            await session.send_packet(PacketWriter().write_8(20).write_8(11))
            await session.send_packet(PacketWriter().write_8(20).write_8(10))
            return
        else:
            # Normal map warp: Send warp completion unlock packets immediately
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
