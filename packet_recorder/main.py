"""
Wonderland Online - Standalone Packet Recorder Entry Point.
Runs Desktop GUI or interactive CLI based on user preference and environment.
"""

from __future__ import annotations

import sys
import argparse

from packet_recorder.cli import run_cli


def main():
    parser = argparse.ArgumentParser(description="Wonderland Online - Standalone Packet Recorder")
    parser.add_argument("--cli", action="store_true", help="Launch interactive Command Line interface instead of GUI")
    parser.add_argument("--mode", choices=["proxy", "sniffer"], default="proxy", help="Capture mode: proxy bridge or passive sniffer")
    parser.add_argument("--listen-port", type=int, default=6414, help="Local listening port for proxy mode (default: 6414)")
    parser.add_argument("--target-host", type=str, default="127.0.0.1", help="Target server host (default: 127.0.0.1)")
    parser.add_argument("--target-port", type=int, default=6414, help="Target server port (default: 6414)")
    parser.add_argument("--out", type=str, default="packet_recorder/recordings", help="Output directory for recordings")

    args = parser.parse_args()

    if args.cli:
        run_cli(
            mode=args.mode,
            listen_port=args.listen_port,
            target_host=args.target_host,
            target_port=args.target_port,
            output_dir=args.out
        )
    else:
        try:
            from packet_recorder.gui import run_gui
            run_gui()
        except Exception as e:
            print(f"GUI launch failed ({e}), falling back to CLI mode...")
            run_cli(
                mode=args.mode,
                listen_port=args.listen_port,
                target_host=args.target_host,
                target_port=args.target_port,
                output_dir=args.out
            )


if __name__ == "__main__":
    main()
