import asyncio
import logging
import sqlite3
import struct
import json
import traceback
import math
import sys
import random
import time
from server.quest_manager import QuestManager
from datetime import datetime

from server.network import PacketReader, PacketWriter, xor_crypt
from server.database import DatabaseManager
from server.battle import Fighter, BattleManager

# Setup logger
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WLO_Server")

# Version string for AC 0 Response
SERVER_VERSION = "Mamiletta"

def safe_int(val, default=0) -> int:
    """Safely cast a value to int, stripping null bytes and whitespace."""
    if val is None:
        return default
    if isinstance(val, int):
        return val
    try:
        s = str(val).strip().split('\x00')[0].strip()
        if not s:
            return default
        return int(s)
    except Exception:
        return default

def get_oa_date_float() -> float:
    """Calculates OADate (days since Dec 30, 1899) as a double, matching C# DateTime.Now.ToOADate()."""
    epoch = datetime(1899, 12, 30)
    delta = datetime.now() - epoch
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400.0

# Configuration payload from AC0.cs
SUBSERVER_CONFIG = bytes([
    37, 1, 145, 1, 2, 101, 0, 2, 102, 0, 2, 103, 0, 2, 106, 0, 2, 202, 0, 2, 201, 0, 2,
    204, 0, 2, 203, 0, 2, 45, 1, 2, 47, 1, 1, 105, 0, 2, 46, 1, 1, 146, 1, 1, 104, 0,
    2, 107, 0, 2, 148, 1, 1, 147, 1, 1, 245, 1, 2, 246, 1, 1, 247, 1, 1, 234, 3, 1,
    235, 3, 1, 78, 4, 1, 79, 4, 1, 35, 3, 1, 33, 3, 2, 34, 3, 1, 233, 3, 2, 133, 3,
    1, 135, 3, 1, 134, 3, 1, 77, 4, 2
])

def get_equip_slot(item_id: int) -> int:
    """Returns the equipment slot index (0-5) based on item ID range."""
    # Head (0): 22000-22999
    if 22000 <= item_id < 23000:
        return 0
    # Body (1): 21000-21999
    elif 21000 <= item_id < 22000:
        return 1
    # Arm (3): 23000-23999
    elif 23000 <= item_id < 24000:
        return 3
    # Feet (4): 24000-24999
    elif 24000 <= item_id < 25000:
        return 4
    # Hand/Weapon (5): 10000-10999, 18000-18999, etc.
    elif (10000 <= item_id < 11000) or (18000 <= item_id < 19000):
        return 5
    # Back/Special (2): Default/Fallback for capes, accessories, etc.
    else:
        return 2

def get_item_at_slot(session, slot: int):
    for item in session.inventory:
        if item.get('slot') == slot:
            return item
    return None

def remove_item_at_slot(session, slot: int, amount: int = 1):
    for item in session.inventory:
        if item.get('slot') == slot:
            if item.get('amount', 1) <= amount:
                session.inventory.remove(item)
            else:
                item['amount'] = item.get('amount', 1) - amount
            return True
    return False

def add_item_to_inventory(session, item_id: int, amount: int = 1, slot: int = None):
    if slot is None:
        used_slots = {item.get('slot') for item in session.inventory if item.get('slot') is not None}
        for s in range(1, 51):
            if s not in used_slots:
                slot = s
                break
    if slot is None or slot > 50:
        return None
    
    existing = get_item_at_slot(session, slot)
    if existing:
        if existing['item_id'] == item_id:
            existing['amount'] = existing.get('amount', 1) + amount
            return slot
        else:
            return None
            
    session.inventory.append({
        "item_id": item_id,
        "amount": amount,
        "damage": 0,
        "slot": slot
    })
    return slot

def get_body_stat_bonus(body: int, head: int, stat_name: str, level: int) -> int:
    bonus = 0
    if stat_name == "str":
        if body == 4 and head == 0:  # Big Female, Iris
            bonus = 1
        elif body == 4 and head == 1:  # Big Female, Lique
            bonus = 2
        elif body == 3 and head == 3:  # Big Male, Kurogane
            bonus = 1
        elif body == 3 and head == 0:  # Big Male, Daniel
            bonus = 1
        elif body == 3 and head == 1:  # Big Male, Sid
            bonus = 2
    elif stat_name == "con":
        if body == 4 and head == 0:  # Big Female, Iris
            bonus = 2
        elif body == 3 and head == 0:  # Big Male, Daniel
            bonus = 2
        elif body == 3 and head == 3:  # Big Male, Kurogane
            bonus = 1
        elif body == 3 and head == 1:  # Big Male, Sid
            bonus = 1
    elif stat_name == "int":
        if body == 4 and head == 2:  # Big Female, Vanessa
            bonus = 3
        elif body == 4 and head == 7:  # Big Female, Karin
            bonus = 1
        elif body == 4 and head == 4:  # Big Female, Jessica
            bonus = 1
        elif body == 3 and head == 3:  # Big Male, Kurogane
            bonus = 1
        elif body == 2 and head == 1:  # Small Female, Betty
            bonus = 1
        elif body == 2 and head == 0:  # Small Female, Nina
            bonus = 1
        elif body == 4 and head == 6:  # Big Female, Maria
            bonus = 2
        elif body == 1 and head == 0:  # Small Male, Rocco
            bonus = 2
        elif body == 4 and head == 5:  # Big Female, Konnotsuroko
            bonus = 2
    elif stat_name == "wis":
        if body == 4 and head == 7:  # Big Female, Karin
            bonus = 1
        elif body == 4 and head == 4:  # Big Female, Jessica
            bonus = 2
        elif body == 3 and head == 2:  # Big Male, More
            bonus = 2
        elif body == 2 and head == 0:  # Small Female, Nina
            bonus = 1
        elif body == 4 and head == 5:  # Big Female, Konnotsuroko
            bonus = 1
    elif stat_name == "agi":
        if body == 4 and head == 7:  # Big Female, Karin
            bonus = 1
        elif body == 4 and head == 1:  # Big Female, Lique
            bonus = 1
        elif body == 2 and head == 1:  # Small Female, Betty
            bonus = 2
        elif body == 2 and head == 0:  # Small Female, Nina
            bonus = 1
        elif body == 4 and head == 6:  # Big Female, Maria
            bonus = 1
        elif body == 1 and head == 0:  # Small Male, Rocco
            bonus = 1
        elif body == 3 and head == 2:  # Big Male, More
            bonus = 1
    return bonus  # Flat bonus, NOT multiplied by level

class PlayerSession:
    """Represents a connected player and their active state."""
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.peername = writer.get_extra_info('peername')
        self.ip = self.peername[0] if self.peername else "0.0.0.0"
        
        # User details
        self.user_id = 0
        self.username = ""
        self.cipher = ""
        
        # Character details
        self.char_id = 0
        self.char_name = ""
        self.level = 1
        self.element = 0
        self.hp = 100
        self.max_hp = 100
        self.sp = 100
        self.max_sp = 100
        self.gold = 0
        self.map_id = 10017  # Default ship map
        self.x = 1042
        self.y = 1075
        self.body = 1
        self.head = 1
        self.hair_color = 0
        self.skin_color = 0
        self.clothing_color = 0
        self.eye_color = 0
        self.reborn = False
        self.job = 0
        self.slot = 1
        self.equipments = [0] * 6  # 6 slots (head, body, back, arms, feet, hand)
        self.inventory = []  # List of items: {"item_id": id, "amount": amt, "damage": dmg}
        self.skills = []  # List of skills: {"skill_id": id, "grade": grade, "exp": exp}
        self.quests = []
        self.exp = 0
        self.potential = 0  # Character Potential (0-12)
        self.points = 0     # Distributable stat points (Attribute Points, Puan)
        self.pets = []  # List of pets: {"pet_id": id, "level": lvl, "exp": exp, ...}
        self.im_points = 5000
        self.im_bonus_points = 1000
        self.im_tokens = 50
        self.bank_gold = 0
        self.is_stall_active = False

        # Vehicle state
        self.riding_vehicle = False
        self.riding_vehicle_type = 0
        self.riding_vehicle_item_id = 0
        self.vehicle_fuel = 0
        self.vehicle_damage = 0
        
        # Stats details
        self._str_val = 10
        self._con_val = 10
        self._int_val = 10
        self._wis_val = 10
        self._agi_val = 10
        
        # Setting toggles
        self.pkable = True
        self.joinable = True
        self.tradable = True
        
        # Connection status
        self.logged_in = False
        self.is_warping = False
        self.in_map = False
        self.pending_battle_unlock = False
        
        # Quest state tracking
        self.active_quest_id = None
        self.active_quest_step = 0
        self.active_quest_dialog_counter = 1  # WLO dialog step counter (byte[3] in AC 20 Sub 1)
        
        # Bathing state
        self.bathing = False
        self.bath_task = None
        
        # Send lock to avoid parallel write corruption
        self.send_lock = asyncio.Lock()


    def get_stat_bonus(self, stat_name: str) -> int:
        add = get_body_stat_bonus(self.body, self.head, stat_name, self.level)
        return add  # Flat bonus, NOT multiplied by level - stats are manually allocated

    @property
    def str_val(self) -> int:
        return self._str_val + self.get_stat_bonus("str")

    @str_val.setter
    def str_val(self, val: int):
        self._str_val = val

    @property
    def con_val(self) -> int:
        return self._con_val + self.get_stat_bonus("con")

    @con_val.setter
    def con_val(self, val: int):
        self._con_val = val

    @property
    def int_val(self) -> int:
        return self._int_val + self.get_stat_bonus("int")

    @int_val.setter
    def int_val(self, val: int):
        self._int_val = val

    @property
    def wis_val(self) -> int:
        return self._wis_val + self.get_stat_bonus("wis")

    @wis_val.setter
    def wis_val(self, val: int):
        self._wis_val = val

    @property
    def agi_val(self) -> int:
        return self._agi_val + self.get_stat_bonus("agi")

    @agi_val.setter
    def agi_val(self, val: int):
        self._agi_val = val

    def update_max_hp_sp(self):
        """Calculates and updates max HP/SP dynamically using WLO formulas."""
        con = self.con_val
        wis = self.wis_val
        lvl = self.level
        
        self.max_hp = int(round(((lvl ** 0.35) * con * 2) + (lvl * 1) + (con * 2) + 180))
        self.max_sp = int(round(((lvl ** 0.3) * wis * 3.2) + (lvl * 1) + (wis * 2) + 94))
        
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        if self.sp > self.max_sp:
            self.sp = self.max_sp

    async def send_packet(self, packet_writer: PacketWriter):
        """Builds and sends an encrypted packet to the client."""
        payload_bytes = bytes(packet_writer.buffer)
        action_code = payload_bytes[0] if len(payload_bytes) > 0 else 0
        sub_code = payload_bytes[1] if len(payload_bytes) > 1 else 0
        logger.info(f"[{self.char_name or self.username or self.ip}] -> SEND AC: {action_code}, Sub: {sub_code}, Len: {len(payload_bytes)}, Hex: {payload_bytes.hex()}")
        
        data = packet_writer.build()
        async with self.send_lock:
            try:
                self.writer.write(data)
                await self.writer.drain()
            except Exception as e:
                logger.error(f"[{self.username}] Send failed: {e}")

    async def send_multi_packets(self, packets: list['PacketWriter']):
        """
        Sends multiple packets as a single combined stream (used for battle init and stats).
        WLO expects multi-packets to be a single 0x44F4 header followed by all the raw payloads concatenated.
        """
        if not packets:
            return
            
        combined_payload = bytearray()
        for pkt in packets:
            combined_payload.extend(pkt.buffer)
            
        # Now wrap combined_payload in a single PacketWriter
        multi_pkt = PacketWriter()
        multi_pkt.buffer = combined_payload
        
        await self.send_packet(multi_pkt)

    async def send_raw_packet(self, data: bytes):
        """Sends a pre-built encrypted packet directly to the client."""
        decrypted_payload = xor_crypt(data[4:])
        action_code = decrypted_payload[0] if len(decrypted_payload) > 0 else 0
        sub_code = decrypted_payload[1] if len(decrypted_payload) > 1 else 0
        logger.info(f"[{self.char_name or self.username or self.ip}] -> SEND AC: {action_code}, Sub: {sub_code}, Len: {len(data)}, Hex: {data.hex()}")
        
        async with self.send_lock:
            try:
                self.writer.write(data)
                await self.writer.drain()
            except Exception as e:
                logger.error(f"[{self.username}] Send raw failed: {e}")

    async def disconnect(self):
        """Disconnects the socket cleanly."""
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except:
            pass

class GameServer:
    """Unified WLO Private Server on Port 6414."""

    @property
    def sessions(self) -> dict:
        """Exposes active sessions as a dict for compatibility with handlers/web admin."""
        return {getattr(s, 'char_id', id(s)): s for s in self.active_sessions}
    
    def __init__(self, db_path: str = "wlo_server.db", static_db_path: str = "server/ServerDataBase.db"):
        self.db_path = db_path
        self.db = DatabaseManager(db_path)
        self.static_db_path = static_db_path
        self.quest_manager = QuestManager(static_db_path)
        self.active_sessions = set()
        self.map_players = {}  # map_id (int) -> set(PlayerSession)
        self.map_ground_items = {}  # map_id (int) -> list of 256 elements (None or dict)
        self.active_battles = {}  # battle_id -> BattleInstance
        self.exp_multiplier = 1.0
        self.gold_multiplier = 1.0
        self.encounter_multiplier = 1.0
        
        # Load Quest Scripts
        self.quest_scripts = {}
        try:
            with open("server/data/quests.json", "r", encoding="utf-8") as f:
                self.quest_scripts = json.load(f)
                # Convert string keys to int for easy lookup by native_click_id
                self.quest_scripts = {int(k): v for k, v in self.quest_scripts.items()}
        except Exception as e:
            logger.warning(f"Failed to load quests.json: {e}")
            
        # Load Drop Table Config
        self.drop_tables = {}
        try:
            with open("server/data/drop_table.json", "r", encoding="utf-8") as f:
                self.drop_tables = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load drop_table.json: {e}")
        
        # Load NPCs and Warp Portals from eve.Emg
        self.map_npcs = {}
        self.map_portals_count = {}
        self.map_portals = {}
        self.item_properties = {}
        self.items = {}
        self._load_all_npcs()
        self._load_compound_dat()
        self._load_formula_dat()
        self._load_item_mix()
        self._load_item_properties()
        self._load_skill_dat()
        
        # Initialize Master Quest Engine and PreEvents Interpreter
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
        eve_path = os.path.join(base_dir, "data", "eve.Emg")
        from server.quests import GLOBAL_QUEST_ENGINE
        from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
        from server.chest_system import ChestSystem
        GLOBAL_QUEST_ENGINE.initialize(base_dir)
        GLOBAL_PREEVENT_INTERPRETER.load_preevents(eve_path)
        self.chest_system = ChestSystem(self.db_path)

        self.SERVER_VERSION = self.db.get_config("server_name", SERVER_VERSION)
        self.SUBSERVER_CONFIG = SUBSERVER_CONFIG

        from server.version_validator import ClientVersionValidator
        self.version_validator = ClientVersionValidator(self.db)

        self._load_handlers()

    def get_server_name(self) -> str:
        """Returns current server branding / name."""
        return self.SERVER_VERSION

    def set_server_name(self, name: str):
        """Sets server branding / name and persists to database."""
        name = name.strip() if name else "Mamiletta"
        self.SERVER_VERSION = name
        self.db.set_config("server_name", name)
        logger.info(f"[Server] Server Name / Branding updated to: '{name}'")

    def get_motd(self) -> str:
        """Returns current MOTD / welcome message from DB or default."""
        return self.db.get_config("welcome_message", "Welcome to the Wonderland Online Private Server! Enjoy your adventure!")

    def set_motd(self, msg: str):
        """Sets MOTD / welcome message and persists to DB."""
        msg = msg.strip() if msg else "Welcome to the Wonderland Online Private Server! Enjoy your adventure!"
        self.db.set_config("welcome_message", msg)
        logger.info(f"[Server] MOTD / Welcome message updated to: '{msg}'")

    async def dispatch_login_motd(self, session: 'PlayerSession'):
        """Dispatches login MOTD (Message of the Day) matching C# WorldServer.DispatchLoginMotd."""
        try:
            if not session:
                return
            motd_raw = self.get_motd()
            lines = [l.strip() for l in (motd_raw or "").replace("\r\n", "\n").split("\n") if l.strip()]
            if not lines:
                lines = ["Welcome to the Wonderland Online Private Server! Enjoy your adventure!"]

            # 1. Send Popup Notice for the first line (AC 23 Sub 57)
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(lines[0]))

            # 2. Send System / GM chat message (type 4 = Red/Orange GM text) for each line (AC 2)
            for line in lines:
                chat_pkt = PacketWriter().write_8(2).write_8(4).write_32(0).write_string_n(line)
                await session.send_packet(chat_pkt)

            logger.info(f"[{getattr(session, 'char_name', 'Player')}] Dispatched {len(lines)} MOTD line(s)")
        except Exception as e:
            logger.error(f"[Server] Error dispatching MOTD: {e}")

    def _load_skill_dat(self):
        """Loads actual skill multipliers from data/Skill.dat using server/skills.json mapping."""
        self.parsed_skills = {}
        try:
            import os, struct, json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
            skill_dat_path = os.path.join(base_dir, "data", "Skill.dat")
            skills_json_path = os.path.join(base_dir, "server", "skills.json")
            
            if os.path.exists(skill_dat_path) and os.path.exists(skills_json_path):
                with open(skills_json_path, 'r', encoding='utf-8') as f:
                    skills_list = json.load(f)
                with open(skill_dat_path, 'rb') as f:
                    dat = f.read()
                
                for i, s in enumerate(skills_list):
                    offset = i * 148
                    if offset + 148 <= len(dat):
                        rec = dat[offset:offset+148]
                        multiplier = struct.unpack('<f', rec[36:40])[0]
                        if not (0.1 < multiplier < 10.0):
                            multiplier = 1.0  # Fallback
                        
                        is_magical = s.get('element', 0) > 0  # Simplification
                        is_heal = "Heal" in s.get('name', '') or "Cure" in s.get('name', '') or "Recovery" in s.get('name', '') or "Shield" in s.get('name', '')
                        
                        self.parsed_skills[s['id']] = (s.get('name', 'Unknown'), s.get('element', 0), is_magical, multiplier, is_heal, s.get('sp', 10))
                logger.info(f"Loaded {len(self.parsed_skills)} skills from Skill.dat")
            else:
                logger.warning("Skill.dat or skills.json not found!")
        except Exception as e:
            logger.error(f"Error loading Skill.dat: {e}")

    def _load_all_npcs(self):
        """Loads all NPCs and their walksteps from data/eve.Emg."""
        import os
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
        eve_path = os.path.join(base_dir, "data", "eve.Emg")
        
        if not os.path.exists(eve_path):
            logger.error(f"[NPC] eve.Emg not found at {eve_path}")
            return
            
        try:
            with open(eve_path, "rb") as f:
                d = f.read()
                
            entrylen = struct.unpack_from("<I", d, 8)[0]
            ptr = 12
            maps = {}
            for i in range(entrylen):
                mapID, sceneID, dataptr, datalen = struct.unpack_from("<HHIH", d, ptr)
                ptr += 10
                maps[mapID] = {
                    'dataptr': dataptr,
                    'datalen': datalen
                }
                
            npc_count = 0
            for mapID, m in maps.items():
                off_ptr = m['dataptr'] + m['datalen'] - 44
                if off_ptr + 44 > len(d):
                    continue
                    
                offsets = struct.unpack_from("<IIIIIIIIIII", d, off_ptr)
                
                # Count portals (warp entries) for this map from eve.Emg
                warp_offset = offsets[6]
                warp_ptr = m['dataptr'] + warp_offset
                if warp_ptr + 2 <= len(d):
                    warp_count = struct.unpack_from("<H", d, warp_ptr)[0]
                    self.map_portals_count[mapID] = warp_count
                    
                    cur_warp_ptr = warp_ptr + 2
                    portals_list = []
                    for _ in range(warp_count):
                        if cur_warp_ptr + 35 > len(d):
                            break
                        w_click_id = struct.unpack_from("<H", d, cur_warp_ptr)[0]
                        w_name_bytes = d[cur_warp_ptr+2 : cur_warp_ptr+22]
                        w_name = w_name_bytes.decode('cp950', errors='ignore').strip('\x00').strip()
                        w_dst_map_raw = struct.unpack_from("<H", d, cur_warp_ptr+22)[0]
                        w_dst_x = struct.unpack_from("<I", d, cur_warp_ptr+24)[0]
                        w_dst_y = struct.unpack_from("<I", d, cur_warp_ptr+28)[0]
                        
                        w_dst_map = w_dst_map_raw
                        
                        portals_list.append({
                            'click_id': w_click_id,
                            'name': w_name,
                            'dst_map': w_dst_map,
                            'dst_x': w_dst_x,
                            'dst_y': w_dst_y
                        })
                        cur_warp_ptr += 35
                    self.map_portals[mapID] = portals_list
                else:
                    self.map_portals_count[mapID] = 0
                    self.map_portals[mapID] = []

            # Load authentic NPCs with strict C# spawn filtering and QuestNpc definitions
            from server.npc_manager import GLOBAL_NPC_MANAGER
            total_loaded = GLOBAL_NPC_MANAGER.load_npcs_from_eve(eve_path)
            self.map_npcs = GLOBAL_NPC_MANAGER.map_npcs
            self.npc_manager = GLOBAL_NPC_MANAGER
            
            # Load Eve Event trees
            from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
            GLOBAL_EVE_INTERPRETER.load(eve_path)
        except Exception as e:
            logger.error(f"[NPC] Error loading NPCs from eve.Emg: {e}", exc_info=True)

    @staticmethod
    def is_village_or_town_map(map_id: int) -> bool:
        """Returns True if the map is a village, town, interior or residential zone."""
        if map_id in (10000, 10010, 60001):
            return True
        if 10001 <= map_id <= 10036:  # Starter Ship, Cabins, Beach, Kelan Village
            return True
        if 12000 <= map_id <= 12030:  # Welling Village
            return True
        if 14000 <= map_id <= 14030:  # Holy Village
            return True
        if 16000 <= map_id <= 16030:  # Kyoto
            return True
        if 18000 <= map_id <= 18030:  # Chang'an
            return True
        return False

    @staticmethod
    def is_static_or_prop_npc(npc: dict, map_id: int) -> bool:
        """Determines whether an NPC entity is a static prop, chest, node, or unmoving entity."""
        tid = npc.get("npc_id", 0)
        click_id = npc.get("click_id", 0)
        name = (npc.get("name") or "").lower().strip()

        if click_id == 0 or tid == 0:
            return True
        if npc.get("x", 0) > 4000 or npc.get("y", 0) > 4000 or (npc.get("x", 0) == 0 and npc.get("y", 0) == 0):
            return True

        # Prop / chest / gathering node / furniture template ID ranges
        if (12000 <= tid <= 12999) or (16000 <= tid <= 16999) or (19000 <= tid <= 35000):
            return True

        # Domestic farm animals in pens
        if tid == 17400:
            return True

        # Name indicators for props / chests / doors / service spots
        prop_keywords = (
            "chest", "crate", "box", "door", "tree", "ore", "mine", "wood", "flower",
            "grass", "statue", "signpost", "guidepost", "hotel", "inn", "storage",
            "bank", "clinic", "shop", "exchanger", "pot", "barrel", "urn", "rock"
        )
        if any(k in name for k in prop_keywords):
            return True

        # Click IDs 6, 7 on starter ship/beach maps
        if map_id in (10017, 10035) and click_id in (6, 7):
            return True

        return False

    async def npc_walk_loop(self):
        """
        Background loop for NPC AI, scripted waypoint movement, and wild roaming.
        Ported 1:1 from C# Map.cs lines 320-330 and QuestNpc.cs.
        """
        logger.info("[NPC] Authentic NPC background AI & waypoint manager active.")
        while True:
            try:
                await asyncio.sleep(1.0)
                now = time.time()
                active_maps = set(self.map_players.keys())
                if active_maps and hasattr(self, 'npc_manager'):
                    self.npc_manager.update(
                        now=now,
                        active_map_ids=active_maps,
                        map_players=self.map_players,
                        broadcast_fn=self.broadcast_to_map
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[NPC] Error in NPC loop: {e}", exc_info=True)

    async def run(self, host: str = "0.0.0.0", port: int = 6414):
        """Starts the asynchronous TCP server."""
        self.loop = asyncio.get_running_loop()
        server = await asyncio.start_server(self.handle_connection, host, port)
        logger.info(f"WLO Private Server successfully started on {host}:{port}")
        
        # Auto-save task
        asyncio.create_task(self.auto_save_loop())

        # NPC walk task
        asyncio.create_task(self.npc_walk_loop())
        
        async with server:
            await server.serve_forever()


    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles a new client socket connection."""
        session = PlayerSession(reader, writer)
        if hasattr(self, 'db') and self.db.is_ip_banned(session.ip):
            logger.warning(f"[Server] Rejected connection from banned IP: {session.ip}")
            try:
                fail_pkt = PacketWriter()
                fail_pkt.write_8(63).write_8(4)
                await session.send_packet(fail_pkt)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Your IP address has been banned from this server."))
                await session.send_packet(PacketWriter().write_8(1).write_8(6))
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            return

        self.active_sessions.add(session)
        logger.info(f"[Server] New connection from {session.ip}")

        try:
            await self.read_packets_loop(session)
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            logger.error(f"[Server] Connection error: {e}\n{traceback.format_exc()}")
        finally:
            self.active_sessions.remove(session)
            await self.handle_disconnect(session)

    async def kick_user(self, user_id: int, reason: str = "Disconnected by administrator"):
        """Kicks any active session associated with user_id."""
        for s in list(self.active_sessions):
            if getattr(s, 'user_id', None) == user_id:
                try:
                    await s.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(reason))
                    await s.send_packet(PacketWriter().write_8(1).write_8(6))
                    s.writer.close()
                except Exception:
                    pass

    async def kick_ip(self, ip: str, reason: str = "Your IP address has been banned"):
        """Kicks all active sessions matching the given IP address."""
        clean_ip = str(ip).strip()
        for s in list(self.active_sessions):
            if getattr(s, 'ip', None) == clean_ip:
                try:
                    await s.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(reason))
                    await s.send_packet(PacketWriter().write_8(1).write_8(6))
                    s.writer.close()
                except Exception:
                    pass

    async def ban_user(self, user_id: int, reason: str = "Banned by administrator"):
        """Bans user in DB and kicks immediately if online."""
        self.db.ban_user(user_id, reason=reason, banned=1)
        await self.kick_user(user_id, f"Account banned: {reason}")
        logger.info(f"[Server] Banned user ID {user_id} (Reason: {reason})")

    async def unban_user(self, user_id: int):
        """Unbans user in DB."""
        self.db.ban_user(user_id, reason="", banned=0)
        logger.info(f"[Server] Unbanned user ID {user_id}")

    async def ban_ip(self, ip: str, reason: str = "Banned by administrator", banned_by: str = "admin"):
        """Bans IP in DB and kicks all active connections from this IP."""
        self.db.ban_ip(ip, reason=reason, banned_by=banned_by)
        await self.kick_ip(ip, f"IP Banned: {reason}")
        logger.info(f"[Server] Banned IP {ip} (Reason: {reason})")

    async def unban_ip(self, ip: str):
        """Unbans IP in DB."""
        self.db.unban_ip(ip)
        logger.info(f"[Server] Unbanned IP {ip}")

    async def read_packets_loop(self, session: PlayerSession):
        """Reads and frames TCP bytes into distinct packets."""
        while True:
            # Framing header: 4 bytes (2 bytes signature 0xF4, 0x44, 2 bytes payload length)
            header = await session.reader.readexactly(4)
            if not header:
                break
                
            # Decrypt header
            decrypted_header = xor_crypt(header)
            signature, payload_len = struct.unpack('<HH', decrypted_header)
            
            if signature != 17652:  # 0x44F4
                logger.error(f"[{session.ip}] Invalid signature: {signature:04X}. Disconnecting.")
                break
                
            # Read payload
            payload = await session.reader.readexactly(payload_len)
            decrypted_payload = xor_crypt(payload)
            
            action_code = decrypted_payload[0] if len(decrypted_payload) > 0 else 0
            sub_code = decrypted_payload[1] if len(decrypted_payload) > 1 else 0
            logger.info(f"[{session.char_name or session.username or session.ip}] <- RECV AC: {action_code}, Sub: {sub_code}, Len: {len(decrypted_payload)}, Hex: {decrypted_payload.hex()}")
            
            # Dispatch
            reader = PacketReader(decrypted_payload)
            action_code = reader.read_8()
            await self.dispatch_packet(session, action_code, reader)

    async def handle_disconnect(self, session: PlayerSession):
        """Cleans up player session on disconnection."""
        logger.info(f"[{session.username or session.ip}] Client disconnected.")
        if session.logged_in and session.char_id:
            # Save character
            self.save_player_to_db(session)
            # Remove from map
            self.remove_player_from_map(session)
            # Broadcast exit to map
            bye = PacketWriter().write_8(1).write_8(1).write_32(session.char_id)
            self.broadcast_to_map(session.map_id, bye, exclude_session=session)
        await session.disconnect()

    def remove_player_from_map(self, session: PlayerSession):
        """Removes session from map tracking."""
        if session.map_id in self.map_players:
            if session in self.map_players[session.map_id]:
                self.map_players[session.map_id].remove(session)

    def add_player_to_map(self, session: PlayerSession, map_id: int):
        """Adds session to map tracking."""
        if map_id not in self.map_players:
            self.map_players[map_id] = set()
        self.map_players[map_id].add(session)

    def update_character_skills(self, session: PlayerSession):
        """Automatically unlocks all matching element skills for the player's element."""
        if not session.char_id:
            return
        
        # Load skills from skills.json if not already loaded
        if not hasattr(self, 'all_skills_db'):
            self.all_skills_db = []
            try:
                import json
                import os
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
                skills_path = os.path.join(base_dir, "server", "skills.json")
                if os.path.exists(skills_path):
                    with open(skills_path, "r", encoding="utf-8") as f:
                        self.all_skills_db = json.load(f)
            except Exception as e:
                logger.error(f"[SKILL] Failed to load skills.json: {e}")
                
        if not self.all_skills_db:
            return
            
        existing_ids = {sk['skill_id'] for sk in session.skills}
        new_skills_added = False
        
        # Determine player's starting special skill ID
        stunt_id = self.get_starter_skill_id(session.body, session.head)
        if stunt_id not in existing_ids:
            session.skills.append({"skill_id": stunt_id, "grade": 1, "exp": 0})
            existing_ids.add(stunt_id)
            new_skills_added = True
            
        # Commented out: Stop automatically unlocking all skills of the element
        # for sk in self.all_skills_db:
        #     sk_id = sk['id']
        #     # Only add if it belongs to player's element and is not already learned
        #     # Earth=1, Water=2, Fire=3, Wind=4
        #     if sk['element'] == session.element and sk_id not in existing_ids:
        #         session.skills.append({"skill_id": sk_id, "grade": 1, "exp": 0})
        #         existing_ids.add(sk_id)
        #         new_skills_added = True
                
        if new_skills_added:
            self.save_player_to_db(session)
            logger.info(f"[SKILL] Added starter skills to {session.char_name} (element={session.element})")

    def save_player_to_db(self, session: PlayerSession):
        """Saves session state to database."""
        if not session.char_id:
            return
        data = {
            'level': session.level,
            'element': session.element,
            'hp': session.hp,
            'max_hp': session.max_hp,
            'sp': session.sp,
            'max_sp': session.max_sp,
            'gold': session.gold,
            'map_id': session.map_id,
            'x': session.x,
            'y': session.y,
            'body': session.body,
            'head': session.head,
            'hair_color': session.hair_color,
            'skin_color': session.skin_color,
            'clothing_color': session.clothing_color,
            'eye_color': session.eye_color,
            'reborn': session.reborn,
            'job': session.job,
            'equipments': [{'item_id': id} for id in session.equipments],
            'inventory': session.inventory,
            'skills': session.skills,
            'quests': session.quests,
            'str': session._str_val,
            'con': session._con_val,
            'int': session._int_val,
            'wis': session._wis_val,
            'agi': session._agi_val,
            'exp': session.exp,
            'pets': session.pets,
            'potential': session.potential,
            'points': session.points,
            'skill_points': getattr(session, 'skill_points', 0),
            'chat_channels_mask': getattr(session, 'chat_channels_mask', 31),
            'im_points': getattr(session, 'im_points', 5000),
            'im_bonus_points': getattr(session, 'im_bonus_points', 1000),
            'im_tokens': getattr(session, 'im_tokens', 50),
            'bank_gold': getattr(session, 'bank_gold', 0),
        }
        self.db.save_character(session.char_id, data)
        try:
            from server.tent import GLOBAL_TENT_MANAGER
            tent = GLOBAL_TENT_MANAGER.get_or_create_tent(session.char_id)
            if tent and tent.is_dirty:
                GLOBAL_TENT_MANAGER.save_tent_to_db(tent)
        except Exception:
            pass

    async def give_exp(self, session: PlayerSession, amount: int):
        """Gives EXP to player, handles level-ups and grants 3 potential points per level gained."""
        if amount <= 0:
            return
        
        old_level = session.level
        session.exp += int(amount * self.exp_multiplier)
        new_level = self.get_level_from_exp(session.exp, session.reborn)
        
        leveled_up = new_level != old_level
        if leveled_up:
            levels_gained = new_level - old_level
            session.level = new_level
            # Give 3 stat points (POINT) per level gained
            session.points = min(255, session.points + levels_gained * 3)
            # Give 1 skill point per level gained
            session.skill_points = min(255, getattr(session, 'skill_points', 0) + levels_gained)
            # Recalculate HP/SP for new level
            session.update_max_hp_sp()
            session.hp = session.max_hp
            session.sp = session.max_sp
            logger.info(f"[{session.char_name}] Level up! {old_level} -> {new_level}, +{levels_gained*3} stat points")
        
        # Save to DB after exp change
        self.save_player_to_db(session)
        
        # Send EXP update (AC 8:1, stat 36)
        p_exp = PacketWriter()
        p_exp.write_8(8).write_8(1).write_8(36).write_8(1).write_64(session.exp)
        await session.send_packet(p_exp)

        if leveled_up:
            # Send Level update (AC 8:1, stat 35)
            p_lvl = PacketWriter()
            p_lvl.write_8(8).write_8(1).write_8(35).write_8(1).write_32(session.level).write_32(0)
            await session.send_packet(p_lvl)
        
        # Send stats update to client
        await self.send_stats_update(session, levelup=leveled_up)
        
        if leveled_up:
            # Unlock any new skills earned with this level, then resend skill list
            self.update_character_skills(session)
            await self.resend_skill_list(session)

    async def resend_skill_list(self, session: 'PlayerSession'):
        """Re-sends all skill slot packets to the client (AC 5:13). Used after login and level-up."""
        for idx, sk in enumerate(session.skills):
            slot = idx + 1
            skill_pkt = PacketWriter()
            skill_pkt.write_8(5).write_8(13)
            skill_pkt.write_8(slot)
            skill_pkt.write_16(sk.get('skill_id', 0))
            await session.send_packet(skill_pkt)
        # Send skill finalize packet
        await session.send_packet(PacketWriter().write_8(5).write_8(4))

    async def auto_save_loop(self):
        """Periodically saves all active character data."""
        while True:
            await asyncio.sleep(60)
            for session in list(self.active_sessions):
                if session.logged_in and session.char_id:
                    try:
                        self.save_player_to_db(session)
                    except Exception as e:
                        logger.error(f"[AutoSave] Error saving player {session.char_name}: {e}")

    def broadcast_to_map(self, map_id: int, packet_writer: PacketWriter, exclude_session: PlayerSession = None):
        """Sends a packet to all players on a map."""
        if map_id not in self.map_players:
            return
        data = packet_writer.build()
        for session in list(self.map_players[map_id]):
            if exclude_session and session == exclude_session:
                continue
            asyncio.create_task(session.send_raw_packet(data))

    def _load_handlers(self):
        """Dynamically scans and registers all packet handlers from server/handlers directory."""
        self.handlers = {}
        import importlib
        import os
        import pkgutil
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        handlers_dir = os.path.join(base_dir, "handlers")
        if not os.path.exists(handlers_dir):
            logger.warning(f"Handlers directory not found at {handlers_dir}")
            return
            
        import server.handlers
        
        for _, module_name, _ in pkgutil.iter_modules(server.handlers.__path__):
            try:
                module = importlib.import_module(f"server.handlers.{module_name}")
                
                codes = []
                if hasattr(module, "ACTION_CODES"):
                    codes = module.ACTION_CODES
                elif hasattr(module, "ACTION_CODE"):
                    codes = [module.ACTION_CODE]
                
                for code in codes:
                    self.handlers[code] = module.handle
                    
                logger.info(f"Loaded packet handler: {module_name} for action codes {codes}")
            except Exception as e:
                logger.error(f"Failed to load packet handler module {module_name}: {e}", exc_info=True)

    async def dispatch_packet(self, session: PlayerSession, action_code: int, reader: PacketReader):
        """Dispatches decrypted Action Codes to corresponding handlers."""
        sub_code = reader.data[1] if len(reader.data) > 1 else 0
        logger.debug(f"[{session.username or session.ip}] Action Code: {action_code}, Sub: {sub_code}, Payload size: {len(reader.data)}, Hex: {reader.data.hex()}")

        handler = self.handlers.get(action_code)
        if handler:
            try:
                await handler(self, session, reader)
            except Exception as e:
                logger.error(f"Error executing handler for Action Code {action_code}: {e}\n{traceback.format_exc()}")
        else:
            logger.info(f"Unhandled Action Code: {action_code}, payload: {reader.data.hex()}")

    async def send_friend_list(self, session: PlayerSession):
        """Sends the character's complete friend list (AC 14 Sub 5) to the client."""
        try:
            friend_ids = []
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    "SELECT CharID1, CharID2 FROM friends WHERE CharID1 = ? OR CharID2 = ?",
                    (session.char_id, session.char_id)
                ).fetchall()
                for r in rows:
                    if r['CharID1'] == session.char_id:
                        friend_ids.append(r['CharID2'])
                    else:
                        friend_ids.append(r['CharID1'])
            
            s = PacketWriter()
            s.write_8(14).write_8(5)
            
            for friend_id in friend_ids:
                friend_char = self.db.get_character_by_id(friend_id)
                if friend_char:
                    # Check online status
                    is_online = any(act.char_id == friend_id for act in self.active_sessions)
                    s.write_32(friend_char['id'])
                    s.write_string(friend_char['name'] or "")
                    s.write_8(friend_char['level'])
                    s.write_8(1 if friend_char.get('reborn') else 0)
                    s.write_8(friend_char['job'])
                    s.write_8(friend_char['element'])
                    s.write_8(friend_char['body'])
                    s.write_8(friend_char['head'])
                    s.write_16(friend_char['hair_color'])
                    s.write_16(friend_char['skin_color'])
                    s.write_16(friend_char['clothing_color'])
                    s.write_16(friend_char['eye_color'])
                    s.write_string("")  # Nickname
                    s.write_8(1 if is_online else 0)
            
            await session.send_packet(s)
            logger.info(f"[AC14] Sent friend list ({len(friend_ids)} friends) to {session.char_name}")
        except Exception as e:
            logger.error(f"[AC14] Error sending friend list: {e}", exc_info=True)

    def get_starter_skill_id(self, body: int, head: int) -> int:
        if body == 4:  # Big Female
            if head == 0: return 15041  # Iris: Love Wish
            elif head == 1: return 12053  # Lique: Gallop
            elif head == 2: return 15003  # Vanessa: Newbie's Stunt
            elif head == 3: return 15060  # Breillat: Throw Dish
            elif head == 4: return 12051  # Jessica: Note
            elif head == 5: return 12049  # Konno Tsuruko: Fire Dance
            elif head == 6: return 11077  # Maria: Cure 2 Players
            elif head == 7: return 15040  # Karin: Palm
        elif body == 3:  # Big Male
            if head == 0: return 15038  # Daniel: Overarm Stumble
            elif head == 1: return 11076  # Sid: Combo x3 Attack
            elif head == 2: return 11183  # More: Deacon Attack
            elif head == 3: return 11182  # Kurogane: Ghost Hammer
        elif body == 2:  # Small Female
            if head == 0: return 15039  # Nina: Wine Flame
            elif head == 1: return 12036  # Betty: Leap
        elif body == 1:  # Small Male
            if head == 0: return 11075  # Rocco: Summon Dogs Groups
        return 15003  # Default fallback: Newbie's Stunt

    # Skill table order -> offset in SkillData.MBTM (offset // 10)
    _SKILL_TABLE_ORDER = {
        11075: 93497,   # Rocco: Summon Dogs Groups
        11076: 93498,   # Sid: Combo x3 Attack
        11077: 93499,   # Maria: Cure 2 Players
        11182: 93543,   # Kurogane: Ghost Hammer
        11183: 93544,   # More: Deacon Attack
        12036: 93572,   # Betty: Leap
        12049: 93581,   # Konno Tsuruko: Fire Dance
        12051: 93582,   # Jessica: Note
        12053: 93583,   # Lique: Gallop
        15003: 93587,   # Newbie's Stunt (fallback / Vanessa)
        15038: 93622,   # Daniel: Overarm Stumble
        15039: 93623,   # Nina: Wine Flame
        15040: 93624,   # Karin: Palm
        15041: 93625,   # Iris: Love Wish
        15060: 93641,   # Breillat: Throw Dish
    }

    def get_skill_table_order(self, skill_id: int) -> int:
        # Table orders are byte offsets / 10 from SkillData.MBTM
        return self._SKILL_TABLE_ORDER.get(skill_id, 93587) & 0xFFFF  # fallback: Newbie's Stunt

    # Skill grade leveling: EXP needed to advance to next grade
    # Grade 1->2: 100 exp, Grade 2->3: 300, 3->4: 600, etc.
    # Max grade is 20
    def get_skill_exp_for_grade(self, grade: int) -> int:
        """Returns the total EXP needed to reach the given grade."""
        if grade <= 1:
            return 0
        # Cumulative: 100 * (1 + 2 + ... + (grade-1)) = 100 * grade * (grade-1) / 2
        return int(100 * grade * (grade - 1) / 2)

    async def give_skill_exp(self, session: PlayerSession, skill_id: int, amount: int):
        """Adds skill EXP and handles skill grade level-ups, sending updates to client."""
        if skill_id <= 0 or amount <= 0:
            return 0
        
        for idx, sk in enumerate(session.skills):
            if sk['skill_id'] == skill_id:
                old_grade = sk.get('grade', 1)
                old_exp = sk.get('exp', 0)
                sk['exp'] = old_exp + amount
                
                # Determine new grade based on total exp
                new_grade = old_grade
                while new_grade < 20:
                    needed = self.get_skill_exp_for_grade(new_grade + 1)
                    if sk['exp'] >= needed:
                        new_grade += 1
                    else:
                        break
                
                if new_grade > old_grade:
                    sk['grade'] = new_grade
                    logger.info(f"[Skill] {session.char_name}'s skill {skill_id} leveled up: grade {old_grade} -> {new_grade} (exp: {sk['exp']})")
                
                # Send update packet (AC 5 Sub 13) to client
                slot = idx + 1
                # AC 8:1 stat 110 = Skill Grade Update
                pkt = PacketWriter()
                pkt.write_8(8).write_8(1)
                pkt.write_8(110).write_8(1)
                pkt.write_32(new_grade)
                pkt.write_32(skill_id)
                await session.send_packet(pkt)
                
                self.save_player_to_db(session)
                return new_grade - old_grade
        return 0

    def load_character_into_session(self, session: PlayerSession, char_id: int):
        """Loads database character stats into PlayerSession."""
        char = self.db.get_character_by_id(char_id)
        session.char_id = char['id']
        session.slot = char['slot']
        session.char_name = char['name']
        session.element = char['element']
        session.hp = char['hp']
        session.sp = char['sp']
        session.gold = char['gold']
        session.map_id = char['map_id']
        session.x = char['x']
        session.y = char['y']
        session.body = char['body']
        session.head = char['head']
        session.hair_color = char['hair_color']
        session.skin_color = char['skin_color']
        session.clothing_color = char['clothing_color']
        session.eye_color = char['eye_color']
        session.reborn = bool(char['reborn'])
        session.job = char['job']
        session.equipments = [eq['item_id'] for eq in char['equipments']]
        while len(session.equipments) < 6:
            session.equipments.append(0)
        session.inventory = char['inventory']
        session.skills = char.get('skills', [])
        session.quests = char.get('quests', [])
        session.exp = char.get('exp', 0)
        session.points = char.get('points', 0)
        session.potential = char.get('potential', 0)
        session.pets = char.get('pets', [])
        session.chat_channels_mask = char.get('chat_channels_mask', 31)
        session.im_points = char.get('im_points', 5000)
        session.im_bonus_points = char.get('im_bonus_points', 1000)
        session.im_tokens = char.get('im_tokens', 50)
        session.bank_gold = char.get('bank_gold', 0)
        
        # Migration: if points is 0 but potential > 0, migrate potential to points
        if session.points == 0 and session.potential > 0:
            session.points = session.potential
            session.potential = 0
        
        # Calculate level dynamically based on EXP
        session.level = self.get_level_from_exp(session.exp, session.reborn)
        
        # Load stats
        session._str_val = char.get('str', 10)
        session._con_val = char.get('con', 10)
        session._int_val = char.get('int', 10)
        session._wis_val = char.get('wis', 10)
        session._agi_val = char.get('agi', 10)
        
        # Update HP/SP dynamically using base stats and calculated level
        session.update_max_hp_sp()

        # Automatically update/patch character skills based on element from skills.json
        self.update_character_skills(session)

        # If migrated potential, save character state
        if (char.get('points', 0) == 0 and char.get('potential', 0) > 0):
            self.save_player_to_db(session)

        # Fix for existing naked characters: if level == 1 and all equipments are 0, set beginner outfit
        if session.level == 1 and all(eq == 0 for eq in session.equipments):
            body = session.body
            head = session.head
            beginner_equips = [0] * 6
            if body == 4: # Big Female
                if head == 0: # Iris
                    beginner_equips = [22005, 21006, 0, 23001, 24006, 0]
                elif head == 1: # Lique
                    beginner_equips = [0, 21007, 0, 23002, 24007, 0]
                elif head == 6: # Maria
                    beginner_equips = [22006, 21011, 0, 0, 24011, 10004]
                elif head == 2: # Vanessa
                    beginner_equips = [0, 21008, 0, 0, 24008, 0]
                elif head == 3: # Breillat
                    beginner_equips = [22007, 21009, 0, 0, 24009, 10002]
                elif head == 7: # Karin
                    beginner_equips = [22008, 21015, 0, 0, 24015, 0]
                elif head == 5: # Konnotsuroko
                    beginner_equips = [0, 21013, 0, 0, 24013, 0]
                elif head == 4: # Jessica
                    beginner_equips = [22002, 21010, 0, 0, 24010, 10003]
            elif body == 3: # Big Male
                if head == 0: # Daniel
                    beginner_equips = [0, 21004, 0, 0, 24004, 0]
                elif head == 1: # Sid
                    beginner_equips = [0, 21005, 0, 0, 24005, 0]
                elif head == 2: # More
                    beginner_equips = [0, 21012, 0, 0, 24012, 0]
                elif head == 3: # Kurogane
                    beginner_equips = [22009, 21014, 0, 0, 24014, 18002]
            elif body == 2: # Small Female
                if head == 0: # Nina
                    beginner_equips = [22003, 21002, 0, 0, 24002, 0]
                elif head == 1: # Betty
                    beginner_equips = [22001, 21003, 0, 0, 24003, 0]
            elif body == 1: # Small Male
                if head == 0: # Rocco
                    beginner_equips = [0, 21001, 0, 0, 24001, 0]
            session.equipments = beginner_equips

    def serialize_character_slot(self, char: dict) -> bytes:
        """Serializes character data to bytes for slot screen."""
        reborn = bool(char.get('reborn', 0))
        total_exp = char.get('exp', 0)
        level = self.get_level_from_exp(total_exp, reborn)
        
        con = char.get('con', 10)
        wis = char.get('wis', 10)
        max_hp = int(round(((level ** 0.35) * con * 2) + (level * 1) + (con * 2) + 180))
        max_sp = int(round(((level ** 0.3) * wis * 3.2) + (level * 1) + (wis * 2) + 94))
        
        hp = min(char.get('hp', max_hp), max_hp)
        sp = min(char.get('sp', max_sp), max_sp)

        writer = PacketWriter()
        writer.write_8(char['slot'])
        writer.write_string(char['name'])
        writer.write_8(level)
        writer.write_8(char['element'])
        writer.write_32(max_hp)
        writer.write_32(hp)
        writer.write_32(max_sp)
        writer.write_32(sp)
        # Exp points placeholder
        writer.write_32(total_exp & 0xFFFFFFFF)  # Low 32 bits of Exp
        writer.write_32(char['gold'])
        writer.write_16(char['body'])
        writer.write_16(char['head'])
        writer.write_16(char['hair_color'])
        writer.write_16(char['skin_color'])
        writer.write_16(char['clothing_color'])
        writer.write_16(char['eye_color'])
        writer.write_bool(reborn)
        writer.write_8(char['job'])
        # Equipments (6 slots)
        equips = char['equipments']
        for i in range(6):
            item_id = equips[i]['item_id'] if i < len(equips) else 0
            writer.write_16(item_id)
        return writer.buffer

    async def commence_login(self, session: PlayerSession):
        """Triggers gameplay initialization sequences."""
        logger.info(f"[{session.char_name}] Commencing login to Map {session.map_id}...")
        
        session.logged_in = True
        session.is_warping = True
        
        # Sequence of initialization packets
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(183).write_16(1)) # World ON
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(53).write_16(1))  # Whisper ON
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(52).write_16(1))  # Local ON
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(54).write_16(1))  # Team ON
        
        # Restore saved chat channels mask (AC 33 Sub 3)
        mask = getattr(session, 'chat_channels_mask', 31)
        await session.send_packet(PacketWriter().write_8(33).write_8(3).write_8(mask))
        
        # Greeting banner
        greet = PacketWriter()
        greet.write_8(70).write_8(1).write_8(23).write_string("Something").write_16(194).write_8(0)
        await session.send_packet(greet)
        
        await session.send_packet(PacketWriter().write_8(20).write_8(33).write_8(0))
        
        # Send character stats (Send8_1) (moved to end of login)
        pass
        
        await asyncio.sleep(0.005)
        await session.send_packet(PacketWriter().write_8(14).write_8(13).write_8(3))
        await session.send_packet(PacketWriter().write_8(75).write_8(8).write_16(0))
        
        # Static config payload (item list configuration)
        dummy_config = PacketWriter().write_bytes(bytes([
            104, 1, 1, 0, 12, 44, 137, 1, 45, 137, 1, 25, 134, 1, 24, 134, 1, 22, 134, 1,
            23, 134, 1, 76, 133, 1, 99, 133, 1, 100, 133, 1, 41, 133, 1, 91, 133, 1, 88, 133, 1
        ]))
        await session.send_packet(dummy_config)
        
        # Character spawn (local format)
        await session.send_packet(self.build_local_char_spawn(session))
        
        # Friend List
        await self.send_friend_list(session)
        
        # Sidebar player stats details (moved to end of login)
        pass
        
        # Inventory update (actual database content)
        await session.send_packet(self.build_inventory_packet(session))
        
        # Equipments update (actual database content)
        await session.send_packet(self.build_equipments_packet(session))
        
        # Gold and Settings
        await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
        
        # Settings packet: 2 bytes settings header, 1 byte tradable, 1 byte pkable, 1 byte joinable
        # Set pkable = 1 to enable PvP by default
        settings = PacketWriter().write_8(33).write_8(2).write_bytes(bytes([31, 1, 1, 1]))
        await session.send_packet(settings)
        
        # --- Warp-in block (target.Teleport in C#) ---
        # 1. Add session to map tracking
        self.add_player_to_map(session, session.map_id)
        
        # 2. Broadcast our spawn to other players on map (remote format) and exchange info
        if session.map_id in self.map_players:
            for r in list(self.map_players[session.map_id]):
                if r.char_id != session.char_id:
                    # Broadcast our remote spawn to the other player r
                    await r.send_packet(self.build_remote_char_spawn(session))
                    # Broadcast our equipment to the other player r
                    await r.send_packet(self.build_other_player_equip(session))
                    # Broadcast 10, 3 to the other player r
                    await r.send_packet(PacketWriter().write_8(10).write_8(3).write_32(session.char_id).write_8(255))
                    # Broadcast 5, 8 (warp in entry signal) to the other player r
                    await r.send_packet(PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0))
                    
                    # Send existing player r's spawn to us
                    await session.send_packet(self.build_remote_char_spawn(r))
                    # Send existing player r's equipment to us
                    await session.send_packet(self.build_other_player_equip(r))
                    # Send existing player r's position to us
                    pos = PacketWriter().write_8(7).write_32(r.char_id).write_16(session.map_id).write_16(r.x).write_16(r.y)
                    await session.send_packet(pos)
                    
        # 3. Send map info
        await self.send_map_info(session)
        
        # Position warp / continuation of login sequence after map entry
        await session.send_packet(PacketWriter().write_8(5).write_8(15).write_8(0))
        await session.send_packet(PacketWriter().write_8(62).write_8(53).write_16(2))
        await session.send_packet(PacketWriter().write_8(5).write_8(21).write_8(session.slot))  # Actual selected character slot
        # Send AC 5:11 (Unlock Skill) for all learned skills
        for sk in session.skills:
            skill_id = sk.get('skill_id', 0)
            grade = sk.get('grade', 1)
            exp = sk.get('exp', 0)
            pkt = PacketWriter()
            pkt.write_8(5).write_8(11)
            pkt.write_32(skill_id)
            pkt.write_32(exp)
            await session.send_packet(pkt)
            
            # AC 8:1 stat 110 = Skill Grade Update
            grade_pkt = PacketWriter()
            grade_pkt.write_8(8).write_8(1)
            grade_pkt.write_8(110).write_8(1)
            grade_pkt.write_32(grade)
            grade_pkt.write_32(skill_id)
            await session.send_packet(grade_pkt)
        
        await session.send_packet(PacketWriter().write_8(5).write_8(14).write_8(2))
        await session.send_packet(PacketWriter().write_8(5).write_8(16).write_8(0))
        
        # Time related - C# uses DateTime.ToOADate() which returns a double (float64), NOT int64
        oa_date_float = get_oa_date_float()
        await session.send_packet(PacketWriter().write_8(23).write_8(140).write_8(3).write_bytes(struct.pack('<d', oa_date_float)))
        await session.send_packet(PacketWriter().write_8(25).write_8(44).write_8(2).write_bytes(struct.pack('<d', oa_date_float)))
        
        await session.send_packet(PacketWriter().write_8(23).write_8(160).write_8(3))
        await session.send_packet(PacketWriter().write_8(75).write_8(7).write_8(1))
        
        # Send quest initialization packets to enable client quest log
        await session.send_packet(PacketWriter().write_8(24).write_8(6).write_bytes(bytes([1, 8, 47, 1, 2, 244, 50, 1, 3, 12, 43, 1])))
        await session.send_packet(PacketWriter().write_8(53).write_8(10).write_bytes(bytes([32, 164, 36, 2, 37, 240, 38, 41, 58, 48, 83, 15])))
        await session.send_packet(PacketWriter().write_8(26).write_8(7).write_bytes(bytes([1, 2, 2, 128, 3, 2, 4, 128, 8, 66, 9, 96, 10, 8, 11, 10, 13, 1])))

        # Synchronize all active/completed quest flags and per-player NPC visibility
        from server.quests import GLOBAL_QUEST_ENGINE
        from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
        await GLOBAL_QUEST_ENGINE.send_all_quest_flags(session)
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(self, session, session.map_id)
        await GLOBAL_PREEVENT_INTERPRETER.replay_actor_visibility(self, session, session.map_id)

        # System prompt message
        prompt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            "Welcome to the WLO Python Private Server! Enjoy your adventure!"
        )
        await session.send_packet(prompt)
        
        await session.send_packet(PacketWriter().write_8(69).write_8(1).write_8(71))
        await session.send_packet(PacketWriter().write_8(20).write_8(60).write_8(1))
        
        # Static packet
        await session.send_packet(PacketWriter().write_bytes(bytes([66, 1, 1, 12, 43, 0, 0, 0, 0, 0, 0, 0, 0])))
        
        # AC 5:13 is actually for Quickbar, not the main skill list!
        # Clear quickbar slots 1-10
        for slot in range(1, 11):
            await session.send_packet(PacketWriter().write_8(5).write_8(13).write_8(slot).write_16(0))
        
        await session.send_packet(PacketWriter().write_8(5).write_8(4))
        
        # Dispatch Authentic Item Mall Handshake (AC 75:1, AC 75:10, AC 75:8, AC 75:7, AC 75:3)
        from server.item_mall import GLOBAL_ITEM_MALL_MANAGER
        await GLOBAL_ITEM_MALL_MANAGER.send_initial_mall_sync(session)

        # Free Starter Items Delivery for New Characters (Authentic PCAP oyunailkgirisvebedavaitemverilmesi.pcapng)
        if not getattr(session, "received_starter_pack", False) and len(session.inventory) <= 2:
            from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
            starter_gifts = GLOBAL_STARTER_PACK_MANAGER.get_delivery_tuples()
            for itm_id, itm_cnt in starter_gifts:
                add_item_to_inventory(session, itm_id, itm_cnt)
                delivery_pkt = PacketWriter().write_8(23).write_8(6).write_16(itm_id).write_16(itm_cnt).write_bytes(bytes(27))
                await session.send_packet(delivery_pkt)
            session.received_starter_pack = True
            self.save_player_to_db(session)
            logger.info(f"[{session.char_name}] Granted authentic starter items pack ({len(starter_gifts)} items) via AC 23 Sub 6.")

        # Always synchronize full inventory packet at the conclusion of login sequence so
        # the client's inventory bag UI is guaranteed to populate for both new and returning players.
        await session.send_packet(self.build_inventory_packet(session))
        
        # Send ground items to the player who just joined the map
        await self.send_ground_items(session)
        
        # Send stats updates at the very end of login so client registers them properly
        await self.send_5_3_login(session)
        await asyncio.sleep(0.5) 
        await self.send_stats_update(session, levelup=False)
        await self.send_pet_list(session)
        
        logger.info(f"[{session.char_name}] Login complete.")

    def start_bath_healing(self, session):
        """Starts asynchronous hot spring healing for bathing player."""
        if session.bath_task and not session.bath_task.done():
            return
            
        async def heal_loop():
            elapsed = 0
            try:
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Entering the Hot Spring. Restoring HP/SP...")
                await session.send_packet(sys_msg)
                
                while session.bathing and elapsed < 300:
                    await asyncio.sleep(10)
                    elapsed += 10
                    
                    # Heals 10%
                    hp_gain = max(1, int(session.max_hp * 0.1))
                    sp_gain = max(1, int(session.max_sp * 0.1))
                    session.hp = min(session.max_hp, session.hp + hp_gain)
                    session.sp = min(session.max_sp, session.sp + sp_gain)
                    
                    # Sync stats to client
                    await self.send_stats_update(session, levelup=False)
                    
                    # Send periodic status
                    status_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Hot Spring Pack time: {elapsed}s")
                    await session.send_packet(status_msg)
                    
                if elapsed >= 300:
                    session.bathing = False
                    status_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Hot Spring time at max!")
                    await session.send_packet(status_msg)
                else:
                    status_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Hot Spring ended")
                    await session.send_packet(status_msg)
            except asyncio.CancelledError:
                status_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Hot Spring ended")
                await session.send_packet(status_msg)
            except Exception as e:
                logger.error(f"[Bath Heal] Error: {e}", exc_info=True)
            finally:
                session.bathing = False
                
        session.bathing = True
        session.bath_task = asyncio.create_task(heal_loop())

    def stop_bath_healing(self, session):
        """Stops hot spring healing for bathing player."""
        session.bathing = False
        if session.bath_task:
            session.bath_task.cancel()
            session.bath_task = None

    def get_max_exp_for_level(self, level: int, reborn: bool = False) -> int:
        """Returns the max EXP to advance from current level to next level."""
        if not reborn:
            return int(round((level + 1) ** 3.1 + 5))
        else:
            if level < 150:
                return int((level + 1) ** 3.3 + 50)
            else:
                return int((level + 1) ** 3.3 + (level + 1 - 150) ** 4.9)

    def get_level_from_exp(self, total_exp: int, reborn: bool = False) -> int:
        """Calculates level dynamically based on total accumulated EXP."""
        level = 1
        temp_exp = total_exp
        while True:
            max_exp = self.get_max_exp_for_level(level, reborn)
            if temp_exp >= max_exp:
                if not reborn and level + 1 > 199:
                    break
                temp_exp -= max_exp
                level += 1
            else:
                break
        return level

    def get_cumulative_exp_for_level(self, level: int, reborn: bool = False) -> int:
        """Returns the total cumulative EXP needed to reach the given level from level 1."""
        total = 0
        for lvl in range(1, level):
            total += self.get_max_exp_for_level(lvl, reborn)
        return total

    def get_exp_within_level(self, total_exp: int, level: int, reborn: bool = False) -> int:
        """Returns the EXP within the current level."""
        cum_exp = self.get_cumulative_exp_for_level(level, reborn)
        return max(0, total_exp - cum_exp)

    def get_player_atk(self, session: PlayerSession) -> int:
        """Calculate player physical attack."""
        lvl = session.level
        if session.element == 3:  # Fire
            val = int(round(lvl * 2.0 + session.str_val * 2.0))
        else:
            val = int(round(lvl * 1.4 + session.str_val * 2.0))
        if getattr(session, 'job', 0) == 1:  # Warrior
            val = int(val * 1.1)
        return val

    def get_player_def(self, session: PlayerSession) -> int:
        """Calculate player physical defense."""
        lvl = session.level
        if session.element == 1:  # Earth
            val = int(round(lvl * 3.0 + session.con_val * 2.0))
        else:
            val = int(round(lvl * 2.0 + session.con_val * 2.0))
        if getattr(session, 'job', 0) == 2:  # Guardian
            val = int(val * 1.1)
        return val

    def get_player_spd(self, session: PlayerSession) -> int:
        """Calculate player speed."""
        lvl = session.level
        if session.element == 4:  # Wind
            val = int(round(lvl * 2.1 + session.agi_val * 2.2))
        else:
            val = int(round(lvl * 1.6 + session.agi_val * 2.2))
        if getattr(session, 'job', 0) in [3, 6]:  # Knight (3) or Thief (6)
            val = int(val * 1.1)
        return val

    def get_player_matk(self, session: PlayerSession) -> int:
        """Calculate player magic attack."""
        lvl = session.level
        if session.element == 3:  # Fire
            val = int(round(lvl * 1.6 + session.int_val * 2.0))
        else:
            val = int(round(lvl * 1.4 + session.int_val * 2.0))
        if getattr(session, 'job', 0) == 4:  # Mage
            val = int(val * 1.1)
        return val

    def get_player_mdef(self, session: PlayerSession) -> int:
        """Calculate player magic defense."""
        lvl = session.level
        val = int(round(lvl * 2.0 + session.wis_val * 2.0))
        if getattr(session, 'job', 0) == 5:  # Priest
            val = int(val * 1.1)
        return val
    def build_stats_update_packets(self, session: PlayerSession, levelup: bool = True) -> list[PacketWriter]:
        """Builds character stats update packets (Send8_1) matching C# emulator perfectly."""
        session.update_max_hp_sp()

        atk = self.get_player_atk(session)

    async def send_stats_update(self, session: PlayerSession, levelup: bool = False):
        """Sends derived stats to the client. Uses AC 8 Sub 1."""
        
        async def send_stat(stat_id: int, val: int, is_exp: bool = False):
            pkt = PacketWriter()
            pkt.write_8(8).write_8(1).write_8(stat_id).write_8(1)
            if is_exp:
                pkt.write_64(val)
            else:
                pkt.write_32(val).write_32(0)
            await session.send_packet(pkt)

        session.update_max_hp_sp()
        atk = self.get_player_atk(session)
        def_val = self.get_player_def(session)
        mat = self.get_player_matk(session)
        mdf = self.get_player_mdef(session)
        spd = self.get_player_spd(session)

        # Send individual 8, 1 updates
        # HP
        await send_stat(207, 0) # EquippedMaxHP
        await send_stat(25, session.hp)
        # SP
        await send_stat(208, 0) # EquippedMaxSP
        await send_stat(26, session.sp)
        # STR
        await send_stat(210, 0) # EquippedATK
        await send_stat(41, atk)
        if levelup: await send_stat(28, session.str_val)
        # CON
        await send_stat(211, 0) # EquippedDEF
        await send_stat(42, def_val)
        if levelup:
            await send_stat(205, session.max_hp)
            await send_stat(29, session.con_val)
        # SPD
        await send_stat(214, 0) # EquippedSPD
        await send_stat(45, spd)
        if levelup: await send_stat(30, session.agi_val)
        # INT
        await send_stat(215, 0) # EquippedMAT
        await send_stat(43, mat)
        if levelup: await send_stat(27, session.int_val)
        # WIS
        await send_stat(216, 0) # EquippedMDF
        await send_stat(44, mdf)
        if levelup:
            await send_stat(206, session.max_sp)
            await send_stat(33, session.wis_val)

        # Points
        await send_stat(38, getattr(session, 'points', 0))
        await send_stat(37, getattr(session, 'skill_points', 0))

    async def send_5_3_login(self, session: PlayerSession):
        """Sends the 5-3 initialization packet (only used during login)."""
        sb = PacketWriter()
        sb.write_8(5).write_8(3)
        sb.write_8(session.element)
        sb.write_32(session.hp)
        sb.write_16(session.sp)
        # Base stats (str, con, int, wis, agi) are 16-bit ushorts
        sb.write_16(session.str_val).write_16(session.con_val).write_16(session.int_val).write_16(session.wis_val).write_16(session.agi_val)
        # Level is a single byte (cap at 255)
        sb.write_8(min(255, session.level))
        # Exp within current level as 64-bit integer
        sb.write_64(max(0, session.exp + 6))
        sb.write_32(session.max_hp)
        sb.write_16(session.max_sp)
        # 7 dummy DWords (Authentic constants 417 and 240)
        sb.write_32(417).write_32(0).write_32(0).write_32(240).write_32(0).write_32(0).write_32(0)
        sb.write_16(0) # 0 skills inside AC 5:3
        sb.write_32(0)
        sb.write_bool(session.reborn)
        sb.write_8(session.job)
        sb.write_8(getattr(session, 'skill_points', 0)) # Potential stat
        await session.send_packet(sb)
        
    def build_pet_list_packet(self, session: PlayerSession) -> PacketWriter:
        p = PacketWriter()
        p.write_8(15).write_8(8)
        for idx, pet in enumerate(session.pets):
            slot = idx + 1
            if slot > 4:
                break
            p.write_8(slot)
            p.write_16(pet.get("pet_id", 0))   # write_16 for NPC IDs
            p.write_32(pet.get("exp", 0))
            p.write_8(pet.get("level", 1))
            
            # HP and SP limits calculation
            level = pet.get("level", 1)
            con = pet.get("con", 5)
            wis = pet.get("wis", 5)
            max_hp = int(round(((level ** 0.35) * con * 2) + (level * 1) + (con * 2) + 180))
            max_sp = int(round(((level ** 0.3) * wis * 3.2) + (level * 1) + (wis * 2) + 94))
            hp = min(pet.get("hp", max_hp), max_hp)
            sp = min(pet.get("sp", max_sp), max_sp)
            
            p.write_32(hp)
            p.write_16(sp)
            p.write_16(pet.get("int", 5))
            p.write_16(pet.get("str", 5))
            p.write_16(pet.get("con", 5))
            p.write_16(pet.get("agi", 5))
            p.write_16(pet.get("wis", 5))
            p.write_8(0)
            p.write_8(pet.get("amity", 100))
            p.write_16(1) # Weapon (1 = default/none)
            p.write_8(0)  # Worn count
            for _ in range(6):
                p.write_16(0) # 6 equipments
            p.write_16(0)
            p.write_8(pet.get("reborn", 0))
            p.write_8(pet.get("potential", 0))
        return p

    async def send_pet_list(self, session: PlayerSession):
        """Sends companion list (AC 15 Sub 8) to the client."""
        await session.send_packet(self.build_pet_list_packet(session))

    async def send_pet_stats(self, session: PlayerSession, slot: int):
        """Sends stats for the pet in the given slot using AC 8 Sub 2."""
        if slot < 1 or slot > len(session.pets):
            return
        pet = session.pets[slot - 1]
        
        level = pet.get("level", 1)
        con = pet.get("con", 5)
        wis = pet.get("wis", 5)
        str_val = pet.get("str", 5)
        agi_val = pet.get("agi", 5)
        int_val = pet.get("int", 5)
        
        max_hp = int(round(((level ** 0.35) * con * 2) + (level * 1) + (con * 2) + 180))
        max_sp = int(round(((level ** 0.3) * wis * 3.2) + (level * 1) + (wis * 2) + 94))
        
        hp = min(pet.get("hp", max_hp), max_hp)
        sp = min(pet.get("sp", max_sp), max_sp)
        
        atk = int(round(level * 1.4 + str_val * 2.0))
        def_val = int(round(level * 1.5 + con * 1.75))
        spd = int(round(level * 1.6 + agi_val * 2.2))
        matk = int(round(level * 1.4 + int_val * 2.0))
        mdef = int(round(level * 2.0 + wis * 2.2))
        
        stats = [
            (205, max_hp),   # Base Max HP
            (207, 0),        # Equipment Max HP bonus
            (25, hp),        # Cur HP
            (206, max_sp),   # Base Max SP
            (208, 0),        # Equipment Max SP bonus
            (26, sp),        # Cur SP
            (35, level),     # Level
            (36, pet.get("exp", 0) + 6),       # Total Exp (int64)
            (37, max(0, level - 1)),  # EXP table index used by client (Level - 1)
            (28, str_val),   # Base STR
            (29, con),       # Base CON
            (30, agi_val),   # Base AGI
            (27, int_val),   # Base INT
            (33, wis),       # Base WIS
            (210, 0),        # Atk bonus
            (41, atk),       # Full Atk
            (211, 0),        # Def bonus
            (42, def_val),   # Full Def
            (214, 0),        # Spd bonus
            (45, spd),       # Full Spd
            (215, 0),        # Matk bonus
            (43, matk),      # Full Magic Atk
            (216, 0),        # Mdef bonus
            (44, mdef),      # Full Magic Def
        ]
        
        for stat_id, val in stats:
            pkt = PacketWriter()
            if stat_id == 36:
                pkt.write_8(8).write_8(2).write_8(stat_id).write_8(1).write_64(val)
            else:
                pkt.write_8(8).write_8(2).write_8(stat_id).write_8(1).write_32(val).write_32(0)
            await session.send_packet(pkt)
            await asyncio.sleep(0.001)

    async def send_ground_items(self, session: PlayerSession):
        """Sends all active ground items on the current map to the player session."""
        items = self.map_ground_items.get(session.map_id)
        if not items:
            return
        for idx, gi in enumerate(items):
            if gi is not None:
                spawn_pkt = PacketWriter()
                spawn_pkt.write_8(23).write_8(3)
                spawn_pkt.write_16(gi["item_id"])
                spawn_pkt.write_16(gi["x"])
                spawn_pkt.write_16(gi["y"])
                spawn_pkt.write_32(idx + 1)
                spawn_pkt.write_8(0)  # Spawns silently on ground
                await session.send_packet(spawn_pkt)

    def build_local_char_spawn(self, session: PlayerSession) -> PacketWriter:
        """Serializes local character map appearance (AC 3 Local Format)."""
        p = PacketWriter()
        p.write_8(3)
        p.write_32(session.char_id)
        p.write_8(session.body)
        p.write_16(session.map_id)
        p.write_16(session.x)
        p.write_16(session.y)
        p.write_8(0)  # Emote/Direction
        p.write_8(session.head)
        p.write_8(0)
        p.write_16(session.hair_color)
        p.write_16(session.skin_color)
        p.write_16(session.clothing_color)
        p.write_16(session.eye_color)
        
        worn_items = [eq for eq in session.equipments if eq > 0]
        p.write_8(len(worn_items))
        for eq_id in worn_items:
            p.write_16(eq_id)
            
        riding_pet_id = 0
        for pet in session.pets:
            if pet.get("riding", False):
                riding_pet_id = pet.get("pet_id", 0)
                break
        p.write_32(riding_pet_id)
        p.write_string(session.char_name)
        p.write_string("")  # Nickname
        p.write_bytes(bytes(14))
        return p


    def build_remote_char_spawn(self, session: PlayerSession) -> PacketWriter:
        """Serializes remote character map appearance (AC 3 Remote Format)."""
        p = PacketWriter()
        p.write_8(3)
        p.write_32(session.char_id)
        p.write_8(session.body)
        p.write_8(session.element)
        p.write_8(session.level)
        p.write_16(session.map_id)
        p.write_16(session.x)
        p.write_16(session.y)
        p.write_8(0)  # Emote/Direction
        p.write_8(session.head)
        p.write_8(0)
        p.write_16(session.hair_color)
        p.write_16(session.skin_color)
        p.write_16(session.clothing_color)
        p.write_16(session.eye_color)
        
        worn_items = [eq for eq in session.equipments if eq > 0]
        p.write_8(len(worn_items))
        for eq_id in worn_items:
            p.write_16(eq_id)
            
        riding_pet_id = 0
        for pet in session.pets:
            if pet.get("riding", False):
                riding_pet_id = pet.get("pet_id", 0)
                break
        p.write_32(riding_pet_id)
        p.write_8(0)
        p.write_bool(session.reborn)
        p.write_8(session.job)
        p.write_string(session.char_name)
        p.write_string("")  # Nickname
        p.write_32(255)
        p.write_8(0) # trailing 00 01 (Part 1)
        p.write_8(1) # trailing 00 01 (Part 2)
        return p

    def build_companion_spawn_packet(self, session: PlayerSession, pet: dict) -> PacketWriter:
        """Serializes companion map appearance (AC 15 Sub 4)."""
        p = PacketWriter()
        p.write_8(15).write_8(4)
        p.write_32(session.char_id)  # Companion Owner Player ID
        p.write_32(pet.get("pet_id"))  # Template NPC ID
        p.write_8(0)  # Unk1
        p.write_8(1)  # Unk2
        
        # Name
        pet_name = pet.get("name")
        if not pet_name:
            pet_name = "Companion"
            try:
                conn = sqlite3.connect(self.static_db_path)
                row = conn.execute("SELECT name FROM npc_data WHERE id = ?", (pet.get("pet_id"),)).fetchone()
                conn.close()
                if row:
                    pet_name = row[0].split(chr(0))[0].strip()
            except Exception as e:
                logger.error(f"[Companion Spawn Packet] Error fetching name: {e}")
        p.write_string(pet_name)
        
        # Trailing fields
        p.write_16(session.x + 30)  # X coordinate, offset from player to avoid overlap
        p.write_16(session.y + 30)  # Y coordinate
        p.write_16(0)  # Weapon ID placeholder
        p.write_8(safe_int(pet.get("reborn"), 0))  # Reborn status
        p.write_8(safe_int(pet.get("job"), 0))  # Job
        return p

    def build_inventory_packet(self, session: PlayerSession) -> PacketWriter:
        """Serializes SQLite inventory items to 29-byte blocks (AC 23 Sub 5)."""
        p = PacketWriter()
        p.write_8(23).write_8(5)

        slots = {}
        for idx, item in enumerate(session.inventory):
            slot = item.get('slot')
            if slot is None:
                for s in range(1, 51):
                    if s not in slots:
                        slot = s
                        break
            if slot and slot <= 50:
                slots[slot] = item

        for slot in range(1, 51):
            item = slots.get(slot)
            p.write_8(slot)
            if item:
                p.write_16(item.get('item_id', 0))
                p.write_8(item.get('amount', 1))
                p.write_8(item.get('damage', 0))
            else:
                p.write_16(0)
                p.write_8(0)
                p.write_8(0)
            p.write_bytes(bytes(24))

        return p

    async def grant_item(self, session: PlayerSession, item_id: int, amount: int = 1, slot: int = None, send_acquire_notice: bool = True) -> bool:
        """
        Atomically grants an item to player inventory, dispatches authentic client sync packets
        (AC 23 Sub 6 item arrival if send_acquire_notice is True, AC 23 Sub 8 slot update, AC 23 Sub 5 full inventory),
        and persists to SQLite database.
        """
        if not session or item_id <= 0:
            return False
        if amount <= 0:
            amount = 1

        actual_slot = add_item_to_inventory(session, item_id, amount=amount, slot=slot)
        if actual_slot is None:
            logger.warning(f"[{getattr(session, 'char_name', 'Player')}] Cannot grant Item #{item_id}: Inventory is full!")
            return False

        # 1. Persist to DB
        self.save_player_to_db(session)

        # 2. AC 23 Sub 6: Authentic Item Delivery / Acquisition packet (triggers 'Obtain X pcs' client popup)
        if send_acquire_notice:
            # Layout: [23, 6, item_id(uint16_LE), amount(uint16_LE), padding(25 zeros)] (31 bytes total)
            p6 = PacketWriter().write_8(23).write_8(6).write_16(item_id).write_16(amount).write_bytes(bytes(25))
            await session.send_packet(p6)

        # 3. AC 23 Sub 8: Specific slot state update
        item = get_item_at_slot(session, actual_slot)
        cur_amt = item.get("amount", amount) if item else amount
        p8 = PacketWriter().write_8(23).write_8(8).write_8(actual_slot).write_16(item_id).write_8(cur_amt).write_8(0).write_bytes(bytes(24))
        await session.send_packet(p8)

        # 4. AC 23 Sub 5: Full 50-slot serialized bag sync
        await session.send_packet(self.build_inventory_packet(session))
        logger.info(f"[{getattr(session, 'char_name', 'Player')}] Granted Item #{item_id} x{amount} in Slot {actual_slot}.")
        return True

    def build_equipments_packet(self, session: PlayerSession) -> PacketWriter:
        """Serializes SQLite equipped items to 21-byte blocks (AC 23 Sub 11)."""
        p = PacketWriter()
        p.write_8(23).write_8(11)
        worn_items = [eq for eq in session.equipments if eq > 0]
        for eq_id in worn_items:
            p.write_16(eq_id)
            p.write_bytes(bytes(19))
        return p

    def build_other_player_equip(self, session: PlayerSession) -> PacketWriter:
        """Serializes non-local player equipment list (AC 5 Sub 0)."""
        p = PacketWriter()
        p.write_8(5).write_8(0).write_32(session.char_id)
        worn_items = [eq for eq in session.equipments if eq > 0]
        for eq_id in worn_items:
            p.write_16(eq_id)
        return p

    async def spawn_existing_map_players(self, session: PlayerSession):
        """Spawns existing map players on the new connection's screen."""
        if session.map_id not in self.map_players:
            return
            
        for r in self.map_players[session.map_id]:
            if r.char_id == session.char_id:
                continue
                
            # Spawn r on session's screen (remote format)
            await session.send_packet(self.build_remote_char_spawn(r))
            
            # Send r's equipment to session
            await session.send_packet(self.build_other_player_equip(r))
            
            # Position update
            pos = PacketWriter()
            pos.write_8(7)
            pos.write_32(r.char_id)
            pos.write_16(session.map_id)
            pos.write_16(r.x)
            pos.write_16(r.y)
            await session.send_packet(pos)

    async def send_map_info(self, session: PlayerSession):
        """Sends map initialization packets matching C# Map.cs SendMapInfo.
        Each packet has its own header - the client parses them individually."""
        
        # 1. Map ID Info (23, 138) - always first
        await session.send_packet(PacketWriter().write_8(23).write_8(138))

        # 2. Send Map NPCs Batch Registration (AC 22 Sub 4 - Matching C# Map.cs lines 1320-1372)
        npcs = self.map_npcs.get(session.map_id, [])
        if npcs:
            npc_pkt = PacketWriter().write_8(22).write_8(4)
            sorted_npcs = sorted(
                npcs,
                key=lambda n: n.click_id if hasattr(n, 'click_id') else (n.get('click_id', 0) if isinstance(n, dict) else 0)
            )
            for npc in sorted_npcs:
                c_id = npc.click_id if hasattr(npc, 'click_id') else (npc.get('click_id', 0) if isinstance(npc, dict) else 0)
                t_id = npc.template_id if hasattr(npc, 'template_id') else ((npc.get('npc_id', 0) or npc.get('template_id', 0)) if isinstance(npc, dict) else 0)
                n_name = npc.name if hasattr(npc, 'name') else (npc.get('name', '') if isinstance(npc, dict) else '')
                n_x = npc.x if hasattr(npc, 'x') else (npc.get('x', 0) if isinstance(npc, dict) else 0)
                n_y = npc.y if hasattr(npc, 'y') else (npc.get('y', 0) if isinstance(npc, dict) else 0)
                is_broken = getattr(npc, 'is_broken', False) or (npc.get('is_broken', False) if isinstance(npc, dict) else False)

                # Check if recruited companion
                is_recruited = False
                if hasattr(session, 'has_recruited_companion'):
                    is_recruited = session.has_recruited_companion(n_name, t_id)
                elif hasattr(session, 'companions'):
                    for c in session.companions:
                        if (c.get('name') and c.get('name').lower() == n_name.lower()) or c.get('npc_id') == t_id:
                            is_recruited = True
                            break

                # Check if opened in charchests for this player
                is_opened = False
                try:
                    from server.chest_system import GLOBAL_CHEST_SYSTEM
                    if hasattr(session, 'char_id') and session.char_id:
                        is_perm = hasattr(npc, 'is_permanent_chest') and npc.is_permanent_chest()
                        is_opened = GLOBAL_CHEST_SYSTEM.is_chest_opened(session.char_id, session.map_id, c_id, is_permanent=is_perm)
                except Exception:
                    is_opened = False

                is_hidden = getattr(npc, 'visible', True) is False or (npc.get('visible', True) is False if isinstance(npc, dict) else False)

                if is_recruited or is_hidden:
                    state = 0xFFFF
                elif is_opened or is_broken:
                    state = 0x0001
                else:
                    state = 0x0000

                npc_pkt.write_16(c_id)
                npc_pkt.write_16(state)
                npc_pkt.write_16(n_x)
                npc_pkt.write_16(n_y)
                npc_pkt.write_8(1)
                npc_pkt.write_8(0)
                npc_pkt.write_32(0)

            await session.send_packet(npc_pkt)

            # Send individual hide packets for recruited companions (AC 22:10)
            for npc in sorted_npcs:
                # Static props and permanent chests must never receive AC 22:10 packets (handled natively via AC 22:4 state)
                if hasattr(npc, 'is_static_npc') and npc.is_static_npc():
                    continue
                c_id = npc.click_id if hasattr(npc, 'click_id') else (npc.get('click_id', 0) if isinstance(npc, dict) else 0)
                t_id = npc.template_id if hasattr(npc, 'template_id') else ((npc.get('npc_id', 0) or npc.get('template_id', 0)) if isinstance(npc, dict) else 0)
                n_name = npc.name if hasattr(npc, 'name') else (npc.get('name', '') if isinstance(npc, dict) else '')
                is_recruited = False
                if hasattr(session, 'has_recruited_companion'):
                    is_recruited = session.has_recruited_companion(n_name, t_id)
                elif hasattr(session, 'companions'):
                    for c in session.companions:
                        if (c.get('name') and c.get('name').lower() == n_name.lower()) or c.get('npc_id') == t_id:
                            is_recruited = True
                            break
                is_hidden = getattr(npc, 'visible', True) is False or (npc.get('visible', True) is False if isinstance(npc, dict) else False)
                if is_recruited or is_hidden:
                    hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(c_id).write_8(0xFF).write_8(0xFF)
                    await session.send_packet(hide_pkt)

        # 3. Evaluate native map PreEvents (Matching C# Map.cs line 1388)
        from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
        await GLOBAL_PREEVENT_INTERPRETER.evaluate_map_preevents(session, session.map_id)

        # 4. Add players on map (including self) and their confirmations
        # C# sends 10,3 for ALL players INCLUDING self (not just others)
        if session.map_id in self.map_players:
            for r in self.map_players[session.map_id]:
                await session.send_packet(PacketWriter().write_8(23).write_8(122).write_32(r.char_id))
                await session.send_packet(PacketWriter().write_8(10).write_8(3).write_32(r.char_id).write_8(255))
                await session.send_packet(PacketWriter().write_8(23).write_8(76).write_32(r.char_id))

        # 5. Map load complete trigger
        await session.send_packet(PacketWriter().write_8(23).write_8(102))
        
        # 6. Interface unlock
        await session.send_packet(PacketWriter().write_8(20).write_8(8))

    async def check_proximity_combat(self, session: PlayerSession):
        """Checks if player walked into aggro range of a hostile map NPC."""
        return # Sadece tıklanınca savaşa girmesi için otomatik aggro kapatıldı
        
        if session.map_id < 60000:
            return
            
        closest_npc = None
        min_dist = 100

        npcs = self.map_npcs.get(session.map_id, [])
        for npc in npcs:
            npc_id = npc.get('npc_id', 0)
            name = npc.get('name') or ""
            # Include Troll in hostile list
            is_hostile = (17000 <= npc_id <= 18000) or ("Monster" in name) or ("Spider" in name) or ("Wolf" in name) or ("Troll" in name)
            
            if is_hostile:
                dx = session.x - npc['x']
                dy = session.y - npc['y']
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist < min_dist:
                    min_dist = dist
                    closest_npc = npc
                    
        if closest_npc:
            npc_id = closest_npc.get('npc_id', 0)
            logger.info(f"[Combat] Auto-aggro triggered: player {session.char_name} walked near hostile {closest_npc['name']} (ID {npc_id}) at distance {min_dist:.1f}")
            await self.enter_battle(session, closest_npc['click_id'], npc_id)

    async def _send_quest_dialogue(self, session: PlayerSession, dialog_hex: str, npc_id: int, step: int = 1, portrait_type: int = 1):
        """Send a WLO dialogue packet (AC 20 Sub 1) matching the real protocol format.

        Real 16-byte payload format (from PCAP analysis):
          [0-2]  = 00 00 00  (padding)
          [3]    = step number (1=normal dialog, 6=option menu)
          [4]    = 01  (fixed)
          [5]    = portrait_type (03=NPC speech, 07=player speech, 06=option)
          [6]    = npc_click_id (low byte)
          [7]    = 00 (padding)
          [8-11] = 01 00 00 00 (flags, sometimes 02 00 00 00)
          [12]   = 00 (padding)
          [13-15]= dialog_hex (3 bytes = Talk.dat byte offset LE)
        """
        click_id_byte = npc_id & 0xFF
        payload = bytes([
            0x00, 0x00, 0x00,       # [0-2] padding
            step & 0xFF,            # [3]   dialog step
            0x01,                   # [4]   fixed
            portrait_type & 0xFF,   # [5]   portrait type (03=NPC, 07=player)
            click_id_byte,          # [6]   npc click_id low byte
            0x00,                   # [7]   padding
            0x01, 0x00, 0x00, 0x00, # [8-11] flags
            0x00,                   # [12]  padding
        ]) + bytes.fromhex(dialog_hex)
        pkt = PacketWriter().write_8(20).write_8(1).write_bytes(payload)
        await session.send_packet(pkt)

    async def send_dialogue(self, session: PlayerSession, click_id: int, talk_id: int, step: int = 1, portrait_type: int = 3):
        """Sends an authentic in-game dialogue packet (AC 20 Sub 1) using a TalkID from Talk.dat."""
        dialog_hex = f"{talk_id & 0xFF:02x}{(talk_id >> 8) & 0xFF:02x}{(talk_id >> 16) & 0xFF:02x}"
        await self._send_quest_dialogue(session, dialog_hex, click_id, step=step, portrait_type=portrait_type)

    async def _send_quest_spawn(self, session: PlayerSession, spawn_hex: str):
        # 03 fd spawn packet
        pkt = PacketWriter().write_bytes(bytes.fromhex(spawn_hex))
        await session.send_packet(pkt)

    async def _send_quest_flag(self, session: PlayerSession, quest_id: int, state: int):
        # AC 24 Sub 5 -> 18 05 <quest_id 16-bit> <state 8-bit>
        pkt = PacketWriter().write_8(24).write_8(5).write_16(quest_id).write_8(state)
        await session.send_packet(pkt)
        
        # Save to database
        if not hasattr(session, 'quests') or session.quests is None:
            session.quests = {}
        if isinstance(session.quests, dict):
            session.quests[str(quest_id)] = state
        elif isinstance(session.quests, list):
            found = False
            for q in session.quests:
                if isinstance(q, dict) and str(q.get("quest_id", q.get("id", ""))) == str(quest_id):
                    q["state"] = state
                    found = True
                    break
            if not found:
                session.quests.append({"quest_id": quest_id, "state": state})
        self.save_player_to_db(session)

    def _is_visible_portal(self, name: str, dest_mapID: int) -> bool:
        if dest_mapID == 58001:
            return False
        blacklist = ['左上', '左下', '右上', 'right', 'left', '右下', '大地图', '大地圖', '上岸']
        for b in blacklist:
            if b in name:
                return False
        if name and name[0].isdigit():
            return False
        return True

    def lookup_portal(self, map_id: int, portal_id: int, by_click_id: bool = False, px: int = 0, py: int = 0) -> tuple:
        """Looks up portal destination.
        Priority:
          1. portal_overrides table in DB
          2. Geometric matching based on reverse-portal destinations (if px, py provided)
          3. eve.Emg portal list: match by direct click_id fallback
        """
        # 1. Check database overrides first
        try:
            conn = sqlite3.connect(self.static_db_path)
            cursor = conn.execute("SELECT dstMap, dstX, dstY FROM portal_overrides WHERE mapID = ? AND portalID = ?", (map_id, portal_id))
            row = cursor.fetchone()
            conn.close()
            if row:
                logger.info(f"[Portal] DB OVERRIDE: map {map_id} portal {portal_id} -> Map {row[0]} ({row[1]}, {row[2]})")
                return row[0], row[1], row[2]
        except Exception as e:
            logger.error(f"[Portal] Failed to query portal_overrides: {e}")

        # 2. Geometric matching (if px, py are provided)
        if px > 0 and py > 0 and not by_click_id:
            best_w = None
            best_dist = 999999
            
            for w in self.map_portals.get(map_id, []):
                # For this candidate portal, check reverse portals from its destination
                rev_portals = [rev_w for rev_w in self.map_portals.get(w['dst_map'], []) if rev_w['dst_map'] == map_id]
                for rev_w in rev_portals:
                    dist = math.hypot(px - rev_w['dst_x'], py - rev_w['dst_y'])
                    if dist < best_dist:
                        best_dist = dist
                        best_w = w
            
            if best_w is not None and best_dist < 400:
                logger.info(f"[Portal] GEOMETRIC: map {map_id} portal {portal_id} pos({px},{py}) -> Map {best_w['dst_map']} ({best_w['dst_x']}, {best_w['dst_y']}) dist={best_dist:.1f}")
                return best_w['dst_map'], best_w['dst_x'], best_w['dst_y']

        # 3. Look up directly in eve.Emg data by click_id
        portals_list = self.map_portals.get(map_id, [])
        for w in portals_list:
            if w['click_id'] == portal_id:
                logger.info(f"[Portal] eve.Emg fallback: map {map_id} portal {portal_id} -> Map {w['dst_map']} ({w['dst_x']}, {w['dst_y']})")
                return w['dst_map'], w['dst_x'], w['dst_y']

        # 4. Fallback: if this map has exactly one portal, use it
        if len(portals_list) == 1:
            w = portals_list[0]
            logger.info(f"[Portal] Single-exit fallback: map {map_id} -> Map {w['dst_map']} ({w['dst_x']}, {w['dst_y']})")
            return w['dst_map'], w['dst_x'], w['dst_y']

        logger.warning(f"[Portal] No destination found for map {map_id} portal {portal_id}")
        return None, None, None


    async def warp_player(self, session: PlayerSession, dst_map: int, dst_x: int, dst_y: int, portal_id: int = 0):
        """Executes full asynchronous map warp sequence."""
        logger.info(f"[{session.char_name}] Warping from map {session.map_id} -> {dst_map} ({dst_x}, {dst_y})")
        
        # 0. Send AC 20 Sub 7 to lock interface
        await session.send_packet(PacketWriter().write_8(20).write_8(7))
        
        # 1. Send AC 12 (Warp Animation) to old map
        anim = PacketWriter()
        anim.write_8(12)
        anim.write_32(session.char_id)
        anim.write_16(dst_map)
        anim.write_16(dst_x)
        anim.write_16(dst_y)
        anim.write_16(portal_id)
        anim.write_8(0)
        self.broadcast_to_map(session.map_id, anim)
        
        # 2. Remove player from old map
        self.remove_player_from_map(session)
        
        # 3. Send interface clear sequences to player
        await session.send_packet(PacketWriter().write_8(23).write_8(32).write_32(session.char_id))
        await session.send_packet(PacketWriter().write_8(23).write_8(112).write_32(session.char_id))
        await session.send_packet(PacketWriter().write_8(23).write_8(132).write_32(session.char_id))
        
        # 4. Update coordinates
        session.map_id = dst_map
        session.x = dst_x
        session.y = dst_y
        session.is_warping = True
        session.in_map = False
        
        # 5. Add to new map
        self.add_player_to_map(session, dst_map)
        
        # 6. Broadcast AC 12 warp confirmation to the entire destination map (including warping player)
        confirm = PacketWriter()
        confirm.write_8(12)
        confirm.write_32(session.char_id)
        confirm.write_16(dst_map)
        confirm.write_16(dst_x)
        confirm.write_16(dst_y)
        confirm.write_16(portal_id)
        confirm.write_8(0)
        self.broadcast_to_map(dst_map, confirm)
        
        # 7. Spawn existing players on session's screen
        await self.spawn_existing_map_players(session)
        
        # 8. Send new map info
        await self.send_map_info(session)
        
        # Send ground items to player on warping to new map
        await self.send_ground_items(session)
        
        # Synchronize per-player NPC visibility and replay actors
        from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(self, session, dst_map)
        await GLOBAL_PREEVENT_INTERPRETER.replay_actor_visibility(self, session, dst_map)

        # Save to database
        self.save_player_to_db(session)
        
    def get_monster_max_hp(self, level: int) -> int:
        return level * 20 + 80

    def get_monster_max_sp(self, level: int) -> int:
        return level * 8 + 20

    def get_monster_atk(self, level: int) -> int:
        return level * 3 + 5

    def get_monster_def(self, level: int) -> int:
        return level * 2 + 3

    def get_monster_stats(self, level: int, element: int) -> dict:
        total_stats = int(level * 2.5 + 10)
        
        # 1=Earth, 2=Water, 3=Fire, 4=Wind
        if element == 1: # Earth (CON heavy)
            con = int(total_stats * 0.40)
            str_val = int(total_stats * 0.20)
            int_val = int(total_stats * 0.10)
            wis_val = int(total_stats * 0.15)
            agi_val = int(total_stats * 0.15)
        elif element == 2: # Water (WIS / HP heavy)
            con = int(total_stats * 0.25)
            str_val = int(total_stats * 0.15)
            int_val = int(total_stats * 0.20)
            wis_val = int(total_stats * 0.25)
            agi_val = int(total_stats * 0.15)
        elif element == 3: # Fire (STR / INT heavy)
            con = int(total_stats * 0.15)
            str_val = int(total_stats * 0.35)
            int_val = int(total_stats * 0.30)
            wis_val = int(total_stats * 0.10)
            agi_val = int(total_stats * 0.10)
        elif element == 4: # Wind (AGI heavy)
            con = int(total_stats * 0.20)
            str_val = int(total_stats * 0.20)
            int_val = int(total_stats * 0.15)
            wis_val = int(total_stats * 0.15)
            agi_val = int(total_stats * 0.30)
        else: # Normal
            con = int(total_stats * 0.20)
            str_val = int(total_stats * 0.20)
            int_val = int(total_stats * 0.20)
            wis_val = int(total_stats * 0.20)
            agi_val = int(total_stats * 0.20)

        str_val = max(2, str_val)
        con_val = max(2, con)
        int_val = max(2, int_val)
        wis_val = max(2, wis_val)
        agi_val = max(2, agi_val)

        # ATK
        if element == 3:
            atk = int(round(level * 2.0 + str_val * 2.0))
        else:
            atk = int(round(level * 1.4 + str_val * 2.0))
            
        # DEF
        if element == 1:
            def_val = int(round(level * 8.0 + con_val * 1.75))
        else:
            def_val = int(round(level * 2.0 + con_val * 1.75))
            
        # SPD
        if element == 4:
            spd = int(round(level * 2.1 + agi_val * 2.2))
        else:
            spd = int(round(level * 1.6 + agi_val * 2.2))
            
        # MATK
        if element == 3:
            matk = int(round(level * 1.6 + int_val * 2.0))
        else:
            matk = int(round(level * 1.4 + int_val * 2.0))
            
        # MDEF
        if element == 3:
            mdef = int(round(level * 2.2 + wis_val * 2.2))
        else:
            mdef = int(round(level * 2.0 + wis_val * 2.2))

        return {
            "atk": atk,
            "def": def_val,
            "matk": matk,
            "mdef": mdef,
            "spd": spd,
            "str": str_val,
            "con": con_val,
            "int": int_val,
            "wis": wis_val,
            "agi": agi_val
        }

    # No hardcoded tables allowed. Data is fetched from ServerDataBase.db npc_data table.

    # ══════════════════════════════════════════════════════════════════════════
    # BATTLE SYSTEM  (Wireshark analizi ile doğrulanmış paket formatları)
    #
    # Sıralama (sunucudan istemciye):
    #   1. AC 8:1  – stat paketleri (savaş öncesi oyuncu statları)
    #   2. AC 11:250 – SADECE oyuncu bilgisi (role=1, ftype=2)
    #   3. AC 11:10 – savaş başla sinyali (1 byte: 0x01)
    #   4. AC 8:2  – stat paketleri (savaş sırasında)
    #   5. AC 11:5 – her monster için ayrı paket (role=1, ftype=7)
    #   Tur sırasında:
    #   6. AC 51:1 – HP/SP güncelleme: gridX(1) gridY(1) statId(1) value(uint32)
    #   7. AC 52:1 – tur bitti / sıradaki tur sinyali
    # ══════════════════════════════════════════════════════════════════════════

    async def _start_pve_battle(self, session: 'PlayerSession', click_id: int, npc_id: int,
                                override_sprite_id: int = 0):
        """PvE savaşını başlatır. Wireshark analizine göre doğru paket sırası."""
        import os, sqlite3, random

        if getattr(session, 'in_battle', False):
            logger.warning(f"[{session.char_name}] Already in battle, skipping")
            return

        # Distance check (0xa9 = 169 pixels limit)
        if click_id > 0 and click_id != 0xFFFF:
            map_npcs = self.map_npcs.get(session.map_id, [])
            map_npc_match = next((n for n in map_npcs if n.get('click_id') == click_id), None)
            if map_npc_match:
                npc_x = map_npc_match.get('x', 0)
                npc_y = map_npc_match.get('y', 0)
                if abs(session.x - npc_x) > 169 or abs(session.y - npc_y) > 169:
                    logger.warning(f"[{session.char_name}] PVE Battle blocked: NPC too far X={abs(session.x - npc_x)} Y={abs(session.y - npc_y)}")
                    return

        # ── Monster verisi ──────────────────────────────────────────────────
        # Decode the raw NPC ID to match database ID
        # Try both with and without the -9 offset to handle both town NPCs and combat NPCs
        npc_base = override_sprite_id if override_sprite_id > 0 else npc_id
        # Pre-decode client-side special template ID mappings
        client_mappings = {
            0x908e: 0x5209,
            0x9092: 0x9090,
            0x9093: 0x9091,
            0x9094: 0x9095,
            0x9096: 0x9097
        }
        mapped_npc_base = client_mappings.get(npc_base & 0xFFFF, npc_base)
        dec_no_offset = (mapped_npc_base & 0xFFFF) ^ 0x5209
        dec_with_offset = dec_no_offset - 9
        
        raw_battle_npc_id = override_sprite_id if override_sprite_id > 0 else npc_id
        
        db_path = os.path.join(os.path.dirname(__file__), 'ServerDataBase.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        db_mon = None
        
        candidates = [
            dec_no_offset,
            dec_with_offset,
            dec_no_offset + 27000,
            dec_with_offset + 27000,
            dec_no_offset + 10000,
            dec_with_offset + 10000,
            npc_base
        ]
        
        battle_npc_id = dec_no_offset
        for cand_id in candidates:
            db_mon = conn.execute("SELECT * FROM npc_data WHERE id=?", (cand_id,)).fetchone()
            if db_mon:
                battle_npc_id = cand_id
                break
            
        # 3rd fallback: map_npcs lookup
        if not db_mon:
            map_npcs = self.map_npcs.get(session.map_id, [])
            map_npc_match = next((n for n in map_npcs if n.get('click_id') == click_id), None)
            if map_npc_match:
                true_npc_id = map_npc_match.get('npc_id', 0)
                true_dec_no = (true_npc_id & 0xFFFF) ^ 0x5209
                true_dec_with = true_dec_no - 9
                true_cands = [
                    true_dec_no,
                    true_dec_with,
                    true_dec_no + 27000,
                    true_dec_with + 27000,
                    true_dec_no + 10000,
                    true_dec_with + 10000,
                    true_npc_id
                ]
                for cand_id in true_cands:
                    db_mon = conn.execute("SELECT * FROM npc_data WHERE id=?", (cand_id,)).fetchone()
                    if db_mon:
                        battle_npc_id = cand_id
                        break
                
                if not db_mon:
                    try:
                        import json
                        with open(os.path.join(os.path.dirname(__file__), 'data', 'npc.json'), 'r', encoding='utf-8') as f:
                            npc_names = json.load(f)
                        npc_name = npc_names.get(str(true_npc_id))
                        if npc_name:
                            db_mon = conn.execute("SELECT * FROM npc_data WHERE name LIKE ? ORDER BY level ASC", (npc_name + "%",)).fetchone()
                            if db_mon:
                                battle_npc_id = db_mon['id']
                    except Exception as e:
                        logger.error(f"Error in NPC name lookup fallback: {e}")
                    
        conn.close()

        if db_mon:
            mon_name = (db_mon['name'] or '').split('\x00')[0].replace('?', '').strip() or 'Monster'
            
            raw_level = safe_int(db_mon['level'], 1)
            # Decrypt level from db (subtract 92 if raw_level >= 92)
            if raw_level >= 92:
                mon_level = max(1, raw_level - 92)
            else:
                mon_level = raw_level
                
            mon_max_hp = safe_int(db_mon['hp']) if db_mon['hp'] and safe_int(db_mon['hp']) > 0 else self.get_monster_max_hp(mon_level)
            
            raw_element = safe_int(db_mon['element'], 0)
            if raw_element in (88, 89, 90, 91, 92):
                mon_element = (raw_element - 88) % 5
            else:
                mon_element = raw_element % 5
        else:
            mon_name = 'Monster'
            mon_level = 1
            mon_max_hp = self.get_monster_max_hp(mon_level)
            mon_element = 0
        mon_max_sp = self.get_monster_max_sp(mon_level)

        logger.info(f"[Battle] PvE start: {session.char_name} vs {mon_name} (id={raw_battle_npc_id} db_id={battle_npc_id} lv={mon_level} hp={mon_max_hp})")

        # ── Savaş state ─────────────────────────────────────────────────────
        battle_id = id(session)
        session.in_battle     = True
        session.pvp_battle_id = battle_id

        # Player and Monster combat stats calculation
        patk = self.get_player_atk(session)
        pdef = self.get_player_def(session)
        pmatk = self.get_player_matk(session)
        pmdef = self.get_player_mdef(session)
        pspd = self.get_player_spd(session)
        
        mstats = self.get_monster_stats(mon_level, mon_element)

        p_fighter = {
            'role': 1, 'ftype': 2,
            'id': session.char_id, 'click_id': 0,
            'x': 4, 'y': 2,
            'max_hp': session.max_hp, 'max_sp': getattr(session, 'max_sp', 100),
            'hp': session.hp,         'sp': getattr(session, 'sp', 100),
            'level': session.level,   'element': getattr(session, 'element', 0),
            'name': session.char_name, 'is_player': True,
            'atk': patk, 'def': pdef, 'matk': pmatk, 'mdef': pmdef, 'spd': pspd
        }

        # Check for active battle pet
        pet_fighter = None
        for idx, pet in enumerate(session.pets):
            if pet.get("in_battle", False):
                pet_lvl = safe_int(pet.get("level"), 1)
                pet_con = safe_int(pet.get("con"), 5)
                pet_wis = safe_int(pet.get("wis"), 5)
                pet_str = safe_int(pet.get("str"), 5)
                pet_agi = safe_int(pet.get("agi"), 5)
                pet_int = safe_int(pet.get("int"), 5)
                
                pet_max_hp = int(round(((pet_lvl ** 0.35) * pet_con * 2) + (pet_lvl * 1) + (pet_con * 2) + 180))
                pet_max_sp = int(round(((pet_lvl ** 0.3) * pet_wis * 3.2) + (pet_lvl * 1) + (pet_wis * 2) + 94))
                pet_hp = min(safe_int(pet.get("hp"), pet_max_hp), pet_max_hp)
                pet_sp = min(safe_int(pet.get("sp"), pet_max_sp), pet_max_sp)
                
                pet_atk = int(round(pet_lvl * 1.4 + pet_str * 2.0))
                pet_def = int(round(pet_lvl * 1.5 + pet_con * 1.75))
                pet_spd = int(round(pet_lvl * 1.6 + pet_agi * 2.2))
                pet_matk = int(round(pet_lvl * 1.4 + pet_int * 2.0))
                pet_mdef = int(round(pet_lvl * 2.0 + pet_wis * 2.2))
                
                # Custom name check
                pet_name = pet.get("name")
                if not pet_name:
                    pet_name = "Companion"
                    try:
                        conn = sqlite3.connect(self.static_db_path)
                        row = conn.execute("SELECT name FROM npc_data WHERE id = ?", (pet.get("pet_id"),)).fetchone()
                        conn.close()
                        if row:
                            pet_name = row[0].split(chr(0))[0].strip()
                    except Exception as e:
                        logger.error(f"[Pet Name] Error fetching: {e}")
                        
                pet_element = 0
                try:
                    conn = sqlite3.connect(self.static_db_path)
                    row = conn.execute("SELECT element FROM npc_data WHERE id = ?", (pet.get("pet_id"),)).fetchone()
                    conn.close()
                    if row:
                        raw_element = int(row[0] or 0)
                        if raw_element in (88, 89, 90, 91, 92):
                            pet_element = (raw_element - 88) % 5
                        else:
                            pet_element = raw_element % 5
                except Exception as e:
                    logger.error(f"[Pet Element] Error fetching: {e}")

                pet_fighter = {
                    'role': 5, 'ftype': 4,
                    'id': pet.get("pet_id"), 'click_id': idx, # slot index (0-based)
                    'owner_id': session.char_id,
                    'x': 3, 'y': 2,
                    'max_hp': pet_max_hp, 'max_sp': pet_max_sp,
                    'hp': pet_hp, 'sp': pet_sp,
                    'level': pet_lvl, 'element': pet_element,
                    'name': pet_name, 'is_player': False, 'is_pet': True,
                    'atk': pet_atk, 'def': pet_def, 'matk': pet_matk, 'mdef': pet_mdef, 'spd': pet_spd
                }
                break

        # Spawn multiple monsters if pet is present
        monsters = []
        if pet_fighter is not None:
            m1 = {
                'role': 1, 'ftype': 7,
                'id': raw_battle_npc_id, 'click_id': click_id,
                'db_id': battle_npc_id,
                'x': 2, 'y': 1,
                'max_hp': mon_max_hp, 'max_sp': mon_max_sp,
                'hp': mon_max_hp,     'sp': mon_max_sp,
                'level': mon_level,   'element': mon_element,
                'name': mon_name, 'is_player': False,
                'atk': mstats['atk'], 'def': mstats['def'], 'matk': mstats['matk'], 'mdef': mstats['mdef'], 'spd': mstats['spd']
            }
            m2 = {
                'role': 1, 'ftype': 7,
                'id': raw_battle_npc_id, 'click_id': click_id + 1,
                'db_id': battle_npc_id,
                'x': 2, 'y': 3,
                'max_hp': mon_max_hp, 'max_sp': mon_max_sp,
                'hp': mon_max_hp,     'sp': mon_max_sp,
                'level': mon_level,   'element': mon_element,
                'name': mon_name, 'is_player': False,
                'atk': mstats['atk'], 'def': mstats['def'], 'matk': mstats['matk'], 'mdef': mstats['mdef'], 'spd': mstats['spd']
            }
            monsters = [m1, m2]
        else:
            m1 = {
                'role': 1, 'ftype': 7,
                'id': raw_battle_npc_id, 'click_id': click_id,
                'db_id': battle_npc_id,
                'x': 2, 'y': 2,
                'max_hp': mon_max_hp, 'max_sp': mon_max_sp,
                'hp': mon_max_hp,     'sp': mon_max_sp,
                'level': mon_level,   'element': mon_element,
                'name': mon_name, 'is_player': False,
                'atk': mstats['atk'], 'def': mstats['def'], 'matk': mstats['matk'], 'mdef': mstats['mdef'], 'spd': mstats['spd']
            }
            monsters = [m1]

        battle = {
            'id': battle_id,
            'player': p_fighter,
            'pet': pet_fighter,
            'monster': monsters[0],  # backwards compatibility
            'monsters': monsters,
            'turn': 0,
            'finished': False,
            'pending_actions': {}
        }
        self.active_battles[battle_id] = battle

        # ── Paket gönderimi ──────────────────────────────────────────────────
        await self._send_battle_start(session, battle)

    async def _send_battle_start(self, session: 'PlayerSession', battle: dict):
        """
        Wireshark'tan doğrulanan savaş başlangıç paketi sırası (DÜZELTILMIŞ):
          0. AC 20:12 (battle mode enter)
          0. AC 6:2 [01]
          1. AC 8:1  stat paketleri (stat_id 0x01XX, 4-byte padding)
          2. AC 11:250 (oyuncu, 2-byte trailing pad)
          3. AC 11:10 [01] (1 byte savaş başla)
          4. AC 8:2  stat paketleri (prefix 04 01 00, 4-byte padding) for pet (if present)
          5. AC 11:5 for pet (if present)
          6. AC 11:5 for each monster
        """
        pf = battle['player']
        pet_f = battle.get('pet')

        # ── 0a. AC 20:12 – savaş modu girişi (boş payload) ─────────────────
        await session.send_packet(PacketWriter().write_8(20).write_8(12))

        # ── 0b. AC 6:2 [01] – mod değişimi sinyali ─────────────────────────
        pkt_62 = PacketWriter()
        pkt_62.write_8(6).write_8(2).write_8(1)
        await session.send_packet(pkt_62)

        bg_id = getattr(session, 'battle_bg_id', session.map_id)
        if hasattr(session, 'battle_bg_id'):
            del session.battle_bg_id
        
        # Map high map IDs (often cave/dungeons) to a valid bg_id
        if bg_id >= 10000:
            map_str = str(bg_id)
            if map_str.startswith(('11', '12', '13', '14', '15', '16')):
                bg_id = 11 # Cave BG
            else:
                bg_id = 1 # Grassland default BG
        
        p250 = PacketWriter()
        p250.write_8(11).write_8(250)
        p250.write_16(bg_id)
        p250.write_8(pf['role'])                 # role=1
        p250.write_8(pf['ftype'])                # ftype=2
        p250.write_32(pf['id'])
        p250.write_16(pf['click_id'])            # 0
        p250.write_32(0)                         # ownerID
        p250.write_8(pf['x'])
        p250.write_8(pf['y'])
        p250.write_32(pf['max_hp'])
        p250.write_16(min(0xFFFF, pf['max_sp']))
        p250.write_32(pf['hp'])
        p250.write_16(min(0xFFFF, pf['sp']))
        p250.write_8(min(255, pf['level']))
        p250.write_8(pf['element'])
        p250.write_8(0)                          # reborn
        p250.write_8(getattr(session, 'job', 0)) # job
        p250.write_16(0)                         # 2-byte trailing padding (Wireshark!)
        await session.send_packet(p250)
        logger.info(f"[Battle] -> {session.char_name}: 11:250 ({len(p250.buffer)}b bg={bg_id})")

        # ── 3. AC 11:10 – savaş başla (1 byte = 0x01) ──────────────────────
        p10 = PacketWriter()
        p10.write_8(11).write_8(10)
        p10.write_8(1)
        await session.send_packet(p10)

        # ── 4. AC 8:2 stat paketleri (savaş sırasında) for pet ─────────────────────
        if pet_f:
            stats_pet_8_2 = [
                (0x01cf, 0),
                (0x0119, pet_f['hp']),       # current HP
                (0x01d0, 0),
                (0x011a, pet_f['sp']),       # current SP
                (0x01d2, 0),
                (0x0129, pet_f['atk']),
                (0x01d3, pet_f['level']),
                (0x012a, pet_f['spd']),
                (0x01d6, 0),
                (0x012d, pet_f['def']),
                (0x01d7, 0),
                (0x012b, pet_f['matk']),
                (0x01d8, 0),
                (0x012c, pet_f['mdef']),
            ]
            for stat_id, val in stats_pet_8_2:
                pkt = PacketWriter()
                pkt.write_8(8).write_8(2)
                pkt.write_8(pf['x']).write_8(pf['y']).write_8(0)  # player coordinate
                pkt.write_16(stat_id)
                pkt.write_32(val)
                pkt.write_32(0)
                await session.send_packet(pkt)

        # ── 5. AC 11:5 – pet spawn (role=5, ftype=4) ─────────────────────────
        if pet_f:
            p5_pet = PacketWriter()
            p5_pet.write_8(11).write_8(5)
            p5_pet.write_8(pet_f['role'])               # role=5
            p5_pet.write_8(pet_f['ftype'])              # ftype=4
            p5_pet.write_32(pet_f['id'])
            p5_pet.write_16(pet_f['click_id'])          # 0-based slot index
            p5_pet.write_32(pet_f['owner_id'])
            p5_pet.write_8(pet_f['x'])
            p5_pet.write_8(pet_f['y'])
            p5_pet.write_32(pet_f['max_hp'])
            p5_pet.write_16(min(0xFFFF, pet_f['max_sp']))
            p5_pet.write_32(pet_f['hp'])
            p5_pet.write_16(min(0xFFFF, pet_f['sp']))
            p5_pet.write_8(min(255, pet_f['level']))
            p5_pet.write_8(pet_f['element'])
            p5_pet.write_8(0)
            p5_pet.write_8(0)
            p5_pet.write_16(0)                          # 2-byte trailing padding
            await session.send_packet(p5_pet)
            logger.info(f"[Battle] -> {session.char_name}: spawned pet 11:5 ({pet_f['name']} id={pet_f['id']})")

        # ── 6. AC 11:5 – monster spawns (role=1, ftype=7) ─────────────────────────
        for mf in battle['monsters']:
            p5 = PacketWriter()
            p5.write_8(11).write_8(5)
            p5.write_8(mf['role'])               # role=1
            p5.write_8(mf['ftype'])              # ftype=7
            p5.write_32(mf['id'])
            p5.write_16(mf['click_id'])
            p5.write_32(0)                       # ownerID
            p5.write_8(mf['x'])
            p5.write_8(mf['y'])
            p5.write_32(mf['max_hp'])
            p5.write_16(min(0xFFFF, mf['max_sp']))
            p5.write_32(mf['hp'])
            p5.write_16(min(0xFFFF, mf['sp']))
            p5.write_8(min(255, mf['level']))
            p5.write_8(mf['element'])
            p5.write_8(0)                        # reborn
            p5.write_8(0)                        # job
            p5.write_16(0)                       # 2-byte trailing padding (Wireshark!)
            await session.send_packet(p5)
            logger.info(f"[Battle] -> {session.char_name}: spawned monster 11:5 ({mf['name']} id={mf['id']})")

        # ── 7. İlk tur init
        await self._send_turn_start(session, battle)

    def _build_pet_fighter(self, session, pet, idx, role, x, y):
        import sqlite3
        pet_lvl = safe_int(pet.get("level"), 1)
        pet_con = safe_int(pet.get("con"), 5)
        pet_wis = safe_int(pet.get("wis"), 5)
        pet_str = safe_int(pet.get("str"), 5)
        pet_agi = safe_int(pet.get("agi"), 5)
        pet_int = safe_int(pet.get("int"), 5)
        
        pet_max_hp = int(round(((pet_lvl ** 0.35) * pet_con * 2) + (pet_lvl * 1) + (pet_con * 2) + 180))
        pet_max_sp = int(round(((pet_lvl ** 0.3) * pet_wis * 3.2) + (pet_lvl * 1) + (pet_wis * 2) + 94))
        pet_hp = min(safe_int(pet.get("hp"), pet_max_hp), pet_max_hp)
        pet_sp = min(safe_int(pet.get("sp"), pet_max_sp), pet_max_sp)
        
        pet_atk = int(round(pet_lvl * 1.4 + pet_str * 2.0))
        pet_def = int(round(pet_lvl * 1.5 + pet_con * 1.75))
        pet_spd = int(round(pet_lvl * 1.6 + pet_agi * 2.2))
        pet_matk = int(round(pet_lvl * 1.4 + pet_int * 2.0))
        pet_mdef = int(round(pet_lvl * 2.0 + pet_wis * 2.2))
        
        pet_name = pet.get("name")
        if not pet_name:
            pet_name = "Companion"
            try:
                conn = sqlite3.connect(self.static_db_path)
                row = conn.execute("SELECT name FROM npc_data WHERE id = ?", (pet.get("pet_id"),)).fetchone()
                conn.close()
                if row:
                    pet_name = row[0].split(chr(0))[0].strip()
            except Exception as e:
                logger.error(f"[Pet Name] Error fetching: {e}")
                
        pet_element = 0
        try:
            conn = sqlite3.connect(self.static_db_path)
            row = conn.execute("SELECT element FROM npc_data WHERE id = ?", (pet.get("pet_id"),)).fetchone()
            conn.close()
            if row:
                raw_element = int(row[0] or 0)
                if raw_element in (88, 89, 90, 91, 92):
                    pet_element = (raw_element - 88) % 5
                else:
                    pet_element = raw_element % 5
        except Exception as e:
            logger.error(f"[Pet Element] Error fetching: {e}")

        return {
            'role': role, 'ftype': 4,
            'id': pet.get("pet_id"), 'click_id': idx,
            'owner_id': session.char_id,
            'x': x, 'y': y,
            'max_hp': pet_max_hp, 'max_sp': pet_max_sp,
            'hp': pet_hp, 'sp': pet_sp,
            'level': pet_lvl, 'element': pet_element,
            'name': pet_name, 'is_player': False, 'is_pet': True,
            'atk': pet_atk, 'def': pet_def, 'matk': pet_matk, 'mdef': pet_mdef, 'spd': pet_spd
        }

    async def _start_pvp_battle(self, challenger: 'PlayerSession', target: 'PlayerSession'):
        """PvP düellosunu (PK) başlatır."""
        import random, sqlite3

        if getattr(challenger, 'in_battle', False) or getattr(target, 'in_battle', False):
            logger.warning(f"[Battle] Cannot start PvP: challenger or target already in battle")
            return

        challenger.in_battle = True
        target.in_battle = True

        battle_id = id(challenger)
        challenger.pvp_battle_id = battle_id
        target.pvp_battle_id = battle_id

        # Challenger fighter details
        c_fighter = {
            'role': 1, 'ftype': 2,
            'id': challenger.char_id, 'click_id': 0,
            'x': 4, 'y': 2,
            'max_hp': challenger.max_hp, 'max_sp': getattr(challenger, 'max_sp', 100),
            'hp': challenger.hp,         'sp': getattr(challenger, 'sp', 100),
            'level': challenger.level,   'element': getattr(challenger, 'element', 0),
            'name': challenger.char_name, 'is_player': True,
            'session': challenger,
            'atk': self.get_player_atk(challenger), 'def': self.get_player_def(challenger),
            'matk': self.get_player_matk(challenger), 'mdef': self.get_player_mdef(challenger),
            'spd': self.get_player_spd(challenger)
        }

        # Target fighter details
        t_fighter = {
            'role': 2, 'ftype': 2,
            'id': target.char_id, 'click_id': 0,
            'x': 2, 'y': 2,
            'max_hp': target.max_hp, 'max_sp': getattr(target, 'max_sp', 100),
            'hp': target.hp,         'sp': getattr(target, 'sp', 100),
            'level': target.level,   'element': getattr(target, 'element', 0),
            'name': target.char_name, 'is_player': True,
            'session': target,
            'atk': self.get_player_atk(target), 'def': self.get_player_def(target),
            'matk': self.get_player_matk(target), 'mdef': self.get_player_mdef(target),
            'spd': self.get_player_spd(target)
        }

        # Check challenger pet
        c_pet_fighter = None
        for idx, pet in enumerate(challenger.pets):
            if pet.get("in_battle", False):
                c_pet_fighter = self._build_pet_fighter(challenger, pet, idx, role=5, x=3, y=2)
                break

        # Check target pet
        t_pet_fighter = None
        for idx, pet in enumerate(target.pets):
            if pet.get("in_battle", False):
                t_pet_fighter = self._build_pet_fighter(target, pet, idx, role=6, x=1, y=2)
                break

        battle = {
            'id': battle_id,
            'is_pvp': True,
            'challenger': c_fighter,
            'pet': c_pet_fighter,
            'target': t_fighter,
            'target_pet': t_pet_fighter,
            'player': c_fighter,         # Turn processing compatibility
            'monster': t_fighter,        # Turn processing compatibility
            'monsters': [t_fighter],     # Turn processing compatibility
            'turn': 0,
            'finished': False,
            'pending_actions': {}
        }
        self.active_battles[battle_id] = battle

        logger.info(f"[Battle] PvP start: {challenger.char_name} vs {target.char_name} (battle_id={battle_id})")

        # Send battle starts to both clients
        await self._send_pvp_battle_start_to_client(challenger, battle, is_challenger=True)
        await self._send_pvp_battle_start_to_client(target, battle, is_challenger=False)

    async def _send_pvp_battle_start_to_client(self, session: 'PlayerSession', battle: dict, is_challenger: bool):
        from server.network import PacketWriter
        
        # 1. AC 20:12 (battle mode enter)
        await session.send_packet(PacketWriter().write_8(20).write_8(12))

        # 2. AC 6:2 [01]
        await session.send_packet(PacketWriter().write_8(6).write_8(2).write_8(1))

        # Determine center player and opponents based on role
        if is_challenger:
            pf = battle['challenger']
            pet_f = battle.get('pet')
            opponents = []
            opponents.append(battle['target'])
            if battle.get('target_pet'):
                opponents.append(battle['target_pet'])
        else:
            pf = battle['target']
            pet_f = battle.get('target_pet')
            opponents = []
            opponents.append(battle['challenger'])
            if battle.get('pet'):
                opponents.append(battle['pet'])

        bg_id = getattr(session, 'battle_bg_id', session.map_id)
        if hasattr(session, 'battle_bg_id'):
            del session.battle_bg_id
        if bg_id >= 10000:
            bg_id = 1

        # AC 11:250 for self player
        p250 = PacketWriter()
        p250.write_8(11).write_8(250)
        p250.write_16(bg_id)
        p250.write_8(pf['role'])
        p250.write_8(pf['ftype'])
        p250.write_32(pf['id'])
        p250.write_16(pf['click_id'])
        p250.write_32(0)
        p250.write_8(pf['x'])
        p250.write_8(pf['y'])
        p250.write_32(pf['max_hp'])
        p250.write_16(min(0xFFFF, pf['max_sp']))
        p250.write_32(pf['hp'])
        p250.write_16(min(0xFFFF, pf['sp']))
        p250.write_8(min(255, pf['level']))
        p250.write_8(pf['element'])
        p250.write_8(0)
        p250.write_8(getattr(session, 'job', 0))
        p250.write_16(0)
        await session.send_packet(p250)

        # AC 11:10 [01] (combat start)
        await session.send_packet(PacketWriter().write_8(11).write_8(10).write_8(1))

        # AC 8:2 for self pet
        if pet_f:
            stats_pet_8_2 = [
                (0x01cf, 0), (0x0119, pet_f['hp']), (0x01d0, 0), (0x011a, pet_f['sp']),
                (0x01d2, 0), (0x0129, pet_f['atk']), (0x01d3, pet_f['level']),
                (0x012a, pet_f['spd']), (0x01d6, 0), (0x012d, pet_f['def']),
                (0x01d7, 0), (0x012b, pet_f['matk']), (0x01d8, 0), (0x012c, pet_f['mdef'])
            ]
            for stat_id, val in stats_pet_8_2:
                pkt = PacketWriter()
                pkt.write_8(8).write_8(2)
                pkt.write_8(pf['x']).write_8(pf['y']).write_8(0)
                pkt.write_16(stat_id)
                pkt.write_32(val)
                pkt.write_32(0)
                await session.send_packet(pkt)

            # AC 11:5 for self pet
            p5_pet = PacketWriter()
            p5_pet.write_8(11).write_8(5)
            p5_pet.write_8(pet_f['role'])
            p5_pet.write_8(pet_f['ftype'])
            p5_pet.write_32(pet_f['id'])
            p5_pet.write_16(pet_f['click_id'])
            p5_pet.write_32(pet_f['owner_id'])
            p5_pet.write_8(pet_f['x'])
            p5_pet.write_8(pet_f['y'])
            p5_pet.write_32(pet_f['max_hp'])
            p5_pet.write_16(min(0xFFFF, pet_f['max_sp']))
            p5_pet.write_32(pet_f['hp'])
            p5_pet.write_16(min(0xFFFF, pet_f['sp']))
            p5_pet.write_8(min(255, pet_f['level']))
            p5_pet.write_8(pet_f['element'])
            p5_pet.write_8(0)
            p5_pet.write_8(0)
            p5_pet.write_16(0)
            await session.send_packet(p5_pet)

        # AC 11:5 for opponents (target/challenger and their pet)
        for op in opponents:
            p5 = PacketWriter()
            p5.write_8(11).write_8(5)
            p5.write_8(op['role'])
            p5.write_8(op['ftype'])
            p5.write_32(op['id'])
            p5.write_16(op['click_id'])
            p5.write_32(op.get('owner_id', 0))
            p5.write_8(op['x'])
            p5.write_8(op['y'])
            p5.write_32(op['max_hp'])
            p5.write_16(min(0xFFFF, op['max_sp']))
            p5.write_32(op['hp'])
            p5.write_16(min(0xFFFF, op['sp']))
            p5.write_8(min(255, op['level']))
            p5.write_8(op['element'])
            p5.write_8(0)
            p5.write_8(0)
            p5.write_16(0)
            await session.send_packet(p5)

        # AC 20:9 (end of spawns / battle ready)
        await session.send_packet(PacketWriter().write_8(20).write_8(9))

        # Turn start
        await self._send_pvp_turn_start(session, battle, is_challenger)

    async def _send_pvp_turn_start(self, session: 'PlayerSession', battle: dict, is_challenger: bool):
        from server.network import PacketWriter
        
        if is_challenger:
            pf = battle['challenger']
            pet_f = battle.get('pet')
            tf = battle['target']
            tpet_f = battle.get('target_pet')
        else:
            pf = battle['target']
            pet_f = battle.get('target_pet')
            tf = battle['challenger']
            tpet_f = battle.get('pet')

        # Sync HP/SP
        sync_list = [
            (pf['x'], pf['y'], pf['hp'], 0x19),
            (pf['x'], pf['y'], pf['sp'], 0x1a),
        ]
        if pet_f and pet_f['hp'] > 0:
            sync_list.append((pet_f['x'], pet_f['y'], pet_f['hp'], 0x19))
            sync_list.append((pet_f['x'], pet_f['y'], pet_f['sp'], 0x1a))
        
        sync_list.append((tf['x'], tf['y'], tf['hp'], 0x19))
        sync_list.append((tf['x'], tf['y'], tf['sp'], 0x1a))
        if tpet_f and tpet_f['hp'] > 0:
            sync_list.append((tpet_f['x'], tpet_f['y'], tpet_f['hp'], 0x19))
            sync_list.append((tpet_f['x'], tpet_f['y'], tpet_f['sp'], 0x1a))

        for x, y, val, stat in sync_list:
            pkt = PacketWriter()
            pkt.write_8(51).write_8(1)
            pkt.write_8(x).write_8(y).write_8(stat).write_32(val)
            await session.send_packet(pkt)

        # Give turn to self player (and their pet if active)
        await session.send_packet(
            PacketWriter().write_8(50).write_8(6).write_8(pf['x']).write_8(pf['y']).write_8(0)
        )
        if pet_f and pet_f['hp'] > 0:
            await session.send_packet(
                PacketWriter().write_8(50).write_8(6).write_8(pet_f['x']).write_8(pet_f['y']).write_8(0)
            )

        # Show combat menu
        await session.send_packet(PacketWriter().write_8(52).write_8(1))

    async def _resolve_pvp_turn(self, session: 'PlayerSession', battle: dict):
        import random, asyncio
        from server.network import PacketWriter

        challenger = battle['challenger']['session']
        target = battle['target']['session']

        battle['turn'] += 1
        turn = battle['turn']

        # Determine all active fighters
        fighters = [battle['challenger'], battle['target']]
        if battle.get('pet') and battle['pet']['hp'] > 0:
            fighters.append(battle['pet'])
        if battle.get('target_pet') and battle['target_pet']['hp'] > 0:
            fighters.append(battle['target_pet'])

        # Sort fighters by Speed (SPD) for turn order!
        fighters.sort(key=lambda f: f.get('spd', 0), reverse=True)

        # Process actions
        combined_anim = PacketWriter()
        combined_anim.write_8(50).write_8(1)
        sync_packets = []

        for actor in fighters:
            if actor['hp'] <= 0:
                continue

            act = battle['pending_actions'].get((actor['x'], actor['y']))
            if not act:
                continue

            action_name = act['action']
            skill_id = act['skill_id']
            dst_x = act['dst_x']
            dst_y = act['dst_y']

            # Find target
            target_fighter = None
            for f in fighters:
                if f['x'] == dst_x and f['y'] == dst_y and f['hp'] > 0:
                    target_fighter = f
                    break

            if not target_fighter and action_name != 'defend':
                # Target dead or invalid, auto select opponent
                opponents = [f for f in fighters if f['role'] != actor['role'] and f['hp'] > 0]
                if opponents:
                    target_fighter = random.choice(opponents)

            if not target_fighter and action_name != 'defend':
                continue

            # Skill processing
            def get_skill_info(sid, actor_el):
                if hasattr(self, 'parsed_skills') and sid in self.parsed_skills:
                    return self.parsed_skills[sid]
                return ("Attack", actor_el, False, 1.0, False, 0)

            skill_name, skill_elem, is_magical, multiplier, is_heal, sp_cost = get_skill_info(skill_id, actor['element'])

            # Deduct SP
            if sp_cost > 0:
                actor['sp'] = max(0, actor['sp'] - sp_cost)
                if actor.get('is_player'):
                    actor['session'].sp = actor['sp']
                elif actor.get('is_pet'):
                    owner_session = challenger if actor['role'] == 5 else target
                    for p in owner_session.pets:
                        if p.get("pet_id") == actor['id']:
                            p['sp'] = actor['sp']
                            break
                sync_packets.append((actor['x'], actor['y'], actor['sp'], 0x1a))

            if is_heal:
                heal_val = int(round(actor['matk'] * multiplier))
                target_fighter['hp'] = min(target_fighter['max_hp'], target_fighter['hp'] + heal_val)
                if target_fighter.get('is_player'):
                    target_fighter['session'].hp = target_fighter['hp']
                elif target_fighter.get('is_pet'):
                    owner_session = challenger if target_fighter['role'] == 5 else target
                    for p in owner_session.pets:
                        if p.get("pet_id") == target_fighter['id']:
                            p['hp'] = target_fighter['hp']
                            break
                
                combined_anim.write_8(0x11).write_8(0x00)
                combined_anim.write_8(actor['x']).write_8(actor['y'])
                combined_anim.write_16(skill_id)
                combined_anim.write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(target_fighter['x']).write_8(target_fighter['y'])
                combined_anim.write_8(1).write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(0x19)
                combined_anim.write_32(heal_val)
                combined_anim.write_8(1)

                sync_packets.append((target_fighter['x'], target_fighter['y'], target_fighter['hp'], 0x19))
            else:
                # Attack
                hitter_element = skill_elem if skill_id != 10001 else actor['element']
                best_atk = max(actor['atk'], actor['matk'])
                def_stat = target_fighter['def']
                target_element = target_fighter['element']

                modified_atk = int(round(best_atk * multiplier))
                if skill_id != 10001:
                    modified_atk += int(15 * multiplier)

                def get_element_correction(hitter_element: int, target_element: int) -> float:
                    if hitter_element == 3:
                        if target_element == 2: return 0.6
                        if target_element == 4: return 1.5
                    elif hitter_element == 1:
                        if target_element == 2: return 1.7
                        if target_element == 4: return 0.6
                    elif hitter_element == 2:
                        if target_element == 3: return 1.7
                        if target_element == 1: return 0.6
                    elif hitter_element == 4:
                        if target_element == 3: return 0.4
                        if target_element == 1: return 1.7
                    elif hitter_element == 0:
                        if target_element in (1, 2, 3, 4): return 1.3
                    return 1.0

                def calculate_atk_damage(atk: int, def_val: int, hitter_element: int, target_element: int) -> int:
                    element_corr = get_element_correction(hitter_element, target_element)
                    rand_val = 0.9 + (random.random() * 0.2)
                    base_dmg = atk * (atk / max(1, atk + def_val/2.0))
                    if atk < 50:
                        base_dmg += atk * 0.5
                    est = base_dmg * element_corr * rand_val
                    return max(1, int(round(est)))

                dmg = calculate_atk_damage(modified_atk, def_stat, hitter_element, target_element)

                # Defend logic
                target_acted = battle['pending_actions'].get((target_fighter['x'], target_fighter['y']))
                if target_acted and target_acted['action'] == 'defend':
                    dmg = max(1, dmg // 2)

                target_fighter['hp'] = max(0, target_fighter['hp'] - dmg)
                if target_fighter.get('is_player'):
                    target_fighter['session'].hp = target_fighter['hp']
                elif target_fighter.get('is_pet'):
                    owner_session = challenger if target_fighter['role'] == 5 else target
                    for p in owner_session.pets:
                        if p.get("pet_id") == target_fighter['id']:
                            p['hp'] = target_fighter['hp']
                            break

                combined_anim.write_8(0x11).write_8(0x00)
                combined_anim.write_8(actor['x']).write_8(actor['y'])
                combined_anim.write_16(skill_id)
                combined_anim.write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(target_fighter['x']).write_8(target_fighter['y'])
                combined_anim.write_8(1).write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(0x19)
                combined_anim.write_32(dmg)
                combined_anim.write_8(1)

                sync_packets.append((target_fighter['x'], target_fighter['y'], target_fighter['hp'], 0x19))

        # Clear turn pending actions
        battle['pending_actions'] = {}

        # Send action notifications (AC 53 Sub 5) to BOTH players
        for actor in fighters:
            pkt_notify = PacketWriter().write_8(53).write_8(5).write_8(actor['x']).write_8(actor['y'])
            await challenger.send_packet(pkt_notify)
            await target.send_packet(pkt_notify)

        # Broadcast combined animations to both
        if len(combined_anim.buffer) > 2:
            await challenger.send_packet(combined_anim)
            await target.send_packet(combined_anim)

        # Sync HP/SP to both
        for x, y, val, stat in sync_packets:
            pkt_sync = PacketWriter().write_8(51).write_8(1).write_8(x).write_8(y).write_8(stat).write_32(val)
            await challenger.send_packet(pkt_sync)
            await target.send_packet(pkt_sync)

        # Wait for animations
        await asyncio.sleep(2.0 if len(fighters) <= 2 else 3.8)

        # Save DB
        self.save_player_to_db(challenger)
        self.save_player_to_db(target)

        # Check battle end conditions
        c_dead = battle['challenger']['hp'] <= 0
        t_dead = battle['target']['hp'] <= 0

        if c_dead or t_dead:
            # End battle
            await self._end_pvp_battle(battle, challenger_won=t_dead)
        else:
            # Start next turn
            await self._send_pvp_turn_start(challenger, battle, is_challenger=True)
            await self._send_pvp_turn_start(target, battle, is_challenger=False)

    async def _end_pvp_battle(self, battle: dict, challenger_won: bool):
        from server.network import PacketWriter
        
        challenger = battle['challenger']['session']
        target = battle['target']['session']

        # 8. AC 11:250 (failure/finish/result) -> Conclude battle
        p110 = PacketWriter().write_8(11).write_8(0).write_32(challenger.char_id).write_16(0)
        await challenger.send_packet(p110)
        await target.send_packet(p110)

        # 9. AC 11:1 [x, y, 0]
        await challenger.send_packet(
            PacketWriter().write_8(11).write_8(1).write_8(battle['challenger']['x']).write_8(battle['challenger']['y']).write_8(0)
        )
        await target.send_packet(
            PacketWriter().write_8(11).write_8(1).write_8(battle['target']['x']).write_8(battle['target']['y']).write_8(0)
        )

        battle['finished'] = True
        bid = battle['id']
        if bid in self.active_battles:
            del self.active_battles[bid]

        challenger.in_battle = False
        challenger.pvp_battle_id = None
        target.in_battle = False
        target.pvp_battle_id = None
        
        logger.info(f"[Battle] PvP finished: challenger_won={challenger_won}")

    async def _send_turn_start(self, session: 'PlayerSession', battle: dict):
        """
        Savaş başladıktan sonra tüm savaşçıların HP/SP'ini gönder
        ve AC=50:6 ile oyuncuya sırayı ver.
        """
        pf = battle['player']
        pet_f = battle.get('pet')
        
        # HP/SP sync tüm savaşçılar
        sync_list = [
            (pf['x'], pf['y'], pf['hp'],  0x19),
            (pf['x'], pf['y'], pf['sp'],  0x1a),
        ]
        if pet_f and pet_f['hp'] > 0:
            sync_list.append((pet_f['x'], pet_f['y'], pet_f['hp'], 0x19))
            sync_list.append((pet_f['x'], pet_f['y'], pet_f['sp'], 0x1a))
            
        for mf in battle['monsters']:
            if mf['hp'] > 0:
                sync_list.append((mf['x'], mf['y'], mf['hp'],  0x19))
                sync_list.append((mf['x'], mf['y'], mf['sp'],  0x1a))
                
        for x, y, val, stat in sync_list:
            pkt = PacketWriter()
            pkt.write_8(51).write_8(1)
            pkt.write_8(x).write_8(y).write_8(stat).write_32(val)
            await session.send_packet(pkt)
            
        # Hangi savaşçıların sırası olduğunu bildir
        await session.send_packet(
            PacketWriter().write_8(50).write_8(6).write_8(pf['x']).write_8(pf['y']).write_8(0)
        )
        if pet_f and pet_f['hp'] > 0:
            await session.send_packet(
                PacketWriter().write_8(50).write_8(6).write_8(pet_f['x']).write_8(pet_f['y']).write_8(0)
            )

        # ── 52:1 – Oyuncuya kontrolü ver (savaş menüsünü göster) ────────────────
        await session.send_packet(
            PacketWriter().write_8(52).write_8(1)
        )

    async def _resolve_pve_turn(self, session: 'PlayerSession', battle: dict):
        """
        PvE turünü çözer. Düzeltìlmiş paket formatı.
        Desteklenenler: oyuncu ve petin ortak tur eylemleri, çoklu monsterlar.
        """
        import random

        pf = battle['player']
        pet_f = battle.get('pet')
        monsters = battle['monsters']
        battle['turn'] += 1
        turn = battle['turn']

        def get_element_correction(hitter_element: int, target_element: int) -> float:
            if hitter_element == 3: # Fire
                if target_element == 2: return 0.6
                if target_element == 4: return 1.5
            elif hitter_element == 1: # Earth
                if target_element == 2: return 1.7
                if target_element == 4: return 0.6
            elif hitter_element == 2: # Water
                if target_element == 3: return 1.7
                if target_element == 1: return 0.6
            elif hitter_element == 4: # Wind
                if target_element == 3: return 0.4
                if target_element == 1: return 1.7
            elif hitter_element == 0: # Normal
                if target_element in (1, 2, 3, 4): return 1.3
            return 1.0

        def calculate_atk_damage(atk: int, def_val: int, hitter_element: int, target_element: int) -> int:
            element_corr = get_element_correction(hitter_element, target_element)
            rand_val = 0.9 + (random.random() * 0.2) # 0.9 to 1.1
            base_dmg = atk * (atk / max(1, atk + def_val/2.0))
            if atk < 50:
                base_dmg += atk * 0.5
            est = base_dmg * element_corr * rand_val
            return max(1, int(round(est)))

        def _hp_pkt(x, y, val):
            p = PacketWriter()
            p.write_8(51).write_8(1)
            p.write_8(x).write_8(y).write_8(0x19).write_32(val)
            return p

        def _sp_pkt(x, y, val):
            p = PacketWriter()
            p.write_8(51).write_8(1)
            p.write_8(x).write_8(y).write_8(0x1a).write_32(val)
            return p

        # Collect actions
        # Collect actions
        actions_to_process = []
        p_act = battle['pending_actions'].get((4, 2))
        if p_act and pf['hp'] > 0:
            actions_to_process.append((pf, p_act))
            
        if pet_f and pet_f['hp'] > 0:
            pet_act = battle['pending_actions'].get((3, 2))
            if pet_act:
                actions_to_process.append((pet_f, pet_act))

        # Clear pending actions
        battle['pending_actions'] = {}

        # Reset defend states for this turn
        pf['is_defending'] = False
        if pet_f:
            pet_f['is_defending'] = False

        # Sort by Speed (SPD) descending for turn execution order
        actions_to_process.sort(key=lambda item: item[0].get('spd', 0), reverse=True)

        combined_anim = PacketWriter()
        combined_anim.write_8(50).write_8(1)
        sync_packets = []

        # Process each player/pet action
        for actor, act in actions_to_process:
            actor_name = actor['name']
            action_name = act['action']
            skill_id = act['skill_id']
            dst_x = act['dst_x']
            dst_y = act['dst_y']

            # ── 1. FLEE ACTION (Skill 60041 / 0xea89) ──
            if action_name == 'flee' or skill_id == 60041:
                logger.info(f"[Battle] T{turn}: {actor_name} flees from combat!")
                # AC 50:6 action execution signal
                await session.send_packet(
                    PacketWriter().write_8(50).write_8(6).write_8(actor['x']).write_8(actor['y']).write_8(0)
                )
                # AC 50:1 Flee animation
                p_flee = PacketWriter()
                p_flee.write_8(50).write_8(1)
                p_flee.write_8(0x11).write_8(0x00)
                p_flee.write_8(actor['x']).write_8(actor['y'])
                p_flee.write_16(60041)
                p_flee.write_8(0).write_8(1)
                p_flee.write_8(actor['x']).write_8(actor['y'])
                p_flee.write_8(1).write_8(0).write_8(1)
                p_flee.write_8(0).write_32(0).write_8(1)
                await session.send_packet(p_flee)
                await asyncio.sleep(1.5)
                await self._end_battle(session, battle, won=False, fled=True)
                return

            # ── 2. DEFEND / SHIELD ACTION (Skill 60021 / 0xea75) ──
            if action_name == 'defend' or skill_id == 60021:
                actor['is_defending'] = True
                logger.info(f"[Battle] T{turn}: {actor_name} enters defensive stance (50% damage reduction).")
                continue

            # Find target monster
            target_mon = None
            for m in monsters:
                if m['x'] == dst_x and m['y'] == dst_y and m['hp'] > 0:
                    target_mon = m
                    break
            if not target_mon:
                for m in monsters:
                    if m['hp'] > 0:
                        target_mon = m
                        break

            if not target_mon:
                continue

            # ── 3. PET CAPTURE ACTION (Skill 10008 / 0x2718) ──
            if action_name == 'capture' or skill_id == 10008:
                logger.info(f"[Battle] T{turn}: {actor_name} attempts to capture {target_mon['name']} at ({target_mon['x']},{target_mon['y']}).")
                # AC 50:6 action execution signal
                await session.send_packet(
                    PacketWriter().write_8(50).write_8(6).write_8(actor['x']).write_8(actor['y']).write_8(0)
                )
                # AC 50:1 Capture animation
                p_cap = PacketWriter()
                p_cap.write_8(50).write_8(1)
                p_cap.write_8(0x11).write_8(0x00)
                p_cap.write_8(actor['x']).write_8(actor['y'])
                p_cap.write_16(10008)
                p_cap.write_8(0).write_8(1)
                p_cap.write_8(target_mon['x']).write_8(target_mon['y'])
                p_cap.write_8(1).write_8(0).write_8(1)
                p_cap.write_8(0).write_32(0).write_8(1)
                await session.send_packet(p_cap)
                await asyncio.sleep(2.0)

                # Roll catch success via battle engine
                from server.battle_engine import GLOBAL_BATTLE_ENGINE
                caught = GLOBAL_BATTLE_ENGINE.roll_catch_success(
                    actor.get('level', 1),
                    target_mon.get('hp', 1),
                    target_mon.get('max_hp', 100),
                    target_mon.get('level', 1)
                )

                if caught:
                    logger.info(f"[Battle] T{turn}: Successfully captured {target_mon['name']}!")
                    # AC 11:4 - Authentic Catch Success Packet: [11, 4, 2, mon_id (4 bytes), 00 00, 01]
                    p11_4 = PacketWriter()
                    p11_4.write_8(11).write_8(4).write_8(2)
                    p11_4.write_32(target_mon['id'])
                    p11_4.write_16(0)
                    p11_4.write_8(1)
                    await session.send_packet(p11_4)

                    # Add pet to player's companions
                    pet_entry = {
                        'pet_id': target_mon['id'],
                        'name': target_mon.get('name', 'Pet'),
                        'level': target_mon.get('level', 1),
                        'element': target_mon.get('element', 0),
                        'hp': target_mon.get('max_hp', 100),
                        'max_hp': target_mon.get('max_hp', 100),
                        'sp': target_mon.get('max_sp', 50),
                        'max_sp': target_mon.get('max_sp', 50),
                        'in_battle': False,
                        'str': target_mon.get('atk', 10) // 2,
                        'con': target_mon.get('def', 10) // 2,
                        'int': target_mon.get('matk', 10) // 2,
                        'wis': target_mon.get('mdef', 10) // 2,
                        'agi': target_mon.get('spd', 10) // 2,
                        'exp': 0,
                        'potential': 0
                    }
                    if not hasattr(session, 'pets') or session.pets is None:
                        session.pets = []
                    session.pets.append(pet_entry)
                    self.save_player_to_db(session)

                    # Send notification & refresh pet list
                    await session.send_packet(
                        PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Successfully caught {target_mon['name']}!"
                        )
                    )
                    await self.send_pet_list(session)

                    # Mark monster as captured & remove from grid
                    target_mon['hp'] = 0
                    target_mon['captured'] = True
                    await session.send_packet(
                        PacketWriter().write_8(53).write_8(1).write_8(target_mon['x']).write_8(target_mon['y']).write_8(1).write_8(0).write_8(0)
                    )
                    await session.send_packet(
                        PacketWriter().write_8(53).write_8(3).write_8(target_mon['x']).write_8(target_mon['y'])
                    )

                    # If all monsters captured or dead, end battle with victory
                    if all(m['hp'] <= 0 for m in monsters):
                        await self._end_battle(session, battle, won=True)
                        return
                else:
                    logger.info(f"[Battle] T{turn}: Failed to capture {target_mon['name']}.")
                    await session.send_packet(
                        PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Failed to capture {target_mon['name']}!"
                        )
                    )
                continue

            # ── 4. ATTACK / SKILL ACTION ──
            # Skill lookup
            def get_skill_info(sid, actor_el):
                if hasattr(self, 'parsed_skills') and sid in self.parsed_skills:
                    return self.parsed_skills[sid]
                return ("Attack", actor_el, False, 1.0, False, 0)

            skill_name, skill_elem, is_magical, multiplier, is_heal, sp_cost = get_skill_info(skill_id, actor['element'])

            # SP deduction
            if sp_cost > 0:
                actor['sp'] = max(0, actor['sp'] - sp_cost)
                if actor.get('is_player'):
                    session.sp = actor['sp']
                elif actor.get('is_pet'):
                    for p in session.pets:
                        if p.get("pet_id") == actor['id']:
                            p['sp'] = actor['sp']
                            break
                sync_packets.append((actor['x'], actor['y'], actor['sp'], 0x1a))

            # Send AC 50:6 action execution signal
            await session.send_packet(
                PacketWriter().write_8(50).write_8(6).write_8(actor['x']).write_8(actor['y']).write_8(0)
            )

            if is_heal:
                heal_val = int(round(actor['matk'] * multiplier))
                actor['hp'] = min(actor['max_hp'], actor['hp'] + heal_val)
                if actor.get('is_player'):
                    session.hp = actor['hp']
                elif actor.get('is_pet'):
                    for p in session.pets:
                        if p.get("pet_id") == actor['id']:
                            p['hp'] = actor['hp']
                            break
                logger.info(f"[Battle] T{turn}: {actor_name} heals for {heal_val} HP.")

                # 19 byte animation block
                combined_anim.write_8(0x11).write_8(0x00)
                combined_anim.write_8(actor['x']).write_8(actor['y'])
                combined_anim.write_16(skill_id)
                combined_anim.write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(actor['x']).write_8(actor['y'])
                combined_anim.write_8(1).write_8(0)
                combined_anim.write_8(1)
                combined_anim.write_8(0x19)
                combined_anim.write_32(heal_val)
                combined_anim.write_8(1)

                sync_packets.append((actor['x'], actor['y'], actor['hp'], 0x19))
            else:
                # Attack/Damage
                hitter_element = skill_elem if skill_id != 10001 else actor['element']
                best_atk = max(actor['atk'], actor['matk'])
                def_stat = target_mon['def'] if target_mon else 5
                target_element = target_mon['element'] if target_mon else 0
                
                modified_atk = int(round(best_atk * multiplier))
                if skill_id != 10001:
                    modified_atk += int(15 * multiplier)

                dmg = calculate_atk_damage(modified_atk, def_stat, hitter_element, target_element)

                if target_mon:
                    target_mon['hp'] = max(0, target_mon['hp'] - dmg)
                    logger.info(f"[Battle] T{turn}: {actor_name} -> {target_mon['name']} ({target_mon['x']},{target_mon['y']}): {dmg} dmg. Target HP: {target_mon['hp']}/{target_mon['max_hp']}")

                    combined_anim.write_8(0x11).write_8(0x00)
                    combined_anim.write_8(actor['x']).write_8(actor['y'])
                    combined_anim.write_16(skill_id)
                    combined_anim.write_8(0)
                    combined_anim.write_8(1)
                    combined_anim.write_8(target_mon['x']).write_8(target_mon['y'])
                    combined_anim.write_8(1).write_8(0)
                    combined_anim.write_8(1)
                    combined_anim.write_8(0x19)
                    combined_anim.write_32(dmg)
                    combined_anim.write_8(1)

                    sync_packets.append((target_mon['x'], target_mon['y'], target_mon['hp'], 0x19))

                    # If monster was defeated, remove from combat grid
                    if target_mon['hp'] <= 0:
                        await session.send_packet(
                            PacketWriter().write_8(53).write_8(1).write_8(target_mon['x']).write_8(target_mon['y']).write_8(1).write_8(0).write_8(0)
                        )
                        await session.send_packet(
                            PacketWriter().write_8(53).write_8(3).write_8(target_mon['x']).write_8(target_mon['y'])
                        )

        # Send combined attack/heal animations
        if len(combined_anim.buffer) > 2:
            await session.send_packet(combined_anim)

        # Sync HP/SP
        for x, y, val, stat in sync_packets:
            await session.send_packet(
                PacketWriter().write_8(51).write_8(1).write_8(x).write_8(y).write_8(stat).write_32(val)
            )

        # Wait for animations to display
        if len(combined_anim.buffer) > 2:
            await asyncio.sleep(2.0 if len(actions_to_process) == 1 else 3.5)

        # Save DB
        self.save_player_to_db(session)

        # Check if all monsters dead
        all_monsters_dead = all(m['hp'] <= 0 for m in monsters)
        if all_monsters_dead:
            await self._end_battle(session, battle, won=True)
            return

        # ── Monsters Counter-Attack ─────────────────────────────────────────
        for mf in monsters:
            if mf['hp'] <= 0:
                continue

            # Select target
            targets = []
            if pf['hp'] > 0:
                targets.append(pf)
            if pet_f and pet_f['hp'] > 0:
                targets.append(pet_f)

            if not targets:
                break

            target = random.choice(targets)
            target_name = target['name']

            # 30% chance for monster to use elemental skill if they have enough SP
            skill_id = 10001
            skill_elem = mf['element']
            multiplier = 1.0
            sp_cost = 0
            
            if random.random() < 0.3 and mf.get('sp', 0) >= 15:
                if mf['element'] == 1:
                    skill_id = random.choice([15085, 30113])
                elif mf['element'] == 2:
                    skill_id = random.choice([15091, 30079])
                elif mf['element'] == 3:
                    skill_id = random.choice([11016, 30112])
                elif mf['element'] == 4:
                    skill_id = random.choice([11007, 30111])
                
                # Fetch skill info if available
                if hasattr(self, 'parsed_skills') and skill_id in self.parsed_skills:
                    _, skill_elem, _, multiplier, _, sp_cost = self.parsed_skills[skill_id]
                else:
                    multiplier = 1.3
                    sp_cost = 10

            if sp_cost > 0:
                mf['sp'] = max(0, mf['sp'] - sp_cost)

            hitter_element = skill_elem if skill_id != 10001 else mf['element']
            best_atk = max(mf['atk'], mf['matk'])
            modified_atk = int(round(best_atk * multiplier))
            if skill_id != 10001:
                modified_atk += int(15 * multiplier)

            dmg_to_target = calculate_atk_damage(modified_atk, target['def'], hitter_element, target['element'])
            
            # Check if target defended in this turn (50% reduction + guarded hit flag)
            target_defended = target.get('is_defending', False)
            if target_defended:
                dmg_to_target = max(1, dmg_to_target // 2)

            target['hp'] = max(0, target['hp'] - dmg_to_target)
            
            if target.get('is_player'):
                session.hp = target['hp']
            elif target.get('is_pet'):
                for p in session.pets:
                    if p.get("pet_id") == target['id']:
                        p['hp'] = target['hp']
                        break

            logger.info(f"[Battle] T{turn}: {mf['name']} -> {target_name} using skill={skill_id}: {dmg_to_target} dmg. Target HP: {target['hp']}/{target['max_hp']} (Defended: {target_defended})")

            # AC 50:6 – monster action execution signal
            await session.send_packet(
                PacketWriter().write_8(50).write_8(6).write_8(mf['x']).write_8(mf['y']).write_8(0)
            )

            # AC 50:1 – monster animation (with guarded flag if defended)
            is_defended_flag = 1 if target_defended else 0
            p_manim = PacketWriter()
            p_manim.write_8(50).write_8(1)
            p_manim.write_8(0x11).write_8(0x00)
            p_manim.write_8(mf['x']).write_8(mf['y'])
            p_manim.write_16(skill_id)
            p_manim.write_8(0).write_8(1)
            p_manim.write_8(target['x']).write_8(target['y'])
            p_manim.write_8(1).write_8(is_defended_flag).write_8(1)
            p_manim.write_8(0x19)
            p_manim.write_32(dmg_to_target)
            p_manim.write_8(1)
            await session.send_packet(p_manim)

            # AC 51:1 – target HP sync & monster SP sync
            await session.send_packet(
                PacketWriter().write_8(51).write_8(1).write_8(target['x']).write_8(target['y']).write_8(0x19).write_32(target['hp'])
            )
            if sp_cost > 0:
                await session.send_packet(
                    PacketWriter().write_8(51).write_8(1).write_8(mf['x']).write_8(mf['y']).write_8(0x1a).write_32(mf['sp'])
                )

            # Delay to let animation play
            await asyncio.sleep(1.4)

            # Check if player dead
            if pf['hp'] <= 0:
                await self._end_battle(session, battle, won=False)
                return

        # ── Sonraki Tur: HP/SP Sync & AC 52:1 (20s Round Timer) ───────────────────
        for stat, val in [(0x19, pf['hp']), (0x1a, pf['sp'])]:
            await session.send_packet(
                PacketWriter().write_8(51).write_8(1).write_8(pf['x']).write_8(pf['y']).write_8(stat).write_32(val)
            )
        if pet_f and pet_f['hp'] > 0:
            for stat, val in [(0x19, pet_f['hp']), (0x1a, pet_f['sp'])]:
                await session.send_packet(
                    PacketWriter().write_8(51).write_8(1).write_8(pet_f['x']).write_8(pet_f['y']).write_8(stat).write_32(val)
                )
        for mf in monsters:
            if mf['hp'] > 0:
                for stat, val in [(0x19, mf['hp']), (0x1a, mf['sp'])]:
                    await session.send_packet(
                        PacketWriter().write_8(51).write_8(1).write_8(mf['x']).write_8(mf['y']).write_8(stat).write_32(val)
                    )

        await session.send_packet(
            PacketWriter().write_8(52).write_8(1)
        )

    async def _do_flee(self, session: 'PlayerSession', battle: dict):
        """Kaçma işlemi: Her zaman başarılı (kullanıcı isteği üzerine)."""
        pf = battle['player']
        
        # 1. AC 53:5 - Action notification
        await session.send_packet(
            PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
        )
        
        # 2. AC 50:1 - Flee animation (skill 60041, source/target = player, no damage)
        p_anim = PacketWriter()
        p_anim.write_8(50).write_8(1)
        p_anim.write_8(0x11).write_8(0x00)          # unk header
        p_anim.write_8(pf['x']).write_8(pf['y'])    # source
        p_anim.write_16(60041)                       # Flee skill ID
        p_anim.write_8(0)                            # flag
        p_anim.write_8(1)                            # hit count
        p_anim.write_8(pf['x']).write_8(pf['y'])    # target
        p_anim.write_8(1).write_8(0).write_8(1)      # flags + is_hit
        p_anim.write_8(0)                            # stat_id (none)
        p_anim.write_32(0)                           # value
        p_anim.write_8(1)                            # final flag
        await session.send_packet(p_anim)
        
        # 3. Wait for client to show escape animation
        await asyncio.sleep(2.0)
        
        await self._end_battle(session, battle, won=False, fled=True)

    async def _end_battle(self, session: 'PlayerSession', battle: dict,
                          won: bool = False, fled: bool = False):
        """
        Savaşı sonlandırır ve ödülleri dağıtır.
        """
        pf = battle['player']
        pet_f = battle.get('pet')
        monsters = battle['monsters']
        primary_mon = monsters[0]

        # 1. Oyuncunun son HP ve SP'ı
        for stat, val in [(0x19, pf['hp']), (0x1a, pf['sp'])]:
            p = PacketWriter()
            p.write_8(51).write_8(1)
            p.write_8(pf['x']).write_8(pf['y']).write_8(stat).write_32(val)
            await session.send_packet(p)

        # Petin son HP ve SP'ı
        if pet_f:
            for stat, val in [(0x19, pet_f['hp']), (0x1a, pet_f['sp'])]:
                p = PacketWriter()
                p.write_8(51).write_8(1)
                p.write_8(pet_f['x']).write_8(pet_f['y']).write_8(stat).write_32(val)
                await session.send_packet(p)

        # 2. Monster'ların son HP'i = 0 (kesin olarak göster)
        if won:
            for mf in monsters:
                p = PacketWriter()
                p.write_8(51).write_8(1)
                p.write_8(mf['x']).write_8(mf['y']).write_8(0x19).write_32(0)
                await session.send_packet(p)

        # 3. Eşya Düşme Mantığı (Drop Item Logic)
        dropped_item_id = 0
        dropped_amount = 0
        if won:
            monster_id_str = str(primary_mon.get('db_id', 0))
            monster_name = (primary_mon.get('name') or "").lower()
            
            drop_rules = []
            if monster_id_str in self.drop_tables:
                drop_rules = self.drop_tables[monster_id_str]
            else:
                resolved_id = None
                try:
                    conn = sqlite3.connect(self.static_db_path)
                    search_name = monster_name.replace('monster', '').replace('mons', '').strip()
                    rows = conn.execute(
                        "SELECT id FROM npc_data WHERE name LIKE ?",
                        (f"%{search_name}%",)
                    ).fetchall()
                    for r in rows:
                        cand_id = str(r[0])
                        if cand_id in self.drop_tables:
                            resolved_id = cand_id
                            break
                    conn.close()
                except Exception as e:
                    logger.error(f"[Drop] Error resolving monster name {monster_name}: {e}")
                
                if resolved_id and resolved_id in self.drop_tables:
                    drop_rules = self.drop_tables[resolved_id]
                else:
                    drop_rules = self.drop_tables.get("default", [])
            
            for rule in drop_rules:
                chance = rule.get("chance", 0.0)
                if random.random() < chance:
                    dropped_item_id = rule.get("item_id", 0)
                    dropped_amount = rule.get("amount", 1)
                    break

            if dropped_item_id > 0:
                slot = add_item_to_inventory(session, dropped_item_id, amount=dropped_amount)
                if slot is not None:
                    self.save_player_to_db(session)
                    
                    item_pkt = PacketWriter()
                    item_pkt.write_8(23).write_8(6).write_16(dropped_item_id).write_8(dropped_amount).write_bytes(bytes(26))
                    await session.send_packet(item_pkt)
                    
                    fly_pkt = PacketWriter()
                    fly_pkt.write_8(53).write_8(4).write_16(dropped_item_id).write_8(primary_mon['x']).write_8(primary_mon['y']).write_8(pf['x']).write_8(pf['y'])
                    await session.send_packet(fly_pkt)

        # Canavarın ölüm animasyonu bitsin diye delay
        await asyncio.sleep(2.0)

        # 5. AC 11:12 [01] – SAVAŞ BİTİŞ SİNYALİ
        await session.send_packet(PacketWriter().write_8(11).write_8(12).write_8(1))

        # 6. EXP ve Gold ödülleri hesaplama & güncelleme
        exp_reward = max(10, primary_mon['level'] * 15)
        gold_reward = max(5, primary_mon['level'] * 8)
        
        if won:
            session.gold += gold_reward
            await self.give_exp(session, exp_reward)

            # Pet rewards
            if pet_f:
                pet_slot = pet_f['click_id'] + 1
                if 1 <= pet_slot <= len(session.pets):
                    pet = session.pets[pet_slot - 1]
                    old_pet_lvl = pet.get("level", 1)
                    pet["exp"] = pet.get("exp", 0) + exp_reward
                    
                    new_pet_lvl = self.get_level_from_exp(pet["exp"], pet.get("reborn", 0) != 0)
                    if new_pet_lvl != old_pet_lvl:
                        pet["level"] = new_pet_lvl
                        pet["potential"] = pet.get("potential", 0) + (new_pet_lvl - old_pet_lvl) * 3
                        logger.info(f"[{session.char_name}] Pet leveled up! {old_pet_lvl} -> {new_pet_lvl}")
                    
                    con = pet.get("con", 5)
                    wis = pet.get("wis", 5)
                    pet_max_hp = int(round(((new_pet_lvl ** 0.35) * con * 2) + (new_pet_lvl * 1) + (con * 2) + 180))
                    pet_max_sp = int(round(((new_pet_lvl ** 0.3) * wis * 3.2) + (new_pet_lvl * 1) + (wis * 2) + 94))
                    pet["hp"] = min(pet_f["hp"], pet_max_hp)
                    pet["sp"] = min(pet_f["sp"], pet_max_sp)
                    
                    self.save_player_to_db(session)
                    await self.send_pet_stats(session, pet_slot)
                    await self.send_pet_list(session)

        # 7. AC 22:6 [battle_type=11, 0, result]
        result = 2 if won else (1 if fled else 0)
        p226 = PacketWriter()
        p226.write_8(22).write_8(6)
        p226.write_8(0x0b).write_8(0x00).write_8(result)
        await session.send_packet(p226)

        # 8. AC 22:5 [battle_type=11, 0, exp_reward, gold_reward]
        if won:
            p_rew = PacketWriter()
            p_rew.write_8(22).write_8(5)
            p_rew.write_16(11)
            p_rew.write_16(min(0xFFFF, exp_reward))
            p_rew.write_16(min(0xFFFF, gold_reward))
            await session.send_packet(p_rew)

        # 9. AC 11:0 [char_id uint32, 0x0000]
        p110 = PacketWriter()
        p110.write_8(11).write_8(0)
        p110.write_32(session.char_id)
        p110.write_16(0)
        await session.send_packet(p110)

        # 10. AC 11:1 [player_x, player_y, 0]
        await session.send_packet(
            PacketWriter().write_8(11).write_8(1).write_8(pf['x']).write_8(pf['y']).write_8(0)
        )

        # State temizliği
        battle['finished'] = True
        bid = battle['id']
        if bid in self.active_battles:
            del self.active_battles[bid]
            
        session.in_battle     = False
        session.pvp_battle_id = None

        # Canavarın haritada görünürlüğünü güncelle
        click_id = primary_mon.get('click_id', 0)
        if click_id > 0:
            target_npc = None
            for npc in self.map_npcs.get(session.map_id, []):
                if npc['click_id'] == click_id:
                    target_npc = npc
                    break
            if fled:
                if target_npc:
                    target_npc['visible'] = True
                async def show_monster_delayed():
                    await asyncio.sleep(0.5)
                    pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0).write_8(0)
                    await session.send_packet(pkt)
                asyncio.create_task(show_monster_delayed())
            elif won:
                if target_npc:
                    target_npc['visible'] = False
                pkt_hide = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0xFF).write_8(0xFF)
                await session.send_packet(pkt_hide)
                
                async def respawn_monster():
                    await asyncio.sleep(15.0)
                    if target_npc:
                        target_npc['visible'] = True
                    pkt_show = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0).write_8(0)
                    self.broadcast_to_map(session.map_id, pkt_show)
                asyncio.create_task(respawn_monster())

        # Check if quest battle win warp is set
        win_warp = getattr(session, 'battle_win_warp', None)
        if won and win_warp:
            logger.info(f"[{session.char_name}] Quest battle won! Warp to map {win_warp['map_id']} pos=({win_warp['x']},{win_warp['y']})")
        elif not won and not fled:
            # Player lost/died: revive with 10% HP/SP and warp to Map 10017
            session.hp = max(1, int(session.max_hp * 0.10))
            session.sp = max(1, int(session.max_sp * 0.10))
            self.save_player_to_db(session)
            logger.info(f"[Battle] {session.char_name} LOST vs {primary_mon.get('name', 'Unknown')}. Revived at 10% HP/SP. Warping to starter ship.")
            await self.warp_player(session, 10017, 1042, 1075)
        else:
            session.battle_win_warp = None  # clear it
            session.pending_battle_unlock = True

            # Fallback unlock task to ensure player is never permanently stuck
            async def fallback_unlock():
                await asyncio.sleep(2.5)
                if getattr(session, 'pending_battle_unlock', False):
                    session.pending_battle_unlock = False
                    logger.info(f"[{session.char_name}] Fallback battle unlock triggered after 2.5 seconds.")
                    await session.send_packet(PacketWriter().write_8(23).write_8(102))
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
            asyncio.create_task(fallback_unlock())

        if won:
            logger.info(f"[Battle] {session.char_name} WON vs {primary_mon.get('name', 'Unknown')}")
        elif fled:
            logger.info(f"[Battle] {session.char_name} FLED vs {primary_mon.get('name', 'Unknown')}")

        # Ensure everything is saved after battle ends
        self.save_player_to_db(session)

    # ──────────────────────────────────────────────────────────────────────────
    # Legacy compat shims
    # ──────────────────────────────────────────────────────────────────────────

    async def enter_battle(self, session, click_id, npc_id, override_sprite_id=0):
        await self._start_pve_battle(session, click_id, npc_id, override_sprite_id)

    # ──────────────────────────────────────────────────────────────────────────
    # Compound / Crafting
    # ──────────────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────────────

    _COMPOUND_RECIPES: dict = {}

    def _xor_byte(self, v: int) -> int:
        return ((v ^ 0xD3) - 3) & 0xFF

    def _xor_word(self, v: int) -> int:
        return ((v ^ 0xFBBC) - 3) & 0xFFFF

    def _load_compound_dat(self):
        """Loads compound recipes from both data/Compound.dat and data/Compound2.dat."""
        import os
        self._COMPOUND_RECIPES = {}
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
        
        # 1. Load Compound.dat (with 8 bytes header)
        compound1_path = os.path.join(base_dir, "data", "Compound.dat")
        if os.path.exists(compound1_path):
            try:
                with open(compound1_path, "rb") as f:
                    d = f.read()
                if len(d) > 8:
                    d_payload = d[8:]
                    record_count = len(d_payload) // 65
                    recipes_loaded = 0
                    for idx in range(record_count):
                        ptr = idx * 65
                        if ptr + 65 > len(d_payload):
                            break
                        result_id = self._xor_word((d_payload[ptr + 1] << 8) + d_payload[ptr]); ptr += 2
                        plan_id   = self._xor_word((d_payload[ptr + 1] << 8) + d_payload[ptr]); ptr += 2
                        _         = self._xor_byte(d_payload[ptr]);                      ptr += 1
                        tool_id   = self._xor_word((d_payload[ptr + 1] << 8) + d_payload[ptr]); ptr += 2
                        result_amount = self._xor_byte(d_payload[ptr]);                  ptr += 1
                        ptr += 3  # unknownByte0-2
                        materials = []
                        for _ in range(5):
                            mat_id  = self._xor_word((d_payload[ptr + 1] << 8) + d_payload[ptr]); ptr += 2
                            mat_amt = self._xor_byte(d_payload[ptr]);                      ptr += 1
                            if mat_id > 0 and mat_amt > 0 and mat_id < 50000:
                                materials.append({"item_id": mat_id, "amount": mat_amt})
                        if result_id > 0 and result_id < 50000 and materials:
                            self._COMPOUND_RECIPES[result_id] = {
                                "compound_id":   result_id,
                                "result_item":   result_id,
                                "result_amount": max(1, result_amount),
                                "materials":     materials,
                            }
                            recipes_loaded += 1
                    logger.info(f"[Compound] Loaded {recipes_loaded} compound recipes from Compound.dat ({record_count} records).")
            except Exception as e:
                logger.error(f"[Compound] Error loading Compound.dat: {e}", exc_info=True)

        # 2. Load Compound2.dat (no header)
        compound2_path = os.path.join(base_dir, "data", "Compound2.dat")
        if os.path.exists(compound2_path):
            try:
                with open(compound2_path, "rb") as f:
                    d = f.read()
                if len(d) >= 65:
                    record_count = len(d) // 65
                    recipes_loaded = 0
                    for idx in range(record_count):
                        ptr = idx * 65
                        if ptr + 65 > len(d):
                            break
                        result_id = self._xor_word((d[ptr + 1] << 8) + d[ptr]); ptr += 2
                        plan_id   = self._xor_word((d[ptr + 1] << 8) + d[ptr]); ptr += 2
                        _         = self._xor_byte(d[ptr]);                      ptr += 1
                        tool_id   = self._xor_word((d[ptr + 1] << 8) + d[ptr]); ptr += 2
                        result_amount = self._xor_byte(d[ptr]);                  ptr += 1
                        ptr += 3  # unknownByte0-2
                        materials = []
                        for _ in range(5):
                            mat_id  = self._xor_word((d[ptr + 1] << 8) + d[ptr]); ptr += 2
                            mat_amt = self._xor_byte(d[ptr]);                      ptr += 1
                            if mat_id > 0 and mat_amt > 0 and mat_id < 50000:
                                materials.append({"item_id": mat_id, "amount": mat_amt})
                        if result_id > 0 and result_id < 50000 and materials:
                            self._COMPOUND_RECIPES[result_id] = {
                                "compound_id":   result_id,
                                "result_item":   result_id,
                                "result_amount": max(1, result_amount),
                                "materials":     materials,
                            }
                            recipes_loaded += 1
                    logger.info(f"[Compound] Loaded {recipes_loaded} compound recipes from Compound2.dat (total recipes: {len(self._COMPOUND_RECIPES)}).")
            except Exception as e:
                logger.error(f"[Compound] Error loading Compound2.dat: {e}", exc_info=True)

    def _load_formula_dat(self):
        """Loads dynamic compounding modifiers from data/Formula.dat (doubles starting at offset 1)."""
        import os
        import struct
        self.alchemy_formulas = []
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
        formula_path = os.path.join(base_dir, "data", "Formula.dat")
        if not os.path.exists(formula_path):
            logger.warning(f"[Compound] Formula.dat not found at {formula_path}")
            return
        try:
            with open(formula_path, "rb") as f:
                d = f.read()
            # Double floats (8 bytes) start at offset 1, ending with padding bytes
            ptr = 1
            while ptr + 8 <= len(d):
                val = struct.unpack('<d', d[ptr:ptr+8])[0]
                self.alchemy_formulas.append(val)
                ptr += 8
            logger.info(f"[Compound] Loaded {len(self.alchemy_formulas)} compounding constants from Formula.dat.")
        except Exception as e:
            logger.error(f"[Compound] Error loading Formula.dat: {e}", exc_info=True)

    def get_compound_recipe(self, compound_id: int) -> dict:
        return self._COMPOUND_RECIPES.get(compound_id, None)

    def _load_item_mix(self):
        self.item_mix_recipes = {}
        import json
        import os
        path = os.path.join("server", "data", "item_mix.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    recipes = json.load(f)
                    for r in recipes:
                        mats = tuple(sorted(r["materials"]))
                        self.item_mix_recipes[mats] = {
                            "result_item": r["result_item"],
                            "result_amount": r.get("result_amount", 1)
                        }
                logger.info(f"[ItemMix] Loaded {len(self.item_mix_recipes)} item mix recipes from {path}")
            except Exception as e:
                logger.error(f"[ItemMix] Error loading item_mix.json: {e}")

    def _load_item_properties(self):
        self.item_properties = {}
        self.items = {}
        import json
        import os
        path = os.path.join("server", "data", "item_properties.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.item_properties = json.load(f)
                for k, v in self.item_properties.items():
                    if isinstance(v, dict):
                        name = v.get("name") or f"Item #{k}"
                        self.items[str(k)] = name
                    else:
                        self.items[str(k)] = str(v)
                logger.info(f"[ItemProperties] Loaded {len(self.item_properties)} item properties and {len(self.items)} item names from {path}")
            except Exception as e:
                logger.error(f"[ItemProperties] Error loading item_properties.json: {e}")

    def get_item_name(self, item_id: int) -> str:
        """Returns the canonical item name or fallback string."""
        from server.dat_loaders import GLOBAL_ITEM_DAT
        if GLOBAL_ITEM_DAT and item_id in GLOBAL_ITEM_DAT.items:
            name = GLOBAL_ITEM_DAT.items[item_id].name
            if name:
                return name
        if hasattr(self, 'items') and isinstance(self.items, dict):
            name = self.items.get(str(item_id))
            if name:
                return name
        
        # Canonical fallback mappings for quest & dynamic items
        fallbacks = {
            48016: "Robinson's Raft",
            48001: "Raft",
            48002: "Canoe",
            48003: "Sailboat",
            48004: "Yacht",
            48005: "Airship",
            48006: "Submarine",
            48013: "UFO",
            48033: "Spacecraft",
            32074: "Raft Plank",
            32075: "Raft Oar",
            32032: "Sail Cloth",
            32073: "Raft Keel",
            41066: "Coconut",
            27001: "Ordinary Wood",
            27002: "Pine Wood",
            28014: "Fresh Fruit",
            28001: "Sea Water",
            30001: "Herb Potion",
            30259: "Black Medicine",
            24001: "Iron Ore",
            24002: "Copper Ore",
            24005: "Coal",
            22061: "Headband",
        }
        return fallbacks.get(item_id, f"Item #{item_id}")

    async def send_compound_list(self, session: PlayerSession):
        """Sends the full compound recipe list to the client via AC 54 Sub 30."""
        if not self._COMPOUND_RECIPES:
            return
        for cid, recipe in self._COMPOUND_RECIPES.items():
            pkt = PacketWriter()
            pkt.write_8(54).write_8(30)
            pkt.write_16(cid)
            pkt.write_16(recipe["result_item"])
            pkt.write_8(recipe["result_amount"])
            mats = recipe.get("materials", [])
            pkt.write_8(len(mats))
            for mat in mats:
                pkt.write_16(mat["item_id"])
                pkt.write_8(mat["amount"])
            await session.send_packet(pkt)
            await asyncio.sleep(0.001)
        logger.info(f"[Compound] Finished sending compound recipes to {session.char_name}")

async def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    server = GameServer()
    await server.run("0.0.0.0", 6414)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
