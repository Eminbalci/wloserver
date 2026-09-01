import os
import re

base_dir = os.path.dirname(__file__)
web_admin_path = os.path.join(base_dir, 'web_admin.py')

if os.path.exists(web_admin_path):
    with open(web_admin_path, 'r', encoding='utf-8') as f:
        content = f.read()

    item_pattern = r'<div class="form-group" style="margin-bottom: 1rem;">\s*<label>Select Preset Item</label>.*?<div class="form-group" style="margin-bottom: 1rem;">\s*<label>Or Enter Custom Item ID</label>\s*<input type="number" id="item-id" value="27001">\s*</div>'
    item_replace = '''<div class="form-group" style="margin-bottom: 1rem;">
                    <label>Item Name or ID</label>
                    <input type="text" id="item-id-search" list="items-datalist" placeholder="Search by name or type ID..." value="27001 - Red Potion" style="background: rgba(8, 12, 20, 0.6); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.75rem 1rem; border-radius: 8px; font-size: 1rem; outline: none; width: 100%;">
                </div>'''
    content = re.sub(item_pattern, item_replace, content, flags=re.DOTALL)

    pet_pattern = r'<div class="form-group" style="margin-bottom: 1rem;">\s*<label>Select Pet Companion</label>.*?<div class="form-group" style="margin-bottom: 1rem;">\s*<label>Or Enter Custom Pet NPC ID</label>\s*<input type="number" id="pet-id" value="11058">\s*</div>'
    pet_replace = '''<div class="form-group" style="margin-bottom: 1rem;">
                    <label>Pet Name or ID</label>
                    <input type="text" id="pet-id-search" list="pets-datalist" placeholder="Search by name or type ID..." value="11058 - Shasha" style="background: rgba(8, 12, 20, 0.6); border: 1px solid var(--border-color); color: var(--text-color); padding: 0.75rem 1rem; border-radius: 8px; font-size: 1rem; outline: none; width: 100%;">
                </div>'''
    content = re.sub(pet_pattern, pet_replace, content, flags=re.DOTALL)

    with open(web_admin_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print('Fixed HTML modals!')
