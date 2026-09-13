import unittest
import asyncio
import os
import sqlite3
from typing import Dict, Any, List

from server.eve_event_interpreter import (
    GLOBAL_EVE_INTERPRETER,
    get_session_quest_state,
    set_session_quest_state,
)
from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
from server.chest_system import GLOBAL_CHEST_SYSTEM
from server.network import PacketWriter


class MockSession:
    def __init__(self, char_id: int = 42, char_name: str = "TestHero", map_id: int = 10035):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = map_id
        self.slot = 0
        self.x = 1300
        self.y = 2140
        self.inventory: List[Dict[str, Any]] = []
        self.quests: List[Dict[str, Any]] = []
        self.pets: List[Dict[str, Any]] = []
        self.sent_packets: List[bytes] = []
        self.dialogue_queue: List[Dict[str, Any]] = []
        self.pending_dialogue_choice = None
        self._actor_visibility = {}
        self.server = None

    async def send_packet(self, pkt):
        if hasattr(pkt, 'buffer'):
            data = bytes(pkt.buffer)
        elif isinstance(pkt, (bytes, bytearray)):
            data = bytes(pkt)
        else:
            data = b''
        self.sent_packets.append(data)


class MockServer:
    def __init__(self, db_path: str = "test_robinson.db"):
        self.db_path = db_path
        self.map_npcs = {}
        self.items = {"48016": "Robinson's Raft"}
        self.chest_system = GLOBAL_CHEST_SYSTEM
        self.broadcast_packets = []

    def get_item_name(self, item_id: int) -> str:
        return self.items.get(str(item_id), f"Item #{item_id}")

    async def grant_item(self, session, item_id: int, count: int = 1):
        session.inventory.append({"item_id": item_id, "count": count, "slot": len(session.inventory)})
        return True

    async def _send_quest_flag(self, session, quest_id: int, state: int):
        found = False
        for q in session.quests:
            if q.get("quest_id") == quest_id:
                q["state"] = state
                found = True
                break
        if not found:
            session.quests.append({"quest_id": quest_id, "state": state, "step": 1})
        pkt = PacketWriter().write_8(24).write_8(5).write_16(quest_id).write_8(state)
        await session.send_packet(pkt)

    async def send_dialogue(self, session, click_id: int, talk_id: int, step: int = 1, portrait_type: int = 3):
        dialog_hex = f"{talk_id & 0xFF:02x}{(talk_id >> 8) & 0xFF:02x}{(talk_id >> 16) & 0xFF:02x}"
        click_id_byte = click_id & 0xFF
        payload = bytes([
            0x00, 0x00, 0x00,
            step & 0xFF,
            0x01,
            portrait_type & 0xFF,
            click_id_byte,
            0x00,
            0x01, 0x00, 0x00, 0x00,
            0x00,
        ]) + bytes.fromhex(dialog_hex)
        pkt = PacketWriter().write_8(20).write_8(1).write_bytes(payload)
        await session.send_packet(pkt)

    def broadcast_to_map(self, map_id: int, pkt, exclude_session=None):
        if hasattr(pkt, 'buffer'):
            data = bytes(pkt.buffer)
        elif isinstance(pkt, (bytes, bytearray)):
            data = bytes(pkt)
        else:
            data = b''
        self.broadcast_packets.append((map_id, data))

    def save_player_to_db(self, session):
        pass


class TestRobinsonRaftChestCascade(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        eve_path = "data/eve.Emg"
        GLOBAL_EVE_INTERPRETER.load(eve_path)
        GLOBAL_PREEVENT_INTERPRETER.load_preevents(eve_path)
        cls.test_db = "test_robinson_cascade.db"
        GLOBAL_CHEST_SYSTEM.db_path = cls.test_db
        GLOBAL_CHEST_SYSTEM._ensure_tables()

    @classmethod
    def tearDownClass(cls):
        GLOBAL_CHEST_SYSTEM.db_path = "wlo_server.db"
        GLOBAL_CHEST_SYSTEM._ensure_tables()
        import gc, time
        gc.collect()
        if os.path.exists(cls.test_db):
            for _ in range(10):
                try:
                    os.remove(cls.test_db)
                    break
                except Exception:
                    gc.collect()
                    time.sleep(0.05)

    async def asyncSetUp(self):
        conn = sqlite3.connect(self.test_db)
        conn.execute("DELETE FROM charchests")
        conn.commit()
        conn.close()

        self.server = MockServer(self.test_db)
        from server.npc_manager import GLOBAL_NPC_MANAGER
        GLOBAL_NPC_MANAGER.load_npcs_from_eve("data/eve.Emg")
        self.server.map_npcs = GLOBAL_NPC_MANAGER.map_npcs

    async def test_fresh_player_takes_raft_cascades_to_robinson_dialogue(self):
        """Taking Robinson's Raft from Chest 7 must cascade immediately into Robinson's dialogue and complete quest to state 2."""
        session = MockSession(char_id=101, char_name="NewAdventurer", map_id=10035)
        session.server = self.server

        # Verify initial state: quest 12046 not started
        self.assertEqual(get_session_quest_state(session, 12046), 0)

        # Click Chest 7
        handled = await GLOBAL_EVE_INTERPRETER.try_execute(self.server, session, click_id=7)
        self.assertTrue(handled)

        # 1. Verify player received Robinson's Raft (Item 48016)
        has_raft = any(it.get("item_id") == 48016 for it in session.inventory)
        self.assertTrue(has_raft, "Player should have received Robinson's Raft (48016)")

        # 2. Verify Chest 7 was recorded in charchests
        self.assertTrue(
            GLOBAL_CHEST_SYSTEM.is_chest_opened(session.char_id, 10035, 7, is_permanent=True),
            "Chest 7 should be recorded as opened in charchests"
        )

        # 3. Verify cascading dialogue was dispatched: Talk 20355 from Robinson (speaker ClickID 1, portrait 3)
        dialogue_pkts = [p for p in session.sent_packets if len(p) >= 2 and p[0] == 20 and p[1] == 1]
        self.assertTrue(len(dialogue_pkts) > 0, "Dialogue packet AC 20:1 must be sent")
        first_diag = dialogue_pkts[0]
        # Payload: [20, 1, 0, 0, 0, step, 1, portrait, speaker, ...]
        portrait = first_diag[7]
        speaker = first_diag[8]
        talk_id = first_diag[15] | (first_diag[16] << 8) | (first_diag[17] << 16)
        self.assertEqual(speaker, 1, "Speaker ClickID must be 1 (Robinson)")
        self.assertEqual(portrait, 3, "Portrait must be 3 (NPC portrait)")
        self.assertEqual(talk_id, 20355, "Talk ID must be 20355 (Robinson's raft explanation)")

        # 4. Verify dialogue queue has remaining conversation steps queued
        self.assertTrue(len(session.dialogue_queue) > 0, "Dialogue queue must contain remaining conversation steps")

        # 5. Verify quest flags updated: Quest 12046 is state 2 (completed), 12047 is state 1
        self.assertEqual(get_session_quest_state(session, 12046), 2, "Quest 12046 must be state 2 (completed)")
        self.assertEqual(get_session_quest_state(session, 12047), 1, "Quest 12047 must be state 1 (in progress)")

        # 6. Verify PreEvent 5 condition on Map 10035 (12046 == 2) matches and sends AC 22:10 [7, 0x01, 0x00]
        session.sent_packets.clear()
        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(self.server, session, 10035)
        # Search for AC 22:10 [7, 0x01, 0x00]
        opened_chest_pkts = [
            p for p in session.sent_packets
            if len(p) >= 6 and p[0] == 22 and p[1] == 10 and (p[2] | (p[3] << 8)) == 7 and p[4] == 1 and p[5] == 0
        ]
        self.assertTrue(len(opened_chest_pkts) > 0, "PreEvent 5 must render Chest 7 in opened frame AC 22:10 [7, 0x01, 0x00]")

    async def test_resumed_player_with_flag_at_1_clicks_chest_triggers_dialogue(self):
        """A player whose quest flag was stuck at 1 (like Char 36) clicking Chest 7 must trigger Robinson's conversation."""
        session = MockSession(char_id=36, char_name="3131dsa", map_id=10035)
        session.server = self.server

        # Simulate user's exact DB state: quest 12046 at state 1, chest in charchests
        set_session_quest_state(session, 12046, 1, 1)
        GLOBAL_CHEST_SYSTEM.record_chest_opened(session.char_id, 10035, 7)

        # Click Chest 7
        handled = await GLOBAL_EVE_INTERPRETER.try_execute(self.server, session, click_id=7)
        self.assertTrue(handled)

        # Must trigger Sub 3 dialogue (not blocked by charchests!)
        dialogue_pkts = [p for p in session.sent_packets if len(p) >= 2 and p[0] == 20 and p[1] == 1]
        self.assertTrue(len(dialogue_pkts) > 0, "Dialogue packet must be sent")
        first_diag = dialogue_pkts[0]
        talk_id = first_diag[15] | (first_diag[16] << 8) | (first_diag[17] << 16)
        self.assertEqual(talk_id, 20355, "Should trigger Robinson's dialogue Talk 20355")

        # Quest 12046 advances to state 2
        self.assertEqual(get_session_quest_state(session, 12046), 2)
        self.assertEqual(get_session_quest_state(session, 12047), 1)

    async def test_completed_quest_chest_does_not_dupe_item(self):
        """Clicking Chest 7 after completing quest 12046 (state 2) and recruiting Robinson must not give duplicate items."""
        session = MockSession(char_id=102, char_name="DoneHero", map_id=10035)
        session.server = self.server
        set_session_quest_state(session, 12046, 2, 1)
        set_session_quest_state(session, 12047, 2, 1)
        set_session_quest_state(session, 15282, 2, 1)
        GLOBAL_CHEST_SYSTEM.record_chest_opened(session.char_id, 10035, 7)

        handled = await GLOBAL_EVE_INTERPRETER.try_execute(self.server, session, click_id=7)
        self.assertTrue(handled)

        # No new item granted
        self.assertEqual(len(session.inventory), 0, "No duplicate raft should be granted")

        # Sends already claimed message
        sys_msgs = [p for p in session.sent_packets if len(p) >= 3 and p[0] == 23 and p[1] == 57]
        self.assertTrue(len(sys_msgs) > 0, "Should send system prompt message")
        prompt_str = sys_msgs[0][3:].decode("ascii", errors="ignore")
        self.assertIn("already claimed", prompt_str)

    async def test_sync_opened_chests_on_map_entry_renders_chest_broken(self):
        """When player enters map 10035, sync_opened_chests_on_map must send AC 22:10 [7, 0x01, 0x00]."""
        session = MockSession(char_id=36, char_name="3131dsa", map_id=10035)
        session.server = self.server
        GLOBAL_CHEST_SYSTEM.record_chest_opened(session.char_id, 10035, 7)

        await GLOBAL_CHEST_SYSTEM.sync_opened_chests_on_map(session, 10035)

        opened_pkts = [
            p for p in session.sent_packets
            if len(p) >= 6 and p[0] == 22 and p[1] == 10 and (p[2] | (p[3] << 8)) == 7 and p[4] == 1 and p[5] == 0
        ]
        self.assertTrue(len(opened_pkts) > 0, "sync_opened_chests_on_map must send AC 22:10 frame [0x01, 0x00] for Chest 7")


if __name__ == "__main__":
    unittest.main()
