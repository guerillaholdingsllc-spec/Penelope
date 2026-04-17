import os, json, time, requests, datetime
from google import genai


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


# ── Vault loader ──────────────────────────────────────────────────────────────
def _load_vault():
    env = {}
    try:
        for line in open("/root/penelope_vault.env"):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    except: pass
    return env
_VAULT = _load_vault()
import os as _os
for _k, _v in _VAULT.items():
    if _k not in _os.environ: _os.environ[_k] = _v



# ── ENV ───────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()

BASE           = "/root/workspace/Penelope"
FEED_FILE      = f"{BASE}/feed.json"
PM_DIR         = f"{BASE}/polymarket"
SIGNALS_FILE   = f"{PM_DIR}/signals.json"
WATCHLIST_FILE = f"{PM_DIR}/watchlist.json"

# ── POLYMARKET API ENDPOINTS (all free, no auth) ──────────────
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API  = "https://data-api.polymarket.com"
CLOB_API  = "https://clob.polymarket.com"

client = genai.Client(api_key=GOOGLE_API_KEY)
os.makedirs(PM_DIR, exist_ok=True)

def log(msg):
    print(f"[POLYMARKET {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def tg(msg):
    try:
        for chunk in [msg[i:i+4000] for i in range(0,len(msg),4000)]:
            _tg_emergency_only("[suppressed direct call]")
            time.sleep(0.3)
    except Exception as e: log(f"TG error: {e}")

def feed(title, content, status="info"):
    try:
        data = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE) as f: data = json.load(f)
        data.insert(0,{"id":int(time.time()),"title":title,"content":content,
                       "status":status,"agent":"PolymarketIntel",
                       "timestamp":datetime.datetime.now().isoformat()})
        with open(FEED_FILE,"w") as f: json.dump(data[:100],f,indent=2)
    except: pass

# ── API CALLS ─────────────────────────────────────────────────
def get_trending_markets(limit=20):
    """Get top trending markets by volume"""
    try:
        res = requests.get(f"{GAMMA_API}/markets",
            params={"limit":limit,"active":"true","closed":"false",
                    "order":"volume24hr","ascending":"false"},
            timeout=15)
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        log(f"Trending markets error: {e}")
        return []

def get_market_prices(condition_id):
    """Get current YES/NO prices for a market"""
    try:
        res = requests.get(f"{CLOB_API}/midpoints",
            params={"condition_id":condition_id}, timeout=10)
        if res.status_code == 200:
            return res.json()
        return {}
    except Exception as e:
        log(f"Price error: {e}")
        return {}

def get_top_traders(limit=10):
    """Get leaderboard of top profitable traders"""
    try:
        res = requests.get(f"{DATA_API}/leaderboard",
            params={"limit":limit,"window":"all_time",
                    "sortBy":"profit","order":"desc"},
            timeout=15)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        log(f"Leaderboard error: {e}")
        return []

def get_wallet_positions(wallet_address):
    """Get all current positions for a wallet"""
    try:
        res = requests.get(f"{DATA_API}/positions",
            params={"user":wallet_address,"sizeThreshold":10,"limit":50},
            timeout=15)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        log(f"Positions error: {e}")
        return []

def get_wallet_activity(wallet_address, limit=20):
    """Get recent trades for a wallet"""
    try:
        res = requests.get(f"{DATA_API}/activity",
            params={"user":wallet_address,"limit":limit,"type":"TRADE"},
            timeout=15)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        log(f"Activity error: {e}")
        return []

def get_market_by_slug(slug):
    """Get specific market data by slug"""
    try:
        res = requests.get(f"{GAMMA_API}/markets",
            params={"slug":slug}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data[0] if data else {}
        return {}
    except Exception as e:
        log(f"Market slug error: {e}")
        return {}

def search_markets(query):
    """Search markets by keyword"""
    try:
        res = requests.get(f"{GAMMA_API}/markets",
            params={"search":query,"active":"true","limit":10},
            timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except Exception as e:
        log(f"Search error: {e}")
        return []

# ── INTELLIGENCE ENGINE ───────────────────────────────────────
def analyze_markets_for_edge(markets):
    """Use Gemini to find mispriced markets with EV > 5%"""
    if not markets: return []

    market_data = []
    for m in markets[:15]:
        market_data.append({
            "title": m.get("question",""),
            "market_price_yes": m.get("outcomePrices",["0.5"])[0],
            "volume_24h": m.get("volume24hr",0),
            "liquidity": m.get("liquidity",0),
            "end_date": m.get("endDate",""),
            "slug": m.get("slug","")
        })

    prompt = f"""You are a calibrated prediction market analyst for Guerilla Holdings.

Analyze these Polymarket markets and find genuine mispricing opportunities.

MARKETS:
{json.dumps(market_data, indent=2)}

For each market:
1. Estimate the TRUE probability based on your knowledge of the topic
2. Compare to the current market price
3. Calculate Expected Value: EV = (true_prob - market_price) 
4. Only flag if |EV| > 0.05 (5% edge minimum)

Return a JSON array of opportunities:
[
  {{
    "title": "market title",
    "slug": "market-slug",
    "market_price": 0.XX,
    "true_probability": 0.XX,
    "ev": 0.XX,
    "direction": "YES" or "NO",
    "confidence": "high/medium/low",
    "reasoning": "why the market is mispriced in 1 sentence",
    "risk": "key risk to this position"
  }}
]

Only include markets where you have genuine conviction. Skip if uncertain.
Return valid JSON only, no explanation."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt)
        text = getattr(response,"text","[]").strip()
        text = text.replace("```json","").replace("```","").strip()
        signals = json.loads(text)
        return [s for s in signals if abs(s.get("ev",0)) > 0.05]
    except Exception as e:
        log(f"Analysis error: {e}")
        return []

def analyze_top_trader(wallet, positions, activity):
    """Analyze a top trader's current positions for copy signals"""
    prompt = f"""You are analyzing a top Polymarket trader for Guerilla Holdings.

WALLET: {wallet}
CURRENT POSITIONS: {json.dumps(positions[:10], indent=2)}
RECENT TRADES: {json.dumps(activity[:10], indent=2)}

Analyze:
1. What markets is this trader most active in?
2. What is their apparent strategy (sports/politics/crypto/macro)?
3. Which of their current positions look most promising to copy?
4. What is their average position size?
5. Any red flags or concerning patterns?

Return JSON:
{{
  "strategy": "description",
  "focus_categories": ["list"],
  "copy_signals": [
    {{
      "market": "title",
      "direction": "YES/NO",
      "current_price": 0.XX,
      "conviction": "high/medium/low",
      "reason": "why copy this"
    }}
  ],
  "avg_position_size": 0,
  "red_flags": ["list or empty"]
}}

Return valid JSON only."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt)
        text = getattr(response,"text","{}").strip()
        text = text.replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        log(f"Trader analysis error: {e}")
        return {}

# ── SAVE & LOAD WATCHLIST ─────────────────────────────────────
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE) as f: return json.load(f)
    # Default: top known wallets to watch
    return {
        "wallets": [],
        "markets": [],
        "min_ev": 0.05,
        "min_liquidity": 1000
    }

def save_signals(signals):
    with open(SIGNALS_FILE,"w") as f:
        json.dump({
            "signals": signals,
            "updated": datetime.datetime.now().isoformat(),
            "count": len(signals)
        }, f, indent=2)

# ── MAIN INTELLIGENCE RUN ─────────────────────────────────────
def run_polymarket_intel():
    log("="*50)
    log("POLYMARKET INTELLIGENCE SCAN STARTING")
    log("="*50)

    today = datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")
    all_signals = []

    # ── SCAN 1: Trending Markets for Mispricing ───────────────
    log("Scanning trending markets for edge...")
    markets = get_trending_markets(25)
    log(f"Found {len(markets)} trending markets")

    if markets:
        signals = analyze_markets_for_edge(markets)
        log(f"Found {len(signals)} signals with EV > 5%")
        all_signals.extend(signals)

    # ── SCAN 2: DEVVE-related markets (personal interest) ─────
    log("Searching DEVVE/crypto markets...")
    crypto_markets = search_markets("crypto")
    if crypto_markets:
        crypto_signals = analyze_markets_for_edge(crypto_markets[:10])
        all_signals.extend(crypto_signals)

    # ── SCAN 3: High volume political/macro markets ───────────
    log("Scanning political/macro markets...")
    macro_markets = search_markets("Federal Reserve interest rate")
    if macro_markets:
        macro_signals = analyze_markets_for_edge(macro_markets[:5])
        all_signals.extend(macro_signals)

    # ── SCAN 4: Top Trader Watchlist ──────────────────────────
    watchlist = load_watchlist()
    trader_signals = []

    for wallet in watchlist.get("wallets",[])[:5]:
        log(f"Analyzing wallet: {wallet[:10]}...")
        positions = get_wallet_positions(wallet)
        activity  = get_wallet_activity(wallet)
        if positions or activity:
            analysis = analyze_top_trader(wallet, positions, activity)
            for cs in analysis.get("copy_signals",[]):
                cs["source"] = f"wallet:{wallet[:10]}"
                trader_signals.append(cs)
        time.sleep(1)

    # ── DEDUPLICATE & RANK ────────────────────────────────────
    seen = set()
    unique_signals = []
    for s in all_signals:
        key = s.get("slug","") or s.get("title","")[:30]
        if key not in seen:
            seen.add(key)
            unique_signals.append(s)

    unique_signals.sort(key=lambda x: abs(x.get("ev",0)), reverse=True)
    save_signals(unique_signals)

    # ── FORMAT TELEGRAM REPORT ────────────────────────────────
    if unique_signals or trader_signals:
        msg = f"📊 *POLYMARKET INTELLIGENCE*\n{today}\n━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if unique_signals:
            msg += f"*🎯 EDGE SIGNALS ({len(unique_signals)} found)*\n\n"
            for s in unique_signals[:5]:
                ev_pct = abs(s.get('ev',0)) * 100
                direction = s.get('direction','YES')
                price = s.get('market_price',0)
                true_prob = s.get('true_probability',0)
                conf = s.get('confidence','medium')
                conf_emoji = {'high':'🔥','medium':'⚡','low':'💧'}.get(conf,'⚡')
                msg += f"{conf_emoji} *{s.get('title','')[:60]}*\n"
                msg += f"   Direction: {direction} | Price: {price:.0%} | True: {true_prob:.0%}\n"
                msg += f"   Edge: +{ev_pct:.1f}% | {s.get('reasoning','')[:80]}\n"
                msg += f"   Risk: _{s.get('risk','')[:60]}_\n\n"

        if trader_signals:
            msg += f"*👛 SMART WALLET SIGNALS ({len(trader_signals)} found)*\n\n"
            for s in trader_signals[:3]:
                msg += f"• *{s.get('market','')[:50]}*\n"
                msg += f"  {s.get('direction','')} @ {s.get('current_price',0):.0%} | {s.get('conviction','')} conviction\n"
                msg += f"  _{s.get('reason','')[:80]}_\n\n"

        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "_Intelligence only. Not financial advice. DYOR._\n"
        msg += "_— Penelope, Guerilla Holdings_"

        tg(msg)
        feed("Polymarket Intelligence Scan",
            f"{len(unique_signals)} edge signals found | {len(trader_signals)} wallet signals",
            "success")

        # Save full report to shipped/
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        report_path = f"{BASE}/shipped/{date_str}_polymarket_intel.md"
        with open(report_path,"w") as f:
            f.write(f"# Polymarket Intelligence Report\n")
            f.write(f"Date: {today}\n\n")
            f.write(f"## Edge Signals ({len(unique_signals)})\n\n")
            for s in unique_signals:
                f.write(f"### {s.get('title','')}\n")
                f.write(f"- Direction: {s.get('direction','')}\n")
                f.write(f"- Market Price: {s.get('market_price',0):.1%}\n")
                f.write(f"- True Probability: {s.get('true_probability',0):.1%}\n")
                f.write(f"- EV: +{abs(s.get('ev',0))*100:.1f}%\n")
                f.write(f"- Confidence: {s.get('confidence','')}\n")
                f.write(f"- Reasoning: {s.get('reasoning','')}\n")
                f.write(f"- Risk: {s.get('risk','')}\n\n")
        log(f"Report saved: {report_path}")

    else:
        msg = f"📊 *POLYMARKET SCAN COMPLETE*\n{today}\n\nNo signals above 5% EV threshold found.\nMarkets appear fairly priced right now.\n\n_Next scan in 4 hours._"
        tg(msg)
        feed("Polymarket Scan — No Signals","No EV > 5% opportunities found","info")

    log(f"COMPLETE — {len(unique_signals)} signals, {len(trader_signals)} wallet signals")

# ── ADD WALLET TO WATCHLIST ───────────────────────────────────
def add_wallet_to_watchlist(wallet_address):
    watchlist = load_watchlist()
    if wallet_address not in watchlist["wallets"]:
        watchlist["wallets"].append(wallet_address)
        with open(WATCHLIST_FILE,"w") as f: json.dump(watchlist,f,indent=2)
        log(f"Added wallet: {wallet_address}")
        return True
    return False

# ── ENTRY POINT ───────────────────────────────────────────────
if __name__ == "__main__":
    log("Polymarket Intelligence starting")
    log(f"Gemini: {'OK' if GOOGLE_API_KEY else 'MISSING'}")
    log(f"Telegram: {'OK' if T_TOKEN else 'MISSING'}")

    tg(f"📊 *POLYMARKET INTELLIGENCE ONLINE*\n"
       f"{datetime.datetime.now().strftime('%B %d %I:%M %p')}\n\n"
       f"Scanning:\n"
       f"• Trending markets for EV > 5%\n"
       f"• Crypto/macro/political markets\n"
       f"• Smart wallet positions\n\n"
       f"_Scans every 4 hours. Intelligence only — no auto trading yet._")

    while True:
        try:
            run_polymarket_intel()
        except Exception as e:
            log(f"ERROR: {e}")
            tg(f"⚠️ Polymarket Intel error: {e}")
        log("Sleeping 4 hours...")
        time.sleep(4 * 60 * 60)