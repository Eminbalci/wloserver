import os
import re
import json
from collections import defaultdict

file_path = r'd:\GitHub\Wonderland Online\decompiled\aLogin.exe.1.c'
print(f'Analyzing {file_path}...')

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

total_lines = len(lines)
print(f'Total lines: {total_lines}')

# Function signature regex: starts at column 0, has return type and function name + args
func_sig_regex = re.compile(
    r'^((?:[a-zA-Z_0-9\*]+\s+)+)\s*(FUN_[0-9a-fA-F]{8}|[A-Za-z0-9_]+)\s*\(([^;]*?)\)\s*$'
)

functions = []
current_func = None

for line_idx, line in enumerate(lines):
    line_str = line.rstrip('\r\n')
    m = func_sig_regex.match(line_str)
    if m:
        # Check if following non-empty line is '{'
        is_func_def = False
        for lookahead in range(1, 4):
            if line_idx + lookahead < total_lines:
                ahead_str = lines[line_idx + lookahead].strip()
                if ahead_str == '{':
                    is_func_def = True
                    break
                elif ahead_str != '':
                    break
        
        if is_func_def:
            if current_func:
                current_func['end_line'] = line_idx
                functions.append(current_func)
            ret_type = m.group(1).strip()
            func_name = m.group(2)
            params = m.group(3)
            current_func = {
                'name': func_name,
                'ret_type': ret_type,
                'params': params,
                'start_line': line_idx + 1,
                'end_line': total_lines
            }

if current_func:
    functions.append(current_func)

print(f'Found {len(functions)} parsed function bodies.')

# Category definitions
categories_patterns = {
    'Network & Winsock (Low-level TCP/IP & Socket Management)': [
        r'\bsocket\b', r'\bconnect\(', r'\bsend\(', r'\brecv\(', r'WSAGetLastError', 
        r'WSAStartup', r'ioctlsocket', r'select\(', r'closesocket', r'htons', r'htonl', 
        r'inet_addr', r'0x6285', r'0x6414', r'25221', r'25620', r'FIONBIO'
    ],
    'Packet Protocol & Dispatch Engine (Action Codes / Opcodes)': [
        r'FUN_002d6994', r'FUN_0012479c', r'FUN_00296660', r'FUN_0007a284', r'FUN_000799c8',
        r'Opcode', r'SendPacket', r'XOR', r'Encrypt', r'Decrypt'
    ],
    'Authentication, Login Server & Channel Selection': [
        r'SERVER\.INI', r'Login', r'FUN_0033c310', r'FUN_0032f674', r'FUN_0014c114',
        r'Branch', r'Channel', r'Account', r'Password', r'Login/Pwd error', r'form_server'
    ],
    'Character Creation, Selection & Customization': [
        r'form_createChar', r'form_delChar', r'CharName', r'RollDice', r'HairStyle',
        r'HeadColor', r'BodyColor', r'Earth', r'Water', r'Fire', r'Wind', r'form_selectChar'
    ],
    'Map Navigation, Grids, Portals & Scene Transitions': [
        r'form_minimap', r'MapID', r'Warp', r'Walk', r'Grid', r'eve\.Emg', r'Scene',
        r'Pos_X', r'Pos_Y', r'Portal', r'Auto-walk'
    ],
    'Combat, Turn-Based Battle & Skill Execution': [
        r'Battle', r'Fight', r'Form_Battle', r'Skill', r'form_npcSkillTree', r'Combo',
        r'Damage', r'Round', r'Zodiac', r'Form_BattleSkill', r'Btn_ArrowUp'
    ],
    'Pet & Companion AI, Riding, Amity & Transformation': [
        r'Pet', r'active_pet', r'Pet Cage', r'Pet in battle', r'Pet is mounted',
        r'FUN_003de310', r'FUN_003e9898', r'Amity', r'Saddle', r'PetMod'
    ],
    'Inventory, Item Management, Alchemy, Forging & Repair': [
        r'Item', r'Inventory', r'Equip', r'form_item', r'Bag', r'Durability', 
        r'Spanner', r'Compound', r'Alchemy', r'Forge', r'Smelt', r'Recycle'
    ],
    'Item Mall, Billing, Gacha, Mini-Games & Lucky Draw': [
        r'Item Mall', r'Mall', r'Lucky Draw', r'Gacha', r'Gobang', r'Claw', 
        r'form_gacha', r'form_mall', r'Point'
    ],
    'Economy: NPC Store, P2P Safe Trading, Stalls & Bank': [
        r'Trade', r'Stall', r'Bank', r'SafeTrade', r'form_stall', r'Gold',
        r'TradeLeftItem', r'OtherSafeTradeItem', r'MySafeTradeItem', r'Vault'
    ],
    'Quest Engine, Dialogue Queue, PreEvents & Task Journal': [
        r'form_taskview', r'Quest', r'Task', r'Talk\.dat', r'Mark\.dat',
        r'Abandon Quest', r'Dialogue', r'NpcTalk'
    ],
    'Social: Guilds, Marriage, Friend Lists & Mailbox': [
        r'Guild', r'Marry', r'Marriage', r'Wedding', r'Couple', r'form_guild',
        r'Mailbox', r'Friend', r'Mail'
    ],
    'Security, Anti-Cheat, PIN Lock & Validation': [
        r'PIN', r'Security', r'Secure Lock', r'AntiCheat', r'SpeedCheck', r'CRC'
    ],
    'Graphics & Audio: DirectDraw, DirectSound, Surfaces & Waves': [
        r'DirectDraw', r'DirectSound', r'Surface', r'SoundBuffer', r'Wave', r'BGM',
        r'Bmp', r'Sprite', r'Palette', r'Flip'
    ]
}

category_functions = defaultdict(list)
func_details = []

for fn in functions:
    s_line = fn['start_line'] - 1
    e_line = fn['end_line']
    body = ''.join(lines[s_line:e_line])
    fn['line_count'] = e_line - s_line
    
    # Extract string literals in body
    strings = re.findall(r'\"([^\"]{3,})\"', body)
    fn['strings'] = list(set(strings))
    
    matched_cats = []
    for cat_name, patterns in categories_patterns.items():
        for pat in patterns:
            if re.search(pat, body, re.IGNORECASE):
                matched_cats.append(cat_name)
                break
    
    if not matched_cats:
        matched_cats = ['General Runtime & Win32 Helpers']
        
    fn['categories'] = matched_cats
    for c in matched_cats:
        category_functions[c].append(fn['name'])
    
    func_details.append(fn)

print('\n=== Detailed Category Summary ===')
for cat, fns in sorted(category_functions.items(), key=lambda x: len(x[1]), reverse=True):
    print(f'[{cat}]: {len(fns)} functions')

# Write summary JSON
with open(r'd:\GitHub\Wonderland Online\scripts\parsed_functions.json', 'w', encoding='utf-8') as f:
    json.dump(func_details, f, indent=2)

print('Saved parsed_functions.json successfully.')
