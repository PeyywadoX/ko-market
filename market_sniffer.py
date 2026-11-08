#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knight Online Pazar Paket Yakalayıcı (ko_market)
-----------------------------------------------
TShark/Npcap üzerinden Knight Online TCP paketlerini dinler:
1. TCPSequenceAssembler ile 1506 baytlık MTU parçalarını (segmentlerini) sıraya koyup birleştirir.
2. \xAA\x55 [len:2] [payload] \x55\xAA paket çerçevesini çözer.
3. Dinamik 0xF2 / 0x2B el sıkışma oturum anahtarını (Session Key) yakalar.
4. USKO AES-128-CBC şifresini (0x01 Session / 0x02 Static) çözer.
5. 0x42 LibLZF sıkıştırmasını açar.
6. Opcode 0x68 Menissiah Pazar Kataloğu (0x30 0x06), Pazar Tezgahları (0x05/0x06),
   Arama Sonuçları (0x23) ve Vitrinleri (0x07) eksiksiz ayrıştırarak market.db'ye yazar.
"""

import sys
import os
import re
import time
import json
import struct
import subprocess
import threading
from collections import defaultdict
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import market_db
import items_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_KEYS_JSON = os.path.join(BASE_DIR, "session_keys.json")

# Kripto Sabitleri (USKO 2626)
AES_STATIC_KEY = struct.pack('<IIII', 0x23E51F87, 0xAD88A178, 0xAA5ECF22, 0x671E185B)
AES_IV = bytes.fromhex('32 4e aa 58 bc b3 ae e3 6b c7 4c 56 36 47 34 f2')
static_cipher = Cipher(algorithms.AES(AES_STATIC_KEY), modes.CBC(AES_IV))

_CIPHER_CACHE = {}
SESSION_KEY = None
dynamic_cipher = None
CLIENT_KEYS = {}
CLIENT_SESSIONS = {}
PENDING_KEY_CANDIDATES = defaultdict(list)

# Renkler
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_GOLD = "\033[38;5;220m"
C_GRAY = "\033[90m"
C_WHITE = "\033[97m"

def _cipher_for(key: bytes):
    if not key or len(key) != 16:
        return None
    if key in _CIPHER_CACHE:
        return _CIPHER_CACHE[key]
    c = Cipher(algorithms.AES(key), modes.CBC(AES_IV))
    _CIPHER_CACHE[key] = c
    return c

def _try_decrypt(cipher_obj, body: bytes):
    """AES-CBC deşifre eder. PKCS7 padding geçerliyse (plaintext, True) döner."""
    if not cipher_obj:
        return b"", False
    try:
        d = cipher_obj.decryptor()
        dec = d.update(body) + d.finalize()
        pad = dec[-1]
        if 1 <= pad <= 16 and dec[-pad:] == bytes([pad] * pad):
            return dec[:-pad], True
        return dec, False
    except Exception:
        return b"", False

def load_session_keys():
    """Kayıtlı oturum anahtarlarını JSON dosyasından yükler."""
    global SESSION_KEY, dynamic_cipher
    if os.path.exists(SESSION_KEYS_JSON):
        try:
            with open(SESSION_KEYS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ip, cinfo in data.get("clients", {}).items():
                hex_k = cinfo.get("key")
                if hex_k and len(hex_k) == 32:
                    kb = bytes.fromhex(hex_k)
                    CLIENT_KEYS[ip] = kb
                    CLIENT_SESSIONS[ip] = _cipher_for(kb)
            last_k = data.get("last_key")
            if last_k and len(last_k) == 32:
                SESSION_KEY = bytes.fromhex(last_k)
                dynamic_cipher = _cipher_for(SESSION_KEY)
                print(f"[*] Kayıtlı oturum anahtarı yüklendi: {last_k[:8]}...{last_k[-8:]}")
        except Exception as e:
            pass

def save_session_key(key_bytes: bytes, stream_id: int = 0, client_ip: str = ""):
    """Doğrulanmış oturum anahtarını kaydeder."""
    global SESSION_KEY, dynamic_cipher
    if not key_bytes or len(key_bytes) != 16:
        return
    SESSION_KEY = key_bytes
    dynamic_cipher = _cipher_for(key_bytes)
    if client_ip:
        CLIENT_KEYS[client_ip] = key_bytes
        CLIENT_SESSIONS[client_ip] = dynamic_cipher

    try:
        j_data = {"last_key": key_bytes.hex(), "clients": {}}
        if os.path.exists(SESSION_KEYS_JSON):
            try:
                with open(SESSION_KEYS_JSON, "r", encoding="utf-8") as f:
                    j_data = json.load(f)
            except Exception:
                pass
        j_data["last_key"] = key_bytes.hex()
        if client_ip:
            if not isinstance(j_data.get("clients"), dict):
                j_data["clients"] = {}
            j_data["clients"][client_ip] = {
                "key": key_bytes.hex(),
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        with open(SESSION_KEYS_JSON, "w", encoding="utf-8") as f:
            json.dump(j_data, f, indent=2)
    except Exception:
        pass
    print(f"\n{C_BOLD}{C_GREEN}[OK] OYUN OTURUM ANAHTARI YAKALANDI: {key_bytes.hex()}{C_RESET}\n", flush=True)

def _queue_key_candidate(stream_id: int, cand: bytes):
    if not cand or len(cand) != 16:
        return
    lst = PENDING_KEY_CANDIDATES[stream_id]
    if cand not in lst:
        lst.append(cand)
        if len(lst) > 8:
            lst.pop(0)

def decode_text(raw_bytes: bytes) -> str:
    """Türkçe ve CP1254 karakterleri temiz çözer."""
    if not raw_bytes:
        return ""
    for enc in ('cp1254', 'utf-8', 'iso-8859-9', 'ascii'):
        try:
            txt = raw_bytes.decode(enc).strip('\x00').strip()
            if txt:
                return txt
        except Exception:
            continue
    return "".join(chr(b) for b in raw_bytes if 32 <= b <= 126).strip()

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
                length += 2
                if i >= in_len: return b""
                ref_offset |= data[i]
                i += 1
                ref_pos = len(out) - ref_offset - 1
                if ref_pos < 0: return b""
                if len(out) + length > expected_len: return b""
                for _ in range(length):
                    out.append(out[ref_pos])
                    ref_pos += 1
            if len(out) > expected_len:
                return b""
        return bytes(out) if len(out) == expected_len else b""
    except Exception:
        return b""

class TCPSequenceAssembler:
    """TCP segmentlerini sıraya koyar, 1506 baytlık MTU parçalarını eksiksiz birleştirir."""
    _SEQ_MOD = 1 << 32
    _SEQ_MASK = _SEQ_MOD - 1
    _SEQ_HALF = 1 << 31

    def __init__(self, max_pending=128, max_pending_bytes=4 * 1024 * 1024, gap_timeout=3.0):
        self.next_seq = None
        self.pending = {}
        self.max_pending = max_pending
        self.max_pending_bytes = max_pending_bytes
        self.pending_bytes = 0
        self.gap_timeout = gap_timeout
        self.gap_since = None
        self.discontinuity = False

    @classmethod
    def _normalize_seq(cls, seq: int, reference: int) -> int:
        if seq > cls._SEQ_MASK:
            return seq
        delta = (seq - (reference & cls._SEQ_MASK)) & cls._SEQ_MASK
        if delta >= cls._SEQ_HALF:
            delta -= cls._SEQ_MOD
        return reference + delta

    def _recover_at(self, seq: int, payload: bytes) -> bytes:
        self.pending.clear()
        self.pending_bytes = 0
        self.gap_since = None
        self.next_seq = seq + len(payload)
        self.discontinuity = True
        return payload

    def feed(self, seq: int, payload: bytes) -> bytes:
        self.discontinuity = False
        if not payload or not isinstance(seq, int) or seq < 0:
            return b""
        if self.next_seq is None:
            self.next_seq = seq + len(payload)
            return payload
        seq = self._normalize_seq(seq, self.next_seq)
        if seq > self.next_seq:
            now = time.monotonic()
            if self.pending and self.gap_since is not None and now - self.gap_since >= self.gap_timeout:
                return self._recover_at(seq, payload)
            previous = self.pending.get(seq)
            if previous is None or len(payload) > len(previous):
                old_size = len(previous) if previous is not None else 0
                self.pending[seq] = payload
                self.pending_bytes += len(payload) - old_size
                if previous is None and self.gap_since is None:
                    self.gap_since = now
            if len(self.pending) > self.max_pending or self.pending_bytes > self.max_pending_bytes:
                return self._recover_at(seq, payload)
            return b""
        overlap = self.next_seq - seq
        if overlap >= len(payload):
            return b""
        chunks = [payload[overlap:]]
        self.next_seq += len(payload) - overlap
        if not self.pending:
            self.gap_since = None
        while self.pending:
            avail = [s for s in self.pending if s <= self.next_seq]
            if not avail: break
            start = min(avail)
            piece = self.pending.pop(start)
            self.pending_bytes -= len(piece)
            ov = self.next_seq - start
            if ov < len(piece):
                chunks.append(piece[ov:])
                self.next_seq += len(piece) - ov
        self.gap_since = time.monotonic() if self.pending else None
        return b"".join(chunks)

def decrypt_ko_aes(payload: bytes, stream_id: int = 0, client_ip: str = "") -> bytes:
    """USKO 2626 AES çözücü. 0x02=statik anahtar, 0x01=oturum anahtarı."""
    if len(payload) < 17 or (len(payload) & 0x0F) != 1 or payload[0] not in (1, 2):
        return payload
    body = payload[1:]

    # Statik Anahtar (0x02)
    if payload[0] == 2:
        plain, _ok = _try_decrypt(static_cipher, body)
        return plain if plain else payload

    # Dinamik Oturum Anahtarı (0x01)
    if dynamic_cipher:
        plain, ok = _try_decrypt(dynamic_cipher, body)
        if ok and plain:
            return plain

    if client_ip and client_ip in CLIENT_SESSIONS:
        plain, ok = _try_decrypt(CLIENT_SESSIONS[client_ip], body)
        if ok and plain:
            return plain

    # Aday anahtarları dene
    for cand in list(PENDING_KEY_CANDIDATES.get(stream_id, [])):
        c = _cipher_for(cand)
        if c:
            plain, ok = _try_decrypt(c, body)
            if ok and plain:
                save_session_key(cand, stream_id=stream_id, client_ip=client_ip)
                return plain

    for ip, k in CLIENT_KEYS.items():
        c = _cipher_for(k)
        if c:
            plain, ok = _try_decrypt(c, body)
            if ok and plain:
                save_session_key(k, stream_id=stream_id, client_ip=client_ip)
                return plain

    return payload

def parse_menissiah_supermarket(data: bytes, direction: str, now_str: str, server_channel: str = "Zero 1"):
    """
    Opcode 0x68 Subtype 0x30: USKO 2626 Menissiah Official List / Kaishan
    Tersine Mühendislik Kaynağı: KnightOnlineUnpack.exe (sub_DEA940 / UISupermaketMain.cpp)
    """
    if len(data) < 3 or data[0] != 0x68 or data[1] != 0x30:
        return False

    sub_sub = data[2]

    # Menissiah Scroll Açılış / Yetki Onayı
    if sub_sub == 0x05:
        if "CLIENT -> SERVER" in direction:
            print(f"[{now_str}] 📜 {C_GOLD}[Menissiah Scroll Açıldı]{C_RESET} İstek Gönderildi", flush=True)
        else:
            res = data[3] if len(data) > 3 else 0
            res_str = "BAŞARILI" if res == 1 else f"Hata ({res})"
            print(f"[{now_str}] 📜 {C_GREEN}[Menissiah Yetkisi Doğrulandı]{C_RESET} Durum: {res_str}", flush=True)
        return True

    # Menissiah Tüm Pazar Kataloğu (sub_DEA940)
    elif sub_sub == 0x06:
        if "CLIENT -> SERVER" in direction:
            return True

        try:
            offset = 3
            if offset + 1 > len(data): return False
            result_code = data[offset]; offset += 1
            if result_code == 0:
                print(f"[{now_str}] ⚠️ [Menissiah] Sunucu pazar verisi bulunamadı dedi.", flush=True)
                return True

            if offset + 6 > len(data): return False
            total_items = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
            merchant_count = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2

            parsed_items = []
            for m_idx in range(merchant_count):
                if offset + 5 > len(data): break
                seller_id = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                n_len = data[offset]; offset += 1
                if offset + n_len + 1 > len(data): break
                seller_name = decode_text(data[offset:offset + n_len]) if n_len else f"Merchant_{seller_id}"
                offset += n_len
                market_type_byte = data[offset]; offset += 1
                mtype = "BUY" if market_type_byte == 1 else "SELL"

                if offset + 12 * 8 > len(data): break
                for slot_idx in range(12):
                    item_id = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                    price = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                    if item_id > 0 and price > 0:
                        iname = items_db.resolve_item_name(item_id)
                        parsed_items.append({
                            "merchant_id": seller_id,
                            "merchant_name": seller_name,
                            "merchant_title": "",
                            "market_type": mtype,
                            "slot": slot_idx,
                            "item_id": item_id,
                            "item_name": iname,
                            "count": 1,
                            "price": price,
                            "durability": 100,
                            "server_channel": server_channel,
                            "location_name": "Moradon",
                            "merchant_x": 0.0,
                            "merchant_z": 0.0,
                        })

            if parsed_items:
                print(f"\n{C_BOLD}{C_GOLD}╔══════════════════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
                print(f"{C_BOLD}{C_GOLD}║  🌟 [{server_channel}] MENİSSİAH CANLI PAZAR PAKETİ ALINDI! [{now_str}]                 ║{C_RESET}")
                print(f"{C_BOLD}{C_GOLD}╠══════════════════════════════════════════════════════════════════════════════════════════════╣{C_RESET}")
                print(f"║  Tezgah Sayısı: {C_BOLD}{merchant_count}{C_RESET} | Ayrıştırılan Eşya: {C_BOLD}{len(parsed_items)}{C_RESET} (Sunucu Toplamı: {total_items})")
                print(f"{C_BOLD}{C_GOLD}╚══════════════════════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n", flush=True)

                market_db.replace_market_catalog(server_channel, parsed_items)
                print(f"║  ✅ {C_GREEN}{C_BOLD}[{server_channel}] Pazar Kataloğu Veritabanına Yazıldı ({len(parsed_items)} Eşya){C_RESET}\n", flush=True)
                return True
        except Exception as e:
            print(f"[{now_str}] ⚠️ Menissiah 0x30 0x06 Ayrıştırma Hatası: {e}", flush=True)
            return True

    return False

def parse_merchant(data: bytes, direction: str, now_str: str, server_channel: str = "Zero 1"):
    """Opcode 0x68 (WIZ_MERCHANT): Menissiah, Tezgah Tıklama ve Vitrinler."""
    if len(data) < 2 or data[0] != 0x68:
        return False

    sub_type = data[1]

    # 1. Menissiah Kataloğu
    if sub_type == 0x30:
        return parse_menissiah_supermarket(data, direction, now_str, server_channel)

    # 2. Pazar Tezgahına Tıklama (12 Slot x 16 Bayt)
    elif sub_type in (0x05, 0x06):
        try:
            if len(data) >= 8:
                offset = 2
                res = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2
                if res != 1: return True
                seller_id = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                seller_name = f"Merchant_{seller_id}"
                mtype = "SELL" if sub_type == 5 else "BUY"

                stall_items = []
                for s_idx in range(12):
                    if offset + 16 > len(data): break
                    item_id = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                    count = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2
                    dur = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2
                    price = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4
                    serial = struct.unpack('<I', data[offset:offset + 4])[0]; offset += 4

                    if item_id > 0:
                        iname = items_db.resolve_item_name(item_id)
                        stall_items.append((s_idx + 1, iname, count, price))
                        market_db.insert_market_item({
                            "merchant_id": seller_id,
                            "merchant_name": seller_name,
                            "merchant_title": "",
                            "market_type": mtype,
                            "slot": s_idx,
                            "item_id": item_id,
                            "item_name": iname,
                            "count": max(1, count),
                            "price": price,
                            "durability": dur,
                            "server_channel": server_channel,
                            "location_name": "Moradon",
                            "merchant_x": 0.0,
                            "merchant_z": 0.0,
                        })

                if stall_items:
                    print(f"\n{C_BOLD}{C_GREEN}🏪 PAZAR TEZGAHI AÇILDI: {seller_name} ({mtype}) | {len(stall_items)} Eşya{C_RESET}")
                    for s_num, iname, cnt, prc in stall_items:
                        print(f"  Slot {s_num:02d}: {iname} x{cnt} | {prc:,} Coin")
                    return True
        except Exception:
            pass

    # 3. Pazar Vitrini ve Başlığı
    elif sub_type == 0x07:
        try:
            if len(data) >= 4:
                offset = 2
                res = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2
                if res == 1 and offset + 2 <= len(data):
                    t_len = struct.unpack('<H', data[offset:offset + 2])[0]; offset += 2
                    if 0 < t_len <= 64 and offset + t_len <= len(data):
                        title = decode_text(data[offset:offset + t_len])
                        if title:
                            print(f"[{now_str}] 📢 {C_CYAN}Pazar Başlığı:{C_RESET} {title}")
                            return True
        except Exception:
            pass

    # 4. Menissiah Buy Store Arama Sonuçları
    elif sub_type == 0x23:
        try:
            if len(data) >= 4:
                count = data[2]
                offset = 3
                print(f"[{now_str}] 🔍 {C_GOLD}[Menissiah Arama Listesi Alındı]{C_RESET} {count} Eşya", flush=True)
                return True
        except Exception:
            pass

    return False

def process_single_packet(packet: bytes, direction: str, now_str: str, server_channel: str = "Zero 1", stream_id: int = 0, client_ip: str = ""):
    """Paketi deşifre eder, sıkıştırmayı açar ve uygun dedektöre yönlendirir."""
    if len(packet) == 0:
        return

    # 0. Dinamik Oturum Anahtarı Adayı (0xF2 / 0x2B El Sıkışma)
    if "SERVER" in direction and len(packet) >= 18:
        if packet[0] == 0xF2:
            k_len = packet[1]
            if k_len == 16 and len(packet) >= 2 + k_len:
                _queue_key_candidate(stream_id, packet[2:2 + k_len])
        elif packet[0] == 0x2B:
            for off in range(1, min(10, len(packet) - 17)):
                if packet[off] == 16:
                    _queue_key_candidate(stream_id, packet[off + 1:off + 17])

    # 1. AES Şifre Çözümü
    decrypted = decrypt_ko_aes(packet, stream_id, client_ip)
    if not decrypted:
        return

    # 2. Sıkıştırılmış Paket (0x42 LibLZF)
    if decrypted[0] == 0x42 and len(decrypted) >= 9:
        try:
            comp_len = struct.unpack('<I', decrypted[1:5])[0]
            decomp_len = struct.unpack('<I', decrypted[5:9])[0]
            inner = None
            if len(decrypted) >= 13 + comp_len:
                inner = lzf_decompress(decrypted[13:13 + comp_len], decomp_len)
            elif len(decrypted) >= 9 + comp_len:
                inner = lzf_decompress(decrypted[9:9 + comp_len], decomp_len)
            if inner:
                process_single_packet(inner, direction, now_str, server_channel, stream_id, client_ip)
                return
        except Exception:
            pass

    # 3. Pazar Paketleri (Opcode 0x68)
    if decrypted[0] == 0x68:
        parse_merchant(decrypted, direction, now_str, server_channel)

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
    """TShark ve Npcap varlığını kontrol eder."""
    tshark_bin = find_tshark()
    if not tshark_bin:
        print(f"\n{C_RED}{'='*64}{C_RESET}")
        print(f"{C_BOLD}{C_WHITE} [!] TShark (Wireshark) Bulunamadı!{C_RESET}")
        print(f"{C_RED}{'='*64}{C_RESET}")
        print("Canlı Knight Online pazar paketlerini dinlemek için Wireshark gereklidir.")
        print("1. https://www.wireshark.org/download.html adresinden Wireshark'ı indirin.")
        print("2. Kurulumda TShark ve Npcap seçeneklerini işaretleyin.")
        print(f"{C_RED}{'='*64}{C_RESET}\n")
        return None

    try:
        check = subprocess.run([tshark_bin, "-D"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "Unable to load Npcap" in (check.stderr or "") or check.returncode != 0:
            print(f"\n{C_YELLOW}{'='*64}{C_RESET}")
            print(f"{C_BOLD}{C_YELLOW} [!] Npcap Paket Sürücüsü Eksik!{C_RESET}")
            print(f"{C_YELLOW}{'='*64}{C_RESET}")
            print("https://npcap.com/ adresinden Npcap Installer indirin ve WinPcap API modunda kurun.")
            print(f"{C_YELLOW}{'='*64}{C_RESET}\n")
            return None
    except Exception:
        pass

    return tshark_bin

def start_sniffer(interface=None):
    """TShark sürecini başlatarak canlı pazar paketlerini dinler."""
    tshark_bin = check_sniffer_prerequisites()
    if not tshark_bin:
        return

    load_session_keys()
    market_db.init_db()

    if not interface:
        interface = os.environ.get("KO_MARKET_INTERFACE", "1")
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            interface = sys.argv[1]

    print(f"\n{C_GOLD}================================================================{C_RESET}")
    print(f"{C_BOLD}{C_WHITE}   PeyywadoX Market — Knight Online Canlı Pazar Dinleyicisi{C_RESET}")
    print(f"{C_GOLD}================================================================{C_RESET}")
    print(f"[*] Dinlenen Portlar: 15001-15200 (TCP)")
    print(f"[*] Ağ Arayüzü: #{interface} | TShark: {tshark_bin}")
    print(f"[*] Menissiah & Pazar Paketleri Dinleniyor...")
    print(f"[*] Önemli İpucu: Karakter seçimine çıkıp tekrar girmeniz veya")
    print(f"    gate'ten geçmeniz durumunda oturum anahtarı otomatik yakalanır.")
    print(f"[*] Çıkmak için Ctrl+C tuşlarına basabilirsiniz.\n")

    cmd = [
        tshark_bin,
        "-i", str(interface),
        "-l", "-n",
        "-f", "tcp and (portrange 15001-15200)",
        "-o", "tcp.relative_sequence_numbers:FALSE",
        "-T", "fields",
        "-e", "tcp.stream",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "tcp.seq",
        "-e", "tcp.payload"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        stream_buffers = defaultdict(bytearray)
        stream_assemblers = {}

        for line in proc.stdout:
            parts = line.strip().split("\t")
            if len(parts) < 7 or not parts[6]:
                continue

            stream_id_str, src_ip, dst_ip, src_port, dst_port, tcp_seq, raw_hex = parts[:7]
            try:
                raw_chunk = bytes.fromhex(raw_hex)
                stream_id = int(stream_id_str)
                seq = int(tcp_seq)
                s_port_int = int(src_port)
                d_port_int = int(dst_port)
            except Exception:
                continue

            if not raw_chunk:
                continue

            is_server = (15000 <= s_port_int <= 15200)
            client_ip = dst_ip if is_server else src_ip
            direction = f"SERVER({src_port}) -> CLIENT" if is_server else f"CLIENT -> SERVER({dst_port})"
            now_str = datetime.now().strftime("%H:%M:%S")

            # TCP Akış Montajı & Segment Birleştirme
            s_key = (stream_id, src_ip, dst_ip, s_port_int, d_port_int)
            s_buf = stream_buffers[s_key]
            assembler = stream_assemblers.setdefault(s_key, TCPSequenceAssembler())
            contiguous = assembler.feed(seq, raw_chunk)
            if assembler.discontinuity:
                s_buf.clear()
            if not contiguous:
                continue
            s_buf.extend(contiguous)

            # KO Çerçeveleme: \xAA\x55 [len:2] [payload] \x55\xAA
            while True:
                start_pos = s_buf.find(b'\xAA\x55')
                if start_pos == -1:
                    if len(s_buf) > 131072:
                        stream_buffers[s_key] = s_buf[-1024:]
                    break

                if len(s_buf) < start_pos + 4:
                    break

                frame_len = s_buf[start_pos + 2] | (s_buf[start_pos + 3] << 8)
                frame_end = start_pos + 4 + frame_len + 2

                if len(s_buf) < frame_end:
                    break

                if s_buf[frame_end - 2:frame_end] == b'\x55\xAA':
                    payload = bytes(s_buf[start_pos + 4:start_pos + 4 + frame_len])
                    stream_buffers[s_key] = s_buf[frame_end:]
                    s_buf = stream_buffers[s_key]

                    process_single_packet(payload, direction, now_str, "Zero 1", stream_id, client_ip)
                else:
                    stream_buffers[s_key] = s_buf[start_pos + 1:]
                    s_buf = stream_buffers[s_key]

    except KeyboardInterrupt:
        print("\n[*] Dinleyici kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"{C_RED}[HATA] {e}{C_RESET}")

if __name__ == "__main__":
    start_sniffer()
