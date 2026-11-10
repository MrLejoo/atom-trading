@echo off
title Subir ATOM a GitHub (MrLejoo/atom-trading)
cd /d "%~dp0"
cls
echo ===========================================================================
echo            ATOM v3.0 - SINCRONIZADOR CON GITHUB
echo ===========================================================================
echo.
echo Repositorio destino: https://github.com/MrLejoo/atom-trading.git
echo Rama actual: main
echo.
echo 1. Si aun no creaste el repositorio en GitHub:
echo    Entra a https://github.com/new y crealo con el nombre: atom-trading (Vacio)
echo.
echo 2. Subiendo todos los cambios y documentacion actualizada...
echo ===========================================================================
echo.
git push -u origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo [EXITO] Tu proyecto ATOM esta 100%% actualizado en GitHub.
    echo Ahora puedes clonarlo en tu otra computadora sin perder nada.
) else (
    echo [AVISO] Si te pidio inicio de sesion, completa el acceso en tu navegador.
    echo Si el repositorio no existe, crealo primero en https://github.com/new
)
echo.
echo ===========================================================================
pause
