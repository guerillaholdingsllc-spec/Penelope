import os, json, time, requests, datetime
from google import genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
FIRECRAWL_KEY  = os.getenv("FIRECRAWL_KEY","fc-81fff09a728d47809ebb453326267d1b").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()

FEED_FILE  = "/root/workspace/Penelope/feed.json"
WORK_DIR   = "/root/workspace/Penelope/shipped"
REPORT_DIR = "/root/workspace/Penelope/crypto_reports"

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(WORK_DIR, exist_ok=True)
client = genai.Client(api_key=GOOGLE_API_KEY)

WATCHLIST = [{"ticker":"DEVVE","name":"Devve","personal":True}]

COIN_SOURCES = {
    "DEVVE":[
        "https://www.coingecko.com/en/coins/devve",
        "https://coinmarketcap.com/currencies/devve/",
        "https://cryptopanic.com/news/?currencies=DEVVE",
        "https://dexscreener.com/search?q=DEVVE",
    ]
}

TRENDING_SOURCES = [
    "https://www.coingecko.com/en/coins/trending",
    "https://coinmarketcap.com/trending-cryptocurrencies/",
    "https://cryptopanic.com/news/hot/",
]

def log(msg):
    print(f"[CRYPTO {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}",flush=True)

def post_to_feed(title,content,status="info"):
    try:
        feed=[]
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE,"r") as f: feed=json.load(f)
        feed.insert(0,{"id":int(time.time()),"title":title,"content":content,
                       "status":status,"agent":"CryptoIntel",
                       "timestamp":datetime.datetime.now().isoformat()})
        feed=feed[:100]
        with open(FEED_FILE,"w") as f: json.dump(feed,f,indent=2)
    except Exception as e: log(f"Feed error:{e}")


import requests as _tg_requests
from datetime import datetime as _tg_dt


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


def scrape(url,max_chars=3000):
    try:
        log(f"Scraping:{url}")
        res=requests.post("https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization":f"Bearer {FIRECRAWL_KEY}","Content-Type":"application/json"},
            json={"url":url,"formats":["markdown"]},timeout=25)
        data=res.json()
        if data.get("success"):
            c=data.get("data",{}).get("markdown","")
            log(f"Got {len(c)} chars")
            return c[:max_chars]
        return ""
    except Exception as e:
        log(f"Scrape error:{e}")
        return ""

def scrape_multiple(urls,max_chars_each=2500):
    out=""
    for url in urls:
        r=scrape(url,max_chars_each)
        if r: out+=f"\n\n--- SOURCE:{url} ---\n{r}"
        time.sleep(2)
    return out

def discover_trending():
    log("Discovering trending...")
    raw=scrape_multiple(TRENDING_SOURCES,max_chars_each=1500)
    if not raw: return []
    try:
        resp=client.models.generate_content(model="gemini-2.5-flash",
            contents=f"From this data extract top 5 trending crypto coins.\nDATA:{raw}\nReturn ONLY JSON array: [{{\"name\":\"Bitcoin\",\"ticker\":\"BTC\"}}]\nNo explanation.")
        txt=getattr(resp,"text","[]").strip().replace("```json","").replace("```","").strip()
        coins=json.loads(txt)
        log(f"Trending:{[c['ticker'] for c in coins]}")
        return coins
    except Exception as e:
        log(f"Trending error:{e}")
        return []

def generate_report(ticker,name,raw_data,is_personal=False):
    today=datetime.datetime.now().strftime("%B %d, %Y")
    portfolio_section=""
    if is_personal:
        portfolio_section="""
## PORTFOLIO ACTION (PERSONAL HOLDING)
- Recommendation: HOLD / ADD / REDUCE / EXIT
- Stop loss level:
- Price target 3 months:
- Price target 6 months:
- Key triggers to watch:
"""
    prompt=f"""You are a senior crypto analyst at Guerilla Holdings Intelligence.
Generate a COMPLETE professional weekly risk assessment report for {name} ({ticker}).
Sold to subscribers at $97-$297/month. Make it worth every dollar.
{"NOTE: This is a PERSONAL PORTFOLIO HOLDING for Guerilla Holdings." if is_personal else ""}

LIVE DATA SCRAPED TODAY:
{raw_data if raw_data else "No live data - use training knowledge, note estimates clearly."}

Write the full report:

# GUERILLA HOLDINGS INTELLIGENCE
## Weekly Crypto Risk Assessment: {name} ({ticker})
**Date:** {today} | **Type:** {"PERSONAL PORTFOLIO" if is_personal else "MARKET INTEL"} | **Analyst:** Penelope AI

---

## EXECUTIVE SUMMARY
(4-5 sentences: project overview, market position, biggest risk, biggest opportunity, verdict)

## RISK SCORE: X/10
## RISK RATING: LOW / MEDIUM / HIGH / CRITICAL
(Explain in 2 sentences)

---

## 1. PROJECT FUNDAMENTALS
- What it does:
- Category:
- Launch date:
- Whitepaper quality:
- Use case viability:
- Development activity:
- Team transparency:
- Audits:
- Fundamental Risk: LOW/MEDIUM/HIGH

## 2. TOKENOMICS
- Total supply:
- Circulating supply:
- Market cap / FDV:
- Token distribution %:
- Vesting schedules:
- Token utility:
- Inflation/burn:
- Tokenomics Risk: LOW/MEDIUM/HIGH

## 3. MARKET DATA
- Current price:
- 24h / 7d / 30d change:
- 24h volume:
- ATH and % below:
- Support / resistance:
- Trend:
- Market Risk: LOW/MEDIUM/HIGH

## 4. LIQUIDITY AND EXCHANGE RISK
- Listed exchanges:
- DEX liquidity:
- Whale concentration:
- Manipulation signs:
- Liquidity Risk: LOW/MEDIUM/HIGH

## 5. SENTIMENT AND NEWS
- Community sentiment:
- Recent positive news:
- Recent negative news:
- Upcoming catalysts:
- Sentiment Risk: LOW/MEDIUM/HIGH

## 6. SECURITY AND RUG RISK
- Contract audited:
- Mint function present:
- Ownership renounced:
- Rug pull probability:
- Security Risk: LOW/MEDIUM/HIGH

## 7. RED FLAGS
(Bullet list - direct and unfiltered)

## 8. OPPORTUNITY SIGNALS
(Bullet list of genuine positive catalysts)

## 9. COMPARABLE PROJECTS
(2-3 similar projects, how {name} compares)

## 10. VERDICT AND RECOMMENDATION
- Action: BUY/HOLD/SELL/AVOID/WATCH
- Conviction: HIGH/MEDIUM/LOW
- Entry zone:
- Target 3 months:
- Target 12 months:
- Stop loss:
- Final verdict:

{portfolio_section}

---
*Guerilla Holdings Intelligence. Not financial advice. {today}*"""
    try:
        resp=client.models.generate_content(model="gemini-2.5-flash",contents=prompt)
        report=getattr(resp,"text","Report failed.")
        log(f"Report done:{len(report)} chars")
        return report
    except Exception as e:
        log(f"Report error:{e}")
        return f"Error generating report for {ticker}:{e}"

def save_report(ticker,report):
    d=datetime.datetime.now().strftime("%Y%m%d")
    for path in [REPORT_DIR,WORK_DIR]:
        with open(f"{path}/{d}_{ticker}_risk_report.md","w") as f: f.write(report)
    log(f"Saved {ticker}")
    return f"{REPORT_DIR}/{d}_{ticker}_risk_report.md"

def run_crypto_intelligence():
    log("="*50)
    log("CRYPTO INTEL WEEKLY RUN STARTING")
    log("="*50)
    today=datetime.datetime.now().strftime("%B %d, %Y")
    all_reports=[]

    post_to_feed("Crypto Intel Starting",f"Weekly crypto research starting {today}","info")
    _tg_emergency_only(f"*GUERILLA HOLDINGS INTEL*\nWeekly crypto research starting {today}\nResearching DEVVE + trending coins...")

    for coin in WATCHLIST:
        ticker=coin["ticker"]; name=coin["name"]; is_p=coin.get("personal",False)
        sources=COIN_SOURCES.get(ticker,[
            f"https://www.coingecko.com/en/coins/{name.lower()}",
            f"https://coinmarketcap.com/currencies/{name.lower()}/",
            f"https://cryptopanic.com/news/?currencies={ticker}",
        ])
        raw=scrape_multiple(sources)
        report=generate_report(ticker,name,raw,is_p)
        save_report(ticker,report)
        all_reports.append({"ticker":ticker,"name":name,"report":report,"personal":is_p})
        post_to_feed(f"Report:{name} ({ticker})",report[:1500],"success")
        time.sleep(3)

    wl=[c["ticker"] for c in WATCHLIST]
    for coin in discover_trending()[:5]:
        ticker=coin.get("ticker",""); name=coin.get("name",ticker)
        if ticker in wl: continue
        sources=[
            f"https://www.coingecko.com/en/coins/{name.lower().replace(' ','-')}",
            f"https://coinmarketcap.com/currencies/{name.lower().replace(' ','-')}/",
            f"https://cryptopanic.com/news/?currencies={ticker}",
        ]
        raw=scrape_multiple(sources)
        report=generate_report(ticker,name,raw,False)
        save_report(ticker,report)
        all_reports.append({"ticker":ticker,"name":name,"report":report,"personal":False})
        post_to_feed(f"Trending:{name} ({ticker})",report[:1500],"success")
        time.sleep(3)

    pr=[r for r in all_reports if r["personal"]]
    tr=[r for r in all_reports if not r["personal"]]
    summary=f"""*GUERILLA HOLDINGS INTELLIGENCE*
Weekly Crypto Reports - {today}

*PERSONAL PORTFOLIO* ({len(pr)} coins)
{chr(10).join([f"- {r['name']} ({r['ticker']}) done" for r in pr])}

*TRENDING INTEL* ({len(tr)} coins)
{chr(10).join([f"- {r['name']} ({r['ticker']}) done" for r in tr])}

Total: {len(all_reports)} reports
Saved: /root/workspace/Penelope/crypto_reports/
Next run: 7 days
- Penelope"""

    _tg_emergency_only(summary)
    time.sleep(2)
    for r in all_reports:
        label="PORTFOLIO HOLDING" if r["personal"] else "MARKET INTEL"
        _tg_emergency_only(f"*{label}: {r['name']} ({r['ticker']})*\n\n"+r["report"][:3600])
        time.sleep(3)

    post_to_feed("Crypto Intel Complete",f"{len(all_reports)} reports done and sent to Telegram.","success")
    log(f"COMPLETE - {len(all_reports)} reports")

if __name__=="__main__":
    log("Crypto Intelligence Engine starting")
    log(f"Watchlist:{[c['ticker'] for c in WATCHLIST]}")
    log(f"Firecrawl:{'OK' if FIRECRAWL_KEY else 'MISSING'}")
    log(f"Gemini:{'OK' if GOOGLE_API_KEY else 'MISSING'}")
    log(f"Telegram:{'OK' if T_TOKEN else 'MISSING'} | Chat ID:{C_ID}")
    while True:
        try:
            run_crypto_intelligence()
        except Exception as e:
            log(f"CRITICAL ERROR:{e}")
            post_to_feed("Crypto Intel Error",str(e),"error")
            try: _tg_emergency_only(f"Crypto Intel Error: {e}")
            except: pass
        log("Sleeping 7 days...")
        time.sleep(7*24*60*60)
