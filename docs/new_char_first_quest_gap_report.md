# WLRI Canlı Oyun Paket ve Sunucu Özellik Boşluk Analizi (Live Server Feature Gap Report)

- **Tarih / Saat:** 2026-09-07 01:23:06
- **Hedef İstemci:** `C:\Games\WLRI\aLogin.exe`
- **Dinlenen Sunucu IP'leri:** 20.187.103.41, 104.208.85.33, 20.187.123.156, 20.205.14.213, 47.238.172.210
- **Toplam İncelenen Ağ Paketi:** 3789
- **Tespit Edilen Farklı Paket Türü:** 476

## 1. Sunucuda Eksik Olan İstemci İstekleri (Client Requests Missing in wloserver)

Aşağıdaki paketler canlı istemci tarafından sunucuya gönderilmiş ancak `wloserver/server/handlers/` içinde işlenmemiştir:

| Durum | Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Boyut | Görülme Sayısı | Örnek Hex |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| - | - | - | *Şu ana kadar eksik istemci isteği saptanmadı.* | - | - | - |

## 2. Orijinal Sunucudan Gelen ve İncelenmesi Gereken Paketler (Server -> Client Protocol)

| Durum | Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Boyut | Görülme Sayısı | Örnek Hex |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `1` | Login / Authentication Request | 6B | 4 | `01 01 38 61 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `3` | Login / Authentication Request | 3B | 1 | `01 03 00` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `9` | Login / Authentication Request | 11B | 1 | `01 09 65 00 01 C3 B9 BC 77 AE 71` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `11` | Login / Authentication Request | 2B | 1 | `01 0B` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `12` | Login / Authentication Request | 3B | 1 | `01 0C 00` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `31` | Login / Authentication Request | 523B | 1 | `01 1F 08 77 30 08 AF AB A4 FD A8 CF A9 78 00 00 55 55 55 55 49 F2 E5 40 55 55 55 55 09 C3 EA 40` |
| 🟣 Yeni Sunucu Paketi | `0x01 (1)` | `32` | Login / Authentication Request | 126B | 1 | `01 20 1E 00 00 00 96 00 00 00 90 01 00 00 8A 02 00 00 84 03 00 00 7E 04 00 00 78 05 00 00 72 06` |
| 🔵 Sunucu Yanıtı | `0x02 (2)` | `11` | Character List / Selection | 55B | 22 | `02 0B 00 00 00 00 32 30 32 36 2F 30 39 2F 30 33 20 A1 6D C4 C6 AC 79 A4 DB B9 D2 4F 6E 6C 69 6E` |
| 🟣 Yeni Sunucu Paketi | `0x03 (3)` | `87` | Actor / NPC / Object Visual Spawn Broadcast | 54B | 1 | `03 57 28 01 00 03 01 32 1E 2F A6 01 27 01 00 03 00 1C AF 7D 1A 1C AF 7D 1A 04 F9 55 16 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x03 (3)` | `88` | Actor / NPC / Object Visual Spawn Broadcast | 54B | 1 | `03 58 28 01 00 03 02 32 1E 2F A6 01 27 01 00 03 00 1C AF 7D 1A 1C AF 7D 1A 04 F9 55 16 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x03 (3)` | `89` | Actor / NPC / Object Visual Spawn Broadcast | 54B | 1 | `03 59 28 01 00 03 03 32 1E 2F A6 01 27 01 00 03 00 1C AF 7D 1A 1C AF 7D 1A 04 F9 55 16 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x03 (3)` | `246` | Actor / NPC / Object Visual Spawn Broadcast | 56B | 2 | `03 F6 E5 03 00 03 22 27 D2 02 E3 03 00 01 00 1C AF 7D 1A C4 10 7E 1A 02 0D 52 C5 5D 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `0` | Character / Entity Despawn | 61B | 8 | `04 00 63 00 00 04 02 9D 1D 32 7E 0D 80 03 00 00 00 E4 0B 77 1A E4 0B 77 1A 05 AE 56 6E 52 6B 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `1` | Character / Entity Despawn | 55B | 1 | `04 01 6B 03 00 01 04 7D A3 33 3E 0A 83 04 00 00 00 1C AF 7D 1A DC 12 7D 1A 04 72 52 5D 5A 4B 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `2` | Character / Entity Despawn | 61B | 5 | `04 02 E1 03 00 04 02 8A 3D 2B 4E 04 47 04 00 05 00 3C 56 84 1A 3C 56 84 1A 05 8D 56 B5 52 E6 36` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `3` | Character / Entity Despawn | 59B | 4 | `04 03 6B 03 00 04 03 6F 45 30 BA 10 AF 05 00 02 00 1C AF 7D 1A 1C AF 7D 1A 06 AC 56 53 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `4` | Character / Entity Despawn | 67B | 3 | `04 04 E0 03 00 04 03 1F 49 F9 E9 01 87 02 00 06 00 33 F8 85 1A 14 27 86 1A 04 BE 58 E0 54 CB 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `5` | Character / Entity Despawn | 73B | 2 | `04 05 76 01 00 01 03 BE 1C 2B 36 08 BB 08 00 00 00 EC 2D 7F 1A BC 01 00 00 06 A7 58 7A 53 78 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `6` | Character / Entity Despawn | 57B | 3 | `04 06 51 03 00 03 03 78 08 2B 6E 02 2F 03 00 01 00 1C AF 7D 1A 1C AF 7D 1A 04 0D 52 78 2B C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `7` | Character / Entity Despawn | 61B | 4 | `04 07 02 02 00 03 03 71 1C 2B 22 08 A3 07 00 01 00 D0 F6 79 1A 5C 20 AD 02 06 A7 58 B7 53 6D 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `8` | Character / Entity Despawn | 51B | 5 | `04 08 94 03 00 03 03 21 4B 2B 67 06 1A 02 00 01 00 1C AF 7D 1A 1C AF 7D 1A 02 EE 54 C5 5D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `9` | Character / Entity Despawn | 59B | 1 | `04 09 37 02 00 04 03 5E 6F 32 32 0C 9B 05 00 04 00 1C AF 7D 1A 1C AF 7D 1A 05 F2 55 12 52 13 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `10` | Character / Entity Despawn | 53B | 3 | `04 0A 91 02 00 04 03 75 FF 32 6A 0B EF 01 00 03 00 74 3B 80 1A 1C AF 7D 1A 01 11 52 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `11` | Character / Entity Despawn | 62B | 1 | `04 0B 70 03 00 03 03 8B 6F 32 96 0C 47 04 00 01 00 48 0C 77 1A CC D4 8A 00 06 B6 56 C6 52 89 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `12` | Character / Entity Despawn | 57B | 2 | `04 0C 9C 01 00 04 03 9C 18 30 42 06 6B 03 00 07 00 1C AF 7D 1A 1C AF 7D 1A 06 AC 56 CE 52 21 33` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `13` | Character / Entity Despawn | 61B | 3 | `04 0D 68 03 00 04 02 78 1D 32 EA 0D 83 04 00 00 00 3B 0E 80 1A 24 DD 83 1A 06 AC 56 99 52 6B 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `14` | Character / Entity Despawn | 70B | 6 | `04 0E 68 03 00 03 03 7C 1D 32 EA 0D 83 04 00 01 00 8B B3 85 1A 6C C5 85 1A 06 E1 56 B0 52 6C 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `15` | Character / Entity Despawn | 57B | 4 | `04 0F E3 03 00 04 02 89 62 EA 4E 13 BB 03 00 05 00 1C 91 82 1A 1C AF 7D 1A 05 CB 52 ED 36 6D 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `16` | Character / Entity Despawn | 59B | 9 | `04 10 B6 02 00 04 03 76 1C 2B 3A 09 3F 07 00 05 00 BD 53 7A 1A DC E4 8E 3B 06 D4 56 8F 52 55 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `17` | Character / Entity Despawn | 65B | 4 | `04 11 64 01 00 04 03 BE 6F 32 EA 03 A7 03 00 00 00 B2 91 84 1A 5C E1 99 3B 03 0E 52 89 46 F9 64` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `18` | Character / Entity Despawn | 56B | 2 | `04 12 E3 03 00 04 03 24 4B 2B BA 06 2F 03 00 03 00 54 05 7C 1A 1C AF 7D 1A 05 F7 55 EE 54 B7 3A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `19` | Character / Entity Despawn | 55B | 3 | `04 13 99 03 00 03 03 67 45 30 78 0A 70 08 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `20` | Character / Entity Despawn | 55B | 4 | `04 14 99 03 00 03 03 6B 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `21` | Character / Entity Despawn | 59B | 7 | `04 15 94 03 00 01 01 1B 12 F8 CC 01 BC 02 00 00 00 14 27 86 1A 1C AF 7D 1A 06 F4 55 09 52 31 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `22` | Character / Entity Despawn | 55B | 5 | `04 16 99 03 00 03 03 68 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `23` | Character / Entity Despawn | 55B | 2 | `04 17 99 03 00 03 03 69 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `24` | Character / Entity Despawn | 55B | 8 | `04 18 73 00 00 04 03 8D 1D 32 7E 0D 80 03 00 01 00 C2 C4 82 1A DC 89 7E 1A 03 0F 52 DA 59 C7 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `25` | Character / Entity Despawn | 55B | 7 | `04 19 99 03 00 03 03 68 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `26` | Character / Entity Despawn | 55B | 6 | `04 1A 99 03 00 03 03 6F 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `27` | Character / Entity Despawn | 51B | 4 | `04 1B 47 02 00 03 03 3F A3 33 66 0A E3 03 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 92 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `28` | Character / Entity Despawn | 55B | 6 | `04 1C 99 03 00 03 03 68 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `29` | Character / Entity Despawn | 51B | 4 | `04 1D 47 02 00 03 03 3F A3 33 66 0A E3 03 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 94 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `30` | Character / Entity Despawn | 55B | 7 | `04 1E 99 03 00 03 03 69 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `31` | Character / Entity Despawn | 55B | 3 | `04 1F 99 03 00 03 03 68 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `32` | Character / Entity Despawn | 51B | 3 | `04 20 E7 03 00 03 03 1A 71 30 12 04 2B 02 00 01 00 83 27 86 1A 34 00 8F 3B 03 EE 54 C5 5D 1D 85` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `33` | Character / Entity Despawn | 53B | 4 | `04 21 E7 03 00 01 03 1B 94 F9 CB 01 96 02 00 00 00 D3 73 85 1A AC F3 90 37 04 F4 55 EE 54 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `34` | Character / Entity Despawn | 55B | 3 | `04 22 99 03 00 03 03 67 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `35` | Character / Entity Despawn | 55B | 4 | `04 23 99 03 00 03 03 73 45 30 78 0A 70 08 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `36` | Character / Entity Despawn | 55B | 7 | `04 24 99 03 00 03 03 70 45 30 12 0C 21 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `37` | Character / Entity Despawn | 53B | 2 | `04 25 57 03 00 02 03 4E 3E 30 E5 05 77 03 00 00 00 41 87 7E 1A 4C B4 9A 3B 03 0A 52 C2 5D 97 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `38` | Character / Entity Despawn | 61B | 4 | `04 26 0B 48 00 02 01 6B CA F8 56 02 94 02 00 01 00 74 BE 7F 1A 8C 92 90 3B 06 F1 55 0B 52 EE 36` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `39` | Character / Entity Despawn | 48B | 5 | `04 27 15 01 00 04 03 7C 6F 32 CE 0B 1F 04 00 06 00 14 27 86 1A 74 3C 6C 05 01 1B 63 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `40` | Character / Entity Despawn | 54B | 6 | `04 28 E4 03 00 04 03 22 08 2B C6 04 63 01 00 06 00 DC AA 85 1A E4 71 9A 3B 03 C4 59 13 52 4E 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `41` | Character / Entity Despawn | 55B | 8 | `04 29 50 03 00 02 03 66 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `42` | Character / Entity Despawn | 57B | 7 | `04 2A 2F 03 00 04 03 5D 69 32 CA 0A F3 02 00 00 00 9F 19 86 1A 1C AF 7D 1A 05 AC 56 86 54 2B 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `43` | Character / Entity Despawn | 50B | 7 | `04 2B 54 00 00 03 03 1C 08 2B 92 01 DF 02 00 01 00 47 B1 7D 1A 1C AF 7D 1A 02 7D 53 1C 85 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `44` | Character / Entity Despawn | 53B | 7 | `04 2C 2F 03 00 04 03 58 69 32 0E 0D 83 04 00 03 00 3F 29 86 1A 1C AF 7D 1A 05 AC 56 B0 52 5D 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `45` | Character / Entity Despawn | 55B | 5 | `04 2D 50 03 00 02 03 6A 45 30 78 0A 70 08 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `46` | Character / Entity Despawn | 57B | 5 | `04 2E 2F 03 00 04 03 56 69 32 0E 0D 83 04 00 07 00 3F 29 86 1A 1C AF 7D 1A 05 E1 56 FA 54 79 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `47` | Character / Entity Despawn | 59B | 2 | `04 2F 30 03 00 02 03 B4 1C 2B AA 07 43 08 00 01 00 3F 29 86 1A 1C AF 7D 1A 06 E1 56 FA 54 78 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `48` | Character / Entity Despawn | 53B | 3 | `04 30 30 03 00 02 03 19 2F F9 35 01 87 02 00 01 00 3F 29 86 1A 1C AF 7D 1A 03 F1 55 0B 52 C3 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `49` | Character / Entity Despawn | 53B | 2 | `04 31 30 03 00 02 03 19 85 F9 53 01 78 02 00 01 00 3F 29 86 1A 1C AF 7D 1A 03 F1 55 0B 52 C3 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `50` | Character / Entity Despawn | 63B | 2 | `04 32 69 01 00 03 02 7A 1C 2B 36 08 93 08 00 03 00 1C AF 7D 1A 1C AF 7D 1A 06 F9 55 BE 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `51` | Character / Entity Despawn | 55B | 8 | `04 33 6E 03 00 03 03 22 E0 2E 86 03 6C 03 00 01 00 1C AF 7D 1A 1C AF 7D 1A 04 0D 52 B9 3A C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `52` | Character / Entity Despawn | 68B | 4 | `04 34 53 00 00 04 03 AB 6F 32 7E 0B F7 03 00 06 00 34 11 7E 1A 44 FC 76 1A 05 F6 55 13 52 89 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `53` | Character / Entity Despawn | 56B | 5 | `04 35 3D 02 00 04 04 8B 6F 32 CE 0B 1F 04 00 00 00 12 94 81 1A 14 F2 79 1A 05 B1 54 0D 33 79 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `54` | Character / Entity Despawn | 53B | 3 | `04 36 7F 03 00 04 04 64 C2 F9 CC 01 BC 02 00 06 00 FC 84 77 1A 1C AF 7D 1A 03 63 59 CE 52 CB 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `55` | Character / Entity Despawn | 53B | 3 | `04 37 7F 03 00 04 01 B4 18 F9 AD 01 4B 02 00 01 00 6C 72 7E 1A 1C AF 7D 1A 04 EE 54 DA 59 72 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `56` | Character / Entity Despawn | 65B | 4 | `04 38 88 03 00 04 02 5E 6F 32 0A 0C A7 03 00 05 00 4C 12 81 1A FC C5 C1 39 01 4D 63 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `57` | Character / Entity Despawn | 55B | 7 | `04 39 5E 47 00 03 01 A0 6F 32 D2 0C 0F 05 00 01 00 24 8A 7C 1A 1C AF 7D 1A 04 0D 52 89 46 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `58` | Character / Entity Despawn | 57B | 4 | `04 3A 88 03 00 04 01 78 E0 2E 12 04 93 03 00 07 00 23 3D 85 1A 0C D7 DE 19 04 F8 55 98 52 1C 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `59` | Character / Entity Despawn | 66B | 4 | `04 3B 64 03 00 01 03 AD 6F 32 BE 0C 27 06 00 00 00 8C 42 85 1A 9C 9C 15 38 06 D4 56 E5 52 A7 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `60` | Character / Entity Despawn | 55B | 5 | `04 3C 44 48 00 04 03 76 1C 2B 5E 08 43 08 00 00 00 3A 9F 85 1A 1C AF 7D 1A 04 F5 55 0E 52 D9 59` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `61` | Character / Entity Despawn | 49B | 3 | `04 3D 73 00 00 03 03 8D 1D 32 7E 0D 80 03 00 00 00 32 E8 80 1A 84 FD 7B 1A 01 0C 52 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `62` | Character / Entity Despawn | 56B | 5 | `04 3E 89 02 00 04 02 56 1F 2B 02 0A 03 02 00 05 00 A0 F2 83 1A D4 39 AC 35 05 CB 52 EE 36 5D 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `63` | Character / Entity Despawn | 71B | 4 | `04 3F 7E 03 00 03 03 77 62 EA BA 0B EF 10 00 00 00 22 14 77 1A 5C BD 0D 00 06 39 56 B0 52 3B 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `64` | Character / Entity Despawn | 54B | 3 | `04 40 89 48 00 03 04 52 69 32 16 0A 57 03 00 01 00 9C 94 77 1A 1C AF 7D 1A 03 0D 52 C5 5D 1B 63` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `65` | Character / Entity Despawn | 63B | 3 | `04 41 E0 03 00 03 03 51 71 F9 BB 02 78 02 00 01 00 DC 63 7C 1A DC 12 7D 1A 05 21 59 C0 53 DF 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `66` | Character / Entity Despawn | 63B | 2 | `04 42 B0 02 00 04 03 5E 34 F9 CB 01 D2 02 00 05 00 2C A6 85 1A 1C AF 7D 1A 06 19 59 C0 53 97 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `67` | Character / Entity Despawn | 61B | 4 | `04 43 AD 02 00 03 03 B6 03 33 3A 04 F3 02 00 01 00 CC 38 85 1A 7C F2 84 1A 06 B5 56 A3 53 C9 3A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `68` | Character / Entity Despawn | 61B | 6 | `04 44 9B 03 00 03 02 7F 27 2B E2 10 1F 04 00 00 00 75 0B 77 1A 24 79 89 00 05 F2 56 99 52 DA 36` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `69` | Character / Entity Despawn | 57B | 4 | `04 45 40 02 00 03 03 61 03 33 FA 07 CB 02 00 01 00 12 F4 82 1A 1C AF 7D 1A 05 AC 56 BE 52 2B 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `70` | Character / Entity Despawn | 60B | 3 | `04 46 2F 45 00 03 03 74 1C 2B 22 08 43 08 00 01 00 BC E8 76 1A 1C AF 7D 1A 06 AB 58 FA 54 6D 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `71` | Character / Entity Despawn | 54B | 6 | `04 47 00 01 00 03 03 94 1D 32 9B 0E E9 05 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 98 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `72` | Character / Entity Despawn | 55B | 3 | `04 48 88 03 00 03 03 69 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `73` | Character / Entity Despawn | 56B | 7 | `04 49 00 01 00 03 03 94 1D 32 FD 0D 30 04 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 94 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `74` | Character / Entity Despawn | 55B | 6 | `04 4A 88 03 00 03 03 67 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `75` | Character / Entity Despawn | 55B | 5 | `04 4B C0 01 00 03 03 6E 4B 2B 32 07 07 03 00 01 00 2B E9 76 1A 9C 42 B3 35 04 0D 52 89 46 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `76` | Character / Entity Despawn | 55B | 5 | `04 4C 88 03 00 03 03 64 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `77` | Character / Entity Despawn | 55B | 6 | `04 4D 4E 03 00 02 03 6A 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `78` | Character / Entity Despawn | 55B | 6 | `04 4E 88 03 00 03 03 67 45 30 78 0A 70 08 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `79` | Character / Entity Despawn | 55B | 4 | `04 4F 88 03 00 03 03 6A 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `80` | Character / Entity Despawn | 55B | 5 | `04 50 4E 03 00 02 03 6D 45 30 1C 0C 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `81` | Character / Entity Despawn | 61B | 3 | `04 51 71 00 00 04 03 BB 6F 32 56 0B CF 03 00 05 00 C3 9A 78 1A 64 B5 7A 1A 06 BB 56 EB 52 6C 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `82` | Character / Entity Despawn | 55B | 4 | `04 52 4E 03 00 02 03 6C 45 30 1C 0C 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `83` | Character / Entity Despawn | 55B | 5 | `04 53 4E 03 00 02 03 6B 45 30 1C 0C 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `84` | Character / Entity Despawn | 55B | 5 | `04 54 4E 03 00 02 03 6C 45 30 1C 0C 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `85` | Character / Entity Despawn | 61B | 4 | `04 55 B7 00 00 02 02 5B 1C 2B DE 0A 5F 0A 00 00 00 63 86 7E 1A C4 63 85 1A 05 D4 56 E5 52 9E 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `86` | Character / Entity Despawn | 59B | 3 | `04 56 E0 01 00 03 03 B5 E0 2E 4A 03 57 03 00 00 00 FB BA 7F 1A BC 01 00 00 06 96 56 3D 54 78 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `87` | Character / Entity Despawn | 59B | 3 | `04 57 B5 02 00 03 03 73 1C 2B 3A 09 3F 07 00 01 00 0C 05 7E 1A 0C ED 81 1A 06 E1 56 B0 52 54 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `88` | Character / Entity Despawn | 55B | 1 | `04 58 86 03 00 03 03 6C 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `89` | Character / Entity Despawn | 56B | 5 | `04 59 00 01 00 02 03 94 1D 32 E0 0E 51 05 00 00 00 1C AF 7D 1A 1C AF 7D 1A 04 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `90` | Character / Entity Despawn | 54B | 4 | `04 5A 00 01 00 02 03 94 1D 32 E0 0E 51 05 00 00 00 1C AF 7D 1A 1C AF 7D 1A 04 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `91` | Character / Entity Despawn | 55B | 5 | `04 5B E1 03 00 03 02 8A 03 33 0A 02 1B 03 00 00 00 93 6C 81 1A 94 9E FD 0F 03 E0 54 85 5E 4D 63` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `92` | Character / Entity Despawn | 58B | 3 | `04 5C 00 01 00 02 03 94 1D 32 9B 0E E9 05 00 00 00 1C AF 7D 1A 1C AF 7D 1A 04 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `93` | Character / Entity Despawn | 53B | 4 | `04 5D 00 01 00 03 03 94 1D 32 FD 0D 30 04 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 97 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `94` | Character / Entity Despawn | 59B | 3 | `04 5E 43 00 00 04 02 A7 6F 32 6A 0B 33 04 00 02 00 EA D5 85 1A D4 C7 9A 3B 06 8F 56 A8 54 72 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `95` | Character / Entity Despawn | 55B | 5 | `04 5F E3 03 00 03 03 62 A3 33 1A 0B 6B 03 00 02 00 F8 0C 80 1A BC E8 76 1A 03 14 52 CC 5D 1B 63` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `96` | Character / Entity Despawn | 60B | 10 | `04 60 AC 02 00 04 02 57 45 30 72 08 37 05 00 05 00 1C AF 7D 1A 1C AF 7D 1A 06 D4 56 E5 52 30 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `97` | Character / Entity Despawn | 68B | 9 | `04 61 52 00 00 04 01 AC 6F 32 7E 0B F7 03 00 04 00 DB 84 7B 1A BC E8 76 1A 05 F2 55 12 52 89 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `98` | Character / Entity Despawn | 66B | 10 | `04 62 B4 02 00 04 02 66 D8 F8 25 02 69 02 00 03 00 16 65 7F 1A 9C AD 92 3B 05 96 56 AC 53 97 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `99` | Character / Entity Despawn | 60B | 7 | `04 63 9B 03 00 03 02 6B 01 32 D2 02 DF 02 00 00 00 75 0B 77 1A 34 CD BA 01 06 6C 59 8F 52 90 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `100` | Character / Entity Despawn | 50B | 7 | `04 64 00 00 00 00 01 01 1F 27 D2 02 E3 03 00 00 00 1C AF 7D 1A 1C AF 7D 1A 00 00 00 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `101` | Character / Entity Despawn | 53B | 8 | `04 65 70 45 00 01 03 1F 08 2B 1E 02 33 04 00 00 00 0C 1D 7A 1A 1C AF 7D 1A 03 F4 55 09 52 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `102` | Character / Entity Despawn | 70B | 6 | `04 66 E3 03 00 04 03 3C 26 F8 7F 02 96 02 00 06 00 EC 75 84 1A FC 00 11 05 04 75 59 B2 54 1E 5B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `103` | Character / Entity Despawn | 57B | 4 | `04 67 70 45 00 02 03 27 08 2B AC 03 02 03 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `104` | Character / Entity Despawn | 57B | 2 | `04 68 70 45 00 02 03 1B 08 2B AC 03 16 03 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `105` | Character / Entity Despawn | 57B | 4 | `04 69 5B 00 00 04 02 B6 6F 32 46 0C 0B 04 00 05 00 5B 99 82 1A 94 8A 0D 00 06 55 59 AC 52 06 76` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `106` | Character / Entity Despawn | 49B | 2 | `04 6A 6E 45 00 02 03 1A 08 2B CE 01 93 03 00 01 00 3A 9F 85 1A 1C AF 7D 1A 03 F1 55 0B 52 C3 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `107` | Character / Entity Despawn | 59B | 3 | `04 6B E1 03 00 03 01 53 B2 30 12 09 9F 01 00 02 00 80 AF 7D 1A E4 24 00 00 05 D4 56 99 52 55 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `108` | Character / Entity Despawn | 51B | 3 | `04 6C 6E 45 00 04 03 20 08 2B F6 01 43 03 00 04 00 A2 76 82 1A 1C AF 7D 1A 04 F2 55 12 52 13 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `109` | Character / Entity Despawn | 57B | 6 | `04 6D 6E 45 00 04 03 19 43 F8 CC 01 BC 02 00 07 00 6B 43 82 1A 5C 21 4E 38 03 F8 55 17 52 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `110` | Character / Entity Despawn | 59B | 3 | `04 6E 44 00 00 03 03 9E 6F 32 FA 07 9B 05 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 89 46 E6 61` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `111` | Character / Entity Despawn | 59B | 5 | `04 6F 03 01 00 03 01 8E 03 33 0A 02 1B 03 00 00 00 2B E9 76 1A BC E8 76 1A 03 AC 56 62 5A F9 64` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `112` | Character / Entity Despawn | 58B | 4 | `04 70 6F 03 00 03 03 42 1C 2B 6E 07 A7 08 00 00 00 1C AF 7D 1A 1C AF 7D 1A 06 72 56 EE 54 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `113` | Character / Entity Despawn | 61B | 7 | `04 71 B6 45 00 04 01 88 6F 32 CE 0B 1F 04 00 06 00 EC 03 86 1A 94 2B 9A 3B 06 AC 56 B5 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `114` | Character / Entity Despawn | 51B | 2 | `04 72 66 01 00 04 03 1A D3 F9 7F 02 1E 02 00 05 00 1C AF 7D 1A 1C AF 7D 1A 03 FF 53 E7 32 CD 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `115` | Character / Entity Despawn | 70B | 4 | `04 73 8B 01 00 02 04 9C C2 F8 7F 02 78 02 00 00 00 BF DD 7F 1A 64 97 4A 0E 06 59 58 7A 53 C3 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `116` | Character / Entity Despawn | 63B | 2 | `04 74 8B 01 00 02 02 9D 60 EA 72 08 23 0A 00 01 00 A3 C9 78 1A BC 01 00 00 05 59 58 06 55 41 5B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `117` | Character / Entity Despawn | 57B | 3 | `04 75 D8 00 00 03 02 A7 6F 32 6A 0B A7 03 00 02 00 B8 AF 85 1A BC E8 76 1A 04 14 52 89 46 CC 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `118` | Character / Entity Despawn | 64B | 1 | `04 76 66 01 00 04 03 1A D7 F9 43 02 96 02 00 05 00 1C AF 7D 1A 1C AF 7D 1A 03 60 59 BB 53 CD 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `119` | Character / Entity Despawn | 59B | 2 | `04 77 D8 00 00 03 01 AF 1D 32 6E 11 97 04 00 03 00 F1 1C 84 1A BC E8 76 1A 05 F9 55 16 52 89 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `120` | Character / Entity Despawn | 55B | 5 | `04 78 6E 03 00 03 03 1D 81 2F 94 02 57 05 00 01 00 1C AF 7D 1A 1C AF 7D 1A 04 0D 52 B7 3A C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `121` | Character / Entity Despawn | 55B | 1 | `04 79 E5 03 00 04 03 57 A3 33 A6 0B A7 03 00 07 00 1C AF 7D 1A 1C AF 7D 1A 04 F8 55 17 52 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `122` | Character / Entity Despawn | 53B | 4 | `04 7A E5 03 00 03 02 51 A3 33 A6 0B A7 03 00 02 00 94 1E 7D 1A 1C AF 7D 1A 03 14 52 CC 5D 4D 63` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `123` | Character / Entity Despawn | 59B | 3 | `04 7B A5 01 00 03 03 B5 E0 2E AE 03 F3 02 00 00 00 FB BA 7F 1A BC 01 00 00 06 5F 58 A0 53 75 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `124` | Character / Entity Despawn | 55B | 5 | `04 7C FF 00 00 04 02 89 6F 32 CE 0B 1F 04 00 05 00 BC 8E 85 1A 54 EE FA 02 04 9B 53 5D 5A 4E 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `125` | Character / Entity Despawn | 57B | 3 | `04 7D 6C 45 00 03 03 B7 60 F8 9D 02 2D 02 00 01 00 1C AF 7D 1A 64 26 7D 1A 06 96 56 E3 52 90 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `127` | Character / Entity Despawn | 56B | 5 | `04 7F 03 02 00 04 04 2A 46 F8 CC 01 BC 02 00 07 00 1C AF 7D 1A 1C AF 7D 1A 03 F8 55 17 52 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `128` | Character / Entity Despawn | 75B | 3 | `04 80 2B 02 00 04 03 67 D2 F9 8F 01 00 02 00 07 00 5A 35 7A 1A BC A0 82 1A 06 81 59 4E 54 02 2C` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `129` | Character / Entity Despawn | 50B | 2 | `04 81 40 03 00 02 03 19 FA 32 CA 0A 73 05 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `130` | Character / Entity Despawn | 55B | 4 | `04 82 87 03 00 03 03 72 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `131` | Character / Entity Despawn | 59B | 3 | `04 83 BF 02 00 04 03 67 1C 2B D6 08 43 08 00 07 00 A4 39 7F 1A BC E8 76 1A 06 8D 56 75 52 6D 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `132` | Character / Entity Despawn | 55B | 3 | `04 84 87 03 00 03 03 6B 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `133` | Character / Entity Despawn | 68B | 3 | `04 85 B7 01 00 01 03 9C 12 F9 7F 02 5A 02 00 00 00 3C CD 85 1A 94 0C 80 1A 05 58 58 BB 53 06 76` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `134` | Character / Entity Despawn | 56B | 4 | `04 86 70 03 00 03 03 32 D7 F8 71 01 87 02 00 00 00 1C AF 7D 1A 54 9A 78 1A 04 0C 52 A8 42 C4 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `135` | Character / Entity Despawn | 55B | 2 | `04 87 87 03 00 03 03 68 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `136` | Character / Entity Despawn | 55B | 3 | `04 88 87 03 00 03 03 6A 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `137` | Character / Entity Despawn | 55B | 5 | `04 89 87 03 00 03 03 66 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `138` | Character / Entity Despawn | 55B | 7 | `04 8A 87 03 00 03 03 67 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `139` | Character / Entity Despawn | 55B | 7 | `04 8B 87 03 00 03 03 67 08 2B F4 01 E8 03 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `140` | Character / Entity Despawn | 59B | 12 | `04 8C DE 03 00 01 03 51 63 EA 39 08 05 14 00 00 00 3F 29 86 1A 84 04 9A 3B 06 F4 55 EE 54 7C 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `141` | Character / Entity Despawn | 59B | 7 | `04 8D DE 03 00 01 03 51 63 EA 39 08 05 14 00 00 00 3F 29 86 1A 84 04 9A 3B 06 F4 55 EE 54 6A 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `142` | Character / Entity Despawn | 59B | 10 | `04 8E 6F 03 00 04 03 B4 0F F8 CC 01 BC 02 00 05 00 4C 2A 7D 1A 54 9A 78 1A 06 81 59 15 52 6B 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `143` | Character / Entity Despawn | 53B | 4 | `04 8F 8D 45 00 04 03 2A 08 2B 5A 02 0B 04 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0F 52 DA 59 C7 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `144` | Character / Entity Despawn | 58B | 5 | `04 90 7C 02 00 04 02 40 3E F9 8F 01 5A 02 00 00 00 A2 ED 83 1A 9C 07 02 27 05 C4 59 EE 54 E9 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `145` | Character / Entity Despawn | 52B | 8 | `04 91 09 01 00 02 01 32 08 2B 96 02 A7 03 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `146` | Character / Entity Despawn | 55B | 8 | `04 92 09 01 00 02 01 32 08 2B AA 02 E3 03 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `147` | Character / Entity Despawn | 55B | 8 | `04 93 DF 03 00 01 03 51 1F 2B EE 09 57 03 00 00 00 6C 01 7C 1A 1C AF 7D 1A 04 F4 55 09 52 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `148` | Character / Entity Despawn | 55B | 7 | `04 94 7C 02 00 04 03 B4 45 30 52 0A CF 08 00 07 00 39 B8 7D 1A 1C AF 7D 1A 05 F8 55 17 52 89 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `149` | Character / Entity Despawn | 55B | 6 | `04 95 09 01 00 02 01 32 08 2B AC 03 B2 02 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `150` | Character / Entity Despawn | 65B | 3 | `04 96 82 00 00 04 03 BD 84 27 FA 02 C7 01 00 03 00 D3 F0 85 1A 14 82 96 3B 06 60 59 D5 53 DA 3A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `151` | Character / Entity Despawn | 60B | 3 | `04 97 6E 02 00 04 03 8A 6F 32 FA 0C D7 05 00 01 00 C0 90 7F 1A B4 03 0D 3A 04 0F 52 DA 59 C7 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `152` | Character / Entity Despawn | 54B | 5 | `04 98 09 01 00 F4 44 02 00 14 08 F4 44 03 00 14 21 00 F4 44 0C 00 08 01 2A 01 04 00 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `153` | Character / Entity Despawn | 57B | 5 | `04 99 09 01 00 02 01 1E 08 2B AE 03 17 02 00 00 00 1C AF 7D 1A 1C AF 7D 1A 03 F3 55 0A 52 C2 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `154` | Character / Entity Despawn | 69B | 4 | `04 9A 92 01 00 03 03 9F 18 30 96 07 F7 03 00 03 00 2B CB 7B 1A 1C AF 7D 1A 06 E1 56 B0 52 27 33` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `155` | Character / Entity Despawn | 62B | 5 | `04 9B 9B 02 00 04 03 B4 AA F8 CC 01 BC 02 00 05 00 EF F4 82 1A BC EA A4 35 06 59 58 A8 53 A9 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `156` | Character / Entity Despawn | 61B | 4 | `04 9C DE 03 00 03 03 1A E9 2E B2 0E B3 06 00 01 00 E4 0B 77 1A 1C AF 7D 1A 04 EE 54 CF 36 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `157` | Character / Entity Despawn | 55B | 4 | `04 9D 52 03 00 02 03 69 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `158` | Character / Entity Despawn | 59B | 8 | `04 9E 9B 02 00 03 03 32 7A F8 CC 01 BC 02 00 01 00 63 15 7C 1A 14 D9 39 14 05 47 56 C2 53 94 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `159` | Character / Entity Despawn | 55B | 5 | `04 9F 52 03 00 02 03 69 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `160` | Character / Entity Despawn | 55B | 8 | `04 A0 52 03 00 02 03 68 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 8C 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `161` | Character / Entity Despawn | 55B | 3 | `04 A1 52 03 00 02 03 6B 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `162` | Character / Entity Despawn | 71B | 4 | `04 A2 66 46 00 04 02 B4 15 F8 43 02 E2 01 00 03 00 04 1E 81 1A 1C AF 7D 1A 05 4A 59 5C 54 C3 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `163` | Character / Entity Despawn | 53B | 2 | `04 A3 E5 03 00 04 02 B4 50 F8 07 02 5A 02 00 06 00 44 F6 77 1A 5C A6 B2 35 03 55 59 B5 54 64 5F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `164` | Character / Entity Despawn | 55B | 1 | `04 A4 52 03 00 02 03 6C 45 30 9C 09 24 09 00 00 00 41 87 7E 1A 4C B4 9A 3B 04 F3 55 0A 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `165` | Character / Entity Despawn | 55B | 4 | `04 A5 15 02 00 03 03 1A 08 2B A6 01 1B 03 00 02 00 2B D1 7A 1A 6C 8B 07 00 02 2D 53 CC 5D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `166` | Character / Entity Despawn | 61B | 3 | `04 A6 71 00 00 01 03 A6 6F 32 46 0C BB 03 00 00 00 DB 48 85 1A C4 B7 77 1A 06 B8 56 09 52 59 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `167` | Character / Entity Despawn | 51B | 3 | `04 A7 15 02 00 01 03 19 44 F8 CC 01 BC 02 00 00 00 6C C5 85 1A 1C AF 7D 1A 02 F4 55 2D 53 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `168` | Character / Entity Despawn | 52B | 4 | `04 A8 15 02 00 04 03 1D 08 2B DE 00 1B 03 00 07 00 03 AE 7A 1A 1C AF 7D 1A 03 F8 55 17 52 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `169` | Character / Entity Despawn | 61B | 3 | `04 A9 84 03 00 03 03 1C 08 2B 12 04 A3 02 00 02 00 1C AF 7D 1A 1C AF 7D 1A 05 EE 54 EA 32 19 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `170` | Character / Entity Despawn | 53B | 1 | `04 AA 7B 03 00 04 02 5D 1C 2B 22 08 43 08 00 02 00 32 1C 81 1A 64 14 EC 08 03 E0 54 C2 46 4E 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `171` | Character / Entity Despawn | 58B | 5 | `04 AB 15 02 00 03 03 1A 08 2B F6 01 F3 02 00 01 00 7B 11 7C 1A 1C AF 7D 1A 04 61 59 7E 53 C2 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `172` | Character / Entity Despawn | 51B | 5 | `04 AC 15 02 00 03 03 19 08 2B A4 01 FC 03 00 01 00 A4 C2 7D 1A 1C AF 7D 1A 02 0D 52 C5 5D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `173` | Character / Entity Despawn | 55B | 3 | `04 AD 4D 00 00 04 02 99 6F 32 FA 07 9B 05 00 06 00 04 5A 77 1A 1C AF 7D 1A 03 CD 52 06 76 85 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `174` | Character / Entity Despawn | 56B | 1 | `04 AE 92 02 00 03 01 27 61 EA 76 13 2B 02 00 01 00 48 98 81 1A 5C A4 84 1A 05 2D 53 E9 32 42 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `175` | Character / Entity Despawn | 61B | 4 | `04 AF 6C 00 00 03 03 3E 08 2B BB 02 67 03 00 01 00 83 27 86 1A D4 C7 9A 3B 06 2D 56 26 53 2D 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `176` | Character / Entity Despawn | 76B | 2 | `04 B0 96 03 00 02 03 66 6C F9 6E 02 D9 01 00 00 00 F1 B7 7F 1A 7C AF A4 1A 06 19 59 B5 53 84 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `177` | Character / Entity Despawn | 57B | 3 | `04 B1 E1 03 00 02 03 19 67 F8 CC 01 BC 02 00 01 00 68 90 7F 1A D4 55 79 1A 03 F1 55 0B 52 C3 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `178` | Character / Entity Despawn | 53B | 2 | `04 B2 89 03 00 04 03 79 1C 2B AA 07 43 08 00 07 00 3F 29 86 1A 1C AF 7D 1A 04 F8 55 EE 54 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `179` | Character / Entity Despawn | 69B | 5 | `04 B3 79 00 00 04 02 AC FF 32 EA 0D CB 02 00 05 00 52 BF 7F 1A 04 00 86 1A 06 8D 56 B5 52 06 76` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `180` | Character / Entity Despawn | 54B | 4 | `04 B4 8A 03 00 01 02 64 6F 32 1E 0C A7 03 00 00 00 1C AF 7D 1A 3C A4 77 1A 04 F4 55 09 52 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `181` | Character / Entity Despawn | 54B | 6 | `04 B5 8A 03 00 03 03 65 6F 32 1E 0C A7 03 00 01 00 14 B0 84 1A 1C AF 7D 1A 03 0D 52 C5 5D B7 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `182` | Character / Entity Despawn | 53B | 4 | `04 B6 8A 03 00 03 03 63 6F 32 1E 0C A7 03 00 00 00 64 3E 79 1A 1C AF 7D 1A 03 0C 52 C4 5D 1C 85` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `183` | Character / Entity Despawn | 68B | 3 | `04 B7 E5 03 00 03 01 2C 60 EA 42 0B FF 0A 00 00 00 C6 A0 7E 1A D4 13 D6 36 06 66 56 8C 52 F2 36` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `184` | Character / Entity Despawn | 54B | 2 | `04 B8 FE 00 00 03 03 94 1D 32 D4 0E 89 04 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 94 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `185` | Character / Entity Despawn | 51B | 6 | `04 B9 58 03 00 02 03 B4 56 2B FA 02 2F 03 00 01 00 C9 76 84 1A 1C AF 7D 1A 03 F1 55 0B 52 C3 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `186` | Character / Entity Despawn | 62B | 7 | `04 BA 83 03 00 04 02 57 62 EA 4E 13 CF 03 00 05 00 E2 5A 77 1A 5C BD 0D 00 06 BB 56 CB 52 19 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `187` | Character / Entity Despawn | 51B | 3 | `04 BB 63 01 00 04 02 BE 6F 32 EA 03 A7 03 00 05 00 4A 02 7C 1A CC 44 94 2C 02 89 46 AB 64 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `188` | Character / Entity Despawn | 57B | 5 | `04 BC 49 00 00 03 03 A8 6F 32 D2 0C AF 05 00 01 00 1C AF 7D 1A 1C AF 7D 1A 06 CA 56 81 53 DA 3A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `189` | Character / Entity Despawn | 56B | 3 | `04 BD 74 03 00 03 04 2B D8 F8 25 02 87 02 00 01 00 AB 7A 7E 1A A4 30 E9 13 04 37 54 97 46 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `190` | Character / Entity Despawn | 68B | 7 | `04 BE 92 03 00 04 02 55 08 2B 0A 02 CB 02 00 05 00 FC B3 84 1A A4 17 67 18 06 93 56 F7 54 96 4A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `191` | Character / Entity Despawn | 55B | 8 | `04 BF DF 03 00 01 02 54 1F 2B EE 09 57 03 00 00 00 FC B9 83 1A 1C AF 7D 1A 04 F4 55 09 52 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `192` | Character / Entity Despawn | 62B | 6 | `04 C0 83 03 00 01 03 5C 6B F8 C6 01 79 02 00 00 00 93 A8 77 1A 84 E0 0D 00 06 BB 56 CB 52 19 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `193` | Character / Entity Despawn | 55B | 9 | `04 C1 97 03 00 04 01 B7 1D 32 CE 0E 24 04 00 00 00 B4 3C 85 1A B4 3C 85 1A 04 F5 55 0E 52 D9 59` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `194` | Character / Entity Despawn | 65B | 5 | `04 C2 BD 02 00 02 03 1C C6 F8 CC 01 BC 02 00 01 00 BA 72 82 1A 1C AF 7D 1A 04 5F 58 DD 53 4E 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `195` | Character / Entity Despawn | 61B | 5 | `04 C3 89 02 00 04 03 6F 6F 32 AA 0C C3 05 00 03 00 17 77 84 1A 14 01 6D 3B 05 F7 55 11 52 12 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `196` | Character / Entity Despawn | 59B | 2 | `04 C4 89 02 00 04 03 72 6F 32 AA 0C C3 05 00 01 00 73 7B 7E 1A 7C 4F 6B 3B 04 0F 52 DA 59 C7 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `197` | Character / Entity Despawn | 55B | 6 | `04 C5 95 03 00 03 01 20 4B 2B 67 06 1A 02 00 03 00 14 27 86 1A 1C AF 7D 1A 04 F9 55 16 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `198` | Character / Entity Despawn | 55B | 9 | `04 C6 95 03 00 03 04 20 4B 2B 67 06 1A 02 00 03 00 14 27 86 1A 1C AF 7D 1A 04 F9 55 16 52 52 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `199` | Character / Entity Despawn | 53B | 4 | `04 C7 95 03 00 01 03 B7 1D 32 CE 0E 24 04 00 00 00 14 27 86 1A 14 27 86 1A 03 F4 55 09 52 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `200` | Character / Entity Despawn | 54B | 1 | `04 C8 FE 00 00 03 03 95 1D 32 D4 0E 89 04 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 95 62` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `201` | Character / Entity Despawn | 55B | 4 | `04 C9 BF 46 00 02 03 1B FA 32 52 0A 87 05 00 00 00 94 6C 81 1A 3C B5 52 38 03 64 58 83 53 6E 64` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `202` | Character / Entity Despawn | 56B | 7 | `04 CA BF 46 00 01 03 19 08 2B DC 00 0C 03 00 00 00 A3 8D 82 1A 9C 94 77 1A 04 9D 59 7D 53 C0 42` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `203` | Character / Entity Despawn | 58B | 6 | `04 CB 89 03 00 04 03 32 4B 2B 79 05 D8 02 00 03 00 1C AF 7D 1A E4 C3 82 1A 05 F7 55 11 52 12 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `204` | Character / Entity Despawn | 59B | 4 | `04 CC E5 03 00 02 01 24 81 2F F2 0A FB 09 00 01 00 7C 0A 81 1A 1C AF 7D 1A 05 F1 55 EE 54 FF 2E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `205` | Character / Entity Despawn | 55B | 4 | `04 CD 3E 03 00 03 01 B4 4B F9 CB 01 B4 02 00 02 00 E6 94 81 1A 04 95 82 1A 05 BE 58 FB 52 97 46` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `206` | Character / Entity Despawn | 59B | 3 | `04 CE A5 01 00 02 03 BE 6F 32 AA 0C 87 05 00 00 00 C3 FF 7C 1A BC E8 76 1A 06 AC 56 A3 53 AF 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `207` | Character / Entity Despawn | 57B | 4 | `04 CF 66 02 00 04 03 BE 6F 32 CA 05 B7 02 00 03 00 5A F9 83 1A 9C FA 3B 36 05 F7 55 11 52 12 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `208` | Character / Entity Despawn | 59B | 1 | `04 D0 E1 03 00 03 02 5B 62 EA 4E 13 CF 03 00 02 00 E8 27 86 1A 4C 61 01 00 06 BB 56 CB 52 19 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `209` | Character / Entity Despawn | 59B | 4 | `04 D1 E1 03 00 04 03 54 62 EA 4E 13 CF 03 00 05 00 E8 27 86 1A E4 0D A5 35 06 B9 56 C9 52 ED 36` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `210` | Character / Entity Despawn | 69B | 4 | `04 D2 1F 01 00 03 01 B9 EB F8 61 02 A5 02 00 00 00 24 A8 77 1A 24 A8 77 1A 06 96 56 C0 52 BA 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `211` | Character / Entity Despawn | 57B | 4 | `04 D3 A7 00 00 03 03 9D A4 30 F4 01 90 01 00 02 00 22 D9 7C 1A 2C 41 81 1A 06 81 59 E7 53 BA 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `212` | Character / Entity Despawn | 57B | 5 | `04 D4 A7 00 00 03 03 9D 1C 2B 52 0A 53 07 00 00 00 82 45 81 1A 6C 1E CC 39 06 8A 59 D8 53 C2 37` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `213` | Character / Entity Despawn | 55B | 3 | `04 D5 8C 03 00 03 03 6E 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `214` | Character / Entity Despawn | 52B | 6 | `04 D6 27 00 00 04 03 1C 08 2B C6 04 C3 00 00 06 00 1C AF 7D 1A 1C AF 7D 1A 04 F6 55 13 52 14 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `215` | Character / Entity Despawn | 55B | 5 | `04 D7 8C 03 00 03 03 6F 45 30 1C 0C 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `216` | Character / Entity Despawn | 55B | 4 | `04 D8 8C 03 00 03 03 68 45 30 DC 0A EC 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `217` | Character / Entity Despawn | 55B | 8 | `04 D9 8C 03 00 03 03 70 45 30 9C 09 24 09 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `218` | Character / Entity Despawn | 63B | 4 | `04 DA B6 02 00 03 03 6C 1C 2B 3A 09 3F 07 00 00 00 E1 1B 86 1A 1C 97 81 1A 06 E1 56 B0 52 6A 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `219` | Character / Entity Despawn | 62B | 5 | `04 DB 84 03 00 03 03 31 4C 2B 12 04 5B 04 00 02 00 02 A9 77 1A 9C 59 0E 00 06 72 56 B3 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `220` | Character / Entity Despawn | 55B | 5 | `04 DC E6 03 00 03 03 70 3F F8 8F 01 5A 02 00 02 00 83 04 77 1A 24 79 89 00 02 14 52 CC 5D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `221` | Character / Entity Despawn | 55B | 5 | `04 DD 8C 03 00 03 03 70 45 30 78 0A 70 08 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 EE 54 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `222` | Character / Entity Despawn | 65B | 9 | `04 DE 34 02 00 04 03 8D 03 33 0A 02 1B 03 00 05 00 7C 10 80 1A 7C 10 80 1A 04 A9 59 62 5A 09 5E` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `223` | Character / Entity Despawn | 57B | 2 | `04 DF BB 02 00 02 04 1A 8C F9 15 03 69 02 00 01 00 C4 F2 82 1A C4 B1 78 1A 06 5F 58 99 54 E7 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `224` | Character / Entity Despawn | 57B | 1 | `04 E0 7F 03 00 02 02 3B 1C 2B 1E 08 77 08 00 00 00 1C AF 7D 1A 1C AF 7D 1A 05 F3 55 EE 54 2B 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `225` | Character / Entity Despawn | 59B | 2 | `04 E1 2B 00 00 02 03 99 6F 32 FA 07 9B 05 00 01 00 1C AF 7D 1A 1C AF 7D 1A 06 C9 56 B5 52 0D 33` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `226` | Character / Entity Despawn | 59B | 4 | `04 E2 28 02 00 02 03 BE 1C 2B 62 09 A3 07 00 01 00 32 06 7C 1A 14 27 86 1A 06 D4 56 E5 52 78 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `227` | Character / Entity Despawn | 74B | 8 | `04 E3 39 02 00 04 03 6F 63 EA 0E 0D 17 0C 00 00 00 9C 40 85 1A 1C AF 7D 1A 06 8F 56 7D 53 6D 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `228` | Character / Entity Despawn | 74B | 2 | `04 E4 39 02 00 04 03 72 63 EA 0E 0D 17 0C 00 00 00 9C 82 7A 1A 1C AF 7D 1A 06 8F 56 7E 53 78 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `229` | Character / Entity Despawn | 59B | 4 | `04 E5 44 00 00 03 04 BE 6F 32 CA 05 B7 02 00 00 00 FC DD 7D 1A 84 FD 7B 1A 06 BE 56 B1 52 20 2F` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `230` | Character / Entity Despawn | 54B | 7 | `04 E6 E5 03 00 04 03 58 A3 33 A6 0B A7 03 00 07 00 1C AF 7D 1A 1C AF 7D 1A 04 F8 55 17 52 CF 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `231` | Character / Entity Despawn | 56B | 4 | `04 E7 E6 03 00 01 03 3D A3 33 1A 0B E3 03 00 00 00 20 E9 76 1A 14 40 0F 00 04 F4 55 EE 54 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `232` | Character / Entity Despawn | 57B | 6 | `04 E8 E6 03 00 01 03 3E A3 33 1A 0B E3 03 00 00 00 20 E9 76 1A 14 40 0F 00 04 F4 55 EE 54 C1 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `233` | Character / Entity Despawn | 51B | 4 | `04 E9 D6 01 00 04 01 BA 6F 32 46 0C 0B 04 00 03 00 E7 27 86 1A BC E8 76 1A 03 C2 53 89 46 F9 64` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `234` | Character / Entity Despawn | 59B | 9 | `04 EA 6B 03 00 04 03 6E 45 30 BA 10 AF 05 00 02 00 1C AF 7D 1A 1C AF 7D 1A 06 31 56 53 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `235` | Character / Entity Despawn | 59B | 7 | `04 EB 6B 03 00 04 03 6E 45 30 BA 10 AF 05 00 02 00 1C AF 7D 1A 1C AF 7D 1A 06 31 56 10 52 F3 32` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `236` | Character / Entity Despawn | 57B | 10 | `04 EC 69 02 00 01 01 9B FF 32 EA 0D CB 02 00 00 00 DA F6 79 1A 74 3C 8A 00 01 F9 64 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `237` | Character / Entity Despawn | 57B | 7 | `04 ED 43 00 00 03 03 A8 6F 32 6A 0B 33 04 00 01 00 A2 11 7E 1A 2C 78 05 00 05 9B 53 89 46 62 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `238` | Character / Entity Despawn | 54B | 5 | `04 EE BF 02 00 04 03 88 6F 32 D2 0C 0F 05 00 06 00 C2 C4 82 1A AC 8B 7F 1A 05 AC 56 13 52 5D 5A` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `239` | Character / Entity Despawn | 55B | 3 | `04 EF 3B 03 00 04 01 98 6F 32 D2 0C 0F 05 00 05 00 DA DE 7D 1A 1C AF 7D 1A 04 15 52 89 46 CD 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `240` | Character / Entity Despawn | 51B | 3 | `04 F0 B9 02 00 04 02 96 6F 32 B4 0C 8D 04 00 00 00 01 F8 77 1A 54 1D 78 1A 00 00 00 00 00 00 01` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `241` | Character / Entity Despawn | 53B | 6 | `04 F1 B9 02 00 01 01 8D 6F 32 B4 0C 8D 04 00 00 00 A8 CA 7A 1A 1C 44 7A 1A 01 8E 62 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `242` | Character / Entity Despawn | 57B | 2 | `04 F2 28 46 00 03 03 AB 6F 32 5A 0C 1F 04 00 02 00 1C AF 7D 1A 64 26 7D 1A 06 E1 56 BE 52 90 2B` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `243` | Character / Entity Despawn | 55B | 1 | `04 F3 2A 00 00 04 03 1C 08 2B 46 02 CF 03 00 01 00 AB DF 82 1A 1C AF 7D 1A 03 0F 52 DA 59 C7 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `244` | Character / Entity Despawn | 51B | 5 | `04 F4 2A 00 00 03 03 2E 08 2B 46 02 57 03 00 00 00 63 09 7E 1A 1C AF 7D 1A 02 0C 52 C4 5D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `246` | Character / Entity Despawn | 55B | 2 | `04 F6 2A 00 00 03 03 19 08 2B 0A 02 DF 02 00 01 00 1C AF 7D 1A 1C AF 7D 1A 03 0D 52 C5 5D 1C 85` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `247` | Character / Entity Despawn | 62B | 3 | `04 F7 FB 00 00 03 03 69 3D 2B 4E 04 47 04 00 02 00 2D E1 7F 1A 94 BA 97 3B 06 D4 56 E5 52 A5 27` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `248` | Character / Entity Despawn | 56B | 5 | `04 F8 DD 03 00 03 03 56 18 30 0E 08 E3 03 00 01 00 DE E7 76 1A EC 03 86 1A 04 0D 52 F3 32 C5 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `249` | Character / Entity Despawn | 54B | 5 | `04 F9 DD 03 00 04 02 57 4B 2B 96 07 43 03 00 05 00 A6 FC 7B 1A EC 03 86 1A 03 15 52 CD 5D 25 63` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `250` | Character / Entity Despawn | 56B | 6 | `04 FA DD 03 00 03 03 56 18 30 36 08 BB 03 00 00 00 A6 FC 7B 1A EC 03 86 1A 04 0C 52 F3 32 C4 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `251` | Character / Entity Despawn | 56B | 3 | `04 FB DD 03 00 03 03 6F A3 33 06 06 B7 02 00 00 00 25 8F 7F 1A 1C 97 81 1A 04 0C 52 06 76 C4 5D` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `252` | Character / Entity Despawn | 46B | 5 | `04 FC 80 03 00 02 02 67 6F 32 72 0D 83 04 00 00 00 1C AF 7D 1A 1C AF 7D 1A 01 4D 63 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `253` | Character / Entity Despawn | 60B | 8 | `04 FD DD 03 00 04 02 6F A3 33 06 06 B7 02 00 07 00 B5 71 80 1A 1C 97 81 1A 06 AC 56 BE 52 06 76` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `254` | Character / Entity Despawn | 58B | 4 | `04 FE DD 03 00 04 03 6D A3 33 06 06 B7 02 00 00 00 1D 96 85 1A 1C 97 81 1A 05 F5 55 BE 52 06 76` |
| 🟣 Yeni Sunucu Paketi | `0x04 (4)` | `255` | Character / Entity Despawn | 53B | 4 | `04 FF B9 02 00 02 03 8F 6F 32 B4 0C 8D 04 00 01 00 34 FE 84 1A F4 DE 84 1A 01 8E 62 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `0` | Map Movement / Coordinate Sync | 14B | 85 | `05 00 57 28 01 00 F9 55 16 52 52 46 CE 5D` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `3` | Map Movement / Coordinate Sync | 78B | 1 | `05 03 03 B9 00 00 00 5F 00 07 00 01 00 00 00 00 00 00 00 01 06 00 00 00 00 00 00 00 B9 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `4` | Map Movement / Coordinate Sync | 2B | 3 | `05 04` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `8` | Map Movement / Coordinate Sync | 7B | 4 | `05 08 F6 E5 03 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `11` | Map Movement / Coordinate Sync | 8B | 1 | `05 0B 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `13` | Map Movement / Coordinate Sync | 5B | 10 | `05 0D 01 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `14` | Map Movement / Coordinate Sync | 3B | 1 | `05 0E 02` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `15` | Map Movement / Coordinate Sync | 3B | 1 | `05 0F 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `16` | Map Movement / Coordinate Sync | 3B | 1 | `05 10 02` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `18` | Map Movement / Coordinate Sync | 7B | 3 | `05 12 E7 E6 03 00 3E` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `21` | Map Movement / Coordinate Sync | 3B | 1 | `05 15 02` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `24` | Map Movement / Coordinate Sync | 5B | 10 | `05 18 01 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `29` | Map Movement / Coordinate Sync | 16B | 1 | `05 1D 02 00 00 00 61 E1 03 00 01 BE 92 03 00 02` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `30` | Map Movement / Coordinate Sync | 8B | 4 | `05 1E 01 F6 E5 03 00 00` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `42` | Map Movement / Coordinate Sync | 4B | 1 | `05 2A 00 00` |
| 🔵 Sunucu Yanıtı | `0x06 (6)` | `2` | Channel & Map Selection ACK | 3B | 13 | `06 02 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `2` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 02 38 03 00 08 2B 76 04 DF 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `5` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 05 53 02 00 08 2B DA 04 67 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `6` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 06 51 03 00 08 2B 6E 02 2F 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `15` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 0F E6 03 00 08 2B 0E 03 8B 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `22` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 16 54 00 00 08 2B E6 02 DF 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `24` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 18 54 00 00 08 2B F6 01 67 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `28` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 1C D7 01 00 08 2B FA 02 67 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `32` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 20 99 03 00 08 2B F4 01 E8 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `33` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 21 99 03 00 08 2B F4 01 E8 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `34` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 22 C0 01 00 08 2B 46 02 7F 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `40` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 28 E4 03 00 08 2B C6 04 63 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `41` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 29 E4 03 00 08 2B DA 04 3B 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `43` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 2B 54 00 00 08 2B 92 01 DF 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `49` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 31 93 00 00 08 2B 72 03 63 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `52` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 34 64 03 00 08 2B E6 02 DB 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `57` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 39 E9 46 00 08 2B AA 02 CF 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `75` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 4B BE 02 00 08 2B 7E 01 BB 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `89` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 59 A9 02 00 08 2B 5A 02 EF 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `90` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 5A DE 03 00 08 2B 36 03 CF 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `93` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 5D B7 02 00 08 2B A6 01 0B 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `96` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 60 C3 01 00 08 2B A6 01 F7 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `97` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 61 E1 03 00 08 2B 4E 04 4F 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `98` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 62 B7 02 00 08 2B C6 04 83 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `99` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 63 B7 02 00 08 2B 2E 01 43 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `101` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 65 70 45 00 08 2B 1E 02 33 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `103` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 67 70 45 00 08 2B AC 03 02 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `104` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 68 70 45 00 08 2B AC 03 16 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `105` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 69 8A 48 00 08 2B 3E 05 8F 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `106` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 6A 6E 45 00 08 2B CE 01 93 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `108` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 6C 6E 45 00 08 2B F6 01 43 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `109` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 6D 0E 48 00 08 2B 5E 03 57 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `124` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 7C E0 01 00 08 2B 26 04 03 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `134` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 86 A5 02 00 08 2B B2 04 3F 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `139` | UNKNOWN / NEW OP-CODE | 11B | 3 | `07 8B 87 03 00 08 2B F4 01 E8 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `142` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 8E 8D 45 00 08 2B 6A 01 7F 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `143` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 8F 8D 45 00 08 2B 5A 02 0B 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `144` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 90 09 01 00 08 2B 36 03 0B 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `145` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 91 09 01 00 08 2B 96 02 A7 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `146` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 92 09 01 00 08 2B AA 02 E3 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `147` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 93 09 01 00 08 2B AC 03 30 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `148` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 94 09 01 00 08 2B 98 03 E4 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `149` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 95 09 01 00 08 2B AC 03 B2 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `152` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 98 09 01 00 08 2B AC 03 58 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `153` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 99 6C 47 00 08 2B 0A 02 A7 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `158` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 9E 5D 00 00 08 2B 1A 01 93 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `165` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 A5 EC 01 00 08 2B 76 04 D7 00` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `166` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 A6 15 02 00 08 2B F6 01 E3 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `168` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 A8 15 02 00 08 2B DE 00 1B 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `169` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 A9 84 03 00 08 2B 12 04 A3 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `171` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 AB 15 02 00 08 2B F6 01 F3 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `172` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 AC 15 02 00 08 2B A4 01 FC 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `175` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 AF 6C 00 00 08 2B BB 02 67 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `176` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 B0 33 03 00 08 2B 62 04 9F 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `186` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 BA 3D 00 00 08 2B 2E 01 CF 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `190` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 BE 92 03 00 08 2B 0A 02 CB 02` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `193` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 C1 73 00 00 08 2B 36 03 93 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `198` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 C6 40 00 00 08 2B 6A 01 2F 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `202` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 CA BF 46 00 08 2B DC 00 0C 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `207` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 CF E6 03 00 08 2B 9A 03 47 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `214` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 D6 27 00 00 08 2B C6 04 C3 00` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `221` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 DD E0 03 00 08 2B DA 04 1B 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `225` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 E1 07 02 00 08 2B 36 03 5B 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `227` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 E3 90 02 00 08 2B 9E 04 B3 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `229` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 E5 CC 01 00 08 2B 7E 01 6B 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `234` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 EA 28 02 00 08 2B AA 02 47 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `237` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 ED 84 03 00 08 2B F4 01 E8 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `238` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 EE BE 00 00 08 2B 06 01 6B 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `239` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 EF 18 48 00 08 2B BE 02 33 04` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `243` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 F3 2A 00 00 08 2B 46 02 CF 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `244` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 F4 2A 00 00 08 2B 46 02 57 03` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `246` | UNKNOWN / NEW OP-CODE | 11B | 2 | `07 F6 8A 45 00 08 2B B2 04 3B 01` |
| 🟣 Yeni Sunucu Paketi | `0x07 (7)` | `252` | UNKNOWN / NEW OP-CODE | 11B | 1 | `07 FC 5A 46 00 08 2B 6E 02 F3 02` |
| 🔵 Sunucu Yanıtı | `0x08 (8)` | `1` | Grid Movement Steps & Path Routing | 12B | 27 | `08 01 CF 01 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x08 (8)` | `3` | Grid Movement Steps & Path Routing | 16B | 3 | `08 03 E7 E6 03 00 23 01 3E 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x09 (9)` | `3` | UNKNOWN / NEW OP-CODE | 3B | 1 | `09 03 00` |
| 🔵 Sunucu Yanıtı | `0x0A (10)` | `3` | System / Combat State Broadcast | 7B | 80 | `0A 03 5D B7 02 00 FF` |
| 🔵 Sunucu Yanıtı | `0x0A (10)` | `6` | System / Combat State Broadcast | 7B | 12 | `0A 06 DE 34 02 00 05` |
| 🔵 Sunucu Yanıtı | `0x0A (10)` | `7` | System / Combat State Broadcast | 3B | 1 | `0A 07 00` |
| 🔵 Sunucu Yanıtı | `0x0B (11)` | `4` | Pet Action / State Change / Capture Result | 642B | 1 | `0B 04 02 5D B7 02 00 00 00 00 02 E1 07 02 00 00 00 00 02 61 E1 03 00 00 00 00 02 20 99 03 00 00` |
| 🔵 Sunucu Yanıtı | `0x0C (12)` | `246` | UNKNOWN / NEW OP-CODE | 14B | 2 | `0C F6 E5 03 00 36 27 0E 04 BB 08 01 00 00` |
| 🔵 Sunucu Yanıtı | `0x0E (14)` | `5` | Item Hotbar Slot / Quick Usage | 30B | 1 | `0E 05 64 00 00 00 06 47 4D A4 A4 A4 DF C8 00 00 00 00 00 1C AF 7D 1A 1C AF 7D 1A 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x0E (14)` | `11` | Item Hotbar Slot / Quick Usage | 28B | 1 | `0E 0B 64 00 00 00 06 47 4D A4 A4 A4 DF C8 00 00 00 00 00 1C AF 7D 1A 1C AF 7D 1A 00` |
| 🔵 Sunucu Yanıtı | `0x0E (14)` | `13` | Item Hotbar Slot / Quick Usage | 3B | 2 | `0E 0D 03` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `1` | Vehicle / Companion Mount & Voyage Navigation | 54B | 1 | `0F 01 F6 E5 03 00 92 2F 00 00 01 08 00 0A 00 02 00 04 00 06 00 01 06 00 00 00 01 00 00 00 00 01` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `4` | Vehicle / Companion Mount & Voyage Navigation | 433B | 1 | `0F 04 20 99 03 00 0A 43 00 00 00 01 06 A4 70 B5 55 A4 6C F3 32 00 00 00 00 00 00 60 C3 01 00 20` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `10` | Vehicle / Companion Mount & Voyage Navigation | 9B | 2 | `0F 0A 10 F6 E5 03 00 90 BB` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `11` | Vehicle / Companion Mount & Voyage Navigation | 7B | 1 | `0F 0B 10 F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `14` | Vehicle / Companion Mount & Voyage Navigation | 13B | 21 | `0F 0E 10 F6 E5 03 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `15` | Vehicle / Companion Mount & Voyage Navigation | 8B | 1 | `0F 0F F6 E5 03 00 90 BB` |
| 🔵 Sunucu Yanıtı | `0x0F (15)` | `18` | Vehicle / Companion Mount & Voyage Navigation | 17B | 1 | `0F 12 10 F6 E5 03 00 90 BB E2 0B 00 00 1B 08 00 00` |
| 🔵 Sunucu Yanıtı | `0x13 (19)` | `1` | Player Status / Stats Sync | 6B | 1 | `13 01 92 2F 00 00` |
| 🔵 Sunucu Yanıtı | `0x14 (20)` | `1` | NPC Interaction / Dialogue Trigger | 18B | 28 | `14 01 00 00 00 01 01 03 0A 00 01 00 00 00 00 AC 75 01` |
| 🔵 Sunucu Yanıtı | `0x14 (20)` | `7` | NPC Interaction / Dialogue Trigger | 2B | 2 | `14 07` |
| 🔵 Sunucu Yanıtı | `0x14 (20)` | `8` | NPC Interaction / Dialogue Trigger | 2B | 18 | `14 08` |
| 🔵 Sunucu Yanıtı | `0x14 (20)` | `10` | NPC Interaction / Dialogue Trigger | 2B | 22 | `14 0A` |
| 🔵 Sunucu Yanıtı | `0x14 (20)` | `11` | NPC Interaction / Dialogue Trigger | 2B | 6 | `14 0B` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `1` | Scene Transition / Camera Waypoint Animation | 5B | 5 | `16 01 03 00 01` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `4` | Scene Transition / Camera Waypoint Animation | 156B | 3 | `16 04 01 00 FF 00 75 00 17 05 01 00 00 00 00 00 02 00 FF 00 66 00 20 05 01 00 00 00 00 00 03 00` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `7` | Scene Transition / Camera Waypoint Animation | 5B | 1 | `16 07 01 00 07` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `10` | Scene Transition / Camera Waypoint Animation | 6B | 2 | `16 0A 06 00 FF FF` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `11` | Scene Transition / Camera Waypoint Animation | 6B | 1 | `16 0B 06 00 FF FF` |
| 🟣 Yeni Sunucu Paketi | `0x16 (22)` | `12` | Scene Transition / Camera Waypoint Animation | 6B | 2 | `16 0C 02 0B 00 05` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `2` | Inventory / Item Manipulation / Ground Loot / Pickup | 5B | 1 | `17 02 01 00 01` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `4` | Inventory / Item Manipulation / Ground Loot / Pickup | 32B | 2 | `17 04 03 01 00 6A A0 00 00 DC 06 39 0D B4 00 00 00 03 02 00 21 B4 00 00 D6 08 E5 10 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `6` | Inventory / Item Manipulation / Ground Loot / Pickup | 33B | 19 | `17 06 F6 84 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `9` | Inventory / Item Manipulation / Ground Loot / Pickup | 4B | 1 | `17 09 10 01` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `11` | Inventory / Item Manipulation / Ground Loot / Pickup | 44B | 1 | `17 0B 0D 52 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 C5 5D 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `31` | Inventory / Item Manipulation / Ground Loot / Pickup | 776B | 1 | `17 1F 5D B7 02 00 08 AD D3 A4 48 B0 D3 A9 B1 01 E1 07 02 00 03 31 30 78 01 60 C3 01 00 09 53 61` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `32` | Inventory / Item Manipulation / Ground Loot / Pickup | 6B | 2 | `17 20 F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `76` | Inventory / Item Manipulation / Ground Loot / Pickup | 6B | 83 | `17 4C F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `102` | Inventory / Item Manipulation / Ground Loot / Pickup | 2B | 3 | `17 66` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `111` | Inventory / Item Manipulation / Ground Loot / Pickup | 97B | 1 | `17 6F 61 E1 03 00 0E 31 30 30 20 46 57 20 41 54 4B 20 50 45 54 02 69 8A 48 00 08 AD D3 A4 48 B0` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `112` | Inventory / Item Manipulation / Ground Loot / Pickup | 6B | 2 | `17 70 F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `122` | Inventory / Item Manipulation / Ground Loot / Pickup | 6B | 86 | `17 7A F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `131` | Inventory / Item Manipulation / Ground Loot / Pickup | 155B | 1 | `17 83 A9 84 03 00 08 AD D3 A4 48 B0 D3 A9 B1 01 29 E4 03 00 0C 43 61 62 69 2C 20 53 6F 66 61 20` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `132` | Inventory / Item Manipulation / Ground Loot / Pickup | 6B | 2 | `17 84 F6 E5 03 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `138` | Inventory / Item Manipulation / Ground Loot / Pickup | 2B | 3 | `17 8A` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `140` | Inventory / Item Manipulation / Ground Loot / Pickup | 11B | 1 | `17 8C 03 5C 9A 83 6F 08 98 E6 40` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `160` | Inventory / Item Manipulation / Ground Loot / Pickup | 3B | 1 | `17 A0 03` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `162` | Inventory / Item Manipulation / Ground Loot / Pickup | 5B | 1 | `17 A2 02 00 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `204` | Inventory / Item Manipulation / Ground Loot / Pickup | 4B | 1 | `17 CC 01 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `208` | Inventory / Item Manipulation / Ground Loot / Pickup | 8B | 2 | `17 D0 02 03 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x17 (23)` | `221` | Inventory / Item Manipulation / Ground Loot / Pickup | 3B | 3 | `17 DD 00` |
| 🟣 Yeni Sunucu Paketi | `0x18 (24)` | `1` | Quest Progress / Step Acceptance / Journal Sync | 5B | 2 | `18 01 08 2F 01` |
| 🟣 Yeni Sunucu Paketi | `0x18 (24)` | `4` | Quest Progress / Step Acceptance / Journal Sync | 4B | 2 | `18 04 08 2F` |
| 🟣 Yeni Sunucu Paketi | `0x18 (24)` | `5` | Quest Progress / Step Acceptance / Journal Sync | 5B | 14 | `18 05 35 00 00` |
| 🔵 Sunucu Yanıtı | `0x19 (25)` | `44` | P2P Secure Trade Handshake & Item Exchange | 11B | 1 | `19 2C 01 5C 9A 83 6F 08 98 E6 40` |
| 🟣 Yeni Sunucu Paketi | `0x1A (26)` | `4` | Player Street Stall Market Listing | 6B | 1 | `1A 04 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x1A (26)` | `10` | Player Street Stall Market Listing | 6B | 1 | `1A 0A 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x20 (32)` | `2` | Player Emote / Expression Animation | 7B | 2 | `20 02 F6 E5 03 00 09` |
| 🔵 Sunucu Yanıtı | `0x21 (33)` | `2` | Friend List / Add / Remove / Online State | 8B | 1 | `21 02 02 01 01 02 7F 00` |
| 🔵 Sunucu Yanıtı | `0x23 (35)` | `2` | UNKNOWN / NEW OP-CODE | 4B | 1 | `23 02 01 01` |
| 🔵 Sunucu Yanıtı | `0x23 (35)` | `4` | UNKNOWN / NEW OP-CODE | 18B | 1 | `23 04 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x23 (35)` | `11` | UNKNOWN / NEW OP-CODE | 2B | 1 | `23 0B` |
| 🔵 Sunucu Yanıtı | `0x23 (35)` | `12` | UNKNOWN / NEW OP-CODE | 7B | 29 | `23 0C F6 E5 03 00 00` |
| 🔵 Sunucu Yanıtı | `0x23 (35)` | `16` | UNKNOWN / NEW OP-CODE | 23B | 1 | `23 10 F6 E5 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x27 (39)` | `9` | Guild System / Clan Roster / Quest Abandon | 381B | 1 | `27 09 E1 07 02 00 42 01 00 00 0D A2 DB A2 E7 A2 E0 41 4E 47 45 52 A2 E1 61 E1 03 00 2D 07 00 00` |
| 🔵 Sunucu Yanıtı | `0x27 (39)` | `31` | Guild System / Clan Roster / Quest Abandon | 452B | 1 | `27 1F 0A 00 00 00 05 2B 00 00 00 07 2E 00 00 00 01 40 00 00 00 14 9A 00 00 00 01 6B 00 00 00 04` |
| 🟣 Yeni Sunucu Paketi | `0x35 (53)` | `10` | Combat Battle Action / Turn Submission / ACK | 2B | 1 | `35 0A` |
| 🔵 Sunucu Yanıtı | `0x36 (54)` | `201` | UNKNOWN / NEW OP-CODE | 16B | 2 | `36 C9 00 01 68 00 02 67 00 02 65 00 03 66 00 03` |
| 🔵 Sunucu Yanıtı | `0x3E (62)` | `4` | Tent Furniture Placement / Movement | 124B | 1 | `3E 04 F6 E5 03 00 01 00 A1 94 2A 00 00 00 27 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x3E (62)` | `45` | Tent Furniture Placement / Movement | 6B | 1543 | `3E 2D 42 E0 03 00` |
| 🔵 Sunucu Yanıtı | `0x3E (62)` | `46` | Tent Furniture Placement / Movement | 342B | 1 | `3E 2E EB E5 03 00 0C C5 77 AA EF B0 D1 C6 5B BF EF C1 CA 7F 03 02 00 0A 50 61 63 6B 20 43 61 72` |
| 🔵 Sunucu Yanıtı | `0x3E (62)` | `53` | Tent Furniture Placement / Movement | 4B | 1 | `3E 35 02 00` |
| 🔵 Sunucu Yanıtı | `0x3F (63)` | `1` | UNKNOWN / NEW OP-CODE | 66B | 1 | `3F 01 01 0A 63 61 72 64 65 6E 69 79 6F 6D 01 03 B9 00 00 00 B9 00 00 00 5F 00 00 00 5F 00 00 00` |
| 🔵 Sunucu Yanıtı | `0x41 (65)` | `3` | Tent World Map Pitching / Enter Tent | 386B | 1 | `41 03 EB E5 03 00 A2 8C DA 04 00 00 BF 04 00 00 00 00 7F 03 02 00 A2 8C 96 02 00 00 DF 02 00 00` |
| 🔵 Sunucu Yanıtı | `0x4B (75)` | `1` | Lucky Draw Wheel Spin / Slot Machine | 1524B | 2 | `4B 01 98 00 75 DF 01 20 00 64 03 03 01 00 4A E0 01 20 00 64 03 03 02 00 23 DE 01 20 00 64 03 03` |
| 🔵 Sunucu Yanıtı | `0x4B (75)` | `7` | Lucky Draw Wheel Spin / Slot Machine | 3B | 1 | `4B 07 01` |
| 🔵 Sunucu Yanıtı | `0x4B (75)` | `8` | Lucky Draw Wheel Spin / Slot Machine | 4B | 2 | `4B 08 00 00` |
| 🔵 Sunucu Yanıtı | `0x4B (75)` | `10` | Lucky Draw Wheel Spin / Slot Machine | 714B | 2 | `4B 0A 47 00 84 78 01 C2 01 64 02 03 01 00 83 87 01 5E 01 64 02 03 02 00 A8 78 01 C2 01 64 02 03` |
| 🟣 Yeni Sunucu Paketi | `0x54 (84)` | `3` | Character Deletion Confirmation | 14B | 1 | `54 03 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x55 (85)` | `13` | UNKNOWN / NEW OP-CODE | 4B | 1 | `55 0D 00 00` |
| 🟣 Yeni Sunucu Paketi | `0x55 (85)` | `20` | UNKNOWN / NEW OP-CODE | 31B | 1 | `55 14 0E 47 75 48 75 4B 75 4C 75 4D 75 4E 75 4F 75 50 75 51 75 52 75 53 75 54 75 55 75 56 75` |
| 🟣 Yeni Sunucu Paketi | `0x5A (90)` | `1` | UNKNOWN / NEW OP-CODE | 4B | 1 | `5A 01 00 01` |
| 🔵 Sunucu Yanıtı | `0x68 (104)` | `1` | Lucky Draw / UFO Claw Machine / Gobang Game | 59B | 2 | `68 01 01 00 12 59 77 01 63 85 01 4C 85 01 2C 89 01 2D 89 01 D2 85 01 19 86 01 18 86 01 16 86 01` |
| 🟣 Yeni Sunucu Paketi | `0x69 (105)` | `2` | UNKNOWN / NEW OP-CODE | 4B | 1 | `69 02 03 01` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `1` | Client Settings / System Option Flag Sync | 6B | 1 | `B7 01 F4 9B 03 00` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `2` | Client Settings / System Option Flag Sync | 6B | 1 | `B7 02 F4 9B 03 00` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `3` | Client Settings / System Option Flag Sync | 18B | 1 | `B7 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `11` | Client Settings / System Option Flag Sync | 4B | 4 | `B7 0B 09 02` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `12` | Client Settings / System Option Flag Sync | 4B | 5 | `B7 0C 01 0A` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `13` | Client Settings / System Option Flag Sync | 8B | 1 | `B7 0D 03 F6 E5 03 00 00` |
| 🔵 Sunucu Yanıtı | `0xB7 (183)` | `17` | Client Settings / System Option Flag Sync | 3B | 1 | `B7 11 00` |
| 🟣 Yeni Sunucu Paketi | `0xB8 (184)` | `2` | Advanced Client Option Configuration | 12B | 2 | `B8 02 01 00 02 00 03 00 04 00 05 00` |
| 🔵 Sunucu Yanıtı | `0xBA (186)` | `9` | Co-op Event / Team Event Instance Room | 9B | 4 | `BA 09 01 00 01 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0xBA (186)` | `11` | Co-op Event / Team Event Instance Room | 6B | 2 | `BA 0B 03 00 00 00` |
| 🔵 Sunucu Yanıtı | `0xBA (186)` | `12` | Co-op Event / Team Event Instance Room | 7B | 4 | `BA 0C 01 00 00 00 00` |
| 🔵 Sunucu Yanıtı | `0xBA (186)` | `14` | Co-op Event / Team Event Instance Room | 12B | 1 | `BA 0E 01 01 0D C5 0C C5 03 00 00 00` |
| 🔵 Sunucu Yanıtı | `0xBA (186)` | `16` | Co-op Event / Team Event Instance Room | 3B | 1 | `BA 10 00` |

## 3. Desteklenen Paketler (Fully Supported Packets in wloserver)

| Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Yön | Boyut | Görülme Sayısı |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x00 (0)` | `-` | Version Validation / Disconnect / Heartbeat | C->S | 1B | 1 |
| `0x02 (2)` | `11` | Character List / Selection | S->C | 55B | 22 |
| `0x05 (5)` | `0` | Map Movement / Coordinate Sync | S->C | 14B | 85 |
| `0x05 (5)` | `3` | Map Movement / Coordinate Sync | S->C | 78B | 1 |
| `0x05 (5)` | `4` | Map Movement / Coordinate Sync | S->C | 2B | 3 |
| `0x05 (5)` | `8` | Map Movement / Coordinate Sync | S->C | 7B | 4 |
| `0x05 (5)` | `11` | Map Movement / Coordinate Sync | S->C | 8B | 1 |
| `0x05 (5)` | `13` | Map Movement / Coordinate Sync | S->C | 5B | 10 |
| `0x05 (5)` | `14` | Map Movement / Coordinate Sync | S->C | 3B | 1 |
| `0x05 (5)` | `15` | Map Movement / Coordinate Sync | S->C | 3B | 1 |
| `0x05 (5)` | `16` | Map Movement / Coordinate Sync | S->C | 3B | 1 |
| `0x05 (5)` | `18` | Map Movement / Coordinate Sync | S->C | 7B | 3 |
| `0x05 (5)` | `21` | Map Movement / Coordinate Sync | S->C | 3B | 1 |
| `0x05 (5)` | `24` | Map Movement / Coordinate Sync | S->C | 5B | 10 |
| `0x05 (5)` | `29` | Map Movement / Coordinate Sync | S->C | 16B | 1 |
| `0x05 (5)` | `30` | Map Movement / Coordinate Sync | S->C | 8B | 4 |
| `0x05 (5)` | `42` | Map Movement / Coordinate Sync | S->C | 4B | 1 |
| `0x06 (6)` | `1` | Channel & Map Selection ACK | C->S | 9B | 145 |
| `0x06 (6)` | `2` | Channel & Map Selection ACK | S->C | 3B | 13 |
| `0x08 (8)` | `1` | Grid Movement Steps & Path Routing | S->C | 12B | 27 |
| `0x08 (8)` | `3` | Grid Movement Steps & Path Routing | S->C | 16B | 3 |
| `0x09 (9)` | `1` | UNKNOWN / NEW OP-CODE | C->S | 35B | 1 |
| `0x09 (9)` | `2` | UNKNOWN / NEW OP-CODE | C->S | 10B | 1 |
| `0x09 (9)` | `3` | UNKNOWN / NEW OP-CODE | S->C | 3B | 1 |
| `0x0A (10)` | `3` | System / Combat State Broadcast | S->C | 7B | 80 |
| `0x0A (10)` | `6` | System / Combat State Broadcast | S->C | 7B | 12 |
| `0x0A (10)` | `7` | System / Combat State Broadcast | S->C | 3B | 1 |
| `0x0B (11)` | `4` | Pet Action / State Change / Capture Result | S->C | 642B | 1 |
| `0x0C (12)` | `1` | UNKNOWN / NEW OP-CODE | C->S | 2B | 2 |
| `0x0C (12)` | `246` | UNKNOWN / NEW OP-CODE | S->C | 14B | 2 |
| `0x0E (14)` | `5` | Item Hotbar Slot / Quick Usage | S->C | 30B | 1 |
| `0x0E (14)` | `11` | Item Hotbar Slot / Quick Usage | S->C | 28B | 1 |
| `0x0E (14)` | `13` | Item Hotbar Slot / Quick Usage | S->C | 3B | 2 |
| `0x0F (15)` | `1` | Vehicle / Companion Mount & Voyage Navigation | S->C | 54B | 1 |
| `0x0F (15)` | `4` | Vehicle / Companion Mount & Voyage Navigation | S->C | 433B | 1 |
| `0x0F (15)` | `7` | Vehicle / Companion Mount & Voyage Navigation | C->S | 5B | 1 |
| `0x0F (15)` | `10` | Vehicle / Companion Mount & Voyage Navigation | S->C | 9B | 2 |
| `0x0F (15)` | `10` | Vehicle / Companion Mount & Voyage Navigation | C->S | 5B | 1 |
| `0x0F (15)` | `11` | Vehicle / Companion Mount & Voyage Navigation | S->C | 7B | 1 |
| `0x0F (15)` | `13` | Vehicle / Companion Mount & Voyage Navigation | C->S | 6B | 1 |
| `0x0F (15)` | `14` | Vehicle / Companion Mount & Voyage Navigation | C->S | 5B | 1 |
| `0x0F (15)` | `14` | Vehicle / Companion Mount & Voyage Navigation | S->C | 13B | 21 |
| `0x0F (15)` | `15` | Vehicle / Companion Mount & Voyage Navigation | S->C | 8B | 1 |
| `0x0F (15)` | `18` | Vehicle / Companion Mount & Voyage Navigation | S->C | 17B | 1 |
| `0x13 (19)` | `1` | Player Status / Stats Sync | S->C | 6B | 1 |
| `0x14 (20)` | `1` | NPC Interaction / Dialogue Trigger | C->S | 4B | 13 |
| `0x14 (20)` | `1` | NPC Interaction / Dialogue Trigger | S->C | 18B | 28 |
| `0x14 (20)` | `6` | NPC Interaction / Dialogue Trigger | C->S | 2B | 51 |
| `0x14 (20)` | `7` | NPC Interaction / Dialogue Trigger | S->C | 2B | 2 |
| `0x14 (20)` | `8` | NPC Interaction / Dialogue Trigger | S->C | 2B | 18 |
| `0x14 (20)` | `8` | NPC Interaction / Dialogue Trigger | C->S | 4B | 1 |
| `0x14 (20)` | `9` | NPC Interaction / Dialogue Trigger | C->S | 3B | 4 |
| `0x14 (20)` | `10` | NPC Interaction / Dialogue Trigger | S->C | 2B | 22 |
| `0x14 (20)` | `11` | NPC Interaction / Dialogue Trigger | S->C | 2B | 6 |
| `0x17 (23)` | `2` | Inventory / Item Manipulation / Ground Loot / Pickup | C->S | 4B | 1 |
| `0x17 (23)` | `2` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 5B | 1 |
| `0x17 (23)` | `4` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 32B | 2 |
| `0x17 (23)` | `6` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 33B | 19 |
| `0x17 (23)` | `9` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 4B | 1 |
| `0x17 (23)` | `11` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 44B | 1 |
| `0x17 (23)` | `31` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 776B | 1 |
| `0x17 (23)` | `32` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 6B | 2 |
| `0x17 (23)` | `54` | Inventory / Item Manipulation / Ground Loot / Pickup | C->S | 2B | 3 |
| `0x17 (23)` | `76` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 6B | 83 |
| `0x17 (23)` | `77` | Inventory / Item Manipulation / Ground Loot / Pickup | C->S | 2B | 1 |
| `0x17 (23)` | `102` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 2B | 3 |
| `0x17 (23)` | `111` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 97B | 1 |
| `0x17 (23)` | `112` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 6B | 2 |
| `0x17 (23)` | `122` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 6B | 86 |
| `0x17 (23)` | `131` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 155B | 1 |
| `0x17 (23)` | `132` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 6B | 2 |
| `0x17 (23)` | `138` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 2B | 3 |
| `0x17 (23)` | `140` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 11B | 1 |
| `0x17 (23)` | `160` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 3B | 1 |
| `0x17 (23)` | `162` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 5B | 1 |
| `0x17 (23)` | `204` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 4B | 1 |
| `0x17 (23)` | `208` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 8B | 2 |
| `0x17 (23)` | `221` | Inventory / Item Manipulation / Ground Loot / Pickup | S->C | 3B | 3 |
| `0x19 (25)` | `44` | P2P Secure Trade Handshake & Item Exchange | S->C | 11B | 1 |
| `0x20 (32)` | `2` | Player Emote / Expression Animation | C->S | 3B | 27 |
| `0x20 (32)` | `2` | Player Emote / Expression Animation | S->C | 7B | 2 |
| `0x20 (32)` | `3` | Player Emote / Expression Animation | C->S | 2B | 3 |
| `0x21 (33)` | `2` | Friend List / Add / Remove / Online State | S->C | 8B | 1 |
| `0x23 (35)` | `2` | UNKNOWN / NEW OP-CODE | C->S | 18B | 1 |
| `0x23 (35)` | `2` | UNKNOWN / NEW OP-CODE | S->C | 4B | 1 |
| `0x23 (35)` | `4` | UNKNOWN / NEW OP-CODE | S->C | 18B | 1 |
| `0x23 (35)` | `11` | UNKNOWN / NEW OP-CODE | S->C | 2B | 1 |
| `0x23 (35)` | `12` | UNKNOWN / NEW OP-CODE | S->C | 7B | 29 |
| `0x23 (35)` | `16` | UNKNOWN / NEW OP-CODE | S->C | 23B | 1 |
| `0x27 (39)` | `9` | Guild System / Clan Roster / Quest Abandon | S->C | 381B | 1 |
| `0x27 (39)` | `31` | Guild System / Clan Roster / Quest Abandon | S->C | 452B | 1 |
| `0x36 (54)` | `201` | UNKNOWN / NEW OP-CODE | S->C | 16B | 2 |
| `0x3E (62)` | `4` | Tent Furniture Placement / Movement | S->C | 124B | 1 |
| `0x3E (62)` | `45` | Tent Furniture Placement / Movement | S->C | 6B | 1543 |
| `0x3E (62)` | `46` | Tent Furniture Placement / Movement | S->C | 342B | 1 |
| `0x3E (62)` | `53` | Tent Furniture Placement / Movement | S->C | 4B | 1 |
| `0x3F (63)` | `1` | UNKNOWN / NEW OP-CODE | S->C | 66B | 1 |
| `0x3F (63)` | `2` | UNKNOWN / NEW OP-CODE | C->S | 3B | 1 |
| `0x3F (63)` | `4` | UNKNOWN / NEW OP-CODE | C->S | 32B | 1 |
| `0x41 (65)` | `3` | Tent World Map Pitching / Enter Tent | S->C | 386B | 1 |
| `0x4B (75)` | `1` | Lucky Draw Wheel Spin / Slot Machine | S->C | 1524B | 2 |
| `0x4B (75)` | `7` | Lucky Draw Wheel Spin / Slot Machine | S->C | 3B | 1 |
| `0x4B (75)` | `8` | Lucky Draw Wheel Spin / Slot Machine | S->C | 4B | 2 |
| `0x4B (75)` | `10` | Lucky Draw Wheel Spin / Slot Machine | S->C | 714B | 2 |
| `0x59 (89)` | `0` | UNKNOWN / NEW OP-CODE | C->S | 6B | 1 |
| `0x5C (92)` | `1` | UNKNOWN / NEW OP-CODE | C->S | 2B | 1 |
| `0x68 (104)` | `1` | Lucky Draw / UFO Claw Machine / Gobang Game | S->C | 59B | 2 |
| `0xB7 (183)` | `1` | Client Settings / System Option Flag Sync | S->C | 6B | 1 |
| `0xB7 (183)` | `2` | Client Settings / System Option Flag Sync | S->C | 6B | 1 |
| `0xB7 (183)` | `3` | Client Settings / System Option Flag Sync | S->C | 18B | 1 |
| `0xB7 (183)` | `11` | Client Settings / System Option Flag Sync | S->C | 4B | 4 |
| `0xB7 (183)` | `12` | Client Settings / System Option Flag Sync | S->C | 4B | 5 |
| `0xB7 (183)` | `13` | Client Settings / System Option Flag Sync | S->C | 8B | 1 |
| `0xB7 (183)` | `17` | Client Settings / System Option Flag Sync | C->S | 3B | 1 |
| `0xB7 (183)` | `17` | Client Settings / System Option Flag Sync | S->C | 3B | 1 |
| `0xBA (186)` | `9` | Co-op Event / Team Event Instance Room | C->S | 4B | 4 |
| `0xBA (186)` | `9` | Co-op Event / Team Event Instance Room | S->C | 9B | 4 |
| `0xBA (186)` | `11` | Co-op Event / Team Event Instance Room | S->C | 6B | 2 |
| `0xBA (186)` | `12` | Co-op Event / Team Event Instance Room | S->C | 7B | 4 |
| `0xBA (186)` | `14` | Co-op Event / Team Event Instance Room | S->C | 12B | 1 |
| `0xBA (186)` | `16` | Co-op Event / Team Event Instance Room | S->C | 3B | 1 |