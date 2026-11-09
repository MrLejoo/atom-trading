"""
ares_server.py - Servidor Web Local de Alta Velocidad para ARES (Starlette + Uvicorn)
Expone la API cuantitativa en tiempo real y sirve el Centro de Comando Legacy Dark (#101010 / #CCCCCC / #007ACC).
"""

import os
import traceback
from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse, HTMLResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from gold_math import FundingPipsGoldCalculator
from ares_market_feed import (
    fetch_candles_df,
    fetch_macro_context,
    fetch_usd_news_calendar,
    check_mt5_status,
    get_clocks_and_killzone,
)
from ares_smc_engine import (
    df_to_chart_candles,
    extract_liquidity_and_sessions,
    scan_fvgs_and_ifvgs,
    scan_5_rule_setups,
    generate_ares_briefing,
    generate_atom_team_reports,
)
from ares_backtest_journal import (
    list_journal_entries,
    add_journal_entry,
    delete_journal_entry,
    get_available_replay_dates,
    load_replay_session,
    run_60d_backtest,
    simulate_fundingpips_scaling,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)


async def index_page(request):
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>ARES cargando interfaz...</h1>")


async def api_live_state(request):
    try:
        qp = request.query_params
        source = qp.get("source", "GC=F")
        interval = qp.get("interval", "5m")
        account_size = float(qp.get("account_size", "10000"))
        risk_pct = float(qp.get("risk_pct", "0.5"))

        df = fetch_candles_df(source=source, interval=interval)
        h1_source = "PAXGUSDT" if source == "PAXGUSDT" else "GC=F"
        h1_df = fetch_candles_df(source=h1_source, interval="1h")

        clocks = get_clocks_and_killzone()
        news = fetch_usd_news_calendar()
        macro = fetch_macro_context()
        mt5_status = check_mt5_status()
        journal = list_journal_entries(limit=50)

        levels = extract_liquidity_and_sessions(df, h1_df=h1_df)
        fvgs = scan_fvgs_and_ifvgs(df, lookback=160)
        scan = scan_5_rule_setups(
            df, levels, news, clocks,
            account_size=account_size, risk_pct=risk_pct,
            h1_df=h1_df, scan_all_hours=(source == "PAXGUSDT")
        )
        briefing = generate_ares_briefing(
            levels, fvgs, scan["setups"], macro, news, clocks
        )

        # Limitar velas enviadas al frontend para máxima fluidez 60fps (últimas 500 velas)
        df_tail = df.iloc[-500:] if len(df) > 500 else df
        candles = df_to_chart_candles(df_tail)
        min_ts = candles[0]["time"] if candles else 0
        visible_markers = [m for m in scan["markers"] if m["time"] >= min_ts]

        return JSONResponse({
            "ok": True,
            "system_name": "ATOM",
            "source": source,
            "interval": interval,
            "candles": candles,
            "levels": levels,
            "fvgs": fvgs,
            "setups": scan["setups"][:12],
            "markers": visible_markers,
            "live_checklist": scan["live_checklist"],
            "briefing": briefing,
            "atom_team": atom_team,
            "macro": macro,
            "news": news,
            "clocks": clocks,
            "mt5_status": mt5_status,
            "journal_stats": journal["stats"],
        })
    except Exception as e:
        return JSONResponse({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc(),
        }, status_code=500)


async def api_calculate_risk(request):
    try:
        body = await request.json()
        account_size = float(body.get("account_size", 10000.0))
        risk_pct = float(body.get("risk_pct", 0.5))
        direction = body.get("direction", "SELL").upper()
        entry_price = float(body.get("entry_price", 0.0))
        stop_loss = float(body.get("stop_loss", 0.0))

        is_sell = (direction == "SELL")
        direction_valid = (stop_loss > entry_price) if is_sell else (stop_loss < entry_price)
        delta = round(abs(entry_price - stop_loss), 2)

        if not direction_valid or delta < 0.2:
            return JSONResponse({
                "ok": False,
                "error": (
                    "En VENTA (SELL) el Stop Loss debe estar ARRIBA de la entrada."
                    if is_sell else
                    "En COMPRA (BUY) el Stop Loss debe estar DEBAJO de la entrada."
                ),
            })

        calc = FundingPipsGoldCalculator(account_size=account_size, risk_pct=risk_pct)
        res = calc.calculate_lot_size(entry_price=entry_price, stop_loss=stop_loss)

        tp1 = round(entry_price - delta * 1.5 if is_sell else entry_price + delta * 1.5, 2)
        tp2 = round(entry_price - delta * 3.0 if is_sell else entry_price + delta * 3.0, 2)

        lot1 = res["split_positions"]["order_1_lots"]
        lot2 = res["split_positions"]["order_2_lots"]
        # Ganancia real exacta con los lotes redondeados de MT5 (1.00 lote = $100 por $1.00 en Oro)
        tp1_usd = round(lot1 * 100.0 * (delta * 1.5), 2)
        tp2_usd = round(lot2 * 100.0 * (delta * 3.0), 2)
        actual_risk_usd = round((lot1 + lot2) * 100.0 * delta, 2)

        strict_range_ok = (2.50 <= delta <= 10.00)

        ticket_str = (
            f"=== BOLETO DE EJECUCIÓN ARES · FUNDINGPIPS ${int(account_size):,} ===\n"
            f"Activo: XAUUSD ({direction})\n"
            f"Entrada Límite (50% CE): {entry_price:.2f}\n"
            f"Stop Loss Técnico:       {stop_loss:.2f} (Distancia: {delta:.2f} pts / {int(delta*10)} pips)\n"
            f"Riesgo Efectivo Total:   ${actual_risk_usd:.2f} USD ({risk_pct:.2f}%)\n"
            f"Margen Dinámico Est.:    ${res['estimated_margin_usd']:.2f} USD\n"
            f"-----------------------------------------------------\n"
            f"[ORDEN 1] {lot1:.2f} Lotes | Entrada {entry_price:.2f} | SL {stop_loss:.2f} | TP1 {tp1:.2f} (1:1.5R -> +${tp1_usd:.2f})\n"
            f"  >> REGLA ACTIVA: Al tocar TP1 ({tp1:.2f}), mover SL de Orden 2 a BREAKEVEN ({entry_price:.2f})\n"
            f"[ORDEN 2] {lot2:.2f} Lotes | Entrada {entry_price:.2f} | SL {stop_loss:.2f} | TP2 {tp2:.2f} (1:3.0R -> +${tp2_usd:.2f})\n"
            f"Beneficio Potencial Completo: +${(tp1_usd + tp2_usd):.2f} USD"
        )

        return JSONResponse({
            "ok": True,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "tp1_price": tp1,
            "tp2_price": tp2,
            "delta_pts": delta,
            "pips": int(round(delta * 10)),
            "strict_range_ok": strict_range_ok,
            "lot_total": round(lot1 + lot2, 2),
            "lot_order_1": lot1,
            "lot_order_2": lot2,
            "actual_risk_usd": actual_risk_usd,
            "target_risk_usd": res["risk_usd"],
            "margin_usd": res["estimated_margin_usd"],
            "tp1_profit_usd": tp1_usd,
            "tp2_profit_usd": tp2_usd,
            "total_potential_usd": round(tp1_usd + tp2_usd, 2),
            "ticket_text": ticket_str,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


async def api_replay_dates(request):
    try:
        dates = get_available_replay_dates()
        return JSONResponse({"ok": True, "dates": dates})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


async def api_replay_session(request):
    try:
        qp = request.query_params
        dates = get_available_replay_dates()
        default_date = "2026-10-23" if "2026-10-23" in dates else (dates[0] if dates else "2026-10-23")
        date_str = qp.get("date", default_date)
        interval = qp.get("interval", "5m")
        data = load_replay_session(date_str=date_str, interval=interval)
        data["ok"] = True
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "trace": traceback.format_exc()}, status_code=500)


async def api_backtest(request):
    try:
        qp = request.query_params
        account_size = float(qp.get("account_size", "10000"))
        risk_pct = float(qp.get("risk_pct", "0.5"))
        only_a_plus = qp.get("only_a_plus", "false").lower() == "true"
        res = run_60d_backtest(account_size=account_size, risk_pct=risk_pct, only_a_plus=only_a_plus)
        res["ok"] = True
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


async def api_journal_list(request):
    return JSONResponse({"ok": True, **list_journal_entries(limit=150)})


async def api_journal_add(request):
    try:
        body = await request.json()
        add_journal_entry(body)
        return JSONResponse({"ok": True, **list_journal_entries(limit=150)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


async def api_journal_delete(request):
    try:
        entry_id = int(request.path_params["id"])
        delete_journal_entry(entry_id)
        return JSONResponse({"ok": True, **list_journal_entries(limit=150)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


async def api_scaling_sim(request):
    try:
        body = await request.json()
        res = simulate_fundingpips_scaling(
            monthly_return_pct=float(body.get("monthly_return_pct", 6.0)),
            profit_split_pct=float(body.get("profit_split_pct", 80.0)),
            reinvest_rate_pct=float(body.get("reinvest_rate_pct", 40.0)),
            months=int(body.get("months", 12)),
        )
        res["ok"] = True
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


routes = [
    Route("/", endpoint=index_page, methods=["GET"]),
    Route("/api/live_state", endpoint=api_live_state, methods=["GET"]),
    Route("/api/calculate_risk", endpoint=api_calculate_risk, methods=["POST"]),
    Route("/api/replay_dates", endpoint=api_replay_dates, methods=["GET"]),
    Route("/api/replay_session", endpoint=api_replay_session, methods=["GET"]),
    Route("/api/backtest", endpoint=api_backtest, methods=["GET"]),
    Route("/api/journal", endpoint=api_journal_list, methods=["GET"]),
    Route("/api/journal", endpoint=api_journal_add, methods=["POST"]),
    Route("/api/journal/{id:int}", endpoint=api_journal_delete, methods=["DELETE"]),
    Route("/api/scaling_sim", endpoint=api_scaling_sim, methods=["POST"]),
    Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=False, routes=routes, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8050, log_level="info")
