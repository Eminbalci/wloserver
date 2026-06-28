# Wonderland Online Server

This repository contains a custom python-based server implementation for Wonderland Online. 

## Structure
- `start.bat` / `start.sh` - Launch scripts for the server
- `server/main.py` - Entry point
- `server/gameserver.py` - Core game server logic
- `server/database.py` - Database interactions
- `server/battle.py` - Battle mechanics and logic
- `server/network.py` - Network handling and packet processing
- `server/quest_manager.py` / `quests.py` - Quest system implementation

## Setup & Installation

The server includes all necessary baseline `data/` files (`eve.Emg`, `Compound2.dat`, `Skill.dat`) required to run out of the box.

1. **Clone this repository** to your local machine.
2. Make sure you have Python 3.8+ installed.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   - On Windows: Double click `start.bat` or run `python -m server.main`
   - On Linux/Mac: `./start.sh` or run `python3 -m server.main`

## Database
The server uses SQLite databases (`wlo_server.db` / `server/ServerDataBase.db`) to store player data, accounts, and static game state.

## Admin Commands
You can type these commands in the game chat to modify your character:
- `:warp <map_id> <x> <y>` - Teleport to a specific map and coordinates.
- `:item add <item_id> [amount]` - Add an item to your inventory.
- `:level <level>` - Set your character's level.
- `:stat <str> <con> <int> <wis> <agi>` - Set your base attributes.
- `:gold <amount>` - Set your gold.
- `:heal` - Fully restore HP and SP.
- `:element <0-4>` - Change your character's element (0: Earth, 1: Water, 2: Fire, 3: Wind, 4: None).
- `:skill <skill_id> [grade]` - Add or level up a skill.
- `:clear` - Clear all items from your inventory.
- `:propshop` - Open the property shop.

## Recent Fixes
- Fixed the Troll quest battle (NPC 17281). Adjusted the background to default, set the correct battle sprite ID using XOR encryption logic (25461 -> 4468), and updated the win map destination to Map 11035.
- Addressed skill logic initialization. Disabled default unlock logic to implement stat-based skill mechanics.
- Fixed a bug where given pets via Web Admin lost their level after a battle due to missing EXP initialization. Given pets now receive their correct cumulative EXP.
- Added elemental skill usage for monsters in PvE battles. Monsters now have a 30% chance to cast elemental skills instead of basic attacks.
- Added Vehicle giving button and management modal to the Web Admin UI.
- Fixed cave combat battle backgrounds (mapping map IDs >= 11000 to the correct cave background).
- Fixed combat NPC lookup for map NPCs (like Poisonous Ant) by adding a name-based fallback lookup via npc.json.
- Fixed a bug in `handle_11_combat.py` where NPC IDs were incorrectly shifted right by 8, preventing combat sprites from spawning.
- Corrected the Vehicle modal HTML classes in `web_admin.py` to fix rendering issues.
- Updated `extract_item_properties.py` to read local `data/Item.dat`.
- Implemented `server/handlers/handle_39_quest.py` to manage quest list requests, abandonment, and help invitations.
- Implemented `server/handlers/handle_25_trade.py` to manage player secure trades and companion trade invitations.
- Updated `server/handlers/handle_20_interaction.py` to support dialog option selection responses (subcmd 2/9).
- Updated `server/handlers/handle_23_items.py` to support street stall registration (subcmd 65), NPC store entry (subcmd 99), starting fishing (subcmd 53) and stopping fishing (subcmd 54).
- Updated `server/database.py`, `server/handlers/handle_63_login.py`, and `server/handlers/handle_2_chat.py` to implement a secure GM authority system (restricting in-game console commands to accounts with `is_gm = 1`, and implementing `:kick`, `:ban`, and `:mute` commands with overlay network packets).
- Updated `server/web_admin.py` to add one-click GM toggle buttons in both the Active Connected Players dashboard and the Accounts/Registered Users list, supporting instant online session promotion and offline DB modifications.
- Implemented `server/handlers/handle_43_team.py` to support group/party invites, acceptances, and departures.
- Updated `server/handlers/handle_50_battle.py` and `server/handlers/handle_39_quest.py` to gracefully mock and handle spectate battle requests, joint battle assistance requests, and guild list retrievals to prevent client hangs.
- Updated `server/database.py` and `server/gameserver.py` to support correct client XOR key `121` for `save.dat` configuration filename matching (e.g. `save119.dat` for character ID `14`).
- Updated `server/gameserver.py` to change forced chat channel disable packets (`24, 5`) to active enable packets (`write_16(1)`) during `commence_login`, ensuring Local, Whisper, Team, Guild, and World chat channels are successfully initialized as ON.
- Implemented chat channel bitmask (`AC 33 Sub 3`) handling in `server/handlers/handle_33_settings.py` and persistent database mapping in `server/database.py` and `server/gameserver.py` (`chat_channels_mask` column) to save and restore player custom chat filters on login.
- Updated `server/gameserver.py` PVE battle counter-attacks to support 30% chance for monsters/NPCs to cast elemental magic skills, deducting SP, playing correct client skill animation IDs, and applying skill damage modifiers dynamically.


## Reverse Engineering



- findings.md, findings_game.md ve extract_funcs.py dosyaları silindi, yapılan analiz işlemleri geri alındı.

- aLogin.exe.1.c dosyasındaki önemli oyun ve paket fonksiyonları analiz edilerek bulgular.md dosyasına kaydedildi.

- aLogin.exe.1.c dosyasındaki oyun mekanikleriyle ilgili detaylı paket ve fonksiyon bilgileri analiz edildi, bulgular.md dosyasına eklenerek güncellendi.

- aLogin.exe.1.c dosyasındaki görev günlükleri, görev paketleri ve sub-opcode işlemleri analiz edilerek bulgular.md dosyasına eklendi.

- aLogin.exe.1.c dosyasındaki NPC tıklama mesafe doğrulamaları ve XOR 0x5209 (21001) şablon eşleştirme algoritmaları analiz edilip bulgular.md dosyasına aktarıldı.

- eve.Emg ve SQLite/JSON canavar veri yapıları incelenerek otomatik agresif savaş tetikleyen canavarların tespit edilme mekanizması analiz edildi, bulgular.md güncellendi.

- aLogin.exe istemci tarafındaki canavar veritabanı (Data\\odd.dat / odd_d01.dat) ve harita karşılaşma havuzu (user\\Map\\MapID_XOR_0x190c.MapData) okuma, çözme ve adım sayacı üzerinden savaş tetikleme algoritmaları analiz edilip bulgular.md dosyasına aktarıldı.

- aLogin.exe decompile kodlarından elde edilen özel istemci şablon ID eşleştirmeleri (0x908e, 0x9092, 0x9093, 0x9094, 0x9096) handle_20_interaction.py ve gameserver.py dosyalarına entegre edilerek NPC/Canavar çözümleme mekanizması güncellendi.

- Görev takip alt paketlerinin (Opcode 39, sub 10, 11, 16, 17, 19, 50, 51) arayüz kilitlenmelerini önleyecek ekoları handle_39_quest.py dosyasına entegre edildi.

- aLogin.exe decompile kodlarından ayıklanan oyun fonksiyonları (network, login, movement/map, combat, quest, pet ve trade) alogin_analyzed klasörü altında ayrı dosyalara açıklama ve paket bilgileriyle birlikte kaydedildi.

- alogin_analyzed klasöründeki C dosyaları, yürüme, simya, koordinat senkronizasyonu ve NPC etkileşim kontrollerini içeren ek fonksiyonlarla ve her fonksiyonun amacını, ofsetlerini ve paket opkodlarını adım adım detaylandıran Türkçe açıklama bloklarıyla güncellendi.

- İstemci analiz bulgularına göre server dosyalarındaki güvenlik açıkları kapatıldı: handle_20_interaction.py ve gameserver.py dosyalarına NPC tıklama mesafesi kontrolü (169 piksel), handle_11_combat.py dosyasına PK düello oyuncu mesafesi kontrolü (271 piksel) entegre edildi.

- PVP PK / düello mekanizmaları (gameserver.py: _start_pvp_battle, _resolve_pvp_turn, _end_pvp_battle ve handle_50_battle.py: dynamic expected_coords) düzgün bir şekilde sisteme eklendi ve entegre edildi.

- alogin_analyzed/network_packet.c dosyası güncellendi. WLO istemcisinde paket gönderme, alma, kuyruğa ekleme, asenkron okuma/yazma işçi döngüleri ve MSG_PEEK kontrollerini yapan tüm 12 ağ I/O fonksiyonu detaylı Türkçe dokümantasyonuyla birlikte ayrıştırıldı.

- alogin_analyzed/network_packet.c dosyası güncellendi: İstemcinin ana ağ paket dağıtıcıları (FUN_00115a38 ve FUN_0010e218) de ayıklanarak ağ dosyasına entegre edildi.

- bulgular.md dosyası güncellendi. Yeni eklenen ağ dağıtıcıları ve sunucu tarafındaki PVP PK / mesafe doğrulama yöntemleri detaylıca dökümante edildi.

- bulgular.md güncellendi. İstemcideki tüm 23 adet OPCODE paket dağılım eşleşmeleri (OPCODE, Özellik adı, sunucu handler dosyaları, istemci dağıtıcısı) detaylı bir tablo halinde dökümante edildi.

- bulgular.md güncellendi. İstemcide tespit edilen gizli mekanikler (Evlilik, Çadır/Mobilya yerleşimi, Kaplıca/Hamam, Pet Reborn evrimleşme ve Kısayol sistemi) detaylarıyla dökümante edildi.

- bulgular.md güncellendi. İstemcideki ileri seviye yerleşik bot (Uzaktan Kumanda), Artı Basma (Forge), Pet Eğitim Oteli ve Posta kutusu sistem metotları analiz edilerek dökümante edildi.

- bulgular.md güncellendi. PVP Arena, Lonca fesih, Karnaval/Takım engelleri ve Pazar (Stall) kısıtlamaları dökümante edildi.

- bulgular.md güncellendi. DirectSound ses motoru, Lonca Kalesi kuşatmaları ve mini-oyun durum kısıtlamaları detaylandırıldı.

- bulgular.md güncellendi. Element tabanlı yetenek sınırlamaları, kısayol barı yetenek doğrulamaları ve Dark Spell genişleme paketi denetimi dökümante edildi.

- bulgular.md güncellendi. Nesne Market (Item Mall / NPC Shop) arayüz yapısı (Form_EightTwelve) ve bakiye puan yetersizliği doğrulamaları dökümante edildi.

- bulgular.md güncellendi. Çadır içi eşya dolabı, depo yerleşimi, geri dönüşüm makinesi limiti ve EXP Boost Buff durumları dökümante edildi.

- bulgular.md güncellendi. Taşıt garaj depolama (garage) doluluk ve sergileme sınırları ile montaj/crafting yarı-mamul limiti dökümante edildi.

- bulgular.md güncellendi. Güvenli Kilit (Secure Lock), Kara Liste (Blacklist), Savaş İzleyici (Spectator) ve Etkinlik Kuponu sistemleri detaylandırıldı.

- bulgular.md güncellendi. Hamam/Banyo (Bathing) kısıtlamaları, ocak/fırın yakıt doğrulamaları ve tavşan kostüm çizimleri dökümante edildi.

- bulgular.md güncellendi. İstemci ile sunucu arasındaki ağ isteklerinin cevap zaman aşımı (Response Timeout) iptal kontrol mekanizmaları dökümante edildi.

- bulgular.md güncellendi. Reborn Job sınıfları (Killer, Warrior, Knight, Mage, Priest) pasif bonus detayları dökümante edildi.

- bulgular.md güncellendi. Giriş sunucusu bağlantı hatası ve karakter şifre doğrulama sistemleri dökümante edildi.

- bulgular.md güncellendi. Yoldaş / Pet (Companion) harita tıklama ve diyalog etkileşim seçenekleri (Master soruları) dökümante edildi.

- bulgular.md güncellendi. Lonca (Guild) kurma kısıtlamaları, davet, ayrılma logları, kural duyuruları, müttefik kontrolü ve Guild List arayüzü dökümante edildi.

- bulgular.md güncellendi. Evcil hayvan dostluk puanı (Amity) sınırı (Amity 40 altı kısıtlamaları) dökümante edildi.

- bulgular.md güncellendi. Simya (Alchemy / Compound) birleştirme arayüzü ve Junior Alchemy yetenek kontrolleri dökümante edildi.

- bulgular.md güncellendi. Sohbet kanalları (Fısıltı, Takım, Lonca, GM) açma/kapama sınırları ve Direct/GM kanal etiketlemeleri dökümante edildi.

- bulgular.md güncellendi. Güvenli Takas (Secure Trade) durum engelleri, Non-tradeable etiketlemeleri ve Cancel deal bildirimleri dökümante edildi.

- bulgular.md güncellendi. Simya ve hammadde nitelik ID eşleştirmeleri (Material Type mapping tablosu) dökümante edildi.

- bulgular.md güncellendi. Karlı haritalardaki kar yağışı animasyon parçacıkları (icon_Snow1, icon_Snow2, icon_Snow3) efekt sistemi dökümante edildi.

- bulgular.md güncellendi. Binek atama (Btn_AssignRide_1) arayüz butonu ve evlilik öncesi gelin kıyafeti kontrolü (Bride needs to dress up) dökümante edildi.

- bulgular.md güncellendi. Item Mall mini oyunları çift ödül etkinliği duyuruları ve (SystemPromp): sohbet önekleri dökümante edildi.

- bulgular.md güncellendi. Element uyumsuz becerileri öğrenme kısıtlamaları (Earth/Water/Fire skill), su toplama mesafesi (Too far from water) ve element sırrı gereksinimleri dökümante edildi.

- bulgular.md güncellendi. Balık tutma esnasında üretim kısıtlamaları (Currently fishing) ve eylem engellemeleri (Fishing, can't act) dökümante edildi.

- bulgular.md güncellendi. Posta kutusu doluluk oran uyarı limitleri (Mailbox volume at 90%), silinen mektup bildirimleri (Letter removed) ve MsgMailBoxLog günlük hedefleri dökümante edildi.

- bulgular.md güncellendi. Çadır mobilyaları (<Furniture>), mobilya kapsülü ve banyo esnasındaki mobilya tamir kısıtlamaları dökümante edildi.

- bulgular.md güncellendi. 40. maddeye ulaşılacak şekilde grup kısıtlamaları (Can't do in team), Expand Map arayüzü, hayalet karakter animasyon durumları (icon_LD_GhostF), uzaktan kumanda bot eylem blokları ve Lonca kalesi savunma günlükleri dökümante edildi.

- bulgular.md güncellendi. 50 adet tam maddeye ulaşacak şekilde ışınlanma engelleri, demirci tamir masrafları, savaşta tamir yasağı, arkadaş silme onayı, Forgotten Scroll yetenek sıfırlama, level up duyuruları, durability run out kısıtlamaları ve PvP arena meydan okuma limitleri dökümante edildi.

- walkthrough.md güncellendi. 50 adet tam maddeye ulaşan istemci kod analizi özetlendi.

- bulgular.md güncellendi. Alınan ve gönderilen paketlerin bayt tabanlı detaylı protokol yapısı (Opcode 0, 2, 6, 8, 9, 11, 12, 14, 15, 20, 23, 25, 63) dökümante edildi.

- Sunucu güncellendi. handle_23_items.py dosyasına balıkçılık durum kontrolü, uzaktan kumanda kısıtlamaları ve donanılan eşya seviye limitleri entegre edildi. handle_9_char_creation.py dosyasına başlangıç stat puan sınırı (maksimum 5 puan) ve isim sınır doğrulaması eklendi.

- Sunucu güncellendi. handle_20_interaction.py dosyasına balıkçılık ve uzaktan kumanda esnasında etkileşim engeli, evlilik töreninde ise gelinlik giyme zorunluluğu (Bride needs to dress up) entegre edildi.

- Sunucu güncellendi. handle_2_chat.py GM beceri ekleme komutuna element kısıtlamaları (Earth/Water/Fire/Wind skill mismatched checks) eklendi.

- Sunucu güncellendi. handle_23_items.py dosyasına taşıt binme (sub 51), taşıt inme (sub 52) ve yakıt yükleme (sub 134) protokolleri entegre edildi.

- Bulgular dosyası (bulgular.md) ve Walkthrough dosyası (walkthrough.md) taşıt binme/yakıt/tamir (Only for Vehicles / Vehicle repaired) analiz detayları ile güncellendi.

- Sunucu güncellendi. handle_23_items.py dosyasına taşıt tamir isteği (sub 135) ve buna uygun olarak istemciye yollanan Opcode 15 sub 23 durum bildirimleri entegre edildi.

- Sunucu güncellendi. Savaş esnasında eşya kullanımı, donanma, tamir ve binek işlemlerinin engellenmesi (Can\'t repair in battle / Can\'t act in battle) sağlandı.

- Sunucu güncellendi. handle_23_items.py Wear/Equip (sub 11) işleyicisine yiyecek/pot gibi can/sp yenileyen sarf malzemeleri (consumable food/potion recovery) için kullanma ve can yenileme desteği eklendi.

- İstemcideki tüm eşya ilişkili C fonksiyonları tarandı. Kilitli eşya korumaları (Item locked, can\'t use) ve arayüz seçim bildirimleri (Item selected for compounding/repair) tespit edilip arşivlendi.

- Sunucu güncellendi. Simya (handle_23_items.py sub 14) birleştirme işleminde oyuncunun Junior Alchemy (ID 15998) yeteneğine sahip olması durumunda elde edilen eşya rankına pozitif bonus verilmesi sağlandı.

- Sunucu güncellendi. Eşya işlemleri (Wear sub 11, Drop sub 3, Destroy sub 124, Compound sub 14) esnasında kilitli eşya doğrulaması (Item locked, can\'t use) entegre edildi.

- Harita taşıt kısıtlamaları (Transports not allowed) istemci tarafında sabit kodlu (hardcoded) olduğu için, bunu aşmak amacıyla sunucu tarafında :ride ve :unride GM komutları eklendi. Bu komutlar taşıta binme işlemini istemcinin kontrolünü atlayarak doğrudan gerçekleştirir.

- Pet binme (Pet Ride - AC 15 Sub 11) ve Pet inme (Pet Rest - AC 15 Sub 12) paketlerinin sunucu yanıtları, PCAP analizlerine uygun olarak (AC 15 Sub 16 ve AC 15 Sub 17 formatında) güncellendi.

- Şans Çekilişi (Lucky Draw - AC 104 Sub 1) sistemi, gönderilen PCAP analizine uygun olarak handle_104_minigame.py içerisine eklendi. Çekiliş sonucu eşyalar 32-bit (ID) formatında envantere eklenerek istemciye iletilir.

- Çadır Sistemi Eklendi: handle_23_items.py (Çadır açma - AC 23 Sub 15), handle_62_tent.py (Çadıra girme ve mobilya yerleştirme - AC 62 Sub 61, Sub 3), handle_65_action.py (Çadır işlemleri - AC 65) implementasyonları yapıldı.

- Sunucu güncellendi. Çadır içi üretim (crafting) mantığı handle_64_crafting.py dosyasına entegre edildi. Paketteki hedef tarif id'si, materyal slot ve adet sayıları okunarak doğru eşyanın verilmesi, doğru slotlardaki materyallerin envanterden silinmesi ve üretim süresi zamanlayıcı paketlerinin doğru gönderilmesi (AC 64 Sub 1, 10 ve 2) sağlandı. Ayrıca Compound2.dat içerisindeki üretim tariflerini çözen extract_recipes.py aracı eklenerek recipes.json dosyası oluşturuldu.

- Sunucu güncellendi. Nesne Market (Item Mall) paket dinleyicisi `handle_34_itemmall.py` oluşturuldu. AC 34 dinlenerek istemciye AC 54 (Kategori onay paketi) ve AC 35 (Cüzdan bakiye paketi) gönderilmesi sağlandı.
