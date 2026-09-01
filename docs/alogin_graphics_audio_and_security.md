# aLogin.exe Grafik, Ses ve Güvenlik/Anti-Hile Motoru

Bu doküman, `aLogin.exe` içerisindeki DirectDraw 7 2D grafik çizim sistemini, DirectSound ses motorunu, 6 haneli ikincil güvenlik PIN kilidini (`AC 226`) ve hız/hareket doğrulama (anti-cheat) mekanizmalarını detaylandırır.

---

## 1. DirectDraw 2D Grafik Motoru ve Yüzey Yönetimi

İstemci, klasik 2.5D izometrik perspektifteki harita zeminlerini, NPC ve karakter sprite'larını DirectDraw yüzeyleri (`IDirectDrawSurface7`) üzerinde işler:

### `FUN_0046f928` (Sprite ve Doku Yüzey Çizici / Blitter)
- **Satır Aralığı:** `457636 - 458310`
- **İmza:** `void FUN_0046f928(int *param_1, int param_2)`
- **94 Durumlu `switch-case` Yapısı:**
  - BMP ve animasyon karelerini arka tampondan (`BackBuffer`) ön ekrana (`PrimarySurface`) aktarır (`BltFast` / `Flip`).
  - Şeffaflık (Color Keying - Magenta / `0xFF00FF`) ve gölgelendirme katmanlarını işler.

### `FUN_0049c3bc` & `FUN_0049f5e8` (Yüzey Palet ve Parlaklık Efektleri)
- **Satır Aralığı:** `482841 - 485565`
- **159 ve 70 Durumlu `switch-case` Yapıları:**
  - Hava durumu efektleri (Yağmur, Kar, Kiraz Çiçeği / Sakura, Sis, Fırtına) esnasında ekran paletini dinamik olarak karartır veya parlatır.

---

## 2. DirectSound Ses ve Müzik Motoru (Audio Engine)

### `FUN_00115a38` (Ses Efekti / WAV Yürütücüsü)
- **Satır Aralığı:** `123752 - 123964`
- **100 Durumlu `switch-case` Yapısı:**
  - `IDirectSoundBuffer` üzerinden arayüz tıklama sesleri, kılıç savurma, büyü patlama, adım ve eşya düşme efektlerini (`.wav`) çalar.

### `FUN_0016ea20` (Harita Arka Plan Müziği / BGM Yönetimi)
- **Satır Aralığı:** `153989 - 154103`
- **43 Durumlu `switch-case` Yapısı:**
  - Harita ID'sine göre ilgili arka plan müziğini döngüsel (looping) olarak çalar veya harita değişiminde ses geçişi (cross-fade) yapar.

---

## 3. Güvenlik, İkincil PIN Kilidi ve Anti-Hile

### 6 Haneli İkincil Güvenlik Kilidi (`AC 226` / `0xE2`)
- **İşleyiş:**
  - Oyuncu banka kasasını açmak, karakter silmek (`form_delChar`), değerli eşyaları takas etmek veya pazara koymak istediğinde sistem 6 haneli güvenlik PIN kodunu talep eder.
  - Şifre istemciden sunucuya doğrudan `0xE2` (`226`) paketi ile doğrulanmak üzere iletilir (`FUN_002d6994(socket, 0xE2, 1, 0)`).

### Hız ve Hareket Doğrulaması (Anti-Cheat Movement Speed Checks)
- İstemci, karakterin bir grid karesinden diğerine geçiş süresini yerel zamanlayıcı ile sınırlar.
- Hız hilesi (Speedhack) girişimlerini tespit etmek amacıyla her adım paketinde (`0x08`) önceki adım zamanı ile aradaki delta kontrol edilir; hız sınırını aşan isteklerde karakter önceki koordinatına geri ışınlanır (Rubberbanding).
