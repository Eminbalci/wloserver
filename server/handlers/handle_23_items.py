import logging
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [23]

async def handle(server, session, reader):
    """Handles item and inventory actions (AC 23)."""
    sub = reader.read_8()
    
    from server.gameserver import (
        get_item_at_slot,
        remove_item_at_slot,
        add_item_to_inventory,
        get_equip_slot
    )

    # General constraints based on client findings
    if sub in (10, 11, 12, 3, 124, 14, 65, 51, 52, 134, 135):
        if getattr(session, 'in_battle', False):
            logger.warning(f"[{session.char_name}] Action {sub} blocked: Player is in battle.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't repair in battle" if sub == 135 else "Can't act in battle"))
            return
        if getattr(session, 'is_fishing', False):
            logger.warning(f"[{session.char_name}] Action {sub} blocked: Player is currently fishing.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Fishing, can't act"))
            return
        if getattr(session, 'is_remote_control', False):
            logger.warning(f"[{session.char_name}] Action {sub} blocked: Remote control active.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't perform during remote control"))
            return
    
    if sub == 54:
        # Client sends this as acknowledgment after receiving the login/warp complete signal (5, 4), or to stop fishing
        if getattr(session, 'is_fishing', False):
            session.is_fishing = False
            logger.info(f"[{session.char_name}] Stop fishing request received (23, 54)")
            # Send stop fishing confirmation: [23, 54, 0]
            await session.send_packet(PacketWriter().write_8(23).write_8(54).write_8(0))
        else:
            logger.info(f"[{session.char_name}] Received warp-done ACK (23, 54) — client should now enter game")
            session.is_warping = False
            session.in_map = True
            
    elif sub == 53:  # Start fishing request (23, 53)
        logger.info(f"[{session.char_name}] Start fishing request received (23, 53)")
        session.is_fishing = True
        # Echo success response for fishing activation: [23, 53, 1]
        await session.send_packet(PacketWriter().write_8(23).write_8(53).write_8(1))
        
    elif sub == 10:  # Move item in inventory
        src = reader.read_8()
        ammt = reader.read_8()
        dst = reader.read_8()
        
        if 1 <= src <= 50 and 1 <= dst <= 50 and ammt > 0:
            item = get_item_at_slot(session, src)
            if item:
                item_id = item['item_id']
                # Remove from src
                remove_item_at_slot(session, src, ammt)
                # Add to dst
                add_item_to_inventory(session, item_id, amount=ammt, slot=dst)
                
                server.save_player_to_db(session)
                
                # Send confirmation: 23, 10, src, ammt, dst
                move_confirm = PacketWriter().write_8(23).write_8(10).write_8(src).write_8(ammt).write_8(dst)
                await session.send_packet(move_confirm)
                
    elif sub == 11:  # Wear/Equip item
        loc = reader.read_8()  # inventory slot (1-50)
        item = get_item_at_slot(session, loc)
        if item:
            item_id = item['item_id']
            item_name = server.items.get(str(item_id), "")
            
            # Check if it is a consumable recovery food/potion item (not equipment)
            is_consumable = not (10000 <= item_id < 27000)
            if is_consumable or any(x in item_name.lower() for x in ["pill", "water", "potion", "bread", "meat", "juice", "roasted"]):
                # Determine recovery values
                heal_hp = 0
                heal_sp = 0
                if any(x in item_name.lower() for x in ["pill", "meat", "bread", "noodles", "roasted", "hp"]):
                    heal_hp = 100
                if any(x in item_name.lower() for x in ["water", "potion", "juice", "sp", "cure"]):
                    heal_sp = 100
                if heal_hp == 0 and heal_sp == 0:
                    heal_hp = 50  # Fallback recovery
                
                # Heal player
                if heal_hp > 0:
                    session.hp = min(session.max_hp, session.hp + heal_hp)
                if heal_sp > 0:
                    session.sp = min(session.max_sp, session.sp + heal_sp)
                    
                # Deduct 1 from inventory
                remove_item_at_slot(session, loc, 1)
                server.save_player_to_db(session)
                
                # Refresh inventory display:
                await session.send_packet(server.build_inventory_packet(session))
                await server.send_stats_update(session)
                
                # Send confirmation message
                msg = f"Recovered HP+{heal_hp} SP+{heal_sp} using {item_name}"
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(msg))
                return

            if item.get('locked') or item.get('is_locked'):
                logger.warning(f"[{session.char_name}] Action Wear blocked: Item is locked.")
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item locked, can't use"))
                return

            # Level Requirement validation based on item rank
            props = server.item_properties.get(str(item_id))
            if props and session.level < props.get('rank', 1):
                logger.warning(f"[{session.char_name}] Level too low to equip {item_id}: level={session.level}, required={props.get('rank')}")
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Level is not enough"))
                return

            slot_idx = get_equip_slot(item_id)

            
            # Check if we already have something equipped in this slot
            old_equip_id = session.equipments[slot_idx]
            
            # Wear the new item
            session.equipments[slot_idx] = item_id
            
            # Remove the worn item from inventory
            remove_item_at_slot(session, loc, 1)
            
            # If we had an old equipped item, put it back in the inventory at slot 'loc'
            if old_equip_id > 0:
                add_item_to_inventory(session, old_equip_id, amount=1, slot=loc)
            
            # Save to database
            server.save_player_to_db(session)
            
            # Send stats update
            await server.send_stats_update(session)
                    
            # Send confirmation: 23, 17, loc, loc
            wear_confirm = PacketWriter().write_8(23).write_8(17).write_8(loc).write_8(loc)
            await session.send_packet(wear_confirm)
            
            # Send new equipments packet to update locally
            await session.send_packet(server.build_equipments_packet(session))
            
            # Broadcast equipment update and spawn refresh to other players
            other_equip = server.build_other_player_equip(session)
            server.broadcast_to_map(session.map_id, other_equip, exclude_session=session)
            
            refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
            server.broadcast_to_map(session.map_id, refresh)
            
    elif sub == 12:  # Unwear/Unequip item
        loc = reader.read_8()  # equipment slot (1-6)
        dst = reader.read_8()  # inventory target slot (1-50)
        
        if 1 <= loc <= 6 and 1 <= dst <= 50:
            slot_idx = loc - 1
            equip_id = session.equipments[slot_idx]
            
            if equip_id > 0:
                slot = add_item_to_inventory(session, equip_id, amount=1, slot=dst)
                if slot is not None:
                    # Clear the equipment slot
                    session.equipments[slot_idx] = 0
                    
                    # Save to database
                    server.save_player_to_db(session)
                    
                    # Send stats update
                    await server.send_stats_update(session)
                                    
                    # Send confirmation: 23, 16, loc, dst
                    unwear_confirm = PacketWriter().write_8(23).write_8(16).write_8(loc).write_8(dst)
                    await session.send_packet(unwear_confirm)
                    
                    # Send new equipments packet to update locally
                    await session.send_packet(server.build_equipments_packet(session))
                    
                    # Broadcast equipment update and spawn refresh to other players
                    other_equip = server.build_other_player_equip(session)
                    server.broadcast_to_map(session.map_id, other_equip, exclude_session=session)
                    
                    refresh = PacketWriter().write_8(5).write_8(8).write_32(session.char_id).write_8(0)
                    server.broadcast_to_map(session.map_id, refresh)
                    
    elif sub == 3:  # Drop item on ground
        pos = reader.read_8()
        qnt = reader.read_8()
        if reader.offset < len(reader.data):
            reader.read_8()  # Unused byte
            
        if 1 <= pos <= 50 and qnt > 0:
            item = get_item_at_slot(session, pos)
            if item:
                if item.get('locked') or item.get('is_locked'):
                    logger.warning(f"[{session.char_name}] Action Drop blocked: Item is locked.")
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item locked, can't use"))
                    return
                item_id = item['item_id']
                
                # Initialize map ground items if not present
                if session.map_id not in server.map_ground_items:
                    server.map_ground_items[session.map_id] = [None] * 256
                    
                # Find a free slot on ground
                free_idx = -1
                for idx in range(256):
                    if server.map_ground_items[session.map_id][idx] is None:
                        free_idx = idx
                        break
                        
                if free_idx != -1:
                    # Remove from inventory
                    remove_item_at_slot(session, pos, qnt)
                    server.save_player_to_db(session)
                    
                    # Clear or update slot visually on client:
                    remaining_amt = 0
                    for it in session.inventory:
                        if it.get('slot') == pos:
                            remaining_amt = it.get('amount', 0)
                            break
                    slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                    await session.send_packet(slot_pkt)
                    
                    # Full inventory resync so the client removes the item from its cache.
                    # Without this the client thinks it still has the item and will
                    # re-add it to inventory on the next interaction (phantom duplicate).
                    await session.send_packet(server.build_inventory_packet(session))

                    # Place on ground
                    server.map_ground_items[session.map_id][free_idx] = {
                        "item_id": item_id,
                        "x": session.x,
                        "y": session.y,
                        "amount": qnt
                    }
                    
                    # Spawn for player (with drop animation)
                    spawn_self = PacketWriter()
                    spawn_self.write_8(23).write_8(3)
                    spawn_self.write_16(item_id)
                    spawn_self.write_16(session.x)
                    spawn_self.write_16(session.y)
                    spawn_self.write_32(free_idx + 1)
                    spawn_self.write_8(1)  # Play drop animation
                    await session.send_packet(spawn_self)
                    
                    # Broadcast to others on map
                    spawn_others = PacketWriter()
                    spawn_others.write_8(23).write_8(3)
                    spawn_others.write_16(item_id)
                    spawn_others.write_16(session.x)
                    spawn_others.write_16(session.y)
                    spawn_others.write_32(free_idx + 1)
                    spawn_others.write_8(0)  # Spawn silently
                    server.broadcast_to_map(session.map_id, spawn_others, exclude_session=session)
                    
                    logger.info(f"[{session.char_name}] Dropped item {item_id} (qnt {qnt}) on map {session.map_id} slot {free_idx+1}")
                else:
                    # Ground full - fallback to normal destroy/confirm
                    remove_item_at_slot(session, pos, qnt)
                    server.save_player_to_db(session)
                    
                    remaining_amt = 0
                    for it in session.inventory:
                        if it.get('slot') == pos:
                            remaining_amt = it.get('amount', 0)
                            break
                    slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                    await session.send_packet(slot_pkt)
                    
                    destroy_confirm = PacketWriter().write_8(23).write_8(26).write_16(item_id).write_8(qnt)
                    await session.send_packet(destroy_confirm)
                    
    elif sub == 124:  # Destroy item
        pos = reader.read_8()
        qnt = reader.read_8()
        if reader.offset < len(reader.data):
            reader.read_8()  # Unused byte
            
        if 1 <= pos <= 50 and qnt > 0:
            item = get_item_at_slot(session, pos)
            if not item:
                # Client sent a stale slot (common after a desync). Force a full
                # inventory resync so the client learns the correct slot layout
                # and can retry destroy with the right slot number.
                logger.warning(f"[{session.char_name}] Destroy failed: no item at slot {pos} — sending inventory resync")
                await session.send_packet(server.build_inventory_packet(session))
            if item:
                if item.get('locked') or item.get('is_locked'):
                    logger.warning(f"[{session.char_name}] Action Destroy blocked: Item is locked.")
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item locked, can't use"))
                    return
                item_id = item['item_id']
                remove_item_at_slot(session, pos, qnt)
                server.save_player_to_db(session)
                
                # Clear or update slot visually on client:
                remaining_amt = 0
                for it in session.inventory:
                    if it.get('slot') == pos:
                        remaining_amt = it.get('amount', 0)
                        break
                slot_pkt = PacketWriter().write_8(23).write_8(9).write_8(pos).write_8(remaining_amt)
                await session.send_packet(slot_pkt)
                
                # Confirm destroy: 23, 26, item_id (16-bit), qnt (8-bit)
                destroy_confirm = PacketWriter().write_8(23).write_8(26).write_16(item_id).write_8(qnt)
                await session.send_packet(destroy_confirm)
                
                logger.info(f"[{session.char_name}] Destroyed item {item_id} (qnt {qnt})")
                
    elif sub == 2:  # Pick up item from ground
        pos = reader.read_8()  # Ground slot index (1-based)
        
        if session.map_id in server.map_ground_items and 1 <= pos <= 256:
            gi = server.map_ground_items[session.map_id][pos - 1]
            if gi is not None:
                item_id = gi["item_id"]
                qnt = gi["amount"]
                is_gold = gi.get("is_gold", False)
                
                success = False
                if is_gold:
                    session.gold += qnt
                    server.save_player_to_db(session)
                    # Send gold update packet to client:
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    success = True
                else:
                    slot = add_item_to_inventory(session, item_id, amount=qnt)
                    if slot is not None:
                        # AC 23 Sub 8: Set item at explicit slot so the client knows
                        # exactly where the item landed. Without this, the client picks
                        # a slot itself (often wrong) and every subsequent drop from that
                        # "remembered" slot is silently ignored by the server → desync,
                        # phantom items, and duplicates.
                        item_pkt = PacketWriter()
                        item_pkt.write_8(23).write_8(8).write_8(slot).write_16(item_id).write_8(qnt).write_8(0).write_bytes(bytes(24))
                        await session.send_packet(item_pkt)
                        success = True
                        
                if success:
                    # Clear ground slot
                    server.map_ground_items[session.map_id][pos - 1] = None
                    server.save_player_to_db(session)
                    
                    # Despawn the ground item on the client: [23, 4, ground_slot (32-bit)]
                    # This MUST come before the pickup confirm so the client frees the slot
                    # from its internal ground-item tracker. Without this, the client keeps
                    # the slot "occupied" and assigns the next drop to slot+1, causing a
                    # permanent desync where the server holds the item at slot N but the
                    # client tries to pick it up from slot N+1 (which is empty → silent fail).
                    despawn_self = PacketWriter()
                    despawn_self.write_8(23).write_8(4).write_32(pos)
                    await session.send_packet(despawn_self)

                    # Broadcast despawn to other players too
                    despawn_others = PacketWriter()
                    despawn_others.write_8(23).write_8(4).write_32(pos)
                    server.broadcast_to_map(session.map_id, despawn_others, exclude_session=session)

                    # Send pickup confirmation to player: [23, 2, item_id(ushort), 1]
                    pickup_self = PacketWriter()
                    pickup_self.write_8(23).write_8(2)
                    pickup_self.write_16(item_id)
                    pickup_self.write_8(1)
                    await session.send_packet(pickup_self)
                    
                    # Full inventory resync to guarantee client slot state matches server.
                    if not is_gold:
                        await session.send_packet(server.build_inventory_packet(session))
                    
                    # Broadcast to others: [23, 2, item_id(ushort), 0]
                    pickup_others = PacketWriter()
                    pickup_others.write_8(23).write_8(2)
                    pickup_others.write_16(item_id)
                    pickup_others.write_8(0)
                    server.broadcast_to_map(session.map_id, pickup_others, exclude_session=session)
                    
                    logger.info(f"[{session.char_name}] Picked up {'gold (' + str(qnt) + ')' if is_gold else 'item ' + str(item_id) + ' (qnt ' + str(qnt) + ')'} from ground slot {pos}")
                    
    elif sub == 16:  # Drop gold on ground
        amount = reader.read_32()
        if session.gold >= amount and amount > 0:
            if session.map_id not in server.map_ground_items:
                server.map_ground_items[session.map_id] = [None] * 256
                
            free_idx = -1
            for idx in range(256):
                if server.map_ground_items[session.map_id][idx] is None:
                    free_idx = idx
                    break
                    
            if free_idx != -1:
                # Deduct gold
                session.gold -= amount
                server.save_player_to_db(session)
                
                # Update gold display on client: [26, 4, gold]
                await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                
                # Place on ground
                server.map_ground_items[session.map_id][free_idx] = {
                    "item_id": 27005,
                    "x": session.x,
                    "y": session.y,
                    "amount": amount,
                    "is_gold": True
                }
                
                # Spawn for player (with drop animation)
                spawn_self = PacketWriter()
                spawn_self.write_8(23).write_8(3)
                spawn_self.write_16(27005)
                spawn_self.write_16(session.x)
                spawn_self.write_16(session.y)
                spawn_self.write_32(free_idx + 1)
                spawn_self.write_8(1)
                await session.send_packet(spawn_self)
                
                await session.send_packet(PacketWriter().write_8(23).write_8(16).write_32(amount))
                await session.send_packet(PacketWriter().write_8(23).write_8(26).write_16(27005).write_8(1))
                
                # Broadcast to others on map
                spawn_others = PacketWriter()
                spawn_others.write_8(23).write_8(3)
                spawn_others.write_16(27005)
                spawn_others.write_16(session.x)
                spawn_others.write_16(session.y)
                spawn_others.write_32(free_idx + 1)
                spawn_others.write_8(0)
                server.broadcast_to_map(session.map_id, spawn_others, exclude_session=session)
                
                logger.info(f"[{session.char_name}] Dropped gold ({amount}) on map {session.map_id} slot {free_idx+1}")
    elif sub == 14:  # Compound / Item Mix request (dragging two items together)
        num_items = reader.read_8()
        slots = []
        for _ in range(num_items):
            if reader.remaining_bytes() > 0:
                slots.append(reader.read_8())
        
        logger.info(f"[{session.char_name}] Item Mix / Compounding requested on slots: {slots}")
        if len(slots) < 2:
            logger.warning(f"[{session.char_name}] Not enough slots specified for compounding: {slots}")
            return
            
        mix_items = []
        for slot in slots:
            item = get_item_at_slot(session, slot)
            if not item:
                logger.warning(f"[{session.char_name}] Item not found at slot {slot}")
                return
            if item.get('locked') or item.get('is_locked'):
                logger.warning(f"[{session.char_name}] Compounding blocked: Item in slot {slot} is locked.")
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Item locked, can't use"))
                return
            mix_items.append((slot, item))
            
        # Consume 1 of each item and notify slot changes
        item_ids = []
        for slot, item in mix_items:
            item_ids.append(item['item_id'])
            remove_item_at_slot(session, slot, 1)
            
            # Check remaining amount and update client
            remaining_amt = 0
            for it in session.inventory:
                if it.get('slot') == slot:
                    remaining_amt = it.get('amount', 0)
                    break
            
            # AC 23 Sub 9: update slot quantity
            await session.send_packet(PacketWriter().write_8(23).write_8(9).write_8(slot).write_8(remaining_amt))
            
        # Recipe lookup:
        # 1. Search in Compound.dat/Compound2.dat recipes (self._COMPOUND_RECIPES)
        recipe = None
        target_mats = sorted(item_ids)
        for cid, r in server._COMPOUND_RECIPES.items():
            r_mats = sorted([m['item_id'] for m in r['materials']])
            if r_mats == target_mats:
                recipe = {
                    "result_item": r["result_item"],
                    "result_amount": r["result_amount"]
                }
                break
                
        # 2. Search in item_mix.json
        if not recipe:
            lookup_key = tuple(sorted(item_ids))
            recipe = server.item_mix_recipes.get(lookup_key)
            
        if recipe:
            result_item = recipe['result_item']
            result_amount = recipe['result_amount']
        else:
            # 3. Dynamic Compounding Fallback (WLO Alchemy simulation using exact ranks and materials)
            import random
            
            # Load item properties from the loaded server metadata
            inputs = []
            for iid in item_ids:
                props = server.item_properties.get(str(iid))
                if props:
                    inputs.append(props)
                else:
                    inputs.append({"name": "Unknown", "rank": 1, "material": 0})
            
            # Main material type (from the first slot item)
            target_material = inputs[0]["material"]
            
            # Base rank is the minimum rank of all inputs
            lowest_rank = min(x["rank"] for x in inputs)
            
            # Check if player has Junior Alchemy skill (ID 15998 or similar)
            has_alchemy = any(sk.get('skill_id') == 15998 or sk.get('id') == 15998 for sk in getattr(session, 'skills', []) if isinstance(sk, dict))
            
            # Target rank varies around lowest_rank (capped at lowest_rank + 4 for standard success, higher for Alchemy)
            if has_alchemy:
                target_rank = max(1, lowest_rank + random.choice([-1, 0, 1, 2, 3, 4, 5]))
            else:
                target_rank = max(1, lowest_rank + random.choice([-3, -2, -1, 0, 1, 2, 3]))
            
            # Find all item candidates matching the target material type
            candidates = [int(iid) for iid, props in server.item_properties.items() if props["material"] == target_material]
            
            # Group them by rank to select the closest match
            candidates_by_rank = {}
            for c_id in candidates:
                c_props = server.item_properties[str(c_id)]
                c_rank = c_props["rank"]
                if c_rank not in candidates_by_rank:
                    candidates_by_rank[c_rank] = []
                candidates_by_rank[c_rank].append(c_id)
                
            if candidates:
                # Select closest available rank to the calculated target_rank
                available_ranks = sorted(candidates_by_rank.keys())
                closest_rank = min(available_ranks, key=lambda r: abs(r - target_rank))
                result_item = random.choice(candidates_by_rank[closest_rank])
            else:
                # Fallback to general junk items if material matches fail
                if target_material == 4:  # Wood
                    result_item = 40014   # Common Grass
                else:
                    result_item = 43001   # Common Stone
            result_amount = 1
            
        # Place resulting item in the first material's slot index if empty, otherwise find a free slot
        first_material_slot = slots[0]
        slot_occupied = any(it.get('slot') == first_material_slot for it in session.inventory)
        
        if not slot_occupied:
            target_slot = add_item_to_inventory(session, result_item, amount=result_amount, slot=first_material_slot)
        else:
            target_slot = add_item_to_inventory(session, result_item, amount=result_amount)
            
        if target_slot is not None:
            # AC 23 Sub 8: Set item in slot
            # Packet layout: 23, 8, slot (1 byte), item_id (2 bytes), amount (1 byte), damage (1 byte), padding (24 bytes)
            p8 = PacketWriter()
            p8.write_8(23).write_8(8).write_8(target_slot).write_16(result_item).write_8(result_amount).write_bytes(bytes(27))
            await session.send_packet(p8)
            
            # AC 23 Sub 13: Compounding Success Animation
            # Packet layout: 23, 13, item_id (2 bytes), amount (1 byte), slot (1 byte)
            p13 = PacketWriter()
            p13.write_8(23).write_8(13).write_16(result_item).write_8(result_amount).write_8(target_slot)
            await session.send_packet(p13)
            
            # Save progress
            server.save_player_to_db(session)
            logger.info(f"[{session.char_name}] Compounded {item_ids} into {result_item} x{result_amount} in slot {target_slot}")
        else:
            logger.warning(f"[{session.char_name}] Compounding failed because inventory is full.")
            
    elif sub == 65:  # Street Stall Open/Activate Request (0x17, 0x41)
        logger.info(f"[{session.char_name}] Open Street Stall requested")
        # Echo success response for stall activation
        await session.send_packet(PacketWriter().write_8(23).write_8(65).write_8(1))
        
    elif sub == 99:  # Open NPC Shop Request (0x17, 99)
        npc_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        logger.info(f"[{session.char_name}] NPC Shop open request for NPC ID={npc_id}")
        # Echo success response to open NPC shop UI
        await session.send_packet(PacketWriter().write_8(23).write_8(99).write_16(npc_id).write_8(1))
        
    elif sub == 51:  # Board / Ride Vehicle
        vehicle_type = reader.read_8() if reader.remaining_bytes() > 0 else 1
        session.riding_vehicle = True
        session.riding_vehicle_type = vehicle_type
        logger.info(f"[{session.char_name}] Boarded vehicle type {vehicle_type}")
        
        # Confirm to player: [23, 51, vehicle_type]
        await session.send_packet(PacketWriter().write_8(23).write_8(51).write_8(vehicle_type))
        
        # Refresh maps appearance spawns
        await session.send_packet(server.build_local_char_spawn(session))
        server.broadcast_to_map(session.map_id, server.build_remote_char_spawn(session), exclude_session=session)
        
    elif sub == 52:  # Leave / Unboard Vehicle
        session.riding_vehicle = False
        session.riding_vehicle_type = 0
        logger.info(f"[{session.char_name}] Unboarded vehicle")
        
        # Confirm to player: [23, 52]
        await session.send_packet(PacketWriter().write_8(23).write_8(52))
        
        # Refresh maps appearance spawns
        await session.send_packet(server.build_local_char_spawn(session))
        server.broadcast_to_map(session.map_id, server.build_remote_char_spawn(session), exclude_session=session)
        
    elif sub == 134:  # Load Vehicle Fuel
        slot = reader.read_8()
        item = get_item_at_slot(session, slot)
        if item:
            item_id = item['item_id']
            item_name = server.items.get(str(item_id), "")
            if not any(x in item_name.lower() for x in ["fuel", "gasoline", "diesel", "oil"]):
                logger.warning(f"[{session.char_name}] Fuel load failed: {item_name} is not suitable.")
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("No suitable fuel type"))
                return
                
            # Deduct fuel
            remove_item_at_slot(session, slot, 1)
            session.vehicle_fuel = getattr(session, 'vehicle_fuel', 0) + 100
            if session.vehicle_fuel > 1000:
                session.vehicle_fuel = 1000
                
            server.save_player_to_db(session)
            await session.send_packet(server.build_inventory_packet(session))
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Vehicle fueled successfully"))
            
    elif sub == 135:  # Repair Vehicle Request
        slot = reader.read_8()
        item = get_item_at_slot(session, slot)
        if item:
            item_id = item['item_id']
            item_name = server.items.get(str(item_id), "")
            if not any(x in item_name.lower() for x in ["spanner", "repair", "wrench"]):
                logger.warning(f"[{session.char_name}] Repair failed: {item_name} is not a valid repair tool.")
                # Send Repair failed packet: Opcode 15, sub 23, status 3 (Repairs failed)
                await session.send_packet(PacketWriter().write_8(15).write_8(23).write_8(3))
                return
                
            # Verify vehicle is active/equipped or player is riding
            if not getattr(session, 'riding_vehicle', False):
                logger.warning(f"[{session.char_name}] Repair failed: Only for Vehicles.")
                await session.send_packet(PacketWriter().write_8(15).write_8(23).write_8(3))
                return
                
            # Deduct 1 repair tool
            remove_item_at_slot(session, slot, 1)
            session.vehicle_damage = 0  # Reset damage
            
            server.save_player_to_db(session)
            await session.send_packet(server.build_inventory_packet(session))
            
            # Send Success: Opcode 15, sub 23, status 2 (Vehicle repaired)
            await session.send_packet(PacketWriter().write_8(15).write_8(23).write_8(2))
            
    elif sub == 14:  # Compound / Alchemy Request
        # Payload: [23, 14, count, slot1, slot2, ...]
        count = reader.read_8()
        slots = []
        for _ in range(count):
            slots.append(reader.read_8())
            
        logger.info(f"[{session.char_name}] Requesting Compound with slots: {slots}")
        
        # Verify items exist in these slots
        valid_items = []
        for s in slots:
            itm = get_item_at_slot(session, s)
            if itm:
                valid_items.append((s, itm['item_id']))
                
        if len(valid_items) == count and count >= 2:
            import random
            
            # 1. Deduct items (AC 23 Sub 9)
            for s, item_id in valid_items:
                remove_item_at_slot(session, s, 1)
                deduct_pkt = PacketWriter().write_8(23).write_8(9).write_8(s).write_8(1)
                await session.send_packet(deduct_pkt)
                
            # 2. Generate outcome item (Random or fixed for now)
            # In a real setup, calculate based on rank and alchemy formulas.
            # PCAP uses 106660 (which is an item ID). We will use a random generic item.
            outcome_item_id = 106660  # e.g. Black Clay or generic alchemy outcome
            
            # Add to inventory
            new_slot = add_item_to_inventory(session, outcome_item_id, 1)
            
            if new_slot is not None:
                server.save_player_to_db(session)
                
                # 3. Send AC 23 Sub 8 (Add Compound Result)
                # Payload: 17 08 slot(1 byte) item_id(4 bytes) + padding(28 bytes)
                res_pkt = PacketWriter().write_8(23).write_8(8)
                res_pkt.write_8(new_slot).write_32(outcome_item_id)
                res_pkt.write_bytes(bytes(28))
                await session.send_packet(res_pkt)
                
                # 4. Send AC 23 Sub 13 (Compound Success Window)
                # Payload: 17 0D item_id(4 bytes) slot(1 byte)
                anim_pkt = PacketWriter().write_8(23).write_8(13)
                anim_pkt.write_32(outcome_item_id).write_8(new_slot)
                await session.send_packet(anim_pkt)
                
                logger.info(f"[{session.char_name}] Compounding successful: {outcome_item_id} added at slot {new_slot}")
            else:
                # Inventory full during compounding? Usually materials are consumed first, so there should be space.
                logger.warning(f"[{session.char_name}] Compounding failed due to full inventory after deduction.")
        else:
            logger.warning(f"[{session.char_name}] Compounding failed: Missing items in slots.")

    elif sub == 15:  # Use Tent
        item_id = reader.read_32()
        logger.info(f"[{session.char_name}] Requesting to open tent (Item ID: {item_id})")
        
        # Tent spawn broadcast: AC 65 Sub 1
        # Format: [65, 1, char_id(4), X(2), Y(2), unk(2), skin(4), unk(4)]
        tent_pkt = PacketWriter().write_8(65).write_8(1)
        tent_pkt.write_32(session.char_id)
        tent_pkt.write_16(session.x)
        tent_pkt.write_16(session.y)
        tent_pkt.write_16(0)     # Padding / Unknown
        tent_pkt.write_32(1115)  # Default Tent Skin ID
        tent_pkt.write_32(0)     # Padding / Unknown
        
        # Broadcast the tent appearance to everyone on the map including the owner
        server.broadcast_to_map(session.map_id, tent_pkt)
        logger.info(f"[{session.char_name}] Spawned Tent at {session.x}, {session.y}")

    else:
        logger.info(f"Unhandled AC 23 Sub-Code: {sub}, payload: {reader.data.hex()}")
