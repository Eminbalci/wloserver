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
            session.beach_cutscene_stage = 1
            session.dialogue_queue = []
            session.emote = 9

            logger.info(f"[{session.char_name}] Triggering Beach Arrival Cutscene (Robinson rescue sequence) on Map 10035...")

            # Authentic PCAP Packets 31-35: Scene & Map Setup
            await session.send_packet(PacketWriter().write_bytes(bytes.fromhex("178a")))
            await session.send_packet(PacketWriter().write_8(23).write_8(122).write_32(session.char_id))
            await session.send_packet(PacketWriter().write_bytes(bytes.fromhex("17dd00")))

            # Packet 34: AC 22 Sub 4 Waypoint nodes (114 bytes)
            wp_hex = (
                "16040100ff006004a5080100000000000200000041035e07010000000000"
                "03000000dd032f08010000000000040000000b027105010000000000"
                "050000007408a807010000000000060000005405c008010000000000"
                "0700000017055b080100000000000800ff0040048a08010000000000"
            )
            await session.send_packet(PacketWriter().write_bytes(bytes.fromhex(wp_hex)))

            # Packet 35: AC 23 Sub 4 (32 bytes)
            await session.send_packet(PacketWriter().write_bytes(bytes.fromhex("17040301006aa00000dc06390db400000003020021b40000d608e51000000000")))

            # Packet 36: AC 32 Sub 2 (Player lies unconscious on sand, Emote 9)
            emote_pkt = PacketWriter().write_8(32).write_8(2).write_32(session.char_id).write_8(9)
            await session.send_packet(emote_pkt)
            server.broadcast_to_map(session.map_id, emote_pkt, exclude_session=session)

            # Packets 37-39: Visual sync & immobilize player controls (AC 5:30)
            await session.send_packet(PacketWriter().write_8(23).write_8(76).write_32(session.char_id))
            await session.send_packet(PacketWriter().write_bytes(bytes.fromhex("1766")))
            await session.send_packet(PacketWriter().write_8(5).write_8(30).write_8(1).write_32(session.char_id).write_8(0))

            # Packets 41-45: Camera Pan & Cinema Mode
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(22).write_8(11).write_8(6).write_8(0).write_8(0xFF).write_8(0xFF)) # Camera Pan
            await session.send_packet(PacketWriter().write_8(6).write_8(2).write_8(1)) # Cinema mode on
            await session.send_packet(PacketWriter().write_8(20).write_8(11))
            await session.send_packet(PacketWriter().write_8(20).write_8(10)) # Advance trigger for camera move
            logger.info(f"[{session.char_name}] Beach Cutscene Stage 1: Dispatched Camera Pan and Cinema Mode.")
            return
        else:
            # Normal map warp: Send warp completion unlock packets immediately
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)
            if hasattr(server, "build_inventory_packet"):
                await session.send_packet(server.build_inventory_packet(session))
