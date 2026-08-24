import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [0]

async def handle(server, session, reader):
    """Processes client connection handshake (AC 0)."""
    logger.info(f"[{session.ip}] Client handshake received.")
    
    # Respond with AC 1 Sub 9 (Server Version)
    v_ack = PacketWriter()
    v_ack.write_8(1)
    v_ack.write_8(9)
    v_ack.write_bytes(bytes([101, 0, 1]))
    server_version = getattr(server, "SERVER_VERSION", "Mamiletta")
    v_ack.write_string_n(server_version)
    await session.send_packet(v_ack)

    # Authentic WLO Mall Category Catalog Matrix (AC 54 Sub 201) from itemmall.pcapng & C# AC0.cs
    mall_matrix = PacketWriter()
    mall_matrix.write_8(54)
    mall_matrix.write_8(201)
    mall_matrix.write_bytes(bytes([0, 1, 101, 0, 3, 103, 0, 2, 104, 0, 3, 102, 0, 3]))
    await session.send_packet(mall_matrix)
    
    # Respond with AC 54 Sub 29 (Sub-server Configuration)
    subserver_config = getattr(server, "SUBSERVER_CONFIG", bytes([
        37, 1, 145, 1, 2, 101, 0, 2, 102, 0, 2, 103, 0, 2, 106, 0, 2, 202, 0, 2, 201, 0, 2,
        204, 0, 2, 203, 0, 2, 45, 1, 2, 47, 1, 1, 105, 0, 2, 46, 1, 1, 146, 1, 1, 104, 0,
        2, 107, 0, 2, 148, 1, 1, 147, 1, 1, 245, 1, 2, 246, 1, 1, 247, 1, 1, 234, 3, 1,
        235, 3, 1, 78, 4, 1, 79, 4, 1, 35, 3, 1, 33, 3, 2, 34, 3, 1, 233, 3, 2, 133, 3,
        1, 135, 3, 1, 134, 3, 1, 77, 4, 2
    ]))
    config = PacketWriter()
    config.write_8(54)
    config.write_8(29)
    config.write_bytes(subserver_config)
    await session.send_packet(config)
