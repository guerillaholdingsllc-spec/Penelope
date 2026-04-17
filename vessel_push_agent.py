"""
vessel_push_agent.py v3
Reads from SQLite DB (vessel.db) — real per-user check-in data
Sends AI-personalized web push notifications to customers
Falls back to Telegram for debugging
"""
import os, json, requests, sqlite3
from datetime import datetime, date
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


VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except: pass

GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY","")
TG_TOKEN       = VAULT.get("TELEGRAM_BOT_TOKEN","")
TG_CHAT        = "6183015901"
DB             = "/root/vessel.db"
PUSH_SERVER    = "http://localhost:5070"
API_URL        = "http://localhost:5101/vessel"

client = genai.Client(api_key=GOOGLE_API_KEY)

def gm(prompt):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r,"text","").strip()
    except: return ""

def tg_debug(msg):
    """Only send to Telegram for operational monitoring — not customer notifications"""
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_active_users():
    """Get all active users with their today's check-in status"""
    conn = get_db()
    today = date.today().isoformat()
    users = conn.execute(
        "SELECT * FROM vessel_users WHERE phase='active' ORDER BY created_at"
    ).fetchall()
    result = []
    for u in users:
        u = dict(u)
        # Parse goals
        try: u['goals'] = json.loads(u.get('goals','[]'))
        except: u['goals'] = [u.get('goal_type','Purpose')]
        # Get today's check-ins
        checkins = conn.execute(
            "SELECT * FROM daily_checkins WHERE user_id=? AND date=?",
            (u['id'], today)
        ).fetchall()
        checkins = [dict(c) for c in checkins]
        u['today_morning'] = any(c['session_completed'] for c in checkins)
        u['today_action']  = any(c['action_completed'] for c in checkins)
        u['today_evening'] = any(c['session_completed'] and c['mood_score'] for c in checkins)
        u['today_mood']    = next((c['mood_score'] for c in checkins if c['mood_score']), 0)
        # Get push subscription
        sub = conn.execute(
            "SELECT * FROM push_subscriptions WHERE user_id=? AND is_active=1 LIMIT 1",
            (u['id'],)
        ).fetchone()
        u['push_sub'] = dict(sub) if sub else None
        result.append(u)
    conn.close()
    return result

def send_web_push(user, payload):
    """Send real web push notification to user's device"""
    if not user.get('push_sub'):
        return False
    try:
        r = requests.post(f"{PUSH_SERVER}/vessel-push-send",
            json={"secret":"sydney123","userId":user['id'],"payload":payload},
            timeout=10)
        return r.ok
    except: return False

def morning():
    print(f"[{datetime.now().strftime('%H:%M')}] Morning notifications...")
    users = get_active_users()
    sent = 0
    for u in users:
        name = (u.get('name','') or '').split()[0] or 'friend'
        goal = (u.get('goals') or ['Purpose'])[0]
        day  = int(u.get('day_count',1))
        uss  = int(u.get('uss_score',50))
        loc  = u.get('dream_location','') or ''

        prompt = f"""You are Vessel, a 365-day manifestation protocol app.
Write a SHORT powerful morning push notification for {name}.
Goal: {goal} | Day: {day} of 365 | USS energy score: {uss}/100 | Dream location: {loc}

2 sentences max, 180 chars max:
- Personal to their goal and day number  
- Warm, slightly cosmic, NOT generic or cheesy
- End with one action they can take RIGHT NOW
Output ONLY the notification text."""

        msg = gm(prompt) or f"Day {day} ✦ Good morning, {name}. Your {goal.lower()} protocol starts now. Open Vessel."

        payload = {
            "title": f"Vessel · Day {day}",
            "body": msg,
            "icon": "/vessel-icon.png",
            "tag": "vessel-morning",
            "type": "morning",
            "url": "https://trustchainservices.com/vessel.html"
        }

        if send_web_push(u, payload):
            sent += 1
            print(f"  Push sent: {name} (Day {day}, {goal})")
        else:
            print(f"  No push sub: {name} — skipping")

    tg_debug(f"🌅 <b>Vessel Morning Push</b>\nSent to {sent}/{len(users)} users")
    print(f"Sent: {sent}/{len(users)}")

def action_nudge():
    print(f"[{datetime.now().strftime('%H:%M')}] Action nudge check...")
    users = get_active_users()
    sent = 0
    for u in users:
        # Only nudge: morning done, action NOT done
        if not u['today_morning'] or u['today_action']:
            continue
        name = (u.get('name','') or '').split()[0] or 'friend'
        goal = (u.get('goals') or ['Purpose'])[0]
        day  = int(u.get('day_count',1))

        action_map = {
            "Wealth": "Make one financial move — a call, a pitch, an email.",
            "Health": "Move your body for 20 minutes. Your body is waiting.",
            "Body":   "Log your meals. Hit your water goal.",
            "Love":   "Reach out to someone who matters today.",
            "Purpose":"30 focused minutes on your thing. Close the other tabs.",
            "Peace":  "10 minutes of stillness. Phone down. Just breathe."
        }
        action = action_map.get(goal, "Take one aligned action toward your biggest goal.")

        prompt = f"""Vessel midday action nudge for {name}.
Morning done ✓ | Action not done yet | Goal: {goal} | Day {day}
1-2 sentences, 160 chars max, warm + direct:
- Acknowledge strong morning start
- The action is what moves the needle
Output ONLY the text."""

        msg = gm(prompt) or f"Morning done ✦ Now the part that matters. {action}"

        payload = {
            "title": "⚡ Action Time",
            "body": msg,
            "icon": "/vessel-icon.png",
            "tag": "vessel-action",
            "type": "action",
            "url": "https://trustchainservices.com/vessel.html"
        }

        if send_web_push(u, payload):
            sent += 1
            print(f"  Action nudge: {name}")

    tg_debug(f"⚡ <b>Vessel Action Nudges</b>\nSent to {sent} users who need it")
    print(f"Nudges sent: {sent}")

def evening_nudge():
    print(f"[{datetime.now().strftime('%H:%M')}] Evening nudge check...")
    users = get_active_users()
    sent = 0
    for u in users:
        if u['today_evening']:
            continue
        name = (u.get('name','') or '').split()[0] or 'friend'
        goal = (u.get('goals') or ['Purpose'])[0]
        day  = int(u.get('day_count',1))
        done_count = sum([u['today_morning'], u['today_action']])
        context = "morning + action complete" if done_count==2 else f"{done_count} sessions done"

        prompt = f"""Vessel evening check-in reminder for {name}.
Goal: {goal} | Day: {day} | Today: {context}
1-2 sentences, 160 chars max, reflective/warm end-of-day tone.
The check-in takes 2 minutes and closes the loop.
Output ONLY the text."""

        msg = gm(prompt) or f"Day {day} isn't complete yet, {name}. 2 minutes to reflect and close the loop."

        payload = {
            "title": "🌙 Evening Check-in",
            "body": msg,
            "icon": "/vessel-icon.png",
            "tag": "vessel-evening",
            "type": "evening",
            "url": "https://trustchainservices.com/vessel.html"
        }

        if send_web_push(u, payload):
            sent += 1
            print(f"  Evening nudge: {name}")

    tg_debug(f"🌙 <b>Vessel Evening Nudges</b>\nSent to {sent} users")
    print(f"Nudges sent: {sent}")

import sys
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv)>1 else "morning"
    if mode=="morning":     morning()
    elif mode=="action":    action_nudge()
    elif mode=="evening":   evening_nudge()