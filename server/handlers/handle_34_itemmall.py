import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [34]

async def handle(server, session, reader):
    """Handles Item Mall (Nesne Market) requests (AC 34)."""
    sub = reader.read_8()
    
    if sub == 1:
        logger.info(f"[{session.char_name}] Requesting Item Mall opening (AC 34 Sub 1)")
        
        # 1. Send Item Mall Categories/Config: AC 54 (0x36) Sub 201 (0xC9)
        # Payload: 00 01 68 00 03 66 00 03 65 00 03 67 00 02
        cat_pkt = PacketWriter().write_8(54).write_8(201)
        # We will write the exact byte sequence observed in the PCAP
        cat_payload = bytes.fromhex("0001680003660003650003670002")
        cat_pkt.write_bytes(cat_payload)
        await session.send_packet(cat_pkt)
        
        # 2. Send Wallet Balances: AC 35 (0x23) Sub 4
        # The payload is 16 bytes of zeros according to PCAP
        wallet_pkt = PacketWriter().write_8(35).write_8(4)
        wallet_pkt.write_bytes(bytes(16)) # 16 bytes of zeros
        await session.send_packet(wallet_pkt)
        
    else:
        logger.info(f"Unhandled AC 34 Sub-Code: {sub}, payload: {reader.data.hex()}")
