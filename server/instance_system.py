"""
Wonderland Online Multi-Stage Party Instance Dungeons (AC 89 / AC 91 / AC 92)
Ported from C# InstanceManager & dungeon handlers
"""

import time
import sqlite3
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


@dataclass
class InstanceTemplate:
    instance_id: int
    name: str
    min_level: int
    map_id: int
    total_rooms: int = 3
    reward_item_id: int = 48033
    reward_gold: int = 25000
    reward_exp: int = 15000


@dataclass
class ActiveInstance:
    instance_id: int
    party_leader_id: int
    members: List[int]
    current_room: int = 1
    is_completed: bool = False
    started_at: float = field(default_factory=time.time)


class InstanceManager:
    """Manages multiplayer dungeon instances, room wave advancement, and daily rewards."""

    TEMPLATES: Dict[int, InstanceTemplate] = {}

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self.active_instances: Dict[int, ActiveInstance] = {}  # LeaderID -> ActiveInstance
        self._load_templates()
        self._ensure_tables()

    def _load_templates(self):
        self.TEMPLATES.clear()
        try:
            from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
            db_insts = GLOBAL_DYNAMIC_DATA.get_instances()
            for i_id, d in db_insts.items():
                self.TEMPLATES[i_id] = InstanceTemplate(
                    instance_id=d["instance_id"],
                    name=d["name"],
                    min_level=d.get("min_level", 10),
                    map_id=d["map_id"],
                    total_rooms=d.get("total_rooms", 3),
                    reward_gold=d.get("reward_gold", 10000),
                    reward_exp=d.get("reward_exp", 5000),
                    reward_item_id=d.get("reward_item_id", 48033)
                )
            logger.info(f"[InstanceManager] Loaded {len(self.TEMPLATES)} dynamic instances from database.")
        except Exception as e:
            logger.warning(f"[InstanceManager] Fallback instances: {e}")
            self.TEMPLATES = {
                1: InstanceTemplate(1, "Haunted Ghost Ship", 40, 16001, 3, 48033, 20000, 10000),
                2: InstanceTemplate(2, "Maya Alien Pyramid", 60, 18001, 4, 48033, 40000, 25000),
                3: InstanceTemplate(3, "Sunken Pirate Cove", 80, 19001, 5, 48033, 80000, 50000),
            }

    def reload_from_db(self, dynamic_mgr=None):
        self._load_templates()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_instances (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    instance_id INTEGER NOT NULL,
                    completed_at REAL,
                    UNIQUE(char_id, instance_id)
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[InstanceManager] DB Init Error: {e}")

    def can_enter_today(self, char_id: int, instance_id: int) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute(
                "SELECT completed_at FROM char_instances WHERE char_id = ? AND instance_id = ?",
                (char_id, instance_id)
            ).fetchone()
            conn.close()
            if not row:
                return True
            # 24-hour daily reset
            return (time.time() - row[0]) >= 86400
        except Exception:
            return True

    async def enter_instance(self, server, leader, instance_id: int) -> bool:
        if not leader or instance_id not in self.TEMPLATES:
            return False

        template = self.TEMPLATES[instance_id]
        if leader.level < template.min_level:
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Requires minimum Level {template.min_level} to enter {template.name}!"
            )
            await leader.send_packet(sys_msg)
            return False

        if not self.can_enter_today(leader.char_id, instance_id):
            sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"You have already completed {template.name} today! Daily reset in 24 hours."
            )
            await leader.send_packet(sys_msg)
            return False

        # Register active instance
        members = [leader.char_id]
        inst = ActiveInstance(instance_id=instance_id, party_leader_id=leader.char_id, members=members)
        self.active_instances[leader.char_id] = inst

        # Warp to instance start
        await server.warp_player(leader, template.map_id, 300, 300)

        # Broadcast instance entry packet (AC 89 Sub 1)
        pkt = PacketWriter().write_8(89).write_8(1).write_16(instance_id).write_8(1)
        await leader.send_packet(pkt)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Instance Started] Entered {template.name} (Room 1/{template.total_rooms})!"
        )
        await leader.send_packet(sys_msg)
        logger.info(f"[InstanceManager] Player {leader.char_name} started instance {template.name}.")
        return True

    async def advance_room(self, server, leader) -> bool:
        if not leader or leader.char_id not in self.active_instances:
            return False

        inst = self.active_instances[leader.char_id]
        template = self.TEMPLATES[inst.instance_id]
        inst.current_room += 1

        if inst.current_room > template.total_rooms:
            # Complete instance
            return await self.complete_instance(server, leader)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Instance Progress] Advanced to Room {inst.current_room}/{template.total_rooms}!"
        )
        await leader.send_packet(sys_msg)
        return True

    async def complete_instance(self, server, leader) -> bool:
        if not leader or leader.char_id not in self.active_instances:
            return False

        inst = self.active_instances.pop(leader.char_id)
        template = self.TEMPLATES[inst.instance_id]

        from server.gameserver import add_item_to_inventory
        leader.gold += template.reward_gold
        leader.exp += template.reward_exp
        add_item_to_inventory(leader, template.reward_item_id, 1)

        # Record daily clear
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO char_instances (char_id, instance_id, completed_at)
                VALUES (?, ?, ?)
            """, (leader.char_id, template.instance_id, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[InstanceManager] DB Error completing instance: {e}")

        # Send celebration animation (AC 5:5: 60050)
        fx = PacketWriter().write_8(5).write_8(5).write_32(leader.char_id).write_16(60050)
        server.broadcast_to_map(leader.map_id, fx)

        await leader.send_packet(PacketWriter().write_8(26).write_8(4).write_32(leader.gold))
        await leader.send_packet(server.build_inventory_packet(leader))
        await server.send_stats_update(leader)

        sys_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
            f"[Instance Victory!] Cleared {template.name}! Rewards: +{template.reward_gold} Gold, +{template.reward_exp} EXP, Item #{template.reward_item_id}!"
        )
        await leader.send_packet(sys_msg)
        server.save_player_to_db(leader)
        logger.info(f"[InstanceManager] Player {leader.char_name} cleared {template.name}.")
        return True


GLOBAL_INSTANCE_MANAGER = InstanceManager()
