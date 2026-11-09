"""
aureus_copilot.py - CLI Interactivo de AUREUS: Tu Copiloto de Trading en XAUUSD
"""

import sys
import os
from gold_math import FundingPipsGoldCalculator
from gold_analyzer import fetch_gold_data, analyze_key_liquidity_levels, detect_recent_fvgs

def banner():
    print("=" * 65)
    print("       AUREUS - ASISTENTE CUANTITATIVO DE TRADING EN ORO       ")
    print("    Especialista en XAUUSD · FundingPips 10K · SMC / ICT / CISD ")
    print("=" * 65)

def main():
    banner()
    calc = FundingPipsGoldCalculator(account_size=10000.0, risk_pct=0.5)
    
    while True:
        print("\n[MENÚ DE COMANDOS]")
        print("  1. Analizar niveles macro de liquidez y FVGs en tiempo real")
        print("  2. Calcular lotaje exacto y división de posición (Split Positions)")
        print("  3. Simular verificación de pre-market (Checklist)")
        print("  4. Salir")
        
        choice = input("\nSelecciona una opción (1-4): ").strip()
        
        if choice == '1':
            print("\nDescargando cotizaciones de Oro...")
            try:
                df = fetch_gold_data(interval='1h', period='5d')
                levels = analyze_key_liquidity_levels(df)
                print("\n--- NIVELES CLAVE DE LIQUIDEZ EXTERNA (HTF) ---")
                for k, v in levels.items():
                    print(f"  • {k}: {v}")
                fvgs = detect_recent_fvgs(df, lookback=12)
                print(f"\n--- FAIR VALUE GAPS (FVG) RECIENTES (Últimas velas 1H) ---")
                for f in fvgs[-3:]:
                    print(f"  • {f['type']} [{f['bottom']} - {f['top']}] | 50% CE: {f['consequent_encroachment_50']}")
            except Exception as e:
                print(f"Error al analizar mercado: {e}")
                
        elif choice == '2':
            print("\n--- CALCULADORA DE RIESGO INSTITUCIONAL (XAUUSD - $10K) ---")
            try:
                entry = float(input("Precio de entrada proyectado (ej. 2742.50): ").strip())
                sl = float(input("Precio de Stop Loss técnico (ej. 2737.50): ").strip())
                res = calc.calculate_lot_size(entry, sl)
                print("\n[RESULTADOS CUANTITATIVOS]")
                print(f"  • Riesgo Máximo: ${res['risk_usd']} USD ({res['risk_percentage']})")
                print(f"  • Distancia al Stop: ${res['price_delta']} puntos/dólares")
                print(f"  • LOTAJE TOTAL RECOMENDADO: {res['lot_size']} lotes")
                print(f"  • Margen Estimado Requerido: ${res['estimated_margin_usd']} USD")
                print("\n[EJECUCIÓN SPLIT POSITIONS]")
                print(f"  • Orden 1: {res['split_positions']['order_1_lots']} lotes -> {res['split_positions']['tp1_ratio']}")
                print(f"  • Orden 2: {res['split_positions']['order_2_lots']} lotes -> {res['split_positions']['tp2_ratio']}")
            except Exception as e:
                print(f"Error en los datos ingresados: {e}")
                
        elif choice == '3':
            print("\n--- PROTOCOLO CHECKLIST PRE-MARKET (HORA VENEZUELA 08:30 - 09:15) ---")
            print("  [ ] 1. ¿Hay noticias rojas de USD entre 09:25 y 11:35 VET? (Si sí, esperar 5m)")
            print("  [ ] 2. ¿Se identificaron el Asian High y Asian Low en el gráfico?")
            print("  [ ] 3. ¿Hubo toma de liquidez (Sweep) en la apertura de NY (09:30 VET)?")
            print("  [ ] 4. ¿Apareció una vela de desplazamiento con CISD o FVG en 1m/5m?")
            print("  [ ] 5. ¿El riesgo por operación es menor o igual a $50 USD (0.50%)?")
            print("  => Si todos los checks son afirmativos: EJECUTAR SIN DUDAR.")
            print("  => Si falta uno solo: FILTRO DE ABSTENCIÓN (PROHIBIDO OPERAR).")
            
        elif choice == '4':
            print("\nHasta luego. Mantén la disciplina.")
            break
        else:
            print("Opción inválida.")

if __name__ == '__main__':
    main()
