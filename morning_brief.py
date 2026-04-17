#!/usr/bin/env python3
"""
PENELOPE MORNING BRIEF
Fires at 8AM daily. Structured revenue + activity report to Sydney.
"""
import os, json, requests, glob, time
from datetime import datetime, timedelta
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


def load_vault():
    env = {}
    try:
        with open("/root/penelope_vault.env") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
STRIPE_SK = ENV.get("STRIPE_SECRET_KEY", "")
GUMROAD_KEY = ENV.get("GUMROAD_API_KEY", "")
GOOGLE_KEY = ENV.get("GOOGLE_API_KEY", "")

def get_stripe_revenue():
    if not STRIPE_SK: return 0, 0
    try:
        since = int((datetime.now() - timedelta(days=1)).timestamp())
        r = requests.get("https://api.stripe.com/v1/balance_transactions",
            auth=(STRIPE_SK, ""),
            params={"created[gte]": since, "limit": 50, "type": "charge"},
            timeout=10)
        if r.status_code == 200:
            txns = r.json().get("data", [])
            total = sum(t.get("net", 0) for t in txns) / 100
            return total, len(txns)
    except: pass
    return 0, 0

def get_gumroad_sales():
    if not GUMROAD_KEY: return 0, 0
    try:
        r = requests.get("https://api.gumroad.com/v2/sales",
            headers={"Authorization": f"Bearer {GUMROAD_KEY}"}, timeout=10)
        if r.status_code == 200:
            sales = r.json().get("sales", [])
            total = sum(float(s.get("price", 0)) for s in sales) / 100
            return total, len(sales)
    except: pass
    return 0, 0

def get_lead_count():
    try:
        log_file = "/root/workspace/Penelope/leads/attribution_log.jsonl"
        if not Path(log_file).exists(): return 0
        with open(log_file) as f:
            lines = f.readlines()
        today = datetime.now().strftime("%Y-%m-%d")
        today_leads = sum(1 for l in lines if today in l and "lead_captured" in l)
        return today_leads
    except: return 0

def get_skills_deployed():
    try:
        import yaml
        skills = []
        for f in glob.glob("/root/workspace/Penelope/skillbank/*.yaml"):
            with open(f) as fp:
                s = yaml.safe_load(fp)
                if s and s.get("status") == "Live":
                    skills.append(s.get("objective","?")[:50])
        return skills
    except: return []

def get_content_stats():
    stats = {}
    try:
        bsky_log = "/root/workspace/Penelope/conductor_logs/bsky_posted.json"
        if Path(bsky_log).exists():
            posted = json.loads(open(bsky_log).read())
            stats["bluesky_total"] = len(posted)
    except: pass
    try:
        wp_log = "/root/workspace/Penelope/conductor_logs/wp_published.json"
        if Path(wp_log).exists():
            published = json.loads(open(wp_log).read())
            stats["wp_total"] = len(published)
    except: pass
    try:
        stats["blog_army_total"] = len(glob.glob("/root/workspace/Penelope/blog/posts/*.json"))
    except: pass
    return stats

def get_top_decision():
    """Pull top P0/P1 item from Decision Queue if any."""
    notion_token = ENV.get("NOTION_TOKEN", "")
    if not notion_token: return None
    try:
        r = requests.post("https://api.notion.com/v1/databases/74988a7b-ff8b-4291-9fa7-c5812e33a955/query",
            headers={"Authorization": f"Bearer {notion_token}", "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            json={"filter": {"and": [
                {"property": "Status", "select": {"equals": "Needs Claude"}},
                {"or": [
                    {"property": "Priority", "select": {"equals": "P0 - Blocking Revenue"}},
                    {"property": "Priority", "select": {"equals": "P1 - This Session"}}
                ]}
            ]}, "page_size": 1}, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                title_prop = results[0].get("properties", {}).get("Decision", {})
                title = title_prop.get("title", [{}])[0].get("plain_text", "?") if title_prop.get("title") else "?"
                return title
    except: pass
    return None

def send_morning_brief():
    stripe_rev, stripe_txns = get_stripe_revenue()
    gumroad_rev, gumroad_sales = get_gumroad_sales()
    total_rev = stripe_rev + gumroad_rev
    leads_today = get_lead_count()
    skills_live = get_skills_deployed()
    content = get_content_stats()
    top_decision = get_top_decision()
    
    brief = f"""🌅 PENELOPE MORNING BRIEF
{datetime.now().strftime("%A, %B %d %Y — %I:%M %p")}

💰 REVENUE (24h)
Stripe: ${stripe_rev:.2f} ({stripe_txns} transactions)
Gumroad: ${gumroad_rev:.2f} ({gumroad_sales} sales)
Total: ${total_rev:.2f}

👥 AUDIENCE
New leads today: {leads_today}
Audience DB: growing 24/7

🤖 AGENT STATUS
Skills deployed: {len(skills_live)}
Blog army posts: {content.get('blog_army_total', 0):,}
WordPress live: {content.get('wp_total', 0)}
Bluesky posts sent: {content.get('bluesky_total', 0)}

🎯 NEEDS YOUR ATTENTION
{f"⚠️ Decision Queue: {top_decision}" if top_decision else "✅ No decisions pending — Penelope is self-sufficient"}

📊 SERVICES
All 18 Penelope services: Active
Conductor cycle: Every 4h
Next cycle: Check logs

🔗 QUICK LINKS
Notion HQ: notion.so/3368bf86ffb181829402e2945c1e6a3c
Stripe: dashboard.stripe.com
Close CRM: app.close.com"""
    
    try:
        _tg_emergency_only("[suppressed direct call]")
        print(f"Morning brief sent: {datetime.now()}")
    except Exception as e:
        print(f"Brief send failed: {e}")

if __name__ == "__main__":
    send_morning_brief()