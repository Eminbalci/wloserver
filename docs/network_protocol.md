# Ağ Protokolü ve Paket Yapısı (Network Protocol & Packet Structure)

Bu doküman, Wonderland Online istemcisi (`aLogin.exe`) ile Python sunucusu arasındaki ağ paketlerinin yapısını, asenkron soket yönetimini ve `server/network.py` modülündeki sınıf/metotları detaylandırır.

## Paket Yapısı (Packet Format)

Her bir ağ paketi binary (ikili) formatta iletilir ve sunucuya gönderilmeden veya istemciye yayınlanmadan önce XOR şifreleme algoritması ile maskelenir.

Ham (şifrelenmemiş) bir paketin genel düzeni şu şekildedir:

| **Alan Adı** | **Veri Tipi** | **Uzunluk (Bayt)** | **Açıklama** |
| :--- | :--- | :--- | :--- |
| **SIGNATURE** | `uint16` (Little Endian) | 2 | Paket imza sabitidir (`0x44F4` veya `17652`). |
| **LENGTH** | `uint16` (Little Endian) | 2 | Payload (paket içeriği) uzunluğu. |
| **PAYLOAD** | `bytes` | `LENGTH` kadar | Asıl veri içeriği (Opcode, Alt-Opcode ve parametreler). |

### XOR Şifreleme (XOR Encryption)
Paketler ağ üzerinde gönderilirken imza, uzunluk ve payload dahil tüm paket bayt bazında XOR işlemine tabi tutulur:
- **Varsayılan Sunucu XOR Anahtarı**: `173` (Dec) / `0xAD` (Hex).
- **Client Save XOR Anahtarı**: `121` (Karakter konfigürasyon kayıtları `save.dat` dosyalarının maskelenmesinde kullanılır).

---

## Modül Sınıfları ve API Referansları

### `xor_crypt` Fonksiyonu
`xor_crypt(data: bytes, key: int = 173) -> bytes`
Verilen bayt dizisini belirtilen anahtar ile XOR'lar.
- **Parametreler**:
  - `data` (bytes): Şifrelenecek veya şifresi çözülecek ham veri.
  - `key` (int): XOR anahtarı (Varsayılan: `173`).
- **Dönen Değer**: `bytes` (XOR'lanmış veri).

---

### `PacketReader` Sınıfı
İstemciden gelen veya çözümlenmiş paket verilerini okumak için yardımcı sınıftır.

`PacketReader(data: bytes)`
- **Parametreler**: `data` (bytes) - Ham paket payload bayt dizisi.

#### Metotlar

##### `read_8() -> int`
Paketten 1 baytlık işaretsiz tam sayı okur ve offseti 1 artırır.
- **Dönen Değer**: `int` (0-255). Offset aşılırsa `0` döner.

##### `read_16() -> int`
Paketten 2 baytlık işaretsiz tam sayı (Little Endian) okur ve offseti 2 artırır.
- **Dönen Değer**: `int` (0-65535). Offset aşılırsa `0` döner.

##### `read_32() -> int`
Paketten 4 baytlık işaretsiz tam sayı (Little Endian) okur ve offseti 4 artırır.
- **Dönen Değer**: `int`. Offset aşılırsa `0` döner.

##### `read_bool() -> bool`
Paketten 1 bayt okur, sıfırdan farklıysa `True`, sıfırsa `False` döner.
- **Dönen Değer**: `bool`.

##### `read_string() -> str`
Uzunluk öneki (1 bayt) olan bir ASCII karakter dizisi okur.
- **Dönen Değer**: `str`. Offset aşımı durumunda boş dize (`""`) döner.

##### `read_string_n() -> str`
Pakette kalan tüm baytları bir ASCII karakter dizisi olarak okur ve offseti paketin sonuna taşır.
- **Dönen Değer**: `str`.

##### `remaining_bytes() -> int`
Pakette henüz okunmamış bayt sayısını döner.
- **Dönen Değer**: `int` (kalan bayt adedi).

---

### `PacketWriter` Sınıfı
Sunucudan istemciye gönderilecek paketleri doğru binary formatta inşa etmek için kullanılır.

`PacketWriter()`
Tüm yazma metotları akıcı arayüz (fluent interface) yapısında olup `self` (PacketWriter) referansını geri döndürür.

#### Metotlar

##### `write_8(val: int) -> PacketWriter`
Buffer'a 1 baytlık değer ekler.
- **Parametreler**: `val` (int).

##### `write_16(val: int) -> PacketWriter`
Buffer'a 2 baytlık Little Endian tam sayı ekler (0-65535 sınırları içine kırpılır).
- **Parametreler**: `val` (int).

##### `write_32(val: int) -> PacketWriter`
Buffer'a 4 baytlık Little Endian tam sayı ekler.
- **Parametreler**: `val` (int).

##### `write_64(val: int) -> PacketWriter`
Buffer'a 8 baytlık Little Endian tam sayı ekler.
- **Parametreler**: `val` (int).

##### `write_bool(val: bool) -> PacketWriter`
Buffer'a boolean değeri (aktifse `1`, değilse `0` olarak 1 bayt) ekler.
- **Parametreler**: `val` (bool).

##### `write_string(val: str) -> PacketWriter`
Buffer'a önce karakter uzunluğunu (1 bayt) ardından ASCII kodlu metni yazar.
- **Parametreler**: `val` (str).

##### `write_string_n(val: str) -> PacketWriter`
Buffer'a uzunluk öneki olmadan düz ASCII kodlu metin yazar.
- **Parametreler**: `val` (str).

##### `write_bytes(val: bytes) -> PacketWriter`
Buffer'a doğrudan ham bayt dizisi ekler.
- **Parametreler**: `val` (bytes).

##### `build() -> bytes`
Paket buffer içeriğine imza ve uzunluk header bilgilerini ekler, veriyi XOR anahtarı (`173`) ile şifreleyerek ağ üzerinden gönderilmeye hazır hale getirir.
- **Dönen Değer**: `bytes` (şifrelenmiş paket paketi).

---

## İstemci Paket Yönlendiricileri (Main Dispatchers)

İstemci tarafında decompile edilen kodlardaki paket dağıtımı iki ana dispatcher fonksiyonu üzerinden yürütülür:
1. **`FUN_00115a38` (Main Dispatcher 1)**: Paketlerin ilk baytındaki OPCODE değerini süzerek Chat (`0x02`), Movement (`0x06`), Combat (`0x0b`), Warp (`0x0c`), Friend (`0x0e`), Pet (`0x0f`), Interaction (`0x14`), Item (`0x17`), Trade (`0x19`), Quest (`0x27`), Battle (`0x32`) ve Login (`0x3f`) gibi sunucu işleyicilerine yönlendirir.
2. **`FUN_0010e218` (Main Dispatcher 2)**: Form ve arayüze yansıtılacak paket tiplerini ayrıştırır.
