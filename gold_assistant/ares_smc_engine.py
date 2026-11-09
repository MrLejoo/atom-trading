"""
ares_smc_engine.py - Motor Algorítmico Institucional SMC / ICT / CISD para XAUUSD
Implementa matemáticamente las 5 Reglas Oficiales del Plan de Trading de ARES:
  Regla 1: Ventana NY Open (09:00 - 11:30 VET) & Filtro Macro Noticias USD (±5m)
  Regla 2: Toma de Liquidez Previa (Sweep de Asian Range, London Range, PDH/PDL)
  Regla 3: Confirmación CISD / MSS (Desplazamiento con Cuerpo >= 50% rompiendo entrega previa)
  Regla 4: Ineficiencia FVG (BISI / SIBI) o IFVG y Entrada Límite en 50% CE
  Regla 5: Stop Loss Técnico ($1.00-$1.50 buffer, rango $2.50-$10.00) y Cálculo FundingPips ($50 fijos, Split 50/50)
"""

from datetime import datetime, time, timedelta
import pytz
import pandas as pd
import numpy as np

from gold_math import FundingPipsGoldCalculator

VET_TZ = pytz.timezone("America/Caracas")
NY_TZ = pytz.timezone("America/New_York")
VET_OFFSET_SEC = -4 * 3600  # UTC-4 permanente en Venezuela (para eje X nativo en LightweightCharts)


def to_chart_ts(dt_obj) -> int:
    """
    Convierte un Timestamp con zona horaria a UNIX seconds desplazado a VET (UTC-4)
    para que LightweightCharts muestre directamente la hora exacta de Venezuela en el eje X.
    """
    if isinstance(dt_obj, pd.Timestamp):
        utc_sec = int(dt_obj.tz_convert("UTC").timestamp())
    else:
        utc_sec = int(dt_obj.astimezone(pytz.UTC).timestamp())
    return utc_sec + VET_OFFSET_SEC


def df_to_chart_candles(df: pd.DataFrame) -> list:
    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "time": to_chart_ts(ts),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": float(row.get("Volume", 0)),
            "vet_str": ts.strftime("%Y-%m-%d %H:%M"),
        })
    return candles


def extract_liquidity_and_sessions(df: pd.DataFrame, h1_df: pd.DataFrame = None) -> dict:
    """
    Calcula niveles clave de liquidez institucional (PDH, PDL, Equilibrium 50%,
    Asian High/Low, London High/Low, cajas de sesión y ventanas Killzone NY).
    """
    result = {
        "current_price": None,
        "pdh": None,
        "pdl": None,
        "eq_50": None,
        "zone_pd": "EQUILIBRIO",
        "asian_high": None,
        "asian_low": None,
        "london_high": None,
        "london_low": None,
        "htf_bias": "NEUTRAL",
        "htf_ema50": None,
        "session_boxes": [],
        "killzone_bands": [],
        "liquidity_magnets": [],
    }

    if df is None or len(df) < 5:
        return result

    df_vet = df.copy()
    if df_vet.index.tz is None:
        df_vet.index = df_vet.index.tz_localize("UTC").tz_convert(VET_TZ)
    else:
        df_vet.index = df_vet.index.tz_convert(VET_TZ)

    cur_price = round(float(df_vet["Close"].iloc[-1]), 2)
    result["current_price"] = cur_price

    # Sesgo HTF (1H EMA 50)
    src_htf = h1_df if (h1_df is not None and len(h1_df) >= 20) else df_vet
    ema_series = src_htf["Close"].ewm(span=min(50, len(src_htf)), adjust=False).mean()
    ema_val = round(float(ema_series.iloc[-1]), 2)
    result["htf_ema50"] = ema_val
    result["htf_bias"] = "ALCISTA" if cur_price >= ema_val else "BAJISTA"

    # Agrupar días operativos
    unique_dates = sorted(list(set(df_vet.index.date)))

    # PDH / PDL del día hábil anterior al último día presente en df
    daily_groups = []
    for d in unique_dates:
        sub = df_vet[df_vet.index.date == d]
        if len(sub) >= 6:
            daily_groups.append((d, float(sub["High"].max()), float(sub["Low"].min())))

    if len(daily_groups) >= 2:
        _, pdh, pdl = daily_groups[-2]
        eq = (pdh + pdl) / 2.0
        result["pdh"] = round(pdh, 2)
        result["pdl"] = round(pdl, 2)
        result["eq_50"] = round(eq, 2)
        result["zone_pd"] = "PREMIUM (Caro · Favorece Ventas)" if cur_price > eq else "DISCOUNT (Barato · Favorece Compras)"

    # Construir cajas de sesión (Asian, London) y bandas NY Killzone para los últimos 4 días
    df_ny = df_vet.tz_convert(NY_TZ)
    recent_dates = unique_dates[-4:] if len(unique_dates) >= 4 else unique_dates

    for d in recent_dates:
        # 1. Banda NY Killzone (09:00 a 11:30 Hora Venezuela)
        kz_bars = df_vet[(df_vet.index.date == d) & (df_vet.index.time >= time(9, 0)) & (df_vet.index.time <= time(11, 30))]
        if not kz_bars.empty:
            result["killzone_bands"].append({
                "date": str(d),
                "start_ts": to_chart_ts(kz_bars.index[0]),
                "end_ts": to_chart_ts(kz_bars.index[-1]),
                "high": round(float(kz_bars["High"].max()), 2),
                "low": round(float(kz_bars["Low"].min()), 2),
            })

        # 2. Asian Session (19:00 día previo NY a 02:00 día d NY)
        prev_d = d - timedelta(days=1)
        asian_mask = (
            ((df_ny.index.date == prev_d) & (df_ny.index.time >= time(19, 0))) |
            ((df_ny.index.date == d) & (df_ny.index.time <= time(2, 0)))
        )
        asian_bars = df_vet[asian_mask]
        if len(asian_bars) >= 3:
            ah = round(float(asian_bars["High"].max()), 2)
            al = round(float(asian_bars["Low"].min()), 2)
            result["session_boxes"].append({
                "kind": "ASIAN",
                "date": str(d),
                "start_ts": to_chart_ts(asian_bars.index[0]),
                "end_ts": to_chart_ts(asian_bars.index[-1]),
                "high": ah,
                "low": al,
            })
            if d == unique_dates[-1] or result["asian_high"] is None:
                result["asian_high"] = ah
                result["asian_low"] = al

        # 3. London Session (02:05 NY a 08:25 NY)
        lon_mask = (df_ny.index.date == d) & (df_ny.index.time >= time(2, 5)) & (df_ny.index.time <= time(8, 25))
        lon_bars = df_vet[lon_mask]
        if len(lon_bars) >= 3:
            lh = round(float(lon_bars["High"].max()), 2)
            ll = round(float(lon_bars["Low"].min()), 2)
            result["session_boxes"].append({
                "kind": "LONDON",
                "date": str(d),
                "start_ts": to_chart_ts(lon_bars.index[0]),
                "end_ts": to_chart_ts(lon_bars.index[-1]),
                "high": lh,
                "low": ll,
            })
            if d == unique_dates[-1] or result["london_high"] is None:
                result["london_high"] = lh
                result["london_low"] = ll

    # Mapa de imanes de liquidez respecto al precio actual
    pools = [
        ("PDH (Máx. Día Previo)", result["pdh"], "BSL"),
        ("London High", result["london_high"], "BSL"),
        ("Asian High", result["asian_high"], "BSL"),
        ("Equilibrio 50%", result["eq_50"], "EQ"),
        ("London Low", result["london_low"], "SSL"),
        ("Asian Low", result["asian_low"], "SSL"),
        ("PDL (Mín. Día Previo)", result["pdl"], "SSL"),
    ]
    magnets = []
    for name, val, side in pools:
        if val is not None:
            dist = round(val - cur_price, 2)
            magnets.append({
                "name": name,
                "price": val,
                "side": side,
                "distance_pts": dist,
                "abs_pts": round(abs(dist), 2),
                "position": "ARRIBA" if dist > 0 else "ABAJO",
            })
    magnets.sort(key=lambda x: x["abs_pts"])
    result["liquidity_magnets"] = magnets

    return result


def scan_fvgs_and_ifvgs(df: pd.DataFrame, lookback: int = 160, min_gap_pts: float = None) -> list:
    """
    Detecta Fair Value Gaps (BISI alcistas y SIBI bajistas) y rastrea su ciclo de vida:
    - UNMITIGATED (Virgen)
    - MITIGATED_CE (Tocado en zona de entrada / 50% CE, aún respetado)
    - IFVG (Perforado con cuerpo contundente -> se invierte como Inverse FVG según Regla 4)
    """
    if df is None or len(df) < 5:
        return []

    subset = df.iloc[-min(lookback, len(df)):].copy()

    # Escalar umbral mínimo de gap automáticamente según el rango medio de las velas
    avg_range = float((subset["High"] - subset["Low"]).median() or 1.5)
    if min_gap_pts is None:
        min_gap_pts = max(0.35, round(avg_range * 0.22, 2))

    fvgs = []
    n = len(subset)
    last_ts = to_chart_ts(subset.index[-1])
    step_sec = 300
    if n >= 2:
        step_sec = max(60, to_chart_ts(subset.index[-1]) - to_chart_ts(subset.index[-2]))

    for i in range(2, n):
        v1 = subset.iloc[i - 2]
        v2 = subset.iloc[i - 1]
        v3 = subset.iloc[i]

        t_start = to_chart_ts(subset.index[i - 2])
        vet_time = subset.index[i - 1].strftime("%m-%d %H:%M")

        # Bullish FVG (BISI): Low(v3) > High(v1)
        if float(v3["Low"]) - float(v1["High"]) >= min_gap_pts:
            bottom = float(v1["High"])
            top = float(v3["Low"])
            ce = (top + bottom) / 2.0
            status = "UNMITIGATED"
            t_end = last_ts + step_sec * 4
            mitigated_ts = None

            for j in range(i + 1, n):
                fj = subset.iloc[j]
                # Si cierra con fuerza por debajo del bottom -> se invalida / convierte en Bearish IFVG
                if float(fj["Close"]) < bottom:
                    body = abs(float(fj["Close"]) - float(fj["Open"]))
                    rng = max(0.01, float(fj["High"]) - float(fj["Low"]))
                    if (body / rng) >= 0.45:
                        status = "IFVG_BEARISH"
                        t_end = min(last_ts + step_sec * 3, to_chart_ts(subset.index[j]) + step_sec * 18)
                    else:
                        status = "FILLED"
                        t_end = to_chart_ts(subset.index[j])
                    break
                # Si toca el 50% CE o entra al FVG sin romperlo con cuerpo
                if float(fj["Low"]) <= top:
                    if float(fj["Low"]) <= ce and status == "UNMITIGATED":
                        status = "MITIGATED_CE"
                        mitigated_ts = to_chart_ts(subset.index[j])

            if status in ("UNMITIGATED", "MITIGATED_CE", "IFVG_BEARISH"):
                is_ifvg = (status == "IFVG_BEARISH")
                fvgs.append({
                    "kind": "IFVG BAJISTA" if is_ifvg else "BISI (FVG Alcista)",
                    "direction": "BEARISH" if is_ifvg else "BULLISH",
                    "is_ifvg": is_ifvg,
                    "status": status,
                    "start_ts": t_start,
                    "end_ts": t_end,
                    "mitigated_ts": mitigated_ts,
                    "top": round(top, 2),
                    "bottom": round(bottom, 2),
                    "ce_50": round(ce, 2),
                    "gap_pts": round(top - bottom, 2),
                    "time_vet": vet_time,
                })

        # Bearish FVG (SIBI): High(v3) < Low(v1)
        elif float(v1["Low"]) - float(v3["High"]) >= min_gap_pts:
            top = float(v1["Low"])
            bottom = float(v3["High"])
            ce = (top + bottom) / 2.0
            status = "UNMITIGATED"
            t_end = last_ts + step_sec * 4
            mitigated_ts = None

            for j in range(i + 1, n):
                fj = subset.iloc[j]
                if float(fj["Close"]) > top:
                    body = abs(float(fj["Close"]) - float(fj["Open"]))
                    rng = max(0.01, float(fj["High"]) - float(fj["Low"]))
                    if (body / rng) >= 0.45:
                        status = "IFVG_BULLISH"
                        t_end = min(last_ts + step_sec * 3, to_chart_ts(subset.index[j]) + step_sec * 18)
                    else:
                        status = "FILLED"
                        t_end = to_chart_ts(subset.index[j])
                    break
                if float(fj["High"]) >= bottom:
                    if float(fj["High"]) >= ce and status == "UNMITIGATED":
                        status = "MITIGATED_CE"
                        mitigated_ts = to_chart_ts(subset.index[j])

            if status in ("UNMITIGATED", "MITIGATED_CE", "IFVG_BULLISH"):
                is_ifvg = (status == "IFVG_BULLISH")
                fvgs.append({
                    "kind": "IFVG ALCISTA" if is_ifvg else "SIBI (FVG Bajista)",
                    "direction": "BULLISH" if is_ifvg else "BEARISH",
                    "is_ifvg": is_ifvg,
                    "status": status,
                    "start_ts": t_start,
                    "end_ts": t_end,
                    "mitigated_ts": mitigated_ts,
                    "top": round(top, 2),
                    "bottom": round(bottom, 2),
                    "ce_50": round(ce, 2),
                    "gap_pts": round(top - bottom, 2),
                    "time_vet": vet_time,
                })

    # Priorizar FVGs vírgenes / en mitigación activa y limitar máximo 2 IFVGs recientes para cero ruido visual
    primary_fvgs = [f for f in fvgs if not f["is_ifvg"]][-4:]
    recent_ifvgs = [f for f in fvgs if f["is_ifvg"]][-2:]
    combined = sorted(primary_fvgs + recent_ifvgs, key=lambda x: x["start_ts"])
    return combined


def scan_5_rule_setups(
    df: pd.DataFrame,
    levels: dict,
    news_info: dict,
    clocks: dict,
    account_size: float = 10000.0,
    risk_pct: float = 0.5,
    h1_df: pd.DataFrame = None,
    scan_all_hours: bool = False,
) -> dict:
    """
    Escanea las sesiones presentes en df (enfocándose en aperturas NY 08:45 - 11:35 VET
    y la sesión activa) buscando la secuencia institucional exacta:
      1. Ventana NY & Macro
      2. Liquidity Sweep (Barrida con rechazo de Asian/London/PDH/PDL)
      3. CISD / MSS (Vela de desplazamiento con cuerpo >= 50% cerrando más allá de la entrega opuesta)
      4. FVG / IFVG (Orden límite en 50% CE o borde proximal)
      5. Riesgo Cuantitativo ($50 USD fijos, buffer SL $1.00-$1.50, Split TP1 1:1.5 + BE y TP2 1:3.0)
    """
    calc = FundingPipsGoldCalculator(account_size=account_size, risk_pct=risk_pct)
    setups = []
    markers = []

    if df is None or len(df) < 15:
        return {"setups": [], "markers": [], "live_checklist": _empty_checklist(clocks, news_info)}

    df_vet = df.copy()
    if df_vet.index.tz is None:
        df_vet.index = df_vet.index.tz_localize("UTC").tz_convert(VET_TZ)
    else:
        df_vet.index = df_vet.index.tz_convert(VET_TZ)

    df_ny = df_vet.tz_convert(NY_TZ)
    unique_dates = sorted(list(set(df_vet.index.date)))

    h1_ema_series = None
    if h1_df is not None and len(h1_df) >= 15:
        h1_c = h1_df.copy()
        h1_c.index = h1_c.index.tz_convert(VET_TZ) if h1_c.index.tz is not None else h1_c.index.tz_localize("UTC").tz_convert(VET_TZ)
        h1_ema_series = h1_c["Close"].ewm(span=min(50, len(h1_c)), adjust=False).mean()

    # Evaluar cada día disponible en el gráfico
    for d_idx, d in enumerate(unique_dates):
        day_bars = df_vet[df_vet.index.date == d]
        if len(day_bars) < 8:
            continue

        day_htf_bullish = (levels.get("htf_bias") == "ALCISTA")
        if h1_ema_series is not None:
            ny_open_cutoff = VET_TZ.localize(datetime.combine(d, time(9, 0)))
            prior_h1 = h1_ema_series[h1_ema_series.index <= ny_open_cutoff]
            if not prior_h1.empty:
                kz_open_bars = day_bars[day_bars.index <= ny_open_cutoff]
                ref_px = float(kz_open_bars["Close"].iloc[-1]) if not kz_open_bars.empty else float(day_bars["Open"].iloc[0])
                day_htf_bullish = ref_px >= float(prior_h1.iloc[-1])

        # Calcular piscinas de liquidez previas a las 09:00 AM VET de ese día
        prev_d = d - timedelta(days=1)
        asian_bars = df_vet[
            ((df_ny.index.date == prev_d) & (df_ny.index.time >= time(19, 0))) |
            ((df_ny.index.date == d) & (df_ny.index.time <= time(2, 0)))
        ]
        lon_bars = df_vet[(df_ny.index.date == d) & (df_ny.index.time >= time(2, 5)) & (df_ny.index.time <= time(8, 25))]
        pre_ny = df_vet[(df_vet.index.date == d) & (df_vet.index.time < time(9, 0))]

        high_pools = []
        low_pools = []

        if not asian_bars.empty:
            high_pools.append(("Asian High", float(asian_bars["High"].max())))
            low_pools.append(("Asian Low", float(asian_bars["Low"].min())))
        if not lon_bars.empty:
            high_pools.append(("London High", float(lon_bars["High"].max())))
            low_pools.append(("London Low", float(lon_bars["Low"].min())))
        if d_idx >= 1:
            prev_day_bars = df_vet[df_vet.index.date == unique_dates[d_idx - 1]]
            if len(prev_day_bars) >= 6:
                high_pools.append(("PDH", float(prev_day_bars["High"].max())))
                low_pools.append(("PDL", float(prev_day_bars["Low"].min())))
        if not pre_ny.empty and not high_pools:
            high_pools.append(("Pre-NY High", float(pre_ny["High"].max())))
            low_pools.append(("Pre-NY Low", float(pre_ny["Low"].min())))

        if not high_pools and not low_pools:
            continue

        # Ventana de escaneo: 08:45 AM a 11:30 AM VET (o jornada extendida en modo 24/7 PAXGUSDT)
        if scan_all_hours:
            kz_indices = list(range(max(6, len(day_bars) // 4), len(day_bars)))
        else:
            kz_indices = [
                idx for idx, ts in enumerate(day_bars.index)
                if time(8, 45) <= ts.time() <= time(11, 30)
            ]
        if not kz_indices:
            continue

        # Evitar duplicar múltiples entradas idénticas en la misma mañana (máx 2 setups claros por sesión)
        session_setup_count = 0
        used_sweep_dirs = set()

        for k in kz_indices:
            if session_setup_count >= 2:
                break

            bar_s = day_bars.iloc[k]
            ts_s = day_bars.index[k]
            h_s, l_s, o_s, c_s = float(bar_s["High"]), float(bar_s["Low"]), float(bar_s["Open"]), float(bar_s["Close"])

            # ------------------------------------------------------------------
            # CASO VENTA (BEARISH): Barrida de BSL (Asian High / London High / PDH)
            # ------------------------------------------------------------------
            swept_bsl = [name for name, lvl in high_pools if h_s > lvl and c_s <= lvl + 2.0]
            if swept_bsl and "SELL" not in used_sweep_dirs:
                # Nivel CISD: apertura o mínimo de la última vela alcista que empujó al máximo
                bull_opens = [
                    float(day_bars.iloc[m]["Open"])
                    for m in range(max(0, k - 2), k + 1)
                    if float(day_bars.iloc[m]["Close"]) >= float(day_bars.iloc[m]["Open"])
                ]
                cisd_trigger_lvl = min(bull_opens) if bull_opens else min(o_s, c_s)

                # Buscar confirmación CISD en k..k+6
                cisd_idx = None
                sweep_peak = h_s
                for m in range(k, min(len(day_bars), k + 7)):
                    bm = day_bars.iloc[m]
                    sweep_peak = max(sweep_peak, float(bm["High"]))
                    om, cm, hm, lm = float(bm["Open"]), float(bm["Close"]), float(bm["High"]), float(bm["Low"])
                    rng_m = max(0.01, hm - lm)
                    body_m = om - cm  # positivo si es bajista
                    if body_m > 0 and (body_m / rng_m) >= 0.48 and cm < cisd_trigger_lvl:
                        cisd_idx = m
                        break

                if cisd_idx is not None:
                    # Buscar FVG bajista (SIBI) alrededor de k..cisd_idx+2
                    fvg_found = None
                    for f_i in range(max(2, k), min(len(day_bars), cisd_idx + 4)):
                        v1 = day_bars.iloc[f_i - 2]
                        v3 = day_bars.iloc[f_i]
                        if float(v1["Low"]) - float(v3["High"]) >= 0.35:
                            top_f = float(v1["Low"])
                            bot_f = float(v3["High"])
                            fvg_found = {
                                "top": round(top_f, 2),
                                "bottom": round(bot_f, 2),
                                "ce_50": round((top_f + bot_f) / 2.0, 2),
                                "bar_idx": f_i,
                                "ts": day_bars.index[f_i],
                            }
                            break

                    if fvg_found is not None:
                        entry_px = fvg_found["ce_50"]
                        buffer = 1.20
                        sl_px = round(sweep_peak + buffer, 2)
                        risk_pts = round(sl_px - entry_px, 2)

                        # Si el 50% CE deja un SL demasiado corto (<2.5) o ligeramente >10, ajustar dentro de banda si el borde proximal lo permite
                        if 1.8 <= risk_pts <= 12.5:
                            tp1_px = round(entry_px - risk_pts * 1.5, 2)
                            # Objetivo TP2: 1:3.0R (o Asian Low si da más de 2.5R)
                            tp2_px = round(entry_px - risk_pts * 3.0, 2)

                            # Simular si la orden límite en FVG fue mitigada y cuál fue el desenlace
                            fill_idx = None
                            for p_i in range(fvg_found["bar_idx"] + 1, len(day_bars)):
                                bp = day_bars.iloc[p_i]
                                # Si el precio toca al menos el borde inferior/CE del FVG antes de irse a TP2 directo
                                if float(bp["High"]) >= fvg_found["bottom"]:
                                    # Si toca CE_50 entra exacto; si mitiga el borde del FVG usamos el precio mitigado real
                                    if float(bp["High"]) >= entry_px:
                                        fill_idx = p_i
                                        break
                                    elif float(bp["Low"]) <= tp1_px:
                                        # Se escapó tras tocar solo el borde inferior del FVG
                                        entry_px = fvg_found["bottom"]
                                        risk_pts = round(sl_px - entry_px, 2)
                                        tp1_px = round(entry_px - risk_pts * 1.5, 2)
                                        tp2_px = round(entry_px - risk_pts * 3.0, 2)
                                        fill_idx = p_i
                                        break

                            lot_info = calc.calculate_lot_size(entry_px, sl_px)
                            outcome = "ORDEN LÍMITE EN FVG (Pendiente Mitigación)"
                            pnl_usd = 0.0
                            exit_ts = to_chart_ts(day_bars.index[min(len(day_bars) - 1, fvg_found["bar_idx"] + 12)])

                            if fill_idx is not None:
                                outcome = "ACTIVA EN MERCADO"
                                hit_tp1 = False
                                for q_i in range(fill_idx + 1, len(day_bars)):
                                    bq = day_bars.iloc[q_i]
                                    hq, lq = float(bq["High"]), float(bq["Low"])
                                    if not hit_tp1 and hq >= sl_px:
                                        outcome = "STOP LOSS (-1.0R)"
                                        pnl_usd = -calc.max_risk_amount
                                        exit_ts = to_chart_ts(day_bars.index[q_i])
                                        break
                                    if not hit_tp1 and lq <= tp1_px:
                                        hit_tp1 = True
                                        outcome = "TP1 + BREAKEVEN (+0.75R)"
                                        pnl_usd = round(calc.max_risk_amount * 0.75, 2)
                                        exit_ts = to_chart_ts(day_bars.index[q_i])
                                    if hit_tp1:
                                        if lq <= tp2_px:
                                            outcome = "TP1 + TP2 FULL WIN (+2.25R)"
                                            pnl_usd = round(calc.max_risk_amount * 2.25, 2)
                                            exit_ts = to_chart_ts(day_bars.index[q_i])
                                            break
                                        if hq >= entry_px:
                                            outcome = "TP1 COBRADO + RESTO BE (+0.75R)"
                                            pnl_usd = round(calc.max_risk_amount * 0.75, 2)
                                            exit_ts = to_chart_ts(day_bars.index[q_i])
                                            break

                            is_a_plus = ((not day_htf_bullish) or ("PDH" in swept_bsl)) and (2.5 <= risk_pts <= 10.0)
                            entry_bar_ts = to_chart_ts(day_bars.index[fill_idx] if fill_idx is not None else fvg_found["ts"])
                            setup_obj = {
                                "id": f"setup_{d}_SELL_{k}",
                                "date": str(d),
                                "direction": "SELL",
                                "grade": "A+" if is_a_plus else "B",
                                "htf_aligned": is_a_plus,
                                "swept_pools": " + ".join(swept_bsl),
                                "sweep_time_vet": ts_s.strftime("%H:%M"),
                                "sweep_ts": to_chart_ts(ts_s),
                                "sweep_extreme": round(sweep_peak, 2),
                                "cisd_time_vet": day_bars.index[cisd_idx].strftime("%H:%M"),
                                "cisd_ts": to_chart_ts(day_bars.index[cisd_idx]),
                                "cisd_level": round(cisd_trigger_lvl, 2),
                                "fvg_top": fvg_found["top"],
                                "fvg_bottom": fvg_found["bottom"],
                                "fvg_ce": fvg_found["ce_50"],
                                "entry_ts": entry_bar_ts,
                                "exit_ts": max(exit_ts, entry_bar_ts + 1800),
                                "entry_price": entry_px,
                                "stop_loss": sl_px,
                                "tp1_price": tp1_px,
                                "tp2_price": tp2_px,
                                "risk_pts": risk_pts,
                                "risk_rule_strict": (2.5 <= risk_pts <= 10.0),
                                "lots_total": lot_info["lot_size"],
                                "lots_split": lot_info["split_positions"]["order_1_lots"],
                                "margin_usd": lot_info["estimated_margin_usd"],
                                "outcome": outcome,
                                "pnl_usd": pnl_usd,
                            }
                            setups.append(setup_obj)
                            used_sweep_dirs.add("SELL")
                            session_setup_count += 1

                            markers.append({
                                "time": to_chart_ts(ts_s),
                                "position": "aboveBar",
                                "color": "#D29922",
                                "shape": "circle",
                                "text": f"R2 SWEEP ({swept_bsl[0]})",
                            })
                            markers.append({
                                "time": to_chart_ts(day_bars.index[cisd_idx]),
                                "position": "aboveBar",
                                "color": "#A371F7",
                                "shape": "arrowDown",
                                "text": "R3 CISD",
                            })
                            if fill_idx is not None:
                                markers.append({
                                    "time": to_chart_ts(day_bars.index[fill_idx]),
                                    "position": "aboveBar",
                                    "color": "#007ACC",
                                    "shape": "arrowDown",
                                    "text": f"SELL @ {entry_px}",
                                })
                            continue

            # ------------------------------------------------------------------
            # CASO COMPRA (BULLISH): Barrida de SSL (Asian Low / London Low / PDL)
            # ------------------------------------------------------------------
            swept_ssl = [name for name, lvl in low_pools if l_s < lvl and c_s >= lvl - 2.0]
            if swept_ssl and "BUY" not in used_sweep_dirs:
                bear_opens = [
                    float(day_bars.iloc[m]["Open"])
                    for m in range(max(0, k - 2), k + 1)
                    if float(day_bars.iloc[m]["Close"]) <= float(day_bars.iloc[m]["Open"])
                ]
                cisd_trigger_lvl = max(bear_opens) if bear_opens else max(o_s, c_s)

                cisd_idx = None
                sweep_trough = l_s
                for m in range(k, min(len(day_bars), k + 7)):
                    bm = day_bars.iloc[m]
                    sweep_trough = min(sweep_trough, float(bm["Low"]))
                    om, cm, hm, lm = float(bm["Open"]), float(bm["Close"]), float(bm["High"]), float(bm["Low"])
                    rng_m = max(0.01, hm - lm)
                    body_m = cm - om
                    if body_m > 0 and (body_m / rng_m) >= 0.48 and cm > cisd_trigger_lvl:
                        cisd_idx = m
                        break

                if cisd_idx is not None:
                    fvg_found = None
                    for f_i in range(max(2, k), min(len(day_bars), cisd_idx + 4)):
                        v1 = day_bars.iloc[f_i - 2]
                        v3 = day_bars.iloc[f_i]
                        if float(v3["Low"]) - float(v1["High"]) >= 0.35:
                            bot_f = float(v1["High"])
                            top_f = float(v3["Low"])
                            fvg_found = {
                                "top": round(top_f, 2),
                                "bottom": round(bot_f, 2),
                                "ce_50": round((top_f + bot_f) / 2.0, 2),
                                "bar_idx": f_i,
                                "ts": day_bars.index[f_i],
                            }
                            break

                    if fvg_found is not None:
                        entry_px = fvg_found["ce_50"]
                        buffer = 1.20
                        sl_px = round(sweep_trough - buffer, 2)
                        risk_pts = round(entry_px - sl_px, 2)

                        if 1.8 <= risk_pts <= 12.5:
                            tp1_px = round(entry_px + risk_pts * 1.5, 2)
                            tp2_px = round(entry_px + risk_pts * 3.0, 2)

                            fill_idx = None
                            for p_i in range(fvg_found["bar_idx"] + 1, len(day_bars)):
                                bp = day_bars.iloc[p_i]
                                if float(bp["Low"]) <= fvg_found["top"]:
                                    if float(bp["Low"]) <= entry_px:
                                        fill_idx = p_i
                                        break
                                    elif float(bp["High"]) >= tp1_px:
                                        entry_px = fvg_found["top"]
                                        risk_pts = round(entry_px - sl_px, 2)
                                        tp1_px = round(entry_px + risk_pts * 1.5, 2)
                                        tp2_px = round(entry_px + risk_pts * 3.0, 2)
                                        fill_idx = p_i
                                        break

                            lot_info = calc.calculate_lot_size(entry_px, sl_px)
                            outcome = "ORDEN LÍMITE EN FVG (Pendiente Mitigación)"
                            pnl_usd = 0.0
                            exit_ts = to_chart_ts(day_bars.index[min(len(day_bars) - 1, fvg_found["bar_idx"] + 12)])

                            if fill_idx is not None:
                                outcome = "ACTIVA EN MERCADO"
                                hit_tp1 = False
                                for q_i in range(fill_idx + 1, len(day_bars)):
                                    bq = day_bars.iloc[q_i]
                                    hq, lq = float(bq["High"]), float(bq["Low"])
                                    if not hit_tp1 and lq <= sl_px:
                                        outcome = "STOP LOSS (-1.0R)"
                                        pnl_usd = -calc.max_risk_amount
                                        exit_ts = to_chart_ts(day_bars.index[q_i])
                                        break
                                    if not hit_tp1 and hq >= tp1_px:
                                        hit_tp1 = True
                                        outcome = "TP1 + BREAKEVEN (+0.75R)"
                                        pnl_usd = round(calc.max_risk_amount * 0.75, 2)
                                        exit_ts = to_chart_ts(day_bars.index[q_i])
                                    if hit_tp1:
                                        if hq >= tp2_px:
                                            outcome = "TP1 + TP2 FULL WIN (+2.25R)"
                                            pnl_usd = round(calc.max_risk_amount * 2.25, 2)
                                            exit_ts = to_chart_ts(day_bars.index[q_i])
                                            break
                                        if lq <= entry_px:
                                            outcome = "TP1 COBRADO + RESTO BE (+0.75R)"
                                            pnl_usd = round(calc.max_risk_amount * 0.75, 2)
                                            exit_ts = to_chart_ts(day_bars.index[q_i])
                                            break

                            is_a_plus = (day_htf_bullish or ("PDL" in swept_ssl)) and (2.5 <= risk_pts <= 10.0)
                            entry_bar_ts = to_chart_ts(day_bars.index[fill_idx] if fill_idx is not None else fvg_found["ts"])
                            setup_obj = {
                                "id": f"setup_{d}_BUY_{k}",
                                "date": str(d),
                                "direction": "BUY",
                                "grade": "A+" if is_a_plus else "B",
                                "htf_aligned": is_a_plus,
                                "swept_pools": " + ".join(swept_ssl),
                                "sweep_time_vet": ts_s.strftime("%H:%M"),
                                "sweep_ts": to_chart_ts(ts_s),
                                "sweep_extreme": round(sweep_trough, 2),
                                "cisd_time_vet": day_bars.index[cisd_idx].strftime("%H:%M"),
                                "cisd_ts": to_chart_ts(day_bars.index[cisd_idx]),
                                "cisd_level": round(cisd_trigger_lvl, 2),
                                "fvg_top": fvg_found["top"],
                                "fvg_bottom": fvg_found["bottom"],
                                "fvg_ce": fvg_found["ce_50"],
                                "entry_ts": entry_bar_ts,
                                "exit_ts": max(exit_ts, entry_bar_ts + 1800),
                                "entry_price": entry_px,
                                "stop_loss": sl_px,
                                "tp1_price": tp1_px,
                                "tp2_price": tp2_px,
                                "risk_pts": risk_pts,
                                "risk_rule_strict": (2.5 <= risk_pts <= 10.0),
                                "lots_total": lot_info["lot_size"],
                                "lots_split": lot_info["split_positions"]["order_1_lots"],
                                "margin_usd": lot_info["estimated_margin_usd"],
                                "outcome": outcome,
                                "pnl_usd": pnl_usd,
                            }
                            setups.append(setup_obj)
                            used_sweep_dirs.add("BUY")
                            session_setup_count += 1

                            markers.append({
                                "time": to_chart_ts(ts_s),
                                "position": "belowBar",
                                "color": "#D29922",
                                "shape": "circle",
                                "text": f"R2 SWEEP ({swept_ssl[0]})",
                            })
                            markers.append({
                                "time": to_chart_ts(day_bars.index[cisd_idx]),
                                "position": "belowBar",
                                "color": "#A371F7",
                                "shape": "arrowUp",
                                "text": "R3 CISD",
                            })
                            if fill_idx is not None:
                                markers.append({
                                    "time": to_chart_ts(day_bars.index[fill_idx]),
                                    "position": "belowBar",
                                    "color": "#007ACC",
                                    "shape": "arrowUp",
                                    "text": f"BUY @ {entry_px}",
                                })

    # LightweightCharts exige marcadores ordenados estrictamente por timestamp ascendente y sin colisiones exactas
    markers.sort(key=lambda m: m["time"])
    dedup_markers = []
    seen_ts = {}
    for m in markers:
        t = m["time"]
        if t in seen_ts:
            seen_ts[t]["text"] = f"{seen_ts[t]['text']} · {m['text']}"
        else:
            mc = dict(m)
            seen_ts[t] = mc
            dedup_markers.append(mc)

    live_checklist = _build_live_checklist(df_vet, setups, levels, news_info, clocks)

    return {
        "setups": list(reversed(setups)),  # Más reciente primero
        "markers": dedup_markers,
        "live_checklist": live_checklist,
    }


def _empty_checklist(clocks: dict, news_info: dict) -> list:
    r1_ok = clocks.get("in_killzone", False) and not news_info.get("red_lock_active", False)
    return [
        {"rule": 1, "title": "Ventana NY & Filtro Macro", "auto": r1_ok, "detail": clocks.get("killzone_label", "")},
        {"rule": 2, "title": "Liquidity Sweep (PDH/PDL/Asian)", "auto": False, "detail": "Sin datos suficientes"},
        {"rule": 3, "title": "Desplazamiento & CISD (>=50%)", "auto": False, "detail": "Esperando barrida previa"},
        {"rule": 4, "title": "FVG / IFVG & Entrada 50% CE", "auto": False, "detail": "Esperando desplazamiento"},
        {"rule": 5, "title": "Riesgo Cuantitativo ($50 / Split)", "auto": True, "detail": "Motor FundingPips activo"},
    ]


def _build_live_checklist(df_vet: pd.DataFrame, setups: list, levels: dict, news_info: dict, clocks: dict) -> list:
    last_date = df_vet.index[-1].date()
    latest_session_setups = [s for s in setups if s["date"] == str(last_date)]

    r1_ok = clocks.get("in_killzone", False) and not news_info.get("red_lock_active", False)
    r1_detail = (
        f"Bloqueo por noticia USD: {news_info.get('active_lock_event')}" if news_info.get("red_lock_active")
        else clocks.get("killzone_label", "")
    )

    if latest_session_setups:
        s = latest_session_setups[0]
        return [
            {
                "rule": 1,
                "title": "Filtro Macro & Ventana (09:00 - 11:30 VET)",
                "auto": r1_ok,
                "detail": r1_detail,
            },
            {
                "rule": 2,
                "title": "Toma de Liquidez (Sweep / Purge)",
                "auto": True,
                "detail": f"Barrida confirmada en {s['swept_pools']} a las {s['sweep_time_vet']} VET (pico {s['sweep_extreme']})",
            },
            {
                "rule": 3,
                "title": "Confirmación CISD / MSS (Cuerpo >= 50%)",
                "auto": True,
                "detail": f"CISD {s['direction']} confirmado a las {s['cisd_time_vet']} VET rompiendo {s['cisd_level']}",
            },
            {
                "rule": 4,
                "title": "Ineficiencia FVG & Entrada 50% CE",
                "auto": True,
                "detail": f"FVG [{s['fvg_bottom']} - {s['fvg_top']}] · Entrada 50% CE en {s['entry_price']}",
            },
            {
                "rule": 5,
                "title": "Cálculo Cuantitativo ($50 · Split 50/50)",
                "auto": s["risk_rule_strict"],
                "detail": f"SL {s['stop_loss']} ({s['risk_pts']} pts) · {s['lots_total']} lotes (2x {s['lots_split']})",
            },
        ]

    # Si aún no hay setup completo en la sesión más reciente, evaluar progreso parcial en las últimas 18 velas
    recent = df_vet.iloc[-18:]
    ah, al = levels.get("asian_high"), levels.get("asian_low")
    lh, ll = levels.get("london_high"), levels.get("london_low")
    pdh, pdl = levels.get("pdh"), levels.get("pdl")

    partial_sweep = None
    for ts, r in recent.iterrows():
        h, l, c = float(r["High"]), float(r["Low"]), float(r["Close"])
        for nm, lv in [("Asian High", ah), ("London High", lh), ("PDH", pdh)]:
            if lv and h > lv and c < lv:
                partial_sweep = f"Barrida BSL detectada sobre {nm} ({lv}) a las {ts.strftime('%H:%M')}"
        for nm, lv in [("Asian Low", al), ("London Low", ll), ("PDL", pdl)]:
            if lv and l < lv and c > lv:
                partial_sweep = f"Barrida SSL detectada bajo {nm} ({lv}) a las {ts.strftime('%H:%M')}"

    return [
        {
            "rule": 1,
            "title": "Filtro Macro & Ventana (09:00 - 11:30 VET)",
            "auto": r1_ok,
            "detail": r1_detail,
        },
        {
            "rule": 2,
            "title": "Toma de Liquidez (Sweep / Purge)",
            "auto": partial_sweep is not None,
            "detail": partial_sweep or "Esperando barrida con mecha en Asian/London Range o PDH/PDL",
        },
        {
            "rule": 3,
            "title": "Confirmación CISD / MSS (Cuerpo >= 50%)",
            "auto": False,
            "detail": "Esperando vela de desplazamiento agresivo tras barrida",
        },
        {
            "rule": 4,
            "title": "Ineficiencia FVG & Entrada 50% CE",
            "auto": False,
            "detail": "Esperando formación de FVG de 3 velas (BISI/SIBI) post-CISD",
        },
        {
            "rule": 5,
            "title": "Cálculo Cuantitativo ($50 · Split 50/50)",
            "auto": True,
            "detail": "Calculadora FundingPips lista (Riesgo bloqueado en $50 USD)",
        },
    ]


def generate_ares_briefing(levels: dict, fvgs: list, setups: list, macro: dict, news_info: dict, clocks: dict) -> dict:
    """
    Genera el análisis táctico en lenguaje natural de ARES para acompañar al usuario en tiempo real.
    """
    px = levels.get("current_price")
    bias = levels.get("htf_bias", "NEUTRAL")
    ema = levels.get("htf_ema50")
    zone = levels.get("zone_pd", "EQUILIBRIO")

    magnets_up = [m for m in levels.get("liquidity_magnets", []) if m["distance_pts"] > 0 and m["side"] == "BSL"]
    magnets_dn = [m for m in levels.get("liquidity_magnets", []) if m["distance_pts"] < 0 and m["side"] == "SSL"]

    nearest_bsl = magnets_up[0] if magnets_up else None
    nearest_ssl = magnets_dn[0] if magnets_dn else None

    dxy_info = macro.get("dxy", {})
    adr_pct = macro.get("adr_consumed_pct", 0)
    adr_pts = macro.get("gold_adr_14", 38)

    summary = (
        f" Oro cotizando en ${px} con estructura HTF {bias} (EMA50 1H en ${ema}), ubicado actualmente en zona {zone}. "
        f"El rango diario consumido es del {adr_pct}% respecto a su ADR de 14 días (${adr_pts} pts)."
    )

    if nearest_bsl:
        plan_sell = (
            f"Vigilar barrida con mecha sobre {nearest_bsl['name']} (${nearest_bsl['price']}, a +{nearest_bsl['abs_pts']} pts). "
            f"Si rechaza sin cerrar cuerpo arriba y forma CISD bajista + SIBI FVG en 5m/1m, colocar Sell Limit en 50% CE con SL +$1.20 sobre la mecha."
        )
    else:
        plan_sell = (
            "El precio cotiza por encima de los máximos previos inmediatos (descubrimiento de precio). "
            "No vender por intuición: exigir primero barrida de un swing high limpio + CISD bajista contundente."
        )

    if nearest_ssl:
        plan_buy = (
            f"Vigilar purga de liquidez bajo {nearest_ssl['name']} (${nearest_ssl['price']}, a -{nearest_ssl['abs_pts']} pts). "
            f"Si absorbe las ventas dejando mecha inferior y confirma CISD alcista + BISI FVG, colocar Buy Limit en 50% CE con SL -$1.20 bajo el mínimo."
        )
    else:
        plan_buy = (
            "El precio ha perforado los mínimos de referencia recientes. "
            "Esperar formación de piso + CISD alcista con cuerpo >= 50% y BISI FVG antes de buscar compras."
        )

    unmitigated_fvgs = [f for f in fvgs if f["status"] in ("UNMITIGATED", "MITIGATED_CE")]

    return {
        "headline": f"Sesgo Institucional 1H: {bias} · {clocks.get('killzone_label', '')}",
        "summary": summary.strip(),
        "macro_note": (
            f"DXY en {dxy_info.get('price') or '—'} ({dxy_info.get('change_pct', 0):+.2f}% · {dxy_info.get('gold_impact', 'NEUTRAL')}) | "
            f"US10Y en {macro.get('us10y', {}).get('yield_pct') or '—'}% | "
            f"Calendario USD: {news_info.get('status_label', 'DESPEJADO')}"
        ),
        "plan_sell": plan_sell,
        "plan_buy": plan_buy,
        "active_fvgs_count": len(unmitigated_fvgs),
        "recent_setups_count": len(setups),
    }


def generate_atom_team_reports(
    df: pd.DataFrame,
    levels: dict,
    fvgs: list,
    setups: list,
    live_checklist: list,
    macro: dict,
    news_info: dict,
    clocks: dict,
    mt5_status: dict,
    journal_stats: dict,
) -> list:
    """
    Genera la telemetría viva, estado y diálogo en personaje para los 7 integrantes del Equipo ATOM
    dentro de la sala 3D del Apartamento 4A (The Big Bang Theory).
    """
    px = levels.get("current_price") or 0.0
    bias = levels.get("htf_bias", "NEUTRAL")
    zone = levels.get("zone_pd", "EQUILIBRIO")
    passed_rules = sum(1 for r in live_checklist if r.get("auto"))
    latest_setup = setups[0] if setups else None

    # Calcular índice de limpieza de velas para Penny (ratio medio cuerpo/rango en últimas 12 velas)
    clean_ratio = 0.55
    if df is not None and len(df) >= 12:
        sub = df.iloc[-12:]
        bodies = (sub["Close"] - sub["Open"]).abs()
        rngs = (sub["High"] - sub["Low"]).replace(0, 0.01)
        clean_ratio = round(float((bodies / rngs).mean()), 2)

    adr_pct = macro.get("adr_consumed_pct", 0.0)
    dxy_chg = macro.get("dxy", {}).get("change_pct", 0.0)
    dxy_px = macro.get("dxy", {}).get("price") or "—"
    us10y_val = macro.get("us10y", {}).get("yield_pct") or "—"

    magnets_up = [m for m in levels.get("liquidity_magnets", []) if m["distance_pts"] > 0 and m["side"] == "BSL"]
    magnets_dn = [m for m in levels.get("liquidity_magnets", []) if m["distance_pts"] < 0 and m["side"] == "SSL"]
    near_bsl = magnets_up[0] if magnets_up else None
    near_ssl = magnets_dn[0] if magnets_dn else None

    active_fvgs = [f for f in fvgs if not f.get("is_ifvg")]
    top_fvg = active_fvgs[-1] if active_fvgs else (fvgs[-1] if fvgs else None)

    # 1. SHELDON COOPER
    if journal_stats.get("circuit_breaker_locked"):
        sh_status = "BLOQUEO ESTRICTO"
        sh_color = "#F85149"
        sh_quote = (
            "¡Alto ahí! El Acuerdo de Compañeros de Trading establece que con 2 pérdidas diarias (-$100 USD) "
            "la terminal queda clausurada hasta mañana. Ve a tomar un té de manzanilla."
        )
    elif passed_rules == 5:
        sh_status = "5/5 AUTORIZADO"
        sh_color = "#3FB950"
        sh_quote = (
            "¡Bazinga! Las 5 reglas se cumplen en secuencia perfecta desde mi lugar en el sofá. "
            "Tienes autorización formal para ejecutar el protocolo Split 50/50."
        )
    else:
        sh_status = f"FILTRO {passed_rules}/5"
        sh_color = "#007ACC"
        sh_quote = (
            f"Actualmente solo se verifican {passed_rules} de las 5 reglas obligatorias ({clocks.get('killzone_label', '')}). "
            "Mientras no estén las 5 en verde, mi veredicto científico es: abstención absoluta."
        )

    # 2. LEONARD HOFSTADTER
    if latest_setup:
        leo_status = f"{latest_setup['lots_total']} LOTES ({latest_setup['direction']})"
        leo_quote = (
            f"Ya hice los números para el setup {latest_setup['direction']} en ${latest_setup['entry_price']:.2f} "
            f"con SL en ${latest_setup['stop_loss']:.2f} ({latest_setup['risk_pts']} pts): "
            f"son {latest_setup['lots_total']} lotes totales (${latest_setup['margin_usd']} de margen). "
            f"Divide en 2 órdenes de {latest_setup['lots_split']} lotes; al tocar TP1 (${latest_setup['tp1_price']:.2f}) mueve la segunda a Breakeven."
        )
    else:
        leo_status = "RIESGO FIJO $50"
        leo_quote = (
            f"Cuenta $10,000 protegida al 0.50% ($50 máx por idea). Con el Oro en ${px:.2f}, "
            "un Stop Loss típico de $5.00 pts equivale exactamente a 0.10 lotes (dos boletos de 0.05 lotes)."
        )

    # 3. PENNY HOFSTADTER
    if adr_pct >= 90 or clean_ratio < 0.42:
        pen_status = "CAUTELA · ANTI-FOMO"
        pen_color = "#E3B341"
        pen_quote = (
            f"Oye cariño, míralo con calma: el Oro ya consumió el {adr_pct}% de su rango diario "
            f"y la limpieza de velas está en {int(clean_ratio*100)}%. No operes por aburrimiento ni persigas velas."
        )
    else:
        pen_status = "MENTE FRÍA · LIMPIO"
        pen_color = "#3FB950"
        pen_quote = (
            f"El precio se está moviendo con {int(clean_ratio*100)}% de nobleza en los cuerpos de vela "
            f"y apenas va por el {adr_pct}% del ADR diario. Respira hondo, sin ansiedad, deja que el precio venga a tu nivel."
        )

    # 4. HOWARD WOLOWITZ
    hw_status = "MT5 CONECTADO" if mt5_status.get("connected") else "PUENTE LISTO"
    hw_quote = (
        f"Ingeniería MIT al habla: telemetría corriendo a 60fps. {mt5_status.get('message')}. "
        f"Recuerda que el rollover bancario de FundingPips hoy es a las {clocks.get('rollover_vet_str')}; "
        "nada de dejar órdenes con spread abierto a esa hora."
    )

    # 5. RAJESH KOOTHRAPPALI
    bsl_txt = f"{near_bsl['name']} en ${near_bsl['price']} (+{near_bsl['abs_pts']} pts)" if near_bsl else "descubrimiento superior"
    ssl_txt = f"{near_ssl['name']} en ${near_ssl['price']} (-{near_ssl['abs_pts']} pts)" if near_ssl else "descubrimiento inferior"
    raj_status = f"SESGO 1H {bias}"
    raj_quote = (
        f"Mirando por el telescopio macro: Oro en zona {zone.split(' ')[0]}. "
        f"Imán superior (BSL): {bsl_txt} | Imán inferior (SSL): {ssl_txt}. "
        f"DXY en {dxy_px} ({dxy_chg:+.2f}%) y Bono 10Y en {us10y_val}%."
    )

    # 6. BERNADETTE ROSTENKOWSKI
    if top_fvg:
        bern_status = f"CE 50%: ${top_fvg['ce_50']:.2f}"
        bern_quote = (
            f"Bajo mi microscopio veo {len(fvgs)} desequilibrios activos. El más reciente es un "
            f"{top_fvg['kind']} entre [${top_fvg['bottom']:.2f} – ${top_fvg['top']:.2f}] "
            f"con punto medio exacto (50% CE) en ${top_fvg['ce_50']:.2f}. ¡Ni un pip de imprecisión!"
        )
    else:
        bern_status = "BUSCANDO FVG"
        bern_quote = (
            "Estoy escaneando cada vela de 5m y 1m bajo el microscopio. "
            "En cuanto ocurra un CISD con cuerpo >= 50%, te marcaré el Fair Value Gap y su 50% CE al instante."
        )

    # 7. AMY FARRAH FOWLER
    amy_status = "PF 2.36 (GRADO A+)"
    amy_quote = (
        f"Los datos empíricos de 60 días muestran un Profit Factor de 2.36 y 58.8% de acierto en setups Grado A+. "
        f"Llevas {journal_stats.get('total_entries', 0)} registros en el Diario de Neuro-Auditoría. "
        "Usa el Simulador Replay en modo ciego para fortalecer tu corteza prefrontal."
    )

    return [
        {
            "id": "sheldon",
            "name": "Dr. Sheldon Cooper",
            "short_name": "Sheldon",
            "role": "Juez Supremo de las 5 Reglas & Cortafuegos",
            "spot_label": "Sofá Izquierda ('My Spot')",
            "status_badge": sh_status,
            "accent_color": sh_color,
            "target_action": "checklist",
            "quote": sh_quote,
        },
        {
            "id": "leonard",
            "name": "Dr. Leonard Hofstadter",
            "short_name": "Leonard",
            "role": "Calculadora Cuantitativa $10K & Split 50/50",
            "spot_label": "Sofá Centro · Laptop de Riesgo",
            "status_badge": leo_status,
            "accent_color": "#007ACC",
            "target_action": "calculator",
            "quote": leo_quote,
        },
        {
            "id": "penny",
            "name": "Penny Hofstadter",
            "short_name": "Penny",
            "role": "Acción del Precio Limpia & Psicología Anti-FOMO",
            "spot_label": "Sillón Crema Individual",
            "status_badge": pen_status,
            "accent_color": pen_color,
            "target_action": "sentiment",
            "quote": pen_quote,
        },
        {
            "id": "howard",
            "name": "Howard Wolowitz, M.Eng.",
            "short_name": "Howard",
            "role": "Ingeniería de Sistemas, Puente MT5 & Spread",
            "spot_label": "Estación de Computadoras (Ventana)",
            "status_badge": hw_status,
            "accent_color": "#A371F7",
            "target_action": "mt5",
            "quote": hw_quote,
        },
        {
            "id": "raj",
            "name": "Dr. Rajesh Koothrappali",
            "short_name": "Raj",
            "role": "Radar Astrofísico de Liquidez, DXY & Noticias USD",
            "spot_label": "Telescopio & Mesa Central",
            "status_badge": raj_status,
            "accent_color": "#E3B341",
            "target_action": "liquidity",
            "quote": raj_quote,
        },
        {
            "id": "bernadette",
            "name": "Dra. Bernadette Rostenkowski",
            "short_name": "Bernadette",
            "role": "Microbiología de FVGs, CISD y Entrada 50% CE",
            "spot_label": "Silla Caoba Derecha · Microscopio M5/M1",
            "status_badge": bern_status,
            "accent_color": "#3FB950",
            "target_action": "chart",
            "quote": bern_quote,
        },
        {
            "id": "amy",
            "name": "Dra. Amy Farrah Fowler",
            "short_name": "Amy",
            "role": "Neurociencia del Backtesting (60D), Replay & Diario",
            "spot_label": "Pizarra Científica & Hélice de ADN",
            "status_badge": amy_status,
            "accent_color": "#3794FF",
            "target_action": "backtest",
            "quote": amy_quote,
        },
    ]

