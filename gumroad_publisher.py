import os, json, time, requests, datetime, glob

# ── ENV ───────────────────────────────────────────────────────────────────────
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY", "XcMmW4EVZsRwLri7PZJTPlw_RsYOjSHOa4IhcTbGAUs").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID", "6183015901").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

WORK_DIR       = "/root/workspace/Penelope/shipped"
REPORT_DIR     = "/root/workspace/Penelope/crypto_reports"
FEED_FILE      = "/root/workspace/Penelope/feed.json"
PUBLISHED_LOG  = "/root/workspace/Penelope/gumroad_published.json"
GUMROAD_BASE   = "https://api.gumroad.com/v2"

# ── LOGGING ───────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[GUMROAD {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── FEED ──────────────────────────────────────────────────────────────────────
def post_to_feed(title, content, status="info"):
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE, "r") as f: feed = json.load(f)
        feed.insert(0, {
            "id": int(time.time()), "title": title, "content": content,
            "status": status, "agent": "GumroadPublisher",
            "timestamp": datetime.datetime.now().isoformat()
        })
        with open(FEED_FILE, "w") as f: json.dump(feed[:100], f, indent=2)
    except Exception as e: log(f"Feed error: {e}")

# ── TELEGRAM ──────────────────────────────────────────────────────────────────

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


def load_published():
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG, "r") as f: return json.load(f)
    return {}

def save_published(data):
    with open(PUBLISHED_LOG, "w") as f: json.dump(data, f, indent=2)

# ── GUMROAD API ───────────────────────────────────────────────────────────────
def gumroad_request(method, endpoint, data=None):
    url = f"{GUMROAD_BASE}/{endpoint}"
    headers = {"Authorization": f"Bearer {GUMROAD_KEY}"}
    try:
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=20)
        elif method == "POST":
            res = requests.post(url, headers=headers, data=data, timeout=20)
        elif method == "PUT":
            res = requests.put(url, headers=headers, data=data, timeout=20)
        result = res.json()
        if not result.get("success"):
            log(f"Gumroad error: {result.get('message', 'unknown')}")
        return result
    except Exception as e:
        log(f"Gumroad request error: {e}")
        return {"success": False}

def get_existing_products():
    result = gumroad_request("GET", "products")
    if result.get("success"):
        return {p["name"]: p for p in result.get("products", [])}
    return {}

def create_product(name, description, price_cents, tags=""):
    log(f"Creating product: {name} at ${price_cents/100:.2f}")
    data = {
        "name": name,
        "description": description,
        "price": price_cents,
        "published": "true",
        "tags": tags,
    }
    result = gumroad_request("POST", "products", data)
    if result.get("success"):
        product = result.get("product", {})
        log(f"Created: {product.get('short_url','')}")
        return product
    return None

def update_product(product_id, description):
    log(f"Updating product: {product_id}")
    data = {"description": description, "published": "true"}
    result = gumroad_request("PUT", f"products/{product_id}", data)
    return result.get("success", False)

# ── PARSE REPORT METADATA ─────────────────────────────────────────────────────
def parse_report_meta(content, filename):
    lines = content.split("\n")
    title = ""
    price_cents = 2700  # default $27

    # Extract title from first heading
    for line in lines[:10]:
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break

    # Determine price and type from filename/content
    fname_lower = filename.lower()
    if "crypto" in fname_lower or "risk_report" in fname_lower:
        ticker = ""
        for part in filename.replace(".md","").split("_"):
            if part.isupper() and len(part) <= 6:
                ticker = part
                break
        title = f"Crypto Risk Report: {ticker} — Weekly Intelligence" if ticker else "Crypto Risk Intelligence Report"
        price_cents = 2700  # $27 per report
        tags = "crypto,risk,intelligence,investing"
        category = "crypto"
    elif "fiverr" in fname_lower or "gig" in fname_lower:
        title = title or "AI Automation Fiverr Gig Package — Ready to Post"
        price_cents = 1700  # $17
        tags = "fiverr,ai,automation,freelance"
        category = "fiverr"
    elif "consulting" in fname_lower or "ai_consult" in fname_lower:
        title = title or "AI Consulting Package — Complete Business Framework"
        price_cents = 4700  # $47
        tags = "consulting,ai,business,automation"
        category = "consulting"
    elif "automation" in fname_lower:
        title = title or "Business Automation Service Package"
        price_cents = 2700  # $27
        tags = "automation,business,productivity"
        category = "automation"
    else:
        title = title or filename.replace(".md","").replace("_"," ").title()
        price_cents = 1700
        tags = "guerilla,holdings,ai,business"
        category = "general"

    return title, price_cents, tags, category

def build_gumroad_description(content, category):
    # Take first 2000 chars of content as preview, add CTA
    preview = content[:2000].strip()

    cta_map = {
        "crypto": """---
## What You Get
- Full professional crypto risk assessment report
- Risk score (1-10) with detailed breakdown  
- Tokenomics, liquidity, sentiment, security analysis
- Red flags and opportunity signals
- Buy/Hold/Sell recommendation with price targets
- Generated weekly with live market data by Penelope AI

## Who This Is For
Crypto investors who want institutional-grade research without paying $500/month for Bloomberg Terminal.

*Produced by Penelope — Guerilla Holdings Intelligence AI System*""",

        "consulting": """---
## What You Get
- Complete AI consulting offer framework
- Target client profile and pain points
- Pricing strategy ($297-$997 packages)
- LinkedIn post ready to publish
- 3-email outreach sequence (cold → value → close)
- Full consulting framework (4-6 steps)
- Sample audit report to show prospects

*Produced by Penelope — Guerilla Holdings AI System*""",

        "fiverr": """---
## What You Get
- Complete Fiverr gig package ready to post today
- SEO-optimized title (80 chars, keyword-rich)
- Full gig description (800-1000 words)
- 3-tier pricing structure
- 5 searchable tags
- FAQ section
- Upsell strategy

*Produced by Penelope — Guerilla Holdings AI System*""",

        "automation": """---
## What You Get
- Complete automation service offer
- Step-by-step workflow instructions
- Tool stack (Zapier, Make, etc.)
- Client proposal template
- Pricing and positioning guide

*Produced by Penelope — Guerilla Holdings AI System*""",

        "general": """---
*Produced by Penelope — Guerilla Holdings AI System*"""
    }

    cta = cta_map.get(category, cta_map["general"])
    return f"{preview}\n\n{cta}"

# ── MAIN PUBLISH CYCLE ────────────────────────────────────────────────────────
def publish_new_products():
    log("=" * 50)
    log("GUMROAD PUBLISHER STARTING")
    log("=" * 50)

    published = load_published()
    existing = get_existing_products()
    new_products = []
    updated_products = []

    # Collect all .md files from shipped/ and crypto_reports/
    all_files = glob.glob(f"{WORK_DIR}/*.md") + glob.glob(f"{REPORT_DIR}/*.md")
    log(f"Found {len(all_files)} deliverable files")

    for filepath in sorted(all_files, reverse=True):
        filename = os.path.basename(filepath)
        file_key = filename

        # Skip already published files that haven't changed
        file_mtime = str(int(os.path.getmtime(filepath)))
        if file_key in published and published[file_key].get("mtime") == file_mtime:
            log(f"Skipping unchanged: {filename}")
            continue

        try:
            with open(filepath, "r") as f:
                content = f.read()

            if len(content) < 200:
                log(f"Skipping too-short file: {filename}")
                continue

            title, price_cents, tags, category = parse_report_meta(content, filename)
            description = build_gumroad_description(content, category)

            # Check if product already exists on Gumroad
            if title in existing:
                product_id = existing[title]["id"]
                log(f"Updating existing product: {title}")
                if update_product(product_id, description):
                    url = existing[title].get("short_url", "")
                    published[file_key] = {"mtime": file_mtime, "product_id": product_id, "url": url, "title": title}
                    updated_products.append({"title": title, "url": url, "price": price_cents/100})
            else:
                # Create new product
                product = create_product(title, description, price_cents, tags)
                if product:
                    url = product.get("short_url", "")
                    pid = product.get("id", "")
                    published[file_key] = {"mtime": file_mtime, "product_id": pid, "url": url, "title": title}
                    new_products.append({"title": title, "url": url, "price": price_cents/100})
                    post_to_feed(
                        f"New Product Live: {title}",
                        f"Published to Gumroad at ${price_cents/100:.2f}\n{url}",
                        "success"
                    )

            save_published(published)
            time.sleep(1)

        except Exception as e:
            log(f"Error processing {filename}: {e}")

    # ── TELEGRAM SUMMARY ──────────────────────────────────────────────────────
    if new_products or updated_products:
        msg = f"*GUERILLA HOLDINGS — GUMROAD UPDATE*\n{datetime.datetime.now().strftime('%B %d, %Y')}\n\n"

        if new_products:
            msg += f"*NEW PRODUCTS LIVE ({len(new_products)})*\n"
            for p in new_products:
                msg += f"• {p['title']}\n  💰 ${p['price']:.2f} → {p['url']}\n\n"

        if updated_products:
            msg += f"*UPDATED PRODUCTS ({len(updated_products)})*\n"
            for p in updated_products:
                msg += f"• {p['title']} → {p['url']}\n"

        msg += f"\n— Penelope, Guerilla Holdings"
        _tg_emergency_only(msg)
        log(f"Done: {len(new_products)} new, {len(updated_products)} updated")
    else:
        log("No new products to publish")

    post_to_feed(
        "Gumroad Sync Complete",
        f"{len(new_products)} new products, {len(updated_products)} updated.",
        "success"
    )

# ── ENTRY POINT — runs every 2 hours checking for new deliverables ─────────────
if __name__ == "__main__":
    log("Gumroad Publisher starting")
    log(f"Gumroad: {'OK' if GUMROAD_KEY else 'MISSING'}")
    log(f"Watching: {WORK_DIR} + {REPORT_DIR}")

    while True:
        try:
            publish_new_products()
        except Exception as e:
            log(f"CRITICAL ERROR: {e}")
            post_to_feed("Gumroad Error", str(e), "error")
            try: _tg_emergency_only(f"Gumroad Publisher Error: {e}")
            except: pass
        log("Sleeping 2 hours...")
        time.sleep(2 * 60 * 60)
