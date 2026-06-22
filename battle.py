import asyncio
import logging
import random
from typing import Dict, Any, Optional

logger = logging.getLogger('gameserver.battle')

class BattleInstance:
    """
    Manages a synchronous PvP battle between two players (team A vs team B).
    In the future, this can be expanded to 4v4 with pets.
    """
    def __init__(self, attacker_session, defender_session):
        self.attacker = attacker_session
        self.defender = defender_session
        
        # Track pending actions for the current turn
        # Key: char_id, Value: action dict
        self.queued_actions: Dict[int, Dict[str, Any]] = {}
        
        # Background task for turn resolution timeout
        self.turn_timeout_task = None
        self.turn_number = 1

    def add_action(self, char_id: int, action: Dict[str, Any]):
        """Queue an action for a player."""
        self.queued_actions[char_id] = action
        logger.info(f"[Battle] Player {char_id} queued action: {action['type']}")
        
        # If both players have submitted actions, resolve the turn immediately
        if self.is_turn_ready():
            asyncio.create_task(self.resolve_turn())

    def is_turn_ready(self) -> bool:
        """Check if both players have submitted an action."""
        has_attacker = self.attacker.char_id in self.queued_actions
        has_defender = self.defender.char_id in self.queued_actions
        return has_attacker and has_defender

    async def start_turn_timer(self):
        """Start a 20-second timer for the turn (WLO standard is 20s)."""
        if self.turn_timeout_task:
            self.turn_timeout_task.cancel()
            
        async def turn_timer():
            await asyncio.sleep(20.0)
            logger.info(f"[Battle] Turn {self.turn_number} timed out. Resolving with default actions.")
            # Auto-defend for missing actions
            if self.attacker.char_id not in self.queued_actions:
                self.queued_actions[self.attacker.char_id] = {"type": "defend"}
            if self.defender.char_id not in self.queued_actions:
                self.queued_actions[self.defender.char_id] = {"type": "defend"}
            await self.resolve_turn()
            
        self.turn_timeout_task = asyncio.create_task(turn_timer())

    def get_opponent(self, session):
        """Returns the opposing player session."""
        if session.char_id == self.attacker.char_id:
            return self.defender
        return self.attacker

    async def broadcast(self, packet):
        """Sends a packet to both players."""
        if self.attacker.writer:
            await self.attacker.send_packet(packet)
        if self.defender.writer:
            await self.defender.send_packet(packet)

    async def resolve_turn(self):
        """Executes the queued actions and broadcasts animations/damage."""
        if self.turn_timeout_task:
            self.turn_timeout_task.cancel()
            self.turn_timeout_task = None

        logger.info(f"[Battle] Resolving turn {self.turn_number} between {self.attacker.char_name} and {self.defender.char_name}")
        
        # 1. Acknowledge turn start to both players (AC 50 Sub 6)
        # Attacker is typically at Grid 4,2
        # Defender is typically at Grid 1,2 (but from their perspective, they are 4,2)
        # We will handle perspective later inside gameserver.py sending.

        # For now, we will handle the battle resolution inside gameserver.py to easily access `PacketWriter` 
        # and other helper functions like `get_player_atk`.
        # This BattleInstance just holds state.
        pass
