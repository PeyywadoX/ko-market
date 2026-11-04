#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Eşya ve İkon Çözümleyici (items_db)
------------------------------------------------
USKO eşya ID'lerini isimlere, yükseltme derecelerine (+1..+10, Rebirth)
ve yerel ikon dosyalarına haritalar.
"""

import os
import re

# Popüler ve Bilinen Eşyalar Kataloğu
ITEM_CATALOG = {
    # Dagger / Bıçak
    111010: "Dagger",
    111020: "Stiletto",
    111030: "Dirk",
    111040: "Kukry",
    111050: "Cleaver",
    120410: "Shard",
    120420: "Mirage Dagger",
    160610: "Mirage Dagger",
    120430: "Dark Vane",
    120440: "Cold-Heart Dagger",
    120450: "Sherion",
    120460: "Chd",
    120500: "Moonlight",
    120510: "Buju Polearm",
    120520: "Khanjar",
    
    # Kılıç / Sword & Tek El
    110010: "Short Sword",
    110020: "Scimitar",
    110030: "Glave",
    110040: "Slayer",
    110050: "Blade",
    120010: "Mirage",
    120020: "Graham",
    120030: "Hell Breaker",
    120040: "Giga",
    120050: "Aventador",
    130010: "Totamic Spear",
    130020: "Iron Impact",
    130030: "Mirage",
    130040: "Deep Scar",
    130050: "Oasis Staff",
    130060: "Chaotic Staff",
    130070: "Scorching Staff",
    130080: "Lightning Erenion",
    130090: "Glacier Erenion",
    130100: "Wreath Erenion",
    130110: "Avedon",
    130120: "Lugias",
    130130: "Hanguk Sword",
    130140: "Smite Hammer",
    130150: "Holy Animor",
    130160: "Lobo Hammer",
    130170: "Lycaon Hammer",
    130180: "Lupus Hammer",
    130210: "Raptor",
    130220: "Iron Necklace",
    130230: "Iron Belt",
    130240: "Chitin Bow",
    130250: "Enion Bow",
    130260: "Eagle's Eye",
    130270: "Helenid",
    130280: "Castellan Bow",
    130290: "Windforce",
    130420: "Iron Impact",
    140220: "Elixir Staff",
    140230: "Salamander Staff",
    140240: "Wizard Staff",
    
    # Kalkanlar / Shields
    210010: "Wood Shield",
    210020: "Round Shield",
    210030: "Black Shield",
    210040: "Kite Shield",
    210050: "Plate Shield",
    220010: "Chitin Shield",
    220020: "Dread Shield",
    220030: "Scorpion Shield",
    220040: "Gab's Blessing",
    220050: "Gab's Adamant",
    220060: "Leonar",
    220070: "Syphior",

    # Zırhlar (Chitin, Shell, Fabric, Linen)
    210040: "Rogue Chitin Armor Pauldron",
    210050: "Rogue Chitin Armor Pants",
    210060: "Rogue Chitin Armor Helmet",
    210070: "Rogue Chitin Armor Gauntlets",
    210080: "Rogue Chitin Armor Boots",
    210140: "Warrior Chitin Armor Pauldron",
    210150: "Warrior Chitin Armor Pants",
    210160: "Warrior Chitin Armor Helmet",
    210170: "Warrior Chitin Armor Gauntlets",
    210180: "Warrior Chitin Armor Boots",
    210240: "Priest Chitin Armor Pauldron",
    210250: "Priest Chitin Armor Pants",
    210260: "Priest Chitin Armor Helmet",
    210270: "Priest Chitin Armor Gauntlets",
    210280: "Priest Chitin Armor Boots",
    210080: "Mage Linen Robe",
    210090: "Mage Linen Pants",
    210100: "Mage Linen Cap",
    210110: "Mage Linen Gloves",
    210120: "Mage Linen Boots",
    220080: "Priest Fabric Coat",
    220090: "Priest Fabric Pants",
    
    # Takılar / Jewelry
    310010: "Ring of Life (ROL)",
    310020: "Ring of Courage (ROC)",
    310030: "Ring of Magic (ROM)",
    310040: "Hero's Valor",
    310050: "Legionnaire Band",
    310060: "Flame Ring",
    310070: "Shio Tears",
    310080: "Imir Ring",
    310090: "Foverin",
    320010: "Iron Necklace",
    320020: "Amulet of Dexterity (AOD)",
    320030: "Amulet of Strength (AOS)",
    320040: "Amulet of Health",
    320050: "Elemental Pendant (EP)",
    320060: "Warrior Pendant (WP)",
    320070: "Priest Pendant (PP)",
    330010: "Iron Belt",
    330020: "Glass Belt",
    330030: "Skeleton Belt",
    330040: "Judicious Belt",
    330050: "Belt of Strength",
    330060: "Belt of Dexterity",
    330070: "String of Skulls (SOS)",
    340010: "Rogue Earring (RE)",
    340020: "Warrior Earring (WE)",
    340030: "Mage Earring (ME)",
    340040: "Cleric Earring (CE)",
    340050: "Secret Silver Earring (SSE)",
    340060: "Howling Rooster (HR)",
    340070: "Lillime's Enticement",
    340080: "Opal Earring",
    340090: "Platinum Earring",
    
    # Parşömenler / PUS / Kutular
    379000: "Blessed Upgrade Scroll (BUS)",
    379010: "Blessed Enchant Scroll (BES)",
    379020: "Upgrade Scroll",
    379030: "Enchant Scroll",
    379006: "Blue Treasure Chest",
    379007: "Green Treasure Chest",
    379008: "Red Treasure Chest",
    379009: "Silvery Gem",
    379011: "Black Gem",
    379012: "Green Gem",
    379013: "Blue Gem",
    379014: "Yellow Gem",
    379015: "Red Gem",
    379016: "Fragment of Avarice",
    379017: "Fragment of Jealousy",
    379018: "Fragment of Lechery",
    810166: "Spirit of Genie",
    800062: "Genie Hammer",
    379040: "Trina's Piece",
    379050: "Tears of Karivdis",
    900000: "Gold Bar (100m)",
    900001: "Silver Bar (10m)",
}

# İsimden ID bulmak için ters sözlük
_NAME_TO_ID = {name.lower(): iid for iid, name in ITEM_CATALOG.items()}

def resolve_item_name(item_id: int) -> str:
    """Eşya ID'sini çözerek isim ve yükseltme seviyesini (+1..+10, Rebirth) döner."""
    if not item_id:
        return "Bilinmeyen Eşya"
        
    s_id = str(item_id)
    # Temel eşya ID'si ve seviye tespiti
    # KO standardında son basamak genellikle yükseltme seviyesidir:
    # 120410 = Shard (+1), 120411 = Shard (+2), ..., 120418 = Shard (+8)
    base_id = (item_id // 10) * 10
    grade = item_id % 10
    
    # Rebirth kontrolü (genellikle 800000000 veya özel reb baytları)
    is_reb = False
    reb_grade = 0
    if item_id >= 800000000:
        is_reb = True
        reb_grade = (item_id % 100) or 1
        base_id = ((item_id - 800000000) // 10) * 10

    base_name = ITEM_CATALOG.get(base_id) or ITEM_CATALOG.get(item_id)
    if not base_name:
        # Yakın ID araması
        for test_base in [base_id, (item_id // 100) * 100]:
            if test_base in ITEM_CATALOG:
                base_name = ITEM_CATALOG[test_base]
                break
                
    if not base_name:
        return f"Item #{item_id}"
        
    if is_reb:
        return f"{base_name} (Rebirth +{reb_grade})"
    elif grade > 0 and grade <= 10:
        return f"{base_name} (+{grade})"
    return base_name

def get_item_id_by_name(item_name: str) -> int:
    """İsimden temel eşya ID'sini döner."""
    if not item_name:
        return 0
    clean = re.sub(r'\s*\(\+?\d+\)|\s*\(Rebirth.*?\)', '', item_name).strip().lower()
    return _NAME_TO_ID.get(clean, 0)

def get_item_icon(item_id: int) -> str:
    """Item ID'ye göre yerel /static/assets/items/ altındaki ikon dosya adını belirler."""
    if not item_id or item_id <= 0:
        return "default.svg"
        
    s = str(item_id)
    # Standart USKO icon dosya isimlendirmesi:
    # itemicon_{kategori}_{grup}_{alt}_{versiyon}.jpg
    # 120410 -> itemicon_1_2041_00_0.jpg
    if len(s) >= 6:
        p1 = s[0]
        p2 = s[1:5]
        cand = f"itemicon_{p1}_{p2}_00_0.jpg"
        return cand
        
    return "default.svg"

def format_coins(coins: int) -> str:
    """Oyun içi coin değerini insan tarafından kolay okunabilir formata çevirir."""
    if not coins or coins <= 0:
        return "0 Coin"
    if coins >= 100_000_000:
        return f"{round(coins / 100_000_000, 2)} GB"
    if coins >= 1_000_000:
        return f"{round(coins / 1_000_000, 2)} M"
    if coins >= 1_000:
        return f"{round(coins / 1000, 1)} K"
    return f"{coins:,}".replace(",", ".") + " Coin"
