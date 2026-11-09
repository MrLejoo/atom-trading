"""
ares_market_feed.py - Motor de Datos en Tiempo Real, Macro y Noticias USD para ARES
Fuentes soportadas:
1. Institucional Oro CME / Spot Proxy (GC=F vía Yahoo Finance HTTP directo sin fallos DNS)
2. Oro Físico Spot 24/7 (PAXGUSDT vía Binance REST para monitoreo en vivo incluso fines de semana)
3. Correlaciones Macro en Vivo: DXY (DX-Y.NYB) y Bonos 10 Años EE.UU. (^TNX)
4. Calendario Económico USD (ForexFactory JSON oficial convertido a Hora Venezuela UTC-4)
5. Puente Opcional MetaTrader 5 (listo para conectar cuando el usuario instale MT5)
"""

import os
import json
import time as time_mod
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import requests

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

VET_TZ = pytz.timezone("America/Caracas")
NY_TZ = pytz.timezone("America/New_York")
UTC_TZ = pytz.UTC

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*"
})

_MEM_CACHE = {}


def _get_cached(key: str, ttl_seconds: int):
    now = time_mod.time()
    if key in _MEM_CACHE:
        ts, data = _MEM_CACHE[key]
        if now - ts <= ttl_seconds:
            return data
    return None


def _set_cached(key: str, data, persist_disk: bool = True):
    _MEM_CACHE[key] = (time_mod.time(), data)
    if persist_disk:
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in key)
        disk_path = os.path.join(CACHE_DIR, f"{safe_name}.json")
        try:
            with open(disk_path, "w", encoding="utf-8") as f:
                json.dump({"saved_at": time_mod.time(), "payload": data}, f)
        except Exception:
            pass


def _load_disk_fallback(key: str):
    safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in key)
    disk_path = os.path.join(CACHE_DIR, f"{safe_name}.json")
    if os.path.exists(disk_path):
        try:
            with open(disk_path, "r", encoding="utf-8") as f:
                return json.load(f).get("payload")
        except Exception:
            return None
    return None


def fetch_yahoo_raw(symbol: str, interval: str = "5m", range_str: str = "10d", ttl: int = 12) -> dict:
    """
    Consulta directa al endpoint v8 chart de Yahoo Finance usando requests (DNS nativo del SO).
    """
    cache_key = f"yf_{symbol}_{interval}_{range_str}"
    cached = _get_cached(cache_key, ttl)
    if cached is not None:
        return cached

    encoded_sym = requests.utils.quote(symbol)
    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_sym}?interval={interval}&range={range_str}&includePrePost=true",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded_sym}?interval={interval}&range={range_str}&includePrePost=true",
    ]

    last_err = None
    for url in urls:
        try:
            resp = SESSION.get(url, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                result_list = payload.get("chart", {}).get("result")
                if result_list:
                    _set_cached(cache_key, result_list[0], persist_disk=True)
                    return result_list[0]
        except Exception as e:
            last_err = e

    fallback = _load_disk_fallback(cache_key)
    if fallback is not None:
        return fallback

    raise RuntimeError(f"No se pudo conectar a Yahoo Finance para {symbol}: {last_err}")


def fetch_candles_df(source: str = "GC=F", interval: str = "5m", range_str: str = None, ttl: int = 10) -> pd.DataFrame:
    """
    Devuelve un DataFrame limpio con columnas ['Open', 'High', 'Low', 'Close', 'Volume']
    indexado por DatetimeIndex en America/Caracas (VET, UTC-4).
    """
    if source == "PAXGUSDT":
        return fetch_paxg_binance_df(interval=interval, limit=750, ttl=ttl)

    if source == "MT5":
        df_mt5 = fetch_mt5_candles_df(interval=interval, count=800)
        if df_mt5 is not None and not df_mt5.empty:
            return df_mt5
        # Si MT5 no está abierto aún, usar GC=F transparente
        source = "GC=F"

    if range_str is None:
        range_map = {
            "1m": "7d",
            "5m": "15d",
            "15m": "30d",
            "1h": "60d",
            "1d": "1y",
        }
        range_str = range_map.get(interval, "15d")

    raw = fetch_yahoo_raw(symbol=source, interval=interval, range_str=range_str, ttl=ttl)
    timestamps = raw.get("timestamp", [])
    quote = raw.get("indicators", {}).get("quote", [{}])[0]

    if not timestamps or not quote:
        raise ValueError(f"Datos vacíos para {source} ({interval}).")

    df = pd.DataFrame({
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Volume": quote.get("volume", [0] * len(timestamps)),
    }, index=pd.to_datetime(timestamps, unit="s", utc=True))

    df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    df["Volume"] = df["Volume"].fillna(0)
    # Eliminar timestamps duplicados y asegurar orden ascendente estricto
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index = df.index.tz_convert(VET_TZ)
    return df


def fetch_paxg_binance_df(interval: str = "5m", limit: int = 600, ttl: int = 8) -> pd.DataFrame:
    """
    Oro físico tokenizado 1:1 (PAX Gold) con cotización spot en tiempo real 24/7 (incluyendo sábados y domingos).
    """
    b_interval = interval if interval in ("1m", "5m", "15m", "1h", "1d") else "5m"
    cache_key = f"paxg_{b_interval}_{limit}"
    cached = _get_cached(cache_key, ttl)
    if cached is None:
        url = f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={b_interval}&limit={limit}"
        try:
            r = SESSION.get(url, timeout=8)
            r.raise_for_status()
            cached = r.json()
            _set_cached(cache_key, cached, persist_disk=True)
        except Exception as e:
            cached = _load_disk_fallback(cache_key)
            if cached is None:
                raise RuntimeError(f"Error consultando PAXGUSDT 24/7: {e}")

    rows = []
    idx = []
    for k in cached:
        idx.append(pd.to_datetime(int(k[0]), unit="ms", utc=True))
        rows.append({
            "Open": float(k[1]),
            "High": float(k[2]),
            "Low": float(k[3]),
            "Close": float(k[4]),
            "Volume": float(k[5]),
        })
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(idx))
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index = df.index.tz_convert(VET_TZ)
    return df


def fetch_macro_context() -> dict:
    """
    Obtiene correlaciones macroeconómicas del Oro en vivo:
    - DXY (Índice del Dólar): correlación inversa con XAUUSD
    - US10Y (Rendimiento Bono Tesoro 10 años EE.UU.): presión de tasas reales
    - ADR 14 días del Oro (Average Daily Range en dólares/puntos)
    """
    macro = {
        "dxy": {"price": None, "change_pct": 0.0, "trend_1h": "NEUTRAL", "gold_impact": "NEUTRAL"},
        "us10y": {"yield_pct": None, "change_pct": 0.0, "gold_impact": "NEUTRAL"},
        "gold_adr_14": 38.0,
        "today_range_pts": 0.0,
        "adr_consumed_pct": 0.0,
    }

    # 1. DXY
    try:
        dxy_df = fetch_candles_df("DX-Y.NYB", interval="1h", range_str="10d", ttl=60)
        if len(dxy_df) >= 20:
            ema50 = dxy_df["Close"].ewm(span=min(50, len(dxy_df)), adjust=False).mean().iloc[-1]
            cur = float(dxy_df["Close"].iloc[-1])
            # Cambio respecto hace 24h aprox
            ref_idx = max(0, len(dxy_df) - 24)
            prev = float(dxy_df["Close"].iloc[ref_idx])
            chg_pct = ((cur - prev) / prev) * 100.0 if prev else 0.0
            trend = "ALCISTA" if cur > ema50 else "BAJISTA"
            # DXY bajista impulsa al Oro al alza; DXY alcista presiona al Oro a la baja
            impact = "FAVORABLE COMPRA ORO" if chg_pct < -0.12 else ("PRESIÓN BAJISTA ORO" if chg_pct > 0.12 else "NEUTRAL")
            macro["dxy"] = {
                "price": round(cur, 2),
                "change_pct": round(chg_pct, 2),
                "trend_1h": trend,
                "gold_impact": impact,
            }
    except Exception:
        pass

    # 2. US10Y (^TNX)
    try:
        tnx_df = fetch_candles_df("^TNX", interval="1h", range_str="10d", ttl=60)
        if len(tnx_df) >= 5:
            cur_y = float(tnx_df["Close"].iloc[-1])
            ref_idx = max(0, len(tnx_df) - 8)
            prev_y = float(tnx_df["Close"].iloc[ref_idx])
            chg_pct = ((cur_y - prev_y) / prev_y) * 100.0 if prev_y else 0.0
            impact = "FAVORABLE COMPRA ORO" if chg_pct < -0.5 else ("PRESIÓN BAJISTA ORO" if chg_pct > 0.5 else "NEUTRAL")
            macro["us10y"] = {
                "yield_pct": round(cur_y, 3),
                "change_pct": round(chg_pct, 2),
                "gold_impact": impact,
            }
    except Exception:
        pass

    # 3. ADR 14 Días del Oro
    try:
        daily_gold = fetch_candles_df("GC=F", interval="1d", range_str="2mo", ttl=300)
        if len(daily_gold) >= 5:
            ranges = (daily_gold["High"] - daily_gold["Low"]).dropna()
            adr_14 = float(ranges.iloc[-15:-1].mean()) if len(ranges) > 15 else float(ranges.mean())
            today_rng = float(ranges.iloc[-1])
            consumed = (today_rng / adr_14 * 100.0) if adr_14 > 0 else 0.0
            macro["gold_adr_14"] = round(adr_14, 2)
            macro["today_range_pts"] = round(today_rng, 2)
            macro["adr_consumed_pct"] = round(min(consumed, 200.0), 1)
    except Exception:
        pass

    return macro


def fetch_usd_news_calendar() -> dict:
    """
    Descarga y filtra noticias económicas de USD (Alto y Medio Impacto) del calendario semanal,
    convertidas a Hora Venezuela (VET UTC-4), evaluando la regla de bloqueo de ±5 minutos de FundingPips.
    """
    cache_key = "ff_calendar_thisweek"
    raw_events = _get_cached(cache_key, ttl_seconds=600)

    if raw_events is None:
        try:
            r = SESSION.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=8)
            if r.status_code == 200:
                raw_events = r.json()
                _set_cached(cache_key, raw_events, persist_disk=True)
        except Exception:
            raw_events = _load_disk_fallback(cache_key)

    now_vet = datetime.now(VET_TZ)
    parsed_events = []
    red_lock_active = False
    active_lock_event = None
    next_red_event = None
    min_minutes_ahead = 999999

    if isinstance(raw_events, list):
        for ev in raw_events:
            if ev.get("country") != "USD":
                continue
            impact = ev.get("impact", "")
            if impact not in ("High", "Medium"):
                continue

            date_str = ev.get("date")
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = NY_TZ.localize(dt)
                dt_vet = dt.astimezone(VET_TZ)
            except Exception:
                continue

            diff_min = (dt_vet - now_vet).total_seconds() / 60.0
            is_red = (impact == "High")

            # Regla FundingPips Cuenta Master: Prohibido abrir/cerrar entre -5 min y +5 min de Carpeta Roja USD
            in_lock_window = is_red and (-5.0 <= diff_min <= 5.0)
            if in_lock_window:
                red_lock_active = True
                active_lock_event = ev.get("title", "Noticia Alto Impacto USD")

            if is_red and diff_min > -5.0 and diff_min < min_minutes_ahead:
                min_minutes_ahead = diff_min
                next_red_event = {
                    "title": ev.get("title", ""),
                    "time_vet": dt_vet.strftime("%Y-%m-%d %H:%M VET"),
                    "hour_vet": dt_vet.strftime("%H:%M"),
                    "minutes_away": round(diff_min, 1),
                    "forecast": ev.get("forecast", "") or "—",
                    "previous": ev.get("previous", "") or "—",
                }

            parsed_events.append({
                "title": ev.get("title", ""),
                "impact": "ALTO (Carpeta Roja)" if is_red else "MEDIO (Carpeta Naranja)",
                "is_red": is_red,
                "date_vet": dt_vet.strftime("%Y-%m-%d"),
                "day_label": dt_vet.strftime("%a %d/%m"),
                "time_vet": dt_vet.strftime("%H:%M"),
                "minutes_diff": round(diff_min, 1),
                "forecast": ev.get("forecast", "") or "—",
                "previous": ev.get("previous", "") or "—",
                "in_killzone": (9 * 60 <= (dt_vet.hour * 60 + dt_vet.minute) <= 11 * 60 + 35),
            })

    # Ordenar cronológicamente
    parsed_events.sort(key=lambda x: (x["date_vet"], x["time_vet"]))

    # Filtrar eventos de hoy y próximos
    today_str = now_vet.strftime("%Y-%m-%d")
    today_events = [e for e in parsed_events if e["date_vet"] == today_str]
    today_red_killzone = [e for e in today_events if e["is_red"] and e["in_killzone"]]

    status_label = "BLOQUEO ROJO ACTIVO (±5m)" if red_lock_active else (
        f"PRECAUCIÓN HOY ({len(today_red_killzone)} Roja en NY)" if today_red_killzone else "USD DESPEJADO"
    )

    return {
        "status_label": status_label,
        "red_lock_active": red_lock_active,
        "active_lock_event": active_lock_event,
        "next_red_event": next_red_event,
        "today_events": today_events,
        "week_events": parsed_events,
    }


def check_mt5_status() -> dict:
    """
    Verifica de forma no intrusiva si existe una terminal MetaTrader 5 activa en el sistema.
    """
    try:
        import MetaTrader5 as mt5
        # Solo consultar si ya hay una terminal corriendo en segundo plano para no forzar apertura
        import subprocess
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
            creationflags=0x08000000,
            text=True,
            timeout=2
        )
        if "terminal64.exe" not in out.lower():
            return {
                "connected": False,
                "installed_pkg": True,
                "message": "Pendiente (Terminal MT5 cerrada / aún no configurada)",
                "spread_pts": None,
                "account_login": None,
            }

        if mt5.initialize():
            acc = mt5.account_info()
            tick = mt5.symbol_info_tick("XAUUSD") or mt5.symbol_info_tick("XAUUSD.")
            spread = round(tick.ask - tick.bid, 2) if tick else None
            info = {
                "connected": True,
                "installed_pkg": True,
                "message": f"Conectado a MT5 #{acc.login}" if acc else "Conectado a MT5",
                "account_login": acc.login if acc else None,
                "balance": acc.balance if acc else None,
                "equity": acc.equity if acc else None,
                "spread_pts": spread,
            }
            return info
    except Exception:
        pass

    return {
        "connected": False,
        "installed_pkg": True,
        "message": "Modo Standalone (Listo para vincular MT5 cuando abras cuenta prueba)",
        "spread_pts": None,
        "account_login": None,
    }


def fetch_mt5_candles_df(interval: str = "5m", count: int = 800):
    """
    Extrae velas directamente de MetaTrader 5 cuando esté activo.
    """
    try:
        import MetaTrader5 as mt5
        status = check_mt5_status()
        if not status.get("connected"):
            return None
        tf_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "1h": mt5.TIMEFRAME_H1,
            "1d": mt5.TIMEFRAME_D1,
        }
        tf = tf_map.get(interval, mt5.TIMEFRAME_M5)
        for sym in ("XAUUSD", "XAUUSD.", "GOLD", "XAUUSDm"):
            rates = mt5.copy_rates_from_pos(sym, tf, 0, count)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(VET_TZ)
                df = df.set_index("time").rename(columns={
                    "open": "Open", "high": "High", "low": "Low", "close": "Close", "tick_volume": "Volume"
                })
                return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return None
    return None


def get_clocks_and_killzone(reference_dt_vet: datetime = None) -> dict:
    """
    Calcula la hora exacta en Venezuela (VET UTC-4) y Nueva York (EST/EDT),
    estado de la ventana operativa (09:00 - 11:30 AM VET) y proximidad al Rollover (17:00 NY).
    """
    now_vet = reference_dt_vet.astimezone(VET_TZ) if reference_dt_vet else datetime.now(VET_TZ)
    now_ny = now_vet.astimezone(NY_TZ)

    is_weekend = now_vet.weekday() >= 5
    vet_minutes = now_vet.hour * 60 + now_vet.minute
    kz_start = 9 * 60        # 09:00 AM VET
    kz_end = 11 * 60 + 30    # 11:30 AM VET

    in_killzone = (not is_weekend) and (kz_start <= vet_minutes <= kz_end)

    # Próxima ventana 09:00 AM VET
    next_kz = now_vet.replace(hour=9, minute=0, second=0, microsecond=0)
    if vet_minutes > kz_end or is_weekend:
        days_add = 1
        while (now_vet + timedelta(days=days_add)).weekday() >= 5:
            days_add += 1
        next_kz = (now_vet + timedelta(days=days_add)).replace(hour=9, minute=0, second=0, microsecond=0)
    elif vet_minutes < kz_start:
        pass

    mins_to_kz = max(0, int((next_kz - now_vet).total_seconds() // 60))
    hrs_to_kz = mins_to_kz // 60
    rem_mins = mins_to_kz % 60

    # Rollover bancario 17:00 NY (convertido dinámicamente a VET según EST/EDT)
    rollover_ny = now_ny.replace(hour=17, minute=0, second=0, microsecond=0)
    rollover_vet = rollover_ny.astimezone(VET_TZ)
    in_rollover_danger = (not is_weekend) and abs((now_vet - rollover_vet).total_seconds()) <= 1800

    return {
        "vet_time": now_vet.strftime("%H:%M:%S"),
        "vet_date": now_vet.strftime("%Y-%m-%d"),
        "vet_day": now_vet.strftime("%A"),
        "ny_time": now_ny.strftime("%H:%M:%S"),
        "ny_tz_abbr": now_ny.tzname(),
        "is_weekend": is_weekend,
        "in_killzone": in_killzone,
        "killzone_label": (
            "NY KILLZONE ACTIVA (09:00 - 11:30 VET)" if in_killzone else (
                f"MERCADO CERRADO (Fin de semana · Abre Lun 09:00 VET)" if is_weekend else
                f"FUERA DE VENTANA (Próxima NY Open en {hrs_to_kz}h {rem_mins}m)"
            )
        ),
        "rollover_vet_str": rollover_vet.strftime("%H:%M VET"),
        "in_rollover_danger": in_rollover_danger,
    }
