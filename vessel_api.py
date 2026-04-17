"""
vessel_api.py — Vessel database API
SQLite backend, runs on port 5100
Handles all user data for Vessel Adult + Vessel Kids
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, os, json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow requests from trustchainservices.com

DB = '/root/vessel.db'
SECRET = 'vessel_api_2026'

# ── DB INIT ──────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Adult users
    c.execute('''CREATE TABLE IF NOT EXISTS vessel_users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT,
        goals TEXT,          -- JSON array
        goal_type TEXT,
        height_ft REAL, height_in REAL,
        weight REAL, body_goal REAL,
        income_bracket TEXT, income_goal TEXT,
        zip TEXT, dream_location TEXT,
        day_count INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 0,
        uss_score INTEGER DEFAULT 50,
        phase TEXT DEFAULT 'active',
        subscription_status TEXT DEFAULT 'free',
        referral_code TEXT,
        referral_count INTEGER DEFAULT 0,
        badges TEXT,         -- JSON array
        start_date TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
    
    # Daily check-ins
    c.execute('''CREATE TABLE IF NOT EXISTS daily_checkins (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        date TEXT NOT NULL,
        mood_score INTEGER,
        session_completed INTEGER DEFAULT 0,
        action_completed INTEGER DEFAULT 0,
        intention TEXT,
        action_note TEXT,
        reflection TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES vessel_users(id)
    )''')
    
    # Vision board items
    c.execute('''CREATE TABLE IF NOT EXISTS vision_board (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        image_url TEXT,
        caption TEXT,
        category TEXT,
        position INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES vessel_users(id)
    )''')
    
    # Custom affirmations
    c.execute('''CREATE TABLE IF NOT EXISTS affirmations (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        text TEXT NOT NULL,
        category TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES vessel_users(id)
    )''')
    
    # Kids profiles
    c.execute('''CREATE TABLE IF NOT EXISTS vessel_kids (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        goals TEXT,           -- JSON array
        day_count INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 0,
        morning_sessions INTEGER DEFAULT 0,
        actions_done INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )''')
    
    # Kids daily check-ins
    c.execute('''CREATE TABLE IF NOT EXISTS kids_checkins (
        id TEXT PRIMARY KEY,
        kid_id TEXT NOT NULL,
        date TEXT NOT NULL,
        mood INTEGER,
        action_done INTEGER DEFAULT 0,
        intention TEXT,
        gratitude TEXT,
        created_at TEXT,
        FOREIGN KEY (kid_id) REFERENCES vessel_kids(id)
    )''')

    # Push subscriptions
    c.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        endpoint TEXT UNIQUE NOT NULL,
        auth_key TEXT,
        p256dh_key TEXT,
        device_type TEXT DEFAULT 'web',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()
    print("DB initialized:", DB)

def gen_id():
    import uuid
    return str(uuid.uuid4()).replace('-','')[:16]

def now():
    return datetime.utcnow().isoformat()

def auth(req):
    return req.headers.get('X-Vessel-Key') == SECRET or req.json and req.json.get('secret') == SECRET

# ── ADULT USER ROUTES ────────────────────────────
@app.route('/vessel/user', methods=['POST'])
def upsert_user():
    d = request.json
    conn = get_db(); c = conn.cursor()
    email = d.get('email','').lower().strip()
    if not email:
        return jsonify({'error':'email required'}), 400
    
    # Check if exists
    existing = c.execute('SELECT id FROM vessel_users WHERE email=?',(email,)).fetchone()
    
    if existing:
        uid = existing['id']
        # Update fields that were sent
        fields = ['name','goals','goal_type','height_ft','height_in','weight','body_goal',
                  'income_bracket','income_goal','zip','dream_location','day_count','streak',
                  'uss_score','phase','subscription_status','referral_code','referral_count','badges']
        updates = {f: json.dumps(d[f]) if isinstance(d.get(f), list) else d[f] 
                   for f in fields if f in d}
        updates['updated_at'] = now()
        if updates:
            set_clause = ', '.join(f'{k}=?' for k in updates)
            c.execute(f'UPDATE vessel_users SET {set_clause} WHERE id=?', 
                     list(updates.values()) + [uid])
    else:
        uid = gen_id()
        goals = d.get('goals', [d.get('goal_type','Purpose')])
        c.execute('''INSERT INTO vessel_users 
            (id,email,name,goals,goal_type,height_ft,height_in,weight,body_goal,
             income_bracket,income_goal,zip,dream_location,day_count,streak,uss_score,
             phase,subscription_status,referral_code,referral_count,badges,start_date,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (uid, email, d.get('name',''), json.dumps(goals), d.get('goal_type','Purpose'),
             d.get('height_ft',0), d.get('height_in',0), d.get('weight',0), d.get('body_goal',0),
             d.get('income_bracket',''), d.get('income_goal',''), d.get('zip',''), d.get('dream_location',''),
             d.get('day_count',1), d.get('streak',0), d.get('uss_score',50),
             d.get('phase','active'), d.get('subscription_status','free'),
             d.get('referral_code',''), d.get('referral_count',0),
             json.dumps(d.get('badges',['Founding Member'])), d.get('start_date', now()[:10]),
             now(), now()))
    
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': uid})

@app.route('/vessel/user/<email>', methods=['GET'])
def get_user(email):
    conn = get_db(); c = conn.cursor()
    row = c.execute('SELECT * FROM vessel_users WHERE email=?', (email.lower(),)).fetchone()
    conn.close()
    if not row:
        return jsonify({'found': False}), 404
    u = dict(row)
    # Parse JSON fields
    for f in ['goals','badges']:
        try: u[f] = json.loads(u[f]) if u[f] else []
        except: u[f] = []
    u['found'] = True
    return jsonify(u)

@app.route('/vessel/user/<user_id>/progress', methods=['POST'])
def update_progress(user_id):
    d = request.json; conn = get_db(); c = conn.cursor()
    c.execute('UPDATE vessel_users SET day_count=?, streak=?, uss_score=?, updated_at=? WHERE id=?',
              (d.get('day_count',1), d.get('streak',0), d.get('uss_score',50), now(), user_id))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

# ── CHECK-IN ROUTES ──────────────────────────────
@app.route('/vessel/checkin', methods=['POST'])
def save_checkin():
    d = request.json; conn = get_db(); c = conn.cursor()
    cid = gen_id()
    c.execute('''INSERT INTO daily_checkins 
        (id,user_id,date,mood_score,session_completed,action_completed,intention,action_note,reflection,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (cid, d.get('user_id'), d.get('date',now()[:10]), d.get('mood_score',0),
         1 if d.get('session_completed') else 0, 1 if d.get('action_completed') else 0,
         d.get('intention',''), d.get('action_note',''), d.get('reflection',''), now()))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': cid})

@app.route('/vessel/checkins/<user_id>', methods=['GET'])
def get_checkins(user_id):
    conn = get_db(); c = conn.cursor()
    rows = c.execute('SELECT * FROM daily_checkins WHERE user_id=? ORDER BY date DESC LIMIT 90',
                     (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── KIDS ROUTES ──────────────────────────────────
@app.route('/vessel/kids', methods=['POST'])
def upsert_kid():
    d = request.json; conn = get_db(); c = conn.cursor()
    kid_id = d.get('id') or gen_id()
    existing = c.execute('SELECT id FROM vessel_kids WHERE id=?',(kid_id,)).fetchone()
    if existing:
        c.execute('''UPDATE vessel_kids SET name=?,age=?,goals=?,day_count=?,streak=?,
                     morning_sessions=?,actions_done=?,updated_at=? WHERE id=?''',
                  (d.get('name'), d.get('age'), json.dumps(d.get('goals',[])),
                   d.get('day_count',1), d.get('streak',0),
                   d.get('morning_sessions',0), d.get('actions_done',0), now(), kid_id))
    else:
        c.execute('''INSERT INTO vessel_kids (id,name,age,goals,day_count,streak,
                     morning_sessions,actions_done,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?)''',
                  (kid_id, d.get('name'), d.get('age'), json.dumps(d.get('goals',[])),
                   d.get('day_count',1), d.get('streak',0),
                   d.get('morning_sessions',0), d.get('actions_done',0), now(), now()))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': kid_id})

@app.route('/vessel/kids/<kid_id>', methods=['GET'])
def get_kid(kid_id):
    conn = get_db(); c = conn.cursor()
    row = c.execute('SELECT * FROM vessel_kids WHERE id=?',(kid_id,)).fetchone()
    conn.close()
    if not row: return jsonify({'found':False}), 404
    k = dict(row)
    try: k['goals'] = json.loads(k['goals']) if k['goals'] else []
    except: k['goals'] = []
    k['found'] = True
    return jsonify(k)

@app.route('/vessel/kids/checkin', methods=['POST'])
def kids_checkin():
    d = request.json; conn = get_db(); c = conn.cursor()
    cid = gen_id()
    c.execute('''INSERT INTO kids_checkins 
        (id,kid_id,date,mood,action_done,intention,gratitude,created_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (cid, d.get('kid_id'), d.get('date',now()[:10]), d.get('mood',0),
         1 if d.get('action_done') else 0, d.get('intention',''), d.get('gratitude',''), now()))
    # Update kid's session counts
    field = 'morning_sessions' if d.get('type')=='morning' else 'actions_done' if d.get('type')=='action' else None
    if field:
        c.execute(f'UPDATE vessel_kids SET {field}={field}+1, updated_at=? WHERE id=?',
                  (now(), d.get('kid_id')))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': cid})

@app.route('/vessel/kids/checkins/<kid_id>', methods=['GET'])
def get_kids_checkins(kid_id):
    conn = get_db(); c = conn.cursor()
    rows = c.execute('SELECT * FROM kids_checkins WHERE kid_id=? ORDER BY date DESC LIMIT 90',
                     (kid_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── AI CONTEXT ENDPOINT ──────────────────────────
# Penelope calls this to get full user context for AI personalization
@app.route('/vessel/ai-context/<email>', methods=['GET'])
def ai_context(email):
    conn = get_db(); c = conn.cursor()
    user = c.execute('SELECT * FROM vessel_users WHERE email=?',(email.lower(),)).fetchone()
    if not user: 
        conn.close()
        return jsonify({'error':'not found'}), 404
    u = dict(user)
    for f in ['goals','badges']:
        try: u[f] = json.loads(u[f]) if u[f] else []
        except: u[f] = []
    # Last 7 check-ins
    checkins = c.execute(
        'SELECT * FROM daily_checkins WHERE user_id=? ORDER BY date DESC LIMIT 7',
        (u['id'],)).fetchall()
    u['recent_checkins'] = [dict(r) for r in checkins]
    # Mood trend
    moods = [r['mood_score'] for r in checkins if r['mood_score']]
    u['avg_mood_7d'] = round(sum(moods)/len(moods),1) if moods else None
    u['sessions_this_week'] = len([r for r in checkins if r['session_completed']])
    u['actions_this_week'] = len([r for r in checkins if r['action_completed']])
    conn.close()
    return jsonify(u)

# ── HEALTH ───────────────────────────────────────
@app.route('/vessel/health', methods=['GET'])
def health():
    conn = get_db(); c = conn.cursor()
    users = c.execute('SELECT COUNT(*) as n FROM vessel_users').fetchone()['n']
    checkins = c.execute('SELECT COUNT(*) as n FROM daily_checkins').fetchone()['n']
    kids = c.execute('SELECT COUNT(*) as n FROM vessel_kids').fetchone()['n']
    conn.close()
    return jsonify({'status':'ok','users':users,'checkins':checkins,'kids':kids,'db':DB})


# ── CORPORATE INQUIRY ────────────────────────────
@app.route('/vessel/corporate-inquiry', methods=['POST'])
def corporate_inquiry():
    d = request.json
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS corporate_inquiries (
        id TEXT PRIMARY KEY, company_name TEXT, contact_email TEXT,
        employee_count TEXT, created_at TEXT)''')
    cid = gen_id()
    c.execute('INSERT INTO corporate_inquiries (id,company_name,contact_email,employee_count,created_at) VALUES (?,?,?,?,?)',
        (cid, d.get('company_name',''), d.get('contact_email',''), d.get('employee_count',''), now()))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': cid})


# ── STRIPE CHECKOUT ──────────────────────────────
import stripe as stripe_lib

_STRIPE_SK = _STRIPE_PK = ''
_PRICE_MO  = 'price_1TLIgfFATVhdolajkdxjzzEW'
_PRICE_YR  = 'price_1TLIgfFATVhdolajtesuYcOo'

try:
    with open('/root/penelope_vault.env') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line.startswith('STRIPE_SECRET_KEY='): _STRIPE_SK = _line.split('=',1)[1].strip()
            elif _line.startswith('STRIPE_PUBLISHABLE_KEY='): _STRIPE_PK = _line.split('=',1)[1].strip()
except: pass
stripe_lib.api_key = _STRIPE_SK

@app.route('/vessel/checkout', methods=['POST'])
def create_checkout():
    d = request.json
    plan = d.get('plan','monthly')
    user_id = d.get('user_id','')
    email   = d.get('email','')
    price_id = _PRICE_YR if plan=='annual' else _PRICE_MO
    try:
        session = stripe_lib.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{'price': price_id, 'quantity': 1}],
            success_url='https://trustchainservices.com/vessel.html?checkout=success&user_id='+user_id,
            cancel_url='https://trustchainservices.com/vessel.html?checkout=cancel',
            customer_email=email or None,
            metadata={'user_id': user_id, 'plan': plan},
            allow_promotion_codes=True,
        )
        return jsonify({'ok': True, 'url': session.url, 'session_id': session.id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/vessel/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig     = request.headers.get('Stripe-Signature','')
    ws = ''
    try:
        with open('/root/penelope_vault.env') as f:
            for line in f:
                if 'STRIPE_WEBHOOK_SECRET=' in line:
                    ws = line.split('=',1)[1].strip(); break
    except: pass
    try:
        event = stripe_lib.Webhook.construct_event(payload, sig, ws)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    if event['type'] == 'checkout.session.completed':
        s = event['data']['object']
        uid = s.get('metadata',{}).get('user_id','')
        plan = s.get('metadata',{}).get('plan','monthly')
        if uid:
            conn = get_db()
            conn.execute("UPDATE vessel_users SET subscription_status=?,updated_at=? WHERE id=?",(plan,now(),uid))
            conn.commit(); conn.close()
            print(f"Subscribed: {uid} -> {plan}")
    return jsonify({'ok': True})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5101)

