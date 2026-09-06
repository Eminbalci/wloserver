"""
Wonderland Online Props Keeper / Storage Action Handler (Action Code 29 / 0x1D).
Reverse-engineered from authentic PCAP captures:
- propskeeper.pcapng (S2C: 1d 06, 14 09, 23 0c, 14 08)

Protocol:
- AC 29 Sub 6 (S->C): Opens Keeper Storage window (0x1D, 0x06).
- AC 29 Sub 5 (S->C): Synchronizes stored items list.
- AC 29 Sub 1 (C->S): Deposit item from inventory slot to keeper: [0x1D, 0x01, inv_slot (1B), amount (2B LE)].
- AC 29 Sub 2 (C->S): Withdraw item from keeper slot to inventory: [0x1D, 0x02, vault_slot (1B), amount (2B LE)].
"""

import logging
from typing import Any
from server.network import PacketWriter, PacketReader
from server.bank_system import GLOBAL_BANK_MANAGER

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [29]


async def handle(server: Any, session: Any, reader: PacketReader) -> None:
    """Dispatches Action Code 29 Props Keeper / Warehouse Storage packets."""
    sub = reader.read_8()
    logger.info(f"[{session.char_name}] AC29 Props Keeper Sub={sub} (0x{sub:02X}), data={reader.data.hex()}")

    # Sub 6: Open Storage Window request
    if sub == 6:
        # S2C: 1d 06
        await session.send_packet(PacketWriter().write_8(29).write_8(6))
        # Synchronize stored items
        await session.send_packet(GLOBAL_BANK_MANAGER.build_vault_packet(session))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

    # Sub 1: Deposit Item to Keeper
    elif sub == 1:
        inv_slot = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        amount = reader.read_16() if reader.remaining_bytes() >= 2 else (reader.read_8() if reader.remaining_bytes() >= 1 else 1)
        if inv_slot > 0 and amount > 0:
            await GLOBAL_BANK_MANAGER.deposit_item(server, session, inv_slot, amount)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

    # Sub 2: Withdraw Item from Keeper
    elif sub == 2:
        vault_slot = reader.read_8() if reader.remaining_bytes() >= 1 else 0
        amount = reader.read_16() if reader.remaining_bytes() >= 2 else (reader.read_8() if reader.remaining_bytes() >= 1 else 1)
        if vault_slot > 0 and amount > 0:
            await GLOBAL_BANK_MANAGER.withdraw_item(server, session, vault_slot, amount)
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

    else:
        logger.debug(f"[{session.char_name}] AC29 unhandled sub {sub}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
