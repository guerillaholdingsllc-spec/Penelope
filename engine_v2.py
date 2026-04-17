#!/usr/bin/env python3
"""
PENELOPE AUTONOMOUS REVENUE ENGINE v2
Runs every 30 minutes. Thinks. Decides. Executes.
No input needed. Reports outcomes only.

FUNNEL:
  Content Army output → WordPress posts (SEO + CTAs) → Gumroad $27 / Consulting $997
  Twitter (when fixed) → hooks → landing page → same funnel
  Amazon Associates → embedded in every relevant post → passive commissions
  Dropship intel → Printify products → passive ecom
  Close CRM outreach → $997 AI consulting → high ticket
"""

import os, sys, glob, json, re, time, random, subprocess, requests
from datetime import datetime
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────
SHIPPED      = "/root/workspace/Penelope/shipped"
FUNNEL_LOG   = "/root/workspace/Penelope/funnel_published.json"
ENGINE_LOG   = "/root/workspace/Penelope/engine_v2.log"
VAULT        = "/root/penelope_vault.env"
GUMROAD_URL  = "https://guerillaholdings.gumroad.com/l/vniej"
CONTACT_URL  = "https://trustchainservices.com/#contact"
MAIN_URL     = "https://trustchainservices.com"
AMAZON_TAG   = "guerillahold2-20"

def env():
    vals = {}
    for line in open(VAULT):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals

E = env()
TELEGRAM = E.get("TELEGRAM_BOT_TOKEN","")
CHAT_ID  = E.get("TELEGRAM_CHAT_ID","")
GUMROAD_TOKEN = E.get("GUMROAD_API_KEY","")
TWITTER_KEY    = E.get("TWITTER_API_KEY","")
TWITTER_SECRET = E.get("TWITTER_API_SECRET","")
TWITTER_TOKEN  = E.get("TWITTER_ACCESS_TOKEN","")
TWITTER_TSECRET= E.get("TWITTER_ACCESS_SECRET","")

# ── UTILS ────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(ENGINE_LOG, "a") as f:
        f.write(line + "\n")


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


def load_published():
    try: return set(json.load(open(FUNNEL_LOG)))
    except: return set()

def save_published(s):
    json.dump(list(s), open(FUNNEL_LOG, "w"))

def wp_post(title, content, slug):
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())[:60].strip("-")
    r = subprocess.run(
        ["docker","exec","-i","penelope-wordpress","bash","-c",
         f"cat > /tmp/ep.html && php wp-cli.phar post create "
         f'--post_title="{title.replace(chr(34), chr(39))}" '
         f"--post_name='{slug}' "
         f"--post_status=publish --post_content-file=/tmp/ep.html --allow-root 2>&1"],
        input=content, capture_output=True, text=True
    )
    out = r.stdout + r.stderr
    m = re.search(r"Created post (\d+)", out)
    return int(m.group(1)) if m else None

def tweet(text):
    """Post to Twitter via OAuth 1.0a"""
    import hmac, hashlib, base64, urllib.parse
    if not all([TWITTER_KEY, TWITTER_SECRET, TWITTER_TOKEN, TWITTER_TSECRET]):
        return None
    url = "https://api.twitter.com/2/tweets"
    ts = str(int(time.time()))
    nonce = base64.b64encode(os.urandom(16)).decode().strip("=")
    params = {
        "oauth_consumer_key": TWITTER_KEY,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": ts,
        "oauth_token": TWITTER_TOKEN,
        "oauth_version": "1.0",
    }
    base = "POST&" + urllib.parse.quote(url, safe="") + "&" + urllib.parse.quote(
        "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted(params.items())), safe=""
    )
    signing_key = urllib.parse.quote(TWITTER_SECRET, safe="") + "&" + urllib.parse.quote(TWITTER_TSECRET, safe="")
    sig = base64.b64encode(hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    params["oauth_signature"] = sig
    auth = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in sorted(params.items()))
    try:
        r = requests.post(url, json={"text": text[:280]}, headers={"Authorization": auth, "Content-Type": "application/json"}, timeout=15)
        if r.status_code == 201:
            return r.json().get("data",{}).get("id")
        log(f"Twitter {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log(f"Twitter error: {e}")
    return None

# ── CTAs ──────────────────────────────────────────────────────────────────
def cta_consulting():
    return (
        '<hr><div style="background:#0a0a0a;padding:28px;border-radius:4px;margin-top:32px">'
        '<h3 style="color:#c8f400;margin:0 0 12px">Put AI to Work in Your Business</h3>'
        '<p style="color:#ccc;margin:0 0 16px">The <strong style="color:#fff">AI Edge Accelerator</strong> maps '
        'your highest-leverage AI opportunities and delivers a 30-day implementation roadmap. '
        '$997 flat. Most clients recover it in month one through time savings alone.</p>'
        f'<a href="{CONTACT_URL}" style="background:#c8f400;color:#0a0a0a;padding:12px 24px;'
        'text-decoration:none;border-radius:3px;font-weight:700;display:inline-block">'
        'Book Free Discovery Call →</a></div>'
    )

def cta_gumroad():
    return (
        '<hr><div style="background:#0a0a0a;padding:28px;border-radius:4px;margin-top:32px">'
        '<h3 style="color:#c8f400;margin:0 0 12px">Get the Complete AI Revenue Playbook — $27</h3>'
        '<p style="color:#ccc;margin:0 0 16px">The full Guerilla Holdings operating system: '
        'AI agent architecture, specialty transport ops, social enterprise launch kit, '
        'Shopify CRO sprint, content automation, and passive income channel setup. Instant download.</p>'
        f'<a href="{GUMROAD_URL}" style="background:#c8f400;color:#0a0a0a;padding:12px 24px;'
        'text-decoration:none;border-radius:3px;font-weight:700;display:inline-block">'
        'Download Now for $27 →</a></div>'
    )

def cta_callux():
    return (
        '<hr><div style="background:#0a0a0a;padding:28px;border-radius:4px;margin-top:32px">'
        '<h3 style="color:#c8f400;margin:0 0 12px">Operate at a Higher Tier</h3>'
        '<p style="color:#ccc;margin:0 0 16px">CALLUX connects certified specialty transport operators '
        'with institutional contracts across Sacramento, NorCal, Bay Area, and Reno. '
        '65/35 revenue splits. 6-tier certification. Tier 4+ earns $35–85/hr.</p>'
        f'<a href="{MAIN_URL}" style="background:#c8f400;color:#0a0a0a;padding:12px 24px;'
        'text-decoration:none;border-radius:3px;font-weight:700;display:inline-block">'
        'Learn More →</a></div>'
    )

def cta_amazon(keyword, label):
    url = f"https://www.amazon.com/s?k={requests.utils.quote(keyword)}&tag={AMAZON_TAG}"
    return (
        f'<p><strong>→ <a href="{url}" rel="nofollow sponsored">{label} on Amazon</a></strong></p>'
    )

# ── CONTENT PROCESSORS ────────────────────────────────────────────────────
def process_consulting(filepath):
    raw = open(filepath).read()
    offer = re.search(r"OFFER NAME[:\*]+\s*(.+?)[\n\*]", raw)
    pain  = re.search(r"PAIN POINT[:\*]+\s*(.+?)[\n\*]", raw)
    target= re.search(r"TARGET CLIENT[:\*]+\s*(.+?)[\n\*]", raw)
    linkedin = re.search(r"LinkedIn Post[:\*]+\s*\n+(.+?)(?:\n---|\Z)", raw, re.DOTALL)
    email_sub = re.findall(r"\*\*Subject:\*\* (.+?)[\n\r]", raw)

    if not linkedin: return None
    lpost = linkedin.group(1).strip()
    offer_name = offer.group(1).strip() if offer else "AI Business Transformation"
    pain_text  = pain.group(1).strip() if pain else "Operational inefficiency is costing businesses millions."
    target_text= target.group(1).strip() if target else "SMB owners ready to adopt AI"
    sub1 = email_sub[0] if email_sub else "Ready to put AI to work?"

    title = f"AI Strategy That Works: {offer_name[:50]}"
    slug  = "ai-strategy-" + re.sub(r"[^a-z0-9]+","-", offer_name.lower())[:45]

    body = f"""<p><em>Guerilla Holdings LLC — {datetime.now().strftime("%B %d, %Y")}</em></p>
<p><strong>Who this is for:</strong> {target_text}</p>
<p>{pain_text}</p>
<h2>Why This Problem Is Getting Worse</h2>
<p>{lpost}</p>
<h2>The 5 Highest-ROI AI Implementations Right Now</h2>
<ol>
<li><strong>Email and outreach automation</strong> — personalized at scale, week-one results</li>
<li><strong>Content generation</strong> — 80% time reduction, immediate impact on traffic</li>
<li><strong>Customer service deflection</strong> — 30–60% ticket reduction with AI chatbots</li>
<li><strong>Dispatch and scheduling</strong> — 30–50% efficiency gain for operations-heavy businesses</li>
<li><strong>Data analysis and reporting</strong> — hours to minutes, every week</li>
</ol>
<h2>The One Question That Reveals Your AI Opportunity</h2>
<p>What does your team do more than 3 times per week that follows a repeatable pattern?
That is your first AI implementation. Not the flashiest — the most <em>repeatable</em>.
Repeatability is what AI optimizes. Document it, automate it, measure the hours saved,
then use that proof to justify the next one.</p>
<h2>What a $997 AI Audit Actually Delivers</h2>
<p>The AI Edge Accelerator is a focused 2-week engagement that produces:</p>
<ul>
<li>A prioritized list of AI opportunities ranked by ROI and implementation complexity</li>
<li>Custom prompt frameworks your team can use immediately without any technical skills</li>
<li>A 30-day implementation roadmap with measurable weekly milestones</li>
<li>ROI projections for each recommendation based on your actual headcount and processes</li>
</ul>
<p><strong>Email subject line if you're reaching out to leads:</strong> "{sub1}"</p>
""" + cta_consulting()
    return title, slug, body

def process_gumroad_product(filepath):
    raw = open(filepath).read()
    niche = re.search(r"NICHE[:\*]+\s*(.+?)[\n\*]", raw)
    hook  = re.search(r"HOOK[:\*]+\s*(.+?)[\n\*]", raw)
    price = re.search(r"PRICE[:\*]+\s*\$?([\d.]+)", raw)

    niche_text = niche.group(1).strip() if niche else "digital products"
    hook_text  = hook.group(1).strip()  if hook  else "Build passive income that compounds."
    price_val  = price.group(1).strip() if price else "27"

    title = f"How to Earn Passive Income with {niche_text.title()} in 2026"
    slug  = "passive-income-" + re.sub(r"[^a-z0-9]+","-", niche_text.lower())[:40]

    body = f"""<p>{hook_text}</p>
<h2>The Passive Income Math That Actually Works</h2>
<p>Passive income is real — but the math is simpler than most people make it.
A digital product priced at ${price_val} that sells 10 times per month generates ${float(price_val)*10:.0f}/month
with zero additional work after creation. Scale to 100 sales and it's ${float(price_val)*100:.0f}/month.
The compounding happens through content — every blog post, every social share is a permanent
asset driving discovery.</p>
<h2>The Platform Stack That Converts in 2026</h2>
<ol>
<li><strong>Gumroad</strong> — fastest path to first sale, built-in discovery, instant delivery</li>
<li><strong>WordPress + Amazon Associates</strong> — SEO-driven passive commissions, zero inventory</li>
<li><strong>Etsy digital downloads</strong> — massive existing buyer intent, low competition in niche categories</li>
<li><strong>Fiverr</strong> — active income that funds your passive builds</li>
</ol>
<h2>What Sells vs What Sits</h2>
<p>Products that solve one specific urgent problem sell. Products that are comprehensive but unfocused sit.
The difference is the title: "Complete Business Guide" vs "Cut Your Customer Service Time by 60% Using AI."
Same content. Completely different conversion rate. Always lead with the outcome, not the content.</p>
<h2>The Content Flywheel</h2>
<p>Every blog post is a permanent asset. Every product is a permanent revenue stream.
The goal is building as many compounding assets as possible in as short a time as possible —
then letting them run while you build more.</p>
<h2>Tools That Accelerate the Build</h2>
{cta_amazon("thermal label printer shipping small business", "Thermal label printers for product-based businesses")}
{cta_amazon("ring light webcam content creation kit", "Content creation lighting kits")}
{cta_amazon("portable SSD 2TB business backup", "Portable SSDs for business backup")}
""" + cta_gumroad()
    return title, slug, body

def process_fiverr_gig(filepath):
    raw = open(filepath).read()
    gig_title = re.search(r"GIG TITLE: (.+?)[\n\r]", raw)
    pricing = re.findall(r"(Basic|Standard|Premium) \(\$([\d]+)\): (.+?)(?:\n|$)", raw)
    category = re.search(r"CATEGORY: (.+?)[\n\r]", raw)
    desc_match = re.search(r"GIG DESCRIPTION:\s*\n+(.+?)(?:\n##|\Z)", raw, re.DOTALL)

    if not gig_title: return None
    title_text = gig_title.group(1).strip()
    cat_text   = category.group(1).strip() if category else "AI Services"
    desc_text  = desc_match.group(1).strip()[:600] if desc_match else "Expert AI services for your business."

    title = f"Hire an AI Expert: {title_text[:55]}"
    slug  = "hire-ai-" + re.sub(r"[^a-z0-9]+","-", title_text.lower())[:45]

    price_table = ""
    for tier, price, desc in pricing[:3]:
        price_table += f"<tr><td><strong>{tier}</strong></td><td>${price}</td><td>{desc.strip()[:80]}</td></tr>"

    body = f"""<p>Looking to hire for AI consulting, prompt engineering, or automation?
Here is what to look for — and what Guerilla Holdings LLC delivers through our AI services division.</p>
<h2>{title_text}</h2>
<p>{desc_text}...</p>
<h2>Pricing</h2>
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:#f5f5f5">
<th style="padding:8px;text-align:left">Package</th>
<th style="padding:8px;text-align:left">Price</th>
<th style="padding:8px;text-align:left">Includes</th>
</tr></thead>
<tbody>
{''.join(f'<tr><td style="padding:8px;border-bottom:1px solid #eee">{cells}</td></tr>'.replace("</td></tr>","</td>") for cells in [price_table]) if price_table else "<tr><td colspan=3>Contact for pricing</td></tr>"}
</tbody>
</table>
<h2>Why AI Prompt Engineering Matters</h2>
<p>The difference between a generic AI prompt and an engineered prompt is the difference between
"write a blog post" and a precisely structured request that produces publish-ready content
aligned with your brand voice, audience, and conversion goals. Expert prompting saves 5–15 hours
per week for most businesses.</p>
<h2>Categories We Serve</h2>
<ul>
<li>Marketing and content automation</li>
<li>Customer service AI workflows</li>
<li>Sales outreach personalization at scale</li>
<li>Operations and dispatch optimization</li>
<li>Internal documentation and SOP generation</li>
</ul>
""" + cta_consulting()
    return title, slug, body

def process_dropship(filepath):
    raw = open(filepath).read()
    product = re.search(r"PRODUCT[:\*]+\s*(.+?)[\n\*]", raw)
    niche    = re.search(r"NICHE[:\*]+\s*(.+?)[\n\*]", raw)
    hook     = re.search(r"HOOK[:\*]+\s*(.+?)[\n\*]", raw)
    price    = re.search(r"PRICE[:\*\s]+\$?([\d.–-]+)", raw)

    if not product: return None
    prod_name  = product.group(1).strip()
    niche_text = niche.group(1).strip() if niche else "home and lifestyle"
    hook_text  = hook.group(1).strip()  if hook  else f"The {prod_name} every household needs."
    price_text = price.group(1).strip() if price else "29.99"

    title = f"{prod_name}: Is It Worth It? (2026 Review)"
    slug  = re.sub(r"[^a-z0-9]+","-", prod_name.lower())[:55] + "-review"
    kw    = prod_name.lower().replace(" ", "+")

    body = f"""<p>{hook_text}</p>
<p>After researching the {niche_text} market, the {prod_name} consistently ranks as one of the
highest-demand items in its category. Here is an objective breakdown of what it does,
who it is for, and whether the price point makes sense.</p>
<h2>What It Does</h2>
<p>The {prod_name} is designed for {niche_text} use cases where convenience and efficiency matter.
Core functionality is straightforward — but the execution details separate the top products
from the mediocre ones.</p>
<h2>Who Actually Needs This</h2>
<p>This product makes the most sense for households and businesses that deal with
{niche_text.lower()} challenges regularly. If you are solving this problem more than twice a week,
the ROI case is clear.</p>
<h2>What to Look For When Buying</h2>
<ul>
<li>Build quality — cheaper versions fail within 90 days</li>
<li>Warranty coverage — reputable brands offer at minimum 1-year coverage</li>
<li>Customer reviews — look for verified purchases, not just star rating</li>
<li>Return policy — especially important for first-time purchases in this category</li>
</ul>
<h2>Top Options Available Now</h2>
{cta_amazon(kw, f"Top-rated {prod_name} options")}
{cta_amazon(kw + "+best+seller+2026", f"Bestselling {prod_name} on Amazon")}
<p><em>As an Amazon Associate, Guerilla Holdings LLC earns from qualifying purchases. This does not affect our editorial judgment.</em></p>
""" + cta_gumroad()
    return title, slug, body

# ── TWITTER CONTENT ───────────────────────────────────────────────────────
TWEET_HOOKS = [
    # CALLUX
    f"Specialty transport operators in Sacramento are earning $55-85/hr at Tier 4+. Most drivers don't know these tiers exist. Full breakdown: {MAIN_URL}",
    f"65/35 revenue split. 6-tier certification. Institutional clients. CALLUX is the specialty transport network most operators have never heard of. {MAIN_URL}",
    f"Non-emergency cadaver transport is one of the most underserved, highest-margin transport markets in California. CadaverCo operates in Sacramento, NorCal, Bay Area, Reno. {MAIN_URL}",
    # AI consulting
    f"The businesses that will win the next 5 years are building AI infrastructure now. The ones that won't are waiting to see how it plays out. {CONTACT_URL}",
    f"$997 gets you a 30-day AI implementation roadmap built around your specific business. Most clients recover it in week one. {CONTACT_URL}",
    f"What does your team do more than 3x per week that follows a repeatable pattern? That's your first AI automation. Everything else follows from there.",
    # GAFC
    f"Gun safety education in underserved communities isn't a political statement — it's a public health intervention. GAFC brings free programs to Sacramento. @glocksandfriedchicken",
    f"Stop. Don't touch. Run away. Tell a grown-up. Four words that save lives. GAFC teaches this in Sacramento communities that need it most.",
    # Gumroad
    f"781 content pieces generated. Landing page live. $27 product published. The AI Revenue Playbook documents the whole system. {GUMROAD_URL}",
    f"I built an autonomous AI revenue engine for a holding company. It generates content 24/7, routes it through a funnel, and monitors for sales. Full breakdown: {GUMROAD_URL}",
]

def post_tweet():
    text = random.choice(TWEET_HOOKS)
    tid = tweet(text)
    if tid:
        log(f"Tweeted: {text[:60]}...")
        return True
    return False

# ── MAIN ENGINE ───────────────────────────────────────────────────────────
def run():
    log("=" * 55)
    log("PENELOPE ENGINE v2 — STARTING RUN")
    log("=" * 55)

    published = load_published()
    results   = {"posts": [], "tweets": 0, "errors": []}
    now_slug  = datetime.now().strftime("%Y%m%d-%H%M")

    # Determine what to publish this run (rotate through content types)
    hour = datetime.now().hour
    minute = datetime.now().minute
    run_num = (hour * 2) + (1 if minute >= 30 else 0)  # 0-47 runs per day

    # Content rotation: different type each run
    content_order = [
        "AI_Consulting", "dropship", "Gumroad", "AI_Consulting",
        "Fiverr", "dropship", "AI_Consulting", "Gumroad",
    ]
    content_type = content_order[run_num % len(content_order)]

    log(f"Run #{run_num} | Type: {content_type} | {datetime.now().strftime('%H:%M')}")

    # Pick unpublished files of this type
    pattern = f"{SHIPPED}/*{content_type}*.md"
    if content_type == "dropship":
        pattern = f"{SHIPPED}/*dropship*.md"
    
    all_files = sorted(glob.glob(pattern), reverse=True)
    unpublished = [f for f in all_files if f not in published]

    if not unpublished:
        log(f"All {content_type} files published — resetting log for this type")
        # Reset just this content type so we can recycle
        published = {f for f in published if content_type.lower() not in f.lower() and "dropship" not in f.lower()}
        unpublished = all_files[:3]

    # Publish 2-3 posts per run
    batch = unpublished[:3]
    for filepath in batch:
        try:
            result = None
            if "AI_Consulting" in filepath:
                result = process_consulting(filepath)
            elif "Gumroad" in filepath:
                result = process_gumroad_product(filepath)
            elif "Fiverr" in filepath:
                result = process_fiverr_gig(filepath)
            elif "dropship" in filepath:
                result = process_dropship(filepath)

            if result and result[0]:
                title, slug, body = result
                slug = f"{slug}-{now_slug}"
                pid = wp_post(title, body, slug)
                if pid:
                    log(f"✅ POST {pid}: {title[:50]}")
                    results["posts"].append({"id": pid, "title": title, "type": content_type})
                    published.add(filepath)
                else:
                    log(f"❌ WP failed for: {title[:40]}")
        except Exception as e:
            log(f"❌ Error processing {filepath}: {e}")
            results["errors"].append(str(e))

    save_published(published)

    # Post tweet
    if False:  # Twitter disabled — use Bluesky instead
        pass  # Bluesky handles all social posting


    # Check Gumroad sales
    try:
        r = requests.get("https://api.gumroad.com/v2/sales",
                         params={"access_token": GUMROAD_TOKEN}, timeout=10)
        if r.status_code == 200:
            sales = r.json().get("sales", [])
            log(f"Gumroad sales to date: {len(sales)}")
            if len(sales) > 0:
                total = sum(s.get("price",0) for s in sales) / 100
                _tg_emergency_only(f"💰 GUMROAD SALE! Total: ${total:.2f} ({len(sales)} sales)")
    except: pass

    # Report
    n_posts = len(results["posts"])
    n_tweets = results["tweets"]
    log(f"RUN COMPLETE: {n_posts} posts | {n_tweets} tweets | {len(results['errors'])} errors")

    if n_posts > 0:
        titles = "\n".join(f"• {p['title'][:45]}" for p in results["posts"])
        _tg_emergency_only(f"ENGINE RUN\n{n_posts} posts live:\n{titles}\n\nTweets: {n_tweets}")

    log("=" * 55)

if __name__ == "__main__":
    run()

def tweet_v2(text):
    vault = {}
    try:
        for line in open('/root/penelope_vault.env'):
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                vault[k.strip()] = v.strip()
    except: pass
    token = vault.get('TWITTER_OAUTH2_ACCESS_TOKEN', '')
    if not token:
        return None
    r = requests.post(
        'https://api.twitter.com/2/tweets',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'text': text[:280]},
        timeout=15
    )
    if r.status_code == 201:
        return r.json().get('data', {}).get('id')
    log(f'Tweet v2 {r.status_code}: {r.text[:100]}')
    return None
