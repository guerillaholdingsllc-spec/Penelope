#!/usr/bin/env python3
"""
CONTENT PERFORMANCE TRACKER
Measures what content works and feeds winners back to army agents.
Runs daily as part of conductor cycle.
"""
import os, json, requests, logging
from datetime import datetime
from pathlib import Path

LOG = "/root/workspace/Penelope/conductor_logs/content_performance.log"
PERF_FILE = "/root/workspace/Penelope/leads/content_performance.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PERF] %(message)s",
    handlers=[logging.FileHandler(LOG), logging.StreamHandler()])
log = logging.getLogger("perf")

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
WP_USER = ENV.get("WORDPRESS_USERNAME", "Penelope")
WP_PASS = ENV.get("WORDPRESS_APP_PASSWORD", "")
BSKY_HANDLE = ENV.get("BLUESKY_HANDLE", "")
BSKY_PASS = ENV.get("BLUESKY_PASSWORD", "")

def check_wp_performance():
    """Get WordPress post performance metrics."""
    if not WP_PASS: return []
    import base64
    token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    try:
        r = requests.get("http://localhost:8081/wp-json/wp/v2/posts?status=publish&per_page=20&orderby=date",
            headers=headers, timeout=15)
        if r.status_code == 200:
            posts = r.json()
            performance = []
            for p in posts:
                performance.append({
                    "id": p["id"],
                    "title": p["title"]["rendered"][:80],
                    "date": p["date"],
                    "url": p["link"],
                    "comment_count": p.get("comment_count", 0),
                    # WordPress doesn't expose view counts without plugin
                    # Track by comment activity as proxy
                })
            return performance
    except Exception as e:
        log.error(f"WP perf check failed: {e}")
    return []

def check_bluesky_performance():
    """Get recent Bluesky post engagement."""
    if not BSKY_HANDLE or not BSKY_PASS: return []
    try:
        # Login
        r = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": BSKY_HANDLE, "password": BSKY_PASS}, timeout=10)
        if r.status_code != 200: return []
        session = r.json()
        
        # Get feed
        r2 = requests.get("https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            params={"actor": session["did"], "limit": 20}, timeout=10)
        
        if r2.status_code == 200:
            feed = r2.json().get("feed", [])
            performance = []
            for item in feed:
                post = item.get("post", {})
                record = post.get("record", {})
                counts = post.get("likeCount", 0), post.get("repostCount", 0), post.get("replyCount", 0)
                performance.append({
                    "text": record.get("text", "")[:80],
                    "created": record.get("createdAt", ""),
                    "likes": counts[0],
                    "reposts": counts[1],
                    "replies": counts[2],
                    "engagement": counts[0] + counts[1] * 2 + counts[2] * 1.5
                })
            # Sort by engagement
            performance.sort(key=lambda x: x["engagement"], reverse=True)
            return performance
    except Exception as e:
        log.error(f"Bluesky perf check failed: {e}")
    return []

def run():
    log.info("Content performance check starting...")
    wp_perf = check_wp_performance()
    bsky_perf = check_bluesky_performance()
    
    report = {
        "date": datetime.now().isoformat(),
        "wordpress": {"posts": len(wp_perf), "data": wp_perf},
        "bluesky": {
            "posts_checked": len(bsky_perf),
            "top_post": bsky_perf[0] if bsky_perf else {},
            "avg_engagement": sum(p["engagement"] for p in bsky_perf) / len(bsky_perf) if bsky_perf else 0,
            "data": bsky_perf[:5]  # Top 5
        }
    }
    
    # Save performance data
    with open(PERF_FILE, "w") as f:
        json.dump(report, f, indent=2)
    
    # Extract winning topics for army agents
    if bsky_perf:
        winners = [p["text"][:50] for p in bsky_perf[:3]]
        log.info(f"Top Bluesky content: {winners}")
        
        # Write winning topics to content strategy file
        strategy_path = Path("/root/workspace/Penelope/leads/content_strategy.json")
        strategy = {"winning_topics": winners, "updated": datetime.now().isoformat(),
                    "avg_engagement": report["bluesky"]["avg_engagement"]}
        with open(strategy_path, "w") as f:
            json.dump(strategy, f, indent=2)
    
    log.info(f"Performance report: {len(wp_perf)} WP posts, {len(bsky_perf)} Bluesky posts analyzed")
    return report

if __name__ == "__main__":
    run()
