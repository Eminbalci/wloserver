import logging
import sqlite3
import time
from server.network import PacketWriter

logger = logging.getLogger("WLO_Server")

ACTION_CODES = [20]


import re

def is_wild_monster(npc_template_id: int, name: str, map_id: int = 0) -> bool:
    """
    Accurately identifies whether an NPC is a wild hostile mob or a peaceful NPC/townsperson/prop.
    Ported from authentic WLO C# QuestNpc.IsWildMonster logic:
    - 10000-12999: Story characters, Companions, Sailors (Never wild monsters)
    - 13000-13999: Shops (Props, Weapon, Armor)
    - 14000-14999: Human Villagers, Townspeople, Passengers, Guards, Elders (e.g. Ashley 14013)
    - 15000-16999: Story / Quest Actors
    - 17000-17999: Authentic wild roaming monsters (e.g. Jellyfish, Spiders, Wolves)
    - 19000-24999: Props, Gathering nodes, Chests, Furniture
    - 25000+: Story cutscene actors
    """
    if not npc_template_id:
        return False

    name_lower = (name or "").lower().strip()

    # 1. Peaceful / Human / Service NPC keywords
    peaceful_keywords = [
        "shop", "store", "market", "keep", "storage", "bank", "vault", "atm", "exchanger",
        "doctor", "witch", "clinic", "hotel", "inn", "guidepost", "signpost", "statue",
        "villager", "citizen", "resident", "grandma", "grandmother", "grandfather",
        "elder", "mayor", "chief", "guard", "soldier", "knight", "merchant",
        "vendor", "trader", "peddler", "innkeeper", "waitress", "nurse", "priest",
        "monk", "clerk", "sailor", "captain", "chef", "cook", "maid", "blacksmith",
        "carpenter", "hunter", "miner", "guide", "girl", "boy", "kid", "child",
        "man", "woman", "lady", "sir", "passenger", "traveler", "tourist", "guest",
        "friend", "robinson", "ashley", "daniel", "iris", "vanessa", "breillat",
        "jessica", "konno", "maria", "karin", "sid", "more", "kurogane", "nina",
        "betty", "rocco", "niss", "elin", "cliff", "sam", "shizune", "clive", "xaolan",
        "chest", "box", "crate", "barrel", "pot", "wood", "stone", "ore", "tree", "mine"
    ]
    for k in peaceful_keywords:
        if len(k) <= 3:
            if re.search(r'\b' + re.escape(k) + r'\b', name_lower):
                return False
        else:
            if k in name_lower:
                return False

    # 2. Template ID Ranges in WLO:
    if npc_template_id < 17000 or npc_template_id >= 18000:
        return False

    # 3. Kelan Village Pigs or domestic animals in 17000-17999 range
    if npc_template_id == 17400 or "pig" in name_lower:
        return False

    # 4. In peaceful town / interior / cabin maps, no roaming hostile monsters
    if map_id in [10000, 10010, 60001] or (10001 <= map_id <= 10036) or (12000 <= map_id <= 12030) or (14000 <= map_id <= 14030):
        monster_names = ["spider", "wolf", "troll", "gelly", "jelly", "wasp", "snake", "boar", "shark", "dinosaur"]
        if not any(m in name_lower for m in monster_names):
            return False

    return True


async def handle(server, session, reader):
    """Processes portals, chest, and dialog clicks (AC 20)."""
    sub = reader.read_8()
    
    # General constraints based on client findings
    if getattr(session, 'is_fishing', False):
        logger.warning(f"[{session.char_name}] Interaction blocked: Player is currently fishing.")
        await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Fishing, can't act"))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        return
    if getattr(session, 'is_remote_control', False):
        logger.warning(f"[{session.char_name}] Interaction blocked: Remote control active.")
        await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Can't perform during remote control"))
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        return
        
    if sub == 8:  # Portal Collision Warp Request
        portal_id = reader.read_16()
        print(f"[PORTAL-RAW] {session.char_name} map={session.map_id} pos=({session.x},{session.y}) portal_id={portal_id} raw={reader.data.hex()}")
        logger.info(f"[{session.char_name}] Stepped on portal ID {portal_id} on map {session.map_id} pos=({session.x},{session.y}) (raw: {reader.data.hex()})")
        
        # Check portal warp cooldown (1.0 seconds)
        current_time = time.time()
        if current_time - getattr(session, 'last_warp_time', 0.0) < 1.0:
            logger.info(f"[{session.char_name}] Ignoring portal collision due to warp cooldown.")
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            return
        
        # Client portal_id may be Gray-coded. Try raw first, then Gray-decoded.
        dst_map, dst_x, dst_y = server.lookup_portal(session.map_id, portal_id, px=session.x, py=session.y)
        if dst_map is None:
            # Try Gray-decoded portal_id
            def _gray_decode(n):
                mask = n
                while mask:
                    mask >>= 1
                    n ^= mask
                return n
            gray_id = _gray_decode(portal_id)
            if gray_id != portal_id:
                logger.info(f"[{session.char_name}] Trying Gray-decoded portal_id: {portal_id} -> {gray_id}")
                dst_map, dst_x, dst_y = server.lookup_portal(session.map_id, gray_id, px=session.x, py=session.y)
        
        if dst_map:
            print(f"[PORTAL] {session.char_name} used portal {portal_id} on map {session.map_id} -> map {dst_map} (x={dst_x}, y={dst_y})")
            logger.info(f"[PORTAL] {session.char_name} used portal {portal_id} on map {session.map_id} -> map {dst_map} (x={dst_x}, y={dst_y})")
            await server.warp_player(session, dst_map, dst_x, dst_y, portal_id)
        else:
            logger.warning(f"[{session.char_name}] Portal {portal_id} not found on map {session.map_id}!")
            # Notify GM chat warning about missing portal destination
            prompt = PacketWriter().write_8(23).write_8(57).write_8(0).write_string(
                f"Portal {portal_id} is not mapped in ServerDataBase.db. Use GM command :warp <map> <x> <y>."
            )
            await session.send_packet(prompt)
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            
    elif sub == 1:  # NPC click
        if reader.remaining_bytes() >= 4:
            reader.read_bytes(3)  # Skip 3 bytes (unk/padding)
            click_id = reader.read_8()
        else:
            click_id = reader.read_8() if reader.remaining_bytes() > 0 else 0
        native_click_id = click_id
        session.last_clicked_npc_id = native_click_id
        logger.info(f"[{session.char_name}] Clicked NPC/Object ID {click_id} on map {session.map_id} (native ID: {native_click_id})")

        # Find the clicked NPC in the map NPCs list
        map_npcs = server.map_npcs.get(session.map_id, [])
        npc = None
        for n in map_npcs:
            if n['click_id'] == native_click_id:
                npc = n
                break
        
        if npc:
            # Distance check (0xa9 = 169 pixels limit)
            npc_x = npc.get('x', 0)
            npc_y = npc.get('y', 0)
            if abs(session.x - npc_x) > 169 or abs(session.y - npc_y) > 169:
                logger.warning(f"[{session.char_name}] NPC interaction blocked: NPC too far X={abs(session.x - npc_x)} Y={abs(session.y - npc_y)}")
                await session.send_packet(PacketWriter().write_8(20).write_8(8))  # Release client lock
                return

            npc_template_id = npc.get('npc_id', 0)
            
            # Resolve canonical authentic NPC name from eve.Emg, Npc.dat, or SceneDataManager
            name = (npc.get('name') or "").strip('\x00').strip()
            if not name or name.lower() == "npc" or name.startswith("unknown"):
                from server.dat_loaders import GLOBAL_NPC_DAT
                name = GLOBAL_NPC_DAT.get_npc_name(npc_template_id)
                if not name or name.startswith("NPC #"):
                    if 14000 <= npc_template_id < 15000:
                        name = "Villager"
                    elif npc_template_id in (13005, 13006, 13007):
                        name = "Shopkeeper"
                    elif npc_template_id == 14151:
                        name = "Doctor"
                    elif npc_template_id == 14134:
                        name = "Props Keeper"
                    elif npc_template_id == 14181:
                        name = "Banker"
                    elif npc_template_id == 17400:
                        name = "Pig"
            
            logger.info(f"[NPC Click] Clicked NPC '{name}' (ID: {click_id}, template: {npc_template_id})")

            # --- 0. WILD MONSTER CLICK (PvE Combat Trigger) ---
            if is_wild_monster(npc_template_id, name, session.map_id):
                logger.info(f"[{session.char_name}] Clicked wild monster NPC {npc_template_id} ({name}) -> entering battle!")
                await server.enter_battle(session, native_click_id, npc_template_id)
                return

            # --- 1. EVE EVENT INTERPRETER (Authentic eve.Emg native event tree) ---
            from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
            if await GLOBAL_EVE_INTERPRETER.try_execute(server, session, native_click_id):
                return

            # --- 1.2 STATIC CHEST / PROP / GATHERING NODE (1:1 C# QuestNpc.cs line 448) ---
            is_static = False
            if hasattr(npc, 'is_static_npc'):
                is_static = npc.is_static_npc()
            else:
                from server.npc_manager import QuestNpc
                dummy = QuestNpc(map_id=session.map_id, click_id=native_click_id, name=name, npc_id=npc_template_id, x=npc_x, y=npc_y)
                is_static = dummy.is_static_npc()

            if is_static and npc_template_id not in (14181, 14157, 14151, 14182, 14152):
                chest_sys = getattr(server, 'chest_system', None)
                if not chest_sys:
                    from server.chest_system import GLOBAL_CHEST_SYSTEM
                    chest_sys = GLOBAL_CHEST_SYSTEM

                if chest_sys:
                    await chest_sys.open_chest(server, session, session.map_id, native_click_id, prop_name=name)
                else:
                    is_broken = getattr(npc, 'is_broken', False) or (npc.get('is_broken', False) if isinstance(npc, dict) else False)
                    if is_broken:
                        await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("This node/chest is currently empty and will respawn soon."))
                        await session.send_packet(PacketWriter().write_8(20).write_8(8))
                        await session.send_packet(PacketWriter().write_8(5).write_8(4))
                        return

                    anim = PacketWriter().write_8(22).write_8(1).write_16(native_click_id).write_8(1)
                    await session.send_packet(anim)
                    server.broadcast_to_map(session.map_id, anim, exclude_session=session)

                    if hasattr(npc, 'is_broken'):
                        npc.is_broken = True
                    elif isinstance(npc, dict):
                        npc['is_broken'] = True

                    from server.gameserver import add_item_to_inventory
                    item_id = 41066 if "coconut" in name.lower() else (27001 if "wood" in name.lower() else 28014)
                    add_item_to_inventory(session, item_id, 1)
                    item_name = server.get_item_name(item_id)
                    await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(f"Obtain {item_name}"))
                    await session.send_packet(PacketWriter().write_8(20).write_8(10))
                    await session.send_packet(server.build_inventory_packet(session))
                    server.save_player_to_db(session)
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
                    await session.send_packet(PacketWriter().write_8(5).write_8(4))
                return

            # --- 1.5 EXPLICIT DOOR / PORTAL TRIGGER CHECK ---
            if "door" in name.lower() or "door" in (npc.get('name') or "").lower():
                linked_portals = npc.get('linked_portals', [])
                if linked_portals:
                    portal_id = linked_portals[0]
                    dst_map, dst_x, dst_y = server.lookup_portal(session.map_id, portal_id, px=npc_x, py=npc_y)
                    if dst_map:
                        logger.info(f"[DOOR] {session.char_name} used door NPC {native_click_id} (portal {portal_id}) -> map {dst_map} ({dst_x},{dst_y})")
                        await server.warp_player(session, dst_map, dst_x, dst_y, portal_id)
                        return

            # --- 2. MASTER QUEST ENGINE (1,050 Authentic Quests from Mark.dat) ---
            from server.quests import GLOBAL_QUEST_ENGINE
            quest_handled, quest_dialogue = await GLOBAL_QUEST_ENGINE.try_handle_npc_quest(server, session, name, npc_template_id)
            if quest_handled and quest_dialogue:
                logger.info(f"[{session.char_name}] Master Quest handled for NPC '{name}' (TID: {npc_template_id}): {quest_dialogue}")
                talk_id = 51168
                await server.send_dialogue(session, native_click_id, talk_id, step=1, portrait_type=3)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(quest_dialogue))
                return

            # --- 3. NPC SERVICES & INTERACTION ---
            # ATM / Bank NPC Interaction
            if "bank" in name.lower() or "atm" in name.lower() or npc_template_id in (14181, 14157):
                dialogue_text = (
                    f"Welcome to WLO Bank!\n"
                    f"Your Inventory Gold: {getattr(session, 'gold', 0):,} gold.\n"
                    f"Your Bank Balance: {getattr(session, 'bank_gold', 0):,} gold."
                )
                await server.send_dialogue(session, native_click_id, 51168, step=1, portrait_type=3)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(dialogue_text))
                return

            # Clinic / Doctor NPC Interaction
            if "doctor" in name.lower() or "clinic" in name.lower() or npc_template_id == 14151:
                max_hp = getattr(session, 'max_hp', 200)
                max_sp = getattr(session, 'max_sp', 100)
                session.hp = max_hp
                session.sp = max_sp
                # Send HP / SP full recovery
                await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x0119).write_32(max_hp).write_32(0))
                await session.send_packet(PacketWriter().write_8(8).write_8(1).write_16(0x011a).write_32(max_sp).write_32(0))
                dialogue_text = "Welcome to the Clinic! Your HP and SP have been fully restored."
                logger.info(f"[{session.char_name}] Restored HP/SP at Doctor (Clinic).")
                await server.send_dialogue(session, native_click_id, 51155, step=1, portrait_type=3)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(dialogue_text))
                return

            # Pet Hotel / Pet Keeper
            if "pet hotel" in name.lower() or "pet keep" in name.lower() or npc_template_id in (14182, 14152):
                dialogue_text = "Welcome to the Pet Hotel! Your companions are in good hands."
                await server.send_dialogue(session, native_click_id, 51168, step=1, portrait_type=3)
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(dialogue_text))
                return

            # Specific character / passenger / story dialogues
            name_lower = (name or "").lower()
            talk_id = 51168
            if npc_template_id == 14013 or "ashley" in name_lower or "mary lou" in name_lower:
                talk_id = 39378 if session.map_id == 12000 else 42605
                dialogue_text = "Hello! I'm Ashley. Are you enjoying this wonderful voyage? The sea breeze is so refreshing today!"
            elif npc_template_id == 14512 or "casino" in name_lower or "astrologia" in name_lower:
                talk_id = 41232
                dialogue_text = "Welcome to the Casino! Enjoy your games and entertainment."
            elif npc_template_id == 12032 or "robinson" in name_lower:
                talk_id = 41916
                dialogue_text = "This is a deserted island. How did you end up here?"
            elif "captain" in name_lower:
                talk_id = 41824
                dialogue_text = "Welcome aboard the Princess Cruise! We are sailing steadily towards our destination."
            elif "sailor" in name_lower:
                talk_id = 39263
                dialogue_text = "Everything is running smoothly on deck! Let me know if you need directions around the ship."
            elif "passenger" in name_lower or session.map_id == 12000:
                talk_id = 39378
                dialogue_text = "Hello there! Welcome to Welling Village!" if session.map_id == 12000 else "Isn't this luxury ship amazing? I love looking out at the endless blue horizon."
            elif "villager" in name_lower or "citizen" in name_lower:
                talk_id = 39378 if session.map_id == 12000 else 51168
                dialogue_text = "Welcome to our village! Please make yourself at home and enjoy your stay."
            else:
                talk_id = 51168
                dialogue_text = f"Hello, adventurer! I am {name}. Welcome to our land! Let me know if you need any assistance."

            logger.info(f"[NPC Click] Sending authentic dialogue window (AC 20 Sub 1, TalkID: {talk_id}): text='{dialogue_text}'")
            await server.send_dialogue(session, native_click_id, talk_id, step=1, portrait_type=3)
            await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string(dialogue_text))
                
    elif sub == 6:  # Continue interaction
        logger.info(f"[{session.char_name}] Continue interaction (AC 20 Sub 6)")
        
        # 0. Storm Cutscene Completion -> Warp to Shipwreck Beach (Map 10035)
        if getattr(session, 'playing_storm_cutscene', False):
            elapsed = time.time() - getattr(session, 'storm_cutscene_start_time', 0)
            if elapsed < 1.0:
                logger.debug(f"[{session.char_name}] Absorbed premature AC 20:6 during Storm Cutscene movie initialization (elapsed: {elapsed:.2f}s)")
                return

            session.playing_storm_cutscene = False
            session.pending_beach_cutscene = True
            session.on_interaction_complete = None
            logger.info(f"[{session.char_name}] Storm Cutscene completed (AC 20:6, duration: {elapsed:.2f}s) -> Teleporting to Beach (Map 10035)")
            await session.send_packet(PacketWriter().write_8(20).write_8(7))  # Warp Out
            await server.warp_player(session, 10035, 1038, 2235)
            return

        # 1. Absorb AC 20:6 during active beach cutscene timeline (Matching C# AC20.cs line 156)
        if getattr(session, 'beach_cutscene_active', False):
            logger.debug(f"[{session.char_name}] Absorbed AC 20:6 during BeachCutsceneActive timeline")
            return

        # 2. Dialogue Queue Advancement (Multi-step dialogue playback)
        queue = getattr(session, 'dialogue_queue', None)
        if queue and len(queue) > 0:
            next_step = queue.pop(0)
            from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
            await GLOBAL_EVE_INTERPRETER._dispatch_step(server, session, next_step)
            return

        # 2b. Map 10035 Robinson Beach Dialogue Completion
        if getattr(session, 'map_id', 0) == 10035 and getattr(session, 'emote', 0) == 9:
            session.emote = 0
            # Frame 2997: Robinson returns to normal standing posture (AC 22:12 [1, 1, 0, 6])
            stand_pkt = PacketWriter().write_8(22).write_8(12).write_8(1).write_8(1).write_8(0).write_8(6)
            await session.send_packet(stand_pkt)
            server.broadcast_to_map(session.map_id, stand_pkt, exclude_session=session)

            # Player stands up (AC 32:2 [char_id, 0])
            e_reset = PacketWriter().write_8(32).write_8(2).write_32(session.char_id).write_8(0)
            await session.send_packet(e_reset)
            server.broadcast_to_map(session.map_id, e_reset, exclude_session=session)

            # Mark Quest 12040 Step 1
            from server.eve_event_interpreter import set_session_quest_state
            set_session_quest_state(session, 12040, 1)
            server.save_player_to_db(session)

            # Unlock Cinema mode, Screen, and Controls
            await session.send_packet(PacketWriter().write_8(6).write_8(2).write_8(0))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            await session.send_packet(PacketWriter().write_8(5).write_8(4))
            logger.info(f"[{session.char_name}] Beach Arrival Cutscene & Robinson dialogue completed. Controls restored.")
            return
            
        # 3. Check Defer Scene Transition Warp
        complete_warp = getattr(session, 'on_interaction_complete', None)
        if complete_warp:
            session.on_interaction_complete = None
            if complete_warp.get("pending_beach"):
                session.pending_beach_cutscene = True
            await server.warp_player(session, complete_warp["map_id"], complete_warp["x"], complete_warp["y"])
            return

        # Check post-battle quest warp
        win_warp = getattr(session, 'battle_win_warp', None)
        if win_warp:
            session.battle_win_warp = None
            logger.info(f"[{session.char_name}] Triggering post-battle quest warp to map {win_warp['map_id']} pos=({win_warp['x']},{win_warp['y']})")
            
            # Niss quest check:
            if getattr(session, 'quest_battle_id', None) == 11066:
                if not hasattr(session, 'quests') or session.quests is None:
                    session.quests = {}
                session.quests['niss'] = 1  # State 1: saved Niss (waiting for pet claim)
                server.save_player_to_db(session)
                session.quest_battle_id = None
                
            await server.warp_player(session, win_warp['map_id'], win_warp['x'], win_warp['y'])
            return
        
        # Check pending battle unlock
        if getattr(session, 'pending_battle_unlock', False):
            session.pending_battle_unlock = False
            logger.info(f"[{session.char_name}] Post-battle unlock: sending map ready and unlock")
            await session.send_packet(PacketWriter().write_8(23).write_8(102))
            await session.send_packet(PacketWriter().write_8(20).write_8(8))
            return
            
        # Handle active quest script
        if session.active_quest_id is not None:
            script = server.quest_scripts.get(session.active_quest_id, [])
            session.active_quest_step += 1
            
            if session.active_quest_step >= len(script):
                logger.info(f"[{session.char_name}] Finished quest script for NPC {session.active_quest_id}")
                session.active_quest_id = None
                session.active_quest_step = 0
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                return
            
            action = script[session.active_quest_step]
            step_num = getattr(session, 'active_quest_dialog_counter', 1)
            
            if action["type"] == "spawn":
                await server._send_quest_spawn(session, action["hex"])
                if "dialog_hex" in action:
                    await server._send_quest_dialogue(session, action["dialog_hex"], session.active_quest_id, step=step_num)
                    session.active_quest_dialog_counter = step_num + 1
            elif action["type"] == "dialog":
                portrait = 3 if action.get('is_quest') else 7
                await server._send_quest_dialogue(session, action["hex"], session.active_quest_id, step=step_num, portrait_type=portrait)
                session.active_quest_dialog_counter = step_num + 1
            elif action["type"] == "flag":
                await server._send_quest_flag(session, action["quest_id"], action["state"])
                next_step = session.active_quest_step + 1
                if next_step < len(script) and script[next_step]["type"] == "dialog":
                    session.active_quest_step = next_step
                    next_action = script[next_step]
                    portrait = 3 if next_action.get('is_quest') else 7
                    await server._send_quest_dialogue(session, next_action["hex"], session.active_quest_id, step=step_num, portrait_type=portrait)
                    session.active_quest_dialog_counter = step_num + 1
                else:
                    logger.info(f"[{session.char_name}] Quest script flag sent. Unlocking.")
                    session.active_quest_id = None
                    session.active_quest_step = 0
                    session.active_quest_dialog_counter = 1
                    await session.send_packet(PacketWriter().write_8(20).write_8(8))
            
            return

        await session.send_packet(PacketWriter().write_8(20).write_8(8))
        await session.send_packet(PacketWriter().write_8(5).write_8(4))
        
    elif sub == 9 or sub == 2:  # Select dialogue option (sub=9 legacy, sub=2 client-accurate)
        option_id = reader.read_8()
        logger.info(f"[{session.char_name}] Selected dialogue option {option_id} (Hex: {hex(option_id)}) (sub={sub})")

        # 0. Native EveEventInterpreter Choice Branch Resolution
        if getattr(session, 'pending_dialogue_choice', None):
            from server.eve_event_interpreter import GLOBAL_EVE_INTERPRETER
            if await GLOBAL_EVE_INTERPRETER.handle_choice_selection(server, session, option_id):
                return
        
        # Marriage Wedding Dress Check (Option 14: hold hands / oath)
        if option_id == 14:
            has_wedding_dress = False
            for equip_id in session.equipments:
                item_name = server.items.get(str(equip_id), "")
                if "wedding" in item_name.lower() or "dress" in item_name.lower():
                    has_wedding_dress = True
                    break
            if not has_wedding_dress:
                logger.warning(f"[{session.char_name}] Marriage blocked: Bride needs to dress up.")
                await session.send_packet(PacketWriter().write_8(23).write_8(57).write_8(0).write_string("Bride needs to dress up"))
                await session.send_packet(PacketWriter().write_8(20).write_8(8))
                return

        # NPC Shop Menu Transitions (Reverse-Engineered from shoplarincalismamantigi.pcapng)
        if option_id == 0x1e:  # Option 30: Open Shop Transaction Menu (Buy/Sell selection)
            # Send Menu 2 prompt [Pkt #677]: [14 01 00 00 00 01 06 03 17 00 00 00 00 00 00 06 00 02]
            current_click = getattr(session, "last_clicked_npc_id", 23) or 23
            menu2_pkt = (
                PacketWriter()
                .write_8(20)
                .write_8(1)
                .write_32(0)
                .write_8(1)
                .write_8(6)
                .write_8(3)
                .write_16(current_click)
                .write_bytes(bytes(6))
                .write_8(6)
                .write_8(0)
                .write_8(2)
            )
            await session.send_packet(menu2_pkt)
            return

        elif option_id == 0x1f:  # Option 31: Buy (Opens Props Shop or Weapon Shop)
            # Check if active NPC is Weapon/Armor merchant or Props merchant
            current_click = getattr(session, "last_clicked_npc_id", 23) or 23
            is_weapon_npc = current_click in (24, 13006, 13007)
            shop_sub = 4 if is_weapon_npc else 3
            await session.send_packet(PacketWriter().write_8(27).write_8(shop_sub))
            await session.send_packet(PacketWriter().write_8(20).write_8(9))
            return

        elif option_id == 0x28:  # Option 40: Sell (Opens Player Inventory Sell Window)
            # Send AC 20 Sub 9 to release dialogue lock so client displays inventory sell UI
            await session.send_packet(PacketWriter().write_8(20).write_8(9))
            return
            
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
    else:
        logger.warning(f"[{session.char_name}] Unhandled AC 20 Sub: {sub}")
        await session.send_packet(PacketWriter().write_8(20).write_8(8))
