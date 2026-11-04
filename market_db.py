#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Pazar Veritabanı ve Sorgu Motoru (ko_market)
----------------------------------------------------------
Hafif, thread-safe SQLite veritabanı. Pazar eşyaları, tezgahlar,
fiyat geçmişi ve arbitraj hesaplamalarını yönetir.
"""

import os
import sqlite3
import time
import json
import threading
from queue import Queue, Empty
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("KO_MARKET_DB_PATH", os.path.join(BASE_DIR, "market.db"))

_write_queue = Queue()
_worker_started = False
_worker_lock = threading.Lock()

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Tabloları ve indeksleri oluşturur."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Pazar Eşyaları (Menissiah ve Tezgahlar)
    c.execute("""
    CREATE TABLE IF NOT EXISTS market_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_id INTEGER,
        merchant_name TEXT,
        merchant_title TEXT DEFAULT '',
        market_type TEXT DEFAULT 'SELL', -- 'SELL' veya 'BUY'
        slot INTEGER DEFAULT 0,
        item_id INTEGER,
        item_name TEXT,
        count INTEGER DEFAULT 1,
        price INTEGER DEFAULT 0,
        durability INTEGER DEFAULT 0,
        server_channel TEXT DEFAULT 'Zero 1',
        location_name TEXT DEFAULT 'Moradon',
        merchant_x INTEGER DEFAULT 0,
        merchant_z INTEGER DEFAULT 0,
        timestamp TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_mitems_name ON market_items(item_name COLLATE NOCASE);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mitems_type ON market_items(market_type);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mitems_price ON market_items(price);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mitems_channel ON market_items(server_channel);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mitems_merchant ON market_items(merchant_name COLLATE NOCASE);")

    # 2. Fiyat Geçmişi (Trend Takibi)
    c.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        market_type TEXT,
        min_price INTEGER,
        max_price INTEGER,
        avg_price INTEGER,
        item_count INTEGER,
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_history_name ON price_history(item_name COLLATE NOCASE, recorded_at);")

    # 3. İzleme / Takip Listesi (Watchlist)
    c.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE,
        target_buy_price INTEGER DEFAULT 0,
        target_sell_price INTEGER DEFAULT 0,
        note TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Meta Durum & İstatistik
    c.execute("""
    CREATE TABLE IF NOT EXISTS market_meta (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()
    
    # Asenkron yazıcı iş parçacığını başlat
    start_db_worker()

def _db_worker():
    conn = get_connection()
    batch = []
    last_commit = time.time()
    
    while True:
        try:
            task = _write_queue.get(timeout=0.5)
            if task is None:
                break
            batch.append(task)
        except Empty:
            pass
        
        now = time.time()
        if batch and (len(batch) >= 100 or now - last_commit >= 1.0):
            try:
                c = conn.cursor()
                for sql, params in batch:
                    c.execute(sql, params)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"[DB WORKER ERROR] {e}")
            finally:
                batch.clear()
                last_commit = now

def start_db_worker():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            t = threading.Thread(target=_db_worker, daemon=True, name="MarketDbWorker")
            t.start()
            _worker_started = True

def queue_execute(sql, params=()):
    """Sorguyu arka planda asenkron çalıştırılmak üzere sıraya koyar."""
    start_db_worker()
    _write_queue.put((sql, params))

# --- SORGULAR & PAZAR YAYINLAMA FONKSİYONLARI ---

def get_market_items(q="", market_type="", channel="", category="", sort_by="price_asc", min_price=None, max_price=None, limit=100, offset=0):
    """Pazar eşyalarını arar ve filtreler."""
    conn = get_connection()
    c = conn.cursor()
    
    where = ["1=1"]
    params = []
    
    if q:
        clean_q = f"%{q.strip()}%"
        where.append("(item_name LIKE ? OR merchant_name LIKE ? OR merchant_title LIKE ?)")
        params.extend([clean_q, clean_q, clean_q])
        
    if market_type and market_type.upper() in ["SELL", "BUY"]:
        where.append("market_type = ?")
        params.append(market_type.upper())
        
    if channel and channel.upper() != "ALL":
        where.append("server_channel LIKE ?")
        params.append(f"%{channel}%")
        
    if min_price is not None and min_price > 0:
        where.append("price >= ?")
        params.append(min_price)
        
    if max_price is not None and max_price > 0:
        where.append("price <= ?")
        params.append(max_price)
        
    where_sql = " AND ".join(where)
    
    order_clause = "price ASC"
    if sort_by == "price_desc":
        order_clause = "price DESC"
    elif sort_by == "newest":
        order_clause = "id DESC"
    elif sort_by == "name_asc":
        order_clause = "item_name ASC, price ASC"
        
    count_sql = f"SELECT COUNT(*) FROM market_items WHERE {where_sql}"
    total_count = c.execute(count_sql, params).fetchone()[0]
    
    data_sql = f"""
    SELECT id, merchant_id, merchant_name, merchant_title, market_type, slot,
           item_id, item_name, count, price, durability, server_channel,
           location_name, merchant_x, merchant_z, timestamp, updated_at
    FROM market_items
    WHERE {where_sql}
    ORDER BY {order_clause}
    LIMIT ? OFFSET ?
    """
    rows = c.execute(data_sql, params + [limit, offset]).fetchall()
    conn.close()
    
    items = [dict(r) for r in rows]
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": items
    }

def get_arbitrage_list(limit=50):
    """SELL ve BUY arasındaki arbitraj (fiyat makası / al-sat kârı) fırsatlarını listeler."""
    conn = get_connection()
    c = conn.cursor()
    
    sql = """
    SELECT 
        s.item_name,
        MIN(s.price) AS min_sell,
        MAX(b.price) AS max_buy,
        COUNT(DISTINCT s.merchant_name) AS seller_count,
        COUNT(DISTINCT b.merchant_name) AS buyer_count,
        s.server_channel AS sell_channel,
        b.server_channel AS buy_channel
    FROM market_items s
    JOIN market_items b ON s.item_name = b.item_name
    WHERE s.market_type = 'SELL' AND b.market_type = 'BUY' AND s.price > 0 AND b.price > 0
    GROUP BY s.item_name
    HAVING (MAX(b.price) - MIN(s.price)) != 0
    ORDER BY (MAX(b.price) - MIN(s.price)) DESC
    LIMIT ?
    """
    rows = c.execute(sql, (limit,)).fetchall()
    conn.close()
    
    results = []
    for r in rows:
        min_sell = r["min_sell"]
        max_buy = r["max_buy"]
        profit = max_buy - min_sell
        profit_pct = round((profit / min_sell) * 100, 1) if min_sell > 0 else 0
        
        results.append({
            "item_name": r["item_name"],
            "min_sell": min_sell,
            "max_buy": max_buy,
            "profit": profit,
            "profit_pct": profit_pct,
            "is_instant_profit": profit > 0,
            "seller_count": r["seller_count"],
            "buyer_count": r["buyer_count"],
            "sell_channel": r["sell_channel"],
            "buy_channel": r["buy_channel"]
        })
    return results

def get_stalls_list(channel="", limit=60):
    """Aktif pazarları (tezgahları) ve içerisindeki eşyaları gruplayarak döner."""
    conn = get_connection()
    c = conn.cursor()
    
    where = ["1=1"]
    params = []
    if channel and channel.upper() != "ALL":
        where.append("server_channel LIKE ?")
        params.append(f"%{channel}%")
        
    where_sql = " AND ".join(where)
    
    # En aktif satıcıları bul
    stalls_sql = f"""
    SELECT merchant_name, merchant_title, market_type, server_channel,
           merchant_x, merchant_z, MAX(updated_at) AS last_seen,
           COUNT(*) AS item_count, SUM(price) AS total_val
    FROM market_items
    WHERE {where_sql}
    GROUP BY merchant_name, market_type
    ORDER BY last_seen DESC
    LIMIT ?
    """
    stalls = [dict(r) for r in c.execute(stalls_sql, params + [limit]).fetchall()]
    
    # Her satıcının eşyalarını çek
    for s in stalls:
        items_sql = """
        SELECT slot, item_id, item_name, count, price, durability
        FROM market_items
        WHERE merchant_name = ? AND market_type = ?
        ORDER BY slot ASC
        LIMIT 12
        """
        s["items"] = [dict(ir) for ir in c.execute(items_sql, (s["merchant_name"], s["market_type"])).fetchall()]
        
    conn.close()
    return stalls

def get_item_history(item_name, limit=20):
    """Belirli bir eşyanın piyasadaki tüm satıcı ve alıcılarını listeler."""
    conn = get_connection()
    c = conn.cursor()
    
    sql = """
    SELECT id, merchant_name, merchant_title, market_type, price, count,
           server_channel, merchant_x, merchant_z, updated_at
    FROM market_items
    WHERE item_name LIKE ?
    ORDER BY market_type DESC, price ASC
    LIMIT ?
    """
    rows = [dict(r) for r in c.execute(sql, (item_name, limit)).fetchall()]
    
    # İstatistikler
    stats_sql = """
    SELECT 
        MIN(CASE WHEN market_type = 'SELL' THEN price END) AS min_sell,
        AVG(CASE WHEN market_type = 'SELL' THEN price END) AS avg_sell,
        MAX(CASE WHEN market_type = 'SELL' THEN price END) AS max_sell,
        MIN(CASE WHEN market_type = 'BUY' THEN price END) AS min_buy,
        AVG(CASE WHEN market_type = 'BUY' THEN price END) AS avg_buy,
        MAX(CASE WHEN market_type = 'BUY' THEN price END) AS max_buy,
        COUNT(*) AS total_listings
    FROM market_items
    WHERE item_name LIKE ?
    """
    stats_row = c.execute(stats_sql, (item_name,)).fetchone()
    conn.close()
    
    return {
        "item_name": item_name,
        "listings": rows,
        "stats": dict(stats_row) if stats_row else {}
    }

def get_market_summary():
    """Özet pazar sayaçlarını ve hacmi döner."""
    conn = get_connection()
    c = conn.cursor()
    
    res = c.execute("""
    SELECT 
        COUNT(*) AS total_items,
        COUNT(DISTINCT merchant_name) AS total_merchants,
        COUNT(DISTINCT item_name) AS distinct_items,
        SUM(CASE WHEN market_type = 'SELL' THEN 1 ELSE 0 END) AS sell_count,
        SUM(CASE WHEN market_type = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
        SUM(CAST(price AS REAL) * CAST(count AS REAL)) AS total_market_volume,
        MAX(updated_at) AS last_update
    FROM market_items
    """).fetchone()
    conn.close()
    
    return dict(res) if res else {}

def seed_sample_data(force=False):
    """Veritabanı boşsa örnek pazar verileriyle doldurur."""
    conn = get_connection()
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM market_items").fetchone()[0]
    if count > 0 and not force:
        conn.close()
        return False
        
    sample_records = [
        # SELL Pazarları
        ("ProTrader", "Shard +8 & Chitinler", "SELL", 0, 120410, "Shard (+8)", 1, 145000000, 100, "Zero 1", "Moradon", 812, 638),
        ("ProTrader", "Shard +8 & Chitinler", "SELL", 1, 120410, "Shard (+7)", 1, 18500000, 100, "Zero 1", "Moradon", 812, 638),
        ("ProTrader", "Shard +8 & Chitinler", "SELL", 2, 210040, "Rogue Chitin Armor Pauldron (+8)", 1, 85000000, 100, "Zero 1", "Moradon", 812, 638),
        ("ProTrader", "Shard +8 & Chitinler", "SELL", 3, 210050, "Rogue Chitin Armor Pants (+8)", 1, 55000000, 100, "Zero 1", "Moradon", 812, 638),
        ("MageKing", "Linen +8 Set ve Stafflar", "SELL", 0, 140220, "Elixir Staff (+8)", 1, 75000000, 100, "Zero 2", "Moradon", 805, 642),
        ("MageKing", "Linen +8 Set ve Stafflar", "SELL", 1, 210080, "Mage Linen Robe (+8)", 1, 12000000, 100, "Zero 2", "Moradon", 805, 642),
        ("MageKing", "Linen +8 Set ve Stafflar", "SELL", 2, 210090, "Mage Linen Pants (+8)", 1, 8000000, 100, "Zero 2", "Moradon", 805, 642),
        ("ScrollDepo", "BUS BES & Genie En Ucuz", "SELL", 0, 379000, "Blessed Upgrade Scroll (BUS)", 100, 2050000, 1, "Zero 1", "Moradon", 820, 635),
        ("ScrollDepo", "BUS BES & Genie En Ucuz", "SELL", 1, 379010, "Blessed Enchant Scroll (BES)", 50, 450000, 1, "Zero 1", "Moradon", 820, 635),
        ("ScrollDepo", "BUS BES & Genie En Ucuz", "SELL", 2, 810166, "Spirit of Genie", 10, 3599000, 1, "Zero 1", "Moradon", 820, 635),
        ("ScrollDepo", "BUS BES & Genie En Ucuz", "SELL", 3, 800062, "Genie Hammer", 30, 2000000, 1, "Zero 1", "Moradon", 820, 635),
        ("WarriorBaba", "Raptor Iron Impact Kelepir", "SELL", 0, 130210, "Raptor (+8)", 1, 320000000, 100, "Zero 1", "Moradon", 810, 630),
        ("WarriorBaba", "Raptor Iron Impact Kelepir", "SELL", 1, 130210, "Raptor (+7)", 1, 42000000, 100, "Zero 1", "Moradon", 810, 630),
        ("WarriorBaba", "Raptor Iron Impact Kelepir", "SELL", 2, 130420, "Iron Impact (+8)", 1, 110000000, 100, "Zero 1", "Moradon", 810, 630),
        ("TakiPazari", "Rol Roc Iron Neck", "SELL", 0, 310010, "Ring of Life (ROL)", 1, 180000000, 100, "Zero 3", "Moradon", 790, 620),
        ("TakiPazari", "Rol Roc Iron Neck", "SELL", 1, 310020, "Ring of Courage (ROC)", 1, 95000000, 100, "Zero 3", "Moradon", 790, 620),
        ("TakiPazari", "Rol Roc Iron Neck", "SELL", 2, 320010, "Iron Necklace", 1, 450000000, 100, "Zero 3", "Moradon", 790, 620),
        ("KutuKiran", "Mavi Yesil Kırmızı Kutu", "SELL", 0, 379006, "Blue Treasure Chest", 40, 8500000, 1, "Zero 2", "Moradon", 815, 645),
        ("KutuKiran", "Mavi Yesil Kırmızı Kutu", "SELL", 1, 379007, "Green Treasure Chest", 60, 2600000, 1, "Zero 2", "Moradon", 815, 645),
        ("KutuKiran", "Mavi Yesil Kırmızı Kutu", "SELL", 2, 379008, "Red Treasure Chest", 100, 1400000, 1, "Zero 2", "Moradon", 815, 645),
        
        # BUY Pazarları (Alıcılar - Arbitraj Simülasyonu)
        ("BusAlinir", "BUS 2.000k NAKIT ALINIR", "BUY", 0, 379000, "Blessed Upgrade Scroll (BUS)", 500, 2000000, 1, "Zero 1", "Moradon", 825, 635),
        ("GenieAlinir", "Genie 3.4m Alinir", "BUY", 0, 810166, "Spirit of Genie", 50, 3400000, 1, "Zero 1", "Moradon", 822, 637),
        ("KutuAlinir", "Mavi 8.2m Kırmızı 1.3m", "BUY", 0, 379006, "Blue Treasure Chest", 100, 8200000, 1, "Zero 2", "Moradon", 818, 647),
        ("KutuAlinir", "Mavi 8.2m Kırmızı 1.3m", "BUY", 1, 379008, "Red Treasure Chest", 200, 1300000, 1, "Zero 2", "Moradon", 818, 647),
        ("TakiAlis", "ROL 170m ROC 90m ALINIR", "BUY", 0, 310010, "Ring of Life (ROL)", 5, 170000000, 100, "Zero 3", "Moradon", 795, 622),
        ("TakiAlis", "ROL 170m ROC 90m ALINIR", "BUY", 1, 310020, "Ring of Courage (ROC)", 10, 90000000, 100, "Zero 3", "Moradon", 795, 622),
        ("UpgradeciAlis", "Raptor +7 40m Shard +7 17m", "BUY", 0, 130210, "Raptor (+7)", 10, 40000000, 100, "Zero 1", "Moradon", 812, 628),
        ("UpgradeciAlis", "Raptor +7 40m Shard +7 17m", "BUY", 1, 120410, "Shard (+7)", 15, 17000000, 100, "Zero 1", "Moradon", 812, 628),
    ]
    
    c.executemany("""
    INSERT INTO market_items (
        merchant_name, merchant_title, market_type, slot, item_id, item_name,
        count, price, durability, server_channel, location_name, merchant_x, merchant_z, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, sample_records)
    
    conn.commit()
    conn.close()
    return True
