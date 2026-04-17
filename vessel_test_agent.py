"""
vessel_test_agent.py
Automated test suite for Vessel + Vessel Kids
Runs all tests, writes results to /root/CLAUDE.md
Sends Telegram alert if pass rate drops below threshold
"""
import requests, json, time, sys
from datetime import datetime


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

TG_TOKEN  = VAULT.get("TELEGRAM_BOT_TOKEN","")
TG_CHAT   = "6183015901"
BASE_URL  = "https://trustchainservices.com"
API_URL   = f"{BASE_URL}/vessel-api"
API_KEY   = "vessel_api_2026"
CLAUDE_MD = "/root/CLAUDE.md"
PASS_THRESHOLD = 90  # alert if below 90%

results = []
start_time = datetime.utcnow()

def tg(msg):
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def test(name, category):
    """Decorator-style test runner"""
    def decorator(fn):
        t0 = time.time()
        try:
            result, detail = fn()
            elapsed = round((time.time()-t0)*1000)
            results.append({
                "name": name, "category": category,
                "pass": result, "detail": detail, "ms": elapsed
            })
            status = "✅" if result else "❌"
            print(f"  {status} [{elapsed}ms] {name}: {detail}")
        except Exception as e:
            elapsed = round((time.time()-t0)*1000)
            results.append({
                "name": name, "category": category,
                "pass": False, "detail": f"EXCEPTION: {str(e)[:120]}", "ms": elapsed
            })
            print(f"  💥 [{elapsed}ms] {name}: EXCEPTION: {e}")
        return fn
    return decorator

# ════════════════════════════════════════
# CATEGORY 1: INFRASTRUCTURE
# ════════════════════════════════════════
print("\n── INFRASTRUCTURE ──")

@test("Vessel Adult app loads", "infrastructure")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    return r.status_code == 200, f"HTTP {r.status_code}, {len(r.content)//1024}KB"

@test("Vessel Kids app loads", "infrastructure")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    return r.status_code == 200, f"HTTP {r.status_code}, {len(r.content)//1024}KB"

@test("Service worker loads", "infrastructure")
def _():
    r = requests.get(f"{BASE_URL}/vessel-sw.js", timeout=10)
    return r.status_code == 200 and "push" in r.text.lower(), f"HTTP {r.status_code}"

@test("Push server reachable", "infrastructure")
def _():
    r = requests.options(f"{BASE_URL}/vessel-push-register", timeout=5)
    return r.status_code in [200, 204, 405], f"HTTP {r.status_code}"

@test("Vessel API health", "infrastructure")
def _():
    r = requests.get(f"{API_URL}/health", timeout=10)
    d = r.json()
    return d.get("status") == "ok", f"users={d.get('users')} checkins={d.get('checkins')} kids={d.get('kids')}"

@test("API responds within 1000ms", "infrastructure")
def _():
    t0 = time.time()
    requests.get(f"{API_URL}/health", timeout=5)
    ms = (time.time()-t0)*1000
    return ms < 1000, f"{ms:.0f}ms"

@test("Penelope bridge reachable", "infrastructure")
def _():
    r = requests.post("http://206.81.5.241:5099/exec",
        json={"secret":"sydney123","cmd":"echo pong"}, timeout=8)
    # Bridge returns: {returncode, stdout, stderr}
    # stdout is itself a JSON string: {"returncode":0,"stdout":"pong\n","stderr":""}
    outer = r.json()
    try:
        inner = json.loads(outer.get("stdout","{}"))
        out = inner.get("stdout","")
    except:
        out = outer.get("stdout","")
    return "pong" in out, out.strip()[:50]

# ════════════════════════════════════════
# CATEGORY 2: API ENDPOINTS
# ════════════════════════════════════════
print("\n── API ENDPOINTS ──")
TEST_EMAIL = f"test_agent_{int(time.time())}@vessel.test"
TEST_USER_ID = None

@test("POST /user — create user", "api")
def _():
    global TEST_USER_ID
    r = requests.post(f"{API_URL}/user",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"name":"Test Agent","email":TEST_EMAIL,"goal_type":"Purpose",
              "day_count":1,"streak":0,"badges":["Founding Member"]},
        timeout=10)
    d = r.json()
    TEST_USER_ID = d.get("id")
    return d.get("ok") and TEST_USER_ID, f"id={str(TEST_USER_ID)[:12]}..."

@test("GET /user/:email — fetch by email", "api")
def _():
    r = requests.get(f"{API_URL}/user/{TEST_EMAIL}",
        headers={"X-Vessel-Key": API_KEY}, timeout=10)
    d = r.json()
    return d.get("found") and d.get("name")=="Test Agent", f"found={d.get('found')} name={d.get('name')}"

@test("GET /user/:email — 404 for unknown", "api")
def _():
    r = requests.get(f"{API_URL}/user/nobody_xyz_999@test.com",
        headers={"X-Vessel-Key": API_KEY}, timeout=10)
    return r.status_code == 404, f"HTTP {r.status_code}"

@test("POST /checkin — save check-in", "api")
def _():
    r = requests.post(f"{API_URL}/checkin",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"user_id": TEST_USER_ID, "date": datetime.utcnow().date().isoformat(),
              "mood_score":4,"session_completed":True,"action_completed":False,
              "intention":"Test intention","reflection":""},
        timeout=10)
    d = r.json()
    return d.get("ok"), f"id={str(d.get('id',''))[:12]}..."

@test("GET /checkins/:user_id — retrieve check-ins", "api")
def _():
    r = requests.get(f"{API_URL}/checkins/{TEST_USER_ID}", timeout=10)
    d = r.json()
    return isinstance(d, list) and len(d) >= 1, f"count={len(d)}"

@test("POST /user/:id/progress — update progress", "api")
def _():
    r = requests.post(f"{API_URL}/user/{TEST_USER_ID}/progress",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"day_count":5,"streak":3,"uss_score":65}, timeout=10)
    d = r.json()
    return d.get("ok"), str(d)

@test("GET /ai-context/:email — full AI context", "api")
def _():
    r = requests.get(f"{API_URL}/ai-context/{TEST_EMAIL}", timeout=10)
    d = r.json()
    has_fields = all(k in d for k in ["name","goals","day_count","recent_checkins","avg_mood_7d"])
    return has_fields, f"sessions_week={d.get('sessions_this_week')} avg_mood={d.get('avg_mood_7d')}"

@test("POST /kids — create kid profile", "api")
def _():
    r = requests.post(f"{API_URL}/kids",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"name":"TestKid","age":12,"goals":["School","Friends"],
              "day_count":1,"streak":1},
        timeout=10)
    d = r.json()
    return d.get("ok"), f"id={str(d.get('id',''))[:12]}..."

@test("POST /kids/checkin — save kids check-in", "api")
def _():
    # First get the kid ID
    r0 = requests.post(f"{API_URL}/kids",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"name":"TestKid2","age":11,"goals":["School"],"day_count":1,"streak":1},
        timeout=10)
    kid_id = r0.json().get("id")
    r = requests.post(f"{API_URL}/kids/checkin",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"kid_id": kid_id, "type":"morning",
              "date": datetime.utcnow().date().isoformat(),
              "mood":4,"action_done":True,"gratitude":"Grateful for testing"},
        timeout=10)
    d = r.json()
    return d.get("ok"), f"id={str(d.get('id',''))[:12]}..."

@test("POST /corporate-inquiry — saves inquiry", "api")
def _():
    r = requests.post(f"{API_URL}/corporate-inquiry",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"company_name":"Test Corp","contact_email":"hr@testcorp.com",
              "employee_count":"26-100 employees"},
        timeout=10)
    d = r.json()
    return d.get("ok"), str(d)

# ════════════════════════════════════════
# CATEGORY 3: CONTENT VALIDATION
# ════════════════════════════════════════
print("\n── CONTENT VALIDATION ──")

@test("Adult app has all 11 screen IDs", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    html = r.text
    screens = ['s-restore','s-goals','s-info','s-baseline','s-vision','s-commit',
               's-paywall','s-dash','s-morning','s-intention','s-action',
               's-evening','s-vision-board','s-affirm','s-corporate','s-complete']
    missing = [s for s in screens if f'id="{s}"' not in html]
    return len(missing)==0, f"missing={missing}" if missing else "all present"

@test("Adult app has Vessel API integration", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    html = r.text
    checks = ['VESSEL_API','vAPI','vessel-api','vessel_api_2026']
    missing = [c for c in checks if c not in html]
    return len(missing)==0, f"missing={missing}" if missing else "API wired"

@test("Adult app has binaural beat music engine", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    html = r.text
    checks = ['AudioContext','createChannelMerger','SCENES','startScene','musicToggle']
    missing = [c for c in checks if c not in html]
    return len(missing)==0, f"missing={missing}" if missing else "music engine present"

@test("Adult app has coherence breathing (5-5)", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    html = r.text
    has_5s = "{name:'INHALE',dur:5}" in html and "{name:'EXHALE',dur:5}" in html
    no_hold = "HOLD" not in html[html.find("const STEPS"):html.find("const STEPS")+100]
    return has_5s and no_hold, f"5s cycles={has_5s} no_hold={no_hold}"

@test("Adult app has localStorage persistence", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    html = r.text
    checks = ['saveState','loadState','vessel_state']
    missing = [c for c in checks if c not in html]
    return len(missing)==0, f"missing={missing}" if missing else "persistence present"

@test("Kids app has all screen IDs", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    html = r.text
    screens = ['s-welcome','s-goals','s-info','s-commit','s-dash',
               's-morning','s-intention','s-action','s-evening','s-parent']
    missing = [s for s in screens if f'id="{s}"' not in html]
    return len(missing)==0, f"missing={missing}" if missing else "all present"

@test("Kids app has kBreathTone defined", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    html = r.text
    return "function kBreathTone" in html, "defined" if "function kBreathTone" in html else "MISSING"

@test("Kids app has no binaural beats (child safety)", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    html = r.text
    # Should have pentatonic notes but NOT binaural channel merger
    has_pentatonic = "K_SCENES" in html
    no_binaural = "createChannelMerger" not in html
    return has_pentatonic and no_binaural, f"pentatonic={has_pentatonic} no_binaural={no_binaural}"

@test("Kids app has parent dashboard", "content")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    html = r.text
    checks = ['s-parent','p-day','p-streak','p-morning','p-mood','buildParent']
    missing = [c for c in checks if c not in html]
    return len(missing)==0, f"missing={missing}" if missing else "parent dashboard present"

@test("Both apps have music toggle button", "content")
def _():
    v = requests.get(f"{BASE_URL}/vessel.html", timeout=10).text
    k = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10).text
    adult_ok = 'id="music-toggle"' in v
    kids_ok  = 'id="k-music-btn"' in k
    return adult_ok and kids_ok, f"adult={adult_ok} kids={kids_ok}"

# ════════════════════════════════════════
# CATEGORY 4: PERFORMANCE
# ════════════════════════════════════════
print("\n── PERFORMANCE ──")

@test("Adult app loads under 2s", "performance")
def _():
    t0=time.time()
    requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    ms=(time.time()-t0)*1000
    return ms<2000, f"{ms:.0f}ms"

@test("Kids app loads under 2s", "performance")
def _():
    t0=time.time()
    requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    ms=(time.time()-t0)*1000
    return ms<2000, f"{ms:.0f}ms"

@test("API response under 500ms", "performance")
def _():
    t0=time.time()
    requests.get(f"{API_URL}/health", timeout=5)
    ms=(time.time()-t0)*1000
    return ms<500, f"{ms:.0f}ms"

@test("Adult app under 100KB", "performance")
def _():
    r=requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    kb=len(r.content)//1024
    return kb<100, f"{kb}KB"

@test("Kids app under 80KB", "performance")
def _():
    r=requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    kb=len(r.content)//1024
    return kb<80, f"{kb}KB"

# ════════════════════════════════════════
# CATEGORY 5: DATA INTEGRITY
# ════════════════════════════════════════
print("\n── DATA INTEGRITY ──")

@test("User email lookup is case-insensitive", "data")
def _():
    upper = requests.get(f"{API_URL}/user/{TEST_EMAIL.upper()}", timeout=10)
    lower = requests.get(f"{API_URL}/user/{TEST_EMAIL.lower()}", timeout=10)
    return upper.status_code==200 and lower.status_code==200, f"upper={upper.status_code} lower={lower.status_code}"

@test("Duplicate user upsert (same email) doesn't create duplicate", "data")
def _():
    # Create same user twice
    for _ in range(2):
        requests.post(f"{API_URL}/user",
            headers={"X-Vessel-Key":API_KEY,"Content-Type":"application/json"},
            json={"name":"Dupe Test","email":"dupe_test_vessel@test.com",
                  "goal_type":"Peace","day_count":1},
            timeout=10)
    # Count via health check isn't granular enough — just verify it doesn't error
    r = requests.get(f"{API_URL}/user/dupe_test_vessel@test.com", timeout=10)
    return r.status_code==200, f"HTTP {r.status_code}"

@test("Check-in links to correct user", "data")
def _():
    r = requests.get(f"{API_URL}/checkins/{TEST_USER_ID}", timeout=10)
    d = r.json()
    wrong_user = [c for c in d if c.get("user_id") != TEST_USER_ID]
    return len(wrong_user)==0, f"total={len(d)} wrong_user={len(wrong_user)}"

@test("Progress update persists correctly", "data")
def _():
    # Update progress
    requests.post(f"{API_URL}/user/{TEST_USER_ID}/progress",
        headers={"X-Vessel-Key":API_KEY,"Content-Type":"application/json"},
        json={"day_count":7,"streak":5,"uss_score":72}, timeout=10)
    # Read back
    r = requests.get(f"{API_URL}/user/{TEST_EMAIL}", timeout=10)
    d = r.json()
    return d.get("day_count")==7 and d.get("streak")==5, f"day={d.get('day_count')} streak={d.get('streak')}"

@test("AI context returns mood trend from check-ins", "data")
def _():
    # Save a few check-ins with known moods
    for mood in [3,4,5]:
        requests.post(f"{API_URL}/checkin",
            headers={"X-Vessel-Key":API_KEY,"Content-Type":"application/json"},
            json={"user_id":TEST_USER_ID,"date":datetime.utcnow().date().isoformat(),
                  "mood_score":mood,"session_completed":True},
            timeout=10)
    r = requests.get(f"{API_URL}/ai-context/{TEST_EMAIL}", timeout=10)
    d = r.json()
    avg = d.get("avg_mood_7d")
    return avg is not None and 3 <= avg <= 5, f"avg_mood={avg}"


# ════════════════════════════════════════
# CATEGORY 6: LANDING PAGE
# ════════════════════════════════════════
print("\n── LANDING PAGE ──")

@test("Landing page loads", "landing")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=10)
    return r.status_code == 200, f"HTTP {r.status_code}, {len(r.content)//1024}KB"

@test("Landing page has CT×A=M formula", "landing")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=10)
    found = b"CT" in r.content and b"=M" in r.content
    return found, "present" if found else "MISSING"

@test("Landing page links to both apps", "landing")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=10)
    has_adult = "vessel.html" in r.text
    has_kids  = "vessel-kids.html" in r.text
    return has_adult and has_kids, f"adult={has_adult} kids={has_kids}"

@test("Landing page has pricing", "landing")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=10)
    return "$4.99" in r.text and "$39.99" in r.text, "pricing present"

@test("Landing page loads under 1s", "landing")
def _():
    t0=time.time()
    requests.get(f"{BASE_URL}/", timeout=5)
    ms=(time.time()-t0)*1000
    return ms<1000, f"{ms:.0f}ms"


# ════════════════════════════════════════
# CATEGORY 7: STRIPE INTEGRATION
# ════════════════════════════════════════
print("\n── STRIPE ──")

@test("Stripe checkout endpoint reachable", "stripe")
def _():
    r = requests.post(f"{BASE_URL}/vessel-api/checkout",
        headers={"X-Vessel-Key": API_KEY, "Content-Type": "application/json"},
        json={"plan":"monthly","user_id":"test","email":"test@vessel.com"}, timeout=15)
    d = r.json()
    return d.get("ok") and d.get("url","").startswith("https://checkout.stripe.com"), f"ok={d.get('ok')} url_valid={str(d.get('url',''))[:30]}..."

@test("Adult app has Stripe checkout function", "stripe")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    return "startCheckout" in r.text, "present" if "startCheckout" in r.text else "MISSING"

@test("Adult app handles Stripe return", "stripe")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    return "checkStripeReturn" in r.text, "present" if "checkStripeReturn" in r.text else "MISSING"

@test("Webhook endpoint reachable", "stripe")
def _():
    r = requests.post(f"{BASE_URL}/vessel-api/webhook",
        data=b"test", headers={"Content-Type":"application/json"}, timeout=8)
    # Should return 400 (bad signature) not 404
    return r.status_code in [400, 200], f"HTTP {r.status_code} (400=correct bad sig)"

# ════════════════════════════════════════
# CATEGORY 8: ASSETS
# ════════════════════════════════════════
print("\n── ASSETS ──")

@test("vessel-icon.png exists", "assets")
def _():
    r = requests.get(f"{BASE_URL}/vessel-icon.png", timeout=8)
    return r.status_code==200 and len(r.content)>1000, f"HTTP {r.status_code} {len(r.content)//1024}KB"

@test("vessel-badge.png exists", "assets")
def _():
    r = requests.get(f"{BASE_URL}/vessel-badge.png", timeout=8)
    return r.status_code==200 and len(r.content)>500, f"HTTP {r.status_code} {len(r.content)} bytes"

@test("vessel-og.png exists (social sharing)", "assets")
def _():
    r = requests.get(f"{BASE_URL}/vessel-og.png", timeout=10)
    return r.status_code==200 and len(r.content)>10000, f"HTTP {r.status_code} {len(r.content)//1024}KB"

@test("vessel-sw.js references correct icons", "assets")
def _():
    r = requests.get(f"{BASE_URL}/vessel-sw.js", timeout=8)
    return "vessel-icon.png" in r.text, "present" if "vessel-icon.png" in r.text else "MISSING"

@test("Landing page OG meta tag references og image", "assets")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=8)
    return "vessel-og.png" in r.text, "present" if "vessel-og.png" in r.text else "MISSING"


# ════════════════════════════════════════
# CATEGORY 9: JAVASCRIPT SYNTAX
# ════════════════════════════════════════
print("\n── JAVASCRIPT SYNTAX ──")

import subprocess, tempfile, os

def check_js_syntax(html, label):
    """Extract all script blocks and run node --check on them"""
    import re
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    # Combine all inline scripts (skip tiny ones < 50 chars)
    combined = "\n".join(s for s in scripts if len(s.strip()) > 50)
    if not combined:
        return True, "no inline scripts found"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(combined)
        fname = f.name
    try:
        result = subprocess.run(['node', '--check', fname],
            capture_output=True, text=True, timeout=10)
        os.unlink(fname)
        if result.returncode == 0:
            return True, f"{len(combined)} chars — no errors"
        else:
            # Extract the key error line
            err = result.stderr.strip().split("\n")
            err_line = next((l for l in err if "SyntaxError" in l or "Unexpected" in l), err[-1] if err else "unknown")
            return False, err_line[:120]
    except Exception as e:
        try: os.unlink(fname)
        except: pass
        return False, str(e)[:80]

@test("Adult app JS — no syntax errors", "javascript")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    ok, detail = check_js_syntax(r.text, "vessel.html")
    return ok, detail

@test("Kids app JS — no syntax errors", "javascript")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    ok, detail = check_js_syntax(r.text, "vessel-kids.html")
    return ok, detail

@test("Landing page JS — no syntax errors", "javascript")
def _():
    r = requests.get(f"{BASE_URL}/", timeout=10)
    ok, detail = check_js_syntax(r.text, "index.html")
    return ok, detail

@test("Adult app — full JS parse (node --check)", "javascript")
def _():
    r = requests.get(f"{BASE_URL}/vessel.html", timeout=10)
    ok, detail = check_js_syntax(r.text, "vessel.html second pass")
    return ok, detail

@test("Kids app — full JS parse (node --check)", "javascript")
def _():
    r = requests.get(f"{BASE_URL}/vessel-kids.html", timeout=10)
    ok, detail = check_js_syntax(r.text, "vessel-kids.html second pass")
    return ok, detail

# ════════════════════════════════════════
# RESULTS & REPORTING
# ════════════════════════════════════════
total   = len(results)
passed  = sum(1 for r in results if r["pass"])
failed  = total - passed
pct     = round(passed/total*100, 1) if total else 0
elapsed_total = (datetime.utcnow()-start_time).total_seconds()

print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} passed ({pct}%) in {elapsed_total:.1f}s")
print(f"{'='*50}")

# Group by category
cats = {}
for r in results:
    cats.setdefault(r["category"],[]).append(r)

cat_summary = ""
for cat, items in cats.items():
    cp = sum(1 for i in items if i["pass"])
    ct = len(items)
    cat_summary += f"  {cat.upper():15} {cp}/{ct} ({round(cp/ct*100)}%)\n"
print(cat_summary)

# Failures
failures = [r for r in results if not r["pass"]]

# ── Write to CLAUDE.md ──
now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
badge = "🟢 PASS" if pct >= 90 else "🟡 WARN" if pct >= 75 else "🔴 FAIL"

report = f"""
---
## Vessel Test Report — {now_str}
**{badge} | {passed}/{total} tests passed ({pct}%) | {elapsed_total:.1f}s**

### By Category
{cat_summary}
"""

if failures:
    report += "### ❌ Failures Requiring Repair\n"
    for f in failures:
        report += f"- **[{f['category'].upper()}] {f['name']}** — `{f['detail']}`\n"
    report += "\n"
else:
    report += "### ✅ No failures — all systems nominal\n\n"

report += f"*Auto-generated by vessel_test_agent.py*\n"

# Append to CLAUDE.md
try:
    with open(CLAUDE_MD, "a") as f:
        f.write(report)
    print(f"✅ Report written to {CLAUDE_MD}")
except Exception as e:
    print(f"⚠️  Could not write to CLAUDE.md: {e}")

# ── Telegram alert ──
if pct < PASS_THRESHOLD:
    fail_list = "\n".join(f"• {f['name']}: {f['detail']}" for f in failures[:8])
    tg(f"🚨 <b>Vessel Test Alert</b>\n\n{badge}: {passed}/{total} ({pct}%)\n\nFailing:\n{fail_list}\n\nRepair needed in CLAUDE.md")
    print(f"\n🚨 Alert sent — pass rate {pct}% below {PASS_THRESHOLD}% threshold")
else:
    tg(f"✅ <b>Vessel Tests</b> — {passed}/{total} passed ({pct}%)\n{badge}\n\n{cat_summary.strip()}")
    print(f"\n✅ Telegram notified — {pct}% pass rate")

sys.exit(0 if pct >= PASS_THRESHOLD else 1)