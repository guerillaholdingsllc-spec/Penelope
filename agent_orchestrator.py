import os, json, time, requests, datetime, threading, uuid
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


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
FIRECRAWL_KEY  = os.getenv("FIRECRAWL_KEY","fc-81fff09a728d47809ebb453326267d1b").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY","2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4").strip()

BASE          = "/root/workspace/Penelope"
FEED_FILE     = f"{BASE}/feed.json"
AGENTS_FILE   = f"{BASE}/agents_status.json"
TASKS_FILE    = f"{BASE}/agent_tasks.json"
SCHEDULE_FILE = f"{BASE}/agent_schedule.json"
GUMROAD_BASE  = "https://api.gumroad.com/v2"

client = genai.Client(api_key=GOOGLE_API_KEY)

AGENTS = {
    "researcher": {"name":"Researcher","emoji":"🔍","hours":4},
    "outreach":   {"name":"Outreach","emoji":"📣","hours":6},
    "analyst":    {"name":"Analyst","emoji":"📊","hours":24},
    "compliance": {"name":"Compliance","emoji":"⚖️","hours":48},
    "crypto":     {"name":"Crypto","emoji":"₿","hours":12},
}

def log(msg, agent="ORC"):
    print(f"[{agent} {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def tg(msg):
    try:
        for chunk in [msg[i:i+4000] for i in range(0,len(msg),4000)]:
            _tg_emergency_only("[suppressed direct call]")
            time.sleep(0.3)
    except Exception as e: log(f"TG error: {e}")

def feed(title, content, status="info", agent="Orchestrator"):
    try:
        data = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE) as f: data = json.load(f)
        data.insert(0,{"id":int(time.time()),"title":title,"content":content,
                       "status":status,"agent":agent,
                       "timestamp":datetime.datetime.now().isoformat()})
        with open(FEED_FILE,"w") as f: json.dump(data[:100],f,indent=2)
    except: pass

def set_status(agent_id, status, preview="", error=""):
    data = {}
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE) as f: data = json.load(f)
    if "agents" not in data: data["agents"] = {}
    data["agents"][agent_id] = {
        "name": AGENTS[agent_id]["name"],
        "emoji": AGENTS[agent_id]["emoji"],
        "status": status,
        "last_run": datetime.datetime.now().isoformat(),
        "last_output_preview": preview[:200],
        "error": error
    }
    data["last_updated"] = datetime.datetime.now().isoformat()
    with open(AGENTS_FILE,"w") as f: json.dump(data,f,indent=2)

def save_task(task):
    data = {"tasks":[]}
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f: data = json.load(f)
    data["tasks"].insert(0,task)
    data["tasks"] = data["tasks"][:100]
    with open(TASKS_FILE,"w") as f: json.dump(data,f,indent=2)

def scrape(url, max_chars=2000):
    try:
        res = requests.post("https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization":f"Bearer {FIRECRAWL_KEY}","Content-Type":"application/json"},
            json={"url":url,"formats":["markdown"]},timeout=25)
        d = res.json()
        if d.get("success"):
            return d.get("data",{}).get("markdown","")[:max_chars]
    except: pass
    return ""

def gem(prompt):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash",contents=prompt)
        return getattr(r,"text","")
    except Exception as e:
        log(f"Gemini error: {e}")
        return ""

def save_output(agent_id, content, suffix="output"):
    ds = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"{BASE}/shipped/{ds}_{agent_id}_{suffix}.md"
    with open(fname,"w") as f: f.write(content)
    return fname

# ── RESEARCHER ────────────────────────────────────────────────
def run_researcher():
    log("Running","RESEARCHER"); set_status("researcher","running")
    raw = {}
    for url,cat in [
        ("https://cryptopanic.com/news/hot/","crypto"),
        ("https://techcrunch.com/category/artificial-intelligence/","ai"),
    ]:
        d = scrape(url,1500)
        if d: raw[cat] = d
        time.sleep(1)

    out = gem(f"""You are the Researcher Agent for Guerilla Holdings.
Analyze this market data and produce a concise intelligence report.
DATA: {json.dumps({k:v[:400] for k,v in raw.items()})}

Produce:
1. TOP 3 MARKET OPPORTUNITIES this week (specific revenue potential)
2. TRENDING TOPICS to incorporate into products
3. RISK ALERTS for Guerilla Holdings ventures (cadaver transport, crypto, AI services)
Max 300 words. Be specific and actionable.""")

    fname = save_output("researcher", out, "intel")
    save_task({"id":str(uuid.uuid4())[:8],"agent":"researcher","type":"intel",
               "file":fname,"output_preview":out[:200],
               "timestamp":datetime.datetime.now().isoformat(),"status":"completed"})
    set_status("researcher","idle",out)
    feed("Research Intel Ready",out[:300],"info","Researcher")
    tg(f"🔍 *RESEARCHER INTEL*\n\n{out[:2000]}")
    log("Done","RESEARCHER")

# ── OUTREACH ──────────────────────────────────────────────────
def run_outreach():
    log("Running","OUTREACH"); set_status("outreach","running")
    raw = {}
    for url,ctx in [
        ("https://www.reddit.com/r/funeralhome/new.json","funeral directors"),
        ("https://www.reddit.com/r/CryptoCurrency/new.json","crypto investors"),
    ]:
        d = scrape(url,1200)
        if d: raw[ctx] = d
        time.sleep(1)

    out = gem(f"""You are the Outreach Agent for Guerilla Holdings.
Find people who need our products and draft outreach messages.

OUR PRODUCTS:
- Cadaver Transport Compliance Kit ($197) — for funeral homes
- DEVVE Investor Brief ($47) — for crypto investors
- AI Automation Package ($297) — for businesses
- CALLUX Driver Cert Guide ($47) — for gig drivers

COMMUNITY DATA:
{json.dumps({k:v[:400] for k,v in raw.items()})}

Draft 3 ready-to-post outreach messages. For each:
- Platform & community
- Context (what they need)
- Message (helpful, non-salesy, leads to product)
- Which product helps them

Mark each READY TO POST — Sydney must manually post these.""")

    tid = str(uuid.uuid4())[:8]
    fname = save_output("outreach", out, "batch")
    save_task({"id":tid,"agent":"outreach","type":"outreach",
               "file":fname,"output_preview":out[:200],
               "requires_approval":True,
               "timestamp":datetime.datetime.now().isoformat(),"status":"pending_approval"})
    set_status("outreach","awaiting_approval",out)
    feed("Outreach Batch — Needs Approval",out[:300],"warning","Outreach")
    tg(f"📣 *OUTREACH AGENT*\nReady for review — post manually when approved.\n\n{out[:3000]}")
    log("Done — awaiting approval","OUTREACH")

# ── ANALYST ───────────────────────────────────────────────────
def run_analyst():
    log("Running","ANALYST"); set_status("analyst","running")
    try:
        pr = requests.get(f"{GUMROAD_BASE}/products",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},timeout=15).json()
        sl = requests.get(f"{GUMROAD_BASE}/sales",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},
            params={"after":(datetime.datetime.now()-datetime.timedelta(days=30)).strftime("%Y-%m-%d")},
            timeout=15).json()
        p_list = pr.get("products",[]) if pr.get("success") else []
        s_list = sl.get("sales",[]) if sl.get("success") else []
        revenue = sum(float(s.get("price",0)) for s in s_list)/100
    except Exception as e:
        p_list,s_list,revenue = [],[],0.0
        log(f"Gumroad err: {e}","ANALYST")

    out = gem(f"""You are the Analyst Agent for Guerilla Holdings.
GUMROAD DATA (30 days):
Products: {len(p_list)} | Sales: {len(s_list)} | Revenue: ${revenue:.2f}
Products: {[p.get("name","") for p in p_list[:10]]}

Give:
1. WINNER: Best product (or plan if no sales)
2. KILL: What to remove/rewrite
3. NEXT PRODUCT: Exact title, price, why it will sell
4. PRICING: Any adjustments needed
Be brutal and specific. Max 250 words.""")

    fname = save_output("analyst", out, "report")
    save_task({"id":str(uuid.uuid4())[:8],"agent":"analyst","type":"analysis",
               "file":fname,"output_preview":out[:200],
               "timestamp":datetime.datetime.now().isoformat(),"status":"completed"})
    set_status("analyst","idle",out)
    feed("Analyst Report",out[:300],"info","Analyst")
    tg(f"📊 *ANALYST REPORT*\n\n{out[:2000]}")
    log("Done","ANALYST")

# ── COMPLIANCE ────────────────────────────────────────────────
def run_compliance():
    log("Running","COMPLIANCE"); set_status("compliance","running")
    d = scrape("https://www.cdph.ca.gov/Programs/OFR/Pages/default.aspx",1500)
    out = gem(f"""You are the Compliance Agent for Guerilla Holdings CadaverCo.
DATA: {d[:800] if d else 'No live data — use knowledge'}
Report:
1. New CA regulations affecting cadaver transport
2. CALLUX driver certification compliance
3. Anything requiring URGENT attention
If no changes: confirm compliance status. Max 150 words.""")

    set_status("compliance","idle",out)
    if "URGENT" in out.upper():
        tg(f"⚖️ *COMPLIANCE ALERT — URGENT*\n\n{out}")
        feed("COMPLIANCE ALERT",out[:300],"error","Compliance")
    else:
        feed("Compliance Check Clear",out[:300],"success","Compliance")
    log("Done","COMPLIANCE")

# ── CRYPTO MONITOR ────────────────────────────────────────────
def run_crypto():
    log("Running","CRYPTO"); set_status("crypto","running")
    d1 = scrape("https://www.coingecko.com/en/coins/devve",1500)
    d2 = scrape("https://cryptopanic.com/news/?currencies=DEVVE",1000)
    out = gem(f"""You are the Crypto Agent monitoring DEVVE for Guerilla Holdings.
DATA: {d1[:600]} {d2[:400]}
Quick status:
1. DEVVE price status (up/down/flat + %)
2. Volume/market cap change
3. Sentiment (one sentence)
4. ALERT (urgent issue or "no alerts")
5. Recommendation (hold/add/reduce/exit + reason)
Max 120 words.""")

    set_status("crypto","idle",out)
    if any(w in out.upper() for w in ["URGENT","EXIT","CRASH","DUMP","ALERT"]):
        tg(f"₿ *DEVVE ALERT*\n\n{out}")
        feed("DEVVE ALERT",out[:300],"error","Crypto")
    else:
        feed("DEVVE Status",out[:300],"info","Crypto")
    log("Done","CRYPTO")

# ── ORCHESTRATOR LOOP ─────────────────────────────────────────
def should_run(agent_id, hours):
    schedule = {}
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE) as f: schedule = json.load(f)
    last = schedule.get(agent_id)
    if not last: return True
    return (datetime.datetime.now()-datetime.datetime.fromisoformat(last)).total_seconds() >= hours*3600

def mark_ran(agent_id):
    schedule = {}
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE) as f: schedule = json.load(f)
    schedule[agent_id] = datetime.datetime.now().isoformat()
    with open(SCHEDULE_FILE,"w") as f: json.dump(schedule,f,indent=2)

RUNNERS = {
    "researcher": run_researcher,
    "outreach":   run_outreach,
    "analyst":    run_analyst,
    "compliance": run_compliance,
    "crypto":     run_crypto,
}

def run_cycle():
    log("Cycle check")
    due = [aid for aid,a in AGENTS.items() if should_run(aid,a["hours"])]
    if not due: log("No agents due"); return
    log(f"Running: {due}")
    tg(f"🤖 *AGENT ARMY*\nLaunching: {', '.join(due)}")
    threads = []
    for aid in due:
        t = threading.Thread(target=RUNNERS[aid], daemon=True)
        threads.append((aid,t))
        t.start()
        mark_ran(aid)
    for aid,t in threads:
        t.join(timeout=120)
    log("Cycle complete")

if __name__ == "__main__":
    log("Agent Orchestrator starting")
    tg(f"🤖 *PENELOPE AGENT ARMY ONLINE*\n"
       f"{datetime.datetime.now().strftime('%B %d %I:%M %p')}\n\n"
       f"Agents: Researcher (4h) · Outreach (6h) · Analyst (24h) · Compliance (48h) · Crypto (12h)\n\n"
       f"_All results sent here and visible in Mission Control._")
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"ERROR: {e}")
            tg(f"⚠️ Orchestrator error: {e}")
        log("Sleeping 30 min...")
        time.sleep(30*60)