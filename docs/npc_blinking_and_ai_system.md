# NPC Blinking Prevention, AI Waypoint & Roaming Architecture

## 1. Problem Diagnosis
In the Wonderland Online client engine, `AC 22 Sub 2` (`[22, 2, clickId (2B), X (2B), Y (2B), speed (1B)]`) commands a ClickID to execute the dynamic movement animation. For static props (such as wooden chests, crates, trees, coconut nodes, ores), the client's "walking" animation frame is an open or moving state. When movement packets are repeatedly broadcast to static ClickIDs, the client toggles between its walking animation and idle frame, resulting in rapid continuous blinking / flickering.

### Root Causes
1. **Misclassified Native Spawns**: Unfiltered `eve.Emg` map parsing loaded phantom entities (`clickId == 0`, `x == 0, y == 0`, `x > 4000, y > 4000`).
2. **Incorrect Visibility Packets**: Legacy server code dispatched `AC 22 Sub 6` for hidden NPCs instead of authentic `AC 22 Sub 10` `[22, 10, clickId (2B), 0xFF, 0xFF]`, causing packet decoding errors in the client engine.
3. **Unconstrained Roaming in Towns**: Domestic farm animals (pigs in Kelan Village) and town citizens were erroneously treated as wild monsters with roaming deltas.

---

## 2. 1:1 C# Parity Solution (`server/npc_manager.py`)

### 2.1 Strict Spawn Filtering
```python
# Map.cs line 187 parity:
if click_id == 0 or (x == 0 and y == 0) or x > 4000 or y > 4000:
    continue
```

### 2.2 Complete Static Prop & Chest Classification (`QuestNpc.is_static_npc()`)
- Template IDs in `12000-12999` (crates, props, beach wreckage)
- Template IDs in `16000-16999` (props, furniture, chests)
- Template IDs in `19000-35000` (mechanisms, statues, static world props)
- Domestic farm animals (`TemplateID == 17400` / Kelan Village pigs)
- Starter ship / beach ClickIDs 6, 7, 10 on maps 10017 and 10035
- Keywords: `chest`, `box`, `crate`, `barrel`, `pot`, `machine`, `wood`, `stone`, `clay`, `mine`, `herb`, `tree`, `door`, `switch`, `lever`, `cabinet`, `desk`, `bed`, `chair`, `stove`, `grass`, `flower`, `shell`, `mushroom`, `ore`, `statue`, `fountain`, `sign`, `well`, `grave`, `cart`, `boat`, `wreck`, `tent`, `fence`, `portal`, `warp`, `prop`, `object`, `game machine`, `coconut`, `driftwood`, `bamboo`, `iron ore`, `copper ore`, `storage`, `bank`, `clinic`, `hotel`, `inn`, `exchanger`, `doctor`, `witch`, `shop`, `store`, `market`.

### 2.3 Scripted Waypoint & Wild Roaming Control (`QuestNpc.update()`)
- **Scripted Waypoints**: Follow predetermined waypoints from `eve.Emg` with natural `3.5s - 7.5s` pauses and walking speed 2 (`AC 22:2`).
- **Outdoor Wild Monsters**: Roam ONLY on field maps (`not is_village_or_town_map()`) with a tight `±40px` step delta and a maximum `60px` leash from spawn.
- **Town & Village Map Safeguards**: Maps 10000..10036 (Kelan), 12000..12030 (Welling), 14000..14030 (Holy Village), 16000..16030 (Kyoto), 18000..18030 (Chang'an) are strictly protected; NPCs without scripted waypoints remain static.

### 2.4 Authentic Visibility & Respawn Packets
- **Hide / Despawn**: `AC 22 Sub 10` `[22, 10, clickId (2B), 0xFF, 0xFF]`
- **Show / Respawn**: `AC 22 Sub 10` `[22, 10, clickId (2B), 0x00, 0x00]`
- **Chest Open State**: `AC 22 Sub 1` `[22, 1, clickId (2B), 0x01]`
