"""
Unit tests for Wonderland Online Standalone Packet Recorder.
Tests XOR-173 cipher, stream reassembly, fragmentation recovery, multi-format session export, and tagging.
"""

import os
import sys
import json
import time
import shutil
import struct
import socket
import tempfile
import unittest
import threading
import asyncio

from packet_recorder.wlo_protocol import (
    XOR_KEY,
    SIGNATURE,
    SIGNATURE_ENCRYPTED,
    xor_crypt,
    WLOPacket,
    WLOStreamReassembler,
    infer_packet_fields,
)
from packet_recorder.recorder_engine import RecordingSession, ProxyBridgeRecorder


def make_test_frame(payload: bytes, encrypt: bool = True) -> bytes:
    header = struct.pack("<HH", SIGNATURE, len(payload))
    full = header + payload
    return xor_crypt(full, XOR_KEY) if encrypt else full


class TestPacketProtocol(unittest.TestCase):
    def test_xor_crypt_symmetric(self):
        data = b"Hello Wonderland Online 12345"
        encrypted = xor_crypt(data, XOR_KEY)
        decrypted = xor_crypt(encrypted, XOR_KEY)
        self.assertEqual(data, decrypted)

    def test_stream_reassembler_complete_packet(self):
        payload = bytes([20, 1, 0x2A, 0x27, 0x00, 0x00, 0x00, 0x00])  # AC 20 (Dialogue)
        frame = make_test_frame(payload, encrypt=True)

        reassembler = WLOStreamReassembler(direction="C->S")
        packets = reassembler.feed(frame)

        self.assertEqual(len(packets), 1)
        pkt = packets[0]
        self.assertEqual(pkt.action_code, 20)
        self.assertEqual(pkt.sub_code, 1)
        self.assertEqual(pkt.direction, "C->S")
        self.assertEqual(pkt.length, len(payload))
        self.assertEqual(pkt.decrypted_payload, payload)
        self.assertEqual(pkt.inferred_fields.get("click_id"), 10026)

    def test_stream_reassembler_fragmentation(self):
        payload = bytes([5, 0x64, 0x00, 0xC8, 0x00])  # AC 5 (Movement x=100, y=200)
        frame = make_test_frame(payload, encrypt=True)

        reassembler = WLOStreamReassembler(direction="C->S")

        # Split frame into 3 tiny chunks
        chunk1 = frame[:2]
        chunk2 = frame[2:5]
        chunk3 = frame[5:]

        pkts1 = reassembler.feed(chunk1)
        self.assertEqual(len(pkts1), 0)

        pkts2 = reassembler.feed(chunk2)
        self.assertEqual(len(pkts2), 0)

        pkts3 = reassembler.feed(chunk3)
        self.assertEqual(len(pkts3), 1)
        self.assertEqual(pkts3[0].action_code, 5)
        self.assertEqual(pkts3[0].inferred_fields.get("x"), 100)
        self.assertEqual(pkts3[0].inferred_fields.get("y"), 200)

    def test_stream_reassembler_coalesced_multiple_packets(self):
        p1 = bytes([2, 1, ord("h"), ord("i")])
        p2 = bytes([6, 0x0A, 0x00, 0x14, 0x00])
        frame = make_test_frame(p1, encrypt=True) + make_test_frame(p2, encrypt=True)

        reassembler = WLOStreamReassembler(direction="S->C")
        packets = reassembler.feed(frame)

        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0].action_code, 2)
        self.assertEqual(packets[1].action_code, 6)

    def test_stream_reassembler_corrupt_recovery(self):
        garbage = b"\x01\x02\x03\xDE\xAD\xBE\xEF"
        valid_payload = bytes([12, 0x01, 0x27, 0x00])  # Warp map 9985
        valid_frame = make_test_frame(valid_payload, encrypt=True)

        reassembler = WLOStreamReassembler(direction="C->S")
        packets = reassembler.feed(garbage + valid_frame)

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].action_code, 12)
        self.assertEqual(packets[0].length, len(valid_payload))


class TestRecordingSession(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wlo_test_rec_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_session_lifecycle_and_export(self):
        session = RecordingSession(output_dir=self.test_dir, session_id="test_session_01")
        session.set_active_tag("Test Bookmark")

        pkt = WLOPacket(
            packet_id=1,
            timestamp=time.time(),
            datetime_str="2026-09-07 14:40:00.000",
            direction="C->S",
            action_code=23,
            sub_code=5,
            action_name="Inventory",
            sub_name="Full Inventory Sync",
            length=10,
            decrypted_payload=bytes([23, 5] + [0] * 8),
            encrypted_bytes=b"\x59\xE9\xBD\xAD\x4A\xAA" + b"\xAD" * 8,
            tag=None,
        )

        session.record_packet(pkt)
        summary = session.finalize()

        self.assertEqual(summary["total_packets"], 1)
        self.assertEqual(summary["client_to_server"], 1)
        self.assertEqual(summary["server_to_client"], 0)
        self.assertEqual(summary["tags_count"], 1)

        # Verify JSONL content
        self.assertTrue(os.path.exists(session.jsonl_path))
        with open(session.jsonl_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["action_code"], 23)
        self.assertEqual(lines[0]["tag"], "Test Bookmark")

        # Verify readable log content
        self.assertTrue(os.path.exists(session.log_path))
        with open(session.log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        self.assertIn("Test Bookmark", log_content)
        self.assertIn("AC 23", log_content)

        # Verify summary JSON
        self.assertTrue(os.path.exists(session.summary_path))
        with open(session.summary_path, "r", encoding="utf-8") as f:
            sum_data = json.load(f)
        self.assertEqual(sum_data["total_packets"], 1)


class TestProxyBridgeRecorder(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="wlo_proxy_rec_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_proxy_forwarding_and_recording(self):
        # 1. Start a simple mock TCP echo server
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.bind(("127.0.0.1", 0))
        target_sock.listen(1)
        target_port = target_sock.getsockname()[1]

        def run_mock_server():
            try:
                conn, _ = target_sock.accept()
                data = conn.recv(1024)
                if data:
                    # Echo response: send back an S->C packet
                    resp_payload = bytes([10, 6, 0x01, 0x02])  # AC 10 (Combat State)
                    resp_frame = make_test_frame(resp_payload, encrypt=True)
                    conn.sendall(resp_frame)
                conn.close()
            except Exception:
                pass
            finally:
                target_sock.close()

        server_thread = threading.Thread(target=run_mock_server, daemon=True)
        server_thread.start()

        # Find free listen port
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        listen_port = probe.getsockname()[1]
        probe.close()

        captured_packets = []
        proxy = ProxyBridgeRecorder(
            listen_host="127.0.0.1",
            listen_port=listen_port,
            target_host="127.0.0.1",
            target_port=target_port,
            output_dir=self.test_dir,
            on_packet_callback=lambda p: captured_packets.append(p),
        )
        proxy.start()
        time.sleep(0.15)  # Wait for proxy to bind

        # 2. Connect client and send a C->S packet
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", listen_port))

        client_payload = bytes([24, 1, 0x05, 0x01])  # Quest AC 24
        client_frame = make_test_frame(client_payload, encrypt=True)
        client_sock.sendall(client_frame)

        # Receive echo response
        resp_data = client_sock.recv(1024)
        client_sock.close()

        time.sleep(0.15)  # Wait for packets to process
        summary = proxy.stop()

        self.assertIsNotNone(summary)
        self.assertGreaterEqual(summary["total_packets"], 1)
        self.assertGreaterEqual(len(captured_packets), 1)

        # Verify C->S packet was captured
        c2s_pkts = [p for p in captured_packets if p.direction == "C->S"]
        self.assertGreaterEqual(len(c2s_pkts), 1)
        self.assertEqual(c2s_pkts[0].action_code, 24)


if __name__ == "__main__":
    unittest.main()

