#!/usr/bin/env python3
"""
PENELOPE BUYING SIGNAL DETECTOR
Monitors engagement signals and routes hot leads to Close CRM with priority flags.

Signals monitored:
- Bluesky post engagement (likes, reposts, replies)
- Email open chains (3+ consecutive opens = hot signal)
- Landing page return visits (tracked via attribution log)
- Content performance spikes (post goes viral)
"""
import json, requests
from datetime import datetime, timedelta
from pathlib import Path

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
BSKY_HANDLE = ENV.get("BLUESKY_HANDLE", "penelope76.bsky.social")
BSKY_PASS = ENV.get("BLUESKY_PASSWORD", "")
CLOSE_KEY = ENV.get("CLOSE_API_KEY", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", "")
NOTION_AUDIENCE_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"

HOT_LEAD_FILE = "/root/workspace/Penelope/leads/hot_leads.jsonl"


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


def get_bluesky_engagement():
    """Get engagement on recent Bluesky posts — detect viral signals."""
    if not BSKY_HANDLE or not BSKY_PASS: return []
    try:
        r = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": BSKY_HANDLE, "password": BSKY_PASS}, timeout=10)
        if r.status_code != 200: return []
        session = r.json()
        
        r2 = requests.get("https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            params={"actor": session["did"], "limit": 20}, timeout=10)
        
        if r2.status_code != 200: return []
        
        hot_posts = []
        for item in r2.json().get("feed", []):
            post = item.get("post", {})
            likes = post.get("likeCount", 0)
            reposts = post.get("repostCount", 0)
            replies = post.get("replyCount", 0)
            engagement = likes + reposts * 2 + replies * 1.5
            
            if engagement >= 5:  # threshold for "hot"
                record = post.get("record", {})
                hot_posts.append({
                    "text": record.get("text", "")[:100],
                    "engagement": engagement,
                    "likes": likes,
                    "reposts": reposts,
                    "replies": replies,
                    "uri": post.get("uri", "")
                })
        
        return sorted(hot_posts, key=lambda x: x["engagement"], reverse=True)
    except Exception as e:
        return []

def check_return_visitors():
    """Check attribution log for leads from same source multiple times (return visitors)."""
    attr_path = Path("/root/workspace/Penelope/leads/attribution_log.jsonl")
    if not attr_path.exists(): return []
    
    events = []
    with open(attr_path) as f:
        for line in f:
            try: events.append(json.loads(line.strip()))
            except: pass
    
    # Find leads that appear multiple times (return visitors)
    from collections import Counter
    lead_sources = [(e.get("lead_id",""), e.get("source","")) for e in events if e.get("lead_id")]
    counts = Counter(lead_sources)
    hot = [(lead_id, source, count) for (lead_id, source), count in counts.items() if count >= 2]
    return hot

def flag_hot_lead_in_crm(email, reason, score_boost=20):
    """Flag a lead as hot in Close CRM."""
    if not CLOSE_KEY or not email: return
    try:
        # Search for existing lead
        r = requests.get(f"https://api.close.com/api/v1/lead/?query=email:{email}",
            auth=(CLOSE_KEY, ""), timeout=10)
        if r.status_code == 200 and r.json().get("data"):
            lead_id = r.json()["data"][0]["id"]
            # Add note
            requests.post(f"https://api.close.com/api/v1/activity/note/",
                auth=(CLOSE_KEY, ""),
                json={"lead_id": lead_id, "note": "HOT SIGNAL: " + reason + " | " + datetime.now().strftime("%Y-%m-%d %H:%M")},
                timeout=10)
    except: pass

def run():
    signals_detected = []
    
    # 1. Check Bluesky engagement spikes
    hot_posts = get_bluesky_engagement()
    if hot_posts:
        top = hot_posts[0]
        msg = f"🔥 VIRAL CONTENT DETECTED\n\nPost: {top['text'][:80]}\nEngagement: {top['engagement']:.0f} (likes:{top['likes']} reposts:{top['reposts']})"


if __name__ == "__main__":
    signals = run()
    print(f"Buying signals: {len(signals)}")
    for s in signals:
        print(f"  {s}")
