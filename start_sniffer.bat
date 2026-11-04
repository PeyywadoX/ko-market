@echo off
chcp 65001 > nul
title KO Market - Paket Yakalayici (Sniffer)
echo ==========================================================
echo   Knight Online Canli Pazar Paket Yakalayici (TShark)
echo ==========================================================
echo.
echo Paket dinleme baslatiliyor...
echo.
python market_sniffer.py
pause
