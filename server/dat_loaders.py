"""
Wonderland Online Unified Binary DAT Loader Suite
Ported from C# wlo.pserver.core & PhoenixData data file parsers:
1. Item.dat (PhxItemDat.cs) - XOR Decrypted Item Database
2. Npc.dat (PhxNpcDat.cs) - 20-byte struct Monster/NPC stats & drop lists
3. Talk.dat (PhxTalkDat.cs) - 17,494 records of 292-byte reversed dialogue trees
4. Compound.dat & Compound2.dat (Compound2Dat.cs) - 65-byte Alchemy & Crafting recipes
5. SceneData.dat (SceneDataManager.cs) - 131-byte Map and BGM metadata
"""

import os
import re
import struct
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger("WLO_Server")


# =========================================================================
# 1. Item.dat Parser (PhxItemDat.cs)
# =========================================================================

def decode_item_32(val: int) -> int:
    return ((val ^ 0x0B80F4B4) - 9) & 0xFFFFFFFF


def decode_item_16(val: int) -> int:
    return ((val ^ 0xEFC3) - 9) & 0xFFFF


def decode_item_8(val: int) -> int:
    return ((val ^ 0x9A) - 9) & 0xFF


@dataclass
class ItemInfo:
    item_id: int
    name: str
    item_type: int = 0
    wear_slot: int = 0
    price: int = 0
    grade: int = 0
    hp: int = 0
    sp: int = 0
    atk: int = 0
    defs: int = 0
    matk: int = 0
    mdef: int = 0
    spd: int = 0


class ItemDatLoader:
    def __init__(self, file_path: Optional[str] = None):
        self.items: Dict[int, ItemInfo] = {}
        if not file_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "Item.dat")
            if os.path.exists(default_path):
                file_path = default_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            self.items.clear()
            # Parse records
            ptr = 0
            while ptr + 60 <= len(data):
                raw_id = struct.unpack_from("<H", data, ptr)[0]
                item_id = decode_item_16(raw_id)
                if item_id == 0 or item_id > 65000:
                    ptr += 2
                    continue

                name_raw = data[ptr + 2 : ptr + 22]
                null_idx = name_raw.find(b"\x00")
                if null_idx != -1:
                    name_raw = name_raw[:null_idx]
                try:
                    name = name_raw.decode("big5")
                except Exception:
                    name = name_raw.decode("latin1", errors="ignore")

                self.items[item_id] = ItemInfo(item_id=item_id, name=name)
                ptr += 60

            logger.info(f"[ItemDatLoader] Loaded {len(self.items)} items from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[ItemDatLoader] Error reading {file_path}: {e}")
            return False


# =========================================================================
# 2. Npc.dat Parser (PhxNpcDat.cs)
# =========================================================================

@dataclass
class NpcInfo:
    npc_id: int
    name: str
    level: int = 1
    hp: int = 100
    sp: int = 50
    str_val: int = 10
    con_val: int = 10
    int_val: int = 10
    wis_val: int = 10
    agi_val: int = 10
    spd_val: int = 10
    element: int = 0
    drop_item_ids: List[int] = field(default_factory=list)


class NpcDatLoader:
    """Parses authentic Npc.dat with exactly 138-byte records and XOR 0x5209 template IDs."""

    def __init__(self, file_path: Optional[str] = None):
        self.npcs: Dict[int, NpcInfo] = {}
        self.npc_names: Dict[int, str] = {}
        if not file_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "Npc.dat")
            if os.path.exists(default_path):
                file_path = default_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            self.npcs.clear()
            self.npc_names.clear()
            record_size = 138  # Authentic WLO Npc.dat record size
            total_records = len(data) // record_size

            for r in range(1, total_records):
                off = r * record_size
                if off + 14 > len(data):
                    break

                raw_id = struct.unpack_from("<H", data, off + 12)[0]
                npc_id = ((raw_id ^ 0x5209) - 1) & 0xFFFF
                if npc_id == 0 or npc_id > 65000:
                    continue

                # Extract reversed ASCII name from off+2..off+12
                raw_name_bytes = data[off + 2 : off + 12]
                valid_bytes = [b for b in raw_name_bytes if 32 <= b <= 126]
                name = "".join(chr(b) for b in reversed(valid_bytes)).strip()
                if not name:
                    null_idx = raw_name_bytes.find(b"\x00")
                    trimmed = raw_name_bytes[:null_idx] if null_idx != -1 else raw_name_bytes
                    try:
                        name = trimmed.decode("big5").strip()
                    except Exception:
                        name = ""

                if name:
                    self.npc_names[npc_id] = name

                level = data[off + 44] if off + 44 < len(data) else 1
                hp = struct.unpack_from("<I", data, off + 45)[0] if off + 49 <= len(data) else 100
                sp = struct.unpack_from("<I", data, off + 49)[0] if off + 53 <= len(data) else 50

                self.npcs[npc_id] = NpcInfo(
                    npc_id=npc_id,
                    name=name or f"NPC #{npc_id}",
                    level=max(1, level),
                    hp=max(10, hp),
                    sp=sp
                )

            logger.info(f"[NpcDatLoader] Loaded {len(self.npc_names)} authentic NPCs from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[NpcDatLoader] Error reading {file_path}: {e}")
            return False

    def get_npc_name(self, template_id: int) -> str:
        """Returns the canonical authentic NPC name from Npc.dat."""
        if template_id in self.npc_names and self.npc_names[template_id]:
            return self.npc_names[template_id]
        if template_id in self.npcs and self.npcs[template_id].name:
            return self.npcs[template_id].name
        if 14000 <= template_id < 15000:
            return "Villager"
        if template_id == 19039:
            return "Coconut Node"
        if template_id in (19035, 16006):
            return "Treasure Chest"
        return f"NPC #{template_id}"


# =========================================================================
# 3. Talk.dat Parser (PhxTalkDat.cs)
# =========================================================================

class TalkDatLoader:
    """Parses authentic Talk.dat with exactly 17,494 records of 292 bytes each."""

    def __init__(self, file_path: Optional[str] = None):
        self.dialogues: Dict[int, str] = {}
        self._by_index: Dict[int, str] = {}
        self._by_offset: Dict[int, str] = {}
        
        if not file_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "Talk.dat")
            if os.path.exists(default_path):
                file_path = default_path
                
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            self.dialogues.clear()
            self._by_index.clear()
            self._by_offset.clear()
            
            record_size = 292
            total_records = len(data) // record_size

            for r in range(total_records):
                off = r * record_size
                if off + record_size > len(data):
                    break

                talk_id = struct.unpack_from("<H", data, off)[0]
                length = data[off + 2]
                if length <= 0 or length > 250:
                    continue

                text_start = off + record_size - 35 - length
                if text_start < off or text_start + length > len(data):
                    continue

                raw_bytes = data[text_start : text_start + length]
                reversed_bytes = raw_bytes[::-1]  # Reverse text

                try:
                    text = reversed_bytes.decode("big5").strip()
                except Exception:
                    text = reversed_bytes.decode("latin1", errors="ignore").strip()

                if text.startswith("fffff"):
                    text = text[5:].strip()

                if text:
                    if talk_id > 0:
                        self.dialogues[talk_id] = text
                    self._by_index[r] = text
                    self._by_offset[off] = text
                    self._by_offset[text_start] = text

            logger.info(f"[TalkDatLoader] Loaded {len(self.dialogues)} dialogues ({len(self._by_index)} indexed) from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[TalkDatLoader] Error reading {file_path}: {e}")
            return False

    def get(self, talk_id: int, default: str = "", player_name: Optional[str] = None) -> str:
        """Resolves dialogue string by TalkID, byte offset, or section record index."""
        if not talk_id:
            return default

        raw_text = None
        lookup_id = (talk_id & 0xFFFF) if (talk_id > 0xFFFF and (talk_id & 0xFFFF) >= 10000) else talk_id

        # 1. System Section (11000..11100)
        if 11000 <= lookup_id <= 11100:
            rec_idx = lookup_id - 11000
            raw_text = self._by_index.get(rec_idx)

        # 2. Storyline & Companion Section (20000..29999)
        elif 20000 <= lookup_id <= 29999:
            rec_idx = lookup_id - 18904
            raw_text = self._by_index.get(rec_idx)

        # 3. World & Village Section (30000..49999)
        elif 30000 <= lookup_id <= 49999:
            rec_idx = lookup_id - 23105
            raw_text = self._by_index.get(rec_idx)

        # 4. Direct Byte Offset lookup
        if not raw_text:
            raw_text = self._by_offset.get(talk_id)
            if not raw_text and talk_id > 20000:
                raw_text = self._by_index.get(talk_id // 292)

        # 5. Direct ID or pure ID lookup
        if not raw_text:
            raw_text = self.dialogues.get(talk_id) or self.dialogues.get(talk_id & 0xFFFF) or self._by_index.get(talk_id)

        # 6. Universal Chapter Bases (60000+, 50000+, 40000+, 30000+, 20000+)
        if not raw_text:
            for b in (60000, 50000, 40000, 30000, 20000):
                if talk_id >= b:
                    calc_idx = talk_id - b
                    if calc_idx in self._by_index:
                        raw_text = self._by_index[calc_idx]
                        break

        if not raw_text:
            return default

        # Clean tags
        cleaned = raw_text
        if player_name:
            cleaned = cleaned.replace('#n/#n', player_name).replace('#n', player_name)
        cleaned = re.sub(r'#s[a-zA-Z0-9_-]+/#s', '', cleaned)
        cleaned = re.sub(r'#f[0-9]+/#f', '', cleaned)
        cleaned = re.sub(r'#[RGBYrgby](.*?)/#[RGBYrgby]', r'\1', cleaned)
        cleaned = re.sub(r'#[a-zA-Z0-9]+/[#a-zA-Z0-9]+', '', cleaned)
        return cleaned.strip()


# =========================================================================
# 4. Compound.dat & Compound2.dat Parser (Compound2Dat.cs)
# =========================================================================

@dataclass
class CompoundRecipe:
    build_code: int
    result_item_id: int
    plan_id: int
    tool_id: int
    materials: List[Tuple[int, int]] = field(default_factory=list)  # (item_id, count)
    build_time: int = 0


class CompoundDatLoader:
    """Parses 65-byte fixed binary compounding recipes from Compound.dat & Compound2.dat."""

    def __init__(self, file_path: Optional[str] = None):
        self.recipes: List[CompoundRecipe] = []
        if not file_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "Compound2.dat")
            if not os.path.exists(default_path):
                default_path = os.path.join(base_dir, "data", "Compound.dat")
            if os.path.exists(default_path):
                file_path = default_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path: str, clear: bool = True) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            if clear:
                self.recipes.clear()

            with open(file_path, "rb") as f:
                data = f.read()

            record_size = 65
            total = len(data) // record_size

            for r in range(total):
                off = r * record_size
                if off + record_size > len(data):
                    break

                b_code, res_id, p_id = struct.unpack_from("<HHH", data, off)
                tool_id = struct.unpack_from("<H", data, off + 7)[0]
                ammt_recv = data[off + 9]

                mats = []
                m1 = struct.unpack_from("<H", data, off + 13)[0]
                c1 = data[off + 15]
                if m1 > 0 and c1 > 0:
                    mats.append((m1, c1))

                m2 = struct.unpack_from("<H", data, off + 16)[0]
                c2 = data[off + 18]
                if m2 > 0 and c2 > 0:
                    mats.append((m2, c2))

                m3 = struct.unpack_from("<H", data, off + 19)[0]
                c3 = data[off + 21]
                if m3 > 0 and c3 > 0:
                    mats.append((m3, c3))

                m4 = struct.unpack_from("<H", data, off + 22)[0]
                c4 = data[off + 24]
                if m4 > 0 and c4 > 0:
                    mats.append((m4, c4))

                m5 = struct.unpack_from("<H", data, off + 25)[0]
                c5 = data[off + 27]
                if m5 > 0 and c5 > 0:
                    mats.append((m5, c5))

                b_time = struct.unpack_from("<H", data, off + 28)[0]

                if res_id > 0 and mats:
                    self.recipes.append(CompoundRecipe(
                        build_code=b_code,
                        result_item_id=res_id,
                        plan_id=p_id,
                        tool_id=tool_id,
                        materials=mats,
                        build_time=b_time
                    ))

            logger.info(f"[CompoundDatLoader] Loaded {len(self.recipes)} compounding recipes from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[CompoundDatLoader] Error reading {file_path}: {e}")
            return False


# =========================================================================
# 5. SceneData.dat Parser (SceneDataManager.cs)
# =========================================================================

class SceneDataLoader:
    """Parses 131-byte map metadata and scene names from SceneData.dat."""

    def __init__(self, file_path: Optional[str] = None):
        self.map_names: Dict[int, str] = {}
        if not file_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(base_dir, "data", "SceneData.dat")
            if os.path.exists(default_path):
                file_path = default_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            self.map_names.clear()
            rec_size = 131
            total = len(data) // rec_size

            for r in range(total):
                off = r * rec_size
                if off + 35 > len(data):
                    break

                length = data[off + 2]
                if length <= 0 or length > 50:
                    length = 30

                chars = bytearray()
                for i in range(length):
                    if off + 14 + i >= len(data):
                        break
                    b = data[off + 14 + i]
                    if 32 <= b <= 126:
                        chars.append(b)

                if chars:
                    chars.reverse()
                    raw = chars.decode("ascii", errors="ignore").strip()
                    bgm_idx = raw.find("%")
                    if bgm_idx != -1:
                        raw = raw[bgm_idx + 1:].strip(" %!#&'><\"")
                    if len(raw) >= 2:
                        self.map_names[r] = raw

            logger.info(f"[SceneDataLoader] Loaded {len(self.map_names)} scene names from {file_path}.")
            return True
        except Exception as e:
            logger.error(f"[SceneDataLoader] Error reading {file_path}: {e}")
            return False


# Global singletons
GLOBAL_ITEM_DAT = ItemDatLoader()
GLOBAL_NPC_DAT = NpcDatLoader()
GLOBAL_TALK_DAT = TalkDatLoader()
GLOBAL_COMPOUND_DAT = CompoundDatLoader()
GLOBAL_SCENE_DAT = SceneDataLoader()
