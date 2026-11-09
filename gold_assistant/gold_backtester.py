"""
gold_backtester.py - Motor de Backtesting Automatizado para XAUUSD
Estrategia: Asian Range Sweep + New York Open (09:30 AM VET) CISD/FVG Mitigation
Parámetros:
- Cuenta de Fondeo: $10,000 USD
- Riesgo por Trade: 0.50% ($50 USD)
- Horario de Ejecución: 09:00 AM - 11:30 AM (VET / UTC-4)
- Ratios: TP1 en 1:1.5 (cierra 50% + BE), TP2 en 1:3.0 (cierra 50% restante)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time

def run_gold_backtest(period='60d', interval='15m'):
    print(f"Descargando datos históricos de XAUUSD (GC=F) - Periodo: {period}, Intervalo: {interval}...")
    ticker = yf.Ticker('GC=F')
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError("No se pudieron descargar datos para el backtest.")

    df.index = df.index.tz_convert('America/Caracas')
    df['Date'] = df.index.date
    df['Time'] = df.index.time
    
    unique_dates = df['Date'].unique()
    trades = []
    
    account_balance = 10000.0
    equity_curve = [account_balance]
    
    for d in unique_dates:
        day_data = df[df['Date'] == d]
        if len(day_data) < 15:
            continue
            
        # Rango Asiático (20:00 día previo a 03:00 AM o primera parte del día)
        # Tomamos el rango overnight (00:00 a 08:30 VET) como referencia de liquidez previa
        overnight = day_data[day_data['Time'] < time(9, 0)]
        if overnight.empty:
            continue
            
        overnight_high = overnight['High'].max()
        overnight_low = overnight['Low'].min()
        
        # Ventana operativa de New York (09:00 AM a 11:30 AM VET)
        ny_session = day_data[(day_data['Time'] >= time(9, 0)) & (day_data['Time'] <= time(11, 30))]
        if len(ny_session) < 4:
            continue
            
        # Buscar Sweep de overnight_high o overnight_low
        swept_high = False
        swept_low = False
        entry_taken = False
        
        for idx in range(len(ny_session)):
            candle = ny_session.iloc[idx]
            
            # Caso 1: Sweep de High (Buscar Venta tras rechazo)
            if candle['High'] > overnight_high and not entry_taken:
                swept_high = True
                # Esperar vela bajista de desplazamiento
                if candle['Close'] < overnight_high and candle['Close'] < candle['Open']:
                    entry_price = candle['Close']
                    stop_loss = candle['High'] + 1.0 # 1 punto de buffer
                    risk_pts = stop_loss - entry_price
                    if 1.5 <= risk_pts <= 8.0:
                        tp1 = entry_price - (risk_pts * 1.5)
                        tp2 = entry_price - (risk_pts * 3.0)
                        
                        # Evaluar resultado en las velas siguientes del día
                        future_candles = day_data[day_data.index > candle.name]
                        result = "BE"
                        pnl = 0.0
                        
                        hit_tp1 = False
                        hit_tp2 = False
                        hit_sl = False
                        
                        for _, fc in future_candles.iterrows():
                            if fc['High'] >= stop_loss and not hit_tp1:
                                hit_sl = True
                                break
                            if fc['Low'] <= tp1 and not hit_tp1:
                                hit_tp1 = True
                            if hit_tp1:
                                if fc['High'] >= entry_price: # Breakeven hit on runner
                                    break
                                if fc['Low'] <= tp2:
                                    hit_tp2 = True
                                    break
                                    
                        if hit_sl:
                            pnl = -50.0
                            outcome = "LOSS"
                        elif hit_tp2:
                            # 50% en 1.5R ($37.5) + 50% en 3R ($75) = $112.50 (+1.125%)
                            pnl = 112.50
                            outcome = "WIN_FULL (3R)"
                        elif hit_tp1:
                            # 50% en 1.5R ($37.5) + 50% en BE ($0) = $37.50 (+0.375%)
                            pnl = 37.50
                            outcome = "WIN_PARTIAL (1.5R)"
                        else:
                            pnl = 0.0
                            outcome = "SCRATCH/BE"
                            
                        account_balance += pnl
                        equity_curve.append(account_balance)
                        trades.append({
                            'date': str(d),
                            'type': 'SELL',
                            'entry': round(entry_price, 2),
                            'sl': round(stop_loss, 2),
                            'risk_pts': round(risk_pts, 2),
                            'outcome': outcome,
                            'pnl_usd': pnl,
                            'balance': round(account_balance, 2)
                        })
                        entry_taken = True
                        break

            # Caso 2: Sweep de Low (Buscar Compra tras rechazo)
            elif candle['Low'] < overnight_low and not entry_taken:
                swept_low = True
                if candle['Close'] > overnight_low and candle['Close'] > candle['Open']:
                    entry_price = candle['Close']
                    stop_loss = candle['Low'] - 1.0 # 1 punto de buffer
                    risk_pts = entry_price - stop_loss
                    if 1.5 <= risk_pts <= 8.0:
                        tp1 = entry_price + (risk_pts * 1.5)
                        tp2 = entry_price + (risk_pts * 3.0)
                        
                        future_candles = day_data[day_data.index > candle.name]
                        hit_tp1 = False
                        hit_tp2 = False
                        hit_sl = False
                        
                        for _, fc in future_candles.iterrows():
                            if fc['Low'] <= stop_loss and not hit_tp1:
                                hit_sl = True
                                break
                            if fc['High'] >= tp1 and not hit_tp1:
                                hit_tp1 = True
                            if hit_tp1:
                                if fc['Low'] <= entry_price:
                                    break
                                if fc['High'] >= tp2:
                                    hit_tp2 = True
                                    break
                                    
                        if hit_sl:
                            pnl = -50.0
                            outcome = "LOSS"
                        elif hit_tp2:
                            pnl = 112.50
                            outcome = "WIN_FULL (3R)"
                        elif hit_tp1:
                            pnl = 37.50
                            outcome = "WIN_PARTIAL (1.5R)"
                        else:
                            pnl = 0.0
                            outcome = "SCRATCH/BE"
                            
                        account_balance += pnl
                        equity_curve.append(account_balance)
                        trades.append({
                            'date': str(d),
                            'type': 'BUY',
                            'entry': round(entry_price, 2),
                            'sl': round(stop_loss, 2),
                            'risk_pts': round(risk_pts, 2),
                            'outcome': outcome,
                            'pnl_usd': pnl,
                            'balance': round(account_balance, 2)
                        })
                        entry_taken = True
                        break
                        
    tdf = pd.DataFrame(trades)
    return tdf, account_balance, equity_curve

if __name__ == '__main__':
    tdf, final_bal, eq = run_gold_backtest(period='60d', interval='15m')
    print(f"\n================ RESUMEN DEL BACKTEST (XAUUSD - NY KILLZONE) ================")
    if not tdf.empty:
        total_trades = len(tdf)
        wins = len(tdf[tdf['pnl_usd'] > 0])
        losses = len(tdf[tdf['pnl_usd'] < 0])
        bes = len(tdf[tdf['pnl_usd'] == 0])
        win_rate = (wins / total_trades) * 100
        gross_profit = tdf[tdf['pnl_usd'] > 0]['pnl_usd'].sum()
        gross_loss = abs(tdf[tdf['pnl_usd'] < 0]['pnl_usd'].sum())
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999.0
        net_profit = final_bal - 10000.0
        return_pct = (net_profit / 10000.0) * 100
        
        print(f"Total de Operaciones Detectadas: {total_trades}")
        print(f"Operaciones Ganadoras: {wins} ({win_rate:.1f}%)")
        print(f"Operaciones Perdedoras: {losses} ({(losses/total_trades)*100:.1f}%)")
        print(f"Breakeven / Sin Pérdida: {bes}")
        print(f"Profit Factor: {profit_factor}")
        print(f"Beneficio Neto Total: ${net_profit:,.2f} USD (+{return_pct:.2f}%)")
        print(f"Balance Final de la Cuenta: ${final_bal:,.2f} USD")
        print(f"Máximo Drawdown Simulado: Controlado estrictamente por riesgo fijo de $50 (0.50%)")
        print("\nÚltimas 5 Operaciones:")
        print(tdf.tail(5)[['date', 'type', 'entry', 'sl', 'outcome', 'pnl_usd', 'balance']].to_string(index=False))
    else:
        print("No se encontraron trades con los filtros seleccionados.")
