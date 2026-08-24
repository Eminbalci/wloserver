# Veritabanı Yönetimi (Database Management)

Bu doküman, Wonderland Online sunucusunun SQLite veritabanı yönetim katmanını (`server/database.py` modülü) ve veri şemalarını detaylandırır.

## Veritabanı Şemaları

Sunucu, oyuncu hesaplarını, karakterleri ve sosyal ilişkileri depolamak için varsayılan olarak `wlo_server.db` dosyasını kullanır. Ayrıca statik oyun nesneleri ve portalları çözmek için `server/ServerDataBase.db` dosyasından okuma yapar.

### 1. `users` Tablosu
Kullanıcı hesap bilgilerini depolar.
- `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): Benzersiz kullanıcı ID'si.
- `username` (TEXT, UNIQUE, NOT NULL): Küçük harfe dönüştürülmüş benzersiz kullanıcı adı.
- `password` (TEXT, NOT NULL): Düz metin olarak saklanan şifre.
- `char_delete_code` (TEXT, DEFAULT ''): Karakter silme işlemi için kullanılan güvenlik kodu.
- `is_gm` (INTEGER, DEFAULT 0): Hesabın Game Master yetkisini belirtir (`1` ise GM).
- `banned` (INTEGER, DEFAULT 0): Hesabın yasaklanma durumunu belirtir (`1` ise yasaklı).

### 2. `characters` Tablosu
Karakterlerin oyun içi durumunu ve envanterini saklar.
- `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): Benzersiz karakter ID'si.
- `user_id` (INTEGER, NOT NULL): `users.id` tablosuna referans (Foreign Key).
- `slot` (INTEGER, NOT NULL): Karakterin kullanıcı slotu (1 veya 2).
- `name` (TEXT, UNIQUE, NOT NULL): Benzersiz karakter adı.
- `level` (INTEGER, DEFAULT 1): Karakter seviyesi.
- `element` (INTEGER, DEFAULT 0): Karakter elementi (0: Yok, 1: Toprak, 2: Su, 3: Ateş, 4: Rüzgar).
- `hp`, `max_hp`, `sp`, `max_sp` (INTEGER): Can ve büyü puanları.
- `gold` (INTEGER, DEFAULT 0): Altın miktarı.
- `map_id` (INTEGER, DEFAULT 10017): Karakterin son bulunduğu harita ID'si.
- `x`, `y` (INTEGER): Karakterin harita koordinatları.
- `body`, `head` (INTEGER): Karakter vücut ve kafa modeli ID'leri.
- `hair_color`, `skin_color`, `clothing_color`, `eye_color` (INTEGER): Karakter kozmetik renkleri.
- `reborn` (INTEGER, DEFAULT 0): Reborn durumu (1 veya 0).
- `job` (INTEGER, DEFAULT 0): Karakter mesleği/sınıfı (Killer, Warrior, Knight, Mage, Priest).
- `equipments` (TEXT, DEFAULT '[]'): Kuşanılmış eşyaların JSON formatında saklanan listesi.
- `inventory` (TEXT, DEFAULT '[]'): Envanterdeki eşyaların JSON listesi.
- `skills` (TEXT, DEFAULT '[]'): Karakter yeteneklerinin ve seviyelerinin JSON listesi.
- `quests` (TEXT, DEFAULT '[]'): Tamamlanan ve aktif görevlerin durumunu içeren JSON listesi.
- `pets` (TEXT, DEFAULT '[]'): Karakterin sahip olduğu evcil hayvanların listesi.
- `potential` (INTEGER, DEFAULT 0): Karakter potansiyeli.
- `points` (INTEGER, DEFAULT 0): Item Mall veya stat dağıtım puanı.
- `skill_points` (INTEGER, DEFAULT 0): Dağıtılmamış yetenek puanları.
- `chat_channels_mask` (INTEGER, DEFAULT 31): Aktif sohbet filtreleri bitmaskesi.
- `str`, `con`, `int`, `wis`, `agi` (INTEGER, DEFAULT 10): Temel nitelik statları.
- `exp` (INTEGER, DEFAULT 0): Birikmiş tecrübe puanı.

### 3. `friends` Tablosu
Oyuncuların arkadaşlık ilişkilerini saklar.
- `CharID1` (INTEGER, NOT NULL): Davet eden veya arkadaş ekleyen karakterin ID'si.
- `CharID2` (INTEGER, NOT NULL): Eklenen karakterin ID'si.
- `AddedDate` (TEXT, NOT NULL): Arkadaş ekleme tarihi.

---

## Sınıf ve Metot Tanımları

### `DatabaseManager` Sınıfı

`DatabaseManager(db_path: str = "wlo_server.db")`

Veritabanı bağlantılarını, tablo oluşturmayı ve veri manipülasyon işlemlerini yürütür.

#### Metotlar

##### `get_connection() -> sqlite3.Connection`
Yeni bir veritabanı bağlantısı oluşturur ve `Row` fabrikasını etkinleştirir.
- **Parametreler**: Yok.
- **Dönen Değer**: `sqlite3.Connection` nesnesi.

##### `init_db()`
Veritabanı tabloları mevcut değilse bunları oluşturur. Eksik sütunları (`is_gm`, `banned`, `exp`, `pets` vb.) dinamik olarak ekler.
- **Parametreler**: Yok.
- **Dönen Değer**: `None`.

##### `register_user(username: str, password: str) -> tuple`
Kullanıcıyı sisteme kaydeder.
- **Parametreler**:
  - `username` (str): Kullanıcı adı.
  - `password` (str): Şifre.
- **Dönen Değer**: `(user_id: int, error_message: str)`. Kayıt başarılıysa `(user_id, "")`, aksi halde `(None, "Hata Mesajı")`.
- **İstisnalar**: `sqlite3.IntegrityError` (Kullanıcı adı zaten varsa).
- **Uç Durumlar (Edge Cases)**: `username` parametresi 3 karakterden kısa veya boş olamaz.

##### `verify_user(username: str, password: str) -> dict`
Kullanıcı kimlik bilgilerini ve yasak durumunu doğrular.
- **Parametreler**:
  - `username` (str): Kullanıcı adı.
  - `password` (str): Şifre.
- **Dönen Değer**: Kullanıcı detaylarını içeren `dict` veya `None`. Karakter slot durumları (slot 1 ve 2) sözlükte döner.
- **Uç Durumlar (Edge Cases)**:
  - Kullanıcı yasaklıysa (`banned == 1`), `{"id": 0, "banned": True}` döner.

##### `create_character(user_id: int, slot: int, name: str, body: int, head: int, hair_color: int, skin_color: int, clothing_color: int, eye_color: int, element: int, cipher: str, str_val: int = 10, con_val: int = 10, int_val: int = 10, wis_val: int = 10, agi_val: int = 10) -> int`
Yeni bir karakter oluşturarak başlangıç ekipmanları ve yeteneklerini tanımlar.
- **Parametreler**: Karakter görünüm, isim, element ve başlangıç stat değerleri.
- **Dönen Değer**: Oluşturulan karakterin benzersiz `id` değeri (başarısızlık durumunda `0`).
- **Detaylar**:
  - Karakter kafa (`head`) ve vücut (`body`) modeline göre başlangıç ekipman setini otomatik atar.
  - Karakter elementine göre fiziksel ve büyüsel başlangıç yeteneklerini (`Rock Attack`, `Ice Attack`, `Flame Attack`, `Wind Attack` vb.) ekler.
- **İstisnalar**: `sqlite3.IntegrityError` (Aynı slotta karakter varsa veya isim alınmışsa).

##### `get_character_by_id(char_id: int) -> dict`
Karakter verilerini veritabanından okur ve JSON alanları Python nesnelerine dönüştürür.
- **Parametreler**: `char_id` (int).
- **Dönen Değer**: Karakter verilerini barındıran `dict` veya `None`.
- **Edge Cases**: `inventory`, `equipments`, `skills`, `quests`, `pets` alanları boş veya null ise varsayılan listeler yüklenir.

##### `save_character(char_id: int, data: dict)`
Karakterin güncel konum, envanter, yetenek ve stat verilerini veritabanına kaydeder.
- **Parametreler**:
  - `char_id` (int): Karakter ID'si.
  - `data` (dict): Karakter özelliklerini barındıran sözlük.
- **Dönen Değer**: `None`.
- **Detaylar**: JSON alanları (`equipments`, `inventory`, `skills`, `quests`, `pets`) otomatik olarak JSON stringine serialize edilir.
