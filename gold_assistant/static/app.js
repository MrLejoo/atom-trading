/* ==========================================================================
   ARES v2.0 — Client Application & Institutional Canvas Overlay Engine
   Palette: Legacy Dark (#101010 Background | #CCCCCC Foreground | #007ACC Accent)
   ========================================================================== */

(() => {
  "use strict";

  // -------------------------------------------------------------------------
  // GLOBAL STATE
  // -------------------------------------------------------------------------
  const state = {
    source: "GC=F",
    interval: "5m",
    autoRefresh: true,
    refreshTimer: null,
    pickMode: null, // 'entry' | 'sl' | null

    layers: {
      killzone: true,
      sessions: true,
      pdhpdl: true,
      fvgs: true,
      markers: true,
      position: true,
    },

    liveData: null,
    manualRuleOverrides: {}, // ruleNum -> boolean
    selectedSetupId: null,

    calc: {
      direction: "SELL",
      account_size: 10000,
      risk_pct: 0.5,
      entry_price: 4042.5,
      stop_loss: 4051.7,
      lastResult: null,
      anchorStartTs: null,
      anchorEndTs: null,
      initialSynced: false,
    },

    replay: {
      dates: [],
      session: null,
      cursorIdx: 40,
      blindMode: false,
      playTimer: null,
    },

    backtestLoaded: false,
    journalLoaded: false,
  };

  // -------------------------------------------------------------------------
  // TOAST HELPER
  // -------------------------------------------------------------------------
  let toastTimeout = null;
  function showToast(msg) {
    const el = document.getElementById("ares-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => el.classList.remove("show"), 2800);
  }

  // -------------------------------------------------------------------------
  // DUAL CLOCK TICKER (VENEZUELA VET & NEW YORK)
  // -------------------------------------------------------------------------
  function startHeaderClocks() {
    const tick = () => {
      try {
        const now = new Date();
        const vetFmt = new Intl.DateTimeFormat("es-VE", {
          timeZone: "America/Caracas",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(now);
        const nyFmt = new Intl.DateTimeFormat("en-US", {
          timeZone: "America/New_York",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
          timeZoneName: "short",
        }).format(now);
        const vetEl = document.getElementById("hdr-clock-vet");
        const nyEl = document.getElementById("hdr-clock-ny");
        if (vetEl) vetEl.textContent = vetFmt;
        if (nyEl) nyEl.textContent = `NY ${nyFmt}`;
      } catch (_) {}
    };
    tick();
    setInterval(tick, 1000);
  }

  // -------------------------------------------------------------------------
  // INSTITUTIONAL CHART CONTROLLER (LightweightCharts + 2D Canvas Overlay)
  // -------------------------------------------------------------------------
  class AresChartController {
    constructor(containerId, canvasId, hudTextId, onPriceClick) {
      this.container = document.getElementById(containerId);
      this.canvas = document.getElementById(canvasId);
      this.hudEl = document.getElementById(hudTextId);
      this.onPriceClick = onPriceClick;

      this.candles = [];
      this.levels = {};
      this.fvgs = [];
      this.positionBox = null;
      this.priceLines = [];
      this.layers = state.layers;

      this._initChart();
    }

    _initChart() {
      this.chart = LightweightCharts.createChart(this.container, {
        layout: {
          background: { type: "solid", color: "#101010" },
          textColor: "#CCCCCC",
          fontFamily: "'Cascadia Code', 'JetBrains Mono', Consolas, monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#1b1b1b" },
          horzLines: { color: "#1b1b1b" },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: {
            color: "#007ACC",
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
            labelBackgroundColor: "#007ACC",
          },
          horzLine: {
            color: "#007ACC",
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
            labelBackgroundColor: "#007ACC",
          },
        },
        rightPriceScale: {
          borderColor: "#262626",
          scaleMargins: { top: 0.09, bottom: 0.09 },
        },
        timeScale: {
          borderColor: "#262626",
          timeVisible: true,
          secondsVisible: false,
          rightOffset: 10,
          barSpacing: 8,
        },
      });

      this.series = this.chart.addCandlestickSeries({
        upColor: "#2EA043",
        downColor: "#F85149",
        borderUpColor: "#3FB950",
        borderDownColor: "#F85149",
        wickUpColor: "#3FB950",
        wickDownColor: "#F85149",
        priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      });

      this.chart.timeScale().subscribeVisibleLogicalRangeChange(() => this.scheduleDraw());

      this.chart.subscribeCrosshairMove((param) => {
        if (!this.hudEl) return;
        if (!param || !param.time || !param.seriesData) {
          this._updateDefaultHud();
          return;
        }
        const bar = param.seriesData.get(this.series);
        if (bar) {
          const dt = new Date(param.time * 1000);
          const hh = String(dt.getUTCHours()).padStart(2, "0");
          const mm = String(dt.getUTCMinutes()).padStart(2, "0");
          const mo = String(dt.getUTCMonth() + 1).padStart(2, "0");
          const dd = String(dt.getUTCDate()).padStart(2, "0");
          const chg = (bar.close - bar.open).toFixed(2);
          const col = bar.close >= bar.open ? "#3FB950" : "#F85149";
          this.hudEl.innerHTML =
            `<strong style="color:#FFF;">XAU/USD</strong> · ${mo}-${dd} ${hh}:${mm} VET &nbsp;|&nbsp; ` +
            `O: ${bar.open.toFixed(2)} &nbsp;H: ${bar.high.toFixed(2)} &nbsp;L: ${bar.low.toFixed(2)} &nbsp;` +
            `C: <span style="color:${col};font-weight:700;">${bar.close.toFixed(2)} (${chg >= 0 ? "+" : ""}${chg})</span>`;
        }
      });

      this.chart.subscribeClick((param) => {
        if (!this.onPriceClick || !param || !param.point) return;
        const px = this.series.coordinateToPrice(param.point.y);
        if (px !== null && !isNaN(px)) {
          this.onPriceClick(Math.round(px * 10) / 10, param.time || null);
        }
      });

      const ro = new ResizeObserver(() => {
        if (!this.container.clientWidth || !this.container.clientHeight) return;
        this.chart.applyOptions({
          width: this.container.clientWidth,
          height: this.container.clientHeight,
        });
        this.scheduleDraw();
      });
      ro.observe(this.container);
    }

    _updateDefaultHud() {
      if (!this.hudEl || !this.candles.length) return;
      const last = this.candles[this.candles.length - 1];
      const col = last.close >= last.open ? "#3FB950" : "#F85149";
      this.hudEl.innerHTML =
        `<strong style="color:#FFF;">XAU/USD</strong> · Última Vela (${last.vet_str || ""} VET) &nbsp;|&nbsp; ` +
        `O: ${last.open.toFixed(2)} &nbsp;H: ${last.high.toFixed(2)} &nbsp;L: ${last.low.toFixed(2)} &nbsp;` +
        `C: <span style="color:${col};font-weight:700;">${last.close.toFixed(2)}</span>`;
    }

    setScene({ candles, levels, fvgs, markers, positionBox, fitContent = false }) {
      this.candles = candles || [];
      this.levels = levels || {};
      this.fvgs = fvgs || [];
      if (positionBox !== undefined) {
        this.positionBox = positionBox;
      }

      this.series.setData(this.candles);
      this.series.setMarkers(this.layers.markers && markers ? markers : []);
      this._rebuildPriceLines();
      this._updateDefaultHud();

      if (fitContent && this.candles.length > 0) {
        const len = this.candles.length;
        const from = Math.max(0, len - 110);
        this.chart.timeScale().setVisibleLogicalRange({ from, to: len + 10 });
      }
      this.scheduleDraw();
    }

    updatePositionBox(positionBox) {
      this.positionBox = positionBox;
      this.scheduleDraw();
    }

    refreshLayers(markers) {
      this.series.setMarkers(this.layers.markers && markers ? markers : []);
      this._rebuildPriceLines();
      this.scheduleDraw();
    }

    focusTimestamp(targetTs) {
      if (!this.candles.length) return;
      const idx = this._nearestIndex(targetTs);
      this.chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, idx - 28),
        to: idx + 32,
      });
      this.scheduleDraw();
    }

    _rebuildPriceLines() {
      for (const pl of this.priceLines) {
        try { this.series.removePriceLine(pl); } catch (_) {}
      }
      this.priceLines = [];

      if (this.layers.pdhpdl && this.levels) {
        if (this.levels.pdh) {
          this.priceLines.push(this.series.createPriceLine({
            price: this.levels.pdh,
            color: "#3794FF",
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: "PDH",
          }));
        }
        if (this.levels.pdl) {
          this.priceLines.push(this.series.createPriceLine({
            price: this.levels.pdl,
            color: "#3794FF",
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: "PDL",
          }));
        }
        if (this.levels.eq_50) {
          this.priceLines.push(this.series.createPriceLine({
            price: this.levels.eq_50,
            color: "#666666",
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            axisLabelVisible: true,
            title: "50% EQ",
          }));
        }
      }
    }

    _nearestIndex(ts) {
      const arr = this.candles;
      const n = arr.length;
      if (!n) return 0;
      const last = arr[n - 1].time;
      if (ts > last) {
        const step = n >= 2 ? Math.max(60, arr[n - 1].time - arr[n - 2].time) : 300;
        return (n - 1) + (ts - last) / step;
      }
      if (ts <= arr[0].time) return 0;

      let lo = 0, hi = n - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const mt = arr[mid].time;
        if (mt === ts) return mid;
        if (mt < ts) lo = mid + 1;
        else hi = mid - 1;
      }
      return Math.min(n - 1, lo);
    }

    xForTime(ts) {
      if (!this.candles.length) return null;
      const logicalIdx = this._nearestIndex(ts);
      return this.chart.timeScale().logicalToCoordinate(logicalIdx);
    }

    yForPrice(px) {
      return this.series.priceToCoordinate(px);
    }

    scheduleDraw() {
      if (this._raf) cancelAnimationFrame(this._raf);
      this._raf = requestAnimationFrame(() => this._drawOverlays());
    }

    _drawOverlays() {
      if (!this.canvas || !this.container) return;
      const dpr = window.devicePixelRatio || 1;
      // Restar ancho aproximado de la escala de precios derecha (64px) y eje inferior (26px) para no invadir escalas
      const plotW = Math.max(10, this.container.clientWidth - 66);
      const plotH = Math.max(10, this.container.clientHeight - 28);

      if (this.canvas.width !== Math.floor(this.container.clientWidth * dpr) ||
          this.canvas.height !== Math.floor(this.container.clientHeight * dpr)) {
        this.canvas.width = Math.floor(this.container.clientWidth * dpr);
        this.canvas.height = Math.floor(this.container.clientHeight * dpr);
      }

      const ctx = this.canvas.getContext("2d");
      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, this.container.clientWidth, this.container.clientHeight);

      // Clip estrictamente al área de velas
      ctx.beginPath();
      ctx.rect(0, 0, plotW, plotH);
      ctx.clip();

      if (!this.candles.length) {
        ctx.restore();
        return;
      }

      // 1. KILLZONE NY VERTICAL BANDS (09:00 - 11:30 VET)
      if (this.layers.killzone && this.levels.killzone_bands) {
        for (const kz of this.levels.killzone_bands) {
          const x1 = this.xForTime(kz.start_ts);
          const x2 = this.xForTime(kz.end_ts);
          if (x1 === null || x2 === null) continue;
          const left = Math.min(x1, x2);
          const w = Math.max(4, Math.abs(x2 - x1));
          if (left + w < 0 || left > plotW) continue;

          ctx.fillStyle = "rgba(0, 122, 204, 0.065)";
          ctx.fillRect(left, 0, w, plotH);

          ctx.strokeStyle = "rgba(0, 122, 204, 0.35)";
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(left, 0);
          ctx.lineTo(left, plotH);
          ctx.moveTo(left + w, 0);
          ctx.lineTo(left + w, plotH);
          ctx.stroke();
          ctx.setLineDash([]);

          if (w > 45) {
            ctx.fillStyle = "rgba(55, 148, 255, 0.85)";
            ctx.font = "bold 10px Consolas, monospace";
            ctx.fillText("NY KILLZONE (09:00-11:30)", Math.max(6, left + 5), plotH - 8);
          }
        }
      }

      // 2. ASIAN & LONDON SESSION BOXES
      if (this.layers.sessions && this.levels.session_boxes) {
        for (const sb of this.levels.session_boxes) {
          const x1 = this.xForTime(sb.start_ts);
          const x2 = this.xForTime(sb.end_ts);
          const yTop = this.yForPrice(sb.high);
          const yBot = this.yForPrice(sb.low);
          if (x1 === null || x2 === null || yTop === null || yBot === null) continue;

          const left = Math.min(x1, x2);
          const w = Math.max(4, Math.abs(x2 - x1));
          const top = Math.min(yTop, yBot);
          const h = Math.max(2, Math.abs(yBot - yTop));
          if (left + w < 0 || left > plotW) continue;

          const isAsian = sb.kind === "ASIAN";
          ctx.fillStyle = isAsian ? "rgba(210, 153, 34, 0.08)" : "rgba(0, 122, 204, 0.07)";
          ctx.fillRect(left, top, w, h);

          ctx.strokeStyle = isAsian ? "rgba(227, 179, 65, 0.65)" : "rgba(55, 148, 255, 0.60)";
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.strokeRect(left, top, w, h);
          ctx.setLineDash([]);

          if (w > 40) {
            ctx.fillStyle = isAsian ? "#E3B341" : "#3794FF";
            ctx.font = "bold 9.5px Consolas, monospace";
            ctx.fillText(
              `${isAsian ? "ASIAN" : "LONDON"} [${sb.low.toFixed(1)} - ${sb.high.toFixed(1)}]`,
              left + 4,
              Math.max(12, top - 4)
            );
          }
        }
      }

      // 3. FAIR VALUE GAPS (BISI / SIBI / IFVG) + 50% CE LINE
      if (this.layers.fvgs && this.fvgs) {
        for (const f of this.fvgs) {
          const x1 = this.xForTime(f.start_ts);
          const x2 = this.xForTime(f.end_ts);
          const yTop = this.yForPrice(f.top);
          const yBot = this.yForPrice(f.bottom);
          const yCe = this.yForPrice(f.ce_50);
          if (x1 === null || x2 === null || yTop === null || yBot === null) continue;

          const left = Math.min(x1, x2);
          const w = Math.max(14, Math.abs(x2 - x1));
          const top = Math.min(yTop, yBot);
          const h = Math.max(2, Math.abs(yBot - yTop));
          if (left + w < 0 || left > plotW) continue;

          const isBull = f.direction === "BULLISH";
          if (f.is_ifvg) {
            ctx.fillStyle = "rgba(163, 113, 247, 0.16)";
            ctx.strokeStyle = "rgba(163, 113, 247, 0.70)";
          } else if (isBull) {
            ctx.fillStyle = "rgba(46, 160, 67, 0.16)";
            ctx.strokeStyle = "rgba(63, 185, 80, 0.65)";
          } else {
            ctx.fillStyle = "rgba(248, 81, 73, 0.16)";
            ctx.strokeStyle = "rgba(248, 81, 73, 0.65)";
          }

          ctx.fillRect(left, top, w, h);
          ctx.lineWidth = 1;
          ctx.strokeRect(left, top, w, h);

          // Línea interna 50% Consequent Encroachment
          if (yCe !== null && h >= 5) {
            ctx.beginPath();
            ctx.setLineDash([2, 3]);
            ctx.moveTo(left, yCe);
            ctx.lineTo(left + w, yCe);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          if (w > 55) {
            ctx.fillStyle = f.is_ifvg ? "#D2A8FF" : (isBull ? "#7EE787" : "#FFA198");
            ctx.font = "9.5px Consolas, monospace";
            ctx.fillText(`${f.is_ifvg ? "IFVG" : "FVG"} CE ${f.ce_50.toFixed(2)}`, left + 4, top + Math.min(11, h - 2));
          }
        }
      }

      // 4. TRADINGVIEW-STYLE LONG / SHORT POSITION RISK-REWARD TOOL
      if (this.layers.position && this.positionBox) {
        const pb = this.positionBox;
        const n = this.candles.length;
        const startLogical = pb.startTs ? this._nearestIndex(pb.startTs) : Math.max(0, n - 18);
        const endLogical = pb.endTs ? Math.max(startLogical + 8, this._nearestIndex(pb.endTs)) : (n + 6);

        const x1 = this.chart.timeScale().logicalToCoordinate(startLogical);
        const x2 = this.chart.timeScale().logicalToCoordinate(endLogical);
        const yEntry = this.yForPrice(pb.entry);
        const ySl = this.yForPrice(pb.sl);
        const yTp1 = this.yForPrice(pb.tp1);
        const yTp2 = this.yForPrice(pb.tp2);

        if (x1 !== null && x2 !== null && yEntry !== null && ySl !== null && yTp2 !== null) {
          const left = Math.max(0, Math.min(x1, x2));
          const right = Math.min(plotW, Math.max(x1, x2));
          const w = Math.max(30, right - left);

          // Stop Zone (Red)
          const slTop = Math.min(yEntry, ySl);
          const slH = Math.abs(ySl - yEntry);
          ctx.fillStyle = "rgba(248, 81, 73, 0.20)";
          ctx.fillRect(left, slTop, w, slH);
          ctx.strokeStyle = "#F85149";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(left, ySl);
          ctx.lineTo(left + w, ySl);
          ctx.stroke();

          // Profit Zone Total (Green)
          const tpTop = Math.min(yEntry, yTp2);
          const tpH = Math.abs(yTp2 - yEntry);
          ctx.fillStyle = "rgba(46, 160, 67, 0.18)";
          ctx.fillRect(left, tpTop, w, tpH);

          // TP1 Line (1:1.5R + Breakeven)
          if (yTp1 !== null) {
            ctx.strokeStyle = "#3FB950";
            ctx.setLineDash([5, 4]);
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            ctx.moveTo(left, yTp1);
            ctx.lineTo(left + w, yTp1);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          // TP2 Line (1:3.0R)
          ctx.strokeStyle = "#2EA043";
          ctx.lineWidth = 1.8;
          ctx.beginPath();
          ctx.moveTo(left, yTp2);
          ctx.lineTo(left + w, yTp2);
          ctx.stroke();

          // Entry Line (#007ACC)
          ctx.strokeStyle = "#007ACC";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(left, yEntry);
          ctx.lineTo(left + w, yEntry);
          ctx.stroke();

          // Etiquetas nítidas sobre la herramienta de posición
          this._drawTag(ctx, left + 4, ySl - 7, `SL ${pb.sl.toFixed(2)} (-$${pb.riskUsd || 50})`, "#2b1214", "#F85149");
          this._drawTag(ctx, left + 4, yEntry - 7, `${pb.direction} ${pb.lots || ""}L @ ${pb.entry.toFixed(2)}`, "#0a2236", "#3794FF");
          if (yTp1 !== null) {
            this._drawTag(ctx, left + 4, yTp1 - 7, `TP1 ${pb.tp1.toFixed(2)} (1:1.5R -> BE)`, "#0e2915", "#3FB950");
          }
          this._drawTag(ctx, left + 4, yTp2 - 7, `TP2 ${pb.tp2.toFixed(2)} (1:3.0R Full)`, "#0b2e13", "#7EE787");
        }
      }

      ctx.restore();
    }

    _drawTag(ctx, x, y, text, bg, fg) {
      ctx.font = "bold 10px Consolas, monospace";
      const tw = ctx.measureText(text).width + 10;
      ctx.fillStyle = bg;
      ctx.fillRect(x, y - 6, tw, 15);
      ctx.strokeStyle = fg;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y - 6, tw, 15);
      ctx.fillStyle = fg;
      ctx.fillText(text, x + 5, y + 5);
    }
  }

  // -------------------------------------------------------------------------
  // INSTANCIAS DE GRÁFICOS
  // -------------------------------------------------------------------------
  let liveChart = null;
  let replayChart = null;
  let equityChart = null;

  // -------------------------------------------------------------------------
  // CARGA Y RENDERIZADO DEL ESTADO EN VIVO (TAB 1)
  // -------------------------------------------------------------------------
  async function loadLiveState(fitChart = false) {
    const subEl = document.getElementById("hdr-status-sub");
    if (subEl) subEl.textContent = "Sincronizando flujo XAU/USD y escáner de 5 reglas...";

    try {
      const qs = new URLSearchParams({
        source: state.source,
        interval: state.interval,
        account_size: String(state.calc.account_size),
        risk_pct: String(state.calc.risk_pct),
      });
      const resp = await fetch(`/api/live_state?${qs.toString()}`);
      const data = await resp.json();
      if (!data.ok) throw new Error(data.error || "Error al consultar estado");

      state.liveData = data;
      renderHeaderTelemetry(data);
      renderLiveChecklist(data.live_checklist, data.journal_stats);
      renderDetectedSetups(data.setups);
      renderBriefingAndMagnets(data.briefing, data.levels);
      renderUsdNewsTable(data.news);

      // Si es la primera carga, auto-cargar el setup más reciente (o precio actual) en la calculadora
      if (!state.calc.initialSynced) {
        state.calc.initialSynced = true;
        if (data.setups && data.setups.length > 0) {
          const s0 = data.setups[0];
          applySetupToCalculator(s0, false);
        } else if (data.levels && data.levels.current_price) {
          const px = data.levels.current_price;
          document.getElementById("calc-entry").value = px.toFixed(2);
          document.getElementById("calc-sl").value = (px + 6.0).toFixed(2);
          await recalculateRisk();
        }
      }

      if (liveChart) {
        liveChart.setScene({
          candles: data.candles,
          levels: data.levels,
          fvgs: data.fvgs,
          markers: data.markers,
          positionBox: buildCurrentPositionBox(),
          fitContent: fitChart,
        });
      }

      if (subEl) {
        subEl.textContent = `${data.clocks.killzone_label} · Rollover diario: ${data.clocks.rollover_vet_str}`;
      }
    } catch (err) {
      if (subEl) subEl.textContent = `Aviso de red: ${err.message}`;
    }
  }

  function buildCurrentPositionBox() {
    const r = state.calc.lastResult;
    if (!r || !r.ok) return null;
    return {
      direction: r.direction,
      entry: r.entry_price,
      sl: r.stop_loss,
      tp1: r.tp1_price,
      tp2: r.tp2_price,
      lots: r.lot_total.toFixed(2),
      riskUsd: r.actual_risk_usd.toFixed(0),
      startTs: state.calc.anchorStartTs,
      endTs: state.calc.anchorEndTs,
    };
  }

  function renderHeaderTelemetry(data) {
    const { levels, macro, news, mt5_status, journal_stats } = data;

    const pxEl = document.getElementById("hdr-gold-price");
    if (pxEl && levels.current_price) pxEl.textContent = `$${levels.current_price.toFixed(2)}`;

    const biasEl = document.getElementById("hdr-htf-bias");
    if (biasEl) {
      biasEl.textContent = `1H ${levels.htf_bias}`;
      biasEl.className = `badge ${levels.htf_bias === "ALCISTA" ? "badge-green" : "badge-red"}`;
    }

    const adrTxt = document.getElementById("hdr-adr-text");
    const adrPct = document.getElementById("hdr-adr-pct");
    if (adrTxt && macro) {
      adrTxt.textContent = `${macro.today_range_pts} / ${macro.gold_adr_14} pts`;
      adrPct.textContent = `${macro.adr_consumed_pct}%`;
    }

    const dxyEl = document.getElementById("hdr-dxy");
    const us10El = document.getElementById("hdr-us10y");
    if (dxyEl && macro && macro.dxy) {
      const p = macro.dxy.price ? macro.dxy.price.toFixed(2) : "—";
      const c = macro.dxy.change_pct >= 0 ? `+${macro.dxy.change_pct}%` : `${macro.dxy.change_pct}%`;
      dxyEl.textContent = `DXY ${p} (${c})`;
      dxyEl.style.color = macro.dxy.change_pct < 0 ? "#3FB950" : (macro.dxy.change_pct > 0.1 ? "#F85149" : "#CCCCCC");
    }
    if (us10El && macro && macro.us10y) {
      const y = macro.us10y.yield_pct ? `${macro.us10y.yield_pct.toFixed(2)}%` : "—";
      us10El.textContent = `10Y ${y}`;
    }

    const newsBadge = document.getElementById("hdr-news-badge");
    if (newsBadge && news) {
      newsBadge.textContent = news.status_label;
      newsBadge.className = `badge ${news.red_lock_active ? "badge-red" : (news.status_label.includes("PRECAUCIÓN") ? "badge-gold" : "badge-green")}`;
    }

    const mt5Badge = document.getElementById("hdr-mt5-badge");
    if (mt5Badge && mt5_status) {
      mt5Badge.textContent = mt5_status.connected
        ? `MT5 Activo · Spread $${mt5_status.spread_pts ?? "—"}`
        : "MT5: Standalone (Listo)";
      mt5Badge.className = `badge ${mt5_status.connected ? "badge-green" : "badge-muted"}`;
      mt5Badge.title = mt5_status.message;
    }

    const cbBadge = document.getElementById("hdr-circuit-badge");
    if (cbBadge && journal_stats) {
      cbBadge.textContent = journal_stats.circuit_breaker_locked
        ? "BLOQUEO DIARIO (-2 STOPS)"
        : `${journal_stats.today_losses}/2 Stops Hoy (${journal_stats.today_pnl_usd >= 0 ? "+" : ""}$${journal_stats.today_pnl_usd})`;
      cbBadge.className = `badge ${journal_stats.circuit_breaker_locked ? "badge-red" : "badge-green"}`;
    }
  }

  // -------------------------------------------------------------------------
  // CHECKLIST INTERACTIVO DE LAS 5 REGLAS
  // -------------------------------------------------------------------------
  function renderLiveChecklist(rules, journalStats) {
    const container = document.getElementById("live-checklist-container");
    if (!container || !rules) return;

    let passedCount = 0;
    container.innerHTML = "";

    for (const r of rules) {
      const effectiveChecked = state.manualRuleOverrides.hasOwnProperty(r.rule)
        ? state.manualRuleOverrides[r.rule]
        : Boolean(r.auto);

      if (effectiveChecked) passedCount++;

      const div = document.createElement("div");
      div.className = `rule-item ${effectiveChecked ? "passed" : "pending"}`;
      div.innerHTML = `
        <input type="checkbox" data-rule="${r.rule}" ${effectiveChecked ? "checked" : ""} />
        <div class="rule-body">
          <div class="rule-head">
            <span>R${r.rule}. ${r.title}</span>
            <span class="badge ${r.auto ? "badge-green" : "badge-muted"}">${r.auto ? "AUTO ✓" : "MANUAL"}</span>
          </div>
          <div class="rule-detail">${r.detail}</div>
        </div>
      `;
      div.querySelector("input").addEventListener("change", (ev) => {
        state.manualRuleOverrides[r.rule] = ev.target.checked;
        renderLiveChecklist(rules, journalStats);
      });
      container.appendChild(div);
    }

    const scoreBadge = document.getElementById("chk-score-badge");
    if (scoreBadge) {
      scoreBadge.textContent = `${passedCount} / 5 Reglas`;
      scoreBadge.className = `badge ${passedCount === 5 ? "badge-green" : "badge-blue"}`;
    }

    const banner = document.getElementById("live-verdict-banner");
    if (!banner) return;

    if (journalStats && journalStats.circuit_breaker_locked) {
      banner.className = "verdict-box verdict-red";
      banner.innerHTML = `⛔ <strong>BLOQUEO POR REGLA DIARIA:</strong> Alcanzaste 2 pérdidas o -$100 USD hoy. Terminal cerrada hasta mañana.`;
    } else if (passedCount === 5) {
      const l1 = state.calc.lastResult ? state.calc.lastResult.lot_order_1.toFixed(2) : "0.03";
      const l2 = state.calc.lastResult ? state.calc.lastResult.lot_order_2.toFixed(2) : "0.03";
      banner.className = "verdict-box verdict-green";
      banner.innerHTML = `🚀 <strong>EJECUCIÓN HABILITADA (5/5):</strong> Colocar 2 órdenes Split (${l1} + ${l2} lotes). Al tocar TP1 mover Orden 2 a Breakeven.`;
    } else {
      banner.className = "verdict-box verdict-red";
      banner.innerHTML = `✋ <strong>FILTRO DE ABSTENCIÓN (${passedCount}/5):</strong> Faltan ${5 - passedCount} confirmaciones para disparar. Paciencia institucional.`;
    }
  }

  // -------------------------------------------------------------------------
  // SETUPS DETECTADOS Y CARGA EN EL GRÁFICO + CALCULADORA
  // -------------------------------------------------------------------------
  function renderDetectedSetups(setups) {
    const listEl = document.getElementById("detected-setups-list");
    const badgeEl = document.getElementById("setups-count-badge");
    if (!listEl) return;

    const arr = setups || [];
    if (badgeEl) badgeEl.textContent = `${arr.length} Detectados`;

    if (!arr.length) {
      listEl.innerHTML = `<div style="color:var(--fg-muted);padding:12px;text-align:center;">Sin setups completos en este rango temporal. Prueba cambiar a 5m o 1m.</div>`;
      return;
    }

    listEl.innerHTML = "";
    for (const s of arr) {
      const isSell = s.direction === "SELL";
      const pnlColor = s.pnl_usd > 0 ? "#3FB950" : (s.pnl_usd < 0 ? "#F85149" : "#CCCCCC");
      const card = document.createElement("div");
      card.className = `setup-card ${state.selectedSetupId === s.id ? "selected" : ""}`;
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
          <div style="display:flex;align-items:center;gap:6px;">
            <span class="badge ${isSell ? "badge-red" : "badge-green"}">${s.direction}</span>
            <span class="badge ${s.grade === "A+" ? "badge-blue" : "badge-muted"}">Grado ${s.grade || "A"}</span>
            <strong class="mono" style="color:#FFF;">${s.date} · ${s.cisd_time_vet} VET</strong>
          </div>
          <span class="mono" style="font-weight:700;color:${pnlColor};">
            ${s.pnl_usd > 0 ? `+$${s.pnl_usd.toFixed(2)}` : (s.pnl_usd < 0 ? `-$${Math.abs(s.pnl_usd).toFixed(2)}` : "Pendiente")}
          </span>
        </div>
        <div style="font-size:11.5px;color:var(--fg-primary);">
          <strong>R2 Sweep:</strong> ${s.swept_pools} (${s.sweep_time_vet}) →
          <strong>R3 CISD:</strong> ${s.cisd_level} →
          <strong>R4 FVG CE:</strong> <span class="mono" style="color:var(--accent-bright);">${s.entry_price.toFixed(2)}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--fg-muted);margin-top:4px;">
          <span class="mono">SL: ${s.stop_loss.toFixed(2)} (${s.risk_pts} pts) · ${s.lots_total} Lotes</span>
          <span>${s.outcome}</span>
        </div>
      `;
      card.addEventListener("click", () => {
        state.selectedSetupId = s.id;
        applySetupToCalculator(s, true);
        renderDetectedSetups(arr);
      });
      listEl.appendChild(card);
    }
  }

  async function applySetupToCalculator(s, focusChart = true) {
    state.calc.direction = s.direction;
    state.calc.anchorStartTs = s.entry_ts;
    state.calc.anchorEndTs = s.exit_ts;

    updateDirectionButtons();
    document.getElementById("calc-entry").value = s.entry_price.toFixed(2);
    document.getElementById("calc-sl").value = s.stop_loss.toFixed(2);

    await recalculateRisk();

    if (focusChart && liveChart) {
      liveChart.focusTimestamp(s.entry_ts);
      showToast(`Setup ${s.direction} (${s.date} ${s.cisd_time_vet} VET) enfocado en el gráfico`);
    }
  }

  // -------------------------------------------------------------------------
  // BRIEFING DE ARES, IMANES DE LIQUIDEZ Y NOTICIAS USD
  // -------------------------------------------------------------------------
  function renderBriefingAndMagnets(briefing, levels) {
    const box = document.getElementById("ares-briefing-box");
    const zoneBadge = document.getElementById("brief-zone-badge");
    if (zoneBadge && levels) {
      zoneBadge.textContent = levels.zone_pd ? levels.zone_pd.split(" ")[0] : "EQUILIBRIO";
    }
    if (box && briefing) {
      box.innerHTML = `
        <div style="background:var(--bg-base);border:1px solid var(--border);border-left:3px solid var(--accent);padding:8px 10px;border-radius:5px;">
          <div style="font-weight:700;color:#FFF;margin-bottom:2px;">${briefing.headline}</div>
          <div style="color:var(--fg-primary);font-size:11.5px;">${briefing.summary}</div>
          <div style="color:var(--fg-muted);font-size:11px;margin-top:4px;">${briefing.macro_note}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;">
          <div style="background:var(--bg-base);border:1px solid var(--border);padding:7px 9px;border-radius:5px;">
            <strong style="color:var(--red);">▼ Escenario Venta (BSL):</strong><br/>
            <span style="color:var(--fg-muted);">${briefing.plan_sell}</span>
          </div>
          <div style="background:var(--bg-base);border:1px solid var(--border);padding:7px 9px;border-radius:5px;">
            <strong style="color:var(--green-bright);">▲ Escenario Compra (SSL):</strong><br/>
            <span style="color:var(--fg-muted);">${briefing.plan_buy}</span>
          </div>
        </div>
      `;
    }

    const tbody = document.querySelector("#liquidity-magnets-table tbody");
    if (tbody && levels && levels.liquidity_magnets) {
      tbody.innerHTML = levels.liquidity_magnets.map((m) => {
        const badgeCls = m.side === "BSL" ? "badge-gold" : (m.side === "SSL" ? "badge-blue" : "badge-muted");
        const sign = m.distance_pts >= 0 ? "+" : "";
        return `
          <tr>
            <td style="font-weight:600;color:#FFF;">${m.name}</td>
            <td><span class="badge ${badgeCls}">${m.side}</span></td>
            <td class="mono">$${m.price.toFixed(2)}</td>
            <td class="mono" style="color:${m.distance_pts >= 0 ? "#E3B341" : "#3794FF"};">${sign}${m.distance_pts.toFixed(2)} pts</td>
          </tr>
        `;
      }).join("");
    }
  }

  function renderUsdNewsTable(news) {
    const tbody = document.querySelector("#usd-news-table tbody");
    if (!tbody || !news) return;
    const list = (news.week_events || []).slice(0, 20);
    if (!list.length) {
      tbody.innerHTML = `<tr><td colspan="4" style="color:var(--fg-muted);text-align:center;">Sin eventos USD de alto impacto registrados.</td></tr>`;
      return;
    }
    tbody.innerHTML = list.map((ev) => `
      <tr>
        <td class="mono" style="white-space:nowrap;">${ev.day_label} <strong>${ev.time_vet}</strong></td>
        <td style="font-weight:600;color:${ev.is_red ? "#FFF" : "var(--fg-primary)"};">
          ${ev.title} ${ev.in_killzone ? '<span class="badge badge-blue" title="Cae dentro de tu horario 09:00-11:30 VET">NY</span>' : ""}
        </td>
        <td><span class="badge ${ev.is_red ? "badge-red" : "badge-gold"}">${ev.is_red ? "ROJA" : "MEDIA"}</span></td>
        <td class="mono" style="color:var(--fg-muted);">${ev.previous} / ${ev.forecast}</td>
      </tr>
    `).join("");
  }

  // -------------------------------------------------------------------------
  // CALCULADORA FUNDINGPIPS $10K
  // -------------------------------------------------------------------------
  function updateDirectionButtons() {
    const bSell = document.getElementById("calc-btn-sell");
    const bBuy = document.getElementById("calc-btn-buy");
    if (state.calc.direction === "SELL") {
      bSell.className = "dir-btn sell-active";
      bBuy.className = "dir-btn";
    } else {
      bSell.className = "dir-btn";
      bBuy.className = "dir-btn buy-active";
    }
  }

  async function recalculateRisk() {
    state.calc.account_size = parseFloat(document.getElementById("calc-account").value) || 10000;
    state.calc.risk_pct = parseFloat(document.getElementById("calc-risk-pct").value) || 0.5;
    state.calc.entry_price = parseFloat(document.getElementById("calc-entry").value) || 0;
    state.calc.stop_loss = parseFloat(document.getElementById("calc-sl").value) || 0;

    try {
      const resp = await fetch("/api/calculate_risk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_size: state.calc.account_size,
          risk_pct: state.calc.risk_pct,
          direction: state.calc.direction,
          entry_price: state.calc.entry_price,
          stop_loss: state.calc.stop_loss,
        }),
      });
      const r = await resp.json();
      state.calc.lastResult = r;

      const ruleBadge = document.getElementById("calc-rule-badge");
      if (!r.ok) {
        if (ruleBadge) {
          ruleBadge.textContent = "DIRECCIÓN SL INVÁLIDA";
          ruleBadge.className = "badge badge-red";
        }
        document.getElementById("res-delta").textContent = r.error || "Revisar SL";
        return;
      }

      if (ruleBadge) {
        ruleBadge.textContent = r.strict_range_ok ? "SL ÓPTIMO ($2.5-$10)" : "SL FUERA DE RANGO ($2.5-$10)";
        ruleBadge.className = `badge ${r.strict_range_ok ? "badge-green" : "badge-gold"}`;
      }

      document.getElementById("res-delta").textContent = `${r.delta_pts.toFixed(2)} pts (${r.pips} pips)`;
      document.getElementById("res-risk-usd").textContent = `$${r.actual_risk_usd.toFixed(2)} USD`;
      document.getElementById("res-margin").textContent = `$${r.margin_usd.toFixed(2)} USD`;
      document.getElementById("res-lots-total").textContent = `${r.lot_total.toFixed(2)} LOTES`;

      document.getElementById("res-ord1-title").textContent = `ORDEN 1 (${r.lot_order_1.toFixed(2)} Lotes)`;
      document.getElementById("res-tp1-px").textContent = `TP1: ${r.tp1_price.toFixed(2)}`;
      document.getElementById("res-tp1-usd").textContent = `+$${r.tp1_profit_usd.toFixed(2)}`;

      document.getElementById("res-ord2-title").textContent = `ORDEN 2 (${r.lot_order_2.toFixed(2)} Lotes)`;
      document.getElementById("res-tp2-px").textContent = `TP2: ${r.tp2_price.toFixed(2)}`;
      document.getElementById("res-tp2-usd").textContent = `+$${r.tp2_profit_usd.toFixed(2)}`;

      if (liveChart) {
        liveChart.updatePositionBox(buildCurrentPositionBox());
      }
      if (state.liveData) {
        renderLiveChecklist(state.liveData.live_checklist, state.liveData.journal_stats);
      }
    } catch (_) {}
  }

  // -------------------------------------------------------------------------
  // TAB 2: SIMULADOR REPLAY VELA A VELA
  // -------------------------------------------------------------------------
  async function initReplayDates() {
    try {
      const resp = await fetch("/api/replay_dates");
      const d = await resp.json();
      if (!d.ok) return;
      state.replay.dates = d.dates || [];
      const sel = document.getElementById("replay-date-select");
      sel.innerHTML = state.replay.dates.map((dt) =>
        `<option value="${dt}" ${dt === "2026-10-23" ? "selected" : ""}>${dt} ${dt === "2026-10-23" ? "★ Caso Estudio" : ""}</option>`
      ).join("");
    } catch (_) {}
  }

  async function loadReplaySession(targetDate = null, jumpToFull = false) {
    stopReplayAutoPlay();
    const sel = document.getElementById("replay-date-select");
    const tf = document.getElementById("replay-tf-select").value;
    const dateStr = targetDate || sel.value || "2026-10-23";
    if (targetDate && sel) sel.value = targetDate;

    const panel = document.getElementById("rep-analysis-panel");
    if (panel) panel.textContent = `Descargando velas históricas para ${dateStr}...`;

    try {
      const resp = await fetch(`/api/replay_session?date=${encodeURIComponent(dateStr)}&interval=${tf}`);
      const data = await resp.json();
      if (!data.ok) throw new Error(data.error);

      state.replay.session = data;
      const total = data.candles.length;
      state.replay.cursorIdx = jumpToFull ? total : Math.min(total, Math.max(15, data.kz_start_idx + 1));

      const scrub = document.getElementById("rep-scrubber");
      scrub.min = 10;
      scrub.max = total;
      scrub.value = state.replay.cursorIdx;

      renderReplayFrame(true);
    } catch (err) {
      if (panel) panel.textContent = `Error: ${err.message}`;
    }
  }

  function renderReplayFrame(fit = false) {
    const sess = state.replay.session;
    if (!sess || !replayChart) return;

    const idx = Math.max(10, Math.min(sess.candles.length, state.replay.cursorIdx));
    const visibleCandles = sess.candles.slice(0, idx);
    const curBar = visibleCandles[visibleCandles.length - 1];
    const curTs = curBar.time;

    document.getElementById("rep-scrubber").value = idx;
    document.getElementById("rep-bar-counter").textContent = `${idx} / ${sess.candles.length} velas`;
    document.getElementById("rep-clock-label").textContent = `${curBar.vet_str} VET`;

    // Evitar lookahead del futuro: filtrar FVGs, marcadores y setups ocurridos solo hasta curTs
    const visibleFvgs = (sess.fvgs || [])
      .filter((f) => f.start_ts <= curTs)
      .map((f) => ({ ...f, end_ts: Math.min(f.end_ts, curTs + 900) }));

    const visibleMarkers = state.replay.blindMode
      ? []
      : (sess.markers || []).filter((m) => m.time <= curTs);

    const revealedSetups = state.replay.blindMode
      ? []
      : (sess.setups || []).filter((s) => s.cisd_ts <= curTs);

    let posBox = null;
    if (revealedSetups.length > 0) {
      const s = revealedSetups[0];
      posBox = {
        direction: s.direction,
        entry: s.entry_price,
        sl: s.stop_loss,
        tp1: s.tp1_price,
        tp2: s.tp2_price,
        lots: s.lots_total.toFixed(2),
        riskUsd: 50,
        startTs: s.entry_ts,
        endTs: Math.min(s.exit_ts, curTs + 1800),
      };
    }

    replayChart.setScene({
      candles: visibleCandles,
      levels: sess.levels,
      fvgs: visibleFvgs,
      markers: visibleMarkers,
      positionBox: posBox,
      fitContent: fit,
    });

    const badge = document.getElementById("rep-setups-badge");
    const panel = document.getElementById("rep-analysis-panel");
    if (state.replay.blindMode) {
      if (badge) badge.textContent = "MODO CIEGO";
      if (panel) {
        panel.innerHTML = `
          <div style="background:var(--bg-base);border:1px solid var(--accent);padding:10px;border-radius:6px;">
            <strong style="color:var(--accent-bright);">🙈 Modo Entrenamiento Activo</strong><br/>
            Las etiquetas de Ares están ocultas. Avanza vela por vela, identifica la barrida (R2), el CISD (R3) y el FVG (R4), anota tu entrada abajo y luego pulsa <strong>"Marcas de Ares"</strong> para auditar tu ojo.
          </div>
        `;
      }
    } else {
      if (badge) badge.textContent = `${revealedSetups.length} Setup(s) hasta ahora`;
      if (panel) {
        if (!revealedSetups.length) {
          panel.innerHTML = `<div style="color:var(--fg-muted);">Avanza hacia la ventana 09:00 - 11:30 AM VET para observar la formación de barridas de liquidez y confirmación CISD.</div>`;
        } else {
          panel.innerHTML = revealedSetups.map((s) => `
            <div style="background:var(--bg-base);border:1px solid var(--border);border-left:3px solid var(--accent);padding:9px;border-radius:6px;">
              <div style="display:flex;justify-content:space-between;font-weight:700;color:#FFF;">
                <span>${s.direction} (${s.grade}) · CISD ${s.cisd_time_vet} VET</span>
                <span class="mono" style="color:${s.pnl_usd >= 0 ? "#3FB950" : "#F85149"};">${s.outcome}</span>
              </div>
              <div style="margin-top:4px;color:var(--fg-muted);font-size:11.5px;">
                • <strong>R2 Sweep:</strong> ${s.swept_pools} @ ${s.sweep_extreme}<br/>
                • <strong>R4 Entrada FVG 50% CE:</strong> <span class="mono" style="color:#FFF;">${s.entry_price.toFixed(2)}</span><br/>
                • <strong>R5 Riesgo:</strong> SL ${s.stop_loss.toFixed(2)} (${s.risk_pts} pts) · ${s.lots_total} Lotes · TP1 ${s.tp1_price.toFixed(2)} / TP2 ${s.tp2_price.toFixed(2)}
              </div>
            </div>
          `).join("");
          // Pre-llenar campos de registro rápido si están vacíos
          const s0 = revealedSetups[0];
          document.getElementById("rep-j-dir").value = s0.direction;
          if (!document.getElementById("rep-j-entry").value) {
            document.getElementById("rep-j-entry").value = s0.entry_price.toFixed(2);
            document.getElementById("rep-j-sl").value = s0.stop_loss.toFixed(2);
          }
        }
      }
    }
  }

  function stopReplayAutoPlay() {
    if (state.replay.playTimer) {
      clearInterval(state.replay.playTimer);
      state.replay.playTimer = null;
    }
    const btn = document.getElementById("rep-btn-play");
    if (btn) btn.textContent = "▶ Auto-Play";
  }

  // -------------------------------------------------------------------------
  // TAB 3: BACKTESTER INSTITUCIONAL 60 DÍAS
  // -------------------------------------------------------------------------
  async function loadBacktest() {
    const onlyAPlus = document.getElementById("bt-only-aplus").checked;
    const riskPct = document.getElementById("bt-risk-select").value;
    const kpiGrid = document.getElementById("bt-kpi-grid");
    if (kpiGrid) kpiGrid.innerHTML = `<div style="color:var(--fg-muted);">Calculando 60 días de sesiones M5 en XAU/USD...</div>`;

    try {
      const resp = await fetch(`/api/backtest?account_size=10000&risk_pct=${riskPct}&only_a_plus=${onlyAPlus}`);
      const data = await resp.json();
      if (!data.ok) throw new Error(data.error);

      state.backtestLoaded = true;
      const m = data.metrics;
      const netCol = m.net_profit_usd >= 0 ? "#3FB950" : "#F85149";

      kpiGrid.innerHTML = `
        <div class="kpi-box">
          <div class="kpi-label">Beneficio Neto (60D)</div>
          <div class="kpi-val" style="color:${netCol};">${m.net_profit_usd >= 0 ? "+" : ""}$${m.net_profit_usd.toFixed(2)}</div>
          <div class="kpi-sub">Balance: $${m.final_balance.toFixed(2)} (${m.net_profit_pct >= 0 ? "+" : ""}${m.net_profit_pct}%)</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">Win Rate Efectivo</div>
          <div class="kpi-val">${m.win_rate_pct}%</div>
          <div class="kpi-sub">${m.wins} Ganadas (${m.full_3r_wins} Full 3R · ${m.partial_be_wins} TP1+BE) / ${m.losses} SL</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">Profit Factor</div>
          <div class="kpi-val" style="color:var(--accent-bright);">${m.profit_factor}</div>
          <div class="kpi-sub">Expectancy: ${m.expectancy_usd >= 0 ? "+" : ""}$${m.expectancy_usd} (${m.expectancy_r}R / trade)</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">Máx. Drawdown Acumulado</div>
          <div class="kpi-val" style="color:${m.fp_daily_limit_safe ? "#3FB950" : "#F85149"};">-$${m.max_drawdown_usd.toFixed(2)} (${m.max_drawdown_pct}%)</div>
          <div class="kpi-sub">Límite FundingPips: $500 Diario / $1,000 Total ✓</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">Total Operaciones</div>
          <div class="kpi-val">${m.total_trades}</div>
          <div class="kpi-sub">Promedio ~${(m.total_trades / 8.5).toFixed(1)} setups limpios / semana</div>
        </div>
      `;

      renderEquityCurve(data.equity_curve || []);

      const tbody = document.querySelector("#bt-trades-table tbody");
      tbody.innerHTML = (data.trades || []).map((t) => `
        <tr>
          <td class="mono">${t.trade_num}</td>
          <td class="mono" style="font-weight:700;color:#FFF;">${t.date}</td>
          <td><span class="badge ${t.grade === "A+" ? "badge-blue" : "badge-muted"}">${t.grade}</span></td>
          <td><span class="badge ${t.direction === "SELL" ? "badge-red" : "badge-green"}">${t.direction}</span></td>
          <td>${t.swept_pools} (${t.sweep_time_vet})</td>
          <td class="mono">${t.cisd_time_vet} @ ${t.cisd_level}</td>
          <td class="mono">$${t.entry_price.toFixed(2)}</td>
          <td class="mono">$${t.stop_loss.toFixed(2)} (${t.risk_pts}p)</td>
          <td class="mono">${t.lots_total}</td>
          <td>${t.outcome}</td>
          <td class="mono" style="font-weight:700;color:${t.pnl_usd >= 0 ? "#3FB950" : "#F85149"};">
            ${t.pnl_usd >= 0 ? "+" : ""}$${t.pnl_usd.toFixed(2)}
          </td>
          <td class="mono">$${t.balance_after.toFixed(2)}</td>
          <td>
            <button class="btn btn-sm btn-outline-accent" data-jump-date="${t.date}">🔍 Ver Replay</button>
          </td>
        </tr>
      `).join("");

      tbody.querySelectorAll("[data-jump-date]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const dt = btn.getAttribute("data-jump-date");
          switchTab("tab-replay");
          loadReplaySession(dt, true);
        });
      });
    } catch (err) {
      if (kpiGrid) kpiGrid.innerHTML = `<div style="color:var(--red);">Error en backtest: ${err.message}</div>`;
    }
  }

  function renderEquityCurve(curve) {
    const container = document.getElementById("bt-equity-chart");
    if (!container) return;
    container.innerHTML = "";

    equityChart = LightweightCharts.createChart(container, {
      layout: {
        background: { type: "solid", color: "#161616" },
        textColor: "#CCCCCC",
        fontFamily: "Consolas, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#202020" },
        horzLines: { color: "#202020" },
      },
      rightPriceScale: { borderColor: "#262626" },
      timeScale: { borderColor: "#262626", timeVisible: false },
    });

    const area = equityChart.addAreaSeries({
      lineColor: "#007ACC",
      topColor: "rgba(0, 122, 204, 0.32)",
      bottomColor: "rgba(0, 122, 204, 0.02)",
      lineWidth: 2,
    });

    const baseTs = 1767225600; // Base sintética diaria para índice secuencial de trades
    const pts = curve.map((pt, i) => ({
      time: baseTs + i * 86400,
      value: pt.balance,
    }));
    area.setData(pts);

    area.createPriceLine({
      price: 10800,
      color: "#3FB950",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Meta Fase 1 ($10,800)",
    });
    area.createPriceLine({
      price: 10000,
      color: "#666666",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dotted,
      axisLabelVisible: true,
      title: "Capital Inicial",
    });

    equityChart.timeScale().fitContent();
  }

  // -------------------------------------------------------------------------
  // TAB 4: DIARIO SQLITE + SIMULADOR ESCALADO FUNDINGPIPS
  // -------------------------------------------------------------------------
  async function loadJournalAndScaling() {
    try {
      const resp = await fetch("/api/journal");
      const data = await resp.json();
      if (data.ok) renderJournalData(data);
    } catch (_) {}
    await runScalingSimulation();
  }

  function renderJournalData(data) {
    state.journalLoaded = true;
    const badge = document.getElementById("j-summary-badge");
    if (badge && data.stats) {
      badge.textContent = `${data.stats.total_entries} Reg · WR ${data.stats.win_rate_pct}% · Neto $${data.stats.total_pnl_usd.toFixed(2)}`;
    }
    const tbody = document.querySelector("#journal-table tbody");
    if (!tbody) return;
    const entries = data.entries || [];
    if (!entries.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="color:var(--fg-muted);text-align:center;padding:16px;">Tu bitácora está lista. Guarda setups desde el Radar, Replay o manualmente arriba.</td></tr>`;
      return;
    }

    tbody.innerHTML = entries.map((e) => `
      <tr>
        <td class="mono">${e.trade_date}</td>
        <td><span class="badge badge-muted">${e.mode}</span></td>
        <td><span class="badge ${e.direction === "SELL" ? "badge-red" : "badge-green"}">${e.direction}</span></td>
        <td class="mono">${e.entry_price} / ${e.stop_loss} (${e.lots}L)</td>
        <td class="mono" style="font-weight:700;color:${e.pnl_usd > 0 ? "#3FB950" : (e.pnl_usd < 0 ? "#F85149" : "#CCC")};">
          ${e.pnl_usd >= 0 ? "+" : ""}$${Number(e.pnl_usd).toFixed(2)}
        </td>
        <td style="font-size:11px;">
          ${e.user_notes ? `<div>${e.user_notes}</div>` : ""}
          ${e.discrepancy_note ? `<div style="color:var(--accent-bright);">⚡ Discrepancia: ${e.discrepancy_note}</div>` : ""}
        </td>
        <td>
          <button class="btn btn-sm" data-del-id="${e.id}" title="Eliminar">✕</button>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-del-id]").forEach((b) => {
      b.addEventListener("click", async () => {
        const id = b.getAttribute("data-del-id");
        const r = await fetch(`/api/journal/${id}`, { method: "DELETE" });
        const d = await r.json();
        if (d.ok) renderJournalData(d);
      });
    });
  }

  async function runScalingSimulation() {
    const ret = parseFloat(document.getElementById("sc-ret").value) || 5.5;
    const split = parseFloat(document.getElementById("sc-split").value) || 80;
    const reinv = parseFloat(document.getElementById("sc-reinv").value) || 35;

    try {
      const resp = await fetch("/api/scaling_sim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          monthly_return_pct: ret,
          profit_split_pct: split,
          reinvest_rate_pct: reinv,
          months: 12,
        }),
      });
      const d = await resp.json();
      if (!d.ok) return;

      document.getElementById("sc-kpis").innerHTML = `
        <div class="kpi-box">
          <div class="kpi-label">Capital Copiado Mes 12</div>
          <div class="kpi-val" style="color:var(--accent-bright);">$${d.final_funded_capital.toLocaleString()}</div>
          <div class="kpi-sub">${d.accounts_managed} cuenta(s) operadas con Copiador</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">Retiros Netos a tu Wallet</div>
          <div class="kpi-val" style="color:var(--green-bright);">+$${d.total_pocket_usdt.toLocaleString()} USDT</div>
          <div class="kpi-sub">Libre tras reinversión en nuevas pruebas</div>
        </div>
      `;

      const tbody = document.querySelector("#sc-table tbody");
      tbody.innerHTML = d.timeline.map((row) => `
        <tr>
          <td class="mono" style="font-weight:700;color:#FFF;">${row.month}</td>
          <td class="mono">$${row.funded_capital.toLocaleString()}</td>
          <td class="mono" style="color:var(--fg-muted);">$${row.eval_capital.toLocaleString()}</td>
          <td class="mono" style="color:#3FB950;">+$${row.pocket_usdt.toLocaleString()}</td>
          <td class="mono" style="font-weight:700;">$${row.cumulative_wallet_usdt.toLocaleString()}</td>
          <td style="font-size:11px;color:var(--fg-muted);">${row.note}</td>
        </tr>
      `).join("");
    } catch (_) {}
  }

  // -------------------------------------------------------------------------
  // NAVEGACIÓN ENTRE PESTAÑAS
  // -------------------------------------------------------------------------
  function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("active", p.id === tabId);
    });

    if (tabId === "tab-live" && liveChart) {
      setTimeout(() => liveChart.scheduleDraw(), 40);
    } else if (tabId === "tab-replay") {
      if (!state.replay.session) loadReplaySession();
      else if (replayChart) setTimeout(() => replayChart.scheduleDraw(), 40);
    } else if (tabId === "tab-backtest") {
      if (!state.backtestLoaded) loadBacktest();
    } else if (tabId === "tab-journal") {
      if (!state.journalLoaded) loadJournalAndScaling();
    }
  }

  // -------------------------------------------------------------------------
  // INICIALIZACIÓN Y EVENT LISTENERS
  // -------------------------------------------------------------------------
  function setupEventListeners() {
    // Tabs
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab")));
    });

    // Fuente y temporalidad en vivo
    document.getElementById("live-source-select").addEventListener("change", (e) => {
      state.source = e.target.value;
      state.calc.initialSynced = false;
      loadLiveState(true);
    });

    document.querySelectorAll(".tf-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tf-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.interval = btn.getAttribute("data-tf");
        loadLiveState(true);
      });
    });

    // Chips de capas visuales
    document.querySelectorAll(".layer-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const key = chip.getAttribute("data-layer");
        state.layers[key] = !state.layers[key];
        chip.classList.toggle("active", state.layers[key]);
        if (liveChart && state.liveData) liveChart.refreshLayers(state.liveData.markers);
        if (replayChart && state.replay.session) renderReplayFrame(false);
      });
    });

    // Selector interactivo de precios sobre el gráfico
    const pickEntryBtn = document.getElementById("btn-pick-entry");
    const pickSlBtn = document.getElementById("btn-pick-sl");
    pickEntryBtn.addEventListener("click", () => {
      state.pickMode = state.pickMode === "entry" ? null : "entry";
      pickEntryBtn.classList.toggle("active", state.pickMode === "entry");
      pickSlBtn.classList.remove("active");
      if (state.pickMode) showToast("Haz clic sobre cualquier precio del gráfico para fijar la ENTRADA");
    });
    pickSlBtn.addEventListener("click", () => {
      state.pickMode = state.pickMode === "sl" ? null : "sl";
      pickSlBtn.classList.toggle("active", state.pickMode === "sl");
      pickEntryBtn.classList.remove("active");
      if (state.pickMode) showToast("Haz clic sobre el gráfico para fijar tu STOP LOSS");
    });

    // Auto-refresh
    const autoBtn = document.getElementById("btn-auto-refresh");
    autoBtn.addEventListener("click", () => {
      state.autoRefresh = !state.autoRefresh;
      autoBtn.textContent = `⏱ Auto 12s: ${state.autoRefresh ? "ON" : "OFF"}`;
    });

    document.getElementById("btn-refresh-now").addEventListener("click", () => loadLiveState(false));
    document.getElementById("btn-fit-chart").addEventListener("click", () => {
      if (liveChart && state.liveData) {
        liveChart.setScene({
          candles: state.liveData.candles,
          levels: state.liveData.levels,
          fvgs: state.liveData.fvgs,
          markers: state.liveData.markers,
          positionBox: buildCurrentPositionBox(),
          fitContent: true,
        });
      }
    });

    // Calculadora FundingPips
    document.getElementById("calc-btn-sell").addEventListener("click", () => {
      state.calc.direction = "SELL";
      updateDirectionButtons();
      const ent = parseFloat(document.getElementById("calc-entry").value) || 4040;
      const sl = parseFloat(document.getElementById("calc-sl").value) || 4046;
      if (sl <= ent) document.getElementById("calc-sl").value = (ent + 6.0).toFixed(2);
      recalculateRisk();
    });
    document.getElementById("calc-btn-buy").addEventListener("click", () => {
      state.calc.direction = "BUY";
      updateDirectionButtons();
      const ent = parseFloat(document.getElementById("calc-entry").value) || 4040;
      const sl = parseFloat(document.getElementById("calc-sl").value) || 4034;
      if (sl >= ent) document.getElementById("calc-sl").value = (ent - 6.0).toFixed(2);
      recalculateRisk();
    });

    ["calc-account", "calc-risk-pct", "calc-entry", "calc-sl"].forEach((id) => {
      document.getElementById(id).addEventListener("input", () => {
        state.calc.anchorStartTs = null;
        state.calc.anchorEndTs = null;
        recalculateRisk();
      });
    });

    document.getElementById("link-auto-buffer").addEventListener("click", (e) => {
      e.preventDefault();
      const ent = parseFloat(document.getElementById("calc-entry").value) || 4040;
      const offset = state.calc.direction === "SELL" ? 5.0 : -5.0;
      document.getElementById("calc-sl").value = (ent + offset).toFixed(2);
      recalculateRisk();
    });

    document.getElementById("btn-copy-ticket").addEventListener("click", async () => {
      const txt = state.calc.lastResult && state.calc.lastResult.ticket_text;
      if (!txt) return;
      try {
        await navigator.clipboard.writeText(txt);
        showToast("Boleto Split FundingPips copiado al portapapeles");
      } catch (_) {
        showToast("Listo para copiar");
      }
    });

    document.getElementById("btn-send-to-journal").addEventListener("click", () => {
      const r = state.calc.lastResult;
      if (r && r.ok) {
        document.getElementById("j-dir").value = r.direction;
        document.getElementById("j-entry").value = r.entry_price.toFixed(2);
        document.getElementById("j-sl").value = r.stop_loss.toFixed(2);
        document.getElementById("j-lots").value = r.lot_total.toFixed(2);
      }
      switchTab("tab-journal");
      showToast("Parámetros cargados en tu Bitácora Operativa");
    });

    // Controles Replay
    document.getElementById("btn-load-replay").addEventListener("click", () => loadReplaySession());
    document.getElementById("rep-btn-kz").addEventListener("click", () => {
      if (!state.replay.session) return;
      stopReplayAutoPlay();
      state.replay.cursorIdx = state.replay.session.kz_start_idx;
      renderReplayFrame(true);
    });
    document.getElementById("rep-btn-prev").addEventListener("click", () => {
      if (!state.replay.session) return;
      stopReplayAutoPlay();
      state.replay.cursorIdx = Math.max(10, state.replay.cursorIdx - 1);
      renderReplayFrame(false);
    });
    document.getElementById("rep-btn-next").addEventListener("click", () => {
      if (!state.replay.session) return;
      stopReplayAutoPlay();
      state.replay.cursorIdx = Math.min(state.replay.session.candles.length, state.replay.cursorIdx + 1);
      renderReplayFrame(false);
    });
    document.getElementById("rep-btn-all").addEventListener("click", () => {
      if (!state.replay.session) return;
      stopReplayAutoPlay();
      state.replay.cursorIdx = state.replay.session.candles.length;
      renderReplayFrame(true);
    });
    document.getElementById("rep-btn-play").addEventListener("click", (ev) => {
      if (!state.replay.session) return;
      if (state.replay.playTimer) {
        stopReplayAutoPlay();
        return;
      }
      ev.target.textContent = "⏸ Pausar";
      state.replay.playTimer = setInterval(() => {
        if (!state.replay.session || state.replay.cursorIdx >= state.replay.session.candles.length) {
          stopReplayAutoPlay();
          return;
        }
        state.replay.cursorIdx += 1;
        renderReplayFrame(false);
      }, 420);
    });
    document.getElementById("rep-scrubber").addEventListener("input", (ev) => {
      stopReplayAutoPlay();
      state.replay.cursorIdx = parseInt(ev.target.value, 10) || 20;
      renderReplayFrame(false);
    });
    document.getElementById("rep-toggle-blind").addEventListener("click", (ev) => {
      state.replay.blindMode = !state.replay.blindMode;
      ev.target.textContent = state.replay.blindMode
        ? "🙈 Marcas de Ares: OCULTAS (Revelar)"
        : "👁️ Marcas de Ares: VISIBLES";
      ev.target.classList.toggle("active", state.replay.blindMode);
      renderReplayFrame(false);
    });

    document.getElementById("btn-save-replay-note").addEventListener("click", async () => {
      const sess = state.replay.session;
      const outVal = document.getElementById("rep-j-out").value;
      const pnlMap = {
        "TP1 + TP2 (+2.25R)": 112.5,
        "TP1 + BE (+0.75R)": 37.5,
        "STOP LOSS (-1R)": -50.0,
        "AUDITORÍA / ESTUDIO": 0.0,
      };
      const payload = {
        trade_date: sess ? sess.date : new Date().toISOString().slice(0, 10),
        mode: "ESTUDIO",
        direction: document.getElementById("rep-j-dir").value,
        entry_price: parseFloat(document.getElementById("rep-j-entry").value) || 0,
        stop_loss: parseFloat(document.getElementById("rep-j-sl").value) || 0,
        lots: 0.06,
        outcome: outVal,
        pnl_usd: pnlMap[outVal] ?? 0,
        user_notes: `Sesión Replay ${sess ? sess.date : ""}`,
        discrepancy_note: document.getElementById("rep-j-disc").value.trim(),
      };
      const r = await fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (d.ok) {
        renderJournalData(d);
        document.getElementById("rep-j-disc").value = "";
        showToast("Análisis y punto de discrepancia guardados en tu Diario");
      }
    });

    // Backtest
    document.getElementById("btn-run-backtest").addEventListener("click", () => loadBacktest());
    document.getElementById("bt-only-aplus").addEventListener("change", () => loadBacktest());
    document.getElementById("bt-risk-select").addEventListener("change", () => loadBacktest());

    // Diario & Escalado
    document.getElementById("j-date").value = new Date().toISOString().slice(0, 10);
    document.getElementById("btn-add-journal").addEventListener("click", async () => {
      const payload = {
        trade_date: document.getElementById("j-date").value,
        mode: document.getElementById("j-mode").value,
        direction: document.getElementById("j-dir").value,
        entry_price: parseFloat(document.getElementById("j-entry").value) || 0,
        stop_loss: parseFloat(document.getElementById("j-sl").value) || 0,
        lots: parseFloat(document.getElementById("j-lots").value) || 0.06,
        outcome: document.getElementById("j-outcome").value,
        pnl_usd: parseFloat(document.getElementById("j-pnl").value) || 0,
        user_notes: document.getElementById("j-notes").value.trim(),
        discrepancy_note: document.getElementById("j-disc").value.trim(),
      };
      const r = await fetch("/api/journal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (d.ok) {
        renderJournalData(d);
        loadLiveState(false);
        document.getElementById("j-notes").value = "";
        document.getElementById("j-disc").value = "";
        showToast("Operación registrada en la base de datos de Atom");
      }
    });

    document.getElementById("btn-run-scaling").addEventListener("click", () => runScalingSimulation());
  }

  // -------------------------------------------------------------------------
  // BOOTSTRAP
  // -------------------------------------------------------------------------
  window.addEventListener("DOMContentLoaded", async () => {
    startHeaderClocks();

    liveChart = new AresChartController("live-tv-chart", "live-overlay-canvas", "hud-ohlc", (price, clickedTs) => {
      if (!state.pickMode) return;
      if (state.pickMode === "entry") {
        document.getElementById("calc-entry").value = price.toFixed(2);
        state.calc.anchorStartTs = clickedTs;
        state.calc.anchorEndTs = null;
        showToast(`Entrada fijada en $${price.toFixed(2)}`);
      } else if (state.pickMode === "sl") {
        document.getElementById("calc-sl").value = price.toFixed(2);
        showToast(`Stop Loss fijado en $${price.toFixed(2)}`);
      }
      state.pickMode = null;
      document.getElementById("btn-pick-entry").classList.remove("active");
      document.getElementById("btn-pick-sl").classList.remove("active");
      recalculateRisk();
    });

    replayChart = new AresChartController("replay-tv-chart", "replay-overlay-canvas", "rep-hud-text", (price) => {
      document.getElementById("rep-j-entry").value = price.toFixed(2);
      showToast(`Precio $${price.toFixed(2)} copiado a tu campo de práctica`);
    });

    setupEventListeners();
    await initReplayDates();
    await loadLiveState(true);

    setInterval(() => {
      const livePanel = document.getElementById("tab-live");
      if (state.autoRefresh && livePanel && livePanel.classList.contains("active")) {
        loadLiveState(false);
      }
    }, 12000);
  });
})();
