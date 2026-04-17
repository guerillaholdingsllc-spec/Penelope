import os, json, time, requests, datetime, schedule
from google import genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
FIRECRAWL_KEY  = os.getenv("FIRECRAWL_KEY","fc-81fff09a728d47809ebb453326267d1b").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY","2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4").strip()

BASE       = "/root/workspace/Penelope"
FEED_FILE  = f"{BASE}/feed.json"
BRIEFS_DIR = f"{BASE}/daily_briefs"
FINANCE    = f"{BASE}/finance/FUND_LEDGER.md"
GUMROAD_BASE = "https://api.gumroad.com/v2"

os.makedirs(BRIEFS_DIR, exist_ok=True)
client = genai.Client(api_key=GOOGLE_API_KEY)

def log(msg):
    print(f"[BRIEF {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


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
                       "status":status,"agent":"DailyBrief",
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

def get_weather():
    try:
        res = requests.get("https://wttr.in/Sacramento+CA?format=3",timeout=10)
        return res.text.strip()
    except: return "Weather unavailable"

def get_news():
    news_sources = [
        "https://cryptopanic.com/news/hot/",
        "https://techcrunch.com/category/artificial-intelligence/",
    ]
    combined = ""
    for url in news_sources:
        data = scrape(url, 1500)
        if data:
            combined += f"\n{data}"
        time.sleep(1)
    return combined

def get_gumroad_stats():
    try:
        products = requests.get(f"{GUMROAD_BASE}/products",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},timeout=15).json()
        sales = requests.get(f"{GUMROAD_BASE}/sales",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},
            params={"after":(datetime.datetime.now()-datetime.timedelta(days=7)).strftime("%Y-%m-%d")},
            timeout=15).json()
        p_count = len(products.get("products",[])) if products.get("success") else 0
        s_list = sales.get("sales",[]) if sales.get("success") else []
        revenue = sum(float(s.get("price",0)) for s in s_list) / 100
        return p_count, len(s_list), revenue
    except: return 0, 0, 0.0

def get_shipped_today():
    today = datetime.datetime.now().strftime("%Y%m%d")
    shipped_dir = f"{BASE}/shipped"
    files = [f for f in os.listdir(shipped_dir) if f.startswith(today)] if os.path.exists(shipped_dir) else []
    return len(files), files[:3]

def get_running_services():
    try:
        result = os.popen("ps aux | grep python | grep -v grep").read()
        services = []
        for line in result.strip().split("\n"):
            if "penelope_env" in line or "workspace" in line:
                parts = line.split()
                script = parts[-1].split("/")[-1] if parts else "unknown"
                services.append(script)
        return services
    except: return []

def generate_daily_brief():
    log("Generating daily brief...")
    today = datetime.datetime.now()
    date_str = today.strftime("%A, %B %d, %Y")
    week_num = today.isocalendar()[1]

    weather = get_weather()
    news_data = get_news()
    p_count, s_count, revenue_7d = get_gumroad_stats()
    shipped_count, shipped_files = get_shipped_today()
    services = get_running_services()

    # Calculate days and deficit progress
    launch_date = datetime.datetime(2026, 3, 30)
    days_running = (today - launch_date).days
    deficit = -50000
    weeks_remaining = max(0, 26 - (days_running // 7))

    prompt = f"""You are Penelope, the autonomous AI teammate for Sydney Kye Garmon at Guerilla Holdings, LLC.
Generate Sydney's Daily Brief for {date_str}.

LIVE DATA:
- Weather: {weather}
- Gumroad products live: {p_count}
- Sales last 7 days: {s_count}
- Revenue last 7 days: ${revenue_7d:.2f}
- Deliverables shipped today: {shipped_count} ({', '.join(shipped_files) if shipped_files else 'none yet'})
- Running services: {', '.join(services) if services else 'checking...'}
- Days since launch: {days_running}
- Weeks remaining to hit target: {weeks_remaining}
- Current deficit: ${deficit:,}

NEWS/TRENDS DATA:
{news_data[:2000] if news_data else "News scraping in progress"}

GUERILLA HOLDINGS CONTEXT:
- Ventures: CadaverCo (transport), CALLUX (dispatch platform), Penelope (AI revenue engine)
- DEVVE crypto holder
- 6-month mission: eliminate $50k deficit
- Phase 1 (now): Get first products live and selling

Generate the brief in this EXACT format:

🌅 *PENELOPE DAILY BRIEF*
*{date_str}*
━━━━━━━━━━━━━━━━━━━━━━

☀️ *SACRAMENTO WEATHER*
{weather}

💰 *REVENUE STATUS*
• 7-day revenue: ${{revenue}}
• Products live: {{count}}
• Sales this week: {{count}}
• Deficit remaining: $50,000 (Day {{days}} of 180)
• Weekly target to hit goal: ${{weekly_target_needed}}

⚡ *SYSTEMS STATUS*
• (list each running service with green checkmark or red X)

📦 *SHIPPED TODAY*
• (list today's deliverables or "Nothing shipped yet today")

📰 *INTELLIGENCE BRIEF*
• (3-4 bullets: AI/tech/crypto/business news relevant to Guerilla Holdings ventures)
• (Focus on: funeral home industry, gig economy, crypto, AI automation)

🎯 *TODAY'S PRIORITY ACTIONS*
1. (Most important revenue action today — specific and actionable)
2. (Second priority — specific)
3. (Third priority — specific)

⚠️ *RISKS & BLOCKERS*
• (Any issues Penelope has detected or anticipates)

💡 *PENELOPE RECOMMENDATION*
(One specific, high-leverage action Sydney should take today to accelerate the $50k recovery)

━━━━━━━━━━━━━━━━━━━━━━
_Week {week_num} · Day {days_running} of 180 · {weeks_remaining} weeks remaining_
_— Penelope, Guerilla Holdings AI_

Be specific, data-driven, and executive-ready. No fluff. Every line should be actionable or informative."""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        brief = getattr(response, "text", "Brief generation failed.")
        log(f"Brief generated: {len(brief)} chars")
        return brief
    except Exception as e:
        log(f"Brief generation error: {e}")
        return f"⚠️ Brief generation failed: {e}"

def send_morning_brief():
    log("Sending morning brief...")
    brief = generate_daily_brief()

    # Save to daily_briefs/
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    fname = f"{BRIEFS_DIR}/{date_str}_morning_brief.md"
    with open(fname, "w") as f:
        f.write(brief)
    log(f"Brief saved: {fname}")

    _tg_emergency_only(brief)
    post_to_feed("Morning Brief Sent", brief[:500], "info")
    log("Morning brief complete")

def send_end_of_day():
    log("Sending end of day summary...")
    today = datetime.datetime.now()
    date_str = today.strftime("%A, %B %d, %Y")

    shipped_count, shipped_files = get_shipped_today()
    p_count, s_count, revenue_7d = get_gumroad_stats()
    services = get_running_services()

    prompt = f"""You are Penelope. Generate Sydney's End of Day Summary for {date_str}.

DATA:
- Deliverables shipped today: {shipped_count}
- Files shipped: {', '.join(shipped_files) if shipped_files else 'none'}
- 7-day revenue: ${revenue_7d:.2f}
- Running services: {', '.join(services) if services else 'unknown'}

Generate a concise end-of-day summary:

🌙 *PENELOPE END OF DAY*
*{date_str}*
━━━━━━━━━━━━━━━━━━━━━━

✅ *COMPLETED TODAY*
• (what shipped, what ran, what was accomplished)

📊 *METRICS*
• Revenue today: (estimate from data)
• Products delivered: {shipped_count}
• Systems uptime: (all services running?)

🔮 *TOMORROW'S FOCUS*
1. (Top priority for tomorrow)
2. (Second priority)

💤 *OVERNIGHT TASKS*
• (What Penelope will do autonomously overnight)

━━━━━━━━━━━━━━━━━━━━━━
_Systems running overnight. Next brief at 08:30._
_— Penelope_"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        summary = getattr(response, "text", "End of day summary failed.")
    except Exception as e:
        summary = f"End of day summary error: {e}"

    date_str2 = today.strftime("%Y-%m-%d")
    fname = f"{BRIEFS_DIR}/{date_str2}_eod_summary.md"
    with open(fname, "w") as f:
        f.write(summary)

    _tg_emergency_only(summary)
    post_to_feed("End of Day Summary", summary[:500], "info")
    log("End of day summary sent")

def run_scheduler():
    log("Daily Brief scheduler starting")
    log("Morning brief: 08:30 PST daily")
    log("End of day: 22:00 PST daily")

    # Send immediately on first run for testing
    log("Sending initial brief now...")
    send_morning_brief()

    # Schedule recurring
    schedule.every().day.at("08:30").do(send_morning_brief)
    schedule.every().day.at("22:00").do(send_end_of_day)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        import schedule
    except ImportError:
        os.system("/root/penelope_env/bin/pip install schedule --quiet")
        import schedule
    run_scheduler()
