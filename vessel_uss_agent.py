"""
vessel_uss_agent.py v2 — reads/writes SQLite, not Base44
USS Score = rolling mood average (7-day) mapped to 0-100
Runs nightly at 3AM
"""
import sqlite3, json
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

DB = "/root/vessel.db"
client = genai.Client(api_key=VAULT.get("GOOGLE_API_KEY",""))

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def compute_uss(user_id):
    """Compute USS score from last 7 days of check-ins"""
    conn = get_db()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    checkins = conn.execute(
        "SELECT mood_score, session_completed, action_completed FROM daily_checkins "
        "WHERE user_id=? AND date>=? ORDER BY date DESC",
        (user_id, week_ago)
    ).fetchall()
    conn.close()
    if not checkins:
        return 50  # default

    moods    = [c['mood_score'] for c in checkins if c['mood_score']]
    sessions = sum(1 for c in checkins if c['session_completed'])
    actions  = sum(1 for c in checkins if c['action_completed'])
    total    = len(checkins)

    mood_avg    = (sum(moods)/len(moods)/5) if moods else 0.5
    session_pct = sessions/max(total,1)
    action_pct  = actions/max(total,1)

    # Weighted: 40% mood, 35% session completion, 25% action completion
    uss = round((mood_avg*0.4 + session_pct*0.35 + action_pct*0.25) * 100)
    return max(1, min(100, uss))

def run_batch():
    print(f"[{datetime.now().strftime('%H:%M')}] USS batch update...")
    conn = get_db()
    users = conn.execute("SELECT id, name FROM vessel_users WHERE phase='active'").fetchall()
    updated = 0
    for u in users:
        uss = compute_uss(u['id'])
        conn.execute("UPDATE vessel_users SET uss_score=?, updated_at=? WHERE id=?",
                     (uss, datetime.utcnow().isoformat(), u['id']))
        print(f"  {u['name']}: USS={uss}")
        updated += 1
    conn.commit(); conn.close()
    print(f"Updated {updated} users")

if __name__ == "__main__":
    run_batch()
