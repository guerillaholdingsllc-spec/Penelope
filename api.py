from flask import Flask, request, jsonify
import os
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


app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
API_SECRET = os.getenv("PENELOPE_API_SECRET", "sydney123")

client = genai.Client(api_key=GOOGLE_API_KEY)

def load_brain():
    try:
        path = "/root/workspace/Penelope/brain_dump.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Brain Read Error: {e}")
    return "No specific instructions found."

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json or {}
    secret = data.get("secret", "")
    if secret != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    knowledge = load_brain()
    prompt = f"""Instructions from your Word Docs:
{knowledge}

User Question:
{user_msg}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    reply = getattr(response, "text", None) or "No response."
    return jsonify({"response": reply})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Penelope API is running"})


@app.route('/')
def index():
    return open('/root/workspace/Penelope/chat.html').read()


@app.route('/feed', methods=['GET'])
def feed():
    import json, os
    path = '/root/workspace/Penelope/feed.json'
    if os.path.exists(path):
        return app.response_class(open(path).read(), mimetype='application/json')
    return app.response_class('[]', mimetype='application/json')




@app.route('/mission')
def mission():
    import json, os, datetime
    feed = []
    if os.path.exists('/root/workspace/Penelope/feed.json'):
        feed = json.loads(open('/root/workspace/Penelope/feed.json').read())
    blogs = sum(1 for i in feed if 'BlogAgent' in (i.get('title') or ''))
    affs = sum(1 for i in feed if 'AffiliateAgent' in (i.get('title') or ''))
    ebooks = sum(1 for i in feed if 'EbookAgent' in (i.get('title') or ''))
    seos = sum(1 for i in feed if 'SEOAgent' in (i.get('title') or ''))
    rows = ""
    for item in feed[:80]:
        ag = (item.get('title') or '').split(']')[0].replace('[','') if '[' in (item.get('title') or '') else 'Agent'
        title = (item.get('title') or '').split('] ')[-1] if '] ' in (item.get('title') or '') else (item.get('title') or '')
        preview = (item.get('content') or '').replace('**','')[:150].replace('\n',' ')
        clr = '#2ecc71' if item.get('status') == 'success' else '#e74c3c' if item.get('status') == 'error' else '#3498db'
        rows += f"""<tr><td style="color:#c9a84c;font-size:10px;white-space:nowrap;padding:6px 8px;border-bottom:1px solid #1a2030">{ag}</td><td style="font-size:10px;color:#6b7280;padding:6px 8px;border-bottom:1px solid #1a2030;white-space:nowrap">{item.get('time','')}</td><td style="padding:6px 8px;border-bottom:1px solid #1a2030"><div style="color:#d4cfc8;font-size:10px">{title[:80]}</div><div style="color:#4a5568;font-size:9px;margin-top:2px">{preview[:120]}...</div></td><td style="padding:6px 8px;border-bottom:1px solid #1a2030"><span style="color:{clr};border:1px solid {clr};font-size:8px;padding:1px 5px">{(item.get('status') or '').upper()}</span></td></tr>"""
    book_bars = ""
    books = ['The Awakening','Fractured Worlds','The Void Between','Architects of War','Last Covenant','Eternal Return']
    for i, b in enumerate(books):
        ch = sum(1 for x in feed if f'EbookAgent-Book{i+1}' in (x.get('title') or ''))
        pct = min(100, int((ch/24)*100))
        book_bars += f"""<div style="margin-bottom:8px"><div style="display:flex;justify-content:space-between;font-size:9px;color:#4a5568;margin-bottom:3px"><span style="color:#d4cfc8">Bk{i+1}: {b}</span><span>{min(ch,24)}/24 ch</span></div><div style="height:4px;background:#1a2030"><div style="height:100%;background:#7a6030;width:{pct}%"></div></div></div>"""
    now = datetime.datetime.now().strftime('%H:%M:%S')
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta http-equiv="refresh" content="30"><title>Mission Control</title><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet"><style>*{{box-sizing:border-box;margin:0;padding:0}}body{{background:#060708;color:#d4cfc8;font-family:'Share Tech Mono',monospace;min-height:100vh}}</style></head><body>
<div style="background:#0a0c0f;border-bottom:1px solid #7a6030;padding:12px 24px;display:flex;align-items:center;gap:16px;position:sticky;top:0;z-index:100">
<div style="width:8px;height:8px;border-radius:50%;background:#2ecc71;box-shadow:0 0 8px #2ecc71"></div>
<div style="font-family:'Orbitron',sans-serif;font-size:11px;font-weight:900;color:#c9a84c;letter-spacing:0.3em">GUERILLA HOLDINGS // MISSION CONTROL</div>
<div style="margin-left:auto;font-size:11px;color:#c9a84c">{now}</div>
<div style="display:flex;gap:20px;margin-left:16px;font-size:10px">
<div><div style="color:#4a5568;font-size:9px">AGENTS</div><div style="color:#c9a84c">25</div></div>
<div><div style="color:#4a5568;font-size:9px">TASKS DONE</div><div style="color:#c9a84c">{len(feed)}</div></div>
<div><div style="color:#4a5568;font-size:9px">STATUS</div><div style="color:#2ecc71">LIVE</div></div>
</div></div>
<div style="display:flex;background:#0a0c0f;border-bottom:1px solid #1a2030">
<div style="flex:1;padding:10px 16px;border-right:1px solid #1a2030"><div style="font-size:8px;color:#4a5568;letter-spacing:0.2em">BLOG POSTS</div><div style="font-family:'Orbitron',sans-serif;font-size:22px;color:#c9a84c">{blogs}</div><div style="font-size:8px;color:#4a5568">8 agents</div></div>
<div style="flex:1;padding:10px 16px;border-right:1px solid #1a2030"><div style="font-size:8px;color:#4a5568;letter-spacing:0.2em">AFFILIATE</div><div style="font-family:'Orbitron',sans-serif;font-size:22px;color:#c9a84c">{affs}</div><div style="font-size:8px;color:#4a5568">6 agents</div></div>
<div style="flex:1;padding:10px 16px;border-right:1px solid #1a2030"><div style="font-size:8px;color:#4a5568;letter-spacing:0.2em">EBOOK CH.</div><div style="font-family:'Orbitron',sans-serif;font-size:22px;color:#c9a84c">{ebooks}</div><div style="font-size:8px;color:#4a5568">6 books</div></div>
<div style="flex:1;padding:10px 16px;border-right:1px solid #1a2030"><div style="font-size:8px;color:#4a5568;letter-spacing:0.2em">SEO</div><div style="font-family:'Orbitron',sans-serif;font-size:22px;color:#c9a84c">{seos}</div><div style="font-size:8px;color:#4a5568">3 agents</div></div>
<div style="flex:1;padding:10px 16px"><div style="font-size:8px;color:#4a5568;letter-spacing:0.2em">TOTAL</div><div style="font-family:'Orbitron',sans-serif;font-size:22px;color:#c9a84c">{len(feed)}</div><div style="font-size:8px;color:#4a5568">all agents</div></div>
</div>
<div style="display:grid;grid-template-columns:280px 1fr;gap:1px;background:#1a2030">
<div style="background:#0e1114;padding:20px;overflow-y:auto">
<div style="font-family:'Orbitron',sans-serif;font-size:9px;color:#7a6030;letter-spacing:0.3em;border-bottom:1px solid #1a2030;padding-bottom:8px;margin-bottom:16px">// DEFICIT TRACKER</div>
<div style="text-align:center;padding:16px 0"><div style="font-family:'Orbitron',sans-serif;font-size:30px;font-weight:900;color:#e74c3c">-$50,000.00</div><div style="font-size:9px;color:#4a5568;letter-spacing:0.2em;margin-top:4px">CURRENT DEFICIT</div></div>
<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:9px;color:#4a5568;margin-bottom:4px"><span>Recovered</span><span>0%</span></div><div style="height:6px;background:#1a2030"><div style="height:100%;background:#c9a84c;width:0%"></div></div></div>
<div style="background:#0a0c0f;border:1px solid #1a7a42;padding:12px;margin:12px 0"><div style="font-size:9px;color:#1a7a42;letter-spacing:0.2em">// TOTAL EARNED</div><div style="font-family:'Orbitron',sans-serif;font-size:20px;color:#2ecc71">$0.00</div></div>
<div style="font-size:9px;color:#4a5568;margin-bottom:8px">Log earnings at /log-earning</div>
<div style="font-family:'Orbitron',sans-serif;font-size:9px;color:#7a6030;letter-spacing:0.3em;border-bottom:1px solid #1a2030;padding-bottom:8px;margin:16px 0 12px">// BOOKS PROGRESS</div>
{book_bars}
</div>
<div style="background:#0e1114">
<div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid #1a2030;background:#0a0c0f">
<div style="font-family:'Orbitron',sans-serif;font-size:9px;color:#7a6030;letter-spacing:0.3em">// LIVE OPERATIONS FEED</div>
<div style="width:6px;height:6px;border-radius:50%;background:#2ecc71"></div>
<div style="font-size:9px;color:#4a5568;margin-left:auto">{len(feed)} entries — auto-refreshes every 30s</div>
</div>
<div style="overflow-y:auto;max-height:calc(100vh - 200px)">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:#060708"><th style="text-align:left;padding:6px 8px;font-size:9px;color:#4a5568;letter-spacing:0.1em;font-weight:400">AGENT</th><th style="text-align:left;padding:6px 8px;font-size:9px;color:#4a5568;letter-spacing:0.1em;font-weight:400">TIME</th><th style="text-align:left;padding:6px 8px;font-size:9px;color:#4a5568;letter-spacing:0.1em;font-weight:400">TASK</th><th style="padding:6px 8px;font-size:9px;color:#4a5568;letter-spacing:0.1em;font-weight:400">STATUS</th></tr></thead>
<tbody>{rows}</tbody></table>
</div></div></div></body></html>"""
    return html


@app.route('/videos')
def videos():
    import glob
    files = sorted(glob.glob('/root/workspace/Penelope/ebooks/trailers/videos/*.mp4'), reverse=True)
    links = "".join([f'<div style="margin:12px 0"><a href="/video/{os.path.basename(f)}" style="color:#c9a84c;font-family:monospace">{os.path.basename(f)}</a></div>' for f in files])
    return f"""<html><body style="background:#060708;color:#d4cfc8;font-family:monospace;padding:24px">
    <h1 style="color:#c9a84c;font-family:Orbitron">Penelope Video Vault</h1>
    <p style="color:#4a5568">{len(files)} clips generated</p>
    {links if links else "<p>No videos yet</p>"}
    </body></html>"""

@app.route('/video/<filename>')
def video(filename):
    import flask
    return flask.send_from_directory('/root/workspace/Penelope/ebooks/trailers/videos', filename)


@app.route('/auth/youtube')
def youtube_auth():
    from google_auth_oauthlib.flow import Flow
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
                "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", ""),
                "redirect_uris": ["http://206.81.5.241:5001/auth/youtube/callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=["https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube"]
    )
    flow.redirect_uri = "http://206.81.5.241:5001/auth/youtube/callback"
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    return f'''<html><body style="background:#060708;color:#d4cfc8;font-family:monospace;padding:40px;text-align:center">
    <h1 style="color:#c9a84c;font-family:serif">Connect YouTube to Penelope</h1>
    <p style="margin:20px 0;color:#4a5568">Click below to authorize Penelope to upload videos to your YouTube channel</p>
    <a href="{auth_url}" style="background:#c9a84c;color:#060708;padding:16px 32px;font-weight:700;text-decoration:none;font-size:16px">AUTHORIZE YOUTUBE</a>
    </body></html>'''

@app.route('/auth/youtube/callback')
def youtube_callback():
    from google_auth_oauthlib.flow import Flow
    import os, json
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
                "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", ""),
                "redirect_uris": ["http://206.81.5.241:5001/auth/youtube/callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=["https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube"]
    )
    flow.redirect_uri = "http://206.81.5.241:5001/auth/youtube/callback"
    flow.fetch_token(authorization_response=request.url.replace("http://", "http://"))
    creds = flow.credentials
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    open("/root/workspace/Penelope/youtube_token.json", "w").write(json.dumps(token_data))
    # Add refresh token to .env
    with open("/root/workspace/Penelope/.env", "a") as f:
        f.write(f"\nYOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    return '''<html><body style="background:#060708;color:#d4cfc8;font-family:monospace;padding:40px;text-align:center">
    <h1 style="color:#2ecc71;font-family:serif">YouTube Connected!</h1>
    <p style="margin:20px 0">Penelope can now upload videos to your YouTube channel automatically.</p>
    <p style="color:#4a5568">You can close this tab.</p>
    </body></html>'''


@app.route('/connect-youtube')
def connect_youtube():
    url = open('/root/workspace/Penelope/yt_auth_url.txt').read().strip()
    return f'''<html><body style="background:#060708;color:#d4cfc8;font-family:monospace;padding:40px;text-align:center">
    <h1 style="color:#c9a84c">Connect YouTube</h1>
    <p style="margin:20px 0">Tap the button below to authorize Penelope:</p>
    <a href="{url}" style="background:#c9a84c;color:#060708;padding:16px 32px;font-weight:700;text-decoration:none;font-size:18px;display:inline-block;margin:20px">AUTHORIZE YOUTUBE</a>
    <p style="color:#4a5568;margin-top:20px">After approving, copy the code and go to /save-yt-code?code=PASTE_CODE_HERE</p>
    </body></html>'''

@app.route('/save-yt-code')
def save_yt_code():
    import json
    from google_auth_oauthlib.flow import InstalledAppFlow
    code = request.args.get('code','')
    if not code:
        return 'No code provided'
    client_config = {'installed': {'client_id': '99896511571-dq0kh3c52ihdg70s473ers25a2to72hg.apps.googleusercontent.com','client_secret': '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','redirect_uris': ['urn:ietf:wg:oauth:2.0:oob'],'auth_uri': 'https://accounts.google.com/o/oauth2/auth','token_uri': 'https://oauth2.googleapis.com/token'}}
    flow = InstalledAppFlow.from_client_config(client_config, scopes=['https://www.googleapis.com/auth/youtube.upload'])
    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
    flow.fetch_token(code=code)
    creds = flow.credentials
    open('/root/workspace/Penelope/youtube_token.json','w').write(json.dumps({'token':creds.token,'refresh_token':creds.refresh_token,'client_id':creds.client_id,'client_secret':creds.client_secret}))
    with open('/root/workspace/Penelope/.env','a') as f:
        f.write(f'\nYOUTUBE_REFRESH_TOKEN={creds.refresh_token}')

    return '<html><body style="background:#060708;color:#2ecc71;font-family:monospace;padding:40px;text-align:center"><h1>YouTube Connected!</h1><p>Penelope can now upload videos automatically.</p></body></html>'


@app.route('/yt-auth-page')
def yt_auth_page():
    url = open('/root/workspace/Penelope/yt_auth_url.txt').read().strip()
    return '<html><body style="background:#060708;padding:40px;text-align:center"><h1 style="color:#c9a84c;font-family:serif">Step 1: Tap button</h1><a href="' + url + '" style="background:#c9a84c;color:#000;padding:16px 32px;font-weight:700;text-decoration:none;font-size:18px;display:inline-block;margin:20px">AUTHORIZE YOUTUBE</a><h1 style="color:#c9a84c;font-family:serif;margin-top:30px">Step 2: Paste code below</h1><form action="/yt-save" method="get"><input name="code" style="width:80%;padding:10px;font-size:14px;background:#1a1a1a;color:#fff;border:1px solid #c9a84c" placeholder="Paste code here"><br><br><button type="submit" style="background:#2ecc71;color:#000;padding:12px 24px;font-size:16px;border:none;font-weight:700;cursor:pointer">SAVE & CONNECT</button></form></body></html>'

@app.route('/yt-save')
def yt_save():
    import json
    from google_auth_oauthlib.flow import InstalledAppFlow
    code = request.args.get('code', '').strip()
    if not code:
        return 'No code!'
    cfg = {"installed": {"client_id": "99896511571-dq0kh3c52ihdg70s473ers25a2to72hg.apps.googleusercontent.com", "client_secret": "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", "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"], "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}}
    try:
        flow = InstalledAppFlow.from_client_config(cfg, scopes=["https://www.googleapis.com/auth/youtube.upload"])
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        flow.fetch_token(code=code)
        creds = flow.credentials
        token = {"token": creds.token, "refresh_token": creds.refresh_token, "client_id": creds.client_id, "client_secret": creds.client_secret}
        open("/root/workspace/Penelope/youtube_token.json", "w").write(json.dumps(token))
        env = open("/root/workspace/Penelope/.env").read()
        if "YOUTUBE_REFRESH_TOKEN" not in env:
            open("/root/workspace/Penelope/.env", "a").write("\nYOUTUBE_REFRESH_TOKEN=" + str(creds.refresh_token))
        return '<html><body style="background:#060708;color:#2ecc71;font-family:monospace;padding:40px;text-align:center"><h1>YouTube Connected!</h1><p>Penelope can now upload videos automatically.</p><p style="color:#c9a84c">Token saved successfully.</p></body></html>'
    except Exception as e:
        return f'<html><body style="background:#060708;color:#e74c3c;padding:40px"><h1>Error: {str(e)}</h1></body></html>'


@app.route('/contact', methods=['POST', 'OPTIONS'])
def contact():
    from flask import request, jsonify
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    try:
        data = request.get_json() or {}
        name = f"{data.get('first_name','')} {data.get('last_name','')}".strip()
        email = data.get('email', '')
        service = data.get('service', '')
        message = data.get('message', '')
        import requests as req
        tg_msg = f"NEW CONTACT\nFrom: {name}\nEmail: {email}\nService: {service}\nMessage: {message[:300]}"
        req.post(
            f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN','')}/sendMessage",
            json={"chat_id": os.environ.get('TELEGRAM_CHAT_ID',''), "text": tg_msg},
            timeout=5
        )
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error"}), 200

@app.route('/oauth/callback')
def oauth_callback():
    from flask import request
    code = request.args.get('code', '')
    if code:
        with open('/root/penelope_gumroad_code.txt', 'w') as f:
            f.write(code)
        return '<h1 style="color:green">Authorized. Close this window.</h1>', 200
    return '<h1>Error: No code</h1>', 400

@app.route('/twitter/callback')
def twitter_oauth_callback():
    import requests as req
    from flask import request as freq
    code = freq.args.get('code', '')
    if not code:
        return '<h1>Error: No code received</h1>', 400
    vault = {}
    try:
        for line in open('/root/penelope_vault.env'):
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                vault[k.strip()] = v.strip()
    except: pass
    r = req.post(
        'https://api.twitter.com/2/oauth2/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        auth=(vault.get('TWITTER_CLIENT_ID',''), vault.get('TWITTER_CLIENT_SECRET','')),
        data={
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'https://penelope.trustchainservices.com/twitter/callback',
            'code_verifier': vault.get('TWITTER_PKCE_VERIFIER',''),
            'client_id': vault.get('TWITTER_CLIENT_ID',''),
        },
        timeout=15
    )
    if r.status_code == 200:
        data = r.json()
        access = data.get('access_token', '')
        refresh = data.get('refresh_token', '')
        os.system("sed -i '/TWITTER_OAUTH2_ACCESS_TOKEN/d' /root/penelope_vault.env")
        os.system("sed -i '/TWITTER_OAUTH2_REFRESH_TOKEN/d' /root/penelope_vault.env")
        with open('/root/penelope_vault.env', 'a') as f:
            f.write(f'TWITTER_OAUTH2_ACCESS_TOKEN={access}\n')
            f.write(f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh}\n')
        tg = vault.get('TELEGRAM_BOT_TOKEN', '')
        chat = vault.get('TELEGRAM_CHAT_ID', '')
        req.post(f'https://api.telegram.org/bot{tg}/sendMessage',
                 json={'chat_id': chat, 'text': 'TWITTER CONNECTED! Token stored. Posting active.'}, timeout=5)
        return '<html><body style="background:#0a0a0a;color:#c8f400;font-family:monospace;padding:60px;text-align:center"><h1>Twitter Connected!</h1><p style="color:#888">Close this window.</p></body></html>', 200
    return f'<h1>Auth failed {r.status_code}</h1><pre>{r.text[:300]}</pre>', 400



TRADING_STATE_FILE = "/root/workspace/Penelope/trading_bot/engine_v3_state.json"

@app.route("/status", methods=["GET"])
def trading_status():
    import json, os, datetime
    try:
        if not os.path.exists(TRADING_STATE_FILE):
            return app.response_class(
                json.dumps({"error": "Engine v3 not started yet."}),
                mimetype="application/json", status=404
            )
        state = json.loads(open(TRADING_STATE_FILE).read())
        strategies_out = {}
        total_capital = 0
        total_value = 0
        for sid, st in state.items():
            if sid == "_meta" or not isinstance(st, dict):
                continue
            strategies_out[sid] = {
                "portfolio_value":    st.get("portfolio_value", 0),
                "initial_capital":    st.get("initial_capital", 0),
                "pnl":                st.get("pnl", 0),
                "pnl_pct":            st.get("pnl_pct", 0),
                "trade_count":        st.get("trade_count", 0),
                "win_count":          st.get("win_count", 0),
                "consecutive_losses": st.get("consecutive_losses", 0),
                "position":           st.get("position"),
                "risk_state":         st.get("risk_state", {}),
            }
            total_capital += st.get("initial_capital", 0)
            total_value   += st.get("portfolio_value", 0)
        total_pnl = total_value - total_capital
        cb_active = 0
        for st in strategies_out.values():
            until = st.get("risk_state", {}).get("circuit_breaker_until")
            if until:
                try:
                    if datetime.datetime.now() < datetime.datetime.fromisoformat(until):
                        cb_active += 1
                except:
                    pass
        ranked  = sorted(strategies_out.items(), key=lambda x: x[1]["pnl_pct"], reverse=True)
        top5    = [{"id": k, **v} for k, v in ranked[:5]]
        bottom5 = [{"id": k, **v} for k, v in ranked[-5:]]
        dead    = [k for k, v in strategies_out.items() if v["trade_count"] == 0]
        payload = {
            "timestamp":   datetime.datetime.now().isoformat(),
            "cycle_count": state.get("_meta", {}).get("cycle_count", 0),
            "started":     state.get("_meta", {}).get("started"),
            "summary": {
                "total_capital":           total_capital,
                "total_value":             round(total_value, 2),
                "total_pnl":               round(total_pnl, 2),
                "total_pnl_pct":           round((total_pnl / total_capital * 100) if total_capital else 0, 2),
                "strategies_count":        len(strategies_out),
                "circuit_breakers_active": cb_active,
                "dead_strategies":         len(dead),
            },
            "top5":       top5,
            "bottom5":    bottom5,
            "dead":       dead,
            "strategies": strategies_out,
        }
        return app.response_class(
            json.dumps(payload, indent=2),
            mimetype="application/json"
        )
    except Exception as e:
        return app.response_class(
            json.dumps({"error": str(e)}),
            mimetype="application/json", status=500
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)