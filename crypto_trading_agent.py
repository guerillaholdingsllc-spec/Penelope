#!/usr/bin/env python3
"""
Penelope Crypto Trading Agent
Connects to crypto exchanges via API. Monitors portfolio, prices,
executes trades, generates daily briefings. Monitors DEVVE for Sydney.

Usage:
  python3 crypto_trading_agent.py --briefing
  python3 crypto_trading_agent.py --portfolio
  python3 crypto_trading_agent.py --price BTC
  python3 crypto_trading_agent.py --analyze BTC 4h
  python3 crypto_trading_agent.py --monitor-devve
  python3 crypto_trading_agent.py --journal
"""

import os,json,time,requests,logging,argparse,hmac,hashlib,urllib.parse
from pathlib import Path
from datetime import datetime,timedelta
import google.generativeai as genai

def _get_gemini_client():
    """Lazy Gemini client — loads key from vault at call time."""
    import os as _o
    key = _o.getenv("GOOGLE_API_KEY", "")
    if not key:
        try:
            for line in open("/root/penelope_vault.env"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip()
                    break
        except: pass
    if not key:
        return None
    import google.generativeai as genai
    return _g.Client(api_key=key)


GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY","")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")

# Exchange API keys (add to vault)
EXCHANGE_API_KEY=os.getenv("EXCHANGE_API_KEY","")
EXCHANGE_API_SECRET=os.getenv("EXCHANGE_API_SECRET","")
EXCHANGE_NAME=os.getenv("EXCHANGE_NAME","coinbase")  # coinbase, binance, kraken

# Coinbase Advanced API (most accessible)
COINBASE_API_KEY=os.getenv("COINBASE_API_KEY","")
COINBASE_API_SECRET=os.getenv("COINBASE_API_SECRET","")

OUTPUT_DIR=Path("/root/workspace/Penelope/crypto_reports")
JOURNAL_FILE=Path("/root/workspace/Penelope/trade_journal.json")
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

logging.basicConfig(level=logging.INFO,format="%(asctime)s [CRYPTO] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/crypto_agent.log"),logging.StreamHandler()])
log=logging.getLogger(__name__)

if GOOGLE_API_KEY:
    pass

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


def gemini(prompt,model="gemini-2.5-flash"):
    m=genai.GenerativeModel(model)
    return m.generate_content(prompt).text

# ── PRICE & MARKET DATA (CoinGecko - free, no auth) ─────────
def get_price(symbol):
    """Get current price from CoinGecko (free API)."""
    coin_map={
        "BTC":"bitcoin","ETH":"ethereum","SOL":"solana",
        "BNB":"binancecoin","DEVVE":"devve","XRP":"ripple",
        "ADA":"cardano","DOGE":"dogecoin","AVAX":"avalanche-2",
        "DOT":"polkadot","LINK":"chainlink","MATIC":"matic-network"
    }
    coin_id=coin_map.get(symbol.upper(),symbol.lower())
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/simple/price",
            params={"ids":coin_id,"vs_currencies":"usd","include_24hr_change":"true","include_market_cap":"true"},
            timeout=15)
        data=r.json()
        if coin_id in data:
            d=data[coin_id]
            return {"symbol":symbol.upper(),"price":d.get("usd",0),
                    "change_24h":d.get("usd_24h_change",0),"market_cap":d.get("usd_market_cap",0)}
    except Exception as e:log.error(f"Price error: {e}")
    return None

def get_market_overview():
    """Get top crypto market data."""
    try:
        r=requests.get("https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency":"usd","order":"market_cap_desc","per_page":10,"page":1,"price_change_percentage":"24h"},
            timeout=15)
        return r.json()
    except Exception as e:log.error(f"Market error: {e}");return []

def get_devve_data():
    """Deep DEVVE monitoring - Sydney holds this."""
    data={"symbol":"DEVVE","sources":{}}
    # CoinGecko
    try:
        r=requests.get("https://api.coingecko.com/api/v3/coins/devve",timeout=15)
        d=r.json()
        data["sources"]["coingecko"]={
            "price":d.get("market_data",{}).get("current_price",{}).get("usd",0),
            "change_24h":d.get("market_data",{}).get("price_change_percentage_24h",0),
            "change_7d":d.get("market_data",{}).get("price_change_percentage_7d",0),
            "market_cap":d.get("market_data",{}).get("market_cap",{}).get("usd",0),
            "volume_24h":d.get("market_data",{}).get("total_volume",{}).get("usd",0),
            "all_time_high":d.get("market_data",{}).get("ath",{}).get("usd",0),
            "description":d.get("description",{}).get("en","")[:500]
        }
    except Exception as e:log.error(f"DEVVE CoinGecko: {e}")
    # CryptoPanic sentiment
    try:
        r=requests.get("https://cryptopanic.com/api/v1/posts/",
            params={"auth_token":"","currencies":"DEVVE","filter":"hot"},timeout=15)
        news=r.json().get("results",[])[:5]
        data["sources"]["news"]=[{"title":n.get("title",""),"url":n.get("url",""),"votes":n.get("votes",{})} for n in news]
    except:data["sources"]["news"]=[]
    return data

def get_chart_data(symbol,days=7):
    """Get price history for analysis."""
    coin_map={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","DEVVE":"devve"}
    coin_id=coin_map.get(symbol.upper(),symbol.lower())
    try:
        r=requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency":"usd","days":days},timeout=15)
        prices=r.json().get("prices",[])
        return [{"timestamp":p[0],"price":p[1]} for p in prices]
    except:return []

# ── AI ANALYSIS ──────────────────────────────────────────────
def analyze_market(symbol,timeframe="4h",chart_data=None,price_data=None):
    """AI-powered market analysis."""
    chart_str=""
    if chart_data:
        prices=[p["price"] for p in chart_data[-20:]]
        chart_str=f"Recent prices: {[round(p,4) for p in prices]}"
    if price_data:
        chart_str+=f"\nCurrent: ${price_data['price']:.4f} | 24h: {price_data['change_24h']:.2f}%"

    prompt=f"""You are a professional crypto trading analyst. Analyze {symbol} on the {timeframe} chart.

Market Data:
    pass
{chart_str}

Provide:
    pass
1. TREND DIRECTION: Trending up/down/ranging?
2. KEY LEVELS: Support and resistance levels
3. SIGNAL: Long / Short / Stay Out — with confidence %
4. REASONING: 2-3 sentences explaining why
5. RISK NOTE: What could invalidate this analysis
6. POSITION SIZE: Conservative suggestion as % of portfolio

Be direct and specific. No fluff. Format clearly."""

    return gemini(prompt)

def generate_daily_briefing():
    """Morning briefing: top news, BTC action, portfolio summary."""
    log.info("Generating daily crypto briefing...")
    _tg_emergency_only("📊 *Generating Daily Crypto Briefing...*")

    # Get market data
    market=get_market_overview()
    btc_data=get_price("BTC")
    eth_data=get_price("ETH")
    devve_data=get_devve_data()
    btc_chart=get_chart_data("BTC",days=1)

    # Get crypto news
    news_summary=""
    try:
        r=requests.get("https://cryptopanic.com/api/v1/posts/",
            params={"auth_token":"","filter":"hot","public":"true"},timeout=15)
        news=r.json().get("results",[])[:8]
        news_summary="\n".join([f"- {n.get('title','')}" for n in news])
    except:news_summary="Could not fetch news"

    market_str="\n".join([f"{c['symbol']}: ${c['current_price']:.2f} ({c['price_change_percentage_24h']:+.1f}%)"
        for c in market[:6] if c.get('symbol')])

    devve_price=devve_data.get("sources",{}).get("coingecko",{}).get("price",0)
    devve_change=devve_data.get("sources",{}).get("coingecko",{}).get("change_24h",0)

    prompt=f"""You are Penelope, AI revenue engine for Guerilla Holdings. Generate Sydney's morning crypto briefing.

MARKET SNAPSHOT:
    pass
{market_str}

BTC: ${btc_data['price'] if btc_data else 'N/A'} | {btc_data['change_24h'] if btc_data else 0:+.1f}% 24h
ETH: ${eth_data['price'] if eth_data else 'N/A'} | {eth_data['change_24h'] if eth_data else 0:+.1f}% 24h
DEVVE (Sydney holds): ${devve_price:.6f} | {devve_change:+.2f}% 24h

TOP CRYPTO NEWS:
    pass
{news_summary}

Generate a concise one-page briefing with:
    pass
1. MARKET MOOD: Bull/Bear/Neutral and why
2. BTC ANALYSIS: Overnight action, key levels to watch
3. DEVVE UPDATE: Price action, sentiment, hold/accumulate/reduce recommendation
4. TOP STORIES: 3 key news items that matter today
5. TODAY'S WATCH LIST: 2-3 coins with setups worth watching
6. ACTION ITEMS: 2-3 specific things Sydney should do/watch today

Keep it tight. Sydney is a busy founder. Use emojis. Make it scannable."""

    briefing=gemini(prompt)

    # Save briefing
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    briefing_file=OUTPUT_DIR/f"briefing_{ts}.txt"
    briefing_file.write_text(briefing)

    _tg_emergency_only(f"📈 *Daily Crypto Briefing — {datetime.now().strftime('%b %d')}*\n\n{briefing[:2000]}")
    log.info(f"Briefing saved: {briefing_file}")
    return briefing

def analyze_trade_journal():
    """Analyze trade history for performance insights."""
    if not JOURNAL_FILE.exists():
        _tg_emergency_only("📔 No trade journal found. Add trades to /root/workspace/Penelope/trade_journal.json")
        return

    trades=json.loads(JOURNAL_FILE.read_text())
    if not trades:return

    prompt=f"""Analyze this trading journal and provide performance insights.

TRADE HISTORY:
    pass
{json.dumps(trades,indent=2)[:3000]}

Provide:
    pass
1. WIN RATE: Percentage of profitable trades
2. BEST PERFORMERS: Top 3 winning trades/pairs
3. WORST PERFORMERS: Top 3 losing trades
4. AVERAGE R:R: Average risk:reward ratio
5. PATTERN ANALYSIS: What strategies/pairs work best
6. MONEY LEAKS: Where losses are concentrated
7. IMPROVEMENT PLAN: 3 specific changes to make

Be specific with numbers. This is a performance audit."""

    analysis=gemini(prompt)
    ts=datetime.now().strftime("%Y%m%d")
    analysis_file=OUTPUT_DIR/f"journal_analysis_{ts}.txt"
    analysis_file.write_text(analysis)
    _tg_emergency_only(f"📔 *Trade Journal Analysis*\n\n{analysis[:1500]}")
    return analysis

def monitor_devve():
    """Deep DEVVE monitoring with AI analysis."""
    log.info("Monitoring DEVVE...")
    data=get_devve_data()
    chart=get_chart_data("DEVVE",days=7)

    cg=data.get("sources",{}).get("coingecko",{})
    price=cg.get("price",0)
    change_24h=cg.get("change_24h",0)
    change_7d=cg.get("change_7d",0)
    market_cap=cg.get("market_cap",0)
    volume=cg.get("volume_24h",0)
    ath=cg.get("all_time_high",0)

    prices=[p["price"] for p in chart[-14:]] if chart else [price]
    avg=sum(prices)/len(prices) if prices else price
    ath_pct=((price/ath)-1)*100 if ath>0 else 0

    prompt=f"""Analyze DEVVE cryptocurrency for Sydney, who holds DEVVE as an investment.

DEVVE DATA:
    pass
- Price: ${price:.8f}
- 24h Change: {change_24h:+.2f}%
- 7d Change: {change_7d:+.2f}%
- Market Cap: ${market_cap:,.0f}
- 24h Volume: ${volume:,.0f}
- All Time High: ${ath:.8f} ({ath_pct:.1f}% from ATH)
- 14-day prices: {[round(p,8) for p in prices]}

RECENT NEWS:
    pass
{json.dumps(data.get('sources',{}).get('news',[]),indent=2)[:500]}

Provide Sydney with:
    pass
1. CURRENT STATUS: Bullish/Bearish/Neutral with reasoning
2. KEY PRICE LEVELS: Support and resistance
3. VOLUME ANALYSIS: Is volume confirming price movement?
4. ATH DISTANCE: Context on where we are vs all-time high
5. HOLD RECOMMENDATION: Hold / Accumulate more / Take partial profits
6. CATALYST WATCH: What could move price significantly soon
7. RISK ASSESSMENT: Main risks to the position right now

Sydney is a founder holding this as part of her portfolio. Be direct."""

    analysis=gemini(prompt)
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file=OUTPUT_DIR/f"devve_{ts}.txt"
    report_file.write_text(f"DEVVE REPORT {datetime.now()}\n\nPrice: ${price:.8f}\n24h: {change_24h:+.2f}%\n7d: {change_7d:+.2f}%\n\n{analysis}")

    _tg_emergency_only(f"💎 *DEVVE Intelligence Report*\n\n💰 Price: ${price:.8f}\n📈 24h: {change_24h:+.2f}%\n📊 7d: {change_7d:+.2f}%\n\n{analysis[:1500]}")
    log.info(f"DEVVE report: {report_file}")
    return analysis

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Penelope Crypto Trading Agent")
    p.add_argument("--briefing",action="store_true",help="Generate daily briefing")
    p.add_argument("--portfolio",action="store_true",help="Check portfolio")
    p.add_argument("--price",help="Get price for symbol e.g. BTC")
    p.add_argument("--analyze",help="Analyze symbol e.g. BTC")
    p.add_argument("--timeframe",default="4h")
    p.add_argument("--monitor-devve",action="store_true",help="Deep DEVVE analysis")
    p.add_argument("--journal",action="store_true",help="Analyze trade journal")
    a=p.parse_args()

    if a.briefing:generate_daily_briefing()
    elif a.monitor_devve:monitor_devve()
    elif a.journal:analyze_trade_journal()
    elif a.price:
        d=get_price(a.price)
        if d:
            print(f"{d['symbol']}: ${d['price']:,.4f} | 24h: {d['change_24h']:+.2f}%")
            _tg_emergency_only(f"💰 *{d['symbol']}*: ${d['price']:,.4f} | 24h: {d['change_24h']:+.2f}%")
    elif a.analyze:
        chart=get_chart_data(a.analyze,days=7)
        price=get_price(a.analyze)
        analysis=analyze_market(a.analyze,a.timeframe,chart,price)
        print(analysis)
        _tg_emergency_only(f"📊 *{a.analyze} Analysis ({a.timeframe})*\n\n{analysis[:1500]}")
    else:
        print("""Penelope Crypto Trading Agent

  python3 crypto_trading_agent.py --briefing          # Morning briefing
  python3 crypto_trading_agent.py --monitor-devve     # DEVVE deep analysis
  python3 crypto_trading_agent.py --price BTC         # Get BTC price
  python3 crypto_trading_agent.py --analyze ETH       # AI market analysis
  python3 crypto_trading_agent.py --journal           # Analyze trade journal

Add to vault for exchange trading:
  EXCHANGE_API_KEY, EXCHANGE_API_SECRET, EXCHANGE_NAME""")