#!/usr/bin/env python3
"""
PENELOPE AUDIENCE ENGINE v1.0
24/7 lead capture, landing pages, funnels, and demographic building.
Spawns specialized sub-agents for each channel and brand.
"""

import os, json, time, requests, logging, random, hashlib
from datetime import datetime
from pathlib import Path
from google import genai
genai_client = genai

# ── Config ───────────────────────────────────────────────────────────────────
VAULT = "/root/penelope_vault.env"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"
LEADS_DIR = "/root/workspace/Penelope/leads"
PAGES_DIR = "/var/www/html/funnels"

def load_vault():
    env = {}
    try:
        with open(VAULT) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
GOOGLE_KEY = ENV.get("GOOGLE_API_KEY", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", ENV.get("NOTION_API_KEY", ""))
NOTION_AUDIENCE_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"  # Audience Intelligence DB

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
Path(LEADS_DIR).mkdir(parents=True, exist_ok=True)
Path(PAGES_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [AUDIENCE] %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/audience.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("audience")

# ── Gemini ───────────────────────────────────────────────────────────────────
def ai(prompt, temp=0.7):
    if not GOOGLE_KEY:
        return "ERROR: no key"
    try:
        client = genai_client.Client(api_key=GOOGLE_KEY)
        cfg = genai_client.types.GenerateContentConfig(temperature=temp)
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=cfg)
        return r.text
    except Exception as e:
        return f"ERROR: {e}"


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


def notion_add_lead(name, email, source, segment, business, funnel="Awareness", score=10, url="", notes=""):
    if not NOTION_TOKEN: return
    try:
        requests.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={
                "parent": {"database_id": NOTION_AUDIENCE_DB},
                "properties": {
                    "Name": {"title": [{"text": {"content": name or "Anonymous"}}]},
                    "Email": {"email": email} if email else {},
                    "Source": {"select": {"name": source}},
                    "Segment": {"multi_select": [{"name": s} for s in (segment if isinstance(segment, list) else [segment])]},
                    "Business": {"select": {"name": business}},
                    "Funnel": {"select": {"name": funnel}},
                    "Lead Score": {"number": score},
                    "Landing Page": {"url": url} if url else {},
                    "Notes": {"rich_text": [{"text": {"content": notes[:500]}}]},
                    "date:Last Touch:start": datetime.now().strftime("%Y-%m-%d"),
                    "date:Last Touch:is_datetime": 0,
                }
            },
            timeout=10
        )
        log.info(f"Lead added to Notion: {name} | {source} | {business}")
    except Exception as e:
        log.error(f"Notion lead add failed: {e}")

# ── BRANDS ───────────────────────────────────────────────────────────────────
BRANDS = {
    "gafc": {
        "name": "Glocks & Fried Chicken",
        "slug": "gafc",
        "tagline": "Real Talk. Real Safety. Real Community.",
        "audience": "Urban communities, gun safety advocates, minority communities, social justice-minded people aged 18-45",
        "segments": ["GAFC Fan", "Gun Safety"],
        "notion_business": "GAFC",
        "color": "#FF6B00",
        "offer": "Free gun safety guide + community membership",
        "cta": "Join the Movement",
        "notion_source": "GAFC"
    },
    "digital": {
        "name": "Guerilla Holdings Digital",
        "slug": "digital",
        "tagline": "AI-Powered. Revenue-Focused. Built Different.",
        "audience": "Entrepreneurs, side hustlers, small business owners, AI enthusiasts aged 25-50",
        "segments": ["Entrepreneur", "AI Enthusiast", "Digital Buyer"],
        "notion_business": "Digital Products",
        "color": "#00FF88",
        "offer": "Free AI Business Automation Starter Kit",
        "cta": "Get Free Access",
        "notion_source": "Landing Page"
    },
    "guerilla": {
        "name": "Guerilla Holdings LLC",
        "slug": "guerilla",
        "tagline": "We Build. We Scale. We Win.",
        "audience": "Business investors, B2B partners, grant organizations, startup founders",
        "segments": ["Entrepreneur", "Grant Seeker"],
        "notion_business": "Guerilla Holdings",
        "color": "#FFD700",
        "offer": "Partner with an AI-Native Holding Company",
        "cta": "Explore Partnership",
        "notion_source": "Landing Page"
    }
}

# ── LANDING PAGE GENERATOR ────────────────────────────────────────────────────
class LandingPageAgent:
    """Generates and deploys HTML landing pages + opt-in forms for each brand."""

    def generate_page(self, brand_key, variant="main"):
        brand = BRANDS[brand_key]
        log.info(f"Generating landing page: {brand_key}/{variant}")

        prompt = f"""Create a high-converting HTML landing page for this brand.

BRAND: {brand['name']}
TAGLINE: {brand['tagline']}
TARGET AUDIENCE: {brand['audience']}
OFFER: {brand['offer']}
CTA TEXT: {brand['cta']}
PRIMARY COLOR: {brand['color']}
VARIANT: {variant}

Requirements:
- Single HTML file with embedded CSS and JS
- Mobile-first responsive design
- Hero section with bold headline and subheadline
- 3 benefit bullets (pain → solution format)
- Email opt-in form (name + email fields)
- Strong CTA button in brand color
- Social proof section (placeholder stats)
- Footer with Guerilla Holdings LLC © 2026
- Form submits to: /api/lead?brand={brand_key}&source=landing_page
- On submit: show thank you message, log to console
- Clean, modern dark theme with accent color {brand['color']}
- NO external dependencies - pure HTML/CSS/JS only
- Include a countdown or urgency element
- Include mobile phone number field (optional)

Make it feel authentic, not corporate. This brand is minority-owned and community-focused.
Return ONLY the complete HTML code, nothing else."""

        html = ai(prompt, temp=0.8)
        
        # Clean if wrapped in markdown
        if "```html" in html:
            html = html.split("```html")[1].split("```")[0].strip()
        elif "```" in html:
            html = html.split("```")[1].split("```")[0].strip()

        return html

    def deploy_page(self, brand_key, html, variant="main"):
        brand = BRANDS[brand_key]
        path = Path(PAGES_DIR) / brand_key
        path.mkdir(parents=True, exist_ok=True)
        
        filename = f"index.html" if variant == "main" else f"{variant}.html"
        filepath = path / filename
        
        with open(filepath, "w") as f:
            f.write(html)
        
        url = f"https://trustchainservices.com/funnels/{brand_key}/{filename}"
        log.info(f"Page deployed: {url}")
        return url

    def run(self):
        log.info("Landing Page Agent starting...")
        deployed = []
        for brand_key in BRANDS:
            try:
                html = self.generate_page(brand_key)
                if len(html) > 500:  # Valid page
                    url = self.deploy_page(brand_key, html)
                    deployed.append(f"{brand_key}: {url}")
                    log.info(f"✅ Deployed: {brand_key}")
                else:
                    log.error(f"Page too short for {brand_key}: {html[:100]}")
            except Exception as e:
                log.error(f"Page gen failed for {brand_key}: {e}")
            time.sleep(2)
        
        if deployed:
            telegram(f"🚀 Landing Pages LIVE:\n" + "\n".join(deployed))
        return deployed

# ── LEAD CAPTURE API ──────────────────────────────────────────────────────────
class LeadCaptureAPI:
    """Flask endpoint that receives form submissions and routes to Notion + Close CRM."""

    def generate_api(self):
        api_code = '''#!/usr/bin/env python3
"""Lead Capture API — receives form submissions from all landing pages."""
from flask import Flask, request, jsonify
import json, requests, logging, os
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lead_api")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6183015901")

SEGMENT_MAP = {
    "gafc": ["GAFC Fan", "Gun Safety"],
    "digital": ["Entrepreneur", "AI Enthusiast"],
    "guerilla": ["Entrepreneur", "Grant Seeker"],
    "callux": ["Transport Pro"],
    "cadaverco": ["Transport Pro"],
}

BUSINESS_MAP = {
    "gafc": "GAFC",
    "digital": "Digital Products",
    "guerilla": "Guerilla Holdings",
    "callux": "CALLUX",
    "cadaverco": "CadaverCo",
}

def score_lead(data):
    score = 10
    if data.get("email"): score += 20
    if data.get("phone"): score += 15
    if data.get("name") and data["name"] != "Anonymous": score += 10
    if data.get("message"): score += 15
    return min(score, 100)

def add_to_notion(data):
    if not NOTION_TOKEN: return
    brand = data.get("brand", "digital")
    segments = SEGMENT_MAP.get(brand, ["Digital Buyer"])
    business = BUSINESS_MAP.get(brand, "Digital Products")
    score = score_lead(data)
    
    props = {
        "Name": {"title": [{"text": {"content": data.get("name", "Anonymous")[:100]}}]},
        "Source": {"select": {"name": "Landing Page"}},
        "Segment": {"multi_select": [{"name": s} for s in segments]},
        "Business": {"select": {"name": business}},
        "Funnel": {"select": {"name": "Interest"}},
        "Lead Score": {"number": score},
        "date:Last Touch:start": datetime.now().strftime("%Y-%m-%d"),
        "date:Last Touch:is_datetime": 0,
        "Notes": {"rich_text": [{"text": {"content": f"Source: {data.get('source','landing_page')} | Page: {data.get('page','/')} | Message: {data.get('message','')}"[:500]}}]},
    }
    if data.get("email"):
        props["Email"] = {"email": data["email"]}
    if data.get("phone"):
        props["Phone"] = {"phone_number": data["phone"]}
    if data.get("page"):
        props["Landing Page"] = {"url": data["page"]}

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
        json={"parent": {"database_id": NOTION_DB}, "properties": props},
        timeout=10
    )
    log.info(f"Notion lead: {r.status_code} | {data.get('email')}")
    return r.status_code

def telegram_alert(data):
    msg = f"""🎯 NEW LEAD CAPTURED
Brand: {data.get('brand','?').upper()}
Name: {data.get('name','Anonymous')}
Email: {data.get('email','none')}
Phone: {data.get('phone','none')}
Source: {data.get('source','landing_page')}
Score: {score_lead(data)}/100"""
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT, "text": msg},
        timeout=10
    )

@app.route("/api/lead", methods=["POST", "GET"])
def capture_lead():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        data["brand"] = data.get("brand", request.args.get("brand", "digital"))
        data["source"] = data.get("source", request.args.get("source", "landing_page"))
        data["page"] = request.referrer or data.get("page", "")
        
        log.info(f"Lead captured: {data.get('email','?')} | {data.get('brand','?')}")
        
        # Store to Notion
        add_to_notion(data)
        
        # Telegram alert for every lead
        try: telegram_alert(data)
        except: pass
        
        return jsonify({"success": True, "message": "You're in! Check your email."}), 200
    except Exception as e:
        log.error(f"Lead capture error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({"status": "lead_capture_active", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
'''
        return api_code

# ── CONTENT SEEDER AGENT ──────────────────────────────────────────────────────
class ContentSeederAgent:
    """Generates social content for Bluesky/Instagram to drive traffic to landing pages."""

    def generate_posts(self, brand_key, count=5):
        brand = BRANDS[brand_key]
        prompt = f"""Generate {count} social media posts for this brand to drive traffic to their landing page.

BRAND: {brand['name']}
TAGLINE: {brand['tagline']}
AUDIENCE: {brand['audience']}
OFFER: {brand['offer']}
LANDING PAGE URL: https://trustchainservices.com/funnels/{brand_key}/

Post requirements:
- Each post under 300 characters (Bluesky limit)
- Authentic voice, not salesy
- Include a hook, value, and soft CTA
- Mix formats: question, stat, story, tip, announcement
- Include relevant hashtags (2-3 max)
- Each post should drive to the landing page naturally

Return as JSON array: [{{"post": "...", "hashtags": ["..."], "type": "question|stat|story|tip|announcement"}}]"""

        response = ai(prompt, temp=0.8)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"): response = response[4:]
            return json.loads(response.strip())
        except:
            return [{"post": f"Check out {brand['name']} — {brand['tagline']} {brand['offer']} → trustchainservices.com/funnels/{brand_key}", "hashtags": [], "type": "announcement"}]

    def save_content_queue(self, brand_key, posts):
        path = Path(LEADS_DIR) / f"content_queue_{brand_key}.json"
        existing = []
        if path.exists():
            try:
                with open(path) as f:
                    existing = json.load(f)
            except: pass
        
        for p in posts:
            p["brand"] = brand_key
            p["created"] = datetime.now().isoformat()
            p["status"] = "queued"
        
        existing.extend(posts)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)
        
        log.info(f"Content queue: {len(posts)} posts saved for {brand_key}")

# ── FUNNEL ARCHITECT AGENT ────────────────────────────────────────────────────
class FunnelArchitectAgent:
    """Designs multi-step funnels: awareness → opt-in → nurture → conversion."""

    def generate_email_sequence(self, brand_key, trigger="opt_in"):
        brand = BRANDS[brand_key]
        prompt = f"""Write a 5-email nurture sequence for new leads who opted in at the {brand['name']} landing page.

BRAND: {brand['name']}
AUDIENCE: {brand['audience']}
OFFER: {brand['offer']}
TRIGGER: {trigger}

Email sequence:
1. Welcome + deliver the lead magnet (immediate)
2. Brand story + social proof (day 2)
3. Value email — teach something useful (day 4)
4. Soft pitch — introduce paid product (day 7)
5. Hard close — limited time offer (day 10)

Return as JSON array:
[{{"day": 0, "subject": "...", "preview": "...", "body": "...", "cta": "...", "cta_url": "..."}}]

Keep each email under 200 words. Conversational, not corporate."""

        response = ai(prompt, temp=0.7)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"): response = response[4:]
            sequence = json.loads(response.strip())
            
            # Save to file
            path = Path(LEADS_DIR) / f"email_sequence_{brand_key}.json"
            with open(path, "w") as f:
                json.dump(sequence, f, indent=2)
            log.info(f"Email sequence saved: {brand_key} ({len(sequence)} emails)")
            return sequence
        except Exception as e:
            log.error(f"Email sequence gen failed: {e}")
            return []

# ── NGINX CONFIG FOR FUNNELS ──────────────────────────────────────────────────
NGINX_FUNNEL_CONFIG = """
# Funnel routes - add to existing nginx config
location /funnels/ {
    alias /var/www/html/funnels/;
    try_files $uri $uri/ $uri/index.html =404;
    add_header Cache-Control "no-cache";
}

location /api/lead {
    proxy_pass http://localhost:5050/api/lead;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "POST, GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
}
"""

# ── MAIN ORCHESTRATOR ─────────────────────────────────────────────────────────
def run_audience_engine():
    log.info("=" * 60)
    log.info("AUDIENCE ENGINE STARTING")
    log.info("=" * 60)

    results = []

    # 1. Landing Pages
    log.info("Phase 1: Generating landing pages...")
    lp_agent = LandingPageAgent()
    pages = lp_agent.run()
    results.append(f"Landing pages: {len(pages)} deployed")

    # 2. Lead Capture API
    log.info("Phase 2: Deploying lead capture API...")
    api_agent = LeadCaptureAPI()
    api_code = api_agent.generate_api()
    api_path = "/root/workspace/Penelope/lead_capture_api.py"
    with open(api_path, "w") as f:
        f.write(api_code)
    log.info("Lead capture API written")
    results.append("Lead capture API: written to lead_capture_api.py")

    # 3. Content Seeder
    log.info("Phase 3: Generating content queues...")
    seeder = ContentSeederAgent()
    for brand_key in BRANDS:
        try:
            posts = seeder.generate_posts(brand_key, count=5)
            seeder.save_content_queue(brand_key, posts)
            results.append(f"Content queue {brand_key}: {len(posts)} posts")
            time.sleep(1)
        except Exception as e:
            log.error(f"Content seeder failed for {brand_key}: {e}")

    # 4. Email Sequences
    log.info("Phase 4: Generating email nurture sequences...")
    funnel = FunnelArchitectAgent()
    for brand_key in BRANDS:
        try:
            seq = funnel.generate_email_sequence(brand_key)
            results.append(f"Email sequence {brand_key}: {len(seq)} emails")
            time.sleep(1)
        except Exception as e:
            log.error(f"Email sequence failed for {brand_key}: {e}")

    # 5. Nginx config
    nginx_path = "/root/workspace/Penelope/nginx_funnel_addon.conf"
    with open(nginx_path, "w") as f:
        f.write(NGINX_FUNNEL_CONFIG)
    results.append("Nginx config: generated")

    summary = "AUDIENCE ENGINE COMPLETE\n" + "\n".join(f"✅ {r}" for r in results)
    log.info(summary)
    telegram(summary)
    return results

if __name__ == "__main__":
    run_audience_engine()
