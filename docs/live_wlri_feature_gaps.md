# WLRI Canlı Oyun Paket ve Sunucu Özellik Boşluk Analizi (Live Server Feature Gap Report)

- **Tarih / Saat:** 2026-09-07 01:11:22
- **Hedef İstemci:** `C:\Games\WLRI\aLogin.exe`
- **Dinlenen Sunucu IP'leri:** 20.187.103.41, 104.208.85.33, 20.187.123.156, 20.205.14.213, 47.238.172.210
- **Toplam İncelenen Ağ Paketi:** 37
- **Tespit Edilen Farklı Paket Türü:** 3

## 1. Sunucuda Eksik Olan İstemci İstekleri (Client Requests Missing in wloserver)

Aşağıdaki paketler canlı istemci tarafından sunucuya gönderilmiş ancak `wloserver/server/handlers/` içinde işlenmemiştir:

| Durum | Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Boyut | Görülme Sayısı | Örnek Hex |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| - | - | - | *Şu ana kadar eksik istemci isteği saptanmadı.* | - | - | - |

## 2. Orijinal Sunucudan Gelen ve İncelenmesi Gereken Paketler (Server -> Client Protocol)

| Durum | Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Boyut | Görülme Sayısı | Örnek Hex |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 🔵 Sunucu Yanıtı | `0x02 (2)` | `1` | Character List / Selection | 48B | 1 | `02 01 D4 E5 03 00 62 75 74 20 66 6F 72 20 6C 69 6B 65 20 61 20 77 65 65 6B 20 49 20 62 65 65 6E` |
| 🔵 Sunucu Yanıtı | `0x05 (5)` | `1` | Map Movement / Coordinate Sync | 8B | 1 | `05 01 FE E5 03 00 E5 84` |
| 🔵 Sunucu Yanıtı | `0x3E (62)` | `45` | Tent Furniture Placement / Movement | 6B | 35 | `3E 2D 42 E0 03 00` |

## 3. Desteklenen Paketler (Fully Supported Packets in wloserver)

| Opcode (Hex/Dec) | Sub-Code | Sistem / İşlev | Yön | Boyut | Görülme Sayısı |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x02 (2)` | `1` | Character List / Selection | S->C | 48B | 1 |
| `0x05 (5)` | `1` | Map Movement / Coordinate Sync | S->C | 8B | 1 |
| `0x3E (62)` | `45` | Tent Furniture Placement / Movement | S->C | 6B | 35 |