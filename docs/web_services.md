# Web Servisleri (Web Services)

Bu doküman, Wonderland Online Python sunucusunda yer alan web tabanlı yönetim (Web Admin) ve kayıt (Web Registration) sunucularını detaylandırır.

---

## 1. Web Yönetim Paneli (Web Admin Dashboard)

Web Yönetim Paneli (`server/web_admin.py` modülü), yöneticilerin sunucuyu canlı olarak izlemelerini, bağlı oyuncuları yönetmelerini, drop tablolarını güncellemelerini ve sistem loglarını taramalarını sağlar.

### A. Sunucu Özellikleri
- **Varsayılan Port**: `8080` (Ana `main.py` dosyası üzerinden `0.0.0.0` IP'si ile başlatılır).
- **Kullanılan Kütüphane**: `aiohttp` (Asenkron HTTP Sunucusu).
- **Arayüz Tasarımı**: Inter ve JetBrains Mono yazı tiplerini kullanan, modern karanlık temalı (dark-mode), responsive bir HTML/CSS/JS tek sayfalık web uygulamasıdır.

### B. Sağlanan HTTP Uç Noktaları (Routes)

- **`GET /`**: Yönetim paneli ana arayüzünü döner (`handle_index`).
- **`GET /api/status`**: Canlı sunucu durumunu (çalışma süresi, CPU/RAM, bağlı oyuncu sayısı, DB boyutu) içeren JSON nesnesi döner.
- **`GET /api/players`**: Aktif bağlı olan oyuncuların listesini (Karakter ID, kullanıcı adı, seviye, harita konumu, GM yetkisi) döner.
- **`POST /api/player/action`**: Canlıdaki bir oyuncuya işlem uygulamak için kullanılır.
  - **Parametreler**: `{"char_name": str, "action": "kick" | "ban" | "mute" | "toggle_gm"}`
- **`GET /api/logs`**: Sunucunun son 100 log satırını döner (JetBrains Mono fontlu konsol terminal görünümünde).
- **`GET /api/db/tables`**: Statik oyun veritabanındaki tabloları listeler.
- **`POST /api/db/query`**: Seçilen bir veritabanı tablosundaki satırları filtrelemek veya aramak için kullanılır.
- **`POST /api/db/insert`**: Veritabanı tablolarına veya `drop_table.json` dosyasına yeni bir veri satırı eklemek için kullanılır.
- **`POST /api/db/delete`**: Tablolardan veya drop tablosundan satır silmek için kullanılır.
- **`GET /api/search/lists`**: Drop tablosuna kural eklerken arama yapılabilmesi için static canavar (`npc.json`), eşya (`items.json`) ve binek araçların listesini döner.

---

## 2. Web Kayıt Paneli (Web Registration Panel)

Web Kayıt Paneli (`server/web_registration.py` modülü), yeni oyuncuların sunucuda hesap oluşturabilmesi için basit ve güvenli bir arayüz sunar.

### A. Sunucu Özellikleri
- **Varsayılan Port**: `8081` (Ana `main.py` dosyası üzerinden `0.0.0.0` IP'si ile başlatılır).
- **Kullanılan Kütüphane**: `aiohttp`.
- **Arayüz Tasarımı**: Outfit yazı tipini kullanan, modern gradient arka planlı, responsive HTML form tasarımıdır.

### B. Sağlanan HTTP Uç Noktaları (Routes)

- **`GET /`**: Kullanıcı kayıt arayüzünü döner (`handle_index`).
- **`POST /api/register`**: Yeni kullanıcı kaydını veritabanına işler.
  - **Parametreler**: `{"username": str, "password": str}`
  - **Dönen Değer**: `{"status": "success" | "error", "message": str}`

### C. Doğrulama ve Güvenlik Kuralları (Validation & Security)

Kayıt uç noktasında aşağıdaki kontroller gerçekleştirilir:
1. Kullanıcı adı ve şifre alanlarının boş olup olmadığı denetlenir.
2. Kullanıcı adı uzunluğu **3 ile 15 karakter** arasında olmalıdır.
3. Şifre uzunluğu **4 ile 20 karakter** arasında olmalıdır.
4. Girilen kullanıcı adı küçük harflere (`lower()`) dönüştürülerek veritabanında `users` tablosunda `username UNIQUE` kısıtlamasına göre kontrol edilir. Kullanıcı adı zaten mevcutsa kayıt reddedilir.
5. İstisnalar yakalanarak loglanır ve kullanıcıya anlamlı hata mesajları döndürülür (`sqlite3.IntegrityError` vb.).
