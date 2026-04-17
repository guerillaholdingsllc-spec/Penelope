"""
vessel_tiktok_agents.py
5 TikTok social agents for Vessel — all Penelope-controlled
Uses google.genai SDK (gemini-2.5-flash), WaveSpeed for visuals
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

GOOGLE_API_KEY  = VAULT.get("GOOGLE_API_KEY","")
WAVESPEED_KEY   = VAULT.get("WAVESPEED_API_KEY","91a8b92b3e6661054bc7a4f84ce02f117ee5cf329a1f7c204982d40b702db11a")
TELEGRAM_TOKEN  = VAULT.get("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT   = "6183015901"

client = genai.Client(api_key=GOOGLE_API_KEY)

BRAND_RULES = """
VESSEL BRAND VOICE RULES (follow strictly):
1. Mysterious & enigmatic — cosmic wonder, never explains everything
2. Empowering — agency, CT×A=M, personal power
3. Science-adjacent — neuroscience + spirituality bridge
4. Dark cosmic language — "energetic constellations", "cosmic alignment"
5. Subtly cultic — "Vessels", "Voyagers", "The Aligned"
Never use exclamation marks in body copy. End posts with ✦
"""

CONTENT_PILLARS = [
    "day_counter",        # "Day 66 ✦ The automaticity threshold is real."
    "protocol_preview",   # show breathing circle, journal, check-in
    "transformation_data",# "47 Vessels crossed Day 66 this week."
    "science_bridge",     # "66 days isn't mysticism. It's neuroscience."
    "cosmic_philosophy",  # deep-space metaphors + CT×A=M
]

def gm(prompt, temp=0.8):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r, "text", "") or ""
    except Exception as e:
        print(f"Gemini: {e}"); return ""

def tg(msg):
    if not TELEGRAM_TOKEN: return
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def log_post(agent_name, platform, content, pillar):
    entry = {"agent":agent_name,"platform":platform,"content":content,
             "pillar":pillar,"timestamp":datetime.now().isoformat()}
    log_path = "/root/workspace/Penelope/social_log.json"
    try:
        with open(log_path) as f: log = json.load(f)
    except: log = {}
    log[f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"] = entry
    with open(log_path,"w") as f: json.dump(log,f,indent=2)

# ──────────────────────────────────────────────────────────────
# AGENT 1: vessel_tiktok_hook_agent
# Viral 3-second hooks, trending audio descriptions, attention openers
# ──────────────────────────────────────────────────────────────
def vessel_tiktok_hook_agent(stats=None):
    """Generate 3 viral TikTok hook scripts per run"""
    print(f"[vessel_tiktok_hook_agent] Running...")
    day_count = (stats or {}).get("avg_day", random.randint(40,180))

    prompt = f"""{BRAND_RULES}

You are vessel_tiktok_hook_agent. Generate 3 TikTok video hook scripts for the VESSEL manifestation app.
Each hook is the first 3 seconds of a video — must stop the scroll immediately.

Context: VESSEL is a 365-day AI manifestation protocol. CT×A=M formula. Dark cosmic aesthetic.
Current community average: Day {day_count} of 365.

For each hook provide:
- VISUAL: what's on screen (dark cosmic imagery, app UI flash, etc.)
- AUDIO: trending audio description or voiceover words
- TEXT OVERLAY: exact words on screen
- CAPTION: full TikTok caption with hashtags

Pillars to use (pick varied): {', '.join(CONTENT_PILLARS)}

Make each distinctly different. Mysterious. Makes viewer ask "what is this?"
Format as JSON array of 3 objects."""

    raw = gm(prompt)
    hooks = []
    try:
        start = raw.find("["); end = raw.rfind("]")+1
        hooks = json.loads(raw[start:end]) if start>=0 else [{"raw":raw}]
    except: hooks = [{"raw":raw}]

    for i, hook in enumerate(hooks):
        content = json.dumps(hook)
        log_post("vessel_tiktok_hook_agent","tiktok",content,"hook")
        print(f"  Hook {i+1}: {str(hook)[:80]}...")

    tg(f"🎵 <b>TikTok Hook Agent</b>\n{len(hooks)} hooks generated\nDay avg: {day_count}")
    return hooks

# ──────────────────────────────────────────────────────────────
# AGENT 2: vessel_tiktok_story_agent
# Day-in-the-life protocol content, simulated user journeys
# ──────────────────────────────────────────────────────────────
def vessel_tiktok_story_agent(stats=None):
    """Generate day-in-the-life protocol story scripts"""
    print(f"[vessel_tiktok_story_agent] Running...")
    day = random.choice([7,30,66,100,180])
    goal = random.choice(["wealth","health","body","love","purpose","peace"])

    prompt = f"""{BRAND_RULES}

You are vessel_tiktok_story_agent. Create 2 TikTok "day-in-the-life protocol" video scripts.
These show a Vessel user's experience — anonymous, atmospheric, NOT testimonial-style.

Video style: slow-motion, dark aesthetic, hands interacting with app, morning ritual feel.
Duration: 15-30 seconds each.

Scenario: A Vessel user on Day {day}, goal: {goal}.

For each video provide:
- SCENE DESCRIPTION: what's visually happening (cinematic, dark)
- VOICEOVER: atmospheric narration (short, cryptic, powerful)
- TEXT OVERLAYS: 2-3 text moments
- CAPTION: TikTok caption + hashtags (include #VesselApp #Day{day})

Make it feel like a glimpse into a sacred private ritual. Outsiders should feel FOMO.
Format as JSON array of 2 objects."""

    raw = gm(prompt)
    scripts = []
    try:
        start = raw.find("["); end = raw.rfind("]")+1
        scripts = json.loads(raw[start:end]) if start>=0 else [{"raw":raw}]
    except: scripts = [{"raw":raw}]

    for s in scripts:
        log_post("vessel_tiktok_story_agent","tiktok",json.dumps(s),"protocol_preview")
        print(f"  Story: {str(s)[:80]}...")

    tg(f"📖 <b>TikTok Story Agent</b>\n{len(scripts)} protocol stories\nDay {day} | Goal: {goal}")
    return scripts

# ──────────────────────────────────────────────────────────────
# AGENT 3: vessel_tiktok_science_agent
# Habit science + manifestation bridges, neuroscience content
# ──────────────────────────────────────────────────────────────
def vessel_tiktok_science_agent():
    """Generate science-bridge TikTok content"""
    print(f"[vessel_tiktok_science_agent] Running...")

    topics = [
        "The 66-day automaticity threshold — why Vessel's protocol is scientifically calibrated",
        "Psychic driving: why daily affirmations actually rewire neural pathways",
        "The USS score: how mood data predicts and prevents manifestation drift",
        "Why CT×A=M is not mysticism — it's behavioral science",
        "Brain-heart coherence: the physiological basis of the Vessel breathing protocol",
        "Sunk cost psychology: why the deeper you go in the protocol the more powerful it becomes",
        "Identity-based habit formation: why Vessel calls you a Vessel not a user",
    ]
    topic = random.choice(topics)

    prompt = f"""{BRAND_RULES}

You are vessel_tiktok_science_agent. Create 1 TikTok educational video script.

Topic: {topic}

Format: Fast-paced, text-on-screen education with dark cosmic visuals.
Duration: 45-60 seconds.

Provide:
- HOOK (first 3 seconds): text or voiceover that stops the scroll
- CONTENT BREAKDOWN: 4-6 key points as text-on-screen moments
- VISUAL DIRECTION: what cosmic/tech imagery to show
- VOICEOVER: full narration script
- CAPTION: with hashtags (#neuroscience #manifestation #habitscience #VesselApp)

Make it feel like insider knowledge. The science validates the spirituality.
Format as JSON object."""

    raw = gm(prompt)
    script = {}
    try:
        start = raw.find("{"); end = raw.rfind("}")+1
        script = json.loads(raw[start:end]) if start>=0 else {"raw":raw}
    except: script = {"raw":raw}

    log_post("vessel_tiktok_science_agent","tiktok",json.dumps(script),"science_bridge")
    print(f"  Science: {topic[:60]}...")
    tg(f"🧬 <b>TikTok Science Agent</b>\nTopic: {topic[:60]}")
    return script

# ──────────────────────────────────────────────────────────────
# AGENT 4: vessel_tiktok_community_agent
# Amplifies anonymous milestones, community transmission posts
# ──────────────────────────────────────────────────────────────
def vessel_tiktok_community_agent(community_stats=None):
    """Generate community milestone amplification posts"""
    print(f"[vessel_tiktok_community_agent] Running...")
    stats = community_stats or {
        "active_vessels": random.randint(50,500),
        "day66_crossings": random.randint(5,47),
        "avg_uss": random.randint(58,82),
        "top_goal": random.choice(["wealth","purpose","health"]),
    }

    prompt = f"""{BRAND_RULES}

You are vessel_tiktok_community_agent. Generate 2 anonymous community milestone posts.
These celebrate the collective Vessel journey without identifying anyone.

Community data:
- Active Vessels: {stats['active_vessels']}
- Crossed Day 66 this week: {stats['day66_crossings']}
- Community average USS score: {stats['avg_uss']}/100
- Most common goal: {stats['top_goal']}

Create 2 posts:
Post 1: A "transmission" post sharing community stats in a mysterious, inspiring way
Post 2: An invitation for community to share their Day milestone in comments

Each post:
- TEXT OVERLAY content (what appears on screen)
- CAPTION with hashtags
- VISUAL: dark cosmic imagery description

Format as JSON array of 2 objects."""

    raw = gm(prompt)
    posts = []
    try:
        start = raw.find("["); end = raw.rfind("]")+1
        posts = json.loads(raw[start:end]) if start>=0 else [{"raw":raw}]
    except: posts = [{"raw":raw}]

    for p in posts:
        log_post("vessel_tiktok_community_agent","tiktok",json.dumps(p),"transformation_data")
        print(f"  Community: {str(p)[:80]}...")

    tg(f"👥 <b>TikTok Community Agent</b>\n{len(posts)} community posts\nActive: {stats['active_vessels']} Vessels")
    return posts

# ──────────────────────────────────────────────────────────────
# AGENT 5: vessel_tiktok_challenge_agent
# Weekly challenges, trend initiation, interactive content
# ──────────────────────────────────────────────────────────────
def vessel_tiktok_challenge_agent(week_number=None):
    """Generate weekly TikTok challenge content"""
    print(f"[vessel_tiktok_challenge_agent] Running...")
    week = week_number or datetime.now().isocalendar()[1]

    challenges_pool = [
        "The 60-Second Wealth Inventory — list 3 things you already have that align with abundance",
        "The CT×A=M Action Challenge — one aligned action before 9AM",
        "The Baseline Shift Challenge — share what's changed in 30 days",
        "The Day 66 Path Challenge — what does your protocol look like?",
        "The One Word Challenge — describe your manifestation journey in one word",
        "The Morning Alignment Challenge — 3 breaths, 1 intention, filmed at sunrise",
        "The Vision Gap Challenge — show NOW vs where you're going",
    ]
    challenge = challenges_pool[week % len(challenges_pool)]

    prompt = f"""{BRAND_RULES}

You are vessel_tiktok_challenge_agent. Create a weekly TikTok challenge launch package for VESSEL.

Week {week} Challenge: {challenge}

Provide:
1. LAUNCH VIDEO (60-90 seconds): full script with visuals, voiceover, text overlays
2. CHALLENGE NAME: catchy, hashtag-friendly (e.g. #VesselDay66Challenge)
3. PARTICIPATION INSTRUCTIONS: simple 3-step guide shown in video
4. LAUNCH CAPTION: full caption with challenge hashtag + community hashtags
5. FOLLOW-UP POST (15-30 sec): reminder/example post for mid-week
6. ENGAGEMENT HOOK: what to say to get comments (e.g. "Drop your Day number below ✦")

Format as JSON object with keys: launch_video, challenge_name, instructions, caption, followup, engagement_hook"""

    raw = gm(prompt)
    package = {}
    try:
        start = raw.find("{"); end = raw.rfind("}")+1
        package = json.loads(raw[start:end]) if start>=0 else {"raw":raw}
    except: package = {"raw":raw}

    log_post("vessel_tiktok_challenge_agent","tiktok",json.dumps(package),"challenge")
    print(f"  Challenge: {challenge[:60]}...")
    tg(f"🎯 <b>TikTok Challenge Agent</b>\nWeek {week}: {challenge[:60]}")
    return package

# ──────────────────────────────────────────────────────────────
# MASTER RUNNER
# ──────────────────────────────────────────────────────────────
def run_all_tiktok_agents(stats=None):
    """Run all 5 TikTok agents and return combined output"""
    print(f"[{datetime.now().isoformat()}] Running all 5 TikTok agents...")
    results = {}

    results["hooks"]     = vessel_tiktok_hook_agent(stats); time.sleep(2)
    results["stories"]   = vessel_tiktok_story_agent(stats); time.sleep(2)
    results["science"]   = vessel_tiktok_science_agent(); time.sleep(2)
    results["community"] = vessel_tiktok_community_agent(); time.sleep(2)
    results["challenge"] = vessel_tiktok_challenge_agent()

    # Save combined output
    output_path = f"/root/workspace/Penelope/shipped/vessel_tiktok_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path,"w") as f:
        json.dump(results,f,indent=2)

    print(f"\nAll TikTok agents complete. Saved: {output_path}")
    tg(f"✅ <b>All 5 TikTok Agents Complete</b>\nSaved: {output_path}")
    return results

if __name__ == "__main__":
    import sys
    agent = sys.argv[1] if len(sys.argv)>1 else "all"
    if agent == "hook":      vessel_tiktok_hook_agent()
    elif agent == "story":   vessel_tiktok_story_agent()
    elif agent == "science": vessel_tiktok_science_agent()
    elif agent == "community": vessel_tiktok_community_agent()
    elif agent == "challenge": vessel_tiktok_challenge_agent()
    else: run_all_tiktok_agents()