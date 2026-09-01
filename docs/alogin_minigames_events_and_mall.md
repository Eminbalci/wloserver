# aLogin.exe Mini Oyunlar, Şans Çarkı ve Item Mall Sistemi

Bu doküman, `aLogin.exe` içerisindeki Şans Çarkını (Lucky Draw - Opcode 75), Pençe / Kıskaç Makinesini (UFO Catcher Claw - Opcode 13), Gobang (Beş Taş / Gomoku - Opcode 104), Item Mall mağazasını ve sunucu çapındaki etkinlik duyurularını yöneten fonksiyonları detaylandırır.

---

## 1. Şans Çarkı ve Etkinlik Dağıtıcısı

### `FUN_003e175c` (Şans Çarkı ve Sistem Etkinlikleri Dağıtıcısı)
- **Satır Aralığı:** `378491 - 378831`
- **İmza:** `void FUN_003e175c(int *param_1, int param_2)`
- **86 Durumlu `switch-case` Yapısı:**
  - Sunucudan gelen etkinlik paketlerini ve çark sonuçlarını dinler:
    - **Çark Çevirme Komutu:** `FUN_002d6994(socket, 0x4B, 1, 0)` (`Opcode 75`) ile çark döndürme isteği atar.
    - **Ödül Çarkı Döndürme Animasyonu:** Gelen kazanan eşya indeksine göre çarkı yavaşlayarak durdurur ve ödül açılış efektini oynatır.
    - **Çifte EXP Etkinliği Duyurusu:** `"Double EXP event has begun! Don't miss it!"` sistem duyurusunu ekrana basar.
    - **Item Mall Çift Ödül Etkinliği:** `"Double rewards in Item Mall mini-games has begun/ended!"` bildirimini işler.

---

## 2. Mini Oyunlar: Pençe Makinesi (Claw Crane) ve Gobang (Gomoku)

### `FUN_0010e218` (Mini Oyun Arayüz ve Hareket Dağıtıcısı)
- **Satır Aralığı:** `119523 - 119760`
- **İmza:** `undefined4 FUN_0010e218(int *param_1, int param_2)`
- **44 Durumlu `switch-case` Yapısı:**
  - **UFO Catcher (Pençe Makinesi - Opcode 13 / `0x0D`):**
    - `0x0D, 1`: Pençeyi sağa/sola hareket ettirme.
    - `0x0D, 4`: Pençeyi aşağı indirme ve kapsül yakalama komutu.
    - `0x0D, 10, 2`: Mini oyun sonu kazanılan eşyayı envantere aktarma.
  - **Gobang (Beş Taş Tahta Oyunu - Opcode 104 / `0x68`):**
    - `15x15` boyutundaki Gobang tahtasında taş koyma (Siyah / Beyaz) koordinatlarını sunucuyla senkronize eder.
    - Çapraz, yatay veya dikey 5 taş birleştiğinde zafer/yenilgi ekranını açar.
  - **Mini Oyun Çıkışı (Exit Handler - Opcode 57 / `0x39`):**
    - Oyuncu çıkış butonuna bastığında `FUN_002d6994(socket, 0x39, 1, 0)` yollayarak oyun oturumunu güvenle kapatır.

---

## 3. Item Mall Mağaza Kataloğu ve Puan Sistemi

- İstemci, sunucuya `0x17` alt kodları veya `TCP 6416` portu üzerinden bağlanarak Item Mall eşya kategorilerini (Ekipman, Binek, Mobilya, İksir, Özel) listeler.
- Oyuncunun mevcut Item Mall Puanı (`Point Balance`) ve VIP derecesi (`Num_Vip_3`) arayüzün üst kısmında gösterilir.
- Satın alma işlemi yapıldığında envanterde yeterli boş alan (`Inventory Space`) olup olmadığı kontrol edilir.
