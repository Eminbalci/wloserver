"""
WLO Battle Engine - Sıfırdan yazılmış PvE/PvP savaş motoru.
C# referans: Battle.cs -> Send_Attack, Send_11_250, Send_11_5
"""
import asyncio
import logging
import random
import struct

logger = logging.getLogger("WLO_Battle")


# ─── Fighter ──────────────────────────────────────────────────────────────────

class Fighter:
    """Savaştaki bir katılımcıyı temsil eder (oyuncu, canavar, pet)."""

    def __init__(
        self,
        char_id: int,
        name: str,
        level: int,
        hp: int,
        max_hp: int,
        sp: int,
        max_sp: int,
        element: int,
        role: int,       # 5=Attacking, 2=Defending
        f_type: int,     # 2=Player, 7=Monster, 4=Pet
        is_monster: bool = False,
        session=None,
    ):
        self.char_id  = char_id
        self.name     = name
        self.level    = level
        self.hp       = hp
        self.max_hp   = max_hp
        self.sp       = sp
        self.max_sp   = max_sp
        self.element  = element
        self.role     = role
        self.f_type   = f_type
        self.is_monster = is_monster
        self.session  = session   # None for monsters

        # Grid pozisyonu
        self.x: int = 0
        self.y: int = 0

        # click_id isteğe bağlı
        self.click_id: int = 0

        # Tur aksiyonu
        self.queued_action: dict | None = None

        # Ölüm durumu
        self.is_dead: bool = False

        # Hız (agility) - daha yüksek → daha önce saldırır
        self.agi_val: int = level * 2
        if session:
            self.agi_val = getattr(session, "agi_val", self.agi_val)

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.is_dead = True


# ─── BattleManager ────────────────────────────────────────────────────────────

class BattleManager:
    """Savaşı yöneten ana sınıf."""

    def __init__(self, battle_id: int, bg_id: int = 2):
        self.battle_id = battle_id
        self.bg_id     = bg_id

        # role=5 → Attacking side, role=2 → Defending side
        self.attackers: list[Fighter] = []
        self.defenders: list[Fighter] = []

        self.turn_number: int = 1
        self.finished: bool   = False

    # ── Fighters ─────────────────────────────────────────────────────────────

    def add_fighter(self, f: Fighter) -> None:
        if f.role == 5:
            self.attackers.append(f)
        else:
            self.defenders.append(f)

    def all_fighters(self) -> list[Fighter]:
        return self.attackers + self.defenders

    def get_fighter(self, char_id: int) -> Fighter | None:
        for f in self.all_fighters():
            if f.char_id == char_id:
                return f
        return None

    # ── Turn helpers ─────────────────────────────────────────────────────────

    def is_turn_ready(self) -> bool:
        """Tüm canlı oyuncular aksiyon gönderdi mi?"""
        for f in self.all_fighters():
            if f.is_dead or f.is_monster:
                continue
            if f.queued_action is None:
                return False
        return True

    def queue_ai_actions(self) -> None:
        """Canavarlar için rastgele saldırı atar."""
        for f in self.all_fighters():
            if f.is_dead or not f.is_monster:
                continue
            if f.queued_action is not None:
                continue
            opponents = self.attackers if f.role == 2 else self.defenders
            living = [o for o in opponents if not o.is_dead]
            if living:
                tgt = random.choice(living)
                f.queued_action = {
                    "type":     "attack",
                    "skill_id": 0,
                    "target_x": tgt.x,
                    "target_y": tgt.y,
                }
            else:
                f.queued_action = {"type": "defend"}

    def clear_actions(self) -> None:
        for f in self.all_fighters():
            f.queued_action = None

    # ── Broadcast ────────────────────────────────────────────────────────────

    async def broadcast(self, pkt) -> None:
        """Paketi tüm insan oyuncularına gönderir."""
        for f in self.all_fighters():
            if f.session and not f.is_monster:
                await f.session.send_packet(pkt)
