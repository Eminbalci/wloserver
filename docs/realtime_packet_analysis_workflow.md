# Wonderland Online Gerçek Zamanlı Paket Dinleme ve Protokol Çözümleme İş Akışı (Real-Time Packet Analysis & Protocol Workflow)

Bu doküman, Wonderland Online oynanırken istemci (`aLogin.exe`) ile sunucu arasındaki ağ trafiğinin anlık olarak dinlenmesi, şifresinin çözülmesi, eylemlerin paketlerle eşleştirilerek protokol yapısının otonom olarak öğrenilmesine ilişkin teknik metodolojiyi açıklar.

---

## 1. Mimari ve Ağ Katmanı

Wonderland Online istemcisi standart TCP soketleri üzerinden (`ws2_32.dll`) iletişim kurar. Bağlantı portları ve paket yapısı şu şekildedir:

- **Hedef Portlar:** `25221`, `25620`, `6414`, `6415`, `6416`, `6500`
- **Paket Başlığı (Header):** 4 Bayt (Little-Endian)
  - `Signature (2 Bayt):` `0x44F4` (Decimal: `17652`)
  - `Length (2 Bayt):` Payload (paket gövdesi) bayt uzunluğu.
- **XOR Maskeleme:** Ham TCP veri akışının tamamı `173` (`0xAD`) anahtarı ile bayt bazında maskelenmiştir.
  $$\text{Byte}_{\text{decrypted}} = \text{Byte}_{\text{raw}} \oplus 173$$

---

## 2. Otonom Paket Analiz ve Öğrenme Döngüsü

```
[Kullanıcı Oyunda Eylem Yapar] (Örn: Çanta Açma, NPC Tıklama, Yetenek Kullanımı)
                 │
                 ▼
[Canlı Dinleme (Sniffer)] ---> Scapy / Npcap ile aLogin.exe TCP trafiğini yakalar
                 │
                 ▼
[XOR 173 Çözümleme] ---------> 0x44F4 sihirli başlık ve paket boyutu ile çerçeveler
                 │
                 ▼
[Eylem-Zaman Eşleştirmesi] --> Eylemin yapıldığı saniyedeki C->S ve S->C paketlerini izole eder
                 │
                 ▼
[Decompile Kod Taraması] ----> aLogin.exe.1.c içindeki FUN_002d6994 ve dispatcher'dan değişken tiplerini bulur
                 │
                 ▼
[Handler ve Docs Üretimi] ---> server/handlers/ altına yeni opcode fonksiyonu ve docs/ altına teknik doküman eklenir
```

---

## 3. `tools/live_packet_sniffer.py` Kullanım Parametreleri

Yeni geliştirilen [tools/live_packet_sniffer.py](file:///D:/GitHub/Wonderland%20Online/tools/live_packet_sniffer.py) aracı hem canlı dinleme hem de çevrimdışı `.pcap` / `.pcapng` analizini destekler:

### Parametreler:
- `--live`: Canlı ağ kartını dinleme modunu başlatır.
- `--pcap <dosya_yolu>`: Önceden kaydedilmiş `.pcap` veya `.pcapng` dosyasını inceler.
- `--duration <saniye>`: Canlı dinleme süresi (Varsayılan: 30s).
- `--limit <adet>`: Maksimum yakalanacak paket sayısı (Varsayılan: 100).
- `--tag "<eylem_tanimi>"`: Yakalanan paketleri kullanıcının gerçekleştirdiği oyun eylemi ile etiketler.
- `--out <json_yolu>`: Çözümlenen paketleri detaylı JSON yapısı olarak diske yazar.

### Canlı Dinleme Örneği:
```bash
python tools/live_packet_sniffer.py --live --duration 60 --tag "NPC Konusmasi ve Gorev Alma" --out logs/npc_quest.json
```

---

## 4. Paket Yapısının ve Alanlarının Çıkarılması (Field Inference)

Paket gövdesi (`Payload`) çözüldüğünde veri yapısı hiyerarşik olarak analiz edilir:

1. **Byte 0 (Action Code / Opcode):** Ana sistem kategorisi (Örn: `20` = NPC, `23` = Envanter, `53` = Savaş).
2. **Byte 1 (Sub-Action Code):** Alt komut (Örn: `AC 23 Sub 6` = Eşya verme, `AC 23 Sub 8` = Slot taşıma).
3. **Değişkenler (Little-Endian):**
   - 2 Bayt (`uint16_LE`): Eşya ID, Harita ID, Koordinat X/Y, Yetenek ID.
   - 4 Bayt (`uint32_LE`): Karakter ID / GUID, EXP, Gold miktarı.
   - Karakter Dizileri (Strings): 1 bayt uzunluk önekli veya null-terminated ASCII karakterler.

---

## 5. İstemci Kaynak Kodu ile Doğrulama (`aLogin.exe`)

Paket tespit edildikten sonra tersine mühendislik ile istemci kodundaki karşılığı doğrulanır:
- **Client -> Server Gönderimleri:** `aLogin.exe.1.c` dosyasında `FUN_002d6994(socket, AC, Sub, ...)` araması yapılır. Fonksiyon parametreleri ve aktarılan struct offsetleri incelenerek bayt sıralaması kesinleştirilir.
- **Server -> Client Yanıtları:** İstemcinin ana ağ işleyicisindeki switch-case blokları taranarak gelen verinin istemci UI veya durum değişkenlerine nasıl yazıldığı teyit edilir.

---

## 6. İstisnalar ve Özel Durumlar (Edge Cases)

- **Parçalanmış TCP Paketleri (Stream Fragmentation):** Tek bir TCP paketinde birden fazla WLO paketi bulunabilir veya tek bir WLO paketi iki TCP segmentine bölünebilir. `extract_packets_from_bytes` fonksiyonu kesilmemiş kalan baytları tamponda tutarak bir sonraki segmentle birleştirir.
- **Save Dosyası XOR Farkı:** Karakter ayarları (`save.dat`) için kullanılan XOR anahtarı `121`'dir; ağ paketleri için ise `173`'tür.
- **Yetki Gereksinimleri:** Canlı paket dinleme için Npcap sürücüsü ve yönetici (Administrator) terminal yetkisi gereklidir.
