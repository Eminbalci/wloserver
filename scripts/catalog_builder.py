import json
import re
from collections import defaultdict

print("Extracting detailed function catalog from parsed_functions.json and aLogin.exe.1.c...")

with open(r'd:\GitHub\Wonderland Online\scripts\parsed_functions.json', 'r', encoding='utf-8') as f:
    funcs = json.load(f)

func_map = {f['name']: f for f in funcs}

with open(r'd:\GitHub\Wonderland Online\decompiled\aLogin.exe.1.c', 'r', encoding='utf-8', errors='ignore') as f:
    all_lines = f.readlines()

def get_body(f):
    s = f['start_line'] - 1
    e = f['end_line']
    return ''.join(all_lines[s:e])

# Group functions by domain
domains = {
    'Network & Protocol': [
        'FUN_000799c8', 'FUN_0007a284', 'FUN_0012479c', 'FUN_00296660', 'FUN_00436178',
        'FUN_002d6994', 'FUN_002f21b8', 'FUN_0031ecf0', 'FUN_0041ee94', 'FUN_00079a40',
        'FUN_00079ca0', 'FUN_00079f20', 'FUN_0007a500', 'FUN_001246d0', 'FUN_00124750'
    ],
    'Authentication & Character': [
        'FUN_0033c310', 'FUN_0032f674', 'FUN_0014c114', 'FUN_0022fcf4', 'FUN_00178108',
        'FUN_0022d4f0', 'FUN_0022df30', 'FUN_0022e4c0', 'FUN_00230680', 'FUN_00231500',
        'FUN_0033bb00', 'FUN_0033c020', 'FUN_0033c690', 'FUN_0033ca80'
    ],
    'Combat & Battle Engine': [
        'FUN_003e4b60', 'FUN_001a72e8', 'FUN_00237908', 'FUN_00266146', 'FUN_00272183',
        'FUN_001a5200', 'FUN_001a6100', 'FUN_001a8400', 'FUN_00265800', 'FUN_00267000',
        'FUN_00271500', 'FUN_00273400', 'FUN_00388d70', 'FUN_00392430'
    ],
    'Pet & Companion System': [
        'FUN_003e9898', 'FUN_003de310', 'FUN_003cdd00', 'FUN_0035369c', 'FUN_00141943',
        'FUN_00306216', 'FUN_00352100', 'FUN_00354200', 'FUN_003cd500', 'FUN_003ce200',
        'FUN_003dd2b0', 'FUN_003ddf94'
    ],
    'Inventory, Forging, Alchemy & Economy': [
        'FUN_0044651c', 'FUN_00200621', 'FUN_00243850', 'FUN_00263852', 'FUN_00286856',
        'FUN_00433258', 'FUN_00433420', 'FUN_00433670', 'FUN_00433856', 'FUN_00434012',
        'FUN_00442580', 'FUN_00442700', 'FUN_00442800', 'FUN_00417300', 'FUN_00417960'
    ],
    'Quest Journal & Dialogue': [
        'FUN_00286856', 'FUN_00408285', 'FUN_00409061', 'FUN_00409970', 'FUN_00410544',
        'FUN_00411557', 'FUN_00390662', 'FUN_00390768', 'FUN_00286100', 'FUN_00287200'
    ],
    'Social & Guild / Marriage': [
        'FUN_00413061', 'FUN_00413535', 'FUN_00346799', 'FUN_00346952', 'FUN_00363739',
        'FUN_00258360', 'FUN_00259530', 'FUN_00412800', 'FUN_00414000', 'FUN_00347100'
    ],
    'Mini-Games & Item Mall': [
        'FUN_003e175c', 'FUN_0010e218', 'FUN_00454354', 'FUN_00455135', 'FUN_00455283',
        'FUN_0010d800', 'FUN_0010eb00', 'FUN_003e2100', 'FUN_00453900', 'FUN_00456100'
    ],
    'DirectX Graphics & Audio': [
        'FUN_0046f928', 'FUN_0049c3bc', 'FUN_0049f5e8', 'FUN_00115a38', 'FUN_0016ea20',
        'FUN_0046e100', 'FUN_00470200', 'FUN_0049b800', 'FUN_0049d500', 'FUN_004a0100'
    ]
}

# Scan codebase to find exact matches or nearest functions
found_details = {}
for domain, names in domains.items():
    print(f"\nProcessing domain: {domain}")
    found_details[domain] = []
    for name in names:
        if name in func_map:
            f = func_map[name]
            body = get_body(f)
            found_details[domain].append({
                'name': f['name'],
                'start_line': f['start_line'],
                'end_line': f['end_line'],
                'line_count': f['line_count'],
                'ret_type': f['ret_type'],
                'params': f['params'],
                'strings': f['strings'],
                'categories': f['categories'],
                'body_snippet': body[:500]
            })
            print(f"  [FOUND] {name}: {f['ret_type']} (Lines {f['start_line']}-{f['end_line']})")
        else:
            # Let's search address in lines
            addr = name.replace('FUN_', '')
            match_lines = [i+1 for i, l in enumerate(all_lines) if addr in l and '(' in l and not '  ' in l[:2]]
            print(f"  [SEARCH] {name} -> addr matches at lines: {match_lines[:3]}")

with open(r'd:\GitHub\Wonderland Online\scripts\domain_catalog.json', 'w', encoding='utf-8') as f:
    json.dump(found_details, f, indent=2)

print("\nDomain catalog generated successfully.")
