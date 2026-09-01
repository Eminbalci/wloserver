# aLogin.exe Savaş Motoru ve Yetenek Sistemi (Combat & Battle Engine)

Bu doküman, `aLogin.exe` içerisindeki 8v8 sıra tabanlı savaş motorunu (Turn-Based Battle), yetenek ağacı arayüzlerini, savaş komutlarını ve etkinlik savaşlarını yöneten fonksiyonları detaylandırır.

---

## 1. Savaş Arayüzü ve Yetenek Yükleyicileri

### `FUN_002b5630` (`Form_BattleSkill_1` Yükleyici ve Yön Kontrolleri)
- **Satır Aralığı:** `272150 - 272262`
- **İmza:** `int * FUN_002b5630(int *param_1, int param_2)`
- **Parametreler:**
  - `param_1`: Savaş formu nesnesi (`Form_Battle`).
  - `param_2`: Aktif karakter/pet göstericisi.
- **İşleyiş:**
  - `Form_BattleSkill_1` yetenek seçim penceresini açar.
  - Sayfalama butonlarını (`Btn_ArrowUp_1`, `Btn_ArrowDn_1`) ve yetersiz SP/durum yasağı ikonlarını (`Icon_Forbid_2`) yükler.
  - Karakterin elementine (Toprak, Su, Ateş, Rüzgar) uygun aktif yetenekleri 4'erli listeler halinde sekmelere dizer.

### `FUN_002591f8` (`form_npcSkillTree` ve Yetenek Öğrenme Arayüzü)
- **Satır Aralığı:** `237897 - 237968`
- **İmza:** `int * FUN_002591f8(int *param_1, int param_2)`
- **İşleyiş:**
  - NPC veya eğitmen ile konuşulduğunda `form_npcSkillTree` arayüzünü oluşturur.
  - Yetenek seviye artırma butonlarını (`icon_levelUp`, `btn_Readme`, `btn_cancel`) bağlar.
  - Yetenek öğrenme gereksinimlerini (Skill Points, Level, Ön Yetenek şartları) doğrular.

### `FUN_002a6ef0` (Savaş Yeteneği Kullanılabilirlik Doğrulayıcısı)
- **Satır Aralığı:** `265977 - 266903`
- **İmza:** `void FUN_002a6ef0(int *param_1, int param_2)`
- **İşleyiş:**
  - Kullanılmak istenen eylemin durumunu doğrular:
    - `"Skill only for battle"`: Sadece savaş esnasında kullanılabilecek yeteneklerin dünya haritasında tetiklenmesini engeller.
    - `"Can't use from Hotbar"`: Hızlı erişim çubuğundan doğrudan kullanılamayan özel eşyaları/yetenekleri denetler.
    - `"No inv. space"`: Savaş sonu veya yetenek sonucu eşya düşüşünde envanter doluluğunu kontrol eder.

---

## 2. Sıra Tabanlı Savaş Durum Dağıtımı

### `FUN_003e4b60` (Savaş Durum ve Aksiyon Dağıtıcısı)
- **Satır Aralığı:** `379471 - 379723`
- **İmza:** `void FUN_003e4b60(int *param_1, int param_2)`
- **59 Durumlu `switch-case` Yapısı:**
  - Gelen savaş paketi durumlarına göre savaş animasyonlarını ve turlarını yürütür:
    - **Durum `1` (Round Start):** Yeni savaş turunu başlatır, 20 saniyelik komut verme zamanlayıcısını çalıştırır.
    - **Durum `2` (Melee / Physical Attack):** Fiziksel vuruş animasyonunu ve hasar sayısını ekrana basar.
    - **Durum `3` (Skill Cast):** Elemental büyü efektini oynatır, SP düşüşünü hesaplar.
    - **Durum `4` (Combo Attack):** Aynı hedefe birden fazla takım üyesi saldırdığında Combo animasyonunu tetikler (2x/3x/4x hasar çarpanı).
    - **Durum `5` (Defend):** Savunma moduna geçer, gelen hasarı %50 azaltır.
    - **Durum `6` (Flee / Escape):** Kaçış girişimini hesaplar (Karakter SPD ve düşman SPD oranına göre başarı/başarısızlık).
    - **Durum `7` (Item Use):** Savaş içi iksir veya diriltme eşyası kullanımını uygular.
    - **Durum `8` (Battle Victory / Defeat):** Savaş sonu EXP, Altın ve Düşen Eşya (Drop) ekranını açar.

---

## 3. Etkinlik Savaşları ve Lonca Savaşları

### `FUN_001a4d00` (Battle Royale Savaş Etkinliği)
- **Satır Aralığı:** `178523 - 178648`
- **İşleyiş:**
  - Seviye 10 ve üzeri oyuncuların Capitol Building 4F haritasındaki Battle Royale alanına girişini ve sıralama puanlarını denetler.
  - Savaş sonu bildirimlerini gösterir: `"Battle Royale has begun"`, `"Battle Royale suspended"`, `"Battle Royale has ended."`.

### `FUN_001a72e8` (Trojan War / Lonca Kuşatması)
- **Satır Aralığı:** `180335 - 180561`
- **İşleyiş:**
  - Saat 20:00'de başlayan Truva Lonca Kuşatması kayıt ve katılım şartlarını doğrular.
  - `"Only same guilds team"`: Kuşatma esnasında yalnızca aynı loncadaki oyuncuların takım kurabilmesini şart koşar.
