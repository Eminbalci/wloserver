# aLogin.exe Ağ İletişimi ve Paket Protokolü Dokümantasyonu

Bu doküman, `aLogin.exe` içerisindeki Winsock ağ fonksiyonlarını, paket oluşturucu/gönderici mekanizmasını (`FUN_002d6994`), paket çözümleyiciyi ve Action Code (Opcode) dağıtım tablosunu detaylandırır.

---

## 1. Alt Seviye Winsock Sarmalayıcıları (Low-Level Winsock Wrappers)

İstemci, ağ iletişiminde `ws2_32.dll` API'lerini kullanan sarmalayıcı fonksiyonlar barındırır:

### `FUN_000799c8` (Async Socket Connect)
- **Satır Aralığı:** `88312 - 88330`
- **İmza:** `void FUN_000799c8(int param_1)`
- **Parametreler:**
  - `param_1`: Soket bağlam göstericisi (`SocketContext*`).
- **İşleyiş:**
  - `socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)` çağrısıyla TCP soketi üretir.
  - `ioctlsocket(s, FIONBIO, &mode)` ile soketi **non-blocking** (asenkron) moda geçirir.
  - `connect()` ile hedef sunucuya asenkron bağlantı başlatır.

### `FUN_00436178` (Port Doğrulayıcı)
- **Satır Aralığı:** `427019 - 427053`
- **İmza:** `undefined1 FUN_00436178(int param_1)`
- **Parametreler:**
  - `param_1`: Hedef port numarası.
- **İşleyiş:**
  - Bağlanılmak istenen portun Wonderland Online varsayılan portları olan **`25221`** (`0x6285`) veya **`25620`** (`0x6414`) olup olmadığını doğrular. Geçersiz port durumunda bağlantı engellenir.

### `FUN_0007a284` (Async Socket Recv Wrapper)
- **Satır Aralığı:** `88800 - 88879`
- **İmza:** `void FUN_0007a284(int *param_1, char *param_2, int param_3)`
- **Parametreler:**
  - `param_1`: Soket nesnesi.
  - `param_2`: Alınacak ham veri tamponu (`recv_buffer`).
  - `param_3`: Okunacak maksimum bayt uzunluğu.
- **İşleyiş:**
  - `recv()` API'sini çağırır. `WSAEWOULDBLOCK` hatasını yakalayarak kuyruğu bloke etmeden arka planda okuma sağlar.
  - Okunan baytları paket başlık denetimi için çerçeveleme katmanına (`Framing layer`) iletir.

### `FUN_0012479c` (Socket Send Wrapper)
- **Satır Aralığı:** `130372 - 130445`
- **İmza:** `void FUN_0012479c(int param_1, int param_2, uint param_3)`
- **Parametreler:**
  - `param_1`: Soket tanımlayıcısı.
  - `param_2`: Gönderilecek paket tamponu adresi (`const char* buffer`).
  - `param_3`: Gönderilecek bayt boyutu (`length`).
- **İşleyiş:**
  - `send()` çağrısı yaparak sunucuya veri iletir. Soket meşgulse veriyi giden kuyruğa (`Outbound Queue`) ekler; bağlantı kopmuşsa `"Socket send aborted"` logu düşer.

---

## 2. Ana Paket Oluşturucu ve Gönderici (`FUN_002d6994`)

`FUN_002d6994`, istemci genelinde 200'den fazla yerde doğrudan çağrılan **Merkezi Paket İnşa ve İletim** fonksiyonudur.

```c
// aLogin.exe Decompile Mantıksal İmzası
int FUN_002d6994(void *socket_context, uint opcode, uint sub_opcode, ...);
```

### Parametreler & Yapı:
1. `socket_context`: `*PTR_DAT_004c87e4` (Aktif bağlantı nesnesi).
2. `opcode`: Ana paket işlem kodu (`Action Code` / `0x01` - `0xFF`).
3. `sub_opcode`: Paketin alt komut kodu (`Sub-Action Code`).
4. `...`: Pakete eklenecek değişken uzunluklu parametreler (ID'ler, koordinatlar, metinler, eşya indeksleri).

---

## 3. İstemciden Sunucuya Gönderilen Paketler (Client-to-Server Opcodes)

| Opcode (Hex) | Opcode (Dec) | Alt-Opcode / Parametreler | İlgili Fonksiyon & Açıklama |
| :--- | :--- | :--- | :--- |
| **`0x00`** | `0` | `0, 0` | Bağlantı yaşama sinyali (Keep-Alive / Heartbeat ping). |
| **`0x06`** | `6` | `1, 0` | Kanal ve Harita Seçim Onayı. |
| **`0x08`** | `8` | `1, 0` / `2, 0, uVar` | Hareket (Grid Movement) adımları ve rota gönderimi. |
| **`0x0B`** | `11` | `1`, `2, 0` | Savaş aksiyonu (Saldırı, Büyü/Skill kullanımı, Kaçış). |
| **`0x0D`** | `13` | `1`, `4`, `10, 2` | Mini Oyunlar (UFO Catcher / Pençe Makinesi, Gobang tahta hamlesi). |
| **`0x0E`** | `14` | `2, 0`, `3, 0` | Eşya kullanım / Envanter hızlı yuva (Hotbar) işlemleri. |
| **`0x0F`** | `15` | `7`, `9`, `10`, `12`, `13` | Binek / Araç Sistemi (Saddle binme/inme, Gemi seyri). |
| **`0x10`** | `16` | `2, 0`, `3, 0`, `4, 0` | Parti / Takım daveti, kabulü ve takımdan ayrılma. |
| **`0x14`** | `20` | `6, 0`, `9, 0` | Harita NPC tıklama ve NPC diyalog başlatma (`Talk.dat`). |
| **`0x17`** | `23` | `0x1F`, `0x33`, `0x34`, `0x36`, `0x48`, `0x49`, `0x75`, `0x87` | Eşya yönetimi, Dayanıklılık tamiri (Spanner), Simya (Alchemy) ve Item Mall. |
| **`0x18`** | `24` | `5, 0` | Karakter hareket ve animasyon durum bildirimleri. |
| **`0x19`** | `25` | `1, 0`, `3, 0`, `10, 0`, `12, 0`, `0x28`, `0x2A` | İki aşamalı Güvenli Oyuncu Takası (P2P Safe Trade). |
| **`0x1A`** | `26` | `3, 0` | Pazar / Tezgah (Street Stall) açma ve eşya yerleştirme. |
| **`0x20`** | `32` | `2, 0`, `3, 0` | Karakter İfadeleri (Emotes) ve animasyonlu duygular. |
| **`0x21`** | `33` | `1, 0`, `2, 0` | Arkadaş Listesi ekleme, onaylama ve silme istekleri. |
| **`0x22`** | `34` | `1, 0` | Kara liste / Engellenen oyuncu yönetimi. |
| **`0x27`** | `39` | `1`, `2`, `7`, `10`, `11`, `12`, `16`, `17`, `19`, `50`, `51` | Görev Günlüğü (Quest Journal) ve Lonca (Guild) operasyonları. |
| **`0x2B`** | `43` | `4, 0` | Posta Kutusu (Mailbox) mektup ve eşya gönderme. |
| **`0x2D`** | `45` | `8, 0` | Şehir Bankası (Bank Storage) altın ve eşya kasası. |
| **`0x32`** | `50` | `1, 0`, `2, 0` | Evlilik Sistemi (Teklif, Düğün salonu, Eş yanına ışınlanma). |
| **`0x39`** | `57` | `1, 0` | Mini Oyun Çıkış ve Arayüz Kapatma bildirimi. |
| **`0x3E`** | `62` | `1`, `7`, `8`, `9`, `10`, `11`, `0x22`, `0x32`, `0x3C`, `0x40`, `0x42` | Çadır İçi Mobilya Yerleştirme, Döndürme ve Geri Toplama. |
| **`0x40`** | `64` | `2, 0` | Çadır İçi Zanaat / Üretim İstasyonları (Crafting Stations). |
| **`0x41`** | `65` | `0x0B`, `0x0C` | Dünyada Çadır Kurma ve Çadır Toplama. |
| **`0x45`** | `69` | `1`, `2` | Berber NPC saç şekillendirme ve 16-bit RGB boyama. |
| **`0x46`** | `70` | `7` | Canavar Dönüşümü (Morph Disguise) iptali. |
| **`0x47`** | `71` | `1` | Eşya Dönüştürme / Eritme (Smelting Recycle). |
| **`0x4A`** | `74` | `2` | Yeniden Doğuş (Rebirth) dönüşümü ve sınıf seçimi. |
| **`0x4B`** | `75` | `1` | Şans Çarkı (Lucky Draw) çevirme komutu. |
| **`0x54`** | `84` | `1, 0` | Karakter Seçim / Silme Onayı. |
| **`0xE2`** | `226` | `1, 0` | 6 Haneli İkincil Güvenlik PIN Kilidi (Security PIN). |

---

## 4. Paket Çözümleme ve Dağıtım Motoru (Packet Dispatcher)

Gelen paketler, `FUN_0031ecf0` (Satır `291503 - 292576`) ve `FUN_0041ee94` (Satır `412750 - 413147`) fonksiyonlarındaki büyük `switch-case` yapıları üzerinden ilgili alt sistem yöneticilerine dağıtılır.

```c
// Örnek Dağıtım Akışı (FUN_0031ecf0):
switch(packet_opcode) {
    case 0x01: // Login Sonucu -> FUN_0033c310()
    case 0x02: // Karakter Listesi -> FUN_0022fcf4()
    case 0x06: // Harita Değişimi -> FUN_001a4d00()
    case 0x0B: // Savaş Güncellemesi -> FUN_003e4b60()
    case 0x14: // NPC Konuşması -> FUN_00417380()
    case 0x17: // Envanter / Eşya -> FUN_0044651c()
    case 0x27: // Görev Günlüğü -> FUN_00314380()
    case 0x3E: // Çadır Mobilyası -> FUN_002a6ef0()
    // ...
}
```
