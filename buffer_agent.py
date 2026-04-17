#!/usr/bin/env python3
"""
PENELOPE BUFFER POSTING AGENT v2
- Twitter: text posts (working)
- Pinterest: WaveSpeed-generated image + description
- TikTok: WaveSpeed-generated image (notification mode)
- Instagram/Facebook: auto-detected when connected, image posts
Runs every 4 hours via cron.
"""
import os, json, time, requests, logging, hashlib
from datetime import datetime
from pathlib import Path
from google import genai


# ── Quantum content topics (added for quantum product launch) ──────────────
QUANTUM_HOOKS = [
    "Is your business ready for the quantum computing threat? Here's what NIST recommends → {link}",
    "Hackers are stealing your encrypted data NOW to decrypt it later. This is called 'Harvest Now Decrypt Later.' Here's what small businesses need to know → {link}",
    "The EU has mandated quantum-safe encryption by 2030. Is your business ready? Plain-English guide → {link}",
    "NIST published new quantum-safe standards in 2024. Most small businesses have never heard of them. We explain it simply → {link}",
    "Google, IBM, and Bain are all preparing for the quantum threat. Here's what that means for YOUR small business → {link}",
    "You don't need a PhD to protect your business from quantum computing threats. Our plain-English guide shows you how → {link}",
    "5 questions every business owner should ask their IT team about quantum computing security → {link}",
    "The 'harvest now, decrypt later' attack: hackers are already preparing for quantum. Are you? → {link}",
]
QUANTUM_LINK = "https://trustchainservices.com/quantum-readiness"
LOG = Path("/root/workspace/Penelope/conductor_logs/buffer_agent.log")
LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [BUFFER] %(message)s",
    handlers=[logging.FileHandler(str(LOG)), logging.StreamHandler()])
log = logging.getLogger("buffer_agent")

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

ENV            = load_vault()
BUFFER_TOKEN   = ENV.get("BUFFER_API_TOKEN", "Uihf9wIwWb8Vs_0qAdeu8kfkHCTHbh-ZwSAyi3G2F1i")
GOOGLE_API_KEY = ENV.get("GOOGLE_API_KEY", "")
WAVESPEED_KEY  = ENV.get("WAVESPEED_API_KEY", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = ENV.get("TELEGRAM_CHAT_ID", "6183015901")

POSTED_FILE   = Path("/root/workspace/Penelope/buffer_posted.json")
IMG_DIR       = Path("/var/www/html/generated")
SERVER_URL    = "https://trustchainservices.com/generated"
GQL_URL       = "https://api.buffer.com/graphql"
BUF_HEADERS   = {"Authorization": f"Bearer {BUFFER_TOKEN}", "Content-Type": "application/json"}

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
IMG_DIR.mkdir(parents=True, exist_ok=True)

# ── Platform configs ──────────────────────────────────────────────────────────
PLATFORMS = {
    "twitter": {
        "needs_image": False,
        "char_limit": 280,
        "prompt": """Write a punchy Twitter/X post for Vessel Protocol — a 365-day manifestation app.
Formula: CT×A=M. App: https://ctxaxm.com — $4.99/month or $39.99/year.
Max 260 chars. End with → https://ctxaxm.com. Max 2 hashtags.
Themes: manifestation, daily practice, digital identity, becoming who you want to be.
Tone: thought-provoking, slightly philosophical, aspirational. Return only the tweet."""
    },
    "tiktok": {
        "needs_image": True,
        "char_limit": 2200,
        "prompt": """Write a TikTok caption for Vessel Protocol — a 365-day manifestation app.
Formula: CT×A=M. Hook line + 2 sentences + CTA "Link in bio → ctxaxm.com" + 3 hashtags.
Themes: manifestation, daily check-ins, becoming your best self, CT×A=M formula.
Tone: curious, authentic, gen-z adjacent. Return only the caption.""",
        "image_prompt": """Minimal aesthetic digital art: glowing vessel/jar containing swirling data streams 
and light particles, dark background, purple and cyan palette, clean modern style, 
no text, square format, suitable for TikTok."""
    },
    "pinterest": {
        "needs_image": True,
        "char_limit": 500,
        "prompt": """Write a Pinterest pin description for Vessel Protocol — 365-day manifestation protocol.
Formula: CT×A=M. App at ctxaxm.com — $4.99/month. Include the URL.
2 sentences of value + 5 keyword-rich hashtags.
Focus: manifestation, daily ritual, personal growth, 365-day challenge, becoming.
Tone: aspirational, clean, actionable. Return only the description.""",
        "image_prompt": """Beautiful infographic-style illustration: person surrounded by flowing data 
visualization charts and personal metrics, soft gradient background in purple/teal, 
minimal and modern, no text overlay, portrait format suitable for Pinterest."""
    },
    "instagram": {
        "needs_image": True,
        "char_limit": 2200,
        "prompt": """Write an Instagram caption alternating between:
- Vessel Protocol (digital identity, data as self-knowledge)  
- GAFC/Glocks and Fried Chicken (gun safety education, community empowerment in marginalized communities)
Pick one theme. 100 words max. End with 6 relevant hashtags.
Tone: authentic, community-first, real. Return only the caption.""",
        "image_prompt": """Compelling social media visual: split between futuristic digital identity visualization 
and warm community gathering scene, modern design, vibrant but not garish, 
square format, no text, suitable for Instagram feed."""
    },
    "facebook": {
        "needs_image": False,
        "char_limit": 63206,
        "prompt": """Write a Facebook post for Vessel Protocol — a 365-day manifestation app.
Formula: CT×A=M. App: https://ctxaxm.com — $4.99/month or $39.99/year.
Alternate between:
- Inspirational: 365-day journey, daily check-ins, becoming who you want to be
- Educational: how CT×A=M works in real life with practical examples  
- Community: invite followers to share their manifestation wins
End with soft CTA: "Start your 365 days → https://ctxaxm.com"
Tone: warm, aspirational, community-first. 2-3 paragraphs. Return only the post."""
    },
    "facebook_gafc": {
        "needs_image": False,
        "char_limit": 63206,
        "prompt": (
            "Write a Facebook post for Glocks and Fried Chicken (GAFC) - a minority-owned gun safety social enterprise in Sacramento, CA. "
            "Mascots: Gloxsie 21 and Bobo Licious. "
            "Topics: safe storage, trigger locks, community safety events, "
            "MWBE grants, Church of Legacy partnership. "
            "Tone: community-first, warm, empowering. 2-3 paragraphs. "
            "End with a gun safety tip or CTA @glocksandfriedchicken. Return only the post."
        )
    },
    "linkedin": {
        "needs_image": False,
        "char_limit": 3000,
        "prompt": """Write a LinkedIn post for Guerilla Holdings LLC. 
Topic: AI-native business operations, autonomous revenue systems, or minority entrepreneurship.
3 short paragraphs. Insight-driven. End with a question to drive engagement.
Tone: authoritative, forward-thinking, genuine. Return only the post."""
    }
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def gql(query: str, variables: dict = None) -> dict:
    body = {"query": query}
    if variables:
        body["variables"] = variables
    try:
        r = requests.post(GQL_URL, headers=BUF_HEADERS, json=body, timeout=20)
        if r.status_code == 200:
            _update_rate(dict(r.headers))
            return r.json().get("data", {})
        if r.status_code == 429:
            _update_rate(dict(r.headers))
            log.warning("Buffer 429 — rate limited, skipping cycle")
            return {}
        log.error(f"GQL HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"GQL error: {e}")
    return {}

def get_channels() -> list:
    """Use cached channel IDs — avoids wasting API quota on channel fetch."""
    cache_file = Path("/root/workspace/Penelope/buffer_channels_cache.json")
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
            channels = []
            for svc in ("twitter", "tiktok", "pinterest", "instagram", "facebook", "facebook_gafc"):
                if svc in cache:
                    channels.append({"id": cache[svc], "service": svc, "name": f"@{svc}"})
            channels.append({"id": "69de9902031bfa423c038e5b", "service": "facebook_gafc", "name": "GlocksAndFriedChicken"})
            if channels:
                return channels
        except: pass
    # Fallback: fetch from API (uses quota)
    data = gql("""{ account { organizations { channels { id service name } } } }""")
    try:
        chs = data["account"]["organizations"][0]["channels"]
        # Cache result for future runs
        cache = {ch["service"]: ch["id"] for ch in chs}
        cache["cached_at"] = datetime.now(timezone.utc).isoformat()
        cache_file.write_text(json.dumps(cache, indent=2))
        return chs
    except:
        return []

def generate_text(service: str) -> str | None:
    if not client:
        return None
    cfg = PLATFORMS.get(service, {})
    if not cfg.get("prompt"):
        return None
    try:
        resp = client.models.generate_content(model="gemini-2.5-flash",
                                               contents=cfg["prompt"])
        text = getattr(resp, "text", "").strip()
        limit = cfg.get("char_limit", 280)
        return text[:limit-3] + "..." if len(text) > limit else text
    except Exception as e:
        log.error(f"Gemini text error [{service}]: {e}")
        return None

def generate_image(service: str) -> str | None:
    """Generate a local quote card image using Pillow. No API credits needed."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap, random

    cfg = PLATFORMS.get(service, {})

    # Pull a random product from catalog for the card
    catalog_path = Path("/root/workspace/Penelope/gumroad_catalog.json")
    product = None
    if catalog_path.exists():
        try:
            import json as _j
            catalog = _j.loads(catalog_path.read_text())
            if catalog:
                product = random.choice(catalog)
        except:
            pass

    # Card content
    if product:
        headline = product["name"][:55]
        subline  = f"${product['price']:.2f}  •  guerillaholdings.gumroad.com"
        cta      = "Download instantly ↗"
    else:
        headline = "Vessel Protocol"
        subline  = "365-day manifestation system"
        cta      = "ctxaxm.com"

    try:
        W, H = 1080, 1080
        # Dark background
        img = Image.new("RGB", (W, H), color=(8, 8, 12))
        draw = ImageDraw.Draw(img)

        # Gold accent bar top
        draw.rectangle([(0, 0), (W, 6)], fill=(232, 184, 75))
        # Teal accent bar bottom
        draw.rectangle([(0, H-6), (W, H)], fill=(0, 200, 160))

        # Border
        draw.rectangle([(24, 24), (W-24, H-24)], outline=(42, 42, 58), width=1)

        # Try to load a font, fall back to default
        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
            font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        except:
            font_lg = ImageFont.load_default()
            font_md = font_lg
            font_sm = font_lg

        # Brand tag
        draw.text((60, 60), "GUERILLA HOLDINGS", font=font_sm, fill=(232, 184, 75))

        # Headline — wrapped
        lines = textwrap.wrap(headline, width=22)
        y = 180
        for line in lines[:3]:
            draw.text((60, y), line, font=font_lg, fill=(238, 238, 245))
            y += 72

        # Divider
        draw.line([(60, y + 20), (W - 60, y + 20)], fill=(42, 42, 58), width=1)
        y += 50

        # Subline
        draw.text((60, y), subline, font=font_sm, fill=(136, 136, 168))
        y += 60

        # CTA
        draw.text((60, y), cta, font=font_md, fill=(0, 200, 160))

        # Bottom brand
        draw.text((60, H - 80), "guerillaholdings.gumroad.com", font=font_sm, fill=(68, 68, 90))

        # Save
        fname = f"{service}_{hashlib.md5(headline.encode()).hexdigest()[:8]}.jpg"
        fpath = IMG_DIR / fname
        img.save(str(fpath), "JPEG", quality=92)

        # Sync to Penelope-2 where nginx/trustchainservices.com is hosted
        try:
            import base64 as _b64
            img_bytes = fpath.read_bytes()
            img_b64 = _b64.b64encode(img_bytes).decode()
            sync_cmd = f"echo '{img_b64}' | base64 -d > /var/www/html/generated/{fname} && chmod 644 /var/www/html/generated/{fname}"
            sync_r = requests.post(
                "https://penelope2.trustchainservices.com/exec",
                json={"secret": "sydney123", "cmd": sync_cmd},
                timeout=20
            )
            log.info(f"Image synced to P2: {sync_r.status_code}")
        except Exception as se:
            log.warning(f"Image sync to P2 failed: {se}")

        pub_url = f"{SERVER_URL}/{fname}"
        log.info(f"Image card ready [{service}]: {pub_url}")
        return pub_url

    except Exception as e:
        log.error(f"Pillow image error [{service}]: {e}")
        return None

def create_post(channel_id: str, service: str, text: str,
                image_url: str = None) -> bool:
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
        createPost(input: $input) {
            ... on PostActionSuccess {
                post { id status dueAt }
            }
            ... on InvalidInputError { message }
            ... on LimitReachedError  { message }
            ... on UnauthorizedError  { message }
            ... on UnexpectedError    { message }
        }
    }"""
    inp = {
        "channelId":     channel_id,
        "text":          text,
        "schedulingType": "automatic",
        "mode":          "addToQueue"
    }
    if image_url:
        inp["assets"] = {"images": [{"url": image_url}]}

    data = gql(mutation, {"input": inp})
    result = data.get("createPost", {})
    post   = result.get("post")
    if post and post.get("id"):
        log.info(f"✅ Queued [{service}]: {text[:55]}... → {post['id']}")
        return True
    msg = result.get("message", "")
    if msg:
        log.error(f"❌ Buffer rejected [{service}]: {msg}")
    else:
        log.warning(f"❌ No ID [{service}]: {result}")
    return False

def load_posted() -> dict:
    if POSTED_FILE.exists():
        try: return json.loads(POSTED_FILE.read_text())
        except: pass
    return {}

def save_posted(posted: dict):
    tmp = POSTED_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(posted, indent=2))
    tmp.rename(POSTED_FILE)

# ── Main ──────────────────────────────────────────────────────────────────────
def get_gumroad_product_post(service: str) -> str | None:
    """Return a Gumroad product post every other cycle."""
    import json as _json, random as _random
    catalog_path = Path("/root/workspace/Penelope/gumroad_catalog.json")
    if not catalog_path.exists():
        return None
    try:
        catalog = _json.loads(catalog_path.read_text())
        if not catalog:
            return None
        p     = _random.choice(catalog)
        n     = p["name"]
        price = p["price"]
        url   = p["url"]
        pt    = p["type"]
        if service == "twitter":
            if pt == "book":
                return f"📖 {n[:50]}\n\nSci-fi epic — only ${price:.0f}\nInstant download → {url}\n\n#SciFi #BookTok #IndieAuthor"
            elif "Prompt" in n:
                return f"🚀 25 AI Business Strategy Prompts\nBuilt for leaders. ${price:.0f} → {url}\n\n#AI #BusinessStrategy #ChatGPT"
            elif "Safety" in n or "Check" in n:
                return f"⚠️ Client data checklist — know your exposure before a breach.\n${price:.0f} → {url}\n\n#DataPrivacy #SmallBusiness"
            elif "Guide" in n:
                return f"📘 Quantum Future Business Guide — AI × strategy × leadership\n${price:.0f} → {url}\n\n#BusinessLeadership #AI"
            else:
                return f"🚀 {n[:45]} — ${price:.0f}\n{url}\n\n#DigitalProducts #Gumroad"
        else:
            return f"{n[:55]} — ${price:.0f}\nInstant digital download → {url}\n\n#DigitalProducts #GumroadFinds"
    except Exception as e:
        log.error(f"Gumroad rotation: {e}")
    return None


_RATE_STATE = Path("/root/workspace/Penelope/buffer_rate_limit_state.json")

def _is_rate_limited() -> bool:
    import time as _t
    if not _RATE_STATE.exists(): return False
    try:
        s = json.loads(_RATE_STATE.read_text())
        if not s.get("rate_limited"): return False
        if _t.time() > s.get("reset_ts", 0) + 60:
            _RATE_STATE.write_text(json.dumps({"rate_limited": False}))
            log.info("Buffer rate limit cleared")
            return False
        log.info(f"Buffer rate limited until {s.get('reset_human','?')}")
        return True
    except: return False

def _update_rate(headers: dict):
    import time as _t
    rem = int(headers.get("x-ratelimit-remaining", 100))
    rst = int(headers.get("x-ratelimit-reset", 0))
    if rem == 0 and rst:
        from datetime import datetime, timezone as tz
        _RATE_STATE.write_text(json.dumps({
            "rate_limited": True, "reset_ts": rst, "remaining": 0,
            "reset_human": datetime.fromtimestamp(rst, tz=tz.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }, indent=2))
        log.warning(f"Buffer rate limited until {datetime.fromtimestamp(rst, tz=tz.utc)}")


def run():
    if _is_rate_limited(): return
    log.info(f"Buffer agent v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    channels = get_channels()
    if not channels:
        log.error("No channels found")
        return

    log.info(f"Live channels: {[(c['service'], c['name']) for c in channels]}")

    posted  = load_posted()
    today   = datetime.now().strftime("%Y-%m-%d")
    cycle   = datetime.now().hour // 4
    results = []

    for ch in channels:
        cid     = ch["id"]
        service = ch["service"].lower()
        name    = ch["name"]
        cfg     = PLATFORMS.get(service, {})

        key = f"{cid}_{today}_{cycle}"
        if key in posted:
            log.info(f"Already posted [{service}] this cycle")
            continue

        # Generate text
        # Alternate: even 4h windows = Vessel, odd = Gumroad product
        import time as _t
        _cycle = int(_t.time() // (4 * 3600))
        if _cycle % 2 == 1:
            _gtext = get_gumroad_product_post(service)
            text   = _gtext if _gtext else generate_text(service)
            if _gtext:
                log.info(f"[{service}] Gumroad rotation active")
        else:
            text = generate_text(service)
        if not text:
            log.warning(f"No text for [{service}]")
            results.append(f"⚠️ {service}: no text")
            continue

        # Generate image if needed
        image_url = None
        if cfg.get("needs_image"):
            image_url = generate_image(service)
            if not image_url:
                log.warning(f"[{service}] image generation failed — skipping (needs media)")
                results.append(f"⚠️ {service}: image failed")
                continue

        if create_post(cid, service, text, image_url):
            posted[key] = {
                "service":   service,
                "name":      name,
                "text":      text[:80],
                "image":     image_url,
                "ts":        datetime.now().isoformat()
            }
            results.append(f"✅ {service}/{name}")
        else:
            results.append(f"❌ {service}/{name}")

        time.sleep(3)

    save_posted(posted)
    log.info(f"Cycle done: {results}")

if __name__ == "__main__":
    run()
