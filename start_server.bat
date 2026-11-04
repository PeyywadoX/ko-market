@echo off
chcp 65001 > nul
title PeyywadoX Market - Web Sunucusu
cls
echo ==========================================================
echo    PeyywadoX Market - Knight Online Canli Pazar Sunucusu
echo ==========================================================
echo.

:: Python tespit (venv öncelikli)
if exist "venv\Scripts\python.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

echo Sunucu baslatiliyor...
echo Web Arayuzu: http://127.0.0.1:5000/
echo JSON Feed:   http://127.0.0.1:5000/api/feed
echo Arbitraj:    http://127.0.0.1:5000/api/arbitrage
echo.

%PY_BIN% app.py
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Sunucu baslatilamadi!
    echo Lutfen once "kurulum.bat" calistirarak gereksinimleri yukleyin.
    echo.
)
pause
