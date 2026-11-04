<div align="center">

# ⚖️ KO Market — Knight Online Canlı Pazar & Arbitraj Sistemi

**Knight Online için Pasif Ağ Paket Dinleme, Anlık Pazar Arama, Arbitraj Analitiği ve REST API / JSON Yayınlama Motoru**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Wireshark / TShark](https://img.shields.io/badge/Network-TShark%20Passive-1679A7.svg?logo=wireshark&logoColor=white)](https://www.wireshark.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📌 Proje Hakkında

**KO Market**, Knight Online oyuncuları ve topluluk geliştiricileri için tasarlanmış bağımsız, hafif ve modern bir pazar takip platformudur. 

Oyun istemcisine (client) veya belleğe (RAM) hiçbir şekilde müdahale etmeden, sadece yerel ağ arayüzündeki pazar paketlerini pasif olarak yakalar, çözer ve web arayüzünde aranabilir, filtrelenebilir ve analiz edilebilir hale getirir.

Ayrıca sunduğu **JSON Feed API** sayesinde pazar verilerini Discord botlarınıza, web sitelerinize veya Telegram bildirim kanallarınıza kolayca entegre edebilirsiniz.

---

## ✨ Öne Çıkan Özellikler

- 🔍 **Anlık Eşya Arama & Filtreleme:**
  Eşya adına (örn: *Shard*, *Raptor*, *+8*, *Chitin*), pazar türüne (**SELL / BUY**), sunucu kanalına (Moradon 1, Moradon 2 vb.) ve eşya kategorisine göre gecikmesiz canlı arama.
- ⚖️ **Otomatik Arbitraj & Kâr Fırsatları:**
  Pazardaki en ucuz satış (SELL) fiyatı ile en yüksek alış (BUY) fiyatını anlık eşleştirerek net kâr makasını ve marj oranını (%) hesaplar.
- 🏪 **Açık Tezgah (Merchant) Görünümü:**
  Alandaki tüm aktif pazar tezgahlarını, 12 yuvalı görsel envanterlerini ve toplam tezgah değerlerini listeler.
- 📡 **Dış Entegrasyonlar İçin REST API & JSON Feed:**
  Discord webhook'ları, pazar botları ve harici analiz yazılımları için optimize edilmiş JSON besleme uç noktaları (`/api/feed`, `/api/market`, `/api/arbitrage`).
- 🛡️ **%100 Pasif ve Güvenli:**
  DLL enjeksiyonu, hook, hafıza okuma veya dosya modifikasyonu **kesinlikle içermez**. Paketler sadece Wireshark / TShark motoruyla pasif soket seviyesinde dinlenir.
- ⚡ **Yüksek Performanslı SQLite WAL Mimarisi:**
  Eşzamanlı okuma ve yazma işlemlerinde kilitlenmeyen, asenkron kuyruklu (Write Queue) SQLite WAL altyapısı.
- 🎨 **PeyywadoX Maskotu, Dark Tasarım & 500+ Eşya İkonu:**
  Resmi PeyywadoX maskotu, Karus & El Morad ırk/sınıf avatarları ve harici CDN gereksinimi duymadan çalışan 500+ yerel eşya ikonu.
- 📚 **2.300+ Eşyalık USKO Kataloğu:**
  Gerçek USKO eşya ID çözümleyici (`catalog_data.json`), +1..+10 ve Rebirth seviye varyasyonları.

---

## 🏗️ Mimari Şeması

```
                             [ Knight Online İstemcisi ]
                                         │ (Ağ Paketleri)
                                         ▼
                            [ Wireshark / TShark Engine ]
                                         │ (TCP Port 15001)
                                         ▼
                           [ market_sniffer.py (Pasif) ]
                                         │ AES-128 / LZF Çözümleme
                                         │ Opcode 0x68 (Menissiah / Merchant)
                                         ▼
                           [ market_db.py (SQLite WAL) ]
                                   ▲            ▲
                     Okuma Sorguları            REST API / Feed
                                   │            │
                           [ app.py (Flask Web Server) ]
                                   │            │
                    ┌──────────────┴────┐  ┌────┴─────────────┐
                    ▼                   ▼  ▼                  ▼
             Web Dashboard          JSON Feed         Discord Botu /
             (Tarayıcı Arayüzü)    (/api/feed)        Dış Entegrasyonlar
```

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler
- **Python 3.10** veya üzeri
- *(Canlı paket dinleme için opsiyonel)*: [Wireshark](https://www.wireshark.org/) (TShark bileşeni seçili olmalıdır)

### 2. Kurulum

Depoyu klonlayın ve bağımlılıkları yükleyin:

```bash
git clone https://github.com/PeyywadoX/ko-market.git
cd ko-market
pip install -r requirements.txt
```

### 3. Çalıştırma

Projeyi çalıştırmak için 2 yöntem bulunur:

#### Yöntem A: Sadece Web Sunucusu & Veri İnceleme
> *Not: Veritabanında veri yoksa sistem otomatik olarak örnek pazar verileriyle (Seed Data) başlar. Oyuna bağlı olmadan hemen arayüzü ve API'yi test edebilirsiniz.*

```bash
python app.py
```
veya Windows üzerinde:
```bat
start_server.bat
```
Tarayıcınızdan **`http://127.0.0.1:5000`** adresine gidin.

#### Yöntem B: Canlı Paket Dinleyici (Sniffer) ile Birlikte
Knight Online çalışırken Moradon pazarındaki verileri canlı yakalamak için:

1. **Ağ Dinleyiciyi Başlatın:**
   ```bash
   python market_sniffer.py
   ```
   *(veya `start_sniffer.bat`)*
2. **Web Sunucusunu Başlatın:**
   ```bash
   python app.py
   ```
Oyunda pazar bölgesinde gezindikçe veya Menissiah / Merchant listelerini açtıkça veriler anında veritabanına ve web paneline yansır.

---

## 📡 REST API & JSON Feed Dokümantasyonu

KO Market, harici uygulamalarınız için zengin JSON API uç noktaları sunar:

### 1. Canlı JSON Feed (En Kolay Entegrasyon)
- **Uç Nokta:** `GET /api/feed`
- **Açıklama:** Discord botları veya web widget'ları için özet pazar hacmi ve en son listelenen 30 eşyayı döner.

```json
{
  "service": "Knight Online Market Feed API",
  "status": "online",
  "generated_at": "2026-11-04T22:00:00",
  "summary": {
    "total_items": 420,
    "total_merchants": 35,
    "sell_merchants": 22,
    "buy_merchants": 13,
    "total_volume_gb": 48.5
  },
  "latest_listings": [
    {
      "item_name": "Shard (+8)",
      "market_type": "SELL",
      "price": 380000000,
      "price_tag": "3.8 GB",
      "seller": "ShadowRogue",
      "channel": "Moradon 1",
      "time": "2026-11-04 21:55:00"
    }
  ]
}
```

---

### 2. Gelişmiş Pazar Arama
- **Uç Nokta:** `GET /api/market`
- **Parametreler:**
  - `q`: Eşya arama terimi (örn: `raptor`, `chitin`, `+7`)
  - `type`: `SELL`, `BUY` veya boş (tümü)
  - `category`: `Dagger`, `Silah`, `Zırh`, `Takı`, `Parşömen & PUS`, `Kutu & Gem`
  - `channel`: Sunucu kanalı (örn: `Moradon 1`)
  - `sort`: `price_asc` (varsayılan), `price_desc`, `newest`, `name_asc`
  - `limit`: Sonuç limiti (varsayılan: 60, maks: 200)
  - `offset`: Sayfalama ofseti

---

### 3. Arbitraj & Kâr Fırsatları
- **Uç Nokta:** `GET /api/arbitrage`
- **Açıklama:** En ucuz SELL ile en yüksek BUY arasındaki kâr marjına göre sıralanmış eşyaları döner.

```bash
curl -X GET "http://127.0.0.1:5000/api/arbitrage"
```

---

### 4. Tekil Eşya Fiyat Özeti
- **Uç Nokta:** `GET /api/item/<item_name>`
- **Örnek:** `/api/item/Shard (+8)`
- **Açıklama:** Eşyanın en düşük satış, en yüksek alış fiyatlarını ve aktif tüm satıcılarını listeler.

---

## 📂 Proje Dizin Yapısı

```
ko_market/
├── app.py                  # Flask Web Sunucusu, REST API & JSON Feed
├── market_sniffer.py       # TShark tabanlı pasif paket yakalama motoru
├── market_db.py            # SQLite WAL veritabanı, asenkron kuyruk & modeller
├── items_db.py             # Eşya kataloğu, ID çözümleyici & ikon eşleştirici
├── requirements.txt        # Minimal Python bağımlılıkları
├── start_server.bat        # Tek tıkla sunucu başlatıcı
├── start_sniffer.bat       # Tek tıkla paket dinleyici başlatıcı
├── LICENSE                 # MIT Lisansı
├── README.md               # Proje dökümantasyonu
├── templates/
│   └── index.html          # Modern SPA Pazar Arayüzü
└── static/
    ├── css/
    │   └── market.css      # Dark temalı modern stil şablonu
    ├── js/
    │   └── market.js       # Dinamik filtreleme, arama ve modal kontrol scripti
    └── assets/
        └── items/          # 500+ eşya ikon kütüphanesi
```

---

## ⚖️ Yasal Uyarı / Disclaimer

Bu proje **eğitim, araştırma ve ağ analizi** amacıyla geliştirilmiştir. 
- Oyun istemcisinin belleğine (RAM) müdahale etmez, kod enjekte etmez ve tersine mühendislik yapmaz.
- Yalnızca ağ bağdaştırıcınızdan geçen ve zaten bilgisayarınıza ulaşmış olan açık ağ paketlerini pasif olarak inceler.
- Yazılımın kullanımından doğabilecek sorumluluk tamamen son kullanıcıya aittir.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak yayınlanmıştır. Dilediğiniz gibi geliştirebilir, fork'layabilir ve kendi projelerinizde kullanabilirsiniz.
