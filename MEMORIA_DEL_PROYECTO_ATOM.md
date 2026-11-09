# 🧠 MEMORIA MAESTRA DEL PROYECTO ATOM (Continuidad de Sesión)

> Si estás abriendo una nueva sesión en Antigravity u otro asistente de IA en otra computadora, dale este prompt inicial:
> *"Lee el archivo MEMORIA_DEL_PROYECTO_ATOM.md de este repositorio y continúa ayudándome a operar y automatizar ATOM"*.

---

## 1. Identidad y Propósito del Proyecto
- **Nombre Oficial:** ATOM ⚛️
- **Activo Exclusivo:** Oro Spot / Futuros CME (`XAU/USD` / `GC=F` / `PAXGUSDT` 24/7).
- **Entorno Operativo:** Cuenta de Evaluación y Fondeada de **$10,000 USD** en **FundingPips** operada desde Venezuela (`VET UTC-4`).
- **Tema Visual:** Legacy Dark (`Fondo: #101010`, `Texto: #CCCCCC`, `Acento: #007ACC`).
- **Ubicación del Servidor Local:** `http://127.0.0.1:8050` (iniciado con `gold_assistant\iniciar_atom.bat`).

---

## 2. La Secuencia Inquebrantable de las 5 Reglas de Oro

1. **Regla 1 (Filtro Macro y Horario Killzone NY):**
   - Horario estricto: **09:00 a 11:30 AM hora de Venezuela (VET UTC-4)**.
   - Fuera de la ventana prohibida de $\pm 5\text{ minutos}$ de noticias rojas USD en ForexFactory.

2. **Regla 2 (Toma de Liquidez / Purga / Sweep):**
   - El precio debe barrer con mecha un foco de liquidez previo evidente (`Asian High/Low`, `London High/Low`, `PDH` o `PDL`) y rechazar hacia adentro.

3. **Regla 3 (Cambio en el Estado de Entrega / CISD con cuerpo $\ge 50\%$):**
   - Se exige una vela contraria de desplazamiento contundente cuyo cuerpo represente al menos el **50% del rango total de la vela**, cerrando por debajo/arriba de la apertura de las velas que crearon el extremo barrido.

4. **Regla 4 (Ineficiencia FVG / IFVG & Entrada en 50% Consequent Encroachment):**
   - Identificar el hueco de 3 velas (`BISI` para compras, `SIBI` para ventas o `IFVG`).
   - La orden límite se programa en el borde o preferentemente en el **50% CE (Consequent Encroachment)**.

5. **Regla 5 (Riesgo Cuantitativo Fijo de $50 USD y Protocolo Split 50/50):**
   - Riesgo monetario estricto de **$50.00 USD (0.50%)** por trade.
   - Stop Loss técnico ubicado a $1.00–$1.50 pts de buffer tras la mecha extrema (rango total permitido: **$2.50 a $10.00 pts**).
   - Lotaje dividido en **2 órdenes iguales (Split 50/50)**:
     - **Orden 1 (50% del lote):** Cobra en Take Profit 1 (**1:1.5R** = +$37.50 USD). Al tocar TP1, la **Orden 2 se mueve a Breakeven**.
     - **Orden 2 (50% del lote):** Corre hasta Take Profit 2 (**1:3.0R** = +$75.00 USD).
   - **Circuit Breaker Diario:** Máximo 2 Stop Loss al día (-$100 USD = -1.0%). Al segundo stop se apaga la plataforma hasta el día siguiente (protección absoluta de la regla de pérdida máxima diaria del 5% / -$500 USD de FundingPips).

---

## 3. Arquitectura del Código
- `gold_assistant/ares_server.py`: Servidor web local ASGI (Starlette / Uvicorn).
- `gold_assistant/ares_market_feed.py`: Conector de datos en vivo de Yahoo Finance v8 (API directa en JSON), ForexFactory calendar y cotizaciones 24/7.
- `gold_assistant/ares_smc_engine.py`: Motor de detección algorítmica de niveles, FVG, CISD, Sweeps y matemática de lotaje.
- `gold_assistant/ares_backtest_journal.py`: Backtester de 60 días y base de datos SQLite `ares_data.db`.
- `gold_assistant/static/`: Frontend en HTML5, CSS3 Legacy Dark, y TradingView LightweightCharts.
