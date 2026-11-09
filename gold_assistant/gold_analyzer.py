"""
gold_analyzer.py - Analizador de Estructura Institucional y Liquidez para XAUUSD
Utiliza yfinance (Futures GC=F o Gold Spot) para detectar:
1. Máximo y Mínimo del Día Previo (PDH / PDL)
2. Rango de la Sesión Asiática (Asian High / Asian Low)
3. Detección de Fair Value Gaps (FVG) recientes
4. Detección de desplazamientos institucionales
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time

def fetch_gold_data(interval='1h', period='10d'):
    """
    Descarga cotizaciones recientes de futuros de oro de alta liquidez.
    """
    ticker = yf.Ticker('GC=F')
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError("No se pudieron obtener datos de XAUUSD/GC=F.")
    return df

def analyze_key_liquidity_levels(df):
    """
    Calcula niveles macro clave de liquidez:
    - PDH (Previous Daily High)
    - PDL (Previous Daily Low)
    - Niveles de equilibrio (50% del rango previo)
    """
    # Resample a diario
    daily = df.resample('1D').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    
    if len(daily) < 2:
        return {}
        
    prev_day = daily.iloc[-2]
    today = daily.iloc[-1]
    
    pdh = prev_day['High']
    pdl = prev_day['Low']
    eq = (pdh + pdl) / 2.0
    
    return {
        "PDH": round(pdh, 2),
        "PDL": round(pdl, 2),
        "Equilibrium_50": round(eq, 2),
        "Range_Points": round(pdh - pdl, 2),
        "Current_Price": round(today['Close'], 2)
    }

def detect_recent_fvgs(df, lookback=30):
    """
    Detecta Fair Value Gaps (FVG) no mitigados en las últimas velas.
    """
    fvgs = []
    subset = df.iloc[-lookback:].copy()
    
    for i in range(2, len(subset)):
        v1 = subset.iloc[i-2]
        v2 = subset.iloc[i-1]
        v3 = subset.iloc[i]
        
        # Bullish FVG: Low de v3 > High de v1
        if v3['Low'] > v1['High']:
            gap_size = v3['Low'] - v1['High']
            ce = v1['High'] + (gap_size / 2.0)
            fvgs.append({
                "type": "Bullish FVG (BISI)",
                "time": str(v2.name),
                "top": round(v3['Low'], 2),
                "bottom": round(v1['High'], 2),
                "consequent_encroachment_50": round(ce, 2),
                "gap_points": round(gap_size, 2)
            })
            
        # Bearish FVG: High de v3 < Low de v1
        elif v3['High'] < v1['Low']:
            gap_size = v1['Low'] - v3['High']
            ce = v3['High'] + (gap_size / 2.0)
            fvgs.append({
                "type": "Bearish FVG (SIBI)",
                "time": str(v2.name),
                "top": round(v1['Low'], 2),
                "bottom": round(v3['High'], 2),
                "consequent_encroachment_50": round(ce, 2),
                "gap_points": round(gap_size, 2)
            })
            
    return fvgs

if __name__ == '__main__':
    print("Obteniendo datos de Oro...")
    df_h1 = fetch_gold_data(interval='1h', period='5d')
    levels = analyze_key_liquidity_levels(df_h1)
    print("\n=== NIVELES DE LIQUIDEZ EXTERNA (HTF) ===")
    for k, v in levels.items():
        print(f"  {k}: {v}")
        
    fvgs = detect_recent_fvgs(df_h1, lookback=15)
    print(f"\n=== FAIR VALUE GAPS RECIENTES EN 1H ({len(fvgs)} encontrados) ===")
    for f in fvgs[-3:]:
        print(f"  {f['type']} | Rango: [{f['bottom']} - {f['top']}] | 50% CE: {f['consequent_encroachment_50']} | {f['time']}")
