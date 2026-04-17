"""
vessel_platform_agents.py
Remaining 15 agents: Pinterest(3) + X/Twitter(3) + Bluesky(2) +
YouTube(2) + Reddit(2) + Email(2) + Blog SEO(1)
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
GUMROAD_KEY    = VAULT.get("GUMROAD_API_KEY","")

client = genai.Client(api_key=GOOGLE_API_KEY)
BV = "VESSEL brand: Mysterious, dark cosmic, CT×A=M, 365-day AI journey, $4.99/month. No exclamation marks. End with ✦"

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

def log_post(agent, platform, content):
    log_path = "/root/workspace/Penelope/social_log.json"
    try:
        with open(log_path) as f: log = json.load(f)
    except: log = {}
    log[f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"] = {
        "agent":agent,"platform":platform,"content":str(content)[:400],
        "timestamp":datetime.now().isoformat()}
    with open(log_path,"w") as f: json.dump(log,f,indent=2)

# ── PINTEREST AGENTS (11-13) ──────────────────────────────────
def vessel_pinterest_inspo_agent():
    print("[vessel_pinterest_inspo_agent] Running...")
    prompt = f"""{BV}
vessel_pinterest_inspo_agent: Create 5 Pinterest pin concepts.
Mix: affirmation quotes, cosmic imagery, manifestation inspiration.
For each pin: title (60 chars), description (150 chars with keywords), image description, link destination.
Keywords: manifestation, law of attraction, spiritual growth, dark aesthetic, CT×A=M
Format: JSON array of 5 pin objects."""
    raw = gm(prompt)
    pins = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        pins = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: pins=[{"raw":raw}]
    log_post("vessel_pinterest_inspo_agent","pinterest",pins)
    tg(f"📌 <b>Pinterest Inspo Agent</b>\n{len(pins)} pins generated")
    return pins

def vessel_pinterest_guide_agent():
    print("[vessel_pinterest_guide_agent] Running...")
    topics = ["CT×A=M Step-by-Step","How the 365-Day Protocol Works","The USS Score Explained",
              "Vessel Morning Alignment Ritual","What Happens at Day 66"]
    topic = random.choice(topics)
    prompt = f"""{BV}
vessel_pinterest_guide_agent: Create 3 infographic-style Pinterest pins about: {topic}
Each pin is educational with visual structure (numbered steps, comparison, process flow).
For each: title, 3-5 key points as text blocks, image layout description, SEO description, hashtags.
Format: JSON array of 3 infographic pin objects."""
    raw = gm(prompt)
    pins = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        pins = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: pins=[{"raw":raw}]
    log_post("vessel_pinterest_guide_agent","pinterest",pins)
    tg(f"📌 <b>Pinterest Guide Agent</b>\n{len(pins)} infographics | {topic[:40]}")
    return pins

def vessel_pinterest_lifestyle_agent():
    print("[vessel_pinterest_lifestyle_agent] Running...")
    prompt = f"""{BV}
vessel_pinterest_lifestyle_agent: Create 4 lifestyle/vision board Pinterest pins.
Show aspirational scenes that evoke: abundance, inner peace, transformation, cosmic alignment.
Each pin: vision board element description, aspirational caption, relevant keywords for SEO.
Dark cosmic twist on wellness aesthetics. Make outsiders want this life.
Format: JSON array of 4 lifestyle pin objects."""
    raw = gm(prompt)
    pins = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        pins = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: pins=[{"raw":raw}]
    log_post("vessel_pinterest_lifestyle_agent","pinterest",pins)
    tg(f"📌 <b>Pinterest Lifestyle Agent</b>\n{len(pins)} lifestyle pins")
    return pins

# ── X/TWITTER AGENTS (14-16) ──────────────────────────────────
def vessel_twitter_thought_agent():
    print("[vessel_twitter_thought_agent] Running...")
    day = random.randint(1,365)
    prompt = f"""{BV}
vessel_twitter_thought_agent: Generate 6 tweets for X/Twitter.
Mix of: day counter transmissions, thought-provoking questions, CT×A=M insights.
Max 280 chars each. Dark, mysterious, no hashtag overload (max 2 per tweet).
One tweet must be: "Day {day} ✦ [powerful one-sentence transmission]"
Format: JSON array of 6 tweet strings."""
    raw = gm(prompt)
    tweets = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        tweets = json.loads(raw[s:e]) if s>=0 else [raw]
    except: tweets=[raw]
    log_post("vessel_twitter_thought_agent","twitter",tweets)
    tg(f"🐦 <b>Twitter Thought Agent</b>\n{len(tweets)} tweets | Day {day}")
    return tweets

def vessel_twitter_news_agent():
    print("[vessel_twitter_news_agent] Running...")
    blog_topics = [
        "The neuroscience of 66-day habit formation",
        "Why action is the missing ingredient in manifestation",
        "How AI personalizes your spiritual growth journey",
        "The science of brain-heart coherence in daily ritual",
    ]
    topic = random.choice(blog_topics)
    prompt = f"""{BV}
vessel_twitter_news_agent: Create 4 tweets linking to Vessel blog content.
Blog topic: {topic}
Tweets should tease the insight without giving it all away — drive clicks.
Include 1-2 relevant hashtags. Max 280 chars. Mix: thread opener, quote, stat, question.
Format: JSON array of 4 tweet strings."""
    raw = gm(prompt)
    tweets = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        tweets = json.loads(raw[s:e]) if s>=0 else [raw]
    except: tweets=[raw]
    log_post("vessel_twitter_news_agent","twitter",tweets)
    tg(f"🐦 <b>Twitter News Agent</b>\n{len(tweets)} link tweets")
    return tweets

def vessel_twitter_engage_agent():
    print("[vessel_twitter_engage_agent] Running...")
    prompt = f"""{BV}
vessel_twitter_engage_agent: Generate engagement content for X/Twitter.

1. WEEKLY POLL (1): cosmic-themed, 4 options, related to manifestation
   Format: question + 4 options
2. REPLY TEMPLATES (5): for when someone mentions manifestation, spiritual growth, or feeling stuck
   Each reply: warm, curious, never salesy, max 200 chars
3. RETWEET COMMENTARY (3): short comments to add when retweeting aligned content
   Each: 1 powerful sentence + ✦

Format: JSON object with poll, replies array, commentary array."""
    raw = gm(prompt)
    content = {}
    try:
        s=raw.find("{"); e=raw.rfind("}")+1
        content = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: content={"raw":raw}
    log_post("vessel_twitter_engage_agent","twitter",content)
    tg(f"🐦 <b>Twitter Engage Agent</b>\nPoll + 5 replies + 3 commentary")
    return content

# ── BLUESKY AGENTS (17-18) ──────────────────────────────────
def vessel_bluesky_community_agent():
    print("[vessel_bluesky_community_agent] Running...")
    day = random.randint(1,365)
    prompt = f"""{BV}
vessel_bluesky_agent_1 (community): Generate 5 Bluesky posts.
Bluesky is for early adopters — slightly more experimental, philosophical, community-building.
Include: open questions, cosmic insights, day counter transmissions, community invitations.
One must be about Day {day}. Posts can be slightly longer than Twitter (300 chars).
Format: JSON array of 5 post strings."""
    raw = gm(prompt)
    posts = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        posts = json.loads(raw[s:e]) if s>=0 else [raw]
    except: posts=[raw]
    log_post("vessel_bluesky_community_agent","bluesky",posts)
    tg(f"🦋 <b>Bluesky Community Agent</b>\n{len(posts)} posts")
    return posts

def vessel_bluesky_deep_agent():
    print("[vessel_bluesky_deep_agent] Running...")
    prompt = f"""{BV}
vessel_bluesky_agent_2 (deep dive): Generate 3 longer Bluesky posts/threads.
These are deeper philosophical explorations of CT×A=M, consciousness, and manifestation science.
Each can be a mini-thread (2-3 connected posts) or one longer post (400-500 chars).
More intellectual, less cryptic. Still Vessel-branded. Bridge ancient wisdom + modern AI.
Format: JSON array of 3 thread objects, each with posts array."""
    raw = gm(prompt)
    threads = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        threads = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: threads=[{"raw":raw}]
    log_post("vessel_bluesky_deep_agent","bluesky",threads)
    tg(f"🦋 <b>Bluesky Deep Agent</b>\n{len(threads)} threads")
    return threads

# ── YOUTUBE AGENTS (19-20) ──────────────────────────────────
def vessel_youtube_concept_agent():
    print("[vessel_youtube_concept_agent] Running...")
    concepts = ["CT×A=M in 60 seconds","What is a USS score?","The 66-day threshold explained",
                "Day 1 vs Day 66: what changes","The 3 phases of the Vessel protocol"]
    concept = random.choice(concepts)
    prompt = f"""{BV}
vessel_youtube_concept_agent: Script a YouTube Short for concept: {concept}
Duration: 45-60 seconds. Fast-paced, animated text style.
Provide: hook (first 5 words), full voiceover script, text overlay sequence,
visual direction, title (under 60 chars), description (under 200 chars), tags (10).
Format: JSON object."""
    raw = gm(prompt)
    script = {}
    try:
        s=raw.find("{"); e=raw.rfind("}")+1
        script = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: script={"raw":raw}
    log_post("vessel_youtube_concept_agent","youtube",script)
    tg(f"📹 <b>YouTube Concept Agent</b>\n{concept}")
    return script

def vessel_youtube_affirm_agent():
    print("[vessel_youtube_affirm_agent] Running...")
    goal = random.choice(["wealth","health","body","love","purpose","peace"])
    prompt = f"""{BV}
vessel_youtube_affirm_agent: Create 2 YouTube Short scripts — affirmation/meditation focus.
Goal type: {goal}. Dark cosmic visuals, ambient audio, 15-30 seconds each.
Short 1: 5 powerful affirmations for {goal} with cinematic pauses
Short 2: 60-second guided micro-visualization for {goal} manifestation
For each: voiceover, visual sequence, text overlays, title, description, tags.
Format: JSON array of 2 Short objects."""
    raw = gm(prompt)
    shorts = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        shorts = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: shorts=[{"raw":raw}]
    log_post("vessel_youtube_affirm_agent","youtube",shorts)
    tg(f"📹 <b>YouTube Affirm Agent</b>\n{len(shorts)} Shorts | {goal}")
    return shorts

# ── REDDIT AGENTS (21-22) ──────────────────────────────────
def vessel_reddit_advice_agent():
    print("[vessel_reddit_advice_agent] Running...")
    scenarios = [
        ("r/getmotivated","I feel stuck and can't seem to make progress on my goals"),
        ("r/spirituality","I've been trying to manifest but nothing seems to work"),
        ("r/selfimprovement","I've tried every productivity system but I fall off after 2 weeks"),
        ("r/LifeAdvice","How do I build habits that actually stick long-term"),
        ("r/lawofattraction","Is manifestation real or just positive thinking?"),
    ]
    sub, situation = random.choice(scenarios)

    prompt = f"""{BV}
vessel_reddit_advice_agent: Write 3 Reddit comment replies for {sub}.
Post situation: "{situation}"

Each reply: genuinely helpful, no mention of Vessel app directly (shadow post style),
references CT×A=M principles naturally, max 200 words, upvote-worthy advice.
Only hint at deeper protocol at end of one reply: "there's actually a structured approach to this..."
Format: JSON array of 3 reply strings."""
    raw = gm(prompt)
    replies = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        replies = json.loads(raw[s:e]) if s>=0 else [raw]
    except: replies=[raw]
    log_post("vessel_reddit_advice_agent","reddit",replies)
    tg(f"🤖 <b>Reddit Advice Agent</b>\n{sub} | {len(replies)} replies")
    return replies

def vessel_reddit_inspire_agent():
    print("[vessel_reddit_inspire_agent] Running...")
    subreddits = ["r/manifestation","r/lawofattraction","r/spirituality","r/selfimprovement"]
    sub = random.choice(subreddits)
    post_types = ["anonymous success story","thought experiment","open question","mini essay"]
    post_type = random.choice(post_types)

    prompt = f"""{BV}
vessel_reddit_inspire_agent: Write 1 original Reddit post for {sub}.
Post type: {post_type}
Topics: manifestation science, habit formation, CT×A=M principles, conscious action.
Max 300 words. No direct Vessel promotion. Genuinely valuable. Sparks conversation.
Include: title, body, optional TL;DR
Format: JSON object with title, body, tldr."""
    raw = gm(prompt)
    post = {}
    try:
        s=raw.find("{"); e=raw.rfind("}")+1
        post = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: post={"raw":raw}
    log_post("vessel_reddit_inspire_agent","reddit",post)
    tg(f"🤖 <b>Reddit Inspire Agent</b>\n{sub} | {post_type}")
    return post

# ── EMAIL AGENTS (23-24) ──────────────────────────────────
def vessel_email_welcome_agent(user_data=None):
    print("[vessel_email_welcome_agent] Running...")
    user = user_data or {"name":"Vessel","goal_types":["wealth","purpose"],"day_count":1}
    goals = user.get("goal_types",["purpose"])
    name = user.get("name","Vessel")

    prompt = f"""{BV}
vessel_email_welcome_agent: Generate the 7-email welcome sequence for a new Vessel subscriber.

User: {name} | Goals: {', '.join(goals)} | Day: {user.get('day_count',1)}

For each of 7 emails (Day 0,1,3,7,14,21,30):
- SUBJECT LINE: intriguing, under 50 chars
- PREVIEW TEXT: 90 char preview
- BODY: 3-4 sentences, mysterious, empowering, brand-aligned
- CTA BUTTON TEXT + URL destination

Make each email feel like a transmission from the cosmos, not a marketing email.
Reference their goal ({goals[0]}) in at least 3 emails.
Format: JSON array of 7 email objects."""
    raw = gm(prompt)
    emails = []
    try:
        s=raw.find("["); e=raw.rfind("]")+1
        emails = json.loads(raw[s:e]) if s>=0 else [{"raw":raw}]
    except: emails=[{"raw":raw}]

    # Save to file for actual sending
    email_path = f"/root/workspace/Penelope/shipped/vessel_welcome_seq_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(email_path,"w") as f: json.dump({"user":user,"emails":emails},f,indent=2)
    tg(f"📧 <b>Email Welcome Agent</b>\n{len(emails)} emails for {name}\nGoals: {', '.join(goals)}")
    return emails

def vessel_email_milestone_agent(user_data=None):
    print("[vessel_email_milestone_agent] Running...")
    user = user_data or {"name":"Vessel","goal_types":["wealth"],"day_count":66,"uss_score":74}
    day = user.get("day_count",66)
    name = user.get("name","Vessel")
    goal = user.get("goal_types",["purpose"])[0]
    uss = user.get("uss_score",65)

    # Determine which milestone email to send
    milestones = {7:"First Week",30:"First Month",66:"Automaticity Lock",
                  100:"Triple Digits",180:"Halfway",365:"Year Complete"}
    milestone = milestones.get(day, f"Day {day}")

    prompt = f"""{BV}
vessel_email_milestone_agent: Write a milestone email for Day {day} ({milestone}).

User: {name} | Primary goal: {goal} | USS Score: {uss}/100

This is the most important email of their journey (especially Day 66 — the identity lock).
- SUBJECT: powerful, references their milestone specifically
- PREVIEW TEXT: 90 chars
- OPENING: acknowledge what they've achieved (in cosmic language)
- BODY: 3-4 paragraphs — what this milestone means, what shifts at this point,
  what to expect next. Reference their goal ({goal}) specifically.
- DATA MOMENT: reference their USS score ({uss}/100) or streak
- CTA: one clear next action in the app
- CLOSING: cryptic, powerful, cosmic

Format: JSON object with all fields."""
    raw = gm(prompt)
    email = {}
    try:
        s=raw.find("{"); e=raw.rfind("}")+1
        email = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: email={"raw":raw}

    email_path = f"/root/workspace/Penelope/shipped/vessel_milestone_day{day}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(email_path,"w") as f: json.dump({"user":user,"email":email},f,indent=2)
    tg(f"📧 <b>Email Milestone Agent</b>\nDay {day}: {milestone} | {name} | USS={uss}")
    return email

# ── BLOG SEO AGENT (25) ──────────────────────────────────
def vessel_blog_seo_agent(topic=None):
    print("[vessel_blog_seo_agent] Running...")
    seo_topics = [
        ("how long does it take to form a habit","habit formation 66 days science",1800),
        ("manifestation techniques that actually work","manifestation techniques",2500),
        ("what is conscious thought in manifestation","conscious thought manifestation",800),
        ("CT×A=M formula explained","CTxA=M manifestation formula",300),
        ("brain heart coherence breathing","brain heart coherence",900),
        ("AI manifestation app 2025","AI manifestation app",600),
        ("365 day habit challenge","365 day habit",700),
        ("the neuroscience of belief and manifestation","neuroscience belief manifestation",1300),
        ("morning ritual manifestation routine","morning manifestation ritual",800),
        ("word of mouth marketing spiritual app","spiritual wellness app growth",400),
    ]

    if topic:
        title, keyword, msv = topic, topic, 500
    else:
        title, keyword, msv = random.choice(seo_topics)

    prompt = f"""{BV}
vessel_blog_seo_agent: Write a complete SEO blog post outline + intro for Vessel.

Title: {title}
Target keyword: {keyword}
Est. monthly searches: {msv}

Provide:
1. SEO TITLE (under 60 chars, includes keyword)
2. META DESCRIPTION (under 155 chars, compelling)
3. ARTICLE OUTLINE: H2 and H3 structure (6-8 sections)
4. INTRODUCTION (200 words): hooks reader, naturally includes keyword,
   establishes Vessel's authority, mysterious + scientific tone
5. INTERNAL LINKS: 3 suggested internal link opportunities to other Vessel content
6. CTA PLACEMENT: where to place Vessel app CTA (section + copy)
7. ESTIMATED READ TIME
8. TARGET AUDIENCE: who finds this via search

Format: JSON object with all fields."""

    raw = gm(prompt, temp=0.5)
    post = {}
    try:
        s=raw.find("{"); e=raw.rfind("}")+1
        post = json.loads(raw[s:e]) if s>=0 else {"raw":raw}
    except: post={"raw":raw}

    post_path = f"/root/workspace/Penelope/shipped/vessel_blog_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(post_path,"w") as f: json.dump({"topic":title,"keyword":keyword,"post":post},f,indent=2)
    print(f"  Blog: {title[:60]}...")
    tg(f"📝 <b>Blog SEO Agent</b>\n{title[:60]}\nKeyword: {keyword}\nMSV: {msv}/mo")
    return post

# ── MASTER RUNNER ──────────────────────────────────────────
def run_all_platform_agents():
    print(f"[{datetime.now().isoformat()}] Running all 15 platform agents...")
    results = {}
    agents = [
        ("pinterest_inspo",   vessel_pinterest_inspo_agent),
        ("pinterest_guide",   vessel_pinterest_guide_agent),
        ("pinterest_lifestyle",vessel_pinterest_lifestyle_agent),
        ("twitter_thought",   vessel_twitter_thought_agent),
        ("twitter_news",      vessel_twitter_news_agent),
        ("twitter_engage",    vessel_twitter_engage_agent),
        ("bluesky_community", vessel_bluesky_community_agent),
        ("bluesky_deep",      vessel_bluesky_deep_agent),
        ("youtube_concept",   vessel_youtube_concept_agent),
        ("youtube_affirm",    vessel_youtube_affirm_agent),
        ("reddit_advice",     vessel_reddit_advice_agent),
        ("reddit_inspire",    vessel_reddit_inspire_agent),
        ("email_welcome",     vessel_email_welcome_agent),
        ("email_milestone",   vessel_email_milestone_agent),
        ("blog_seo",          vessel_blog_seo_agent),
    ]
    for name, fn in agents:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            results[name] = {"error":str(e)}
        time.sleep(2)

    output_path = f"/root/workspace/Penelope/shipped/vessel_platform_agents_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path,"w") as f: json.dump(results,f,indent=2)
    print(f"All 15 platform agents complete. Saved: {output_path}")
    tg(f"✅ <b>All 15 Platform Agents Complete</b>\n{output_path}")
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        agent_map = {
            "pinterest_inspo":    vessel_pinterest_inspo_agent,
            "pinterest_guide":    vessel_pinterest_guide_agent,
            "pinterest_lifestyle":vessel_pinterest_lifestyle_agent,
            "twitter_thought":    vessel_twitter_thought_agent,
            "twitter_news":       vessel_twitter_news_agent,
            "twitter_engage":     vessel_twitter_engage_agent,
            "bluesky_community":  vessel_bluesky_community_agent,
            "bluesky_deep":       vessel_bluesky_deep_agent,
            "youtube_concept":    vessel_youtube_concept_agent,
            "youtube_affirm":     vessel_youtube_affirm_agent,
            "reddit_advice":      vessel_reddit_advice_agent,
            "reddit_inspire":     vessel_reddit_inspire_agent,
            "email_welcome":      vessel_email_welcome_agent,
            "email_milestone":    vessel_email_milestone_agent,
            "blog_seo":           vessel_blog_seo_agent,
        }
        fn = agent_map.get(sys.argv[1])
        if fn: fn()
        else: print(f"Unknown agent: {sys.argv[1]}")
    else:
        run_all_platform_agents()