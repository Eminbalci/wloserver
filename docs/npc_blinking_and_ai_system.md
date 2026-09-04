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

### 2.3 Client-Side Walk Simulation & Blinking Prevention
- **Native Map NPC Simulation**: Native `eve.Emg` map NPCs have their walk cycles and waypoints animated locally by the Wonderland Online client engine. Broadcasting redundant server-side `AC 22 Sub 2` movement packets forcefully resets the client sprite animation to frame 0, causing rapid flickering and blinking.
- **Server Update Responsibility**: `QuestNpc.update()` solely manages gathering node respawn lifecycles (`AC 22 Sub 10`), leaving native map NPC animation loops to the client's internal renderer.

### 2.4 Authentic Visibility & Respawn Packets
- **Hide / Despawn**: `AC 22 Sub 10` `[22, 10, clickId (2B), 0xFF, 0xFF]`
- **Show / Respawn**: `AC 22 Sub 10` `[22, 10, clickId (2B), 0x00, 0x00]`
- **Chest Open State**: `AC 22 Sub 1` `[22, 1, clickId (2B), 0x01]`
- **Map Load Batch Registration**: `AC 22 Sub 4` `[22, 4, (clickId 2B, state 2B, x 2B, y 2B, 1 1B, 0 1B, 0 4B)...]`
  - `state = 0x0000`: Closed / Intact / Normal state.
  - `state = 0x0001`: Opened / Broken / Action state (for looted treasure chests, broken crates, gathered nodes).
  - `state = 0xFFFF`: Recruited companion or hidden entity.

### 2.5 Permanent Chest vs Gathering Node Classification
- **Permanent Chests** (`QuestNpc.is_permanent_chest()`):
  - Templates `19034` (Treas Che), `19035` (Treas Che), `19037` (Cask), `19038` (Chest/Crate), `12000-12999`, `16000-16999`.
  - Persisted in SQLite `charchests`.
  - Once looted, remains in `state = 0x0001` (open/broken) permanently per character.
  - `QuestNpc.update()` immediately returns for permanent chests and never broadcasts respawn packets.
  - `is_chest_opened(char_id, map_id, chest_id, is_permanent=True)` guarantees permanent chests never expire after `default_respawn_seconds`.
- **Gathering Nodes** (`QuestNpc.is_gathering_node()`):
  - Coconuts, ores, clay, wood, herbs, mushrooms.
  - Respawns after cooldown using `AC 22 Sub 10 [clickId, 0x00, 0x00]`.

### 2.6 Blinking & Flickering Root Causes & Fixes
1. **Redundant AC 22:10 on Map Load (`send_map_info`)**:
   - `send_map_info` was sending `AC 22:10 [clickId, 0xFF, 0xFF]` immediately following `AC 22:4`. Static props and permanent chests are now excluded from post-`AC 22:4` hide packet iterations.
2. **PreEvent Visibility Redundant Show Packets (`preevent_interpreter.py`)**:
   - `sync_per_player_npc_visibility` was broadcasting `AC 22:10 [clickId, 0x00, 0x00]` for visible rules, resetting static prop sprite animations to frame 0 and causing blinking. Static props and chests are now excluded from sending redundant show packets.
3. **Chest System Respawn Expiration**:
   - `ChestSystem.is_chest_opened()` was resetting opened chests back to closed state after 60 seconds because `default_respawn_seconds` expired. Added strict `is_permanent` flag to keep world chests open permanently without blinking.
