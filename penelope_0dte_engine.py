#!/usr/bin/env python3
"""
penelope_0dte_engine.py — Penelope 0DTE Options Engine
=======================================================
Research-backed same-day expiration options trading for SPY.

STRATEGY SUMMARY (from 230k+ trade analysis, Option Alpha + Alpaca research):
- Primary: Iron Condor (63% win rate, 94% held-to-expiry win rate)
- Secondary: Credit Spread — directional bias from 5-day SMA
- Underlying: SPY (88% of 0DTE volume, $0.01-0.03 bid-ask, daily expirations)
- Entry: 2+ hours AFTER open (avg 37% return vs morning entries)
- IVP gate: IVP > 50 (sell premium when IV is elevated)
- Short delta: 0.14–0.16 OTM (high probability of expiring worthless)
- Spread width: $2–$4 (balances premium vs capital at risk)
- Profit target: 50% of credit received
- Stop loss: 2× credit received (max loss = 2× max profit)
- Max risk per trade: 1–2% of portfolio
- Hard close: 3:45 PM ET (15 min before expiration — avoid gamma explosion)
- PDT rule: max 3 round-trips per 5 days on paper account < $25k

ALPACA API:
- Options contracts: GET /v1beta1/options/contracts/{symbol}
- Symbol format: SPY250414P00580000 (ticker + YYMMDD + C/P + 8-digit strike×1000)
- Multi-leg orders: POST /v2/orders with legs[] array (Level 3 required)
- Snapshots (greeks): GET /v1beta1/options/snapshots/{symbol}
"""

import os, time, json, sqlite3, logging
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
VAULT = {}
try:
    for line in open("/root/penelope_vault.env"):
        if "=" in line and not line.startswith("#"):
            k, _, v = line.strip().partition("=")
            VAULT[k.strip()] = v.strip()
except: pass

ALPACA_KEY    = VAULT.get("ALPACA_API_KEY", "")
ALPACA_SECRET = VAULT.get("ALPACA_SECRET_KEY", "")
PAPER_BASE    = "https://paper-api.alpaca.markets/v2"
DATA_BASE     = "https://data.alpaca.markets/v1beta1"

HEADERS = {
    "APCA-API-KEY-ID":     ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type":        "application/json",
}

# ── Strategy parameters (from 230k trade research) ────────────────────────────
UNDERLYING        = "SPY"
ENTRY_AFTER_MINS  = 120        # Enter 2h after open (9:30 + 2h = 11:30 AM ET)
CLOSE_BY_MINS     = 375        # Hard close at 3:45 PM ET (375 min after 9:30)
IVP_MIN           = 50         # Only sell premium when IVP > 50
SHORT_DELTA_MIN   = 0.12       # Short strike delta range
SHORT_DELTA_MAX   = 0.18
SPREAD_WIDTH      = 2.0        # $2 wide spreads
PROFIT_TARGET_PCT = 0.50       # Close at 50% of credit
STOP_LOSS_MULT    = 2.0        # Stop at 2× credit
MAX_RISK_PCT      = 0.015      # 1.5% of portfolio per trade
MAX_TRADES_DAY    = 1          # 1 iron condor per day (PDT protection)
CYCLE_SECS        = 300        # Check every 5 minutes

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH = Path("/root/workspace/Penelope/trading_bot/0dte_engine.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [0DTE] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH)),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ── Persistent ledger ─────────────────────────────────────────────────────────
DB_PATH = Path("/root/workspace/Penelope/trading_bot/0dte_ledger.db")

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS trades (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        date         TEXT,
        strategy     TEXT,
        symbol       TEXT,
        legs         TEXT,
        credit       REAL,
        close_price  REAL,
        pnl_usd      REAL,
        pnl_pct      REAL,
        exit_reason  TEXT,
        opened_at    TEXT,
        closed_at    TEXT
    )""")
    conn.commit()
    conn.close()

def log_trade(strategy, symbol, legs, credit, close_price,
              pnl_usd, exit_reason, opened_at):
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO trades VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)",
        (date.today().isoformat(), strategy, symbol, json.dumps(legs),
         credit, close_price, pnl_usd,
         round(pnl_usd / max(credit * 100, 0.01), 4),
         exit_reason, opened_at,
         datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
    log.info(f"Ledger: {strategy} {exit_reason} P/L=${pnl_usd:+.2f}")

# ── Alpaca helpers ────────────────────────────────────────────────────────────
import requests

def alpaca_get(path, params=None, base=DATA_BASE):
    try:
        r = requests.get(f"{base}{path}", headers=HEADERS,
                         params=params or {}, timeout=10)
        if r.status_code == 200:
            return r.json()
        log.warning(f"GET {path}: {r.status_code} {r.text[:100]}")
    except Exception as e:
        log.error(f"GET {path} error: {e}")
    return {}

def alpaca_post(path, body):
    try:
        r = requests.post(f"{PAPER_BASE}{path}", headers=HEADERS,
                          json=body, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
        log.warning(f"POST {path}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log.error(f"POST {path} error: {e}")
    return {}

def get_account():
    return alpaca_get("/account", base=PAPER_BASE)

def get_clock():
    return alpaca_get("/clock", base=PAPER_BASE)

# ── Market timing ─────────────────────────────────────────────────────────────
def market_open_minutes():
    """Minutes elapsed since 9:30 AM ET today."""
    now_et = datetime.now(timezone(timedelta(hours=-4)))  # EDT
    open_et = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    delta = (now_et - open_et).total_seconds() / 60
    return delta

def is_entry_window():
    """Between 11:30 AM and 3:45 PM ET."""
    mins = market_open_minutes()
    return ENTRY_AFTER_MINS <= mins <= CLOSE_BY_MINS

def is_close_time():
    """After 3:45 PM ET — hard close all positions."""
    return market_open_minutes() >= CLOSE_BY_MINS

# ── Options chain ─────────────────────────────────────────────────────────────
def get_0dte_chain():
    """Fetch today's SPY options contracts from Alpaca."""
    today = date.today().isoformat()
    data = alpaca_get(f"/options/contracts/{UNDERLYING}", {
        "expiration_date_gte": today,
        "expiration_date_lte": today,
        "limit": 200,
    })
    return data.get("option_contracts", [])

def get_snapshots(symbols: list):
    """Fetch Greeks + quotes for a list of option symbols."""
    if not symbols:
        return {}
    data = alpaca_get(f"/options/snapshots/{UNDERLYING}", {
        "symbols": ",".join(symbols[:50]),
    })
    return data.get("snapshots", {})

def get_spy_price():
    """Latest SPY price from Alpaca."""
    d = alpaca_get(f"/stocks/{UNDERLYING}/quotes/latest",
                   base="https://data.alpaca.markets/v2")
    q = d.get("quote", {})
    return (q.get("ap", 0) + q.get("bp", 0)) / 2 or 0

def calc_ivp_proxy(chain):
    """
    Proxy IV percentile using ATM IV vs OTM IV spread.
    Real IVP requires historical data — this is a same-day estimate.
    Returns 0–100 score.
    """
    ivs = []
    for c in chain:
        iv = c.get("implied_volatility") or c.get("iv", 0)
        if iv and 0.05 < float(iv) < 3.0:
            ivs.append(float(iv))
    if not ivs:
        return 60  # Default to above threshold — proceed
    avg_iv = sum(ivs) / len(ivs)
    # Rough percentile: normalize against typical SPY IV range 10%–60%
    return min(100, max(0, (avg_iv - 0.10) / 0.50 * 100))

# ── Strike selection ──────────────────────────────────────────────────────────
def select_iron_condor_legs(chain, spot_price, snapshots):
    """
    Select 4 legs for iron condor:
    - Short put: delta ~0.15 OTM put
    - Long put:  short_put_strike - SPREAD_WIDTH
    - Short call: delta ~0.15 OTM call
    - Long call: short_call_strike + SPREAD_WIDTH

    Returns dict with leg symbols or None if no valid setup found.
    """
    puts  = [c for c in chain if c.get("type") == "put"
             and float(c.get("strike_price", 0)) < spot_price]
    calls = [c for c in chain if c.get("type") == "call"
             and float(c.get("strike_price", 0)) > spot_price]

    if not puts or not calls:
        log.warning("No puts or calls found in chain")
        return None

    # Sort by proximity to target delta
    short_put  = _find_by_delta(puts, snapshots, target=0.15, option_type="put")
    short_call = _find_by_delta(calls, snapshots, target=0.15, option_type="call")

    if not short_put or not short_call:
        log.warning("Could not find target-delta strikes")
        return None

    sp_strike = float(short_put["strike_price"])
    sc_strike = float(short_call["strike_price"])

    # Find protective wings
    long_put  = _find_strike(puts, sp_strike - SPREAD_WIDTH, "put")
    long_call = _find_strike(calls, sc_strike + SPREAD_WIDTH, "call")

    if not long_put or not long_call:
        log.warning("Could not find wing strikes")
        return None

    return {
        "short_put":  short_put["symbol"],
        "long_put":   long_put["symbol"],
        "short_call": short_call["symbol"],
        "long_call":  long_call["symbol"],
        "sp_strike":  sp_strike,
        "sc_strike":  sc_strike,
        "lp_strike":  float(long_put["strike_price"]),
        "lc_strike":  float(long_call["strike_price"]),
    }

def _find_by_delta(contracts, snapshots, target, option_type):
    best, best_diff = None, 999
    for c in contracts:
        sym   = c.get("symbol", "")
        snap  = snapshots.get(sym, {})
        greeks = snap.get("greeks", {})
        delta  = greeks.get("delta", None)
        if delta is None:
            continue
        delta = abs(float(delta))
        diff  = abs(delta - target)
        if SHORT_DELTA_MIN <= delta <= SHORT_DELTA_MAX and diff < best_diff:
            best, best_diff = c, diff
    return best

def _find_strike(contracts, target_strike, option_type):
    best, best_diff = None, 999
    for c in contracts:
        s    = float(c.get("strike_price", 0))
        diff = abs(s - target_strike)
        if diff < best_diff:
            best, best_diff = c, diff
    return best if best_diff <= 1.0 else None

# ── Credit calculation ────────────────────────────────────────────────────────
def calc_net_credit(legs, snapshots):
    """
    Net credit = (short_put mid + short_call mid)
               - (long_put mid  + long_call mid)
    """
    def mid(sym):
        snap  = snapshots.get(sym, {})
        quote = snap.get("latestQuote", snap.get("latestTrade", {}))
        bp    = float(quote.get("bp", quote.get("p", 0)) or 0)
        ap    = float(quote.get("ap", quote.get("p", 0)) or 0)
        return (bp + ap) / 2 if bp and ap else 0

    credit = (mid(legs["short_put"])  + mid(legs["short_call"])
            - mid(legs["long_put"])   - mid(legs["long_call"]))
    return round(credit, 4)

# ── Order execution ───────────────────────────────────────────────────────────
def place_iron_condor(legs, credit, qty=1):
    """
    Submit multi-leg iron condor order via Alpaca Level 3 API.
    """
    order = {
        "type":         "limit",
        "time_in_force": "day",
        "order_class":  "mleg",
        "qty":          str(qty),
        "limit_price":  str(round(credit * 0.95, 2)),  # Slight discount for fill
        "legs": [
            {"symbol": legs["short_put"],  "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_open"},
            {"symbol": legs["long_put"],   "side": "buy",  "ratio_qty": "1",
             "position_intent": "buy_to_open"},
            {"symbol": legs["short_call"], "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_open"},
            {"symbol": legs["long_call"],  "side": "buy",  "ratio_qty": "1",
             "position_intent": "buy_to_open"},
        ]
    }
    result = alpaca_post("/orders", order)
    return result

def close_position(legs, qty=1):
    """Close iron condor by buying back all legs."""
    order = {
        "type":         "market",
        "time_in_force": "day",
        "order_class":  "mleg",
        "qty":          str(qty),
        "legs": [
            {"symbol": legs["short_put"],  "side": "buy",  "ratio_qty": "1",
             "position_intent": "buy_to_close"},
            {"symbol": legs["long_put"],   "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_close"},
            {"symbol": legs["short_call"], "side": "buy",  "ratio_qty": "1",
             "position_intent": "buy_to_close"},
            {"symbol": legs["long_call"],  "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_close"},
        ]
    }
    return alpaca_post("/orders", order)

# ── Daily state ───────────────────────────────────────────────────────────────
STATE_FILE = Path("/root/workspace/Penelope/trading_bot/0dte_state.json")

def load_state():
    today = date.today().isoformat()
    if STATE_FILE.exists():
        s = json.loads(STATE_FILE.read_text())
        if s.get("date") == today:
            return s
    return {"date": today, "trades_today": 0, "open_position": None}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))

# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    log.info("=== 0DTE Options Engine LIVE ===")
    log.info(f"Strategy: SPY Iron Condor | Entry after 11:30 AM ET | Close by 3:45 PM ET")
    log.info(f"Params: delta={SHORT_DELTA_MIN}-{SHORT_DELTA_MAX} | width=${SPREAD_WIDTH} | "
             f"target={int(PROFIT_TARGET_PCT*100)}% | stop={STOP_LOSS_MULT}x")
    init_db()

    while True:
        try:
            clock = get_clock()
            if not clock.get("is_open"):
                next_open = clock.get("next_open", "?")
                log.info(f"Market closed. Next open: {next_open}")
                time.sleep(600)
                continue

            state = load_state()
            mins  = market_open_minutes()
            acct  = get_account()
            equity = float(acct.get("equity", 100000))

            log.info(f"Market open {mins:.0f}min | equity=${equity:,.2f} | "
                     f"trades_today={state['trades_today']} | "
                     f"position={'OPEN' if state['open_position'] else 'flat'}")

            # ── Hard close at 3:45 PM ─────────────────────────────────────
            if is_close_time() and state["open_position"]:
                log.info("3:45 PM hard close — closing all 0DTE positions")
                result = close_position(state["open_position"]["legs"])
                close_price = state["open_position"].get("current_price", 0)
                credit      = state["open_position"]["credit"]
                pnl         = (credit - close_price) * 100
                log_trade("iron_condor_0dte", UNDERLYING,
                          state["open_position"]["legs"],
                          credit, close_price, pnl,
                          "TIME_EXIT_345PM",
                          state["open_position"]["opened_at"])
                state["open_position"] = None
                save_state(state)
                log.info(f"Position closed — P/L ${pnl:+.2f}")
                time.sleep(CYCLE_SECS)
                continue

            # ── Monitor open position ─────────────────────────────────────
            if state["open_position"]:
                pos       = state["open_position"]
                credit    = pos["credit"]
                opened_at = pos["opened_at"]
                legs      = pos["legs"]

                # Get current value of all 4 legs
                all_syms  = list(legs.values())
                snaps     = get_snapshots(all_syms)
                curr_cost = calc_net_credit(legs, snaps)  # Current cost to close

                pnl_pct = (credit - curr_cost) / credit if credit > 0 else 0

                log.info(f"Position: credit=${credit:.4f} | "
                         f"current=${curr_cost:.4f} | "
                         f"P/L={pnl_pct*100:+.1f}%")

                # Profit target: 50% of credit
                if pnl_pct >= PROFIT_TARGET_PCT:
                    log.info(f"PROFIT TARGET HIT {pnl_pct*100:.1f}% — closing")
                    close_position(legs)
                    pnl = (credit - curr_cost) * 100
                    log_trade("iron_condor_0dte", UNDERLYING, legs,
                              credit, curr_cost, pnl, "PROFIT_TARGET_50PCT", opened_at)
                    state["open_position"] = None
                    save_state(state)
                    time.sleep(CYCLE_SECS)
                    continue

                # Stop loss: 2× credit
                if curr_cost >= credit * (1 + STOP_LOSS_MULT):
                    log.warning(f"STOP LOSS HIT {pnl_pct*100:.1f}% — closing")
                    close_position(legs)
                    pnl = (credit - curr_cost) * 100
                    log_trade("iron_condor_0dte", UNDERLYING, legs,
                              credit, curr_cost, pnl, "STOP_LOSS_2X", opened_at)
                    state["open_position"] = None
                    save_state(state)
                    time.sleep(CYCLE_SECS)
                    continue

                # Update current price in state
                state["open_position"]["current_price"] = curr_cost
                save_state(state)
                time.sleep(CYCLE_SECS)
                continue

            # ── Entry logic ───────────────────────────────────────────────
            if not is_entry_window():
                log.info(f"Not in entry window yet ({mins:.0f}min / need {ENTRY_AFTER_MINS}min)")
                time.sleep(CYCLE_SECS)
                continue

            if state["trades_today"] >= MAX_TRADES_DAY:
                log.info("Max trades for today reached")
                time.sleep(CYCLE_SECS)
                continue

            # Fetch chain
            chain = get_0dte_chain()
            if not chain:
                log.warning("No 0DTE chain available — market may not be open yet or API issue")
                time.sleep(CYCLE_SECS)
                continue

            # IVP gate
            ivp = calc_ivp_proxy(chain)
            log.info(f"IVP proxy: {ivp:.1f} (need >{IVP_MIN})")
            if ivp < IVP_MIN:
                log.info("IVP too low — not ideal for premium selling, skipping")
                time.sleep(CYCLE_SECS)
                continue

            # Get spot + snapshots
            spot = get_spy_price()
            if not spot:
                log.warning("Could not get SPY spot price")
                time.sleep(CYCLE_SECS)
                continue

            log.info(f"SPY spot: ${spot:.2f} | Chain: {len(chain)} contracts")
            syms  = [c["symbol"] for c in chain]
            snaps = get_snapshots(syms)

            # Select legs
            legs = select_iron_condor_legs(chain, spot, snaps)
            if not legs:
                log.warning("No valid iron condor setup found")
                time.sleep(CYCLE_SECS)
                continue

            # Calculate credit
            credit = calc_net_credit(legs, snaps)
            if credit <= 0.10:
                log.warning(f"Credit too low (${credit:.4f}) — skipping")
                time.sleep(CYCLE_SECS)
                continue

            # Position sizing: max 1.5% of equity at risk
            max_risk   = equity * MAX_RISK_PCT
            spread_risk = (SPREAD_WIDTH - credit) * 100  # Max loss per contract
            qty        = max(1, int(max_risk / spread_risk)) if spread_risk > 0 else 1
            qty        = min(qty, 5)  # Cap at 5 contracts paper trading

            log.info(f"ENTRY: SP={legs['sp_strike']} SC={legs['sc_strike']} "
                     f"LP={legs['lp_strike']} LC={legs['lc_strike']} "
                     f"credit=${credit:.4f} qty={qty}")

            # Place order
            result = place_iron_condor(legs, credit, qty)
            if result.get("id"):
                log.info(f"✅ Order placed: {result['id']} | "
                         f"target=${credit*PROFIT_TARGET_PCT:.4f} | "
                         f"stop=${credit*(1+STOP_LOSS_MULT):.4f}")
                state["open_position"] = {
                    "order_id":     result["id"],
                    "legs":         legs,
                    "credit":       credit,
                    "qty":          qty,
                    "current_price": credit,
                    "opened_at":    datetime.now(timezone.utc).isoformat(),
                }
                state["trades_today"] += 1
                save_state(state)
            else:
                log.warning(f"Order failed: {result}")

        except Exception as e:
            log.error(f"Cycle error: {e}", exc_info=True)

        time.sleep(CYCLE_SECS)

if __name__ == "__main__":
    run()
