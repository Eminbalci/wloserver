"""
Wonderland Online Master Quest Engine
Ported from C# wlo.pserver.core/Game/QuestRelated and DataBase/QuestDataBase
"""

import os
import re
import time
import struct
import logging
from enum import IntEnum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")


class QuestState(IntEnum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3


class QuestType(IntEnum):
    DIALOGUE = 0
    ITEM_COLLECTION = 1
    MONSTER_BATTLE = 2
    DELIVERY = 3
    EXPLORATION = 4


@dataclass
class QuestRequirementItem:
    item_id: int
    amount: int
    item_name: str = ""


@dataclass
class QuestReward:
    gold: int = 0
    exp: int = 0
    companion_pet_id: int = 0
    companion_name: str = ""
    items: List[Tuple[int, int]] = field(default_factory=list)

    def add_item(self, item_id: int, count: int = 1) -> "QuestReward":
        self.items.append((item_id, count))
        return self


@dataclass
class QuestStep:
    step_index: int = 1
    target_npc_template_id: int = 0
    target_npc_pattern: str = ""
    step_type: QuestType = QuestType.DIALOGUE
    prompt_dialogue: str = ""
    in_progress_dialogue: str = ""
    complete_dialogue: str = ""
    required_items: List[QuestRequirementItem] = field(default_factory=list)
    grant_items_on_step: List[Tuple[int, int]] = field(default_factory=list)
    step_reward: Optional[QuestReward] = None
    battle_monster_id: int = 0
    battle_monster_name: str = ""


@dataclass
class QuestDefinition:
    quest_id: int
    title: str
    npc_name_pattern: str = ""
    type: QuestType = QuestType.ITEM_COLLECTION
    map_id: int = 0
    description: str = ""
    required_level: int = 1
    npc_template_id: int = 0
    category: str = "🏝️ Storyline & Area"
    area_name: str = "Unknown"
    in_progress_mark_id: int = 0
    completed_mark_id: int = 0
    all_linked_mark_ids: List[int] = field(default_factory=list)
    required_items: List[QuestRequirementItem] = field(default_factory=list)
    reward: QuestReward = field(default_factory=QuestReward)
    intro_dialogue: str = ""
    in_progress_dialogue: str = ""
    complete_dialogue: str = ""
    already_completed_dialogue: str = ""
    battle_monster_id: int = 0
    battle_monster_name: str = ""
    prerequisite_quest_ids: List[int] = field(default_factory=list)
    despawn_npc_click_ids: List[int] = field(default_factory=list)
    despawn_npc_template_ids: List[int] = field(default_factory=list)
    relocate_to_map_id: int = 0
    steps: List[QuestStep] = field(default_factory=list)

    def add_prerequisite_quest(self, quest_id: int) -> "QuestDefinition":
        if quest_id not in self.prerequisite_quest_ids:
            self.prerequisite_quest_ids.append(quest_id)
        return self

    def add_step(self, step: QuestStep) -> "QuestDefinition":
        if step is not None:
            step.step_index = len(self.steps) + 1
            self.steps.append(step)
        return self


@dataclass
class PlayerQuest:
    quest_id: int
    state: QuestState = QuestState.IN_PROGRESS
    step: int = 1
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class QuestEngine:
    """Master runtime quest engine for Wonderland Online."""

    def __init__(self, static_db_path: str = "server/ServerDataBase.db"):
        self.static_db_path = static_db_path
        self._registered_quests: Dict[int, QuestDefinition] = {}
        self._master_quests: Dict[int, QuestDefinition] = {}
        self._npc_name_cache: Dict[int, str] = {}
        self._npc_tid_by_name: Dict[str, int] = {}
        self._initialized = False

    @property
    def all_quests(self) -> Dict[int, QuestDefinition]:
        return self._registered_quests

    @property
    def master_quests(self) -> Dict[int, QuestDefinition]:
        return self._master_quests

    def initialize(self, base_dir: Optional[str] = None):
        """Initializes the quest engine and loads quests from Mark.dat / database."""
        if self._initialized:
            return

        self._registered_quests.clear()
        self._master_quests.clear()

        # Load NPC name cache from database if available
        self._ensure_npc_cache()

        # Try loading authentic quests from data/Mark.dat
        if not base_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        mark_dat_path = os.path.join(base_dir, "data", "Mark.dat")
        if not os.path.exists(mark_dat_path):
            mark_dat_path = os.path.join(base_dir, "..", "data", "Mark.dat")

        if os.path.exists(mark_dat_path):
            self.load_authentic_quests_from_mark_dat(mark_dat_path)
        else:
            logger.warning(f"[QuestEngine] Mark.dat not found at {mark_dat_path}")

        self._initialized = True
        logger.info(f"[QuestEngine] Initialized with {len(self._registered_quests)} registered quests ({len(self._master_quests)} master quests).")

    def _ensure_npc_cache(self):
        """Builds NPC name lookup cache from static database."""
        if self._npc_name_cache:
            return

        import sqlite3
        if not os.path.exists(self.static_db_path):
            return

        try:
            conn = sqlite3.connect(self.static_db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, name FROM npc_data").fetchall()
            for r in rows:
                nid = int(r["id"])
                raw_name = (r["name"] or "").split("\x00")[0].strip()
                if raw_name:
                    self._npc_name_cache[nid] = raw_name
                    lower = raw_name.lower()
                    if lower not in self._npc_tid_by_name:
                        self._npc_tid_by_name[lower] = nid
            conn.close()
        except Exception as e:
            logger.warning(f"[QuestEngine] Error building NPC cache: {e}")

    def get_npc_name(self, tid: int) -> str:
        self._ensure_npc_cache()
        return self._npc_name_cache.get(tid, f"NPC #{tid}")

    def resolve_default_npc_tid(self, pattern: str, title: str, area: str) -> int:
        if not pattern and not title:
            return 0

        self._ensure_npc_cache()

        if pattern:
            p_lower = pattern.strip().lower()
            if p_lower in self._npc_tid_by_name:
                return self._npc_tid_by_name[p_lower]

            for name_lower, tid in self._npc_tid_by_name.items():
                if name_lower == p_lower or name_lower in p_lower or p_lower in name_lower:
                    return tid

        if title:
            t_lower = title.strip().lower()
            for name_lower, tid in self._npc_tid_by_name.items():
                if len(name_lower) >= 3 and name_lower in t_lower:
                    return tid

        return 0

    def extract_npc_pattern(self, title: str, body: str) -> str:
        self._ensure_npc_cache()
        full = f"{title or ''} {body or ''}".lower().strip()

        for name_lower, tid in self._npc_tid_by_name.items():
            if len(name_lower) >= 3 and name_lower in full:
                return self._npc_name_cache.get(tid, name_lower.title())

        cleaned_title = self._clean_string(title)
        cleaned_title = re.sub(r"^(Don't Leave!|Death of|Save|Help|Find|The|A)\s*", "", cleaned_title, flags=re.IGNORECASE).strip("!?. ")
        return cleaned_title if cleaned_title else self._clean_string(title)

    def extract_area_from_text(self, title: str, body: str) -> str:
        full = f"{title or ''} {body or ''}".lower()

        if "south pole" in full or "iceberg" in full or "glacier" in full: return "South Pole"
        if "mayan" in full or "alien base" in full or "stone door" in full or "dentist" in full: return "Maya"
        if "kelan" in full: return "Kelan Village"
        if "weiling" in full or "welling" in full: return "Welling Village"
        if "holy village" in full or "cathedral" in full or "church" in full: return "Holy Village"
        if "north island" in full: return "North Island"
        if "south island" in full: return "South Island"
        if "kelp" in full: return "Kelp Island"
        if "japan" in full or "kyoto" in full or "edo" in full: return "Japan"
        if "china" in full or "chang'an" in full or "great wall" in full: return "China"
        if "egypt" in full or "pyramid" in full or "nile" in full: return "Egypt"
        if "maya" in full: return "Maya"
        if "persia" in full or "persian" in full: return "Persia"
        if "rome" in full or "roman" in full or "colosseum" in full: return "Rome"
        if "athens" in full or "greece" in full or "athenian" in full: return "Athens"
        if "dragon palace" in full or "dragon ball" in full: return "Dragon Palace"
        if "ghost ship" in full or "pirate ship" in full: return "Ghost Ship"
        if "bangkok" in full or "thailand" in full or "siam" in full: return "Bangkok"
        if "india" in full or "taj mahal" in full: return "India"
        if "australia" in full or "sydney" in full: return "Australia"
        if "hawaii" in full or "honolulu" in full: return "Hawaii"
        if "korea" in full or "seoul" in full: return "Korea"
        if "cornwell" in full or "cornwall" in full: return "Cornwell"

        return "North Island"

    def determine_quest_category(self, title: str, area: str) -> str:
        t = (title or "").lower()
        a = (area or "").lower()

        if any(x in t for x in ["roca", "niss", "clive", "sasha", "xaolan", "sam", "shizune", "elin", "victoria", "angela", "suzuru", "eva", "robinson", "fred", "magellan", "kanako", "charlotte", "rebirth", "reincarnation", "skill master"]):
            return "👥 Companion & Rebirth"
        if any(x in t for x in ["raft", "canoe", "ship", "boat", "airplane", "rocket", "ufo", "tent", "craftsman", "alchemy", "make a"]):
            return "🛠️ Crafting & Vehicles"
        if any(x in t for x in ["whack", "collect", "contest", "quiz", "test", "game"]):
            return "🎯 Minigames & Challenges"
        if any(x in t for x in ["zodiac", "trial", "ghost", "dragon", "round", "palace", "tower", "cave", "pirate"]):
            return "🐉 Dungeons & Instances"
        return "🏝️ Storyline & Area"

    def resolve_default_map_id(self, area: str, title: str, description: str) -> int:
        full = f"{area or ''} {title or ''} {description or ''}".lower()

        if "cathedral" in full or "church" in full: return 10017
        if "kelan" in full: return 10001
        if "holy village" in full: return 10010
        if "weiling" in full or "welling" in full: return 10020
        if "south pole" in full or "iceberg" in full or "matchstick" in full: return 11001
        if "kelp" in full: return 12001
        if "japan" in full or "kyoto" in full or "edo" in full: return 13001
        if "china" in full or "chang'an" in full or "great wall" in full: return 14001
        if "egypt" in full or "pyramid" in full or "nile" in full: return 15001
        if "maya" in full: return 16001
        if "persia" in full: return 17001
        if "rome" in full or "colosseum" in full: return 18001
        if "athens" in full or "greece" in full: return 19001
        if "dragon palace" in full or "dragon ball" in full: return 21001
        if "ghost ship" in full or "pirate" in full: return 22001
        if "bangkok" in full or "thailand" in full: return 23001
        if "india" in full or "taj mahal" in full: return 24001
        if "australia" in full or "sydney" in full: return 25001
        if "hawaii" in full or "honolulu" in full: return 26001
        if "korea" in full or "seoul" in full: return 27001
        if "cornwell" in full or "cornwall" in full: return 28001
        if "south island" in full: return 11000

        return 10000

    def generate_default_reward(self, title: str, npc_pattern: str) -> QuestReward:
        full = f"{title or ''} {npc_pattern or ''}".lower()

        if "sasha" in full: return QuestReward(2000, 5000, 10012, "Sasha")
        if "roca" in full: return QuestReward(1500, 4000, 10014, "Roca")
        if "niss" in full: return QuestReward(1500, 4000, 10016, "Niss")
        if "clive" in full: return QuestReward(3000, 8000, 10018, "Clive")
        if "sam" in full: return QuestReward(2500, 6000, 10020, "Sam")
        if "elin" in full: return QuestReward(3500, 10000, 10022, "Elin")
        if "shizune" in full: return QuestReward(4000, 12000, 10024, "Shizune")
        if "victoria" in full: return QuestReward(4500, 15000, 10026, "Victoria")
        if "angela" in full: return QuestReward(5000, 18000, 10028, "Angela")
        if "eva" in full: return QuestReward(5000, 20000, 10030, "Eva")
        if "robinson" in full: return QuestReward(3000, 10000, 12032, "Robinson")

        return QuestReward(500, 1000)

    def determine_step_type(self, text: str) -> QuestType:
        t = (text or "").lower()
        if any(x in t for x in ["defeat", "kill", "monster", "guard", "battle"]):
            return QuestType.MONSTER_BATTLE
        if any(x in t for x in ["give", "bring", "collect", "water", "item", "wine", "egg"]):
            return QuestType.ITEM_COLLECTION
        if any(x in t for x in ["door", "maze", "cave", "find", "go ahead", "leave here", "drift ashore", "grovel", "reach"]):
            return QuestType.EXPLORATION
        return QuestType.DIALOGUE

    def determine_step_target(self, text: str, default_npc: str) -> str:
        t = (text or "").lower()
        if "stone door" in t or "secret door" in t or "door" in t: return "Stone Door / Entrance"
        if "alien base" in t or "mayan cave" in t or "cave" in t: return "Secret Cave Passage"
        if "astrologer" in t: return "Astrologer"
        if "matchstick girl" in t: return "Matchstick Girl"
        if "father" in t: return "Father"
        if "roca" in t: return "Roca"
        if "sasha" in t: return "Sasha"
        if "monkey" in t: return "Little Monkey"
        if "priest" in t: return "Priest"
        if "guard" in t: return "Guard"
        if "leader" in t or "chief" in t: return "Village Leader"
        if "dentist" in t: return "Dentist"
        if "zhuang zhi" in t: return "Zhuang Zhi"
        if "granny" in t: return "Granny"
        if "villager" in t: return "Villager"
        return default_npc if default_npc else "Quest NPC"

    def _extract_reversed_string(self, data: bytes, start: int, max_len: int) -> str:
        chars = []
        end = min(len(data), start + max_len)
        for i in range(start, end):
            b = data[i]
            if 32 <= b <= 126:
                chars.append(chr(b))
            else:
                if len(chars) >= 3:
                    chars.reverse()
                    s = "".join(chars).strip()
                    if "'s's's" not in s and s not in ("0", "s'", "'s"):
                        return s
                chars.clear()
        if len(chars) >= 3:
            chars.reverse()
            s = "".join(chars).strip()
            if "'s's's" not in s and s not in ("0", "s'", "'s"):
                return s
        return ""

    def _clean_string(self, s: str) -> str:
        if not s:
            return ""
        cleaned = s.replace("s's's's's'", "").replace("'s's's's's'", "").replace("s's's", "").strip()
        if cleaned in ("s'", "'s", "0"):
            return ""
        filtered = [c for c in cleaned if 32 <= ord(c) <= 126 and c not in ("&", "$", "`")]
        return "".join(filtered).strip()

    def load_authentic_quests_from_mark_dat(self, file_path: str):
        """Parses binary Mark.dat and constructs all Master Quests."""
        if not os.path.exists(file_path):
            return

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            if len(data) < 256:
                return

            num_records = len(data) // 553
            loaded_count = 0
            parsed_list = []

            for mark_id in range(1, num_records + 1):
                offset = (mark_id - 1) * 553
                entry = self._parse_mark_entry(data, offset, mark_id)
                if entry and entry.get("title"):
                    parsed_list.append(entry)

                    q_title = entry["title"]
                    q_npc_pattern = entry.get("npc_pattern") or q_title
                    q_desc = entry.get("description") or q_title
                    q_loc = entry.get("location") or "Unknown"

                    quest = QuestDefinition(
                        quest_id=mark_id,
                        title=q_title,
                        npc_name_pattern=q_npc_pattern,
                        type=QuestType.DIALOGUE,
                        map_id=self.resolve_default_map_id(q_loc, q_title, q_desc),
                        npc_template_id=self.resolve_default_npc_tid(q_npc_pattern, q_title, q_loc),
                        description=q_desc,
                        intro_dialogue=entry.get("intro_dialogue") or q_desc,
                        in_progress_dialogue=entry.get("in_progress_dialogue") or q_desc,
                        complete_dialogue=entry.get("completed_summary") or q_desc,
                        already_completed_dialogue=entry.get("completed_summary") or q_desc,
                        category=self.determine_quest_category(q_title, q_loc),
                        area_name=q_loc,
                        in_progress_mark_id=mark_id,
                        completed_mark_id=mark_id,
                        reward=self.generate_default_reward(q_title, q_npc_pattern),
                    )

                    # Multi-stage steps
                    step_descs = entry.get("step_descriptions", [])
                    for idx, s_desc in enumerate(step_descs):
                        s_type = self.determine_step_type(s_desc)
                        s_target = self.determine_step_target(s_desc, quest.npc_name_pattern)
                        comp_text = entry.get("completed_summary") if (idx == len(step_descs) - 1 and entry.get("completed_summary")) else s_desc

                        quest.add_step(QuestStep(
                            step_index=idx + 1,
                            target_npc_template_id=quest.npc_template_id,
                            target_npc_pattern=s_target,
                            step_type=s_type,
                            prompt_dialogue=s_desc,
                            in_progress_dialogue=s_desc,
                            complete_dialogue=comp_text or s_desc,
                        ))

                    self._registered_quests[mark_id] = quest
                    loaded_count += 1

            # Build Master Quests by pairing consecutive in-progress and completed marks
            self._build_master_quests(parsed_list)
            logger.info(f"[QuestEngine] Loaded {loaded_count} authentic Mark.dat entries into {len(self._master_quests)} structured Master Quests.")
        except Exception as e:
            logger.error(f"[QuestEngine] Error reading Mark.dat: {e}", exc_info=True)

    def _parse_mark_entry(self, data: bytes, offset: int, mark_id: int) -> Optional[Dict[str, Any]]:
        try:
            # 1. Extract Title from [200..265]
            title = self._extract_reversed_string(data, offset + 200, 65)
            if not title or title.startswith("Visit Mark") or title.startswith("Time Mark") or title.startswith("Quest Mark"):
                return None

            # 2. Extract Body from [266..525]
            body = self._extract_reversed_string(data, offset + 266, 260)
            if not body or body.startswith("Visit Mark") or body.startswith("Time Mark") or body.startswith("Visit Mar") or body.startswith("Time Mar") or body == "Quest Mark" or (body == title and title in ("North Island", "South Island", "Maya", "Japan", "China", "Egypt")):
                return None

            cleaned_title = self._clean_string(title)
            npc_pattern = self.extract_npc_pattern(cleaned_title, body)
            location = self.extract_area_from_text(cleaned_title, body)

            entry = {
                "mark_id": mark_id,
                "title": cleaned_title,
                "npc_pattern": npc_pattern,
                "location": location,
                "step_descriptions": [],
                "completed_summary": "",
                "description": "",
                "intro_dialogue": "",
                "in_progress_dialogue": ""
            }

            if "#" in body:
                matches = re.findall(r"#(\d{2})([^#]*)", body)
                for step_num, step_text_raw in matches:
                    step_text = self._clean_string(step_text_raw)
                    if not step_text or step_text in ("s'", "'s"):
                        continue
                    if step_num == "99":
                        entry["completed_summary"] = step_text
                    else:
                        entry["step_descriptions"].append(step_text)

                if entry["step_descriptions"]:
                    entry["intro_dialogue"] = entry["step_descriptions"][0]
                if len(entry["step_descriptions"]) > 1:
                    entry["in_progress_dialogue"] = " ".join(entry["step_descriptions"][1:3])
                elif entry["step_descriptions"]:
                    entry["in_progress_dialogue"] = entry["step_descriptions"][0]

                if entry["completed_summary"]:
                    entry["description"] = entry["completed_summary"]
                elif entry["step_descriptions"]:
                    entry["description"] = entry["step_descriptions"][0]
                else:
                    entry["description"] = self._clean_string(body)
            else:
                cleaned_body = self._clean_string(body)
                entry["description"] = cleaned_body
                entry["intro_dialogue"] = cleaned_body
                entry["in_progress_dialogue"] = cleaned_body
                entry["completed_summary"] = cleaned_body

            return entry
        except Exception:
            return None

    def _build_master_quests(self, marks: List[Dict[str, Any]]):
        self._master_quests.clear()
        processed = set()

        i = 0
        while i < len(marks):
            m = marks[i]
            mark_id = m["mark_id"]
            if mark_id in processed:
                i += 1
                continue

            q_title = m["title"]
            q_pattern = m.get("npc_pattern") or q_title
            q_desc = m.get("description") or q_title
            q_loc = m.get("location") or "Unknown"

            master = QuestDefinition(
                quest_id=mark_id,
                title=q_title,
                npc_name_pattern=q_pattern,
                type=QuestType.DIALOGUE,
                map_id=self.resolve_default_map_id(q_loc, q_title, q_desc),
                npc_template_id=self.resolve_default_npc_tid(q_pattern, q_title, q_loc),
                description=q_desc,
                intro_dialogue=m.get("intro_dialogue") or q_desc,
                in_progress_dialogue=m.get("in_progress_dialogue") or q_desc,
                complete_dialogue=m.get("completed_summary") or q_desc,
                already_completed_dialogue=m.get("completed_summary") or q_desc,
                category=self.determine_quest_category(q_title, q_loc),
                area_name=q_loc,
                in_progress_mark_id=mark_id,
                completed_mark_id=mark_id,
                reward=self.generate_default_reward(q_title, q_pattern),
            )

            # Steps
            step_descs = m.get("step_descriptions", [])
            for s_idx, s_text in enumerate(step_descs):
                s_type = self.determine_step_type(s_text)
                s_target = self.determine_step_target(s_text, master.npc_name_pattern)
                comp_text = m.get("completed_summary") if (s_idx == len(step_descs) - 1 and m.get("completed_summary")) else s_text

                master.add_step(QuestStep(
                    step_index=s_idx + 1,
                    target_npc_template_id=master.npc_template_id,
                    target_npc_pattern=s_target,
                    step_type=s_type,
                    prompt_dialogue=s_text,
                    in_progress_dialogue=s_text,
                    complete_dialogue=comp_text or s_text,
                ))

            master.all_linked_mark_ids.append(mark_id)
            processed.add(mark_id)

            # Check next entry for paired completion mark
            if i + 1 < len(marks):
                next_m = marks[i + 1]
                next_title = (next_m.get("title") or "").strip().lower()
                cur_title_lower = q_title.strip().lower()

                if next_title and (next_title == cur_title_lower or next_title.startswith(cur_title_lower) or cur_title_lower.startswith(next_title)):
                    master.completed_mark_id = next_m["mark_id"]
                    master.all_linked_mark_ids.append(next_m["mark_id"])
                    if next_m.get("completed_summary"):
                        master.complete_dialogue = next_m["completed_summary"]
                        master.already_completed_dialogue = next_m["completed_summary"]
                    processed.add(next_m["mark_id"])
                    i += 1  # Merged pair

            self._master_quests[master.quest_id] = master
            self._registered_quests[master.quest_id] = master
            i += 1

    def register_quest(self, quest: QuestDefinition):
        if quest:
            self._registered_quests[quest.quest_id] = quest

    def get_quest(self, quest_id: int) -> Optional[QuestDefinition]:
        return self._registered_quests.get(quest_id) or self._master_quests.get(quest_id)

    def _is_npc_match(self, pattern: str, target_tid: int, current_name: str, current_tid: int) -> bool:
        if target_tid > 0 and current_tid > 0 and target_tid == current_tid:
            return True

        if pattern and current_name:
            p = pattern.lower().strip()
            c = current_name.lower().strip()
            if c == p or p in c or c in p:
                return True

        return False

    def find_quest_for_player_npc(
        self,
        player_quests: Dict[int, PlayerQuest],
        npc_name: str,
        template_id: int
    ) -> Tuple[Optional[QuestDefinition], Optional[QuestStep], bool]:
        """
        Finds active or available quest for player interaction with an NPC.
        Returns (quest, matching_step, is_new_quest).
        """
        lower = (npc_name or "").lower().strip()
        if not lower and template_id == 0:
            return None, None, False

        # 1. Check in-progress quests for matching step
        if player_quests:
            for q_id, pq in player_quests.items():
                if pq.state == QuestState.IN_PROGRESS and q_id in self._registered_quests:
                    q = self._registered_quests[q_id]
                    if q.steps:
                        step_idx = max(1, pq.step)
                        if step_idx <= len(q.steps):
                            step = q.steps[step_idx - 1]
                            if (self._is_npc_match(step.target_npc_pattern, step.target_npc_template_id, lower, template_id) or
                                self._is_npc_match(q.npc_name_pattern, q.npc_template_id, lower, template_id)):
                                return q, step, False
                    elif self._is_npc_match(q.npc_name_pattern, q.npc_template_id, lower, template_id):
                        return q, None, False

        # 2. Check for starting new quests (NotStarted) with Prerequisite Quest checks
        for q in self._registered_quests.values():
            if player_quests and q.quest_id in player_quests:
                if player_quests[q.quest_id].state == QuestState.COMPLETED:
                    continue

            # Validate all prerequisite quests
            if q.prerequisite_quest_ids:
                all_prereqs_met = True
                for prereq_id in q.prerequisite_quest_ids:
                    if not player_quests or prereq_id not in player_quests or player_quests[prereq_id].state != QuestState.COMPLETED:
                        all_prereqs_met = False
                        break
                if not all_prereqs_met:
                    continue

            if q.steps:
                first_step = q.steps[0]
                if (self._is_npc_match(first_step.target_npc_pattern, first_step.target_npc_template_id, lower, template_id) or
                    self._is_npc_match(q.npc_name_pattern, q.npc_template_id, lower, template_id)):
                    return q, first_step, True
            elif self._is_npc_match(q.npc_name_pattern, q.npc_template_id, lower, template_id):
                return q, None, True

        # 3. Fallback: Check completed quests for dialogue repetition
        if player_quests:
            for q_id, pq in player_quests.items():
                if pq.state == QuestState.COMPLETED and q_id in self._registered_quests:
                    q = self._registered_quests[q_id]
                    if self._is_npc_match(q.npc_name_pattern, q.npc_template_id, lower, template_id):
                        return q, None, False

        return None, None, False

    async def try_handle_npc_quest(self, server, session, npc_name: str, template_id: int) -> Tuple[bool, str]:
        """
        Handles NPC dialogue and multi-stage quest progression when clicked.
        Returns (handled, dialogue_text).
        """
        if not session or not session.char_id:
            return False, ""

        player_quests = self.get_player_quests_dict(session)
        quest, current_step, is_new_quest = self.find_quest_for_player_npc(player_quests, npc_name, template_id)
        if not quest:
            return False, ""

        if quest.quest_id not in player_quests:
            pq = PlayerQuest(quest.quest_id, QuestState.NOT_STARTED, 1)
            player_quests[quest.quest_id] = pq
        else:
            pq = player_quests[quest.quest_id]

        dialogue = ""

        # A. Multi-Stage Step Progression Engine
        if quest.steps:
            handled, dialogue = await self._handle_multi_step_quest(server, session, quest, pq, current_step, is_new_quest)
            self.save_player_quest(session, quest.quest_id)
            return handled, dialogue

        # B. Single-NPC Legacy Quest Engine
        if pq.state == QuestState.NOT_STARTED:
            if quest.type == QuestType.DIALOGUE:
                await self.grant_rewards(server, session, quest)
                pq.state = QuestState.COMPLETED
                pq.completed_at = time.time()
                self.save_player_quest(session, quest.quest_id)
                await self.send_quest_update(session, quest.quest_id, QuestState.COMPLETED)
                dialogue = quest.complete_dialogue or quest.intro_dialogue
            else:
                pq.state = QuestState.IN_PROGRESS
                pq.step = 1
                self.save_player_quest(session, quest.quest_id)
                await self.send_quest_update(session, quest.quest_id, QuestState.IN_PROGRESS, 1)
                dialogue = quest.intro_dialogue
            return True, dialogue

        elif pq.state == QuestState.IN_PROGRESS:
            if quest.type == QuestType.ITEM_COLLECTION:
                if self.check_and_consume_items(session, quest.required_items):
                    await self.grant_rewards(server, session, quest)
                    pq.state = QuestState.COMPLETED
                    pq.completed_at = time.time()
                    self.save_player_quest(session, quest.quest_id)
                    await self.send_quest_update(session, quest.quest_id, QuestState.COMPLETED)
                    dialogue = quest.complete_dialogue
                else:
                    dialogue = quest.in_progress_dialogue
            elif quest.type == QuestType.MONSTER_BATTLE:
                dialogue = quest.in_progress_dialogue
            else:
                await self.grant_rewards(server, session, quest)
                pq.state = QuestState.COMPLETED
                pq.completed_at = time.time()
                self.save_player_quest(session, quest.quest_id)
                await self.send_quest_update(session, quest.quest_id, QuestState.COMPLETED)
                dialogue = quest.complete_dialogue
            return True, dialogue

        elif pq.state == QuestState.COMPLETED:
            dialogue = quest.already_completed_dialogue or quest.complete_dialogue
            return True, dialogue

        return False, dialogue

    async def _handle_multi_step_quest(
        self,
        server,
        session,
        quest: QuestDefinition,
        pq: PlayerQuest,
        step: Optional[QuestStep],
        is_new_quest: bool
    ) -> Tuple[bool, str]:
        if not step:
            step = quest.steps[0] if quest.steps else None

        if pq.state == QuestState.COMPLETED:
            dialogue = quest.already_completed_dialogue or "Thank you again for your assistance!"
            return True, dialogue

        if is_new_quest or pq.state == QuestState.NOT_STARTED:
            pq.state = QuestState.IN_PROGRESS
            pq.step = 1
            self.save_player_quest(session, quest.quest_id)
            await self.send_quest_update(session, quest.quest_id, QuestState.IN_PROGRESS, 1)
            dialogue = step.prompt_dialogue if step else quest.intro_dialogue
            return True, dialogue

        # In Progress
        if step and step.step_type == QuestType.ITEM_COLLECTION:
            if self.check_and_consume_items(session, step.required_items):
                # Grant step items if any
                from server.gameserver import add_item_to_inventory
                for it_id, count in step.grant_items_on_step:
                    add_item_to_inventory(session, it_id, count)

                if pq.step >= len(quest.steps):
                    await self.grant_rewards(server, session, quest)
                    pq.state = QuestState.COMPLETED
                    pq.completed_at = time.time()
                    self.save_player_quest(session, quest.quest_id)
                    await self.send_quest_update(session, quest.quest_id, QuestState.COMPLETED)
                    dialogue = step.complete_dialogue or quest.complete_dialogue
                else:
                    pq.step += 1
                    self.save_player_quest(session, quest.quest_id)
                    await self.send_quest_update(session, quest.quest_id, QuestState.IN_PROGRESS, pq.step)
                    dialogue = step.complete_dialogue
            else:
                dialogue = step.in_progress_dialogue
        else:
            from server.gameserver import add_item_to_inventory
            if step and step.grant_items_on_step:
                for it_id, count in step.grant_items_on_step:
                    add_item_to_inventory(session, it_id, count)

            if pq.step >= len(quest.steps):
                await self.grant_rewards(server, session, quest)
                pq.state = QuestState.COMPLETED
                pq.completed_at = time.time()
                self.save_player_quest(session, quest.quest_id)
                await self.send_quest_update(session, quest.quest_id, QuestState.COMPLETED)
                dialogue = step.complete_dialogue if step else quest.complete_dialogue
            else:
                pq.step += 1
                self.save_player_quest(session, quest.quest_id)
                await self.send_quest_update(session, quest.quest_id, QuestState.IN_PROGRESS, pq.step)
                dialogue = step.prompt_dialogue if step else (step.complete_dialogue if step else "")

        return True, dialogue

    def check_and_consume_items(self, session, items: List[QuestRequirementItem]) -> bool:
        if not items:
            return True

        from server.gameserver import remove_item_at_slot

        # 1. Verify player has all items
        for req in items:
            total_amt = sum(
                it.get("amount", 1)
                for it in session.inventory
                if it.get("item_id") == req.item_id
            )
            if total_amt < req.amount:
                return False

        # 2. Consume items
        for req in items:
            rem = req.amount
            for it in list(session.inventory):
                if it.get("item_id") == req.item_id:
                    take = min(rem, it.get("amount", 1))
                    slot = it.get("slot")
                    if slot is not None:
                        remove_item_at_slot(session, slot, take)
                    else:
                        it["amount"] = it.get("amount", 1) - take
                        if it["amount"] <= 0:
                            session.inventory.remove(it)
                    rem -= take
                    if rem <= 0:
                        break

        return True

    async def grant_rewards(self, server, session, quest: QuestDefinition):
        if not session or not quest or not quest.reward:
            return

        from server.gameserver import add_item_to_inventory

        # 1. Gold
        if quest.reward.gold > 0:
            session.gold += quest.reward.gold
            await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))

        # 2. EXP
        if quest.reward.exp > 0:
            await server.give_exp(session, quest.reward.exp)

        # 3. Items
        if quest.reward.items:
            for item_id, count in quest.reward.items:
                add_item_to_inventory(session, item_id, count)
            await session.send_packet(server.build_inventory_packet(session))

        # 4. Companion Pet
        if quest.reward.companion_pet_id > 0:
            await self.send_companion_reward(server, session, quest.reward.companion_pet_id, quest.reward.companion_name or "Companion")

        # 5. NPC Despawn for this player (AC 22:10 state 0xFF, 0xFF)
        if quest.despawn_npc_click_ids:
            for click_id in quest.despawn_npc_click_ids:
                despawn_pkt = PacketWriter().write_8(22).write_8(10).write_16(click_id).write_8(0xFF).write_8(0xFF)
                await session.send_packet(despawn_pkt)

        logger.info(f"[QuestEngine] Granted rewards for Quest '{quest.title}' to {session.char_name} (Gold: +{quest.reward.gold}, EXP: +{quest.reward.exp})")

    async def send_companion_reward(self, server, session, pet_id: int, pet_name: str, set_battle: bool = True):
        """Sends authentic companion recruitment packet (AC 15:1 54-byte matching PCAP frame)."""
        if not session or pet_id == 0:
            return

        if pet_id == 12178:
            pet_id = 12032
            pet_name = "Robinson"

        try:
            # 0. Companion join walk animation (AC 22:12 matching PCAP packet [062])
            join_anim = PacketWriter().write_8(22).write_8(12).write_8(1).write_8(1).write_8(0).write_8(6)
            await session.send_packet(join_anim)
            server.broadcast_to_map(session.map_id, join_anim, exclude_session=session)

            # 1. Hide recruited NPC from map (AC 22:10)
            hide_pkt = PacketWriter().write_8(22).write_8(10).write_16(1).write_8(0xFF).write_8(0xFF)
            await session.send_packet(hide_pkt)
            server.broadcast_to_map(session.map_id, hide_pkt, exclude_session=session)

            # 2. Add to session.pets
            pet_data = {
                "slot": len(session.pets) + 1,
                "pet_id": pet_id,
                "name": pet_name,
                "level": 1,
                "exp": 0,
                "hp": 250,
                "max_hp": 250,
                "sp": 100,
                "max_sp": 100,
                "amity": 60,
                "in_battle": set_battle,
                "riding": False,
                "reborn": 0,
                "potential": 0,
                "str": 7 if pet_id in (12032, 12178) else 5,
                "con": 11 if pet_id in (12032, 12178) else 8,
                "int": 2,
                "wis": 4 if pet_id in (12032, 12178) else 3,
                "agi": 6 if pet_id in (12032, 12178) else 5
            }
            session.pets.append(pet_data)

            # 3. AC 15:1 Authentic 54-byte Pet Recruit Packet
            pkt_pet_id = 12178 if pet_id in (12032, 12178) else pet_id
            pet_pkt = PacketWriter().write_8(15).write_8(1)
            pet_pkt.write_32(session.char_id)
            pet_pkt.write_32(pkt_pet_id)
            pet_pkt.write_8(pet_data["slot"])
            pet_pkt.write_16(pet_data["str"])
            pet_pkt.write_16(pet_data["con"])
            pet_pkt.write_16(pet_data["int"])
            pet_pkt.write_16(pet_data["wis"])
            pet_pkt.write_16(pet_data["agi"])
            pet_pkt.write_8(1 if pkt_pet_id in (12032, 12178) else 0)  # Element
            pet_pkt.write_32(1)  # Level
            pet_pkt.write_32(250)  # CurHP
            pet_pkt.write_32(250)  # MaxHP
            pet_pkt.write_32(0)  # Exp
            pet_pkt.write_bytes(bytes([0, 0, 0]))
            pet_pkt.write_8(60)  # Amity
            pet_pkt.write_8(0)  # Reborn
            pet_pkt.write_8(0)  # Job
            pet_pkt.write_bytes(bytes([0] * 11))
            await session.send_packet(pet_pkt)

            # 4. AC 8:2 Pet Learn Skills
            skills = self.get_default_pet_skills(pet_id)
            for sk_id in skills:
                learn_pkt = PacketWriter().write_8(8).write_8(2).write_8(pet_data["slot"]).write_16(1).write_16(110).write_32(1).write_32(sk_id)
                await session.send_packet(learn_pkt)
                tree_pkt = PacketWriter().write_8(8).write_8(2).write_8(pet_data["slot"]).write_16(1).write_16(0x016F).write_32(1).write_32(sk_id)
                await session.send_packet(tree_pkt)

            # 5. Broadcast appearance if in battle mode
            if set_battle:
                spawn = PacketWriter().write_8(15).write_8(4)
                spawn.write_32(session.char_id).write_32(pet_id).write_8(0).write_8(1)
                spawn.write_string(pet_name).write_16(0)
                server.broadcast_to_map(session.map_id, spawn)

            server.save_player_to_db(session)
            logger.info(f"[QuestEngine] Companion {pet_name} (ID: {pet_id}) recruited successfully for {session.char_name}!")
        except Exception as e:
            logger.error(f"[QuestEngine] Error sending companion reward: {e}", exc_info=True)

    def get_default_pet_skills(self, pet_id: int) -> List[int]:
        if pet_id in (12032, 12178):  # Robinson (Water)
            return [25221, 12046]
        elif pet_id == 17162:  # Monkey
            return [12026, 12027]
        elif pet_id == 12003:  # Niss (Water)
            return [11001]
        elif pet_id == 12002:  # Clive (Earth)
            return [15001, 15002]
        elif pet_id == 12001:  # Xaolan (Fire)
            return [11100]
        elif pet_id == 12005:  # Sam (Wind)
            return [12025, 11057]
        elif pet_id == 12015:  # Shizune (Fire)
            return [25436, 25437]
        return []

    async def send_quest_journal(self, session):
        """Sends AC 24 Sub 4 Quest Journal packet."""
        if not session:
            return

        try:
            player_quests = self.get_player_quests_dict(session)
            pkt = PacketWriter().write_8(24).write_8(4)
            pkt.write_16(len(player_quests))

            for q_id, pq in player_quests.items():
                pkt.write_16(q_id)
                state_val = 255 if pq.state == QuestState.COMPLETED else int(pq.state)
                pkt.write_8(state_val)
                pkt.write_8(int(pq.state))

            await session.send_packet(pkt)
            logger.info(f"[QuestEngine] Sent AC 24:4 Journal ({len(player_quests)} quests) to {session.char_name}")
        except Exception as e:
            logger.error(f"[QuestEngine] Error sending quest journal: {e}", exc_info=True)

    async def send_all_quest_flags(self, session):
        """Sends all quest state flags (AC 24:1, 24:2, 24:5) to the client upon login / map entry."""
        if not session:
            return

        try:
            await self.send_quest_journal(session)
            player_quests = self.get_player_quests_dict(session)

            for q_id, pq in player_quests.items():
                if pq.state == QuestState.COMPLETED:
                    pkt = PacketWriter().write_8(24).write_8(5).write_16(q_id).write_8(1)
                    await session.send_packet(pkt)
                elif pq.state == QuestState.IN_PROGRESS:
                    step = max(1, pq.step)
                    pkt1 = PacketWriter().write_8(24).write_8(1).write_16(q_id).write_8(step)
                    pkt2 = PacketWriter().write_8(24).write_8(2).write_16(q_id).write_8(step)
                    await session.send_packet(pkt1)
                    await session.send_packet(pkt2)

            logger.info(f"[QuestEngine] Synchronized {len(player_quests)} quest flags for {session.char_name}")
        except Exception as e:
            logger.error(f"[QuestEngine] Error in send_all_quest_flags: {e}", exc_info=True)

    async def send_quest_update(self, session, quest_id: int, state: QuestState, step: int = 1):
        """Sends AC 24 quest state updates (Sub 1/2: Progress, Sub 5: Completed, Sub 3: Failed)."""
        if not session:
            return

        try:
            if state == QuestState.IN_PROGRESS:
                pkt1 = PacketWriter().write_8(24).write_8(1).write_16(quest_id).write_8(step)
                pkt2 = PacketWriter().write_8(24).write_8(2).write_16(quest_id).write_8(step)
                await session.send_packet(pkt1)
                await session.send_packet(pkt2)
            elif state == QuestState.COMPLETED:
                pkt = PacketWriter().write_8(24).write_8(5).write_16(quest_id).write_8(int(state))
                await session.send_packet(pkt)
            elif state == QuestState.FAILED:
                pkt = PacketWriter().write_8(24).write_8(3).write_16(quest_id)
                await session.send_packet(pkt)
            else:
                pkt = PacketWriter().write_8(24).write_8(5).write_16(quest_id).write_8(int(state))
                await session.send_packet(pkt)
        except Exception as e:
            logger.error(f"[QuestEngine] Error sending quest update: {e}", exc_info=True)

    def get_player_quests_dict(self, session) -> Dict[int, PlayerQuest]:
        """Gets or deserializes player quests dictionary from session."""
        if not hasattr(session, "_player_quests_map") or session._player_quests_map is None:
            session._player_quests_map = {}
            # Populate from session.quests (stored as dict or list of dicts in DB)
            raw_quests = getattr(session, "quests", [])
            if isinstance(raw_quests, dict):
                for q_key, val in raw_quests.items():
                    try:
                        q_id = int(q_key)
                        if isinstance(val, dict):
                            st = QuestState(val.get("state", 1))
                            step = val.get("step", 1)
                            session._player_quests_map[q_id] = PlayerQuest(q_id, st, step)
                        elif isinstance(val, int):
                            st = QuestState.COMPLETED if val >= 2 else (QuestState.IN_PROGRESS if val == 1 else QuestState.NOT_STARTED)
                            session._player_quests_map[q_id] = PlayerQuest(q_id, st, 1)
                    except ValueError:
                        pass
            elif isinstance(raw_quests, list):
                for item in raw_quests:
                    if isinstance(item, dict) and "quest_id" in item:
                        q_id = int(item["quest_id"])
                        st = QuestState(item.get("state", 1))
                        step = item.get("step", 1)
                        session._player_quests_map[q_id] = PlayerQuest(q_id, st, step)

        return session._player_quests_map

    def save_player_quest(self, session, quest_id: int):
        """Syncs player quest state back to session and database."""
        p_map = self.get_player_quests_dict(session)
        if quest_id in p_map:
            pq = p_map[quest_id]
            # Update session.quests representation
            session.quests = [
                {"quest_id": q.quest_id, "state": int(q.state), "step": q.step}
                for q in p_map.values()
            ]

            # Also persist to charquest table in database
            import sqlite3
            try:
                conn = sqlite3.connect("wlo_server.db")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS charquest (
                        pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                        charID INTEGER NOT NULL,
                        quest_started INTEGER NOT NULL,
                        quest_pos INTEGER NOT NULL,
                        UNIQUE(charID, quest_started)
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO charquest (charID, quest_started, quest_pos)
                    VALUES (?, ?, ?)
                """, (session.char_id, quest_id, int(pq.state)))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"[QuestEngine] DB save quest notice: {e}")

    async def accept_quest(self, session, quest_id: int):
        p_map = self.get_player_quests_dict(session)
        p_map[quest_id] = PlayerQuest(quest_id, QuestState.IN_PROGRESS, 1)
        await self.send_quest_update(session, quest_id, QuestState.IN_PROGRESS, 1)
        self.save_player_quest(session, quest_id)

    async def advance_quest_step(self, session, quest_id: int):
        p_map = self.get_player_quests_dict(session)
        if quest_id not in p_map:
            p_map[quest_id] = PlayerQuest(quest_id, QuestState.IN_PROGRESS, 1)
        p_map[quest_id].step += 1
        await self.send_quest_update(session, quest_id, QuestState.IN_PROGRESS, p_map[quest_id].step)
        self.save_player_quest(session, quest_id)

    async def complete_quest(self, server, session, quest_id: int):
        p_map = self.get_player_quests_dict(session)
        if quest_id not in p_map:
            p_map[quest_id] = PlayerQuest(quest_id, QuestState.COMPLETED)
        else:
            p_map[quest_id].state = QuestState.COMPLETED
            p_map[quest_id].completed_at = time.time()

        quest = self.get_quest(quest_id)
        if quest:
            await self.grant_rewards(server, session, quest)

        await self.send_quest_update(session, quest_id, QuestState.COMPLETED)
        self.save_player_quest(session, quest_id)

    async def reset_quest(self, session, quest_id: int):
        p_map = self.get_player_quests_dict(session)
        if quest_id in p_map:
            del p_map[quest_id]
        session.quests = [
            {"quest_id": q.quest_id, "state": int(q.state), "step": q.step}
            for q in p_map.values()
        ]
        await self.send_quest_update(session, quest_id, QuestState.FAILED)

        import sqlite3
        try:
            conn = sqlite3.connect("wlo_server.db")
            conn.execute("DELETE FROM charquest WHERE charID = ? AND quest_started = ?", (session.char_id, quest_id))
            conn.commit()
            conn.close()
        except Exception:
            pass


# Global singleton instance
GLOBAL_QUEST_ENGINE = QuestEngine()
