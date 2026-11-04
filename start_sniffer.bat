@echo off
chcp 65001 > nul
title PeyywadoX Market - Paket Yakalayici (Sniffer)
cls
echo ==========================================================
echo    PeyywadoX Market - Canli Pazar Paket Yakalayici (TShark)
echo ==========================================================
echo.

:: Python tespit (venv öncelikli)
if exist "venv\Scripts\python.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

%PY_BIN% market_sniffer.py
if %errorlevel% neq 0 (
    echo.
    echo [BILGI] Dinleyici sonlandirildi veya bir sorun olustu.
    echo Lutfen once "kurulum.bat" calistirdiginizdan emin olun.
    echo.
)
pause
