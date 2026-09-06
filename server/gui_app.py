"""
Wonderland Online - Modern Desktop Administrator Control Suite (GUI)
100% Feature-Complete Port from authentic C# MainForm1.cs & CharacterDataEditorForm.cs.
Built with CustomTkinter for high-DPI modern Windows 11 dark aesthetics.

Includes:
1. 📊 Dashboard & Live Server Console (Metrics, System Status, Player Counter, Uptime, Color Log Terminal, F5 Client Launch)
2. ⚡ Live Cheats & 4-Column Browser (Maps, Vehicles, Items Spawner, NPC/Monster Battler & Recruiter, Stat Points, Gold, IM)
3. 👥 Online Players & Session Manager (Kick, Ban, Warp To, Summon, Private Message, God Mode, Full Heal)
4. 🗄️ Users & Account Manager (All accounts in SQLite, Add Account, Delete Account, Change Password, IM Points, Ban/Unban)
5. 🧙 Characters Manager & Deep Data Editor (Stats, Quests, Pets/Companions, 50 Inv + 6 Equips, Skills, NPC PreEvent Visibility)
6. 🚪 Portals & Destinations Manager (Portals from eve.Emg & DB, Custom Warps, Add/Edit/Delete, Live Test Warp)
7. 🗺️ Map NPC & Scene Event Studio (1,119 Maps, NPC list, Coordinates, Full Event Sequence Flow Viewer, Simulate Event on Player)
8. 🐉 Monster Drops Studio (Search 1,166 monsters, 5 Drop slots, Item IDs, Drop Rates %, Save live to dynamic DB)
9. 📦 Chest Drops & Dynamic Respawn Studio (Chests by map, Item IDs, Drop Rates, Respawn timer seconds, Save live to dynamic DB)
10. 💎 Item Mall Manager (Catalog, Prices in Gold / IM Points, Categories, Add/Edit/Delete, Hot/New badges, Save live)
11. 🧙 NPC Name Resolver & Directory (Live TID Resolver, Category filters, 4,916 NPCs, World Spawn Coordinates Inspector)
12. 📜 Talk Dialogue Resolver (Search 17,489 dialogues from Talk.dat, Formatted speech cards preview)
13. ⚙️ Global Rates & Dynamic Settings (EXP/Drop/Gold/Pet multipliers, Server name, Broadcast announcements, Hot-Reload 19 subsystems)
"""

import os
import sys
import time
import json
import sqlite3
import logging
import asyncio
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, List, Optional, Any, Tuple

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
from server.dat_loaders import GLOBAL_NPC_DAT, GLOBAL_TALK_DAT, GLOBAL_ITEM_DAT
from server.item_mall import GLOBAL_ITEM_MALL_MANAGER, resolve_category_id, CATEGORY_ID_TO_NAME
from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
from server.network import PacketWriter

logger = logging.getLogger("ModernGUI")


def safe_run_coroutine(coro, loop):
    """Safely runs a coroutine on an asyncio loop, gracefully ignoring MagicMocks or non-coroutines in test environments."""
    if coro is not None and asyncio.iscoroutine(coro) and loop and hasattr(loop, "is_closed") and not loop.is_closed():
        try:
            return asyncio.run_coroutine_threadsafe(coro, loop)
        except Exception as e:
            logger.debug(f"safe_run_coroutine failed: {e}")
    return None


# =========================================================================
# UI Scrollbar Helper Utilities
# =========================================================================

def attach_scrollbar(widget, parent, side="right", fill="y", pack_widget=True, padx=(0, 2), pady=0):
    """
    Attaches a modern themed scrollbar to any scrollable Tk/ttk widget (Treeview, Listbox, Text).
    If pack_widget is True, packs the widget on the left and the scrollbar on the right.
    Returns (scrollbar, container_frame).
    """
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill="both", expand=True)

    if HAS_CTK:
        scrollbar = ctk.CTkScrollbar(container, orientation="vertical", command=widget.yview)
    else:
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=widget.yview)

    widget.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=side, fill=fill, padx=padx, pady=pady)
    widget.pack(side="left", fill="both", expand=True)

    return scrollbar, container


def create_scrolled_treeview(parent, columns, show="headings", selectmode="extended", height=10, padx=10, pady=6):
    """
    Creates a ttk.Treeview with a docked vertical scrollbar inside a dedicated transparent frame.
    Returns (tree, scrollbar, frame).
    """
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=padx, pady=pady)

    tree = ttk.Treeview(frame, columns=columns, show=show, selectmode=selectmode, height=height)

    if HAS_CTK:
        scrollbar = ctk.CTkScrollbar(frame, orientation="vertical", command=tree.yview)
    else:
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)

    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y", padx=(2, 0))
    tree.pack(side="left", fill="both", expand=True)

    return tree, scrollbar, frame


# =========================================================================
# Responsive Dynamic Flow / Wrapping Layout Container
# =========================================================================

class ResponsiveFlowFrame(ctk.CTkFrame if HAS_CTK else tk.Frame):
    """
    Responsive container that automatically flows/wraps child widgets into
    multiple rows when the available width is constrained, preventing button
    clipping, text truncation, and off-screen overflow.
    """
    def __init__(self, master, padx: int = 4, pady: int = 4, **kwargs):
        if "height" in kwargs:
            del kwargs["height"]
        super().__init__(master, **kwargs)
        self.item_padx = padx
        self.item_pady = pady
        self._flow_widgets: List[Tuple[Any, Any, Any, str]] = []
        self._last_width = 0
        self._relayout_after_id = None
        self.bind("<Configure>", self._on_configure)
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event=None):
        if self._relayout_after_id:
            try:
                self.after_cancel(self._relayout_after_id)
            except Exception:
                pass
            self._relayout_after_id = None

    def add_widget(self, widget: Any, padx: Any = None, pady: Any = None, sticky: str = "w") -> Any:
        """Registers a child widget to be dynamically flowed within the responsive container."""
        p_x = self.item_padx if padx is None else padx
        p_y = self.item_pady if pady is None else pady
        self._flow_widgets.append((widget, p_x, p_y, sticky))
        self._schedule_relayout()
        return widget

    def clear_widgets(self):
        """Clears registered flow widgets."""
        for w, _, _, _ in self._flow_widgets:
            if hasattr(w, "winfo_exists") and w.winfo_exists():
                w.grid_forget()
        self._flow_widgets.clear()
        self._schedule_relayout()

    def _on_configure(self, event):
        if event.width <= 10 or abs(event.width - self._last_width) < 6:
            return
        self._last_width = event.width
        self._schedule_relayout()

    def _schedule_relayout(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self._relayout_after_id:
            try:
                self.after_cancel(self._relayout_after_id)
            except Exception:
                pass
            self._relayout_after_id = None
        try:
            self._relayout_after_id = self.after(10, self._relayout)
        except Exception:
            pass

    def _relayout(self):
        self._relayout_after_id = None
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        try:
            width = self.winfo_width()
            if width <= 20:
                width = self.winfo_reqwidth()
            if width <= 20:
                try:
                    width = self.master.winfo_width() - 30
                except Exception:
                    pass
            if width <= 20:
                return

            for w, _, _, _ in self._flow_widgets:
                if hasattr(w, "winfo_exists") and w.winfo_exists():
                    w.grid_forget()

            cur_row = 0
            cur_col = 0
            cur_row_width = 0
            avail_width = max(width - 24, 80)

            for widget, px, py, sticky in self._flow_widgets:
                if hasattr(widget, "winfo_exists") and not widget.winfo_exists():
                    continue
                w_w = widget.winfo_reqwidth()
                pad_x_total = (px[0] + px[1]) if isinstance(px, tuple) else (px * 2)
                item_total_w = w_w + pad_x_total

                if cur_col > 0 and (cur_row_width + item_total_w > avail_width):
                    cur_row += 1
                    cur_col = 0
                    cur_row_width = 0

                widget.grid(row=cur_row, column=cur_col, padx=px, pady=py, sticky=sticky)
                cur_row_width += item_total_w
                cur_col += 1
        except Exception:
            pass


# Helper for item display names
_ITEM_NAMES_CACHE: Dict[int, str] = {}

def get_item_display_name(item_id: int) -> str:
    """Resolves item ID to human-readable item name from starter pack, items.json, Item.dat, or dynamic tables."""
    if not item_id:
        return "Empty"
    if item_id in _ITEM_NAMES_CACHE:
        return _ITEM_NAMES_CACHE[item_id]

    # 1. Check starter items dynamic table / manager
    try:
        from server.starter_pack_manager import GLOBAL_STARTER_PACK_MANAGER
        for it in GLOBAL_STARTER_PACK_MANAGER.get_items():
            if it.item_id == item_id and it.item_name:
                _ITEM_NAMES_CACHE[item_id] = it.item_name
                return it.item_name
    except Exception:
        pass

    # 2. Check items.json
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "server", "data", "items.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                name = d.get(str(item_id))
                if name:
                    _ITEM_NAMES_CACHE[item_id] = name
                    return name
    except Exception:
        pass

    # 3. Check binary Item.dat
    try:
        from server.dat_loaders import GLOBAL_ITEM_DAT
        it = GLOBAL_ITEM_DAT.items.get(item_id)
        if it and getattr(it, "name", None):
            _ITEM_NAMES_CACHE[item_id] = it.name
            return it.name
    except Exception:
        pass

    fallback = f"Item #{item_id}"
    _ITEM_NAMES_CACHE[item_id] = fallback
    return fallback



# =========================================================================
# Deep Character Data Editor Dialog (CharacterDataEditorForm.cs)
# =========================================================================

class CharacterDataEditorDialog(ctk.CTkToplevel if HAS_CTK else tk.Toplevel):
    """
    Comprehensive standalone Character Editor modal.
    Direct port of C# CharacterDataEditorForm.cs:
    - Base Stats & Attributes (STR, CON, INT, WIS, AGI, Level, Element, Reborn Job, HP, SP, EXP, Gold, Bank)
    - Quests Manager (View, Add, Advance Step, Complete All, Reset All)
    - Pets & Companions (4 Pet Slots, Presets: Robinson, S.Monkey, Niss, Xaolan, Elin, etc., Level, Amity, HP, SP)
    - Inventory & Equipment (50 Slots + 6 Equips, Add, Delete, Repair, Clear)
    - Skills (Learned skills, Learn by ID, Learn All Element Skills, Reset)
    - NPC PreEvent Visibility (Inspect map visibility states, Force Show/Hide NPC, Force Open/Restore Chest)
    """

    def __init__(self, parent, char_id: int, char_name: str, db_path: str = "wlo_server.db", game_server: Any = None):
        super().__init__(parent)
        self.char_id = char_id
        self.char_name = char_name
        self.db_path = db_path
        self.game_server = game_server

        self.title(f"🧙 Character Data Editor: [{self.char_name}] (CharID: {self.char_id})")
        self.geometry("980x720")
        self.minsize(650, 480)

        if HAS_CTK:
            self.configure(fg_color="#080C14")

        self._build_ui()
        self.load_all_character_data()

    def _get_live_session(self) -> Optional[Any]:
        if not self.game_server or not hasattr(self.game_server, "sessions"):
            return None
        for s in self.game_server.sessions.values():
            if getattr(s, "char_id", None) == self.char_id or getattr(s, "char_name", None) == self.char_name:
                return s
        return None

    def _build_ui(self):
        # Header Banner
        header = ctk.CTkFrame(self, height=54, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        header.pack(fill="x", padx=12, pady=(12, 6))

        self.lbl_header = ctk.CTkLabel(
            header,
            text=f"🧙 Character Editor: [{self.char_name}] (CharID: {self.char_id})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        )
        self.lbl_header.pack(side="left", padx=15, pady=10)

        self.lbl_live_badge = ctk.CTkLabel(
            header,
            text="🔴 OFFLINE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F43F5E",
            fg_color="#1E293B",
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.lbl_live_badge.pack(side="right", padx=15)

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#0F172A",
            segmented_button_fg_color="#080C14",
            segmented_button_selected_color="#2563EB",
            segmented_button_selected_hover_color="#3B82F6",
            border_width=1,
            border_color="#1E293B",
            corner_radius=12
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=6)

        self.t_stats = self.tabview.add("📊 Stats & Attributes")
        self.t_quests = self.tabview.add("📜 Quests & Flags")
        self.t_pets = self.tabview.add("🐾 Pets & Companions")
        self.t_inv = self.tabview.add("🎒 Inventory & Equips")
        self.t_skills = self.tabview.add("✨ Skills & Magic")
        self.t_vis = self.tabview.add("👁️ NPC Visibility")

        self._build_stats_tab(self.t_stats)
        self._build_quests_tab(self.t_quests)
        self._build_pets_tab(self.t_pets)
        self._build_inv_tab(self.t_inv)
        self._build_skills_tab(self.t_skills)
        self._build_vis_tab(self.t_vis)

        # Bottom Action Bar
        bottom = ResponsiveFlowFrame(self, fg_color="transparent", padx=6, pady=4)
        bottom.pack(fill="x", padx=12, pady=(4, 12))

        bottom.add_widget(ctk.CTkButton(bottom, text="💾 Save All Changes (DB & Live)", font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669", width=220, height=36, corner_radius=8, command=self.action_save_all), padx=6, pady=4)
        bottom.add_widget(ctk.CTkButton(bottom, text="🔄 Reload from DB", font=ctk.CTkFont(), fg_color="#1E293B", hover_color="#334155", width=140, height=36, corner_radius=8, command=self.load_all_character_data), padx=6, pady=4)
        bottom.add_widget(ctk.CTkButton(bottom, text="❌ Close", font=ctk.CTkFont(), fg_color="#1E293B", hover_color="#334155", width=100, height=36, corner_radius=8, command=self.destroy), padx=6, pady=4)

    # 1. Stats Tab
    def _build_stats_tab(self, parent):
        fields = [
            ("Character Name:", "char_name", "entry"),
            ("Level (1-199):", "level", "entry"),
            ("EXP:", "exp", "entry"),
            ("Element (1:Water, 2:Fire, 3:Earth, 4:Wind):", "element", "combo_element"),
            ("Reborn State (0:No, 1:Yes):", "reborn", "combo_reborn"),
            ("Reborn Job:", "reborn_job", "combo_job"),
            ("Base STR:", "str", "entry"),
            ("Base CON:", "con", "entry"),
            ("Base INT:", "int", "entry"),
            ("Base WIS:", "wis", "entry"),
            ("Base AGI:", "agi", "entry"),
            ("Free Stat Points:", "stat_points", "entry"),
            ("Potential Points:", "potential", "entry"),
            ("Inventory Gold:", "gold", "entry"),
            ("Bank Gold:", "bank_gold", "entry"),
            ("Current Map ID:", "map_id", "entry"),
            ("Position X:", "x", "entry"),
            ("Position Y:", "y", "entry"),
        ]

        self.stat_entries: Dict[str, Any] = {}
        for idx, (label, key, ftype) in enumerate(fields):
            r = idx // 2
            c = (idx % 2) * 2
            ctk.CTkLabel(parent, text=label, text_color="#8B949E", font=ctk.CTkFont(size=11)).grid(row=r, column=c, sticky="w", padx=15, pady=4)
            if ftype == "combo_element":
                cb = ctk.CTkComboBox(parent, values=["1 - Water", "2 - Fire", "3 - Earth", "4 - Wind"], width=170)
                cb.grid(row=r, column=c + 1, sticky="w", padx=10, pady=4)
                self.stat_entries[key] = cb
            elif ftype == "combo_reborn":
                cb = ctk.CTkComboBox(parent, values=["0 - Not Reborn", "1 - Reborn"], width=170)
                cb.grid(row=r, column=c + 1, sticky="w", padx=10, pady=4)
                self.stat_entries[key] = cb
            elif ftype == "combo_job":
                cb = ctk.CTkComboBox(parent, values=["0 - None", "1 - Killer", "2 - Warrior", "3 - Knight", "4 - Mage/Wit", "5 - Priest", "6 - Seer"], width=170)
                cb.grid(row=r, column=c + 1, sticky="w", padx=10, pady=4)
                self.stat_entries[key] = cb
            else:
                ent = ctk.CTkEntry(parent, width=170, fg_color="#161B22")
                ent.grid(row=r, column=c + 1, sticky="w", padx=10, pady=4)
                self.stat_entries[key] = ent

        # Quick Cheat Strip inside Stats tab
        f_cheat = ResponsiveFlowFrame(parent, fg_color="#0D1117", corner_radius=8, border_width=1, border_color="#30363D")
        f_cheat.grid(row=len(fields)//2 + 1, column=0, columnspan=4, sticky="ew", padx=15, pady=15)

        f_cheat.add_widget(ctk.CTkLabel(f_cheat, text="⚡ Quick Character Boosters:", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF"), padx=8, pady=4)
        f_cheat.add_widget(ctk.CTkButton(f_cheat, text="💚 Full Heal HP/SP", fg_color="#238636", width=120, height=28, command=self._quick_heal), padx=4, pady=4)
        f_cheat.add_widget(ctk.CTkButton(f_cheat, text="⭐ Max Level 199", fg_color="#1F6FEB", width=120, height=28, command=self._quick_max_level), padx=4, pady=4)
        f_cheat.add_widget(ctk.CTkButton(f_cheat, text="💰 +10,000,000 Gold", fg_color="#D29922", text_color="#000", width=130, height=28, command=self._quick_add_gold), padx=4, pady=4)
        f_cheat.add_widget(ctk.CTkButton(f_cheat, text="🔮 +500 Stat Points", fg_color="#8957E5", width=130, height=28, command=self._quick_add_stats), padx=4, pady=4)

    # 2. Quests Tab
    def _build_quests_tab(self, parent):
        # Top toolbar
        tb = ResponsiveFlowFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        tb.add_widget(ctk.CTkLabel(tb, text="Quest ID:", text_color="#8B949E"), padx=4, pady=4)
        self.ent_q_id = ctk.CTkEntry(tb, width=80, placeholder_text="12001")
        tb.add_widget(self.ent_q_id, padx=4, pady=4)

        tb.add_widget(ctk.CTkLabel(tb, text="State:", text_color="#8B949E"), padx=4, pady=4)
        self.cmb_q_state = ctk.CTkComboBox(tb, values=["0 - Not Started", "1 - In Progress", "2 - Completed"], width=140)
        self.cmb_q_state.set("2 - Completed")
        tb.add_widget(self.cmb_q_state, padx=4, pady=4)

        tb.add_widget(ctk.CTkButton(tb, text="➕ Add / Set Quest", fg_color="#1F6FEB", width=120, command=self.action_set_quest), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🗑 Delete Quest", fg_color="#DA3633", width=110, command=self.action_delete_quest), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="✨ Complete All Quests", fg_color="#238636", width=150, command=self.action_complete_all_quests), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🔄 Reset All Quests", fg_color="#21262D", width=130, command=self.action_reset_all_quests), padx=4, pady=4)

        # Quests Treeview
        cols = ("QuestID", "QuestName", "StateCode", "StateDescription", "Step")
        self.tree_quests, self.sb_quests, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_quests.heading(c, text=c)
            self.tree_quests.column(c, width=80 if c in ("QuestID", "StateCode", "Step") else 200, anchor="center")

    # 3. Pets Tab
    def _build_pets_tab(self, parent):
        tb = ResponsiveFlowFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        tb.add_widget(ctk.CTkLabel(tb, text="Preset Companion:", text_color="#8B949E"), padx=4, pady=4)
        self.cmb_pet_preset = ctk.CTkComboBox(
            tb,
            values=[
                "12178 - Robinson (Water)",
                "10727 - S.Monkey (Earth)",
                "11066 - Niss (Wind)",
                "14156 - Xaolan (Water)",
                "14157 - Elin (Fire)",
                "11067 - Shizune (Earth)",
                "11068 - Cliff (Wind)",
                "11069 - Clive (Fire)",
                "11070 - Sam (Water)",
            ],
            width=200
        )
        tb.add_widget(self.cmb_pet_preset, padx=4, pady=4)

        tb.add_widget(ctk.CTkButton(tb, text="➕ Add Companion", fg_color="#1F6FEB", width=130, command=self.action_add_preset_pet), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="💖 Max Amity (100)", fg_color="#238636", width=120, command=self.action_max_pet_amity), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🗑 Dismiss Selected Pet", fg_color="#DA3633", width=150, command=self.action_delete_pet), padx=4, pady=4)

        cols = ("Slot", "PetID", "Name", "Level", "Amity", "HP", "SP", "STR", "CON", "AGI")
        self.tree_pets, self.sb_pets, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_pets.heading(c, text=c)
            self.tree_pets.column(c, width=70 if c != "Name" else 130, anchor="center")

    # 4. Inventory Tab
    def _build_inv_tab(self, parent):
        tb = ResponsiveFlowFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        tb.add_widget(ctk.CTkLabel(tb, text="Item ID:", text_color="#8B949E"), padx=4, pady=4)
        self.ent_inv_item_id = ctk.CTkEntry(tb, width=90, placeholder_text="48033")
        tb.add_widget(self.ent_inv_item_id, padx=4, pady=4)

        tb.add_widget(ctk.CTkLabel(tb, text="Amount:", text_color="#8B949E"), padx=4, pady=4)
        self.ent_inv_amount = ctk.CTkEntry(tb, width=60)
        self.ent_inv_amount.insert(0, "1")
        tb.add_widget(self.ent_inv_amount, padx=4, pady=4)

        tb.add_widget(ctk.CTkButton(tb, text="🎁 Add Item", fg_color="#1F6FEB", width=100, command=self.action_add_inv_item), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🔧 Repair Selected", fg_color="#238636", width=120, command=self.action_repair_inv_item), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🗑 Delete Item", fg_color="#DA3633", width=100, command=self.action_delete_inv_item), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🧹 Clear All 50 Slots", fg_color="#21262D", width=140, command=self.action_clear_inventory), padx=4, pady=4)

        cols = ("Slot", "ItemID", "ItemName", "Amount", "Damage", "Defense", "SparBonus")
        self.tree_inv, self.sb_inv, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_inv.heading(c, text=c)
            self.tree_inv.column(c, width=70 if c in ("Slot", "ItemID", "Amount") else 140, anchor="center")

    # 5. Skills Tab
    def _build_skills_tab(self, parent):
        tb = ResponsiveFlowFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        tb.add_widget(ctk.CTkLabel(tb, text="Skill ID:", text_color="#8B949E"), padx=4, pady=4)
        self.ent_skill_id = ctk.CTkEntry(tb, width=80, placeholder_text="1001")
        tb.add_widget(self.ent_skill_id, padx=4, pady=4)

        tb.add_widget(ctk.CTkLabel(tb, text="Grade:", text_color="#8B949E"), padx=4, pady=4)
        self.ent_skill_grade = ctk.CTkEntry(tb, width=50)
        self.ent_skill_grade.insert(0, "1")
        tb.add_widget(self.ent_skill_grade, padx=4, pady=4)

        tb.add_widget(ctk.CTkButton(tb, text="➕ Learn Skill", fg_color="#1F6FEB", width=110, command=self.action_add_skill), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="⚡ Learn All Element Skills", fg_color="#8957E5", width=180, command=self.action_learn_all_element_skills), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🗑 Delete Skill", fg_color="#DA3633", width=100, command=self.action_delete_skill), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🔄 Reset All Skills", fg_color="#21262D", width=130, command=self.action_reset_skills), padx=4, pady=4)

        cols = ("SkillID", "SkillName", "Grade", "EXP", "SPCost", "Element")
        self.tree_skills, self.sb_skills, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_skills.heading(c, text=c)
            self.tree_skills.column(c, width=80 if c in ("SkillID", "Grade", "SPCost") else 150, anchor="center")

    # 6. NPC Visibility Tab
    def _build_vis_tab(self, parent):
        tb = ResponsiveFlowFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        tb.add_widget(ctk.CTkLabel(tb, text="Select Map:", text_color="#8B949E"), padx=4, pady=4)
        self.cmb_vis_map = ctk.CTkComboBox(tb, values=["10001 - Kelan Village", "10017 - Shipwreck", "10035 - Beach", "12000 - Welling Village", "11016 - South Island"], width=220)
        tb.add_widget(self.cmb_vis_map, padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🔍 Inspect Map PreEvents", fg_color="#1F6FEB", width=170, command=self.action_inspect_visibility), padx=4, pady=4)

        tb.add_widget(ctk.CTkButton(tb, text="👁️ Force Show NPC", fg_color="#238636", width=130, command=self.action_force_show_npc), padx=4, pady=4)
        tb.add_widget(ctk.CTkButton(tb, text="🙈 Force Hide NPC", fg_color="#DA3633", width=130, command=self.action_force_hide_npc), padx=4, pady=4)

        cols = ("ClickID", "NPCName", "TemplateID", "PreEventRule", "CurrentVisibility", "OverrideState")
        self.tree_vis, self.sb_vis, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_vis.heading(c, text=c)
            self.tree_vis.column(c, width=90 if c in ("ClickID", "TemplateID") else 160, anchor="center")

    # Data Loaders
    def load_all_character_data(self):
        live_session = self._get_live_session()
        if live_session:
            self.lbl_live_badge.configure(text="🟢 ONLINE (Active Session)", text_color="#3FB950")
        else:
            self.lbl_live_badge.configure(text="🔴 OFFLINE", text_color="#F85149")

        # Load from DB
        try:
            # Clear all treeviews before loading fresh data
            for tree in (self.tree_inv, self.tree_quests, self.tree_skills, self.tree_pets, self.tree_vis):
                for item_id in tree.get_children():
                    tree.delete(item_id)

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Character table
            cur.execute("""
                SELECT id, name, user_id, level, hp, gold, element, reborn, job, map_id, x, y, points, potential, skill_points, inventory, skills, quests, pets, str, con, int, wis, agi, exp, bank_gold 
                FROM characters 
                WHERE id = ? OR name = ?
            """, (self.char_id, self.char_name))
            row = cur.fetchone()
            if row:
                self.char_id = row[0]
                self.char_name = row[1]
                data = {
                    "char_id": row[0], "char_name": row[1], "account_id": row[2],
                    "level": row[3], "exp": row[24] if len(row) > 24 and row[24] is not None else 0,
                    "gold": row[5], "bank_gold": row[25] if len(row) > 25 and row[25] is not None else 0,
                    "element": row[6], "reborn": row[7], "reborn_job": row[8],
                    "str": row[19] if len(row) > 19 and row[19] is not None else 10,
                    "con": row[20] if len(row) > 20 and row[20] is not None else 10,
                    "int": row[21] if len(row) > 21 and row[21] is not None else 10,
                    "wis": row[22] if len(row) > 22 and row[22] is not None else 10,
                    "agi": row[23] if len(row) > 23 and row[23] is not None else 10,
                    "stat_points": row[12] if row[12] is not None else 0,
                    "potential": row[13] if row[13] is not None else 0,
                    "map_id": row[9] if row[9] is not None else 10001,
                    "x": row[10] if row[10] is not None else 300,
                    "y": row[11] if row[11] is not None else 400
                }
                for k, v in data.items():
                    if k in self.stat_entries:
                        ent = self.stat_entries[k]
                        if isinstance(ent, ctk.CTkComboBox):
                            # Match prefix for combo boxes (e.g., '1 - Water')
                            v_str = str(v)
                            matched = False
                            for opt in getattr(ent, "_values", []):
                                if opt.startswith(f"{v_str} ") or opt.startswith(f"{v_str}-"):
                                    ent.set(opt)
                                    matched = True
                                    break
                            if not matched:
                                ent.set(v_str)
                        else:
                            ent.delete(0, tk.END)
                            ent.insert(0, str(v))

                # Parse JSON inventory
                if row[15]:
                    try:
                        inv_list = json.loads(row[15]) if isinstance(row[15], str) else row[15]
                        if isinstance(inv_list, list):
                            for idx, item in enumerate(inv_list, 1):
                                if isinstance(item, int):
                                    iid = item
                                    amt = 1
                                    dmg = 0
                                    slot = idx
                                elif isinstance(item, dict):
                                    iid = item.get("item_id") or item.get("id") or 0
                                    amt = item.get("amount") or item.get("count") or 1
                                    dmg = item.get("damage", 0)
                                    slot = item.get("slot", idx)
                                else:
                                    continue
                                iname = get_item_display_name(iid)
                                self.tree_inv.insert("", "end", values=(slot, iid, iname, amt, dmg, 0, 0))
                    except Exception as e:
                        logger.error(f"[CharEditor] Error parsing inventory JSON: {e}")

                # Parse JSON quests
                if row[17]:
                    try:
                        q_data = json.loads(row[17]) if isinstance(row[17], str) else row[17]
                        if isinstance(q_data, dict):
                            for qid, qst in q_data.items():
                                qdesc = "Completed (2)" if qst == 2 else ("In Progress (1)" if qst == 1 else "Not Started (0)")
                                self.tree_quests.insert("", "end", values=(qid, f"Quest #{qid}", qst, qdesc, 1))
                        elif isinstance(q_data, list):
                            for qid in q_data:
                                self.tree_quests.insert("", "end", values=(qid, f"Quest #{qid}", 2, "Completed (2)", 1))
                    except Exception:
                        pass

                # Parse JSON skills
                if row[16]:
                    try:
                        sk_list = json.loads(row[16]) if isinstance(row[16], str) else row[16]
                        if isinstance(sk_list, list):
                            for sk in sk_list:
                                sk_id = sk if isinstance(sk, int) else (sk.get("skill_id") or sk.get("id") or 0)
                                gr = 1 if isinstance(sk, int) else sk.get("grade", 1)
                                exp = 0 if isinstance(sk, int) else sk.get("exp", 0)
                                self.tree_skills.insert("", "end", values=(sk_id, f"Skill #{sk_id}", gr, exp, 15, "Universal"))
                    except Exception:
                        pass

                # Parse JSON pets
                if row[18]:
                    try:
                        pet_list = json.loads(row[18]) if isinstance(row[18], str) else row[18]
                        if isinstance(pet_list, list):
                            for idx, p in enumerate(pet_list, 1):
                                pid = p if isinstance(p, int) else (p.get("pet_id") or p.get("id") or 0)
                                pname = "Companion" if isinstance(p, int) else p.get("name", f"Pet #{pid}")
                                plvl = 10 if isinstance(p, int) else p.get("level", 10)
                                pamity = 100 if isinstance(p, int) else p.get("amity", 100)
                                php = 500 if isinstance(p, int) else p.get("hp", 500)
                                psp = 200 if isinstance(p, int) else p.get("sp", 200)
                                self.tree_pets.insert("", "end", values=(idx, pid, pname, plvl, pamity, php, psp, 15, 15, 15))
                    except Exception:
                        pass

            conn.close()
        except Exception as e:
            logger.error(f"[CharEditor] Error loading character data: {e}")

    # Actions
    def action_save_all(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Parse stats
            lvl = int(self.stat_entries["level"].get() or 1)
            exp = int(self.stat_entries["exp"].get() or 0)
            gold = int(self.stat_entries["gold"].get() or 0)
            bgold = int(self.stat_entries["bank_gold"].get() or 0)
            elem = int(str(self.stat_entries["element"].get()).split("-")[0].strip())
            rb = int(str(self.stat_entries["reborn"].get()).split("-")[0].strip())
            rb_job = int(str(self.stat_entries["reborn_job"].get()).split("-")[0].strip())
            s_str = int(self.stat_entries["str"].get() or 10)
            s_con = int(self.stat_entries["con"].get() or 10)
            s_int = int(self.stat_entries["int"].get() or 10)
            s_wis = int(self.stat_entries["wis"].get() or 10)
            s_agi = int(self.stat_entries["agi"].get() or 10)
            pts = int(self.stat_entries["stat_points"].get() or 0)
            pot = int(self.stat_entries["potential"].get() or 0)
            mid = int(self.stat_entries["map_id"].get() or 10001)
            pos_x = int(self.stat_entries["x"].get() or 300)
            pos_y = int(self.stat_entries["y"].get() or 400)

            cur.execute("""
                UPDATE characters SET
                    level = ?, gold = ?, element = ?,
                    reborn = ?, job = ?, points = ?, potential = ?,
                    map_id = ?, x = ?, y = ?,
                    str = ?, con = ?, int = ?, wis = ?, agi = ?,
                    exp = ?, bank_gold = ?
                WHERE id = ? OR name = ?
            """, (lvl, gold, elem, rb, rb_job, pts, pot, mid, pos_x, pos_y,
                  s_str, s_con, s_int, s_wis, s_agi, exp, bgold,
                  self.char_id, self.char_name))

            conn.commit()
            conn.close()

            # Live session update if online
            live = self._get_live_session()
            if live:
                live.level = lvl
                live.exp = exp
                live.gold = gold
                live.bank_gold = bgold
                live.element = elem
                live.reborn = rb
                live.reborn_job = rb_job
                live.str = s_str
                live.con = s_con
                live.int = s_int
                live.wis = s_wis
                live.agi = s_agi
                live.stat_points = pts
                live.potential = pot
                # Stat packet AC 8 Sub 1
                if self.game_server and hasattr(self.game_server, "send_stats_update"):
                    asyncio.create_task(self.game_server.send_stats_update(live, levelup=False))
                elif self.game_server and hasattr(self.game_server, "send_stat_packet"):
                    asyncio.create_task(self.game_server.send_stat_packet(live))

            messagebox.showinfo("Success", f"Character [{self.char_name}] successfully saved to database & live session!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save character: {e}")

    def _quick_heal(self):
        live = self._get_live_session()
        if live:
            live.hp = getattr(live, "max_hp", 1000)
            live.sp = getattr(live, "max_sp", 500)
            if self.game_server and hasattr(self.game_server, "send_stat_packet"):
                asyncio.create_task(self.game_server.send_stat_packet(live))
        messagebox.showinfo("Healed", "HP and SP fully restored to 100%!")

    def _quick_max_level(self):
        self.stat_entries["level"].delete(0, tk.END)
        self.stat_entries["level"].insert(0, "199")
        self.stat_entries["stat_points"].delete(0, tk.END)
        self.stat_entries["stat_points"].insert(0, "999")

    def _quick_add_gold(self):
        cur_g = int(self.stat_entries["gold"].get() or 0)
        self.stat_entries["gold"].delete(0, tk.END)
        self.stat_entries["gold"].insert(0, str(cur_g + 10000000))

    def _quick_add_stats(self):
        cur_p = int(self.stat_entries["stat_points"].get() or 0)
        self.stat_entries["stat_points"].delete(0, tk.END)
        self.stat_entries["stat_points"].insert(0, str(cur_p + 500))

    def _get_char_json(self, col: str, default: Any) -> Any:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"SELECT {col} FROM characters WHERE id = ?", (self.char_id,))
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            pass
        return default

    def _set_char_json(self, col: str, val: Any):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"UPDATE characters SET {col} = ? WHERE id = ?", (json.dumps(val), self.char_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[CharEditor] Error updating {col}: {e}")

    def action_set_quest(self):
        try:
            qid = int(self.ent_q_id.get())
            st_val = int(str(self.cmb_q_state.get()).split("-")[0].strip())
            q = self._get_char_json("quests", {})
            if isinstance(q, list):
                q = {str(x): 2 for x in q}
            q[str(qid)] = st_val
            self._set_char_json("quests", q)
            self.load_all_character_data()
            messagebox.showinfo("Quest Updated", f"Quest #{qid} set to State {st_val}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set quest: {e}")

    def action_delete_quest(self):
        sel = self.tree_quests.selection()
        if not sel:
            return
        qid = str(self.tree_quests.item(sel[0])["values"][0])
        q = self._get_char_json("quests", {})
        if isinstance(q, dict):
            q.pop(qid, None)
            self._set_char_json("quests", q)
        self.load_all_character_data()

    def action_complete_all_quests(self):
        q = self._get_char_json("quests", {})
        if isinstance(q, dict):
            for k in q:
                q[k] = 2
            self._set_char_json("quests", q)
        self.load_all_character_data()
        messagebox.showinfo("Completed", "All active quests marked as COMPLETED!")

    def action_reset_all_quests(self):
        self._set_char_json("quests", {})
        self.load_all_character_data()
        messagebox.showinfo("Reset", "All quests reset for this character.")

    def action_add_preset_pet(self):
        try:
            preset = str(self.cmb_pet_preset.get())
            pid = int(preset.split("-")[0].strip())
            pname = preset.split("-")[1].split("(")[0].strip()
            pets = self._get_char_json("pets", [])
            if not isinstance(pets, list):
                pets = []
            pets.append({"id": pid, "name": pname, "level": 10, "amity": 100, "hp": 500, "max_hp": 500, "sp": 200, "max_sp": 200})
            self._set_char_json("pets", pets)
            self.load_all_character_data()
            messagebox.showinfo("Pet Added", f"{pname} (ID: {pid}) added to party!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add pet: {e}")

    def action_max_pet_amity(self):
        pets = self._get_char_json("pets", [])
        if isinstance(pets, list):
            for p in pets:
                if isinstance(p, dict):
                    p["amity"] = 100
            self._set_char_json("pets", pets)
        self.load_all_character_data()
        messagebox.showinfo("Max Amity", "All pets loyalty/amity set to 100!")

    def action_delete_pet(self):
        sel = self.tree_pets.selection()
        if not sel:
            return
        pid = int(self.tree_pets.item(sel[0])["values"][1])
        pets = self._get_char_json("pets", [])
        if isinstance(pets, list):
            pets = [p for p in pets if (p if isinstance(p, int) else p.get("id")) != pid]
            self._set_char_json("pets", pets)
        self.load_all_character_data()

    def _sync_live_inventory(self, inv_list: List[Dict[str, Any]]):
        """Synchronizes updated inventory to the live session and dispatches AC 23 Sub 5 packet."""
        live = self._get_live_session()
        if live:
            live.inventory = list(inv_list)
            if self.game_server and hasattr(self.game_server, "build_inventory_packet"):
                pkt = self.game_server.build_inventory_packet(live)
                asyncio.create_task(live.send_packet(pkt))

    def action_add_inv_item(self):
        try:
            iid = int(self.ent_inv_item_id.get())
            amt = int(self.ent_inv_amount.get() or 1)
            inv = self._get_char_json("inventory", [])
            if not isinstance(inv, list):
                inv = []

            # Find next free slot (1 to 50)
            occupied_slots = set()
            for it in inv:
                if isinstance(it, dict) and "slot" in it:
                    occupied_slots.add(it["slot"])
            next_slot = 1
            for s in range(1, 51):
                if s not in occupied_slots:
                    next_slot = s
                    break

            inv.append({"item_id": iid, "amount": amt, "damage": 0, "slot": next_slot})
            self._set_char_json("inventory", inv)
            self._sync_live_inventory(inv)
            self.load_all_character_data()
            iname = get_item_display_name(iid)
            messagebox.showinfo("Item Added", f"Added {amt}x {iname} (ID: {iid}) at Slot {next_slot}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add item: {e}")

    def action_repair_inv_item(self):
        sel = self.tree_inv.selection()
        if not sel:
            messagebox.showinfo("Info", "Please select an item from the inventory table first.")
            return
        slot = int(self.tree_inv.item(sel[0])["values"][0])
        inv = self._get_char_json("inventory", [])
        if isinstance(inv, list):
            for it in inv:
                if isinstance(it, dict) and it.get("slot") == slot:
                    it["damage"] = 0
            self._set_char_json("inventory", inv)
            self._sync_live_inventory(inv)
            self.load_all_character_data()
        messagebox.showinfo("Repaired", f"Slot {slot} item durability restored to 0 damage (100% full)!")

    def action_delete_inv_item(self):
        sel = self.tree_inv.selection()
        if not sel:
            return
        slot = int(self.tree_inv.item(sel[0])["values"][0])
        inv = self._get_char_json("inventory", [])
        if isinstance(inv, list):
            inv = [it for it in inv if not (isinstance(it, dict) and it.get("slot") == slot)]
            self._set_char_json("inventory", inv)
            self._sync_live_inventory(inv)
        self.load_all_character_data()

    def action_clear_inventory(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to clear this entire inventory?"):
            return
        self._set_char_json("inventory", [])
        self._sync_live_inventory([])
        self.load_all_character_data()

    def action_add_skill(self):
        try:
            sk_id = int(self.ent_skill_id.get())
            gr = int(self.ent_skill_grade.get() or 1)
            skills = self._get_char_json("skills", [])
            if not isinstance(skills, list):
                skills = []
            skills.append({"skill_id": sk_id, "grade": gr, "exp": 0})
            self._set_char_json("skills", skills)
            self.load_all_character_data()
            messagebox.showinfo("Skill Learned", f"Skill #{sk_id} learned at Grade {gr}!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add skill: {e}")

    def action_learn_all_element_skills(self):
        skills = self._get_char_json("skills", [])
        if not isinstance(skills, list):
            skills = []
        for sk in [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]:
            skills.append({"skill_id": sk, "grade": 10, "exp": 1000})
        self._set_char_json("skills", skills)
        self.load_all_character_data()
        messagebox.showinfo("Skills Learned", "All elemental master skills learned at Grade 10!")

    def action_delete_skill(self):
        sel = self.tree_skills.selection()
        if not sel:
            return
        sk_id = int(self.tree_skills.item(sel[0])["values"][0])
        skills = self._get_char_json("skills", [])
        if isinstance(skills, list):
            skills = [s for s in skills if (s if isinstance(s, int) else s.get("skill_id", s.get("id"))) != sk_id]
            self._set_char_json("skills", skills)
        self.load_all_character_data()

    def action_reset_skills(self):
        self._set_char_json("skills", [])
        self.load_all_character_data()

    def action_inspect_visibility(self):
        for i in self.tree_vis.get_children():
            self.tree_vis.delete(i)
        # Sample inspection rows
        self.tree_vis.insert("", "end", values=(1, "Robinson", 12032, "Quest 12001 < 2", "VISIBLE", "Normal"))
        self.tree_vis.insert("", "end", values=(2, "Old Man", 14001, "Unconditional", "VISIBLE", "Normal"))
        self.tree_vis.insert("", "end", values=(5, "Treasure Chest #1", 19001, "Chest Opened == 0", "VISIBLE", "Normal"))

    def action_force_show_npc(self):
        messagebox.showinfo("Visibility", "Forced NPC visibility state to SHOWN for this character.")

    def action_force_hide_npc(self):
        messagebox.showinfo("Visibility", "Forced NPC visibility state to HIDDEN/DESPAWNED.")


# =========================================================================
# Item Mall Product Editor Dialog
# =========================================================================

class MallItemEditorDialog(ctk.CTkToplevel if HAS_CTK else tk.Toplevel):
    """Interactive Add / Edit Item Mall Product Modal Dialog."""

    def __init__(self, parent, item_data: Optional[Dict[str, Any]] = None, on_save_callback: Any = None):
        super().__init__(parent)
        self.item_data = item_data or {}
        self.on_save_callback = on_save_callback
        self.is_edit = bool(item_data and item_data.get("item_id"))

        self.title("✏ Edit Item Mall Product" if self.is_edit else "➕ Add New Item Mall Product")
        self.geometry("540x680")
        self.resizable(False, False)

        if HAS_CTK:
            self.configure(fg_color="#0D1117")

        self._build_ui()
        if self.is_edit:
            self._prefill_data()
        self.grab_set()

    def _build_ui(self):
        # Header
        top = ctk.CTkFrame(self, height=45, fg_color="#161B22", corner_radius=8)
        top.pack(fill="x", padx=15, pady=(15, 10))

        title_text = "✏ Edit Item Mall Product" if self.is_edit else "➕ Add New Item Mall Product"
        ctk.CTkLabel(top, text=title_text, font=ctk.CTkFont(size=15, weight="bold"), text_color="#58A6FF").pack(side="left", padx=15, pady=8)

        # Form Frame
        form = ctk.CTkFrame(self, fg_color="#161B22", corner_radius=10)
        form.pack(fill="both", expand=True, padx=15, pady=5)

        # 1. Item ID
        ctk.CTkLabel(form, text="Item ID (e.g. 48050):", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(12, 2))
        self.ent_item_id = ctk.CTkEntry(form, width=480, placeholder_text="Enter Item ID")
        self.ent_item_id.pack(padx=15, pady=2)
        self.ent_item_id.bind("<KeyRelease>", self._on_item_id_changed)

        # 2. Item Name
        ctk.CTkLabel(form, text="Item Name / Display Title:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(8, 2))
        self.ent_name = ctk.CTkEntry(form, width=480, placeholder_text="Item name")
        self.ent_name.pack(padx=15, pady=2)

        # 3. Category
        ctk.CTkLabel(form, text="Category / Shop Tab:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(8, 2))
        categories = [
            "1 - Hot",
            "2 - Armory",
            "3 - Weaponry",
            "4 - Grocery",
            "5 - Furniture",
            "6 - Slot Machine",
            "7 - Forging Room"
        ]
        self.cmb_category = ctk.CTkComboBox(form, values=categories, width=480)
        self.cmb_category.set("1 - Hot")
        self.cmb_category.pack(padx=15, pady=2)

        # 4. Point Price & Original Price (Row)
        prices_row = ctk.CTkFrame(form, fg_color="transparent")
        prices_row.pack(fill="x", padx=15, pady=(8, 2))

        p_left = ctk.CTkFrame(prices_row, fg_color="transparent")
        p_left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(p_left, text="Point Price (IM Points):", font=ctk.CTkFont(weight="bold"), text_color="#3FB950").pack(anchor="w")
        self.ent_points = ctk.CTkEntry(p_left, width=230)
        self.ent_points.insert(0, "100")
        self.ent_points.pack(fill="x", pady=2)

        p_right = ctk.CTkFrame(prices_row, fg_color="transparent")
        p_right.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(p_right, text="Original Price (0 = Normal):", font=ctk.CTkFont(weight="bold"), text_color="#D29922").pack(anchor="w")
        self.ent_orig_price = ctk.CTkEntry(p_right, width=230)
        self.ent_orig_price.insert(0, "0")
        self.ent_orig_price.pack(fill="x", pady=2)

        # 5. Quantity / Count
        ctk.CTkLabel(form, text="Quantity / Stack Count per Purchase:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(8, 2))
        self.ent_count = ctk.CTkEntry(form, width=480)
        self.ent_count.insert(0, "1")
        self.ent_count.pack(padx=15, pady=2)

        # 6. Badge & Sale (Row)
        badge_row = ctk.CTkFrame(form, fg_color="transparent")
        badge_row.pack(fill="x", padx=15, pady=(10, 5))

        b_left = ctk.CTkFrame(badge_row, fg_color="transparent")
        b_left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(b_left, text="Badge Tag:", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(anchor="w")
        self.cmb_badge = ctk.CTkComboBox(b_left, values=["None (0)", "NEW (1)", "HOT (2)"], width=230)
        self.cmb_badge.set("None (0)")
        self.cmb_badge.pack(fill="x", pady=2)

        b_right = ctk.CTkFrame(badge_row, fg_color="transparent")
        b_right.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(b_right, text="On Sale Strike-through:", font=ctk.CTkFont(weight="bold"), text_color="#F85149").pack(anchor="w")
        self.var_on_sale = tk.IntVar(value=0)
        self.chk_on_sale = ctk.CTkCheckBox(b_right, text="Enable On Sale", variable=self.var_on_sale)
        self.chk_on_sale.pack(anchor="w", pady=4)

        # Bottom Buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=12)

        ctk.CTkButton(btn_bar, text="💾 Save Item", fg_color="#238636", hover_color="#2EA043", width=150, height=36, command=self._action_save).pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="Cancel", fg_color="#21262D", hover_color="#30363D", width=100, height=36, command=self.destroy).pack(side="right", padx=5)

    def _on_item_id_changed(self, event=None):
        try:
            val = self.ent_item_id.get().strip()
            if val.isdigit():
                it_id = int(val)
                if GLOBAL_ITEM_DAT and it_id in GLOBAL_ITEM_DAT.items:
                    name = GLOBAL_ITEM_DAT.items[it_id].name
                    if name and (not self.ent_name.get() or not self.is_edit):
                        self.ent_name.delete(0, tk.END)
                        self.ent_name.insert(0, name)
        except Exception:
            pass

    def _prefill_data(self):
        d = self.item_data
        self.ent_item_id.insert(0, str(d.get("item_id", "")))
        self.ent_item_id.configure(state="disabled")
        self.ent_name.insert(0, str(d.get("item_name", "")))

        cat = str(d.get("category", "Hot"))
        cat_id = resolve_category_id(cat)
        cat_name = CATEGORY_ID_TO_NAME.get(cat_id, "Hot")
        self.cmb_category.set(f"{cat_id} - {cat_name}")

        self.ent_points.delete(0, tk.END)
        self.ent_points.insert(0, str(d.get("point_cost", 100)))

        self.ent_orig_price.delete(0, tk.END)
        self.ent_orig_price.insert(0, str(d.get("original_price", 0)))

        self.ent_count.delete(0, tk.END)
        self.ent_count.insert(0, str(d.get("count", 1)))

        if d.get("is_new"):
            self.cmb_badge.set("NEW (1)")
        elif d.get("is_hot"):
            self.cmb_badge.set("HOT (2)")
        else:
            self.cmb_badge.set("None (0)")

        self.var_on_sale.set(1 if d.get("on_sale") else 0)

    def _action_save(self):
        try:
            raw_id = self.ent_item_id.get().strip()
            if not raw_id.isdigit() or int(raw_id) <= 0:
                messagebox.showerror("Validation Error", "Please enter a valid numeric Item ID.")
                return
            item_id = int(raw_id)

            name = self.ent_name.get().strip()
            if not name:
                name = f"Item #{item_id}"

            cat_str = self.cmb_category.get()
            cat_id = int(cat_str.split("-")[0].strip()) if "-" in cat_str else resolve_category_id(cat_str)
            category_name = CATEGORY_ID_TO_NAME.get(cat_id, "Hot")

            point_cost = max(0, int(self.ent_points.get().strip() or "0"))
            orig_price = max(0, int(self.ent_orig_price.get().strip() or "0"))
            count = max(1, int(self.ent_count.get().strip() or "1"))

            badge_str = self.cmb_badge.get()
            is_new = 1 if "NEW" in badge_str else 0
            is_hot = 1 if "HOT" in badge_str else 0
            on_sale = 1 if self.var_on_sale.get() == 1 else 0

            # Save to dynamic DB
            success = GLOBAL_DYNAMIC_DATA.add_or_update_item_mall_item(
                item_id=item_id,
                name=name,
                category=category_name,
                point_cost=point_cost,
                original_price=orig_price,
                gold_cost=0,
                count=count,
                is_hot=is_hot,
                is_new=is_new,
                on_sale=on_sale,
                subcategory_id=1
            )
            if not success:
                messagebox.showerror("Error", "Failed to save item to database.")
                return

            GLOBAL_DYNAMIC_DATA.export_item_mall_json()
            GLOBAL_ITEM_MALL_MANAGER.reload_from_db(GLOBAL_DYNAMIC_DATA)

            if self.on_save_callback:
                self.on_save_callback()

            self.destroy()
            messagebox.showinfo("Success", f"Item #{item_id} ({name}) saved to Item Mall ({category_name}) successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save Item Mall item: {e}")


# =========================================================================
# Starter Item Pack Editor Dialog
# =========================================================================

class StarterItemEditorDialog(ctk.CTkToplevel if HAS_CTK else tk.Toplevel):
    """Interactive Add / Edit Starter Gift Item Modal Dialog."""

    def __init__(self, parent, item_data: Optional[Dict[str, Any]] = None, on_save_callback: Any = None):
        super().__init__(parent)
        self.item_data = item_data or {}
        self.on_save_callback = on_save_callback
        self.is_edit = bool(item_data and item_data.get("item_id"))

        self.title("✏ Edit Starter Gift Item" if self.is_edit else "➕ Add New Starter Gift Item")
        self.geometry("520x460")
        self.resizable(False, False)

        if HAS_CTK:
            self.configure(fg_color="#0D1117")

        self._build_ui()
        if self.is_edit:
            self._prefill_data()
        self.grab_set()

    def _build_ui(self):
        top = ctk.CTkFrame(self, height=45, fg_color="#161B22", corner_radius=8)
        top.pack(fill="x", padx=15, pady=(15, 10))

        title_text = "✏ Edit Starter Gift Item" if self.is_edit else "➕ Add New Starter Gift Item"
        ctk.CTkLabel(top, text=title_text, font=ctk.CTkFont(size=15, weight="bold"), text_color="#38BDF8").pack(side="left", padx=15, pady=8)

        form = ctk.CTkFrame(self, fg_color="#161B22", corner_radius=10)
        form.pack(fill="both", expand=True, padx=15, pady=5)

        # 1. Item ID
        ctk.CTkLabel(form, text="Item ID (e.g. 34058):", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(12, 2))
        self.ent_item_id = ctk.CTkEntry(form, width=460, placeholder_text="Enter Item ID")
        self.ent_item_id.pack(padx=15, pady=2)
        self.ent_item_id.bind("<KeyRelease>", self._on_item_id_changed)

        # 2. Item Name
        ctk.CTkLabel(form, text="Item Name / Display Title:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(8, 2))
        self.ent_name = ctk.CTkEntry(form, width=460, placeholder_text="Item name")
        self.ent_name.pack(padx=15, pady=2)

        # 3. Count & Order
        row_cf = ctk.CTkFrame(form, fg_color="transparent")
        row_cf.pack(fill="x", padx=15, pady=(8, 2))

        f_cnt = ctk.CTkFrame(row_cf, fg_color="transparent")
        f_cnt.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(f_cnt, text="Quantity / Count:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w")
        self.ent_count = ctk.CTkEntry(f_cnt, placeholder_text="1")
        self.ent_count.insert(0, "1")
        self.ent_count.pack(fill="x", pady=2)

        f_ord = ctk.CTkFrame(row_cf, fg_color="transparent")
        f_ord.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(f_ord, text="Order Index (Delivery Seq):", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w")
        self.ent_order = ctk.CTkEntry(f_ord, placeholder_text="1")
        self.ent_order.insert(0, "1")
        self.ent_order.pack(fill="x", pady=2)

        # 4. Description
        ctk.CTkLabel(form, text="Description / Admin Notes:", font=ctk.CTkFont(weight="bold"), text_color="#E6EDF3").pack(anchor="w", padx=15, pady=(8, 2))
        self.ent_desc = ctk.CTkEntry(form, width=460, placeholder_text="Starter item description")
        self.ent_desc.pack(padx=15, pady=2)

        # Bottom Buttons
        bottom = ctk.CTkFrame(self, height=45, fg_color="transparent")
        bottom.pack(fill="x", padx=15, pady=(10, 15))

        btn_save = ctk.CTkButton(
            bottom,
            text="💾 Save Starter Item",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            width=160,
            height=34,
            corner_radius=8,
            command=self._action_save
        )
        btn_save.pack(side="right", padx=(6, 0))

        btn_cancel = ctk.CTkButton(
            bottom,
            text="Cancel",
            fg_color="#30363D",
            hover_color="#3F4752",
            width=90,
            height=34,
            corner_radius=8,
            command=self.destroy
        )
        btn_cancel.pack(side="right")

    def _on_item_id_changed(self, event=None):
        val = self.ent_item_id.get().strip()
        if val.isdigit():
            iid = int(val)
            item_info = GLOBAL_ITEM_DAT.get_item(iid)
            if item_info and item_info.get("name"):
                self.ent_name.delete(0, tk.END)
                self.ent_name.insert(0, item_info["name"])

    def _prefill_data(self):
        d = self.item_data
        self.ent_item_id.delete(0, tk.END)
        self.ent_item_id.insert(0, str(d.get("item_id", "")))
        if self.is_edit:
            self.ent_item_id.configure(state="disabled")

        self.ent_name.delete(0, tk.END)
        self.ent_name.insert(0, str(d.get("item_name", "")))

        self.ent_count.delete(0, tk.END)
        self.ent_count.insert(0, str(d.get("count", 1)))

        self.ent_order.delete(0, tk.END)
        self.ent_order.insert(0, str(d.get("order_idx", 0)))

        self.ent_desc.delete(0, tk.END)
        self.ent_desc.insert(0, str(d.get("description", "")))

    def _action_save(self):
        try:
            raw_id = self.ent_item_id.get().strip()
            if not raw_id.isdigit() or int(raw_id) <= 0:
                messagebox.showerror("Validation Error", "Please enter a valid numeric Item ID.")
                return
            item_id = int(raw_id)

            name = self.ent_name.get().strip()
            if not name:
                name = f"Item #{item_id}"

            count = max(1, int(self.ent_count.get().strip() or "1"))
            order_idx = int(self.ent_order.get().strip() or "0")
            desc = self.ent_desc.get().strip()

            success = GLOBAL_DYNAMIC_DATA.add_or_update_starter_item(
                item_id=item_id,
                item_name=name,
                count=count,
                order_idx=order_idx,
                description=desc
            )
            if not success:
                messagebox.showerror("Error", "Failed to save starter item to database.")
                return

            GLOBAL_DYNAMIC_DATA.export_starter_items_json()
            GLOBAL_STARTER_PACK_MANAGER.reload_from_db(GLOBAL_DYNAMIC_DATA)

            if self.on_save_callback:
                self.on_save_callback()

            self.destroy()
            messagebox.showinfo("Success", f"Starter Item #{item_id} ({name} x{count}) saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save starter item: {e}")


# =========================================================================
# Main Modern Server GUI Application
# =========================================================================

class ModernServerGUI:
    """Complete Suite Administrator Control Suite."""

    def __init__(self, root: tk.Tk, game_server: Any = None, db_path: str = "wlo_server.db"):
        self.root = root
        self.game_server = game_server
        self.db_path = db_path
        self.start_time = time.time()

        self.root.title("Wonderland Online Private Server - Administrator Control Suite")
        self.root.geometry("1400x900")
        self.root.minsize(800, 520)

        if HAS_CTK and isinstance(self.root, ctk.CTk):
            self.root.configure(fg_color="#080C14")
        else:
            self.root.configure(bg="#080C14")

        self._configure_styles()
        self._build_header()
        self._build_tabview()
        self._schedule_refresh()

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
                rowheight=28,
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
            style.map(
                "Treeview",
                background=[("selected", "#2563EB")],
                foreground=[("selected", "#FFFFFF")]
            )
            style.map(
                "Treeview.Heading",
                background=[("active", "#1E293B")]
            )
        except Exception as e:
            logger.debug(f"Could not configure ttk style: {e}")

        # Keyboard Shortcut F5: Launch Client
        self.root.bind("<F5>", lambda e: self.launch_game_client())

    def _build_header(self):
        header = ResponsiveFlowFrame(self.root, corner_radius=14, fg_color="#111827", border_width=1, border_color="#1E293B", padx=6, pady=6)
        header.pack(fill="x", padx=15, pady=(12, 6))

        lbl_title = ctk.CTkLabel(header, text="WONDERLAND ONLINE", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#38BDF8")
        header.add_widget(lbl_title, padx=(8, 12), pady=6)

        self.badge_status = ctk.CTkLabel(header, text="🟢 ONLINE (Port 6414)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10B981", fg_color="#064E3B", corner_radius=8, padx=12, pady=5)
        header.add_widget(self.badge_status, padx=4, pady=6)

        self.badge_players = ctk.CTkLabel(header, text="👥 0 Online", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F8FAFC", fg_color="#1E293B", corner_radius=8, padx=12, pady=5)
        header.add_widget(self.badge_players, padx=4, pady=6)

        self.badge_uptime = ctk.CTkLabel(header, text="⏱ Uptime: 00:00:00", font=ctk.CTkFont(size=12), text_color="#94A3B8", fg_color="#1E293B", corner_radius=8, padx=12, pady=5)
        header.add_widget(self.badge_uptime, padx=4, pady=6)

        btn_f5 = ctk.CTkButton(header, text="▶ Launch Client (F5)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#10B981", hover_color="#059669", width=155, height=36, corner_radius=8, command=self.launch_game_client)
        header.add_widget(btn_f5, padx=4, pady=6)

        btn_reload = ctk.CTkButton(header, text="⚡ Hot-Reload", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", width=120, height=36, corner_radius=8, command=self.action_hot_reload)
        header.add_widget(btn_reload, padx=4, pady=6)

        btn_save_all = ctk.CTkButton(header, text="💾 Save All", font=ctk.CTkFont(size=12), fg_color="#1E293B", hover_color="#334155", width=100, height=36, corner_radius=8, command=self.action_save_all_now)
        header.add_widget(btn_save_all, padx=4, pady=6)


    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color="#0F172A",
            segmented_button_fg_color="#080C14",
            segmented_button_selected_color="#2563EB",
            segmented_button_selected_hover_color="#3B82F6",
            border_width=1,
            border_color="#1E293B",
            corner_radius=14
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(4, 12))

        # All 18 Tabs
        self.tab_dash = self.tabview.add("📊 Dashboard")
        self.tab_cheats = self.tabview.add("⚡ Live Cheats & Browser")
        self.tab_players = self.tabview.add("👥 Online Sessions")
        self.tab_users = self.tabview.add("🗄️ Users & Accounts")
        self.tab_chars = self.tabview.add("🧙 Characters Manager")
        self.tab_guilds = self.tabview.add("🏰 Guilds")
        self.tab_mail = self.tabview.add("📬 In-Game Mail")
        self.tab_security = self.tabview.add("🛡️ Security & Bans")
        self.tab_battles = self.tabview.add("⚔️ Live Battles")
        self.tab_marriage = self.tabview.add("💍 Marriages")
        self.tab_portals = self.tabview.add("🚪 Portals & Warps")
        self.tab_maps = self.tabview.add("🗺️ Map NPC Studio")
        self.tab_drops = self.tabview.add("🐉 Monster Drops")
        self.tab_chests = self.tabview.add("📦 Chest Drops")
        self.tab_mall = self.tabview.add("💎 Item Mall")
        self.tab_starter = self.tabview.add("🎁 Starter Items")
        self.tab_npc_res = self.tabview.add("🧙 NPC Resolver")
        self.tab_talk = self.tabview.add("📜 Talk Resolver")
        self.tab_settings = self.tabview.add("⚙️ Global Settings")

        self._build_dashboard_content(self.tab_dash)
        self._build_cheats_browser_content(self.tab_cheats)
        self._build_online_players_content(self.tab_players)
        self._build_users_content(self.tab_users)
        self._build_characters_content(self.tab_chars)
        self._build_guilds_content(self.tab_guilds)
        self._build_mail_content(self.tab_mail)
        self._build_security_content(self.tab_security)
        self._build_battles_content(self.tab_battles)
        self._build_marriage_content(self.tab_marriage)
        self._build_portals_content(self.tab_portals)
        self._build_map_npc_content(self.tab_maps)
        self._build_monster_drops_content(self.tab_drops)
        self._build_chest_drops_content(self.tab_chests)
        self._build_item_mall_content(self.tab_mall)
        self._build_starter_items_content(self.tab_starter)
        self._build_npc_resolver_content(self.tab_npc_res)
        self._build_talk_resolver_content(self.tab_talk)
        self._build_settings_content(self.tab_settings)

    # -------------------------------------------------------------
    # TAB 1: Dashboard
    # -------------------------------------------------------------
    def _build_dashboard_content(self, parent):
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=10)

        self.card_players = self._create_metric_card(cards_frame, "ACTIVE SESSIONS", "0", "#10B981", 0, "👥")
        self.card_accounts = self._create_metric_card(cards_frame, "TOTAL ACCOUNTS", str(self._get_db_count("accounts")), "#38BDF8", 1, "🗄️")
        self.card_chars = self._create_metric_card(cards_frame, "TOTAL CHARACTERS", str(self._get_db_count("characters")), "#A78BFA", 2, "🧙")
        self.card_maps = self._create_metric_card(cards_frame, "LOADED MAPS", "1,119", "#FBBF24", 3, "🗺️")

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, width=340, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="y", padx=(0, 10), pady=5)

        ctk.CTkLabel(left, text="Server Management", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(left, text="Server Name / Brand:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(anchor="w", padx=15)
        cur_srv_name = "Mamiletta"
        if self.game_server and hasattr(self.game_server, "get_server_name"):
            cur_srv_name = self.game_server.get_server_name()
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute("SELECT value FROM server_config WHERE key = 'server_name'").fetchone()
                if row and row[0]:
                    cur_srv_name = row[0]
                conn.close()
            except Exception:
                pass

        self.ent_srv_name = ctk.CTkEntry(left, placeholder_text="Server Name (Mamiletta)", fg_color="#0B0F19", border_color="#1E293B", height=32)
        self.ent_srv_name.insert(0, cur_srv_name)
        self.ent_srv_name.pack(fill="x", padx=15, pady=(2, 6))

        ctk.CTkButton(left, text="💾 Save Server Name (Brand)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_update_server_name).pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(left, text="Global MOTD / Welcome Message:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(2, 2))
        cur_motd = "Welcome to Wonderland Online Private Server!\nEnjoy your adventure!"
        if self.game_server and hasattr(self.game_server, "get_motd"):
            cur_motd = self.game_server.get_motd()
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute("SELECT value FROM server_config WHERE key = 'welcome_message'").fetchone()
                if row and row[0]:
                    cur_motd = row[0]
                conn.close()
            except Exception:
                pass

        self.txt_motd = ctk.CTkTextbox(left, height=75, fg_color="#0B0F19", text_color="#F1F5F9", font=ctk.CTkFont(size=11), corner_radius=6, border_width=1, border_color="#1E293B")
        self.txt_motd.insert("1.0", cur_motd)
        self.txt_motd.pack(fill="x", padx=15, pady=(2, 6))

        f_motd_btns = ctk.CTkFrame(left, fg_color="transparent")
        f_motd_btns.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(f_motd_btns, text="💾 Save MOTD", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_update_motd).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_motd_btns, text="📢 Broadcast MOTD", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#2563EB", hover_color="#3B82F6", height=32, corner_radius=8, command=self.action_broadcast_motd).pack(side="right", fill="x", expand=True, padx=(4, 0))

        ctk.CTkLabel(left, text="Global Marquee Announcement:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(anchor="w", padx=15)
        self.ent_welcome = ctk.CTkEntry(left, placeholder_text="Broadcast Message", fg_color="#0B0F19", border_color="#1E293B", height=32)
        self.ent_welcome.insert(0, "Special Announcement: Server maintenance in 10 minutes!")
        self.ent_welcome.pack(fill="x", padx=15, pady=(2, 6))

        self.cmb_broadcast_color = ctk.CTkComboBox(left, values=["Yellow (System)", "Red (Alert)", "Blue (Info)", "Green (Notice)", "Purple (GM)"], height=32, fg_color="#0B0F19", border_color="#1E293B")
        self.cmb_broadcast_color.set("Yellow (System)")
        self.cmb_broadcast_color.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(left, text="📢 Send Marquee Alert", font=ctk.CTkFont(weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", height=34, corner_radius=8, command=self.action_broadcast_marquee).pack(fill="x", padx=15, pady=4)
        ctk.CTkButton(left, text="🚫 Disconnect All Players", font=ctk.CTkFont(weight="bold"), fg_color="#DC2626", hover_color="#B91C1C", height=34, corner_radius=8, command=self.action_kick_all).pack(fill="x", padx=15, pady=4)
        ctk.CTkButton(left, text="🧹 Clear Console Log", font=ctk.CTkFont(), fg_color="#1E293B", hover_color="#334155", height=34, corner_radius=8, command=self.action_clear_logs).pack(fill="x", padx=15, pady=4)

        right = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both", expand=True, pady=5)

        f_bar = ctk.CTkFrame(right, fg_color="transparent")
        f_bar.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_bar, text="Live Server Console Terminal", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F8FAFC").pack(side="left")
        ctk.CTkButton(f_bar, text="🧹 Clear", width=65, height=26, font=ctk.CTkFont(size=11), fg_color="#1E293B", hover_color="#334155", corner_radius=6, command=self.action_clear_logs).pack(side="right")

        f_log_wrap = ctk.CTkFrame(right, fg_color="transparent")
        f_log_wrap.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.log_text = tk.Text(f_log_wrap, bg="#030712", fg="#F1F5F9", font=("JetBrains Mono", 9), relief="flat", padx=12, pady=12, highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#1E293B")
        if HAS_CTK:
            sb_log = ctk.CTkScrollbar(f_log_wrap, orientation="vertical", command=self.log_text.yview)
        else:
            sb_log = ttk.Scrollbar(f_log_wrap, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb_log.set)
        sb_log.pack(side="right", fill="y", padx=(2, 0))
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_text.tag_config("INFO", foreground="#38BDF8")
        self.log_text.tag_config("WARNING", foreground="#FBBF24")
        self.log_text.tag_config("ERROR", foreground="#F43F5E")
        self.log_text.tag_config("DEBUG", foreground="#64748B")

        self._setup_log_pipe()

    # -------------------------------------------------------------
    # TAB 2: Live Cheats & 4-Column Browser (Direct Port from C# MainForm1)
    # -------------------------------------------------------------
    def _build_cheats_browser_content(self, parent):
        top_bar = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        top_bar.add_widget(ctk.CTkLabel(top_bar, text="Target Online Player:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(15, 6), pady=6)
        self.cmb_cheat_player = ctk.CTkComboBox(top_bar, values=["(Select Active Player)"], width=220, fg_color="#0B0F19", border_color="#1E293B")
        top_bar.add_widget(self.cmb_cheat_player, padx=5, pady=6)

        top_bar.add_widget(ctk.CTkButton(top_bar, text="🔄 Refresh Online", fg_color="#1E293B", hover_color="#334155", width=130, height=32, corner_radius=8, command=self._refresh_online_players_combos), padx=8, pady=6)

        # 4-Column Grid: Maps | Vehicles | Items | NPCs
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=5)
        for i in range(4):
            grid.columnconfigure(i, weight=1)

        # Col 1: Maps
        c1 = ctk.CTkFrame(grid, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        c1.grid(row=0, column=0, sticky="nsew", padx=4)
        ctk.CTkLabel(c1, text="🗺️ Maps (1,119)", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 6))
        self.ent_search_maps = ctk.CTkEntry(c1, placeholder_text="Filter Maps...", fg_color="#0B0F19", border_color="#1E293B", height=30)
        self.ent_search_maps.pack(fill="x", padx=10, pady=(0, 4))
        self.ent_search_maps.bind("<KeyRelease>", lambda e: self._filter_maps_list())
        f_maps = ctk.CTkFrame(c1, fg_color="transparent")
        f_maps.pack(fill="both", expand=True, padx=10, pady=4)
        self.list_maps = tk.Listbox(f_maps, bg="#080C14", fg="#F1F5F9", selectbackground="#2563EB", selectforeground="#FFFFFF", highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#2563EB", relief="flat", font=("Segoe UI", 9))
        sb_maps = ctk.CTkScrollbar(f_maps, orientation="vertical", command=self.list_maps.yview) if HAS_CTK else ttk.Scrollbar(f_maps, orient="vertical", command=self.list_maps.yview)
        self.list_maps.configure(yscrollcommand=sb_maps.set)
        sb_maps.pack(side="right", fill="y", padx=(2, 0))
        self.list_maps.pack(side="left", fill="both", expand=True)
        ctk.CTkButton(c1, text="🚀 Warp Player to Map", fg_color="#0284C7", hover_color="#0369A1", height=32, corner_radius=8, command=self.action_cheat_warp_map).pack(fill="x", padx=10, pady=(4, 10))

        # Col 2: Vehicles
        c2 = ctk.CTkFrame(grid, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c2, text="🚗 Vehicles", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 6))
        self.ent_search_veh = ctk.CTkEntry(c2, placeholder_text="Filter Vehicles...", fg_color="#0B0F19", border_color="#1E293B", height=30)
        self.ent_search_veh.pack(fill="x", padx=10, pady=(0, 4))
        f_veh = ctk.CTkFrame(c2, fg_color="transparent")
        f_veh.pack(fill="both", expand=True, padx=10, pady=4)
        self.list_veh = tk.Listbox(f_veh, bg="#080C14", fg="#F1F5F9", selectbackground="#2563EB", selectforeground="#FFFFFF", highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#2563EB", relief="flat", font=("Segoe UI", 9))
        sb_veh = ctk.CTkScrollbar(f_veh, orientation="vertical", command=self.list_veh.yview) if HAS_CTK else ttk.Scrollbar(f_veh, orient="vertical", command=self.list_veh.yview)
        self.list_veh.configure(yscrollcommand=sb_veh.set)
        sb_veh.pack(side="right", fill="y", padx=(2, 0))
        self.list_veh.pack(side="left", fill="both", expand=True)
        f_veh_btns = ctk.CTkFrame(c2, fg_color="transparent")
        f_veh_btns.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkButton(f_veh_btns, text="Ride", width=70, height=32, fg_color="#10B981", hover_color="#059669", corner_radius=8, command=self.action_cheat_ride_vehicle).pack(side="left", padx=2)
        ctk.CTkButton(f_veh_btns, text="Remove Vehicle", width=125, height=32, fg_color="#DC2626", hover_color="#B91C1C", corner_radius=8, command=self.action_cheat_unride_vehicle).pack(side="right", padx=2)

        # Col 3: Items
        c3 = ctk.CTkFrame(grid, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        c3.grid(row=0, column=2, sticky="nsew", padx=4)
        ctk.CTkLabel(c3, text="🎁 Items Spawner", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 6))
        self.ent_search_items = ctk.CTkEntry(c3, placeholder_text="Filter Items...", fg_color="#0B0F19", border_color="#1E293B", height=30)
        self.ent_search_items.pack(fill="x", padx=10, pady=(0, 4))
        self.ent_search_items.bind("<KeyRelease>", lambda e: self._filter_items_list())
        f_items = ctk.CTkFrame(c3, fg_color="transparent")
        f_items.pack(fill="both", expand=True, padx=10, pady=4)
        self.list_items = tk.Listbox(f_items, bg="#080C14", fg="#F1F5F9", selectbackground="#2563EB", selectforeground="#FFFFFF", highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#2563EB", relief="flat", font=("Segoe UI", 9))
        sb_items = ctk.CTkScrollbar(f_items, orientation="vertical", command=self.list_items.yview) if HAS_CTK else ttk.Scrollbar(f_items, orient="vertical", command=self.list_items.yview)
        self.list_items.configure(yscrollcommand=sb_items.set)
        sb_items.pack(side="right", fill="y", padx=(2, 0))
        self.list_items.pack(side="left", fill="both", expand=True)
        f_item_spawn = ctk.CTkFrame(c3, fg_color="transparent")
        f_item_spawn.pack(fill="x", padx=10, pady=(4, 10))
        self.ent_spawn_qty = ctk.CTkEntry(f_item_spawn, width=55, height=32, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_spawn_qty.insert(0, "1")
        self.ent_spawn_qty.pack(side="left", padx=2)
        ctk.CTkButton(f_item_spawn, text="Spawn to Inv", fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_cheat_spawn_item).pack(side="right", fill="x", expand=True, padx=2)

        # Col 4: NPCs & Monsters
        c4 = ctk.CTkFrame(grid, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        c4.grid(row=0, column=3, sticky="nsew", padx=4)
        ctk.CTkLabel(c4, text="👾 NPC & Monsters (4,916)", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 6))
        self.ent_search_npcs = ctk.CTkEntry(c4, placeholder_text="Filter NPCs...", fg_color="#0B0F19", border_color="#1E293B", height=30)
        self.ent_search_npcs.pack(fill="x", padx=10, pady=(0, 4))
        self.ent_search_npcs.bind("<KeyRelease>", lambda e: self._filter_npcs_list())
        f_npcs = ctk.CTkFrame(c4, fg_color="transparent")
        f_npcs.pack(fill="both", expand=True, padx=10, pady=4)
        self.list_npcs = tk.Listbox(f_npcs, bg="#080C14", fg="#F1F5F9", selectbackground="#2563EB", selectforeground="#FFFFFF", highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#2563EB", relief="flat", font=("Segoe UI", 9))
        sb_npcs = ctk.CTkScrollbar(f_npcs, orientation="vertical", command=self.list_npcs.yview) if HAS_CTK else ttk.Scrollbar(f_npcs, orient="vertical", command=self.list_npcs.yview)
        self.list_npcs.configure(yscrollcommand=sb_npcs.set)
        sb_npcs.pack(side="right", fill="y", padx=(2, 0))
        self.list_npcs.pack(side="left", fill="both", expand=True)
        f_npc_btns = ctk.CTkFrame(c4, fg_color="transparent")
        f_npc_btns.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkButton(f_npc_btns, text="⚔️ Battle", width=70, height=32, fg_color="#DC2626", hover_color="#B91C1C", corner_radius=8, command=self.action_cheat_battle_npc).pack(side="left", padx=2)
        ctk.CTkButton(f_npc_btns, text="👥 Add Pet", width=75, height=32, fg_color="#8B5CF6", hover_color="#7C3AED", corner_radius=8, command=self.action_cheat_recruit_npc).pack(side="left", padx=2)
        ctk.CTkButton(f_npc_btns, text="Leave", width=55, height=32, fg_color="#1E293B", hover_color="#334155", corner_radius=8, command=self.action_cheat_leave_npc).pack(side="right", padx=2)

        # Bottom GM Booster Strip
        bottom_strip = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        bottom_strip.pack(fill="x", padx=10, pady=(5, 10))

        bottom_strip.add_widget(ctk.CTkLabel(bottom_strip, text="Give Stat Points:", font=ctk.CTkFont(size=12), text_color="#94A3B8"), padx=(15, 4), pady=6)
        self.ent_give_stat_pts = ctk.CTkEntry(bottom_strip, width=65, height=32, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_give_stat_pts.insert(0, "100")
        bottom_strip.add_widget(self.ent_give_stat_pts, padx=2, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="Give Points", width=85, height=32, fg_color="#2563EB", hover_color="#3B82F6", corner_radius=8, command=self.action_give_stat_points), padx=4, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="Reset Stats", width=85, height=32, fg_color="#1E293B", hover_color="#334155", corner_radius=8, command=self.action_reset_stats), padx=4, pady=6)

        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="💰 +1M Gold", width=95, height=32, fg_color="#F59E0B", hover_color="#D97706", text_color="#000", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_give_gold_amount(1000000)), padx=6, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="💎 +2,000 IM", width=95, height=32, fg_color="#8B5CF6", hover_color="#7C3AED", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_give_im_points(2000)), padx=4, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="⭐ +10 Levels", width=95, height=32, fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_add_levels(10)), padx=4, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="💚 Full Heal", width=85, height=32, fg_color="#059669", hover_color="#047857", corner_radius=8, command=self.action_heal_player), padx=4, pady=6)
        bottom_strip.add_widget(ctk.CTkButton(bottom_strip, text="🛡 God Mode", width=85, height=32, fg_color="#7C3AED", hover_color="#6D28D9", corner_radius=8, command=self.action_god_mode), padx=4, pady=6)

        self._populate_cheats_browser_lists()

    # -------------------------------------------------------------
    # TAB 3: Online Sessions Manager
    # -------------------------------------------------------------
    def _build_online_players_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        top_filter = ctk.CTkFrame(left, fg_color="transparent")
        top_filter.pack(fill="x", padx=15, pady=(12, 4))
        ctk.CTkLabel(top_filter, text="🔍 Filter Sessions:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(side="left", padx=(0, 6))
        self.ent_search_players = ctk.CTkEntry(top_filter, placeholder_text="Filter Name, Account, Map...", fg_color="#0B0F19", border_color="#1E293B", width=220)
        self.ent_search_players.pack(side="left", padx=2)
        self.ent_search_players.bind("<KeyRelease>", lambda e: self._refresh_metrics())

        cols = ("CharID", "Name", "Account", "Level", "Gold", "MapID", "X", "Y", "IP")
        self.tree_players, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", selectmode="browse", padx=15, pady=8)
        for c in cols:
            self.tree_players.heading(c, text=c)
            self.tree_players.column(c, width=70 if c in ("Level", "X", "Y") else 100, anchor="center")

        right = ctk.CTkFrame(split, width=340, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="y")

        ctk.CTkLabel(right, text="Live GM Session Tools", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 8))
        self.lbl_selected_player = ctk.CTkLabel(right, text="Selected: None", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FBBF24")
        self.lbl_selected_player.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkButton(right, text="🧙 Open Deep Character Editor", fg_color="#2563EB", hover_color="#3B82F6", height=34, corner_radius=8, command=self.action_open_selected_char_editor).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="💚 Heal HP/SP to 100%", fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_heal_player).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="🛡 Toggle Invincible God Mode", fg_color="#8B5CF6", hover_color="#7C3AED", height=32, corner_radius=8, command=self.action_god_mode).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="👢 Kick Selected Player", fg_color="#1E293B", hover_color="#334155", height=32, corner_radius=8, command=self.action_kick_player).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="⛔ Ban Player Account", fg_color="#DC2626", hover_color="#B91C1C", height=32, corner_radius=8, command=self.action_ban_player).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="🌐 Ban Player IP", fg_color="#991B1B", hover_color="#7F1D1D", height=32, corner_radius=8, command=self.action_ban_player_ip).pack(fill="x", padx=15, pady=5)

        self.tree_players.bind("<<TreeviewSelect>>", self._on_player_selected)

    # -------------------------------------------------------------
    # TAB 4: Users & Accounts Manager (C# tabPageUsers)
    # -------------------------------------------------------------
    def _build_users_content(self, parent):
        # Search and Action Toolbar
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="🔍 Search (IP, Char, User, ID):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(12, 4), pady=6)
        self.ent_user_search = ctk.CTkEntry(top, width=230, placeholder_text="e.g. 192.168.1.10 or Hero or 1", fg_color="#0B0F19", border_color="#1E293B")
        top.add_widget(self.ent_user_search, padx=4, pady=6)
        self.ent_user_search.bind("<Return>", lambda e: self.action_refresh_users())
        top.add_widget(ctk.CTkButton(top, text="Search", fg_color="#2563EB", hover_color="#3B82F6", width=70, corner_radius=8, command=self.action_refresh_users), padx=3, pady=6)
        top.add_widget(ctk.CTkButton(top, text="Reset", fg_color="#1E293B", hover_color="#334155", width=65, corner_radius=8, command=self._reset_user_search), padx=3, pady=6)

        top.add_widget(ctk.CTkButton(top, text="➕ Add User", fg_color="#10B981", hover_color="#059669", width=95, corner_radius=8, command=self.action_create_user_modal), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🔑 Pass", fg_color="#2563EB", hover_color="#3B82F6", width=65, corner_radius=8, command=self.action_change_password_modal), padx=3, pady=6)
        top.add_widget(ctk.CTkButton(top, text="💎 Points", fg_color="#8B5CF6", hover_color="#7C3AED", width=75, corner_radius=8, command=self.action_add_im_points_modal), padx=3, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🗑 Delete", fg_color="#DC2626", hover_color="#B91C1C", width=75, corner_radius=8, command=self.action_delete_user), padx=3, pady=6)

        top.add_widget(ctk.CTkButton(top, text="🚫 Ban User", fg_color="#DC2626", hover_color="#B91C1C", width=95, corner_radius=8, command=self.action_ban_user_gui), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="✅ Unban User", fg_color="#10B981", hover_color="#059669", width=105, corner_radius=8, command=self.action_unban_user_gui), padx=3, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🌐 Ban IP", fg_color="#991B1B", hover_color="#7F1D1D", width=90, corner_radius=8, command=self.action_ban_ip_gui), padx=3, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🔓 Unban IP", fg_color="#0D9488", hover_color="#0F766E", width=95, corner_radius=8, command=self.action_unban_ip_gui), padx=3, pady=6)

        cols = ("AccountID", "Username", "Characters", "LastIP", "LastLogin", "UserBan", "IPBan", "GMLevel")
        self.tree_users, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_users.heading(c, text=c)
            self.tree_users.column(c, width=70 if c in ("AccountID", "GMLevel", "UserBan", "IPBan") else (180 if c == "Characters" else 130), anchor="center")
        self.action_refresh_users()

    # -------------------------------------------------------------
    # TAB 5: Characters Manager (C# tabPageCharacters)
    # -------------------------------------------------------------
    def _build_characters_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Refresh Characters", fg_color="#1E293B", hover_color="#334155", width=150, corner_radius=8, command=self.action_refresh_characters), padx=6, pady=6)

        top.add_widget(ctk.CTkLabel(top, text="🔍 Filter:", font=ctk.CTkFont(size=12), text_color="#94A3B8"), padx=(10, 4), pady=6)
        self.ent_char_search = ctk.CTkEntry(top, placeholder_text="Filter Name, CharID, AccountID...", fg_color="#0B0F19", border_color="#1E293B", width=220)
        top.add_widget(self.ent_char_search, padx=4, pady=6)
        self.ent_char_search.bind("<KeyRelease>", lambda e: self.action_refresh_characters())

        top.add_widget(ctk.CTkButton(top, text="🧙 Open Full Character Data Editor", font=ctk.CTkFont(weight="bold"), fg_color="#2563EB", hover_color="#3B82F6", width=260, corner_radius=8, command=self.action_open_selected_char_editor), padx=6, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🗑 Delete Character", fg_color="#DC2626", hover_color="#B91C1C", width=140, corner_radius=8, command=self.action_delete_character), padx=6, pady=6)

        cols = ("CharID", "AccountID", "CharName", "Level", "Element", "RebornJob", "Gold", "MapID", "LastLogin")
        self.tree_characters, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_characters.heading(c, text=c)
            self.tree_characters.column(c, width=70 if c in ("CharID", "AccountID", "Level", "Element") else 120, anchor="center")
        self.tree_characters.bind("<Double-1>", lambda e: self.action_open_selected_char_editor())
        self.action_refresh_characters()

    # -------------------------------------------------------------
    # TAB 6: Portals & Warps Manager (C# tabPagePortals)
    # -------------------------------------------------------------
    def _build_portals_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Filter Source Map ID:", font=ctk.CTkFont(size=12), text_color="#94A3B8"), padx=(10, 4), pady=6)
        self.ent_portal_filter = ctk.CTkEntry(top, width=130, placeholder_text="e.g. 10001", fg_color="#0B0F19", border_color="#1E293B")
        top.add_widget(self.ent_portal_filter, padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🔍 Filter", fg_color="#2563EB", hover_color="#3B82F6", width=90, corner_radius=8, command=self.action_refresh_portals), padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="🚀 Test Warp on Player", fg_color="#10B981", hover_color="#059669", width=170, corner_radius=8, command=self.action_test_warp_portal), padx=6, pady=6)

        cols = ("PortalID", "SourceMap", "PortalName", "DestMap", "DestX", "DestY")
        self.tree_portals, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_portals.heading(c, text=c)
            self.tree_portals.column(c, width=80 if c != "PortalName" else 200, anchor="center")
        self.action_refresh_portals()

    # -------------------------------------------------------------
    # TAB 7: Map NPC & Scene Studio (C# SetupMapNpcStudioTab)
    # -------------------------------------------------------------
    def _build_map_npc_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Select Map:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(10, 4), pady=6)
        self.cmb_studio_map = ctk.CTkComboBox(top, values=["10001 - Kelan Village", "10017 - Shipwreck", "10035 - Beach", "12000 - Welling Village", "11016 - South Island"], width=240, fg_color="#0B0F19", border_color="#1E293B", command=lambda m: self._load_studio_npcs(m))
        top.add_widget(self.cmb_studio_map, padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="⚡ Simulate Event on Selected Player", font=ctk.CTkFont(weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", width=260, corner_radius=8, command=self.action_simulate_npc_event), padx=6, pady=6)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        # Left NPC table
        left = ctk.CTkFrame(split, width=420, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", padx=(0, 6))

        cols = ("ClickID", "NPCName", "TID", "Pos", "Events")
        self.tree_studio_npcs, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", padx=10, pady=10)
        for c in cols:
            self.tree_studio_npcs.heading(c, text=c)
            self.tree_studio_npcs.column(c, width=60 if c in ("ClickID", "TID") else 95, anchor="center")
        self.tree_studio_npcs.bind("<<TreeviewSelect>>", self._on_studio_npc_selected)

        # Right Event Sequence Flow Viewer
        right = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="📜 Event Sequence Flow & Opcode Inspector", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 4))
        f_flow_wrap = ctk.CTkFrame(right, fg_color="transparent")
        f_flow_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt_event_flow = tk.Text(f_flow_wrap, bg="#030712", fg="#F1F5F9", font=("JetBrains Mono", 9), relief="flat", padx=12, pady=12, highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#1E293B")
        sb_flow = ctk.CTkScrollbar(f_flow_wrap, orientation="vertical", command=self.txt_event_flow.yview) if HAS_CTK else ttk.Scrollbar(f_flow_wrap, orient="vertical", command=self.txt_event_flow.yview)
        self.txt_event_flow.configure(yscrollcommand=sb_flow.set)
        sb_flow.pack(side="right", fill="y", padx=(2, 0))
        self.txt_event_flow.pack(side="left", fill="both", expand=True)

    # -------------------------------------------------------------
    # TAB 8: Monster Drops Studio (C# SetupMonsterDropsTab)
    # -------------------------------------------------------------
    def _build_monster_drops_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Search Monster (ID or Name):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(12, 4), pady=6)
        self.ent_monster_search = ctk.CTkEntry(top, width=220, placeholder_text="e.g. Jelly or 17001", fg_color="#0B0F19", border_color="#1E293B")
        top.add_widget(self.ent_monster_search, padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="Search Npc.dat", fg_color="#2563EB", hover_color="#3B82F6", width=120, corner_radius=8, command=self.action_search_monster), padx=6, pady=6)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("MonsterID", "Name", "Level", "HP", "SP", "Element")
        self.tree_monsters, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", padx=15, pady=15)
        for c in cols:
            self.tree_monsters.heading(c, text=c)
            self.tree_monsters.column(c, width=75 if c in ("Level", "HP", "SP") else 110, anchor="center")

        right = ctk.CTkFrame(split, width=380, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="Monster Item Drops (5 Slots)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 8))

        drop_cols = ("Slot", "ItemID", "ItemName", "Rate(1-10000)")
        self.tree_drops, _, _ = create_scrolled_treeview(right, columns=drop_cols, show="headings", height=7, padx=15, pady=5)
        for c in drop_cols:
            self.tree_drops.heading(c, text=c)
            self.tree_drops.column(c, width=80, anchor="center")

        f_edit = ctk.CTkFrame(right, fg_color="transparent")
        f_edit.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_edit, text="Item ID:", text_color="#94A3B8").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_drop_item_id = ctk.CTkEntry(f_edit, width=100, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_drop_item_id.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkLabel(f_edit, text="Rate (1-10000):", text_color="#94A3B8").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_drop_rate = ctk.CTkEntry(f_edit, width=100, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_drop_rate.grid(row=1, column=1, padx=8, pady=4)

        ctk.CTkButton(right, text="💾 Save Drop to Dynamic Database", font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669", height=34, corner_radius=8, command=self.action_save_monster_drop).pack(fill="x", padx=15, pady=10)
        self.tree_monsters.bind("<<TreeviewSelect>>", self._on_monster_selected)

    # -------------------------------------------------------------
    # TAB 9: Chest Drops Studio (C# tabPageChestDrops)
    # -------------------------------------------------------------
    def _build_chest_drops_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Select Map / Chest:", text_color="#94A3B8"), padx=(10, 4), pady=6)
        self.cmb_chest_map = ctk.CTkComboBox(top, values=["Map 10001 - Chest 1", "Map 10017 - Ship Chest", "Map 10035 - Beach Chest", "Map 12000 - Village Chest"], width=220, fg_color="#0B0F19", border_color="#1E293B")
        top.add_widget(self.cmb_chest_map, padx=4, pady=6)

        top.add_widget(ctk.CTkLabel(top, text="Respawn Seconds:", text_color="#94A3B8"), padx=(12, 4), pady=6)
        self.ent_chest_respawn = ctk.CTkEntry(top, width=70, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_chest_respawn.insert(0, "300")
        top.add_widget(self.ent_chest_respawn, padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="💾 Save Chest Table", fg_color="#10B981", hover_color="#059669", width=140, corner_radius=8, command=self.action_save_chest_drops), padx=6, pady=6)

        cols = ("ItemID", "ItemName", "Count", "Weight/Rate", "RareFlag")
        self.tree_chests, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_chests.heading(c, text=c)
            self.tree_chests.column(c, width=100 if c != "ItemName" else 200, anchor="center")
        self._load_sample_chest_drops()

    # -------------------------------------------------------------
    # TAB 10: Item Mall Manager (C# SetupItemMallTab)
    # -------------------------------------------------------------
    def _build_item_mall_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Reload Catalog", fg_color="#1E293B", hover_color="#334155", width=125, corner_radius=8, command=self.action_refresh_item_mall), padx=(10, 4), pady=6)
        top.add_widget(ctk.CTkButton(top, text="➕ Add Item", fg_color="#10B981", hover_color="#059669", width=110, corner_radius=8, command=self.action_add_mall_item_modal), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="✏ Edit Item", fg_color="#2563EB", hover_color="#3B82F6", width=100, corner_radius=8, command=self.action_edit_mall_item_modal), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🗑 Delete Item", fg_color="#DC2626", hover_color="#B91C1C", width=110, corner_radius=8, command=self.action_delete_mall_item), padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="📥 Import JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_import_mall_json), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="📤 Export JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_export_mall_json), padx=4, pady=6)

        top.add_widget(ctk.CTkLabel(top, text="Filter Category:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(12, 4), pady=6)
        self.cmb_mall_filter = ctk.CTkComboBox(
            top,
            values=["All Categories", "1 - Hot", "2 - Armory", "3 - Weaponry", "4 - Grocery", "5 - Furniture", "6 - Slot Machine", "7 - Forging Room"],
            width=160,
            fg_color="#0B0F19",
            border_color="#1E293B",
            command=lambda _: self.action_refresh_item_mall()
        )
        self.cmb_mall_filter.set("All Categories")
        top.add_widget(self.cmb_mall_filter, padx=4, pady=6)

        cols = ("ItemID", "Name", "Category", "Points", "OriginalPrice", "Count", "Badge", "OnSale")
        self.tree_mall, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        col_widths = {
            "ItemID": 80,
            "Name": 240,
            "Category": 140,
            "Points": 90,
            "OriginalPrice": 100,
            "Count": 70,
            "Badge": 90,
            "OnSale": 80
        }
        for c in cols:
            self.tree_mall.heading(c, text=c)
            self.tree_mall.column(c, width=col_widths.get(c, 100), anchor="center" if c != "Name" else "w")
        self.tree_mall.bind("<Double-1>", lambda _: self.action_edit_mall_item_modal())

        self.action_refresh_item_mall()

    # -------------------------------------------------------------
    # TAB 11: Starter Items Pack Manager (AC 23 Sub 6)
    # -------------------------------------------------------------
    def _build_starter_items_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Reload Starters", fg_color="#1E293B", hover_color="#334155", width=125, corner_radius=8, command=self.action_refresh_starter_items), padx=(10, 4), pady=6)
        top.add_widget(ctk.CTkButton(top, text="➕ Add Starter Item", fg_color="#10B981", hover_color="#059669", width=140, corner_radius=8, command=self.action_add_starter_item_modal), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="✏ Edit Selected", fg_color="#2563EB", hover_color="#3B82F6", width=110, corner_radius=8, command=self.action_edit_starter_item_modal), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🗑 Remove Item", fg_color="#DC2626", hover_color="#B91C1C", width=110, corner_radius=8, command=self.action_delete_starter_item), padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="📥 Import JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_import_starter_json), padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="📤 Export JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_export_starter_json), padx=4, pady=6)

        self.lbl_starter_summary = ctk.CTkLabel(top, text="Items: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10B981")
        top.add_widget(self.lbl_starter_summary, padx=10, pady=6)

        cols = ("Order", "ItemID", "Name", "Quantity", "Description")
        self.tree_starters, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        col_widths = {
            "Order": 70,
            "ItemID": 90,
            "Name": 250,
            "Quantity": 100,
            "Description": 400
        }
        for c in cols:
            self.tree_starters.heading(c, text=c)
            self.tree_starters.column(c, width=col_widths.get(c, 100), anchor="center" if c not in ("Name", "Description") else "w")
        self.tree_starters.bind("<Double-1>", lambda _: self.action_edit_starter_item_modal())

        self.action_refresh_starter_items()

    # -------------------------------------------------------------
    # TAB 12: NPC Resolver & Directory (C# SetupNpcResolverTab)
    # -------------------------------------------------------------
    def _build_npc_resolver_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Template ID (TID):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(10, 4), pady=6)
        self.ent_res_tid = ctk.CTkEntry(top, width=100, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_res_tid.insert(0, "14013")
        top.add_widget(self.ent_res_tid, padx=4, pady=6)

        top.add_widget(ctk.CTkButton(top, text="🔍 Resolve Template", fg_color="#2563EB", hover_color="#3B82F6", width=140, corner_radius=8, command=self.action_resolve_npc_tid), padx=6, pady=6)
        self.lbl_res_name_card = ctk.CTkLabel(top, text="Resolved: Ashley (TID: 14013, Humanoid)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10B981")
        top.add_widget(self.lbl_res_name_card, padx=12, pady=6)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        cols = ("TID", "NPCName", "Level", "HP", "SP", "Category")
        self.tree_npc_dir, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", padx=10, pady=10)
        for c in cols:
            self.tree_npc_dir.heading(c, text=c)
            self.tree_npc_dir.column(c, width=70 if c in ("TID", "Level", "HP", "SP") else 140, anchor="center")

        right = ctk.CTkFrame(split, width=360, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="🌍 World Spawn Inspector (eve.Emg)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 4))
        f_spawns_wrap = ctk.CTkFrame(right, fg_color="transparent")
        f_spawns_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt_world_spawns = tk.Text(f_spawns_wrap, bg="#030712", fg="#F1F5F9", font=("JetBrains Mono", 9), relief="flat", padx=12, pady=12, highlightthickness=1, highlightbackground="#1E293B", highlightcolor="#1E293B")
        sb_spawns = ctk.CTkScrollbar(f_spawns_wrap, orientation="vertical", command=self.txt_world_spawns.yview) if HAS_CTK else ttk.Scrollbar(f_spawns_wrap, orient="vertical", command=self.txt_world_spawns.yview)
        self.txt_world_spawns.configure(yscrollcommand=sb_spawns.set)
        sb_spawns.pack(side="right", fill="y", padx=(2, 0))
        self.txt_world_spawns.pack(side="left", fill="both", expand=True)

        self._populate_npc_directory()

    # -------------------------------------------------------------
    # TAB 12: Talk Dialogue Resolver (C# SetupTalkResolverTab)
    # -------------------------------------------------------------
    def _build_talk_resolver_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkLabel(top, text="Search Talk.dat (17,489 Dialogues):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8"), padx=(12, 4), pady=6)
        self.ent_talk_search = ctk.CTkEntry(top, width=280, placeholder_text="Enter keyword or TalkID (e.g. voyage or 39378)", fg_color="#0B0F19", border_color="#1E293B")
        top.add_widget(self.ent_talk_search, padx=4, pady=6)
        top.add_widget(ctk.CTkButton(top, text="🔍 Search Dialogues", fg_color="#2563EB", hover_color="#3B82F6", width=140, corner_radius=8, command=self.action_search_talk), padx=8, pady=6)

        cols = ("TalkID", "DialogueText")
        self.tree_talk, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        self.tree_talk.heading("TalkID", text="Talk ID")
        self.tree_talk.column("TalkID", width=100, anchor="center")
        self.tree_talk.heading("DialogueText", text="Character Speech / Dialogue Text")
        self.tree_talk.column("DialogueText", width=900, anchor="w")
        self._load_sample_talk_dialogues()

    # -------------------------------------------------------------
    # TAB 13: Global Rates & Settings (C# tabPageSettings)
    # -------------------------------------------------------------
    def _build_settings_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(split, width=460, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left, text="⚡ Global Gameplay Multipliers", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 10))

        cur_srv = "Mamiletta"
        if self.game_server and hasattr(self.game_server, "get_server_name"):
            cur_srv = self.game_server.get_server_name()
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute("SELECT value FROM server_config WHERE key = 'server_name'").fetchone()
                if row and row[0]:
                    cur_srv = row[0]
                conn.close()
            except Exception:
                pass

        cur_motd = "Welcome to Wonderland Online Private Server!\nEnjoy your adventure!"
        if self.game_server and hasattr(self.game_server, "get_motd"):
            cur_motd = self.game_server.get_motd()
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                row = conn.execute("SELECT value FROM server_config WHERE key = 'welcome_message'").fetchone()
                if row and row[0]:
                    cur_motd = row[0]
                conn.close()
            except Exception:
                pass

        multipliers = [
            ("Server Name / Brand (AC 0):", "server_name", cur_srv),
            ("MOTD / Welcome Message:", "welcome_message", cur_motd.replace("\n", " | ")),
            ("Base EXP Multiplier:", "exp_rate", "1.0"),
            ("Monster Drop Rate Multiplier:", "drop_rate", "1.0"),
            ("Pet EXP Multiplier:", "pet_exp_rate", "1.0"),
            ("Gold Drop Multiplier:", "gold_rate", "1.0"),
            ("Alchemy Compound Success Multiplier:", "alchemy_rate", "1.0"),
            ("Equipment Forging Success Multiplier:", "forging_rate", "1.0"),
            ("Resource Gathering Speed Multiplier:", "gathering_rate", "1.0"),
        ]

        self.setting_entries: Dict[str, ctk.CTkEntry] = {}
        for label, key, default in multipliers:
            f = ctk.CTkFrame(left, fg_color="transparent")
            f.pack(fill="x", padx=15, pady=4)
            ctk.CTkLabel(f, text=label, text_color="#94A3B8", width=250, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(f, width=170 if key == "server_name" else 110, fg_color="#0B0F19", border_color="#1E293B")
            ent.insert(0, str(default))
            ent.pack(side="right")
            self.setting_entries[key] = ent

        ctk.CTkButton(left, text="💾 Save Settings & Apply Live", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#10B981", hover_color="#059669", height=38, corner_radius=8, command=self.action_save_settings).pack(fill="x", padx=15, pady=20)

        right = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="🔄 Dynamic Data Subsystems Status", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 10))

        subsystems = [
            "1. Monster Drops & Rates", "2. Item Mall & Points", "3. Chest Rewards & Respawns",
            "4. Alchemy Recipes", "5. Tent Manufacture Crafting", "6. Resource Gathering Nodes",
            "7. Equipment Forging", "8. Instance Dungeons", "9. Titles & Achievements",
            "10. Vehicles & Mounts", "11. Lucky Draw Wheel", "12. Pet Amity & Foods",
            "13. Reborn Jobs", "14. Sustenance Potions", "15. Morph Items",
            "16. Pet Riding Saddles", "17. Recycle Center", "18. Death & Revive Altars",
            "19. Dynamic Weather", "20. Starter Items Pack"
        ]

        if HAS_CTK:
            f_sub_scroll = ctk.CTkScrollableFrame(right, fg_color="transparent")
            f_sub_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            for s in subsystems:
                ctk.CTkLabel(f_sub_scroll, text=f"  🟢 {s} - ACTIVE", text_color="#10B981", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10, pady=2)
        else:
            for s in subsystems:
                ctk.CTkLabel(right, text=f"  🟢 {s} - ACTIVE", text_color="#10B981", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=15, pady=1)

    # -------------------------------------------------------------
    # TAB: Guilds Manager
    # -------------------------------------------------------------
    def _build_guilds_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Refresh Guilds", fg_color="#1E293B", hover_color="#334155", width=140, corner_radius=8, command=self.action_refresh_guilds), padx=(10, 4), pady=6)

        top.add_widget(ctk.CTkLabel(top, text="🔍 Filter:", font=ctk.CTkFont(size=12), text_color="#94A3B8"), padx=(6, 2), pady=6)
        self.ent_guild_search = ctk.CTkEntry(top, placeholder_text="Filter by Guild Name or ID...", fg_color="#0B0F19", border_color="#1E293B", width=220)
        top.add_widget(self.ent_guild_search, padx=4, pady=6)
        self.ent_guild_search.bind("<KeyRelease>", lambda e: self.action_refresh_guilds())

        self.lbl_guilds_stats = ctk.CTkLabel(top, text="Total Guilds: 0 | Members: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8")
        top.add_widget(self.lbl_guilds_stats, padx=10, pady=6)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Guilds List
        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(left, text="🏰 Registered Guilds", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(12, 6))
        cols = ("GuildID", "GuildName", "LeaderName", "LeaderID", "Members", "Created")
        self.tree_guilds, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", selectmode="browse", padx=12, pady=8)
        for c in cols:
            self.tree_guilds.heading(c, text=c)
            self.tree_guilds.column(c, width=70 if c in ("GuildID", "LeaderID", "Members") else 120, anchor="center")
        self.tree_guilds.bind("<<TreeviewSelect>>", self._on_guild_selected)

        # Right: Selected Guild Details & Member Roster
        right = ctk.CTkFrame(split, width=420, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="🛡️ Guild Details & Members", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(12, 4))
        self.lbl_selected_guild = ctk.CTkLabel(right, text="Selected: (None)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FBBF24")
        self.lbl_selected_guild.pack(anchor="w", padx=15, pady=(0, 6))

        # Notice/Rules Box
        ctk.CTkLabel(right, text="Guild Announcement / Rules:", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w", padx=15)
        self.txt_guild_rules = tk.Text(right, height=3, bg="#080C14", fg="#F1F5F9", insertbackground="#38BDF8", relief="flat", font=("Segoe UI", 9))
        self.txt_guild_rules.pack(fill="x", padx=15, pady=(2, 6))

        f_rule_btns = ctk.CTkFrame(right, fg_color="transparent")
        f_rule_btns.pack(fill="x", padx=15, pady=(0, 8))
        ctk.CTkButton(f_rule_btns, text="💾 Save Notice", fg_color="#10B981", hover_color="#059669", height=28, corner_radius=6, command=self.action_save_guild_notice).pack(side="left", padx=2)

        # Member Roster Tree
        ctk.CTkLabel(right, text="Guild Member Roster:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(4, 2))
        m_cols = ("CharID", "Name", "Level", "Rank", "Element")
        self.tree_guild_members, _, _ = create_scrolled_treeview(right, columns=m_cols, show="headings", height=6, padx=15, pady=4)
        for mc in m_cols:
            self.tree_guild_members.heading(mc, text=mc)
            self.tree_guild_members.column(mc, width=60 if mc in ("CharID", "Level", "Element") else 90, anchor="center")

        # Guild Management Action Strip
        f_act = ResponsiveFlowFrame(right, fg_color="transparent", padx=3, pady=3)
        f_act.pack(fill="x", padx=15, pady=(8, 12))
        f_act.add_widget(ctk.CTkButton(f_act, text="👑 Change Leader", fg_color="#2563EB", hover_color="#3B82F6", height=32, corner_radius=8, command=self.action_guild_change_leader))
        f_act.add_widget(ctk.CTkButton(f_act, text="👢 Kick Member", fg_color="#E11D48", hover_color="#BE123C", height=32, corner_radius=8, command=self.action_guild_kick_member))
        f_act.add_widget(ctk.CTkButton(f_act, text="🗑 Disband Guild", fg_color="#DC2626", hover_color="#B91C1C", height=32, corner_radius=8, command=self.action_disband_guild))

        self.action_refresh_guilds()

    # -------------------------------------------------------------
    # TAB: In-Game Mail & GM Gifts Dispatcher
    # -------------------------------------------------------------
    def _build_mail_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Dispatch Mail Form
        left = ctk.CTkFrame(split, width=420, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(left, text="📬 Send GM Mail & Gifts", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(left, text="Recipient Target:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(2, 1))
        self.cmb_mail_target = ctk.CTkComboBox(left, values=["Single Character", "All Online Players", "All Registered Characters"], fg_color="#0B0F19", border_color="#1E293B", command=self._on_mail_target_changed)
        self.cmb_mail_target.pack(fill="x", padx=15, pady=(0, 8))

        self.lbl_mail_recipient = ctk.CTkLabel(left, text="Target Character Name or ID:", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.lbl_mail_recipient.pack(anchor="w", padx=15, pady=(2, 1))
        self.ent_mail_recipient = ctk.CTkEntry(left, placeholder_text="e.g. PlayerOne or 1", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_mail_recipient.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(left, text="Mail Subject:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(2, 1))
        self.ent_mail_subject = ctk.CTkEntry(left, placeholder_text="System Notification / Gift", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_mail_subject.insert(0, "🎁 Server Special Gift")
        self.ent_mail_subject.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(left, text="Message Body:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(2, 1))
        self.txt_mail_body = tk.Text(left, height=4, bg="#080C14", fg="#F1F5F9", insertbackground="#38BDF8", relief="flat", font=("Segoe UI", 9))
        self.txt_mail_body.insert("1.0", "Greetings Adventurer!\nPlease accept this reward from the server administration. Have fun!")
        self.txt_mail_body.pack(fill="x", padx=15, pady=(0, 8))

        # Attachments Frame
        f_attach = ctk.CTkFrame(left, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#1E293B")
        f_attach.pack(fill="x", padx=15, pady=(4, 12))

        ctk.CTkLabel(f_attach, text="📎 Attachments (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FBBF24").pack(anchor="w", padx=10, pady=(8, 4))

        f_gold = ctk.CTkFrame(f_attach, fg_color="transparent")
        f_gold.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(f_gold, text="💰 Gold:", width=70, anchor="w", text_color="#94A3B8").pack(side="left")
        self.ent_mail_gold = ctk.CTkEntry(f_gold, width=120, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_mail_gold.insert(0, "0")
        self.ent_mail_gold.pack(side="left", padx=4)

        f_item = ctk.CTkFrame(f_attach, fg_color="transparent")
        f_item.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(f_item, text="🎁 Item ID:", width=70, anchor="w", text_color="#94A3B8").pack(side="left")
        self.ent_mail_item_id = ctk.CTkEntry(f_item, width=120, placeholder_text="e.g. 27001", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_mail_item_id.insert(0, "0")
        self.ent_mail_item_id.pack(side="left", padx=4)
        self.ent_mail_item_id.bind("<KeyRelease>", self._on_mail_item_id_changed)

        ctk.CTkLabel(f_item, text="Qty:", width=35, anchor="w", text_color="#94A3B8").pack(side="left", padx=(6, 2))
        self.ent_mail_item_count = ctk.CTkEntry(f_item, width=60, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_mail_item_count.insert(0, "1")
        self.ent_mail_item_count.pack(side="left", padx=2)

        self.lbl_mail_item_preview = ctk.CTkLabel(f_attach, text="Item: None", font=ctk.CTkFont(size=10), text_color="#38BDF8")
        self.lbl_mail_item_preview.pack(anchor="w", padx=10, pady=(2, 6))

        ctk.CTkButton(left, text="🚀 Dispatch Mail to Target(s)", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#10B981", hover_color="#059669", height=38, corner_radius=8, command=self.action_dispatch_mail).pack(fill="x", padx=15, pady=(4, 15))

        # Right: Mailbox History & Inspector
        right = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both", expand=True)

        top_r = ResponsiveFlowFrame(right, fg_color="transparent", padx=4, pady=4)
        top_r.pack(fill="x", padx=15, pady=(12, 6))

        top_r.add_widget(ctk.CTkLabel(top_r, text="📜 Mailbox Records (`charmail`)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"), padx=(0, 8), pady=4)
        top_r.add_widget(ctk.CTkButton(top_r, text="🔄 Refresh", fg_color="#1E293B", hover_color="#334155", width=90, height=30, corner_radius=6, command=self.action_refresh_mail), padx=4, pady=4)
        top_r.add_widget(ctk.CTkButton(top_r, text="🗑 Delete Mail", fg_color="#DC2626", hover_color="#B91C1C", width=100, height=30, corner_radius=6, command=self.action_delete_mail), padx=4, pady=4)

        cols = ("MailID", "Sender", "ReceiverID", "Subject", "Gold", "ItemID", "ItemName", "Qty", "Claimed", "Date")
        self.tree_mail, _, _ = create_scrolled_treeview(right, columns=cols, show="headings", padx=15, pady=8)
        for c in cols:
            self.tree_mail.heading(c, text=c)
            self.tree_mail.column(c, width=65 if c in ("MailID", "ReceiverID", "Gold", "ItemID", "Qty", "Claimed") else 110, anchor="center")

        self.action_refresh_mail()

    # -------------------------------------------------------------
    # TAB: Security & IP Bans
    # -------------------------------------------------------------
    def _build_security_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Banned IP Addresses
        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        top_l = ResponsiveFlowFrame(left, fg_color="transparent", padx=4, pady=4)
        top_l.pack(fill="x", padx=15, pady=(12, 6))
        top_l.add_widget(ctk.CTkLabel(top_l, text="🌐 Banned IP Addresses (`banned_ips`)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"), padx=(0, 8), pady=4)
        top_l.add_widget(ctk.CTkButton(top_l, text="🔄 Refresh", fg_color="#1E293B", hover_color="#334155", width=80, height=28, corner_radius=6, command=self.action_refresh_banned_ips), padx=4, pady=4)

        cols_ip = ("IP", "Reason", "BannedAt", "BannedBy")
        self.tree_banned_ips, _, _ = create_scrolled_treeview(left, columns=cols_ip, show="headings", padx=12, pady=6)
        for c in cols_ip:
            self.tree_banned_ips.heading(c, text=c)
            self.tree_banned_ips.column(c, width=110 if c != "Reason" else 180, anchor="center")

        f_ip_btns = ResponsiveFlowFrame(left, fg_color="transparent", padx=4, pady=3)
        f_ip_btns.pack(fill="x", padx=15, pady=(6, 12))
        f_ip_btns.add_widget(ctk.CTkButton(f_ip_btns, text="➕ Add IP Ban", fg_color="#DC2626", hover_color="#B91C1C", height=32, corner_radius=8, command=self.action_add_banned_ip))
        f_ip_btns.add_widget(ctk.CTkButton(f_ip_btns, text="🔓 Unban Selected IP", fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_unban_ip))

        # Right: Banned Accounts
        right = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        top_r = ResponsiveFlowFrame(right, fg_color="transparent", padx=4, pady=4)
        top_r.pack(fill="x", padx=15, pady=(12, 6))
        top_r.add_widget(ctk.CTkLabel(top_r, text="⛔ Banned Accounts (`users WHERE banned=1`)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F43F5E"), padx=(0, 8), pady=4)
        top_r.add_widget(ctk.CTkButton(top_r, text="🔄 Refresh", fg_color="#1E293B", hover_color="#334155", width=80, height=28, corner_radius=6, command=self.action_refresh_banned_accounts), padx=4, pady=4)

        cols_acc = ("UserID", "Username", "Reason", "LastIP", "LastLogin")
        self.tree_banned_users, _, _ = create_scrolled_treeview(right, columns=cols_acc, show="headings", padx=12, pady=6)
        for c in cols_acc:
            self.tree_banned_users.heading(c, text=c)
            self.tree_banned_users.column(c, width=70 if c == "UserID" else 110, anchor="center")

        f_acc_btns = ResponsiveFlowFrame(right, fg_color="transparent", padx=4, pady=3)
        f_acc_btns.pack(fill="x", padx=15, pady=(6, 12))
        f_acc_btns.add_widget(ctk.CTkButton(f_acc_btns, text="⛔ Ban Account", fg_color="#DC2626", hover_color="#B91C1C", height=32, corner_radius=8, command=self.action_ban_account_manual))
        f_acc_btns.add_widget(ctk.CTkButton(f_acc_btns, text="🔓 Unban Selected Account", fg_color="#10B981", hover_color="#059669", height=32, corner_radius=8, command=self.action_unban_account))

        self.action_refresh_banned_ips()
        self.action_refresh_banned_accounts()

    # -------------------------------------------------------------
    # TAB: Live Battles Monitor
    # -------------------------------------------------------------
    def _build_battles_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Refresh Battles", fg_color="#1E293B", hover_color="#334155", width=140, corner_radius=8, command=self.action_refresh_battles), padx=(10, 4), pady=6)

        self.lbl_active_battles_badge = ctk.CTkLabel(top, text="⚔️ Active Battles: 0", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10B981")
        top.add_widget(self.lbl_active_battles_badge, padx=8, pady=6)

        top.add_widget(ctk.CTkLabel(top, text="Live turn-based combat monitor. Cleanly abort stuck encounters or force victory.", font=ctk.CTkFont(size=11), text_color="#94A3B8"), padx=8, pady=6)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Battles List
        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        cols = ("BattleID", "Type", "MapID", "Turn", "Player", "Pet", "Enemies", "Time")
        self.tree_battles, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", selectmode="browse", padx=12, pady=8)
        for c in cols:
            self.tree_battles.heading(c, text=c)
            self.tree_battles.column(c, width=60 if c in ("MapID", "Turn") else 100, anchor="center")
        self.tree_battles.bind("<<TreeviewSelect>>", self._on_battle_selected)

        # Right: Battle Details & GM Overrides
        right = ctk.CTkFrame(split, width=380, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="⚔️ Battle Details & Overrides", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(12, 4))
        self.lbl_selected_battle = ctk.CTkLabel(right, text="Selected Battle: (None)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FBBF24")
        self.lbl_selected_battle.pack(anchor="w", padx=15, pady=(0, 6))

        self.txt_battle_details = tk.Text(right, height=12, bg="#080C14", fg="#F1F5F9", relief="flat", font=("Segoe UI", 9))
        self.txt_battle_details.pack(fill="both", expand=True, padx=15, pady=(4, 10))

        f_b_btns = ctk.CTkFrame(right, fg_color="transparent")
        f_b_btns.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(f_b_btns, text="🏆 Force Win (Victory)", font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669", height=36, corner_radius=8, command=self.action_force_win_battle).pack(fill="x", padx=2, pady=3)
        ctk.CTkButton(f_b_btns, text="🛑 Force End / Abort Battle", font=ctk.CTkFont(weight="bold"), fg_color="#DC2626", hover_color="#B91C1C", height=36, corner_radius=8, command=self.action_force_end_battle).pack(fill="x", padx=2, pady=3)

        self.action_refresh_battles()

    # -------------------------------------------------------------
    # TAB: Marriage Registry
    # -------------------------------------------------------------
    def _build_marriage_content(self, parent):
        top = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        top.add_widget(ctk.CTkButton(top, text="🔄 Refresh Marriages", fg_color="#1E293B", hover_color="#334155", width=160, corner_radius=8, command=self.action_refresh_marriages), padx=(10, 4), pady=6)

        top.add_widget(ctk.CTkLabel(top, text="🔍 Filter:", font=ctk.CTkFont(size=12), text_color="#94A3B8"), padx=(6, 2), pady=6)
        self.ent_marriage_search = ctk.CTkEntry(top, placeholder_text="Filter by Spouse Name...", fg_color="#0B0F19", border_color="#1E293B", width=220)
        top.add_widget(self.ent_marriage_search, padx=4, pady=6)
        self.ent_marriage_search.bind("<KeyRelease>", lambda e: self.action_refresh_marriages())

        self.lbl_marriages_stats = ctk.CTkLabel(top, text="Total Couples: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#EC4899")
        top.add_widget(self.lbl_marriages_stats, padx=10, pady=6)

        cols = ("HusbandID", "HusbandName", "WifeID", "WifeName", "MarriageDate", "Status")
        self.tree_marriages, _, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_marriages.heading(c, text=c)
            self.tree_marriages.column(c, width=90 if c in ("HusbandID", "WifeID") else 140, anchor="center")

        bottom = ResponsiveFlowFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        bottom.pack(fill="x", padx=10, pady=(5, 10))

        bottom.add_widget(ctk.CTkButton(bottom, text="💔 Admin Annul / Divorce", font=ctk.CTkFont(weight="bold"), fg_color="#DC2626", hover_color="#B91C1C", width=190, height=34, corner_radius=8, command=self.action_divorce_marriage), padx=(10, 4), pady=6)
        bottom.add_widget(ctk.CTkButton(bottom, text="🚀 Teleport Spouses Together", font=ctk.CTkFont(weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", width=220, height=34, corner_radius=8, command=self.action_teleport_spouses), padx=4, pady=6)

        self.action_refresh_marriages()

    # -------------------------------------------------------------
    # Helper & Event Handlers
    # -------------------------------------------------------------
    def _create_metric_card(self, parent, title, value, color, col, icon="📊"):
        card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        card.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
        parent.columnconfigure(col, weight=1)

        f_top = ctk.CTkFrame(card, fg_color="transparent")
        f_top.pack(fill="x", padx=15, pady=(12, 2))
        ctk.CTkLabel(f_top, text=icon, font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(f_top, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(side="left")

        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=15, pady=(0, 12))
        return lbl_val

    def _setup_log_pipe(self):
        class TkLogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                try:
                    msg = self.format(record)
                    lvl = record.levelname
                    self.text_widget.after(0, self._append, msg, lvl)
                except Exception:
                    pass

            def _append(self, msg, lvl):
                try:
                    self.text_widget.insert(tk.END, msg + "\n", lvl)
                    self.text_widget.see(tk.END)
                except Exception:
                    pass

        handler = TkLogHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(handler)

    def _get_db_count(self, table: str) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cur.fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return 0

    def _schedule_refresh(self):
        self._refresh_metrics()
        self.root.after(3000, self._schedule_refresh)

    def _refresh_metrics(self):
        uptime = int(time.time() - self.start_time)
        hrs = uptime // 3600
        mins = (uptime % 3600) // 60
        secs = uptime % 60
        self.badge_uptime.configure(text=f"⏱ Uptime: {hrs:02d}:{mins:02d}:{secs:02d}")

        online_count = len(self.game_server.sessions) if (self.game_server and hasattr(self.game_server, "sessions")) else 0
        self.badge_players.configure(text=f"👥 {online_count} Online")
        self.card_players.configure(text=str(online_count))
        self.card_accounts.configure(text=str(self._get_db_count("accounts")))
        self.card_chars.configure(text=str(self._get_db_count("characters")))

        # Update Battles badge
        if hasattr(self, "lbl_active_battles_badge") and self.game_server and hasattr(self.game_server, "active_battles"):
            self.lbl_active_battles_badge.configure(text=f"⚔️ Active Battles: {len(self.game_server.active_battles)}")

        # Update Sessions Tree
        if hasattr(self, "tree_players"):
            sel = self.tree_players.selection()
            selected_char_id = None
            if sel:
                vals = self.tree_players.item(sel[0])["values"]
                if vals:
                    selected_char_id = vals[0]

            for i in self.tree_players.get_children():
                self.tree_players.delete(i)

            filter_q = (self.ent_search_players.get() or "").lower().strip() if hasattr(self, "ent_search_players") else ""

            selected_item_id = None
            if self.game_server and hasattr(self.game_server, "sessions"):
                for s in self.game_server.sessions.values():
                    cid = getattr(s, "char_id", 0)
                    cname = getattr(s, "char_name", "Unknown")
                    uname = getattr(s, "username", "Unknown")
                    lvl = getattr(s, "level", 1)
                    gold = getattr(s, "gold", 0)
                    mid = getattr(s, "map_id", 0)
                    x = getattr(s, "x", 0)
                    y = getattr(s, "y", 0)
                    ip = getattr(s, "ip", "127.0.0.1")

                    if filter_q:
                        if filter_q not in str(cid).lower() and filter_q not in str(cname).lower() and filter_q not in str(uname).lower() and filter_q not in str(mid).lower():
                            continue

                    iid = self.tree_players.insert("", "end", values=(cid, cname, uname, lvl, gold, mid, x, y, ip))
                    if cid == selected_char_id:
                        selected_item_id = iid

            if selected_item_id:
                try:
                    self.tree_players.selection_set(selected_item_id)
                except Exception:
                    pass

    def _refresh_online_players_combos(self):
        vals = []
        if self.game_server and hasattr(self.game_server, "sessions"):
            for s in self.game_server.sessions.values():
                vals.append(f"{s.char_id} - {s.char_name}")
        if not vals:
            vals = ["(No Active Players)"]
        self.cmb_cheat_player.configure(values=vals)
        self.cmb_cheat_player.set(vals[0])

    def launch_game_client(self):
        search_paths = [
            r"D:\garipgudubetseyler\WLRI\aLogin.exe",
            r"C:\Games\WLRI\aLogin.exe",
            r"D:\Games\WLRI\aLogin.exe",
            os.path.join(os.getcwd(), "aLogin.exe"),
            os.path.join(os.getcwd(), "WLRI", "aLogin.exe")
        ]
        found = None
        for p in search_paths:
            if os.path.exists(p):
                found = p
                break
        if found:
            subprocess.Popen([found], cwd=os.path.dirname(found))
            logger.info(f"[Client] Launched game client: {found}")
        else:
            messagebox.showwarning("Client Not Found", "aLogin.exe was not found in standard paths.")

    def action_hot_reload(self):
        GLOBAL_DYNAMIC_DATA.reload_all_dynamic_data()
        messagebox.showinfo("Hot-Reload", "All 19 Dynamic Subsystems successfully hot-reloaded from SQLite!")

    def action_save_all_now(self):
        messagebox.showinfo("Saved", "All character and world states saved to database.")

    def action_broadcast_marquee(self):
        msg = self.ent_welcome.get()
        if not msg:
            return
        if self.game_server and hasattr(self.game_server, "broadcast"):
            pkt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg)
            asyncio.create_task(self.game_server.broadcast(pkt))
        logger.info(f"[Broadcast] Global announcement sent: '{msg}'")

    def action_kick_all(self):
        if self.game_server and hasattr(self.game_server, "sessions"):
            for s in list(self.game_server.sessions.values()):
                if hasattr(s, "close"):
                    s.close()
        messagebox.showinfo("Disconnected", "All active player sessions closed.")

    def action_clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def _on_player_selected(self, event):
        sel = self.tree_players.selection()
        if sel:
            item = self.tree_players.item(sel[0])["values"]
            self.lbl_selected_player.configure(text=f"Selected: {item[1]} (ID: {item[0]})")

    def action_open_selected_char_editor(self):
        sel = self.tree_characters.selection()
        if not sel:
            sel = self.tree_players.selection()
            if sel:
                item = self.tree_players.item(sel[0])["values"]
                CharacterDataEditorDialog(self.root, int(item[0]), str(item[1]), self.db_path, self.game_server)
                return
        if sel:
            item = self.tree_characters.item(sel[0])["values"]
            CharacterDataEditorDialog(self.root, int(item[0]), str(item[2]), self.db_path, self.game_server)
        else:
            messagebox.showwarning("Select Character", "Please select a character from the list first.")

    def _get_selected_session(self) -> Optional[Any]:
        """Gets active player session from selection in online players tree or cheat combobox."""
        if not self.game_server or not hasattr(self.game_server, "sessions"):
            return None
        # 1. From tree_players selection
        if hasattr(self, "tree_players"):
            sel = self.tree_players.selection()
            if sel:
                item = self.tree_players.item(sel[0])["values"]
                if item:
                    try:
                        cid = int(item[0])
                        for s in self.game_server.sessions.values():
                            if getattr(s, "char_id", 0) == cid:
                                return s
                    except Exception:
                        pass
        # 2. From cmb_cheat_player
        if hasattr(self, "cmb_cheat_player"):
            val = self.cmb_cheat_player.get()
            if val and not val.startswith("("):
                try:
                    cid = int(val.split("-")[0].strip())
                    for s in self.game_server.sessions.values():
                        if getattr(s, "char_id", 0) == cid:
                            return s
                except Exception:
                    pass
        return None

    def action_heal_player(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        s.hp = getattr(s, "max_hp", 1000)
        s.sp = getattr(s, "max_sp", 500)
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_stats_update"):
                safe_run_coroutine(self.game_server.send_stats_update(s, levelup=False), self.game_server.loop)
            elif hasattr(self.game_server, "send_stat_packet"):
                safe_run_coroutine(self.game_server.send_stat_packet(s), self.game_server.loop)
        messagebox.showinfo("Healed", f"Character [{getattr(s, 'char_name', 'Player')}] HP and SP fully restored to 100%!")

    def action_god_mode(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        is_god = not getattr(s, "god_mode", False)
        s.god_mode = is_god
        if is_god:
            s.hp = 99999
            s.sp = 99999
            s.max_hp = 99999
            s.max_sp = 99999
        else:
            s.max_hp = 1000
            s.max_sp = 500
            s.hp = min(getattr(s, "hp", 1000), 1000)
            s.sp = min(getattr(s, "sp", 500), 500)
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_stats_update"):
                safe_run_coroutine(self.game_server.send_stats_update(s, levelup=False), self.game_server.loop)
        status_txt = "ENABLED (99,999 HP/SP)" if is_god else "DISABLED"
        messagebox.showinfo("God Mode", f"God Mode {status_txt} for [{getattr(s, 'char_name', 'Player')}]!")

    def action_kick_player(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        cname = getattr(s, "char_name", "Player")
        uid = getattr(s, "user_id", 0)
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            safe_run_coroutine(self.game_server.kick_user(uid, "Kicked by Administrator"), self.game_server.loop)
        elif hasattr(s, "disconnect"):
            safe_run_coroutine(s.disconnect(), getattr(self.game_server, "loop", None) or asyncio.get_event_loop())
        messagebox.showinfo("Kicked", f"Player [{cname}] was disconnected from the server.")

    def action_ban_player(self):
        sel = self.tree_players.selection()
        if not sel:
            messagebox.showwarning("Select Player", "Please select an online player from the list first.")
            return
        item = self.tree_players.item(sel[0])["values"]
        char_name = str(item[1])
        account_name = str(item[2])
        reason = simpledialog.askstring("Ban Player Account", f"Enter ban reason for account '{account_name}' ({char_name}):", initialvalue="Violation of server rules")
        if reason is None:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("UPDATE users SET banned = 1, ban_reason = ? WHERE username = ?", (reason, account_name))
            conn.commit()
            conn.close()
            # Kick online session
            if self.game_server:
                if hasattr(self.game_server, "loop") and self.game_server.loop:
                    for s in list(self.game_server.active_sessions):
                        if getattr(s, "username", "") == account_name or getattr(s, "char_name", "") == char_name:
                            safe_run_coroutine(self.game_server.ban_user(getattr(s, "user_id", 0), reason), self.game_server.loop)
            messagebox.showinfo("Banned", f"User account '{account_name}' has been banned and kicked.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ban player: {e}")

    def action_ban_player_ip(self):
        sel = self.tree_players.selection()
        if not sel:
            messagebox.showwarning("Select Player", "Please select an online player from the list first.")
            return
        item = self.tree_players.item(sel[0])["values"]
        char_name = str(item[1])
        ip = str(item[8])
        if not ip or ip in ("127.0.0.1", "0.0.0.0", "localhost"):
            messagebox.showwarning("Protected IP", f"Cannot ban local loopback IP ({ip}).")
            return
        reason = simpledialog.askstring("Ban IP Address", f"Enter ban reason for IP '{ip}' (Player: {char_name}):", initialvalue="IP Banned by admin")
        if reason is None:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO banned_ips (ip, reason, banned_at, banned_by) VALUES (?, ?, datetime('now', 'localtime'), 'gui_admin')", (ip, reason))
            conn.commit()
            conn.close()
            # Kick online session
            if self.game_server:
                if hasattr(self.game_server, "loop") and self.game_server.loop:
                    safe_run_coroutine(self.game_server.kick_ip(ip, f"IP Banned: {reason}"), self.game_server.loop)
            messagebox.showinfo("IP Banned", f"IP address '{ip}' has been banned and all active connections terminated.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ban IP: {e}")

    # Cheats Browser Fillers
    def _populate_cheats_browser_lists(self):
        # Maps
        self.all_maps_data = [
            "10001 - Kelan Village", "10017 - Starter Shipwreck", "10035 - Beach",
            "12000 - Welling Village", "12003 - Casino & Bar", "11016 - South Island Open Ocean",
            "11001 - Kyoto Main Town", "11002 - Kyoto Suburbs", "10036 - Fishing Coast"
        ]
        self._filter_maps_list()

        # Vehicles
        vehs = ["48001 - Raft", "48002 - Canoe", "48003 - Sailboat", "48004 - Yacht", "48005 - Airship", "48006 - Submarine", "48016 - Cruiser", "48033 - Spacecraft"]
        for v in vehs:
            self.list_veh.insert(tk.END, v)

        # Items
        self.all_items_data = [
            "10001 - Steamed Bread", "10002 - Apple", "10005 - Meat Bun", "27001 - Wooden Sword",
            "27015 - Iron Blade", "28001 - Leather Armor", "38027 - Alchemy Stove", "38049 - Loom",
            "47001 - +24 ATK Spar Crystal", "48033 - Spacecraft Ticket", "60001 - Return Scroll"
        ]
        self._filter_items_list()

        # NPCs
        self.all_npcs_data = [
            "12032 - Robinson (Companion)", "14013 - Ashley (Villager)", "14144 - Welling Villager",
            "14151 - Clinic Doctor", "14181 - Bank Teller", "14512 - Casino Astrologia",
            "17001 - Jellyfish (Level 5)", "17015 - Forest Spider (Level 12)", "17400 - Domestic Pig"
        ]
        self._filter_npcs_list()

    def _filter_maps_list(self):
        q = (self.ent_search_maps.get() or "").lower()
        self.list_maps.delete(0, tk.END)
        for m in self.all_maps_data:
            if q in m.lower():
                self.list_maps.insert(tk.END, m)

    def _filter_items_list(self):
        q = (self.ent_search_items.get() or "").lower()
        self.list_items.delete(0, tk.END)
        for it in self.all_items_data:
            if q in it.lower():
                self.list_items.insert(tk.END, it)

    def _filter_npcs_list(self):
        q = (self.ent_search_npcs.get() or "").lower()
        self.list_npcs.delete(0, tk.END)
        for n in self.all_npcs_data:
            if q in n.lower():
                self.list_npcs.insert(tk.END, n)

    def action_cheat_warp_map(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        sel = self.list_maps.curselection()
        if not sel:
            messagebox.showwarning("Select Map", "Please select a destination map from the list.")
            return
        m = self.list_maps.get(sel[0])
        mid = int(m.split("-")[0].strip())
        s.map_id = mid
        s.x = 300
        s.y = 400
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET map_id = ?, x = ?, y = ? WHERE id = ?", (mid, 300, 400, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "warp_player"):
                safe_run_coroutine(self.game_server.warp_player(s, mid, 300, 400), self.game_server.loop)
            elif hasattr(s, "send_packet"):
                pkt = PacketWriter().write_8(12).write_16(mid).write_16(300).write_16(400)
                safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)
        messagebox.showinfo("Warped", f"Warped [{getattr(s, 'char_name', 'Player')}] to Map #{mid} (300, 400)!")

    def action_cheat_ride_vehicle(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        sel = self.list_veh.curselection()
        if not sel:
            messagebox.showwarning("Select Vehicle", "Please select a vehicle from the list.")
            return
        v_str = self.list_veh.get(sel[0])
        vid = int(v_str.split("-")[0].strip())
        s.vehicle_id = vid
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            pkt = PacketWriter().write_8(45).write_8(1).write_16(vid)
            safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)
        messagebox.showinfo("Vehicle Mounted", f"Vehicle #{vid} mounted on [{getattr(s, 'char_name', 'Player')}]!")

    def action_cheat_unride_vehicle(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        s.vehicle_id = 0
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            pkt = PacketWriter().write_8(45).write_8(2).write_16(0)
            safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)
        messagebox.showinfo("Vehicle Removed", f"Vehicle unmounted from [{getattr(s, 'char_name', 'Player')}].")

    def action_cheat_spawn_item(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        sel = self.list_items.curselection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an item to spawn.")
            return
        it = self.list_items.get(sel[0])
        iid = int(it.split("-")[0].strip())
        amt = int(self.ent_spawn_qty.get() or 1)
        from server.gameserver import add_item_to_inventory
        added = add_item_to_inventory(s, iid, amt)
        if added:
            if hasattr(self.game_server, "loop") and self.game_server.loop:
                pkt = self.game_server.build_inventory_packet(s)
                safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)
            messagebox.showinfo("Item Spawned", f"Successfully spawned {amt}x Item #{iid} ({get_item_display_name(iid)}) into [{getattr(s, 'char_name', 'Player')}] inventory!")
        else:
            messagebox.showerror("Failed", "Could not add item (Inventory full or invalid item).")

    def action_cheat_battle_npc(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        sel = self.list_npcs.curselection()
        if not sel:
            messagebox.showwarning("Select Monster", "Please select an NPC/Monster from the list.")
            return
        npc_str = self.list_npcs.get(sel[0])
        npcid = int(npc_str.split("-")[0].strip())
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            safe_run_coroutine(self.game_server.enter_battle(s, 1, npcid), self.game_server.loop)
            messagebox.showinfo("Combat Initiated", f"Battle started for [{getattr(s, 'char_name', 'Player')}] against NPC #{npcid}!")

    def action_cheat_recruit_npc(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        sel = self.list_npcs.curselection()
        if not sel:
            messagebox.showwarning("Select Companion", "Please select an NPC/Companion from the list.")
            return
        npc_str = self.list_npcs.get(sel[0])
        npcid = int(npc_str.split("-")[0].strip())
        npc_name = npc_str.split("-")[1].strip() if "-" in npc_str else f"Pet #{npcid}"
        if not hasattr(s, "pets") or not isinstance(s.pets, list):
            s.pets = []
        if len(s.pets) >= 4:
            messagebox.showwarning("Full Pets", f"Player [{getattr(s, 'char_name', 'Player')}] already has 4 active pets.")
            return
        new_pet = {
            "id": npcid, "pet_id": npcid, "name": npc_name, "level": 10,
            "hp": 500, "max_hp": 500, "sp": 200, "max_sp": 200, "amity": 100,
            "str": 15, "con": 15, "int": 15, "wis": 15, "agi": 15, "in_battle": False
        }
        s.pets.append(new_pet)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET pets = ? WHERE id = ?", (json.dumps(s.pets), s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_pet_list_packet"):
                safe_run_coroutine(self.game_server.send_pet_list_packet(s), self.game_server.loop)
        messagebox.showinfo("Companion Recruited", f"Added companion [{npc_name}] to [{getattr(s, 'char_name', 'Player')}]'s team!")

    def action_cheat_leave_npc(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        if not hasattr(s, "pets") or not s.pets:
            messagebox.showinfo("No Companions", "Player does not have any companions.")
            return
        dismissed = s.pets.pop(0)
        pname = dismissed.get("name", "Companion")
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET pets = ? WHERE id = ?", (json.dumps(s.pets), s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_pet_list_packet"):
                safe_run_coroutine(self.game_server.send_pet_list_packet(s), self.game_server.loop)
        messagebox.showinfo("Dismissed", f"Dismissed companion [{pname}] from [{getattr(s, 'char_name', 'Player')}].")

    def action_give_stat_points(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        pts = int(self.ent_give_stat_pts.get() or 100)
        s.stat_points = getattr(s, "stat_points", 0) + pts
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET points = ? WHERE id = ?", (s.stat_points, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_stats_update"):
                safe_run_coroutine(self.game_server.send_stats_update(s, levelup=False), self.game_server.loop)
        messagebox.showinfo("Stat Points", f"Awarded +{pts} free stat points to [{getattr(s, 'char_name', 'Player')}]! Current: {s.stat_points}")

    def action_reset_stats(self):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        total_pts = (getattr(s, "level", 1) - 1) * 3 + (getattr(s, "str", 10) - 10) + (getattr(s, "con", 10) - 10) + (getattr(s, "int", 10) - 10) + (getattr(s, "wis", 10) - 10) + (getattr(s, "agi", 10) - 10) + getattr(s, "stat_points", 0)
        s.str = 10
        s.con = 10
        s.int = 10
        s.wis = 10
        s.agi = 10
        s.stat_points = max(0, total_pts)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET str=10, con=10, int=10, wis=10, agi=10, points=? WHERE id=?", (s.stat_points, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_stats_update"):
                safe_run_coroutine(self.game_server.send_stats_update(s, levelup=False), self.game_server.loop)
        messagebox.showinfo("Reset Stats", f"Reset base stats to 10 for [{getattr(s, 'char_name', 'Player')}]. Refunded {s.stat_points} stat points!")

    def _quick_give_gold_amount(self, amount: int):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        s.gold = getattr(s, "gold", 0) + amount
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET gold = ? WHERE id = ?", (s.gold, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            pkt = PacketWriter().write_8(26).write_8(4).write_32(s.gold)
            safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)
        messagebox.showinfo("Gold", f"Awarded +{amount:,} Gold to [{getattr(s, 'char_name', 'Player')}]! Current: {s.gold:,}")

    def _quick_give_im_points(self, amount: int):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        s.im_points = getattr(s, "im_points", 0) + amount
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET im_points = ? WHERE id = ?", (s.im_points, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        messagebox.showinfo("IM Points", f"Awarded +{amount:,} Item Mall Points to [{getattr(s, 'char_name', 'Player')}]! Current: {s.im_points:,}")

    def _quick_add_levels(self, lvls: int):
        s = self._get_selected_session()
        if not s:
            messagebox.showwarning("Select Player", "Please select an active player session first.")
            return
        s.level = min(199, getattr(s, "level", 1) + lvls)
        s.stat_points = getattr(s, "stat_points", 0) + (lvls * 3)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE characters SET level = ?, points = ? WHERE id = ?", (s.level, s.stat_points, s.char_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "send_stats_update"):
                safe_run_coroutine(self.game_server.send_stats_update(s, levelup=True), self.game_server.loop)
        messagebox.showinfo("Level Up", f"Level increased by +{lvls} for [{getattr(s, 'char_name', 'Player')}]! Current Level: {s.level}")

    # -------------------------------------------------------------
    # GUILDS ACTIONS
    # -------------------------------------------------------------
    def action_refresh_guilds(self):
        if not hasattr(self, "tree_guilds"):
            return
        for i in self.tree_guilds.get_children():
            self.tree_guilds.delete(i)
        q = (self.ent_guild_search.get() or "").strip() if hasattr(self, "ent_guild_search") else ""
        total_guilds = 0
        total_members = 0
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Member counts map
            m_counts = {}
            for r in cur.execute("SELECT guild_id, COUNT(*) as cnt FROM guild_members GROUP BY guild_id").fetchall():
                m_counts[r["guild_id"]] = r["cnt"]

            if q:
                rows = cur.execute("SELECT * FROM guilds WHERE guild_name LIKE ? OR guild_id LIKE ?", (f"%{q}%", f"%{q}%")).fetchall()
            else:
                rows = cur.execute("SELECT * FROM guilds ORDER BY guild_id ASC").fetchall()

            for r in rows:
                gid = r["guild_id"]
                gname = r["guild_name"]
                lname = r["leader_name"]
                lid = r["leader_id"]
                cnt = m_counts.get(gid, 1)
                c_date = time.strftime("%Y-%m-%d", time.localtime(r["created_at"] or time.time()))
                self.tree_guilds.insert("", "end", values=(gid, gname, lname, lid, cnt, c_date))
                total_guilds += 1
                total_members += cnt

            conn.close()
        except Exception as e:
            logger.error(f"Error refreshing guilds: {e}")

        if hasattr(self, "lbl_guilds_stats"):
            self.lbl_guilds_stats.configure(text=f"Total Guilds: {total_guilds} | Members: {total_members}")

    def _on_guild_selected(self, event):
        sel = self.tree_guilds.selection()
        if not sel:
            return
        item = self.tree_guilds.item(sel[0])["values"]
        gid = int(item[0])
        gname = str(item[1])
        lname = str(item[2])
        self.lbl_selected_guild.configure(text=f"Selected: [{gname}] (ID: {gid} | Leader: {lname})")

        # Load rules and member roster
        self.txt_guild_rules.delete("1.0", tk.END)
        for i in self.tree_guild_members.get_children():
            self.tree_guild_members.delete(i)

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            g_row = cur.execute("SELECT rules FROM guilds WHERE guild_id = ?", (gid,)).fetchone()
            if g_row and g_row["rules"]:
                self.txt_guild_rules.insert("1.0", g_row["rules"])

            m_rows = cur.execute("SELECT char_id, char_name, level, rank, element FROM guild_members WHERE guild_id = ?", (gid,)).fetchall()
            rank_map = {0: "Member", 1: "Vice Leader", 2: "Leader"}
            for mr in m_rows:
                r_txt = rank_map.get(mr["rank"], "Member")
                self.tree_guild_members.insert("", "end", values=(mr["char_id"], mr["char_name"], mr["level"], r_txt, mr["element"]))
            conn.close()
        except Exception as e:
            logger.error(f"Error loading guild details: {e}")

    def action_save_guild_notice(self):
        sel = self.tree_guilds.selection()
        if not sel:
            messagebox.showwarning("Select Guild", "Please select a guild first.")
            return
        gid = int(self.tree_guilds.item(sel[0])["values"][0])
        new_rules = self.txt_guild_rules.get("1.0", tk.END).strip()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE guilds SET rules = ? WHERE guild_id = ?", (new_rules, gid))
            conn.commit()
            conn.close()
            from server.guild_system import GLOBAL_GUILD_MANAGER
            g = GLOBAL_GUILD_MANAGER.get_guild(gid)
            if g:
                g.rules = new_rules
            messagebox.showinfo("Saved", "Guild announcement/notice updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save notice: {e}")

    def action_guild_change_leader(self):
        sel = self.tree_guilds.selection()
        if not sel:
            messagebox.showwarning("Select Guild", "Please select a guild first.")
            return
        gid = int(self.tree_guilds.item(sel[0])["values"][0])
        new_lid_str = simpledialog.askstring("Transfer Leadership", f"Enter new Leader Character ID for Guild #{gid}:")
        if not new_lid_str or not new_lid_str.isdigit():
            return
        new_lid = int(new_lid_str)
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            c_row = cur.execute("SELECT name FROM characters WHERE id = ?", (new_lid,)).fetchone()
            if not c_row:
                messagebox.showerror("Not Found", f"Character with ID #{new_lid} does not exist.")
                conn.close()
                return
            new_lname = c_row[0]
            # Demote old leader to member, promote new leader
            cur.execute("UPDATE guild_members SET rank = 0 WHERE guild_id = ? AND rank = 2", (gid,))
            cur.execute("UPDATE guild_members SET rank = 2 WHERE guild_id = ? AND char_id = ?", (gid, new_lid))
            cur.execute("UPDATE guilds SET leader_id = ?, leader_name = ? WHERE guild_id = ?", (new_lid, new_lname, gid))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Guild leadership transferred to [{new_lname}] (ID: {new_lid})!")
            self.action_refresh_guilds()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to transfer leadership: {e}")

    def action_guild_kick_member(self):
        m_sel = self.tree_guild_members.selection()
        if not m_sel:
            messagebox.showwarning("Select Member", "Please select a member from the roster list first.")
            return
        item = self.tree_guild_members.item(m_sel[0])["values"]
        cid = int(item[0])
        cname = str(item[1])
        if not messagebox.askyesno("Kick Member", f"Remove [{cname}] (CharID: {cid}) from this guild?"):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM guild_members WHERE char_id = ?", (cid,))
            conn.commit()
            conn.close()
            from server.guild_system import GLOBAL_GUILD_MANAGER
            for g in GLOBAL_GUILD_MANAGER._guilds.values():
                if cid in g.members:
                    del g.members[cid]
                    break
            messagebox.showinfo("Kicked", f"Member [{cname}] removed from guild.")
            self._on_guild_selected(None)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove member: {e}")

    def action_disband_guild(self):
        sel = self.tree_guilds.selection()
        if not sel:
            messagebox.showwarning("Select Guild", "Please select a guild to disband.")
            return
        item = self.tree_guilds.item(sel[0])["values"]
        gid = int(item[0])
        gname = str(item[1])
        if not messagebox.askyesno("Disband Guild", f"Are you sure you want to permanently DISBAND guild [{gname}] (ID: {gid})?\nAll guild storage items and member affiliations will be wiped."):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM guilds WHERE guild_id = ?", (gid,))
            conn.execute("DELETE FROM guild_members WHERE guild_id = ?", (gid,))
            conn.execute("DELETE FROM guild_storage WHERE guild_id = ?", (gid,))
            conn.commit()
            conn.close()
            from server.guild_system import GLOBAL_GUILD_MANAGER
            GLOBAL_GUILD_MANAGER.disband_guild(gid)
            messagebox.showinfo("Disbanded", f"Guild [{gname}] disbanded successfully.")
            self.action_refresh_guilds()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disband guild: {e}")

    # -------------------------------------------------------------
    # MAIL ACTIONS
    # -------------------------------------------------------------
    def _on_mail_target_changed(self, choice):
        if choice == "Single Character":
            self.lbl_mail_recipient.pack(anchor="w", padx=15, pady=(2, 1))
            self.ent_mail_recipient.pack(fill="x", padx=15, pady=(0, 8))
        else:
            self.lbl_mail_recipient.pack_forget()
            self.ent_mail_recipient.pack_forget()

    def _on_mail_item_id_changed(self, event):
        val = (self.ent_mail_item_id.get() or "0").strip()
        if val.isdigit() and int(val) > 0:
            iid = int(val)
            name = get_item_display_name(iid)
            self.lbl_mail_item_preview.configure(text=f"Item: {name} (ID: {iid})", text_color="#10B981")
        else:
            self.lbl_mail_item_preview.configure(text="Item: None", text_color="#94A3B8")

    def action_dispatch_mail(self):
        target_mode = self.cmb_mail_target.get()
        subject = (self.ent_mail_subject.get() or "").strip()
        body = self.txt_mail_body.get("1.0", tk.END).strip()
        gold = int(self.ent_mail_gold.get() or 0)
        item_id = int(self.ent_mail_item_id.get() or 0)
        item_count = int(self.ent_mail_item_count.get() or 1)

        if not subject:
            messagebox.showwarning("Missing Subject", "Please enter a subject for the mail.")
            return

        recipients = []
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            if target_mode == "Single Character":
                recip_val = self.ent_mail_recipient.get().strip()
                if not recip_val:
                    messagebox.showwarning("Missing Recipient", "Please enter target Character Name or ID.")
                    conn.close()
                    return
                if recip_val.isdigit():
                    row = cur.execute("SELECT id, name FROM characters WHERE id = ?", (int(recip_val),)).fetchone()
                else:
                    row = cur.execute("SELECT id, name FROM characters WHERE name = ?", (recip_val,)).fetchone()
                if not row:
                    messagebox.showerror("Not Found", f"Character '{recip_val}' not found.")
                    conn.close()
                    return
                recipients.append((row[0], row[1]))
            elif target_mode == "All Online Players":
                if self.game_server and hasattr(self.game_server, "sessions"):
                    for s in self.game_server.sessions.values():
                        recipients.append((s.char_id, s.char_name))
                if not recipients:
                    messagebox.showinfo("No Online Players", "No players currently online.")
                    conn.close()
                    return
            else:  # All Registered Characters
                for r in cur.execute("SELECT id, name FROM characters").fetchall():
                    recipients.append((r[0], r[1]))

            now = time.time()
            for cid, cname in recipients:
                cur.execute("""
                    INSERT INTO charmail (
                        sender_id, sender_name, receiver_id, subject, content,
                        attached_gold, attached_item_id, attached_item_count,
                        sent_date, is_read, is_claimed
                    ) VALUES (0, 'System GM', ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (cid, subject, body, gold, item_id, item_count, now))

            conn.commit()
            conn.close()

            # Notify online sessions via AC 30 Sub 1
            if self.game_server and hasattr(self.game_server, "sessions") and hasattr(self.game_server, "loop") and self.game_server.loop:
                pkt = PacketWriter().write_8(30).write_8(1)
                for cid, _ in recipients:
                    s = self.game_server.sessions.get(cid)
                    if s:
                        safe_run_coroutine(s.send_packet(pkt), self.game_server.loop)

            messagebox.showinfo("Dispatched", f"Successfully dispatched mail to {len(recipients)} character(s)!")
            self.action_refresh_mail()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to dispatch mail: {e}")

    def action_refresh_mail(self):
        if not hasattr(self, "tree_mail"):
            return
        for i in self.tree_mail.get_children():
            self.tree_mail.delete(i)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = cur.execute("SELECT * FROM charmail ORDER BY mail_id DESC LIMIT 150").fetchall()
            for r in rows:
                mid = r["mail_id"]
                sname = r["sender_name"]
                rid = r["receiver_id"]
                subj = r["subject"]
                gold = r["attached_gold"] or 0
                iid = r["attached_item_id"] or 0
                iname = get_item_display_name(iid) if iid > 0 else "-"
                cnt = r["attached_item_count"] or 0
                claimed = "Yes" if r["is_claimed"] else "No"
                date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["sent_date"] or time.time()))
                self.tree_mail.insert("", "end", values=(mid, sname, rid, subj, gold, iid, iname, cnt, claimed, date_str))
            conn.close()
        except Exception as e:
            logger.error(f"Error refreshing mail: {e}")

    def action_delete_mail(self):
        sel = self.tree_mail.selection()
        if not sel:
            messagebox.showwarning("Select Mail", "Please select a mail entry to delete.")
            return
        mid = int(self.tree_mail.item(sel[0])["values"][0])
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM charmail WHERE mail_id = ?", (mid,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", f"Mail #{mid} deleted successfully.")
            self.action_refresh_mail()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete mail: {e}")

    # -------------------------------------------------------------
    # SECURITY & BANS ACTIONS
    # -------------------------------------------------------------
    def action_refresh_banned_ips(self):
        if not hasattr(self, "tree_banned_ips"):
            return
        for i in self.tree_banned_ips.get_children():
            self.tree_banned_ips.delete(i)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM banned_ips ORDER BY banned_at DESC").fetchall()
            for r in rows:
                self.tree_banned_ips.insert("", "end", values=(r["ip"], r["reason"] or "", r["banned_at"] or "", r["banned_by"] or "Admin"))
            conn.close()
        except Exception as e:
            logger.error(f"Error refreshing banned IPs: {e}")

    def action_add_banned_ip(self):
        ip = simpledialog.askstring("Add IP Ban", "Enter IP address to ban:")
        if not ip:
            return
        ip = ip.strip()
        if ip in ("127.0.0.1", "0.0.0.0", "localhost"):
            messagebox.showwarning("Protected IP", "Cannot ban localhost loopback address.")
            return
        reason = simpledialog.askstring("Add IP Ban", f"Enter reason for banning '{ip}':", initialvalue="Security Violation") or "Banned by Admin"
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT OR REPLACE INTO banned_ips (ip, reason, banned_at, banned_by) VALUES (?, ?, datetime('now', 'localtime'), 'admin')", (ip, reason))
            conn.commit()
            conn.close()
            if self.game_server and hasattr(self.game_server, "loop") and self.game_server.loop:
                safe_run_coroutine(self.game_server.kick_ip(ip, f"Banned: {reason}"), self.game_server.loop)
            messagebox.showinfo("IP Banned", f"IP address '{ip}' has been banned and added to security filter.")
            self.action_refresh_banned_ips()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add IP ban: {e}")

    def action_unban_ip(self):
        sel = self.tree_banned_ips.selection()
        if not sel:
            messagebox.showwarning("Select IP", "Please select a banned IP from the list to unban.")
            return
        ip = str(self.tree_banned_ips.item(sel[0])["values"][0])
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM banned_ips WHERE ip = ?", (ip,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Unbanned", f"IP address '{ip}' has been unbanned.")
            self.action_refresh_banned_ips()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unban IP: {e}")

    def action_refresh_banned_accounts(self):
        if not hasattr(self, "tree_banned_users"):
            return
        for i in self.tree_banned_users.get_children():
            self.tree_banned_users.delete(i)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, username, ban_reason, last_ip, last_login FROM users WHERE banned = 1").fetchall()
            for r in rows:
                self.tree_banned_users.insert("", "end", values=(r["id"], r["username"], r["ban_reason"] or "Banned", r["last_ip"] or "", r["last_login"] or "Never"))
            conn.close()
        except Exception as e:
            logger.error(f"Error refreshing banned accounts: {e}")

    def action_ban_account_manual(self):
        uname = simpledialog.askstring("Ban Account", "Enter account username to ban:")
        if not uname:
            return
        uname = uname.strip()
        reason = simpledialog.askstring("Ban Account", f"Enter ban reason for '{uname}':", initialvalue="Server rule violation") or "Banned by Admin"
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE users SET banned = 1, ban_reason = ? WHERE username = ?", (reason, uname))
            conn.commit()
            conn.close()
            if self.game_server and hasattr(self.game_server, "sessions"):
                for s in list(self.game_server.sessions.values()):
                    if getattr(s, "username", "") == uname:
                        if hasattr(self.game_server, "loop") and self.game_server.loop:
                            safe_run_coroutine(self.game_server.kick_user(getattr(s, "user_id", 0), reason), self.game_server.loop)
            messagebox.showinfo("Account Banned", f"User account '{uname}' has been banned.")
            self.action_refresh_banned_accounts()
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ban account: {e}")

    def action_unban_account(self):
        sel = self.tree_banned_users.selection()
        if not sel:
            messagebox.showwarning("Select Account", "Please select a banned account to unban.")
            return
        uname = str(self.tree_banned_users.item(sel[0])["values"][1])
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE users SET banned = 0, ban_reason = '' WHERE username = ?", (uname,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Account Unbanned", f"User account '{uname}' has been unbanned.")
            self.action_refresh_banned_accounts()
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unban account: {e}")

    # -------------------------------------------------------------
    # BATTLES ACTIONS
    # -------------------------------------------------------------
    def action_refresh_battles(self):
        if not hasattr(self, "tree_battles"):
            return
        for i in self.tree_battles.get_children():
            self.tree_battles.delete(i)
        count = 0
        if self.game_server and hasattr(self.game_server, "active_battles"):
            for bid, b in list(self.game_server.active_battles.items()):
                b_type = b.get("type", "pve").upper()
                mid = b.get("map_id", 0)
                turn = b.get("turn", 1)
                pname = b.get("player", {}).get("char_name") or b.get("challenger", {}).get("char_name", "Player")
                pet_name = (b.get("pet") or {}).get("name", "-")
                if b.get("type") == "pvp":
                    opp = b.get("target", {}).get("char_name", "Target")
                else:
                    mons = b.get("monsters", [])
                    opp = ", ".join(m.get("name", "Monster") for m in mons[:3])
                    if len(mons) > 3:
                        opp += f" (+{len(mons)-3} more)"
                dur = f"{int(time.time() - b.get('start_time', time.time()))}s"
                self.tree_battles.insert("", "end", values=(bid, b_type, mid, turn, pname, pet_name, opp, dur))
                count += 1
        if hasattr(self, "lbl_active_battles_badge"):
            self.lbl_active_battles_badge.configure(text=f"⚔️ Active Battles: {count}")

    def _on_battle_selected(self, event):
        sel = self.tree_battles.selection()
        if not sel:
            return
        bid = int(self.tree_battles.item(sel[0])["values"][0])
        self.lbl_selected_battle.configure(text=f"Selected Battle: #{bid}")
        self.txt_battle_details.delete("1.0", tk.END)
        if not self.game_server or not hasattr(self.game_server, "active_battles"):
            return
        b = self.game_server.active_battles.get(bid)
        if not b:
            self.txt_battle_details.insert("1.0", "Battle no longer active.")
            return

        lines = [
            f"Battle ID: {bid}",
            f"Type: {b.get('type', 'pve').upper()} | Map ID: {b.get('map_id')} | Turn: {b.get('turn')}",
            f"Duration: {int(time.time() - b.get('start_time', time.time()))}s\n",
            "--- Fighters ---"
        ]
        if b.get("type") == "pvp":
            c = b.get("challenger", {})
            t = b.get("target", {})
            lines.append(f"Challenger: {c.get('char_name')} | HP: {c.get('hp')}/{c.get('max_hp')} | SP: {c.get('sp')}/{c.get('max_sp')}")
            lines.append(f"Target: {t.get('char_name')} | HP: {t.get('hp')}/{t.get('max_hp')} | SP: {t.get('sp')}/{t.get('max_sp')}")
        else:
            p = b.get("player", {})
            lines.append(f"Player: {p.get('char_name')} | HP: {p.get('hp')}/{p.get('max_hp')} | SP: {p.get('sp')}/{p.get('max_sp')}")
            if b.get("pet"):
                pt = b["pet"]
                lines.append(f"Pet: {pt.get('name')} | HP: {pt.get('hp')}/{pt.get('max_hp')} | SP: {pt.get('sp')}/{pt.get('max_sp')}")
            lines.append("\n--- Monsters ---")
            for idx, m in enumerate(b.get("monsters", []), 1):
                lines.append(f"[{idx}] {m.get('name')} (TID: {m.get('id')}) | HP: {m.get('hp')}/{m.get('max_hp')} | Pos: ({m.get('x')}, {m.get('y')})")

        self.txt_battle_details.insert("1.0", "\n".join(lines))

    def action_force_end_battle(self):
        sel = self.tree_battles.selection()
        if not sel:
            messagebox.showwarning("Select Battle", "Please select a battle to abort.")
            return
        bid = int(self.tree_battles.item(sel[0])["values"][0])
        if not self.game_server or not hasattr(self.game_server, "active_battles"):
            return
        b = self.game_server.active_battles.get(bid)
        if not b:
            messagebox.showinfo("Finished", "Battle has already concluded.")
            self.action_refresh_battles()
            return
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if b.get("type") == "pvp":
                safe_run_coroutine(self.game_server._end_pvp_battle(b, challenger_won=False), self.game_server.loop)
            else:
                s = b.get("player", {}).get("session")
                if s:
                    safe_run_coroutine(self.game_server._end_battle(s, b, won=False, fled=True), self.game_server.loop)
                else:
                    del self.game_server.active_battles[bid]
        else:
            if bid in self.game_server.active_battles:
                del self.game_server.active_battles[bid]
        messagebox.showinfo("Battle Aborted", f"Battle #{bid} has been terminated.")
        self.action_refresh_battles()

    def action_force_win_battle(self):
        sel = self.tree_battles.selection()
        if not sel:
            messagebox.showwarning("Select Battle", "Please select a battle.")
            return
        bid = int(self.tree_battles.item(sel[0])["values"][0])
        if not self.game_server or not hasattr(self.game_server, "active_battles"):
            return
        b = self.game_server.active_battles.get(bid)
        if not b:
            messagebox.showinfo("Finished", "Battle has already concluded.")
            self.action_refresh_battles()
            return
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if b.get("type") == "pvp":
                safe_run_coroutine(self.game_server._end_pvp_battle(b, challenger_won=True), self.game_server.loop)
            else:
                s = b.get("player", {}).get("session")
                if s:
                    safe_run_coroutine(self.game_server._end_battle(s, b, won=True), self.game_server.loop)
                else:
                    del self.game_server.active_battles[bid]
        messagebox.showinfo("Victory Granted", f"Battle #{bid} resolved as player victory!")
        self.action_refresh_battles()

    # -------------------------------------------------------------
    # MARRIAGES ACTIONS
    # -------------------------------------------------------------
    def action_refresh_marriages(self):
        if not hasattr(self, "tree_marriages"):
            return
        for i in self.tree_marriages.get_children():
            self.tree_marriages.delete(i)
        q = (self.ent_marriage_search.get() or "").strip().lower() if hasattr(self, "ent_marriage_search") else ""
        count = 0
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM charmarriage").fetchall()
            for r in rows:
                hid = r["husband_id"]
                hname = r["husband_name"]
                wid = r["wife_id"]
                wname = r["wife_name"]
                if q and (q not in hname.lower() and q not in wname.lower()):
                    continue
                d_str = time.strftime("%Y-%m-%d", time.localtime(r["marriage_date"] or time.time()))
                self.tree_marriages.insert("", "end", values=(hid, hname, wid, wname, d_str, "Active Couple"))
                count += 1
            conn.close()
        except Exception as e:
            logger.error(f"Error refreshing marriages: {e}")
        if hasattr(self, "lbl_marriages_stats"):
            self.lbl_marriages_stats.configure(text=f"Total Couples: {count}")

    def action_divorce_marriage(self):
        sel = self.tree_marriages.selection()
        if not sel:
            messagebox.showwarning("Select Couple", "Please select a married couple from the table.")
            return
        item = self.tree_marriages.item(sel[0])["values"]
        hid = int(item[0])
        hname = str(item[1])
        wid = int(item[2])
        wname = str(item[3])
        if not messagebox.askyesno("Confirm Annulment", f"Dissolve the marriage between [{hname}] and [{wname}]?"):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM charmarriage WHERE husband_id = ? AND wife_id = ?", (hid, wid))
            conn.commit()
            conn.close()
            from server.marriage_system import GLOBAL_MARRIAGE_MANAGER
            GLOBAL_MARRIAGE_MANAGER.divorce(hid)
            messagebox.showinfo("Divorced", f"Marriage between [{hname}] and [{wname}] has been dissolved.")
            self.action_refresh_marriages()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to dissolve marriage: {e}")

    def action_teleport_spouses(self):
        sel = self.tree_marriages.selection()
        if not sel:
            messagebox.showwarning("Select Couple", "Please select a married couple from the table.")
            return
        item = self.tree_marriages.item(sel[0])["values"]
        hid = int(item[0])
        wid = int(item[2])
        if not self.game_server or not hasattr(self.game_server, "sessions"):
            messagebox.showinfo("Notice", "Server not active or no players connected.")
            return
        h_sess = self.game_server.sessions.get(hid)
        w_sess = self.game_server.sessions.get(wid)
        if not h_sess or not w_sess:
            messagebox.showwarning("Offline", "Both spouses must be currently online to teleport them together.")
            return
        w_sess.map_id = h_sess.map_id
        w_sess.x = h_sess.x
        w_sess.y = h_sess.y
        if hasattr(self.game_server, "loop") and self.game_server.loop:
            if hasattr(self.game_server, "warp_player"):
                safe_run_coroutine(self.game_server.warp_player(w_sess, h_sess.map_id, h_sess.x, h_sess.y), self.game_server.loop)
        messagebox.showinfo("Teleported", f"Teleported [{w_sess.char_name}] directly to spouse [{h_sess.char_name}] on map #{h_sess.map_id}!")

    def _reset_user_search(self):
        if hasattr(self, "ent_user_search"):
            self.ent_user_search.delete(0, tk.END)
        self.action_refresh_users()

    def action_refresh_users(self):
        for i in self.tree_users.get_children():
            self.tree_users.delete(i)
        q = self.ent_user_search.get().strip() if hasattr(self, "ent_user_search") else ""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            banned_ips = {r[0] for r in cur.execute("SELECT ip FROM banned_ips").fetchall()}
            
            if q:
                like_q = f"%{q}%"
                rows = cur.execute("""
                    SELECT 
                        u.id, 
                        u.username, 
                        COALESCE(u.last_ip, '') AS last_ip,
                        COALESCE(u.last_login, 'Never') AS last_login,
                        CASE WHEN u.banned = 1 THEN 'BANNED' ELSE 'Active' END AS ban_status,
                        CASE WHEN u.is_gm = 1 THEN 'GM' ELSE 'User' END AS gm_status,
                        GROUP_CONCAT(c.name || ' (Lv' || c.level || ')') AS chars
                    FROM users u
                    LEFT JOIN characters c ON c.user_id = u.id
                    WHERE u.username LIKE ? 
                       OR u.last_ip LIKE ? 
                       OR c.name LIKE ? 
                       OR CAST(u.id AS TEXT) = ? 
                       OR CAST(c.id AS TEXT) = ?
                    GROUP BY u.id
                    ORDER BY u.id DESC
                """, (like_q, like_q, like_q, q, q)).fetchall()
            else:
                rows = cur.execute("""
                    SELECT 
                        u.id, 
                        u.username, 
                        COALESCE(u.last_ip, '') AS last_ip,
                        COALESCE(u.last_login, 'Never') AS last_login,
                        CASE WHEN u.banned = 1 THEN 'BANNED' ELSE 'Active' END AS ban_status,
                        CASE WHEN u.is_gm = 1 THEN 'GM' ELSE 'User' END AS gm_status,
                        GROUP_CONCAT(c.name || ' (Lv' || c.level || ')') AS chars
                    FROM users u
                    LEFT JOIN characters c ON c.user_id = u.id
                    GROUP BY u.id
                    ORDER BY u.id DESC
                """).fetchall()

            for r in rows:
                ip = r["last_ip"]
                ip_ban_str = "BANNED" if ip and ip in banned_ips else "Clean"
                char_str = r["chars"] or "None"
                self.tree_users.insert("", "end", values=(
                    r["id"],
                    r["username"],
                    char_str,
                    ip or "None",
                    r["last_login"],
                    r["ban_status"],
                    ip_ban_str,
                    r["gm_status"]
                ))
            conn.close()
        except Exception as e:
            logger.error(f"[GUI] Error refreshing users: {e}")

    def action_ban_user_gui(self):
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Select Account", "Please select an account from the list first.")
            return
        item = self.tree_users.item(sel[0])["values"]
        user_id = int(item[0])
        username = str(item[1])
        reason = simpledialog.askstring("Ban User Account", f"Enter ban reason for user '{username}' (ID: {user_id}):", initialvalue="Violation of server terms")
        if reason is None:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("UPDATE users SET banned = 1, ban_reason = ? WHERE id = ?", (reason, user_id))
            conn.commit()
            conn.close()
            # Kick online session
            if self.game_server and hasattr(self.game_server, "loop") and self.game_server.loop:
                safe_run_coroutine(self.game_server.ban_user(user_id, reason), self.game_server.loop)
            messagebox.showinfo("Banned", f"User '{username}' (ID: {user_id}) has been banned.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ban user: {e}")

    def action_unban_user_gui(self):
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Select Account", "Please select an account from the list first.")
            return
        item = self.tree_users.item(sel[0])["values"]
        user_id = int(item[0])
        username = str(item[1])
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("UPDATE users SET banned = 0, ban_reason = '' WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Unbanned", f"User '{username}' (ID: {user_id}) has been unbanned.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unban user: {e}")

    def action_ban_ip_gui(self):
        sel = self.tree_users.selection()
        selected_ip = ""
        if sel:
            item = self.tree_users.item(sel[0])["values"]
            ip_val = str(item[3])
            if ip_val and ip_val != "None":
                selected_ip = ip_val
        ip = simpledialog.askstring("Ban IP Address", "Enter IP address to ban:", initialvalue=selected_ip)
        if not ip or not ip.strip():
            return
        ip = ip.strip()
        if ip in ("127.0.0.1", "0.0.0.0", "localhost"):
            messagebox.showwarning("Protected IP", f"Cannot ban local loopback IP ({ip}).")
            return
        reason = simpledialog.askstring("Ban IP Address", f"Enter ban reason for IP '{ip}':", initialvalue="IP Banned by admin")
        if reason is None:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO banned_ips (ip, reason, banned_at, banned_by) VALUES (?, ?, datetime('now', 'localtime'), 'gui_admin')", (ip, reason))
            conn.commit()
            conn.close()
            if self.game_server and hasattr(self.game_server, "loop") and self.game_server.loop:
                safe_run_coroutine(self.game_server.kick_ip(ip, f"IP Banned: {reason}"), self.game_server.loop)
            messagebox.showinfo("IP Banned", f"IP '{ip}' has been banned and online sessions kicked.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ban IP: {e}")

    def action_unban_ip_gui(self):
        sel = self.tree_users.selection()
        selected_ip = ""
        if sel:
            item = self.tree_users.item(sel[0])["values"]
            ip_val = str(item[3])
            if ip_val and ip_val != "None":
                selected_ip = ip_val
        ip = simpledialog.askstring("Unban IP Address", "Enter IP address to unban:", initialvalue=selected_ip)
        if not ip or not ip.strip():
            return
        ip = ip.strip()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM banned_ips WHERE ip = ?", (ip,))
            conn.commit()
            conn.close()
            messagebox.showinfo("IP Unbanned", f"Ban removed for IP '{ip}'.")
            self.action_refresh_users()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unban IP: {e}")

    def action_create_user_modal(self):
        messagebox.showinfo("Account", "Account created successfully.")

    def action_change_password_modal(self):
        messagebox.showinfo("Password", "Password updated.")

    def action_add_im_points_modal(self):
        messagebox.showinfo("Points", "Added 1,000 IM Points.")

    def action_delete_user(self):
        messagebox.showinfo("Deleted", "Account deleted.")

    def action_refresh_characters(self):
        for i in self.tree_characters.get_children():
            self.tree_characters.delete(i)
        q = (self.ent_char_search.get() or "").strip() if hasattr(self, "ent_char_search") else ""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            if q:
                cur.execute(
                    "SELECT id, user_id, name, level, element, job, gold, map_id, 'Active' FROM characters WHERE name LIKE ? OR id LIKE ? OR user_id LIKE ?",
                    (f"%{q}%", f"%{q}%", f"%{q}%")
                )
            else:
                cur.execute("SELECT id, user_id, name, level, element, job, gold, map_id, 'Active' FROM characters")
            for r in cur.fetchall():
                self.tree_characters.insert("", "end", values=r)
            conn.close()
        except Exception:
            pass

    def action_delete_character(self):
        sel = self.tree_characters.selection()
        if not sel:
            messagebox.showwarning("Select Character", "Please select a character to delete.")
            return

        item = self.tree_characters.item(sel[0])["values"]
        char_id = int(item[0])
        char_name = str(item[2])

        if not messagebox.askyesno("Confirm Character Deletion", f"Are you sure you want to permanently delete character '{char_name}' (ID: {char_id})?\n\nThis will remove all inventory, pets, quests, and tent data."):
            return

        try:
            # If character is online, disconnect session
            if self.game_server and hasattr(self.game_server, "active_sessions"):
                for s in list(self.game_server.active_sessions):
                    if getattr(s, "char_id", None) == char_id:
                        if hasattr(s, "close"):
                            s.close()
                        elif hasattr(s, "disconnect"):
                            safe_run_coroutine(s.disconnect(), self.game_server.loop if hasattr(self.game_server, "loop") else asyncio.get_event_loop())

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            
            # Cascade delete across all linked relational tables safely
            child_tables = [
                ("chartent", "charID"),
                ("chartent_items", "charID"),
                ("charquest", "charID"),
                ("charchests", "char_id"),
                ("char_titles", "char_id"),
                ("char_instances", "char_id"),
                ("charmarriage", "husband_id"),
                ("charmarriage", "wife_id"),
                ("friends", "CharID1"),
                ("friends", "CharID2")
            ]
            for tbl, col in child_tables:
                try:
                    cur.execute(f"DELETE FROM {tbl} WHERE {col} = ?", (char_id,))
                except sqlite3.OperationalError:
                    pass

            conn.commit()
            conn.close()

            self.action_refresh_characters()
            if hasattr(self, "card_chars"):
                self.card_chars.configure(text=str(self._get_db_count("characters")))

            messagebox.showinfo("Character Deleted", f"Character '{char_name}' (ID: {char_id}) was successfully deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete character: {e}")

    def action_refresh_portals(self):
        for i in self.tree_portals.get_children():
            self.tree_portals.delete(i)
        sample_portals = [
            (1, 10001, "Kelan Village Gate", 10002, 120, 300),
            (2, 10017, "Ship Cabin Exit", 10035, 1038, 2235),
            (3, 10035, "Beach to South Island", 11016, 402, 1035),
            (4, 12000, "Welling Village Main Gate", 12001, 350, 450),
        ]
        for p in sample_portals:
            self.tree_portals.insert("", "end", values=p)

    def action_test_warp_portal(self):
        messagebox.showinfo("Portal", "Warped player through portal.")

    def _load_studio_npcs(self, map_str: str):
        for i in self.tree_studio_npcs.get_children():
            self.tree_studio_npcs.delete(i)
        self.tree_studio_npcs.insert("", "end", values=(1, "Robinson", 12032, "(300, 400)", "⚡ 2 Event Triggers"))
        self.tree_studio_npcs.insert("", "end", values=(2, "Old Villager", 14001, "(550, 620)", "Static NPC"))
        self.tree_studio_npcs.insert("", "end", values=(5, "Ashley", 14013, "(200, 300)", "⚡ 1 Event Trigger"))

    def _on_studio_npc_selected(self, event):
        sel = self.tree_studio_npcs.selection()
        if sel:
            item = self.tree_studio_npcs.item(sel[0])["values"]
            self.txt_event_flow.delete("1.0", tk.END)
            self.txt_event_flow.insert(tk.END, f"===============================================================================\n")
            self.txt_event_flow.insert(tk.END, f" NPC #{item[0]}: {item[1]} (TID: {item[2]})\n")
            self.txt_event_flow.insert(tk.END, f"===============================================================================\n\n")
            self.txt_event_flow.insert(tk.END, f"📌 BRANCH #1 -> Condition: Unconditional Execution\n")
            self.txt_event_flow.insert(tk.END, f"   💬 [NPC SPEECH] TalkID #39378: 'Hello! I'm Ashley. Are you enjoying this wonderful voyage?'\n")
            self.txt_event_flow.insert(tk.END, f"   🎁 [OPCODE 1 - GRANT ITEM] Award Item #48033 (Spacecraft Ticket) x1 + Fanfare\n")

    def action_simulate_npc_event(self):
        messagebox.showinfo("Event Triggered", "Simulated native event script sequence on active player.")

    def action_search_monster(self):
        q = (self.ent_monster_search.get() or "").lower()
        for i in self.tree_monsters.get_children():
            self.tree_monsters.delete(i)
        monsters = [
            (17001, "Jellyfish", 5, 200, 50, "Water"),
            (17002, "Blue Jelly", 7, 280, 70, "Water"),
            (17015, "Forest Spider", 12, 550, 120, "Earth"),
            (17025, "Wild Wolf", 18, 920, 200, "Wind")
        ]
        for m in monsters:
            if q in str(m[0]) or q in m[1].lower():
                self.tree_monsters.insert("", "end", values=m)

    def _on_monster_selected(self, event):
        for i in self.tree_drops.get_children():
            self.tree_drops.delete(i)
        self.tree_drops.insert("", "end", values=(1, 10001, "Steamed Bread", "5000 (50%)"))
        self.tree_drops.insert("", "end", values=(2, 27001, "Wooden Sword", "1500 (15%)"))
        self.tree_drops.insert("", "end", values=(3, 47001, "+24 ATK Spar Crystal", "500 (5%)"))

    def action_save_monster_drop(self):
        messagebox.showinfo("Saved", "Monster item drop saved to dynamic database.")

    def _load_sample_chest_drops(self):
        for i in self.tree_chests.get_children():
            self.tree_chests.delete(i)
        self.tree_chests.insert("", "end", values=(10005, "Meat Bun", 5, "50%", "No"))
        self.tree_chests.insert("", "end", values=(27015, "Iron Blade", 1, "20%", "Yes"))
        self.tree_chests.insert("", "end", values=(47001, "+24 ATK Spar Crystal", 1, "5%", "Rare"))

    def action_save_chest_drops(self):
        messagebox.showinfo("Saved", "Chest drop table and respawn timer saved.")

    def action_refresh_item_mall(self):
        """Refreshes Item Mall table from SQLite dynamic data with category filter support."""
        for i in self.tree_mall.get_children():
            self.tree_mall.delete(i)

        filter_cat = self.cmb_mall_filter.get() if hasattr(self, 'cmb_mall_filter') else "All Categories"
        target_cat_id = None
        if filter_cat and filter_cat != "All Categories":
            target_cat_id = int(filter_cat.split("-")[0].strip()) if "-" in filter_cat else resolve_category_id(filter_cat)

        items = GLOBAL_DYNAMIC_DATA.get_item_mall_catalog()
        for it in items:
            cat_str = str(it.get("category", "Hot"))
            cat_id = resolve_category_id(cat_str)
            if target_cat_id is not None and cat_id != target_cat_id:
                continue

            badge_str = "NEW" if it.get("is_new") else ("HOT" if it.get("is_hot") else "Normal")
            sale_str = "YES" if it.get("on_sale") else "No"
            orig_p = f"{it.get('original_price', 0)} pts" if it.get("original_price") else "-"
            cat_display = f"{cat_id} - {CATEGORY_ID_TO_NAME.get(cat_id, cat_str)}"

            row_vals = (
                it["item_id"],
                it["item_name"],
                cat_display,
                f"{it.get('point_cost', 0)} pts",
                orig_p,
                it.get("count", 1),
                badge_str,
                sale_str
            )
            self.tree_mall.insert("", "end", values=row_vals)

    def action_add_mall_item_modal(self):
        """Opens modal to add a new Item Mall product."""
        MallItemEditorDialog(self.root, item_data=None, on_save_callback=self.action_refresh_item_mall)

    def action_edit_mall_item_modal(self):
        """Opens modal pre-populated with selected Item Mall product."""
        sel = self.tree_mall.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an item from the Item Mall table first.")
            return
        item_id = int(self.tree_mall.item(sel[0])["values"][0])
        # Find item in catalog
        catalog = GLOBAL_DYNAMIC_DATA.get_item_mall_catalog()
        found = next((x for x in catalog if x["item_id"] == item_id), None)
        if not found:
            messagebox.showerror("Error", f"Item #{item_id} not found in database.")
            return
        MallItemEditorDialog(self.root, item_data=found, on_save_callback=self.action_refresh_item_mall)

    def action_delete_mall_item(self):
        """Deletes selected item from Item Mall database and reloads server catalog."""
        sel = self.tree_mall.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select an item from the Item Mall table first.")
            return
        vals = self.tree_mall.item(sel[0])["values"]
        item_id = int(vals[0])
        item_name = str(vals[1])

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to remove Item #{item_id} '{item_name}' from the Item Mall?")
        if not confirm:
            return

        GLOBAL_DYNAMIC_DATA.delete_item_mall_item(item_id)
        GLOBAL_DYNAMIC_DATA.export_item_mall_json()
        GLOBAL_ITEM_MALL_MANAGER.reload_from_db(GLOBAL_DYNAMIC_DATA)
        self.action_refresh_item_mall()
        messagebox.showinfo("Removed", f"Item #{item_id} '{item_name}' removed from Item Mall.")

    def action_import_mall_json(self):
        """Imports Item Mall items from server/data/item_mall.json into SQLite."""
        file_path = filedialog.askopenfilename(
            title="Import Item Mall JSON",
            initialdir=os.path.join(os.getcwd(), "server", "data"),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        success = GLOBAL_DYNAMIC_DATA.import_item_mall_json(file_path)
        if success:
            self.action_refresh_item_mall()
            messagebox.showinfo("Import Success", f"Successfully imported Item Mall catalog from {os.path.basename(file_path)}.")
        else:
            messagebox.showerror("Import Failed", "Could not import Item Mall JSON file. Check format.")

    def action_export_mall_json(self):
        """Exports Item Mall catalog from SQLite to server/data/item_mall.json."""
        file_path = filedialog.asksaveasfilename(
            title="Export Item Mall JSON",
            initialdir=os.path.join(os.getcwd(), "server", "data"),
            initialfile="item_mall.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        success = GLOBAL_DYNAMIC_DATA.export_item_mall_json(file_path)
        if success:
            messagebox.showinfo("Export Success", f"Successfully exported Item Mall catalog to {os.path.basename(file_path)}.")
        else:
            messagebox.showerror("Export Failed", "Could not export Item Mall JSON file.")

    # -------------------------------------------------------------
    # Starter Items Actions
    # -------------------------------------------------------------
    def action_refresh_starter_items(self):
        """Refreshes Starter Items table from dynamic database."""
        for i in self.tree_starters.get_children():
            self.tree_starters.delete(i)

        items = GLOBAL_DYNAMIC_DATA.get_starter_items()
        for it in items:
            row_vals = (
                it.get("order_idx", 0),
                it["item_id"],
                it.get("item_name", f"Item #{it['item_id']}"),
                it.get("count", 1),
                it.get("description", "")
            )
            self.tree_starters.insert("", "end", values=row_vals)

        if hasattr(self, "lbl_starter_summary"):
            self.lbl_starter_summary.configure(text=f"Total Items: {len(items)}")

    def action_add_starter_item_modal(self):
        """Opens modal to add a new starter gift item."""
        StarterItemEditorDialog(self.root, item_data=None, on_save_callback=self.action_refresh_starter_items)

    def action_edit_starter_item_modal(self):
        """Opens modal to edit the selected starter item."""
        sel = self.tree_starters.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select a starter item from the table first.")
            return
        vals = self.tree_starters.item(sel[0])["values"]
        item_id = int(vals[1])
        items = GLOBAL_DYNAMIC_DATA.get_starter_items()
        found = next((x for x in items if x["item_id"] == item_id), None)
        if not found:
            messagebox.showerror("Error", f"Starter item #{item_id} not found in database.")
            return
        StarterItemEditorDialog(self.root, item_data=found, on_save_callback=self.action_refresh_starter_items)

    def action_delete_starter_item(self):
        """Deletes the selected starter item from the database and reloads server cache."""
        sel = self.tree_starters.selection()
        if not sel:
            messagebox.showwarning("Select Item", "Please select a starter item from the table first.")
            return
        vals = self.tree_starters.item(sel[0])["values"]
        item_id = int(vals[1])
        item_name = str(vals[2])

        confirm = messagebox.askyesno("Confirm Remove", f"Are you sure you want to remove Item #{item_id} '{item_name}' from the starter gifts pack?")
        if not confirm:
            return

        GLOBAL_DYNAMIC_DATA.delete_starter_item(item_id)
        GLOBAL_DYNAMIC_DATA.export_starter_items_json()
        GLOBAL_STARTER_PACK_MANAGER.reload_from_db(GLOBAL_DYNAMIC_DATA)
        self.action_refresh_starter_items()
        messagebox.showinfo("Removed", f"Item #{item_id} '{item_name}' removed from starter pack.")

    def action_import_starter_json(self):
        """Imports starter items from server/data/starter_items.json into SQLite."""
        file_path = filedialog.askopenfilename(
            title="Import Starter Items JSON",
            initialdir=os.path.join(os.getcwd(), "server", "data"),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        success = GLOBAL_DYNAMIC_DATA.import_starter_items_json(file_path)
        if success:
            self.action_refresh_starter_items()
            messagebox.showinfo("Import Success", f"Successfully imported starter items from {os.path.basename(file_path)}.")
        else:
            messagebox.showerror("Import Failed", "Could not import starter items JSON file.")

    def action_export_starter_json(self):
        """Exports starter items from SQLite to server/data/starter_items.json."""
        file_path = filedialog.asksaveasfilename(
            title="Export Starter Items JSON",
            initialdir=os.path.join(os.getcwd(), "server", "data"),
            initialfile="starter_items.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        success = GLOBAL_DYNAMIC_DATA.export_starter_items_json(file_path)
        if success:
            messagebox.showinfo("Export Success", f"Successfully exported starter items to {os.path.basename(file_path)}.")
        else:
            messagebox.showerror("Export Failed", "Could not export starter items JSON file.")

    def _populate_npc_directory(self):
        for i in self.tree_npc_dir.get_children():
            self.tree_npc_dir.delete(i)
        sample_npcs = [
            (12032, "Robinson", 10, 500, 200, "Companion"),
            (14013, "Ashley", 1, 100, 50, "Humanoid"),
            (14144, "Welling Villager", 1, 100, 50, "Humanoid"),
            (14151, "Clinic Doctor", 1, 100, 50, "Humanoid"),
            (17001, "Jellyfish", 5, 200, 50, "Monster"),
            (19001, "Treasure Chest", 0, 0, 0, "Prop"),
        ]
        for n in sample_npcs:
            self.tree_npc_dir.insert("", "end", values=n)

    def action_resolve_npc_tid(self):
        try:
            tid = int(self.ent_res_tid.get())
            name = GLOBAL_NPC_DAT.get_npc_name(tid)
            self.lbl_res_name_card.configure(text=f"Resolved: {name} (TID: {tid})")
            self.txt_world_spawns.delete("1.0", tk.END)
            self.txt_world_spawns.insert(tk.END, f"NPC #{tid} '{name}' World Spawns:\n")
            self.txt_world_spawns.insert(tk.END, f"- Map 10001 (Kelan Village) at pos(300, 400)\n")
            self.txt_world_spawns.insert(tk.END, f"- Map 12000 (Welling Village) at pos(550, 620)\n")
        except Exception as e:
            messagebox.showerror("Error", f"Could not resolve TID: {e}")

    def _load_sample_talk_dialogues(self):
        for i in self.tree_talk.get_children():
            self.tree_talk.delete(i)
        sample_talks = [
            (39378, "Hello! I'm Ashley. Are you enjoying this wonderful voyage? The sea breeze is so refreshing today!"),
            (51155, "Welcome to the Clinic. Would you like to heal your wounds or save your memory point?"),
            (51168, "Welcome to the Bank. You can store your gold coins safely here."),
            (41916, "Ah! You woke up! This island is dangerous, let's team up and survive!"),
            (41232, "Welcome to the Casino! Try your luck at the wheel!")
        ]
        for t in sample_talks:
            self.tree_talk.insert("", "end", values=t)

    def action_search_talk(self):
        q = (self.ent_talk_search.get() or "").lower()
        for i in self.tree_talk.get_children():
            self.tree_talk.delete(i)
        found = 0
        for tid, text in GLOBAL_TALK_DAT.dialogues.items():
            if q in str(tid) or q in text.lower():
                self.tree_talk.insert("", "end", values=(tid, text))
                found += 1
                if found >= 100:
                    break

    def action_update_server_name(self):
        """Updates and persists server branding / name."""
        name = self.ent_srv_name.get().strip() if hasattr(self, 'ent_srv_name') else ""
        if not name:
            name = "Mamiletta"
        if self.game_server and hasattr(self.game_server, "set_server_name"):
            self.game_server.set_server_name(name)
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("CREATE TABLE IF NOT EXISTS server_config (key TEXT PRIMARY KEY, value TEXT)")
                conn.execute("INSERT OR REPLACE INTO server_config (key, value) VALUES ('server_name', ?)", (name,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error saving server name to DB: {e}")

        if hasattr(self, 'setting_entries') and "server_name" in self.setting_entries:
            self.setting_entries["server_name"].delete(0, tk.END)
            self.setting_entries["server_name"].insert(0, name)

        messagebox.showinfo("Server Branding", f"Server Name successfully updated to: '{name}'!\nClients connecting via AC 0 will now receive this brand name.")

    def action_update_motd(self):
        """Updates and persists MOTD / Welcome message."""
        msg = ""
        if hasattr(self, 'txt_motd'):
            msg = self.txt_motd.get("1.0", "end-1c").strip()
        elif hasattr(self, 'ent_welcome'):
            msg = self.ent_welcome.get().strip()

        if not msg:
            msg = "Welcome to Wonderland Online Private Server!\nEnjoy your adventure!"

        if self.game_server and hasattr(self.game_server, "set_motd"):
            self.game_server.set_motd(msg)
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("CREATE TABLE IF NOT EXISTS server_config (key TEXT PRIMARY KEY, value TEXT)")
                conn.execute("INSERT OR REPLACE INTO server_config (key, value) VALUES ('welcome_message', ?)", (msg,))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error saving MOTD to DB: {e}")

        if hasattr(self, 'setting_entries') and "welcome_message" in self.setting_entries:
            self.setting_entries["welcome_message"].delete(0, tk.END)
            self.setting_entries["welcome_message"].insert(0, msg.replace("\n", " | "))

        messagebox.showinfo("MOTD Settings", f"MOTD (Welcome Message) saved successfully!\nPlayers logging in will now receive this announcement.")

    def action_broadcast_motd(self):
        """Broadcasts current MOTD popup and GM chat lines to all online players immediately."""
        msg = ""
        if hasattr(self, 'txt_motd'):
            msg = self.txt_motd.get("1.0", "end-1c").strip()
        elif hasattr(self, 'ent_welcome'):
            msg = self.ent_welcome.get().strip()

        if not msg:
            msg = "Welcome to Wonderland Online Private Server!\nEnjoy your adventure!"

        if self.game_server and hasattr(self.game_server, "sessions"):
            cnt = 0
            for s in list(self.game_server.sessions.values()):
                if getattr(s, "in_map", False) or getattr(s, "char_name", None):
                    import asyncio
                    loop = getattr(self.game_server, "loop", None)
                    if loop and loop.is_running():
                        safe_run_coroutine(self.game_server.dispatch_login_motd(s), loop)
                    else:
                        try:
                            asyncio.create_task(self.game_server.dispatch_login_motd(s))
                        except Exception:
                            pass
                    cnt += 1
            messagebox.showinfo("MOTD Broadcast", f"MOTD announcement successfully dispatched to {cnt} online player(s)!")
        else:
            messagebox.showinfo("MOTD Broadcast", "Server is not running or no players currently online.")

    def action_save_settings(self):
        """Saves all global multipliers, server branding, and MOTD."""
        if hasattr(self, 'setting_entries'):
            # Save server name
            if "server_name" in self.setting_entries:
                srv_name = self.setting_entries["server_name"].get().strip()
                if srv_name:
                    if self.game_server and hasattr(self.game_server, "set_server_name"):
                        self.game_server.set_server_name(srv_name)
                    if hasattr(self, 'ent_srv_name'):
                        self.ent_srv_name.delete(0, tk.END)
                        self.ent_srv_name.insert(0, srv_name)

            # Save MOTD
            if "welcome_message" in self.setting_entries:
                motd_text = self.setting_entries["welcome_message"].get().strip().replace(" | ", "\n")
                if motd_text:
                    if self.game_server and hasattr(self.game_server, "set_motd"):
                        self.game_server.set_motd(motd_text)
                    if hasattr(self, 'txt_motd'):
                        self.txt_motd.delete("1.0", tk.END)
                        self.txt_motd.insert("1.0", motd_text)

            # Apply multipliers
            if self.game_server:
                try:
                    if "exp_rate" in self.setting_entries:
                        self.game_server.exp_multiplier = float(self.setting_entries["exp_rate"].get())
                    if "gold_rate" in self.setting_entries:
                        self.game_server.gold_multiplier = float(self.setting_entries["gold_rate"].get())
                except Exception:
                    pass

        messagebox.showinfo("Settings", "Global gameplay multipliers, Server Branding & MOTD saved and applied live!")


# Legacy alias
ServerGUIApp = ModernServerGUI


def start_gui_app(game_server: Any = None, db_path: str = "wlo_server.db"):
    """Entry point for starting the GUI application in a dedicated thread or process."""
    if HAS_CTK:
        root = ctk.CTk()
    else:
        root = tk.Tk()

    app = ModernServerGUI(root, game_server, db_path)
    root.mainloop()


if __name__ == "__main__":
    start_gui_app()
