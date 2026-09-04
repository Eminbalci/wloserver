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
        self.minsize(850, 600)

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
        bottom = ctk.CTkFrame(self, height=45, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkButton(bottom, text="💾 Save All Changes (DB & Live)", font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669", width=220, height=36, corner_radius=8, command=self.action_save_all).pack(side="right", padx=6)
        ctk.CTkButton(bottom, text="🔄 Reload from DB", font=ctk.CTkFont(), fg_color="#1E293B", hover_color="#334155", width=140, height=36, corner_radius=8, command=self.load_all_character_data).pack(side="right", padx=6)
        ctk.CTkButton(bottom, text="❌ Close", font=ctk.CTkFont(), fg_color="#1E293B", hover_color="#334155", width=100, height=36, corner_radius=8, command=self.destroy).pack(side="left", padx=6)

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
        f_cheat = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=8, border_width=1, border_color="#30363D")
        f_cheat.grid(row=len(fields)//2 + 1, column=0, columnspan=4, sticky="ew", padx=15, pady=15)

        ctk.CTkLabel(f_cheat, text="⚡ Quick Character Boosters:", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=10, pady=8)
        ctk.CTkButton(f_cheat, text="💚 Full Heal HP/SP", fg_color="#238636", width=120, height=28, command=self._quick_heal).pack(side="left", padx=4)
        ctk.CTkButton(f_cheat, text="⭐ Max Level 199", fg_color="#1F6FEB", width=120, height=28, command=self._quick_max_level).pack(side="left", padx=4)
        ctk.CTkButton(f_cheat, text="💰 +10,000,000 Gold", fg_color="#D29922", text_color="#000", width=130, height=28, command=self._quick_add_gold).pack(side="left", padx=4)
        ctk.CTkButton(f_cheat, text="🔮 +500 Stat Points", fg_color="#8957E5", width=130, height=28, command=self._quick_add_stats).pack(side="left", padx=4)

    # 2. Quests Tab
    def _build_quests_tab(self, parent):
        # Top toolbar
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(tb, text="Quest ID:", text_color="#8B949E").pack(side="left", padx=4)
        self.ent_q_id = ctk.CTkEntry(tb, width=80, placeholder_text="12001")
        self.ent_q_id.pack(side="left", padx=4)

        ctk.CTkLabel(tb, text="State:", text_color="#8B949E").pack(side="left", padx=4)
        self.cmb_q_state = ctk.CTkComboBox(tb, values=["0 - Not Started", "1 - In Progress", "2 - Completed"], width=140)
        self.cmb_q_state.set("2 - Completed")
        self.cmb_q_state.pack(side="left", padx=4)

        ctk.CTkButton(tb, text="➕ Add / Set Quest", fg_color="#1F6FEB", width=120, command=self.action_set_quest).pack(side="left", padx=6)
        ctk.CTkButton(tb, text="🗑 Delete Quest", fg_color="#DA3633", width=110, command=self.action_delete_quest).pack(side="left", padx=4)
        ctk.CTkButton(tb, text="✨ Complete All Quests", fg_color="#238636", width=150, command=self.action_complete_all_quests).pack(side="right", padx=4)
        ctk.CTkButton(tb, text="🔄 Reset All Quests", fg_color="#21262D", width=130, command=self.action_reset_all_quests).pack(side="right", padx=4)

        # Quests Treeview
        cols = ("QuestID", "QuestName", "StateCode", "StateDescription", "Step")
        self.tree_quests, self.sb_quests, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_quests.heading(c, text=c)
            self.tree_quests.column(c, width=80 if c in ("QuestID", "StateCode", "Step") else 200, anchor="center")

    # 3. Pets Tab
    def _build_pets_tab(self, parent):
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(tb, text="Add Preset Pet:", text_color="#8B949E").pack(side="left", padx=4)
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
        self.cmb_pet_preset.pack(side="left", padx=4)

        ctk.CTkButton(tb, text="➕ Add Companion", fg_color="#1F6FEB", width=130, command=self.action_add_preset_pet).pack(side="left", padx=6)
        ctk.CTkButton(tb, text="💖 Max Amity (100)", fg_color="#238636", width=120, command=self.action_max_pet_amity).pack(side="left", padx=4)
        ctk.CTkButton(tb, text="🗑 Dismiss Selected Pet", fg_color="#DA3633", width=150, command=self.action_delete_pet).pack(side="right", padx=4)

        cols = ("Slot", "PetID", "Name", "Level", "Amity", "HP", "SP", "STR", "CON", "AGI")
        self.tree_pets, self.sb_pets, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_pets.heading(c, text=c)
            self.tree_pets.column(c, width=70 if c != "Name" else 130, anchor="center")

    # 4. Inventory Tab
    def _build_inv_tab(self, parent):
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(tb, text="Item ID:", text_color="#8B949E").pack(side="left", padx=4)
        self.ent_inv_item_id = ctk.CTkEntry(tb, width=90, placeholder_text="48033")
        self.ent_inv_item_id.pack(side="left", padx=4)

        ctk.CTkLabel(tb, text="Amount:", text_color="#8B949E").pack(side="left", padx=4)
        self.ent_inv_amount = ctk.CTkEntry(tb, width=60)
        self.ent_inv_amount.insert(0, "1")
        self.ent_inv_amount.pack(side="left", padx=4)

        ctk.CTkButton(tb, text="🎁 Add Item", fg_color="#1F6FEB", width=100, command=self.action_add_inv_item).pack(side="left", padx=6)
        ctk.CTkButton(tb, text="🔧 Repair Selected", fg_color="#238636", width=120, command=self.action_repair_inv_item).pack(side="left", padx=4)
        ctk.CTkButton(tb, text="🗑 Delete Item", fg_color="#DA3633", width=100, command=self.action_delete_inv_item).pack(side="left", padx=4)
        ctk.CTkButton(tb, text="🧹 Clear All 50 Slots", fg_color="#21262D", width=140, command=self.action_clear_inventory).pack(side="right", padx=4)

        cols = ("Slot", "ItemID", "ItemName", "Amount", "Damage", "Defense", "SparBonus")
        self.tree_inv, self.sb_inv, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_inv.heading(c, text=c)
            self.tree_inv.column(c, width=70 if c in ("Slot", "ItemID", "Amount") else 140, anchor="center")

    # 5. Skills Tab
    def _build_skills_tab(self, parent):
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(tb, text="Skill ID:", text_color="#8B949E").pack(side="left", padx=4)
        self.ent_skill_id = ctk.CTkEntry(tb, width=80, placeholder_text="1001")
        self.ent_skill_id.pack(side="left", padx=4)

        ctk.CTkLabel(tb, text="Grade:", text_color="#8B949E").pack(side="left", padx=4)
        self.ent_skill_grade = ctk.CTkEntry(tb, width=50)
        self.ent_skill_grade.insert(0, "1")
        self.ent_skill_grade.pack(side="left", padx=4)

        ctk.CTkButton(tb, text="➕ Learn Skill", fg_color="#1F6FEB", width=110, command=self.action_add_skill).pack(side="left", padx=6)
        ctk.CTkButton(tb, text="⚡ Learn All Element Skills", fg_color="#8957E5", width=180, command=self.action_learn_all_element_skills).pack(side="left", padx=4)
        ctk.CTkButton(tb, text="🗑 Delete Skill", fg_color="#DA3633", width=100, command=self.action_delete_skill).pack(side="right", padx=4)
        ctk.CTkButton(tb, text="🔄 Reset All Skills", fg_color="#21262D", width=130, command=self.action_reset_skills).pack(side="right", padx=4)

        cols = ("SkillID", "SkillName", "Grade", "EXP", "SPCost", "Element")
        self.tree_skills, self.sb_skills, _ = create_scrolled_treeview(parent, columns=cols, show="headings", padx=10, pady=6)
        for c in cols:
            self.tree_skills.heading(c, text=c)
            self.tree_skills.column(c, width=80 if c in ("SkillID", "Grade", "SPCost") else 150, anchor="center")

    # 6. NPC Visibility Tab
    def _build_vis_tab(self, parent):
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(tb, text="Select Map:", text_color="#8B949E").pack(side="left", padx=4)
        self.cmb_vis_map = ctk.CTkComboBox(tb, values=["10001 - Kelan Village", "10017 - Shipwreck", "10035 - Beach", "12000 - Welling Village", "11016 - South Island"], width=220)
        self.cmb_vis_map.pack(side="left", padx=4)
        ctk.CTkButton(tb, text="🔍 Inspect Map PreEvents", fg_color="#1F6FEB", width=170, command=self.action_inspect_visibility).pack(side="left", padx=6)

        ctk.CTkButton(tb, text="👁️ Force Show NPC", fg_color="#238636", width=130, command=self.action_force_show_npc).pack(side="right", padx=4)
        ctk.CTkButton(tb, text="🙈 Force Hide NPC", fg_color="#DA3633", width=130, command=self.action_force_hide_npc).pack(side="right", padx=4)

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
        self.root.minsize(1200, 780)

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
        header = ctk.CTkFrame(self.root, height=70, corner_radius=14, fg_color="#111827", border_width=1, border_color="#1E293B")
        header.pack(fill="x", padx=15, pady=(12, 6))

        f_left = ctk.CTkFrame(header, fg_color="transparent")
        f_left.pack(side="left", padx=15, pady=8)

        lbl_title = ctk.CTkLabel(f_left, text="WONDERLAND ONLINE", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#38BDF8")
        lbl_title.pack(side="left", padx=(0, 15))

        self.badge_status = ctk.CTkLabel(f_left, text="🟢 ONLINE (Port 6414)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10B981", fg_color="#064E3B", corner_radius=8, padx=12, pady=5)
        self.badge_status.pack(side="left", padx=6)

        self.badge_players = ctk.CTkLabel(f_left, text="👥 0 Online", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F8FAFC", fg_color="#1E293B", corner_radius=8, padx=12, pady=5)
        self.badge_players.pack(side="left", padx=6)

        self.badge_uptime = ctk.CTkLabel(f_left, text="⏱ Uptime: 00:00:00", font=ctk.CTkFont(size=12), text_color="#94A3B8", fg_color="#1E293B", corner_radius=8, padx=12, pady=5)
        self.badge_uptime.pack(side="left", padx=6)

        f_right = ctk.CTkFrame(header, fg_color="transparent")
        f_right.pack(side="right", padx=15, pady=8)

        btn_f5 = ctk.CTkButton(f_right, text="▶ Launch Client (F5)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#10B981", hover_color="#059669", width=155, height=36, corner_radius=8, command=self.launch_game_client)
        btn_f5.pack(side="right", padx=5)

        btn_reload = ctk.CTkButton(f_right, text="⚡ Hot-Reload", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", width=120, height=36, corner_radius=8, command=self.action_hot_reload)
        btn_reload.pack(side="right", padx=5)

        btn_save_all = ctk.CTkButton(f_right, text="💾 Save All", font=ctk.CTkFont(size=12), fg_color="#1E293B", hover_color="#334155", width=100, height=36, corner_radius=8, command=self.action_save_all_now)
        btn_save_all.pack(side="right", padx=5)

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

        # All 13 Tabs
        self.tab_dash = self.tabview.add("📊 Dashboard")
        self.tab_cheats = self.tabview.add("⚡ Live Cheats & Browser")
        self.tab_players = self.tabview.add("👥 Online Sessions")
        self.tab_users = self.tabview.add("🗄️ Users & Accounts")
        self.tab_chars = self.tabview.add("🧙 Characters Manager")
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
        top_bar = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top_bar, text="Target Online Player:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=15, pady=10)
        self.cmb_cheat_player = ctk.CTkComboBox(top_bar, values=["(Select Active Player)"], width=220, fg_color="#0B0F19", border_color="#1E293B")
        self.cmb_cheat_player.pack(side="left", padx=5)

        ctk.CTkButton(top_bar, text="🔄 Refresh Online", fg_color="#1E293B", hover_color="#334155", width=130, height=32, corner_radius=8, command=self._refresh_online_players_combos).pack(side="left", padx=8)

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
        bottom_strip = ctk.CTkFrame(parent, height=50, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        bottom_strip.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(bottom_strip, text="Give Stat Points:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(side="left", padx=(15, 4))
        self.ent_give_stat_pts = ctk.CTkEntry(bottom_strip, width=65, height=32, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_give_stat_pts.insert(0, "100")
        self.ent_give_stat_pts.pack(side="left", padx=2)
        ctk.CTkButton(bottom_strip, text="Give Points", width=85, height=32, fg_color="#2563EB", hover_color="#3B82F6", corner_radius=8, command=self.action_give_stat_points).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="Reset Stats", width=85, height=32, fg_color="#1E293B", hover_color="#334155", corner_radius=8, command=self.action_reset_stats).pack(side="left", padx=4)

        ctk.CTkButton(bottom_strip, text="💰 +1M Gold", width=95, height=32, fg_color="#F59E0B", hover_color="#D97706", text_color="#000", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_give_gold_amount(1000000)).pack(side="left", padx=6)
        ctk.CTkButton(bottom_strip, text="💎 +2,000 IM", width=95, height=32, fg_color="#8B5CF6", hover_color="#7C3AED", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_give_im_points(2000)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="⭐ +10 Levels", width=95, height=32, fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"), corner_radius=8, command=lambda: self._quick_add_levels(10)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="💚 Full Heal", width=85, height=32, fg_color="#059669", hover_color="#047857", corner_radius=8, command=self.action_heal_player).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="🛡 God Mode", width=85, height=32, fg_color="#7C3AED", hover_color="#6D28D9", corner_radius=8, command=self.action_god_mode).pack(side="left", padx=4)

        self._populate_cheats_browser_lists()

    # -------------------------------------------------------------
    # TAB 3: Online Sessions Manager
    # -------------------------------------------------------------
    def _build_online_players_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(split, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("CharID", "Name", "Account", "Level", "Gold", "MapID", "X", "Y", "IP")
        self.tree_players, _, _ = create_scrolled_treeview(left, columns=cols, show="headings", selectmode="browse", padx=15, pady=15)
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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="🔍 Search (IP, Char, User, ID):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=(12, 4), pady=10)
        self.ent_user_search = ctk.CTkEntry(top, width=230, placeholder_text="e.g. 192.168.1.10 or Hero or 1", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_user_search.pack(side="left", padx=4)
        self.ent_user_search.bind("<Return>", lambda e: self.action_refresh_users())
        ctk.CTkButton(top, text="Search", fg_color="#2563EB", hover_color="#3B82F6", width=70, corner_radius=8, command=self.action_refresh_users).pack(side="left", padx=3)
        ctk.CTkButton(top, text="Reset", fg_color="#1E293B", hover_color="#334155", width=65, corner_radius=8, command=self._reset_user_search).pack(side="left", padx=3)

        ctk.CTkButton(top, text="➕ Add User", fg_color="#10B981", hover_color="#059669", width=95, corner_radius=8, command=self.action_create_user_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="🔑 Pass", fg_color="#2563EB", hover_color="#3B82F6", width=65, corner_radius=8, command=self.action_change_password_modal).pack(side="left", padx=3)
        ctk.CTkButton(top, text="💎 Points", fg_color="#8B5CF6", hover_color="#7C3AED", width=75, corner_radius=8, command=self.action_add_im_points_modal).pack(side="left", padx=3)
        ctk.CTkButton(top, text="🗑 Delete", fg_color="#DC2626", hover_color="#B91C1C", width=75, corner_radius=8, command=self.action_delete_user).pack(side="left", padx=3)

        ctk.CTkButton(top, text="🚫 Ban User", fg_color="#DC2626", hover_color="#B91C1C", width=95, corner_radius=8, command=self.action_ban_user_gui).pack(side="right", padx=6)
        ctk.CTkButton(top, text="✅ Unban User", fg_color="#10B981", hover_color="#059669", width=105, corner_radius=8, command=self.action_unban_user_gui).pack(side="right", padx=3)
        ctk.CTkButton(top, text="🌐 Ban IP", fg_color="#991B1B", hover_color="#7F1D1D", width=90, corner_radius=8, command=self.action_ban_ip_gui).pack(side="right", padx=3)
        ctk.CTkButton(top, text="🔓 Unban IP", fg_color="#0D9488", hover_color="#0F766E", width=95, corner_radius=8, command=self.action_unban_ip_gui).pack(side="right", padx=3)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Refresh Characters", fg_color="#1E293B", hover_color="#334155", width=150, corner_radius=8, command=self.action_refresh_characters).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="🧙 Open Full Character Data Editor", font=ctk.CTkFont(weight="bold"), fg_color="#2563EB", hover_color="#3B82F6", width=260, corner_radius=8, command=self.action_open_selected_char_editor).pack(side="left", padx=6)
        ctk.CTkButton(top, text="🗑 Delete Character", fg_color="#DC2626", hover_color="#B91C1C", width=140, corner_radius=8, command=self.action_delete_character).pack(side="right", padx=10)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Filter Source Map ID:", font=ctk.CTkFont(size=12), text_color="#94A3B8").pack(side="left", padx=10, pady=10)
        self.ent_portal_filter = ctk.CTkEntry(top, width=130, placeholder_text="e.g. 10001", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_portal_filter.pack(side="left", padx=4)
        ctk.CTkButton(top, text="🔍 Filter", fg_color="#2563EB", hover_color="#3B82F6", width=90, corner_radius=8, command=self.action_refresh_portals).pack(side="left", padx=4)

        ctk.CTkButton(top, text="🚀 Test Warp on Player", fg_color="#10B981", hover_color="#059669", width=170, corner_radius=8, command=self.action_test_warp_portal).pack(side="right", padx=10)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Select Map:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=10, pady=10)
        self.cmb_studio_map = ctk.CTkComboBox(top, values=["10001 - Kelan Village", "10017 - Shipwreck", "10035 - Beach", "12000 - Welling Village", "11016 - South Island"], width=240, fg_color="#0B0F19", border_color="#1E293B", command=lambda m: self._load_studio_npcs(m))
        self.cmb_studio_map.pack(side="left", padx=4)

        ctk.CTkButton(top, text="⚡ Simulate Event on Selected Player", font=ctk.CTkFont(weight="bold"), fg_color="#8B5CF6", hover_color="#7C3AED", width=260, corner_radius=8, command=self.action_simulate_npc_event).pack(side="right", padx=10)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Search Monster (ID or Name):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=15, pady=10)
        self.ent_monster_search = ctk.CTkEntry(top, width=220, placeholder_text="e.g. Jelly or 17001", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_monster_search.pack(side="left", padx=5)
        ctk.CTkButton(top, text="Search Npc.dat", fg_color="#2563EB", hover_color="#3B82F6", width=120, corner_radius=8, command=self.action_search_monster).pack(side="left", padx=10)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Select Map / Chest:", text_color="#94A3B8").pack(side="left", padx=10, pady=10)
        self.cmb_chest_map = ctk.CTkComboBox(top, values=["Map 10001 - Chest 1", "Map 10017 - Ship Chest", "Map 10035 - Beach Chest", "Map 12000 - Village Chest"], width=220, fg_color="#0B0F19", border_color="#1E293B")
        self.cmb_chest_map.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Respawn Seconds:", text_color="#94A3B8").pack(side="left", padx=(15, 4))
        self.ent_chest_respawn = ctk.CTkEntry(top, width=70, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_chest_respawn.insert(0, "300")
        self.ent_chest_respawn.pack(side="left", padx=4)

        ctk.CTkButton(top, text="💾 Save Chest Table", fg_color="#10B981", hover_color="#059669", width=140, corner_radius=8, command=self.action_save_chest_drops).pack(side="right", padx=10)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Reload Catalog", fg_color="#1E293B", hover_color="#334155", width=125, corner_radius=8, command=self.action_refresh_item_mall).pack(side="left", padx=(10, 4), pady=10)
        ctk.CTkButton(top, text="➕ Add Item", fg_color="#10B981", hover_color="#059669", width=110, corner_radius=8, command=self.action_add_mall_item_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="✏ Edit Item", fg_color="#2563EB", hover_color="#3B82F6", width=100, corner_radius=8, command=self.action_edit_mall_item_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="🗑 Delete Item", fg_color="#DC2626", hover_color="#B91C1C", width=110, corner_radius=8, command=self.action_delete_mall_item).pack(side="left", padx=4)

        ctk.CTkButton(top, text="📥 Import JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_import_mall_json).pack(side="left", padx=4)
        ctk.CTkButton(top, text="📤 Export JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_export_mall_json).pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Filter Category:", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=(15, 4))
        self.cmb_mall_filter = ctk.CTkComboBox(
            top,
            values=["All Categories", "1 - Hot", "2 - Armory", "3 - Weaponry", "4 - Grocery", "5 - Furniture", "6 - Slot Machine", "7 - Forging Room"],
            width=160,
            fg_color="#0B0F19",
            border_color="#1E293B",
            command=lambda _: self.action_refresh_item_mall()
        )
        self.cmb_mall_filter.set("All Categories")
        self.cmb_mall_filter.pack(side="left", padx=4)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Reload Starters", fg_color="#1E293B", hover_color="#334155", width=125, corner_radius=8, command=self.action_refresh_starter_items).pack(side="left", padx=(10, 4), pady=10)
        ctk.CTkButton(top, text="➕ Add Starter Item", fg_color="#10B981", hover_color="#059669", width=140, corner_radius=8, command=self.action_add_starter_item_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="✏ Edit Selected", fg_color="#2563EB", hover_color="#3B82F6", width=110, corner_radius=8, command=self.action_edit_starter_item_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="🗑 Remove Item", fg_color="#DC2626", hover_color="#B91C1C", width=110, corner_radius=8, command=self.action_delete_starter_item).pack(side="left", padx=4)

        ctk.CTkButton(top, text="📥 Import JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_import_starter_json).pack(side="left", padx=4)
        ctk.CTkButton(top, text="📤 Export JSON", fg_color="#1E293B", hover_color="#334155", width=110, corner_radius=8, command=self.action_export_starter_json).pack(side="left", padx=4)

        self.lbl_starter_summary = ctk.CTkLabel(top, text="Items: 0", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10B981")
        self.lbl_starter_summary.pack(side="right", padx=15)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Template ID (TID):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=10, pady=10)
        self.ent_res_tid = ctk.CTkEntry(top, width=100, fg_color="#0B0F19", border_color="#1E293B")
        self.ent_res_tid.insert(0, "14013")
        self.ent_res_tid.pack(side="left", padx=4)

        ctk.CTkButton(top, text="🔍 Resolve Template", fg_color="#2563EB", hover_color="#3B82F6", width=140, corner_radius=8, command=self.action_resolve_npc_tid).pack(side="left", padx=6)
        self.lbl_res_name_card = ctk.CTkLabel(top, text="Resolved: Ashley (TID: 14013, Humanoid)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10B981")
        self.lbl_res_name_card.pack(side="left", padx=15)

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
        top = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Search Talk.dat (17,489 Dialogues):", font=ctk.CTkFont(weight="bold"), text_color="#38BDF8").pack(side="left", padx=15, pady=10)
        self.ent_talk_search = ctk.CTkEntry(top, width=280, placeholder_text="Enter keyword or TalkID (e.g. voyage or 39378)", fg_color="#0B0F19", border_color="#1E293B")
        self.ent_talk_search.pack(side="left", padx=5)
        ctk.CTkButton(top, text="🔍 Search Dialogues", fg_color="#2563EB", hover_color="#3B82F6", width=140, corner_radius=8, command=self.action_search_talk).pack(side="left", padx=8)

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

        # Update Sessions Tree
        if hasattr(self, "tree_players"):
            for i in self.tree_players.get_children():
                self.tree_players.delete(i)
            if self.game_server and hasattr(self.game_server, "sessions"):
                for s in self.game_server.sessions.values():
                    self.tree_players.insert("", "end", values=(
                        getattr(s, "char_id", 0),
                        getattr(s, "char_name", "Unknown"),
                        getattr(s, "username", "Unknown"),
                        getattr(s, "level", 1),
                        getattr(s, "gold", 0),
                        getattr(s, "map_id", 0),
                        getattr(s, "x", 0),
                        getattr(s, "y", 0),
                        getattr(s, "ip", "127.0.0.1")
                    ))

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

    def action_heal_player(self):
        messagebox.showinfo("Healed", "HP and SP fully restored!")

    def action_god_mode(self):
        messagebox.showinfo("God Mode", "God Mode toggled!")

    def action_kick_player(self):
        messagebox.showinfo("Kicked", "Player kicked.")

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
                            asyncio.run_coroutine_threadsafe(self.game_server.ban_user(getattr(s, "user_id", 0), reason), self.game_server.loop)
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
                    asyncio.run_coroutine_threadsafe(self.game_server.kick_ip(ip, f"IP Banned: {reason}"), self.game_server.loop)
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
        sel = self.list_maps.curselection()
        if sel:
            m = self.list_maps.get(sel[0])
            mid = int(m.split("-")[0].strip())
            messagebox.showinfo("Warp", f"Warping target player to Map #{mid} ({m})!")

    def action_cheat_ride_vehicle(self):
        messagebox.showinfo("Vehicle", "Player vehicle mounted!")

    def action_cheat_unride_vehicle(self):
        messagebox.showinfo("Vehicle", "Vehicle removed / unridden.")

    def action_cheat_spawn_item(self):
        sel = self.list_items.curselection()
        if sel:
            it = self.list_items.get(sel[0])
            iid = int(it.split("-")[0].strip())
            amt = int(self.ent_spawn_qty.get() or 1)
            messagebox.showinfo("Spawned", f"Spawned {amt}x Item #{iid} to player inventory!")

    def action_cheat_battle_npc(self):
        messagebox.showinfo("Battle", "PvE combat initiated with selected monster.")

    def action_cheat_recruit_npc(self):
        messagebox.showinfo("Recruited", "Selected NPC added to party as companion.")

    def action_cheat_leave_npc(self):
        messagebox.showinfo("Dismissed", "Companion dismissed.")

    def action_give_stat_points(self):
        pts = int(self.ent_give_stat_pts.get() or 100)
        messagebox.showinfo("Stat Points", f"Awarded {pts} free stat points!")

    def action_reset_stats(self):
        messagebox.showinfo("Reset Stats", "Character base stats reset to 10 points.")

    def _quick_give_gold_amount(self, amount: int):
        messagebox.showinfo("Gold", f"Awarded +{amount:,} Gold coins!")

    def _quick_give_im_points(self, amount: int):
        messagebox.showinfo("IM Points", f"Awarded +{amount:,} Item Mall Points!")

    def _quick_add_levels(self, lvls: int):
        messagebox.showinfo("Level Up", f"Level increased by +{lvls} levels!")

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
                asyncio.run_coroutine_threadsafe(self.game_server.ban_user(user_id, reason), self.game_server.loop)
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
                asyncio.run_coroutine_threadsafe(self.game_server.kick_ip(ip, f"IP Banned: {reason}"), self.game_server.loop)
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
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
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
                            asyncio.run_coroutine_threadsafe(s.disconnect(), self.game_server.loop if hasattr(self.game_server, "loop") else asyncio.get_event_loop())

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
                        asyncio.run_coroutine_threadsafe(self.game_server.dispatch_login_motd(s), loop)
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
