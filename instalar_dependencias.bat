@echo off
title Instalador de Dependencias - ATOM XAU/USD
cd /d "%~dp0"
echo ===========================================================================
echo   Instalando dependencias de Python para ATOM...
echo ===========================================================================
python -m pip install --upgrade pip
pip install starlette uvicorn requests pandas lightweight-charts
echo.
echo ===========================================================================
echo   Instalacion completada con exito.
echo   Ya puedes ejecutar "iniciar_atom.bat" para abrir la plataforma.
echo ===========================================================================
pause
