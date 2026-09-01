# aLogin.exe Master Function Index & Reverse Engineering Catalog

Bu doküman, Wonderland Online **`aLogin.exe`** binary dosyasında bulunan 9,106 fonksiyonun ana alt sistemlerine göre referans indeksidir.

---

## 1. Ağ & Protokol İletimi (Network & Netcode)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_000799c8`** | `88312 - 88330` | `void(int socket_ctx)` | Asenkron TCP soketi başlatır (`FIONBIO`), sunucuya bağlanır. |
| **`FUN_00436178`** | `427019 - 427053` | `bool(int port)` | Port doğrulama (`25221` veya `25620`). |
| **`FUN_0007a284`** | `88800 - 88879` | `void(int *s, char *buf, int len)` | Non-blocking soket veri okuma (`recv`). |
| **`FUN_0012479c`** | `130372 - 130445` | `void(int s, int buf, uint len)` | Ham veri gönderimi (`send`), hata yakalama. |
| **`FUN_002d6994`** | `283131 / ~200 çağrı` | `int(void *s, uint op, uint sub, ...)` | **Merkezi Paket İnşa ve Gönderim Motoru**. |
| **`FUN_002f21b8`** | `283137 / çağrılar` | `void(void *s, uint op, void *buf)` | Tamponlu paket gönderim yardımcısı. |
| **`FUN_0031ecf0`** | `291503 - 292576` | `void(int *ctx, int pkt)` | Gelen paket ana dağıtım motoru (39 `switch-case`). |
| **`FUN_0041ee94`** | `412750 - 413147` | `void(int *ctx, int pkt)` | Alt seviye paket dağıtım motoru (33 `switch-case`). |

---

## 2. Giriş, Sunucu & Karakter Yönetimi (Auth & Character)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_0032f674`** | `299311 - 299528` | `void(undefined4 ui, int idx)` | `SERVER.INI` dosyasını tarayarak sunucu listesini yükler. |
| **`FUN_0033c310`** | `303177 - 303242` | `void(int *ctx, int pkt)` | Giriş sonucunu işler (`0x01` başarılı, `0x02` Pwd error). |
| **`FUN_0014c114`** | `146882 - 147065` | `void(int ui, int pkt)` | Sunucudan gelen 21 kanallık listeyi ayrıştırır. |
| **`FUN_0022fcf4`** | `224848 - 225579` | `void(int *form, int pkt)` | 4 Karakter yuvasını, isim, seviye ve elementlerini yükler. |
| **`FUN_001a3f68`** | `178104 - 178141` | `void(int p1, int p2)` | Rebirth sınıflarını yükler (Warrior, Knight, Killer, Priest, Wit, Seer). |
| **`FUN_0022d4f0`** | `223800 - 224100` | `void(int form)` | Karakter silme ve 6 haneli PIN denetimi. |

---

## 3. Savaş Motoru & Yetenekler (Combat & Skills)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_002b5630`** | `272150 - 272262` | `int*(int *form, int actor)` | `Form_BattleSkill_1` yetenek penceresini açar. |
| **`FUN_002591f8`** | `237897 - 237968` | `int*(int *form, int npc)` | `form_npcSkillTree` yetenek öğrenme arayüzünü açar. |
| **`FUN_002a6ef0`** | `265977 - 266903` | `void(int *ctx, int act)` | Savaş yeteneği ve hızlı yuva kontrolü (`Skill only for battle`). |
| **`FUN_003e4b60`** | `379471 - 379723` | `void(int *ctx, int pkt)` | Savaş turları, kombolar ve aksiyon dağıtıcısı (59 case). |
| **`FUN_001a4d00`** | `178523 - 178648` | `void(int p1, int p2)` | Battle Royale 4F etkinlik savaş yöneticisi. |
| **`FUN_001a72e8`** | `180335 - 180561` | `void(int p1, int p2)` | Truva Lonca Savaşı (Trojan War) yöneticisi. |

---

## 4. Evcil Hayvan & Binek (Pet & Companion)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_003de310`** | `376389 - 376408` | `void(int player)` | Aktif pet çağırma / gizleme bayrağını (`0x1efc`) günceller. |
| **`FUN_003e9898`** | `382158 - 384691` | `byte(int pet, int state)` | **Pet AI Karar Ağacı** (92 case, modlar 0..7, 0x2F..0x35). |
| **`FUN_003cdd00`** | `367049 - 367775` | `void(int pet, int skill)` | Pet yetenek animasyonları ve efektleri (41 case). |
| **`FUN_0013d794`** | `141887 - 142153` | `void(int p1, int p2)` | Pet savaş (`Pet in battle!`) ve binek (`Pet is mounted!`) kısıtlamaları. |
| **`FUN_00344974`** | `306173 - 306517` | `void(int pet)` | Pet satış ve Pet Kafesi (`Pet Cage`) takas doğrulaması. |

---

## 5. Envanter, Simya & Ekonomi (Inventory, Forging & Economy)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_0044651c`** | `437214 - 439407` | `void(int *inv, int item)` | **Ana Eşya Kullanım Dağıtıcısı** (46 case: iksir, zırh, mobilya, binek). |
| **`FUN_00267ea8`** | `243792 - 243995` | `void(int item, int token)`| Ekipman dövme (Forging) ve jeton/puan harcama. |
| **`FUN_002a1f14`** | `262687 - 264666` | `void(int *trade, int pkt)`| İki aşamalı Güvenli Takas (P2P Safe Trade) yuva eşleştirici. |
| **`FUN_001d9f08`** | `200599 - 200758` | `void(int target)` | Oyuncu Pazar Tezgahı (`form_stall`) ve kilit denetimi. |

---

## 6. Görev & Diyalog Motoru (Quest & Dialogue)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_00314380`** | `286844 - 286867` | `void(int *form)` | Görev Günlüğü (`form_taskview_1`) liste talebi (`Opcode 39 / Sub 1`). |
| **`FUN_00417380`** | `408264 - 408302` | `void(int *ctx, int p2)` | Takım içi görev paylaşımı (`Opcode 39 / Sub 2`). |
| **`FUN_0041a0a8`** | `409935 - 409963` | `void(int *ctx)` | Görevi bırakma (`Abandon Quest` - `Opcode 39 / Sub 7`). |
| **`FUN_0041894c`** | `409068 - 409078` | `void(int *ctx)` | Lonca üye görev listesi (`Opcode 39 / Sub 10-12`). |
| **`FUN_003f9318`** | `390657 - 390668` | `void(int task_id)` | Görev takip HUD sabitleme (`Opcode 39 / Sub 50`). |
| **`FUN_003f9680`** | `390763 - 390774` | `void(int task_id)` | Görev takip HUD kaldırma (`Opcode 39 / Sub 51`). |

---

## 7. Mini Oyunlar & Etkinlikler (Mini-Games & Events)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_003e175c`** | `378491 - 378831` | `void(int *ctx, int pkt)` | Şans Çarkı (Lucky Draw - Opcode 75) & Çifte EXP duyuruları (86 case). |
| **`FUN_0010e218`** | `119523 - 119760` | `int(int *ui, int pkt)` | UFO Catcher Pençe Makinesi (Opcode 13) & Gobang tahtası (44 case). |

---

## 8. Grafik & Ses Motoru (Graphics & Audio)

| Fonksiyon Adı | Adres / Satır | Dönüş & İmzası | Açıklama |
| :--- | :--- | :--- | :--- |
| **`FUN_0046f928`** | `457636 - 458310` | `void(int *surf, int spr)` | DirectDraw yüzey çizici ve sprite blitter (94 case). |
| **`FUN_0049c3bc`** | `482841 - 484254` | `int(int *surf, int pal)` | Hava durumu ve yüzey palet efektleri (159 case). |
| **`FUN_0049f5e8`** | `485343 - 485565` | `void(int *surf, int eff)` | Dinamik aydınlatma ve parlaklık ayarları (70 case). |
| **`FUN_00115a38`** | `123752 - 123964` | `int(int snd_id)` | DirectSound WAV efekt oynatıcı (100 case). |
| **`FUN_0016ea20`** | `153989 - 154103` | `int(int bgm_id)` | Harita arka plan müziği (BGM) döngü yöneticisi (43 case). |
