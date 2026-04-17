import os, json, time, requests, datetime, glob
from google import genai

# ── ENV ───────────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID", "6183015901").strip()
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY", "2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4").strip()

WORK_DIR       = "/root/workspace/Penelope/shipped"
REPORT_DIR     = "/root/workspace/Penelope/crypto_reports"
FEED_FILE      = "/root/workspace/Penelope/feed.json"
SOCIAL_LOG     = "/root/workspace/Penelope/social_log.json"
GUMROAD_BASE   = "https://api.gumroad.com/v2"

client = genai.Client(api_key=GOOGLE_API_KEY)

def log(msg):
    print(f"[SOCIAL {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def post_to_feed(title, content, status="info"):
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE, "r") as f: feed = json.load(f)
        feed.insert(0, {"id": int(time.time()), "title": title, "content": content,
                        "status": status, "agent": "SocialPublisher",
                        "timestamp": datetime.datetime.now().isoformat()})
        with open(FEED_FILE, "w") as f: json.dump(feed[:100], f, indent=2)
    except Exception as e: log(f"Feed error: {e}")


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


def load_social_log():
    if os.path.exists(SOCIAL_LOG):
        with open(SOCIAL_LOG, "r") as f: return json.load(f)
    return {}

def save_social_log(data):
    with open(SOCIAL_LOG, "w") as f: json.dump(data, f, indent=2)

def get_gumroad_products():
    try:
        res = requests.get(f"{GUMROAD_BASE}/products",
            headers={"Authorization": f"Bearer {GUMROAD_KEY}"}, timeout=20)
        data = res.json()
        if data.get("success"):
            return data.get("products", [])
        return []
    except Exception as e:
        log(f"Gumroad error: {e}")
        return []

def generate_social_content(product_title, product_description, product_url, price, category):
    today = datetime.datetime.now().strftime("%B %d, %Y")

    # Map category to target audience and subreddits
    audience_map = {
        "cadaver": {
            "audience": "funeral home directors, coroner offices, and medical transport operators in California",
            "pain_points": "compliance headaches, driver shortages, documentation nightmares, losing contracts to bigger companies",
            "reddit": ["r/funeralhome", "r/mortuary", "r/smallbusiness", "r/entrepreneur"],
            "hashtags": "#FuneralHome #CadaverTransport #MedicalTransport #California #Compliance #SmallBusiness"
        },
        "crypto": {
            "audience": "retail crypto investors who are tired of losing money and want systematic risk management",
            "pain_points": "buying tops, panic selling bottoms, no risk management system, getting wrecked on altcoins",
            "reddit": ["r/CryptoCurrency", "r/CryptoMarkets", "r/investing", "r/personalfinance"],
            "hashtags": "#Crypto #Bitcoin #RiskManagement #Investing #DYOR #CryptoInvesting"
        },
        "callux": {
            "audience": "independent drivers, gig workers, and transportation entrepreneurs looking to increase income",
            "pain_points": "inconsistent income, no premium job access, competing on Uber/Lyft price race to bottom",
            "reddit": ["r/gig", "r/WorkOnline", "r/entrepreneur", "r/Flipping"],
            "hashtags": "#GigEconomy #SpecialtyTransport #MedicalTransport #SideHustle #Entrepreneur"
        },
        "ai_services": {
            "audience": "small business owners in transport and healthcare who want to automate without hiring",
            "pain_points": "spending hours on admin, missing calls, billing errors, can't afford full-time staff",
            "reddit": ["r/smallbusiness", "r/entrepreneur", "r/automation", "r/AItools"],
            "hashtags": "#AIAutomation #SmallBusiness #Efficiency #MedicalTransport #NoCode"
        }
    }

    info = audience_map.get(category, audience_map["ai_services"])

    prompt = f"""You are a copywriter for Guerilla Holdings, a business intelligence company run by a sharp entrepreneur in Sacramento, California.

Generate COMPLETE social media content to sell this product:

PRODUCT: {product_title}
PRICE: ${price}
URL: {product_url}
DESCRIPTION PREVIEW: {product_description[:500] if product_description else "Professional business resource"}
TARGET AUDIENCE: {info['audience']}
PAIN POINTS: {info['pain_points']}

Generate ALL of the following - each section clearly labeled:

---LINKEDIN_POST---
(Write a 150-200 word LinkedIn post that:
- Opens with a bold statement or surprising fact (no "I am excited to share")
- Addresses a real pain point the target audience has
- Explains what the product solves in plain language
- Ends with a soft CTA and the product URL
- Sounds like a real person, not a corporation
- NO emojis except maybe 1-2 max)

---TWITTER_THREAD---
(Write a 5-tweet thread:
Tweet 1: Hook - bold claim or surprising stat (under 280 chars)
Tweet 2: Problem - what pain this solves
Tweet 3: Solution - what's inside the product
Tweet 4: Social proof angle - who needs this
Tweet 5: CTA with URL and price
Number each tweet 1/5, 2/5, etc.)

---REDDIT_POST---
(Write a Reddit post for {info['reddit'][0]}:
- Title: engaging, not salesy, sounds like a community member
- Body: 150-200 words genuinely helpful content related to the topic
- Soft mention of the resource at the end
- Must not sound like an ad - lead with value)

---TELEGRAM_ANNOUNCEMENT---
(Write a Telegram message to announce this new product to followers:
- Short, punchy, 80-100 words
- Bold the product name
- Clear price and URL
- What problem it solves in one sentence
- Professional but direct)

---EMAIL_SUBJECT_LINES---
(Write 5 email subject lines for promoting this product:
- Mix of curiosity, urgency, benefit-focused
- Under 50 characters each
- No clickbait, no ALL CAPS)

Make all copy authentic, direct, and focused on real value. Today is {today}."""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(response, "text", "")
    except Exception as e:
        log(f"Content generation error: {e}")
        return ""

def parse_social_sections(content):
    sections = {}
    markers = [
        "LINKEDIN_POST", "TWITTER_THREAD", "REDDIT_POST",
        "TELEGRAM_ANNOUNCEMENT", "EMAIL_SUBJECT_LINES"
    ]
    for i, marker in enumerate(markers):
        start_tag = f"---{marker}---"
        end_tag = f"---{markers[i+1]}---" if i+1 < len(markers) else None
        start = content.find(start_tag)
        if start == -1: continue
        start += len(start_tag)
        end = content.find(end_tag) if end_tag else len(content)
        sections[marker] = content[start:end].strip()
    return sections

def save_social_content(product_name, sections, product_url, price):
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    safe_name = product_name.replace(" ", "_").replace("/", "-")[:40]
    fname = f"/root/workspace/Penelope/shipped/{date_str}_{safe_name}_social.md"
    content = f"# Social Content: {product_name}\nGenerated: {datetime.datetime.now().isoformat()}\nURL: {product_url}\nPrice: ${price}\n\n"
    for key, val in sections.items():
        content += f"## {key.replace('_', ' ')}\n\n{val}\n\n---\n\n"
    with open(fname, "w") as f: f.write(content)
    log(f"Saved social content: {fname}")
    return fname

def run_social_publisher():
    log("="*50)
    log("SOCIAL PUBLISHER STARTING")
    log("="*50)

    social_log = load_social_log()
    products = get_gumroad_products()

    if not products:
        log("No Gumroad products found — nothing to promote")
        return

    log(f"Found {len(products)} Gumroad products")
    new_content = []

    for product in products:
        pid = product.get("id", "")
        name = product.get("name", "")
        url = product.get("short_url", "")
        price = product.get("price", 0) / 100
        description = product.get("description", "")
        published = product.get("published", False)

        if not published or not url:
            continue

        # Determine category from product name
        name_lower = name.lower()
        if any(w in name_lower for w in ["cadaver", "funeral", "transport", "compliance"]):
            category = "cadaver"
        elif any(w in name_lower for w in ["crypto", "devve", "bitcoin", "risk report", "investor"]):
            category = "crypto"
        elif any(w in name_lower for w in ["callux", "driver", "certification", "specialty"]):
            category = "callux"
        else:
            category = "ai_services"

        # Check if we generated content for this product recently (within 7 days)
        last_gen = social_log.get(pid, {}).get("last_generated", "")
        if last_gen:
            days_ago = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_gen)).days
            if days_ago < 7:
                log(f"Skipping {name} — content generated {days_ago} days ago")
                continue

        log(f"Generating social content for: {name}")
        content = generate_social_content(name, description, url, price, category)

        if not content:
            log(f"Failed to generate content for {name}")
            continue

        sections = parse_social_sections(content)
        fname = save_social_content(name, sections, url, price)

        social_log[pid] = {
            "name": name,
            "last_generated": datetime.datetime.now().isoformat(),
            "file": fname,
            "url": url
        }
        save_social_log(social_log)

        new_content.append({
            "name": name,
            "url": url,
            "price": price,
            "sections": sections,
            "file": fname
        })

        post_to_feed(
            f"Social Content Ready: {name}",
            f"LinkedIn, Twitter, Reddit + email content generated\nProduct URL: {url}",
            "success"
        )
        time.sleep(3)

    # ── SEND TO TELEGRAM ──────────────────────────────────────────────────────
    if new_content:
        today = datetime.datetime.now().strftime("%B %d, %Y")
        summary = f"*GUERILLA HOLDINGS — SOCIAL CONTENT READY*\n{today}\n\n"
        summary += f"Content generated for {len(new_content)} products:\n\n"

        for item in new_content:
            summary += f"📦 *{item['name']}* — ${item['price']}\n{item['url']}\n\n"

        summary += "Full content (LinkedIn, Twitter threads, Reddit posts, email subjects) saved to shipped/ folder.\n\n"
        summary += "_Post this content daily to drive traffic to your Gumroad products._\n— Penelope"
        _tg_emergency_only(summary)

        # Send each product's Telegram announcement directly
        for item in new_content:
            if "TELEGRAM_ANNOUNCEMENT" in item["sections"]:
                time.sleep(2)
                _tg_emergency_only(f"🚀 *NEW PRODUCT*\n\n{item['sections']['TELEGRAM_ANNOUNCEMENT']}")

        log(f"DONE — {len(new_content)} products got social content")
    else:
        log("No new content needed")

    post_to_feed("Social Publisher Complete",
        f"Social content generated for {len(new_content)} products.", "success")

if __name__ == "__main__":
    log("Social Publisher starting")
    log(f"Gumroad: {'OK' if GUMROAD_KEY else 'MISSING'}")
    log(f"Gemini: {'OK' if GOOGLE_API_KEY else 'MISSING'}")
    log(f"Telegram: {'OK' if T_TOKEN else 'MISSING'}")

    while True:
        try:
            run_social_publisher()
        except Exception as e:
            log(f"CRITICAL ERROR: {e}")
            post_to_feed("Social Publisher Error", str(e), "error")
            try: _tg_emergency_only(f"Social Publisher Error: {e}")
            except: pass
        log("Sleeping 6 hours...")
        time.sleep(6 * 60 * 60)
