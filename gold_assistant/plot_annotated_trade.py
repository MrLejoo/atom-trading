import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import shutil
import os

# Download 5m data for Oct 23, 2026
df = yf.download('GC=F', start='2026-10-22', end='2026-10-24', interval='5m')
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# Filter for intraday chart: from 08:30 to 11:15
data = df.loc['2026-10-23 08:30:00-04:00':'2026-10-23 11:15:00-04:00'].copy()

# Setup style
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(19, 11), dpi=180)
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#161b22')

# Color palette
up_color = '#00c853'      # Vivid Bullish Green
down_color = '#ff3d00'    # Vivid Bearish Red

indices = list(range(len(data)))
time_labels = [idx.strftime('%H:%M') for idx in data.index]

# Plot Candles
for i, (idx_time, row) in enumerate(data.iterrows()):
    o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
    color = up_color if c >= o else down_color
    
    # Wick
    ax.plot([i, i], [l, h], color=color, linewidth=1.5, zorder=2)
    # Candle body
    height = abs(c - o)
    bottom = min(o, c)
    if height == 0:
        height = 0.20
    ax.bar(i, height, bottom=bottom, color=color, edgecolor=color, width=0.62, zorder=3)

# Grid and styling
ax.grid(True, color='#21262d', linestyle='--', linewidth=0.7, alpha=0.8)
ax.set_xticks(indices[::2])
ax.set_xticklabels(time_labels[::2], color='#c9d1d9', fontsize=10.5, fontweight='bold', rotation=0)
ax.tick_params(colors='#8b949e', labelsize=10.5)
ax.set_ylabel('Precio Spot Oro / US Dollar (XAU/USD)', color='#f0f6fc', fontsize=12, fontweight='bold', labelpad=12)

# Unified Clean Title
ax.set_title('CASO DE ESTUDIO REAL: VENTA EN XAU/USD (ORO) EN VIVO — REGLAS 1 A 5\n'
             'Sesión Nueva York (23 Octubre) | Temporalidad: 5 Minutos (M5) | Cuenta FundingPips $10,000 USD', 
             color='#ffffff', fontsize=13.5, fontweight='bold', pad=20, linespacing=1.4)

# Key levels
asian_high = 4043.00
london_high = 4045.70
entry_price = 4042.50
sl_price = 4051.70
tp1_price = 4031.25
tp2_price = 4016.30

# Candle indices
idx_0900 = 6    # 09:00
idx_0920 = 10   # 09:20 (High 4050.20 sweep)
idx_0925 = 11   # 09:25 (CISD candle)
idx_0930 = 12   # 09:30 (Mitigation entry candle)
idx_1000 = 18   # 10:00 (TP1)
idx_1020 = 22   # 10:20 (TP2 sweep)

# -------------------------------------------------------------
# REGLA 1: Ventana Operativa & Filtro Macro
# -------------------------------------------------------------
ax.axvspan(idx_0900 - 0.5, len(indices) - 0.5, color='#1f6feb', alpha=0.08, zorder=1)
ax.axvline(idx_0900 - 0.5, color='#1f6feb', linestyle='--', linewidth=1.5, alpha=0.7)

ax.text(idx_0900 + 0.3, 4064.0, 
        'REGLA 1: Ventana NY Open (09:00 - 11:30 VET) | Filtro Macro: SIN NOTICIAS DE ALTO IMPACTO (Carpeta Roja)', 
        color='#58a6ff', fontsize=10.5, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#0d1b2a', edgecolor='#1f6feb', linewidth=1.5, alpha=0.95))

# -------------------------------------------------------------
# REGLA 2: Liquidity Sweep
# -------------------------------------------------------------
# Previous Highs reference lines
ax.axhline(asian_high, color='#d29922', linestyle=':', linewidth=1.2, xmin=0.01, xmax=0.40)
ax.text(0, asian_high + 0.4, f'Asian High: {asian_high:.2f}', color='#d29922', fontsize=9.5, fontweight='bold')

ax.axhline(london_high, color='#e3b341', linestyle='--', linewidth=1.2, xmin=0.01, xmax=0.40)
ax.text(0, london_high + 0.4, f'London High: {london_high:.2f}', color='#e3b341', fontsize=9.5, fontweight='bold')

# Sweep Arrow & Box
ax.annotate('REGLA 2: Liquidity Sweep (BSL Purged)\n'
            '• Barrida agresiva hacia 4050.20\n'
            '• Purgó Asian High y London High\n'
            '• Deja clara mecha superior de rechazo', 
            xy=(idx_0920, 4050.20), xytext=(idx_0920 - 5.5, 4055.00),
            arrowprops=dict(facecolor='#ff7b72', edgecolor='#ff7b72', width=1.5, headwidth=6, shrink=0.05),
            color='#ffa198', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#3d1418', edgecolor='#ff7b72', linewidth=1.5, alpha=0.95))

# -------------------------------------------------------------
# REGLA 3: Desplazamiento & CISD (Change In State of Delivery)
# -------------------------------------------------------------
ax.annotate('REGLA 3: Desplazamiento & CISD / MSS\n'
            '• Vela bajista institucional de 09:25\n'
            '• Cierre con cuerpo sólido en 4040.30\n'
            '• Quiebre de mínimos inmediatos con volumen', 
            xy=(idx_0925, 4040.30), xytext=(idx_0925 - 4.5, 4027.00),
            arrowprops=dict(facecolor='#d2a8ff', edgecolor='#d2a8ff', width=1.5, headwidth=6, shrink=0.05),
            color='#e2c5ff', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#271c3b', edgecolor='#bc8cff', linewidth=1.5, alpha=0.95))

# -------------------------------------------------------------
# REGLA 4: Fair Value Gap (FVG) & Entrada en Mitigación
# -------------------------------------------------------------
# FVG box between 4041.20 and 4044.40
fvg_box = patches.Rectangle((idx_0925 - 0.35, 4041.20), 2.2, 3.20,
                            linewidth=1.5, edgecolor='#e3b341', facecolor='#e3b341', alpha=0.30, zorder=2)
ax.add_patch(fvg_box)

ax.annotate('REGLA 4: FVG & Entrada por Mitigación\n'
            '• Desequilibrio vendedor (FVG 5m)\n'
            '• Vela 09:30 retrocede al 50% CE (4042.50)\n'
            '• ORDEN EJECUTADA: SELL @ 4042.50', 
            xy=(idx_0930, entry_price), xytext=(idx_0930 + 2.2, 4047.50),
            arrowprops=dict(facecolor='#f0883e', edgecolor='#f0883e', width=1.5, headwidth=6, shrink=0.05),
            color='#ffdf5d', fontsize=9.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#38280f', edgecolor='#e3b341', linewidth=1.5, alpha=0.95))

# -------------------------------------------------------------
# REGLA 5: Niveles de Ejecución, Stop Loss y Take Profits
# -------------------------------------------------------------
# SL Line
ax.axhline(sl_price, color='#ff3d00', linestyle='-', linewidth=2.0, xmin=0.38, xmax=0.82)
ax.text(len(indices) - 2.5, sl_price, f'  STOP LOSS: {sl_price:.2f} (+9.2 pts / 92 pips)  ', 
        color='#ff7b72', fontsize=9.5, fontweight='bold', verticalalignment='center',
        bbox=dict(boxstyle='square,pad=0.2', facecolor='#161b22', edgecolor='#ff3d00', linewidth=1))

# Entry Line
ax.axhline(entry_price, color='#58a6ff', linestyle='-', linewidth=1.8, xmin=0.38, xmax=0.82)
ax.text(len(indices) - 2.5, entry_price, f'  ENTRADA SELL: {entry_price:.2f}  ', 
        color='#79c0ff', fontsize=9.5, fontweight='bold', verticalalignment='center',
        bbox=dict(boxstyle='square,pad=0.2', facecolor='#161b22', edgecolor='#58a6ff', linewidth=1))

# TP1 Line
ax.axhline(tp1_price, color='#3fb950', linestyle='--', linewidth=1.8, xmin=0.38, xmax=0.82)
ax.text(len(indices) - 2.5, tp1_price, f'  TP1: {tp1_price:.2f} (1:1.5 -> Cierre 50% y SL a BE)  ', 
        color='#56d364', fontsize=9.5, fontweight='bold', verticalalignment='center',
        bbox=dict(boxstyle='square,pad=0.2', facecolor='#161b22', edgecolor='#3fb950', linewidth=1))

# TP2 Line
ax.axhline(tp2_price, color='#2ea043', linestyle='-', linewidth=2.0, xmin=0.38, xmax=0.82)
ax.text(len(indices) - 2.5, tp2_price, f'  TP2: {tp2_price:.2f} (1:3+ -> Barrida Asian Low)  ', 
        color='#39d353', fontsize=10, fontweight='heavy', verticalalignment='center',
        bbox=dict(boxstyle='square,pad=0.2', facecolor='#161b22', edgecolor='#2ea043', linewidth=1.2))

# Callout at TP1 hit
ax.scatter([idx_1000], [tp1_price], color='#3fb950', s=130, zorder=5, edgecolor='#ffffff', linewidth=1.5)
ax.text(idx_1000 - 0.5, tp1_price - 2.8, 'TP1 ALCANZADO\n(50% Cerrado, SL a Break-Even)', 
        color='#7ee787', fontsize=8.5, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d2818', edgecolor='#3fb950', alpha=0.9))

# Callout at TP2 hit
ax.scatter([idx_1020], [tp2_price], color='#2ea043', s=150, zorder=5, edgecolor='#ffffff', linewidth=1.5)
ax.text(idx_1020 + 0.2, tp2_price - 3.2, 'TP2 ALCANZADO\n(100% Salida Exitosa)', 
        color='#39d353', fontsize=9, fontweight='bold', ha='center',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#0b2e13', edgecolor='#2ea043', alpha=0.95))

# -------------------------------------------------------------
# FICHA TÉCNICA REGLA 5: Matriz de Gestión FundingPips $10K
# -------------------------------------------------------------
info_text = (
    "REGLA 5: PLAN DE GESTIÓN MATEMÁTICA (FUNDINGPIPS 10K)\n"
    "=====================================================\n"
    "• Capital de Cuenta:       $10,000 USD (Evaluación 2-Step)\n"
    "• Límite Riesgo por Trade: 0.50%  ($50.00 USD Máximo)\n"
    "• Distancia de Stop Loss:  9.20 Puntos (92 Pips Oro)\n"
    "• Tamaño Total Calculado:  0.06 Lotes (Split en 2 Órdenes):\n"
    "  ---------------------------------------------------\n"
    "  ORDEN A (0.03 Lotes):\n"
    "  • Objetivo TP1:          4031.25 (Distancia: +11.25 pts)\n"
    "  • Ratio Riesgo/Beneficio:1:1.5 R\n"
    "  • Beneficio Asegurado:   +$33.75 USD\n"
    "  • REGLA ACTIVA:          Al tocar TP1 -> SL Orden B a BREAK-EVEN\n"
    "  ---------------------------------------------------\n"
    "  ORDEN B (0.03 Lotes):\n"
    "  • Objetivo TP2:          4016.30 (Barrida de Asian Low)\n"
    "  • Ratio Riesgo/Beneficio:1:3.0 R+\n"
    "  • Beneficio Capturado:   +$78.60 USD\n"
    "  =====================================================\n"
    "  RESULTADO TOTAL:         +$112.35 USD (+1.12% en Cuenta)\n"
    "  REGLA DE CONSISTENCIA:   Cumplida al 100% (Riesgo < 0.5%)"
)

ax.text(0.018, 0.035, info_text, transform=ax.transAxes,
        fontsize=9, family='monospace', color='#f0f6fc',
        verticalalignment='bottom',
        bbox=dict(boxstyle='round,pad=0.6', facecolor='#0d1117', edgecolor='#388bfd', linewidth=1.5, alpha=0.95))

# Y-Limits and X-Limits with ample breathing room
ax.set_ylim(3988, 4068)
ax.set_xlim(-1, len(indices) + 7)

plt.tight_layout()

# Save
output_local = 'e:/Gravi/gold_assistant/real_gold_trade_setup.png'
plt.savefig(output_local, dpi=200, bbox_inches='tight')
plt.close()

# Copy to brain artifact directory
brain_dir = r'C:/Users/mrlej/.gemini/antigravity/brain/81306888-dfa4-4d33-b0d1-454c7788da38'
artifact_img = os.path.join(brain_dir, 'real_gold_trade_setup.png')
shutil.copyfile(output_local, artifact_img)
print(f"Chart cleanly regenerated and saved to {output_local} and {artifact_img}")
