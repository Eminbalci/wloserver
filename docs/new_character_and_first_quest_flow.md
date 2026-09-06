# Sıfırdan Karakter Oluşturma ve İlk Görev Canlı Paket Analiz Raporu (New Character & First Quest Live Analysis)

Bu doküman, `C:\Games\WLRI\aLogin.exe` istemcisi üzerinden sıfırdan karakter oluşturulup ilk görevin (Ocean Star gemisi ve Kelan Sahili) tamamlanması sırasında canlı olarak kaydedilen 3.789 ağ paketinin (`yeni_karakter_ve_ilk_gorev.pcapng`) tersine mühendislik analizini içerir.

---

## 1. Genel Oturum İstatistikleri

- **Kaynak PCAP:** `C:\Users\muham\OneDrive\Masaüstü\paketler\yeni_karakter_ve_ilk_gorev.pcapng` (247.495 Bayt)
- **Toplam Çözümlenen Ağ Paketi:** 3.789 adet
- **Tespit Edilen Farklı Paket Türü (Opcode + Sub):** 476 varyant
- **Eksik C->S İstemci İsteği:** 0 (İstemcinin yolladığı tüm temel komutlar `wloserver/server/handlers/` tarafından desteklenmektedir).

---

## 2. Kronolojik Protokol Akışı (Byte-by-Byte Sequence)

### A. Karakter Oluşturma ve Doğrulama (AC 9 / 0x09)
1. **İstemci Karakter Oluşturma Talebi (`C->S AC 9 Sub 1`):**
   - Format: `[09, 01, slot (1B), name (PascalString), body (1B), element (1B), hair (2B), skin (2B), cloth (2B), eye (2B)]` (35 Bayt).
2. **Karakter Slot Seçimi (`C->S AC 9 Sub 2`):**
   - Format: `[09, 02, slot_id (1B)]` (10 Bayt).
3. **Sunucu Oluşturma Onayı (`S->C AC 9 Sub 3`):**
   - Format: `[09, 03, status=0x00]` (3 Bayt) — Karakter başarıyla oluşturuldu ve haritaya yönlendirildi.

---

### B. İlk Giriş ve Başlangıç Hediyeleri Dağıtımı (AC 23 / 0x17 Sub 6)
Sunucu, yeni karakter haritada doğar doğmaz başlangıç paketlerini ardı ardına teslim eder:
- **`S->C AC 23 Sub 6` (Eşya Verme - 19 Paket):**
  - Format: `[23, 6, item_id (uint16_LE), count (uint16_LE), 27 zero bytes padding]` (33 Bayt).
  - Örnek Hex: `17 06 F6 84 01 00 00 00 ...` (Item ID `34038` - Başlangıç hediyeleri, potlar ve ekipmanlar).
- **`S->C AC 23 Sub 140`:** Karakterin ilk giriş zaman damgası (OA Date Float).
- **`S->C AC 23 Sub 160`:** Yeni oyuncu hediye kutusu UI tetikleyicisi.

---

### C. Gemi Sinematiği ve Kaptan ile İlk Konuşma (AC 20 / 0x14 & AC 186 / 0xBA)
Ocean Star yolcu gemisinde Kaptan (NPC ID `10`) ile yapılan diyalog akışı:
1. **Kaptana Tıklama (`C->S AC 20 Sub 1` - 13 kez):**
   - Format: `[20, 1, npc_id=0x000A (uint16_LE)]` (4 Bayt).
2. **Kaptan Diyalog Açılışı (`S->C AC 20 Sub 1` - 28 kez):**
   - Format: `[20, 1, step, talk_id=95660]` (18 Bayt).
   - Metin (`Talk.dat`): *"Hello, I'm captain here. Welcome to Ocean Star..."*
3. **Diyalog İlerleme / "Devam" Butonu (`C->S AC 20 Sub 6` - 51 kez):**
   - Format: `[20, 6]` (2 Bayt) — Oyuncu diyalog kutusundaki "Next/İleri" butonuna tıklar.
4. **Sonraki Cümle Promptu (`S->C AC 20 Sub 10` - 22 kez):**
   - Format: `[20, 10]` (2 Bayt) — Sunucu sonraki metne geçilmesini emreder.
   - İkinci Metin (`Talk.dat`): *"Contact our service staff anytime if you have any question..."* (Talk ID 95661).
5. **Görev Seçeneği Seçimi (`C->S AC 20 Sub 9` - 4 kez):**
   - Format: `[20, 9, option_index]` (3 Bayt) — Görev teklifini onaylama.
6. **Diyalog Kapanışı (`S->C AC 20 Sub 8` - 18 kez):**
   - Format: `[20, 8]` (2 Bayt) — Konuşma penceresini kapatır.

---

### D. Görev Kabulü ve Günlük Kaydı (AC 24 / 0x18 & AC 39 / 0x27)
1. **Görevin Kabul Edilmesi (`S->C AC 24 Sub 1` - 2 kez):**
   - **Hex:** `18 01 08 2F 01`
   - **Çözümleme:** `Action Code = 24`, `Sub = 1`, `Quest ID = 0x2F08` (12040), `Step = 1`.
   - İstemciye görevin başarıyla alındığını ve aktif görevler arasına eklendiğini bildirir.
2. **Ara Hedef / Tetikleyici Güncellemesi (`S->C AC 24 Sub 4` - 2 kez):**
   - **Hex:** `18 04 08 2F`
   - **Çözümleme:** `Quest ID = 12040` ara hedefi işaretlendi (gemi kazası tetikleyicisi).
3. **Görev Günlüğü Durum Güncellemesi (`S->C AC 24 Sub 5` - 14 kez):**
   - **Hex:** `18 05 35 00 00`
   - **Çözümleme:** Günlük girdisi güncellendi ve istemcinin görev bildirim paneli yenilendi.
4. **F10 Görev Defteri Senkronizasyonu (`S->C AC 39 Sub 9`):**
   - 381 baytlık tam görev ağacı senkronizasyon paketi.

---

### E. Gemi Batışı, Sahil Işınlanması ve Yerden Eşya Toplama
1. **Harita Değişimi (`S->C AC 6 Sub 2` & `C->S AC 6 Sub 1`):**
   - Gemi içinden Kelan Sahili'ne (`Map 10001`) geçiş onayı.
2. **Sahilde Yerden Eşya Toplama (`AC 23 Sub 2`):**
   - `C->S AC 23 Sub 2`: `[23, 2, ground_item_slot (2B)]` (4 Bayt) — Sahildeki eşyaya tıklama.
   - `S->C AC 23 Sub 2`: `[23, 2, result=1]` (5 Bayt) — Eşyanın envantere alındığı ve haritadan silindiği bildirimi.
3. **Sahilde Çadır ve Diğer Oyuncu Varlıkları (`AC 62` & `AC 4`):**
   - Sahilde kurulu olan çadırların mobilya kalp atışları (`AC 62 Sub 45`) ve oyuncu hareketleri (`AC 5 Sub 1/0`).
