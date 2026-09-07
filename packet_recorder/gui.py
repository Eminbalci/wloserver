"""
Wonderland Online - Modern Desktop GUI for Packet Recorder.
Built with CustomTkinter for modern Windows dark aesthetics.
Provides live packet visualization, real-time tagging, packet inspector, and 1-click export.
"""

from __future__ import annotations

import os
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Any, Dict, List

try:
    import customtkinter as ctk
    HAS_CTK = True
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    HAS_CTK = False

from packet_recorder.wlo_protocol import WLOPacket, bytes_to_hex_preview, bytes_to_ascii_preview
from packet_recorder.recorder_engine import ProxyBridgeRecorder, SnifferRecorder


class PacketRecorderGUI:
    """Desktop GUI interface for recording and inspecting Wonderland Online game packets."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🎮 Wonderland Online - Packet Recorder & Session Analyzer")
        self.root.geometry("1180x760")
        self.root.minsize(800, 520)

        if HAS_CTK and isinstance(self.root, ctk.CTk):
            self.root.configure(fg_color="#0B0F19")
        else:
            self.root.configure(bg="#0B0F19")

        self.recorder: Optional[Any] = None
        self.is_recording = False
        self.start_time = 0.0
        self.output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "recordings"))
        os.makedirs(self.output_dir, exist_ok=True)

        self._all_packets: List[WLOPacket] = []
        self._auto_scroll = True

        self._configure_styles()
        self._build_ui()
        self._schedule_timer()

    def _configure_styles(self):
        try:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure(
                "Treeview",
                background="#0B0F19",
                foreground="#F1F5F9",
                fieldbackground="#0B0F19",
                bordercolor="#1E293B",
                borderwidth=0,
                rowheight=26,
                font=("Segoe UI", 9)
            )
            style.configure(
                "Treeview.Heading",
                background="#111827",
                foreground="#38BDF8",
                relief="flat",
                borderwidth=1,
                bordercolor="#1E293B",
                font=("Segoe UI", 9, "bold")
            )
            style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")])
        except Exception:
            pass

    def _build_ui(self):
        # 1. Top Control Header
        top = ctk.CTkFrame(self.root, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=12, pady=(12, 6))

        # Title
        ctk.CTkLabel(
            top,
            text="🎮 WLO Packet Recorder",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        ).pack(side="left", padx=(14, 10), pady=10)

        # Mode Selector
        ctk.CTkLabel(top, text="Mode:", text_color="#94A3B8").pack(side="left", padx=(6, 2))
        self.cmb_mode = ctk.CTkComboBox(
            top,
            values=["Proxy Bridge (Recommended)", "Passive Sniffer"],
            width=200,
            command=self._on_mode_change
        )
        self.cmb_mode.set("Proxy Bridge (Recommended)")
        self.cmb_mode.pack(side="left", padx=4)

        # Upstream Host & Port Frame
        self.f_conn = ctk.CTkFrame(top, fg_color="transparent")
        self.f_conn.pack(side="left", padx=10)

        ctk.CTkLabel(self.f_conn, text="Target IP:", text_color="#94A3B8").pack(side="left", padx=(4, 2))
        self.ent_target_host = ctk.CTkEntry(self.f_conn, width=110)
        self.ent_target_host.insert(0, "127.0.0.1")
        self.ent_target_host.pack(side="left", padx=2)

        ctk.CTkLabel(self.f_conn, text="Port:", text_color="#94A3B8").pack(side="left", padx=(6, 2))
        self.ent_target_port = ctk.CTkEntry(self.f_conn, width=65)
        self.ent_target_port.insert(0, "6414")
        self.ent_target_port.pack(side="left", padx=2)

        # Action Buttons
        self.btn_toggle_rec = ctk.CTkButton(
            top,
            text="▶ Start Recording",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            width=150,
            height=34,
            command=self.toggle_recording
        )
        self.btn_toggle_rec.pack(side="right", padx=(6, 14), pady=8)

        btn_open_folder = ctk.CTkButton(
            top,
            text="📁 Open Folder",
            fg_color="#1E293B",
            hover_color="#334155",
            width=110,
            height=34,
            command=self.open_recordings_folder
        )
        btn_open_folder.pack(side="right", padx=4, pady=8)

        # 2. Metric Cards Row
        cards = ctk.CTkFrame(self.root, fg_color="transparent")
        cards.pack(fill="x", padx=12, pady=4)

        self.lbl_card_total = self._create_metric_card(cards, "TOTAL PACKETS", "0", "#38BDF8")
        self.lbl_card_c2s = self._create_metric_card(cards, "CLIENT -> SERVER (C->S)", "0", "#06B6D4")
        self.lbl_card_s2c = self._create_metric_card(cards, "SERVER -> CLIENT (S->C)", "0", "#10B981")
        self.lbl_card_time = self._create_metric_card(cards, "ELAPSED DURATION", "00:00", "#F59E0B")
        self.lbl_card_kb = self._create_metric_card(cards, "DATA VOLUME", "0.0 KB", "#8B5CF6")

        # 3. Live Annotation / Tagging Bar
        tag_bar = ctk.CTkFrame(self.root, fg_color="#111827", corner_radius=10, border_width=1, border_color="#1E293B")
        tag_bar.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(tag_bar, text="📌 Add In-Game Note / Bookmark:", font=ctk.CTkFont(weight="bold"), text_color="#F59E0B").pack(side="left", padx=12, pady=8)
        self.ent_tag = ctk.CTkEntry(
            tag_bar,
            placeholder_text="Type what you are currently doing (e.g. 'Clicked Robinson NPC', 'Entered Battle', 'Used Item')...",
            width=540
        )
        self.ent_tag.pack(side="left", fill="x", expand=True, padx=6, pady=8)
        self.ent_tag.bind("<Return>", lambda e: self.action_add_tag())

        btn_add_tag = ctk.CTkButton(
            tag_bar,
            text="📌 Bookmark Action",
            fg_color="#F59E0B",
            hover_color="#D97706",
            text_color="#000000",
            font=ctk.CTkFont(weight="bold"),
            width=150,
            command=self.action_add_tag
        )
        btn_add_tag.pack(side="right", padx=12, pady=8)

        # 4. Main Table View with Scrollbar
        mid_pane = ctk.CTkFrame(self.root, fg_color="transparent")
        mid_pane.pack(fill="both", expand=True, padx=12, pady=4)

        # Filter and Options strip
        filter_strip = ctk.CTkFrame(mid_pane, fg_color="transparent")
        filter_strip.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(filter_strip, text="Filter by Opcode / Text:", text_color="#94A3B8").pack(side="left", padx=4)
        self.ent_filter = ctk.CTkEntry(filter_strip, width=220, placeholder_text="e.g. 20, combat, warp...")
        self.ent_filter.pack(side="left", padx=4)
        self.ent_filter.bind("<KeyRelease>", self._on_filter_changed)

        self.var_autoscroll = tk.BooleanVar(value=True)
        chk_autoscroll = ctk.CTkCheckBox(filter_strip, text="Auto-Scroll", variable=self.var_autoscroll)
        chk_autoscroll.pack(side="right", padx=8)

        # Scrolled Treeview
        tree_container = ctk.CTkFrame(mid_pane, fg_color="transparent")
        tree_container.pack(fill="both", expand=True)

        cols = ("id", "time", "dir", "opcode", "name", "sub", "len", "tag")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse", height=12)
        self.tree.heading("id", text="#")
        self.tree.heading("time", text="Elapsed")
        self.tree.heading("dir", text="Direction")
        self.tree.heading("opcode", text="Opcode (AC)")
        self.tree.heading("name", text="System / Description")
        self.tree.heading("sub", text="Sub")
        self.tree.heading("len", text="Len")
        self.tree.heading("tag", text="Bookmark / Tag")

        self.tree.column("id", width=55, anchor="center")
        self.tree.column("time", width=80, anchor="center")
        self.tree.column("dir", width=85, anchor="center")
        self.tree.column("opcode", width=95, anchor="center")
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("sub", width=55, anchor="center")
        self.tree.column("len", width=65, anchor="center")
        self.tree.column("tag", width=220, anchor="w")

        # Color Tags for rows
        self.tree.tag_configure("C2S", foreground="#38BDF8")
        self.tree.tag_configure("S2C", foreground="#34D399")
        self.tree.tag_configure("TAGGED", background="#1E293B", foreground="#FBBF24")

        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(2, 0))
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_packet_selected)

        # 5. Bottom Packet Inspector Details Card
        bottom = ctk.CTkFrame(self.root, height=130, fg_color="#111827", corner_radius=10, border_width=1, border_color="#1E293B")
        bottom.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(bottom, text="🔍 Packet Inspector (Hex Dump & Dissection)", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(6, 2))

        self.txt_inspector = tk.Text(bottom, height=5, bg="#080C14", fg="#E2E8F0", font=("Consolas", 9), relief="flat", padx=8, pady=4)
        self.txt_inspector.pack(fill="x", padx=12, pady=(0, 8))

    def _create_metric_card(self, parent, title: str, init_val: str, color: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=10, border_width=1, border_color="#1E293B")
        card.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color="#94A3B8").pack(anchor="w", padx=10, pady=(6, 1))
        val_lbl = ctk.CTkLabel(card, text=init_val, font=ctk.CTkFont(size=17, weight="bold"), text_color=color)
        val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
        return val_lbl

    def _on_mode_change(self, mode_str: str):
        if "Sniffer" in mode_str:
            self.f_conn.pack_forget()
        else:
            self.f_conn.pack(side="left", padx=10)

    def action_add_tag(self):
        text = self.ent_tag.get().strip()
        if not text:
            return
        if self.recorder:
            self.recorder.add_tag(text)
        self.ent_tag.delete(0, tk.END)
        # Briefly flash tag entry
        self.ent_tag.configure(placeholder_text=f"Last note saved: '{text}'")

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        mode_str = self.cmb_mode.get()
        target_host = self.ent_target_host.get().strip() or "127.0.0.1"
        try:
            target_port = int(self.ent_target_port.get().strip() or "6414")
        except ValueError:
            target_port = 6414

        self._all_packets.clear()
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.start_time = time.time()

        if "Sniffer" in mode_str:
            self.recorder = SnifferRecorder(
                output_dir=self.output_dir,
                on_packet_callback=self._on_packet_received,
            )
        else:
            self.recorder = ProxyBridgeRecorder(
                listen_host="127.0.0.1",
                listen_port=6414,
                target_host=target_host,
                target_port=target_port,
                output_dir=self.output_dir,
                on_packet_callback=self._on_packet_received,
            )

        self.recorder.start()
        self.is_recording = True
        self.btn_toggle_rec.configure(text="⏹ Stop Recording", fg_color="#EF4444", hover_color="#DC2626")

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.btn_toggle_rec.configure(text="▶ Start Recording", fg_color="#10B981", hover_color="#059669")

        summary = None
        if self.recorder:
            summary = self.recorder.stop()
            self.recorder = None

        if summary:
            msg = (
                f"Recording Session Complete!\n\n"
                f"Total Packets: {summary['total_packets']}\n"
                f"Client -> Server: {summary['client_to_server']}\n"
                f"Server -> Client: {summary['server_to_client']}\n"
                f"Duration: {summary['duration_sec']}s\n\n"
                f"Files saved in:\n{self.output_dir}\n\n"
                f"You can now share these files directly with the AI assistant!"
            )
            messagebox.showinfo("Recording Saved", msg)

    def _on_packet_received(self, pkt: WLOPacket):
        # Called from background thread, schedule UI update on main thread
        self.root.after(0, self._insert_packet_ui, pkt)

    def _insert_packet_ui(self, pkt: WLOPacket):
        self._all_packets.append(pkt)

        # Update metric cards
        total = len(self._all_packets)
        c2s = sum(1 for p in self._all_packets if p.direction == "C->S")
        s2c = total - c2s
        tot_bytes = sum(p.length for p in self._all_packets)

        self.lbl_card_total.configure(text=str(total))
        self.lbl_card_c2s.configure(text=str(c2s))
        self.lbl_card_s2c.configure(text=str(s2c))
        self.lbl_card_kb.configure(text=f"{tot_bytes / 1024:.1f} KB")

        # Filter check
        f_txt = self.ent_filter.get().strip().lower()
        if f_txt:
            match = (
                f_txt in str(pkt.action_code)
                or f_txt in pkt.action_name.lower()
                or (pkt.tag and f_txt in pkt.tag.lower())
                or (pkt.sub_name and f_txt in pkt.sub_name.lower())
            )
            if not match:
                return

        tag_name = "TAGGED" if pkt.tag else ("C2S" if pkt.direction == "C->S" else "S2C")
        elapsed = pkt.timestamp - self.start_time
        vals = (
            pkt.packet_id,
            f"{elapsed:.2f}s",
            pkt.direction,
            f"AC {pkt.action_code}",
            pkt.action_name,
            pkt.sub_code if pkt.sub_code is not None else "-",
            pkt.length,
            pkt.tag or ""
        )
        item_id = self.tree.insert("", "end", values=vals, tags=(tag_name,))

        if self.var_autoscroll.get():
            self.tree.see(item_id)

    def _on_filter_changed(self, event=None):
        for i in self.tree.get_children():
            self.tree.delete(i)

        f_txt = self.ent_filter.get().strip().lower()
        for pkt in self._all_packets:
            if f_txt:
                match = (
                    f_txt in str(pkt.action_code)
                    or f_txt in pkt.action_name.lower()
                    or (pkt.tag and f_txt in pkt.tag.lower())
                    or (pkt.sub_name and f_txt in pkt.sub_name.lower())
                )
                if not match:
                    continue
            tag_name = "TAGGED" if pkt.tag else ("C2S" if pkt.direction == "C->S" else "S2C")
            elapsed = pkt.timestamp - self.start_time
            vals = (
                pkt.packet_id,
                f"{elapsed:.2f}s",
                pkt.direction,
                f"AC {pkt.action_code}",
                pkt.action_name,
                pkt.sub_code if pkt.sub_code is not None else "-",
                pkt.length,
                pkt.tag or ""
            )
            self.tree.insert("", "end", values=vals, tags=(tag_name,))

    def _on_packet_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        pkt_id = int(vals[0])
        pkt = next((p for p in self._all_packets if p.packet_id == pkt_id), None)
        if not pkt:
            return

        self.txt_inspector.delete("1.0", tk.END)
        self.txt_inspector.insert(tk.END, pkt.to_readable_card())

    def _schedule_timer(self):
        if self.is_recording and self.start_time > 0:
            elapsed = int(time.time() - self.start_time)
            m = elapsed // 60
            s = elapsed % 60
            self.lbl_card_time.configure(text=f"{m:02d}:{s:02d}")
        self.root.after(1000, self._schedule_timer)

    def open_recordings_folder(self):
        os.makedirs(self.output_dir, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(self.output_dir)
            else:
                subprocess.Popen(["xdg-open", self.output_dir])
        except Exception as e:
            messagebox.showinfo("Recordings Path", f"Saved in:\n{self.output_dir}")


def run_gui():
    root = ctk.CTk() if HAS_CTK else tk.Tk()
    app = PacketRecorderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
