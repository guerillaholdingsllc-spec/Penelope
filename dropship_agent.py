"""
DropshipAgent - Autonomous dropship operations agent for Penelope
Handles: trend scraping → product scoring → AutoDS/Shopify import → marketing content → social distribution
Runs as a thread inside agent_army.py alongside existing agents.
"""

import os
import time
import json
import random
import datetime
import requests
from google import genai

# ── Config pulled from vault env ─────────────────────────────────────────────
GOOGLE_API_KEY     = os.environ.get("GOOGLE_API_KEY", "")
FIRECRAWL_KEY      = os.environ.get("FIRECRAWL_KEY", "")
SHOPIFY_TOKEN      = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_STORE      = os.environ.get("SHOPIFY_STORE", "penelope-9678.myshopify.com")
TELEGRAM_TOKEN     = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "6183015901")
AMAZON_TAG         = os.environ.get("AMAZON_ASSOCIATES_TAG", "guerillahold2-20")

model = genai.GenerativeModel("gemini-2.5-flash")

AGENT = "DropshipAgent"
SHIPPED_DIR = "/root/workspace/Penelope/shipped"
FEED_FILE   = "/root/workspace/Penelope/feed.json"

# Cycle timing (seconds)
TREND_INTERVAL    = 3600 * 4   # scrape trends every 4 hours
PRODUCT_INTERVAL  = 3600 * 2   # import products every 2 hours
CONTENT_INTERVAL  = 3600       # generate marketing content every hour


# ── Utilities ─────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{AGENT}] {msg}", flush=True)



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


def post_to_feed(title: str, body: str, status: str = "success"):
    """Append entry to Penelope's shared feed.json."""
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE) as f:
                feed = json.load(f)
        feed.append({
            "agent": AGENT,
            "title": title,
            "body": body,
            "status": status,
            "ts": datetime.datetime.utcnow().isoformat(),
        })
        feed = feed[-500:]  # keep last 500
        with open(FEED_FILE, "w") as f:
            json.dump(feed, f, indent=2)
    except Exception as e:
        log(f"Feed write error: {e}")


def save_shipped(filename: str, content: str):
    os.makedirs(SHIPPED_DIR, exist_ok=True)
    path = os.path.join(SHIPPED_DIR, filename)
    with open(path, "w") as f:
        f.write(content)
    log(f"Saved: {path}")
    return path


def firecrawl_scrape(url: str) -> str:
    """Scrape a URL via Firecrawl, return markdown text."""
    try:
        r = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30,
        )
        data = r.json()
        return data.get("data", {}).get("markdown", "") or ""
    except Exception as e:
        log(f"Firecrawl error ({url}): {e}")
        return ""


def ai(prompt: str) -> str:
    """Call Gemini, return text."""
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        log(f"AI error: {e}")
        return ""


# ── Shopify helpers ───────────────────────────────────────────────────────────

def shopify_headers():
    return {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }


def shopify_create_product(title: str, description: str, price: str, vendor: str = "AutoDS", tags: str = "") -> dict:
    """Create a product draft in Shopify."""
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json"
    payload = {
        "product": {
            "title": title,
            "body_html": description,
            "vendor": vendor,
            "tags": tags,
            "status": "draft",
            "variants": [{"price": price, "inventory_management": "shopify"}],
        }
    }
    try:
        r = requests.post(url, headers=shopify_headers(), json=payload, timeout=15)
        if r.status_code == 201:
            product = r.json().get("product", {})
            log(f"Shopify product created: {product.get('id')} — {title}")
            return product
        else:
            log(f"Shopify error {r.status_code}: {r.text[:200]}")
            return {}
    except Exception as e:
        log(f"Shopify exception: {e}")
        return {}


def shopify_list_products(limit: int = 10) -> list:
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json?limit={limit}&status=any"
    try:
        r = requests.get(url, headers=shopify_headers(), timeout=10)
        return r.json().get("products", [])
    except Exception as e:
        log(f"Shopify list error: {e}")
        return []


# ── Trend scraping ────────────────────────────────────────────────────────────

TREND_SOURCES = [
    "https://www.amazon.com/gp/bestsellers/",
    "https://trends.google.com/trending?geo=US",
    "https://www.aliexpress.com/category/all/hot-products.html",
    "https://www.tiktok.com/tag/tiktokmademebuyit",
]


def scrape_trending_products() -> list[dict]:
    """Scrape multiple sources, return scored product candidates."""
    log("Scraping trending products...")
    raw_data = []

    for url in TREND_SOURCES:
        content = firecrawl_scrape(url)
        if content:
            raw_data.append(f"SOURCE: {url}\n{content[:3000]}")
        time.sleep(2)

    if not raw_data:
        log("No trend data scraped.")
        return []

    combined = "\n\n---\n\n".join(raw_data)

    prompt = f"""You are a dropshipping product analyst. Analyze this trending product data and identify the TOP 5 winning products to sell.

For each product output STRICT JSON (array of 5 objects):
[
  {{
    "title": "Product name",
    "niche": "category",
    "why_trending": "one sentence",
    "suggested_price": "29.99",
    "supplier_search": "search term for AutoDS/AliExpress",
    "tags": "comma,separated,tags",
    "marketing_angle": "one sentence USP for ads"
  }}
]

Prioritize: high margin potential, viral appeal, solves a problem, ships fast from US/EU suppliers.
Output ONLY the JSON array, no other text.

DATA:
{combined[:6000]}"""

    result = ai(prompt)

    try:
        # Strip any markdown code fences
        clean = result.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        products = json.loads(clean)
        log(f"Found {len(products)} trending products")
        return products
    except Exception as e:
        log(f"Parse error on product list: {e}\nRaw: {result[:300]}")
        return []


# ── Content generation ────────────────────────────────────────────────────────

def generate_product_content(product: dict) -> dict:
    """Generate full marketing package for a product."""
    prompt = f"""You are an elite dropshipping copywriter. Generate a complete marketing package for this product.

PRODUCT: {product['title']}
NICHE: {product['niche']}
MARKETING ANGLE: {product['marketing_angle']}
PRICE: ${product['suggested_price']}

Generate ALL of the following sections, labeled exactly as shown:

## SHOPIFY_DESCRIPTION
(SEO-optimized HTML product description, 200-300 words, include benefits, features, and a call to action)

## TIKTOK_SCRIPT
(15-second viral TikTok script, hook + problem + solution + CTA, conversational tone)

## INSTAGRAM_CAPTION
(Engaging Instagram caption with emojis, hashtags included, under 150 words)

## LINKEDIN_POST
(Professional LinkedIn post connecting the product to productivity/lifestyle trends, 100 words)

## EMAIL_SUBJECT
(5 subject line variants, numbered)

## FACEBOOK_AD
(Facebook ad copy: headline + primary text + CTA, under 100 words total)"""

    content = ai(prompt)
    return {
        "product": product,
        "content": content,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }


def parse_section(content: str, section: str) -> str:
    """Extract a section from the generated content."""
    try:
        start = content.find(f"## {section}")
        if start == -1:
            return ""
        start = content.find("\n", start) + 1
        end = content.find("## ", start)
        return content[start:end].strip() if end != -1 else content[start:].strip()
    except Exception:
        return ""


# ── Main agent loop ───────────────────────────────────────────────────────────

def run_dropship_agent():
    log("DropshipAgent starting...")
    _tg_emergency_only("DropshipAgent online — starting autonomous dropship operations")

    last_trend_scrape = 0
    last_product_import = 0
    last_content_gen = 0
    product_queue: list[dict] = []

    while True:
        now = time.time()

        # ── Step 1: Scrape trending products ──────────────────────────────
        if now - last_trend_scrape >= TREND_INTERVAL:
            try:
                products = scrape_trending_products()
                if products:
                    product_queue.extend(products)
                    # Dedupe by title
                    seen = set()
                    deduped = []
                    for p in product_queue:
                        if p["title"] not in seen:
                            seen.add(p["title"])
                            deduped.append(p)
                    product_queue = deduped[-20:]  # keep latest 20

                    summary = "\n".join([f"- {p['title']} (${p['suggested_price']})" for p in products])
                    save_shipped(
                        f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}_trending_products.md",
                        f"# Trending Products — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}\n\n{summary}\n\n```json\n{json.dumps(products, indent=2)}\n```"
                    )
                    _tg_emergency_only(f"Found {len(products)} trending products: {products[0]['title']}, {products[1]['title'] if len(products) > 1 else '...'}")
                    post_to_feed("Trending Products Scraped", summary)
                last_trend_scrape = now
            except Exception as e:
                log(f"Trend scrape error: {e}")

        # ── Step 2: Import product to Shopify ─────────────────────────────
        if now - last_product_import >= PRODUCT_INTERVAL and product_queue:
            try:
                product = product_queue.pop(0)
                log(f"Importing to Shopify: {product['title']}")

                # Generate description first
                content_pkg = generate_product_content(product)
                description = parse_section(content_pkg["content"], "SHOPIFY_DESCRIPTION")

                if SHOPIFY_TOKEN and description:
                    shopify_product = shopify_create_product(
                        title=product["title"],
                        description=description,
                        price=product["suggested_price"],
                        tags=product.get("tags", ""),
                    )
                    if shopify_product:
                        _tg_emergency_only(f"✅ Product imported to Shopify: {product['title']} @ ${product['suggested_price']}")
                        post_to_feed(
                            f"Shopify Product Created: {product['title']}",
                            f"ID: {shopify_product.get('id')} | Price: ${product['suggested_price']}\n{product['marketing_angle']}"
                        )
                else:
                    log("Shopify token missing or no description generated — skipping import")

                # Save full content package regardless
                slug = product["title"].lower().replace(" ", "_")[:40]
                save_shipped(
                    f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}_dropship_{slug}.md",
                    f"# {product['title']}\n\n**Niche:** {product['niche']}\n**Price:** ${product['suggested_price']}\n**Why Trending:** {product['why_trending']}\n\n---\n\n{content_pkg['content']}"
                )

                last_product_import = now
            except Exception as e:
                log(f"Product import error: {e}")

        # ── Step 3: Generate & post marketing content ──────────────────────
        if now - last_content_gen >= CONTENT_INTERVAL:
            try:
                # Pick a random product from Shopify to market
                shop_products = shopify_list_products(limit=20)
                if shop_products:
                    target = random.choice(shop_products)
                    title = target.get("title", "")
                    price = target.get("variants", [{}])[0].get("price", "")
                    tags = target.get("tags", "")

                    prompt = f"""Write a high-converting TikTok/Instagram/LinkedIn social media post for this dropship product.

Product: {title}
Price: ${price}
Tags: {tags}

Write one punchy post (under 100 words) with emojis and 5 relevant hashtags. Make it feel organic, not salesy.
Include the store link placeholder: [STORE_LINK]"""

                    post_content = ai(prompt)
                    if post_content:
                        slug = title.lower().replace(" ", "_")[:30]
                        save_shipped(
                            f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}_social_{slug}.md",
                            f"# Social Post: {title}\n\n{post_content}"
                        )
                        post_to_feed(f"Social Content: {title}", post_content)
                        log(f"Social content generated for: {title}")

                last_content_gen = now
            except Exception as e:
                log(f"Content gen error: {e}")

        # ── Sleep briefly then loop ────────────────────────────────────────
        time.sleep(60)


if __name__ == "__main__":
    run_dropship_agent()
