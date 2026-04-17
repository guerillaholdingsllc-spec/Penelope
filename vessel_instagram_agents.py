"""
vessel_instagram_agents.py
5 Instagram agents for Vessel — visual, stories, reels, carousels, community
"""
import os, json, requests, time, random
from datetime import datetime
from google import genai


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


VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except: pass

GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY","")
TELEGRAM_TOKEN = VAULT.get("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT  = "6183015901"

client = genai.Client(api_key=GOOGLE_API_KEY)

BRAND_RULES = """VESSEL BRAND VOICE: Mysterious, empowering, science-adjacent, dark cosmic language, subtly cultic.
Never exclamation marks in body copy. End posts with ✦. CT×A=M formula. 365-day journey."""

def gm(prompt, temp=0.75):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r,"text","") or ""
    except Exception as e:
        print(f"Gemini: {e}"); return ""

def tg(msg):
    if not TELEGRAM_TOKEN: return
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def log_post(agent, content, pillar="general"):
    log_path = "/root/workspace/Penelope/social_log.json"
    try:
        with open(log_path) as f: log = json.load(f)
    except: log = {}
    log[f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"] = {
        "agent":agent,"platform":"instagram","content":content[:500],"pillar":pillar,
        "timestamp":datetime.now().isoformat()}
    with open(log_path,"w") as f: json.dump(log,f,indent=2)

# ──────────────────────────────────────────────────────────────
# AGENT 6: vessel_ig_visual_agent
# High-quality dark cosmic grid posts, aesthetic brand identity
# ──────────────────────────────────────────────────────────────
def vessel_ig_visual_agent():
    print("[vessel_ig_visual_agent] Running...")
    themes = [
        "sacred geometry + CT×A=M formula", "dark nebula + Day counter",
        "breathing circle animation still", "cosmic blueprint + manifestation",
        "gold on black + affirmation", "USS score visualization"
    ]
    theme = random.choice(themes)

    prompt = f"""{BRAND_RULES}

vessel_ig_visual_agent: Create 2 Instagram grid post concepts.

Theme: {theme}

For each post:
- IMAGE DESCRIPTION: detailed visual description (dark cosmic, gold accents, sacred geometry)
- CAPTION: 3-4 sentences, mysterious, ends with ✦ and 5 relevant hashtags
- ALT TEXT: descriptive for accessibility
- OPTIMAL POST TIME: when to schedule

Format as JSON array of 2 objects."""

    raw = gm(prompt)
    posts = []
    try:
        s = raw.find("["); e = raw.rfind("]")+1
        posts = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: posts = [{"raw":raw}]

    for p in posts:
        log_post("vessel_ig_visual_agent", json.dumps(p), "cosmic_philosophy")
    tg(f"🖼 <b>IG Visual Agent</b>\n{len(posts)} grid posts | Theme: {theme[:40]}")
    return posts

# ──────────────────────────────────────────────────────────────
# AGENT 7: vessel_ig_story_agent
# Interactive stories, polls, Q&A, daily affirmations, CTAs
# ──────────────────────────────────────────────────────────────
def vessel_ig_story_agent():
    print("[vessel_ig_story_agent] Running...")
    story_types = ["poll","question","affirmation","countdown","quiz","cta"]
    selected = random.sample(story_types, 3)

    prompt = f"""{BRAND_RULES}

vessel_ig_story_agent: Create 5 Instagram Stories for today.

Story types to include: {', '.join(selected)} + 2 more of your choice

For each story:
- STORY TYPE: (poll/question/affirmation/countdown/quiz/link/cta)
- BACKGROUND: dark cosmic visual description
- TEXT: main copy (short, powerful)
- INTERACTIVE ELEMENT: poll options / question prompt / quiz answer
- STICKER/CTA: swipe up, link, etc.

Story sequence should flow: awareness → curiosity → engagement → action

Format as JSON array of 5 story objects."""

    raw = gm(prompt)
    stories = []
    try:
        s = raw.find("["); e = raw.rfind("]")+1
        stories = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: stories = [{"raw":raw}]

    log_post("vessel_ig_story_agent", json.dumps(stories), "engagement")
    tg(f"📱 <b>IG Story Agent</b>\n{len(stories)} stories | Types: {', '.join(selected)}")
    return stories

# ──────────────────────────────────────────────────────────────
# AGENT 8: vessel_ig_reel_agent
# Instagram Reels — trending audio, educational, brand awareness
# ──────────────────────────────────────────────────────────────
def vessel_ig_reel_agent():
    print("[vessel_ig_reel_agent] Running...")
    day = random.choice([7,30,66,100,180,365])
    goal = random.choice(["wealth","health","body","love","purpose","peace"])

    prompt = f"""{BRAND_RULES}

vessel_ig_reel_agent: Create 2 Instagram Reel scripts.

Context: Vessel Day {day} protocol moment, goal type: {goal}

Reel 1: Educational (30-45 seconds) — explain one CT×A=M concept cinematically
Reel 2: Atmospheric (15-20 seconds) — pure aesthetic protocol moment, minimal words

For each:
- HOOK: first frame / first word
- VISUAL SEQUENCE: shot-by-shot description (dark, cinematic)
- AUDIO: trending audio description or original voiceover
- TEXT OVERLAYS: key words that appear on screen
- CAPTION: full Instagram caption with hashtags
- COVER IMAGE: description of thumbnail

Format as JSON array of 2 objects."""

    raw = gm(prompt)
    reels = []
    try:
        s = raw.find("["); e = raw.rfind("]")+1
        reels = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: reels = [{"raw":raw}]

    for r in reels:
        log_post("vessel_ig_reel_agent", json.dumps(r), "protocol_preview")
    tg(f"🎬 <b>IG Reel Agent</b>\n{len(reels)} reels | Day {day} | {goal}")
    return reels

# ──────────────────────────────────────────────────────────────
# AGENT 9: vessel_ig_carousel_agent
# Deep-dive carousels — educational, step-by-step, value-driven
# ──────────────────────────────────────────────────────────────
def vessel_ig_carousel_agent():
    print("[vessel_ig_carousel_agent] Running...")
    topics = [
        "CT×A=M: The Complete Breakdown (5 slides)",
        "What happens to your brain after 66 days of Vessel (6 slides)",
        "The 3 Phases of Your 365-Day Journey (4 slides)",
        "Why Most Manifestation Fails (And What Vessel Does Differently) (5 slides)",
        "Your Morning Alignment Protocol: A Step-by-Step Guide (6 slides)",
        "The USS Score Explained: How Vessel Reads Your Energy (5 slides)",
        "From Baseline to Manifested: The Vessel Transformation Arc (6 slides)",
    ]
    topic = random.choice(topics)

    prompt = f"""{BRAND_RULES}

vessel_ig_carousel_agent: Create a full Instagram Carousel post.

Topic: {topic}

For each slide provide:
- SLIDE NUMBER & TITLE
- VISUAL: dark cosmic imagery description + layout
- HEADLINE: large bold text on slide (short)
- BODY: 1-2 sentences of supporting copy
- DESIGN NOTE: specific visual element (chart, icon, sacred geometry)

Also provide:
- COVER SLIDE (slide 1): the hook that makes people swipe
- FINAL SLIDE: CTA slide with "Begin Your Vessel Journey" or similar
- FULL CAPTION: for the post (includes "swipe to unlock →")
- HASHTAGS: 10-15 relevant tags

Format as JSON object with slides array and post_details object."""

    raw = gm(prompt)
    carousel = {}
    try:
        s = raw.find("{"); e = raw.rfind("}")+1
        carousel = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: carousel = {"raw":raw}

    log_post("vessel_ig_carousel_agent", json.dumps(carousel)[:500], "education")
    print(f"  Carousel: {topic[:60]}...")
    tg(f"📊 <b>IG Carousel Agent</b>\n{topic[:60]}")
    return carousel

# ──────────────────────────────────────────────────────────────
# AGENT 10: vessel_ig_community_agent
# Engagement, comment replies, DMs, UGC re-shares
# ──────────────────────────────────────────────────────────────
def vessel_ig_community_agent(recent_comments=None):
    print("[vessel_ig_community_agent] Running...")
    sample_comments = recent_comments or [
        "What is Day 66?",
        "How does the breathing protocol work?",
        "Is this app available on iPhone?",
        "I'm on Day 23 and already feeling different",
        "What's CT×A=M?",
        "How do I get started?",
    ]

    prompt = f"""{BRAND_RULES}

vessel_ig_community_agent: Generate reply templates for Instagram comments.

Recent comments to reply to:
{json.dumps(sample_comments, indent=2)}

For each comment provide:
- ORIGINAL COMMENT: (the comment)
- REPLY: warm, mysterious, brand-aligned response (2-3 sentences max)
- TONE: matches USS-style (warm but not over-eager, cosmic but not alienating)

Also generate:
- 3 PROACTIVE ENGAGEMENT COMMENTS: things Vessel posts on related accounts' content
- 1 UGC RE-SHARE CAPTION TEMPLATE: for when a user shares their Vessel journey

Format as JSON object with replies array, proactive array, and ugc_template."""

    raw = gm(prompt)
    engagement = {}
    try:
        s = raw.find("{"); e = raw.rfind("}")+1
        engagement = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: engagement = {"raw":raw}

    log_post("vessel_ig_community_agent", json.dumps(engagement)[:500], "community")
    print(f"  Community: {len(sample_comments)} comment replies generated")
    tg(f"💬 <b>IG Community Agent</b>\n{len(sample_comments)} replies + proactive engagement")
    return engagement

# ──────────────────────────────────────────────────────────────
# MASTER RUNNER
# ──────────────────────────────────────────────────────────────
def run_all_instagram_agents():
    print(f"[{datetime.now().isoformat()}] Running all 5 Instagram agents...")
    results = {}
    results["visual"]    = vessel_ig_visual_agent(); time.sleep(2)
    results["stories"]   = vessel_ig_story_agent(); time.sleep(2)
    results["reels"]     = vessel_ig_reel_agent(); time.sleep(2)
    results["carousel"]  = vessel_ig_carousel_agent(); time.sleep(2)
    results["community"] = vessel_ig_community_agent()

    output_path = f"/root/workspace/Penelope/shipped/vessel_instagram_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path,"w") as f: json.dump(results,f,indent=2)
    print(f"All Instagram agents complete. Saved: {output_path}")
    tg(f"✅ <b>All 5 Instagram Agents Complete</b>\n{output_path}")
    return results

if __name__ == "__main__":
    import sys
    agent = sys.argv[1] if len(sys.argv)>1 else "all"
    if agent == "visual":     vessel_ig_visual_agent()
    elif agent == "story":    vessel_ig_story_agent()
    elif agent == "reel":     vessel_ig_reel_agent()
    elif agent == "carousel": vessel_ig_carousel_agent()
    elif agent == "community":vessel_ig_community_agent()
    else: run_all_instagram_agents()