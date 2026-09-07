"""
Wonderland Online - Packet Protocol Dissector & Stream Reassembler.
Self-contained protocol engine with zero external dependencies on the game server.
"""

from __future__ import annotations

import struct
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Generator

XOR_KEY: int = 173  # 0xAD
SIGNATURE: int = 17652  # 0x44F4 (Little Endian: 0xF4, 0x44)
SIGNATURE_ENCRYPTED: bytes = bytes([0xF4 ^ XOR_KEY, 0x44 ^ XOR_KEY])  # b'\x59\xE9'

KNOWN_ACTION_CODES: Dict[int, str] = {
    0: "Heartbeat / Version Check / Disconnect",
    1: "Login / Authentication Request",
    2: "Character List / Selection / Chat",
    3: "Actor / NPC / Object Visual Spawn Broadcast",
    4: "Character / Entity Despawn",
    5: "Map Movement / Coordinate Sync",
    6: "Movement / Waypoint Walk",
    7: "Interactive World Object Action",
    8: "Character Stats & Attributes Sync",
    9: "Character Creation",
    10: "Combat Battle Encounter / State Broadcast",
    11: "Combat Command / Skill Cast / Target Submission",
    12: "Map Teleport / Warp Portal",
    13: "Player Action / Animation Emote",
    14: "Friends List / Social Handshake",
    15: "Companion / Pet Management & AI",
    16: "Party / Team System & Invite",
    18: "Hotbar / Quick Slot Configuration",
    19: "Player Status / Extended Stats",
    20: "NPC Interaction / Dialogue Trigger",
    21: "Item Usage / Consumable Activation",
    22: "Scene Transition / Camera Waypoint",
    23: "Inventory / Item Manipulation / Ground Loot",
    24: "Quest Engine / Step Progress / Journal Sync",
    25: "P2P Secure Trade Handshake",
    26: "Reborn Transformation / Job Evolution",
    27: "NPC Shop Buy / Sell Transaction",
    28: "Auxiliary Action / PK Duel Invitation",
    29: "Props Keeper / Bank Vault Storage",
    30: "In-Game Mail System / Mailbox Notice",
    31: "Mail Attachment / Letter Delivery",
    32: "Player Emote / Expression",
    33: "Friend System / Social Blacklist",
    34: "Item Mall Product Catalog & Points Balance",
    35: "Character Deletion",
    37: "Guild War / Battlefield State",
    39: "Guild System / Clan Roster & Storage",
    40: "Player Street Stall / Player Market",
    43: "Team Action / Party Formation",
    44: "Marriage System / Couple Teleport",
    45: "Vehicle System / Mount / Ship Voyage",
    50: "Combat Battle Result / Victory / Defeat",
    51: "PvP Duel Challenge Acceptance",
    53: "Combat Turn Action Confirmation",
    54: "Game Option / Settings Toggle",
    55: "Audio / Sound Effect Trigger",
    57: "Minigame Exit / Category Dismiss",
    59: "Ship / Vehicle World Map Voyage",
    61: "Tent Exterior Pitch / Furniture State",
    62: "Tent Furniture Placement / Movement",
    63: "Game Server Login Handshake",
    64: "Tent Crafting Station / Tool Manufacturing",
    65: "Tent Entry / Exit World Map",
    66: "Weather / Atmospheric Environmental Event",
    68: "Divorce / Marriage Annulment",
    69: "Barber NPC Hair Styling & Dyeing",
    70: "Monster Morph Transformation",
    71: "Lucky Draw / Minigame Event / Smelting Recycle",
    74: "Job Class Advancement / Rebirth",
    75: "Item Mall / Lucky Draw Wheel Spin",
    82: "Marriage Registry & Ceremony",
    84: "Viewport / Camera Focus Area",
    85: "Multi-stage Instance Dungeon Room",
    89: "Event Cutscene Animation Trigger",
    90: "Title & Achievement System Update",
    91: "Item Mall Bonus Reward Catalog & Claim",
    92: "VIP / Bonus Store Points Exchange",
    104: "Claw Machine / UFO Catcher / Gobang Board Game",
    122: "Alchemy / Compounding Preview",
    183: "Client System Option Sync",
    184: "Audio & Resolution Client Settings",
    186: "Co-op Cutscene / Team Event Synchronization",
    199: "GM / Administrative Command Packet",
    226: "Secondary Security PIN Verification",
}

KNOWN_SUB_CODES: Dict[Tuple[int, int], str] = {
    (0, 0): "Ping / Heartbeat",
    (0, 65): "Rejection (Version Mismatch)",
    (10, 1): "Battle Start",
    (10, 2): "Battle Round Begin",
    (10, 3): "Battle Heartbeat",
    (10, 6): "Battle State Sync",
    (11, 1): "Attack Action",
    (11, 2): "Skill Cast",
    (11, 3): "Use Item in Battle",
    (11, 4): "Defend",
    (11, 5): "Flee / Escape",
    (12, 1): "Warp to Map",
    (20, 1): "NPC Dialogue Init",
    (20, 2): "Dialogue Next Step",
    (20, 3): "Dialogue Option Selection",
    (23, 1): "Move Item Slot",
    (23, 2): "Drop Item to Ground",
    (23, 3): "Use Consumable Item",
    (23, 4): "Equip Item",
    (23, 5): "Full Inventory Sync",
    (23, 7): "Item Quantity Update",
    (23, 8): "Loot Item from Ground",
    (23, 57): "Marquee Announcement Notice",
    (24, 1): "Quest Step Advance",
    (24, 2): "Quest Log Sync",
    (25, 1): "Request Trade",
    (25, 2): "Accept Trade",
    (25, 3): "Add Trade Item / Gold",
    (25, 4): "Lock Trade",
    (25, 5): "Confirm Trade",
    (25, 6): "Cancel Trade",
    (27, 1): "Buy NPC Item",
    (27, 2): "Sell Item to NPC",
    (29, 1): "Bank Deposit Item",
    (29, 2): "Bank Withdraw Item",
    (29, 6): "Bank Storage Sync",
    (30, 1): "Mail Envelope Notification",
    (30, 2): "Open Mailbox",
    (30, 3): "Read Mail Content",
    (30, 4): "Send New Mail",
    (30, 5): "Delete Mail",
    (34, 1): "Item Mall Catalog Request",
    (34, 2): "Item Mall Purchase",
    (45, 1): "Mount Vehicle",
    (45, 2): "Dismount Vehicle",
    (62, 1): "Place Tent Furniture",
    (62, 2): "Pickup Tent Furniture",
    (64, 1): "Start Crafting Recipe",
    (64, 2): "Collect Crafted Product",
    (65, 1): "Pitch Personal Tent",
    (65, 2): "Pack Up Personal Tent",
    (75, 1): "Lucky Draw Spin",
    (91, 1): "Bonus Mall Catalog",
    (91, 2): "Claim Bonus Item",
    (104, 1): "Claw Machine Play",
}


def xor_crypt(data: bytes, key: int = XOR_KEY) -> bytes:
    """Fast byte-wise XOR decryption/encryption."""
    return bytes(b ^ key for b in data)


def bytes_to_ascii_preview(data: bytes) -> str:
    """Converts bytes to printable ASCII string, replacing non-printable bytes with '.'."""
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in data)


def bytes_to_hex_preview(data: bytes, max_len: int = 64) -> str:
    """Converts bytes to spaced hex string with optional truncation."""
    hex_str = " ".join(f"{b:02X}" for b in data[:max_len])
    if len(data) > max_len:
        hex_str += f" ... (+{len(data) - max_len} bytes)"
    return hex_str


@dataclass
class WLOPacket:
    """Structured representation of an individual Wonderland Online network packet."""
    packet_id: int
    timestamp: float
    datetime_str: str
    direction: str  # "C->S" (Client to Server) or "S->C" (Server to Client)
    action_code: int
    sub_code: Optional[int]
    action_name: str
    sub_name: Optional[str]
    length: int
    decrypted_payload: bytes
    encrypted_bytes: bytes
    tag: Optional[str] = None
    inferred_fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def hex_payload(self) -> str:
        return " ".join(f"{b:02X}" for b in self.decrypted_payload)

    @property
    def ascii_payload(self) -> str:
        return bytes_to_ascii_preview(self.decrypted_payload)

    @property
    def raw_hex(self) -> str:
        return " ".join(f"{b:02X}" for b in self.encrypted_bytes)

    def to_dict(self) -> Dict[str, Any]:
        """Converts packet to a JSON-serializable dictionary."""
        return {
            "packet_id": self.packet_id,
            "timestamp": self.timestamp,
            "datetime": self.datetime_str,
            "direction": self.direction,
            "action_code": self.action_code,
            "sub_code": self.sub_code,
            "action_name": self.action_name,
            "sub_name": self.sub_name,
            "length": self.length,
            "tag": self.tag,
            "hex_payload": self.hex_payload,
            "ascii_payload": self.ascii_payload,
            "raw_hex": self.raw_hex,
            "inferred_fields": self.inferred_fields,
        }

    def to_readable_card(self, elapsed_sec: float = 0.0) -> str:
        """Formats packet into an inspection card."""
        sub_str = f" Sub {self.sub_code}" if self.sub_code is not None else ""
        sub_detail = f" ({self.sub_name})" if self.sub_name else ""
        tag_str = f"Tag: [{self.tag}]\n" if self.tag else ""
        field_str = ""
        if self.inferred_fields:
            field_str = "Fields: " + ", ".join(f"{k}={v}" for k, v in self.inferred_fields.items()) + "\n"

        lines = [
            f"[{elapsed_sec:08.3f}s] #{self.packet_id:05d} | {self.direction} | AC {self.action_code} ({self.action_name}){sub_str}{sub_detail} | {self.length} bytes",
        ]
        if tag_str:
            lines.append("  " + tag_str.strip())
        if field_str:
            lines.append("  " + field_str.strip())
        lines.append(f"  HEX:   {bytes_to_hex_preview(self.decrypted_payload, max_len=48)}")
        lines.append(f"  ASCII: {bytes_to_ascii_preview(self.decrypted_payload[:48])}")
        return "\n".join(lines)


def infer_packet_fields(action_code: int, sub_code: Optional[int], payload: bytes) -> Dict[str, Any]:
    """Infers structured high-level fields from known WLO packet types."""
    fields: Dict[str, Any] = {}
    length = len(payload)

    try:
        if action_code == 2:  # Chat / Selection
            if length >= 2:
                fields["channel"] = payload[1]
                if length >= 3:
                    fields["text"] = payload[2:].decode("ascii", errors="ignore")

        elif action_code == 5:  # Map Movement
            if length >= 5:
                fields["x"] = struct.unpack_from("<H", payload, 1)[0]
                fields["y"] = struct.unpack_from("<H", payload, 3)[0]

        elif action_code == 6:  # Waypoint Walk
            if length >= 5:
                fields["target_x"] = struct.unpack_from("<H", payload, 1)[0]
                fields["target_y"] = struct.unpack_from("<H", payload, 3)[0]

        elif action_code == 12:  # Warp
            if length >= 3:
                fields["map_id"] = struct.unpack_from("<H", payload, 1)[0]

        elif action_code == 20:  # NPC Dialogue
            if sub_code == 1 and length >= 6:
                fields["click_id"] = struct.unpack_from("<I", payload, 2)[0]
            elif length >= 5:
                fields["click_id"] = struct.unpack_from("<I", payload, 1)[0]
            elif length >= 3:
                fields["dialog_id"] = struct.unpack_from("<H", payload, 1)[0]

        elif action_code == 23:  # Items
            if sub_code == 57 and length >= 3:
                fields["announcement_type"] = payload[2]
                if length >= 4:
                    fields["message"] = payload[3:].decode("ascii", errors="ignore")
            elif sub_code in (3, 4) and length >= 3:
                fields["slot"] = payload[2]
                if length >= 5:
                    fields["item_id"] = struct.unpack_from("<H", payload, 3)[0]

        elif action_code == 24:  # Quest
            if length >= 3:
                fields["quest_id"] = struct.unpack_from("<H", payload, 1)[0]
            if length >= 4:
                fields["step"] = payload[3]

        elif action_code == 27:  # NPC Shop
            if length >= 5:
                fields["item_id"] = struct.unpack_from("<H", payload, 1)[0]
                fields["quantity"] = struct.unpack_from("<H", payload, 3)[0]

        elif action_code == 34:  # Item Mall
            if length >= 5:
                fields["mall_item_id"] = struct.unpack_from("<H", payload, 1)[0]

        elif action_code == 62:  # Tent
            if length >= 7:
                fields["furniture_id"] = struct.unpack_from("<H", payload, 1)[0]
                fields["x"] = struct.unpack_from("<H", payload, 3)[0]
                fields["y"] = struct.unpack_from("<H", payload, 5)[0]

    except Exception:
        pass

    return fields


class WLOStreamReassembler:
    """
    Robust TCP streaming reassembler for Wonderland Online.
    Reconstructs individual packets from fragmented or coalesced TCP streams.
    Handles XOR-173 decryption, 0x44F4 framing, and automatic desync recovery.
    """

    def __init__(self, direction: str = "C->S"):
        self.direction = direction
        self.buffer = bytearray()
        self.packet_counter = 0

    def feed(self, chunk: bytes, active_tag: Optional[str] = None) -> List[WLOPacket]:
        """
        Feeds raw TCP bytes into the reassembler and extracts all completed WLO packets.
        """
        if not chunk:
            return []

        self.buffer.extend(chunk)
        packets: List[WLOPacket] = []

        while len(self.buffer) >= 4:
            # Check for encrypted header signature (b'\x59\xE9')
            # 0x44F4 in little-endian is [0xF4, 0x44]. XORed with 173 (0xAD) -> [0x59, 0xE9]
            sig_enc = self.buffer[0:2]
            is_encrypted = (sig_enc == SIGNATURE_ENCRYPTED)
            is_plain = (sig_enc == bytes([0xF4, 0x44]))

            if not (is_encrypted or is_plain):
                # Search forward for signature byte to recover sync
                idx_enc = self.buffer.find(SIGNATURE_ENCRYPTED, 1)
                idx_plain = self.buffer.find(bytes([0xF4, 0x44]), 1)

                candidates = [i for i in (idx_enc, idx_plain) if i != -1]
                if candidates:
                    next_sig = min(candidates)
                    del self.buffer[:next_sig]
                    continue
                else:
                    # Keep only last byte in case signature was split across boundary
                    del self.buffer[:-1]
                    break

            # Read 2-byte little-endian length
            raw_len_bytes = bytes(self.buffer[2:4])
            if is_encrypted:
                len_bytes = xor_crypt(raw_len_bytes)
            else:
                len_bytes = raw_len_bytes

            payload_len = struct.unpack("<H", len_bytes)[0]

            # Validate reasonable packet length (0 to 16,384 bytes)
            if payload_len > 16384:
                # Corrupted header, skip 1 byte and resync
                del self.buffer[0:1]
                continue

            total_packet_len = 4 + payload_len
            if len(self.buffer) < total_packet_len:
                # Incomplete packet in TCP stream, wait for next chunk
                break

            # Extract full raw frame
            full_frame = bytes(self.buffer[:total_packet_len])
            del self.buffer[:total_packet_len]

            # Extract and decrypt payload
            raw_payload = full_frame[4:]
            if is_encrypted:
                decrypted_payload = xor_crypt(raw_payload)
            else:
                decrypted_payload = raw_payload

            self.packet_counter += 1
            now = datetime.datetime.now()
            ts = now.timestamp()
            dt_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            action_code = decrypted_payload[0] if len(decrypted_payload) > 0 else 0
            sub_code = decrypted_payload[1] if len(decrypted_payload) > 1 else None
            action_name = KNOWN_ACTION_CODES.get(action_code, f"Unknown Opcode ({action_code})")
            sub_name = KNOWN_SUB_CODES.get((action_code, sub_code)) if sub_code is not None else None

            inferred = infer_packet_fields(action_code, sub_code, decrypted_payload)

            packet = WLOPacket(
                packet_id=self.packet_counter,
                timestamp=ts,
                datetime_str=dt_str,
                direction=self.direction,
                action_code=action_code,
                sub_code=sub_code,
                action_name=action_name,
                sub_name=sub_name,
                length=payload_len,
                decrypted_payload=decrypted_payload,
                encrypted_bytes=full_frame,
                tag=active_tag,
                inferred_fields=inferred,
            )
            packets.append(packet)

        return packets
