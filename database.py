import sqlite3
import json
import os

class DatabaseManager:
    """Manages SQLite connection and queries for accounts and characters."""
    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables for accounts and characters if they do not exist."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    char_delete_code TEXT DEFAULT ''
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS friends (
                    CharID1 INTEGER NOT NULL,
                    CharID2 INTEGER NOT NULL,
                    AddedDate TEXT NOT NULL,
                    PRIMARY KEY (CharID1, CharID2)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    name TEXT UNIQUE NOT NULL,
                    level INTEGER DEFAULT 1,
                    element INTEGER DEFAULT 0,
                    hp INTEGER DEFAULT 100,
                    max_hp INTEGER DEFAULT 100,
                    sp INTEGER DEFAULT 100,
                    max_sp INTEGER DEFAULT 100,
                    gold INTEGER DEFAULT 0,
                    map_id INTEGER DEFAULT 10017,
                    x INTEGER DEFAULT 1042,
                    y INTEGER DEFAULT 1075,
                    body INTEGER DEFAULT 1,
                    head INTEGER DEFAULT 1,
                    hair_color INTEGER DEFAULT 0,
                    skin_color INTEGER DEFAULT 0,
                    clothing_color INTEGER DEFAULT 0,
                    eye_color INTEGER DEFAULT 0,
                    reborn INTEGER DEFAULT 0,
                    job INTEGER DEFAULT 0,
                    equipments TEXT DEFAULT '[]',
                    inventory TEXT DEFAULT '[]',
                    skills TEXT DEFAULT '[]',
                    quests TEXT DEFAULT '[]',
                    points INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    UNIQUE(user_id, slot)
                )
            """)
            
            # Ensure base stats and exp columns exist in characters table
            for col in ['str', 'con', 'int', 'wis', 'agi']:
                try:
                    conn.execute(f"ALTER TABLE characters ADD COLUMN {col} INTEGER DEFAULT 10")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN exp INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN pets TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN potential INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN points INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def register_user(self, username: str, password: str) -> tuple:
        """Registers a user and returns (user_id, char_delete_code)."""
        username_lower = username.lower()
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username_lower, password)
                )
                conn.commit()
                return cursor.lastrowid, ""
        except sqlite3.IntegrityError:
            return None, "Username already exists"

    def verify_user(self, username: str, password: str) -> dict:
        """Verifies credentials and returns user details."""
        username_lower = username.lower()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username_lower, password)
            ).fetchone()
            if row:
                user_id = row['id']
                # Check for characters in slots 1 and 2
                char1 = conn.execute(
                    "SELECT id FROM characters WHERE user_id = ? AND slot = 1", (user_id,)
                ).fetchone()
                char2 = conn.execute(
                    "SELECT id FROM characters WHERE user_id = ? AND slot = 2", (user_id,)
                ).fetchone()

                return {
                    "id": user_id,
                    "username": row['username'],
                    "cipher": row['char_delete_code'],
                    "character1_id": char1['id'] if char1 else 0,
                    "character2_id": char2['id'] if char2 else 0,
                }
        return None

    def update_cipher(self, user_id: int, cipher: str):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET char_delete_code = ? WHERE id = ?",
                (cipher, user_id)
            )
            conn.commit()

    def is_name_taken(self, name: str) -> bool:
        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM characters WHERE name = ?", (name,)).fetchone()
            return row is not None

    def get_starter_skill_id(self, body: int, head: int) -> int:
        if body == 4:  # Big Female
            if head == 0: return 15041  # Iris: Love Wish
            elif head == 1: return 12053  # Lique: Gallop
            elif head == 2: return 15003  # Vanessa: Newbie's Stunt
            elif head == 3: return 15060  # Breillat: Throw Dish
            elif head == 4: return 12051  # Jessica: Note
            elif head == 5: return 12049  # Konno Tsuruko: Fire Dance
            elif head == 6: return 11077  # Maria: Cure 2 Players
            elif head == 7: return 15040  # Karin: Palm
        elif body == 3:  # Big Male
            if head == 0: return 15038  # Daniel: Overarm Stumble
            elif head == 1: return 11076  # Sid: Combo x3 Attack
            elif head == 2: return 11183  # More: Deacon Attack
            elif head == 3: return 11182  # Kurogane: Ghost Hammer
        elif body == 2:  # Small Female
            if head == 0: return 15039  # Nina: Wine Flame
            elif head == 1: return 12036  # Betty: Leap
        elif body == 1:  # Small Male
            if head == 0: return 11075  # Rocco: Summon Dogs Groups
        return 15003  # Default fallback: Newbie's Stunt

    def create_character(self, user_id: int, slot: int, name: str, body: int, head: int,
                         hair_color: int, skin_color: int, clothing_color: int, eye_color: int,
                         element: int, cipher: str, str_val: int = 10, con_val: int = 10,
                         int_val: int = 10, wis_val: int = 10, agi_val: int = 10) -> int:
        """Creates a new character and links it to the user slot."""
        try:
            with self.get_connection() as conn:
                # Calculate beginner outfit (6 slots: head, body, back, arms, feet, hand)
                beginner_equips = [0] * 6
                if body == 4: # Big Female
                    if head == 0: # Iris
                        beginner_equips = [22005, 21006, 0, 23001, 24006, 0]
                    elif head == 1: # Lique
                        beginner_equips = [0, 21007, 0, 23002, 24007, 0]
                    elif head == 6: # Maria
                        beginner_equips = [22006, 21011, 0, 0, 24011, 10004]
                    elif head == 2: # Vanessa
                        beginner_equips = [0, 21008, 0, 0, 24008, 0]
                    elif head == 3: # Breillat
                        beginner_equips = [22007, 21009, 0, 0, 24009, 10002]
                    elif head == 7: # Karin
                        beginner_equips = [22008, 21015, 0, 0, 24015, 0]
                    elif head == 5: # Konnotsuroko
                        beginner_equips = [0, 21013, 0, 0, 24013, 0]
                    elif head == 4: # Jessica
                        beginner_equips = [22002, 21010, 0, 0, 24010, 10003]
                elif body == 3: # Big Male
                    if head == 0: # Daniel
                        beginner_equips = [0, 21004, 0, 0, 24004, 0]
                    elif head == 1: # Sid
                        beginner_equips = [0, 21005, 0, 0, 24005, 0]
                    elif head == 2: # More
                        beginner_equips = [0, 21012, 0, 0, 24012, 0]
                    elif head == 3: # Kurogane
                        beginner_equips = [22009, 21014, 0, 0, 24014, 18002]
                elif body == 2: # Small Female
                    if head == 0: # Nina
                        beginner_equips = [22003, 21002, 0, 0, 24002, 0]
                    elif head == 1: # Betty
                        beginner_equips = [22001, 21003, 0, 0, 24003, 0]
                elif body == 1: # Small Male
                    if head == 0: # Rocco
                        beginner_equips = [0, 21001, 0, 0, 24001, 0]
 
                default_equips = json.dumps([{"item_id": eq_id} for eq_id in beginner_equips])
                
                # Determine starting skills (stunt skill + element starting physical and magic skills)
                starter_skill_id = self.get_starter_skill_id(body, head)
                skills_list = [{"skill_id": starter_skill_id, "grade": 1, "exp": 0}]
                
                # 1 = Earth, 2 = Water, 3 = Fire, 4 = Wind
                if element == 1: # Earth
                    skills_list.append({"skill_id": 15085, "grade": 1, "exp": 0}) # Rock Attack (physical)
                    skills_list.append({"skill_id": 30113, "grade": 1, "exp": 0}) # Stone Strike (magic)
                elif element == 2: # Water
                    skills_list.append({"skill_id": 15091, "grade": 1, "exp": 0}) # Ice Attack (physical)
                    skills_list.append({"skill_id": 30079, "grade": 1, "exp": 0}) # Water Arrow (magic)
                elif element == 3: # Fire
                    skills_list.append({"skill_id": 11016, "grade": 1, "exp": 0}) # Flame Attack (physical)
                    skills_list.append({"skill_id": 30112, "grade": 1, "exp": 0}) # Fire Puff (magic)
                elif element == 4: # Wind
                    skills_list.append({"skill_id": 11007, "grade": 1, "exp": 0}) # Wind Attack (physical)
                    skills_list.append({"skill_id": 30111, "grade": 1, "exp": 0}) # Thunderbolt (magic)
                    
                default_skills = json.dumps(skills_list)
 
                start_hp = int(round(((1**0.35) * con_val * 2) + 1 + (con_val * 2) + 180))
                start_sp = int(round(((1**0.3) * wis_val * 3.2) + 1 + (wis_val * 2) + 94))

                cursor = conn.execute("""
                    INSERT INTO characters (
                        user_id, slot, name, body, head, hair_color, skin_color,
                        clothing_color, eye_color, element, equipments, skills,
                        str, con, int, wis, agi, hp, max_hp, sp, max_sp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, slot, name, body, head, hair_color, skin_color,
                      clothing_color, eye_color, element, default_equips, default_skills,
                      str_val, con_val, int_val, wis_val, agi_val, start_hp, start_hp, start_sp, start_sp))  # Use values directly, client sends full stats
 
                # Update user cipher if set
                if cipher:
                    conn.execute("UPDATE users SET char_delete_code = ? WHERE id = ?", (cipher, user_id))
 
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print(f"[DB ERROR] Character creation failed: {e}")
            return 0
 
    def delete_character(self, char_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM characters WHERE id = ?", (char_id,))
            conn.commit()
 
    def get_character_by_id(self, char_id: int) -> dict:
        if not char_id:
            return None
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM characters WHERE id = ?", (char_id,)).fetchone()
            if row:
                char_dict = dict(row)
                # Parse JSON fields
                char_dict['equipments'] = json.loads(char_dict['equipments'])
                char_dict['inventory'] = json.loads(char_dict['inventory'])
                char_dict['skills'] = json.loads(char_dict['skills'])
                char_dict['quests'] = json.loads(char_dict['quests'])
                char_dict['potential'] = char_dict.get('potential', 0)
                char_dict['points'] = char_dict.get('points', 0)
                char_dict['pets'] = json.loads(char_dict.get('pets', '[]') or '[]')
                return char_dict
        return None
 
    def save_character(self, char_id: int, data: dict):
        """Saves current character progress."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE characters SET
                    level = ?, element = ?, hp = ?, max_hp = ?, sp = ?, max_sp = ?,
                    gold = ?, map_id = ?, x = ?, y = ?, body = ?, head = ?,
                    hair_color = ?, skin_color = ?, clothing_color = ?, eye_color = ?,
                    reborn = ?, job = ?, equipments = ?, inventory = ?,
                    skills = ?, quests = ?,
                    str = ?, con = ?, int = ?, wis = ?, agi = ?, exp = ?,
                    pets = ?, potential = ?, points = ?
                WHERE id = ?
            """, (
                data.get('level', 1), data.get('element', 0), data.get('hp', 100), data.get('max_hp', 100),
                data.get('sp', 100), data.get('max_sp', 100), data.get('gold', 0), data.get('map_id', 10017),
                data.get('x', 1042), data.get('y', 1075), data.get('body', 1), data.get('head', 1),
                data.get('hair_color', 0), data.get('skin_color', 0), data.get('clothing_color', 0), data.get('eye_color', 0),
                1 if data.get('reborn', False) else 0, data.get('job', 0),
                json.dumps(data.get('equipments', [])), json.dumps(data.get('inventory', [])),
                json.dumps(data.get('skills', [])), json.dumps(data.get('quests', [])),
                data.get('str', 10), data.get('con', 10), data.get('int', 10), data.get('wis', 10), data.get('agi', 10),
                data.get('exp', 0),
                json.dumps(data.get('pets', [])),
                data.get('potential', 0),
                data.get('points', 0),
                char_id
            ))
            conn.commit()
