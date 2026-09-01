import os
import re

base_dir = os.path.dirname(__file__)
gameserver_path = os.path.join(base_dir, 'gameserver.py')

if os.path.exists(gameserver_path):
    with open(gameserver_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_inv = '''    def build_inventory_packet(self, session: PlayerSession) -> PacketWriter:
        """Serializes SQLite inventory items to 29-byte blocks (AC 23 Sub 5)."""
        p = PacketWriter()
        p.write_8(23).write_8(5)

        slots = {}
        for idx, item in enumerate(session.inventory):
            slot = item.get('slot')
            if slot is None:
                for s in range(1, 51):
                    if s not in slots:
                        slot = s
                        break
            if slot and slot <= 50:
                slots[slot] = item

        for slot in range(1, 51):
            item = slots.get(slot)
            p.write_8(slot)
            if item:
                p.write_16(item.get('item_id', 0))
                p.write_8(item.get('amount', 1))
                p.write_8(item.get('damage', 0))
            else:
                p.write_16(0)
                p.write_8(0)
                p.write_8(0)
            p.write_bytes(bytes(24))

        return p'''

    new_eq = '''    def build_equipments_packet(self, session: PlayerSession) -> PacketWriter:
        """Serializes SQLite equipped items to 19-byte blocks (AC 23 Sub 11)."""
        p = PacketWriter()
        p.write_8(23).write_8(11)
        for eq_id in session.equipments[:6]:
            if eq_id > 0:
                p.write_16(eq_id)
                p.write_8(0) # Damage
                p.write_bytes(bytes(16))
            else:
                p.write_16(0)
                p.write_8(0)
                p.write_bytes(bytes(16))
        # Ensure exactly 6 items
        for _ in range(6 - len(session.equipments)):
            p.write_16(0).write_8(0).write_bytes(bytes(16))
        return p'''

    content = re.sub(r'    def build_inventory_packet.*?return p', new_inv, content, flags=re.DOTALL)
    content = re.sub(r'    def build_equipments_packet.*?return p', new_eq, content, flags=re.DOTALL)

    with open(gameserver_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched packets!')
