"""
Wonderland Online - Interactive Command Line Packet Recorder.
Provides live console feedback, tagging, and multi-format session export.
"""

from __future__ import annotations

import os
import sys
import time
import argparse
from typing import Optional

from packet_recorder.wlo_protocol import WLOPacket
from packet_recorder.recorder_engine import ProxyBridgeRecorder, SnifferRecorder


def format_packet_oneline(pkt: WLOPacket, elapsed: float) -> str:
    sub_info = f" Sub {pkt.sub_code}" if pkt.sub_code is not None else ""
    tag_info = f" | Tag: [{pkt.tag}]" if pkt.tag else ""
    arrow = "-->" if pkt.direction == "C->S" else "<--"
    return f"[{elapsed:07.2f}s] #{pkt.packet_id:05d} {arrow} [{pkt.direction}] AC {pkt.action_code:03d} ({pkt.action_name}){sub_info} | {pkt.length:3d}B{tag_info}"


def run_cli(
    mode: str = "proxy",
    listen_port: int = 6414,
    target_host: str = "127.0.0.1",
    target_port: int = 6414,
    output_dir: str = "packet_recorder/recordings",
):
    print("=" * 80)
    print(" 🎮 WONDERLAND ONLINE - AUTHENTIC PACKET RECORDER (CLI)")
    print("=" * 80)

    start_time = time.time()
    packet_count = 0

    def on_packet(pkt: WLOPacket):
        nonlocal packet_count
        packet_count += 1
        elapsed = time.time() - start_time
        print(format_packet_oneline(pkt, elapsed))

    def on_status(status: str):
        print(f"[STATUS] {status}")

    recorder = None
    if mode == "sniffer":
        print(f" Mode: Passive Network Sniffer (Game Ports: 6414, 6415, 6416, 25221, 25620)")
        recorder = SnifferRecorder(
            output_dir=output_dir,
            on_packet_callback=on_packet,
            on_status_callback=on_status,
        )
    else:
        print(f" Mode: Transparent TCP Proxy Bridge")
        print(f" Listening: 127.0.0.1:{listen_port} -> Upstream: {target_host}:{target_port}")
        recorder = ProxyBridgeRecorder(
            listen_host="127.0.0.1",
            listen_port=listen_port,
            target_host=target_host,
            target_port=target_port,
            output_dir=output_dir,
            on_packet_callback=on_packet,
            on_status_callback=on_status,
        )

    print(f" Output Directory: {os.path.abspath(output_dir)}")
    print("-" * 80)
    print(" Quick Commands while playing:")
    print("   tag <text>   : Bookmark what you are doing (e.g. 'tag clicked npc robinson')")
    print("   stats        : Show current statistics")
    print("   q / exit     : Stop recording and save all files")
    print("-" * 80)

    recorder.start()

    try:
        while recorder.is_running:
            try:
                line = input().strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            if line.lower() in ("q", "quit", "exit"):
                break
            elif line.lower() == "stats":
                if recorder.session:
                    s = recorder.session
                    print(f"\n--- [SESSION STATS] ---")
                    print(f" Total: {s.total_packets} | C->S: {s.client_packets} | S->C: {s.server_packets} | Bytes: {s.total_bytes}")
                    print(f" Active Tag: {s._active_tag}")
                    print(f" Top Opcodes: {sorted(s.action_counts.items(), key=lambda x: x[1], reverse=True)[:5]}")
                    print("-----------------------\n")
            elif line.lower().startswith("tag "):
                tag_text = line[4:].strip()
                recorder.add_tag(tag_text)
                print(f"[TAG ADDED] >>> {tag_text} <<<")
            else:
                # Direct input treated as tag
                recorder.add_tag(line)
                print(f"[TAG ADDED] >>> {line} <<<")

    finally:
        print("\nStopping recorder and saving files...")
        summary = recorder.stop()
        print("=" * 80)
        print(" ✅ RECORDING COMPLETE!")
        if summary:
            print(f" Total Packets: {summary['total_packets']} (C->S: {summary['client_to_server']}, S->C: {summary['server_to_client']})")
            print(f" Duration: {summary['duration_sec']}s")
            print(f" Files Created:")
            for k, v in summary['files'].items():
                if v:
                    print(f"   - {k.upper()}: {v}")
        print("=" * 80)
        print(" You can now upload these files or share them with the AI assistant!")
