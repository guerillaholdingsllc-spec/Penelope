"""
vessel_marketing_agent.py
Penelope's Vessel marketing implementation.
Actually executes marketing — Bluesky posts live, 
content packages written to disk for human posting on locked platforms.
Runs daily, tracks everything in Notion.
"""
import os, json, requests, time, random
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
BLUESKY_PW     = VAULT.get("BLUESKY_PASSWORD","")
APP_URL        = "https://ctxaxm.com/vessel.html"
KIDS_URL       = "https://ctxaxm.com/vessel-kids.html"
LAND_URL       = "https://ctxaxm.com"
OUTPUT_DIR     = Path("/root/workspace/Penelope/vessel_marketing_output")
OUTPUT_DIR.mkdir(exist_ok=True)

client = genai.Client(api_key=GOOGLE_API_KEY)

BRAND = """VESSEL — 365-Day Manifestation Protocol
Formula: CT×A=M (Conscious Thought × Action = Manifestation)
Price: $4.99/month or $39.99/year
App: ctxaxm.com/vessel.html
Vessel Kids: ctxaxm.com/vessel-kids.html
Brand voice: Mysterious, dark cosmic, empowering, science-adjacent.
NOT spiritual fluff. Real protocol. Real action required.
End posts with ✦. Never use exclamation marks in body copy."""

def gm(prompt):
    try:
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return (getattr(r,"text","") or "").strip()
    except Exception as e:
        print(f"Gemini: {e}"); return ""

def tg(msg):
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

# ── BLUESKY (actually posts live) ────────────────────────
def bluesky_post(text):
    """Live post to Bluesky"""
    try:
        # Login
        auth = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier":BLUESKY_HANDLE,"password":BLUESKY_PW}, timeout=10)
        if not auth.ok:
            print(f"Bluesky login failed: {auth.text[:100]}")
            return False
        token = auth.json().get("accessJwt")
        did   = auth.json().get("did")
        
        # Build post with URL card if URL in text
        record = {
            "$type": "app.bsky.feed.post",
            "text": text[:300],
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "langs": ["en"]
        }
        
        # Post
        r = requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {token}"},
            json={"repo":did,"collection":"app.bsky.feed.post","record":record},
            timeout=10)
        if r.ok:
            print(f"  ✅ Bluesky: posted")
            return True
        else:
            print(f"  ❌ Bluesky: {r.text[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ Bluesky error: {e}")
        return False

# ── CONTENT GENERATION ──────────────────────────────────
def gen_daily_content():
    """Generate full day's marketing content package"""
    today = date.today().isoformat()
    day_num = (date.today() - date(2026, 4, 12)).days + 1  # Days since launch
    
    # Get user count from API
    try:
        r = requests.get("https://ctxaxm.com/vessel-api/health", timeout=5)
        d = r.json()
        user_count = d.get('users', 0)
        checkin_count = d.get('checkins', 0)
    except:
        user_count = 0
        checkin_count = 0

    content = {}

    # 1. BLUESKY — 3 posts daily (actually live)
    print("  Generating Bluesky posts...")
    bsky_prompt = f"""{BRAND}
Write 3 Bluesky posts for today. Day {day_num} since launch. {user_count} users in protocol.
Mix of: protocol truth, formula drop, transformation nudge.
Each max 280 chars. Include {APP_URL} in at least one.
Format: JSON array of 3 strings."""
    
    bsky_raw = gm(bsky_prompt)
    try:
        import re
        bsky_json = re.search(r'\[.*?\]', bsky_raw, re.DOTALL)
        bsky_posts = json.loads(bsky_json.group()) if bsky_json else []
    except:
        bsky_posts = [
            f"Day {day_num}. The protocol holds. {user_count} Vessels in motion. CT×A=M. ✦\n{APP_URL}",
            f"Conscious thought without action is just dreaming. Vessel requires both. ✦",
            f"365 days. One formula. Your reality, rewritten. ✦\n{LAND_URL}"
        ]
    content['bluesky'] = bsky_posts

    # 2. TIKTOK SCRIPTS — 2 scripts daily (for manual posting)
    print("  Generating TikTok scripts...")
    tt_prompt = f"""{BRAND}
Write 2 TikTok video scripts for Vessel. Keep each under 45 seconds when spoken.
Formats:
1. "Day in the protocol" POV — show morning breath, intention, action, evening check-in
2. "What is CT×A=M" — explain the formula fast, hook in first 3 seconds

For each: Hook (0-3s), Body (3-35s), CTA (35-45s), on-screen text suggestions, caption with hashtags.
Format: JSON array of 2 script objects with fields: hook, body, cta, onscreen_text, caption, hashtags"""
    
    tt_raw = gm(tt_prompt)
    try:
        import re
        tt_json = re.search(r'\[.*?\]', tt_raw, re.DOTALL)
        tt_scripts = json.loads(tt_json.group()) if tt_json else []
    except:
        tt_scripts = [{"hook": "I did this for 365 days.", "body": f"Every morning: breathe for 5 minutes. Set one intention. One aligned action. Evening: log your mood, reflect. That's the Vessel protocol. CT×A=M.", "cta": f"Link in bio. Start free. {APP_URL}", "caption": f"365 days of this changed everything ✦\n{APP_URL}", "hashtags": "#manifestation #vessel #ctxaxm #dailyprotocol #lawofattraction"}]
    content['tiktok'] = tt_scripts

    # 3. INSTAGRAM CAPTIONS — 3 (feed, reel, story)
    print("  Generating Instagram content...")
    ig_prompt = f"""{BRAND}
Write 3 Instagram content pieces for Vessel:
1. Feed post: Motivational, formula-focused, 150-200 chars + hashtags
2. Reel caption: For a 15-30s reel showing the breathing circle, 100 chars + hashtags
3. Story slide: 5 sequential story slides (text only) building to a CTA

Format: JSON with keys: feed, reel, story_slides (array of 5 strings)"""
    
    ig_raw = gm(ig_prompt)
    try:
        import re
        ig_json = re.search(r'\{.*\}', ig_raw, re.DOTALL)
        ig_content = json.loads(ig_json.group()) if ig_json else {}
    except:
        ig_content = {
            "feed": f"Your reality is built one day at a time.\nCT×A=M — the only manifestation formula that requires proof.\n365 days. 3 sessions. One protocol. ✦\n{APP_URL}\n\n#vessel #manifestation #ctxaxm #365days #protocol",
            "reel": f"5 breaths. One intention. One action. Repeat for 365 days. ✦ {APP_URL}\n#vessel #breathwork #manifestation",
            "story_slides": ["Day 1.", "You set an intention.", "You took one action.", "You reflected.", f"That's CT×A=M. Start free at {APP_URL}"]
        }
    content['instagram'] = ig_content

    # 4. TWITTER/X THREAD — 5 tweets
    print("  Generating Twitter thread...")
    tw_prompt = f"""{BRAND}
Write a 5-tweet thread about the Vessel protocol for Twitter/X.
Hook tweet should make people stop scrolling.
Thread builds: hook → problem → formula → proof → CTA
Each tweet max 240 chars. Include {APP_URL} in final tweet.
Format: JSON array of 5 tweet strings."""
    
    tw_raw = gm(tw_prompt)
    try:
        import re
        tw_json = re.search(r'\[.*?\]', tw_raw, re.DOTALL)
        tw_thread = json.loads(tw_json.group()) if tw_json else []
    except:
        tw_thread = [
            "Most people meditate and hope.\nVessel users manifest and prove. ✦",
            "The difference: CT×A=M.\nConscious Thought × Action = Manifestation.\nYou cannot manifest without both.",
            "365 days. 3 sessions daily. Morning breathing. One action. Evening reflection.\nSimple. Hard. Real.",
            f"{user_count} people are in protocol right now. Changing their reality one day at a time. ✦",
            f"Start free. No app store. Works on any phone.\n{APP_URL}"
        ]
    content['twitter'] = tw_thread

    # 5. SEO BLOG POST — 1 per day
    print("  Generating blog post...")
    blog_prompt = f"""{BRAND}
Write a 400-word SEO blog post for Vessel.
Topic: Pick one of [how CT×A=M works, manifestation vs meditation, the science of coherence breathing, why 365 days matters, manifestation for kids]
Include: H1, 3 H2s, keyword-rich but natural, CTA at end linking to {APP_URL}
Target keywords: manifestation app, CT×A=M, 365 day protocol, conscious manifestation
Format: Markdown"""
    
    blog_content = gm(blog_prompt)
    content['blog'] = blog_content

    # 6. EMAIL SUBJECT LINES — 5 options for campaigns
    print("  Generating email subjects...")
    email_prompt = f"""{BRAND}
Write 5 email subject lines for Vessel marketing campaigns.
Mix: curiosity, formula drops, social proof, urgency.
No clickbait. No exclamation marks. Vessel brand voice.
Format: JSON array of 5 strings."""
    
    email_raw = gm(email_prompt)
    try:
        import re
        email_json = re.search(r'\[.*?\]', email_raw, re.DOTALL)
        email_subjects = json.loads(email_json.group()) if email_json else []
    except:
        email_subjects = [
            "CT×A=M — the formula that requires action",
            f"Day {day_num} of the protocol",
            "What actually separates manifesters from dreamers",
            "365 days. One daily protocol. Your reality.",
            "The only manifestation app that makes you prove it"
        ]
    content['email_subjects'] = email_subjects

    return content, user_count, day_num

def post_bluesky_content(posts):
    """Actually post to Bluesky"""
    posted = 0
    for i, post in enumerate(posts[:3]):
        if bluesky_post(post):
            posted += 1
        time.sleep(30)  # Space posts out
    return posted

def save_content_package(content, day_num):
    """Save all content to dated file for easy manual posting"""
    today = date.today().isoformat()
    output_file = OUTPUT_DIR / f"vessel_content_{today}.json"
    
    package = {
        "date": today,
        "day_since_launch": day_num,
        "generated_at": datetime.now().isoformat(),
        "ready_to_post": {
            "bluesky": "AUTO-POSTED ✅",
            "tiktok": "READY — record video using scripts below",
            "instagram": "READY — design image, use caption below",
            "twitter": "READY — paste thread in order",
            "blog": "READY — post to ctxaxm.com/blog or Medium"
        },
        "content": content
    }
    
    with open(output_file, 'w') as f:
        json.dump(package, f, indent=2, ensure_ascii=False)
    
    return str(output_file)

def run():
    print(f"[{datetime.now().strftime('%H:%M')}] Vessel Marketing Agent running...")
    
    # Generate all content
    print("Generating content package...")
    content, user_count, day_num = gen_daily_content()
    
    # Actually post to Bluesky (live)
    print("Posting to Bluesky...")
    bsky_posted = post_bluesky_content(content.get('bluesky', []))
    
    # Save everything else for manual posting
    output_file = save_content_package(content, day_num)
    print(f"Content saved: {output_file}")
    
    # Summary to Telegram
    tg_msg = f"""📣 <b>Vessel Marketing — Day {day_num}</b>

<b>Auto-posted:</b>
✅ Bluesky: {bsky_posted}/3 posts live

<b>Ready for you to post:</b>
📱 TikTok: {len(content.get('tiktok',[]))} video scripts
📸 Instagram: feed + reel + 5 story slides  
🐦 Twitter: {len(content.get('twitter',[]))} tweet thread
📝 Blog: 400-word SEO post ready

<b>Vessel stats:</b>
👤 Users: {user_count}
🔗 {APP_URL}

Content package: vessel_content_{date.today().isoformat()}.json"""
    
    tg(tg_msg)
    print("Done.")

if __name__ == "__main__":
    run()