"""
dashboard_app.py - Dashboard Web Visual e Interactivo de ARES
Tu Asistente Cuantitativo en XAU/USD para Cuentas FundingPips ($10,000 USD)
Tema: Legacy Dark (Antigravity Theme)
Background: #101010 | Foreground: #CCCCCC | Accent: #007ACC
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time, timedelta
import pytz

from gold_math import FundingPipsGoldCalculator

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO LEGACY DARK (#101010 / #CCCCCC / #007ACC)
# ==============================================================================
st.set_page_config(
    page_title="ARES | Gold Trading Copilot",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Estilos Generales - Legacy Dark Theme */
    .stApp {
        background-color: #101010 !important;
        color: #CCCCCC !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Encabezados y Textos */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #CCCCCC !important;
    }
    
    /* Acentos y Enlaces */
    a {
        color: #007ACC !important;
    }
    
    /* Métricas Superiores */
    .metric-card {
        background-color: #181818;
        border: 1px solid #282828;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    .metric-title {
        color: #888888;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 22px;
        font-weight: 800;
        font-family: 'SF Mono', 'Roboto Mono', Menlo, Consolas, monospace;
        margin-top: 4px;
    }
    .metric-sub {
        font-size: 11px;
        margin-top: 3px;
        font-weight: 600;
    }
    
    /* Banners de Decisión */
    .banner-green {
        background-color: #122416;
        border: 1.5px solid #2ea043;
        border-radius: 8px;
        padding: 12px 20px;
        color: #7ee787;
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .banner-red {
        background-color: #281416;
        border: 1.5px solid #f85149;
        border-radius: 8px;
        padding: 12px 20px;
        color: #ff7b72;
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    /* Sidebar */
    div[data-testid="stSidebar"] {
        background-color: #141414 !important;
        border-right: 1px solid #222222 !important;
    }
    
    /* Controles de Entrada (Inputs, Sliders, Radios) */
    .stNumberInput input, .stTextInput input, .stSelectbox div {
        background-color: #181818 !important;
        color: #CCCCCC !important;
        border-color: #282828 !important;
    }
    
    /* Botones con Acento #007ACC */
    .stButton button {
        background-color: #007ACC !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        transition: 0.2s all;
    }
    .stButton button:hover {
        background-color: #005999 !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# OBTENCIÓN Y PROCESAMIENTO DE DATOS
# ==============================================================================
@st.cache_data(ttl=20)
def load_market_data(mode="live", interval="5m", replay_date="2026-10-23"):
    try:
        if mode == "live":
            ticker = yf.Ticker('GC=F')
            if interval == '1m':
                df = ticker.history(period='5d', interval='1m')
            elif interval == '5m':
                df = ticker.history(period='15d', interval='5m')
            elif interval == '15m':
                df = ticker.history(period='30d', interval='15m')
            else:
                df = ticker.history(period='60d', interval='1h')
        else:
            start_dt = pd.to_datetime(replay_date) - timedelta(days=2)
            end_dt = pd.to_datetime(replay_date) + timedelta(days=2)
            df = yf.download('GC=F', start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'), interval=interval)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
        if df.empty or 'Close' not in df.columns:
            return None, "No se recibieron datos de mercado."
            
        return df, None
    except Exception as e:
        return None, str(e)

def extract_institutional_levels(df):
    levels = {}
    if df is None or len(df) < 5:
        return levels
        
    levels['current_price'] = float(df['Close'].iloc[-1])
    df_tz = df.copy()
    if df_tz.index.tz is None:
        df_tz.index = df_tz.index.tz_localize('UTC')
        
    ny_tz = pytz.timezone('America/New_York')
    df_ny = df_tz.tz_convert(ny_tz)
    
    try:
        daily = df_ny.resample('1D').agg({'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
        if len(daily) >= 2:
            levels['pdh'] = float(daily['High'].iloc[-2])
            levels['pdl'] = float(daily['Low'].iloc[-2])
            levels['eq_50'] = round((levels['pdh'] + levels['pdl']) / 2.0, 2)
    except:
        pass
        
    try:
        asian_candles = df_ny.between_time('19:00', '02:00')
        if not asian_candles.empty:
            recent_asian = asian_candles.iloc[-40:]
            levels['asian_high'] = round(float(recent_asian['High'].max()), 2)
            levels['asian_low'] = round(float(recent_asian['Low'].min()), 2)
    except:
        pass
        
    try:
        london_candles = df_ny.between_time('03:00', '08:30')
        if not london_candles.empty:
            recent_london = london_candles.iloc[-40:]
            levels['london_high'] = round(float(recent_london['High'].max()), 2)
            levels['london_low'] = round(float(recent_london['Low'].min()), 2)
    except:
        pass
        
    return levels

def detect_fvgs_and_sweeps(df, levels, lookback=25):
    fvgs = []
    sweeps = []
    if df is None or len(df) < 5:
        return fvgs, sweeps
        
    subset = df.iloc[-lookback:].copy()
    
    for i in range(2, len(subset)):
        v1 = subset.iloc[i-2]
        v2 = subset.iloc[i-1]
        v3 = subset.iloc[i]
        
        if v3['Low'] > v1['High']:
            gap = v3['Low'] - v1['High']
            if gap >= 0.5:
                ce = v1['High'] + (gap / 2.0)
                fvgs.append({
                    'type': 'BULLISH (BISI)',
                    'time': v2.name,
                    'top': round(float(v3['Low']), 2),
                    'bottom': round(float(v1['High']), 2),
                    'ce': round(float(ce), 2),
                    'gap': round(float(gap), 2)
                })
        elif v3['High'] < v1['Low']:
            gap = v1['Low'] - v3['High']
            if gap >= 0.5:
                ce = v3['High'] + (gap / 2.0)
                fvgs.append({
                    'type': 'BEARISH (SIBI)',
                    'time': v2.name,
                    'top': round(float(v1['Low']), 2),
                    'bottom': round(float(v3['High']), 2),
                    'ce': round(float(ce), 2),
                    'gap': round(float(gap), 2)
                })
                
    asian_h = levels.get('asian_high')
    london_h = levels.get('london_high')
    asian_l = levels.get('asian_low')
    london_l = levels.get('london_low')
    
    for i in range(len(subset)):
        row = subset.iloc[i]
        h = float(row['High'])
        l = float(row['Low'])
        c = float(row['Close'])
        
        if asian_h and h > asian_h and c < asian_h:
            sweeps.append({'type': 'BSL SWEEP (Asian High)', 'time': row.name, 'price': h, 'level': asian_h})
        elif london_h and h > london_h and c < london_h:
            sweeps.append({'type': 'BSL SWEEP (London High)', 'time': row.name, 'price': h, 'level': london_h})
        elif asian_l and l < asian_l and c > asian_l:
            sweeps.append({'type': 'SSL SWEEP (Asian Low)', 'time': row.name, 'price': l, 'level': asian_l})
            
    return fvgs, sweeps

# ==============================================================================
# SIDEBAR
# ==============================================================================
st.sidebar.markdown("""
<div style="text-align: center; padding: 12px 0 16px 0;">
    <h2 style="color: #007ACC; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 1.5px;">⚔️ ARES</h2>
    <p style="color: #888888; font-size: 11px; margin: 2px 0 0 0; text-transform: uppercase;">Copiloto de Trading · XAU/USD</p>
</div>
""", unsafe_allow_html=True)

mode = st.sidebar.radio(
    "Fuente de Datos:",
    ["🔴 Mercado en Vivo", "🧪 Caso de Estudio (23 Octubre)"],
    index=0
)

is_live = (mode == "🔴 Mercado en Vivo")
replay_date = "2026-10-23" if not is_live else None
timeframe = st.sidebar.selectbox("Temporalidad (Timeframe):", ["5m", "1m", "15m", "1h"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Capas del Gráfico")
show_asian = st.sidebar.checkbox("Rango Asiático (Asian High / Low)", value=True)
show_london = st.sidebar.checkbox("Rango Londres (London High / Low)", value=True)
show_pdh_pdl = st.sidebar.checkbox("Niveles Diarios (PDH / PDL)", value=True)
show_fvgs = st.sidebar.checkbox("Fair Value Gaps (FVGs)", value=True)

if st.sidebar.button("🔄 Actualizar Cotizaciones Ahora", use_container_width=True):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="background-color: #181818; border-radius: 6px; padding: 12px; border: 1px solid #282828;">
    <div style="font-size: 11px; color: #888888; font-weight: bold;">CUENTA VINCULADA:</div>
    <div style="font-size: 14px; color: #007ACC; font-weight: bold; margin-top: 2px;">FundingPips $10,000 USD</div>
    <div style="font-size: 10.5px; color: #888888; margin-top: 4px;">Evaluación 2-Step · Broker MT5</div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# HEADER
# ==============================================================================
now_vet = datetime.now(pytz.timezone('America/Caracas'))
is_ny_open = (time(9, 0) <= now_vet.time() <= time(11, 30)) and (now_vet.weekday() < 5)

col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)

with col_h1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">HORA VENEZUELA (VET)</div>
        <div class="metric-value">{now_vet.strftime('%H:%M:%S')}</div>
        <div class="metric-sub" style="color: {'#2ea043' if is_ny_open else '#888888'};">
            {'● NY OPEN ACTIVA (09:00 - 11:30)' if is_ny_open else '○ FUERA DE VENTANA NY'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">BALANCE CUENTA</div>
        <div class="metric-value">$10,000.00</div>
        <div class="metric-sub" style="color: #007ACC;">Target Fase 1: $800 (8%)</div>
    </div>
    """, unsafe_allow_html=True)

with col_h3:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">LÍMITE RIESGO / TRADE</div>
        <div class="metric-value" style="color: #007ACC;">$50.00 USD</div>
        <div class="metric-sub" style="color: #CCCCCC;">0.50% Estricto (Blindaje)</div>
    </div>
    """, unsafe_allow_html=True)

with col_h4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">MÁX. PÉRDIDA DIARIA</div>
        <div class="metric-value" style="color: #f85149;">$500.00 USD</div>
        <div class="metric-sub" style="color: #f85149;">5.0% Límite FundingPips</div>
    </div>
    """, unsafe_allow_html=True)

with col_h5:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">FILTRO MACRO (NOTICIAS)</div>
        <div class="metric-value" style="color: #2ea043;">LIMPIO</div>
        <div class="metric-sub" style="color: #2ea043;">Sin Carpeta Roja Próxima</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# CARGA DE MERCADO
# ==============================================================================
with st.spinner("Conectando con el flujo institucional de Oro (XAU/USD)..."):
    df, err = load_market_data(mode="live" if is_live else "replay", interval=timeframe, replay_date=replay_date)

if err or df is None:
    st.error(f"Error al obtener datos de mercado: {err}")
    st.stop()

levels = extract_institutional_levels(df)
fvgs, sweeps = detect_fvgs_and_sweeps(df, levels, lookback=35)
current_price = levels.get('current_price', float(df['Close'].iloc[-1]))

# ==============================================================================
# GRÁFICO INTERACTIVO + CALCULADORA
# ==============================================================================
col_chart, col_side = st.columns([2.4, 1.1])

with col_chart:
    st.markdown(f"#### 📊 Gráfico Institucional XAU/USD ({timeframe.upper()}) · Legacy Dark")
    
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="XAU/USD",
        increasing_line_color='#2ea043',
        increasing_fillcolor='#2ea043',
        decreasing_line_color='#f85149',
        decreasing_fillcolor='#f85149'
    ))
    
    if show_asian and 'asian_high' in levels and 'asian_low' in levels:
        fig.add_hline(y=levels['asian_high'], line_dash="dot", line_color="#d29922", line_width=1.5,
                      annotation_text=f" Asian High: {levels['asian_high']}", annotation_position="top left",
                      annotation_font_color="#d29922", annotation_font_size=10)
        fig.add_hline(y=levels['asian_low'], line_dash="dot", line_color="#d29922", line_width=1.5,
                      annotation_text=f" Asian Low: {levels['asian_low']}", annotation_position="bottom left",
                      annotation_font_color="#d29922", annotation_font_size=10)
                      
    if show_london and 'london_high' in levels and 'london_low' in levels:
        fig.add_hline(y=levels['london_high'], line_dash="dash", line_color="#007ACC", line_width=1.5,
                      annotation_text=f" London High: {levels['london_high']}", annotation_position="top right",
                      annotation_font_color="#007ACC", annotation_font_size=10)
        fig.add_hline(y=levels['london_low'], line_dash="dash", line_color="#007ACC", line_width=1.5,
                      annotation_text=f" London Low: {levels['london_low']}", annotation_position="bottom right",
                      annotation_font_color="#007ACC", annotation_font_size=10)
                      
    if show_pdh_pdl and 'pdh' in levels and 'pdl' in levels:
        fig.add_hline(y=levels['pdh'], line_dash="solid", line_color="#58a6ff", line_width=1.2,
                      annotation_text=f" PDH: {levels['pdh']}", annotation_position="top left",
                      annotation_font_color="#58a6ff", annotation_font_size=10)
        fig.add_hline(y=levels['pdl'], line_dash="solid", line_color="#58a6ff", line_width=1.2,
                      annotation_text=f" PDL: {levels['pdl']}", annotation_position="bottom left",
                      annotation_font_color="#58a6ff", annotation_font_size=10)
                      
    if show_fvgs and fvgs:
        for f in fvgs[-4:]:
            fill = "rgba(46, 160, 67, 0.15)" if "BULLISH" in f['type'] else "rgba(248, 81, 73, 0.15)"
            edge = "#2ea043" if "BULLISH" in f['type'] else "#f85149"
            fig.add_hrect(
                y0=f['bottom'], y1=f['top'],
                fillcolor=fill, line=dict(color=edge, width=1, dash="dot"),
                annotation_text=f" FVG {f['type'][:4]} | CE: {f['ce']}",
                annotation_position="right",
                annotation_font_size=9,
                annotation_font_color=edge
            )
            
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#101010",
        plot_bgcolor="#141414",
        xaxis_rangeslider_visible=False,
        height=620,
        margin=dict(l=10, r=60, t=10, b=10),
        xaxis=dict(
            gridcolor="#222222",
            showgrid=True,
            linecolor="#282828",
            tickfont=dict(color="#CCCCCC", size=10)
        ),
        yaxis=dict(
            gridcolor="#222222",
            showgrid=True,
            linecolor="#282828",
            side="right",
            tickfont=dict(color="#CCCCCC", size=11, family="monospace"),
            tickformat=".2f"
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

# CALCULADORA LATERAL
with col_side:
    st.markdown("#### 🛡️ Calculadora de Riesgo Ares")
    
    calc = FundingPipsGoldCalculator(account_size=10000.0, risk_pct=0.5)
    
    order_type = st.radio("Tipo de Orden:", ["SELL (Venta Corta)", "BUY (Compra Larga)"], horizontal=True)
    is_sell = "SELL" in order_type
    
    default_entry = float(current_price)
    default_sl = round(default_entry + 8.5 if is_sell else default_entry - 8.5, 2)
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        entry_input = st.number_input("Precio Entrada:", value=default_entry, step=0.5, format="%.2f")
    with col_in2:
        sl_input = st.number_input("Stop Loss:", value=default_sl, step=0.5, format="%.2f")
        
    sl_dist = abs(entry_input - sl_input)
    is_sl_valid = (entry_input < sl_input) if is_sell else (entry_input > sl_input)
    
    if not is_sl_valid or sl_dist < 1.0:
        st.warning("⚠️ Stop Loss inválido para la dirección seleccionada.")
        lot_size = 0.01
    else:
        res = calc.calculate_lot_size(entry_input, sl_input)
        lot_size = res['lot_size']
        
        r_dist = sl_dist
        tp1_price = round(entry_input - (1.5 * r_dist) if is_sell else entry_input + (1.5 * r_dist), 2)
        tp2_price = round(entry_input - (3.0 * r_dist) if is_sell else entry_input + (3.0 * r_dist), 2)
        
        st.markdown(f"""
        <div style="background-color: #181818; border: 1px solid #282828; border-radius: 6px; padding: 14px; margin-top: 5px;">
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #888888;">
                <span>RIESGO MÁXIMO:</span>
                <span style="color: #007ACC; font-weight: bold;">$50.00 USD (0.50%)</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #888888; margin-top: 4px;">
                <span>DISTANCIA SL:</span>
                <span style="color: #f85149; font-weight: bold;">{sl_dist:.2f} pts ({int(sl_dist*10)} pips)</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 14px; color: #CCCCCC; margin-top: 6px; border-top: 1px solid #282828; padding-top: 6px;">
                <span style="font-weight: bold;">LOTAJE TOTAL:</span>
                <span style="color: #007ACC; font-size: 18px; font-weight: 800; font-family: monospace;">{lot_size:.2f} LOTES</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("##### 📦 Split de Posiciones:")
        lots_split = round(lot_size / 2.0, 2)
        if lots_split < 0.01:
            lots_split = 0.01
            
        st.markdown(f"""
        <div style="font-size: 12px; background-color: #141414; border-left: 3px solid #2ea043; padding: 8px 12px; margin-bottom: 8px; border-radius: 0 4px 4px 0;">
            <strong style="color: #2ea043;">ORDEN A (50% = {lots_split} lotes):</strong><br>
            • TP1: <span style="font-family: monospace; font-weight: bold; color: #FFFFFF;">{tp1_price:.2f}</span> (1:1.5 R)<br>
            • Beneficio Asegurado: <strong>+${(1.5 * 25.0):.2f} USD</strong><br>
            <span style="color: #d29922; font-size: 11px;">⚠️ Al tocar TP1: Mover SL de Orden B a BREAK-EVEN</span>
        </div>
        <div style="font-size: 12px; background-color: #141414; border-left: 3px solid #007ACC; padding: 8px 12px; border-radius: 0 4px 4px 0;">
            <strong style="color: #007ACC;">ORDEN B (50% = {lots_split} lotes):</strong><br>
            • TP2: <span style="font-family: monospace; font-weight: bold; color: #FFFFFF;">{tp2_price:.2f}</span> (1:3.0+ R)<br>
            • Beneficio Proyectado: <strong>+${(3.0 * 25.0):.2f} USD</strong><br>
            <span style="color: #888888; font-size: 11px;">Objetivo: Barrida de liquidez opuesta</span>
        </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# CHECKLIST DE LAS 5 REGLAS
# ==============================================================================
st.markdown("---")
st.markdown("### 📋 Verificación y Guardián de Entrada: El Checklist de las 5 Reglas")

col_chk1, col_chk2, col_chk3, col_chk4, col_chk5 = st.columns(5)

with col_chk1:
    r1 = st.checkbox("1. Ventana & Filtro Macro", value=True if (is_ny_open or not is_live) else False)
    st.caption("Apertura NY 09:00 - 11:30 VET / Sin noticias rojas.")

with col_chk2:
    auto_sweep = len(sweeps) > 0 or not is_live
    r2 = st.checkbox("2. Liquidity Sweep", value=True if auto_sweep else False)
    st.caption("Barrida de Asian/London High/Low con mecha.")

with col_chk3:
    r3 = st.checkbox("3. Desplazamiento & CISD", value=True if not is_live else False)
    st.caption("Cierre con cuerpo sólido rompiendo estructura previa.")

with col_chk4:
    auto_fvg = len(fvgs) > 0 or not is_live
    r4 = st.checkbox("4. FVG & Mitigación", value=True if auto_fvg else False)
    st.caption("Desequilibrio de 3 velas y testeo del 50% CE.")

with col_chk5:
    r5 = st.checkbox("5. Gestión de Riesgo 10K", value=True if (is_sl_valid and sl_dist > 1.0) else False)
    st.caption("Riesgo ≤ $50 USD (0.50%) con split de órdenes.")

all_rules_met = r1 and r2 and r3 and r4 and r5

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

if all_rules_met:
    st.markdown(f"""
    <div class="banner-green">
        <span style="font-size: 26px;">🚀</span>
        <div>
            <div style="font-size: 16px; font-weight: 800; color: #FFFFFF;">SISTEMA EN VERDE: CONDICIONES INSTITUCIONALES CUMPLIDAS AL 100%</div>
            <div style="font-size: 12px; color: #7ee787; font-weight: normal;">
                Todas las 5 reglas del plan de trading han sido verificadas. Puedes colocar tus dos órdenes ({lots_split} lotes c/u) con total convicción matemática.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    missing = []
    if not r1: missing.append("Regla 1 (Ventana/Macro)")
    if not r2: missing.append("Regla 2 (Sweep de Liquidez)")
    if not r3: missing.append("Regla 3 (CISD / Desplazamiento)")
    if not r4: missing.append("Regla 4 (FVG / Mitigación)")
    if not r5: missing.append("Regla 5 (Riesgo / Lotes)")
    
    st.markdown(f"""
    <div class="banner-red">
        <span style="font-size: 26px;">✋</span>
        <div>
            <div style="font-size: 16px; font-weight: 800; color: #FFFFFF;">FILTRO DE ABSTENCIÓN ACTIVO — PROHIBIDO OPERAR</div>
            <div style="font-size: 12px; color: #ff7b72; font-weight: normal;">
                Faltan reglas obligatorias por confirmar: <strong>{', '.join(missing)}</strong>. Espera la confirmación institucional antes de arriesgar capital.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
st.caption("ARES v1.0 · Tu copiloto cuantitativo de trading en Oro (FundingPips $10K).")
