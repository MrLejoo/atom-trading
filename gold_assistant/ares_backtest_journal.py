"""
ares_backtest_journal.py - Laboratorio de Backtesting 60D, Replay Vela a Vela,
Diario SQLite (con Puntos de Discrepancia) y Simulador de Escalado FundingPips Venezuela.
"""

import os
import sqlite3
from datetime import datetime, time, timedelta
import pytz
import pandas as pd

from ares_market_feed import fetch_candles_df, VET_TZ, NY_TZ
from ares_smc_engine import (
    df_to_chart_candles,
    extract_liquidity_and_sessions,
    scan_fvgs_and_ifvgs,
    scan_5_rule_setups,
    to_chart_ts,
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ares_data.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            mode TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            tp1_price REAL,
            tp2_price REAL,
            lots REAL NOT NULL,
            outcome TEXT NOT NULL,
            pnl_usd REAL NOT NULL,
            rules_score INTEGER DEFAULT 5,
            swept_level TEXT,
            user_notes TEXT,
            discrepancy_note TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def list_journal_entries(limit: int = 100) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM journal_entries ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    today_str = datetime.now(VET_TZ).strftime("%Y-%m-%d")
    today_live = [r for r in rows if r["trade_date"] == today_str and r["mode"] in ("VIVO", "DEMO_MT5")]
    losses_today = sum(1 for r in today_live if r["pnl_usd"] < 0)
    pnl_today = round(sum(r["pnl_usd"] for r in today_live), 2)

    circuit_locked = (losses_today >= 2) or (pnl_today <= -100.0)

    total_pnl = round(sum(r["pnl_usd"] for r in rows), 2)
    wins = sum(1 for r in rows if r["pnl_usd"] > 0)
    losses = sum(1 for r in rows if r["pnl_usd"] < 0)
    wr = round((wins / (wins + losses)) * 100.0, 1) if (wins + losses) > 0 else 0.0

    return {
        "entries": rows,
        "stats": {
            "total_entries": len(rows),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": wr,
            "total_pnl_usd": total_pnl,
            "today_losses": losses_today,
            "today_pnl_usd": pnl_today,
            "circuit_breaker_locked": circuit_locked,
            "circuit_message": (
                "BLOQUEO DIARIO ACTIVO (-2 pérdidas o -$100 USD alcanzados hoy · Cierre de terminal obligatorio)"
                if circuit_locked else
                f"Operativa habilitada hoy ({losses_today}/2 stops usados · PnL hoy: ${pnl_today:+.2f})"
            ),
        },
    }


def add_journal_entry(payload: dict) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_str = datetime.now(VET_TZ).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO journal_entries (
            created_at, trade_date, mode, direction, entry_price, stop_loss,
            tp1_price, tp2_price, lots, outcome, pnl_usd, rules_score,
            swept_level, user_notes, discrepancy_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_str,
        payload.get("trade_date") or datetime.now(VET_TZ).strftime("%Y-%m-%d"),
        payload.get("mode", "ESTUDIO"),
        payload.get("direction", "SELL"),
        float(payload.get("entry_price", 0)),
        float(payload.get("stop_loss", 0)),
        float(payload.get("tp1_price", 0)),
        float(payload.get("tp2_price", 0)),
        float(payload.get("lots", 0.06)),
        payload.get("outcome", "PENDIENTE"),
        float(payload.get("pnl_usd", 0.0)),
        int(payload.get("rules_score", 5)),
        payload.get("swept_level", ""),
        payload.get("user_notes", ""),
        payload.get("discrepancy_note", ""),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": new_id}


def delete_journal_entry(entry_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def get_available_replay_dates() -> list:
    """
    Devuelve la lista de fechas hábiles disponibles en los últimos 60 días de 5m de Oro.
    """
    df_5m = fetch_candles_df("GC=F", interval="5m", range_str="60d", ttl=600)
    dates = sorted(list(set(df_5m.index.date)), reverse=True)
    valid_dates = []
    for d in dates:
        day_df = df_5m[(df_5m.index.date == d) & (df_5m.index.time >= time(9, 0)) & (df_5m.index.time <= time(11, 30))]
        if len(day_df) >= 8:
            valid_dates.append(str(d))
    return valid_dates


def load_replay_session(date_str: str, interval: str = "5m") -> dict:
    """
    Carga una sesión histórica completa (incluyendo contexto previo asiático/londinense
    + jornada de Nueva York hasta las 14:30 VET) lista para el reproductor Vela a Vela.
    """
    rng = "7d" if interval == "1m" else "60d"
    df_all = fetch_candles_df("GC=F", interval=interval, range_str=rng, ttl=600)
    h1_all = fetch_candles_df("GC=F", interval="1h", range_str="60d", ttl=600)

    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    prev_date = target_date - timedelta(days=1)

    # Incluir desde el día anterior a las 18:00 VET hasta el target_date a las 15:00 VET
    start_bound = VET_TZ.localize(datetime.combine(prev_date, time(18, 0)))
    end_bound = VET_TZ.localize(datetime.combine(target_date, time(15, 0)))

    sub = df_all[(df_all.index >= start_bound) & (df_all.index <= end_bound)].copy()
    if len(sub) < 15:
        # Si hubo fin de semana antes (ej. lunes), ampliar ventana hacia atrás 3 días
        start_bound = VET_TZ.localize(datetime.combine(target_date - timedelta(days=3), time(18, 0)))
        sub = df_all[(df_all.index >= start_bound) & (df_all.index <= end_bound)].copy()

    # Incluir también el día hábil previo completo para cálculo exacto de PDH/PDL
    ext_start = VET_TZ.localize(datetime.combine(target_date - timedelta(days=4), time(0, 0)))
    ext_df = df_all[(df_all.index >= ext_start) & (df_all.index <= end_bound)].copy()
    h1_sub = h1_all[h1_all.index <= end_bound].copy()

    levels = extract_liquidity_and_sessions(ext_df, h1_df=h1_sub)
    fvgs = scan_fvgs_and_ifvgs(sub, lookback=len(sub))

    dummy_news = {"red_lock_active": False, "status_label": "Modo Replay Histórico"}
    dummy_clocks = {"in_killzone": True, "killzone_label": f"Sesión Replay {date_str} (09:00 - 11:30 VET)"}
    scan_res = scan_5_rule_setups(ext_df, levels, dummy_news, dummy_clocks, account_size=10000.0, risk_pct=0.5)

    day_setups = [s for s in scan_res["setups"] if s["date"] == date_str]
    candles = df_to_chart_candles(sub)

    # Encontrar el índice exacto donde arranca las 08:55 / 09:00 AM VET en el array `candles`
    kz_start_idx = 0
    target_kz_dt = VET_TZ.localize(datetime.combine(target_date, time(9, 0)))
    target_kz_ts = to_chart_ts(target_kz_dt)
    for i, c in enumerate(candles):
        if c["time"] >= target_kz_ts:
            kz_start_idx = max(10, i)
            break

    # Filtrar marcadores dentro del rango de sub
    min_ts = candles[0]["time"] if candles else 0
    max_ts = candles[-1]["time"] if candles else 0
    day_markers = [m for m in scan_res["markers"] if min_ts <= m["time"] <= max_ts]

    return {
        "date": date_str,
        "interval": interval,
        "candles": candles,
        "kz_start_idx": kz_start_idx,
        "levels": levels,
        "fvgs": fvgs,
        "setups": day_setups,
        "markers": day_markers,
    }


def run_60d_backtest(account_size: float = 10000.0, risk_pct: float = 0.5, only_a_plus: bool = False) -> dict:
    """
    Ejecuta el backtest institucional de 60 días sobre velas de 5 minutos de XAUUSD (GC=F)
    aplicando estrictamente las 5 Reglas (Ventana NY + Sweep + CISD >=50% + FVG 50% CE + Split 1.5R/3R).
    """
    df_5m = fetch_candles_df("GC=F", interval="5m", range_str="60d", ttl=600)
    h1_df = fetch_candles_df("GC=F", interval="1h", range_str="60d", ttl=600)

    levels = extract_liquidity_and_sessions(df_5m, h1_df=h1_df)
    dummy_news = {"red_lock_active": False, "status_label": "Backtest"}
    dummy_clocks = {"in_killzone": True, "killzone_label": "Backtest 60D"}

    res = scan_5_rule_setups(
        df_5m, levels, dummy_news, dummy_clocks,
        account_size=account_size, risk_pct=risk_pct, h1_df=h1_df
    )
    # Orden cronológico ascendente
    all_setups = list(reversed(res["setups"]))
    if only_a_plus:
        all_setups = [s for s in all_setups if s.get("grade") == "A+"]
    closed_trades = [s for s in all_setups if s["pnl_usd"] != 0.0]

    balance = account_size
    peak_balance = account_size
    max_dd_usd = 0.0
    equity_curve = [{"date": "Inicio", "balance": round(account_size, 2), "drawdown_usd": 0.0}]

    trades_out = []
    phase1_day = None
    phase1_target = account_size * 1.08  # +8% ($10,800)

    for idx, tr in enumerate(closed_trades, start=1):
        balance += tr["pnl_usd"]
        peak_balance = max(peak_balance, balance)
        dd = peak_balance - balance
        max_dd_usd = max(max_dd_usd, dd)

        if phase1_day is None and balance >= phase1_target:
            phase1_day = tr["date"]

        tr_row = dict(tr)
        tr_row["trade_num"] = idx
        tr_row["balance_after"] = round(balance, 2)
        trades_out.append(tr_row)

        equity_curve.append({
            "date": f"{tr['date']} #{idx}",
            "balance": round(balance, 2),
            "drawdown_usd": round(-dd, 2),
        })

    total = len(trades_out)
    wins = [t for t in trades_out if t["pnl_usd"] > 0]
    losses = [t for t in trades_out if t["pnl_usd"] < 0]
    full_3r = [t for t in wins if "TP2" in t["outcome"]]
    partial_be = [t for t in wins if "TP2" not in t["outcome"]]

    gross_profit = sum(t["pnl_usd"] for t in wins)
    gross_loss = abs(sum(t["pnl_usd"] for t in losses))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    wr = round((len(wins) / total) * 100.0, 1) if total > 0 else 0.0
    net_usd = round(balance - account_size, 2)
    net_pct = round((net_usd / account_size) * 100.0, 2)
    expectancy_usd = round(net_usd / total, 2) if total > 0 else 0.0
    risk_unit = account_size * (risk_pct / 100.0)
    expectancy_r = round(expectancy_usd / risk_unit, 2) if risk_unit > 0 else 0.0

    return {
        "metrics": {
            "period": "Últimos 60 Días (M5 NY Killzone 09:00-11:30 VET)",
            "initial_capital": account_size,
            "final_balance": round(balance, 2),
            "net_profit_usd": net_usd,
            "net_profit_pct": net_pct,
            "total_trades": total,
            "wins": len(wins),
            "full_3r_wins": len(full_3r),
            "partial_be_wins": len(partial_be),
            "losses": len(losses),
            "win_rate_pct": wr,
            "profit_factor": pf,
            "expectancy_usd": expectancy_usd,
            "expectancy_r": expectancy_r,
            "max_drawdown_usd": round(max_dd_usd, 2),
            "max_drawdown_pct": round((max_dd_usd / account_size) * 100.0, 2),
            "phase1_reached_date": phase1_day or "En progreso",
            "fp_daily_limit_safe": max_dd_usd < (account_size * 0.05),
            "fp_static_limit_safe": max_dd_usd < (account_size * 0.10),
        },
        "equity_curve": equity_curve,
        "trades": list(reversed(trades_out)),  # Más recientes arriba en la tabla
    }


def simulate_fundingpips_scaling(
    monthly_return_pct: float = 6.0,
    profit_split_pct: float = 80.0,
    reinvest_rate_pct: float = 40.0,
    months: int = 12,
) -> dict:
    """
    Simula la hoja de ruta real del usuario desde Venezuela:
    Arrancar con 1 cuenta de $10,000 USD en FundingPips (costo aprox $89-$99),
    aprobar Fase 1 (8%) + Fase 2 (5%), cobrar retiros en USDT (ERC20) y usar parte
    de las ganancias para comprar nuevas cuentas copiadas con el copiador nativo de FundingPips
    (hasta el tope de asignación de $300,000 USD).
    """
    # Catálogo aproximado evaluaciones 2-Step FundingPips
    eval_catalog = [
        (100000, 399),
        (50000, 239),
        (25000, 139),
        (10000, 89),
    ]

    funded_capital = 0.0
    pending_eval_capital = 10000.0
    eval_progress_pct = 0.0  # Requiere 13% acumulado (8% F1 + 5% F2)
    reinvest_pool = 0.0
    wallet_usdt_net = 0.0
    accounts_count = 1
    timeline = []

    for m in range(1, months + 1):
        note = ""
        # Avance de cuentas en evaluación
        if pending_eval_capital > 0:
            eval_progress_pct += monthly_return_pct
            if eval_progress_pct >= 13.0:
                funded_capital = min(300000.0, funded_capital + pending_eval_capital)
                note = f"¡Cuenta(s) aprobada(s)! +${pending_eval_capital:,.0f} pasan a Master"
                pending_eval_capital = 0.0
                eval_progress_pct = 0.0
            else:
                note = f"En evaluación ({eval_progress_pct:.1f}% / 13.0% meta F1+F2)"

        # Rendimiento sobre capital ya fondeado (Master)
        gross_profit = funded_capital * (monthly_return_pct / 100.0)
        payout_usdt = gross_profit * (profit_split_pct / 100.0)

        reinvest_amt = payout_usdt * (reinvest_rate_pct / 100.0)
        pocket_usdt = payout_usdt - reinvest_amt

        wallet_usdt_net += pocket_usdt
        reinvest_pool += reinvest_amt

        # Comprar nuevas evaluaciones con fondo de reinversión si aún no llegamos a $300K
        bought = []
        while (funded_capital + pending_eval_capital) < 300000.0:
            purchased_any = False
            for cap, cost in eval_catalog:
                if reinvest_pool >= cost and (funded_capital + pending_eval_capital + cap) <= 300000.0:
                    reinvest_pool -= cost
                    pending_eval_capital += cap
                    accounts_count += 1
                    bought.append(f"${cap // 1000}K")
                    purchased_any = True
                    break
            if not purchased_any:
                break

        if bought:
            extra = f"Compra evaluación ({', '.join(bought)}) para Copiador"
            note = f"{note} · {extra}" if note else extra

        timeline.append({
            "month": f"Mes {m}",
            "funded_capital": round(funded_capital, 0),
            "eval_capital": round(pending_eval_capital, 0),
            "monthly_payout_usdt": round(payout_usdt, 2),
            "pocket_usdt": round(pocket_usdt, 2),
            "cumulative_wallet_usdt": round(wallet_usdt_net, 2),
            "note": note or "Operando Master con Copiador activo",
        })

    return {
        "final_funded_capital": funded_capital,
        "total_pocket_usdt": round(wallet_usdt_net, 2),
        "accounts_managed": accounts_count,
        "timeline": timeline,
    }
