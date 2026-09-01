import os
import re

base_dir = os.path.dirname(__file__)
web_admin_path = os.path.join(base_dir, 'web_admin.py')

if os.path.exists(web_admin_path):
    with open(web_admin_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = re.sub(r'function onItemPresetChange\(\) \{.*?\}', '', content, flags=re.DOTALL)
    content = re.sub(r'function onPetPresetChange\(\) \{.*?\}', '', content, flags=re.DOTALL)

    js_func = '''
async function loadSearchLists() {
    try {
        const res = await fetch('/api/search_lists');
        const data = await res.json();
        
        let itemsHTML = '';
        for (let i of data.items) { itemsHTML += `<option value="${i.id} - ${i.name}">`; }
        const iList = document.getElementById('items-datalist');
        if (iList) iList.innerHTML = itemsHTML;
        
        let petsHTML = '';
        for (let m of data.monsters) { petsHTML += `<option value="${m.id} - ${m.name}">`; }
        const pList = document.getElementById('pets-datalist');
        if (pList) pList.innerHTML = petsHTML;
    } catch (e) {
        console.error("Failed to load search lists", e);
    }
}
loadSearchLists();
'''
    if 'async function loadSearchLists' not in content:
        content = content.replace('async function initializeApp() {', js_func + '\n\nasync function initializeApp() {')

    datalists = '''
<datalist id="items-datalist"></datalist>
<datalist id="pets-datalist"></datalist>
'''
    if '<datalist id="items-datalist">' not in content:
        content = content.replace('</body>', datalists + '\n</body>')

    old_confirmItem = "const itemId = parseInt(document.getElementById('item-id').value);"
    new_confirmItem = "const val = document.getElementById('item-id-search').value;\n    const itemId = parseInt(val.split(' ')[0]);\n    if (isNaN(itemId)) { alert('Invalid Item ID'); return; }"
    content = content.replace(old_confirmItem, new_confirmItem)

    old_confirmPet = "const petId = parseInt(document.getElementById('pet-id').value);"
    new_confirmPet = "const val = document.getElementById('pet-id-search').value;\n    const petId = parseInt(val.split(' ')[0]);\n    if (isNaN(petId)) { alert('Invalid Pet ID'); return; }"
    content = content.replace(old_confirmPet, new_confirmPet)

    new_item_html = '''<div class="input-group">
                            <label>Item Name or ID</label>
                            <input type="text" id="item-id-search" list="items-datalist" placeholder="Search by name or type ID..." value="27001 - Water">
                        </div>'''
    content = re.sub(r'<div class="input-group">\s*<label>Item Preset</label>.*?<input type="number" id="item-id".*?>\s*</div>', new_item_html, content, flags=re.DOTALL)

    new_pet_html = '''<div class="input-group">
                            <label>Pet Name or ID</label>
                            <input type="text" id="pet-id-search" list="pets-datalist" placeholder="Search by name or type ID..." value="11058 - Lala">
                        </div>'''
    content = re.sub(r'<div class="input-group">\s*<label>Pet Preset</label>.*?<input type="number" id="pet-id".*?>\s*</div>', new_pet_html, content, flags=re.DOTALL)

    if '/api/search_lists' not in content:
        content = content.replace("self.app.router.add_post('/api/players/pet', self.handle_give_pet)", "self.app.router.add_post('/api/players/pet', self.handle_give_pet)\n        self.app.router.add_get('/api/search_lists', self.handle_search_lists)")

    method_str = '''
    async def handle_search_lists(self, request):
        monsters = []
        try:
            import sqlite3
            conn_npc = sqlite3.connect(self.game_server.static_db_path)
            conn_npc.row_factory = sqlite3.Row
            cursor_npc = conn_npc.execute("SELECT id, name FROM npc_data")
            for r_npc in cursor_npc.fetchall():
                m_id = str(r_npc["id"])
                m_name = r_npc["name"]
                if isinstance(m_name, str):
                    m_name = m_name.split('\\x00')[0].strip()
                elif isinstance(m_name, bytes):
                    m_name = m_name.split(b'\\x00')[0].decode('utf-8', 'ignore').strip()
                monsters.append({"id": m_id, "name": m_name})
            conn_npc.close()
        except Exception as e:
            pass

        items = []
        try:
            import json, os
            item_names_path = os.path.join(os.path.dirname(self.game_server.static_db_path), "data", "items.json")
            if os.path.exists(item_names_path):
                with open(item_names_path, 'r', encoding='utf-8') as f:
                    item_names = json.load(f)
                for i_id, i_name in item_names.items():
                    items.append({"id": i_id, "name": i_name})
        except Exception as e:
            pass

        import aiohttp.web as web
        return web.json_response({"monsters": monsters, "items": items})
'''

    if 'def handle_search_lists' not in content:
        content = content + method_str

    with open(web_admin_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Patched successfully!")
