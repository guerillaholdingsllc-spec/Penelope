"""
ContentArmyAgent - Penelope's Autonomous Content Marketing Engine
Reads trending dropship products → deploys full content marketing stack

Generates per product:
  - LinkedIn native post (professional/value angle)
  - Instagram caption + 30 hashtags (lifestyle/visual)  
  - TikTok script (15-30 sec viral hook)
  - Twitter/X thread (5-tweet educational)
  - Reddit post (subreddit-targeted, value-first)
  - YouTube title + description + 20 tags
  - 3-email drip sequence (subject + body)
  - Amazon affiliate angle (guerillahold2-20)
  - SEO blog post outline (1500 word structure)
  - Pinterest pin description

Runs every 2 hours. Posts daily digest to Telegram.
"""

import os, time, json, datetime, re, glob
import urllib.request, urllib.parse

# ── Config ──────────────────────────────────────────────────────────────────
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6183015901")
FIRECRAWL_KEY    = os.environ.get("FIRECRAWL_KEY", "")
AMAZON_TAG       = os.environ.get("AMAZON_ASSOCIATES_TAG", "guerillahold2-20")
SHOPIFY_STORE    = os.environ.get("SHOPIFY_STORE", "penelope-9678.myshopify.com")
SHIPPED_DIR      = "/root/workspace/Penelope/shipped"
MARKETING_DIR    = "/root/workspace/Penelope/shipped/marketing"
PROCESSED_LOG    = "/root/workspace/Penelope/content_army_processed.json"
AGENT            = "ContentArmyAgent"
INTERVAL         = 7200  # 2 hours

# ── AI Setup ─────────────────────────────────────────────────────────────────
try:
    from google import genai as genai_client
    client = genai_client.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
except Exception:
    try:
        import google.generativeai as _g
        _g.configure(api_key=GOOGLE_API_KEY)
        _model = _g.GenerativeModel("gemini-2.5-flash")
        class _FakeClient:
            class models:
                @staticmethod
                def generate_content(model, contents):
                    class R: text = _model.generate_content(contents).text
                    return R()
        client = _FakeClient()
    except Exception:
        client = None

def log(msg):
    print(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}][{AGENT}] {msg}", flush=True)


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


def ai(prompt, max_tokens=2000):
    if not client:
        return ""
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return r.text.strip()
    except Exception as e:
        log(f"AI err: {e}")
        return ""

def scrape(url):
    if not FIRECRAWL_KEY: return ""
    try:
        req_data = json.dumps({"url": url, "formats": ["markdown"]}).encode()
        req = urllib.request.Request(
            "https://api.firecrawl.dev/v1/scrape",
            data=req_data,
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read()).get("data", {}).get("markdown", "")[:3000]
    except Exception:
        return ""

# ── Product Parsing ───────────────────────────────────────────────────────────
def load_processed():
    try:
        return set(json.load(open(PROCESSED_LOG)))
    except Exception:
        return set()

def save_processed(processed):
    try:
        json.dump(list(processed), open(PROCESSED_LOG, "w"))
    except Exception:
        pass

def read_trending_products():
    """Read all trending product files from shipped/ and parse products."""
    products = []
    pattern = os.path.join(SHIPPED_DIR, "*_trending_products.md")
    for f in sorted(glob.glob(pattern), reverse=True)[:5]:  # last 5 files
        try:
            content = open(f).read()
            # Try to parse JSON block inside the markdown
            json_match = re.search(r'\[[\s\S]*?\]', content)
            if json_match:
                raw = json_match.group(0)
                parsed = json.loads(raw)
                for p in parsed:
                    p['_source_file'] = os.path.basename(f)
                    products.extend([p] if isinstance(p, dict) else [])
        except Exception:
            # Fallback: parse markdown list
            lines = [l.strip('- ').strip() for l in content.split('\n') if l.strip().startswith('- ')]
            for line in lines:
                title_match = re.match(r'^(.+?)\s*\(\$[\d.]+\)', line)
                price_match = re.search(r'\$[\d.]+', line)
                if title_match:
                    products.append({
                        "title": title_match.group(1).strip(),
                        "suggested_price": price_match.group(0).replace('$','') if price_match else "39.99",
                        "niche": "General",
                        "marketing_angle": f"Top trending product: {title_match.group(1)}",
                        "_source_file": os.path.basename(f)
                    })
    # Deduplicate by title
    seen = set()
    unique = []
    for p in products:
        key = p.get("title","").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    return unique

# ── Content Generation ────────────────────────────────────────────────────────
STORE_URL = f"https://{SHOPIFY_STORE}"

def gen_linkedin_post(p):
    prompt = f"""You are a LinkedIn content strategist for a dropshipping e-commerce store.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Niche: {p.get('niche','Consumer Goods')}
Marketing Angle: {p.get('marketing_angle','')}

Write a LinkedIn native post that:
- Opens with a bold hook (stat, question, or contrarian take)
- Shares 3-4 insights about WHY this product solves a real problem
- Uses line breaks for scanability (each thought on its own line)
- Ends with a subtle CTA ("Check it out →" + {STORE_URL})
- 150-250 words, professional but human tone
- NO emojis overload — max 2-3 strategic emojis
- Relevant hashtags at end (5-7)

Output ONLY the post text, ready to publish."""
    return ai(prompt)

def gen_instagram_caption(p):
    prompt = f"""You are an Instagram content creator for a trending products store.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Marketing Angle: {p.get('marketing_angle','')}

Write an Instagram caption that:
- Opens with a STRONG hook (first line must stop the scroll)
- 3-4 sentences describing the transformation/benefit
- Creates urgency or FOMO naturally
- Ends with CTA: "Shop now → link in bio 🔗"
- Then 2 blank lines, then exactly 30 hashtags in a block
- Mix of: 5 high-volume (1M+), 10 mid-volume (100K-1M), 10 niche (10K-100K), 5 branded

Output format:
CAPTION_TEXT

#hashtag1 #hashtag2 ... (30 total)"""
    return ai(prompt)

def gen_tiktok_script(p):
    prompt = f"""You are a viral TikTok scriptwriter for a trending products account.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Why Trending: {p.get('why_trending', p.get('marketing_angle',''))}

Write a TikTok video script (20-30 seconds when spoken):
- HOOK (0-3 sec): Pattern interrupt — something shocking or unexpected
- PROBLEM (3-8 sec): Relatable pain point the viewer feels RIGHT NOW
- SOLUTION (8-18 sec): Show/explain the product solving it dramatically  
- SOCIAL PROOF (18-23 sec): Quick stat or testimonial angle
- CTA (23-30 sec): "Link in bio" + urgency trigger

Format as:
[HOOK - 0-3s]
Script text here

[PROBLEM - 3-8s]
Script text here

[SOLUTION - 8-18s]
Script text here

[SOCIAL PROOF - 18-23s]
Script text here

[CTA - 23-30s]
Script text here

CAPTION: (TikTok caption + 10 hashtags)
TRENDING SOUNDS: (3 trending sound suggestions for this type of content)"""
    return ai(prompt)

def gen_twitter_thread(p):
    prompt = f"""You are a Twitter growth expert. Write a 5-tweet thread about this product.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Angle: {p.get('marketing_angle','')}

Rules:
- Tweet 1: HOOK that makes people want to read the whole thread (end with "🧵")
- Tweet 2: The problem (relatable, specific)
- Tweet 3: The solution (how this product helps, with specifics)
- Tweet 4: Stats/social proof angle or "people don't know that..."
- Tweet 5: CTA + link ({STORE_URL}) + 3-5 hashtags

Each tweet must be under 280 characters.
Format as:
Tweet 1: [text]
Tweet 2: [text]
...etc"""
    return ai(prompt)

def gen_reddit_post(p):
    niche = p.get('niche','').lower()
    subreddits = {
        'beauty': ['r/SkincareAddiction', 'r/beauty', 'r/MakeupAddiction'],
        'tech': ['r/gadgets', 'r/BuyItForLife', 'r/homeautomation'],
        'pet': ['r/dogs', 'r/cats', 'r/Pets'],
        'kitchen': ['r/Cooking', 'r/BuyItForLife', 'r/mealprep'],
        'fitness': ['r/fitness', 'r/homegym', 'r/loseit'],
        'car': ['r/cars', 'r/AutoDetailing', 'r/CarTalk'],
        'home': ['r/homeimprovement', 'r/InteriorDesign', 'r/BuyItForLife'],
        'baby': ['r/Parenting', 'r/NewParents', 'r/beyondthebump'],
    }
    target_subs = ['r/BuyItForLife', 'r/deals', 'r/shutupandtakemymoney']
    for key, subs in subreddits.items():
        if key in niche:
            target_subs = subs
            break
    
    prompt = f"""Write a genuine Reddit post about this product. Sound like a real person, NOT marketing.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Why Good: {p.get('why_trending', p.get('marketing_angle',''))}
Target subreddits: {', '.join(target_subs)}

Format:
SUBREDDIT: [best subreddit from the list]
TITLE: [Reddit title — question or "I found..." style, no sales language]
BODY: [2-3 paragraphs. Personal story angle. Mention you found it at ~${p.get('suggested_price','39.99')}. Include store link naturally: {STORE_URL}]
FLAIR: [appropriate flair for that subreddit]"""
    return ai(prompt)

def gen_youtube_content(p):
    prompt = f"""You are a YouTube SEO expert. Create content for a product review/showcase video.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Key Benefits: {p.get('marketing_angle','')}
Amazon Associates Tag: {AMAZON_TAG}

Generate:
TITLE_1: [SEO title, 60 chars max, includes "review" or "unboxing" or benefit keyword]
TITLE_2: [Alternative title with different angle]
TITLE_3: [Curiosity-gap title]

DESCRIPTION:
[First 2 lines — most important, show in search preview]
[3 paragraphs about the product]
[Timestamps section: 0:00 Intro, 0:30 Unboxing, 1:30 Features, 3:00 Demo, 5:00 Final Thoughts]
[Link: {STORE_URL}]
[Amazon search angle: https://www.amazon.com/s?k={urllib.parse.quote(p['title'])}&tag={AMAZON_TAG}]
[#ProductName #ProductReview]

TAGS: [20 comma-separated YouTube tags, mix of specific and general]

THUMBNAIL_CONCEPT: [Describe the thumbnail: text overlay, image composition, colors]"""
    return ai(prompt)

def gen_email_sequence(p):
    prompt = f"""Write a 3-email drip sequence for someone who viewed but didn't buy this product.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Store: {STORE_URL}

Email 1 (Send: 1 hour after view):
SUBJECT_A: [benefit-focused]
SUBJECT_B: [curiosity-gap]  
SUBJECT_C: [FOMO-based]
BODY: [150 words, address objections, include product link]

Email 2 (Send: 24 hours after view):
SUBJECT: [social proof angle]
BODY: [100 words, testimonial/review angle, soft CTA]

Email 3 (Send: 72 hours after view, FINAL):
SUBJECT: [last chance / scarcity]
BODY: [100 words, urgency + 10% discount angle, strong CTA]"""
    return ai(prompt)

def gen_amazon_content(p):
    search_url = f"https://www.amazon.com/s?k={urllib.parse.quote(p['title'])}&tag={AMAZON_TAG}"
    prompt = f"""Write Amazon affiliate content for this product niche.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Amazon Tag: {AMAZON_TAG}
Search URL: {search_url}

Generate:
COMPARISON_POST_INTRO: [200 words — "Best [product type] in 2026: Our Top Picks" intro]
PRODUCT_SUMMARY: [100 words product description optimized for "why buy this" angle]
BUYING_GUIDE_TIPS: [5 bullet points — what to look for when buying this type of product]
CTA_TEXT: [50 words — "Check current prices on Amazon" style CTA with affiliate link]"""
    return ai(prompt)

def gen_seo_blog_outline(p):
    prompt = f"""Create an SEO blog post outline targeting people searching for this product.

Product: {p['title']}
Target Price: ${p.get('suggested_price','39.99')}

Generate:
PRIMARY_KEYWORD: [main search term, 3-5 words]
SECONDARY_KEYWORDS: [5 related terms]
META_TITLE: [60 chars, includes primary keyword]
META_DESCRIPTION: [160 chars, click-worthy]

OUTLINE:
H1: [Main title]
H2: Introduction (hook + problem statement)
H2: What is [Product]? 
H3: Key Features
H3: Who Needs This?
H2: Top Benefits of [Product]
H3: Benefit 1 [with explanation prompt]
H3: Benefit 2
H3: Benefit 3
H2: How to Use [Product] — Step by Step
H2: [Product] vs Alternatives
H2: Where to Buy [Product] in 2026
[Include: {STORE_URL}]
H2: Final Verdict
H2: FAQ (5 questions with answer prompts)

ESTIMATED_WORD_COUNT: 1500
INTERNAL_LINKING_OPPORTUNITIES: [3 related posts to write next]"""
    return ai(prompt)

def gen_pinterest_pin(p):
    prompt = f"""Write Pinterest pin content for this product.

Product: {p['title']}
Price: ${p.get('suggested_price','39.99')}
Angle: {p.get('marketing_angle','')}
Store: {STORE_URL}

PIN_TITLE: [100 chars max, keyword-rich, benefit-focused]
PIN_DESCRIPTION: [500 chars, conversational, includes keywords naturally, ends with CTA + link]
BOARD_SUGGESTIONS: [5 board names this pin should go in]
KEYWORDS: [15 Pinterest keywords for this pin]"""
    return ai(prompt)

# ── Package Assembly ──────────────────────────────────────────────────────────
def generate_full_package(product):
    title = product.get("title", "Unknown Product")
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:40]
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')
    
    log(f"Generating content package: {title}")
    
    package = {
        "product": product,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "store_url": STORE_URL,
    }
    
    # Generate all content
    log(f"  → LinkedIn...")
    package["linkedin"] = gen_linkedin_post(product)
    
    log(f"  → Instagram...")
    package["instagram"] = gen_instagram_caption(product)
    
    log(f"  → TikTok...")
    package["tiktok"] = gen_tiktok_script(product)
    
    log(f"  → Twitter thread...")
    package["twitter"] = gen_twitter_thread(product)
    
    log(f"  → Reddit...")
    package["reddit"] = gen_reddit_post(product)
    
    log(f"  → YouTube...")
    package["youtube"] = gen_youtube_content(product)
    
    log(f"  → Email sequence...")
    package["email"] = gen_email_sequence(product)
    
    log(f"  → Amazon affiliate...")
    package["amazon"] = gen_amazon_content(product)
    
    log(f"  → SEO blog outline...")
    package["blog"] = gen_seo_blog_outline(product)
    
    log(f"  → Pinterest...")
    package["pinterest"] = gen_pinterest_pin(product)
    
    # Save as organized markdown
    os.makedirs(MARKETING_DIR, exist_ok=True)
    fname = os.path.join(MARKETING_DIR, f"{timestamp}_marketing_{slug}.md")
    
    content = f"""# 📦 Content Marketing Package
## {title} | ${product.get('suggested_price','39.99')} | {timestamp} UTC

**Niche:** {product.get('niche', 'General')}  
**Why Trending:** {product.get('why_trending', product.get('marketing_angle',''))}  
**Store:** {STORE_URL}  

---

## 💼 LINKEDIN POST
{package['linkedin']}

---

## 📸 INSTAGRAM CAPTION
{package['instagram']}

---

## 🎵 TIKTOK SCRIPT
{package['tiktok']}

---

## 🐦 TWITTER THREAD
{package['twitter']}

---

## 👾 REDDIT POST
{package['reddit']}

---

## 📺 YOUTUBE CONTENT
{package['youtube']}

---

## 📧 EMAIL SEQUENCE (3-PART DRIP)
{package['email']}

---

## 🛒 AMAZON AFFILIATE CONTENT
{package['amazon']}

---

## ✍️ SEO BLOG OUTLINE
{package['blog']}

---

## 📌 PINTEREST PIN
{package['pinterest']}

---
*Generated by ContentArmyAgent | Penelope AI System*
"""
    
    open(fname, 'w').write(content)
    log(f"Saved: {fname}")
    return fname, package

# ── Main Loop ─────────────────────────────────────────────────────────────────
def run_content_army():
    log("ContentArmyAgent starting...")
    _tg_emergency_only("ContentArmyAgent online 📢 — Deploying content marketing army overnight")
    
    processed = load_processed()
    session_count = 0
    
    while True:
        try:
            log("Scanning for products to market...")
            products = read_trending_products()
            log(f"Found {len(products)} total products, {len(processed)} already processed")
            
            new_products = [p for p in products if p.get("title","").lower().strip() not in processed]
            
            if not new_products:
                log("All products processed. Waiting for new trending products...")
            else:
                log(f"Processing {len(new_products)} new products...")
                session_packages = []
                
                for product in new_products:
                    try:
                        fname, pkg = generate_full_package(product)
                        processed.add(product.get("title","").lower().strip())
                        save_processed(processed)
                        session_packages.append((product['title'], pkg.get('suggested_price','0'), fname))
                        session_count += 1
                        time.sleep(5)  # rate limit between products
                    except Exception as e:
                        log(f"Error processing {product.get('title','?')}: {e}")
                
                # Send Telegram digest
                if session_packages:
                    digest_lines = [f"✅ Content army deployed for {len(session_packages)} products:\n"]
                    for title, price, fname in session_packages:
                        digest_lines.append(f"• {title} (${price})")
                    digest_lines.append(f"\n📁 Saved to: {MARKETING_DIR}")
                    digest_lines.append(f"📊 Total packages generated: {session_count}")
                    digest_lines.append("\nContent includes: LinkedIn, Instagram, TikTok, Twitter, Reddit, YouTube, Email, Amazon, Blog, Pinterest")
                    _tg_emergency_only("\n".join(digest_lines))
                    log(f"Session complete: {len(session_packages)} packages generated")
        
        except Exception as e:
            log(f"Loop error: {e}")
        
        log(f"Sleeping {INTERVAL//3600}h until next run...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run_content_army()
