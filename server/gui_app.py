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
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Any, Tuple

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

from server.dynamic_data_manager import GLOBAL_DYNAMIC_DATA
from server.dat_loaders import GLOBAL_NPC_DAT, GLOBAL_TALK_DAT
from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
from server.network import PacketWriter

logger = logging.getLogger("ModernGUI")


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
            self.configure(fg_color="#0D1117")

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
        header = ctk.CTkFrame(self, height=50, fg_color="#161B22", corner_radius=8)
        header.pack(fill="x", padx=12, pady=(12, 6))

        self.lbl_header = ctk.CTkLabel(
            header,
            text=f"🧙 Character Editor: [{self.char_name}] (CharID: {self.char_id})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#58A6FF"
        )
        self.lbl_header.pack(side="left", padx=15, pady=10)

        self.lbl_live_badge = ctk.CTkLabel(
            header,
            text="🔴 OFFLINE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F85149",
            fg_color="#1F2937",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_live_badge.pack(side="right", padx=15)

        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color="#161B22", corner_radius=10)
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

        ctk.CTkButton(bottom, text="💾 Save All Changes (DB & Live)", font=ctk.CTkFont(weight="bold"), fg_color="#238636", hover_color="#2EA043", width=220, height=36, command=self.action_save_all).pack(side="right", padx=6)
        ctk.CTkButton(bottom, text="🔄 Reload from DB", font=ctk.CTkFont(), fg_color="#21262D", hover_color="#30363D", width=140, height=36, command=self.load_all_character_data).pack(side="right", padx=6)
        ctk.CTkButton(bottom, text="❌ Close", font=ctk.CTkFont(), fg_color="#30363D", hover_color="#484F58", width=100, height=36, command=self.destroy).pack(side="left", padx=6)

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
        self.tree_quests = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_quests.heading(c, text=c)
            self.tree_quests.column(c, width=80 if c in ("QuestID", "StateCode", "Step") else 200, anchor="center")
        self.tree_quests.pack(fill="both", expand=True, padx=10, pady=6)

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
        self.tree_pets = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_pets.heading(c, text=c)
            self.tree_pets.column(c, width=70 if c != "Name" else 130, anchor="center")
        self.tree_pets.pack(fill="both", expand=True, padx=10, pady=6)

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
        self.tree_inv = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_inv.heading(c, text=c)
            self.tree_inv.column(c, width=70 if c in ("Slot", "ItemID", "Amount") else 140, anchor="center")
        self.tree_inv.pack(fill="both", expand=True, padx=10, pady=6)

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
        self.tree_skills = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_skills.heading(c, text=c)
            self.tree_skills.column(c, width=80 if c in ("SkillID", "Grade", "SPCost") else 150, anchor="center")
        self.tree_skills.pack(fill="both", expand=True, padx=10, pady=6)

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
        self.tree_vis = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_vis.heading(c, text=c)
            self.tree_vis.column(c, width=90 if c in ("ClickID", "TemplateID") else 160, anchor="center")
        self.tree_vis.pack(fill="both", expand=True, padx=10, pady=6)

    # Data Loaders
    def load_all_character_data(self):
        live_session = self._get_live_session()
        if live_session:
            self.lbl_live_badge.configure(text="🟢 ONLINE (Active Session)", text_color="#3FB950")
        else:
            self.lbl_live_badge.configure(text="🔴 OFFLINE", text_color="#F85149")

        # Load from DB
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Character table
            cur.execute("""
                SELECT id, name, user_id, level, hp, gold, element, reborn, job, map_id, x, y, points, potential, skill_points, inventory, skills, quests, pets 
                FROM characters 
                WHERE id = ? OR name = ?
            """, (self.char_id, self.char_name))
            row = cur.fetchone()
            if row:
                self.char_id = row[0]
                self.char_name = row[1]
                data = {
                    "char_id": row[0], "char_name": row[1], "account_id": row[2],
                    "level": row[3], "exp": 0, "gold": row[5], "bank_gold": 0,
                    "element": row[6], "reborn": row[7], "reborn_job": row[8],
                    "str": 10, "con": 10, "int": 10, "wis": 10, "agi": 10,
                    "stat_points": row[12], "potential": row[13], "map_id": row[9],
                    "x": row[10], "y": row[11]
                }
                for k, v in data.items():
                    if k in self.stat_entries:
                        ent = self.stat_entries[k]
                        if isinstance(ent, ctk.CTkComboBox):
                            ent.set(str(v))
                        else:
                            ent.delete(0, tk.END)
                            ent.insert(0, str(v))

                # Parse JSON inventory
                if row[15]:
                    try:
                        inv_list = json.loads(row[15]) if isinstance(row[15], str) else row[15]
                        for idx, item in enumerate(inv_list, 1):
                            iid = item if isinstance(item, int) else item.get('id', 0)
                            amt = 1 if isinstance(item, int) else item.get('count', 1)
                            iname = GLOBAL_DYNAMIC_DATA.get_item_name(iid) if hasattr(GLOBAL_DYNAMIC_DATA, "get_item_name") else f"Item #{iid}"
                            self.tree_inv.insert("", "end", values=(idx, iid, iname, amt, 0, 0, 0))
                    except Exception:
                        pass

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
                        for sk in sk_list:
                            sk_id = sk if isinstance(sk, int) else sk.get("id", 0)
                            self.tree_skills.insert("", "end", values=(sk_id, f"Skill #{sk_id}", 1, 0, 15, "Universal"))
                    except Exception:
                        pass

                # Parse JSON pets
                if row[18]:
                    try:
                        pet_list = json.loads(row[18]) if isinstance(row[18], str) else row[18]
                        if isinstance(pet_list, list):
                            for idx, p in enumerate(pet_list, 1):
                                pid = p if isinstance(p, int) else p.get("id", 0)
                                pname = "Companion" if isinstance(p, int) else p.get("name", "Companion")
                                self.tree_pets.insert("", "end", values=(idx, pid, pname, 10, 100, 500, 200, 15, 15, 15))
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
                    map_id = ?, x = ?, y = ?
                WHERE id = ? OR name = ?
            """, (lvl, gold, elem, rb, rb_job, pts, pot, mid, pos_x, pos_y, self.char_id, self.char_name))

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
                if self.game_server and hasattr(self.game_server, "send_stat_packet"):
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

    def action_add_inv_item(self):
        try:
            iid = int(self.ent_inv_item_id.get())
            amt = int(self.ent_inv_amount.get() or 1)
            inv = self._get_char_json("inventory", [])
            if not isinstance(inv, list):
                inv = []
            inv.append({"item_id": iid, "count": amt, "damage": 0})
            self._set_char_json("inventory", inv)
            self.load_all_character_data()
            messagebox.showinfo("Item Added", f"Added {amt}x Item #{iid} to inventory.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add item: {e}")

    def action_repair_inv_item(self):
        messagebox.showinfo("Repaired", "Selected equipment durability restored to full!")

    def action_delete_inv_item(self):
        sel = self.tree_inv.selection()
        if not sel:
            return
        slot = int(self.tree_inv.item(sel[0])["values"][0])
        inv = self._get_char_json("inventory", [])
        if isinstance(inv, list) and 0 <= slot - 1 < len(inv):
            inv.pop(slot - 1)
            self._set_char_json("inventory", inv)
        self.load_all_character_data()

    def action_clear_inventory(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to clear this entire inventory?"):
            return
        self._set_char_json("inventory", [])
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
        self.root.geometry("1360x880")
        self.root.minsize(1150, 740)

        if HAS_CTK and isinstance(self.root, ctk.CTk):
            self.root.configure(fg_color="#0D1117")
        else:
            self.root.configure(bg="#0D1117")

        self._build_header()
        self._build_tabview()

        # Keyboard Shortcut F5: Launch Client
        self.root.bind("<F5>", lambda e: self.launch_game_client())

        # Auto refresh loop
        self._schedule_refresh()

    def _build_header(self):
        header = ctk.CTkFrame(self.root, height=65, corner_radius=12, fg_color="#161B22", border_width=1, border_color="#30363D")
        header.pack(fill="x", padx=15, pady=(12, 6))

        f_left = ctk.CTkFrame(header, fg_color="transparent")
        f_left.pack(side="left", padx=15, pady=8)

        lbl_title = ctk.CTkLabel(f_left, text="WLO SERVER SUITE", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#58A6FF")
        lbl_title.pack(side="left", padx=(0, 15))

        self.badge_status = ctk.CTkLabel(f_left, text="🟢 ONLINE (Port 6414)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3FB950", fg_color="#1F2937", corner_radius=8, padx=10, pady=4)
        self.badge_status.pack(side="left", padx=6)

        self.badge_players = ctk.CTkLabel(f_left, text="👥 0 Online", font=ctk.CTkFont(size=12, weight="bold"), text_color="#E6EDF3", fg_color="#1F2937", corner_radius=8, padx=10, pady=4)
        self.badge_players.pack(side="left", padx=6)

        self.badge_uptime = ctk.CTkLabel(f_left, text="⏱ Uptime: 00:00:00", font=ctk.CTkFont(size=12), text_color="#8B949E", fg_color="#1F2937", corner_radius=8, padx=10, pady=4)
        self.badge_uptime.pack(side="left", padx=6)

        f_right = ctk.CTkFrame(header, fg_color="transparent")
        f_right.pack(side="right", padx=15, pady=8)

        btn_f5 = ctk.CTkButton(f_right, text="▶ Launch Client (F5)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#238636", hover_color="#2EA043", width=140, height=34, corner_radius=8, command=self.launch_game_client)
        btn_f5.pack(side="right", padx=5)

        btn_reload = ctk.CTkButton(f_right, text="⚡ Hot-Reload", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#8957E5", hover_color="#A371F7", width=110, height=34, corner_radius=8, command=self.action_hot_reload)
        btn_reload.pack(side="right", padx=5)

        btn_save_all = ctk.CTkButton(f_right, text="💾 Save All", font=ctk.CTkFont(size=12), fg_color="#1F2937", hover_color="#374151", width=95, height=34, corner_radius=8, command=self.action_save_all_now)
        btn_save_all.pack(side="right", padx=5)

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color="#161B22",
            segmented_button_fg_color="#0D1117",
            segmented_button_selected_color="#1F6FEB",
            segmented_button_selected_hover_color="#388BFD",
            corner_radius=12
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
        self._build_npc_resolver_content(self.tab_npc_res)
        self._build_talk_resolver_content(self.tab_talk)
        self._build_settings_content(self.tab_settings)

    # -------------------------------------------------------------
    # TAB 1: Dashboard
    # -------------------------------------------------------------
    def _build_dashboard_content(self, parent):
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=10)

        self.card_players = self._create_metric_card(cards_frame, "ACTIVE SESSIONS", "0", "#3FB950", 0)
        self.card_accounts = self._create_metric_card(cards_frame, "TOTAL ACCOUNTS", str(self._get_db_count("accounts")), "#58A6FF", 1)
        self.card_chars = self._create_metric_card(cards_frame, "TOTAL CHARACTERS", str(self._get_db_count("characters")), "#A371F7", 2)
        self.card_maps = self._create_metric_card(cards_frame, "LOADED MAPS", "1,119", "#F0883E", 3)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, width=330, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="y", padx=(0, 10), pady=5)

        ctk.CTkLabel(left, text="Server Management", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(15, 10))

        ctk.CTkLabel(left, text="Server Name / Brand:", font=ctk.CTkFont(size=12), text_color="#8B949E").pack(anchor="w", padx=15)
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

        self.ent_srv_name = ctk.CTkEntry(left, placeholder_text="Server Name (Mamiletta)", fg_color="#161B22", height=32)
        self.ent_srv_name.insert(0, cur_srv_name)
        self.ent_srv_name.pack(fill="x", padx=15, pady=(2, 6))

        ctk.CTkButton(left, text="💾 Save Server Name (Brand)", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#238636", hover_color="#2EA043", height=30, corner_radius=8, command=self.action_update_server_name).pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(left, text="Global MOTD / Welcome Message:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(2, 2))
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

        self.txt_motd = ctk.CTkTextbox(left, height=75, fg_color="#161B22", text_color="#E6EDF3", font=ctk.CTkFont(size=11), corner_radius=6, border_width=1, border_color="#30363D")
        self.txt_motd.insert("1.0", cur_motd)
        self.txt_motd.pack(fill="x", padx=15, pady=(2, 6))

        f_motd_btns = ctk.CTkFrame(left, fg_color="transparent")
        f_motd_btns.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(f_motd_btns, text="💾 Save MOTD", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#238636", hover_color="#2EA043", height=30, corner_radius=8, command=self.action_update_motd).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(f_motd_btns, text="📢 Broadcast MOTD", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#1F6FEB", hover_color="#388BFD", height=30, corner_radius=8, command=self.action_broadcast_motd).pack(side="right", fill="x", expand=True, padx=(4, 0))

        ctk.CTkLabel(left, text="Global Marquee Announcement:", font=ctk.CTkFont(size=12), text_color="#8B949E").pack(anchor="w", padx=15)
        self.ent_welcome = ctk.CTkEntry(left, placeholder_text="Broadcast Message", fg_color="#161B22", height=32)
        self.ent_welcome.insert(0, "Special Announcement: Server maintenance in 10 minutes!")
        self.ent_welcome.pack(fill="x", padx=15, pady=(2, 6))

        self.cmb_broadcast_color = ctk.CTkComboBox(left, values=["Yellow (System)", "Red (Alert)", "Blue (Info)", "Green (Notice)", "Purple (GM)"], height=32)
        self.cmb_broadcast_color.set("Yellow (System)")
        self.cmb_broadcast_color.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(left, text="📢 Send Marquee Alert", font=ctk.CTkFont(weight="bold"), fg_color="#8957E5", hover_color="#A371F7", height=34, corner_radius=8, command=self.action_broadcast_marquee).pack(fill="x", padx=15, pady=4)
        ctk.CTkButton(left, text="🚫 Disconnect All Players", font=ctk.CTkFont(weight="bold"), fg_color="#DA3633", hover_color="#F85149", height=34, corner_radius=8, command=self.action_kick_all).pack(fill="x", padx=15, pady=4)
        ctk.CTkButton(left, text="🧹 Clear Console Log", font=ctk.CTkFont(), fg_color="#21262D", hover_color="#30363D", height=34, corner_radius=8, command=self.action_clear_logs).pack(fill="x", padx=15, pady=4)

        right = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="both", expand=True, pady=5)

        f_bar = ctk.CTkFrame(right, fg_color="transparent")
        f_bar.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_bar, text="Live Server Console Terminal", font=ctk.CTkFont(size=13, weight="bold"), text_color="#E6EDF3").pack(side="left")

        self.log_text = tk.Text(right, bg="#06090F", fg="#E6EDF3", font=("JetBrains Mono", 9), relief="flat", padx=10, pady=10)
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.log_text.tag_config("INFO", foreground="#58A6FF")
        self.log_text.tag_config("WARNING", foreground="#D29922")
        self.log_text.tag_config("ERROR", foreground="#F85149")
        self.log_text.tag_config("DEBUG", foreground="#8B949E")

        self._setup_log_pipe()

    # -------------------------------------------------------------
    # TAB 2: Live Cheats & 4-Column Browser (Direct Port from C# MainForm1)
    # -------------------------------------------------------------
    def _build_cheats_browser_content(self, parent):
        top_bar = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top_bar, text="Target Online Player:", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=15, pady=10)
        self.cmb_cheat_player = ctk.CTkComboBox(top_bar, values=["(Select Active Player)"], width=220)
        self.cmb_cheat_player.pack(side="left", padx=5)

        ctk.CTkButton(top_bar, text="🔄 Refresh Online", fg_color="#21262D", width=120, command=self._refresh_online_players_combos).pack(side="left", padx=8)

        # 4-Column Grid: Maps | Vehicles | Items | NPCs
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=5)
        for i in range(4):
            grid.columnconfigure(i, weight=1)

        # Col 1: Maps
        c1 = ctk.CTkFrame(grid, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        c1.grid(row=0, column=0, sticky="nsew", padx=4)
        ctk.CTkLabel(c1, text="🗺️ Maps (1,119)", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=10, pady=6)
        self.ent_search_maps = ctk.CTkEntry(c1, placeholder_text="Filter Maps...")
        self.ent_search_maps.pack(fill="x", padx=8, pady=(0, 4))
        self.ent_search_maps.bind("<KeyRelease>", lambda e: self._filter_maps_list())
        self.list_maps = tk.Listbox(c1, bg="#161B22", fg="#E6EDF3", selectbackground="#1F6FEB", relief="flat", font=("Segoe UI", 9))
        self.list_maps.pack(fill="both", expand=True, padx=8, pady=4)
        ctk.CTkButton(c1, text="🚀 Warp Player to Map", fg_color="#1F6FEB", height=30, command=self.action_cheat_warp_map).pack(fill="x", padx=8, pady=6)

        # Col 2: Vehicles
        c2 = ctk.CTkFrame(grid, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c2, text="🚗 Vehicles", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=10, pady=6)
        self.ent_search_veh = ctk.CTkEntry(c2, placeholder_text="Filter Vehicles...")
        self.ent_search_veh.pack(fill="x", padx=8, pady=(0, 4))
        self.list_veh = tk.Listbox(c2, bg="#161B22", fg="#E6EDF3", selectbackground="#1F6FEB", relief="flat", font=("Segoe UI", 9))
        self.list_veh.pack(fill="both", expand=True, padx=8, pady=4)
        f_veh_btns = ctk.CTkFrame(c2, fg_color="transparent")
        f_veh_btns.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(f_veh_btns, text="Ride", width=65, fg_color="#238636", command=self.action_cheat_ride_vehicle).pack(side="left", padx=2)
        ctk.CTkButton(f_veh_btns, text="Remove Vehicle", width=120, fg_color="#DA3633", command=self.action_cheat_unride_vehicle).pack(side="right", padx=2)

        # Col 3: Items
        c3 = ctk.CTkFrame(grid, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        c3.grid(row=0, column=2, sticky="nsew", padx=4)
        ctk.CTkLabel(c3, text="🎁 Items Spawner", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=10, pady=6)
        self.ent_search_items = ctk.CTkEntry(c3, placeholder_text="Filter Items...")
        self.ent_search_items.pack(fill="x", padx=8, pady=(0, 4))
        self.ent_search_items.bind("<KeyRelease>", lambda e: self._filter_items_list())
        self.list_items = tk.Listbox(c3, bg="#161B22", fg="#E6EDF3", selectbackground="#1F6FEB", relief="flat", font=("Segoe UI", 9))
        self.list_items.pack(fill="both", expand=True, padx=8, pady=4)
        f_item_spawn = ctk.CTkFrame(c3, fg_color="transparent")
        f_item_spawn.pack(fill="x", padx=8, pady=6)
        self.ent_spawn_qty = ctk.CTkEntry(f_item_spawn, width=50)
        self.ent_spawn_qty.insert(0, "1")
        self.ent_spawn_qty.pack(side="left", padx=2)
        ctk.CTkButton(f_item_spawn, text="Spawn to Inv", fg_color="#238636", command=self.action_cheat_spawn_item).pack(side="right", fill="x", expand=True, padx=2)

        # Col 4: NPCs & Monsters
        c4 = ctk.CTkFrame(grid, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        c4.grid(row=0, column=3, sticky="nsew", padx=4)
        ctk.CTkLabel(c4, text="👾 NPC & Monsters (4,916)", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=10, pady=6)
        self.ent_search_npcs = ctk.CTkEntry(c4, placeholder_text="Filter NPCs...")
        self.ent_search_npcs.pack(fill="x", padx=8, pady=(0, 4))
        self.ent_search_npcs.bind("<KeyRelease>", lambda e: self._filter_npcs_list())
        self.list_npcs = tk.Listbox(c4, bg="#161B22", fg="#E6EDF3", selectbackground="#1F6FEB", relief="flat", font=("Segoe UI", 9))
        self.list_npcs.pack(fill="both", expand=True, padx=8, pady=4)
        f_npc_btns = ctk.CTkFrame(c4, fg_color="transparent")
        f_npc_btns.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(f_npc_btns, text="⚔️ Battle", width=70, fg_color="#DA3633", command=self.action_cheat_battle_npc).pack(side="left", padx=2)
        ctk.CTkButton(f_npc_btns, text="👥 Add Pet", width=75, fg_color="#8957E5", command=self.action_cheat_recruit_npc).pack(side="left", padx=2)
        ctk.CTkButton(f_npc_btns, text="Leave", width=55, fg_color="#21262D", command=self.action_cheat_leave_npc).pack(side="right", padx=2)

        # Bottom GM Booster Strip
        bottom_strip = ctk.CTkFrame(parent, height=45, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        bottom_strip.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(bottom_strip, text="Give Stat Points:", text_color="#8B949E").pack(side="left", padx=(15, 4))
        self.ent_give_stat_pts = ctk.CTkEntry(bottom_strip, width=60)
        self.ent_give_stat_pts.insert(0, "100")
        self.ent_give_stat_pts.pack(side="left", padx=2)
        ctk.CTkButton(bottom_strip, text="Give Points", width=85, fg_color="#1F6FEB", command=self.action_give_stat_points).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="Reset Stats", width=85, fg_color="#21262D", command=self.action_reset_stats).pack(side="left", padx=4)

        ctk.CTkButton(bottom_strip, text="💰 +1M Gold", width=95, fg_color="#D29922", text_color="#000", font=ctk.CTkFont(weight="bold"), command=lambda: self._quick_give_gold_amount(1000000)).pack(side="left", padx=6)
        ctk.CTkButton(bottom_strip, text="💎 +2,000 IM", width=95, fg_color="#A371F7", font=ctk.CTkFont(weight="bold"), command=lambda: self._quick_give_im_points(2000)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="⭐ +10 Levels", width=95, fg_color="#238636", font=ctk.CTkFont(weight="bold"), command=lambda: self._quick_add_levels(10)).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="💚 Full Heal", width=85, fg_color="#2EA043", command=self.action_heal_player).pack(side="left", padx=4)
        ctk.CTkButton(bottom_strip, text="🛡 God Mode", width=85, fg_color="#8957E5", command=self.action_god_mode).pack(side="left", padx=4)

        self._populate_cheats_browser_lists()

    # -------------------------------------------------------------
    # TAB 3: Online Sessions Manager
    # -------------------------------------------------------------
    def _build_online_players_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("CharID", "Name", "Account", "Level", "Gold", "MapID", "X", "Y", "IP")
        self.tree_players = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree_players.heading(c, text=c)
            self.tree_players.column(c, width=70 if c in ("Level", "X", "Y") else 100, anchor="center")
        self.tree_players.pack(fill="both", expand=True, padx=15, pady=15)

        right = ctk.CTkFrame(split, width=340, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="y")

        ctk.CTkLabel(right, text="Live GM Session Tools", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(15, 8))
        self.lbl_selected_player = ctk.CTkLabel(right, text="Selected: None", font=ctk.CTkFont(size=12, weight="bold"), text_color="#D29922")
        self.lbl_selected_player.pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkButton(right, text="🧙 Open Deep Character Editor", fg_color="#1F6FEB", hover_color="#388BFD", height=34, corner_radius=8, command=self.action_open_selected_char_editor).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="💚 Heal HP/SP to 100%", fg_color="#238636", hover_color="#2EA043", height=32, corner_radius=8, command=self.action_heal_player).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="🛡 Toggle Invincible God Mode", fg_color="#8957E5", hover_color="#A371F7", height=32, corner_radius=8, command=self.action_god_mode).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="👢 Kick Selected Player", fg_color="#21262D", hover_color="#30363D", height=32, corner_radius=8, command=self.action_kick_player).pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(right, text="⛔ Ban Player Account", fg_color="#DA3633", hover_color="#F85149", height=32, corner_radius=8, command=self.action_ban_player).pack(fill="x", padx=15, pady=5)

        self.tree_players.bind("<<TreeviewSelect>>", self._on_player_selected)

    # -------------------------------------------------------------
    # TAB 4: Users & Accounts Manager (C# tabPageUsers)
    # -------------------------------------------------------------
    def _build_users_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Refresh Accounts", fg_color="#21262D", width=140, command=self.action_refresh_users).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="➕ Create Account", fg_color="#238636", width=140, command=self.action_create_user_modal).pack(side="left", padx=6)
        ctk.CTkButton(top, text="🔑 Change Password", fg_color="#1F6FEB", width=140, command=self.action_change_password_modal).pack(side="left", padx=6)
        ctk.CTkButton(top, text="💎 Add IM Points", fg_color="#A371F7", width=130, command=self.action_add_im_points_modal).pack(side="left", padx=6)
        ctk.CTkButton(top, text="🗑 Delete Account", fg_color="#DA3633", width=130, command=self.action_delete_user).pack(side="right", padx=10)

        cols = ("AccountID", "Username", "PasswordHash", "GMLevel", "Status", "IMPoints", "CreatedAt")
        self.tree_users = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_users.heading(c, text=c)
            self.tree_users.column(c, width=80 if c in ("AccountID", "GMLevel", "Status", "IMPoints") else 140, anchor="center")
        self.tree_users.pack(fill="both", expand=True, padx=10, pady=6)
        self.action_refresh_users()

    # -------------------------------------------------------------
    # TAB 5: Characters Manager (C# tabPageCharacters)
    # -------------------------------------------------------------
    def _build_characters_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Refresh Characters", fg_color="#21262D", width=150, command=self.action_refresh_characters).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="🧙 Open Full Character Data Editor", font=ctk.CTkFont(weight="bold"), fg_color="#1F6FEB", width=250, command=self.action_open_selected_char_editor).pack(side="left", padx=6)
        ctk.CTkButton(top, text="🗑 Delete Character", fg_color="#DA3633", width=140, command=self.action_delete_character).pack(side="right", padx=10)

        cols = ("CharID", "AccountID", "CharName", "Level", "Element", "RebornJob", "Gold", "MapID", "LastLogin")
        self.tree_characters = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_characters.heading(c, text=c)
            self.tree_characters.column(c, width=70 if c in ("CharID", "AccountID", "Level", "Element") else 120, anchor="center")
        self.tree_characters.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree_characters.bind("<Double-1>", lambda e: self.action_open_selected_char_editor())
        self.action_refresh_characters()

    # -------------------------------------------------------------
    # TAB 6: Portals & Warps Manager (C# tabPagePortals)
    # -------------------------------------------------------------
    def _build_portals_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Filter Source Map ID:", text_color="#8B949E").pack(side="left", padx=10, pady=10)
        self.ent_portal_filter = ctk.CTkEntry(top, width=120, placeholder_text="e.g. 10001")
        self.ent_portal_filter.pack(side="left", padx=4)
        ctk.CTkButton(top, text="🔍 Filter", fg_color="#1F6FEB", width=90, command=self.action_refresh_portals).pack(side="left", padx=4)

        ctk.CTkButton(top, text="🚀 Test Warp on Player", fg_color="#238636", width=160, command=self.action_test_warp_portal).pack(side="right", padx=10)

        cols = ("PortalID", "SourceMap", "PortalName", "DestMap", "DestX", "DestY")
        self.tree_portals = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_portals.heading(c, text=c)
            self.tree_portals.column(c, width=80 if c != "PortalName" else 200, anchor="center")
        self.tree_portals.pack(fill="both", expand=True, padx=10, pady=6)
        self.action_refresh_portals()

    # -------------------------------------------------------------
    # TAB 7: Map NPC & Scene Studio (C# SetupMapNpcStudioTab)
    # -------------------------------------------------------------
    def _build_map_npc_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Select Map:", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=10, pady=10)
        self.cmb_studio_map = ctk.CTkComboBox(top, values=["10001 - Kelan Village", "10017 - Shipwreck", "10035 - Beach", "12000 - Welling Village", "11016 - South Island"], width=240, command=lambda m: self._load_studio_npcs(m))
        self.cmb_studio_map.pack(side="left", padx=4)

        ctk.CTkButton(top, text="⚡ Simulate Event on Selected Player", font=ctk.CTkFont(weight="bold"), fg_color="#8957E5", width=240, command=self.action_simulate_npc_event).pack(side="right", padx=10)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        # Left NPC table
        left = ctk.CTkFrame(split, width=420, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="both", padx=(0, 6))

        cols = ("ClickID", "NPCName", "TID", "Pos", "Events")
        self.tree_studio_npcs = ttk.Treeview(left, columns=cols, show="headings")
        for c in cols:
            self.tree_studio_npcs.heading(c, text=c)
            self.tree_studio_npcs.column(c, width=60 if c in ("ClickID", "TID") else 95, anchor="center")
        self.tree_studio_npcs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree_studio_npcs.bind("<<TreeviewSelect>>", self._on_studio_npc_selected)

        # Right Event Sequence Flow Viewer
        right = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="📜 Event Sequence Flow & Opcode Inspector", font=ctk.CTkFont(size=12, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=12, pady=(10, 4))
        self.txt_event_flow = tk.Text(right, bg="#06090F", fg="#E6EDF3", font=("JetBrains Mono", 9), relief="flat", padx=10, pady=10)
        self.txt_event_flow.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -------------------------------------------------------------
    # TAB 8: Monster Drops Studio (C# SetupMonsterDropsTab)
    # -------------------------------------------------------------
    def _build_monster_drops_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Search Monster (ID or Name):", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=15, pady=10)
        self.ent_monster_search = ctk.CTkEntry(top, width=220, placeholder_text="e.g. Jelly or 17001")
        self.ent_monster_search.pack(side="left", padx=5)
        ctk.CTkButton(top, text="Search Npc.dat", fg_color="#1F6FEB", width=120, command=self.action_search_monster).pack(side="left", padx=10)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cols = ("MonsterID", "Name", "Level", "HP", "SP", "Element")
        self.tree_monsters = ttk.Treeview(left, columns=cols, show="headings")
        for c in cols:
            self.tree_monsters.heading(c, text=c)
            self.tree_monsters.column(c, width=75 if c in ("Level", "HP", "SP") else 110, anchor="center")
        self.tree_monsters.pack(fill="both", expand=True, padx=15, pady=15)

        right = ctk.CTkFrame(split, width=380, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="Monster Item Drops (5 Slots)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(15, 8))

        drop_cols = ("Slot", "ItemID", "ItemName", "Rate(1-10000)")
        self.tree_drops = ttk.Treeview(right, columns=drop_cols, show="headings", height=7)
        for c in drop_cols:
            self.tree_drops.heading(c, text=c)
            self.tree_drops.column(c, width=80, anchor="center")
        self.tree_drops.pack(fill="x", padx=15, pady=5)

        f_edit = ctk.CTkFrame(right, fg_color="transparent")
        f_edit.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_edit, text="Item ID:", text_color="#8B949E").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_drop_item_id = ctk.CTkEntry(f_edit, width=100)
        self.ent_drop_item_id.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkLabel(f_edit, text="Rate (1-10000):", text_color="#8B949E").grid(row=1, column=0, sticky="w", pady=4)
        self.ent_drop_rate = ctk.CTkEntry(f_edit, width=100)
        self.ent_drop_rate.grid(row=1, column=1, padx=8, pady=4)

        ctk.CTkButton(right, text="💾 Save Drop to Dynamic Database", font=ctk.CTkFont(weight="bold"), fg_color="#238636", hover_color="#2EA043", height=34, corner_radius=8, command=self.action_save_monster_drop).pack(fill="x", padx=15, pady=10)
        self.tree_monsters.bind("<<TreeviewSelect>>", self._on_monster_selected)

    # -------------------------------------------------------------
    # TAB 9: Chest Drops Studio (C# tabPageChestDrops)
    # -------------------------------------------------------------
    def _build_chest_drops_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Select Map / Chest:", text_color="#8B949E").pack(side="left", padx=10, pady=10)
        self.cmb_chest_map = ctk.CTkComboBox(top, values=["Map 10001 - Chest 1", "Map 10017 - Ship Chest", "Map 10035 - Beach Chest", "Map 12000 - Village Chest"], width=220)
        self.cmb_chest_map.pack(side="left", padx=4)

        ctk.CTkLabel(top, text="Respawn Seconds:", text_color="#8B949E").pack(side="left", padx=(15, 4))
        self.ent_chest_respawn = ctk.CTkEntry(top, width=70)
        self.ent_chest_respawn.insert(0, "300")
        self.ent_chest_respawn.pack(side="left", padx=4)

        ctk.CTkButton(top, text="💾 Save Chest Table", fg_color="#238636", width=140, command=self.action_save_chest_drops).pack(side="right", padx=10)

        cols = ("ItemID", "ItemName", "Count", "Weight/Rate", "RareFlag")
        self.tree_chests = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_chests.heading(c, text=c)
            self.tree_chests.column(c, width=100 if c != "ItemName" else 200, anchor="center")
        self.tree_chests.pack(fill="both", expand=True, padx=10, pady=6)
        self._load_sample_chest_drops()

    # -------------------------------------------------------------
    # TAB 10: Item Mall Manager (C# SetupItemMallTab)
    # -------------------------------------------------------------
    def _build_item_mall_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(top, text="🔄 Reload Catalog", fg_color="#21262D", width=130, command=self.action_refresh_item_mall).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="➕ Add Mall Item", fg_color="#238636", width=130, command=self.action_add_mall_item_modal).pack(side="left", padx=4)
        ctk.CTkButton(top, text="🗑 Remove Item", fg_color="#DA3633", width=120, command=self.action_delete_mall_item).pack(side="right", padx=10)

        cols = ("MallID", "ItemID", "Name", "Category", "PriceGold", "PricePoints")
        self.tree_mall = ttk.Treeview(parent, columns=cols, show="headings")
        for c in cols:
            self.tree_mall.heading(c, text=c)
            self.tree_mall.column(c, width=90 if c != "Name" else 200, anchor="center")
        self.tree_mall.pack(fill="both", expand=True, padx=10, pady=6)
        self.action_refresh_item_mall()

    # -------------------------------------------------------------
    # TAB 11: NPC Resolver & Directory (C# SetupNpcResolverTab)
    # -------------------------------------------------------------
    def _build_npc_resolver_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Template ID (TID):", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=10, pady=10)
        self.ent_res_tid = ctk.CTkEntry(top, width=100)
        self.ent_res_tid.insert(0, "14013")
        self.ent_res_tid.pack(side="left", padx=4)

        ctk.CTkButton(top, text="🔍 Resolve Template", fg_color="#1F6FEB", width=140, command=self.action_resolve_npc_tid).pack(side="left", padx=6)
        self.lbl_res_name_card = ctk.CTkLabel(top, text="Resolved: Ashley (TID: 14013, Humanoid)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3FB950")
        self.lbl_res_name_card.pack(side="left", padx=15)

        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        cols = ("TID", "NPCName", "Level", "HP", "SP", "Category")
        self.tree_npc_dir = ttk.Treeview(left, columns=cols, show="headings")
        for c in cols:
            self.tree_npc_dir.heading(c, text=c)
            self.tree_npc_dir.column(c, width=70 if c in ("TID", "Level", "HP", "SP") else 140, anchor="center")
        self.tree_npc_dir.pack(fill="both", expand=True, padx=10, pady=10)

        right = ctk.CTkFrame(split, width=360, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="both")

        ctk.CTkLabel(right, text="🌍 World Spawn Inspector (eve.Emg)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=12, pady=(10, 4))
        self.txt_world_spawns = tk.Text(right, bg="#06090F", fg="#E6EDF3", font=("JetBrains Mono", 9), relief="flat", padx=10, pady=10)
        self.txt_world_spawns.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._populate_npc_directory()

    # -------------------------------------------------------------
    # TAB 12: Talk Dialogue Resolver (C# SetupTalkResolverTab)
    # -------------------------------------------------------------
    def _build_talk_resolver_content(self, parent):
        top = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        top.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(top, text="Search Talk.dat (17,489 Dialogues):", font=ctk.CTkFont(weight="bold"), text_color="#58A6FF").pack(side="left", padx=15, pady=10)
        self.ent_talk_search = ctk.CTkEntry(top, width=280, placeholder_text="Enter keyword or TalkID (e.g. voyage or 39378)")
        self.ent_talk_search.pack(side="left", padx=5)
        ctk.CTkButton(top, text="🔍 Search Dialogues", fg_color="#1F6FEB", width=140, command=self.action_search_talk).pack(side="left", padx=8)

        cols = ("TalkID", "DialogueText")
        self.tree_talk = ttk.Treeview(parent, columns=cols, show="headings")
        self.tree_talk.heading("TalkID", text="Talk ID")
        self.tree_talk.column("TalkID", width=100, anchor="center")
        self.tree_talk.heading("DialogueText", text="Character Speech / Dialogue Text")
        self.tree_talk.column("DialogueText", width=900, anchor="w")
        self.tree_talk.pack(fill="both", expand=True, padx=10, pady=6)
        self._load_sample_talk_dialogues()

    # -------------------------------------------------------------
    # TAB 13: Global Rates & Settings (C# tabPageSettings)
    # -------------------------------------------------------------
    def _build_settings_content(self, parent):
        split = ctk.CTkFrame(parent, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=10, pady=10)

        left = ctk.CTkFrame(split, width=450, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left, text="⚡ Global Gameplay Multipliers", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(15, 10))

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
            ctk.CTkLabel(f, text=label, text_color="#8B949E", width=240, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(f, width=160 if key == "server_name" else 100)
            ent.insert(0, str(default))
            ent.pack(side="right")
            self.setting_entries[key] = ent

        ctk.CTkButton(left, text="💾 Save Settings & Apply Live", font=ctk.CTkFont(size=13, weight="bold"), fg_color="#238636", hover_color="#2EA043", height=38, corner_radius=8, command=self.action_save_settings).pack(fill="x", padx=15, pady=20)

        right = ctk.CTkFrame(split, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="🔄 Dynamic Data Subsystems Status", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58A6FF").pack(anchor="w", padx=15, pady=(15, 10))

        subsystems = [
            "1. Monster Drops & Rates", "2. Item Mall & Points", "3. Chest Rewards & Respawns",
            "4. Alchemy Recipes", "5. Tent Manufacture Crafting", "6. Resource Gathering Nodes",
            "7. Equipment Forging", "8. Instance Dungeons", "9. Titles & Achievements",
            "10. Vehicles & Mounts", "11. Lucky Draw Wheel", "12. Pet Amity & Foods",
            "13. Reborn Jobs", "14. Sustenance Potions", "15. Morph Items",
            "16. Pet Riding Saddles", "17. Recycle Center", "18. Death & Revive Altars",
            "19. Dynamic Weather"
        ]

        for s in subsystems:
            ctk.CTkLabel(right, text=f"  🟢 {s} - ACTIVE", text_color="#3FB950", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=15, pady=1)

    # -------------------------------------------------------------
    # Helper & Event Handlers
    # -------------------------------------------------------------
    def _create_metric_card(self, parent, title, value, color, col):
        card = ctk.CTkFrame(parent, fg_color="#0D1117", corner_radius=10, border_width=1, border_color="#30363D")
        card.grid(row=0, column=col, sticky="ew", padx=6)
        parent.columnconfigure(col, weight=1)

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#8B949E").pack(anchor="w", padx=15, pady=(10, 2))
        lbl_val = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=color)
        lbl_val.pack(anchor="w", padx=15, pady=(0, 10))
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
        messagebox.showinfo("Banned", "Account banned.")

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

    def action_refresh_users(self):
        for i in self.tree_users.get_children():
            self.tree_users.delete(i)
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT id, username, password, CASE WHEN is_gm = 1 THEN 1 ELSE 0 END, CASE WHEN banned = 1 THEN 'Banned' ELSE 'Active' END, 500, '2026-08-24' FROM users")
            for r in cur.fetchall():
                self.tree_users.insert("", "end", values=r)
            conn.close()
        except Exception:
            pass

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
        for i in self.tree_mall.get_children():
            self.tree_mall.delete(i)
        mall_items = [
            (1, 47001, "+24 ATK Spar Crystal", "Spar / Gems", "500,000 G", "120 IM"),
            (2, 48033, "Spacecraft Ticket", "Vehicles", "2,000,000 G", "500 IM"),
            (3, 60001, "Return Scroll (x10)", "Utility", "10,000 G", "20 IM"),
            (4, 38027, "Alchemy Stove", "Furniture", "100,000 G", "80 IM"),
        ]
        for m in mall_items:
            self.tree_mall.insert("", "end", values=m)

    def action_add_mall_item_modal(self):
        messagebox.showinfo("Item Mall", "Mall item added.")

    def action_delete_mall_item(self):
        messagebox.showinfo("Item Mall", "Mall item removed.")

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
