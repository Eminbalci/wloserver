import logging
import random
from server.network import PacketWriter
from server.gameserver import add_item_to_inventory

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [104]

async def handle(server, session, reader):
    """Processes Lucky Draw and minigames (AC 104)."""
    sub = reader.read_8()
    
    if sub == 1:  # Lucky Draw Spin Request
        logger.info(f"[{session.char_name}] Requested Lucky Draw Spin")
        
        # In a real scenario, we should deduct a "Lucky Draw Ticket" or Item Mall points.
        # Check if player has ticket etc.
        
        # PCAP shows [104, 1] from client.
        # Server responds with [23, 6] Add Item, then [104, 1, 02, category?, index?]
        
        # Mock rewards
        # 100653: Holy Water
        # 100652: Tear of Angel
        # 48013: UFO (jackpot)
        rewards = [
            (100653, 1, 5, 1), # Holy Water, category 5, index 1
            (100652, 1, 5, 2), # Tear of Angel, category 5, index 2
            (100652, 1, 4, 3),
            (48013, 1, 3, 4),  # UFO
            (100651, 1, 2, 5), # Memory Card
        ]
        
        reward_item, qty, cat, idx = random.choice(rewards)
        
        # Add item to inventory
        slot = add_item_to_inventory(session, reward_item, qty)
        
        if slot is not None:
            server.save_player_to_db(session)
            
            # Send inventory update (AC 23 Sub 6 - Add Item)
            # Payload: 17 06 [4 bytes ItemID] [1 byte Qty] [26 bytes padding]
            item_pkt = PacketWriter()
            item_pkt.write_8(23).write_8(6).write_32(reward_item).write_8(qty).write_bytes(bytes(26))
            await session.send_packet(item_pkt)
            
            # Send Lucky Draw result
            # Payload: 68 01 02 [Cat] [Idx]
            # In PCAP: 68 01 02 05 01, 68 01 02 05 02, 68 01 02 04 03
            draw_res = PacketWriter().write_8(104).write_8(1).write_8(2).write_8(cat).write_8(idx)
            await session.send_packet(draw_res)
            
            # Optional: Broadcast if it's a jackpot (e.g. UFO)
            if reward_item == 48013:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"Congratulations! {session.char_name} won a UFO from Lucky Draw!"
                )
                server.broadcast_to_map(session.map_id, sys_msg)
        else:
            # Inventory full
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Inventory full. Cannot use Lucky Draw.")
            await session.send_packet(sys_msg)
