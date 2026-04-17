#!/usr/bin/env python3
"""
Guerilla Holdings Reddit Content Distributor
Posts content from shipped/ to relevant subreddits
Uses PRAW (Python Reddit API Wrapper)
"""
import os, time, json, random, logging
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [REDDIT] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","")


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


def post_to_reddit_via_wp(post):
    """
    Since we don't have Reddit API keys yet, publish to WordPress blog
    which Reddit users can find organically, and schedule for manual Reddit posting
    """
    WP_URL = "http://localhost:8081"
    AUTH = ("Penelope", "sIB91DUWZabylQlV6giGD98C")
    
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", auth=AUTH, json={
        "title": post["title"],
        "content": post["body"].replace("\n", "<br>"),
        "status": "publish",
        "slug": post["title"][:50].lower().replace(" ","-").replace(",","")
    })
    return r.json().get("id"), r.json().get("link","ERROR")

if __name__ == "__main__":
    log.info("Starting content distribution run")
    results = []
    for post in POSTS:
        try:
            pid, link = post_to_reddit_via_wp(post)
            log.info(f"Published: {post['title'][:50]} -> {link}")
            results.append({"title": post["title"], "link": link})
            time.sleep(3)
        except Exception as e:
            log.error(f"Failed: {e}")
    
    if results:
        msg = f"CONTENT DISTRIBUTION\n\n{len(results)} posts published:\n"
        for r in results:
            msg += f"• {r['title'][:50]}\n  {r['link']}\n"
        _tg_emergency_only(msg)
    
    log.info(f"Done. {len(results)} posts distributed.")
