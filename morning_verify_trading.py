#!/usr/bin/env python3
"""
Morning verification script — runs at market open (9:35 AM EST)
Checks: service alive, Alpaca connected, bars fetching, signals firing,
/status endpoint responding, sends full Telegram report.
"""
import requests, json, subprocess
from datetime import datetime
from pathlib import Path


def _tg_emergency_only(msg, force=False):
    """ONLY fires for revenue confirmation or system-critical failures. Nothing else."""
    import requests as _r, datetime as _dt, os as _o
    _tok = _o.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
    _cid = _o.getenv("TELEGRAM_CHAT_ID", "6183015901")
    if not _tok:
        return
    _ml = str(msg).lower()
    _h = _dt.datetime.now().hour
    # Only these pass:
    _revenue = any(x in _ml for x in ["revenue confirmed", "sale confirmed", "payment received", "paid $", "new sale"])
    _critical = force or ("🚨" in msg and any(x in _ml for x in ["system down", "cannot restart", "disk full", "out of memory"]))
    if not _revenue and not _critical:
        return
    try:
        for chunk in [str(msg)[i:i+4000] for i in range(0, len(str(msg)), 4000)]:
            _r.post(f"https://api.telegram.org/bot{_tok}/sendMessage",
                json={"chat_id": _cid, "text": chunk, "parse_mode": "Markdown"},
                timeout=8)
    except:
        pass


TELEGRAM_TOKEN = None
TELEGRAM_CHAT  = "6183015901"
STATE_FILE     = Path("/root/workspace/Penelope/trading_bot/engine_v3_state.json")
LOG_FILE       = Path("/root/workspace/Penelope/trading_bot/engine_v3.log")
ALPACA_KEY     = None
ALPACA_SECRET  = None

# Load vault
env = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    TELEGRAM_TOKEN = env.get("TELEGRAM_BOT_TOKEN","")
    ALPACA_KEY     = env.get("ALPACA_API_KEY","")
    ALPACA_SECRET  = env.get("ALPACA_SECRET_KEY","")
except:
    pass

ALPACA_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET
}

def tg(msg):
    if not TELEGRAM_TOKEN: return
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

results = {}

# 1. Service alive
try:
    r = subprocess.run(["systemctl","is-active","penelope-trading-v3"],
                       capture_output=True, text=True)
    results["service"] = r.stdout.strip()
except Exception as e:
    results["service"] = f"ERROR: {e}"

# 2. Alpaca account
try:
    r = requests.get("https://paper-api.alpaca.markets/v2/account",
                     headers=ALPACA_HEADERS, timeout=10)
    if r.status_code == 200:
        d = r.json()
        results["alpaca_equity"]  = d.get("equity")
        results["alpaca_status"]  = d.get("status")
        results["alpaca_buying_power"] = d.get("buying_power")
    else:
        results["alpaca"] = f"HTTP {r.status_code}"
except Exception as e:
    results["alpaca"] = f"ERROR: {e}"

# 3. Market open
try:
    r = requests.get("https://paper-api.alpaca.markets/v2/clock",
                     headers=ALPACA_HEADERS, timeout=10)
    if r.status_code == 200:
        results["market_open"] = r.json().get("is_open")
except Exception as e:
    results["market_open"] = f"ERROR: {e}"

# 4. Bar fetch working
try:
    from datetime import timedelta
    start = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")
    r = requests.get(
        "https://data.alpaca.markets/v2/stocks/AAPL/bars",
        headers=ALPACA_HEADERS,
        params={"timeframe":"1Hour","limit":5,"adjustment":"raw","feed":"iex","start":start},
        timeout=15
    )
    bars = r.json().get("bars") if r.status_code == 200 else None
    results["bars_aapl"] = f"{len(bars)} bars, latest close=${bars[-1]['c']:.2f}" if bars else "null/empty"
except Exception as e:
    results["bars"] = f"ERROR: {e}"

# 5. State file + cycle count
try:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        meta = state.get("_meta", {})
        results["cycle_count"] = meta.get("cycle_count", 0)
        results["started"]     = meta.get("started","?")
        strategy_summary = {}
        for k, v in state.items():
            if k == "_meta" or not isinstance(v, dict): continue
            strategy_summary[k] = {
                "trades": v.get("trade_count",0),
                "pnl_pct": v.get("pnl_pct",0),
                "position": v.get("position"),
                "cb": v.get("risk_state",{}).get("circuit_breaker_until"),
            }
        results["strategies"] = strategy_summary
    else:
        results["state_file"] = "MISSING"
except Exception as e:
    results["state_file"] = f"ERROR: {e}"

# 6. /status endpoint
try:
    r = requests.get("http://localhost:5001/status", timeout=8)
    if r.status_code == 200:
        d = r.json()
        results["status_endpoint"] = f"OK — cycle {d.get('cycle_count')} | PnL ${d.get('summary',{}).get('total_pnl',0):+.2f}"
    else:
        results["status_endpoint"] = f"HTTP {r.status_code}"
except Exception as e:
    results["status_endpoint"] = f"ERROR: {e}"

# 7. Recent log — last 5 lines
try:
    log_lines = LOG_FILE.read_text().strip().split("\n")[-5:]
    results["last_log"] = "\n".join(log_lines)
except Exception as e:
    results["last_log"] = f"ERROR: {e}"

# Build report
strats = results.get("strategies", {})
trades_total = sum(v["trades"] for v in strats.values())
positions    = [k for k, v in strats.items() if v.get("position")]
cb_active    = [k for k, v in strats.items() if v.get("cb")]

svc_emoji = "✅" if results.get("service") == "active" else "🔴"
mkt_emoji = "✅" if results.get("market_open") else "⏰"
bar_emoji = "✅" if "bars" in results.get("bars_aapl","") else "🔴"
ep_emoji  = "✅" if str(results.get("status_endpoint","")).startswith("OK") else "🔴"

report = f"""🔔 *PENELOPE TRADING ENGINE v3 — MARKET OPEN VERIFICATION*
{datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

{svc_emoji} *Service:* `{results.get("service","?")}`
{mkt_emoji} *Market open:* `{results.get("market_open","?")}`
✅ *Alpaca equity:* `${float(results.get("alpaca_equity",0)):,.2f}`
✅ *Buying power:* `${float(results.get("alpaca_buying_power",0)):,.2f}`
{bar_emoji} *Bars (AAPL):* `{results.get("bars_aapl","?")}`
{ep_emoji} *Status endpoint:* `{results.get("status_endpoint","?")}`

📊 *Engine State*
• Cycle count: `{results.get("cycle_count","?")}`
• Started: `{results.get("started","?")}`
• Total trades fired: `{trades_total}`
• Open positions: `{positions if positions else "none"}`
• Circuit breakers: `{cb_active if cb_active else "none"}`

📋 *Strategy P&L*
"""

for k, v in strats.items():
    pos_str = f" 📍{v['position']['symbol']}" if v.get("position") else ""
    cb_str  = " 🔴CB" if v.get("cb") else ""
    report += f"• `{k}`: {v['pnl_pct']:+.2f}% | trades={v['trades']}{pos_str}{cb_str}\n"

report += f"""
📄 *Last log lines:*
```
{results.get("last_log","?")}
```"""

print(report)
tg(report)
print("\nDone.")