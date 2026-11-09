@echo off
title AUREUS - Asistente Cuantitativo en Oro (FundingPips 10K)
color 0A
echo =====================================================================
echo           INICIANDO AUREUS DASHBOARD INTERACTIVO (XAU/USD)
echo                  FundingPips $10,000 USD · SMC / ICT
echo =====================================================================
echo.
echo Abriendo servidor local en tu navegador por defecto...
cd /d "%~dp0"
python -m streamlit run dashboard_app.py --server.port 8501 --browser.gatherUsageStats false
pause
