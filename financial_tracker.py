import os, json, time, requests, datetime
from google import genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY","").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID","6183015901").strip()
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY","2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4").strip()

BASE         = "/root/workspace/Penelope"
FEED_FILE    = f"{BASE}/feed.json"
LEDGER_FILE  = f"{BASE}/finance/FUND_LEDGER.md"
ROI_LOG      = f"{BASE}/finance/ROI_LOG.md"
FINANCE_JSON = f"{BASE}/finance/finance_state.json"
GUMROAD_BASE = "https://api.gumroad.com/v2"

client = _get_gemini_client()
def log(msg):
    print(f"[FINANCE {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


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
                       "status":status,"agent":"FinanceTracker",
                       "timestamp":datetime.datetime.now().isoformat()})
        with open(FEED_FILE,"w") as f: json.dump(feed[:100],f,indent=2)
    except Exception as e: log(f"Feed error: {e}")

def load_finance_state():
    if os.path.exists(FINANCE_JSON):
        with open(FINANCE_JSON,"r") as f: return json.load(f)
    return {
        "deficit": -50000.0,
        "autonomy_fund": 100.0,
        "total_revenue": 0.0,
        "total_expenses": 0.0,
        "weekly_records": [],
        "launch_date": "2026-03-30",
        "experiments": []
    }

def save_finance_state(state):
    with open(FINANCE_JSON,"w") as f: json.dump(state, f, indent=2)

def get_gumroad_revenue(days=7):
    try:
        after = (datetime.datetime.now()-datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        res = requests.get(f"{GUMROAD_BASE}/sales",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},
            params={"after":after},timeout=15)
        data = res.json()
        if data.get("success"):
            sales = data.get("sales",[])
            total = sum(float(s.get("price",0)) for s in sales) / 100
            return total, len(sales)
        return 0.0, 0
    except Exception as e:
        log(f"Gumroad revenue error: {e}")
        return 0.0, 0

def generate_weekly_report(state, revenue_7d, sales_7d):
    today = datetime.datetime.now()
    launch = datetime.datetime.strptime(state["launch_date"], "%Y-%m-%d")
    days_running = (today - launch).days
    weeks_running = days_running // 7
    weeks_remaining = max(0, 26 - weeks_running)

    weekly_target = abs(state["deficit"]) / max(weeks_remaining, 1)
    monthly_target = weekly_target * 4

    # Phase tracking
    if days_running <= 21:
        phase = "Phase 1 — Stabilize (Weeks 1-3)"
        phase_target = "Operational clarity, 20 micro-offers, pick top 3"
    elif days_running <= 56:
        phase = "Phase 2 — Revenue Experiments (Weeks 4-8)"
        phase_target = "Target: $500-$2,000 from early wins"
    elif days_running <= 112:
        phase = "Phase 3 — Systemized Income (Months 3-4)"
        phase_target = "Target: $5k-$12k cumulative by Month 4"
    else:
        phase = "Phase 4 — Scale & Optimize (Months 5-6)"
        phase_target = "Target: $10k-$20k/month, eliminate deficit"

    prompt = f"""You are Penelope, financial intelligence officer for Guerilla Holdings.
Generate the weekly financial report for Sydney.

FINANCIAL DATA:
- Deficit: ${state['deficit']:,.2f}
- Autonomy Fund: ${state['autonomy_fund']:.2f}
- Total Revenue to Date: ${state['total_revenue']:.2f}
- Revenue Last 7 Days: ${revenue_7d:.2f}
- Sales Last 7 Days: {sales_7d}
- Days Running: {days_running}
- Weeks Remaining: {weeks_remaining}
- Weekly Target Needed: ${weekly_target:,.2f}/week to hit goal
- Monthly Target Needed: ${monthly_target:,.2f}/month
- Current Phase: {phase}
- Phase Target: {phase_target}

Generate this weekly financial report:

💰 *GUERILLA HOLDINGS — WEEKLY FINANCIAL REPORT*
*Week {weeks_running + 1} · {today.strftime("%B %d, %Y")}*
━━━━━━━━━━━━━━━━━━━━━━

📊 *FINANCIAL SNAPSHOT*
• Deficit: ${state['deficit']:,.2f}
• Revenue this week: ${revenue_7d:.2f}
• Sales this week: {sales_7d}
• Total revenue to date: ${state['total_revenue']:.2f}
• Autonomy fund: ${state['autonomy_fund']:.2f}

🎯 *PROGRESS TO GOAL*
• Weekly target needed: ${weekly_target:,.2f}
• This week vs target: (on track / behind / ahead — by how much)
• Projected completion at current rate: (date or "need to accelerate")
• % of way to eliminating deficit: (calculate)

📈 *CURRENT PHASE*
{phase}
Target: {phase_target}
Status: (on track/behind/ahead with specific reasoning)

💡 *FINANCIAL RECOMMENDATIONS*
1. (Highest-leverage action to increase revenue this week — specific)
2. (Product or pricing adjustment to make)
3. (Experiment to run with $25 or less)

⚠️ *FINANCIAL RISKS*
• (Any risks to the revenue plan)

🔮 *NEXT WEEK FORECAST*
• Expected revenue: $X-$Y range based on current trajectory
• Key milestone to hit

━━━━━━━━━━━━━━━━━━━━━━
_Next report: {(today + datetime.timedelta(days=7)).strftime("%B %d, %Y")}_
_— Penelope, Guerilla Holdings Finance_"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(response, "text", "Report failed.")
    except Exception as e:
        return f"Report generation error: {e}"

def update_ledger(state, revenue_7d, sales_7d):
    today = datetime.datetime.now()
    week_entry = {
        "week": today.strftime("%Y-W%U"),
        "date": today.strftime("%Y-%m-%d"),
        "revenue": revenue_7d,
        "sales": sales_7d,
        "expenses": 0.0,
        "net": revenue_7d,
        "balance": state["total_revenue"] + revenue_7d
    }

    # Update state
    state["total_revenue"] = round(state["total_revenue"] + revenue_7d, 2)
    state["weekly_records"].append(week_entry)
    state["deficit"] = round(-50000 + state["total_revenue"], 2)

    # Update ledger markdown
    with open(LEDGER_FILE, "a") as f:
        f.write(f"\n| {today.strftime('%Y-%m-%d')} | Week {len(state['weekly_records'])} revenue | $0 | revenue | ${revenue_7d:.2f} | logged | {sales_7d} sales |")
    with open(ROI_LOG, "a") as f:
        f.write(f"\n| {today.strftime('%Y-%m-%d')} | Weekly total | Gumroad | ${revenue_7d:.2f} | $0 | ${revenue_7d:.2f} | active |")

    save_finance_state(state)
    return state

def run_financial_tracker():
    log("="*50)
    log("FINANCIAL TRACKER RUNNING")
    log("="*50)

    state = load_finance_state()
    revenue_7d, sales_7d = get_gumroad_revenue(7)
    log(f"7-day revenue: ${revenue_7d:.2f} | Sales: {sales_7d}")

    state = update_ledger(state, revenue_7d, sales_7d)
    report = generate_weekly_report(state, revenue_7d, sales_7d)

    # Save report
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    fname = f"{BASE}/finance/{date_str}_weekly_report.md"
    with open(fname, "w") as f:
        f.write(report)
    log(f"Report saved: {fname}")

    _tg_emergency_only(report)
    post_to_feed("Weekly Financial Report",
        f"Revenue: ${revenue_7d:.2f} | Sales: {sales_7d} | Deficit: ${state['deficit']:,.2f}",
        "success")

    log(f"DONE — Deficit: ${state['deficit']:,.2f}")

if __name__ == "__main__":
    log("Financial Tracker starting")
    log("Runs every Monday at 08:30")

    # Run immediately
    run_financial_tracker()

    while True:
        now = datetime.datetime.now()
        # Run every Monday at 08:30
        if now.weekday() == 0 and now.hour == 8 and now.minute == 30:
            run_financial_tracker()
        time.sleep(60)
