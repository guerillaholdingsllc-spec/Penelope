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
        "prompt": """Write a punchy Twitter/X post for Vessel Protocol — a tool that turns your digital 
data trail into personal narrative and self-knowledge. Max 260 chars. Max 2 hashtags.
Themes: digital identity, data ownership, personal analytics, self-awareness.
Tone: thought-provoking, slightly philosophical, not corporate. Return only the tweet."""
    },
    "tiktok": {
        "needs_image": True,
        "char_limit": 2200,
        "prompt": """Write a TikTok caption for Vessel Protocol. Short hook line + 2 sentences + 3 hashtags.
Vessel turns your digital footprint into meaningful personal insight.
Tone: curious, authentic, gen-z adjacent. Return only the caption.""",
        "image_prompt": """Minimal aesthetic digital art: glowing vessel/jar containing swirling data streams 
and light particles, dark background, purple and cyan palette, clean modern style, 
no text, square format, suitable for TikTok."""
    },
    "pinterest": {
        "needs_image": True,
        "char_limit": 500,
        "prompt": """Write a Pinterest pin description for Vessel Protocol.
2 sentences of value + 5 keyword-rich hashtags.
Focus: personal growth, self-tracking, data visualization, digital wellness.
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
        "prompt": """Write a Facebook post for Guerilla Holdings LLC — AI-native holding company in Sacramento.
Ventures: CadaverCo (specialty transport), CALLUX (gig transport marketplace), 
GAFC (gun safety education in marginalized communities).
2-3 short paragraphs. Community-focused or educational angle. No hard sell.
Tone: professional but human, Sacramento-based. Return only the post text."""
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
            return r.json().get("data", {})
        log.error(f"GQL HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.error(f"GQL error: {e}")
    return {}

def get_channels() -> list:
    data = gql("""{ account { organizations { channels { id service name } } } }""")
    try:
        return data["account"]["organizations"][0]["channels"]
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
    """Generate image via WaveSpeed, save to nginx, return public URL."""
    if not WAVESPEED_KEY:
        log.warning("No WaveSpeed key")
        return None
    cfg = PLATFORMS.get(service, {})
    img_prompt = cfg.get("image_prompt")
    if not img_prompt:
        return None
    try:
        # Submit job
        r = requests.post(
            "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-dev",
            headers={"Authorization": f"Bearer {WAVESPEED_KEY}",
                     "Content-Type": "application/json"},
            json={"prompt": img_prompt, "size": "1024x1024", "num_inference_steps": 25},
            timeout=30
        )
        if r.status_code != 200:
            log.error(f"WaveSpeed submit error: {r.status_code} {r.text[:200]}")
            return None
        job_id = r.json().get("data", {}).get("id")
        if not job_id:
            log.error(f"No job ID from WaveSpeed: {r.text[:200]}")
            return None
        log.info(f"WaveSpeed job {job_id} submitted for [{service}]")

        # Poll for result
        for attempt in range(24):  # 2 min max
            time.sleep(5)
            pr = requests.get(
                f"https://api.wavespeed.ai/api/v3/predictions/{job_id}/result",
                headers={"Authorization": f"Bearer {WAVESPEED_KEY}"},
                timeout=15
            )
            if pr.status_code == 200:
                pdata = pr.json().get("data", {})
                status = pdata.get("status")
                if status == "completed":
                    outputs = pdata.get("outputs", [])
                    if outputs:
                        img_url = outputs[0]
                        # Download and host locally
                        img_r = requests.get(img_url, timeout=30)
                        if img_r.status_code == 200:
                            fname = f"{service}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.jpg"
                            fpath = IMG_DIR / fname
                            fpath.write_bytes(img_r.content)
                            pub_url = f"{SERVER_URL}/{fname}"
                            log.info(f"Image ready [{service}]: {pub_url}")
                            return pub_url
                elif status == "failed":
                    log.error(f"WaveSpeed job failed: {pdata.get('error')}")
                    return None
            time.sleep(0)  # already slept above
        log.error(f"WaveSpeed timeout for [{service}]")
        return None
    except Exception as e:
        log.error(f"WaveSpeed error [{service}]: {e}")
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
def run():
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
