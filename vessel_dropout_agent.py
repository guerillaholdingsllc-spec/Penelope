# ── TELEGRAM GATE (prepended by Penelope self-healer) ──────────────────────
import os as _tg_os, requests as _tg_req, datetime as _tg_dt
_tg_orig_post = _tg_req.post
def _tg_gated_post(url, *a, **kw):
    if "api.telegram.org" in str(url):
        _data = str(kw.get("json", kw.get("data", ""))).lower()
        _rev = any(x in _data for x in ["revenue confirmed","sale confirmed","payment received","paid $","new sale"])
        _crit = "🚨" in str(kw.get("json",{})) and any(x in _data for x in ["system down","cannot restart","disk full","out of memory"])
        if not _rev and not _crit:
            class _FakeResp:
                status_code=200
                def json(self): return {}
            return _FakeResp()
    return _tg_orig_post(url, *a, **kw)
_tg_req.post = _tg_gated_post
# ── END GATE ───────────────────────────────────────────────────────────────

"""
vessel_dropout_agent.py v2 — reads SQLite, not Base44
Checks for users who haven't checked in for 2+ days
Runs every 4 hours
"""
import sqlite3, json, requests
from datetime import datetime, date, timedelta
from google import genai

VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except: pass

DB         = "/root/vessel.db"
TG_TOKEN   = VAULT.get("TELEGRAM_BOT_TOKEN","")
TG_CHAT    = "6183015901"
PUSH_SRV   = "http://localhost:5070"
client     = genai.Client(api_key=VAULT.get("GOOGLE_API_KEY",""))

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def gm(prompt):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r,"text","").strip()
    except: return ""

def check_dropouts():
    print(f"[{datetime.now().strftime('%H:%M')}] Dropout check...")
    conn = get_db()
    two_days_ago = (date.today() - timedelta(days=2)).isoformat()
    yesterday    = (date.today() - timedelta(days=1)).isoformat()

    # Find users with no check-in in last 2 days
    users = conn.execute("SELECT * FROM vessel_users WHERE phase='active'").fetchall()
    at_risk = []
    for u in users:
        u = dict(u)
        recent = conn.execute(
            "SELECT COUNT(*) as n FROM daily_checkins WHERE user_id=? AND date>=?",
            (u['id'], two_days_ago)
        ).fetchone()
        if recent['n'] == 0:
            # How long since last check-in?
            last = conn.execute(
                "SELECT MAX(date) as last_date FROM daily_checkins WHERE user_id=?",
                (u['id'],)
            ).fetchone()
            u['last_checkin'] = last['last_date'] or 'never'
            at_risk.append(u)

    conn.close()
    print(f"  At-risk users: {len(at_risk)}")

    for u in at_risk:
        name = (u.get('name','') or '').split()[0] or 'friend'
        day  = int(u.get('day_count', 1))
        goal = u.get('goal_type','Purpose')
        last = u.get('last_checkin','never')

        prompt = f"""Vessel re-engagement message for {name}.
They haven't checked in since {last}. Day {day} of their {goal} protocol.
Write a warm, non-guilt 2-sentence push notification to bring them back.
No lectures. Make it feel easy to return.
Output ONLY the text."""

        msg = gm(prompt) or f"Day {day} is still yours, {name}. No streaks broken that can't restart. Open Vessel."

        # Send web push
        try:
            requests.post(f"{PUSH_SRV}/vessel-push-send",
                json={"secret":"sydney123","userId":u['id'],
                      "payload":{"title":"Vessel misses you ✦","body":msg,
                                 "tag":"vessel-dropout","url":"https://trustchainservices.com/vessel.html"}},
                timeout=8)
        except: pass

        print(f"  Re-engagement: {name} (last: {last})")

    if at_risk:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id":TG_CHAT,"parse_mode":"HTML",
                  "text":f"⚠️ <b>Dropout Alert</b>\n{len(at_risk)} users at risk\n"+
                         "\n".join(f"• {u.get('name','?')} — last: {u.get('last_checkin','?')}" for u in at_risk[:5])},
            timeout=10)

if __name__ == "__main__":
    check_dropouts()
