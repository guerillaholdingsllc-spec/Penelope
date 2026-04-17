import os, json, time, requests, datetime
from google import genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
try:
    from google import genai
    if GOOGLE_API_KEY:
                _genai_ready = True
    else:
        _genai_ready = False
except Exception as _ge:
    _genai_ready = False
FIRECRAWL_KEY  = os.getenv("FIRECRAWL_KEY","fc-81fff09a728d47809ebb453326267d1b").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()

BASE      = "/root/workspace/Penelope"
FEED_FILE = f"{BASE}/feed.json"
OPP_FILE  = f"{BASE}/00_OPPORTUNITIES.md"

client = _get_gemini_client()
def log(msg):
    print(f"[RADAR {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


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


def post_to_feed(title, content, status="info"):
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE,"r") as f: feed = json.load(f)
        feed.insert(0,{"id":int(time.time()),"title":title,"content":content,
                       "status":status,"agent":"OpportunityRadar",
                       "timestamp":datetime.datetime.now().isoformat()})
        with open(FEED_FILE,"w") as f: json.dump(feed[:100],f,indent=2)
    except Exception as e: log(f"Feed error: {e}")

def scrape(url, max_chars=2000):
    try:
        res = requests.post("https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization":f"Bearer {FIRECRAWL_KEY}","Content-Type":"application/json"},
            json={"url":url,"formats":["markdown"]},timeout=20)
        data = res.json()
        if data.get("success"):
            return data.get("data",{}).get("markdown","")[:max_chars]
        return ""
    except: return ""

def scan_opportunities():
    log("Scanning for opportunities...")

    # Scan relevant markets
    sources = [
        ("https://www.reddit.com/r/funeralhome/new.json", "funeral_home"),
        ("https://cryptopanic.com/news/hot/", "crypto"),
        ("https://www.reddit.com/r/gig/new.json", "gig_economy"),
        ("https://techcrunch.com/category/artificial-intelligence/", "ai"),
    ]

    market_data = {}
    for url, category in sources:
        data = scrape(url, 1500)
        if data:
            market_data[category] = data
        time.sleep(1)

    today = datetime.datetime.now().strftime("%B %d, %Y")

    prompt = f"""You are Penelope, opportunity radar for Guerilla Holdings.

Sydney runs: CadaverCo (cadaver transport), CALLUX (dispatch platform), digital products, crypto (DEVVE).
Mission: Eliminate $50k deficit in 6 months. Currently in Phase 1.

LIVE MARKET DATA:
{json.dumps({k: v[:500] for k,v in market_data.items()}, indent=2)}

Identify 5 specific, actionable opportunities for TODAY ({today}).

For each opportunity:
- Must be executable within 2 hours
- Must have clear revenue potential
- Must align with existing Guerilla Holdings ventures

Format as:

🎯 *OPPORTUNITY RADAR — {today}*
━━━━━━━━━━━━━━━━━━━━━━

*OPPORTUNITY 1: [Title]*
• Category: [CadaverCo / CALLUX / Digital Product / Crypto]
• Revenue potential: $X
• Time to execute: X hours
• Action: (exact specific step to take right now)
• Why now: (what's happening in the market today that makes this timely)

(repeat for 5 opportunities)

━━━━━━━━━━━━━━━━━━━━━━
*TOP PICK TODAY:* Opportunity #X — (one sentence why)
_— Penelope Radar_"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        opps = getattr(response, "text", "Radar scan failed.")
        log(f"Opportunities generated: {len(opps)} chars")
        return opps
    except Exception as e:
        log(f"Opportunity generation error: {e}")
        return f"Radar error: {e}"

def run_radar():
    log("="*50)
    log("OPPORTUNITY RADAR SCANNING")
    log("="*50)

    opportunities = scan_opportunities()

    # Update opportunities file
    with open(OPP_FILE, "w") as f:
        f.write(f"# PENELOPE OPPORTUNITY RADAR\nUpdated: {datetime.datetime.now().isoformat()}\n\n")
        f.write(opportunities)

    _tg_emergency_only(opportunities)
    post_to_feed("Opportunity Radar", opportunities[:500], "info")
    log("Radar scan complete")

if __name__ == "__main__":
    log("Opportunity Radar starting")
    log("Scans every 4 hours")

    # Run immediately
    run_radar()

    while True:
        time.sleep(4 * 60 * 60)
        run_radar()
