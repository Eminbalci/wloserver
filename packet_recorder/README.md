# 🎮 Wonderland Online - Paket Kaydedici ve Oturum Analizörü (Packet Recorder)

Bu sistem, Wonderland Online oynarken istemci (Client) ve sunucu (Server) arasındaki tüm ağ paketlerini çift yönlü (`C->S` ve `S->C`), zaman damgalı, XOR-173 çözümlü ve insan tarafından okunabilir olarak kaydetmek için tasarlanmıştır.

Sunucu kodlarından bağımsız, tamamen harici ve taşınabilir bir modüldür.

---

## 🚀 Hızlı Başlangıç (Nasıl Kullanılır?)

### 1. Çalıştırma
Aşağıdaki yöntemlerden biriyle kaydediciyi başlatabilirsiniz:
- **Görsel Arayüz (Önerilen)**: `start_recorder_gui.bat` veya ana dizindeki `start_packet_recorder.bat` dosyasına çift tıklayın (veya terminalde `python -m packet_recorder.main` çalıştırın).
- **Komut Satırı (CLI)**: `start_recorder_cli.bat` dosyasına çift tıklayın (veya `python -m packet_recorder.main --cli`).

### 2. Kayda Başlama & Oyuna Girme
1. Arayüz açıldığında:
   - **Mode**: `Proxy Bridge (Recommended)`
   - **Target IP**: Bağlanmak istediğiniz sunucunun IP adresi (Yerel sunucu ise `127.0.0.1`, resmi veya harici sunucu ise o sunucunun IP'si).
   - **Port**: `6414`
2. **▶ Start Recording** butonuna basın.
3. Oyunu (`aLogin.exe` / `aMain.exe`) başlatın ve normal şekilde oynayın.

### 3. Oynarken Not / Etiket (Bookmark) Ekleme ⭐ (Çok Önemli!)
Oyunda belirli bir işlem yaparken (örneğin bir NPC'ye tıkladığınızda, savaşa girdiğinizde, eşya aldığınızda):
- Arayüzdeki **"Add In-Game Note / Bookmark"** kutusuna ne yaptığınızı yazıp **Enter**'a basın (veya CLI'da `tag npc robinson` yazın).
- Bu not, o anda kaydedilen paketlerin içerisine etiket olarak işlenir.
- Böylece dosyaları bize ilettiğinizde, hangi paketin hangi oyuniçi eyleme denk geldiğini 100% kesinlikle anlayabiliriz!

### 4. Kaydı Bitirme ve Paketleri Verme
1. Oynamanız bittiğinde **⏹ Stop Recording** butonuna basın.
2. **📁 Open Folder** butonuna tıklayın.
3. Açılan `packet_recorder/recordings/` klasöründeki dosyaları (özellikle `.jsonl` ve `.log` dosyalarını) kopyalayıp asistana verin.

---

## 📁 Üretilen Dosya Formatları

Her kayıt oturumu için `packet_recorder/recordings/` klasöründe 4 dosya oluşturulur:

1. **`session_YYYYMMDD_HHMMSS.jsonl`**:
   - Her satırda tek bir pakete ait JSON nesnesi yer alır.
   - Zaman damgası, milisaniye cinsinden geçen süre, yön (`C->S` veya `S->C`), Opcode (`action_code`), çözülmüş HEX yükü, ASCII dökümü ve etiketleri içerir.
   - Yapay zeka ve analiz araçları için en ideal formattır.

2. **`session_YYYYMMDD_HHMMSS_readable.log`**:
   - İnsan gözüyle kolayca okunabilecek kart formatında log dökümüdür:
     ```text
     [00:00:12.450s] #00021 | C->S | AC 20 (NPC Interaction / Dialogue Trigger) Sub 1 | 8 bytes
       Tag: [Clicked Robinson NPC]
       Fields: click_id=10042
       HEX:   14 01 2A 27 00 00 00 00
       ASCII: ..*'....
     ```

3. **`session_YYYYMMDD_HHMMSS.pcap`**:
   - Wireshark ile incelenebilen standart ağ yakalama dosyasıdır.

4. **`session_YYYYMMDD_HHMMSS_summary.json`**:
   - Oturumun özet istatistiklerini, süre, paket sayısı, yön dağılımı ve opcode frekanslarını barındırır.

---

## ⚙️ Parametreler ve Komut Satırı Seçenekleri

```bash
# GUI modunda başlatma
python -m packet_recorder.main

# CLI modunda başlatma
python -m packet_recorder.main --cli

# Farklı bir hedef sunucu ve port için proxy
python -m packet_recorder.main --cli --target-host 192.168.1.50 --target-port 6414

# Pasif Ağ Dinleme (Sniffer) modu (Npcap / Scapy)
python -m packet_recorder.main --cli --mode sniffer
```
