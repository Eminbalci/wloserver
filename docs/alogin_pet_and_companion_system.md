# aLogin.exe Evcil Hayvan ve Yoldaş Sistemi (Pet & Companion System)

Bu doküman, `aLogin.exe` içerisindeki evcil hayvan (pet) yapay zekasını, çağrılma/gizlenme durumlarını, binek olarak sürülmesini, sevgi (Amity) sistemini ve Pet Kafesi takas kısıtlamalarını yöneten fonksiyonları detaylandırır.

---

## 1. Pet Çağırma, Gizleme ve Durum Yönetimi

### `FUN_003de310` (Aktif Pet Çağırma/Gizleme Durum Değiştirici)
- **Satır Aralığı:** `376389 - 376408`
- **İmza:** `void FUN_003de310(int param_1)`
- **Parametreler:**
  - `param_1`: Oyuncu/Karakter veri nesnesi.
- **İşleyiş:**
  - Oyuncunun en fazla 4 pet yuvasını (`iVar1` 1'den 5'e) tarar.
  - Pet yapısındaki `0x1efc` ofset bayrağını günceller:
    - **Bayrak = `1`:** Pet harita üzerinde çağrılmış (summoned) ve karakterin arkasında yürümektedir.
    - **Bayrak = `0`:** Pet geri çekilmiş / gizlenmiştir.

### `FUN_0013d794` (Pet Savaş ve Binek Kısıtlamaları)
- **Satır Aralığı:** `141887 - 142153`
- **İşleyiş:**
  - Petin durumunu denetleyerek uygunsuz eylemleri engeller:
    - `"Pet in battle!"`: Pet savaş halindeyken envanterden silinmesini, takas edilmesini veya beslenmesini engeller.
    - `"Pet is mounted!"`: Pet binek olarak sürülüyorken eşya üretimi veya kaplıcaya girilmesini durdurur (`"Bathing, unable to make"`).

---

## 2. Pet Yapay Zeka (AI) Modları ve Yetenek Karar Ağacı

### `FUN_003e9898` (Pet AI Durum ve Yetenek Seçim Ağacı)
- **Satır Aralığı:** `382158 - 384691`
- **İmza:** `undefined1 FUN_003e9898(int param_1, int param_2)`
- **92 Durumlu `switch-case` Yapısı:**
  - Petin kimliğine (Örn: `0x1088` Niss, `0xCA0` Cliff, `0xAFE` Roca, `0x91B` Sam) ve HP/SP durumuna göre otomatik savaş yapay zekasını belirler.
  - `active_pet + 0x121` adresindeki mod değerlerini günceller:
    - `0`: Standart Saldırı Modu (Auto Attack).
    - `1`: Savunma / Koruma Modu (Defensive Guard).
    - `2`: Destek / İyileştirme Modu (Support / Heal).
    - `3`: Büyü / Elemental Saldırı Modu (Magic / Skill Burst).
    - `4`: Dinlenme Modu (Rest Mode - Çadır içi HP/SP yenileme).
    - `5`: Tezgah Modu (Stall Mode - Oyuncu yokken pazar nöbetçisi).
    - `6` - `7`: Dolaşma Modu (Roam Mode).
    - `0x2F`, `0x31`, `0x33`, `0x35`: Mod geçiş ve animasyon tetikleyicileri.

### `FUN_003cdd00` (Pet Animasyon ve Yetenek Efekti Yürütücüsü)
- **Satır Aralığı:** `367049 - 367775`
- **41 Durumlu `switch-case` Yapısı (`0x18` - `0x1F`):**
  - Petin özel büyülerini kullanırken sergileyeceği animasyon çerçevelerini ve ses efektlerini yürütür.

---

## 3. Pet Binek Sistemi ve Takas Kısıtlamaları

### Pet Sürüşü (Pet Riding)
- Oyuncu bir binek petine Eyer (`Saddle` / Eşya ID `38020`) taktığında, pet binek durumuna geçer.
- Oyuncunun dünya haritasındaki hareket hızına **+%40 hareket hızı** çarpanı eklenir.
- Knight (Şövalye) mesleği pasif özelliği sayesinde eyersiz binek kullanımında dahi binek hızının %20'sini (`1/5 SPD`) doğrudan kazanır.

### `FUN_00344974` (Pet Satış ve Takas Doğrulayıcısı)
- **Satır Aralığı:** `306173 - 306517`
- **İşleyiş:**
  - `"Can't sell active pet"`: Haritada çağrılmış durumdaki petlerin satılmasını engeller.
  - `"Can't sell mounted pet"`: Sürülmekte olan binek petlerinin pazar tezgahına koyulmasını engeller.
  - Takas edilmek istenen hikaye/yoldaş petleri için **Pet Kafesi** (`Pet Cage`) eşyasının envanterde bulunmasını doğrular.
