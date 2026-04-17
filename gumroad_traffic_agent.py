#!/usr/bin/env python3
"""
Gumroad Traffic Drip Agent — runs every 6h
Fills Buffer queue with Gumroad product posts + AI images.
"""
import os, sys, requests, json, time, random, logging
from pathlib import Path
from datetime import datetime, timezone

LOG  = Path("/root/workspace/Penelope/conductor_logs/gumroad_traffic.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
# Single handler — systemd captures stdout, file handler logs to disk
_log_handler = logging.FileHandler(LOG)
_log_handler.setFormatter(logging.Formatter("%(asctime)s [GT] %(message)s"))
_stdout_handler = logging.StreamHandler(sys.stdout)
_stdout_handler.setFormatter(logging.Formatter("%(asctime)s [GT] %(message)s"))
logging.getLogger().handlers = [_log_handler, _stdout_handler]
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger()

def env():
    e = {}
    try:
        for l in open("/root/penelope_vault.env"):
            if "=" in l and not l.startswith("#"):
                k,v=l.strip().split("=",1); e[k.strip()]=v.strip()
    except: pass
    return e

E             = env()
BUFFER_TOKEN  = E.get("BUFFER_API_TOKEN","Uihf9wIwWb8Vs_0qAdeu8kfkHCTHbh-ZwSAyi3G2F1i")
WS_KEY        = E.get("WAVESPEED_API_KEY","")
GQL_URL       = "https://api.buffer.com/graphql"
BH            = {"Authorization": f"Bearer {BUFFER_TOKEN}", "Content-Type": "application/json"}
WSH           = {"Authorization": f"Bearer {WS_KEY}", "Content-Type": "application/json"}
IMG_DIR       = Path("/var/www/html/generated")
SERVER        = "https://trustchainservices.com/generated"
CATALOG       = Path("/root/workspace/Penelope/gumroad_catalog.json")
IMG_DIR.mkdir(parents=True, exist_ok=True)

CHANNELS = {
    "twitter":   "69db9b41031bfa423cf6d64e",
    "tiktok":    "69db9bcf031bfa423cf6d86b",
    "pinterest": "69db9be6031bfa423cf6d8be",
    "facebook":  "69de9902031bfa423c038e5b",
}

IMAGES = {
    "book":      ("gumroad_book_cover.jpg",
                  "Epic sci-fi digital art: fractured planets colliding in space, deep blue purple, cinematic, no text, portrait"),
    "prompts":   ("gumroad_prompts_cover.jpg",
                  "Futuristic AI business: glowing circuit board chess board with quantum patterns, electric blue gold, minimal, no text, portrait"),
    "checklist": ("gumroad_checklist_cover.jpg",
                  "Data security shield: glowing padlock with document icons and checkmarks, blue green, tech, no text, portrait"),
    "guide":     ("gumroad_guide_cover.jpg",
                  "Quantum business leadership: leader silhouette before holographic quantum waves, navy gold, aspirational, no text, portrait"),
    "other":     ("gumroad_other_cover.jpg",
                  "Modern digital product: sleek device mockup glowing interface, neon dark background, tech, no text, portrait"),
}

MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
        ... on PostActionSuccess { post { id status } }
        ... on InvalidInputError { message }
        ... on LimitReachedError  { message }
        ... on UnauthorizedError  { message }
        ... on UnexpectedError    { message }
    }
}"""

def gql(q, v=None):
    r = requests.post(GQL_URL, headers=BH,
        json={"query": q, "variables": v or {}}, timeout=20)
    if r.status_code == 429:
        update_rate_state(dict(r.headers))
        return {}
    if r.status_code == 200:
        update_rate_state(dict(r.headers))
        return r.json().get("data", {})
    return {}

def get_spec(p):
    n, pt = p["name"], p["type"]
    if pt=="book": return "book"
    if "Prompt" in n: return "prompts"
    if "Safety" in n or "Check" in n: return "checklist"
    if "Guide" in n: return "guide"
    return "other"

def ensure_image(key):
    fname, prompt = IMAGES[key]
    path = IMG_DIR / fname
    if path.exists():
        return f"{SERVER}/{fname}"
    log.info(f"Generating {key} image...")
    try:
        r = requests.post("https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-dev",
            headers=WSH, json={"prompt": prompt, "size": "768x1024", "num_inference_steps": 25},
            timeout=30)
        if r.status_code != 200: return None
        job_id = r.json().get("data",{}).get("id")
        if not job_id: return None
        for _ in range(30):
            time.sleep(5)
            pr = requests.get(f"https://api.wavespeed.ai/api/v3/predictions/{job_id}/result",
                headers=WSH, timeout=15)
            if pr.status_code==200:
                pd = pr.json().get("data",{})
                if pd.get("status")=="completed":
                    urls = pd.get("outputs",[])
                    if urls:
                        img = requests.get(urls[0], timeout=30)
                        if img.status_code==200:
                            path.write_bytes(img.content)
                            log.info(f"Image saved: {fname}")
                            return f"{SERVER}/{fname}"
                elif pd.get("status")=="failed": return None
    except Exception as e:
        log.error(f"Image gen: {e}")
    return None

def make_text(p, svc):
    n, price, url, pt = p["name"], p["price"], p["url"], p["type"]
    if pt == "book":
        if svc == "twitter":
            return f"📖 {n[:50]}\n\nOnly ${price:.0f} — sci-fi saga you won't put down\n\n→ {url}\n\n#SciFi #BookTok #IndieAuthor #DigitalBooks"
        return (f"{n} — Sci-Fi Ebook ${price:.0f}\n\nFractured worlds. High stakes. Instant download.\n\n{url}\n\n"
                f"#SciFiBooks #EpicSciFi #IndieAuthor #GumroadFinds #BookLovers #SpaceOpera")
    elif "Prompt" in n:
        if svc == "twitter":
            return f"🚀 25 AI Business Strategy Prompts\nBuilt for leaders who move fast.\n${price:.0f} → {url}\n\n#AI #BusinessStrategy #ChatGPT #Entrepreneur"
        return (f"25 AI Business Strategy Prompts — ${price:.0f}\nStop starting from scratch. "
                f"ChatGPT + Claude frameworks ready to deploy.\n✅ Instant download\n{url}\n\n"
                f"#AIPrompts #BusinessStrategy #Entrepreneur #ChatGPT #GumroadFinds #DigitalDownload")
    elif "Safety" in n or "Check" in n:
        if svc == "twitter":
            return f"⚠️ Client data checklist — know your exposure before a breach.\n${price:.0f} → {url}\n\n#DataPrivacy #SmallBusiness #Cybersecurity"
        return (f"Client Data Safety Checklist — ${price:.0f}\nGDPR + CCPA in plain English. "
                f"Protect clients before it's too late.\n✅ Instant PDF\n{url}\n\n"
                f"#DataPrivacy #SmallBusiness #Cybersecurity #GumroadFinds #DataProtection")
    elif "Guide" in n:
        if svc == "twitter":
            return f"📘 Quantum Future Business Guide\nAI × strategy × leadership for 2026+\n${price:.0f} → {url}\n\n#BusinessLeadership #AI #Strategy"
        return (f"The Quantum Future — Business Leader's Guide ${price:.0f}\n"
                f"Forward-thinking playbook for leaders navigating AI and disruption.\n✅ Instant download\n{url}\n\n"
                f"#BusinessLeadership #AIStrategy #FutureOfWork #GumroadFinds #QuantumFuture")
    else:
        return f"{n[:50]} — ${price:.0f}\nInstant digital download → {url}\n\n#DigitalProducts #GumroadFinds"

def post(channel_id, text, img=None):
    inp = {"channelId": channel_id, "text": text,
           "schedulingType": "automatic", "mode": "addToQueue"}
    if img:
        inp["assets"] = {"images": [{"url": img}]}
    d = gql(MUTATION, {"input": inp})
    r = d.get("createPost", {})
    p = r.get("post")
    if p and p.get("id"): return True, p["id"]
    return False, r.get("message", str(r))[:80]

RATE_STATE_FILE = Path("/root/workspace/Penelope/buffer_rate_limit_state.json")

def is_rate_limited() -> bool:
    """Check if Buffer API is in cooldown. Returns True if we should skip."""
    import time as _t
    if not RATE_STATE_FILE.exists():
        return False
    try:
        s = json.loads(RATE_STATE_FILE.read_text())
        if not s.get("rate_limited"):
            return False
        reset_ts = s.get("reset_ts", 0)
        if _t.time() > reset_ts + 60:
            # Reset window has passed — clear state
            RATE_STATE_FILE.write_text(json.dumps({"rate_limited": False}))
            log.info("Buffer rate limit window cleared — resuming")
            return False
        remaining = reset_ts - _t.time()
        log.info(f"Buffer rate limited — {remaining/3600:.1f}h until reset ({s.get('reset_human','')})")
        return True
    except Exception as e:
        log.error(f"Rate state check error: {e}")
        return False

def update_rate_state(headers: dict):
    """Parse response headers and update rate limit state."""
    import time as _t
    remaining = int(headers.get("x-ratelimit-remaining", 100))
    reset_ts  = int(headers.get("x-ratelimit-reset", 0))
    limited   = remaining == 0
    if limited and reset_ts:
        state = {
            "rate_limited": True,
            "reset_ts":     reset_ts,
            "reset_human":  datetime.fromtimestamp(reset_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "detected_at":  datetime.now(timezone.utc).isoformat(),
            "remaining":    remaining,
        }
        RATE_STATE_FILE.write_text(json.dumps(state, indent=2))
        log.warning(f"Buffer rate limited — reset at {state['reset_human']}")


def run():
    log.info("=== Gumroad Traffic Drip run ===")
    if is_rate_limited():
        return  # skip entire run — API in cooldown
    if not CATALOG.exists():
        log.error("Catalog missing"); return
    catalog = json.loads(CATALOG.read_text())

    # Ensure images
    img_cache = {}
    for key in IMAGES:
        img_cache[key] = ensure_image(key)

    random.shuffle(catalog)
    ok = fail = 0
    # Track which channels are at daily capacity
    # Pinterest: 5/day platform limit, Twitter/TikTok: 10 queue cap
    DAILY_LIMITS = {"twitter": 10, "tiktok": 10, "pinterest": 5, "facebook": 3}
    full_channels = set()
    daily_counts  = {svc: 0 for svc in CHANNELS}

    for p in catalog:
        key = get_spec(p)
        img = img_cache.get(key)
        for svc, cid in CHANNELS.items():
            if svc in full_channels:
                continue  # skip — already at cap
            text     = make_text(p, svc)
            need_img = svc in ("pinterest", "tiktok")
            success, info = post(cid, text, img if need_img else None)
            if success:
                log.info(f"✅ [{svc}] {p['name'][:35]}")
                ok += 1
                daily_counts[svc] = daily_counts.get(svc, 0) + 1
                # Check if we've hit the daily limit for this channel
                if daily_counts[svc] >= DAILY_LIMITS.get(svc, 10):
                    log.info(f"⏸  [{svc}] Daily limit reached ({DAILY_LIMITS.get(svc,10)}) — skipping rest")
                    full_channels.add(svc)
            else:
                if "limit" in str(info).lower() or "Whoops" in str(info) or "maximum" in str(info).lower() or "5" in str(info):
                    log.info(f"⏸  [{svc}] Platform limit hit — skipping for this run")
                    full_channels.add(svc)
                else:
                    log.warning(f"❌ [{svc}] {p['name'][:30]}: {info}")
                    fail += 1
            time.sleep(0.4)

        # All channels full — no point continuing
        if len(full_channels) == len(CHANNELS):
            log.info("All channels at capacity — run complete")
            break

    log.info(f"Done: {ok} posted, {fail} failed — sleeping 12h")

if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception as e:
            log.error(f"Run error: {e}")
        time.sleep(12 * 3600)  # 12h
