#!/usr/bin/env python3
"""
PENELOPE EXECUTION ENGINE
The missing link — maps deployed skill objectives to real actions.
Called by conductor Phase 3 after Supreme Court passes.
"""
import os, json, requests, logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXEC] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/conductor_logs/execution.log"),
              logging.StreamHandler()])
log = logging.getLogger("exec")

def verify_url(url, min_size_kb=0):
    """QC gate — verify URL is live before publishing it."""
    try:
        r = requests.head(url, timeout=8, allow_redirects=True)
        if r.status_code != 200:
            log.warning(f"URL FAILED QC: {url} -> {r.status_code}")
            return False
        size = int(r.headers.get("content-length", 0)) // 1024
        if min_size_kb > 0 and size < min_size_kb:
            log.warning(f"URL too small: {url} ({size}KB < {min_size_kb}KB)")
            return False
        return True
    except Exception as e:
        log.warning(f"URL check error: {url}: {e}")
        return False



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
BREVO_KEY = ENV.get("BREVO_API_KEY", "")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
BLUESKY_HANDLE = ENV.get("BLUESKY_HANDLE", "")
BLUESKY_PASSWORD = ENV.get("BLUESKY_PASSWORD", "")
CLOSE_KEY = ENV.get("CLOSE_API_KEY", "")
GUMROAD_KEY = ENV.get("GUMROAD_API_KEY", "")
STRIPE_SK = ENV.get("STRIPE_SECRET_KEY", "")

RESULTS_LOG = Path("/root/workspace/Penelope/conductor_logs/execution_results.jsonl")

def log_result(skill_id, action, success, detail, revenue=0):
    entry = {
        "ts": datetime.now().isoformat(),
        "skill_id": skill_id,
        "action": action,
        "success": success,
        "detail": str(detail)[:200],
        "revenue": revenue
    }
    with open(RESULTS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def post_to_bluesky(text):
    """Post content to Bluesky."""
    try:
        r = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_PASSWORD}, timeout=10)
        if r.status_code != 200:
            return False, f"Login failed: {r.status_code}"
        session = r.json()
        r2 = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={"repo": session["did"], "collection": "app.bsky.feed.post",
                  "record": {"text": text[:300], "createdAt": datetime.now().isoformat() + "Z",
                             "langs": ["en"]}}, timeout=10)
        return r2.status_code in [200, 201], r2.json().get("uri", "posted")
    except Exception as e:
        return False, str(e)

def publish_to_wordpress(title, content):
    """Publish blog post to WordPress."""
    import base64
    WP_USER = ENV.get("WORDPRESS_USERNAME", "Penelope")
    WP_PASS = ENV.get("WORDPRESS_APP_PASSWORD", "")
    if not WP_PASS:
        return False, "No WP credentials"
    token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.post("http://localhost:8081/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            json={"title": title[:200], "content": content, "status": "publish"}, timeout=30)
        if r.status_code in [200, 201]:
            return True, r.json().get("link", "published")
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def send_b2b_outreach_email(target_industry):
    """Send B2B cold outreach via Brevo."""
    if not BREVO_KEY:
        return False, "No Brevo key"
    
    sequences_path = Path("/root/workspace/Penelope/leads/b2b_outreach_sequences.json")
    if not sequences_path.exists():
        return False, "No sequences"
    
    sequences = json.loads(sequences_path.read_text())
    seq = sequences.get(target_industry)
    if not seq:
        return False, f"No sequence for {target_industry}"
    
    emails = seq.get("sequence", [])
    if not emails:
        return False, "Empty sequence"
    
    email = emails[0]
    # Use a placeholder target email for now (would come from lead list)
    target_email = f"owner@{target_industry.replace(' ','').lower()}sacramento.example.com"
    
    r = requests.post("https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
        json={
            "sender": {"name": "Sydney Garmon", "email": ENV.get("GMAIL_FROM", "sydneygarmon@gmail.com")},
            "to": [{"email": target_email}],
            "subject": email.get("subject", f"Quick question about your {target_industry}"),
            "textContent": email.get("body", "")
        }, timeout=15)
    return r.status_code in [200, 201], f"Email queued for {target_industry}"

def drain_welcome_emails():
    """Send all queued welcome emails."""
    queue = Path("/root/workspace/Penelope/leads/welcome_queue.jsonl")
    if not queue.exists():
        return 0, "No queue"
    
    sent = 0
    lines = queue.read_text().strip().split("\n")
    remaining = []
    
    for line in lines:
        if not line.strip():
            continue
        try:
            lead = json.loads(line)
            if lead.get("status") == "sent":
                remaining.append(line)
                continue
            
            email = lead.get("email", "")
            name = lead.get("name", "Friend")
            brand = lead.get("brand", "digital")
            
            if BREVO_KEY and email:
                r = requests.post("https://api.brevo.com/v3/smtp/email",
                    headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
                    json={
                        "sender": {"name": "Guerilla Holdings", "email": ENV.get("GMAIL_FROM", "sydneygarmon@gmail.com")},
                        "to": [{"email": email, "name": name}],
                        "subject": f"Welcome to Guerilla Holdings, {name} 🔥",
                        "htmlContent": f"""<div style="font-family:Arial;max-width:600px;margin:0 auto;padding:24px;">
<h2>You\'re in, {name}.</h2>
<p>Welcome to Guerilla Holdings — we build AI-powered revenue systems for entrepreneurs who move differently.</p>
<p>Here\'s what to expect: over the next 10 days, you\'ll get our best frameworks for automating your business.</p>
<p>First one drops tomorrow.</p>
<p>— Sydney & the Guerilla Holdings team</p>
<p><a href="https://trustchainservices.com/funnels/{brand}/">Visit your dashboard →</a></p>
</div>"""
                    }, timeout=15)
                if r.status_code in [200, 201]:
                    lead["status"] = "sent"
                    sent += 1
            
            remaining.append(json.dumps(lead))
        except:
            remaining.append(line)
    
    queue.write_text("\n".join(remaining) + "\n")
    return sent, f"Sent {sent} welcome emails"

def get_high_value_blog_post():
    """Get an unposted blog post from army."""
    import glob
    published_log = Path("/root/workspace/Penelope/conductor_logs/wp_published.json")
    try:
        published = set(json.loads(published_log.read_text()))
    except:
        published = set()
    
    posts = sorted(glob.glob("/root/workspace/Penelope/blog/posts/*.json"),
                   key=os.path.getmtime, reverse=True)
    
    for p in posts:
        if p not in published:
            try:
                data = json.loads(open(p).read())
                if len(data.get("content","")) > 300 and data.get("title"):
                    return p, data
            except:
                pass
    return None, None

def execute_skill(skill):
    """
    Execute a skill based on its objective.
    Returns (success, action_taken, revenue_generated)
    """
    objective = skill.get("objective", "").lower()
    skill_id = skill.get("skill_id", "?")
    business = skill.get("business", "Digital")
    results = []
    revenue = 0

    # CONTENT PUBLISHING — post to WP + Bluesky
    if any(kw in objective for kw in ["blog", "post", "publish", "content", "wordpress", "article", "gafc", "gun safety", "cadaverco", "gloxsie", "bobo", "firearm", "character"]):
        post_path, post_data = get_high_value_blog_post()
        if post_data:
            title = post_data.get("title", "")[:200]
            content = post_data.get("content", "")
            
            # Publish to WordPress
            ok, detail = publish_to_wordpress(title, content)
            results.append(f"WP: {'✅' if ok else '❌'} {detail}")
            
            if ok:
                # Track published
                published_log = Path("/root/workspace/Penelope/conductor_logs/wp_published.json")
                try:
                    done = set(json.loads(published_log.read_text()))
                except:
                    done = set()
                done.add(post_path)
                published_log.write_text(json.dumps(list(done)))
            
            # Also post snippet to Bluesky
            snippet = f"{title[:200]}\n\nblog.trustchainservices.com"
            ok2, detail2 = post_to_bluesky(snippet)
            results.append(f"Bluesky: {'✅' if ok2 else '❌'} {detail2}")
    
    # EMAIL OUTREACH
    elif any(kw in objective for kw in ["email", "outreach", "nurture", "welcome", "sequence", "brevo", "gumroad", "book series", "upsell", "promotional", "lead list"]):
        sent, detail = drain_welcome_emails()
        results.append(f"Email: {detail}")
    
    # SOCIAL POSTING
    elif any(kw in objective for kw in ["bluesky", "social", "tweet", "share", "instagram", "thread", "awareness", "brand"]):
        # Get content from queue
        content_queue = Path("/root/workspace/Penelope/leads/content_queue_digital.json")
        if content_queue.exists():
            try:
                items = json.loads(content_queue.read_text())
                queued = [i for i in items if i.get("status") == "queued"]
                if queued:
                    post_text = queued[0].get("content", queued[0].get("text", ""))[:300]
                    if post_text:
                        ok, detail = post_to_bluesky(post_text)
                        results.append(f"Bluesky: {'✅' if ok else '❌'} {detail}")
            except: pass
    
    # GUMROAD / PRODUCT
    elif any(kw in objective for kw in ["gumroad", "product", "listing", "ebook", "digital product", "awakening", "fractured", "book", "digital"]):
        # Check current sales
        if GUMROAD_KEY:
            try:
                r = requests.get("https://api.gumroad.com/v2/products",
                    headers={"Authorization": f"Bearer {GUMROAD_KEY}"}, timeout=10)
                if r.status_code == 200:
                    prods = r.json().get("products", [])
                    total_sales = sum(p.get("sales_count", 0) for p in prods)
                    results.append(f"Gumroad: {len(prods)} products, {total_sales} total sales")
            except Exception as e:
                results.append(f"Gumroad check: {e}")
    
    # GRANT APPLICATION
    elif any(kw in objective for kw in ["grant", "gafc", "gun safety", "calvip", "everytown"]):
        results.append("Grant: GAFC grant hunter runs daily at 8AM — check conductor_logs/gafc_grant_hunter.log")
    
    # B2B OUTREACH
    elif any(kw in objective for kw in ["restaurant", "dental", "hvac", "sacramento", "business", "b2b", "cold", "callux", "transport", "funeral", "outreach sequence"]):
        ok, detail = send_b2b_outreach_email("restaurants")
        results.append(f"B2B: {detail}")
    
    # DEFAULT: rotate through actions so Penelope does varied things each cycle
    else:
        import random
        action_roll = random.randint(1, 4)
        
        if action_roll == 1:
            # Publish blog post to WordPress
            post_path, post_data = get_high_value_blog_post()
            if post_data:
                ok, detail = publish_to_wordpress(
                    post_data.get("title","")[:200],
                    post_data.get("content","")
                )
                results.append(f"WP publish: {'✅' if ok else '❌'} {detail}")
        
        elif action_roll == 2:
            # Post to Bluesky from content queue
            import glob, json as _json
            queue_files = glob.glob("/root/workspace/Penelope/leads/content_queue_*.json")
            for qf in queue_files[:1]:
                try:
                    items = _json.loads(open(qf).read())
                    queued = [i for i in items if i.get("status") == "queued"]
                    if queued:
                        text = queued[0].get("content", queued[0].get("text",""))[:300]
                        if text:
                            ok, detail = post_to_bluesky(text)
                            results.append(f"Bluesky post: {'✅' if ok else '❌'} {detail[:60]}")
                            queued[0]["status"] = "posted"
                            open(qf, "w").write(_json.dumps(items, indent=2))
                except: pass
        
        elif action_roll == 3:
            # Drain welcome emails via Brevo
            sent, detail = drain_welcome_emails()
            results.append(f"Email drain: {detail}")
        
        else:
            # Publish blog post (fallback)
            post_path, post_data = get_high_value_blog_post()
            if post_data:
                ok, detail = publish_to_wordpress(
                    post_data.get("title","")[:200],
                    post_data.get("content","")
                )
                results.append(f"WP publish: {'✅' if ok else '❌'} {detail}")
    
    # If nothing matched, default to publishing a blog post — always useful
    if not results:
        post_path, post_data = get_high_value_blog_post()
        if post_data:
            ok, detail_wp = publish_to_wordpress(
                post_data.get("title","")[:200],
                post_data.get("content","")
            )
            results.append(f"Fallback WP publish: {'✅' if ok else '❌'} {detail_wp}")
        else:
            # Post to Bluesky about GAFC as last resort
            ok, detail_bs = post_to_bluesky(
                "🔫 GAFC — Glocks & Fried Chicken: Gun safety education for our communities. "
                "Knowledge protects lives. #GunSafety #GAFC #Community"
            )
            results.append(f"Fallback Bluesky: {'✅' if ok else '❌'} {detail_bs}")

    success = any("✅" in r for r in results)
    detail = " | ".join(results) if results else "No action executed"
    
    log.info(f"Skill {skill_id}: {detail}")
    log_result(skill_id, objective[:60], success, detail, revenue)
    
    return success, detail, revenue

if __name__ == "__main__":
    import yaml, glob
    # Test: find and execute first verified skill
    for f in glob.glob("/root/workspace/Penelope/skillbank/*.yaml"):
        with open(f) as fp:
            skill = yaml.safe_load(fp)
        if skill and skill.get("status") == "Verified":
            print(f"Executing: {skill.get("objective","?")[:60]}")
            ok, detail, rev = execute_skill(skill)
            print(f"Result: {'SUCCESS' if ok else 'FAIL'} | {detail}")
            break
