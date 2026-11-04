#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Eşya ve İkon Çözümleyici (items_db)
------------------------------------------------
USKO eşya kataloğunu (2,300+ eşya), ID eşleştirmesini,
yükseltme derecelerini (+1..+10, Rebirth) ve yerel ikon dosyalarını yönetir.
"""

import os
import re
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(BASE_DIR, "catalog_data.json")
STATIC_ITEMS_DIR = os.path.join(BASE_DIR, "static", "assets", "items")

_ID_TO_INFO = {}        # int(item_id) -> (item_name, icon_code)
_BASE_NAME_TO_ICON = {} # clean_base_name -> icon_code
_NAME_TO_ID = {}        # clean_item_name -> int(item_id)

def _load_catalog():
    global _ID_TO_INFO, _BASE_NAME_TO_ICON, _NAME_TO_ID
    if not os.path.exists(CATALOG_FILE):
        return

    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            
        for k, v in raw.items():
            try:
                iid = int(k)
            except ValueError:
                continue
            iname = v[0]
            icode = str(v[1]).strip()
            
            _ID_TO_INFO[iid] = (iname, icode)
            
            # İsimden ID'ye ters harita
            n_clean = iname.lower().strip()
            if n_clean not in _NAME_TO_ID:
                _NAME_TO_ID[n_clean] = iid
                
            # Taban isimden ikona (örn: "shard (+8)" -> "shard")
            base_name = re.sub(r'\s*\(\+?\d+.*?\)', '', n_clean).strip()
            if base_name and base_name not in _BASE_NAME_TO_ICON:
                _BASE_NAME_TO_ICON[base_name] = icode
                
    except Exception as e:
        print(f"[!] Katalog yuklenirken hata: {e}")

_load_catalog()

# Özel USKO eşleşmeleri
_MANUAL_BASE_ICONS = {
    "shard": "11121000",
    "raptor": "15621000",
    "iron impact": "14621000",
    "elixir staff": "18111000",
    "mirage dagger": "11061000",
    "dark vane": "11121000",
    "hell breaker": "14621000",
    "avedon": "13582000",
    "lugias": "12151000",
    "hanguk sword": "12151000",
    "chitin shield": "17025000",
    "dread shield": "17910200",
    "scorpion shield": "17920500",
    "ring of life": "33021000",
    "ring of courage": "33011000",
    "iron necklace": "32031000",
    "iron belt": "34061000",
    "blessed upgrade scroll": "37901600",
    "blessed enchant scroll": "37902200",
    "spirit of genie": "81036900",
    "genie hammer": "37909900",
    "blue treasure chest": "37915600",
    "green treasure chest": "37915500",
    "red treasure chest": "37915400",
    "silvery gem": "38919600",
    "blue gem": "38919900",
    "gold bar": "37906800",
}

def resolve_item_name(item_id: int) -> str:
    """Eşya ID'sini çözerek isim ve seviyesini döner."""
    if not item_id or item_id <= 0:
        return "Bilinmeyen Eşya"
        
    iid = int(item_id)
    if iid in _ID_TO_INFO:
        return _ID_TO_INFO[iid][0]
        
    s = str(iid)
    # Taban eşya araması (son basamakları sıfırlayarak)
    if len(s) == 9:
        for suffix in ['0001', '0000', '0047', '0048', '0217', '0218']:
            cand = int(s[:5] + suffix)
            if cand in _ID_TO_INFO:
                raw_name = _ID_TO_INFO[cand][0]
                base_clean = re.sub(r'\s*\(\+?\d+.*?\)', '', raw_name).strip()
                last_digit = int(s[-1])
                if 1 <= last_digit <= 10:
                    return f"{base_clean} (+{last_digit})"
                return base_clean

    return f"Item #{item_id}"

def get_item_id_by_name(item_name: str) -> int:
    """İsimden temel eşya ID'sini döner."""
    if not item_name:
        return 0
    clean = item_name.lower().strip()
    if clean in _NAME_TO_ID:
        return _NAME_TO_ID[clean]
        
    # Parantezsiz arama
    base_clean = re.sub(r'\s*\(\+?\d+.*?\)', '', clean).strip()
    for name, iid in _NAME_TO_ID.items():
        if base_clean in name:
            return iid
            
    return 0

def _icon_filename_from_base(base: str) -> str:
    """8 haneli icon_code değerinden diskteki en uygun JPG dosya adını belirler."""
    if not base:
        return "default.svg"
        
    base = str(base).strip()
    
    # 10 haneli (Ruler of Legend vb. 11_1331_xx_0)
    if len(base) == 10 and base.startswith("11"):
        return f"itemicon_{base[:2]}_{base[2:6]}_{base[6:8]}_0.jpg"
        
    if base.startswith("1") and len(base) >= 9 and not base.startswith("11"):
        base = base[1:]
        
    if len(base) >= 8:
        base = base[:8]
    else:
        base = base.ljust(8, '0')
        
    last = base[7]
    candidates = [
        f"itemicon_{base[0]}_{base[1:5]}_{base[5:7]}_{last}.jpg",
        f"itemicon_{base[0]}_{base[1:5]}_{base[5:7]}_0.jpg",
        f"itemicon_{base[0]}_{base[1:5]}_00_0.jpg",
        f"itemicon_{base[0]}_{base[1:5]}_10_0.jpg",
        f"itemicon_{base[0]}_{base[1:5]}_20_0.jpg",
        f"itemicon_{base[0]}_{base[1:5]}_12_1.jpg",
    ]
    
    # Parça varyasyonları (zırhlar için 1..5)
    for p in ['1', '2', '3', '4', '5', '0']:
        candidates.append(f"itemicon_{base[0]}_{base[1:5]}_{base[5:7]}_{p}.jpg")
        
    for c in candidates:
        if os.path.exists(os.path.join(STATIC_ITEMS_DIR, c)):
            return c
            
    # Diskte bulunamasa dahi standart kural dosya adını dön (app.py upstream'den indirsin)
    return candidates[1]

def get_item_icon(item_id: int, item_name: str = "") -> str:
    """Eşya ID'si veya isminden en doğru yerel ikon dosya adını döner."""
    try:
        iid = int(item_id or 0)
    except (ValueError, TypeError):
        iid = 0
        
    s = str(iid) if iid > 0 else ""
    
    # 1. Özel / bilinen eşya kuralları
    if s.startswith("900144") or iid == 900144023:
        return "itemicon_9_0014_40_0.jpg" # Monster Stone
    if s.startswith("11133"):
        sub = s[6] if len(s) > 6 else "5"
        return f"itemicon_11_1331_{sub}0_0.jpg" # Ruler of Legend
        
    # 2. Katalogdan doğrudan ID eşleştirmesi
    if iid in _ID_TO_INFO:
        icode = _ID_TO_INFO[iid][1]
        if icode:
            return _icon_filename_from_base(icode)
            
    # 3. İsim üzerinden eşleştirme
    if item_name:
        clean_n = item_name.lower().strip()
        base_n = re.sub(r'\s*\(\+?\d+.*?\)', '', clean_n).strip()
        if base_n in _MANUAL_BASE_ICONS:
            return _icon_filename_from_base(_MANUAL_BASE_ICONS[base_n])
        if base_n in _BASE_NAME_TO_ICON:
            return _icon_filename_from_base(_BASE_NAME_TO_ICON[base_n])
            
    # 4. 9 haneli prefix araması (yükseltme seviyeleri için)
    if len(s) == 9:
        for suffix in ['0001', '0000', '0047', '0048', '0217', '0218']:
            cand = int(s[:5] + suffix)
            if cand in _ID_TO_INFO:
                icode = _ID_TO_INFO[cand][1]
                return _icon_filename_from_base(icode)
                
    # 5. Taban ID'den standart türetim
    if len(s) >= 8:
        return _icon_filename_from_base(s[:8])
        
    return "default.svg"

def format_coins(coins: int) -> str:
    """Oyun içi coin değerini formatlar."""
    if not coins or coins <= 0:
        return "0 Coin"
    if coins >= 100_000_000:
        return f"{round(coins / 100_000_000, 2)} GB"
    if coins >= 1_000_000:
        return f"{round(coins / 1_000_000, 2)} M"
    if coins >= 1_000:
        return f"{round(coins / 1000, 1)} K"
    return f"{coins:,}".replace(",", ".") + " Coin"
