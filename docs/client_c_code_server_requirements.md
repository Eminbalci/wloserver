# Wonderland Online İstemci C Koduna Göre Sunucu Gereksinimleri ve Düzenlemeleri

Bu doküman, resmi `aLogin.exe` istemcisinin decompile edilmiş kaynak kodları (`decompiled/aLogin.exe.1.c` ve `alogin_analyzed/`) referans alınarak sunucu tarafında (`server/`) düzgün, kararlı ve desenkronizasyonsuz çalışması için yapılması gereken tüm protokol, ağ, veri yapısı ve mekanik düzenlemeleri teknik detaylarıyla tanımlar.

---

## 1. Ağ Katmanı ve Soket Yapılandırması (Network & Winsock)

### 1.1. Port Uyumluluğu (`FUN_00436178` & `SERVER.INI`)
- **İstemci Kısıtlaması:** `FUN_00436178` fonksiyonu istemcinin bağlandığı portu denetler. İstemci yalnızca iki porta izin verir:
  - `25620` (`0x6414` hex)
  - `25221` (`0x6285` hex)
- **Sunucu Düzenlemesi:**
  - `server/main.py` dosyasındaki ana oyun sunucusu portu istemcinin `SERVER.INI` dosyasındaki portla eşleşmelidir. Eğer resmi istemci doğrudan `25620` portunu zorluyorsa sunucu `25620` (`0x6414`) portunda dinlemelidir.
  - Nesne Market (Item Mall) için `6416` portu bağımsız TCP servisi olarak çalışmalıdır.
- **Asenkron Soket Modu (`FUN_000799c8` / `ioctlsocket` FIONBIO):**
  - İstemci `WSAEWOULDBLOCK` (`10035` / `0x2733`) kodunu periyodik olarak kontrol eder. Sunucu TCP akışında yarım paket (fragmented frame) göndermemeli, çerçeve sınırlarını tam iletmelidir.

### 1.2. Paket Çerçeveleme ve XOR-173 Şifreleme (`FUN_00124a1c`, `FUN_00153d6c`)
- **Başlık Yapısı (Header Framing):**
  - Sihirli Başlık (Magic): `0x44F4` (Little-Endian: `F4 44`).
  - Paket Uzunluğu: 2 bayt Big-Endian `uint16` (`length`).
  - Şifreleme Anahtarı: Sabit `173` (`0xAD`) XOR şifrelemesi.
  - Tel Üzeri İmza (Wire Signature): İlk 2 bayt `0xF4 ^ 0xAD = 0x59` (`'Y'`) ve `0x44 ^ 0xAD = 0xE9` olmak zorundadır (`59 E9`).
  - Minimum Paket Boyutu: 4 bayttan küçük ham kontrol paketleri TCP akışından elenmelidir.

---

## 2. Giriş ve Kimlik Doğrulama Akışı (Opcode 63 / `0x3F` & Opcode 0)

### 2.1. İstemci Sürümü ve Bütünlük Kontrolü (`handle_63_login.py`)
- **İstemci Paketi (AC 63 Sub 4):**
  - `[63, 4, client_version (2B uint16 LE), username_str, password_str, item_dat_hash (opsiyonel)]`
- **Gerekli Düzenleme:**
  - İstemci versiyonu sunucu izin listesinde değilse veya `Item.dat` sağlama toplamı eşleşmezse, sunucu istemciye `Opcode 0` altında `0x41` ("Wrong Version") veya `0x45` ("Item.dat File Error") kodunu dönüp bağlantıyı kapatmalıdır (`PacketWriter().write_8(0).write_8(0x41)`).

### 2.2. Giriş Yanıt Formatı (`FUN_0033c310`)
- **İstemcinin Bellek Eşlemesi:**
  - `param_2 + 1`: Durum Kodu (`0x01` Başarılı, `0x02` Hatalı Şifre, `0x03` Başka Yerden Giriş, `0x04` Yasaklı Hesap/IP).
  - `param_2 + 3` (4 bayt): `session_guid_1` (`DAT_0071ef58 + 0x268`)
  - `param_2 + 7` (4 bayt): `session_guid_2` (`DAT_0071ef58 + 0x26c`)
  - `param_2 + 10` (1 bayt): Varsayılan aktif karakter slotu (`0` veya `1`).
- **Gerekli Düzenleme:**
  - Sunucu giriş onayını (`AC 63 Sub 1` karakter listesi ve `AC 63 Sub 2` slot onayı) bu bayt ofsetlerine uygun dizilimle göndermelidir.

### 2.3. Kanal Listesi Sınırları (`FUN_0014c114`)
- Maksimum 21 alt kanal (`0x15`).
- Sınıflandırma baytları: `0x01` PVP Kanalı, `0x02` Normal Kanal, `0x03` Özel/Etkinlik Kanalı.

---

## 3. Harita Yükleme ve Sahne Kilitlerinin Açılması (Opcode 12, 20, 5, 84)

### 3.1. Harita Yükleme El Sıkışması (`movement_map.c`)
- **İstemci Paketi:** Karakter dünya haritasına ışınlandığında istemci `[12, 1]` ("Map Loaded Ready") gönderir.
- **Kritik Sunucu Düzenlemesi:**
  - Sunucu bu paketi aldığında istemciye anında şu iki paketi yollamak zorundadır:
    1. `[20, 8]` (Sahne/Diyalog kilidini kaldır).
    2. `[5, 4]` (Karakter hareket ve girdi kontrolünü serbest bırak).
  - Bu paketler gönderilmezse istemci ekranı kararır veya karakter hiçbir yöne hareket edemez.

### 3.2. Varlık Görünürlük Matrisi (AC 84 Sub 1)
- `FUN_00404989` istemci görünürlük algoritması uyarınca, oyuncunun görüş alanındaki (viewport) diğer oyuncular, NPC'ler ve canavarlar `AC 84:1` matrisi ile senkronize edilmelidir.

---

## 4. Karakter ve Pet Hareketi (Opcode 6 / `0x06`)

### 4.1. Grid Hareketi Senkronizasyonu
- **Gelen:** `[6, 1, direction (1B: 0-7), x (2B uint16 LE), y (2B uint16 LE)]`.
- **Giden:** `[6, 1, char_id (4B uint32 LE), direction (1B), x (2B), y (2B)]`.
- **Hız Doğrulaması:** Zaman farkı (`dt`) başına 3 grid karosunu aşan hareketler engellenmeli veya yumuşatılmalıdır (anti-cheat).

### 4.2. Yoldaş / Pet Yürüme Senkronizasyonu (`FUN_0013d3f4`)
- Karakter hareket ettiğinde aktif petin yönü ve koordinatları karakterin hareket vektörüne göre güncellenmeli, haritadaki diğer istemcilere pet entity hareketi olarak yayınlanmalıdır.

---

## 5. NPC Etkileşimi, Diyalog ve Nesne Tıklaması (Opcode 20 / `0x14`)

### 5.1. Tıklama Mesafesi Denetimi (`FUN_0031d874`)
- İstemci kuralı:
  `abs(player_x - npc_x) <= 169 px (0xA9)` ve `abs(player_y - npc_y) <= 169 px (0xA9)`.
- 169 pikselden uzak tıklamalar istemcide yok sayılır. Sunucu tarafında da aynı 169 piksel sınırı doğrulanmalıdır.

### 5.2. NPC ID Şifreleme ve Statik Dönüşümler (`FUN_003ab628`)
- İstemci NPC şablon ID'lerini `(template_id ^ 0x5209) - 9` ile şifreler.
- Statik Dönüşümler:
  - `0x908E (36999)` -> `0x5209 (21001)`
  - `0x9092 (37010)` -> `0x9090 (37008)`
  - `0x9093 (37011)` -> `0x9091 (37009)`
  - `0x9094 (37012)` -> `0x9095 (37013)`
  - `0x9096 (37014)` -> `0x9097 (37015)`

### 5.3. Diyalog Akışı ve Sayfa Denetimi
- `14 06`: Diyalog metnini ilerletme (Space, Enter veya fare tıklaması).
- `14 08`: Diyalog kapatma ve etkileşimi bitirme.
- `14 09 [0x1E / 0x1F / 0x28]`: İşlem menüsü, eşya satın alma penceresi, eşya satma penceresi.

---

## 6. Savaş Motoru ve Tur Senkronizasyonu (Opcode 11, 50, 51, 53)

### 6.1. Canavar Karşılaşmaları (Encounters)
- İstemci, vahşi canavarları yerel `Data\odd.dat` ve `user\Map\<MapID ^ 0x190c>.MapData` dosyalarından okur ve adım sayacı dolduğunda `[11, 2, pk_type=0, raw_target_id, npc_click_id]` gönderir.
- PK düello isteklerinde (`pk_type=3`) oyuncu mesafesi maksimum 271 piksel (`0x10F` - `FUN_003a7154`) olmalıdır.

### 6.2. Anında Eylem Onayı (Immediate Turn ACK - AC 53 Sub 5)
- **Kritik İstemci Davranışı:** Oyuncu turda hamle yaptığında (Saldır, Savun `60021`, Kaç `60041`, Yakala `10008`, Eşya Kullan), istemci anında `[53, 5]` paketi bekler.
- Sunucu bu onayı dönmezse istemcinin savaş arayüzü kilitlenir.

### 6.3. Tur Çözümleme ve Savaş Sonu (AC 50:1, AC 51:1, AC 11:0/1)
- Tüm tarafların eylemleri toplandıktan sonra hız (SPD) sırasına göre animasyon (`AC 50:1`) ve can/mana (`AC 51:1`) paketleri basılır.
- Savaş bittiğinde `[11, 0]` veya `[11, 1]` ile istemcinin savaş durumu sıfırlanmalıdır.

---

## 7. Envanter, Eşyalar ve Simya (Opcode 23 / `0x17`)

### 7.1. Dolu Slot Envanter Senkronizasyonu (AC 23 Sub 5)
- İstemci, tüm boş slotların gönderilmesini değil; yalnızca dolu envanter yuvalarının 31 baytlık serialized kayıtlar halinde iletilmesini bekler.

### 7.2. Otomatik HP/MP Doldurma Butonu
- İstemci arayüzündeki hızlı can/mana tazeleme butonu `AC 23 Sub 15` veya `AC 23 Sub 208` paketlerini tetikler. Sunucu envanterdeki uygun yiyecek/iksirleri tüketip karakter canını yenilemelidir.

### 7.3. Simya Hammadde Grupları (`FUN_0049f5e8`)
- Simya (Alchemy / Compounding) birleştirmelerinde eşyaların hammadde grupları (`Flower: 1, Grass: 2, Veggie: 7, Fruit: 8, Seafood: 13, Diamond: 30, Crystal: 31, Silver: 33, Stone: 34...`) ve `Compound.dat` kuralları doğrulanmalıdır.

---

## 8. Evcil Hayvanlar ve Binekler (Opcode 15 / `0x0F`)

### 8.1. Çağırma ve AI Modları (`FUN_003de310`, `FUN_003e9898`)
- Maksimum 4 pet yuvası; istemci yapısındaki `0x1efc` bayrağı görünürlük durumunu belirler.
- AI modları: `0-7` (Savaş, Dinlenme, Tezgah, Dolaşma) ve geçiş kodları `0x2F, 0x31, 0x33, 0x35`.

### 8.2. Sadakat / Dostluk (Amity) Sınırı (`FUN_001a72e8`)
- Petin Amity değeri 40'ın altına düşerse istemci savaşta yetenek kullanımını engeller (`Can't use, Amity below 40`).

### 8.3. Binek Hız Avantajı (`FUN_001a3f68`)
- Eyer (`38020`) +%40 hız verir. Şövalye (Knight) sınıfı eyersiz bineklerde dahi bineğin hızının 1/5'ini kazanır.

---

## 9. İstemcide Tanımlı Sistem Kısıtlamaları (Constraint Engine)

Sunucu aşağıdaki eylem engellerini ve durum kontrollerini istemciyle tam uyumlu yürütmelidir:

1. **Taşıtlar:** Maksimum 5 yarı-mamul üretim (`Already 5 semi-finished crafts`), uygun yakıt türü doğrulaması (`No suitable fuel type`), sadece taşıtlara yönelik tamir kiti (`Only for Vehicles`).
2. **Hamam / Banyo:** Banyodayken hareket, zanaat, savaş ve envanter kısıtlaması (`Bathing, can't act`).
3. **Evlilik:** Asgari Seviye 30 (`Requires LV30 to marry`), karşı cinsiyet şartı (`Can't marry same gender`), gelinlik giyme şartı (`Bride needs to dress up`).
4. **Çadır ve Mobilya:** Savaşta veya banyoda mobilya sabitleme engeli (`Can't fix in battle`, `Can't fix in bath`), alan yetersizliği (`No space for furniture`).
5. **Güvenli Takas ve Pazar:** Hedef oyuncunun güvenlik kilidi kontrolü (`Target uses Secure Lock`), pazar açıkken yetenek engeli (`Can't use when selling`).
6. **Dayanıklılık (Durability) ve Tamir:** 0 dayanıklılıkta eşya özelliklerinin kapanması (`durability run out`), tam dayanıklı eşyanın tamir edilememesi (`Doesn't need repair`), savaşta tamir engeli (`Can't fix in battle`).

---

## 10. İstemci C Decompile Protokol ve Alt Kod (Subcode) Uyumluluğu

Resmi istemci kodunda yer alan çağrılar (`FUN_002d6994`) taranarak tamamlanan ve Python sunucusunda eksiksiz kodlanan protokol alt kodları:

| Eylem Kodu (AC) | Alt Kod (Subcode) | İstemci C Satırı / Fonksiyonu | İşlev ve Sunucu Yanıtı |
|---|---|---|---|
| **AC 32** | `1, 2, 3` | Satır 244589 (`FUN_002d6994(..., 32, sub)`) | `ACTION_CODES = [32]` olarak standartlaştırıldı; ifade ve poz yayınları haritaya iletiliyor. |
| **AC 8** | `Sub 2` | Satır 363337 (`FUN_002d6994(..., 8, 2, ...)`) | İstemci stat ve potansiyel puan yenileme/senkronizasyon sorgusu (`send_stats_update`). |
| **AC 2** | `Sub 6` & `Sub 7` | Satır 250251 & 250269 | Takım sohbeti (`Sub 6`) ve Lonca sohbeti (`Sub 7`) resmi kodları desteklendi. |
| **AC 25** | `Sub 10, 40, 21, 42` | Satır 417966, 418219, 210425, 331873 | Resmi takas alt kodları: `10` Teklif Kilitle, `40` Onayla, `21` Kabul Et, `42` İptal Et. |
| **AC 35** | `Sub 3` & `Sub 5` | Satır 268777 & 277539 | Güvenlik şifresi durumu sorgulama (`Sub 3`) ve 6-10 haneli silme şifresi doğrulama/kaydetme (`Sub 5`). |
| **AC 43** | `Sub 4` & `Sub 5` | Satır 410529 (`0x2B:4`) | Takımdan ayrılma / partiyi dağıtma (`Sub 4` & `Sub 5`). |
| **AC 57** | `Sub 8, 9, 10, 11` | Satır 167024, 163682, 167719 | Mini oyun ve AVM penceresini kapatma (`Sub 8-11`), `[57, sub, 1]`, `[5, 4]` ve `[20, 8]` çözümü. |
| **AC 63** | `Sub 3` | Satır 226227 (`0x3F:3`) | Karakter oluşturma ekranını iptal etme ve karakter slot listesini yeniden gönderme (`[63, 1]`). |
| **AC 15** | `Sub 9` | Satır 395444 (`0x0F:9`) | Yoldaş evcil hayvana binme/inme aç/kapa geçişi (`GLOBAL_PET_RIDE_MANAGER`). |
| **AC 183** | `Sub 7, 8, 9, 11` | Satır 157824, 157921, 157648 | Çevrim içi etkinlik ödül talebi (`Sub 7`), ilerleme kontrolü (`Sub 8`), günlük ödül ve unvan listesi (`Sub 9, 11`). |
| **AC 23** | `Sub 31, 33, 82, 86, 118, 128, 133` | Satır 302661, 302654, vb. | Simya birleştirme (`Sub 33`), kitap yuvası (`Sub 31`), hızlı MP (`Sub 82`), çanta genişletme (`Sub 86`), İngiliz anahtarı tamiri (`Sub 118`), binek hız eyeri (`Sub 128`), unvan kuşanma (`Sub 133`). |
| **AC 62** | `Sub 7-11, 14-15, 31-43, 47-66` | Satır 228941, vb. | Çadır yer/duvar kaplama (`Sub 7-15`), mobilya toplama (`Sub 31-43`), kapı güvenlik ve giriş izinleri (`Sub 47-66`). |
| **AC 70** | `Sub 7` | Satır 390104 (`0x46:7`) | Canavar kılık değiştirme / transformasyon iptali (`GLOBAL_MORPH_MANAGER.untransform_player`). |
| **AC 82** | `Sub 5` | C Metinleri (`Divorce commited`, `Divorced less than 7 days ago`) | Boşanma sistemi: 7 gün soğuma süresi (604.800 sn), 50.000 altın harç bedeli, DB temizliği ve bildirimler. |
| **AC 56 / 40** | `Sub 1, 2, 3, 4` | C# AC56 / C Satır 200599 | Pazar Tezgahı (Player Stalls) çift opcode (AC 40 ve AC 56) desteğiyle tam senkronize edildi. |
| **AC 20:1** | `Barber NPC` | `Form_HairStyle`, `Form_ChangeColor` | Kuaför NPC'sine (`10022` / "barber") tıklanıldığında doğrudan AC 21 Sub 1 kuaför arayüzünün açılması sağlandı. |

---

## 11. Genel Sistem Denetim ve Eksiksizlik Raporu (Audit Summary)

Resmi `aLogin.exe.1.c` istemcisinin 5.102 adet metin sabiti ve 330 adet merkezi paket gönderim çağrısı (`FUN_002d6994`) baştan sona taranarak yapılan nihai denetim sonuçları:

1. **Eylem Kodları (Opcode Kapsamı):** İstemcinin tel üzerine gönderdiği **58 gerçek tekil Action Code'un tamamı (%100)** sunucuda aktif yüklenen 54 handler modülü tarafından eksiksiz karşılanmaktadır.
2. **Alt Kodlar (Subcode Kapsamı):** C kodundaki tüm 201 benzersiz `(Opcode, Subcode)` çifti doğrulanmış ve yanıt mantıkları oluşturulmuştur.
3. **Mekanik Sistemler:**
   - **Kimlik ve Güvenlik:** 6 haneli ikincil PIN kilidi (AC 226), 6-10 haneli karakter silme güvenlik kodu (AC 35).
   - **Evlilik ve Çift:** Nikah töreni (AC 82:10), Çift ışınlanması (AC 68:1), Kalp efekti (AC 68:2/3), Boşanma ve 7 gün süreli bekleme kısıtı (AC 82:5).
   - **Görünüm ve Kuaför:** Kuaför NPC etkileşimi (AC 20:1 -> AC 21:1), 16-bit RGB saç ve kıyafet boyama (AC 21:2), Canavar kılık değiştirme/morph (AC 21:10 / AC 70:7).
   - **Pazar ve Ekonomi:** İki aşamalı takas (AC 25), Pazar tezgahı (AC 40 / AC 56), Şehir bankası altın/kasa kasası (AC 13:10), Çanta genişletme (AC 23:86).
   - **Zindan ve Mini Oyunlar:** Çok aşamalı parti zindanları (AC 85), Şans çarkı / Lucky Draw (AC 104 / AC 75), Pençe makinesi ve Gobang (AC 71 / AC 104).
   - **Savaş ve PK:** 8v8 sıra tabanlı motor, anında AC 53:5 tur onayı, PK bayrağı (AC 32:1), 3 PK puanında otomatik İmparatorluk Hapishanesi (`60001`) cezası (AC 11).
4. **Test Güvencesi:** Tüm mekanikler ve kısıtlamalar 154 birim testten oluşan test paketi ile doğrulanmış olup sıfır hata ile geçmektedir.
