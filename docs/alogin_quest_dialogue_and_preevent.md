# aLogin.exe Görev, Diyalog ve PreEvent Sistemi (Quest & Dialogue Engine)

Bu doküman, `aLogin.exe` içerisindeki görev günlüğünü (Quest Journal - `form_taskview_1`), **Opcode 39 (`0x27`)** alt paket protokolünü, `Talk.dat` diyalog kuyruğunu ve `eve.Emg` PreEvent tetikleyicilerini yöneten fonksiyonları detaylandırır.

---

## 1. Görev Günlüğü ve Opcode 39 Alt Protokol Fonksiyonları

İstemci ile sunucu arasındaki tüm görev ve günlük işlemleri `FUN_002d6994` üzerinden **Opcode 39 (`0x27`)** paketiyle yürütülür:

### `FUN_00314380` (Görev Listesi Talebi / Journal Open)
- **Satır Aralığı:** `286844 - 286867`
- **İmza:** `void FUN_00314380(int *param_1)`
- **Paket:** `FUN_002d6994(socket, 0x27, 1, 0)` -> **Alt-Opcode `1`**
- **İşleyiş:**
  - Oyuncu Görev Günlüğü arayüzünü (`form_taskview_1`) açtığında sunucuya aktif görevlerin listesini istemek üzere gönderilir.

### `FUN_00417380` (Takım İçi Görev Yardımı / Paylaşımı)
- **Satır Aralığı:** `408264 - 408302`
- **İmza:** `void FUN_00417380(int *param_1, int param_2)`
- **Paket:** `FUN_002d6994(socket, 0x27, 2, 0)` -> **Alt-Opcode `2`**
- **İşleyiş:**
  - Takım lideri veya üyesi ortak bir görevi takım arkadaşlarıyla paylaşmak istediğinde tetiklenir.
  - Hedef meşgulse `"Unable to apply, player is busy"` uyarısını basar.

### `FUN_00418854` & `FUN_0041a0a8` (Görevi Bırakma / Abandon Quest)
- **Satır Aralığı:** `409935 - 409963`
- **İmza:** `void FUN_0041a0a8(int *param_1)`
- **Paket:** `FUN_002d6994(socket, 0x27, 7, 0)` -> **Alt-Opcode `7`**
- **İşleyiş:**
  - Oyuncu günlükten bir görevi iptal ettiğinde (`Abandon Quest`) sunucuya bildirim göndererek görev durumunu sıfırlar.

### `FUN_0041894c` & `FUN_0041896c` (Lonca Görev / Üye Listesi Senkronizasyonu)
- **Satır Aralığı:** `409068 - 409089`
- **Paket:**
  - `FUN_002d6994(socket, 0x27, 10, 0)` -> **Alt-Opcode `10`**
  - `FUN_002d6994(socket, 0x27, 11, 0)` -> **Alt-Opcode `11`**
  - `FUN_002d6994(socket, 0x27, 12, 0)` -> **Alt-Opcode `12`**
- **İşleyiş:**
  - Görev günlüğünde lonca üye ve katkı durumunu listeler.

### `FUN_003f9318` & `FUN_003f9680` (Görev İzleme / Tracking HUD)
- **Satır Aralığı:** `390657 - 390774`
- **Paket:**
  - `FUN_002d6994(socket, 0x27, 50, 0)` (`0x32`) -> Görev takibini HUD paneline sabitleme.
  - `FUN_002d6994(socket, 0x27, 51, 0)` (`0x33`) -> Görev takibini HUD panelinden kaldırma.

---

## 2. `Talk.dat` Çok Adımlı Diyalog Kuyruğu ve NPC Eşleştirme

- Haritada bir NPC'ye tıklandığında istemci sunucuya **Opcode 20 (`0x14`)** paketi gönderir (`FUN_002d6994(socket, 0x14, 6, 0)`).
- Sunucudan dönen diyalog ID'si, istemci tarafında `Talk.dat` binary tablosundan taranarak oyuncu ve NPC portreleri, metin blokları, dallanma seçenekleri (Seçim A / Seçim B) ve ifade animasyonları (`AC 32`) ile sırayla ekranda yürütülür.

---

## 3. `eve.Emg` PreEvent ve Dinamik Görünürlük Bayrakları

- İstemci, 1,119 haritanın her birinde yer alan dinamik aktörlerin (NPC'ler, Sandıklar, Işınlanma kapıları) görünürlüğünü `eve.Emg` dosyasındaki PreEvent bayt kodlarına göre doğrular.
- Oyuncunun tamamladığı görev bayrakları (`Mark.dat` kayıtları) karşılaştırılarak, tamamlanmış görev NPC'leri haritadan gizlenir veya yeni hikaye NPC'leri görünür kılınır.
