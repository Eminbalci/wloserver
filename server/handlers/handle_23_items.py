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
        if getattr(session, 'bathing', False):
            logger.warning(f"[{session.char_name}] Action {sub} blocked: Player is currently bathing.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't use in bath"))
            return

    from server.item_mall import GLOBAL_ITEM_MALL_MANAGER

    if sub == 54:
        # Client sends this as acknowledgment after receiving the login/warp complete signal (5, 4), or to stop fishing
        if getattr(session, 'is_fishing', False):
            session.is_fishing = False
            logger.info(f"[{session.char_name}] Stop fishing request received (23, 54)")
            # Send stop fishing confirmation: [23, 54, 0]
            await session.send_packet(PacketWriter().write_8(23).write_8(54).write_8(0))
        else:
            logger.info(f"[{session.char_name}] Received warp-done ACK (23, 54) — entering map")
            session.is_warping = False
            session.in_map = True
            await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub == 25:  # Request IM Point Balance (C# AC23.Recv25)
        await GLOBAL_ITEM_MALL_MANAGER.send_point_balance(session)

    elif sub == 26:  # Buy Item from Mall (C# AC23.Recv26)
        if reader.remaining_bytes() >= 2:
            item_id = reader.read_16()
            count = reader.read_8() if reader.remaining_bytes() >= 1 else 1
            if count <= 0:
                count = 1
            await GLOBAL_ITEM_MALL_MANAGER.purchase_item(server, session, item_id, count)

    elif sub == 77:  # Request Player Stall / Market Listings (C# AC23.Recv77)
        # S->C [23, 4, 0] = stall list (0 active)
        await session.send_packet(PacketWriter().write_8(23).write_8(4).write_8(0))
        # S->C [23, 102] = end of stall list
        await session.send_packet(PacketWriter().write_8(23).write_8(102))

    elif sub == 53:  # Start fishing request (23, 53)
        if getattr(session, 'is_stall_active', False):
            logger.warning(f"[{session.char_name}] Fishing blocked: Player has an active stall.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Cancel Stall to fish"))
            return
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
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("LV is low to equip"))
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
    elif sub == 15:  # HP / SP Auto-Recovery / Quick-Fill Button Click (AC 23 Sub 15)
        # Authentic payload: [23, 15, stat_type (8=HP, 9=SP), target_type (1=self/pet), slot (uint16_LE: 0=player, >0=pet)]
        from server.sustenance_system import GLOBAL_SUSTENANCE_MANAGER
        if reader.remaining_bytes() >= 4:
            stat_type = reader.read_8()
            target_type = reader.read_8()
            slot = reader.read_16()
            await GLOBAL_SUSTENANCE_MANAGER.handle_auto_heal_button(server, session, stat_type, target_type, slot)

    elif sub == 3:  # Drop item on ground
        if getattr(session, 'bathing', False):
            logger.warning(f"[{session.char_name}] Drop blocked: Player is currently bathing.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Don't litter In Hot Springs!"))
            return
            
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
                
    elif sub == 2:  # Pick up item from ground (AC 23 Sub 2)
        # Authentic payload: [23, 2, ground_slot (uint16_LE)]
        pos = reader.read_16() if reader.remaining_bytes() >= 2 else reader.read_8()
        
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
                    await session.send_packet(PacketWriter().write_8(26).write_8(4).write_32(session.gold))
                    success = True
                else:
                    slot = add_item_to_inventory(session, item_id, amount=qnt)
                    if slot is not None:
                        # Authentic AC 23 Sub 6: Add item to inventory (33 bytes)
                        # S->C [23, 6, item_id (uint16_LE), count (uint16_LE), 27 zero bytes]
                        item_pkt = PacketWriter().write_8(23).write_8(6).write_16(item_id).write_16(qnt).write_bytes(bytes(27))
                        await session.send_packet(item_pkt)
                        success = True
                        
                if success:
                    # Clear ground slot
                    server.map_ground_items[session.map_id][pos - 1] = None
                    server.save_player_to_db(session)
                    
                    # Authentic AC 23 Sub 2: Ground Item Despawn broadcast (5 bytes)
                    # S->C [23, 2, ground_slot (uint16_LE), 1]
                    despawn_pkt = PacketWriter().write_8(23).write_8(2).write_16(pos).write_8(1)
                    server.broadcast_to_map(session.map_id, despawn_pkt)
                    
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
            
        # Broadcast compounding visual effect to map (AC 23 Sub 122)
        server.broadcast_to_map(session.map_id, PacketWriter().write_8(23).write_8(122).write_32(session.char_id))

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
            
            # AC 23 Sub 9: Deduct 1 item from slot (Authentic format: [23, 9, slot, 1])
            await session.send_packet(PacketWriter().write_8(23).write_8(9).write_8(slot).write_8(1))
            
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
            # Authentic AC 23 Sub 8: Add Compounded item to slot (33 bytes)
            # S->C [23, 8, slot (uint8), item_id (uint16_LE), count (uint8), 27 zero bytes]
            p8 = PacketWriter().write_8(23).write_8(8).write_8(target_slot).write_16(result_item).write_8(min(255, result_amount)).write_bytes(bytes(27))
            await session.send_packet(p8)
            
            # Authentic AC 23 Sub 13: Compounding Success Result Window (6 bytes)
            # S->C [23, 13, item_id (uint16_LE), count (uint8), slot (uint8)]
            p13 = PacketWriter().write_8(23).write_8(13).write_16(result_item).write_8(min(255, result_amount)).write_8(target_slot)
            await session.send_packet(p13)
            
            # Save progress
            server.save_player_to_db(session)
            logger.info(f"[{session.char_name}] Compounded {item_ids} into {result_item} x{result_amount} in slot {target_slot}")
        else:
            logger.warning(f"[{session.char_name}] Compounding failed because inventory is full.")
            
    elif sub == 65:  # Street Stall Open/Activate Request (0x17, 0x41)
        if getattr(session, 'riding_vehicle', False):
            logger.warning(f"[{session.char_name}] Stall blocked: Player is riding a vehicle.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't use when mounted"))
            return
        if getattr(session, 'is_fishing', False):
            logger.warning(f"[{session.char_name}] Stall blocked: Player is fishing.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Fishing, can't act"))
            return
        session.is_stall_active = True
        logger.info(f"[{session.char_name}] Open Street Stall requested")
        # Echo success response for stall activation
        await session.send_packet(PacketWriter().write_8(23).write_8(65).write_8(1))
        
    elif sub == 66:  # Close Street Stall Request
        session.is_stall_active = False
        logger.info(f"[{session.char_name}] Street Stall closed")
        await session.send_packet(PacketWriter().write_8(23).write_8(66).write_8(1))
        
    elif sub == 99:  # Open NPC Shop Request (0x17, 99)
        npc_id = reader.read_16() if reader.remaining_bytes() >= 2 else 0
        logger.info(f"[{session.char_name}] NPC Shop open request for NPC ID={npc_id}")
        # Echo success response to open NPC shop UI
        await session.send_packet(PacketWriter().write_8(23).write_8(99).write_16(npc_id).write_8(1))
        
    elif sub == 51:  # Board / Ride Vehicle
        if getattr(session, 'is_stall_active', False):
            logger.warning(f"[{session.char_name}] Board vehicle blocked: Active stall.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't mount with Stall"))
            return
        if getattr(session, 'bathing', False):
            logger.warning(f"[{session.char_name}] Board vehicle blocked: Bathing.")
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't mount in bath"))
            return
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
            
    elif sub == 100:  # Use Tent item from inventory
        item_id = reader.read_32() if reader.remaining_bytes() >= 4 else 38001
        logger.info(f"[{session.char_name}] Requesting to open tent (Item ID: {item_id})")
        from server.tent import GLOBAL_TENT_MANAGER
        tent = GLOBAL_TENT_MANAGER.get_or_create_tent(session.char_id)
        GLOBAL_TENT_MANAGER.pitch_tent_on_map(server, session, tent.tent_type)

    else:
        logger.info(f"Unhandled AC 23 Sub-Code: {sub}, payload: {reader.data.hex()}")
