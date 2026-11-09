@echo off
title ATOM 3D - Apartamento 4A - Laboratorio Cuantitativo XAU/USD (FundingPips 10K)
cd /d "%~dp0"
echo ===========================================================================
echo   ATOM - Apartamento 4A (The Big Bang Theory) - XAU/USD FundingPips 10K
echo   Abriendo Sala 3D Interactiva en http://127.0.0.1:8050 ...
echo ===========================================================================
start "" "http://127.0.0.1:8050"
python ares_server.py
pause
