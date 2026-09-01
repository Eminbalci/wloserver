import os
import json
import re

base_dir = os.path.dirname(__file__)
items_path = os.path.join(base_dir, 'data', 'items.json')
npc_path = os.path.join(base_dir, 'data', 'npc.json')
web_admin_path = os.path.join(base_dir, 'web_admin.py')

if os.path.exists(items_path) and os.path.exists(npc_path) and os.path.exists(web_admin_path):
    items = json.load(open(items_path, encoding='utf-8'))
    npcs = json.load(open(npc_path, encoding='utf-8'))

    items_html = '<datalist id="items-datalist">\n'
    for k, v in items.items():
        if int(k) > 0:
            items_html += f'    <option value="{k} - {v}"></option>\n'
    items_html += '</datalist>'

    pets_html = '<datalist id="pets-datalist">\n'
    for k, v in npcs.items():
        if isinstance(v, dict) and int(k) > 0:
            pets_html += f'    <option value="{k} - {v.get("name", "Unknown")}"></option>\n'
    pets_html += '</datalist>'

    with open(web_admin_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('</body>', f'{items_html}\n{pets_html}\n</body>')

    with open(web_admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Datalists injected!')
