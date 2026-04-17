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
vessel_social_agent.py
Distributes Vessel milestone cards + community content
Bluesky + any connected social via existing social_autoposter infrastructure
Runs daily 10AM + 7PM
"""
import os, json, requests, time
from datetime import datetime
from google import genai as _genai
_vessel_client = None

def _get_client():
    global _vessel_client
    if _vessel_client is None:
        _vessel_client = _genai.Client(api_key=GOOGLE_API_KEY)
    return _vessel_client

VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except:
    pass

TELEGRAM_TOKEN = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = "6183015901"
GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY", "")
# Bluesky config (using vesselprotocol.bsky.social)
BLUESKY_HANDLE  = "vesselprotocol.bsky.social"
BLUESKY_API_URL = "https://bsky.social/xrpc"

VESSEL_SOCIAL_TEMPLATES = [
    "Day {day}. The protocol holds. ✦",
    "Day {day}. A Vessel is shifting. ✦",
    "Day {day}. Baseline no longer matches the vision. ✦",
    "Day {day}. CT × A = M. Still proving it. ✦",
    "Day {day}. The automaticity threshold is real. ✦",
    "{count} Vessels in protocol today. ✦",
    "The community wall grows. Anonymous milestones. Real change. ✦",
    "365 days is not a commitment. It is a becoming. ✦",
    "What you manifest, you first become. ✦",
    "The protocol is not about perfection. It is about continuity. ✦",
]

def gemini(prompt, temperature=0.7, max_tokens=2000):
    try:
        client = _get_client()
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r, "text", "") or ""
    except Exception as e:
        print(f"Gemini error: {e}")
        return ""

def bluesky_login(password):
    """Auth with Bluesky"""
    try:
        r = requests.post(
            f"{BLUESKY_API_URL}/com.atproto.server.createSession",
            json={"identifier": BLUESKY_HANDLE, "password": password},
            timeout=15
        )
        if r.ok:
            data = r.json()
            return data.get("accessJwt"), data.get("did")
    except Exception as e:
        print(f"Bluesky login error: {e}")
    return None, None

def bluesky_post(token, did, text):
    """Post to Bluesky"""
    try:
        r = requests.post(
            f"{BLUESKY_API_URL}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "text": text[:300],
                    "$type": "app.bsky.feed.post",
                    "createdAt": datetime.utcnow().isoformat() + "Z"
                }
            },
            timeout=15
        )
        return r.ok
    except Exception as e:
        print(f"Bluesky post error: {e}")
    return False

def generate_vessel_post(stats=None):
    """Generate a Vessel social post — mysterious, cult-building"""
    prompt = """Write a single short social media post for the Vessel manifestation protocol community.

Context: Vessel is a 365-day manifestation app with CT×A=M formula. Sacred geometry aesthetic.
The post should feel like a transmission from an insider community — mysterious, magnetic, authentic.
It should make outsiders curious what Vessel is without explaining it.

Rules:
- Under 30 words
- No hashtags
- No emojis except ✦ at the end
- Sentence case
- Present tense
- Sounds human, not marketing

Format: [message] ✦

Reply with ONLY the post."""

    post = gemini(prompt)
    if not post:
        import random
        template = random.choice(VESSEL_SOCIAL_TEMPLATES)
        day = (stats or {}).get("avg_day", 47)
        count = (stats or {}).get("active_users", 0)
        post = template.format(day=day, count=count)
    return post

def post_to_social(post_text, stats=None):
    """Post to all connected platforms"""
    results = {}

    # Try existing social_log.json to see what's connected
    try:
        with open("/root/workspace/Penelope/social_log.json") as f:
            social_log = json.load(f)
    except:
        social_log = {}

    # Bluesky post attempt
    bluesky_pass = VAULT.get("BLUESKY_PASSWORD", "")
    if bluesky_pass:
        token, did = bluesky_login(bluesky_pass)
        if token:
            ok = bluesky_post(token, did, post_text)
            results["bluesky"] = "posted" if ok else "failed"
            print(f"Bluesky: {'✓' if ok else '✗'} {post_text[:50]}")
        else:
            results["bluesky"] = "auth_failed"
    else:
        results["bluesky"] = "no_credentials"
        print(f"[MOCK BLUESKY POST]: {post_text}")

    # Log the attempt regardless
    log_entry = {
        "platform": "vessel_social",
        "post": post_text,
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        log_path = "/root/workspace/Penelope/social_log.json"
        with open(log_path) as f:
            log = json.load(f)
    except:
        log = {}

    log[f"vessel_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"] = log_entry
    try:
        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)
    except:
        pass

    return results

def run_social_post(stats=None, custom_post=None):
    """Main runner — generate and distribute one Vessel post"""
    print(f"[{datetime.utcnow().isoformat()}] VesselSocialAgent running")

    post = custom_post or generate_vessel_post(stats)
    print(f"Post: {post}")

    results = post_to_social(post, stats)

    if TELEGRAM_TOKEN:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT,
                    "text": (
                        f"📣 <b>Vessel Social Posted</b>\n"
                        f"<i>{post}</i>\n"
                        f"Platforms: {json.dumps(results)}"
                    ),
                    "parse_mode": "HTML"
                },
                timeout=10
            )
        except:
            pass

    return {"post": post, "results": results}

if __name__ == "__main__":
    result = run_social_post(stats={"avg_day": 47, "active_users": 12})
    print(json.dumps(result, indent=2))
