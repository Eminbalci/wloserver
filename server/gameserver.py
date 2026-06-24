import asyncio
import logging
import sqlite3
import struct
import json
import traceback
import math
import sys
import random
from server.quest_manager import QuestManager
from datetime import datetime

from server.network import PacketReader, PacketWriter, xor_crypt
from server.database import DatabaseManager
from server.battle import Fighter, BattleManager

# Setup logger
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WLO_Server")

# Version string for AC 0 Response
SERVER_VERSION = "1.0.0.0"

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

def encode_item16(val):
    return ((val ^ 0xEFC3) - 9) & 0xFFFF

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
    
    def __init__(self, db_path: str = "wlo_server.db", static_db_path: str = "server/ServerDataBase.db"):
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
        self._load_all_npcs()
        self._load_compound_dat()
        self._load_skill_dat()

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

                npc_offset = offsets[0]
                
                npc_ptr = m['dataptr'] + npc_offset
                if npc_ptr + 2 > len(d):
                    continue
                    
                elen = struct.unpack_from("<H", d, npc_ptr)[0]
                if elen == 0:
                    continue
                    
                cur_ptr = npc_ptr + 2
                npcs = []
                for _ in range(elen):
                    if cur_ptr + 50 > len(d):
                        break
                        
                    clickId = struct.unpack_from("<H", d, cur_ptr)[0]
                    name_len = d[cur_ptr+2]
                    name_bytes = d[cur_ptr+3 : cur_ptr+3+name_len]
                    name = name_bytes.decode('cp950', errors='ignore')
                    
                    cur_ptr += 22
                    
                    unknownbyte1 = d[cur_ptr]
                    cur_ptr += 1
                    
                    x = struct.unpack_from("<I", d, cur_ptr)[0]
                    cur_ptr += 4
                    y = struct.unpack_from("<I", d, cur_ptr)[0]
                    cur_ptr += 4
                    
                    # Events (store them)
                    blen = d[cur_ptr]
                    events = list(d[cur_ptr+1:cur_ptr+1+blen])
                    cur_ptr += 1 + blen
                    
                    # unknownbytearray2 = linked portal IDs (door triggers)
                    blen = d[cur_ptr]
                    linked_portals = list(d[cur_ptr+1:cur_ptr+1+blen])
                    cur_ptr += 1 + blen
                    
                    unknownbyte2 = d[cur_ptr]
                    cur_ptr += 1
                    
                    npcId = struct.unpack_from("<I", d, cur_ptr)[0]
                    cur_ptr += 4
                    
                    rotation = d[cur_ptr]
                    cur_ptr += 1
                    
                    walk_behavior = d[cur_ptr]
                    cur_ptr += 1
                    
                    unknownbyte5 = d[cur_ptr]
                    cur_ptr += 1
                    
                    # walksteps
                    blen = d[cur_ptr]
                    cur_ptr += 1
                    walksteps = []
                    for _ in range(blen):
                        wx = struct.unpack_from("<I", d, cur_ptr)[0]
                        wy = struct.unpack_from("<I", d, cur_ptr+4)[0]
                        delay = struct.unpack_from("<I", d, cur_ptr+8)[0]
                        walksteps.append({'x': wx, 'y': wy, 'delay': delay})
                        cur_ptr += 12
                        
                    # skip unknown bytes and walkpatterns and unknown words
                    cur_ptr += 13
                    
                    blen = d[cur_ptr]
                    cur_ptr += 1 + blen * 92
                    
                    cur_ptr += 8
                    
                    npcs.append({
                        'click_id': clickId,
                        'name': name,
                        'npc_id': npcId,
                        'x': x,
                        'y': y,
                        'rotation': rotation,
                        'walk_behavior': walk_behavior,
                        'walksteps': walksteps,
                        'events': events,
                        'linked_portals': linked_portals,  # portal IDs this NPC triggers (doors)
                        'cur_step': 0,
                        'next_walk_time': 0.0
                    })
                    npc_count += 1
                    
                self.map_npcs[mapID] = npcs
            logger.info(f"[NPC] Loaded {npc_count} NPCs across {len(self.map_npcs)} maps from eve.Emg.")
        except Exception as e:
            logger.error(f"[NPC] Error loading NPCs from eve.Emg: {e}", exc_info=True)

    async def npc_walk_loop(self):
        """Background loop that executes NPC walks and broadcasts movement packets to clients."""
        import time
        import random
        
        logger.info("[NPC] Starting NPC walk loop task.")
        while True:
            try:
                now = time.time()
                for map_id, npcs in self.map_npcs.items():
                    # Only walk NPCs on maps that have active players!
                    if map_id not in self.map_players or not self.map_players[map_id]:
                        continue
                        
                    for npc in npcs:
                        if npc['next_walk_time'] > now:
                            continue
                            
                        # Scripted path walking (behavior 5)
                        if npc['walk_behavior'] == 5 and npc['walksteps']:
                            step = npc['walksteps'][npc['cur_step'] % len(npc['walksteps'])]
                            
                            pkt = PacketWriter()
                            pkt.write_8(22).write_8(2)
                            pkt.write_16(npc['click_id'])
                            pkt.write_16(step['x'])
                            pkt.write_16(step['y'])
                            pkt.write_8(3) # speed
                            
                            self.broadcast_to_map(map_id, pkt)
                            
                            npc['cur_step'] = (npc['cur_step'] + 1) % len(npc['walksteps'])
                            npc['next_walk_time'] = now + max(1.0, float(step.get('delay', 0)) / 1000.0)
                            
                        # Random walking (behavior 4)
                        elif npc['walk_behavior'] == 4:
                            dx = random.randint(-120, 120)
                            dy = random.randint(-120, 120)
                            target_x = npc['x'] + dx
                            target_y = npc['y'] + dy
                            
                            pkt = PacketWriter()
                            pkt.write_8(22).write_8(2)
                            pkt.write_16(npc['click_id'])
                            pkt.write_16(target_x)
                            pkt.write_16(target_y)
                            pkt.write_8(3) # speed
                            
                            self.broadcast_to_map(map_id, pkt)
                            
                            npc['next_walk_time'] = now + random.uniform(4.0, 9.0)
            except Exception as e:
                logger.error(f"[NPC] Error in NPC walk loop: {e}", exc_info=True)
                
            await asyncio.sleep(0.5)

    async def run(self, host: str = "0.0.0.0", port: int = 6414):
        """Starts the asynchronous TCP server."""
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
            
        for sk in self.all_skills_db:
            sk_id = sk['id']
            # Only add if it belongs to player's element and is not already learned
            # Earth=1, Water=2, Fire=3, Wind=4
            if sk['element'] == session.element and sk_id not in existing_ids:
                session.skills.append({"skill_id": sk_id, "grade": 1, "exp": 0})
                existing_ids.add(sk_id)
                new_skills_added = True
                
        if new_skills_added:
            self.save_player_to_db(session)
            logger.info(f"[SKILL] Added {len(session.skills)} skills to {session.char_name} (element={session.element})")

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
        }
        self.db.save_character(session.char_id, data)

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

    async def dispatch_packet(self, session: PlayerSession, action_code: int, reader: PacketReader):
        """Dispatches decrypted Action Codes to corresponding handlers."""
        # Log received packets for debugging
        sub_code = reader.data[1] if len(reader.data) > 1 else 0
        logger.debug(f"[{session.username or session.ip}] Action Code: {action_code}, Sub: {sub_code}, Payload size: {len(reader.data)}, Hex: {reader.data.hex()}")

        if action_code == 0:
            await self.handle_handshake(session, reader)
        elif action_code == 63:
            await self.handle_login_selection(session, reader)
        elif action_code == 9:
            await self.handle_character_creation(session, reader)
        elif action_code == 8:
            await self.handle_action_8(session, reader)
        elif action_code == 35:
            await self.handle_character_deletion(session, reader)
        elif action_code == 2:
            await self.handle_chat_gm(session, reader)
        elif action_code == 6:
            await self.handle_movement(session, reader)
        elif action_code == 20:
            await self.handle_interaction(session, reader)
        elif action_code == 12:
            await self.handle_warp_done(session, reader)
        elif action_code == 23:
            await self.handle_action_23(session, reader)
        elif action_code == 33:
            await self.handle_action_33(session, reader)
        elif action_code == 11:
            await self.handle_combat(session, reader)
        elif action_code == 50:
            await self.handle_battle_action(session, reader)
        elif action_code == 15:
            await self.handle_action_15(session, reader)
        elif action_code == 37:
            await self.handle_action_37(session, reader)
        elif action_code == 14:
            await self.handle_action_14(session, reader)
        elif action_code == 54:
            await self.handle_action_54(session, reader)
        elif action_code == 30:
            await self.handle_action_30(session, reader)
        elif action_code == 31:
            await self.handle_action_31(session, reader)
        else:
            logger.info(f"Unhandled Action Code: {action_code}, payload: {reader.data.hex()}")

    async def handle_action_8(self, session: PlayerSession, reader: PacketReader):
        """Handles stats and potential point allocation (AC 8)."""
        sub = reader.read_8()
        logger.info(f"[AC8] handle_action_8 called. SubCmd={sub}, data: {reader.data.hex()}")
        if sub == 1:
            target_type = reader.read_8()
            target_slot = reader.read_8()
            stat_id = reader.read_8()
            amount = reader.read_32()
            
            logger.info(f"[AC8] Allocating stats: target_type={target_type}, target_slot={target_slot}, stat_id={stat_id}, amount={amount}")
            
            # Verify points
            if target_type == 0: # Player
                if session.points >= amount:
                    session.points -= amount
                    if stat_id == 28: # STR
                        session._str_val += amount
                    elif stat_id == 29: # CON
                        session._con_val += amount
                    elif stat_id == 27: # INT
                        session._int_val += amount
                    elif stat_id == 33: # WIS
                        session._wis_val += amount
                    elif stat_id == 30: # AGI
                        session._agi_val += amount
                    
                    self.save_player_to_db(session)
                    await self.send_stats_update(session, levelup=True)
                    logger.info(f"[AC8] Player allocated stat {stat_id} by {amount}. Remaining points: {session.points}")
                else:
                    logger.warning(f"[AC8] Player tried to allocate {amount} points but only has {session.points}")
            
            elif target_type == 1: # Pet
                if 1 <= target_slot <= len(session.pets):
                    pet = session.pets[target_slot - 1]
                    pet_potential = pet.get("potential", 0)
                    if pet_potential >= amount:
                        pet["potential"] = pet_potential - amount
                        if stat_id == 28: # STR
                            pet["str"] = pet.get("str", 5) + amount
                        elif stat_id == 29: # CON
                            pet["con"] = pet.get("con", 5) + amount
                        elif stat_id == 27: # INT
                            pet["int"] = pet.get("int", 5) + amount
                        elif stat_id == 33: # WIS
                            pet["wis"] = pet.get("wis", 5) + amount
                        elif stat_id == 30: # AGI
                            pet["agi"] = pet.get("agi", 5) + amount
                        
                        self.save_player_to_db(session)
                        await self.send_pet_stats(session, target_slot)
                        await self.send_pet_list(session)
                        logger.info(f"[AC8] Pet slot {target_slot} allocated stat {stat_id} by {amount}. Remaining potential: {pet['potential']}")
                    else:
                        logger.warning(f"[AC8] Pet tried to allocate {amount} points but only has {pet_potential}")

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

    async def handle_action_14(self, session: PlayerSession, reader: PacketReader):
        """Handles Friend System (AC 14) actions."""
        sub = reader.read_8()
        logger.info(f"[AC14] handle_action_14 called. SubCmd={sub}")
        
        if sub == 1:  # Add Friend Request (by name)
            target_name = reader.read_string()
            logger.info(f"[AC14] Add Friend Request from {session.char_name} to {target_name}")
            
            # Find target player session
            target = None
            for act in self.active_sessions:
                if act.char_name == target_name:
                    target = act
                    break
                    
            if target:
                logger.info(f"[AC14] Target {target_name} found. Sending friend request...")
                s = PacketWriter()
                s.write_8(14).write_8(1)
                s.write_string(session.char_name)
                await target.send_packet(s)
            else:
                logger.info(f"[AC14] Target {target_name} NOT found")
                s = PacketWriter()
                s.write_8(14).write_8(1)
                s.write_8(0)  # Failure
                await session.send_packet(s)
                
        elif sub == 2:  # Dual purpose - Friend List Request OR Friend Request Send
            flag = reader.read_8()
            target_char_id = reader.read_32()
            ignored_string = reader.read_string()
            
            logger.info(f"[AC14] SubCmd 2. Flag={flag}, TargetCharID={target_char_id}")
            
            if target_char_id == 0:
                await self.send_friend_list(session)
            else:
                # Find target player by CharID
                target = None
                for act in self.active_sessions:
                    if act.char_id == target_char_id:
                        target = act
                        break
                        
                if target:
                    logger.info(f"[AC14] Target {target.char_name} (ID:{target_char_id}) found. Sending friend request...")
                    s = PacketWriter()
                    s.write_8(14).write_8(2)
                    s.write_32(session.char_id)
                    s.write_string("")
                    await target.send_packet(s)
                    
        elif sub == 3:  # Friend Accept
            flag = reader.read_8()
            requester_char_id = reader.read_32()
            ignored_string = reader.read_string()
            
            logger.info(f"[AC14] Friend Accept from {session.char_name} for Requester ID: {requester_char_id}")
            
            # Find requester
            requester = None
            for act in self.active_sessions:
                if act.char_id == requester_char_id:
                    requester = act
                    break
                    
            if not requester:
                logger.info(f"[AC14] Requester CharID {requester_char_id} not online/found")
                return
                
            try:
                smaller = min(session.char_id, requester_char_id)
                larger = max(session.char_id, requester_char_id)
                
                with self.db.get_connection() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO friends (CharID1, CharID2, AddedDate) VALUES (?, ?, datetime('now'))",
                        (smaller, larger)
                    )
                    conn.commit()
                    
                logger.info(f"[AC14] Friendship added: {session.char_id} <-> {requester_char_id}")
                
                # Send success to requester
                s = PacketWriter()
                s.write_8(14).write_8(3)
                s.write_8(1)  # Success
                s.write_string(session.char_name)
                await requester.send_packet(s)
                
                # Send success to accepter
                s2 = PacketWriter()
                s2.write_8(14).write_8(3)
                s2.write_8(1)  # Success
                await session.send_packet(s2)
                
                # Auto-refresh lists
                await self.send_friend_list(session)
                await self.send_friend_list(requester)
            except Exception as e:
                logger.error(f"[AC14] Database/Accept error: {e}", exc_info=True)
                
        elif sub == 4:  # Remove Friend OR Friend List Request
            # Check if remaining bytes in packet for friend_char_id (at least 4 bytes)
            if reader.remaining_bytes() >= 4:
                friend_char_id = reader.read_32()
                logger.info(f"[AC14] Friend Remove Request from {session.char_name} for CharID {friend_char_id}")
                try:
                    smaller = min(session.char_id, friend_char_id)
                    larger = max(session.char_id, friend_char_id)
                    
                    with self.db.get_connection() as conn:
                        conn.execute(
                            "DELETE FROM friends WHERE CharID1 = ? AND CharID2 = ?",
                            (smaller, larger)
                        )
                        conn.commit()
                        
                    logger.info(f"[AC14] Removed friendship: {session.char_id} <-> {friend_char_id}")
                    await self.send_friend_list(session)
                except Exception as e:
                    logger.error(f"[AC14] Database error removing friend: {e}", exc_info=True)
            else:
                logger.info(f"[AC14] Friend List Request (SubCmd 4) from {session.char_name}")
                await self.send_friend_list(session)

    async def handle_handshake(self, session: PlayerSession, reader: PacketReader):
        """Processes client connection handshake (AC 0)."""
        logger.info(f"[{session.ip}] Client handshake received.")
        
        # Respond with AC 1 Sub 9 (Server Version)
        v_ack = PacketWriter()
        v_ack.write_8(1)
        v_ack.write_8(9)
        v_ack.write_bytes(bytes([107, 0, 1]))
        v_ack.write_string_n(SERVER_VERSION)
        await session.send_packet(v_ack)
        
        # Respond with AC 54 Sub 29 (Sub-server Configuration)
        config = PacketWriter()
        config.write_8(54)
        config.write_8(29)
        config.write_bytes(SUBSERVER_CONFIG)
        await session.send_packet(config)

    async def handle_login_selection(self, session: PlayerSession, reader: PacketReader):
        """Handles user authentication, slot updates (AC 63)."""
        sub = reader.read_8()
        
        if sub == 4:  # Login Authentication
            username = reader.read_string()
            password = reader.read_string()
            
            logger.info(f"[Auth] Username '{username}' attempting login...")
            
            # Check database credentials
            user_data = self.db.verify_user(username, password)
            
            if not user_data:
                # User doesn't exist, execute Auto-Registration
                user_id, err = self.db.register_user(username, password)
                if user_id:
                    logger.info(f"[Auth] Auto-registered new account: '{username}'")
                    user_data = self.db.verify_user(username, password)
                else:
                    logger.error(f"[Auth] Auto-registration failed for '{username}': {err}")
                    
            if user_data:
                session.user_id = user_data['id']
                session.username = user_data['username']
                session.cipher = user_data['cipher']
                
                # Send Login Success
                success_pkt = PacketWriter()
                success_pkt.write_8(63)
                success_pkt.write_8(2)
                success_pkt.write_32(session.user_id)
                await session.send_packet(success_pkt)
                
                # Send Character List
                list_pkt = PacketWriter()
                list_pkt.write_8(63)
                list_pkt.write_8(1)
                
                # Slot 1 character
                char1 = self.db.get_character_by_id(user_data['character1_id'])
                if char1:
                    list_pkt.write_bytes(self.serialize_character_slot(char1))
                
                # Slot 2 character
                char2 = self.db.get_character_by_id(user_data['character2_id'])
                if char2:
                    list_pkt.write_bytes(self.serialize_character_slot(char2))
                    
                await session.send_packet(list_pkt)
                
                # Send AC 35, Sub 11
                await session.send_packet(PacketWriter().write_8(35).write_8(11))
            else:
                # Login failure
                fail_pkt = PacketWriter()
                fail_pkt.write_8(63).write_8(2)
                await session.send_packet(fail_pkt)
                await session.send_packet(PacketWriter().write_8(1).write_8(6))

        elif sub == 2:  # Selected Character Slot
            slot = reader.read_8()
            if slot not in (1, 2):
                await session.send_packet(PacketWriter().write_8(0).write_8(32))
                return
                
            # Query slot character
            user_data = self.db.verify_user(session.username, "dummy")  # Just fetch user IDs
            # Wait, verify_user needs correct password, let's query db directly or use verify_user results
            with self.db.get_connection() as conn:
                row = conn.execute("SELECT id FROM characters WHERE user_id = ? AND slot = ?", (session.user_id, slot)).fetchone()
                char_id = row['id'] if row else 0
                
            if not char_id:
                # No character in slot: request creation
                create_req = PacketWriter()
                create_req.write_8(1)
                create_req.write_8(3)
                create_req.write_bool(bool(session.cipher))
                await session.send_packet(create_req)
            else:
                # Character exists: confirm login
                # Load character stats into session first to populate session.char_id
                self.load_character_into_session(session, char_id)
                
                confirm = PacketWriter()
                confirm.write_8(63)
                confirm.write_8(2)
                confirm.write_32(session.char_id)
                await session.send_packet(confirm)
                
                # Commence Map Entry!
                await self.commence_login(session)

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
            writer.write_16(encode_item16(item_id))
        return writer.buffer

    async def handle_character_creation(self, session: PlayerSession, reader: PacketReader):
        """Processes character creation and name availability (AC 9)."""
        sub = reader.read_8()
        
        if sub == 2:  # Check Name Availability
            name = reader.read_string_n()
            taken = self.db.is_name_taken(name)
            status = 1 if taken or len(name) < 4 or len(name) > 14 else 0
            if status == 0:
                session.char_name = name
            
            resp = PacketWriter()
            resp.write_8(9).write_8(3).write_8(status)
            await session.send_packet(resp)
            
        elif sub == 1:  # Create character
            body = reader.read_16()
            head = reader.read_16()
            hair_color = reader.read_16()
            skin_color = reader.read_16()
            clothing_color = reader.read_16()
            eye_color = reader.read_16()
            element = reader.read_8()
            
            # Stats (read in client-sent order: str, agi, wis, int, con)
            str_val = reader.read_8()  # str
            agi_val = reader.read_8()  # agi
            wis_val = reader.read_8()  # wis
            int_val = reader.read_8()  # int
            con_val = reader.read_8()  # con
            
            cipher = ""
            if not session.cipher:
                cipher = reader.read_string()
                
            # Determine slot (check which slot is free)
            slot = 1
            user_data = self.db.verify_user(session.username, "dummy")
            with self.db.get_connection() as conn:
                row = conn.execute("SELECT id FROM characters WHERE user_id = ? AND slot = 1", (session.user_id,)).fetchone()
                if row:
                    slot = 2
                    
            char_id = self.db.create_character(
                session.user_id, slot, session.char_name, body, head,
                hair_color, skin_color, clothing_color, eye_color, element, cipher,
                str_val=str_val, con_val=con_val, int_val=int_val, wis_val=wis_val, agi_val=agi_val
            )
            
            if char_id:
                logger.info(f"[Char] Character '{session.char_name}' created in slot {slot}")
                if cipher:
                    session.cipher = cipher
                    
                # Load character stats first to populate session.char_id
                self.load_character_into_session(session, char_id)
                
                # Commence Map Entry directly (no 63, 2 confirm packet!)
                await self.commence_login(session)
            else:
                # Creation error
                await session.send_packet(PacketWriter().write_8(0).write_8(30))

    async def handle_character_deletion(self, session: PlayerSession, reader: PacketReader):
        """Processes character slot deletion (AC 35)."""
        sub = reader.read_8()
        if sub == 2:  # Delete Character request
            slot = reader.read_8()
            reader.read_string()  # Unknown string
            password = reader.read_string()
            
            # Allow deletion if cipher matches or is empty
            matches = not session.cipher or session.cipher == password
            
            if matches:
                # Fetch character ID
                with self.db.get_connection() as conn:
                    row = conn.execute("SELECT id FROM characters WHERE user_id = ? AND slot = ?", (session.user_id, slot)).fetchone()
                    char_id = row['id'] if row else 0
                    
                if char_id:
                    self.db.delete_character(char_id)
                    logger.info(f"[Char] Character in slot {slot} deleted successfully.")
                    
                # Deletion success packet sequences
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(53).write_8(0).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(52).write_8(0).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(54).write_8(0).write_8(0))
                await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(183).write_8(0).write_8(0))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                
                resp = PacketWriter().write_8(35).write_8(2).write_8(1).write_8(slot)
                await session.send_packet(resp)
            else:
                # Cipher mismatch
                resp = PacketWriter().write_8(35).write_8(2).write_8(3).write_8(slot)
                await session.send_packet(resp)

    async def commence_login(self, session: PlayerSession):
        """Triggers gameplay initialization sequences."""
        logger.info(f"[{session.char_name}] Commencing login to Map {session.map_id}...")
        
        session.logged_in = True
        session.is_warping = True
        
        # Sequence of initialization packets
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(183).write_16(0))
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(53).write_16(0))
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(52).write_16(0))
        await session.send_packet(PacketWriter().write_8(24).write_8(5).write_8(54).write_16(0))
        
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
        
        # Send ground items to the player who just joined the map
        await self.send_ground_items(session)
        
        # Send stats updates at the very end of login so client registers them properly
        await self.send_5_3_login(session)
        await asyncio.sleep(0.5) 
        await self.send_stats_update(session, levelup=False)
        await self.send_pet_list(session)
        
        logger.info(f"[{session.char_name}] Login complete.")

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
            return int(round(lvl * 2.0 + session.str_val * 2.0))
        return int(round(lvl * 1.4 + session.str_val * 2.0))

    def get_player_def(self, session: PlayerSession) -> int:
        """Calculate player physical defense."""
        lvl = session.level
        if session.element == 1:  # Earth
            return int(round(lvl * 3.0 + session.con_val * 2.0))
        return int(round(lvl * 2.0 + session.con_val * 2.0))

    def get_player_spd(self, session: PlayerSession) -> int:
        """Calculate player speed."""
        lvl = session.level
        if session.element == 4:  # Wind
            return int(round(lvl * 2.1 + session.agi_val * 2.2))
        return int(round(lvl * 1.6 + session.agi_val * 2.2))

    def get_player_matk(self, session: PlayerSession) -> int:
        """Calculate player magic attack."""
        lvl = session.level
        if session.element == 3:  # Fire
            return int(round(lvl * 1.6 + session.int_val * 2.0))
        return int(round(lvl * 1.4 + session.int_val * 2.0))

    def get_player_mdef(self, session: PlayerSession) -> int:
        """Calculate player magic defense."""
        lvl = session.level
        if session.element == 3:  # Fire
            return int(round(lvl * 2.0 + session.wis_val * 2.0))
        return int(round(lvl * 2.0 + session.wis_val * 2.0))
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
            
        p.write_32(0)
        p.write_string(session.char_name)
        p.write_string("")  # Nickname
        p.write_32(0)
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
            
        p.write_32(0)
        p.write_8(0)
        p.write_bool(session.reborn)
        p.write_8(session.job)
        p.write_string(session.char_name)
        p.write_string("")  # Nickname
        p.write_32(255)
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
                
        for slot, item in sorted(slots.items()):
            p.write_8(slot)
            p.write_16(item.get('item_id', 0))
            p.write_8(item.get('amount', 1))
            p.write_8(item.get('damage', 0))
            p.write_bytes(bytes(24))
            
        return p

    def build_equipments_packet(self, session: PlayerSession) -> PacketWriter:
        """Serializes SQLite equipped items to 19-byte blocks (AC 23 Sub 11)."""
        p = PacketWriter()
        p.write_8(23).write_8(11)
        for eq_id in session.equipments:
            if eq_id > 0:
                p.write_16(eq_id)
                p.write_8(0) # Damage
                p.write_bytes(bytes(16))
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
        """Sends map initialization packets as SEPARATE framed TCP packets.
        Each packet has its own header - the client parses them individually."""
        
        # 1. Map ID Info (23, 138) - always first
        await session.send_packet(PacketWriter().write_8(23).write_8(138))
        
        # 2. Add players on map (including self) and their confirmations
        # C# sends 10,3 for ALL players INCLUDING self (not just others)
        if session.map_id in self.map_players:
            for r in self.map_players[session.map_id]:
                await session.send_packet(PacketWriter().write_8(23).write_8(122).write_32(r.char_id))
                await session.send_packet(PacketWriter().write_8(10).write_8(3).write_32(r.char_id).write_8(255))
                await session.send_packet(PacketWriter().write_8(23).write_8(76).write_32(r.char_id))
                
        # Send visibility states of hidden map NPCs
        npcs = self.map_npcs.get(session.map_id, [])
        for npc in npcs:
            if npc.get('visible', True) is False:
                pkt_hide = PacketWriter()
                pkt_hide.write_8(22).write_8(6).write_16(npc['click_id']).write_8(0)
                await session.send_packet(pkt_hide)

        # 3. Map load complete trigger
        await session.send_packet(PacketWriter().write_8(23).write_8(102))
        
        # 4. Interface unlock
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

    async def handle_stat_allocation(self, session: PlayerSession, reader: PacketReader):
        """Handles stat point allocation (AC 6, Sub 1)."""
        ac = reader.read_8()
        sub = reader.read_8()
        stat_type = reader.read_8()
        
        # User requested to spend a stat point
        if getattr(session, 'points', 0) >= 1:
            session.points -= 1
            
            if stat_type == 1:
                session.str_val += 1
            elif stat_type == 2:
                session.con_val += 1
            elif stat_type == 3:
                session.int_val += 1
            elif stat_type == 4:
                session.wis_val += 1
            elif stat_type == 5:
                session.agi_val += 1
            else:
                logger.warning(f"[{session.char_name}] Unknown stat allocation type: {stat_type}")
                session.points += 1 # refund
                return
                
            self.save_player_to_db(session)
            await self.send_stats_update(session, levelup=True)
            logger.info(f"[{session.char_name}] Allocated 1 point to stat_type {stat_type}. Remaining points: {session.points}")
        else:
            logger.warning(f"[{session.char_name}] Tried to allocate stat without enough points.")

    async def handle_movement(self, session: PlayerSession, reader: PacketReader):
        """Processes character walking movement (AC 6)."""
        sub = reader.read_8()
        if sub == 1:
            direction = reader.read_8()
            x = reader.read_16()
            y = reader.read_16()
            
            session.x = x
            session.y = y
            
            # Broadcast movement update to map
            mov = PacketWriter()
            mov.write_8(6).write_8(1)
            mov.write_32(session.char_id)
            mov.write_8(direction)
            mov.write_16(x)
            mov.write_16(y)
            self.broadcast_to_map(session.map_id, mov, exclude_session=session)
            
            # Check auto-aggro (proximity combat)
            if not getattr(session, 'in_battle', False):
                await self.check_proximity_combat(session)

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
        session.quests[str(quest_id)] = state
        self.db.save_player(session)

    async def handle_interaction(self, session: PlayerSession, reader: PacketReader):
        """Processes portals, chest, and dialog clicks (AC 20)."""
        sub = reader.read_8()
        if sub == 8:  # Portal Collision Warp Request
            portal_id = reader.read_16()
            print(f"[PORTAL-RAW] {session.char_name} map={session.map_id} pos=({session.x},{session.y}) portal_id={portal_id} raw={reader.data.hex()}")
            logger.info(f"[{session.char_name}] Stepped on portal ID {portal_id} on map {session.map_id} pos=({session.x},{session.y}) (raw: {reader.data.hex()})")
            
            # Check portal warp cooldown (1.0 seconds)
            import time
            current_time = time.time()
            if current_time - getattr(session, 'last_warp_time', 0.0) < 1.0:
                logger.info(f"[{session.char_name}] Ignoring portal collision due to warp cooldown.")
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                return
            
            # Client portal_id may be Gray-coded. Try raw first, then Gray-decoded.
            dst_map, dst_x, dst_y = self.lookup_portal(session.map_id, portal_id, px=session.x, py=session.y)
            if dst_map is None:
                # Try Gray-decoded portal_id
                def _gray_decode(n):
                    mask = n
                    while mask:
                        mask >>= 1
                        n ^= mask
                    return n
                gray_id = _gray_decode(portal_id)
                if gray_id != portal_id:
                    logger.info(f"[{session.char_name}] Trying Gray-decoded portal_id: {portal_id} -> {gray_id}")
                    dst_map, dst_x, dst_y = self.lookup_portal(session.map_id, gray_id, px=session.x, py=session.y)
            
            if dst_map:
                print(f"[PORTAL] {session.char_name} used portal {portal_id} on map {session.map_id} -> map {dst_map} (x={dst_x}, y={dst_y})")
                logger.info(f"[PORTAL] {session.char_name} used portal {portal_id} on map {session.map_id} -> map {dst_map} (x={dst_x}, y={dst_y})")
                await self.warp_player(session, dst_map, dst_x, dst_y, portal_id)
            else:
                logger.warning(f"[{session.char_name}] Portal {portal_id} not found on map {session.map_id}!")
                # Notify GM chat warning about missing portal destination
                prompt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    f"Portal {portal_id} is not mapped in ServerDataBase.db. Use GM command :warp <map> <x> <y>."
                )
                await session.send_packet(prompt)
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 1:  # NPC click
            # İstemci paketi payload formatı: 20 01 00 00 00 [click_id] ...
            # decrypted_payload[5] (offset 4 after AC & Sub) click_id barındırır.
            if reader.remaining_bytes() >= 4:
                reader.read_bytes(3)  # Skip 3 bytes (unk/padding)
                click_id = reader.read_8()
            else:
                click_id = reader.read_8() if reader.remaining_bytes() > 0 else 0
            native_click_id = click_id
            logger.info(f"[{session.char_name}] Clicked NPC/Object ID {click_id} on map {session.map_id} (native ID: {native_click_id})")

            # Find the clicked NPC in the map NPCs list
            map_npcs = self.map_npcs.get(session.map_id, [])
            npc = None
            for n in map_npcs:
                if n['click_id'] == native_click_id:
                    npc = n
                    break
            
            if npc:
                # --- DOOR / PORTAL TRIGGER CHECK ---
                # If this NPC has linked_portals (unk2 field in eve.Emg), it acts as a door.
                # The linked portal IDs refer to warp portals in the same map's portal list.
                linked_portals = npc.get('linked_portals', [])
                if linked_portals:
                    # Use the first linked portal ID to perform the warp
                    portal_id = linked_portals[0]
                    logger.info(f"[{session.char_name}] NPC {native_click_id} is a door - triggering portal {portal_id} on map {session.map_id}")
                    dst_map, dst_x, dst_y = self.lookup_portal(session.map_id, portal_id)
                    if dst_map:
                        logger.info(f"[DOOR] {session.char_name} used door NPC {native_click_id} (portal {portal_id}) -> map {dst_map} ({dst_x},{dst_y})")
                        await self.warp_player(session, dst_map, dst_x, dst_y, portal_id)
                    else:
                        logger.warning(f"[DOOR] Door NPC {native_click_id} linked portal {portal_id} has no destination on map {session.map_id}!")
                        await session.send_packet(PacketWriter().write_8(20).write_8(8))
                    return
                
                npc_id = npc['npc_id']
                
                # Dynamic NPC ID mapping resolver
                db_id = None
                row = None
                try:
                    conn = sqlite3.connect(self.static_db_path)
                    conn.row_factory = sqlite3.Row
                    
                    # 1. Hardcoded overrides for maps (e.g. Map 10017 - Starter Ship Deck)
                    overrides = {
                        (10017, 9): 25787,   # Crew on Deck
                        (10017, 10): 25789,  # Captain
                        (10017, 3): 25786,   # Crew
                        (10017, 11): 25786,  # Crew
                    }
                    if (session.map_id, native_click_id) in overrides:
                        db_id = overrides[(session.map_id, native_click_id)]
                        row = conn.execute("SELECT * FROM npc_data WHERE id = ?", (db_id,)).fetchone()
                    
                    # 2. Try formula candidates sequentially if not resolved by overrides
                    if not row:
                        decoded_id = ((npc_id & 0xFFFF) ^ 0x5209) - 9
                        candidates = [
                            decoded_id + 27000,
                            decoded_id + 10000,
                            decoded_id,
                            npc_id * 2,
                            npc_id + 16000,
                            npc_id
                        ]
                        for cand_id in candidates:
                            r = conn.execute("SELECT * FROM npc_data WHERE id = ?", (cand_id,)).fetchone()
                            if r:
                                db_id = cand_id
                                row = r
                                break
                                
                    # 3. Try fallback query using map_tid
                    if not row:
                        for tid in [npc_id - 1, npc_id]:
                            r = conn.execute("SELECT * FROM npc_data WHERE map_tid = ? LIMIT 1", (tid,)).fetchone()
                            if r:
                                db_id = r['id']
                                row = r
                                break
                    
                    # 4. Ultimate fallback
                    if not row:
                        db_id = npc_id * 2
                        row = conn.execute("SELECT * FROM npc_data WHERE id = ?", (db_id,)).fetchone()
                        
                    conn.close()
                except Exception as e:
                    logger.error(f"[NPC Click] Error querying npc_data: {e}")
                
                logger.info(f"[NPC Click] Clicked NPC '{npc['name']}' (ID: {click_id}, template: {npc_id}, db_id: {db_id})")
                
                if row:
                    name = (row['name'] or "").strip('\x00').strip()
                    npc_template_id = npc_id  # template ID from eve.Emg
                    talk_id = 1  # Hardcode to small valid portrait index (1) instead of DB dummy 58645
                    logger.info(f"[NPC Click] Query success: name='{name}', npc_template={npc_template_id}, talk_id={talk_id}")
                else:
                    name = "NPC"
                    npc_template_id = npc_id
                    talk_id = 1
                    logger.info(f"[NPC Click] Query failed. Using defaults.")
                    
                # ── QUEST BATTLES ──
                quest_info = self.quest_manager.get_quest_battle(npc_template_id)
                if quest_info:
                    logger.info(f"[{session.char_name}] Starting quest battle with NPC {npc_template_id}!")
                    session.quest_battle_id = npc_template_id
                    session.battle_win_warp = {
                        "map_id": quest_info["win_map_id"],
                        "x": quest_info["win_x"],
                        "y": quest_info["win_y"]
                    }
                    session.battle_bg_id = quest_info["bg_id"]
                    battle_sprite = quest_info["battle_sprite_id"]
                    
                    await self.enter_battle(session, native_click_id, npc_template_id, battle_sprite)
                    return    
                    
                # Check if the NPC is a shopkeeper or merchant
                is_shopkeeper = any(x in name.lower() for x in ["shopkeeper", "merchant", "clerk", "taverner", "bartender", "pet keeper"])
                if is_shopkeeper or native_click_id == 23:
                    # Send official Props Shop dialogue packet for NPC 23
                    if "props" in name.lower() or native_click_id == 23:
                        dialog_hex = "140100000001060317000000000000050001"
                        dialog_bytes = bytes.fromhex(dialog_hex)[2:] # Skip 14 01
                        pkt = PacketWriter().write_8(20).write_8(1).write_bytes(dialog_bytes)
                        await session.send_packet(pkt)
                        return
                        
                    # Determine event ID from eve.Emg: 34 for Weapon Shopkeeper, 31 for Props Shopkeeper
                    shop_id = 34 if "weapon" in name.lower() else 31
                    
                    # Send shop items list (AC 54 Sub 89) and open shop command (AC 54 Sub 1)
                    for s_id in [shop_id, 2, native_click_id]:
                        shop_pkt = PacketWriter()
                        shop_pkt.write_8(54).write_8(89).write_8(s_id).write_8(2) # Tab count 2
                        
                        # Tab 1 items
                        shop_pkt.write_16(602).write_8(1)
                        shop_pkt.write_16(603).write_8(1)
                        
                        # Tab 2 items
                        shop_pkt.write_16(701).write_8(2)
                        shop_pkt.write_16(702).write_8(2)
                        shop_pkt.write_16(703).write_8(2)
                        
                        await session.send_packet(shop_pkt)
                        
                        # Send shop trigger/open command (AC 54 Sub 1)
                        open_shop = PacketWriter()
                        open_shop.write_8(54).write_8(1).write_8(s_id).write_8(native_click_id)
                        await session.send_packet(open_shop)
                    
                    # Release client action lock to finalize transaction and render shop UI
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
                else:
                    # Check if the NPC is a combat/monster NPC (regular click-to-fight mob)
                    decoded_id = ((npc_template_id & 0xFFFF) ^ 0x5209) - 9
                    is_monster = (
                        str(npc_template_id) in self.drop_tables or
                        str(decoded_id) in self.drop_tables or
                        str(decoded_id + 27000) in self.drop_tables or
                        str(decoded_id + 10000) in self.drop_tables or
                        any(x in name.lower() for x in ["monster", "spider", "wolf", "troll", "grape", "crab", "gelly", "wasp", "snake", "boar", "brother", "sister", "lord", "dinosaur", "stegosaurus", "shark"]) or
                        (17000 <= npc_template_id <= 18000)
                    )
                    if is_monster:
                        logger.info(f"[{session.char_name}] Clicked monster NPC {npc_template_id} ({name}) -> entering battle!")
                        await self.enter_battle(session, native_click_id, npc_template_id)
                        return

                    # Check if NPC has a quest script
                    # We first try to match by the unique DB ID. If not found, we fallback to the local native_click_id.
                    # For small click IDs (< 100), we restrict them to starter maps (10000 - 10100) to prevent map collisions.
                    is_starter_map = 10000 <= session.map_id < 10100
                    
                    quest_trigger_id = None
                    if db_id and db_id in self.quest_scripts:
                        quest_trigger_id = db_id
                    elif native_click_id in self.quest_scripts:
                        if native_click_id >= 100 or is_starter_map:
                            quest_trigger_id = native_click_id
                            
                    if quest_trigger_id is not None:
                        script = self.quest_scripts[quest_trigger_id]
                        if len(script) > 0:
                            logger.info(f"[{session.char_name}] Starting quest script for NPC {quest_trigger_id} (clicked {native_click_id})")
                            session.active_quest_id = quest_trigger_id
                            session.active_quest_step = 0
                            session.active_quest_dialog_counter = 1  # tracks per-step dialog sequence number
                            action = script[0]
                            if action["type"] == "dialog":
                                portrait = 3 if action.get('is_quest') else 7  # 03=NPC speech, 07=player
                                await self._send_quest_dialogue(session, action["hex"], native_click_id, step=1, portrait_type=portrait)
                            return

                    # Default fallback dialogue for non-shopkeeper NPCs
                    dialogue_text = "Hello, traveller! Beautiful day, isn't it? Let me know if you need anything."
                    pkt = PacketWriter()
                    pkt.write_8(52).write_8(1).write_16(1).write_string(dialogue_text)
                    logger.info(f"[NPC Click] Sending dialogue (AC 52 Sub 1): talk_id=1, text='{dialogue_text}'")
                    await session.send_packet(pkt)
                    
                    # Release client action lock to finalize transaction and render dialogue UI
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 6:  # Continue interaction
            logger.info(f"[{session.char_name}] Continue interaction (AC 20 Sub 6)")
            # Check post-battle quest warp
            win_warp = getattr(session, 'battle_win_warp', None)
            if win_warp:
                session.battle_win_warp = None
                logger.info(f"[{session.char_name}] Triggering post-battle quest warp to map {win_warp['map_id']} pos=({win_warp['x']},{win_warp['y']})")
                await self.warp_player(session, win_warp['map_id'], win_warp['x'], win_warp['y'])
                return
            
            # Check pending battle unlock
            if getattr(session, 'pending_battle_unlock', False):
                session.pending_battle_unlock = False
                logger.info(f"[{session.char_name}] Post-battle unlock: sending map ready and unlock")
                await session.send_packet(PacketWriter().write_8(23).write_8(102))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                return
            # Handle active quest script
            if session.active_quest_id is not None:
                script = self.quest_scripts.get(session.active_quest_id, [])
                session.active_quest_step += 1
                
                # Check if we reached the end of the script
                if session.active_quest_step >= len(script):
                    logger.info(f"[{session.char_name}] Finished quest script for NPC {session.active_quest_id}")
                    session.active_quest_id = None
                    session.active_quest_step = 0
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
                    return
                
                # Execute next action
                action = script[session.active_quest_step]
                step_num = getattr(session, 'active_quest_dialog_counter', 1)
                
                # Some actions (like spawn) require multiple packets or have embedded dialogs
                if action["type"] == "spawn":
                    await self._send_quest_spawn(session, action["hex"])
                    if "dialog_hex" in action:
                        await self._send_quest_dialogue(session, action["dialog_hex"], session.active_quest_id, step=step_num)
                        session.active_quest_dialog_counter = step_num + 1
                elif action["type"] == "dialog":
                    portrait = 3 if action.get('is_quest') else 7
                    await self._send_quest_dialogue(session, action["hex"], session.active_quest_id, step=step_num, portrait_type=portrait)
                    session.active_quest_dialog_counter = step_num + 1
                elif action["type"] == "flag":
                    await self._send_quest_flag(session, action["quest_id"], action["state"])
                    # After a flag, continue the script immediately (flag+dialog in same response)
                    # Check if there's a next dialog step
                    next_step = session.active_quest_step + 1
                    if next_step < len(script) and script[next_step]["type"] == "dialog":
                        session.active_quest_step = next_step
                        next_action = script[next_step]
                        portrait = 3 if next_action.get('is_quest') else 7
                        await self._send_quest_dialogue(session, next_action["hex"], session.active_quest_id, step=step_num, portrait_type=portrait)
                        session.active_quest_dialog_counter = step_num + 1
                    else:
                        logger.info(f"[{session.char_name}] Quest script flag sent. Unlocking.")
                        session.active_quest_id = None
                        session.active_quest_step = 0
                        session.active_quest_dialog_counter = 1
                        await session.send_packet(PacketWriter().write_8(20).write_8(8))
                
                return

            await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 9:  # Select dialogue option
            option_id = reader.read_8()
            logger.info(f"[{session.char_name}] Selected dialogue option {option_id} (Hex: {hex(option_id)})")
            
            # Check if this is the Props Shop Buy/Sell dialogue
            if option_id == 0x1f:  # Option 31: Buy
                await session.send_packet(PacketWriter().write_8(27).write_8(3))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                return
            elif option_id == 0x1e:  # Option 30: Sell
                # Send the "Sell" cursor/dialogue state
                sell_hex = "140100000001060317000000000000060002"
                sell_bytes = bytes.fromhex(sell_hex)[2:]
                pkt = PacketWriter().write_8(20).write_8(1).write_bytes(sell_bytes)
                await session.send_packet(pkt)
                return
                
            # Release client action lock after selection
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
        else:
            logger.warning(f"[{session.char_name}] Unhandled AC 20 Sub: {sub}")
            await session.send_packet(PacketWriter().write_8(20).write_8(8))

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
        
    async def handle_warp_done(self, session: PlayerSession, reader: PacketReader):
        """Processes map loading complete response from client (AC 12)."""
        sub = reader.read_8()
        if sub == 1:
            session.is_warping = False
            session.in_map = True
            
            # Set warp cooldown timestamp when warp completes successfully
            import time
            session.last_warp_time = time.time()
            
            # Send warp completion unlock packets
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            
            # Broadcast our appearance to other players on new map (remote format)
            self.broadcast_to_map(session.map_id, self.build_remote_char_spawn(session), exclude_session=session)
            
            logger.info(f"[{session.char_name}] Warp completed successfully.")

    async def handle_action_23(self, session: PlayerSession, reader: PacketReader):
        """Handles item and inventory actions (AC 23)."""
        sub = reader.read_8()
        if sub == 54:
            # Client sends this as acknowledgment after receiving the login/warp complete signal (5, 4).
            # The C# server also does nothing in response — the client transitions autonomously.
            logger.info(f"[{session.char_name}] Received warp-done ACK (23, 54) — client should now enter game")
            session.is_warping = False
            session.in_map = True
        elif sub == 10:  # Move item in inventory
            src = reader.read_8()
            ammt = reader.read_8()
            dst = reader.read_8()
            
            if 1 <= src <= 50 and 1 <= dst <= 50 and ammt > 0:
                item = get_item_at_slot(session, src)
                if item:
                    item_id = item['item_id']
                    # Remove from src
                    remove_item_at_slot(session, src, ammt)
                    # Add to dst
                    add_item_to_inventory(session, item_id, amount=ammt, slot=dst)
                    
                    self.save_player_to_db(session)
                    
                    # Send confirmation: 23, 10, src, ammt, dst
                    move_confirm = PacketWriter().write_8(23).write_8(10).write_8(src).write_8(ammt).write_8(dst)
                    await session.send_packet(move_confirm)
        elif sub == 11:  # Wear/Equip item
            loc = reader.read_8()  # inventory slot (1-50)
            item = get_item_at_slot(session, loc)
            if item:
                item_id = item['item_id']
                slot_idx = get_equip_slot(item_id)
                
                # Check if we already have something equipped in this slot
                old_equip_id = session.equipments[slot_idx]
                
                # Wear the new item
                session.equipments[slot_idx] = item_id
                
                # Remove the worn item from inventory
                remove_item_at_slot(session, loc, 1)
                
                # If we had an old equipped item, put it back in the inventory at slot 'loc'
                if old_equip_id > 0:
                    add_item_to_inventory(session, old_equip_id, amount=1, slot=loc)
                
                # Save to database
                self.save_player_to_db(session)
                
                # Send stats update
                await self.send_stats_update(session)
                        
                # Send confirmation: 23, 17, loc, loc
                wear_confirm = PacketWriter().write_8(23).write_8(17).write_8(loc).write_8(loc)
                await session.send_packet(wear_confirm)
                
                # Send new equipments packet to update locally
                await session.send_packet(self.build_equipments_packet(session))
                
                # Broadcast equipment update and spawn refresh to other players
                other_equip = self.build_other_player_equip(session)
                self.broadcast_to_map(session.map_id, other_equip, exclude_session=session)
                
                refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                self.broadcast_to_map(session.map_id, refresh)
        elif sub == 12:  # Unwear/Unequip item
            loc = reader.read_8()  # equipment slot (1-6)
            dst = reader.read_8()  # inventory target slot (1-50)
            
            if 1 <= loc <= 6 and 1 <= dst <= 50:
                slot_idx = loc - 1
                equip_id = session.equipments[slot_idx]
                
                if equip_id > 0:
                    slot = add_item_to_inventory(session, equip_id, amount=1, slot=dst)
                    if slot is not None:
                        # Clear the equipment slot
                        session.equipments[slot_idx] = 0
                        
                        # Save to database
                        self.save_player_to_db(session)
                        
                        # Send stats update
                        await self.send_stats_update(session)
                                        
                        # Send confirmation: 23, 16, loc, dst
                        unwear_confirm = PacketWriter().write_8(23).write_8(16).write_8(loc).write_8(dst)
                        await session.send_packet(unwear_confirm)
                        
                        # Send new equipments packet to update locally
                        await session.send_packet(self.build_equipments_packet(session))
                        
                        # Broadcast equipment update and spawn refresh to other players
                        other_equip = self.build_other_player_equip(session)
                        self.broadcast_to_map(session.map_id, other_equip, exclude_session=session)
                        
                        refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                        self.broadcast_to_map(session.map_id, refresh)
        elif sub == 3:  # Drop item on ground
            pos = reader.read_8()
            qnt = reader.read_8()
            if reader.offset < len(reader.data):
                reader.read_8()  # Unused byte (ukn)
                
            if 1 <= pos <= 50 and qnt > 0:
                item = get_item_at_slot(session, pos)
                if item:
                    item_id = item['item_id']
                    
                    # Initialize map ground items if not present
                    if session.map_id not in self.map_ground_items:
                        self.map_ground_items[session.map_id] = [None] * 256
                        
                    # Find a free slot on ground
                    free_idx = -1
                    for idx in range(256):
                        if self.map_ground_items[session.map_id][idx] is None:
                            free_idx = idx
                            break
                            
                    if free_idx != -1:
                        # Remove from inventory
                        remove_item_at_slot(session, pos, qnt)
                        self.save_player_to_db(session)
                        
                        # Clear or update slot visually on client:
                        remaining_amt = 0
                        for it in session.inventory:
                            if it.get('slot') == pos:
                                remaining_amt = it.get('amount', 0)
                                break
                        slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                        await session.send_packet(slot_pkt)
                        
                        # Place on ground
                        self.map_ground_items[session.map_id][free_idx] = {
                            "item_id": item_id,
                            "x": session.x,
                            "y": session.y,
                            "amount": qnt
                        }
                        
                        # Spawn for player (with drop animation)
                        spawn_self = PacketWriter()
                        spawn_self.write_8(23).write_8(3)
                        spawn_self.write_16(encode_item16(item_id))
                        spawn_self.write_16(session.x)
                        spawn_self.write_16(session.y)
                        spawn_self.write_32(free_idx + 1)
                        spawn_self.write_8(1)  # Play drop animation
                        await session.send_packet(spawn_self)
                        
                        # Broadcast to others on map
                        spawn_others = PacketWriter()
                        spawn_others.write_8(23).write_8(3)
                        spawn_others.write_16(encode_item16(item_id))
                        spawn_others.write_16(session.x)
                        spawn_others.write_16(session.y)
                        spawn_others.write_32(free_idx + 1)
                        spawn_others.write_8(0)  # Spawn silently
                        self.broadcast_to_map(session.map_id, spawn_others, exclude_session=session)

                        
                        logger.info(f"[{session.char_name}] Dropped item {item_id} (qnt {qnt}) on map {session.map_id} slot {free_idx+1}")
                    else:
                        # Ground full - fallback to normal destroy/confirm
                        remove_item_at_slot(session, pos, qnt)
                        self.save_player_to_db(session)
                        
                        remaining_amt = 0
                        for it in session.inventory:
                            if it.get('slot') == pos:
                                remaining_amt = it.get('amount', 0)
                                break
                        slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                        await session.send_packet(slot_pkt)
                        
                        destroy_confirm = PacketWriter().write_8(23).write_8(26).write_16(encode_item16(item_id)).write_8(qnt)
                        await session.send_packet(destroy_confirm)
                        
        elif sub == 124:  # Destroy item
            pos = reader.read_8()
            qnt = reader.read_8()
            if reader.offset < len(reader.data):
                reader.read_8()  # Unused byte (ukn)
                
            if 1 <= pos <= 50 and qnt > 0:
                item = get_item_at_slot(session, pos)
                if item:
                    item_id = item['item_id']
                    remove_item_at_slot(session, pos, qnt)
                    self.save_player_to_db(session)
                    
                    # Clear or update slot visually on client:
                    remaining_amt = 0
                    for it in session.inventory:
                        if it.get('slot') == pos:
                            remaining_amt = it.get('amount', 0)
                            break
                    slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                    await session.send_packet(slot_pkt)
                    
                    # Confirm destroy: 23, 26, item_id (16-bit), qnt (8-bit)
                    destroy_confirm = PacketWriter().write_8(23).write_8(26).write_16(encode_item16(item_id)).write_8(qnt)
                    await session.send_packet(destroy_confirm)

                    
                    logger.info(f"[{session.char_name}] Destroyed item {item_id} (qnt {qnt})")

        elif sub == 2:  # Pick up item from ground
            pos = reader.read_8()  # Ground slot index (1-based)
            
            if session.map_id in self.map_ground_items and 1 <= pos <= 256:
                gi = self.map_ground_items[session.map_id][pos - 1]
                if gi is not None:
                    item_id = gi["item_id"]
                    qnt = gi["amount"]
                    is_gold = gi.get("is_gold", False)
                    
                    success = False
                    if is_gold:
                        session.gold += qnt
                        self.save_player_to_db(session)
                        # Send gold update packet to client:
                        await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                        success = True
                    else:
                        slot = add_item_to_inventory(session, item_id, amount=qnt)
                        if slot is not None:
                            # Send item add success packet to client:
                            item_pkt = PacketWriter()
                            item_pkt.write_8(23).write_8(6).write_8(0).write_8(slot).write_16(qnt).write_16(encode_item16(item_id)).write_bytes(bytes(25))
                            await session.send_packet(item_pkt)
                            success = True
                            
                    if success:
                        # Clear ground slot
                        self.map_ground_items[session.map_id][pos - 1] = None
                        self.save_player_to_db(session)
                        
                        # Send pickup confirmation to player: [23, 2, item_id(ushort), 1]
                        pickup_self = PacketWriter()
                        pickup_self.write_8(23).write_8(2)
                        pickup_self.write_16(encode_item16(item_id))  # ItemID, NOT ground slot index!
                        pickup_self.write_8(1)  # plays pickup sound/adds to inventory
                        await session.send_packet(pickup_self)
                        
                        # Broadcast to others: [23, 2, item_id(ushort), 0]
                        pickup_others = PacketWriter()
                        pickup_others.write_8(23).write_8(2)
                        pickup_others.write_16(encode_item16(item_id))  # ItemID, NOT ground slot index!
                        pickup_others.write_8(0)
                        self.broadcast_to_map(session.map_id, pickup_others, exclude_session=session)
                        
                        # Update inventory locally
                        await session.send_packet(self.build_inventory_packet(session))
                        
                        logger.info(f"[{session.char_name}] Picked up {'gold (' + str(qnt) + ')' if is_gold else 'item ' + str(item_id) + ' (qnt ' + str(qnt) + ')'} from ground slot {pos}")

        elif sub == 16:  # Drop gold on ground
            amount = reader.read_32()
            if session.gold >= amount and amount > 0:
                # Initialize map ground items if not present
                if session.map_id not in self.map_ground_items:
                    self.map_ground_items[session.map_id] = [None] * 256
                    
                # Find a free slot on ground
                free_idx = -1
                for idx in range(256):
                    if self.map_ground_items[session.map_id][idx] is None:
                        free_idx = idx
                        break
                        
                if free_idx != -1:
                    # Deduct gold
                    session.gold -= amount
                    self.save_player_to_db(session)
                    
                    # Update gold display on client: [26, 4, gold]
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    
                    # Place on ground (Gold Bag visual model set to Blue Potion 27005)
                    self.map_ground_items[session.map_id][free_idx] = {
                        "item_id": 27005,
                        "x": session.x,
                        "y": session.y,
                        "amount": amount,
                        "is_gold": True
                    }
                    
                    # Spawn for player (with drop animation)
                    spawn_self = PacketWriter()
                    spawn_self.write_8(23).write_8(3)
                    spawn_self.write_16(27005)
                    spawn_self.write_16(session.x)
                    spawn_self.write_16(session.y)
                    spawn_self.write_32(free_idx + 1)
                    spawn_self.write_8(1)  # Play drop animation
                    await session.send_packet(spawn_self)
                    
                    # Confirm gold drop: [26, 4, gold_amount] already sent above for visual update.
                    # Send additional gold drop/discard confirmation: [23, 16, amount(uint32)]
                    await session.send_packet(PacketWriter().write_8(23).write_8(16).write_32(amount))
                    # Also send generic discard confirm
                    await session.send_packet(PacketWriter().write_8(23).write_8(26).write_16(27005).write_8(1))
                    
                    # Broadcast to others on map
                    spawn_others = PacketWriter()
                    spawn_others.write_8(23).write_8(3)
                    spawn_others.write_16(27005)
                    spawn_others.write_16(session.x)
                    spawn_others.write_16(session.y)
                    spawn_others.write_32(free_idx + 1)
                    spawn_others.write_8(0)  # Spawn silently
                    self.broadcast_to_map(session.map_id, spawn_others, exclude_session=session)
                    
                    logger.info(f"[{session.char_name}] Dropped gold ({amount}) on map {session.map_id} slot {free_idx+1}")
        else:
            logger.info(f"Unhandled AC 23 Sub-Code: {sub}, payload: {reader.data.hex()}")

    async def handle_action_33(self, session: PlayerSession, reader: PacketReader):
        """Processes settings changes (AC 33)."""
        sub = reader.read_8()
        if sub == 1:
            setting_type = reader.read_8()
            if setting_type == 1:
                session.pkable = not session.pkable
                val = 1 if session.pkable else 2
            elif setting_type == 2:
                session.joinable = not session.joinable
                val = 1 if session.joinable else 2
            elif setting_type == 4:
                session.tradable = not session.tradable
                val = 1 if session.tradable else 2
            else:
                return
                
            resp = PacketWriter().write_8(33).write_8(1).write_8(setting_type).write_8(val)
            await session.send_packet(resp)

    async def handle_action_37(self, session: PlayerSession, reader: PacketReader):
        """Processes companion detail requests (AC 37)."""
        sub = reader.read_8()
        if sub == 1:
            slot = reader.read_8()
            logger.info(f"[{session.char_name}] Requested stats for pet in slot {slot}")
            await self.send_pet_stats(session, slot)

    async def handle_action_15(self, session: PlayerSession, reader: PacketReader):
        """Processes companion and pet actions (AC 15)."""
        sub = reader.read_8()
        
        if sub == 2:  # Dismiss Pet
            slot = reader.read_8()
            if 1 <= slot <= len(session.pets):
                pet = session.pets[slot - 1]
                pet_id = pet.get("pet_id")
                logger.info(f"[{session.char_name}] Dismissing pet {pet_id} from slot {slot}")
                
                # Check if this pet is currently in battle, rest it first
                if pet.get("in_battle", False):
                    # Broadcast despawn
                    despawn = PacketWriter().write_8(19).write_8(7).write_32(session.char_id)
                    self.broadcast_to_map(session.map_id, despawn)
                    
                    # Broadcast appearance update
                    refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                    self.broadcast_to_map(session.map_id, refresh)
                
                # Remove pet
                session.pets.pop(slot - 1)
                
                # Save changes
                try:
                    self.save_player_to_db(session)
                except Exception as db_err:
                    logger.error(f"[Dismiss Pet] Error saving to DB: {db_err}")
                
                # Send dismiss confirmation: AC 15 Sub 2, owner ID, slot index
                dismiss_pkt = PacketWriter().write_8(15).write_8(2).write_32(session.char_id).write_8(slot)
                await session.send_packet(dismiss_pkt)
                
                # Refresh companion list
                await self.send_pet_list(session)
                
        elif sub == 4:  # Toggle Battle/Rest
            slot = reader.read_8()
            state = reader.read_8()
            
            if 1 <= slot <= len(session.pets):
                pet = session.pets[slot - 1]
                pet_id = pet.get("pet_id")
                
                if state == 1:  # Bring into battle (spawn on map)
                    logger.info(f"[{session.char_name}] Setting pet {pet_id} at slot {slot} to BATTLE state")
                    
                    # Update pet in_battle state
                    for idx, p in enumerate(session.pets):
                        p["in_battle"] = (idx == slot - 1)
                        
                    # 1. Send owner packet: AC 19 Sub 4
                    pp = PacketWriter().write_8(19).write_8(4).write_32(session.char_id).write_32(pet_id)
                    await session.send_packet(pp)
                    
                    # 2. Broadcast companion spawn to map: AC 15 Sub 4
                    spawn = PacketWriter().write_8(15).write_8(4)
                    spawn.write_32(session.char_id)
                    spawn.write_32(pet_id)
                    spawn.write_8(0)
                    spawn.write_8(1)
                    
                    # Look up pet template name
                    pet_name = "Companion"
                    try:
                        conn = sqlite3.connect(self.static_db_path)
                        conn.row_factory = sqlite3.Row
                        row = conn.execute("SELECT name FROM npc_data WHERE id = ?", (pet_id,)).fetchone()
                        conn.close()
                        if row:
                            pet_name = row['name'].strip('\x00').strip()
                    except Exception as e:
                        logger.error(f"[Pet Spawn] Error getting name for pet template {pet_id}: {e}")
                    
                    spawn.write_string(pet_name)
                    spawn.write_16(0)  # Weapon ID placeholder
                    
                    self.broadcast_to_map(session.map_id, spawn)
                    
                    # 3. Broadcast force refresh player appearance: AC 5 Sub 8
                    refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                    self.broadcast_to_map(session.map_id, refresh)
                    
                else:  # Standby / Rest pet
                    logger.info(f"[{session.char_name}] Setting pet {pet_id} at slot {slot} to REST state")
                    pet["in_battle"] = False
                    
                    # 1. Send rest owner confirmation: AC 19 Sub 2
                    rest_owner = PacketWriter().write_8(19).write_8(2)
                    await session.send_packet(rest_owner)
                    
                    # 2. Broadcast despawn to map: AC 19 Sub 7
                    despawn = PacketWriter().write_8(19).write_8(7).write_32(session.char_id)
                    self.broadcast_to_map(session.map_id, despawn)
                    
                    # 3. Broadcast force refresh player appearance: AC 5 Sub 8
                    refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                    self.broadcast_to_map(session.map_id, refresh)
                    
                # Save changes
                try:
                    self.save_player_to_db(session)
                except Exception as db_err:
                    logger.error(f"[Pet Battle Toggle] Error saving to DB: {db_err}")
                    
        elif sub in [16, 17]:
            logger.info(f"[{session.char_name}] Companion ride action received: sub={sub}")

    async def handle_chat_gm(self, session: PlayerSession, reader: PacketReader):
        """Processes chat messages and GM commands (AC 2)."""
        sub = reader.read_8()
        if sub == 2:
            msg = reader.read_string_n()
            words = msg.split(' ')
            
            if words[0] == ":warp" and len(words) >= 4:
                try:
                    dst_map = int(words[1])
                    dst_x = int(words[2])
                    dst_y = int(words[3])
                    await self.warp_player(session, dst_map, dst_x, dst_y)
                except ValueError:
                    pass
            elif words[0] == ":propshop":
                await session.send_packet(PacketWriter().write_8(27).write_8(3))
            elif words[0] == ":item" and len(words) >= 3 and words[1] == "add":
                try:
                    item_id = int(words[2])
                    amount = int(words[3]) if len(words) >= 4 else 1
                    
                    slot = add_item_to_inventory(session, item_id, amount=amount)
                    if slot is not None:
                        self.save_player_to_db(session)
                        
                        # Send item add success packet to client:
                        # [23, 6, slot(8), item_id (uint16), ammt (8), 0, 24 bytes of zero]
                        item_pkt = PacketWriter()
                        item_pkt.write_8(23).write_8(6).write_8(0).write_8(slot).write_16(amount).write_16(encode_item16(item_id)).write_bytes(bytes(25))
                        await session.send_packet(item_pkt)
                            
                        # System chat confirmation
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Item {item_id} added to inventory."
                        )
                        await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":level" and len(words) >= 2:
                try:
                    level_num = int(words[1])
                    level_num = max(1, min(199, level_num))
                    session.exp = self.get_cumulative_exp_for_level(level_num, session.reborn)
                    session.level = level_num
                    session.update_max_hp_sp()
                    session.hp = session.max_hp
                    session.sp = session.max_sp
                    
                    await self.send_stats_update(session)
                    self.save_player_to_db(session)
                    
                    # Chat confirmation
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Level set to {session.level}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":stat" and len(words) >= 6:
                try:
                    str_val = int(words[1])
                    con_val = int(words[2])
                    int_val = int(words[3])
                    wis_val = int(words[4])
                    agi_val = int(words[5])
                    
                    session.str_val = max(1, str_val)
                    session.con_val = max(1, con_val)
                    session.int_val = max(1, int_val)
                    session.wis_val = max(1, wis_val)
                    session.agi_val = max(1, agi_val)
                    
                    session.update_max_hp_sp()
                    session.hp = session.max_hp
                    session.sp = session.max_sp
                    
                    await self.send_stats_update(session)
                    self.save_player_to_db(session)
                    
                    # Chat confirmation
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        "Base stats updated successfully."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":gold" and len(words) >= 2:
                try:
                    gold_amt = int(words[1])
                    session.gold = max(0, gold_amt)
                    
                    # Gold update packet (26, 4)
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    self.save_player_to_db(session)
                    
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Gold set to {session.gold}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":heal":
                session.hp = session.max_hp
                session.sp = session.max_sp
                
                await self.send_stats_update(session)
                        
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    "HP and SP fully restored."
                )
                await session.send_packet(sys_msg)
            elif words[0] == ":element" and len(words) >= 2:
                try:
                    element_num = int(words[1])
                    if 0 <= element_num <= 4:
                        session.element = element_num
                        
                        await self.send_stats_update(session)
                        self.save_player_to_db(session)
                        
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                            f"Element set to {session.element}."
                        )
                        await session.send_packet(sys_msg)
                except ValueError:
                    pass
            elif words[0] == ":clear":
                session.inventory = []
                self.save_player_to_db(session)
                
                # Send empty inventory packet
                await session.send_packet(self.build_inventory_packet(session))
                
                sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                    "Inventory cleared."
                )
                await session.send_packet(sys_msg)
            elif words[0] == ":skill" and len(words) >= 2:
                try:
                    skill_id = int(words[1])
                    grade = int(words[2]) if len(words) >= 3 else 1
                    
                    exists = False
                    for sk in session.skills:
                        if sk['skill_id'] == skill_id:
                            sk['grade'] = grade
                            exists = True
                            break
                    if not exists:
                        session.skills.append({
                            "skill_id": skill_id,
                            "grade": grade,
                            "exp": 0
                        })
                    
                    self.save_player_to_db(session)
                                
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                        f"Skill {skill_id} learned/updated to grade {grade}."
                    )
                    await session.send_packet(sys_msg)
                except ValueError:
                    pass
            else:
                # Regular chat: broadcast to map
                chat_pkt = PacketWriter()
                chat_pkt.write_8(2).write_8(2)
                chat_pkt.write_32(session.char_id)
                chat_pkt.write_string_n(msg)
                self.broadcast_to_map(session.map_id, chat_pkt, exclude_session=session)

    # ─── Monster stat helpers ─────────────────────────────────────────────────
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

    async def handle_combat(self, session: 'PlayerSession', reader: PacketReader):
        """AC 11: İstemciden gelen savaş başlatma/aksiyon isteği."""
        sub = reader.read_8()
        logger.info(f"[{session.char_name}] handle_combat sub={sub}")
        if sub == 1:
            # Kaçma (Flee) isteği
            escape_type = reader.read_8() if reader.remaining_bytes() > 0 else 0
            logger.info(f"[{session.char_name}] Flee request: escape_type={escape_type}")
            battle_id = getattr(session, 'pvp_battle_id', None)
            if battle_id and battle_id in self.active_battles:
                battle = self.active_battles[battle_id]
                await self._do_flee(session, battle)
        elif sub == 2:
            # İstemci bir NPC'ye tıkladı (Savaş başlatma)
            # Wireshark analizi:
            #   pkType (1 byte)
            #   rawTargetID (4 bytes) -> targetID = rawTargetID >> 8
            #   clickID (2 bytes)
            if reader.remaining_bytes() < 7:
                logger.warning(f"[{session.char_name}] handle_combat sub=2 has too few bytes: {reader.remaining_bytes()}")
                return
            pk_type = reader.read_8()
            raw_target_id = reader.read_32()
            npc_id = raw_target_id >> 8
            npc_click_id = reader.read_16()
            logger.info(f"[{session.char_name}] Combat request: pk_type={pk_type} npc_id={npc_id} npc_click={npc_click_id}")
            await self._start_pve_battle(session, npc_click_id, npc_id)

    async def _start_pve_battle(self, session: 'PlayerSession', click_id: int, npc_id: int,
                                override_sprite_id: int = 0):
        """PvE savaşını başlatır. Wireshark analizine göre doğru paket sırası."""
        import os, sqlite3, random

        if getattr(session, 'in_battle', False):
            logger.warning(f"[{session.char_name}] Already in battle, skipping")
            return

        # ── Monster verisi ──────────────────────────────────────────────────
        # Decode the raw NPC ID to match database ID
        mapped_npc_id = ((npc_id & 0xFFFF) ^ 0x5209) - 9
        mapped_override_id = (((override_sprite_id & 0xFFFF) ^ 0x5209) - 9) if override_sprite_id > 0 else 0
        
        raw_battle_npc_id = override_sprite_id if override_sprite_id > 0 else npc_id
        battle_npc_id = mapped_override_id if mapped_override_id > 0 else mapped_npc_id
        
        db_path = os.path.join(os.path.dirname(__file__), 'ServerDataBase.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        db_mon = None
        candidates = [
            battle_npc_id,
            battle_npc_id + 27000,
            battle_npc_id + 10000,
            mapped_npc_id,
            mapped_npc_id + 27000,
            mapped_npc_id + 10000,
        ]
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
                # Test true_npc_id variations too
                true_dec = ((true_npc_id & 0xFFFF) ^ 0x5209) - 9
                true_cands = [true_npc_id, true_dec, true_dec + 27000, true_dec + 10000]
                for cand_id in true_cands:
                    db_mon = conn.execute("SELECT * FROM npc_data WHERE id=?", (cand_id,)).fetchone()
                    if db_mon:
                        battle_npc_id = cand_id
                        break
                    
        conn.close()

        # Custom stats for starter map monsters due to corrupted level/element columns in db
        REAL_MONSTER_STATS = {
            5200: {"name": "Grape Mons", "level": 1, "hp": 40, "element": 0}, # None
            5199: {"name": "Globefish", "level": 12, "hp": 560, "element": 2},     # Water
            30960: {"name": "Persian Cat", "level": 5, "hp": 180, "element": 0},    # None
            6217: {"name": "Picky Mouse", "level": 3, "hp": 110, "element": 1},    # Earth
        }

        if battle_npc_id in REAL_MONSTER_STATS:
            stats = REAL_MONSTER_STATS[battle_npc_id]
            mon_name = stats["name"]
            mon_level = stats["level"]
            mon_max_hp = stats["hp"]
            mon_element = stats["element"]
        elif db_mon:
            mon_name = (db_mon['name'] or '').strip('\x00').strip() or 'Monster'
            if '?' in mon_name:
                mon_name = 'Monster'
            
            raw_level = int(db_mon['level'] or 1)
            # Decrypt or fallback if raw level is corrupted (e.g. 93 or 96)
            if raw_level in (93, 96):
                mon_level = max(1, (battle_npc_id % 15) + 1)
            else:
                mon_level = raw_level
                
            mon_max_hp = int(db_mon['hp']) if db_mon['hp'] and 0 < int(db_mon['hp']) < 20000 else self.get_monster_max_hp(mon_level)
            
            raw_element = int(db_mon['element'] or 0)
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

        logger.info(f"[Battle] PvE start: {session.char_name} vs {mon_name} (id={raw_battle_npc_id} lv={mon_level} hp={mon_max_hp})")

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

        # Fighter nesneleri (basit dict)
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
        m_fighter = {
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

        battle = {
            'id': battle_id,
            'player': p_fighter,
            'monster': m_fighter,
            'turn': 0,
            'finished': False,
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
          4. AC 8:2  stat paketleri (prefix 04 01 00, 4-byte padding)
          5. AC 11:5 (monsterlar, 2-byte trailing pad)

        KRİTİK HATALAR DÜZELTILDI:
          - Stat ID'ler 0x0119 formatında (0x0100 prefix ŞARTT!)
          - Padding 6 byte değil 4 byte!
          - 11:250 ve 11:5 sonunda 2 byte trailing pad
          - AC 20:12 ve AC 6:2 eklendi
        """
        pf = battle['player']
        mf = battle['monster']

        # ── 0a. AC 20:12 – savaş modu girişi (boş payload) ─────────────────
        await session.send_packet(PacketWriter().write_8(20).write_8(12))

        # ── 0b. AC 6:2 [01] – mod değişimi sinyali ─────────────────────────
        pkt_62 = PacketWriter()
        pkt_62.write_8(6).write_8(2).write_8(1)
        await session.send_packet(pkt_62)

        # ── 2. AC 11:250 – SADECE oyuncu (role=1, ftype=2) ─────────────────
        # Format: sig(2) len(2) AC(1) Sub(1) bg_id(2) + fighter_block(30) + pad(2)
        # TOPLAM len = 36 (Wireshark'tan)
        bg_id = 0x0451
        p250 = PacketWriter()
        p250.write_8(11).write_8(250)
        p250.write_16(bg_id)
        # Oyuncu fighter block (30 bytes)
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

        # ── 4. AC 8:2 stat paketleri (savaş sırasında) ─────────────────────
        # Format: AC(1) Sub(1) 04 01 00 stat_id(2) value(4) padding(4) = 15 bytes
        stats_8_2 = [
            (0x01cf, 0),
            (0x0119, pf['hp']),       # current HP
            (0x01d0, 0),
            (0x011a, pf['sp']),       # current SP
            (0x01d2, 0)
        ]
        for stat_id, val in stats_8_2:
            pkt = PacketWriter()
            pkt.write_8(8).write_8(2)
            pkt.write_8(4).write_8(1).write_8(0)  # prefix: 04 01 00
            pkt.write_16(stat_id)
            pkt.write_32(val)
            pkt.write_32(0)           # 4 byte padding (6 değil!)
            await session.send_packet(pkt)

        # ── 5. AC 11:5 – monster (role=1, ftype=7) ─────────────────────────
        # Format: AC(1) Sub(1) fighter_block(30) + pad(2) = 34 bytes
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
        logger.info(f"[Battle] -> {session.char_name}: 11:5 ({mf['name']} id={mf['id']})")

        # ── 6. İlk tur init: AC 51:1 HP/SP tüm fighterlar + AC 52:1 ─────────
        # Wireshark Capture 3: savaş başladıktan sonra sunucu önce HP/SP
        # sync paketleri gönderir, sonra 52:1 ile oyuncuya sıra verir.
        await self._send_turn_start(session, battle)

    async def handle_battle_action(self, session: 'PlayerSession', reader: PacketReader):
        """AC 50: İstemciden gelen savaş aksiyonu."""
        raw_data = reader.data  # tüm paketi logla
        sub = reader.read_8() if reader.remaining_bytes() > 0 else 0
        extra = raw_data[1:].hex() if len(raw_data) > 1 else ''
        logger.info(f"[{session.char_name}] AC50 sub={sub} extra={extra}")

        battle_id = getattr(session, 'pvp_battle_id', None)
        if battle_id is None or battle_id not in self.active_battles:
            logger.warning(f"[{session.char_name}] AC50 but not in battle, raw={raw_data.hex()}")
            return

        battle = self.active_battles[battle_id]
        if battle['finished']:
            return

        # Tüm saldırı sub değerlerini saldırı olarak say (doğru sub'u log'dan öğreniriz)
        if sub in (0, 1, 2, 3, 6, 7):   # saldırı benzeri komutlar
            skill_id = 10001
            if sub == 1 and reader.remaining_bytes() >= 8:
                try:
                    src_x = reader.read_8()
                    src_y = reader.read_8()
                    dst_x = reader.read_8()
                    dst_y = reader.read_8()
                    skill_id = reader.read_16()
                    logger.info(f"[{session.char_name}] Battle action sub=1 parsed skill_id={skill_id}")
                except Exception as e:
                    logger.error(f"Error parsing AC50 sub=1 payload: {e}")
            
            if skill_id == 60021:
                await self._resolve_pve_turn(session, battle, action='defend', skill_id=skill_id)
            elif skill_id == 60041:
                await self._do_flee(session, battle)
            else:
                await self._resolve_pve_turn(session, battle, action='attack', skill_id=skill_id)
        elif sub == 4:  # Savunma
            await self._resolve_pve_turn(session, battle, action='defend')
        elif sub == 5:  # Kaç
            await self._do_flee(session, battle)
        else:
            logger.warning(f"[{session.char_name}] AC50 unhandled sub={sub}")

    async def _send_turn_start(self, session: 'PlayerSession', battle: dict):
        """
        Savaş başladıktan sonra tüm savaşçıların HP/SP'ini gönder
        ve AC=50:6 ile oyuncuya sırayı ver.

        Wireshark CAP-B: sunucu önce 51:1 HP sync, sonra 50:6 turn-start gönderiyor.
        (Eski kodda hatalı olarak 52:1 kullanılıyordu)
        """
        pf = battle['player']
        mf = battle['monster']
        # HP/SP sync tüm savaşçılar
        for x, y, val, stat in [
            (pf['x'], pf['y'], pf['hp'],  0x19),
            (pf['x'], pf['y'], pf['sp'],  0x1a),
            (mf['x'], mf['y'], mf['hp'],  0x19),
            (mf['x'], mf['y'], mf['sp'],  0x1a),
        ]:
            pkt = PacketWriter()
            pkt.write_8(51).write_8(1)
            pkt.write_8(x).write_8(y).write_8(stat).write_32(val)
            await session.send_packet(pkt)
        # AC 53:5 [player_x, player_y] – hangi savaşçının sırası olduğunu bildir
        await session.send_packet(
            PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
        )
        # AC 50:6 [player_x, player_y, 0] – TUR BAŞ ISIGNALI (52:1 değil!)
        # Wireshark CAP-B PKT02'den doğrulama
        await session.send_packet(
            PacketWriter().write_8(50).write_8(6).write_8(pf['x']).write_8(pf['y']).write_8(0)
        )
        # AC 52:1 – Oyuncuya komut seçme izni ver (34 01)
        await session.send_packet(
            PacketWriter().write_8(52).write_8(1)
        )
        logger.info(f"[Battle] -> {session.char_name}: turn-start (p={pf['hp']}HP m={mf['hp']}HP)")

    async def _resolve_pve_turn(self, session: 'PlayerSession', battle: dict, action: str, skill_id: int = 10001):
        """
        PvE turünü çözer. Düzeltìlmiş paket formatı:

        Wireshark CAP-B'den doğrulanan sıra:
          1. AC 53:5 [attacker_x, attacker_y]            -- eylem bildirimi
          2. AC 50:1 [19 byte saldırı anim paketi]      -- animasyon + hasar
          3. AC 51:1 [target_x, target_y, HP, new_val]  -- HP güncelle
          4. AC 50:6 [player_x, player_y, 0]            -- sonraki tur sinyali
        """
        import random

        pf = battle['player']
        mf = battle['monster']
        battle['turn'] += 1
        turn = battle['turn']

        def get_skill_info(sid):
            if hasattr(self, 'parsed_skills') and sid in self.parsed_skills:
                return self.parsed_skills[sid]
            # Fallback
            return (f"Skill {sid}", pf['element'], False, 1.0, False, 0)

        def get_element_correction(hitter_element: int, target_element: int) -> float:
            # 1=Earth, 2=Water, 3=Fire, 4=Wind, 0=Normal
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
            
            # Base WLO-style damage calculation
            # Use atk * (atk / (atk + def_val/2)) for better scaling at all levels
            base_dmg = atk * (atk / max(1, atk + def_val/2.0))
            
            # Add a flat boost for low levels so they can actually kill things
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

        async def _monster_counter_attack():
            dmg_to_p = calculate_atk_damage(mf.get('atk', mf['level']*3), pf.get('def', pf['level']*2), mf['element'], pf['element'])
            if action == 'defend':
                dmg_to_p = max(1, dmg_to_p // 2)
            pf['hp'] = max(0, pf['hp'] - dmg_to_p)
            session.hp = pf['hp']
            logger.info(f"[Battle] T{turn}: {mf['name']} -> {pf['name']}: "
                        f"{dmg_to_p} dmg p_hp={pf['hp']}/{mf['max_hp']}")

            # AC 53:5 – monster eylem bildirimi
            await session.send_packet(
                PacketWriter().write_8(53).write_8(5).write_8(mf['x']).write_8(mf['y'])
            )

            # AC 50:1 – monster saldırı animasyonu
            p_manim = PacketWriter()
            p_manim.write_8(50).write_8(1)
            p_manim.write_8(0x11).write_8(0x00)         # unk header
            p_manim.write_8(mf['x']).write_8(mf['y'])   # saldıran (monster)
            p_manim.write_8(0x11).write_8(0x27)         # anim tipi
            p_manim.write_8(0).write_8(1)               # flag + hit_count
            p_manim.write_8(pf['x']).write_8(pf['y'])   # hedef (oyuncu)
            p_manim.write_8(1).write_8(0).write_8(1)    # flags + is_hit
            p_manim.write_8(0x19)                        # stat = HP
            p_manim.write_32(dmg_to_p)                   # hasar
            p_manim.write_8(1)                           # final flag
            await session.send_packet(p_manim)

            # AC 51:1 – oyuncu HP güncelle
            await session.send_packet(_hp_pkt(pf['x'], pf['y'], pf['hp']))
            
            # Delay to let monster counter-attack animation play on client
            await asyncio.sleep(1.2)

            # ── Oyuncu Öldü mü? ────────────────────────────────────────────────
            if pf['hp'] <= 0:
                await self._end_battle(session, battle, won=False)
                return

            # ── Sonraki Tur: AC 50:6 (52:1 değil!) ─────────────────────────────
            # Wireshark CAP-B PKT02 doğruladı: turn-ready = AC 50:6 [x, y, 0]
            await session.send_packet(
                PacketWriter().write_8(50).write_8(6).write_8(pf['x']).write_8(pf['y']).write_8(0)
            )
            # AC 52:1 – Oyuncuya komut seçme izni ver (34 01)
            await session.send_packet(
                PacketWriter().write_8(52).write_8(1)
            )

        # ── Oyuncu Eylemi (Saldırı, Beceri veya Savunma) ───────────────────────
        if action in ('attack', 'defend'):
            if skill_id == 10008:
                # ── YAKALAMA (CAPTURE) MEKANİĞİ ───────────────────────────────
                logger.info(f"[{session.char_name}] Attempting capture on {mf['name']} (level={mf['level']}, HP={mf['hp']}/{mf['max_hp']})")
                
                # 1. Limit Check: max 4 pets
                if len(session.pets) >= 4:
                    # Send list full chat notification
                    sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Evcil hayvan listeniz dolu! (Maksimum 4)")
                    await session.send_packet(sys_msg)
                    
                    # Play capture fail animation (skill 10009)
                    await session.send_packet(
                        PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
                    )
                    
                    p_anim = PacketWriter()
                    p_anim.write_8(50).write_8(1)
                    p_anim.write_8(0x11).write_8(0x00)
                    p_anim.write_8(pf['x']).write_8(pf['y'])
                    p_anim.write_16(10009)                       # Capture Fail Skill ID
                    p_anim.write_8(0)
                    p_anim.write_8(1)
                    p_anim.write_8(mf['x']).write_8(mf['y'])
                    p_anim.write_8(1).write_8(0).write_8(1)
                    p_anim.write_8(0x19)
                    p_anim.write_32(0)
                    p_anim.write_8(1)
                    await session.send_packet(p_anim)
                    
                    await asyncio.sleep(2.4)
                    # Let the battle continue to monster's turn
                else:
                    # 2. Probability check
                    current_hp = mf['hp']
                    max_hp = mf['max_hp']
                    player_level = pf['level']
                    monster_level = mf['level']
                    
                    chance = 0.1 + (0.4 * (1.0 - current_hp / max_hp)) + (0.02 * (player_level - monster_level))
                    chance = max(0.05, min(0.95, chance))
                    
                    success = random.random() < chance
                    logger.info(f"[{session.char_name}] Capture chance: {chance:.2f}, success: {success}")
                    
                    if success:
                        # Success animation (skill 10008)
                        await session.send_packet(
                            PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
                        )
                        
                        p_anim = PacketWriter()
                        p_anim.write_8(50).write_8(1)
                        p_anim.write_8(0x11).write_8(0x00)
                        p_anim.write_8(pf['x']).write_8(pf['y'])
                        p_anim.write_16(10008)                       # Capture Success Skill ID
                        p_anim.write_8(0)
                        p_anim.write_8(1)
                        p_anim.write_8(mf['x']).write_8(mf['y'])
                        p_anim.write_8(1).write_8(0).write_8(1)
                        p_anim.write_8(0x19)
                        p_anim.write_32(0)
                        p_anim.write_8(1)
                        await session.send_packet(p_anim)
                        
                        await asyncio.sleep(2.4)
                        
                        # Send HP update to monster = 0 (to make it disappear visually)
                        await session.send_packet(_hp_pkt(mf['x'], mf['y'], 0))
                        
                        # Add pet dict to session.pets with full stats
                        if len(session.pets) >= 4:
                            await self.system_message(session, "You cannot carry any more pets!")
                            return
                            
                        pet_id = mf.get('db_id', mf['id'])
                        if not pet_id:
                            # Fallback mapping
                            mapped_npc_id = ((mf['id'] & 0xFFFF) ^ 0x5209) - 9
                            pet_id = mapped_npc_id
                            
                        # Experimental Pet ID mappings for slimes
                        if pet_id == 4184: # Banana Monster
                            pet_id = 17005
                        elif pet_id == 4185: # Grape Monster
                            pet_id = 17004
                        elif pet_id == 4197: # Kiwi Monster
                            pet_id = 17002
                            
                        # Send pet capture packet (Must be exactly 54 bytes)
                        pkt = PacketWriter()
                        pkt.write_8(15).write_8(1)
                        pkt.write_32(session.char_id)
                        pkt.write_32(pet_id)
                        
                        # The remaining 44 bytes from the official server PCAP
                        static_pet_data = bytes.fromhex('0100000000000000000100010600000000000000000000000000000000000000003c00000000000000000000')
                        for b in static_pet_data:
                            pkt.write_8(b)
                            
                        await session.send_packet(pkt)
                            
                        lvl = max(1, min(199, mf['level']))
                        base_con = 5 + lvl // 3
                        base_wis = 5 + lvl // 3
                        base_str = 5 + lvl // 3
                        base_agi = 5 + lvl // 3
                        base_int = 5 + lvl // 3
                        pet_max_hp = int(round(((lvl ** 0.35) * base_con * 2) + (lvl * 1) + (base_con * 2) + 180))
                        pet_max_sp = int(round(((lvl ** 0.3) * base_wis * 3.2) + (lvl * 1) + (base_wis * 2) + 94))
                        
                        pet_data = {
                            "pet_id": pet_id,
                            "level": lvl,
                            "exp": 0,
                            "amity": 100,
                            "reborn": 0,
                            "potential": 0,
                            "str": base_str,
                            "con": base_con,
                            "int": base_int,
                            "wis": base_wis,
                            "agi": base_agi,
                            "hp": pet_max_hp,
                            "sp": pet_max_sp
                        }
                        session.pets.append(pet_data)
                        self.save_player_to_db(session)
                        
                        # Update pet list on client
                        await self.send_pet_list(session)
                        
                        # Chat notification
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Tebrikler! {mf['name']} yakalandı!")
                        await session.send_packet(sys_msg)
                        
                        # End battle in victory
                        await self._end_battle(session, battle, won=True)
                        return
                    else:
                        # Fail animation (skill 10009)
                        await session.send_packet(
                            PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
                        )
                        
                        p_anim = PacketWriter()
                        p_anim.write_8(50).write_8(1)
                        p_anim.write_8(0x11).write_8(0x00)
                        p_anim.write_8(pf['x']).write_8(pf['y'])
                        p_anim.write_16(10009)                       # Capture Fail Skill ID
                        p_anim.write_8(0)
                        p_anim.write_8(1)
                        p_anim.write_8(mf['x']).write_8(mf['y'])
                        p_anim.write_8(1).write_8(0).write_8(1)
                        p_anim.write_8(0x19)
                        p_anim.write_32(0)
                        p_anim.write_8(1)
                        await session.send_packet(p_anim)
                        
                        await asyncio.sleep(2.4)
                        
                        # Chat notification
                        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"{mf['name']} yakalanamadı.")
                        await session.send_packet(sys_msg)
                        # Let the battle continue to monster's turn

            else:
                # Normal skill processing (attack, defend, or any skill that is NOT capture)
                skill_info = get_skill_info(skill_id)
                
                # Check SP cost and fallback if insufficient
                sp_cost = skill_info[5] if len(skill_info) > 5 else 0
                if pf['sp'] < sp_cost:
                    skill_id = 10001
                    skill_info = ("Attack", pf['element'], False, 1.0, False, 0)
                    sp_cost = 0
                    logger.info(f"[Battle] Insufficient SP for skill. Falling back to normal attack.")

                skill_name, skill_elem, is_magical, multiplier, is_heal, _ = skill_info

                # Deduct SP
                if sp_cost > 0:
                    pf['sp'] = max(0, pf['sp'] - sp_cost)
                    session.sp = pf['sp']
                    await session.send_packet(_sp_pkt(pf['x'], pf['y'], pf['sp']))

                # Gain skill experience (1-3 EXP per use)
                if skill_id != 10001:
                    await self.give_skill_exp(session, skill_id, random.randint(1, 3))

                # Retrieve skill Grade for damage/healing scaling
                skill_grade = 1
                for sk in session.skills:
                    if sk.get('skill_id') == skill_id:
                        skill_grade = sk.get('grade', 1)
                        break
                grade_multiplier = 1.0 + (skill_grade - 1) * 0.05

                if is_heal:
                    # Healing calculation scaled by Grade
                    matk = pf.get('matk', pf['level']*3)
                    heal_val = int(round(matk * multiplier * grade_multiplier))
                    pf['hp'] = min(pf['max_hp'], pf['hp'] + heal_val)
                    session.hp = pf['hp']
                    logger.info(f"[Battle] T{turn}: {pf['name']} heals themselves for {heal_val} HP (Grade {skill_grade}). Current HP: {pf['hp']}/{pf['max_hp']}")

                    # AC 53:5 – oyuncu eylem bildirimi
                    await session.send_packet(
                        PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
                    )

                    # AC 50:1 – heal animasyonu (hedef oyuncunun kendisi)
                    p_anim = PacketWriter()
                    p_anim.write_8(50).write_8(1)
                    p_anim.write_8(0x11).write_8(0x00)          # unk header
                    p_anim.write_8(pf['x']).write_8(pf['y'])    # saldıran pozisyon
                    p_anim.write_16(skill_id)                    # beceri ID'si
                    p_anim.write_8(0)                            # flag
                    p_anim.write_8(1)                            # hit_count
                    p_anim.write_8(pf['x']).write_8(pf['y'])    # hedef pozisyon (kendi)
                    p_anim.write_8(1).write_8(0)                 # flags
                    p_anim.write_8(1)                            # is_hit
                    p_anim.write_8(0x19)                         # stat_id = HP
                    p_anim.write_32(heal_val)                    # yeşil iyileşme miktarı
                    p_anim.write_8(1)                            # final flag
                    await session.send_packet(p_anim)

                    # AC 51:1 – oyuncu HP güncelle
                    await session.send_packet(_hp_pkt(pf['x'], pf['y'], pf['hp']))
                    
                    delay = 1.8 if skill_id == 10001 else 3.8
                    await asyncio.sleep(delay)
                else:
                    # Normal or Skill damage calculation scaled by Grade
                    hitter_element = skill_elem if skill_id != 10001 else pf['element']
                    
                    # Instead of forcing MATK for all elemental skills, use the highest of ATK or MATK
                    # since physical classes can use elemental physical skills.
                    best_atk = max(pf.get('atk', pf['level']*3), pf.get('matk', pf['level']*3))
                    def_stat = mf.get('def', mf['level']*2)
                    
                    # Apply skill and grade multipliers
                    modified_atk = int(round(best_atk * multiplier * grade_multiplier))
                    
                    # Add base skill damage scaling (so skills always hit noticeably harder than normal attacks)
                    if skill_id != 10001:
                        modified_atk += int(15 * multiplier)
                        
                    dmg_to_mon = calculate_atk_damage(modified_atk, def_stat, hitter_element, mf['element'])
                    
                    if action == 'defend':
                        dmg_to_mon = max(1, dmg_to_mon // 2)
                        
                    mf['hp'] = max(0, mf['hp'] - dmg_to_mon)
                    logger.info(f"[Battle] T{turn}: {pf['name']} uses {skill_name} (Grade {skill_grade}) -> {mf['name']}: "
                                f"{dmg_to_mon} dmg (element={hitter_element}) mon_hp={mf['hp']}/{mf['max_hp']}")

                    # AC 53:5 – oyuncu eylem bildirimi
                    await session.send_packet(
                        PacketWriter().write_8(53).write_8(5).write_8(pf['x']).write_8(pf['y'])
                    )

                    # AC 50:1 – saldırı animasyonu + hasar (19 byte payload)
                    p_anim = PacketWriter()
                    p_anim.write_8(50).write_8(1)
                    p_anim.write_8(0x11).write_8(0x00)          # unk header
                    p_anim.write_8(pf['x']).write_8(pf['y'])    # saldıran pozisyon
                    p_anim.write_16(skill_id)                    # beceri ID'si
                    p_anim.write_8(0)                            # flag
                    p_anim.write_8(1)                            # hit_count
                    p_anim.write_8(mf['x']).write_8(mf['y'])    # hedef pozisyon
                    p_anim.write_8(1).write_8(0)                 # flags
                    p_anim.write_8(1)                            # is_hit
                    p_anim.write_8(0x19)                         # stat_id = HP
                    p_anim.write_32(dmg_to_mon)                  # hasar miktarı
                    p_anim.write_8(1)                            # final flag
                    await session.send_packet(p_anim)

                    # AC 51:1 – monster HP güncelle
                    await session.send_packet(_hp_pkt(mf['x'], mf['y'], mf['hp']))
                    
                    delay = 1.8 if skill_id == 10001 else 3.8
                    await asyncio.sleep(delay)

        # ── Monster Öldü mü? ───────────────────────────────────────────────
        if mf['hp'] <= 0:
            await self._end_battle(session, battle, won=True)
            return

        # ── Monster Karşı Saldırısı ─────────────────────────────────────────
        dmg_to_p = calculate_atk_damage(mf.get('atk', mf['level']*3), pf.get('def', pf['level']*2), mf['element'], pf['element'])
        if action == 'defend':
            dmg_to_p = max(1, dmg_to_p // 2)
        pf['hp'] = max(0, pf['hp'] - dmg_to_p)
        session.hp = pf['hp']
        logger.info(f"[Battle] T{turn}: {mf['name']} -> {pf['name']}: "
                    f"{dmg_to_p} dmg p_hp={pf['hp']}/{pf['max_hp']}")

        # AC 53:5 – monster eylem bildirimi
        await session.send_packet(
            PacketWriter().write_8(53).write_8(5).write_8(mf['x']).write_8(mf['y'])
        )

        # AC 50:1 – monster saldırı animasyonu
        p_manim = PacketWriter()
        p_manim.write_8(50).write_8(1)
        p_manim.write_8(0x11).write_8(0x00)         # unk header
        p_manim.write_8(mf['x']).write_8(mf['y'])   # saldıran (monster)
        p_manim.write_8(0x11).write_8(0x27)         # anim tipi
        p_manim.write_8(0).write_8(1)               # flag + hit_count
        p_manim.write_8(pf['x']).write_8(pf['y'])   # hedef (oyuncu)
        p_manim.write_8(1).write_8(0).write_8(1)    # flags + is_hit
        p_manim.write_8(0x19)                        # stat = HP
        p_manim.write_32(dmg_to_p)                   # hasar
        p_manim.write_8(1)                           # final flag
        await session.send_packet(p_manim)

        # AC 51:1 – oyuncu HP güncelle
        await session.send_packet(_hp_pkt(pf['x'], pf['y'], pf['hp']))
        
        # Delay to let monster counter-attack animation play on client
        await asyncio.sleep(1.4)

        # ── Oyuncu Öldü mü? ────────────────────────────────────────────────
        if pf['hp'] <= 0:
            await self._end_battle(session, battle, won=False)
            return

        # ── Sonraki Tur: AC 50:6 (52:1 değil!) ─────────────────────────────
        # Wireshark CAP-B PKT02 doğruladı: turn-ready = AC 50:6 [x, y, 0]
        await session.send_packet(
            PacketWriter().write_8(50).write_8(6).write_8(pf['x']).write_8(pf['y']).write_8(0)
        )
        # AC 52:1 – Oyuncuya komut seçme izni ver (34 01)
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
        Savaşı sonlandırır. Wireshark CAP-C'den doğrulanan paket sırası:

        1. AC 51:1 [player final HP/SP]
        2. AC 51:1 [monster_x, monster_y, HP=0] (monster öldü)
        3. AC 23:6 [dropped_item_id, amount] <-- Eğer canavar eşya düşürdüyse
        4. AC 53:4 [dropped_item_id, src_x, src_y, dst_x, dst_y] <-- Eşya uçma animasyonu
        5. AC 11:12 [01]  <-- SAVAŞ BİTİŞ SİNYALİ
        6. AC 8:1 [stat_id=36, target=1, val=exp_val_64] <-- EXP güncelleme (Wireshark CAP-C)
        7. AC 22:6 [0b, 00, result]
        8. AC 22:5 [0b, 00, exp_reward, gold_reward] <-- Savaş ödülleri ekranı (Wireshark CAP-C)
        9. AC 11:0 [char_id uint32, 0x0000]
        10. AC 11:1 [player_x, player_y, 0]
        """
        pf = battle['player']
        mf = battle['monster']

        # 1. Oyuncunun son HP ve SP'ı
        for stat, val in [(0x19, pf['hp']), (0x1a, pf['sp'])]:
            p = PacketWriter()
            p.write_8(51).write_8(1)
            p.write_8(pf['x']).write_8(pf['y']).write_8(stat).write_32(val)
            await session.send_packet(p)

        # 2. Monster'un son HP'i = 0 (kesin olarak göster)
        if won:
            p = PacketWriter()
            p.write_8(51).write_8(1)
            p.write_8(mf['x']).write_8(mf['y']).write_8(0x19).write_32(0)
            await session.send_packet(p)

        # 3. Eşya Düşme Mantığı (Drop Item Logic)
        # Wireshark CAP-C'den doğrulandı: AC 23:6 ve AC 53:4
        dropped_item_id = 0
        dropped_amount = 0
        if won:
            # Canavar ID'sine veya ismine göre drop tablosunu bul
            monster_id_str = str(mf.get('db_id', 0))
            monster_name = (mf.get('name') or "").lower()
            
            drop_rules = []
            if monster_id_str in self.drop_tables:
                drop_rules = self.drop_tables[monster_id_str]
            else:
                # Canavar isminde 'spider', 'wolf' vb. geçiyorsa o kuralı eşle
                matched = False
                for rule_key, rules in self.drop_tables.items():
                    if rule_key != "default" and rule_key in monster_name:
                        drop_rules = rules
                        matched = True
                        break
                if not matched:
                    drop_rules = self.drop_tables.get("default", [])
            
            # Drop şansını değerlendir
            for rule in drop_rules:
                chance = rule.get("chance", 0.0)
                if random.random() < chance:
                    dropped_item_id = rule.get("item_id", 0)
                    dropped_amount = rule.get("amount", 1)
                    break # Sadece tek bir eşya düşürme limiti (WLO standart)

            if dropped_item_id > 0:
                slot = add_item_to_inventory(session, dropped_item_id, amount=dropped_amount)
                if slot is not None:
                    self.save_player_to_db(session)
                    
                    # AC 23:6 - Eşya ekleme paketi (slot, item_id, amount, ...)
                    item_pkt = PacketWriter()
                    item_pkt.write_8(23).write_8(6).write_8(0).write_8(slot).write_16(dropped_amount).write_16(encode_item16(dropped_item_id)).write_bytes(bytes(25))
                    await session.send_packet(item_pkt)
                    
                    # AC 53:4 - Eşya uçma animasyonu (src_x, src_y -> dst_x, dst_y)
                    fly_pkt = PacketWriter()
                    fly_pkt.write_8(53).write_8(4).write_16(encode_item16(dropped_item_id)).write_8(mf['x']).write_8(mf['y']).write_8(pf['x']).write_8(pf['y'])
                    await session.send_packet(fly_pkt)

        # Canavarın ölüm animasyonu ve eşya uçma animasyonu bitsin diye delay
        await asyncio.sleep(2.0)

        # 5. AC 11:12 [01] – SAVAŞ BİTİŞ SİNYALİ
        await session.send_packet(PacketWriter().write_8(11).write_8(12).write_8(1))

        # 6. EXP ve Gold ödülleri hesaplama & güncelleme
        exp_reward = max(10, mf['level'] * 15)
        gold_reward = max(5, mf['level'] * 8)
        if won:
            session.gold += gold_reward
            await self.give_exp(session, exp_reward)
            # give_exp handles save_player_to_db and AC 8:1 EXP/Level updates

        # 7. AC 22:6 [battle_type=11, 0, result]
        result = 2 if won else (1 if fled else 0)
        p226 = PacketWriter()
        p226.write_8(22).write_8(6)
        p226.write_8(0x0b).write_8(0x00).write_8(result)
        await session.send_packet(p226)

        # 8. AC 22:5 [battle_type=11, 0, exp_reward, gold_reward] (Wireshark)
        if won:
            p_rew = PacketWriter()
            p_rew.write_8(22).write_8(5)
            p_rew.write_16(11)  # battle type 11
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
        click_id = mf.get('click_id', 0)
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
                    pkt = PacketWriter()
                    pkt.write_8(22).write_8(6).write_16(click_id).write_8(1)
                    await session.send_packet(pkt)
                asyncio.create_task(show_monster_delayed())
            elif won:
                if target_npc:
                    target_npc['visible'] = False
                pkt_hide = PacketWriter()
                pkt_hide.write_8(22).write_8(6).write_16(click_id).write_8(0)
                await session.send_packet(pkt_hide)
                
                async def respawn_monster():
                    await asyncio.sleep(15.0)
                    if target_npc:
                        target_npc['visible'] = True
                    pkt_show = PacketWriter()
                    pkt_show.write_8(22).write_8(6).write_16(click_id).write_8(1)
                    self.broadcast_to_map(session.map_id, pkt_show)
                asyncio.create_task(respawn_monster())

        # Check if quest battle win warp is set
        win_warp = getattr(session, 'battle_win_warp', None)
        if won and win_warp:
            logger.info(f"[{session.char_name}] Quest battle won! Warp to map {win_warp['map_id']} pos=({win_warp['x']},{win_warp['y']}) pending rewards closing.")
        elif not won and not fled:
            # Player lost/died: revive with 10% HP/SP and warp to Map 10017
            session.hp = max(1, int(session.max_hp * 0.10))
            session.sp = max(1, int(session.max_sp * 0.10))
            self.save_player_to_db(session)
            logger.info(f"[Battle] {session.char_name} LOST vs {mf['name']}. Revived at 10% HP/SP. Warping to starter ship.")
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
            logger.info(f"[Battle] {session.char_name} WON vs {mf['name']}")
        elif fled:
            logger.info(f"[Battle] {session.char_name} FLED")

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
        """Loads compound recipes from data/Compound2.dat using 65-byte XOR-protected records."""
        import os
        self._COMPOUND_RECIPES = {}
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(self.static_db_path)))
        compound_path = os.path.join(base_dir, "data", "Compound2.dat")
        if not os.path.exists(compound_path):
            logger.warning(f"[Compound] Compound2.dat not found at {compound_path}")
            return
        try:
            with open(compound_path, "rb") as f:
                d = f.read()
            if len(d) < 65:
                return
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
            logger.info(f"[Compound] Loaded {recipes_loaded} compound recipes from Compound2.dat ({record_count} records).")
        except Exception as e:
            logger.error(f"[Compound] Error loading Compound2.dat: {e}", exc_info=True)

    def get_compound_recipe(self, compound_id: int) -> dict:
        return self._COMPOUND_RECIPES.get(compound_id, None)

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

    async def handle_action_54(self, session: PlayerSession, reader: PacketReader):
        """Handles shop purchases, compound/crafting, and other AC 54 events."""
        sub = reader.read_8()
        logger.info(f"[AC54] handle_action_54 called. SubCmd={sub}, data: {reader.data.hex()}")

        if sub == 3:  # Buy item from shop
            shop_id = reader.read_8()
            tab_id  = reader.read_8()
            item_id = reader.read_16()
            amount  = reader.read_8()
            item_prices = {602: 50, 603: 100, 701: 200, 702: 150, 703: 250, 27001: 50, 27005: 100}
            price = item_prices.get(item_id, 100) * amount
            if session.gold >= price:
                if add_item_to_inventory(session, item_id, amount=amount):
                    session.gold -= price
                    self.save_player_to_db(session)
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    item_pkt = PacketWriter()
                    item_pkt.write_8(23).write_8(6).write_8(0).write_8(slot).write_16(amount).write_16(encode_item16(item_id)).write_bytes(bytes(25))
                    await session.send_packet(item_pkt)
                    buy_confirm = PacketWriter()
                    buy_confirm.write_8(54).write_8(3).write_8(shop_id).write_8(tab_id).write_16(encode_item16(item_id)).write_8(amount)
                    await session.send_packet(buy_confirm)
            else:
                logger.warning(f"[AC54] Not enough gold ({session.gold} < {price})")

        elif sub == 30:  # Compound / Crafting request
            compound_id = reader.read_16()
            recipe = self.get_compound_recipe(compound_id)
            if recipe:
                required_items = recipe.get("materials", [])
                result_item    = recipe.get("result_item", 0)
                result_amount  = recipe.get("result_amount", 1)
                can_craft = True
                for mat in required_items:
                    total_owned = sum(it.get("amount", 0) for it in session.inventory if it.get("item_id") == mat["item_id"])
                    if total_owned < mat["amount"]:
                        can_craft = False
                        break
                if can_craft and result_item > 0:
                    for mat in required_items:
                        remaining = mat["amount"]
                        for it in session.inventory[:]:
                            if it.get("item_id") == mat["item_id"] and remaining > 0:
                                owned = it.get("amount", 1)
                                if owned <= remaining:
                                    remaining -= owned
                                    session.inventory.remove(it)
                                else:
                                    it["amount"] = owned - remaining
                                    remaining = 0
                    add_item_to_inventory(session, result_item, amount=result_amount)
                    self.save_player_to_db(session)
                    await session.send_packet(self.build_inventory_packet(session))
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Compound success! Created {result_amount}x Item {result_item}!"))
                else:
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Compound failed! Missing required materials."))
            else:
                logger.warning(f"[AC54] Unknown compound recipe ID: {compound_id}")
        else:
            logger.info(f"[AC54] Unhandled SubCmd: {sub}")

    async def handle_action_30(self, session: PlayerSession, reader: PacketReader):
        """Handles item selling to NPC shop (AC 30)."""
        sub = reader.read_8()
        logger.info(f"[AC30] handle_action_30 called. SubCmd={sub}, data: {reader.data.hex()}")
        
        if sub == 2:  # Sell item request
            slot_idx = reader.read_8()  # inventory slot (1-50)
            amount = reader.read_8() if reader.remaining_bytes() > 0 else 1
            
            item = get_item_at_slot(session, slot_idx)
            if item:
                item_id = item['item_id']
                # Determine selling price (simple formula or fallback price)
                # In WLO, typical items sell for a fraction of buy price, let's use 10 gold per unit fallback
                item_sell_prices = {602: 10, 603: 20, 701: 40, 702: 30, 703: 50}
                sell_price = item_sell_prices.get(item_id, 10) * amount
                
                # Remove from inventory
                remove_item_at_slot(session, slot_idx, amount)
                session.gold += sell_price
                self.save_player_to_db(session)
                
                # Send gold update: [26, 4, gold]
                await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                
                # Send slot update: [23, 9, slot_idx, remaining_amount]
                remaining_amt = 0
                for it in session.inventory:
                    if it.get('slot') == slot_idx:
                        remaining_amt = it.get('amount', 0)
                        break
                await session.send_packet(PacketWriter().write_8(23).write_8(9).write_8(slot_idx).write_8(remaining_amt))
                
                # Send sell confirmation: [30, 2, 00 00 00 ... ] (AC 30 Sub 2 payload LE)
                # Real payload size is 32 bytes (confirmed from PCAP)
                # Formatted as: c9 af 01 00 (uint32 sell_price LE) followed by 28 bytes padding
                confirm_pkt = PacketWriter().write_8(30).write_8(2).write_32(sell_price).write_bytes(bytes(28))
                await session.send_packet(confirm_pkt)
                
                # Also send UI unlock
                await session.send_packet(PacketWriter().write_8(30).write_8(7))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                logger.info(f"[{session.char_name}] Sold item {item_id} (amount={amount}) for {sell_price} gold.")
            else:
                logger.warning(f"[AC30] Inventory slot {slot_idx} is empty.")
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 1: # Open sell menu confirm
            # Real protocol sends [30, 5, 01, 01] followed by [30, 6]
            await session.send_packet(PacketWriter().write_8(30).write_8(5).write_8(1).write_8(1))
            await session.send_packet(PacketWriter().write_8(30).write_8(6))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))

    async def handle_action_31(self, session: PlayerSession, reader: PacketReader):
        """Handles item purchasing from NPC shop (AC 31)."""
        sub = reader.read_8()
        logger.info(f"[AC31] handle_action_31 called. SubCmd={sub}, data: {reader.data.hex()}")
        
        if sub == 2:  # Confirm purchase step 1
            # Real protocol: S->C AC 31 Sub 2 payload [ff ff ff ff] followed by Sub 7
            await session.send_packet(PacketWriter().write_8(31).write_8(2).write_32(0xFFFFFFFF))
            await session.send_packet(PacketWriter().write_8(31).write_8(7))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 3:  # Purchase finalization
            shop_id = reader.read_8() if reader.remaining_bytes() > 0 else 31
            # Real protocol: S->C AC 31 Sub 3 payload [01 03] (confirm slot index/buy action)
            # Followed by Sub 9, Sub 12 and gold/inventory updates
            await session.send_packet(PacketWriter().write_8(31).write_8(3).write_8(1).write_8(3))
            await session.send_packet(PacketWriter().write_8(31).write_8(9))
            await session.send_packet(PacketWriter().write_8(31).write_8(12))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
        elif sub == 12:
            await session.send_packet(PacketWriter().write_8(31).write_8(12))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
        else:
            await session.send_packet(PacketWriter().write_8(20).write_8(8))


async def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    server = GameServer()
    await server.run("0.0.0.0", 6414)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
