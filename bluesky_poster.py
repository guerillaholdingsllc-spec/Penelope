#!/usr/bin/env python3
"""
PENELOPE BLUESKY AUTO-POSTER
Posts content to Penelope's Bluesky (penelope76.bsky.social)
Runs every 4 hours via cron.
Pulls content from feed.json shipped/ directory.
"""
import os, json, time, requests, logging
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("/root/workspace/Penelope/conductor_logs/bluesky.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [BLUESKY] %(message)s",
    handlers=[logging.FileHandler(str(LOG)), logging.StreamHandler()])
log = logging.getLogger("bluesky")

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
HANDLE   = ENV.get("BLUESKY_HANDLE", "penelope76.bsky.social")
PASSWORD = ENV.get("BLUESKY_PASSWORD", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = ENV.get("TELEGRAM_CHAT_ID", "6183015901")

POSTED_FILE = Path("/root/workspace/Penelope/bluesky_posted.json")
FEED_FILE   = Path("/root/workspace/Penelope/feed.json")

# Content themes for autonomous posting when no shipped content exists
CONTENT_THEMES = [
    "AI is not replacing humans — it's replacing humans who don't use AI. The gap is widening daily. Which side are you on?",
    "Most people think building passive income requires capital. Wrong. It requires systems. Systems require time, not money.",
    "Guerilla Holdings is an AI-native holding company. Every dollar we make, an agent found it first.",
    "The automation playbook nobody tells you: Start with the task you hate most. That's always the highest ROI automation.",
    "GAFC — Glocks and Fried Chicken. Gun safety education in communities that need it most. Real impact, not optics.",
    "Revenue while you sleep isn't magic. It's 200+ hours of agent infrastructure running 24/7 so you don't have to.",
    "The best business model in 2026: AI creates the content, AI distributes it, AI monitors the results. You collect.",
    "Every problem is a product waiting to happen. What problem do you have right now that 10,000 other people also have?",
]

def get_session():
    """Authenticate with Bluesky."""
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": PASSWORD},
        timeout=15
    )
    if r.status_code == 200:
        return r.json()
    log.error(f"Auth failed: {r.status_code} {r.text[:200]}")
    return None

def post_to_bluesky(session, text):
    """Post a record to Bluesky."""
    # Truncate to 300 chars (Bluesky limit)
    if len(text) > 295:
        text = text[:292] + "..."
    
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
        "langs": ["en"]
    }
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {session['accessJwt']}"},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": record
        },
        timeout=15
    )
    if r.status_code == 200:
        uri = r.json().get("uri","")
        log.info(f"Posted: {text[:60]}... → {uri}")
        return True
    log.error(f"Post failed: {r.status_code} {r.text[:200]}")
    return False

def load_posted():
    if POSTED_FILE.exists():
        try: return set(json.loads(POSTED_FILE.read_text()))
        except: pass
    return set()

def save_posted(posted):
    tmp = POSTED_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(list(posted)[-200:]))  # keep last 200
    tmp.rename(POSTED_FILE)

def get_next_content(posted):
    """Get next piece of content to post - from shipped/ or themes."""
    # Try shipped content first
    shipped = Path("/root/workspace/Penelope/shipped")
    if shipped.exists():
        for f in sorted(shipped.glob("*.md"), reverse=True)[:20]:
            key = f.name
            if key in posted:
                continue
            try:
                content = f.read_text()
                # Extract first meaningful paragraph
                lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
                if lines:
                    text = lines[0][:295]
                    if len(text) > 50:  # meaningful content
                        return text, key
            except: pass
    
    # Try Gumroad product rotation (every 3rd post)
    if len(posted) % 3 == 0:
        try:
            import random as _r
            catalog_path = Path("/root/workspace/Penelope/gumroad_catalog.json")
            if catalog_path.exists():
                import json as _j
                catalog = _j.loads(catalog_path.read_text())
                if catalog:
                    p = _r.choice(catalog)
                    name = p["name"]
                    price = p["price"]
                    url = p["url"]
                    if "Chronicles" in name or "Awakening" in name:
                        text = f"📖 {name} — ${price:.2f}\nSci-fi epic, instant download\n{url}\n#SciFi #IndieAuthor #BookTok"
                    elif "Prompt" in name:
                        text = f"🚀 {name}\n25 AI business prompts built for leaders — ${price:.2f}\n{url}\n#AI #Business #ChatGPT"
                    elif "Checklist" in name:
                        text = f"⚠️ Know your data exposure before a breach.\nClient Data Safety Checklist — ${price:.2f}\n{url}\n#DataSecurity #SmallBusiness"
                    elif "Guide" in name:
                        text = f"📘 {name}\nAI × strategy × leadership — ${price:.2f}\n{url}\n#BusinessLeadership #AI"
                    elif "Playbook" in name or "Content" in name:
                        text = f"✍️ {name}\nGenerate 10x more content, faster — ${price:.2f}\n{url}\n#ContentMarketing #AI"
                    else:
                        text = f"🛍️ {name} — ${price:.2f}\nInstant digital download\n{url}\n#DigitalProducts #Gumroad"
                    key = f"gumroad_{p.get('id','x')}_{datetime.now().strftime('%Y%m%d_%H')}"
                    if key not in posted:
                        return text[:295], key
        except Exception as e:
            log.warning(f"Gumroad rotation error: {e}")

    # Fall back to themes - round robin
    theme_idx = len(posted) % len(CONTENT_THEMES)
    text = CONTENT_THEMES[theme_idx]
    key = f"theme_{theme_idx}_{datetime.now().strftime('%Y%m%d')}"
    if key not in posted:
        return text, key
    
    # All themes posted today - skip
    return None, None

def run():
    if not PASSWORD:
        log.error("BLUESKY_PASSWORD not in vault")
        return
    
    log.info(f"Bluesky poster starting — handle: {HANDLE}")
    
    session = get_session()
    if not session:
        return
    
    posted = load_posted()
    text, key = get_next_content(posted)
    
    if not text:
        log.info("No new content to post")
        return
    
    if post_to_bluesky(session, text):
        posted.add(key)
        save_posted(posted)
        log.info(f"Success. Total posted: {len(posted)}")
    else:
        log.warning("Post failed")

if __name__ == "__main__":
    run()
