@echo off
chcp 65001 > nul
title KO Market - Web Sunucusu
echo ==========================================================
echo   Knight Online Canli Pazar ve Arbitraj Sunucusu
echo ==========================================================
echo.
echo Sunucu baslatiliyor...
echo Web Arayuzu: http://127.0.0.1:5000/
echo JSON Feed:   http://127.0.0.1:5000/api/feed
echo.
python app.py
pause
