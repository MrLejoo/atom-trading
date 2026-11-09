# ⚛️ ATOM · Plataforma Cuantitativa XAU/USD (FundingPips $10K)

## 🚀 Cómo iniciar en esta computadora

1. **Si es la primera vez que abres el proyecto en esta máquina:**
   - Haz doble clic en `instalar_dependencias.bat` para instalar las librerías necesarias de Python (`starlette`, `uvicorn`, `requests`, `pandas`).

2. **Para abrir la plataforma:**
   - Haz doble clic en `gold_assistant\iniciar_atom.bat`.
   - Se abrirá automáticamente tu navegador en **http://127.0.0.1:8050**.

---

## 🧭 ¿Qué contiene cada pestaña?

1. **📡 Radar & Puntos de Entrada en Vivo:**
   - Gráfico interactivo institucional con velas de 5m/1m.
   - Detección automática de Killzone NY (09:00 - 11:30 VET), Asian/London Range y FVGs (50% CE).
   - Checklist de las **5 Reglas de Oro** con veredicto en tiempo real.
   - Calculadora cuantitativa de riesgo fijo en **$50 USD (0.5%)** con protocolo Split 50/50 (`TP1 1:1.5R + Breakeven` / `TP2 1:3.0R`).
   - Mapa de imanes de liquidez y calendario USD en hora de Venezuela (VET UTC-4).

2. **⏪ Simulador Replay Vela a Vela:**
   - 50 sesiones históricas de New York para entrenar el ojo institucional.
   - Modo entrenamiento a ciegas (*Blind Mode*) para auditar tu lectura.

3. **📈 Backtester Institucional (60 Días):**
   - Estadísticas objetivas en cuenta de $10K (Win Rate, Profit Factor, Curva de Equidad).

4. **📓 Diario, Discrepancias & Escalado:**
   - Bitácora persistente en SQLite (`ares_data.db`).
   - Hoja de ruta de retiros por USDT ERC20 y escalado a $300K con copiador nativo.

5. **🏛️ Biblia del Oro & Reglas FundingPips:**
   - Reglas críticas de la firma fondeada (bloqueo ±5 min en noticias USD de alto impacto, apalancamiento escalonado y cierre antes del rollover bancario a las 18:00 VET).
