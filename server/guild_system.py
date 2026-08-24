"""
Wonderland Online Guild System & Guild Storage
Ported from C# wlo.pserver.core/Game/PlayerRelated/Guild.cs and Src/Network/ActionCodes/AC39.cs
"""

import time
import sqlite3
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class GuildMemberRank(IntEnum):
    MEMBER = 0
    VICE_LEADER = 1
    LEADER = 2


@dataclass
class GuildMember:
    char_id: int
    char_name: str
    level: int
    job: int
    element: int
    rank: GuildMemberRank = GuildMemberRank.MEMBER


@dataclass
class Guild:
    guild_id: int
    guild_name: str
    leader_id: int
    leader_name: str
    icon: int = 3402
    rules: str = ""
    created_at: float = field(default_factory=time.time)
    members: Dict[int, GuildMember] = field(default_factory=dict)
    storage: List[Dict[str, Any]] = field(default_factory=list)  # [{'item_id': id, 'count': c}]

    @property
    def member_count(self) -> int:
        return len(self.members)


class GuildManager:
    """Manages player guilds, member hierarchies, shared storage, and SQLite persistence."""

    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._guilds: Dict[int, Guild] = {}             # GuildID -> Guild
        self._player_guild: Dict[int, int] = {}         # CharID -> GuildID
        self._pending_invites: Dict[int, int] = {}      # TargetID -> GuildID
        self._ensure_tables()
        self._load_from_db()

    def _ensure_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_name VARCHAR(50) NOT NULL UNIQUE,
                    leader_id INTEGER NOT NULL,
                    leader_name VARCHAR(50) NOT NULL,
                    icon INTEGER DEFAULT 3402,
                    rules TEXT DEFAULT '',
                    created_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_members (
                    char_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    char_name VARCHAR(50) NOT NULL,
                    level INTEGER DEFAULT 1,
                    job INTEGER DEFAULT 0,
                    element INTEGER DEFAULT 0,
                    rank INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_storage (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    count INTEGER NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[GuildManager] DB Init Error: {e}")

    def _load_from_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM guilds").fetchall()
            for r in rows:
                g = Guild(
                    guild_id=r["guild_id"],
                    guild_name=r["guild_name"],
                    leader_id=r["leader_id"],
                    leader_name=r["leader_name"],
                    icon=r["icon"] or 3402,
                    rules=r["rules"] or "",
                    created_at=r["created_at"] or time.time()
                )
                self._guilds[g.guild_id] = g

            # Load members
            m_rows = conn.execute("SELECT * FROM guild_members").fetchall()
            for mr in m_rows:
                gid = mr["guild_id"]
                if gid in self._guilds:
                    gm = GuildMember(
                        char_id=mr["char_id"],
                        char_name=mr["char_name"],
                        level=mr["level"],
                        job=mr["job"],
                        element=mr["element"],
                        rank=GuildMemberRank(mr["rank"])
                    )
                    self._guilds[gid].members[gm.char_id] = gm
                    self._player_guild[gm.char_id] = gid

            # Load storage
            s_rows = conn.execute("SELECT * FROM guild_storage").fetchall()
            for sr in s_rows:
                gid = sr["guild_id"]
                if gid in self._guilds:
                    self._guilds[gid].storage.append({
                        "item_id": sr["item_id"],
                        "count": sr["count"]
                    })

            conn.close()
            logger.info(f"[GuildManager] Loaded {len(self._guilds)} guilds from DB.")
        except Exception as e:
            logger.error(f"[GuildManager] Error loading guilds: {e}")

    def get_player_guild(self, char_id: int) -> Optional[Guild]:
        gid = self._player_guild.get(char_id)
        return self._guilds.get(gid) if gid else None

    async def create_guild(self, server, player, name: str, icon: int = 3402) -> bool:
        if not player or not name or len(name.strip()) < 2:
            return False

        if player.char_id in self._player_guild:
            await self.send_system_msg(player, "You are already a member of a guild!")
            return False

        if player.level < 30:
            await self.send_system_msg(player, "Requires Level 30 or higher to create a guild!")
            return False

        if player.gold < 100000:
            await self.send_system_msg(player, "Creating a guild requires 100,000 gold!")
            return False

        # Deduct gold
        player.gold -= 100000
        await player.send_packet(PacketWriter().write_8(26).write_8(4).write_32(player.gold))

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO guilds (guild_name, leader_id, leader_name, icon, rules, created_at)
                VALUES (?, ?, ?, ?, '', ?)
            """, (name, player.char_id, player.char_name, icon, time.time()))
            guild_id = cur.lastrowid

            cur.execute("""
                INSERT INTO guild_members (char_id, guild_id, char_name, level, job, element, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (player.char_id, guild_id, player.char_name, player.level, getattr(player, 'job', 0), player.element, GuildMemberRank.LEADER))

            conn.commit()
            conn.close()

            # Create in memory
            guild = Guild(
                guild_id=guild_id,
                guild_name=name,
                leader_id=player.char_id,
                leader_name=player.char_name,
                icon=icon,
                created_at=time.time()
            )
            guild.members[player.char_id] = GuildMember(
                char_id=player.char_id,
                char_name=player.char_name,
                level=player.level,
                job=getattr(player, 'job', 0),
                element=player.element,
                rank=GuildMemberRank.LEADER
            )
            self._guilds[guild_id] = guild
            self._player_guild[player.char_id] = guild_id

            # Ack AC 39 Sub 2
            ack_pkt = PacketWriter().write_8(39).write_8(2).write_8(1)
            await player.send_packet(ack_pkt)

            # Global server announcement
            server_msg = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"[Guild] Player {player.char_name} has founded the guild <{name}>!"
            )
            server.broadcast_to_map(player.map_id, server_msg)
            logger.info(f"[GuildManager] Guild <{name}> created by {player.char_name}.")
            return True
        except sqlite3.IntegrityError:
            await self.send_system_msg(player, "A guild with that name already exists!")
            return False
        except Exception as e:
            logger.error(f"[GuildManager] Error creating guild: {e}", exc_info=True)
            return False

    async def invite_player(self, inviter, target):
        guild = self.get_player_guild(inviter.char_id)
        if not guild:
            await self.send_system_msg(inviter, "You are not in a guild!")
            return

        member = guild.members.get(inviter.char_id)
        if not member or member.rank == GuildMemberRank.MEMBER:
            await self.send_system_msg(inviter, "Only Guild Leaders and Vice Leaders can invite members!")
            return

        if target.char_id in self._player_guild:
            await self.send_system_msg(inviter, "That player is already in a guild!")
            return

        self._pending_invites[target.char_id] = guild.guild_id

        # Send invite prompt to target (AC 39:2)
        inv_pkt = PacketWriter().write_8(39).write_8(2).write_32(inviter.char_id).write_string(guild.guild_name)
        await target.send_packet(inv_pkt)
        await self.send_system_msg(inviter, f"Guild invitation sent to {target.char_name}.")

    async def accept_invite(self, server, target):
        if target.char_id not in self._pending_invites:
            return

        guild_id = self._pending_invites.pop(target.char_id)
        guild = self._guilds.get(guild_id)
        if not guild:
            return

        # Add member to DB
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO guild_members (char_id, guild_id, char_name, level, job, element, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (target.char_id, guild_id, target.char_name, target.level, getattr(target, 'job', 0), target.element, GuildMemberRank.MEMBER))
            conn.commit()
            conn.close()

            gm = GuildMember(
                char_id=target.char_id,
                char_name=target.char_name,
                level=target.level,
                job=getattr(target, 'job', 0),
                element=target.element,
                rank=GuildMemberRank.MEMBER
            )
            guild.members[target.char_id] = gm
            self._player_guild[target.char_id] = guild_id

            await self.send_guild_info(target)
            await self.send_guild_members(target)
            await self.broadcast_to_guild(server, guild, f"{target.char_name} has joined the guild!")
            logger.info(f"[GuildManager] {target.char_name} joined guild <{guild.guild_name}>.")
        except Exception as e:
            logger.error(f"[GuildManager] Error joining guild: {e}")

    async def send_guild_info(self, session):
        guild = self.get_player_guild(session.char_id)
        if not guild:
            return

        pkt = PacketWriter().write_8(39).write_8(1)
        pkt.write_16(guild.guild_id)
        pkt.write_string(guild.guild_name)
        pkt.write_string(guild.leader_name)
        pkt.write_32(guild.icon)
        pkt.write_16(guild.member_count)
        pkt.write_string(guild.rules)
        await session.send_packet(pkt)

    async def send_guild_members(self, session):
        guild = self.get_player_guild(session.char_id)
        if not guild:
            return

        pkt = PacketWriter().write_8(39).write_8(12).write_16(len(guild.members))
        for m in guild.members.values():
            pkt.write_32(m.char_id)
            pkt.write_string(m.char_name)
            pkt.write_16(m.level)
            pkt.write_8(m.job)
            pkt.write_8(m.element)
            pkt.write_8(int(m.rank))

        await session.send_packet(pkt)

    async def broadcast_to_guild(self, server, guild: Guild, msg: str):
        if not guild or not msg:
            return
        pkt = PacketWriter().write_8(2).write_8(4).write_string(msg)
        for char_id in guild.members.keys():
            s = server.sessions.get(char_id)
            if s:
                await s.send_packet(pkt)

    async def send_system_msg(self, session, msg: str):
        if not session or not msg:
            return
        sys_pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
        await session.send_packet(sys_pkt)


GLOBAL_GUILD_MANAGER = GuildManager()
