# aLogin.exe Kimlik Doğrulama, Sunucu/Kanal ve Karakter Yönetimi

Bu doküman, `aLogin.exe` içerisindeki giriş (authentication), sunucu listesi (`SERVER.INI`), kanal seçimi, karakter oluşturma, karakter silme ve Rebirth (Yeniden Doğuş) sınıflarını yöneten fonksiyonları detaylandırır.

---

## 1. Giriş ve Sunucu/Kanal Fonksiyonları

### `FUN_0032f674` (`SERVER.INI` ve Sunucu Grubu Ayrıştırıcı)
- **Satır Aralığı:** `299311 - 299528`
- **İmza:** `void FUN_0032f674(undefined4 param_1, int param_2)`
- **Parametreler:**
  - `param_1`: Hedef UI liste nesnesi göstericisi.
  - `param_2`: Sunucu grubu indeksi.
- **İşleyiş:**
  - `GetPrivateProfileStringA` API'sini kullanarak yerel `SERVER.INI` dosyasını tarar.
  - Sunucu isimlerini, IP adreslerini ve portlarını (`25221` / `25620`) okur.
  - `form_server` listesini doldurur ve oyuncunun sunucu seçimini hazırlar.

### `FUN_0033c310` (Giriş Yanıtı Paket İşleyicisi)
- **Satır Aralığı:** `303177 - 303242`
- **İmza:** `void FUN_0033c310(int *param_1, int param_2)`
- **Parametreler:**
  - `param_1`: İstemci oturum nesnesi.
  - `param_2`: Sunucudan gelen ham paket göstericisi (`packet_data`).
- **İşleyiş:**
  - `param_2 + 1` ofsetindeki baytı (Sonuç Kodu) kontrol eder:
    - **`0x01` (Başarılı Giriş):** Oyuncunun Account GUID değerini (`DAT_0071ef58 + 0x268`) kaydeder, karakter seçim ekranı arayüzünü (`form_selectChar`) aktifleştirir.
    - **`0x02` (Hatalı Şifre/Kullanıcı):** `"Login/Pwd error"` hata bildirimini arayüzde gösterir.
    - **`0x03` (Hesap Zaten Oyunda):** `"Account already logged in"` uyarısını basar.
    - **`0x04` (Hesap Askıya Alınmış / Yasaklı):** `"Account blocked / banned"` penceresini açar.

### `FUN_0014c114` (Kanal Listesi Paket Ayrıştırıcısı)
- **Satır Aralığı:** `146882 - 147065`
- **İmza:** `void FUN_0014c114(int param_1, int param_2)`
- **Parametreler:**
  - `param_1`: Kanal UI liste bileşeni.
  - `param_2`: Gelen kanal paketi tamponu.
- **İşleyiş:**
  - Sunucudan gelen maksimum 21 kanallık listeyi ayrıştırır.
  - Kanal türü bayraklarına göre arayüz butonlarını renklendirir:
    - `0x01`: Normal Kanal (Yeşil / Standart PVE).
    - `0x02`: PK / PVP Kanalı (Kırmızı / Serbest Düello).
    - `0x03`: Etkinlik / Özel Kanal (Sarı / Event).

---

## 2. Karakter Oluşturma, Seçme ve Silme Fonksiyonları

### `FUN_0022fcf4` (Karakter Listesi ve Slot Yönetimi)
- **Satır Aralığı:** `224848 - 225579`
- **İmza:** `void FUN_0022fcf4(int *param_1, int param_2)`
- **Parametreler:**
  - `param_1`: Karakter seçim form bağlamı (`form_selectChar`).
  - `param_2`: Gelen karakter verisi tamponu.
- **İşleyiş:**
  - Oyuncuya ait 4 karakter yuvasını tarar.
  - Her karakterin ID, İsim, Seviye (Level), Element (Earth=0, Water=1, Fire=2, Wind=3), Saç stili, Vücut renkleri ve giyili ekipman modellerini yükler.

### `FUN_001a3f68` (Karakter Rebirth Sınıfları ve Nitelik Açıklamaları)
- **Satır Aralığı:** `178104 - 178141`
- **İmza:** `void FUN_001a3f68(int param_1, int param_2)`
- **İşleyiş:**
  - Yeniden Doğuş (Rebirth) sonrasında seçilebilecek 6 ileri seviye meslek sınıfının açıklamalarını ve pasif stat çarpanlarını arayüze bağlar:
    1. **Warrior (Savaşçı):** Yüksek DEF ve fiziksel direnç; çeviklikten feragat eder.
    2. **Knight (Şövalye):** Yüksek hareket kabiliyeti ve SPD; eyersiz binek kullanımında binek hızının 1/5'ini kazanır.
    3. **Killer (Suikastçı):** Yüksek ATK ve kritik vuruş olasılığı.
    4. **Priest (Rahip):** Yüksek MDEF ve büyü koruması, takım destek büyüleri.
    5. **Wit (Bilge):** Yüksek MATK ve elemental alan hasarı.
    6. **Seer (Kâhin):** Yüksek mühürleme (Seal) başarı oranı ve durum etkileri.

### Karakter Silme ve Güvenlik Denetimi
- Oyuncu karakter silme butonuna (`form_delChar`) bastığında `FUN_0022d4f0` tetiklenir.
- Karakterin silinebilmesi için 6 haneli ikincil güvenlik PIN kodunun (`AC 226` / `0xE2`) doğrulanması zorunludur. Yanlış girilirse karakter silme işlemi durdurulur.
