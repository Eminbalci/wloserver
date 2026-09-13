"""
Unit and integration tests for South Island Beach (Map 10035) treasure chests,
props, PreEvents evaluation, and actor state isolation.
"""

import unittest
from typing import Dict, List, Any

from server.network import PacketWriter, PacketReader
from server.preevent_interpreter import GLOBAL_PREEVENT_INTERPRETER
from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER, set_session_quest_state
from server.npc_manager import GLOBAL_NPC_MANAGER


class MockSession:
    def __init__(self, char_id=123456, char_name="BeachExplorer", map_id=10035):
        self.char_id = char_id
        self.char_name = char_name
        self.map_id = map_id
        self.x = 1038
        self.y = 2235
        self.quests = []
        self.pets = []
        self.inventory: List[Dict[str, Any]] = []
        self.sent_packets: List[str] = []
        self._actor_visibility: Dict[int, bool] = {}
        self.server = None

    async def send_packet(self, pkt):
        raw = pkt.buffer if hasattr(pkt, 'buffer') else bytes(pkt)
        self.sent_packets.append(raw.hex())


class MockServer:
    def __init__(self):
        self.map_npcs = {}
        self.quest_scripts = {}
        self.items = {"32075": "Raft Oar", "41066": "Coconut"}

    def get_item_name(self, item_id: int) -> str:
        return self.items.get(str(item_id), f"Item #{item_id}")

    def broadcast_to_map(self, map_id, pkt, exclude_session=None):
        pass

    def save_player_to_db(self, session):
        pass

    async def _send_quest_flag(self, session, quest_id: int, state: int):
        pass

    async def grant_item(self, session, item_id: int, count: int = 1):
        session.inventory.append({"item_id": item_id, "count": count})


class TestBeachChestsPreevent(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        GLOBAL_PREEVENT_INTERPRETER.load_preevents("data/eve.Emg")
        GLOBAL_EVE_INTERPRETER.load("data/eve.Emg")
        GLOBAL_NPC_MANAGER.load_npcs_from_eve("data/eve.Emg")

        self.server = MockServer()
        self.server.map_npcs[10035] = GLOBAL_NPC_MANAGER.map_npcs.get(10035, [])
        self.session = MockSession()
        self.session.server = self.server

    async def test_beach_fresh_player_chests_visible_and_closed(self):
        """
        A fresh player arriving on Map 10035 must NOT have any unopened chests despawned
        or sent corrupting AC 22:11 scene isolation packets.
        """
        s = self.session
        srv = self.server

        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(srv, s, 10035)

        # No hide packets should be sent for unopened chests (2, 3, 4, 5, 7) or coconut (6)
        for click_id in (2, 3, 4, 5, 6, 7):
            hide_10 = f"160a{click_id:02x}00ffff"
            hide_11 = f"160b{click_id:02x}00ffff"
            corrupt_11 = f"160b{click_id:02x}000000"
            self.assertFalse(
                any(hide_10 in pkt for pkt in s.sent_packets),
                f"Chest #{click_id} was unexpectedly sent AC 22:10 despawn packet!"
            )
            self.assertFalse(
                any(hide_11 in pkt for pkt in s.sent_packets),
                f"Chest #{click_id} was unexpectedly sent AC 22:11 despawn packet!"
            )
            self.assertFalse(
                any(corrupt_11 in pkt for pkt in s.sent_packets),
                f"Chest #{click_id} was unexpectedly sent AC 22:11 corrupting 0x00 0x00 packet!"
            )
            self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 10035, click_id))

    async def test_click_raft_oar_chest_opens_only_chest_3(self):
        """
        Clicking Chest #3 (ClickID 3, Raft Oar Quest 12026) must set Chest #3
        to opened state (AC 22:10 [22, 10, 3, 1, 0]) while leaving all other chests
        (2, 4, 5, 7) and Coconut (6) intact and visible.
        """
        s = self.session
        srv = self.server

        # Execute Click on Chest 3 via EveEventInterpreter
        res = await GLOBAL_EVE_INTERPRETER.try_execute(srv, s, 3)
        self.assertTrue(res, "EveEventInterpreter failed to execute Chest #3 interaction")

        # Verify Raft Oar was granted
        self.assertTrue(
            any(it.get("item_id") == 32075 for it in s.inventory),
            "Raft Oar (#32075) was not added to player inventory"
        )

        # Verify Chest 3 received opened frame: 22 (0x16), 10 (0x0a), click_id 3 (0x03 0x00), state 1, 0 (0x01 0x00)
        opened_pkt = "160a03000100"
        self.assertTrue(
            any(opened_pkt in pkt for pkt in s.sent_packets),
            f"Chest #3 opened sprite packet ({opened_pkt}) was not sent! Packets: {s.sent_packets}"
        )

        # Other chests (2, 4, 5, 7) must NOT be despawned or sent opened state
        for other_cid in (2, 4, 5, 7):
            hide_10 = f"160a{other_cid:02x}00ffff"
            hide_11 = f"160b{other_cid:02x}00ffff"
            self.assertFalse(
                any(hide_10 in pkt for pkt in s.sent_packets),
                f"Unopened chest #{other_cid} was despawned by AC 22:10!"
            )
            self.assertFalse(
                any(hide_11 in pkt for pkt in s.sent_packets),
                f"Unopened chest #{other_cid} was despawned by AC 22:11!"
            )
            self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 10035, other_cid))

        # Coconut (6) must still be visible and not despawned
        self.assertFalse(any("160a0600ffff" in pkt for pkt in s.sent_packets))
        self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 10035, 6))

    async def test_reentry_with_opened_chest_shows_chest_3_opened_and_others_closed(self):
        """
        When re-entering Map 10035 with Quest 12026 already completed,
        Chest 3 receives opened frame while other chests remain closed.
        """
        s = self.session
        srv = self.server

        # Mark Quest 12026 completed (chest opened)
        set_session_quest_state(s, 12026, 2, step=1)
        s.sent_packets.clear()

        await GLOBAL_PREEVENT_INTERPRETER.sync_per_player_npc_visibility(srv, s, 10035)

        # Chest 3 must receive opened sprite frame
        opened_pkt = "160a03000100"
        self.assertTrue(
            any(opened_pkt in pkt for pkt in s.sent_packets),
            f"Chest #3 did not receive opened sprite packet on map sync: {s.sent_packets}"
        )

        # Other chests must receive NO state modification packets
        for other_cid in (2, 4, 5, 7):
            self.assertFalse(
                any(f"160a{other_cid:02x}00" in pkt for pkt in s.sent_packets),
                f"Other chest #{other_cid} received unexpected state packet!"
            )

    async def test_click_coconut_despawns_only_coconut(self):
        """
        Picking the Coconut on the beach (ClickID 6, Quest 12034) must despawn ONLY
        the Coconut (AC 22:10 6 FF FF), while leaving all chests (2, 3, 4, 5, 7) visible.
        """
        s = self.session
        srv = self.server

        res = await GLOBAL_EVE_INTERPRETER.try_execute(srv, s, 6)
        self.assertTrue(res, "EveEventInterpreter failed to execute Coconut #6 interaction")

        # Verify Coconut item granted
        self.assertTrue(any(it.get("item_id") == 41066 for it in s.inventory))

        # Verify Coconut #6 received hide packet: 22, 10, click 6, FF FF
        hide_coconut = "160a0600ffff"
        self.assertTrue(
            any(hide_coconut in pkt for pkt in s.sent_packets),
            f"Coconut #6 was not despawned! Packets: {s.sent_packets}"
        )

        # Chests (2, 3, 4, 5, 7) must NOT be despawned
        for cid in (2, 3, 4, 5, 7):
            self.assertFalse(any(f"160a{cid:02x}00ffff" in pkt for pkt in s.sent_packets))
            self.assertTrue(GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(s, 10035, cid))


if __name__ == "__main__":
    unittest.main()

