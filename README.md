<div align="center">

# KO Market - Knight Online Pazar ve Arbitraj Takip Sistemi

**Knight Online için Pasif Ağ Paket Dinleme, Anlık Pazar Arama, Arbitraj Analitiği ve REST API / JSON Veri Akışı**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite WAL](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Wireshark / TShark](https://img.shields.io/badge/Network-TShark%20Passive-1679A7.svg?logo=wireshark&logoColor=white)](https://www.wireshark.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## Proje Hakkında

**KO Market**, Knight Online için geliştirilmiş hafif ve modüler bir pazar takip ve fiyat analiz platformudur.

Oyun istemcisine (client) veya belleğe (RAM) müdahale etmeden, yerel ağ arayüzündeki pazar paketlerini pasif olarak yakalar, çözer ve web arayüzünde aranabilir, filtrelenebilir ve analiz edilebilir hale getirir.

Sunulan **JSON Feed API** sayesinde pazar verileri Discord botlarına, web sitelerine veya bildirim servislerine kolayca entegre edilebilir.

---

## Özellikler

- **Anlık Eşya Arama ve Filtreleme:**  
  Eşya adına (örn: *Shard*, *Raptor*, *+8*, *Chitin*), pazar türüne (**SELL / BUY**), sunucu kanalına (Zero 1, Moradon 1 vb.) ve eşya kategorisine göre filtreleme.
- **Arbitraj ve Fiyat Analizi:**  
  Pazardaki en ucuz satış (SELL) fiyatı ile en yüksek alış (BUY) fiyatını anlık eşleştirerek fiyat makasını ve marj oranını (%) hesaplar.
- **Açık Tezgah (Merchant) Görünümü:**  
  Alandaki tüm aktif pazar tezgahlarını, 12 yuvalı görsel envanterlerini ve toplam tezgah değerlerini listeler.
- **Dış Entegrasyonlar İçin REST API ve JSON Feed:**  
  Discord webhook'ları ve harici analiz yazılımları için optimize edilmiş JSON besleme uç noktaları (`/api/feed`, `/api/market`, `/api/arbitrage`).
- **Pasif Ağ Analizi:**  
  DLL enjeksiyonu, hook, hafıza okuma veya dosya modifikasyonu içermez. Paketler Wireshark / TShark motoruyla soket seviyesinde pasif olarak dinlenir.
- **SQLite WAL Mimarisi:**  
  Eşzamanlı okuma ve yazma işlemlerinde kilitlenmeyen, asenkron kuyruklu (Write Queue) SQLite WAL altyapısı.
- **Dark Tasarım ve 500+ Eşya İkonu:**  
  Karus ve El Morad ırk/sınıf avatarları ile harici CDN gereksinimi duymadan çalışan 500+ yerel eşya ikonu.
- **2.300+ Eşyalık USKO Kataloğu:**  
  Orijinal USKO eşya ID çözümleyici (`catalog_data.json`), +1..+10 ve Rebirth seviye varyasyonları.

---

## Mimari Şeması

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

## Kurulum ve Başlatma

### Yöntem 1: Windows İçin Tek Tıkla Kurulum

1. Projeyi indirin veya klonlayın:
   ```bash
   git clone https://github.com/PeyywadoX/ko-market.git
   cd ko-market
   ```
2. **`kurulum.bat`** (veya `setup.bat`) dosyasına çift tıklayın.  
   *Sanal ortamı oluşturur, kütüphaneleri yükler ve veritabanını hazırlar.*
3. **`start_server.bat`** dosyasına çift tıklayarak paneli açın.  
   Tarayıcınızda **`http://127.0.0.1:5000`** adresine gidebilirsiniz.

---

### Canlı Paket Dinleyici (Sniffer) Kurulumu

> **Not:** Sadece pazar verilerini incelemek, web panelini kullanmak veya Discord botuna JSON Feed bağlamak için Wireshark **gerekmez**. Sistem dahili gerçekçi verilerle doğrudan çalışır.

Knight Online çalışırken kendi oyununuzdaki pazar paketlerini canlı yakalamak istiyorsanız:

1. [Wireshark İndir](https://www.wireshark.org/download.html) (Windows Installer 64-bit).
2. Kurulum ekranında şu seçeneklerin işaretli olduğundan emin olun:
   - **TShark** (Komut satırı motoru)
   - **Install Npcap** (Paket yakalama sürücüsü)
3. Npcap kurulurken:
   - **"Install Npcap in WinPcap API-compatible Mode"** seçeneğini işaretleyin.
4. **`start_sniffer.bat`** dosyasını çalıştırın.  
   Oyunda Moradon pazar bölgesinde gezindikçe veya tezgahları açtıkça tüm eşyalar anında veritabanına ve web paneline yansır.

---

### Yöntem 2: Manuel Geliştirici Kurulumu

```bash
# Depoyu klonlayın
git clone https://github.com/PeyywadoX/ko-market.git
cd ko-market

# Sanal ortam oluşturun ve aktif edin
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Web sunucusunu başlatın
python app.py

# (İsteğe bağlı) Paket dinleyiciyi başlatın
python market_sniffer.py
```

---

## REST API ve JSON Feed Dokümantasyonu

### 1. Canlı JSON Feed
- **Uç Nokta:** `GET /api/feed`
- **Açıklama:** Discord botları veya web widget'ları için pazar özeti ve son listelenen eşyaları döner.

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
      "channel": "Zero 1",
      "time": "2026-11-04 21:55:00"
    }
  ]
}
```

---

### 2. Pazar Arama
- **Uç Nokta:** `GET /api/market`
- **Parametreler:**
  - `q`: Eşya arama terimi (örn: `raptor`, `chitin`, `+7`)
  - `type`: `SELL`, `BUY` veya boş (tümü)
  - `category`: `Dagger`, `Silah`, `Zırh`, `Takı`, `Parşömen & PUS`, `Kutu & Gem`
  - `channel`: Sunucu kanalı (örn: `Zero 1`)
  - `sort`: `price_asc` (varsayılan), `price_desc`, `newest`, `name_asc`
  - `limit`: Sonuç limiti (varsayılan: 60, maks: 200)
  - `offset`: Sayfalama ofseti

---

### 3. Arbitraj Fırsatları
- **Uç Nokta:** `GET /api/arbitrage`
- **Açıklama:** En ucuz SELL ile en yüksek BUY arasındaki fiyat farkına göre sıralanmış eşyaları döner.

```bash
curl -X GET "http://127.0.0.1:5000/api/arbitrage"
```

---

### 4. Tekil Eşya Fiyat Özeti
- **Uç Nokta:** `GET /api/item/<item_name>`
- **Örnek:** `/api/item/Shard (+8)`
- **Açıklama:** Eşyanın en düşük satış, en yüksek alış fiyatlarını ve aktif satıcılarını listeler.

---

## Proje Dizin Yapısı

```
ko_market/
├── app.py                  # Flask Web Sunucusu, REST API & JSON Feed
├── market_sniffer.py       # TShark tabanlı pasif paket yakalama motoru
├── market_db.py            # SQLite WAL veritabanı, asenkron kuyruk & modeller
├── items_db.py             # Eşya kataloğu, ID çözümleyici & ikon eşleştirici
├── catalog_data.json       # 2.300+ USKO eşya ID ve ikon kataloğu
├── requirements.txt        # Python bağımlılıkları
├── kurulum.bat             # Otomatik kurulum sihirbazı
├── setup.bat               # Kurulum sihirbazı alias
├── start_server.bat        # Web sunucusu başlatıcı
├── start_sniffer.bat       # Paket dinleyici başlatıcı
├── LICENSE                 # MIT Lisansı
├── README.md               # Proje dokümantasyonu
├── templates/
│   └── index.html          # Pazar Arayüzü
└── static/
    ├── css/
    │   └── market.css      # Stil şablonu
    ├── js/
    │   └── market.js       # Dinamik filtreleme ve arayüz kontrolleri
    ├── brand/
    │   └── peyywadox-mascot.png  # PeyywadoX logo/maskot görseli
    └── assets/
        ├── classes/        # Karakter sınıf ikonları
        └── items/          # 500+ eşya ikon kütüphanesi
```

---

## Yasal Uyarı / Disclaimer

Bu proje **eğitim, araştırma ve ağ analizi** amacıyla geliştirilmiştir. 
- Oyun istemcisinin belleğine (RAM) müdahale etmez, kod enjekte etmez ve tersine mühendislik yapmaz.
- Yalnızca ağ bağdaştırıcısından geçen açık ağ paketlerini pasif olarak inceler.
- Yazılımın kullanımından doğabilecek sorumluluk son kullanıcıya aittir.

---

## Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında açık kaynak olarak yayınlanmıştır.
