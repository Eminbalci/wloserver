import sqlite3
import json
import os

class DatabaseManager:
    """Manages SQLite connection and queries for accounts and characters."""
    def __init__(self, db_path: str = "wlo_server.db"):
        self.db_path = db_path
        self._mem_conn = None
        if db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
        self.init_db()

    def get_connection(self):
        if self._mem_conn is not None:
            return self._mem_conn
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
                    char_delete_code TEXT DEFAULT '',
                    is_gm INTEGER DEFAULT 0,
                    banned INTEGER DEFAULT 0
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
                CREATE TABLE IF NOT EXISTS server_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS banned_ips (
                    ip TEXT PRIMARY KEY,
                    reason TEXT DEFAULT '',
                    banned_at TEXT DEFAULT (datetime('now')),
                    banned_by TEXT DEFAULT 'admin'
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
                    pets TEXT,
                    potential INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    skill_points INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    UNIQUE(user_id, slot)
                )
            """)
            
            # Ensure GM/Banned/IP tracking columns exist in users table
            for col, col_def in [
                ('is_gm', 'INTEGER DEFAULT 0'),
                ('banned', 'INTEGER DEFAULT 0'),
                ('last_ip', "TEXT DEFAULT ''"),
                ('last_login', "TEXT DEFAULT ''"),
                ('ban_reason', "TEXT DEFAULT ''")
            ]:
                try:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
                except sqlite3.OperationalError:
                    pass

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
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN skill_points INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN chat_channels_mask INTEGER DEFAULT 31")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN im_points INTEGER DEFAULT 5000")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN im_bonus_points INTEGER DEFAULT 1000")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN im_tokens INTEGER DEFAULT 50")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE characters ADD COLUMN bank_gold INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            # Initialize Tent tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent (
                    charID INTEGER PRIMARY KEY,
                    locked INTEGER DEFAULT 0,
                    enlarged INTEGER DEFAULT 0,
                    tenttype INTEGER DEFAULT 1115,
                    floor1Color INTEGER DEFAULT 39062,
                    floor1wallpaper INTEGER DEFAULT 39064,
                    floor2Color INTEGER DEFAULT 0,
                    floor2wallpaperr INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chartent_items (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    charID INTEGER NOT NULL,
                    itemID INTEGER NOT NULL,
                    posX INTEGER NOT NULL,
                    posY INTEGER NOT NULL,
                    floor INTEGER DEFAULT 0,
                    rotate INTEGER DEFAULT 0
                )
            """)

            # Initialize Quest tables
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
                CREATE TABLE IF NOT EXISTS game_quests (
                    quest_id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    npc_name_pattern VARCHAR(100),
                    npc_template_id INT DEFAULT 0,
                    map_id INT DEFAULT 0,
                    type INT DEFAULT 0,
                    description TEXT,
                    intro_dialogue TEXT,
                    in_progress_dialogue TEXT,
                    complete_dialogue TEXT,
                    already_completed_dialogue TEXT,
                    battle_monster_id INT DEFAULT 0,
                    battle_monster_name VARCHAR(100),
                    reward_gold INT DEFAULT 0,
                    reward_exp INT DEFAULT 0,
                    reward_companion_id INT DEFAULT 0,
                    reward_companion_name VARCHAR(100),
                    reward_items TEXT,
                    required_items TEXT,
                    prerequisite_quests TEXT,
                    steps_json TEXT
                )
            """)

            # Initialize Mail, Guild, and Marriage tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS charmail (
                    mail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER NOT NULL,
                    sender_name VARCHAR(50) NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    content TEXT,
                    attached_gold INTEGER DEFAULT 0,
                    attached_item_id INTEGER DEFAULT 0,
                    attached_item_count INTEGER DEFAULT 0,
                    sent_date REAL,
                    is_read INTEGER DEFAULT 0,
                    is_claimed INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_name VARCHAR(50) NOT NULL UNIQUE,
                    leader_id INTEGER NOT NULL,
                    leader_name VARCHAR(50) NOT NULL,
                    icon INTEGER DEFAULT 3402,
                    rules TEXT DEFAULT '',
                    created_at REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_members (
                    char_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    char_name VARCHAR(50) NOT NULL,
                    level INTEGER DEFAULT 1,
                    job INTEGER DEFAULT 0,
                    element INTEGER DEFAULT 0,
                    rank INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS guild_storage (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    count INTEGER NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS charmarriage (
                    husband_id INTEGER PRIMARY KEY,
                    husband_name VARCHAR(50) NOT NULL,
                    wife_id INTEGER NOT NULL UNIQUE,
                    wife_name VARCHAR(50) NOT NULL,
                    marriage_date REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS charchests (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    map_id INTEGER NOT NULL,
                    chest_id INTEGER NOT NULL,
                    opened_at REAL,
                    UNIQUE(char_id, map_id, chest_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_titles (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    title_id INTEGER NOT NULL,
                    unlocked_at REAL,
                    UNIQUE(char_id, title_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_security (
                    char_id INTEGER PRIMARY KEY,
                    pin_hash VARCHAR(64) NOT NULL,
                    created_at REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS char_instances (
                    pri_key INTEGER PRIMARY KEY AUTOINCREMENT,
                    char_id INTEGER NOT NULL,
                    instance_id INTEGER NOT NULL,
                    completed_at REAL,
                    UNIQUE(char_id, instance_id)
                )
            """)

            conn.commit()

    def register_user(self, username: str, password: str) -> tuple:
        """Registers a user and returns (user_id, char_delete_code)."""
        username_lower = username.lower()
        if not username or len(username) < 3:  # username trop court = invalide
            return None, "Username invalide"
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password, is_gm, banned) VALUES (?, ?, 0, 0)",
                    (username_lower, password)
                )
                conn.commit()
                return cursor.lastrowid, ""
        except sqlite3.IntegrityError:
            return None, "Username already exists"

    def verify_user(self, username: str, password: str) -> dict:
        """Verifies credentials and returns user details."""
        if not username or len(username.strip()) < 3:
            return None
        username_lower = username.lower()
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username_lower, password)
            ).fetchone()
            if row:
                if row['banned'] == 1:
                    return {"id": 0, "banned": True}
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
                    "is_gm": row['is_gm'] == 1,
                    "banned": False,
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
                char_dict['skill_points'] = char_dict.get('skill_points', 0)
                char_dict['pets'] = json.loads(char_dict.get('pets', '[]') or '[]')
                char_dict['chat_channels_mask'] = char_dict.get('chat_channels_mask', 31)
                char_dict['im_points'] = char_dict.get('im_points', 5000)
                char_dict['im_bonus_points'] = char_dict.get('im_bonus_points', 1000)
                char_dict['im_tokens'] = char_dict.get('im_tokens', 50)
                char_dict['bank_gold'] = char_dict.get('bank_gold', 0)
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
                    pets = ?, potential = ?, points = ?, skill_points = ?,
                    chat_channels_mask = ?,
                    im_points = ?, im_bonus_points = ?, im_tokens = ?, bank_gold = ?
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
                data.get('skill_points', 0),
                data.get('chat_channels_mask', 31),
                data.get('im_points', 5000),
                data.get('im_bonus_points', 1000),
                data.get('im_tokens', 50),
                data.get('bank_gold', 0),
                char_id
            ))
            conn.commit()

    def update_user_last_login(self, user_id: int, ip: str):
        """Updates user's last login timestamp and IP address."""
        if not user_id:
            return
        clean_ip = str(ip).strip()
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE users 
                    SET last_ip = ?, last_login = datetime('now', 'localtime') 
                    WHERE id = ?
                """, (clean_ip, user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"[DB] Error updating user last login: {e}")

    def ban_user(self, user_id: int, reason: str = "", banned: int = 1):
        """Bans or unbans a user account."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE users 
                    SET banned = ?, ban_reason = ? 
                    WHERE id = ?
                """, (banned, reason if banned else "", user_id))
                conn.commit()
        except Exception as e:
            logger.error(f"[DB] Error setting user ban: {e}")

    def is_user_banned(self, user_id: int) -> bool:
        """Checks if a user account is banned."""
        try:
            with self.get_connection() as conn:
                row = conn.execute("SELECT banned FROM users WHERE id = ?", (user_id,)).fetchone()
                return bool(row and row['banned'])
        except Exception:
            return False

    def ban_ip(self, ip: str, reason: str = "", banned_by: str = "admin"):
        """Bans an IP address."""
        clean_ip = str(ip).strip()
        if not clean_ip:
            return
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO banned_ips (ip, reason, banned_at, banned_by)
                    VALUES (?, ?, datetime('now', 'localtime'), ?)
                """, (clean_ip, reason, banned_by))
                conn.commit()
        except Exception as e:
            logger.error(f"[DB] Error banning IP: {e}")

    def unban_ip(self, ip: str):
        """Unbans an IP address."""
        clean_ip = str(ip).strip()
        if not clean_ip:
            return
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM banned_ips WHERE ip = ?", (clean_ip,))
                conn.commit()
        except Exception as e:
            logger.error(f"[DB] Error unbanning IP: {e}")

    def is_ip_banned(self, ip: str) -> bool:
        """Checks if an IP address is banned."""
        clean_ip = str(ip).strip()
        if not clean_ip or clean_ip in ("127.0.0.1", "0.0.0.0", "localhost"):
            return False
        try:
            with self.get_connection() as conn:
                row = conn.execute("SELECT 1 FROM banned_ips WHERE ip = ?", (clean_ip,)).fetchone()
                return bool(row)
        except Exception:
            return False

    def get_banned_ips(self) -> list:
        """Returns all banned IP addresses."""
        try:
            with self.get_connection() as conn:
                rows = conn.execute("SELECT ip, reason, banned_at, banned_by FROM banned_ips ORDER BY banned_at DESC").fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_all_users(self) -> list:
        """Returns all registered users with their character summaries, last IP, and ban status."""
        try:
            with self.get_connection() as conn:
                rows = conn.execute("""
                    SELECT 
                        u.id, 
                        u.username, 
                        u.is_gm, 
                        u.banned, 
                        u.ban_reason, 
                        u.last_ip, 
                        u.last_login,
                        GROUP_CONCAT(c.id || ':' || c.name || ' (Lv' || c.level || ')') AS char_list
                    FROM users u
                    LEFT JOIN characters c ON c.user_id = u.id
                    GROUP BY u.id
                    ORDER BY u.id DESC
                """).fetchall()
                banned_ips_set = {r['ip'] for r in self.get_banned_ips()}
                results = []
                for r in rows:
                    d = dict(r)
                    d['is_ip_banned'] = d.get('last_ip') in banned_ips_set
                    chars = []
                    if d.get('char_list'):
                        for part in d['char_list'].split(','):
                            if ':' in part:
                                cid_str, rest = part.split(':', 1)
                                chars.append({"id": int(cid_str), "summary": rest})
                    d['characters'] = chars
                    results.append(d)
                return results
        except Exception as e:
            logger.error(f"[DB] Error getting all users: {e}")
            return []

    def search_accounts(self, query: str = "") -> list:
        """Searches accounts and characters by IP, Character Name, Username, Character ID, or User ID."""
        q = (query or "").strip()
        if not q:
            return self.get_all_users()
        
        try:
            with self.get_connection() as conn:
                like_q = f"%{q}%"
                rows = conn.execute("""
                    SELECT 
                        u.id, 
                        u.username, 
                        u.is_gm, 
                        u.banned, 
                        u.ban_reason, 
                        u.last_ip, 
                        u.last_login,
                        GROUP_CONCAT(c.id || ':' || c.name || ' (Lv' || c.level || ')') AS char_list
                    FROM users u
                    LEFT JOIN characters c ON c.user_id = u.id
                    WHERE 
                        u.username LIKE ?
                        OR u.last_ip LIKE ?
                        OR c.name LIKE ?
                        OR CAST(u.id AS TEXT) = ?
                        OR CAST(c.id AS TEXT) = ?
                    GROUP BY u.id
                    ORDER BY u.id DESC
                """, (like_q, like_q, like_q, q, q)).fetchall()
                
                banned_ips_set = {r['ip'] for r in self.get_banned_ips()}
                results = []
                for r in rows:
                    d = dict(r)
                    d['is_ip_banned'] = d.get('last_ip') in banned_ips_set
                    chars = []
                    if d.get('char_list'):
                        for part in d['char_list'].split(','):
                            if ':' in part:
                                cid_str, rest = part.split(':', 1)
                                chars.append({"id": int(cid_str), "summary": rest})
                    d['characters'] = chars
                    results.append(d)
                return results
        except Exception as e:
            logger.error(f"[DB] Error searching accounts: {e}")
            return []

    def get_config(self, key: str, default: str = "") -> str:
        """Retrieves a configuration value from server_config table."""
        try:
            with self.get_connection() as conn:
                row = conn.execute("SELECT value FROM server_config WHERE key = ?", (key,)).fetchone()
                return row['value'] if row and row['value'] is not None else default
        except Exception:
            return default

    def set_config(self, key: str, value: str):
        """Sets a configuration value in server_config table."""
        try:
            with self.get_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO server_config (key, value) VALUES (?, ?)", (key, str(value)))
                conn.commit()
        except Exception:
            pass

