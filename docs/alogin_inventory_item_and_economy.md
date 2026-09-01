# aLogin.exe Envanter, Eşya, Simya ve Ekonomi Sistemi

Bu doküman, `aLogin.exe` içerisindeki envanter yönetimini, eşya kullanım dağıtıcısını (`FUN_0044651c`), ekipman dövmeyi (Forging), simyayı (Alchemy), P2P Güvenli Takası (`FUN_002a1f14`), Oyuncu Pazarlarını (Stall) ve Banka sistemini detaylandırır.

---

## 1. Envanter ve Eşya Kullanım Dağıtıcısı

### `FUN_0044651c` (Ana Eşya Kullanım ve Etki Dağıtıcısı)
- **Satır Aralığı:** `437214 - 439407`
- **İmza:** `void FUN_0044651c(int *param_1, int param_2)`
- **46 Durumlu `switch-case` Yapısı:**
  - Tıklanan veya kullanılan eşyanın türüne (`ItemType`) göre ilgili alt motoru tetikler:
    - **Durum `1` (Tüketilebilir İksirler):** HP / SP yenileyen yiyecek ve iksirler (Rice Ball, Potion).
    - **Durum `2` (Ekipman Giy / Çıkar):** Silah, Zırh, Başlık, Ayakkabı, Yüzük yuvalarına eşya takma ve stat güncelleme.
    - **Durum `3` (Işınlanma Parşömenleri):** Geri Dönüş Parşömeni (Return Scroll), Hafıza Parşömeni (Memory Scroll).
    - **Durum `4` (Çadır Mobilyası):** Çadır içi dekorasyon ve zanaat aletlerinin yere yerleştirilmesi (`0x3E`).
    - **Durum `5` (Binek / Araç Eşyaları):** Eyer (Saddle), Sal, Buharlı Gemi, Uçan Halı araç aktivasyonları.
    - **Durum `7` (Anahtar & Sandıklar):** Bronz, Gümüş, Altın anahtarlarla dünya sandıklarını açma.
    - **Durum `10` (Simya & Birleştirme Kitapları):** Alchemy Book I - IV ile bileşik derecesini artırma.
    - **Durum `0x0B` (Dönüşüm Hapları):** Disguise Morph iksirleri (Jelly, Wolf, Ghost).

---

## 2. Ekipman Dayanıklılığı, Tamir ve Dövme (Forging & Repair)

### Ekipman Dayanıklılığı ve İngiliz Anahtarı (Spanner Repair)
- Her savaş sonunda kuşanılmış zırh ve silahların dayanıklılık (`Durability`) değeri 1 azalır.
- Dayanıklılık 0'a ulaştığında eşyanın verdiği tüm statlar geçici olarak devre dışı kalır.
- Oyuncu `Spanner` (İngiliz Anahtarı) veya `Small Spanner` kullandığında `0x17` (`23`) alt opcodeları ile dayanıklılık maksimum değerine onarılır.

### `FUN_00267ea8` (Ekipman Dövme ve Kristal Yuvaları)
- **Satır Aralığı:** `243792 - 243995`
- **İşleyiş:**
  - Dövme Jetonları (`Forging Tokens`) veya Item Mall Puanı harcayarak ekipman seviyesini yükseltir.
  - İstemci içi doğrulama diyalogları:
    - `"You have #R%d tokens/#R\nForge 1 time uses #R1/#R\n\nItem won't be tradeable\nConfirm?"`: Dövülen eşyanın takas edilemez (Untradeable) hale geleceğini uyarır.
    - `"All tokens used up\nWill #Rconsume Points/#R\nConfirm?"`: Jeton bittiğinde puan harcama onayı ister.
    - `"Forge at max"`: Ekipmanın maksimum dövme seviyesine (`+10`) ulaştığını bildirir.

---

## 3. Ekonomi: P2P Güvenli Takas ve Pazar Tezgahları (Street Stalls)

### `FUN_002a1f14` (İki Aşamalı Güvenli Takas Yuva Eşleştirici)
- **Satır Aralığı:** `262687 - 264666`
- **İmza:** `void FUN_002a1f14(int *param_1, int param_2)`
- **İşleyiş:**
  - `TradeLeftItem`, `OtherSafeTradeItem`, `MySafeTradeItem` fonksiyonlarını koordine eder.
  - İki aşamalı takas doğrulaması:
    1. **Aşama 1 (Kilit / Lock):** İki oyuncu da eşyalarını koyup "Lock" butonuna basar. Eşyalar üzerinde değişiklik yapılamaz.
    2. **Aşama 2 (Onay / Confirm):** İki oyuncu da kilitlenmiş listeyi onayladığında sunucuya `0x19` (`25`) paketi gönderilerek transfer tamamlanır.

### `FUN_001d9f08` (Pazar Tezgahı ve Güvenlik Denetimi)
- **Satır Aralığı:** `200599 - 200758`
- **İşleyiş:**
  - Oyuncuların sokaklarda pazar tezgahı (`form_stall`) açmasını veya başkasının pazarına tıklamasını yönetir.
  - `"Target uses Stall"`: Hedef oyuncu pazar açmışsa doğrudan takas teklifini engeller, mağaza arayüzünü açar.
  - `"Target uses Secure Lock"`: Karakteri kilitli olan hedeflerle ticareti durdurur.
