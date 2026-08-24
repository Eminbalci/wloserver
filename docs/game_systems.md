# Oyun Sistemleri (Game Systems)

Bu doküman, Wonderland Online Python sunucusunda çalışan temel oyun mekaniklerini, mesafe güvenlik kurallarını, savaş motorunu ve GM (Game Master) komutlarını detaylandırır.

---

## 1. Savaş ve Combat Motoru (Battle & Combat Engine)

Savaşlar PVE (Canavarlarla Karşılaşmalar) ve PVP PK (Oyuncular Arası Düellolar) olarak ikiye ayrılır.

### A. Rastgele Karşılaşmalar (PVE Encounters)
- Oyuncu harita üzerinde hareket ettikçe istemci tarafında adım sayacı artar.
- Adım limitine ulaşıldığında, bulunulan bölgenin `.MapData` karşılaşma havuzundaki canavarlar seçilir ve sunucuya **Opcode 11 Sub-opcode 2** (Savaş Başlatma İsteği) gönderilir.
- Sunucu tarafında tıklanan veya savaşılan hedefin mesafesi doğrulanır.

### B. PVP Düello / PK Daveti (PVP Battle Duel)
- Bir oyuncu diğerine PK teklif ettiğinde **Opcode 11 Sub-opcode 3** (PK Daveti) paketi tetiklenir.
- Sunucu, iki oyuncunun aynı haritada olduğunu ve aralarındaki mesafenin **271 pikselden** (`0x10f`) kısa olduğunu doğrular. Mesafe sınırı aşılırsa istek reddedilir.
- Savaş başladığında taraflar `_start_pvp_battle(challenger, target)` metodu ile düello durumuna alınır.

### C. Sıra Çözümleme ve Yetenekler (Turn Resolution)
- Savaş esnasında oyuncular ve petlerinin hız değerleri (`spd`) kıyaslanarak turn sırası belirlenir.
- Her tur oyuncuların eylemlerinin (`expected_coords`) tamamlanması beklenir.
- Canavarlar / NPC'ler PVE savaşlarında %30 olasılıkla temel saldırı yerine element tabanlı büyü yeteneklerini kullanabilir. Yetenek kullanımında hedefin SP miktarı düşürülür, animasyon ID'si gönderilir ve yetenek hasar çarpanı uygulanır.

---

## 2. Etkileşim ve Mesafe Doğrulamaları (Interaction Distance Checks)

Güvenlik amacıyla sunucu tarafında oyuncunun yaptığı fiziksel tıklamalar ve etkileşimler mesafe doğrulamasına tabi tutulur:

- **NPC Tıklama Mesafesi**: `handle_20_interaction.py` üzerinde oyuncu haritadaki bir NPC ile etkileşime girdiğinde, oyuncu koordinatları ile NPC koordinatları arasındaki fark kontrol edilir. Mesafe her iki eksende de **169 pikselden** (`0xa9`) büyükse etkileşim engellenir.
- **PVP Düello Mesafesi**: PK davetlerinde oyuncular arası mesafe **271 pikseli** aşmamalıdır.
- **Su Toplama Mesafesi**: Su kaynaklarından su toplarken karakterin su kaynağı nesnesine olan mesafesi kontrol edilir (`Too far from water` doğrulaması).

---

## 3. GM (Game Master) Yetki ve Komut Sistemi

Oyunda belirli hesaplar `is_gm = 1` olarak işaretlenebilir. Sadece bu hesaplar oyun içi sohbette `:` öneki ile başlayan GM komutlarını çalıştırabilir.

### GM Komutları Listesi

| **Komut** | **Açıklama** | **Örnek Kullanım** |
| :--- | :--- | :--- |
| `:warp <map_id> <x> <y>` | Belirtilen haritaya ve koordinata ışınlar. | `:warp 10017 1000 1000` |
| `:item add <item_id> [amount]` | Karakter envanterine eşya ekler. | `:item add 10004 1` |
| `:level <level>` | Karakter seviyesini ayarlar. | `:level 100` |
| `:stat <str> <con> <int> <wis> <agi>` | Karakterin temel niteliklerini setler. | `:stat 100 100 100 100 100` |
| `:gold <amount>` | Karakterin altın miktarını günceller. | `:gold 50000` |
| `:heal` | Karakter HP ve SP değerlerini tamamen doldurur. | `:heal` |
| `:element <0-4>` | Karakter elementini değiştirir (0:Yok, 1:Toprak, 2:Su, 3:Ateş, 4:Rüzgar). | `:element 3` |
| `:skill <skill_id> [grade]` | Belirtilen yeteneği seviyesiyle birlikte öğrenir/günceller. | `:skill 15003 10` |
| `:clear` | Karakter envanterini tamamen temizler. | `:clear` |
| `:propshop` | Eşya dükkan arayüzünü açar. | `:propshop` |
| `:kick <char_name>` | Karakteri oyundan atar (GM yetkisi gerekir). | `:kick Ahmet` |
| `:ban <char_name>` | Karakterin hesabını yasaklar (banned = 1). | `:ban Hileci` |
| `:mute <char_name>` | Karakterin sohbette konuşmasını engeller. | `:mute Troll` |
| `:ride <vehicle_id>` | Taşıt kısıtlamalarını aşarak taşıta binmeyi sağlar. | `:ride 27001` |
| `:unride` | Taşıttan inmeyi tetikler. | `:unride` |
| `:remote` | Remote control oto-savaş durumunu (is_remote_control) tetikler. | `:remote` |

- **Element Uyuşmazlık Doğrulaması**: `:skill` komutuyla veya normal yollarla yetenek öğrenilirken karakterin element uyuşmazlığı denetlenir. Karakter kendi elementi haricindeki element büyülerini öğrenemez (`Earth/Water/Fire skill mismatched` denetimleri).

---

## 4. Eşya, Simya ve Ticaret Sistemleri

### A. Eşya Kullanımı ve Tüketimi
- Sarf malzemeleri (yiyecek, iksir vb.) kullanıldığında HP ve SP değerlerini belirlenen oranlarda yeniler.
- Seviye limiti bulunan ekipmanlar sadece gerekli seviyeye ulaşıldığında kuşanılabilir.
- Karakter envanterinde kilitli olan eşyalar (`Item locked, can't use`) satılamaz, çöpe atılamaz, yok edilemez veya takasta kullanılamaz.

### B. Simya (Compound) ve Junior Alchemy
- Envanterdeki malzemeler birleştirilerek yeni eşyalar sentezlenir.
- Karakterin **Junior Alchemy** (ID: `15998`) yeteneği aktif ise, simya sentezleme sonucunda elde edilecek eşyanın rankına pozitif bonus eklenir.

---

## 5. Çadır ve Crafting Sistemi

- **Çadır Açma & Giriş**: Oyuncu `handle_23_items.py` (Opcode 23 Sub-opcode 15) aracılığıyla kişisel çadırını haritaya kurabilir ve `handle_62_tent.py` ile çadıra girebilir.
- **Mobilya Yerleştirme**: Çadır içine envanterdeki mobilyalar yerleştirilebilir. Savaşta veya yıkanırken mobilya sabitleme/tamir işlemleri engellenir (`Can't fix in bath` / `Can't fix in battle`).
- **Üretim (Crafting)**: Çadır içerisindeki üretim araçları (tezgahlar, ocaklar) ile crafting gerçekleştirilir. Sentezleme tarifleri `recipes.json` dosyasından okunur. Crafting başlatıldığında süre zamanlayıcı paketleri (Opcode 64 Sub-opcode 1, 10, 2) gönderilir. Balık tutarken veya gruptayken üretim yapılması engellenir (`Currently fishing` ve `Can't do in team` doğrulamaları).

---

## 6. Taşıt ve Ulaşım Mekanizmaları (Vehicles)

- **Binme & İnme**: Oyuncu kano, sal, araba gibi araçlara binebilir (Opcode 23 Sub-opcode 51) veya inebilir (Sub-opcode 52).
- **Yakıt Yükleme**: Araçların çalışabilmesi için envanterden yakıt yüklenmesi gerekir (Opcode 23 Sub-opcode 134). Uygun olmayan yakıt türlerinde `"No suitable fuel type"` uyarısı verilir.
- **Tamir Kitleri**: Araç hasar aldığında taşıt tamir kiti ile tamir edilebilir. Savaş esnasında veya araç dışı nesnelerde tamir işlemi engellenir (`Only for Vehicles` / `Can't repair in battle`).
