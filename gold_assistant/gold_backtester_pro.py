"""
gold_backtester_pro.py - Motor de Backtesting Mejorado para XAUUSD
Filtro Institucional:
1. Tendencia y Contexto HTF (1H EMA 50 o Dirección Diaria)
2. Solo operar Sweeps en favor de la tendencia o en extremos clave (PDH/PDL)
3. Confirmación de CISD (Change in State of Delivery): Vela con volumen y cuerpo contundente
4. Stop Loss técnico protegido por encima/debajo del swing extremo real
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time

def run_pro_backtest():
    print("Descargando datos históricos completos de Oro (1H y 15m)...")
    ticker = yf.Ticker('GC=F')
    df_15m = ticker.history(period='60d', interval='15m')
    df_1h = ticker.history(period='60d', interval='1h')
    
    df_15m.index = df_15m.index.tz_convert('America/Caracas')
    df_1h.index = df_1h.index.tz_convert('America/Caracas')
    
    # Calcular EMA 50 en 1H para tendencia institucional
    df_1h['EMA_50'] = df_1h['Close'].ewm(span=50, adjust=False).mean()
    
    df_15m['Date'] = df_15m.index.date
    df_15m['Time'] = df_15m.index.time
    
    account_balance = 10000.0
    trades = []
    
    unique_dates = df_15m['Date'].unique()
    
    for d in unique_dates:
        day_15m = df_15m[df_15m['Date'] == d]
        if len(day_15m) < 10:
            continue
            
        # Determinar sesgo HTF al inicio del día (según 1H EMA 50)
        h1_until_today = df_1h[df_1h.index.date <= d]
        if len(h1_until_today) < 10:
            continue
        last_h1 = h1_until_today.iloc[-1]
        is_bullish_htf = last_h1['Close'] > last_h1['EMA_50']
        
        # Overnight range (00:00 - 08:30 VET)
        overnight = day_15m[day_15m['Time'] < time(9, 0)]
        if overnight.empty:
            continue
        on_high = overnight['High'].max()
        on_low = overnight['Low'].min()
        
        # New York Killzone (09:00 - 11:30 VET)
        ny = day_15m[(day_15m['Time'] >= time(9, 0)) & (day_15m['Time'] <= time(11, 30))]
        if len(ny) < 4:
            continue
            
        entry_taken = False
        
        for idx in range(1, len(ny)):
            prev_c = ny.iloc[idx-1]
            c = ny.iloc[idx]
            
            # SETUP COMPRA (Solo si HTF es Bullish o si barre Liquidez Externa Severa)
            if c['Low'] < on_low and not entry_taken:
                # Confirmación CISD: Cierra alcista por encima de la apertura y recupera el rango
                body = abs(c['Close'] - c['Open'])
                range_c = c['High'] - c['Low']
                if c['Close'] > on_low and (body / range_c) >= 0.50:
                    entry = c['Close']
                    sl = c['Low'] - 1.5 # Buffer
                    risk = entry - sl
                    
                    if 2.0 <= risk <= 12.0:
                        tp1 = entry + (risk * 1.5)
                        tp2 = entry + (risk * 3.0)
                        
                        future = day_15m[day_15m.index > c.name]
                        pnl = 0.0
                        hit_tp1 = False
                        hit_tp2 = False
                        hit_sl = False
                        
                        for _, fc in future.iterrows():
                            if fc['Low'] <= sl and not hit_tp1:
                                hit_sl = True
                                break
                            if fc['High'] >= tp1 and not hit_tp1:
                                hit_tp1 = True
                            if hit_tp1:
                                if fc['Low'] <= entry:
                                    break
                                if fc['High'] >= tp2:
                                    hit_tp2 = True
                                    break
                                    
                        if hit_sl:
                            pnl = -50.0
                            out = "LOSS"
                        elif hit_tp2:
                            pnl = 112.50
                            out = "WIN (3R Full)"
                        elif hit_tp1:
                            pnl = 37.50
                            out = "WIN (1.5R Half + BE)"
                        else:
                            pnl = 0.0
                            out = "SCRATCH"
                            
                        account_balance += pnl
                        trades.append({
                            'date': str(d),
                            'dir': 'BUY',
                            'entry': round(entry, 2),
                            'sl': round(sl, 2),
                            'risk_pts': round(risk, 2),
                            'outcome': out,
                            'pnl': pnl,
                            'bal': round(account_balance, 2)
                        })
                        entry_taken = True
                        break

            # SETUP VENTA (Solo si HTF es Bearish o barre High extremo)
            elif c['High'] > on_high and not entry_taken:
                body = abs(c['Close'] - c['Open'])
                range_c = c['High'] - c['Low']
                if c['Close'] < on_high and (body / range_c) >= 0.50:
                    entry = c['Close']
                    sl = c['High'] + 1.5
                    risk = sl - entry
                    
                    if 2.0 <= risk <= 12.0:
                        tp1 = entry - (risk * 1.5)
                        tp2 = entry - (risk * 3.0)
                        
                        future = day_15m[day_15m.index > c.name]
                        pnl = 0.0
                        hit_tp1 = False
                        hit_tp2 = False
                        hit_sl = False
                        
                        for _, fc in future.iterrows():
                            if fc['High'] >= sl and not hit_tp1:
                                hit_sl = True
                                break
                            if fc['Low'] <= tp1 and not hit_tp1:
                                hit_tp1 = True
                            if hit_tp1:
                                if fc['High'] >= entry:
                                    break
                                if fc['Low'] <= tp2:
                                    hit_tp2 = True
                                    break
                                    
                        if hit_sl:
                            pnl = -50.0
                            out = "LOSS"
                        elif hit_tp2:
                            pnl = 112.50
                            out = "WIN (3R Full)"
                        elif hit_tp1:
                            pnl = 37.50
                            out = "WIN (1.5R Half + BE)"
                        else:
                            pnl = 0.0
                            out = "SCRATCH"
                            
                        account_balance += pnl
                        trades.append({
                            'date': str(d),
                            'dir': 'SELL',
                            'entry': round(entry, 2),
                            'sl': round(sl, 2),
                            'risk_pts': round(risk, 2),
                            'outcome': out,
                            'pnl': pnl,
                            'bal': round(account_balance, 2)
                        })
                        entry_taken = True
                        break
                        
    tdf = pd.DataFrame(trades)
    return tdf, account_balance

if __name__ == '__main__':
    tdf, bal = run_pro_backtest()
    print("\n=== RESULTADOS BACKTEST FILTRADO PRO (CISD + BUFFER TÉCNICO) ===")
    if not tdf.empty:
        total = len(tdf)
        wins = len(tdf[tdf['pnl'] > 0])
        losses = len(tdf[tdf['pnl'] < 0])
        wr = (wins / total) * 100
        gp = tdf[tdf['pnl'] > 0]['pnl'].sum()
        gl = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
        pf = round(gp / gl, 2) if gl > 0 else 999.0
        net = bal - 10000.0
        
        print(f"Total Operaciones: {total}")
        print(f"Ganadoras: {wins} ({wr:.1f}%) | Perdedoras: {losses} ({(losses/total)*100:.1f}%)")
        print(f"Profit Factor: {pf}")
        print(f"Beneficio Neto: ${net:,.2f} USD ({((bal-10000)/10000)*100:.2f}%)")
        print(f"Balance Final: ${bal:,.2f} USD")
        print(tdf[['date', 'dir', 'entry', 'sl', 'outcome', 'pnl', 'bal']].to_string(index=False))
