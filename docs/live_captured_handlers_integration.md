# Canlı Oyundan Yakalanan Protokollerin Sunucuya Entegrasyonu (Live Captured Handlers Integration)

Bu doküman, `C:\Games\WLRI\aLogin.exe` canlı oyun oturumundan gerçek zamanlı dinlenen ve sunucuya (`server/handlers/`) eklenen yeni paket işleyicileri ile alt-kod (sub-code) güncellemelerini detaylandırır.

---

## 1. Yeni Eklenen Handler: `handle_10_combat.py` (AC 10)

Canlı oyunda haritada gezinirken ve karşılaşmalarda tespit edilen **Opcode 10 (`0x0A`)** için yeni işleyici oluşturuldu.

- **Dosya:** [`server/handlers/handle_10_combat.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_10_combat.py)
- **Action Code:** `10`

### Desteklenen Alt Kodlar (Sub-Codes):
1. **Sub 6 (Encounter Heartbeat / Combat State Broadcast):**
   - **Yön:** `C->S` / `S->C`
   - **Format:** `[10, 6, char_id (uint32_LE), state_flags (uint16_LE)]`
   - **İşlev:** Karakterin savaş / karşılaşma durumunu ve harita oyuncularına olan görünürlük bayrağını senkronize eder.
2. **Sub 3 (Battle Engagement & Aura Broadcast):**
   - **Yön:** `S->C`
   - **Format:** `[10, 3, char_id (uint32_LE), aura_value (uint8)]`
   - **İşlev:** Savaş alanına giren oyuncunun aurasını ve harita savaşı durumunu çevre oyunculara yayınlar (`server.broadcast_to_map`).

---

## 2. Güncellenen Handler: `handle_186_cutscene.py` (AC 186)

Canlı oyunda tespit edilen Co-op / Takım Etkinliği oda durumu yayınları (`0xBA 0x0C` ve `0xBA 0x08`) eklendi.

- **Dosya:** [`server/handlers/handle_186_cutscene.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_186_cutscene.py)
- **Action Code:** `186` (`0xBA`)

### Eklenen Alt Kodlar:
1. **Sub 12 (Co-op Event Room State Broadcast):**
   - **Yön:** `S->C` / `C->S`
   - **Format:** `[186, 12, room_id (uint16_LE), member_count (uint8), max_members (uint8), status (uint8)]`
   - **İşlev:** Takım etkinlik odasının oyuncu sayısını ve aktiflik durumunu istemci arayüzüne senkronize eder.
2. **Sub 8 (Co-op Event Room Join / Ready Handshake):**
   - **Yön:** `C->S` / `S->C`
   - **Format:** `[186, 8, room_id (uint16_LE), status (uint8)]`
   - **İşlev:** Odaya katılma ve hazır olma durumunu onaylar.

---

## 3. Güncellenen Handler: `handle_35_char_deletion.py` (AC 35)

Canlı oyunda tespit edilen altın ve bakiye senkronizasyon paketi eklendi.

- **Dosya:** [`server/handlers/handle_35_char_deletion.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_35_char_deletion.py)
- **Action Code:** `35` (`0x23`)

### Eklenen Alt Kod:
1. **Sub 12 (Currency / Gold Balance Sync Handshake):**
   - **Yön:** `C->S` / `S->C`
   - **Format:** `[35, 12, gold (uint32_LE), reserved (uint8)]`
   - **İşlev:** Karakterin mevcut altın miktarını istemci UI paneline ve alt bara yansıtır.

---

## 4. Güncellenen Handler: `handle_62_tent.py` (AC 62)

Canlı oyunda en yüksek frekansta (70+ kez) yakalanan çadır içi mobilya ve varlık durumu kalp atışı paketi eklendi.

- **Dosya:** [`server/handlers/handle_62_tent.py`](file:///D:/GitHub/Wonderland%20Online/server/handlers/handle_62_tent.py)
- **Action Code:** `62` (`0x3E`)

### Eklenen Alt Kod:
1. **Sub 45 (Tent Presence & Furniture Sync Heartbeat):**
   - **Yön:** `C->S` / `S->C`
   - **Format:** `[62, 45, char_id (uint32_LE)]`
   - **İşlev:** Oyuncunun çadır içi mobilya etkileşim durumunu ve çadır varlık yayınını güncel tutar.
