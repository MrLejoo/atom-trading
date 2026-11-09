@echo off
title Subir ATOM a GitHub
cd /d "%~dp0"
echo ===========================================================================
echo   Subiendo proyecto ATOM a https://github.com/MrLejoo/atom-trading.git
echo ===========================================================================
echo.
git push -u origin main
echo.
echo ===========================================================================
echo   Listo! Presiona cualquier tecla para cerrar esta ventana.
echo ===========================================================================
pause
