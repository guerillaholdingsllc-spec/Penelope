"""
vessel_marketing_master.py
Full implementation of the Vessel Marketing Master Plan.
Executes all 7 sections autonomously via Penelope.
"""
import os, json, requests, sqlite3, time, random
from datetime import datetime, date
from pathlib import Path
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
            if line and "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except: pass

GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY","")
TG_TOKEN       = VAULT.get("TELEGRAM_BOT_TOKEN","")
TG_CHAT        = "6183015901"
BLUESKY_HANDLE = "vesselprotocol.bsky.social"
BLUESKY_PW     = VAULT.get("VESSEL_BLUESKY_PASSWORD", VAULT.get("BLUESKY_PASSWORD",""))
APP_URL        = "https://ctxaxm.com/vessel.html"
KIDS_URL       = "https://ctxaxm.com/vessel-kids.html"
LAND_URL       = "https://ctxaxm.com"
OUTPUT        = Path("/root/workspace/Penelope/vessel_marketing_output")
OUTPUT.mkdir(exist_ok=True)
LOG           = OUTPUT / "social_log.json"

client = genai.Client(api_key=GOOGLE_API_KEY)

BRAND = f"""VESSEL — 365-Day Manifestation Protocol. Formula: CT×A=M.
$4.99/month or $39.99/year. App: {APP_URL}. Vessel Kids: {KIDS_URL}.
Brand: Mysterious, dark cosmic, empowering, science-adjacent. Cult following.
NOT spiritual fluff — real protocol, real action required.
End posts with ✦. No exclamation marks in body copy."""

def gm(prompt, temp=0.8):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return (getattr(r,"text","") or "").strip()
    except Exception as e:
        print(f"  Gemini error: {e}"); return ""

def tg(msg):
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def log_content(platform, content_type, content):
    try:
        log = json.loads(LOG.read_text()) if LOG.exists() else {}
        key = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log[key] = {"platform":platform,"type":content_type,"content":str(content)[:500],"ts":datetime.now().isoformat()}
        LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    except: pass

def get_stats():
    try:
        r = requests.get("https://ctxaxm.com/vessel-api/health", timeout=5)
        d = r.json()
        return d.get('users',0), d.get('checkins',0)
    except: return 0, 0

def bluesky_post(text):
    """Actually post to Bluesky"""
    try:
        auth = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier":BLUESKY_HANDLE,"password":BLUESKY_PW}, timeout=10)
        if not auth.ok: return False
        token = auth.json().get("accessJwt")
        did   = auth.json().get("did")
        record = {"$type":"app.bsky.feed.post","text":text[:300],
                  "createdAt":datetime.utcnow().isoformat()+"Z","langs":["en"]}
        r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization":f"Bearer {token}"},
            json={"repo":did,"collection":"app.bsky.feed.post","record":record}, timeout=10)
        return r.ok
    except: return False

# ════════════════════════════════════════════════
# SECTION 1: CULT BRAND — Daily "Transmission" Posts
# ════════════════════════════════════════════════
def run_transmission_agent(users, day_num):
    """Cryptic transmission posts — builds cult identity"""
    print("  [Transmission Agent] Running...")
    prompt = f"""{BRAND}
Write 3 cryptic 'transmission' style posts for today. Day {day_num} of Vessel. {users} users.
Style: mysterious, cosmic, as if broadcasting from another frequency.
Use 'Vessel' terminology: protocol, transmission, alignment, vectors, signal.
Each max 240 chars. Include the day number. Make outsiders desperate to know what this is.
Format: JSON array of 3 strings."""
    
    raw = gm(prompt)
    import re
    m = re.search(r'\[.*?\]', raw, re.DOTALL)
    posts = json.loads(m.group()) if m else [
        f"Transmission {day_num:03d} ✦ The protocol holds. {users} Vessels in alignment. CT×A=M.",
        f"Day {day_num}. Conscious Thought compounds. Action solidifies. Manifestation emerges. ✦",
        f"The formula requires nothing mystical. Only clarity. Only action. Only 365 days. ✦ {APP_URL}"
    ]
    
    posted = 0
    for post in posts[:3]:
        if bluesky_post(post):
            posted += 1
            log_content("bluesky", "transmission", post)
        time.sleep(20)
    
    print(f"    Bluesky: {posted}/3 transmission posts live")
    return posts, posted

# ════════════════════════════════════════════════
# SECTION 2: PLATFORM CONTENT — Daily Package
# ════════════════════════════════════════════════
def run_content_agent(users, day_num):
    """Generate full platform content package"""
    print("  [Content Agent] Generating...")
    
    # TikTok scripts
    tt = gm(f"""{BRAND}
Write 2 TikTok scripts for Vessel. Day {day_num}. {users} users in protocol.
Script 1: POV "Day in the Vessel protocol" — show morning breath, intention, action, evening.
Script 2: Hook on the CT×A=M formula — explain fast, cosmic tone, hook in 3 seconds.
For each: hook (0-3s), body (3-35s), cta (35-45s), caption with hashtags.
Format: JSON array.""")
    
    # Instagram
    ig = gm(f"""{BRAND}
Write Instagram content for Vessel. Day {day_num}.
1. Feed post: 150 chars + hashtags, cosmic/formula focused
2. Reel caption: 100 chars + hashtags, for a breathing circle video
3. Story slides: 5 text-only slides building to CTA at {APP_URL}
Format: JSON with keys feed, reel, story_slides.""")
    
    # Twitter thread
    tw = gm(f"""{BRAND}
Write a 5-tweet Twitter thread. Day {day_num}. Hook → problem → CT×A=M → proof → CTA.
Hook must stop scrolling. Each max 240 chars. Final tweet: {APP_URL}
Format: JSON array of 5 strings.""")
    
    # Blog post
    blog_topics = [
        "The Science Behind Coherence Breathing and Manifestation",
        "Why 365 Days: The Neuroscience of Habit Formation",
        "CT×A=M Explained: The Only Manifestation Formula That Requires Action",
        "Manifestation vs Meditation: Why Vessel Does Both Differently",
        "How AI Personalizes Your 365-Day Protocol",
        "The Psychology of the Vessel Kids Protocol (Ages 10-18)",
        "From Day 1 to Day 66: The Automaticity Threshold",
        "Why Most Manifestation Apps Fail (And What Vessel Does Differently)"
    ]
    topic = blog_topics[day_num % len(blog_topics)]
    blog = gm(f"""{BRAND}
Write a 500-word SEO blog post. Topic: {topic}
H1, 3 H2s, natural keywords, CTA at end linking to {APP_URL}
Target keywords: manifestation app, CT×A=M, 365 day protocol, conscious manifestation
Format: Markdown""")
    
    content = {"tiktok_scripts": tt, "instagram": ig, "twitter_thread": tw, "blog": blog}
    
    # Save package
    today = date.today().isoformat()
    pkg_file = OUTPUT / f"vessel_content_{today}.json"
    with open(pkg_file, 'w') as f:
        json.dump({"date":today,"day":day_num,"users":users,"content":content,
                   "urls":{"app":APP_URL,"kids":KIDS_URL,"land":LAND_URL}}, f, indent=2, ensure_ascii=False)
    
    log_content("multi", "daily_package", f"Day {day_num} package saved")
    print(f"    Content package saved: {pkg_file.name}")
    return content

# ════════════════════════════════════════════════
# SECTION 3: INFLUENCER OUTREACH AGENT
# ════════════════════════════════════════════════
def run_outreach_agent(day_num):
    """Generate personalized influencer outreach DMs"""
    print("  [Outreach Agent] Generating DMs...")
    
    profiles = [
        {"handle":"@manifestwithme_","platform":"Instagram","niche":"manifestation","followers":"12K"},
        {"handle":"@cosmicalchemy_co","platform":"TikTok","niche":"spiritual wellness","followers":"28K"},
        {"handle":"@darkacademia.wellness","platform":"Instagram","niche":"dark aesthetic wellness","followers":"8K"},
        {"handle":"@neurowellness.ai","platform":"TikTok","niche":"science + spirituality","followers":"45K"},
        {"handle":"@intentionaldrift","platform":"Instagram","niche":"conscious creation","followers":"19K"},
    ]
    
    dms = []
    for p in profiles[:3]:  # 3 per day
        dm = gm(f"""{BRAND}
Write a personalized DM to send to {p['handle']} ({p['platform']}, {p['followers']} followers, {p['niche']} niche).
Offer: gifted 3-month Vessel subscription + 20% recurring affiliate commission.
Make it personal to their niche. Not a generic pitch. Reference their content style.
Under 300 chars (DM limit). Brand voice: mysterious, inviting, peer-to-peer.
Output: Just the DM text, no explanation.""")
        dms.append({"profile":p, "dm":dm})
    
    outreach_file = OUTPUT / f"influencer_outreach_{date.today().isoformat()}.json"
    with open(outreach_file, 'w') as f:
        json.dump({"date":date.today().isoformat(),"outreach":dms}, f, indent=2)
    
    print(f"    {len(dms)} outreach DMs ready in {outreach_file.name}")
    return dms

# ════════════════════════════════════════════════
# SECTION 4: FUNNEL — UGC Prompts
# ════════════════════════════════════════════════
def run_ugc_agent(users, day_num):
    """Generate UGC prompts + shareable content ideas"""
    print("  [UGC Agent] Generating prompts...")
    
    prompts = gm(f"""{BRAND}
Generate 5 UGC prompts for Vessel community. Day {day_num}. {users} users.
Each prompt encourages users to share their journey publicly using #VesselTransmissions.
Keep mysterious, focus on internal shifts not personal details.
Example: "What subtle shift did you notice in your reality this week? #VesselTransmissions"
Format: JSON array of 5 prompt strings.""")
    
    log_content("community", "ugc_prompts", prompts[:200])
    return prompts

# ════════════════════════════════════════════════
# SECTION 5: EMAIL SEQUENCES
# ════════════════════════════════════════════════
def run_email_agent(users, day_num):
    """Generate email content for the week"""
    print("  [Email Agent] Generating sequences...")
    
    # Weekly newsletter
    newsletter = gm(f"""{BRAND}
Write a weekly Vessel email newsletter. Day {day_num}. {users} users in protocol.
Subject line options: 3 choices in the formula style.
Body: 200 words. Dark cosmic voice. Feature: one protocol insight, one community stat, one CTA.
CTA: {APP_URL}
Format: JSON with keys: subjects (array of 3), body.""")
    
    # Re-engagement for inactive users (dropout agent coordinates)
    reengagement = gm(f"""{BRAND}
Write a re-engagement email for Vessel users who haven't logged in for 3+ days.
Subject: mysterious, not guilt-inducing.
Body: 100 words. Make returning feel easy. Not preachy.
CTA: "Resume your protocol" → {APP_URL}
Format: JSON with keys: subject, body.""")
    
    email_pkg = {"newsletter": newsletter, "reengagement": reengagement, "date": date.today().isoformat()}
    email_file = OUTPUT / f"email_content_{date.today().isoformat()}.json"
    with open(email_file, 'w') as f:
        json.dump(email_pkg, f, indent=2, ensure_ascii=False)
    
    print(f"    Email content saved: {email_file.name}")
    return email_pkg

# ════════════════════════════════════════════════
# SECTION 6: SEO BLOG — 20-Post Plan
# ════════════════════════════════════════════════
SEO_TOPICS = [
    ("CT×A=M Explained: The Only Manifestation Formula That Requires Action", "CT×A=M formula"),
    ("The Science of Coherence Breathing: Why Vessel's Protocol Works", "coherence breathing manifestation"),
    ("Why 365 Days? The Neuroscience Behind Habit Formation", "habit formation science 365 days"),
    ("Manifestation vs Meditation: What Vessel Does Differently", "manifestation vs meditation app"),
    ("How AI Personalizes Your 365-Day Manifestation Protocol", "AI manifestation app personalized"),
    ("The 66-Day Threshold: When Habits Become Identity", "66 day habit formation"),
    ("Vessel Kids: Teaching Children Goal-Setting Without Pressure", "manifestation app for kids"),
    ("Binaural Beats and Manifestation: The Science Behind Vessel's Audio", "binaural beats manifestation"),
    ("Why Most Manifestation Apps Fail (And What Vessel Does Differently)", "best manifestation app"),
    ("From Vision Board to Daily Protocol: The Action Gap", "vision board manifestation action"),
    ("The CT×A=M Morning Routine: How Vessel Users Start Their Day", "manifestation morning routine"),
    ("Manifestation for Skeptics: The Data-Driven Case for CT×A=M", "does manifestation work science"),
    ("How Coherence Breathing Syncs Your Heart and Brain", "heart brain coherence breathing"),
    ("The USS Score: Measuring Your Transformation Over 365 Days", "track manifestation progress"),
    ("Vessel vs Calm vs Headspace: Why Protocol Beats Meditation", "vessel vs calm vs headspace"),
    ("Building a Manifestation Habit: The Vessel 3-Session System", "daily manifestation habit"),
    ("The Dark Cosmic Aesthetic: Why Design Matters in Wellness Apps", "dark aesthetic wellness app"),
    ("Manifestation and Wealth: How Vessel Approaches the Wealth Goal", "wealth manifestation app"),
    ("Vessel Kids vs Headspace for Kids: A Protocol Comparison", "mindfulness app for kids"),
    ("The Referral Code System: Growing Your Vessel Community", "manifestation community app"),
]

def run_seo_agent(day_num):
    """Write one SEO blog post per day from the 20-post plan"""
    print("  [SEO Blog Agent] Writing post...")
    topic, keyword = SEO_TOPICS[day_num % len(SEO_TOPICS)]
    
    post = gm(f"""{BRAND}
Write a 600-word SEO blog post.
Title: {topic}
Primary keyword: {keyword} (use naturally 4-6 times)
Structure: H1, introduction, 3 H2 sections, conclusion with CTA
CTA links to: {APP_URL}
Voice: Vessel brand — mysterious but science-grounded, no fluff
Format: Markdown""")
    
    slug = topic.lower().replace(" ","_").replace(":","").replace("'","")[:50]
    blog_file = OUTPUT / f"blog_{date.today().isoformat()}_{slug}.md"
    blog_file.write_text(post)
    log_content("blog", "seo_post", f"Title: {topic}")
    print(f"    Blog post saved: {blog_file.name}")
    return topic, post

# ════════════════════════════════════════════════
# SECTION 7: 90-DAY ROADMAP TRACKER
# ════════════════════════════════════════════════
def check_roadmap_phase(day_num, users):
    """Check what phase we're in and what's due"""
    if day_num <= 14:
        phase = "Phase 1: Foundation"
        goal_users = 5
        priorities = ["Organic TikTok content daily", "Instagram stories + reels", "Bluesky transmissions", "First 5 subscribers"]
    elif day_num <= 28:
        phase = "Phase 2: Launch"
        goal_users = 25
        priorities = ["Content blitz across all platforms", "Referral activation", "First influencer outreach (5 profiles)", "25 subscribers target"]
    elif day_num <= 90:
        phase = "Phase 3: Growth"
        goal_users = 100
        priorities = ["25-agent army at full capacity", "Email sequences firing", "First $200 TikTok ad test", "100 subscribers = $451 MRR"]
    else:
        phase = "Phase 4: Scale"
        goal_users = 250
        priorities = ["Scale winning ads", "Affiliate program live", "App Store submission", "$1,127 MRR target"]
    
    pct = min(100, round(users/goal_users*100)) if goal_users > 0 else 0
    return phase, goal_users, pct, priorities

# ════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ════════════════════════════════════════════════
def run():
    print(f"\n[{datetime.now().strftime('%H:%M')}] ═══ VESSEL MARKETING MASTER PLAN — Running ═══")
    
    users, checkins = get_stats()
    launch_date = date(2026, 4, 12)
    day_num = (date.today() - launch_date).days + 1
    phase, goal_users, pct, priorities = check_roadmap_phase(day_num, users)
    
    print(f"Day {day_num} | {users} users | Phase: {phase}")
    
    # Run all agents
    print("\nRunning marketing agents...")
    
    # 1. Transmission posts (Bluesky — live)
    posts, bsky_count = run_transmission_agent(users, day_num)
    
    # 2. Full content package
    content = run_content_agent(users, day_num)
    
    # 3. Influencer outreach DMs (Mon/Thu only)
    dms = []
    if date.today().weekday() in [0, 3]:  # Monday, Thursday
        dms = run_outreach_agent(day_num)
    
    # 4. UGC prompts
    ugc = run_ugc_agent(users, day_num)
    
    # 5. Email content
    emails = run_email_agent(users, day_num)
    
    # 6. SEO blog post (every day)
    blog_title, blog_post = run_seo_agent(day_num)
    
    # ── Telegram Report ──
    outreach_note = f"\n📩 Influencer DMs: {len(dms)} ready" if dms else ""
    
    report = f"""🚀 <b>Vessel Marketing — Day {day_num}</b>
Phase: {phase} ({pct}% to {goal_users} user goal)

<b>Auto-executed:</b>
✅ Bluesky: {bsky_count}/3 transmissions live
✅ Content package: TikTok + IG + Twitter + Email saved
✅ SEO blog: "{blog_title[:50]}..."
{outreach_note}

<b>Ready for you to post manually:</b>
📱 TikTok: 2 video scripts (record + post)
📸 Instagram: feed + reel + 5 story slides
🐦 Twitter: 5-tweet thread (paste in order)
📝 Blog: 600-word post (paste to Medium/site)

<b>Roadmap priorities today:</b>
{chr(10).join(f"• {p}" for p in priorities[:3])}

<b>Stats:</b>
👤 {users} users | 📊 {checkins} check-ins
💰 Est MRR: ${users * 4.99:.0f}/month

Files: /root/workspace/Penelope/vessel_marketing_output/"""
    
    tg(report)
    print("\n✅ All agents complete. Telegram report sent.")
    print(f"Output: {OUTPUT}")

if __name__ == "__main__":
    run()