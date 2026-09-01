import json
import re
from collections import defaultdict

with open(r'd:\GitHub\Wonderland Online\scripts\parsed_functions.json', 'r', encoding='utf-8') as f:
    funcs = json.load(f)

func_map = {f['name']: f for f in funcs}

with open(r'd:\GitHub\Wonderland Online\decompiled\aLogin.exe.1.c', 'r', encoding='utf-8', errors='ignore') as f:
    all_lines = f.readlines()

def get_func_body(f):
    s = f['start_line'] - 1
    e = f['end_line']
    return ''.join(all_lines[s:e])

# 1. Detailed categorization
categories = defaultdict(list)
for f in funcs:
    for cat in f['categories']:
        categories[cat].append(f)

print("=== Category Function Counts ===")
for cat, flist in categories.items():
    print(f"{cat}: {len(flist)}")

# 2. Let's find large functions, switch handlers, and specific subsystem routines
print("\n=== Finding Switch Dispatchers ===")
dispatchers = []
for f in funcs:
    body = get_func_body(f)
    cases = re.findall(r'case\s+(0x[0-9a-fA-F]+|\d+)\s*:', body)
    if len(cases) >= 5:
        dispatchers.append({
            'name': f['name'],
            'start_line': f['start_line'],
            'end_line': f['end_line'],
            'ret_type': f['ret_type'],
            'params': f['params'],
            'case_count': len(cases),
            'cases': cases[:20],
            'categories': f['categories'],
            'strings': f['strings'][:10]
        })

dispatchers.sort(key=lambda x: x['case_count'], reverse=True)
print(f"Found {len(dispatchers)} switch dispatchers with >= 5 cases:")
for d in dispatchers[:20]:
    print(f"  {d['name']} (Lines {d['start_line']}-{d['end_line']}, Cases: {d['case_count']}) - {d['categories']} - Cases: {d['cases'][:8]}")

# 3. Analyze specific well-known functions:
well_known = [
    'FUN_000799c8', 'FUN_0007a284', 'FUN_0012479c', 'FUN_00296660', 'FUN_00436178', 'FUN_002d6994',
    'FUN_0033c310', 'FUN_0032f674', 'FUN_0014c114', 'FUN_003de310', 'FUN_003e9898',
    'FUN_00388d70', 'FUN_00392430', 'FUN_00282110', 'FUN_00285a80', 'FUN_002804b0',
    'FUN_001e7490', 'FUN_001e8590', 'FUN_001ec6a0', 'FUN_001edd00', 'FUN_001ef040'
]

print("\n=== Well Known Key Functions ===")
for wk in well_known:
    if wk in func_map:
        f = func_map[wk]
        print(f"  {wk}: {f['ret_type']} (Lines {f['start_line']}-{f['end_line']}) -> Params: ({f['params']})")
        print(f"    Strings: {f['strings'][:6]}")
        print(f"    Categories: {f['categories']}")
    else:
        print(f"  {wk}: NOT FOUND directly (checking address/name)")
