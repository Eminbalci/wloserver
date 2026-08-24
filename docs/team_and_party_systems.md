# Team & Party Management System

This document outlines the server-side team invitation handshake flows, member pairing, and leave sequences implemented in `server/handlers/handle_43_team.py`.

---

## 1. Team Invitation Handshake (Opcode 43)

The team system manages party creation and player pairing using **Opcode 43** (0x2B).

### A. Team Invitation (Sub-opcode 1)
1. **Request**: The inviter sends **Opcode 43, Sub-opcode 1** containing the target player's character name string.
2. **Session Search**: The server loops through `server.active_sessions` to match the target's name.
3. **Outcomes**:
   - **Target is Online**: The server forwards the invitation packet containing the inviter's name to the target player: `[43, 1, inviter_name]`.
   - **Target is Offline / Not Found**: The server rejects the request and sends a failure notification back to the inviter: `[43, 1, 0]`.

### B. Accepting Team Invitations (Sub-opcode 2)
1. **Acceptance**: The target player replies with **Opcode 43, Sub-opcode 2** containing the inviter's character name string.
2. **Pairing Broadcast**: The server establishes the team bond and transmits confirmation packets to both sessions:
   - **To Inviter**: Sends `[43, 2, target_name, 1]` (indicates target joined).
   - **To Target**: Sends `[43, 2, inviter_name, 1]` (indicates inviter joined).

### C. Leaving a Team (Sub-opcode 5)
1. **Leave Request**: Any party member can request to leave the active team by sending **Opcode 43, Sub-opcode 5**.
2. **Broadcast**: The server resolves party status variables and broadcasts the departure notification to the map: `[43, 5, leaving_char_name]`.

---

## 2. Interaction Lock Releases

For any unhandled or rejected sub-opcodes in Opcode 43, the server must automatically transmit the standard interaction lock release packet to prevent the client UI from freezing:

- **Lock Release Packet**: `[20, 8]` (Opcode 20, Sub-opcode 8).
