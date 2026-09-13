# NPC Visibility, PreEvent Interpreter & Companion Isolation

This technical specification details the runtime actor visibility architecture, dual-packet despawn protocol (`AC 22 Sub 10` & `AC 22 Sub 11`), companion party isolation, and per-map PreEvent bytecode resolution in Wonderland Online.

## Architectural Purpose

In official Wonderland Online, story companions (such as Roca, Robinson, Niss, Clive, Fred) and staged quest actors (pigs, lost pets, gravestones, monuments) exist across multiple map coordinate spaces and submaps. To prevent visual duplication, client-side sprite ghosting, or narrative sequence breaks:
1. **Scene Isolation**: Companions must only appear in their canonical map scenes prior to recruitment and must vanish upon joining a player's active party or pet roster.
2. **Dual-Packet Synchronization**: Both `AC 22 Sub 10` (actor spawn/despawn frame) and `AC 22 Sub 11` (scene interaction hitbox isolation) must be dispatched simultaneously.
3. **Map-Specific Visibility Lifecycles**:
   - **Map 12000 (Kelan Village Outdoors)**: Roca (`CID 32`) is strictly hidden outdoors; grave cutscene copy (`CID 34`) is visible only during Quest 13052 ("Death of Roca's Father") prior to recruitment; `CID 36` is permanently hidden.
   - **Map 12001 (Kelan Chief's House)**: Roca (`CID 2`) is canonically stationed next to Chief (`CID 1`) and remains visible until recruited.

---

## API Specifications

### `send_actor_hide(session: PlayerSession, click_id: int) -> None`

Dispatches dual despawn packets to hide an entity from the player's viewport and updates the session's visibility cache.

- **Parameters**:
  - `session`: The connected player session instance.
  - `click_id`: 16-bit integer identifier of the target actor/NPC on the active map.
- **Return Type**: `None`
- **Network Packets Dispatched**:
  - `AC 22 Sub 10` (`160a<click_id_le>ffff`): Official actor despawn frame.
  - `AC 22 Sub 11` (`160b<click_id_le>ffff`): Scene isolation frame suppressing residual interaction click areas.
- **Session Mutation**: `session._actor_visibility[click_id] = False`
- **Exceptions**: Silently logs warning if `session.send_packet` fails due to socket disconnect.
- **Edge Cases**:
  - If the actor is already recorded as `False` in `session._actor_visibility`, packets are still dispatched during full map synchronization to guarantee client reconciliation.

### `send_actor_show(session: PlayerSession, click_id: int) -> None`

Dispatches dual spawn packets to restore an entity's visibility on the player's viewport and updates the session's visibility cache.

- **Parameters**:
  - `session`: The connected player session instance.
  - `click_id`: 16-bit integer identifier of the target actor/NPC on the active map.
- **Return Type**: `None`
- **Network Packets Dispatched**:
  - `AC 22 Sub 10` (`160a<click_id_le>0000`): Official actor spawn frame.
  - `AC 22 Sub 11` (`160b<click_id_le>0000`): Scene integration frame activating interaction hitboxes.
- **Session Mutation**: `session._actor_visibility[click_id] = True`
- **Exceptions**: Silently logs warning on disconnected socket streams.
- **Edge Cases**:
  - Delta suppression: Avoids sending redundant show packets to permanent static props/chests unless their recorded state was `False`.

### `has_recruited_companion(session: PlayerSession, npc_name: str, template_id: int) -> bool`

Determines whether a given story companion has joined the player's roster, is currently summoned, or has completed their recruitment quest storyline.

- **Parameters**:
  - `session`: The connected player session instance.
  - `npc_name`: String name of the companion (e.g. `"Roca"`, `"Robinson"`, `"Niss"`). Case-insensitive.
  - `template_id`: 16-bit base template ID of the NPC entity.
- **Return Type**: `bool` (`True` if recruited/owned, `False` otherwise).
- **Evaluation Order**:
  1. **Pet Roster (`session.pets`)**: Inspects all owned pets against `COMPANION_ALIASES` mapping (e.g. Roca aliases: `14001, 14161, 14162`) and case-insensitive name matching.
  2. **Active Pet ID (`session.active_pet_id`)**: Inspects currently summoned companion ID.
  3. **Quest State Fallback**:
     - *Roca*: Quest 13052 `state == 3` (Completed) or Quest 13098 `state in (1, 3)` (Started/Completed).
     - *Robinson*: Quest 15283 or Quest 12040 `state in (1, 3)`.
     - *S.Monkey*: Quest 12018 `state in (1, 3)`.
- **Exceptions**: None; returns `False` if session or attributes are uninitialized.
- **Edge Cases**:
  - Player with pet in storage/tent: Alias map covers base IDs, upgraded IDs, and rebirth companion IDs.

### `evaluate_map_preevents(session: PlayerSession, map_id: int) -> None`

Processes map-level PreEvent bytecode from `data/eve.Emg` and applies authoritative per-map lifecycle overrides.

- **Parameters**:
  - `session`: The target player session.
  - `map_id`: Integer ID of the active or destination map.
- **Return Type**: `None`
- **Map Lifecycle Overrides**:
  - **Map 12000 (Kelan Village)**:
    - `CID 32` (Roca village square): Always hidden via `send_actor_hide(session, 32)`.
    - `CID 34` (Roca grave mourning): Visible only if Quest 13052 is in progress (`state == 1`) and not recruited; otherwise hidden.
    - `CID 36` (Roca grave standing): Always hidden.
    - `CID 33 & 35` (Father's Statue & Sword): Hidden when Quest 13098 is NotStarted (`state == 2`); shown otherwise.
    - `CID 28 & 20` (Lina's Dogs): `CID 28` hidden until quest finished; `CID 20` shown only during Quest 13046 step 1.
    - `CID 14, 15, 16` (Quest Pigs): `CID 14` shown when Q12020 step $\ge 2$ or completed; `CID 15` shown ONLY when Q12020 step $== 1$; `CID 16` hidden when Q13020 $== 2$ or flag 13021 $== 1$.
    - `CID 18 & 19` (Baby Bees): Hidden when Quest 13023 is NotStarted (`state == 2`).
    - `CID 10, 17, 31` (Permanent Scenery): Preserved; never hidden.
  - **Map 12001 (Chief's House)**:
    - `CID 2` (Roca): Visible by default; hidden if `has_recruited_companion(session, "Roca", 14162)` is `True`.
    - `CID 3` (Staged Copy): Always hidden.
- **Bytecode Interpretation**: Evaluates condition blocks (`Opcode 0x05` for Quest/Flag comparisons) and executes action blocks (`action_op == 0x02` for hide/show).
- **Exceptions**: Unhandled bytecode anomalies are trapped in try-except blocks and logged with diagnostics without crashing the player session.

### `is_npc_visible_to_player(session: PlayerSession, map_id: int, click_id: int) -> bool`

Queries the authoritative visibility state for an entity on a given map for the requesting player.

- **Parameters**:
  - `session`: The target player session.
  - `map_id`: Integer ID of the map.
  - `click_id`: Integer Click ID of the NPC.
- **Return Type**: `bool`
- **Resolution Strategy**:
  1. Checks `session._actor_visibility.get(click_id)`. If explicitly set, returns cached boolean.
  2. Falls back to static map baseline rules if uninitialized.

---

## Interaction Gating (`handle_20_interaction.py`)

When a client transmits `AC 20 Sub 1` (NPC Interaction Click):
1. The server checks `GLOBAL_PREEVENT_INTERPRETER.is_npc_visible_to_player(session, session.map_id, click_id)`.
2. If `False`:
   - Enforces client reconciliation by dispatching `AC 22 Sub 10 [click_id, 0xFF, 0xFF]`.
   - Sends `AC 20 Sub 8` to unlock client control immediately.
   - Suppresses dialogue queues, event bytecode triggers, and combat initialization.
