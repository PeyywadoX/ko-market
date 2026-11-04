@echo off
chcp 65001 > nul
title PeyywadoX Market - Otomatik Kurulum Sihirbazi
cls
echo ==========================================================
echo    PeyywadoX Market - Knight Online Canli Pazar Sistemi
echo             OTOMATIK KURULUM SIHIRBAZI
echo ==========================================================
echo.

:: 1. Python Kontrolü
python --version > nul 2>&1
if errorlevel 1 (
    echo [HATA] Sisteminizde Python bulunamadi!
    echo.
    echo Lutfen Python 3.10 veya uzeri bir surum yukleyin:
    echo https://www.python.org/downloads/
    echo.
    echo ONEMLI: Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin!
    echo.
    pause
    exit /b 1
)

echo [1/4] Python bulundu:
python --version
echo.

:: 2. Sanal Ortam (venv) Olusturma
echo [2/4] Python Sanal Ortami hazirlaniyor...
if not exist "venv\Scripts\python.exe" (
    python -m venv venv
    echo       Sanal ortam basariyla olusturuldu: venv
) else (
    echo       Mevcut sanal ortam kullaniliyor: venv
)
echo.

:: 3. Bagimliliklari Yukleme
echo [3/4] Gerekli kutuphaneler yukleniyor: Flask, Cryptography...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m pip install --upgrade pip > nul 2>&1
    venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
    python -m pip install --upgrade pip > nul 2>&1
    python -m pip install -r requirements.txt
)
if errorlevel 1 (
    echo [HATA] Paketler yuklenirken bir sorun olustu.
    pause
    exit /b 1
)
echo       Kutuphaneler eksiksiz yuklendi.
echo.

:: 4. Veritabanı ve Örnek Veri Kontrolü
echo [4/4] Veritabani ve USKO esya katalogu hazirlaniyor...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import market_db; market_db.init_db(); market_db.seed_sample_data()"
) else (
    python -c "import market_db; market_db.init_db(); market_db.seed_sample_data()"
)
echo       Veritabani basariyla hazirlandi.
echo.

:: Wireshark / TShark Kontrolü
echo ==========================================================
echo          CANLI PAKET DINLEME (TSHARK) DURUMU
echo ==========================================================
if exist "C:\Program Files\Wireshark\tshark.exe" (
    echo [OK] Wireshark ve TShark bulundu: C:\Program Files\Wireshark\tshark.exe
) else (
    echo [BILGI] Oyundan canli paket yakalamak istiyorsaniz:
    echo         Wireshark ve Npcap yuklemelisiniz:
    echo         https://www.wireshark.org/download.html
    echo         Not: Sadece web paneli ve JSON feed icin Wireshark gerekmez.
)
echo ==========================================================
echo.
echo [TEBRIKLER] Kurulum basariyla tamamlandi!
echo.
echo Sistemi baslatmak icin:
echo   1. Web Arayuzu ve JSON Feed: start_server.bat
echo   2. Canli Paket Dinleyici:    start_sniffer.bat
echo.
pause
