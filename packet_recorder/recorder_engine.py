"""
Wonderland Online - Packet Recorder Engine.
Supports Transparent TCP Proxy Bridge (Recommended, Zero Driver Required)
and Passive Scapy Network Sniffer with real-time multi-format export (JSONL, Readable LOG, PCAP, Summary JSON).
"""

from __future__ import annotations

import os
import time
import json
import socket
import asyncio
import logging
import threading
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any, Tuple

from packet_recorder.wlo_protocol import (
    WLOPacket,
    WLOStreamReassembler,
    xor_crypt,
)

try:
    import scapy.all as scapy
    from scapy.layers.inet import IP, TCP, Ether
    from scapy.utils import PcapWriter
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

logger = logging.getLogger("PacketRecorder")


class RecordingSession:
    """Manages output file streams and statistics for a single recording session."""

    def __init__(self, output_dir: str, session_id: Optional[str] = None):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        if session_id is None:
            session_id = "session_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id

        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_packets = 0
        self.client_packets = 0
        self.server_packets = 0
        self.total_bytes = 0
        self.action_counts: Dict[int, int] = {}
        self.tags: List[Dict[str, Any]] = []
        self._active_tag: Optional[str] = None
        self._lock = threading.Lock()

        # Paths
        self.jsonl_path = os.path.join(self.output_dir, f"{self.session_id}.jsonl")
        self.log_path = os.path.join(self.output_dir, f"{self.session_id}_readable.log")
        self.pcap_path = os.path.join(self.output_dir, f"{self.session_id}.pcap")
        self.summary_path = os.path.join(self.output_dir, f"{self.session_id}_summary.json")

        # Open file handles with line buffering for instant flush
        self._jsonl_file = open(self.jsonl_path, "a", encoding="utf-8", buffering=1)
        self._log_file = open(self.log_path, "a", encoding="utf-8", buffering=1)

        # Write initial human-readable log header
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log_file.write(
            f"================================================================================\n"
            f" Wonderland Online - Authentic Packet Recording Session\n"
            f" Session ID: {self.session_id}\n"
            f" Started At: {now_str}\n"
            f" Files: {os.path.basename(self.jsonl_path)}, {os.path.basename(self.log_path)}\n"
            f"================================================================================\n\n"
        )

        # PCAP writer
        self._pcap_writer = None
        if HAS_SCAPY:
            try:
                self._pcap_writer = PcapWriter(self.pcap_path, append=True, sync=True)
            except Exception as e:
                logger.debug(f"Could not initialize PCAP writer: {e}")

    def set_active_tag(self, tag_text: str):
        """Sets a tag/annotation that will be attached to subsequent packets."""
        with self._lock:
            tag_text = tag_text.strip()
            self._active_tag = tag_text if tag_text else None
            if self._active_tag:
                elapsed = time.time() - self.start_time
                tag_entry = {
                    "timestamp": time.time(),
                    "elapsed_sec": round(elapsed, 3),
                    "tag": self._active_tag,
                    "packet_idx": self.total_packets,
                }
                self.tags.append(tag_entry)
                # Write tag event to log file
                self._log_file.write(
                    f"\n>>> [BOOKMARK / TAG at {elapsed:08.3f}s] {self._active_tag} <<<\n\n"
                )

    def record_packet(self, packet: WLOPacket):
        """Records a parsed packet to JSONL, human-readable LOG, and PCAP."""
        with self._lock:
            self.total_packets += 1
            if packet.direction == "C->S":
                self.client_packets += 1
            else:
                self.server_packets += 1

            self.total_bytes += packet.length
            self.action_counts[packet.action_code] = self.action_counts.get(packet.action_code, 0) + 1

            # Attach active tag if set
            if self._active_tag and not packet.tag:
                packet.tag = self._active_tag

            elapsed = packet.timestamp - self.start_time

            # 1. Write JSONL line
            packet_dict = packet.to_dict()
            packet_dict["elapsed_sec"] = round(elapsed, 3)
            self._jsonl_file.write(json.dumps(packet_dict, ensure_ascii=False) + "\n")

            # 2. Write formatted card to human-readable log
            self._log_file.write(packet.to_readable_card(elapsed_sec=elapsed) + "\n\n")

            # 3. Write synthetic packet to PCAP for Wireshark
            if self._pcap_writer:
                try:
                    src_ip = "127.0.0.1" if packet.direction == "C->S" else "10.0.0.1"
                    dst_ip = "10.0.0.1" if packet.direction == "C->S" else "127.0.0.1"
                    sport = 55000 if packet.direction == "C->S" else 6414
                    dport = 6414 if packet.direction == "C->S" else 55000
                    raw_frame = packet.encrypted_bytes

                    scapy_pkt = Ether() / IP(src=src_ip, dst=dst_ip) / TCP(sport=sport, dport=dport, flags="PA") / raw_frame
                    scapy_pkt.time = packet.timestamp
                    self._pcap_writer.write(scapy_pkt)
                except Exception:
                    pass

    def finalize(self) -> Dict[str, Any]:
        """Finalizes the recording session and writes summary JSON."""
        with self._lock:
            self.end_time = time.time()
            duration = self.end_time - self.start_time

            summary = {
                "session_id": self.session_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_sec": round(duration, 2),
                "total_packets": self.total_packets,
                "client_to_server": self.client_packets,
                "server_to_client": self.server_packets,
                "total_bytes": self.total_bytes,
                "action_code_histogram": self.action_counts,
                "tags_count": len(self.tags),
                "tags": self.tags,
                "files": {
                    "jsonl": self.jsonl_path,
                    "readable_log": self.log_path,
                    "pcap": self.pcap_path if (self._pcap_writer and os.path.exists(self.pcap_path)) else None,
                }
            }

            try:
                with open(self.summary_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.debug(f"Could not write summary JSON: {e}")

            try:
                self._log_file.write(
                    f"================================================================================\n"
                    f" Session Finished | Total Packets: {self.total_packets} "
                    f"(C->S: {self.client_packets}, S->C: {self.server_packets}) | "
                    f"Duration: {duration:.2f}s\n"
                    f" Summary saved to: {os.path.basename(self.summary_path)}\n"
                    f"================================================================================\n"
                )
                self._jsonl_file.close()
                self._log_file.close()
                if self._pcap_writer:
                    self._pcap_writer.close()
            except Exception:
                pass

            return summary


class ProxyBridgeRecorder:
    """
    High-performance transparent TCP proxy bridge for Wonderland Online.
    Listens on local port (e.g. 127.0.0.1:6414) and forwards traffic to remote server.
    Completely non-intrusive, zero external drivers or root privileges required.
    """

    def __init__(
        self,
        listen_host: str = "127.0.0.1",
        listen_port: int = 6414,
        target_host: str = "127.0.0.1",
        target_port: int = 6414,
        output_dir: str = "packet_recorder/recordings",
        on_packet_callback: Optional[Callable[[WLOPacket], None]] = None,
        on_status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.output_dir = output_dir
        self.on_packet_callback = on_packet_callback
        self.on_status_callback = on_status_callback

        self.session: Optional[RecordingSession] = None
        self.server: Optional[asyncio.AbstractServer] = None
        self.is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def _notify_status(self, status: str):
        if self.on_status_callback:
            try:
                self.on_status_callback(status)
            except Exception:
                pass

    def add_tag(self, tag: str):
        """Adds live annotation tag to the recording."""
        if self.session:
            self.session.set_active_tag(tag)

    async def _handle_connection(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        client_addr = client_writer.get_extra_info("peername")
        logger.info(f"[Proxy] Client connected from {client_addr}")
        self._notify_status(f"Client connected: {client_addr}")

        try:
            target_reader, target_writer = await asyncio.open_connection(self.target_host, self.target_port)
            logger.info(f"[Proxy] Connected upstream to {self.target_host}:{self.target_port}")
        except Exception as e:
            logger.error(f"[Proxy] Failed to connect upstream to {self.target_host}:{self.target_port}: {e}")
            self._notify_status(f"Upstream connection failed: {e}")
            client_writer.close()
            await client_writer.wait_closed()
            return

        c2s_reassembler = WLOStreamReassembler(direction="C->S")
        s2c_reassembler = WLOStreamReassembler(direction="S->C")

        async def forward_c2s():
            try:
                while self.is_running:
                    data = await client_reader.read(4096)
                    if not data:
                        break
                    target_writer.write(data)
                    await target_writer.drain()

                    # Reassemble and record
                    packets = c2s_reassembler.feed(data, active_tag=self.session._active_tag if self.session else None)
                    for pkt in packets:
                        if self.session:
                            self.session.record_packet(pkt)
                        if self.on_packet_callback:
                            try:
                                self.on_packet_callback(pkt)
                            except Exception:
                                pass
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"[Proxy] C->S stream error: {e}")
            finally:
                try:
                    target_writer.close()
                    await target_writer.wait_closed()
                except Exception:
                    pass

        async def forward_s2c():
            try:
                while self.is_running:
                    data = await target_reader.read(4096)
                    if not data:
                        break
                    client_writer.write(data)
                    await client_writer.drain()

                    # Reassemble and record
                    packets = s2c_reassembler.feed(data, active_tag=self.session._active_tag if self.session else None)
                    for pkt in packets:
                        if self.session:
                            self.session.record_packet(pkt)
                        if self.on_packet_callback:
                            try:
                                self.on_packet_callback(pkt)
                            except Exception:
                                pass
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"[Proxy] S->C stream error: {e}")
            finally:
                try:
                    client_writer.close()
                    await client_writer.wait_closed()
                except Exception:
                    pass

        # Run both forwarding loops concurrently
        await asyncio.gather(forward_c2s(), forward_s2c(), return_exceptions=True)
        logger.info(f"[Proxy] Connection closed for {client_addr}")
        self._notify_status("Client disconnected")

    async def _start_server(self):
        self.session = RecordingSession(self.output_dir)
        self.is_running = True
        self.server = await asyncio.start_server(self._handle_connection, self.listen_host, self.listen_port)
        addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
        logger.info(f"[Proxy] Proxy Bridge active on {addrs} -> {self.target_host}:{self.target_port}")
        self._notify_status(f"Recording active on {self.listen_host}:{self.listen_port} -> {self.target_host}:{self.target_port}")
        async with self.server:
            await self.server.serve_forever()

    def start(self):
        """Starts the proxy bridge in a dedicated background thread."""
        if self.is_running:
            return

        def run_thread():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._start_server())
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"[Proxy] Error in loop: {e}")
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=run_thread, daemon=True, name="WLO-ProxyRecorder")
        self._thread.start()

    def stop(self) -> Optional[Dict[str, Any]]:
        """Stops the proxy bridge and finalizes the recording session."""
        self.is_running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

        summary = None
        if self.session:
            summary = self.session.finalize()
            self.session = None

        self._notify_status("Recording stopped")
        return summary


class SnifferRecorder:
    """
    Passive Scapy network sniffer for Wonderland Online.
    Captures raw packets on network interfaces matching game ports.
    """

    def __init__(
        self,
        ports: Tuple[int, ...] = (6414, 6415, 6416, 25221, 25620),
        output_dir: str = "packet_recorder/recordings",
        on_packet_callback: Optional[Callable[[WLOPacket], None]] = None,
        on_status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.ports = ports
        self.output_dir = output_dir
        self.on_packet_callback = on_packet_callback
        self.on_status_callback = on_status_callback

        self.session: Optional[RecordingSession] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._reassemblers: Dict[str, WLOStreamReassembler] = {}

    def _notify_status(self, status: str):
        if self.on_status_callback:
            try:
                self.on_status_callback(status)
            except Exception:
                pass

    def add_tag(self, tag: str):
        if self.session:
            self.session.set_active_tag(tag)

    def _on_sniffed_packet(self, scapy_pkt: Any):
        if not self.is_running or not scapy_pkt.haslayer(TCP):
            return

        tcp_layer = scapy_pkt[TCP]
        raw_payload = bytes(tcp_layer.payload)
        if not raw_payload:
            return

        sport = tcp_layer.sport
        dport = tcp_layer.dport

        if dport in self.ports:
            direction = "C->S"
        elif sport in self.ports:
            direction = "S->C"
        else:
            return

        flow_key = f"{direction}_{sport}_{dport}"
        if flow_key not in self._reassemblers:
            self._reassemblers[flow_key] = WLOStreamReassembler(direction=direction)

        reassembler = self._reassemblers[flow_key]
        packets = reassembler.feed(raw_payload, active_tag=self.session._active_tag if self.session else None)
        for pkt in packets:
            if self.session:
                self.session.record_packet(pkt)
            if self.on_packet_callback:
                try:
                    self.on_packet_callback(pkt)
                except Exception:
                    pass

    def start(self):
        if not HAS_SCAPY:
            self._notify_status("Error: Scapy is required for sniffer mode")
            return
        if self.is_running:
            return

        self.session = RecordingSession(self.output_dir)
        self.is_running = True
        self._reassemblers.clear()

        port_filter = " or ".join(f"port {p}" for p in self.ports)
        bpf_filter = f"tcp and ({port_filter})"
        self._notify_status(f"Sniffing packets on {bpf_filter}...")

        def run_sniff():
            try:
                scapy.sniff(
                    filter=bpf_filter,
                    prn=self._on_sniffed_packet,
                    store=False,
                    stop_filter=lambda p: not self.is_running
                )
            except Exception as e:
                logger.error(f"[Sniffer] Error: {e}")
                self._notify_status(f"Sniffer error: {e}")
            finally:
                self.is_running = False

        self._thread = threading.Thread(target=run_sniff, daemon=True, name="WLO-PassiveSniffer")
        self._thread.start()

    def stop(self) -> Optional[Dict[str, Any]]:
        self.is_running = False
        summary = None
        if self.session:
            summary = self.session.finalize()
            self.session = None
        self._notify_status("Sniffer stopped")
        return summary
