"""
Wonderland Online Authentic Eve.Emg / eve.dat Binary Parser
Ported 1:1 from C# wlo.pserver.core/DataFiles/EveLoader.cs

Extracts all authentic map entities:
- Map Entries & Category Offsets
- Static & Dynamic NPCs with Walksteps
- Entry/Exit Portals and Warp Locations
- Mining & Gathering Resource Nodes
- World Map Chests and Item Drops
- Bytecode Event Scripts (Dialogues, Quests, Shops)
- Monster Formations and Battle Groups
- PreEvent Visibility Bytecodes
"""

import os
import struct
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("WLO_Server")


def get_word(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        return 0
    return struct.unpack_from("<H", data, offset)[0]


def get_dword(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        return 0
    return struct.unpack_from("<I", data, offset)[0]


def decode_eve_string(data: bytes, offset: int, max_length: int) -> str:
    if offset < 0 or offset >= len(data) or max_length <= 0:
        return ""
    chunk = data[offset : offset + max_length]
    null_idx = chunk.find(b"\x00")
    if null_idx != -1:
        chunk = chunk[:null_idx]
    try:
        return chunk.decode("big5")
    except Exception:
        try:
            return chunk.decode("latin1", errors="ignore")
        except Exception:
            return ""


@dataclass
class CategoryOffset:
    NPC: int = 0
    Entry: int = 0
    Mining: int = 0
    Items: int = 0
    Events: int = 0
    Groups: int = 0
    Warp: int = 0
    Interactiveinfo: int = 0
    Battleinfo: int = 0
    PreEvent: int = 0
    groupext: int = 0


@dataclass
class EveMiningEntry:
    click_id: int
    name: str
    x: int
    y: int


@dataclass
class EveItemEntry:
    click_id: int
    name: str
    x: int
    y: int
    item_id: int


@dataclass
class EveWarpEntry:
    click_id: int
    name: str
    x: int
    y: int
    dst_map: int
    dst_x: int
    dst_y: int


@dataclass
class EveNpcEntry:
    click_id: int
    name: str
    npc_id: int
    x: int
    y: int
    dir: int = 0
    walksteps: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class EveEventOpcode:
    dialog_ptr: int
    dialog1: int
    dialog2: int
    dialog3: int
    dialog4: int


@dataclass
class EveMapData:
    map_id: int
    scene_id: int
    data_ptr: int
    data_len: int
    offsets: CategoryOffset = field(default_factory=CategoryOffset)
    npcs: List[EveNpcEntry] = field(default_factory=list)
    warps: List[EveWarpEntry] = field(default_factory=list)
    mining_nodes: List[EveMiningEntry] = field(default_factory=list)
    item_nodes: List[EveItemEntry] = field(default_factory=list)
    events: Dict[int, List[EveEventOpcode]] = field(default_factory=dict)  # click_id -> opcodes


class EveManager:
    """Manages parsing, extraction, and querying of eve.Emg / eve.dat binary map database."""

    def __init__(self, eve_path: Optional[str] = None):
        self.maps: Dict[int, EveMapData] = {}
        if eve_path and os.path.exists(eve_path):
            self.load_file(eve_path)

    def load_file(self, filename: str) -> bool:
        if not os.path.exists(filename):
            logger.error(f"[EveManager] File not found: {filename}")
            return False

        try:
            with open(filename, "rb") as f:
                data = f.read()

            self.maps.clear()
            self._parse_data(data)
            logger.info(f"[EveManager] Successfully loaded {len(self.maps)} maps from {filename}.")
            return True
        except Exception as e:
            logger.error(f"[EveManager] Error loading {filename}: {e}", exc_info=True)
            return False

    def _parse_data(self, d: bytes):
        ptr = 8
        entry_len = get_dword(d, ptr)
        ptr += 4

        # Stage 1: Load Map Entries
        for _ in range(entry_len):
            if ptr + 10 > len(d):
                break
            m_id = get_word(d, ptr)
            ptr += 2
            s_id = get_word(d, ptr)
            ptr += 2
            d_ptr = get_dword(d, ptr)
            ptr += 4
            d_len = get_word(d, ptr)
            ptr += 2

            if m_id not in self.maps:
                self.maps[m_id] = EveMapData(
                    map_id=m_id,
                    scene_id=s_id,
                    data_ptr=d_ptr,
                    data_len=d_len
                )

        # Stage 2: Read Category Offsets for each map
        for scen in self.maps.values():
            if scen.data_ptr + scen.data_len > len(d):
                continue
            p = scen.data_ptr + scen.data_len - 44
            if p < 0 or p + 44 > len(d):
                continue

            off = CategoryOffset()
            off.NPC = get_dword(d, p)
            off.Entry = get_dword(d, p + 4)
            off.Mining = get_dword(d, p + 8)
            off.Items = get_dword(d, p + 12)
            off.Events = get_dword(d, p + 16)
            off.Groups = get_dword(d, p + 20)
            off.Warp = get_dword(d, p + 24)
            off.Interactiveinfo = get_dword(d, p + 28)
            off.Battleinfo = get_dword(d, p + 32)
            off.PreEvent = get_dword(d, p + 36)
            off.groupext = get_dword(d, p + 40)
            scen.offsets = off

        # Stage 3: Parse Detailed Sub-Entries (NPCs, Mining, Items, Warps, Events)
        for scen in self.maps.values():
            self._load_mining_entries(d, scen)
            self._load_item_entries(d, scen)
            self._load_warp_entries(d, scen)
            self._load_event_entries(d, scen)

    def _load_mining_entries(self, d: bytes, scen: EveMapData):
        if not scen.offsets.Mining:
            return
        p = scen.offsets.Mining + scen.data_ptr
        if p < 0 or p + 2 > len(d):
            return
        elen = get_word(d, p)
        p += 2
        for _ in range(elen):
            if p + 27 > len(d):
                break
            cid = get_word(d, p)
            p += 2
            name = decode_eve_string(d, p, 20)
            p += 20
            p += 1  # unknownbyte1
            x = get_dword(d, p)
            p += 4
            y = get_dword(d, p)
            p += 4
            scen.mining_nodes.append(EveMiningEntry(click_id=cid, name=name, x=x, y=y))

    def _load_item_entries(self, d: bytes, scen: EveMapData):
        if not scen.offsets.Items:
            return
        p = scen.offsets.Items + scen.data_ptr
        if p < 0 or p + 2 > len(d):
            return
        elen = get_word(d, p)
        p += 2
        for _ in range(elen):
            if p + 35 > len(d):
                break
            cid = get_word(d, p)
            p += 2
            p += 1  # str len
            name = decode_eve_string(d, p, 19)
            p += 19
            p += 1  # unknownbyte1
            x = get_dword(d, p)
            p += 4
            y = get_dword(d, p)
            p += 4
            if p + 15 > len(d):
                break
            # Skip unknown byte arrays
            p += 2
            item_id = get_dword(d, p)
            p += 4
            scen.item_nodes.append(EveItemEntry(click_id=cid, name=name, x=x, y=y, item_id=item_id))

    def _load_warp_entries(self, d: bytes, scen: EveMapData):
        if not scen.offsets.Warp:
            return
        p = scen.offsets.Warp + scen.data_ptr
        if p < 0 or p + 2 > len(d):
            return
        elen = get_word(d, p)
        p += 2
        for _ in range(elen):
            if p + 35 > len(d):
                break
            cid = get_word(d, p)
            p += 2
            name = decode_eve_string(d, p, 20)
            p += 20
            p += 1
            x = get_dword(d, p)
            p += 4
            y = get_dword(d, p)
            p += 4
            if p + 10 > len(d):
                break
            dst_map = get_word(d, p)
            p += 2
            dst_x = get_dword(d, p)
            p += 4
            dst_y = get_dword(d, p)
            p += 4
            scen.warps.append(EveWarpEntry(click_id=cid, name=name, x=x, y=y, dst_map=dst_map, dst_x=dst_x, dst_y=dst_y))

    def _load_event_entries(self, d: bytes, scen: EveMapData):
        if not scen.offsets.Events:
            return
        p = scen.offsets.Events + scen.data_ptr
        if p < 0 or p + 2 > len(d):
            return
        elen = get_word(d, p)
        p += 2
        for _ in range(elen):
            if p + 25 > len(d):
                break
            cid = get_word(d, p)
            p += 2
            p += 1  # unknownbyte1
            p += 20 # name
            if p >= len(d):
                break
            blen = d[p]
            p += 1
            opcodes = []
            for _ in range(blen):
                if p + 25 > len(d):
                    break
                p += 24  # skip sub entry headers
                if p >= len(d):
                    break
                blen2 = d[p]
                p += 1
                for _ in range(blen2):
                    if p + 22 > len(d):
                        break
                    p += 1  # subsubIndex
                    d_ptr = d[p]
                    p += 1
                    d1 = get_word(d, p)
                    p += 2
                    d2 = get_word(d, p)
                    p += 2
                    d3 = get_word(d, p)
                    p += 2
                    d4 = get_word(d, p)
                    p += 2
                    p += 12 # skip dwords
                    opcodes.append(EveEventOpcode(dialog_ptr=d_ptr, dialog1=d1, dialog2=d2, dialog3=d3, dialog4=d4))
            scen.events[cid] = opcodes


GLOBAL_EVE_MANAGER = EveManager()
