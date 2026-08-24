# Wonderland Online - Character Deletion System (AC 35 & Admin GUI)

## Overview
Comprehensive character deletion pipeline supporting both in-game client deletion (AC 35 Sub 2) and server admin suite GUI deletion.

## 1. Client-Side Deletion Protocol (`server/handlers/handle_35_char_deletion.py`)
* **Request Packet (`AC 35 Sub 2`)**:
  * `Byte[0]`: Action Code `35`
  * `Byte[1]`: Sub Code `2`
  * `Byte[2]`: Slot (`1` or `2`)
  * `String`: Unknown string (`uknw`)
  * `String`: Deletion Security Password (`pw`)
* **Security & Cipher Verification**:
  * Checks user's deletion cipher (`char_delete_code` in `users` table).
  * If cipher is not configured (empty), deletion is permitted by default.
  * If cipher is set, strictly matches against `pw`.
* **Database & Relation Cascade**:
  * Deletes row from `characters` table for matching `user_id` and `slot`.
  * Cascades cleanup across `chartent`, `chartent_items`, `charquest`, `charchests`, `char_titles`, and `char_instances`.
  * If no characters remain for user, resets user cipher.
* **Handshake Packets**:
  * Handshake: `AC 24:5 [53, 0]`, `AC 24:5 [52, 0]`, `AC 24:5 [54, 0]`, `AC 24:5 [183, 0]`, `AC 20:8`
  * Success Response: `AC 35:2 [1, slot]`
  * Password Error Response: `AC 35:2 [3, slot]`

## 2. Server Suite Admin GUI Deletion (`server/gui_app.py`)
* **Characters Manager Tab (`self.tab_chars`)**:
  * **"🗑 Delete Character" Button (`action_delete_character`)**:
    * Reads selected character from `self.tree_characters`.
    * Confirms action with modal dialog.
    * Disconnects active session if player is currently online.
    * Performs full database cleanup from `characters` and safely cascades across child tables (`chartent`, `chartent_items`, `charquest`, `charchests`, `char_titles`, `char_instances`, `charmarriage`, `friends`).
    * Refreshes table view + dashboard counter.
  * **Character Editor Modal (`CharacterDataEditorDialog`)**:
    * Persists `quests`, `pets`, `inventory`, and `skills` directly to the corresponding JSON columns in the `characters` table without querying non-existent standalone tables.
