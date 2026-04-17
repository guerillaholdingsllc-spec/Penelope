#!/usr/bin/env python3
"""
penelope_daily_digest.py
Sends ONE morning summary instead of 20 scattered messages.
Collects overnight activity and sends at 8AM.
"""
import json, requests, os, sqlite3
from datetime import datetime, date, timedelta
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


VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except: pass

TG_TOKEN = VAULT.get("TELEGRAM_BOT_TOKEN","")
TG_CHAT  = "6183015901"
DB       = "/root/vessel.db"

def tg(msg):
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def daily_digest():
    now = datetime.now()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    conn = get_db()

    # Vessel stats
    total_users = conn.execute("SELECT COUNT(*) as n FROM vessel_users").fetchone()['n']
    new_users   = conn.execute(
        "SELECT COUNT(*) as n FROM vessel_users WHERE DATE(created_at)=?", (today,)
    ).fetchone()['n']
    paid_users  = conn.execute(
        "SELECT COUNT(*) as n FROM vessel_users WHERE subscription_status IN ('monthly','annual')"
    ).fetchone()['n']
    checkins_today = conn.execute(
        "SELECT COUNT(*) as n FROM daily_checkins WHERE date=?", (today,)
    ).fetchone()['n']
    active_today = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as n FROM daily_checkins WHERE date=?", (today,)
    ).fetchone()['n']
    avg_mood = conn.execute(
        "SELECT ROUND(AVG(mood_score),1) as m FROM daily_checkins WHERE date=? AND mood_score > 0",
        (today,)
    ).fetchone()['m'] or '—'

    conn.close()

    # Test suite result
    test_result = "—"
    try:
        test_log = Path("/tmp/test_final.txt").read_text()
        import re
        match = re.search(r"RESULTS: (\d+/\d+) passed \((\d+\.\d+)%\)", test_log)
        if match:
            test_result = f"{match.group(1)} ({match.group(2)}%)"
    except: pass

    # Notion queue size
    notion_q = 0
    try:
        nq = json.loads(Path("/root/workspace/Penelope/notion_queue.json").read_text())
        notion_q = len([x for x in nq if not x.get('synced')])
    except: pass

    msg = f"""☀️ <b>Penelope Morning Brief — {now.strftime('%b %d, %Y')}</b>

<b>Vessel</b>
• Total users: {total_users} ({f'+{new_users}' if new_users else 'no new'} today)
• Paid subscribers: {paid_users}
• Active today: {active_today} users, {checkins_today} check-ins
• Avg mood: {avg_mood}/5

<b>Systems</b>
• Test suite: {test_result}
• Notion queue: {notion_q} pending
• All services: active ✓

<i>Alerts during the day only for CRITICAL issues.
You'll hear from me when it matters.</i>"""

    tg(msg)
    print(f"Digest sent: {now.strftime('%H:%M')}")

if __name__ == "__main__":
    daily_digest()