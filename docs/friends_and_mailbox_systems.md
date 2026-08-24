# Friends & Mailbox Systems

This document outlines the server-side friend list pairings, invitation flows, database relationships, and deletion rules implemented in `server/handlers/handle_14_friends.py`.

---

## 1. Friend Management (Opcode 14)

The friend system coordinates relationships and lists updates using **Opcode 14** (0x0E).

### A. Adding Friends by Name (Sub-opcode 1)
- **Invite Request**: Inviter sends target character name.
- **Outcomes**:
  - **Online**: Server forwards invite containing inviter's name: `[14, 1, inviter_name]`.
  - **Offline**: Server responds with failure: `[14, 1, 0]`.

### B. Adding Friends by ID / List Retrieval (Sub-opcode 2)
- If target `char_id != 0`: Server forwards request to target player: `[14, 2, inviter_id, ""]`.
- If target `char_id == 0`: Acts as a direct request to refresh the friend list (`send_friend_list`).

### C. Accepting Friend Requests (Sub-opcode 3)
1. **Accept Request**: Accepter sends requester's character ID.
2. **Database Insertion**: To prevent duplicate pairings, the server orders the IDs and inserts a row into the `friends` table:
   ```sql
   INSERT OR IGNORE INTO friends (CharID1, CharID2, AddedDate) 
   VALUES (MIN(ID1, ID2), MAX(ID1, ID2), datetime('now'))
   ```
3. **Confirmations**:
   - **To Requester**: Sends `[14, 3, 1, accepter_name]`.
   - **To Accepter**: Sends `[14, 3, 1]`.
   - Both sessions automatically trigger list refreshes.

### D. Deleting Friends (Sub-opcode 4)
- **Remove Request**: Client sends friend's character ID.
- **Database Deletion**: Deletes relation from DB:
   ```sql
   DELETE FROM friends WHERE CharID1 = MIN(ID1, ID2) AND CharID2 = MAX(ID1, ID2)
   ```
- Both sessions refresh lists. If sub-opcode 4 payload has no ID, it serves as a generic list retrieval.
