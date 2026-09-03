# Web Servisleri (Web Services)

Bu doküman, Wonderland Online Python sunucusunda yer alan web tabanlı kayıt (Web Registration) sunucusunu ve modern yönetim arayüzü mimarisini detaylandırır.

---

## 1. Yönetim Mimarisi (Desktop GUI Suite)

Web tabanlı admin paneli yerine, tüm sunucu yönetimi, canlı GM araçları, karakter düzenleyici ve ban sistemleri **Modern Desktop Administrator Control Suite** (`server/gui_app.py`) bünyesinde merkezi ve yüksek performanslı CustomTkinter arayüzü üzerinden yürütülmektedir. Ayrıntılar için [administrator_gui_suite.md](administrator_gui_suite.md) dokümanına bakınız.

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
