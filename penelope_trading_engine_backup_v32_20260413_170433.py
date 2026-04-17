#!/usr/bin/env python3
"""
PENELOPE TRADING ENGINE v3.1
Fixes:
  - bars=null guard (market closed / weekend)
  - duplicate log handlers removed
  - snapshot fallback for price when bars unavailable
  - _meta excluded from strategy status loop
"""

import os, json, time, requests, logging
from datetime import datetime, date, timedelta
from pathlib import Path

# ── Vault ────────────────────────────────────────────────────────────────────
def load_vault():
    env = {}
    try:
        with open("/root/penelope_vault.env") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except:
        pass
    return env

ENV            = load_vault()
ALPACA_KEY     = ENV.get("ALPACA_API_KEY", "")
ALPACA_SECRET  = ENV.get("ALPACA_SECRET_KEY", "")
ALPACA_BASE    = "https://paper-api.alpaca.markets/v2"
ALPACA_DATA    = "https://data.alpaca.markets/v2"
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = ENV.get("TELEGRAM_CHAT_ID", "6183015901")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type": "application/json"
}

STATE_FILE = Path("/root/workspace/Penelope/trading_bot/engine_v3_state.json")
FEED_FILE  = Path("/root/workspace/Penelope/feed.json")
LOG_FILE   = Path("/root/workspace/Penelope/trading_bot/engine_v3.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Logging (single handler, no duplicates) ───────────────────────────────────
logger = logging.getLogger("penelope_v3")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.propagate = False
fh = logging.FileHandler(str(LOG_FILE))
fh.setFormatter(logging.Formatter("%(asctime)s [TRADE-V3] %(message)s"))
logger.addHandler(fh)
log = logger

# ── Strategy definitions ──────────────────────────────────────────────────────
STRATEGIES = [
    {"id": "momentum-AAPL",   "fn": "momentum",    "symbol": "AAPL", "capital": 5000, "max_dd_pct": 60, "interval": 300},
    {"id": "momentum-NVDA",   "fn": "momentum",    "symbol": "NVDA", "capital": 5000, "max_dd_pct": 60, "interval": 300},
    {"id": "rsi-MSFT",        "fn": "rsi",         "symbol": "MSFT", "capital": 5000, "max_dd_pct": 60, "interval": 300},
    {"id": "rsi-SPY",         "fn": "rsi",         "symbol": "SPY",  "capital": 5000, "max_dd_pct": 60, "interval": 300},
    {"id": "macd-QQQ",        "fn": "macd",        "symbol": "QQQ",  "capital": 5000, "max_dd_pct": 60, "interval": 300},
    {"id": "mean_revert-SPY", "fn": "mean_revert", "symbol": "SPY",  "capital": 5000, "max_dd_pct": 50, "interval": 300},
    {"id": "orb-AAPL",        "fn": "orb",         "symbol": "AAPL", "capital": 5000, "max_dd_pct": 40, "interval": 300},
]

# ── Atomic state ──────────────────────────────────────────────────────────────
def load_state() -> dict:
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except:
            state = {}
    for s in STRATEGIES:
        sid = s["id"]
        if sid not in state:
            state[sid] = {
                "initial_capital":    s["capital"],
                "portfolio_value":    s["capital"],
                "peak_value":         s["capital"],
                "cash":               s["capital"],
                "position":           None,
                "trade_count":        0,
                "win_count":          0,
                "pnl":                0.0,
                "pnl_pct":            0.0,
                "consecutive_losses": 0,
                "risk_state": {
                    "current_drawdown_pct":  0.0,
                    "max_drawdown_pct":      s["max_dd_pct"],
                    "circuit_breaker_until": None,
                    "short_pause_until":     None,
                }
            }
    return state

def save_state(state: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.rename(STATE_FILE)

# ── Alpaca API ────────────────────────────────────────────────────────────────
def alpaca_get(path: str, base=None) -> dict | list:
    url = (base or ALPACA_BASE) + path
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            return r.json()
        log.warning(f"Alpaca GET {path} → {r.status_code}: {r.text[:150]}")
    except Exception as e:
        log.warning(f"Alpaca GET {path} error: {e}")
    return {}

def alpaca_post(path: str, body: dict) -> dict:
    try:
        r = requests.post(f"{ALPACA_BASE}{path}", headers=HEADERS, json=body, timeout=12)
        return r.json()
    except Exception as e:
        log.warning(f"Alpaca POST {path} error: {e}")
        return {"error": str(e)}

def get_account() -> dict:
    return alpaca_get("/account")

def get_bars(symbol: str, timeframe="1Hour", limit=60) -> list:
    """Fetch bars directly with correct params. Returns [] on any failure."""
    from datetime import timedelta
    start = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00Z")
    try:
        r = requests.get(
            f"{ALPACA_DATA}/stocks/{symbol}/bars",
            headers=HEADERS,
            params={
                "timeframe": timeframe,
                "limit": limit,
                "adjustment": "raw",
                "feed": "iex",
                "start": start,
            },
            timeout=15
        )
        if r.status_code == 200:
            bars = r.json().get("bars")
            return bars if bars else []
        log.warning(f"Bars {symbol} → {r.status_code}: {r.text[:120]}")
    except Exception as e:
        log.warning(f"Bars {symbol} error: {e}")
    return []

def get_latest_price(symbol: str) -> float | None:
    """Get price via snapshot (works even when market closed)."""
    data = alpaca_get(f"/stocks/{symbol}/snapshot", base=ALPACA_DATA)
    if isinstance(data, dict):
        # Try latest trade first, fall back to daily bar close
        lt = data.get("latestTrade", {})
        if lt.get("p"):
            return float(lt["p"])
        db = data.get("dailyBar", {})
        if db.get("c"):
            return float(db["c"])
    return None


# ── ADX / ATR / VWAP helpers (added v3.2) ─────────────────────────────────
def calc_atr(bars: list, period: int = 14) -> float:
    """Average True Range — volatility-normalized stop distance."""
    if len(bars) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i-1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period if trs else 0.0


def calc_adx(bars: list, period: int = 14) -> float:
    """Average Directional Index — measures trend strength.
    Returns 0-100. >= 20 = trending, < 20 = choppy/sideways."""
    if len(bars) < period + 2:
        return 0.0
    pdm, mdm, trs = [], [], []
    for i in range(1, len(bars)):
        h, l = bars[i]["h"], bars[i]["l"]
        ph, pl, pc = bars[i-1]["h"], bars[i-1]["l"], bars[i-1]["c"]
        up, down = h - ph, pl - l
        pdm.append(up   if up > down and up > 0   else 0.0)
        mdm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    def smooth(d, p):
        s = [sum(d[:p])]
        for x in d[p:]:
            s.append(s[-1] - s[-1] / p + x)
        return s
    atr14 = smooth(trs, period)
    pdm14 = smooth(pdm, period)
    mdm14 = smooth(mdm, period)
    if not atr14 or atr14[-1] == 0:
        return 0.0
    pdi = 100 * pdm14[-1] / atr14[-1]
    mdi = 100 * mdm14[-1] / atr14[-1]
    denom = pdi + mdi
    return round(100 * abs(pdi - mdi) / denom if denom > 0 else 0.0, 2)


def calc_vwap(bars: list) -> float:
    """Volume-Weighted Average Price — intraday fair value."""
    cum_tv = cum_v = 0.0
    for b in bars:
        tp  = (b["h"] + b["l"] + b["c"]) / 3
        vol = b.get("v", 1) or 1
        cum_tv += tp * vol
        cum_v  += vol
    return cum_tv / cum_v if cum_v > 0 else (bars[-1]["c"] if bars else 0.0)


ADX_THRESHOLD  = 20    # minimum trend strength to allow new entries
ATR_STOP_MULT  = 1.5   # stop = entry_price - ATR_STOP_MULT * ATR
ADX_BAR_LIMIT  = 40    # bars to fetch for ADX calculation


def place_order(symbol: str, side: str, qty: float, strategy_id: str) -> dict:
    body = {
        "symbol": symbol,
        "qty": str(round(qty, 4)),
        "side": side,
        "type": "market",
        "time_in_force": "day",
        "client_order_id": f"{strategy_id}-{int(time.time())}"
    }
    result = alpaca_post("/orders", body)
    log.info(f"ORDER {side.upper()} {qty} {symbol} [{strategy_id}] → {result.get('id','ERR')}: {result.get('status','?')}")
    return result

def is_market_open() -> bool:
    clock = alpaca_get("/clock")
    return bool(clock.get("is_open", False))

# ── Telegram ──────────────────────────────────────────────────────────────────
def telegram(msg: str, force=False):
    """Revenue/critical only gate — self-contained, no external import."""
    import os as _o, requests as _r
    _tok = _o.getenv("TELEGRAM_BOT_TOKEN", "")
    _cid = "6183015901"
    _ml  = str(msg).lower()
    _rev  = any(x in _ml for x in ["revenue confirmed","sale confirmed","payment received","paid $","new sale"])
    _crit = force or ("🚨" in msg and any(x in _ml for x in ["system down","cannot restart","disk full","out of memory"]))
    if not _rev and not _crit:
        return
    try:
        _r.post(f"https://api.telegram.org/bot{_tok}/sendMessage",
            json={"chat_id": _cid, "text": str(msg)[:4000], "parse_mode": "Markdown"},
            timeout=8)
    except:
        pass


def post_feed(title: str, content: str, status="info"):
    try:
        feed = []
        if FEED_FILE.exists():
            try:
                feed = json.loads(FEED_FILE.read_text())
            except:
                feed = []
        feed.insert(0, {
            "id": int(time.time()),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": f"[TradeV3] {title}",
            "content": content,
            "status": status,
            "agent": "TradingEngineV3"
        })
        feed = feed[:100]
        tmp = FEED_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(feed, indent=2))
        tmp.rename(FEED_FILE)
    except Exception as e:
        log.warning(f"Feed error: {e}")

# ── Risk / Circuit Breaker ────────────────────────────────────────────────────
def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except:
        return None

def is_circuit_broken(sid: str, risk: dict) -> bool:
    until = parse_dt(risk.get("circuit_breaker_until"))
    if until and datetime.now() < until:
        return True
    if until and datetime.now() >= until:
        risk["circuit_breaker_until"] = None
    return False

def is_short_paused(sid: str, risk: dict) -> bool:
    until = parse_dt(risk.get("short_pause_until"))
    if until and datetime.now() < until:
        return True
    if until and datetime.now() >= until:
        risk["short_pause_until"] = None
    return False

def check_circuit_breaker(sid: str, st: dict, current_value: float):
    risk = st["risk_state"]
    peak = st["peak_value"]
    if current_value > peak:
        st["peak_value"] = current_value
        peak = current_value
    dd_pct = ((peak - current_value) / peak * 100) if peak > 0 else 0
    risk["current_drawdown_pct"] = round(dd_pct, 2)
    if dd_pct >= risk["max_drawdown_pct"] and not risk.get("circuit_breaker_until"):
        until = (datetime.now() + timedelta(hours=24)).isoformat()
        risk["circuit_breaker_until"] = until
        msg = (f"🚨 *CIRCUIT BREAKER TRIPPED*\n"
               f"Strategy: `{sid}`\n"
               f"Drawdown: {dd_pct:.1f}% (max: {risk['max_drawdown_pct']}%)\n"
               f"Peak: ${peak:,.2f} → Now: ${current_value:,.2f}\n"
               f"Paused 24h until: {until[:16]}")
        log.warning(f"[{sid}] CIRCUIT BREAKER → {until}")
        send_critical("trading-circuit-breaker", msg)
        post_feed(f"Circuit Breaker: {sid}", msg, "error")

def check_consecutive_losses(sid: str, st: dict):
    if st["consecutive_losses"] >= 5:
        risk = st["risk_state"]
        if not risk.get("short_pause_until"):
            until = (datetime.now() + timedelta(hours=1)).isoformat()
            risk["short_pause_until"] = until
            msg = (f"⚠️ *5 CONSECUTIVE LOSSES*\n"
                   f"Strategy: `{sid}`\nCooling off 1h until {until[:16]}")
            log.warning(f"[{sid}] 5 consecutive losses → 1h pause")
            send_critical("trading-circuit-breaker", msg)

# ── Signal functions (stateless, return 'buy'/'sell'/'hold') ──────────────────
def signal_momentum(symbol: str) -> str:
    """ROC momentum with VWAP confirmation (v3.2).
    Entry: ROC > 2% AND price above VWAP (institutional flow confirms).
    Exit:  ROC < -2% OR price drops back below VWAP (early exit).
    """
    bars = get_bars(symbol, limit=25)
    if len(bars) < 21:
        log.info(f"[momentum/{symbol}] Not enough bars ({len(bars)}), hold")
        return "hold"
    closes = [b["c"] for b in bars]
    roc    = (closes[-1] - closes[-21]) / closes[-21] * 100
    vwap   = calc_vwap(bars)
    price  = closes[-1]
    log.info(f"[momentum/{symbol}] ROC={roc:.2f}% price={price:.2f} VWAP={vwap:.2f}")
    if roc > 2.0 and price > vwap:
        return "buy"                          # momentum + VWAP confirm
    if roc < -2.0 or (roc < 0 and price < vwap):
        return "sell"                         # reversal or VWAP loss
    return "hold"

def signal_rsi(symbol: str, period=14) -> str:
    bars = get_bars(symbol, limit=period + 5)
    if len(bars) < period + 1:
        log.info(f"[rsi/{symbol}] Not enough bars ({len(bars)}), hold")
        return "hold"
    closes = [b["c"] for b in bars]
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return "hold"
    rsi = 100 - (100 / (1 + avg_gain / avg_loss))
    log.info(f"[rsi/{symbol}] RSI={rsi:.1f}")
    if rsi < 35: return "buy"
    if rsi > 65: return "sell"
    return "hold"

def signal_macd(symbol: str) -> str:
    bars = get_bars(symbol, limit=60)
    if len(bars) < 35:
        log.info(f"[macd/{symbol}] Not enough bars ({len(bars)}), hold")
        return "hold"
    closes = [b["c"] for b in bars]
    def ema(data, period):
        k = 2 / (period + 1)
        r = [data[0]]
        for v in data[1:]:
            r.append(v * k + r[-1] * (1 - k))
        return r
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)
    prev_cross = macd_line[-2] - signal_line[-2]
    curr_cross = macd_line[-1] - signal_line[-1]
    log.info(f"[macd/{symbol}] MACD={macd_line[-1]:.4f} Sig={signal_line[-1]:.4f}")
    if prev_cross < 0 and curr_cross > 0: return "buy"
    if prev_cross > 0 and curr_cross < 0: return "sell"
    return "hold"

def signal_mean_revert(symbol: str, period=20) -> str:
    bars = get_bars(symbol, limit=period + 5)
    if len(bars) < period:
        log.info(f"[mean_revert/{symbol}] Not enough bars ({len(bars)}), hold")
        return "hold"
    closes = [b["c"] for b in bars[-period:]]
    mean = sum(closes) / len(closes)
    std = (sum((c - mean)**2 for c in closes) / len(closes)) ** 0.5
    upper = mean + 2 * std
    lower = mean - 2 * std
    price = closes[-1]
    log.info(f"[mean_revert/{symbol}] price={price:.2f} lower={lower:.2f} upper={upper:.2f}")
    if price < lower: return "buy"
    if price > upper: return "sell"
    return "hold"

def signal_orb(symbol: str) -> str:
    now = datetime.utcnow()
    # ORB window: 13:30–14:00 UTC (9:30–10:00 AM EST)
    in_window = (now.hour == 13 and now.minute >= 30) or (now.hour == 14 and now.minute < 1)
    if not in_window:
        log.info(f"[orb/{symbol}] Outside ORB window, hold")
        return "hold"
    bars = get_bars(symbol, timeframe="15Min", limit=10)
    if len(bars) < 3:
        log.info(f"[orb/{symbol}] Not enough 15m bars, hold")
        return "hold"
    orh = max(b["h"] for b in bars[:2])
    orl = min(b["l"] for b in bars[:2])
    current = bars[-1]["c"]
    log.info(f"[orb/{symbol}] ORH={orh:.2f} ORL={orl:.2f} cur={current:.2f}")
    if current > orh: return "buy"
    if current < orl: return "sell"
    return "hold"

SIGNAL_MAP = {
    "momentum":   signal_momentum,
    "rsi":        signal_rsi,
    "macd":       signal_macd,
    "mean_revert": signal_mean_revert,
    "orb":        signal_orb,
}

# ── Execution ─────────────────────────────────────────────────────────────────
def execute_strategy(s: dict, st: dict):
    sid     = s["id"]
    symbol  = s["symbol"]
    capital = st["initial_capital"]
    cash    = st["cash"]
    pos     = st.get("position")
    risk    = st["risk_state"]

    price = get_latest_price(symbol)
    if not price:
        log.warning(f"[{sid}] No price available, skipping")
        return

    current_value = cash + (pos["qty"] * price if pos else 0)
    st["portfolio_value"] = round(current_value, 2)
    st["pnl"]     = round(current_value - capital, 2)
    st["pnl_pct"] = round(((current_value - capital) / capital) * 100, 2)

    check_circuit_breaker(sid, st, current_value)
    if is_circuit_broken(sid, risk):
        log.info(f"[{sid}] Circuit breaker active, skip")
        return
    if is_short_paused(sid, risk):
        log.info(f"[{sid}] Short pause active, skip")
        return


    # ── ADX gate: skip new entries in choppy/trending-down markets ────────
    if not pos:
        adx_bars = get_bars(symbol, limit=ADX_BAR_LIMIT)
        adx_val  = calc_adx(adx_bars)
        log.info(f"[{sid}] ADX={adx_val:.1f} (threshold={ADX_THRESHOLD})")
        if adx_val < ADX_THRESHOLD:
            log.info(f"[{sid}] ADX too low ({adx_val:.1f}) — market choppy, skip entry")
            return

    # ── ATR stop: exit open position if price drops below ATR stop ────────
    if pos:
        atr_bars  = get_bars(symbol, limit=ADX_BAR_LIMIT)
        atr_val   = calc_atr(atr_bars)
        atr_stop  = pos["avg_price"] - ATR_STOP_MULT * atr_val
        if atr_val > 0 and price <= atr_stop:
            qty    = pos["qty"]
            result = place_order(symbol, "sell", qty, sid)
            if result.get("id"):
                trade_pnl = (price - pos["avg_price"]) * qty
                st["consecutive_losses"] += 1
                check_consecutive_losses(sid, st)
                st["position"] = None
                st["cash"]     = round(cash + qty * price, 2)
                st["trade_count"] += 1
                log.warning(f"[{sid}] ATR STOP HIT @ ${price:.2f} "
                            f"(stop=${atr_stop:.2f} atr=${atr_val:.2f}) "
                            f"PnL=${trade_pnl:+.2f}")
                post_feed(f"ATR STOP {symbol}",
                          f"ATR stop hit: {symbol} @ ${price:.2f} | PnL=${trade_pnl:+.2f}",
                          "warning")
            return

    signal_fn = SIGNAL_MAP.get(s["fn"])
    if not signal_fn:
        return

    try:
        signal = signal_fn(symbol)
    except Exception as e:
        log.error(f"[{sid}] Signal error: {e}")
        return

    log.info(f"[{sid}] signal={signal} value=${current_value:.2f} pnl={st['pnl_pct']:+.1f}%")

    if signal == "buy" and not pos and cash >= 200:
        qty = round((cash * 0.95) / price, 4)
        if qty < 0.001:
            return
        result = place_order(symbol, "buy", qty, sid)
        if result.get("id"):
            st["position"] = {"symbol": symbol, "qty": qty, "avg_price": price, "entry_time": datetime.now().isoformat()}
            st["cash"] = round(cash - qty * price, 2)
            st["trade_count"] += 1
            msg = f"📈 *BUY* `{symbol}` x{qty} @ ${price:.2f}\nStrategy: `{sid}`"
            telegram(msg)
            post_feed(f"BUY {symbol}", msg, "success")

    elif signal == "sell" and pos:
        qty = pos["qty"]
        result = place_order(symbol, "sell", qty, sid)
        if result.get("id"):
            trade_pnl = (price - pos["avg_price"]) * qty
            if trade_pnl > 0:
                st["win_count"] += 1
                st["consecutive_losses"] = 0
            else:
                st["consecutive_losses"] += 1
                check_consecutive_losses(sid, st)
            st["position"] = None
            st["cash"] = round(cash + qty * price, 2)
            st["trade_count"] += 1
            msg = (f"📉 *SELL* `{symbol}` x{qty} @ ${price:.2f}\n"
                   f"Strategy: `{sid}` | Trade PnL: ${trade_pnl:+.2f}\n"
                   f"Consecutive losses: {st['consecutive_losses']}")
            telegram(msg)
            post_feed(f"SELL {symbol}", msg, "success")

# ── Status ────────────────────────────────────────────────────────────────────
def print_status(state: dict, cycle: int):
    acct = get_account()
    total_capital = sum(st.get("initial_capital", 0) for k, st in state.items()
                        if k != "_meta" and isinstance(st, dict))
    total_value   = sum(st.get("portfolio_value", 0) for k, st in state.items()
                        if k != "_meta" and isinstance(st, dict))
    total_pnl     = total_value - total_capital
    cb_count = sum(1 for k, st in state.items()
                   if k != "_meta" and isinstance(st, dict)
                   and is_circuit_broken(k, st.get("risk_state", {})))

    log.info("=" * 60)
    log.info(f"PENELOPE v3 — Cycle {cycle} | Alpaca: ${float(acct.get('portfolio_value',0)):,.2f}")
    log.info(f"Engine PnL: ${total_pnl:+,.2f} | CB active: {cb_count}")
    log.info("-" * 60)
    ranked = sorted(
        [(k, st) for k, st in state.items() if k != "_meta" and isinstance(st, dict)],
        key=lambda x: x[1].get("pnl_pct", 0), reverse=True
    )
    for sid, st in ranked:
        cb = "🔴" if is_circuit_broken(sid, st.get("risk_state", {})) else ""
        sp = "⏸" if is_short_paused(sid, st.get("risk_state", {})) else ""
        log.info(f"  {sid}: {st.get('pnl_pct',0):+.2f}% | "
                 f"trades={st.get('trade_count',0)} wins={st.get('win_count',0)} "
                 f"losses={st.get('consecutive_losses',0)} {cb}{sp}")
    log.info("=" * 60)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("PENELOPE TRADING ENGINE v3.1 STARTING")
    acct = get_account()
    if not acct.get("id"):
        log.error("ALPACA CONNECTION FAILED")
        telegram("🚨 Trading Engine v3: Alpaca connection FAILED", force=True)
        return

    equity = float(acct.get("portfolio_value", 0))
    log.info(f"Alpaca OK — Paper equity: ${equity:,.2f}")
    telegram(
        f"🚀 *PENELOPE TRADING ENGINE v3.1 ONLINE*\n"
        f"Paper equity: ${equity:,.2f}\n"
        f"Strategies: {len(STRATEGIES)}\n"
        f"Fixes: bars-null guard, single log handler, snapshot price fallback",
        force=True
    )

    state = load_state()
    if "_meta" not in state:
        state["_meta"] = {"cycle_count": 0, "started": datetime.now().isoformat()}

    post_feed("Engine v3.2 Online", f"Trading engine v3.2 started (ADX+ATR+VWAP). {len(STRATEGIES)} strategies.", "success")

    while True:
        cycle = state["_meta"]["cycle_count"]
        log.info(f"─── CYCLE {cycle} ───")

        market_open = is_market_open()
        log.info(f"Market open: {market_open}")

        for s in STRATEGIES:
            if s["fn"] == "orb" and not market_open:
                continue
            try:
                execute_strategy(s, state[s["id"]])
            except Exception as e:
                log.error(f"[{s['id']}] Unhandled error: {e}")
            time.sleep(1)

        state["_meta"]["cycle_count"] += 1
        save_state(state)
        print_status(state, cycle)

        # Hourly Telegram summary (every 12 cycles × 5min = 60min)
        if cycle > 0 and cycle % 12 == 0:
            total_cap = sum(st.get("initial_capital",0) for k,st in state.items() if k!="_meta" and isinstance(st,dict))
            total_val = sum(st.get("portfolio_value",0) for k,st in state.items() if k!="_meta" and isinstance(st,dict))
            pnl = total_val - total_cap
            pct = (pnl/total_cap*100) if total_cap else 0
            msg = f"📊 *TRADING ENGINE v3.1 HOURLY*\nPnL: ${pnl:+,.2f} ({pct:+.2f}%)\nCycle: {cycle}\n"
            telegram(msg)

        log.info(f"Cycle {cycle} complete. Sleeping 300s...")
        time.sleep(300)

if __name__ == "__main__":
    main()
