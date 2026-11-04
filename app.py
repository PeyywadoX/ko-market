#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Pazar Web Sunucusu ve Yayınlama API'si (ko_market)
--------------------------------------------------------------
Canlı Pazar Arama, Arbitraj Analitiği, REST API ve JSON Veri Besleme (Feed).
"""

import os
import sys
import time
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, Response

import market_db
import items_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
ICONS_DIR = os.path.join(STATIC_DIR, "assets", "items")

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)

# Formatlayıcı Fonksiyon
def enrich_item(item):
    """Eşyayı ikon, kategori ve insan tarafından okunabilir para birimiyle zenginleştirir."""
    price = item.get("price") or 0
    it_id = item.get("item_id") or 0
    item_name = item.get("item_name") or "Bilinmeyen Eşya"
    
    # İkon
    icon = items_db.get_item_icon(it_id) if it_id > 0 else "default.svg"
    
    # Para formatı (Coin, M, GB)
    m_val = round(price / 1_000_000, 2)
    gb_val = round(price / 100_000_000, 2)
    
    if price >= 100_000_000:
        price_tag = f"{gb_val} GB"
    elif price >= 1_000_000:
        price_tag = f"{m_val} M"
    elif price >= 1_000:
        price_tag = f"{round(price / 1000, 1)} K"
    else:
        price_tag = f"{price} Coin"
        
    formatted_coin = f"{price:,}".replace(",", ".")
    
    # Derece / Kalite rengi belirleme
    grade_color = "#94a3b8" # Standart
    if "+7" in item_name:
        grade_color = "#38bdf8" # Nadir / Mavi
    elif "+8" in item_name:
        grade_color = "#f59e0b" # Epik / Altın
    elif "+9" in item_name:
        grade_color = "#ec4899" # Efsanevi / Pembe
    elif "+10" in item_name or "Rebirth" in item_name or "Reb" in item_name:
        grade_color = "#a855f7" # Rebirth / Mor
        
    category = "Diğer"
    n_lower = item_name.lower()
    if any(w in n_lower for w in ["shard", "dagger", "stiletto", "dirk", "kukry"]):
        category = "Dagger"
    elif any(w in n_lower for w in ["raptor", "iron impact", "elixir", "iron bow", "chitin bow", "sword", "axe", "spear"]):
        category = "Silah"
    elif any(w in n_lower for w in ["chitin", "shell", "fp", "fabric", "linen", "armor", "pauldron", "pads", "boots"]):
        category = "Zırh"
    elif any(w in n_lower for w in ["ring", "necklace", "earring", "belt", "rol", "roc", "iron neck"]):
        category = "Takı"
    elif any(w in n_lower for w in ["scroll", "bus", "bes", "genie", "trina", "hammer"]):
        category = "Parşömen & PUS"
    elif any(w in n_lower for w in ["chest", "kutu", "gem", "fragment"]):
        category = "Kutu & Gem"

    item["icon"] = icon
    item["price_tag"] = price_tag
    item["formatted_coin"] = formatted_coin
    item["grade_color"] = grade_color
    item["category"] = category
    return item

# --- ROTATLAR ---

@app.route("/")
def index():
    """Ana Pazar Arayüzü."""
    return render_template("index.html")

@app.route("/icons/<path:filename>")
def serve_icon(filename):
    """Yerel eşya ikonunu sunar."""
    safe_name = os.path.basename(filename)
    icon_path = os.path.join(ICONS_DIR, safe_name)
    if os.path.exists(icon_path):
        return send_from_directory(ICONS_DIR, safe_name)
    return send_from_directory(ICONS_DIR, "default.svg")

@app.route("/api/market")
def api_market():
    """Pazar eşyalarını arama ve filtreleme API'si."""
    q = request.args.get("q", "").strip()
    mtype = request.args.get("type", "").strip().upper()
    channel = request.args.get("channel", "").strip()
    category = request.args.get("category", "").strip()
    sort_by = request.args.get("sort", "price_asc").strip()
    
    try:
        min_p = int(request.args.get("min_price", 0))
    except ValueError:
        min_p = 0
    try:
        max_p = int(request.args.get("max_price", 0))
    except ValueError:
        max_p = 0
        
    limit = min(int(request.args.get("limit", 60)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    
    data = market_db.get_market_items(
        q=q, market_type=mtype, channel=channel, category=category,
        sort_by=sort_by, min_price=min_p, max_price=max_p,
        limit=limit, offset=offset
    )
    
    # Eşyaları zenginleştir
    data["items"] = [enrich_item(it) for it in data["items"]]
    return jsonify(data)

@app.route("/api/arbitrage")
def api_arbitrage():
    """SELL ve BUY arasındaki arbitraj (kâr / fiyat makası) fırsatları."""
    limit = min(int(request.args.get("limit", 40)), 100)
    items = market_db.get_arbitrage_list(limit=limit)
    
    for it in items:
        # Fiyat etiketleri
        min_s = it["min_sell"]
        max_b = it["max_buy"]
        profit = it["profit"]
        
        it["min_sell_fmt"] = f"{min_s:,}".replace(",", ".")
        it["max_buy_fmt"] = f"{max_b:,}".replace(",", ".")
        it["profit_fmt"] = f"{profit:,}".replace(",", ".")
        it["icon"] = items_db.get_item_icon(items_db.get_item_id_by_name(it["item_name"]))
    
    return jsonify({
        "total": len(items),
        "arbitrage": items
    })

@app.route("/api/stalls")
def api_stalls():
    """Açık merchant tezgahlarını ve içeriklerini döner."""
    channel = request.args.get("channel", "")
    limit = min(int(request.args.get("limit", 50)), 100)
    stalls = market_db.get_stalls_list(channel=channel, limit=limit)
    
    for s in stalls:
        s["formatted_total"] = f"{int(s['total_val'] or 0):,}".replace(",", ".")
        for it in s["items"]:
            enrich_item(it)
            
    return jsonify({"total": len(stalls), "stalls": stalls})

@app.route("/api/item/<path:item_name>")
def api_item_detail(item_name):
    """Tekil bir eşyanın piyasa analizi ve satıcı listesi."""
    detail = market_db.get_item_history(item_name)
    detail["listings"] = [enrich_item(it) for it in detail["listings"]]
    return jsonify(detail)

@app.route("/api/stats")
def api_stats():
    """Genel pazar metrikleri ve sayaçları."""
    summary = market_db.get_market_summary()
    total_vol = int(summary.get("total_market_volume") or 0)
    summary["formatted_volume_gb"] = round(total_vol / 100_000_000, 1)
    summary["formatted_volume_coins"] = f"{total_vol:,}".replace(",", ".")
    return jsonify(summary)

@app.route("/api/feed")
def api_feed():
    """Dış sistemler (Discord Botu, Webhook veya Harici Siteler) için JSON Canlı Pazar Beslemesi."""
    summary = market_db.get_market_summary()
    recent = market_db.get_market_items(sort_by="newest", limit=30)
    
    feed_data = {
        "status": "online",
        "service": "Knight Online Market Feed API",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_items": summary.get("total_items", 0),
            "total_merchants": summary.get("total_merchants", 0),
            "sell_merchants": summary.get("sell_count", 0),
            "buy_merchants": summary.get("buy_count", 0),
            "total_volume_gb": round((summary.get("total_market_volume") or 0) / 100_000_000, 2)
        },
        "latest_listings": [
            {
                "item_name": it["item_name"],
                "market_type": it["market_type"],
                "price": it["price"],
                "price_tag": enrich_item(dict(it))["price_tag"],
                "seller": it["merchant_name"],
                "channel": it["server_channel"],
                "time": it["timestamp"]
            }
            for it in recent["items"]
        ]
    }
    return jsonify(feed_data)

@app.route("/api/stream")
def sse_stream():
    """Server-Sent Events canlı pazar sinyali."""
    def event_stream():
        while True:
            time.sleep(4.0)
            summary = market_db.get_market_summary()
            payload = json.dumps({
                "type": "heartbeat",
                "ts": int(time.time()),
                "total_items": summary.get("total_items", 0),
                "total_merchants": summary.get("total_merchants", 0)
            })
            yield f"data: {payload}\n\n"
            
    return Response(event_stream(), mimetype="text/event-stream")

def start_server(port=5000, host="127.0.0.1"):
    """Sunucuyu başlatır."""
    market_db.init_db()
    market_db.seed_sample_data() # Boşsa örnek verileri ekler
    print(f"[*] Knight Online Pazar Sunucusu Hazır:")
    print(f"    Web Arayüzü: http://{host}:{port}/")
    print(f"    JSON Feed:   http://{host}:{port}/api/feed")
    print(f"    Arbitraj:    http://{host}:{port}/api/arbitrage\n")
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == "__main__":
    bind_host = os.environ.get("KO_MARKET_HOST", "127.0.0.1")
    bind_port = int(os.environ.get("KO_MARKET_PORT", 5000))
    start_server(port=bind_port, host=bind_host)
