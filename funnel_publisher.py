#!/usr/bin/env python3
import os, re, glob, subprocess, json, requests
from datetime import datetime

TELEGRAM = os.environ.get("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","")
SHIPPED = "/root/workspace/Penelope/shipped"
LOG = "/root/workspace/Penelope/funnel_published.json"
GUMROAD_URL = "https://guerillaholdings.gumroad.com/l/vniej"
CONTACT_URL = "https://trustchainservices.com/#contact"
MAIN_URL = "https://trustchainservices.com"


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


def load_log():
    try: return json.load(open(LOG))
    except: return []

def wp_post(title, content, slug):
    r = subprocess.run(
        ["docker","exec","-i","penelope-wordpress","bash","-c",
         "cat > /tmp/fp.html && php wp-cli.phar post create "
         "--post_title='{}' --post_name='{}' "
         "--post_status=publish --post_content-file=/tmp/fp.html "
         "--allow-root 2>&1".format(
             title.replace("'","\'"), slug[:60]
         )
        ],
        input=content, capture_output=True, text=True
    )
    out = r.stdout + r.stderr
    m = re.search(r"Created post (\d+)", out)
    return int(m.group(1)) if m else None

def cta(ctype):
    if ctype == "consulting":
        return (
            "<hr><h3>Ready to Put AI to Work in Your Business?</h3>"
            "<p>The <b>AI Edge Accelerator</b> maps your highest-leverage AI opportunities "
            "and delivers an actionable 30-day roadmap. $997 flat, no retainer. "
            "Most clients recover the investment within the first month.</p>"
            f'<p><a href="{CONTACT_URL}" style="background:#0a0a0a;color:#c8f400;'
            'padding:12px 24px;text-decoration:none;border-radius:3px;'
            'font-weight:bold;display:inline-block">Book Free Discovery Call</a></p>'
        )
    elif ctype == "gumroad":
        return (
            "<hr><h3>Get the Complete AI Revenue Playbook — $27</h3>"
            "<p>The full Guerilla Holdings operating system: AI agent architecture, "
            "specialty transport ops, social enterprise launch kit, Shopify CRO sprint, "
            "and passive income channel setup. Instant digital download.</p>"
            f'<p><a href="{GUMROAD_URL}" style="background:#0a0a0a;color:#c8f400;'
            'padding:12px 24px;text-decoration:none;border-radius:3px;'
            'font-weight:bold;display:inline-block">Download Now for $27</a></p>'
        )
    else:
        return f'<hr><p><a href="{MAIN_URL}">TrustChain Services</a> — Sacramento, CA</p>'

def make_consulting_post(filepath):
    raw = open(filepath).read()
    linkedin = re.search(r"LinkedIn Post[:\*]+\n+(.+?)(?:\n---)", raw, re.DOTALL)
    offer = re.search(r"OFFER NAME[:\*]+\s*(.+?)\n", raw)
    pain = re.search(r"PAIN POINT[:\*]+\s*(.+?)\n", raw)
    if not linkedin:
        return None, None, None
    lpost = linkedin.group(1).strip()
    offer_name = offer.group(1).strip() if offer else "AI Consulting"
    pain_text = pain.group(1).strip() if pain else "Operational costs are rising and AI adoption is accelerating."
    
    title = f"AI for Business Operators: {offer_name[:45]}"
    slug = "ai-business-" + re.sub("[^a-z0-9]+", "-", offer_name.lower())[:40]
    
    body = (
        f"<p><em>{datetime.now().strftime('%B %d, %Y')} — Guerilla Holdings LLC</em></p>"
        f"<p>{pain_text}</p>"
        f"<h2>The Opportunity Most Businesses Are Missing</h2>"
        f"<p>{lpost}</p>"
        "<h2>Where AI Delivers the Fastest ROI</h2>"
        "<p>After working with businesses across manufacturing, transport, and services, "
        "these are the highest-leverage AI applications in order of ROI speed:</p>"
        "<ol>"
        "<li><b>Customer-facing copy and content</b> — 80% time reduction, immediate</li>"
        "<li><b>Email sequences and outreach</b> — personalization at scale, week one</li>"
        "<li><b>Internal documentation and SOPs</b> — onboarding and training, month one</li>"
        "<li><b>Dispatch and scheduling</b> — 30-50% efficiency gain for operations</li>"
        "<li><b>Data analysis and reporting</b> — hours to minutes, ongoing</li>"
        "</ol>"
        "<h2>The One Question That Determines ROI</h2>"
        "<p>What task does your team do more than 3 times per week that follows a repeatable pattern? "
        "That is your first AI implementation. Not the flashiest, not the most complex — "
        "the most <em>repeatable</em>. Repeatability is what AI optimizes.</p>"
        "<p>Once you implement that one, document the time saved. That documentation "
        "is your business case for every implementation that follows.</p>"
    ) + cta("consulting")
    
    return title, slug, body

def make_gumroad_post(filepath):
    raw = open(filepath).read()
    product = re.search(r"(?:PRODUCT NAME|PRODUCT TITLE)[:\*]+\s*(.+?)\n", raw)
    niche = re.search(r"NICHE[:\*]+\s*(.+?)\n", raw)
    hook_m = re.search(r"HOOK[:\*]+\s*(.+?)\n", raw)
    
    niche_text = niche.group(1).strip() if niche else "digital products"
    hook_text = hook_m.group(1).strip() if hook_m else "Build revenue streams that compound over time."
    
    title = f"How to Make Money with {niche_text.title()} in 2026 (Real Numbers)"
    slug = "make-money-" + re.sub("[^a-z0-9]+","-", niche_text.lower())[:40]
    
    body = (
        f"<p>{hook_text}</p>"
        "<h2>The Real Numbers on Digital Product Revenue</h2>"
        "<p>Digital products have zero marginal cost after creation. "
        "Every sale after your initial investment is pure margin. "
        "Here is what realistic performance looks like:</p>"
        "<ul>"
        "<li><b>Month 1:</b> Product creation + first sales (goal: cover creation cost)</li>"
        "<li><b>Month 2-3:</b> SEO and social content driving organic discovery</li>"
        "<li><b>Month 4+:</b> Compounding — each new content piece adds to a growing traffic base</li>"
        "</ul>"
        "<h2>What Sells vs What Sits</h2>"
        "<p>Products that solve a specific, urgent problem sell. "
        "Products that are comprehensive but unfocused sit. "
        "The difference is the title: 'Complete Business Guide' vs "
        "'How to Cut Your Customer Service Time by 60% Using AI.' "
        "Same content, completely different conversion rate.</p>"
        "<h2>The Platform Decision</h2>"
        "<p>Gumroad for first launch — lowest friction, built-in discovery. "
        "Once you have social proof (reviews, sales count), expand to other platforms. "
        "Never launch everywhere simultaneously — diluted traffic doesn't build momentum anywhere.</p>"
        "<h2>Content That Converts to Sales</h2>"
        "<p>Every blog post, every tweet, every Reddit comment should answer a question "
        "your buyer is actively searching for. Then end with: "
        "'I built a complete system for this. It's $27.'</p>"
    ) + cta("gumroad")
    
    return title, slug, body

# Execute
published = load_log()
results = []

consulting_files = sorted(glob.glob(f"{SHIPPED}/*AI_Consulting*.md"), reverse=True)
for f in consulting_files[:3]:
    if f in published: continue
    t, s, b = make_consulting_post(f)
    if t:
        pid = wp_post(t, b, s)
        if pid:
            print(f"CONSULTING POST {pid}: {t[:55]}")
            results.append(t)
            published.append(f)

gumroad_files = sorted(glob.glob(f"{SHIPPED}/*Gumroad*.md"), reverse=True)
for f in gumroad_files[:2]:
    if f in published: continue
    t, s, b = make_gumroad_post(f)
    if t:
        pid = wp_post(t, b, s)
        if pid:
            print(f"GUMROAD POST {pid}: {t[:55]}")
            results.append(t)
            published.append(f)

json.dump(published, open(LOG,"w"))

if results:
    _tg_emergency_only(f"FUNNEL LIVE\n{len(results)} new posts:\n" + "\n".join(f"• {r[:50]}" for r in results))
print(f"Complete: {len(results)} posts published.")
