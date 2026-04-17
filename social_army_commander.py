#!/usr/bin/env python3
"""
SOCIAL ARMY COMMANDER v1.0
Takes the 25-agent army's output and distributes it across all channels.

The army writes. This commander publishes, posts, and monetizes.

Channels:
- Bluesky (penelope76.bsky.social) — excerpts + hooks driving to blog/landing page  
- WordPress blog — full posts already generated, just need publishing
- Gumroad — ebook chapters bundled as digital products
- Amazon Associates — affiliate links injected into review posts
- Notion content tracker — what's published, what's queued, what performed
"""

import os, json, time, glob, logging, requests, random
from datetime import datetime
from pathlib import Path
from google import genai as _g

VAULT = "/root/penelope_vault.env"
BLOG_DIR = "/root/workspace/Penelope/blog/posts"
EBOOK_DIR = "/root/workspace/Penelope/ebooks"
LEADS_DIR = "/root/workspace/Penelope/leads"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"
FEED_FILE = "/root/workspace/Penelope/feed.json"

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
NOTION_OPS_DB = "aaac5800-d381-48c0-b135-2af97fe9d188"
WP_URL = ENV.get("WORDPRESS_URL", "https://trustchainservices.com")
WP_USER = ENV.get("WORDPRESS_USERNAME", "")
WP_PASS = ENV.get("WORDPRESS_APP_PASSWORD", "")
AMAZON_TAG = "guerillahold2-20"
BLUESKY_HANDLE = ENV.get("BLUESKY_HANDLE", "penelope76.bsky.social")
BLUESKY_PASSWORD = ENV.get("BLUESKY_PASSWORD", "")

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [COMMANDER] %(message)s',
    handlers=[logging.FileHandler(f"{LOG_DIR}/social_commander.log"), logging.StreamHandler()])
log = logging.getLogger("commander")

def ai(prompt, temp=0.7):
    try:
        client = _g.Client(api_key=GOOGLE_KEY)
        cfg = _g.types.GenerateContentConfig(temperature=temp)
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


class BlueskyPublisher:
    def __init__(self):
        self.session = None

    def login(self):
        if not BLUESKY_PASSWORD: return False
        r = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_PASSWORD}, timeout=10)
        if r.status_code == 200:
            self.session = r.json()
            return True
        return False

    def post(self, text):
        if not self.session and not self.login(): return False
        text = text[:300]
        r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {self.session['accessJwt']}"},
            json={"repo": self.session["did"], "collection": "app.bsky.feed.post",
                  "record": {"text": text, "createdAt": datetime.utcnow().isoformat() + "Z",
                             "langs": ["en-US"]}}, timeout=10)
        if r.status_code == 200:
            log.info(f"Bluesky posted: {text[:60]}")
            return True
        log.error(f"Bluesky post failed: {r.status_code} {r.text[:100]}")
        return False

    def post_blog_hook(self, post_data):
        """Convert a blog post into a Bluesky hook that drives clicks."""
        title = post_data.get("title", "")
        content = post_data.get("content", "")[:800]
        brand = post_data.get("agent", "")

        prompt = f"""Convert this blog post into a compelling Bluesky post (max 280 chars).

TITLE: {title}
CONTENT EXCERPT: {content}

Rules:
- Start with a hook (question, stat, or bold claim)
- 1-2 sentences max
- End with: "Full breakdown → trustchainservices.com"
- Include 1-2 relevant hashtags
- Sound human, not like an AI wrote it
- Match the niche: {brand}

Return ONLY the post text, nothing else."""

        hook = ai(prompt, temp=0.8)
        # Clean up
        hook = hook.strip().strip('"').strip("'")[:300]
        return self.post(hook)

# ── WORDPRESS PUBLISHER ───────────────────────────────────────────────────────
class WordPressPublisher:
    def __init__(self):
        self.base = f"{WP_URL}/wp-json/wp/v2"
        self.published_file = Path(LOG_DIR) / "wp_published.json"
        self.published = set()
        if self.published_file.exists():
            try:
                self.published = set(json.loads(self.published_file.read_text()))
            except: pass

    def save_published(self):
        self.published_file.write_text(json.dumps(list(self.published)))

    def inject_affiliate_links(self, content):
        """Inject Amazon Associates affiliate links into relevant content."""
        affiliate_products = {
            "AI tools": f"https://www.amazon.com/s?k=ai+tools+software&tag={AMAZON_TAG}",
            "laptop": f"https://www.amazon.com/s?k=best+laptop+2026&tag={AMAZON_TAG}",
            "book": f"https://www.amazon.com/s?k=science+fiction+books&tag={AMAZON_TAG}",
            "headset": f"https://www.amazon.com/s?k=noise+canceling+headset&tag={AMAZON_TAG}",
            "standing desk": f"https://www.amazon.com/s?k=standing+desk&tag={AMAZON_TAG}",
            "monitor": f"https://www.amazon.com/s?k=ultrawide+monitor&tag={AMAZON_TAG}",
        }
        for keyword, url in affiliate_products.items():
            if keyword.lower() in content.lower() and url not in content:
                content = content.replace(keyword, f'<a href="{url}" target="_blank">{keyword}</a>', 1)
        return content

    def publish(self, post_data):
        if not WP_USER or not WP_PASS:
            return None
        
        import base64 as _b64
        _token = _b64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        
        title = post_data.get("title", "Untitled")[:200]
        post_hash = hash(title)
        
        if post_hash in self.published:
            return None  # Already published
        
        content = self.inject_affiliate_links(post_data.get("content", ""))
        
        try:
            import base64 as _b64
            _token = _b64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
            _headers = {"Authorization": f"Basic {_token}", "Content-Type": "application/json"}
            r = requests.post(f"{self.base}/posts",
                headers=_headers,
                json={
                    "title": title,
                    "content": content,
                    "status": "publish",
                    "categories": [],
                    "tags": [],
                },
                timeout=30)
            
            if r.status_code in [200, 201]:
                post_id = r.json().get("id")
                post_url = r.json().get("link", "")
                self.published.add(post_hash)
                self.save_published()
                log.info(f"WordPress published: {title[:50]} | {post_url}")
                return post_url
            else:
                log.error(f"WordPress publish failed: {r.status_code}")
                return None
        except Exception as e:
            log.error(f"WordPress error: {e}")
            return None

# ── CONTENT COMMANDER ─────────────────────────────────────────────────────────
class ContentCommander:
    """Orchestrates the army's output across all channels."""

    def __init__(self):
        self.bsky = BlueskyPublisher()
        self.wp = WordPressPublisher()
        self.posted_to_bsky = self._load_posted("bsky_posted.json")
        self.bsky.login()

    def _load_posted(self, fname):
        path = Path(LOG_DIR) / fname
        try:
            return set(json.loads(path.read_text()))
        except: return set()

    def _save_posted(self, posted_set, fname):
        path = Path(LOG_DIR) / fname
        path.write_text(json.dumps(list(posted_set)))

    def get_unposted_blogs(self, limit=5):
        """Get blog posts not yet distributed."""
        all_posts = glob.glob(f"{BLOG_DIR}/*.json")
        all_posts.sort(key=os.path.getmtime, reverse=True)  # newest first
        
        unposted = []
        for p in all_posts:
            if p not in self.posted_to_bsky:
                try:
                    data = json.loads(open(p).read())
                    data["_file"] = p
                    unposted.append(data)
                    if len(unposted) >= limit:
                        break
                except: pass
        return unposted

    def generate_brand_content(self, count=10):
        """Generate fresh branded content for GAFC, Digital, Guerilla for Bluesky."""
        brands = [
            {
                "name": "GAFC",
                "context": "Glocks & Fried Chicken — gun safety education for marginalized communities. Authentic, community-focused, not corporate.",
                "hashtags": "#GunSafety #Community #GAFC #BlackOwnedBusiness"
            },
            {
                "name": "Guerilla Holdings Digital",
                "context": "AI-native holding company. Revenue engines. Entrepreneurs who build different.",
                "hashtags": "#AI #Entrepreneur #Automation #SideHustle"
            },
            {
                "name": "Revenue Mindset",
                "context": "Building autonomous income streams with AI. Real talk about money, systems, and freedom.",
                "hashtags": "#PassiveIncome #AIBusiness #FinancialFreedom"
            }
        ]

        posts = []
        for brand in brands:
            prompt = f"""Write {count//3} Bluesky posts for this brand.

BRAND: {brand['name']}
CONTEXT: {brand['context']}
HASHTAGS TO ROTATE: {brand['hashtags']}

Rules:
- Each post max 280 characters
- Mix formats: tip, question, stat, story hook, hot take
- Authentic voice — not corporate, not salesy  
- Drive curiosity about trustchainservices.com
- Use hashtags sparingly (1-2 max per post)
- Each post must be meaningfully different

Return as JSON array of strings (just the post text)."""

            response = ai(prompt, temp=0.85)
            try:
                if "```" in response:
                    response = response.split("```")[1]
                    if response.startswith("json"): response = response[4:]
                brand_posts = json.loads(response.strip())
                posts.extend(brand_posts)
            except:
                posts.append(f"{brand['name']}: {response[:250]}")

        return posts

    def run_distribution_cycle(self):
        """Main cycle: take army output, distribute to all channels."""
        log.info("Distribution cycle starting...")
        stats = {"bsky_posted": 0, "wp_published": 0, "new_content": 0}

        # 1. Post fresh branded content to Bluesky (3 posts per cycle)
        log.info("Generating branded Bluesky content...")
        brand_posts = self.generate_brand_content(count=9)
        for post_text in brand_posts[:3]:  # 3 per cycle, don't spam
            if self.bsky.post(post_text):
                stats["bsky_posted"] += 1
                time.sleep(3)

        # 2. Take top blog posts and push to Bluesky as hooks
        log.info("Distributing blog posts to Bluesky...")
        unposted = self.get_unposted_blogs(limit=3)
        for post_data in unposted:
            if self.bsky.post_blog_hook(post_data):
                self.posted_to_bsky.add(post_data["_file"])
                stats["bsky_posted"] += 1
                time.sleep(5)

        self._save_posted(self.posted_to_bsky, "bsky_posted.json")

        # 3. Publish blog posts to WordPress (5 per cycle)
        log.info("Publishing to WordPress...")
        all_posts = glob.glob(f"{BLOG_DIR}/*.json")
        all_posts.sort(key=os.path.getmtime, reverse=True)
        
        published_count = 0
        for p in all_posts[:20]:  # scan recent 20, publish up to 5
            try:
                data = json.loads(open(p).read())
                url = self.wp.publish(data)
                if url:
                    published_count += 1
                    stats["wp_published"] += 1
                    if published_count >= 5:
                        break
                    time.sleep(2)
            except: pass

        # 4. Save content queue for brand posts (remaining ones for next cycles)
        queue_path = Path(LEADS_DIR) / "army_content_queue.json"
        existing = []
        try:
            existing = json.loads(queue_path.read_text()) if queue_path.exists() else []
        except: pass
        
        new_queued = [{"post": p, "brand": "army", "status": "queued", 
                       "created": datetime.now().isoformat()} 
                      for p in brand_posts[3:]]  # Queue remaining
        existing.extend(new_queued)
        existing = existing[-200:]  # Keep last 200
        queue_path.write_text(json.dumps(existing, indent=2))
        stats["new_content"] = len(new_queued)

        # 5. Report ebook progress
        ebook_status = {}
        for book_num in range(1, 7):
            chapters = glob.glob(f"{EBOOK_DIR}/Book{book_num}/Chapter_*.md")
            ebook_status[f"Book{book_num}"] = len(chapters)

        summary = f"""Distribution cycle complete:
Bluesky posts: {stats['bsky_posted']}
WordPress published: {stats['wp_published']}
Content queued: {stats['new_content']}
Ebook progress: {', '.join(f'B{k[-1]}:{v}ch' for k,v in ebook_status.items())}
Blog library: {len(glob.glob(BLOG_DIR+'/*.json'))} posts"""

        log.info(summary)
        
        # Only telegram if meaningful activity
        if stats["bsky_posted"] > 0 or stats["wp_published"] > 0:
            telegram(summary)

        return stats

# ── EBOOK PACKAGER ────────────────────────────────────────────────────────────
class EbookPackager:
    """Bundle completed ebook books and prep for Gumroad/KDP listing."""

    def check_completions(self):
        completed = []
        for book_num in range(1, 7):
            chapters = sorted(glob.glob(f"{EBOOK_DIR}/Book{book_num}/Chapter_*.md"))
            if len(chapters) >= 24:
                completed.append({"book": book_num, "chapters": len(chapters), "path": f"{EBOOK_DIR}/Book{book_num}/"})
        return completed

    def generate_gumroad_listing(self, book_num):
        """Generate a Gumroad product listing for a completed ebook."""
        BOOK_TITLES = {
            1: "The Awakening", 2: "The Fractured Worlds", 3: "The Void Between",
            4: "The Architects of War", 5: "The Last Covenant", 6: "The Eternal Return"
        }
        title = BOOK_TITLES.get(book_num, f"Book {book_num}")

        # Read first chapter for context
        chapter_1 = ""
        try:
            chapter_1 = open(f"{EBOOK_DIR}/Book{book_num}/Chapter_01.md").read()[:1000]
        except: pass

        prompt = f"""Write a compelling Gumroad ebook listing for this sci-fi fantasy novel.

TITLE: {title} (Book {book_num} of The Chronicles Series)
EXCERPT: {chapter_1}

Write:
1. Tagline (under 10 words)
2. Product description (150 words, gripping, makes you want to buy)
3. What's included (24 chapters, approx X pages, etc.)
4. Suggested price: $4.99
5. Tags to use on Gumroad

Format for direct copy-paste into Gumroad."""

        listing = ai(prompt, temp=0.7)
        
        # Save listing
        listing_path = Path(EBOOK_DIR) / f"Book{book_num}" / "gumroad_listing.txt"
        listing_path.write_text(listing)
        log.info(f"Gumroad listing generated: Book {book_num}")
        return listing

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run():
    log.info("="*60)
    log.info("SOCIAL ARMY COMMANDER STARTING")
    log.info("="*60)

    commander = ContentCommander()
    packager = EbookPackager()

    # Check for completed ebooks and generate listings
    completed = packager.check_completions()
    if completed:
        for book in completed:
            log.info(f"Book {book['book']} complete! Generating Gumroad listing...")
            listing = packager.generate_gumroad_listing(book["book"])
            telegram(f"EBOOK COMPLETE — Book {book['book']} ready for Gumroad!\n\nListing generated at {book['path']}gumroad_listing.txt\n\nNext: Upload chapters + listing to gumroad.com")

    # Run distribution cycle
    stats = commander.run_distribution_cycle()
    return stats

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        log.info("Social Army Commander daemon starting (2h cycle)")
        telegram("📣 Social Army Commander ONLINE — distributing 3,362 posts across channels")
        while True:
            try:
                run()
            except Exception as e:
                log.error(f"Commander error: {e}")
            time.sleep(7200)  # Every 2 hours
    else:
        run()
