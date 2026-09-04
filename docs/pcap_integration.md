# PCAP Integration Specifications: First Login, Mini-Games, Lucky Draw & Vehicles

## 1. Overview
Reverse-engineered and integrated packet flows from four authentic client network captures (`.pcapng` files):
- `oyunailkgirisvebedavaitemverilmesi.pcapng`
- `ilkgorevtamami.pcapng`
- `minigameoynadim.pcapng`
- `gunlukluckydraw.pcapng`

## 2. Packet Formats & Sub-Codes

### AC 23 Sub 6: Item Delivery
- **Direction:** Server -> Client
- **Length:** 33 bytes
- **Structure:**
  - `[0]`: `23` (Action Code)
  - `[1]`: `6` (Sub-Code)
  - `[2:4]`: `item_id` (uint16_LE)
  - `[4:6]`: `count` (uint16_LE)
  - `[6:33]`: 27 zero bytes padding
- **Use Cases:** Lucky Draw reward delivery, free starter gifts upon initial character login, quest item distribution.

### AC 23 Sub 77: Login Scene Ready ACK / Market Query
- **Direction:** Client -> Server (`17 4d`)
- **Length:** 2 bytes
- **Server Response:**
  - AC 23 Sub 4: `[23, 4, 0]` (Empty stall listing)
  - AC 23 Sub 102: `[23, 102]` (End of stall listings)

### AC 104 Sub 1 & Sub 2: Lucky Draw Wheel & Mini-Games
- **Client Spin Request:** `[104, 1]` (2 bytes)
- **Server Wheel Stop:** `[104, 1, 2, category, slot_index]` (5 bytes)
- **Item Delivery:** Followed immediately by AC 23 Sub 6.

### AC 15 Vehicle Sub-Codes:
- **Sub 14:** Spawn vehicle on map -> Server responds with `AC 15 Sub 18` (`[15, 18, 21, char_id (4), item_id (2), x (4), y (4)]`).
- **Sub 7:** Board placed vehicle -> Server responds with `AC 15 Sub 10` (`[15, 10, 21, char_id (4), item_id (2)]`).
- **Sub 10:** Packup/dismount vehicle -> Server responds with `AC 15 Sub 15` and `AC 15 Sub 11`.
- **Sub 13:** Vehicle navigation orientation sync.

## 3. Integrated Components
- `server/gameserver.py`: Integrated free starter gift pack delivery for new characters upon login completion.
- `server/minigames_system.py`: Verified weighted draw logic, category mapping, and AC 23 Sub 6 packet emission.
- `server/handlers/handle_15_companion.py`: Added complete vehicle placement, boarding, and packup handlers.
- `server/handlers/handle_23_items.py`: Added AC 23 Sub 77 scene acknowledgment handler and unified stall query flow.
