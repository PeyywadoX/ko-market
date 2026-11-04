#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Pazar Paket Yakalayıcı (ko_market)
-----------------------------------------------
Sadece Menissiah ve Pazar Tezgahı paketlerini (Opcode 0x68)
pasif olarak dinler, deşifre eder ve veritabanına kaydeder.
Bellek okuma / enjeksiyon içermez.
"""

import sys
import os
import time
import struct
import subprocess
import threading

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import market_db
import items_db

# Kripto Sabitleri (USKO 2626)
AES_STATIC_KEY = struct.pack('<IIII', 0x23E51F87, 0xAD88A178, 0xAA5ECF22, 0x671E185B)
AES_IV = bytes.fromhex('32 4e aa 58 bc b3 ae e3 6b c7 4c 56 36 47 34 f2')
static_cipher = Cipher(algorithms.AES(AES_STATIC_KEY), modes.CBC(AES_IV))

# Renkler
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_GOLD = "\033[38;5;220m"
C_WHITE = "\033[97m"

def lzf_decompress(data: bytes, expected_len: int) -> bytes:
    """Knight Online LibLZF Açıcı (sub_87D510)."""
    try:
        if expected_len < 0:
            return b""
        in_len = len(data)
        out = bytearray()
        i = 0
        while i < in_len:
            ctrl = data[i]
            i += 1
            if ctrl < 32:
                lit_len = ctrl + 1
                if i + lit_len > in_len: return b""
                out.extend(data[i:i + lit_len])
                i += lit_len
            else:
                length = ctrl >> 5
                ref_offset = (ctrl & 0x1f) << 8
                if length == 7:
                    if i >= in_len: return b""
                    length += data[i]
                    i += 1
                ref_offset += data[i]
                i += 1
                ref_offset += 1
                length += 2
                ref_pos = len(out) - ref_offset
                if ref_pos < 0: return b""
                for _ in range(length):
                    out.append(out[ref_pos])
                    ref_pos += 1
        return bytes(out)
    except Exception:
        return b""

def decrypt_packet(payload: bytes) -> bytes:
    """Paketin AES-128 şifresini çözer."""
    if len(payload) < 16 or len(payload) % 16 != 0:
        return payload
    try:
        decryptor = static_cipher.decryptor()
        return decryptor.update(payload) + decryptor.finalize()
    except Exception:
        return payload

def parse_merchant_packet(data: bytes, channel: str = "Zero 1"):
    """Opcode 0x68 (WIZ_MERCHANT): Menissiah ve Pazar Tezgahlarını işler."""
    if len(data) < 2 or data[0] != 0x68:
        return False

    sub_type = data[1]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- 1. MENİSSİAH OFFICIAL LIST (Subtype 0x30 / 0x06) ---
    if sub_type == 0x30 and len(data) >= 8:
        action = data[2] if len(data) > 2 else 0
        if action == 0x06: # Tam Pazar Kataloğu
            try:
                # Menissiah paket yapısı: satıcılar ve 12 slotluk eşyaları
                offset = 4
                total_stalls = struct.unpack_from('<H', data, offset)[0]
                offset += 2
                
                saved_count = 0
                for _ in range(min(total_stalls, 500)):
                    if offset + 6 > len(data): break
                    seller_id = struct.unpack_from('<I', data, offset)[0]
                    name_len = struct.unpack_from('<H', data, offset + 4)[0]
                    offset += 6
                    if offset + name_len > len(data): break
                    seller_name = data[offset:offset+name_len].decode('latin-1', errors='ignore').strip('\x00')
                    offset += name_len
                    
                    # 12 Slot eşyaları
                    for slot in range(12):
                        if offset + 16 > len(data): break
                        it_id, count, dur, price, serial = struct.unpack_from('<IHHIQ', data, offset)
                        offset += 16
                        if it_id > 0 and price > 0:
                            item_name = items_db.resolve_item_name(it_id)
                            market_db.queue_execute("""
                            INSERT INTO market_items (
                                merchant_id, merchant_name, market_type, slot, item_id, item_name,
                                count, price, durability, server_channel, timestamp
                            ) VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (seller_id, seller_name, slot, it_id, item_name, count, price, dur, channel, now_str))
                            saved_count += 1
                            
                if saved_count > 0:
                    print(f"{C_GREEN}[MENİSSİAH]{C_RESET} {saved_count} pazar eşyası güncellendi. ({channel})")
                    return True
            except Exception as e:
                pass

    # --- 2. TEZGAHA TIKLAMA / İNCELEME (Subtype 0x05 / 0x06) ---
    elif sub_type in (0x05, 0x06) and len(data) >= 8:
        try:
            seller_id = struct.unpack_from('<I', data, 4)[0]
            offset = 8
            mtype = 'SELL' if sub_type == 0x05 else 'BUY'
            
            saved_count = 0
            for slot in range(12):
                if offset + 16 > len(data): break
                it_id, count, dur, price, serial = struct.unpack_from('<IHHIQ', data, offset)
                offset += 16
                if it_id > 0:
                    item_name = items_db.resolve_item_name(it_id)
                    market_db.queue_execute("""
                    INSERT INTO market_items (
                        merchant_id, merchant_name, market_type, slot, item_id, item_name,
                        count, price, durability, server_channel, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (seller_id, f"Merchant_{seller_id}", mtype, slot, it_id, item_name, count, price, dur, channel, now_str))
                    saved_count += 1
                    
            if saved_count > 0:
                print(f"{C_CYAN}[TEZGAH TIKLANDI]{C_RESET} {mtype} - {saved_count} eşya kaydedildi.")
                return True
        except Exception:
            pass

    return False

def process_raw_packet(raw_hex: str, channel: str = "Zero 1"):
    """TShark'tan gelen ham hex baytlarını işler."""
    try:
        raw_bytes = bytes.fromhex(raw_hex)
        if len(raw_bytes) < 4:
            return
            
        # KO başlığı ve çerçevesi (AA 55 ... 55 AA)
        payload = raw_bytes
        if raw_bytes.startswith(b'\xaa\x55'):
            payload = raw_bytes[2:]
        if payload.endswith(b'\x55\xaa'):
            payload = payload[:-2]
            
        # Sıkıştırma kontrolü (0x42 LibLZF)
        if len(payload) > 13 and payload[0] == 0x42:
            comp_len, decomp_len, crc = struct.unpack_from('<III', payload, 1)
            decompressed = lzf_decompress(payload[13:], decomp_len)
            if decompressed:
                payload = decompressed

        # AES Deşifre
        decrypted = decrypt_packet(payload)
        
        # Pazar paketi mi?
        if len(decrypted) > 0 and decrypted[0] == 0x68:
            parse_merchant_packet(decrypted, channel)
            
    except Exception:
        pass

def find_tshark():
    """Sistemde TShark yolunu tespit eder."""
    candidates = [
        r"C:\Program Files\Wireshark\tshark.exe",
        r"C:\Program Files (x86)\Wireshark\tshark.exe",
        "tshark"
    ]
    for path in candidates:
        try:
            res = subprocess.run([path, "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                return path
        except FileNotFoundError:
            continue
    return None

def check_sniffer_prerequisites():
    """TShark ve Npcap varlığını kontrol eder, eksikse rehber sunar."""
    tshark_bin = find_tshark()
    if not tshark_bin:
        print(f"\n{C_RED}{'='*64}{C_RESET}")
        print(f"{C_BOLD}{C_WHITE} [!] TShark (Wireshark) Bulunamadı!{C_RESET}")
        print(f"{C_RED}{'='*64}{C_RESET}")
        print("Canlı Knight Online pazar paketlerini dinlemek için Wireshark gereklidir.")
        print("\nNasıl Kurulur? (1 Dakika):")
        print("1. https://www.wireshark.org/download.html adresinden Wireshark'ı indirin.")
        print("2. Kurulum ekranında şu kutucukların işaretli olduğundan emin olun:")
        print("   [x] TShark (Command Line Tool)")
        print("   [x] Install Npcap (Paket Yakalama Sürücüsü)")
        print("3. Kurulum tamamlandıktan sonra 'start_sniffer.bat'ı tekrar başlatın.")
        print(f"{C_RED}{'='*64}{C_RESET}\n")
        return None

    # Npcap kontrolü
    try:
        check = subprocess.run([tshark_bin, "-D"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "Unable to load Npcap" in (check.stderr or "") or check.returncode != 0:
            print(f"\n{C_YELLOW}{'='*64}{C_RESET}")
            print(f"{C_BOLD}{C_YELLOW} [!] Npcap Paket Sürücüsü Eksik!{C_RESET}")
            print(f"{C_YELLOW}{'='*64}{C_RESET}")
            print("TShark sisteminizde kurulu fakat Windows ağ paketlerini okumak için Npcap gereklidir.")
            print("\nNasıl Çözülür? (1 Dakika):")
            print("1. https://npcap.com/ adresine gidin ve 'Npcap Installer'ı indirin.")
            print("2. Kurulumda 'Install Npcap in WinPcap API-compatible Mode' kutucuğunu işaretleyin.")
            print("3. Kurulum bitince bu programı tekrar çalıştırın!")
            print(f"{C_YELLOW}{'='*64}{C_RESET}\n")
            return None
    except Exception:
        pass

    return tshark_bin

def start_sniffer(interface=None, port=15001):
    """TShark sürecini başlatarak canlı pazar paketlerini dinler."""
    tshark_bin = check_sniffer_prerequisites()
    if not tshark_bin:
        return

    # Arayüz tespiti
    if not interface:
        interface = os.environ.get("KO_MARKET_INTERFACE", "1")
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            interface = sys.argv[1]

    market_db.init_db()
    print(f"{C_GOLD}===================================================={C_RESET}")
    print(f"{C_BOLD}{C_WHITE}   PeyywadoX — Knight Online Canlı Pazar Dinleyicisi{C_RESET}")
    print(f"{C_GOLD}===================================================={C_RESET}")
    print(f"[*] Dinlenen Portlar: 15001-15200 (TCP)")
    print(f"[*] Ağ Arayüzü: #{interface} | TShark: {tshark_bin}")
    print(f"[*] USKO Menissiah & Pazar paketleri dinleniyor...")
    print(f"[*] Çıkmak için Ctrl+C tuşlarına basabilirsiniz.\n")

    cmd = [
        tshark_bin,
        "-i", str(interface),
        "-f", "tcp and (portrange 15001-15200)",
        "-T", "fields",
        "-e", "data"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        for line in proc.stdout:
            raw_data = line.strip().replace(":", "")
            if raw_data:
                process_raw_packet(raw_data)
    except KeyboardInterrupt:
        print("\n[*] Dinleyici durduruldu.")
    except Exception as e:
        print(f"{C_RED}[HATA] {e}{C_RESET}")

if __name__ == "__main__":
    start_sniffer()
