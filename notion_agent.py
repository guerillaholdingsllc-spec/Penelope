#!/usr/bin/env python3
"""
Penelope Notion Template Agent
Research trending Notion templates → generate Notion AI prompts →
create preview HTML → write Etsy/Gumroad listings → auto-publish

Usage:
  python3 notion_agent.py --research --count 10
  python3 notion_agent.py --niche "budget tracker" --price 27
  python3 notion_agent.py --batch 5
  python3 notion_agent.py --list
"""

import os,json,time,requests,logging,argparse
from pathlib import Path
from datetime import datetime
from google import genai

def _get_gemini_client():
    """Lazy Gemini client — loads key from vault at call time."""
    import os as _o
    key = _o.getenv("GOOGLE_API_KEY", "")
    if not key:
        try:
            for line in open("/root/penelope_vault.env"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip()
                    break
        except: pass
    if not key:
        return None
    from google import genai as _g
    return _g.Client(api_key=key)


GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY","")
GUMROAD_KEY=os.getenv("GUMROAD_API_KEY","2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
FIRECRAWL_KEY=os.getenv("FIRECRAWL_KEY","")

OUTPUT_DIR=Path("/root/workspace/Penelope/notion_output")
PROJECTS_LOG=Path("/root/workspace/Penelope/notion_projects.json")
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

logging.basicConfig(level=logging.INFO,format="%(asctime)s [NOTION] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/notion_agent.log"),logging.StreamHandler()])
log=logging.getLogger(__name__)

if GOOGLE_API_KEY:
    pass

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


def gemini(prompt,model="gemini-2.5-flash"):
    m=genai.GenerativeModel(model)
    return m.generate_content(prompt).text

def clean_json(t):
    t=t.strip()
    if "```json" in t:t=t.split("```json")[1].split("```")[0].strip()
    elif "```" in t:t=t.split("```")[1].split("```")[0].strip()
    return t

def clean_html(t):
    t=t.strip()
    if "```html" in t:t=t.split("```html")[1].split("```")[0].strip()
    elif "```" in t:t=t.split("```")[1].split("```")[0].strip()
    return t

# ── STEP 1: RESEARCH trending Notion templates ───────────────

def research_trending_templates(count=10):
    """Find trending Notion template niches with revenue data."""
    log.info(f"Researching {count} trending Notion template niches...")
    _tg_emergency_only(f"🔍 *Notion Research Agent*\nFinding {count} trending template niches with revenue potential...")

    prompt=f"""You are an Etsy and Gumroad market researcher specializing in Notion templates.

Find {count} trending Notion template niches that are:
    pass
1. Currently selling well on Etsy and Gumroad
2. Have proven demand (people pay $17-$79 for them)
3. Can be built entirely in Notion without coding
4. Solve a specific pain point for a clear audience

For each provide:
    pass
- niche: template category name
- target_audience: who buys this
- pain_point: what problem it solves
- estimated_price: realistic Etsy price $17-$79
- estimated_monthly_revenue: what top sellers make
- competition_level: low/medium/high
- key_features: 5 features the template must have
- etsy_keywords: 5 SEO keywords for Etsy listing
- why_buy: emotional reason someone purchases this

Known high-performers to include if relevant:
    pass
- Finance/budget trackers ($21K/month proven)
- Second brain / PKM templates ($500K total proven)
- Life planner 2026
- Student planner / study tracker
- Business CRM tracker
- Content creator planner
- Habit tracker
- Project management board
- Wedding planner
- Meal planner / grocery tracker

Return ONLY valid JSON:
    pass
{{"templates":[{{"niche":"","target_audience":"","pain_point":"","estimated_price":27,"estimated_monthly_revenue":"","competition_level":"","key_features":[],"etsy_keywords":[],"why_buy":""}}]}}"""

    result=gemini(prompt)
    try:
        data=json.loads(clean_json(result))
        templates=data.get("templates",[])
        research_file=OUTPUT_DIR/f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        research_file.write_text(json.dumps(data,indent=2))
        summary="\n".join([f"• *{t['niche']}* — ${t['estimated_price']} — {t['target_audience']}" for t in templates[:6]])
        _tg_emergency_only(f"✅ *Research Complete — {len(templates)} niches found*\n\n{summary}\n\nRun with --niche to build any of these!")
        log.info(f"Research saved: {research_file}")
        return templates
    except Exception as e:
        log.error(f"Research error: {e}")
        return []

# ── STEP 2: GENERATE Notion AI prompt ────────────────────────

def generate_notion_prompt(niche,features=None,price=27,audience=""):
    """Generate the exact prompt to paste into Notion AI to build the template."""
    log.info(f"Generating Notion AI prompt for: {niche}")

    features_str=", ".join(features) if features else f"all core features for a {niche}"

    prompt=f"""You are a Notion expert and digital product creator. Create a detailed, copy-paste-ready prompt for Notion AI to build a premium {niche} template.

Target audience: {audience or f"people who need a {niche}"}
Price point: ${price} (premium quality required)
Key features needed: {features_str}

The prompt must instruct Notion AI to:
    pass
1. Use emojis on every heading for visual appeal
2. Include progress bars using Notion formulas
3. Add warning indicators (🚨) when limits are exceeded
4. Create summary dashboards with calculated totals
5. Include a transaction/entry log with database
6. Add visual charts or graphs where relevant
7. Make it beginner-friendly but look premium
8. Include instructions section for buyers
9. Use clean, consistent color coding
10. Add rollup formulas for automatic calculations

Write the FULL prompt as if you're telling Notion AI exactly what to build.
Make it detailed enough that Notion AI can build the COMPLETE template in one shot.
Include specific formula examples where needed.
This should produce something that sells for ${price} on Etsy.

Start with: "Build me a complete [niche] Notion template that..."
End with specific formula instructions."""

    notion_prompt=gemini(prompt)
    return notion_prompt.strip()

# ── STEP 3: GENERATE HTML preview ────────────────────────────

def generate_preview_html(niche,notion_prompt,price,audience,features,etsy_keywords):
    """Generate a beautiful HTML preview/mockup of what the Notion template looks like."""
    log.info(f"Generating HTML preview for: {niche}")

    features_list=features[:6] if features else [f"Feature {i}" for i in range(1,7)]
    keywords=etsy_keywords[:5] if etsy_keywords else [niche,"notion template","digital planner"]

    prompt=f"""Build a COMPLETE, realistic HTML mockup/preview of a Notion template for "{niche}".

This is a DEMO/PREVIEW page that shows what the template looks like — like a product screenshot.

Requirements:
    pass
- Mimic Notion's actual UI style (white/light background, clean sans-serif, sidebar nav)
- Show realistic data and content for "{niche}"
- Include: header with emoji, navigation sidebar, main content area
- Show at least 2-3 key sections of the template
- Include progress bars (CSS-based), tables with data, summary cards
- Use Notion's actual color scheme: white bg, light gray borders, black text
- Show formula results (like running totals, percentages)
- Include the warning emoji (🚨) example when over budget/limit
- Look like a real premium Notion template worth ${price}
- Target audience: {audience}
- Key features shown: {', '.join(features_list)}
- Mobile responsive

CRITICAL: This must look like an actual Notion workspace screenshot.
Use Notion's Inter font, clean minimal design, and realistic template data.

Return ONLY complete HTML starting with <!DOCTYPE html>."""

    html=gemini(prompt)
    return clean_html(html)

# ── STEP 4: GENERATE Etsy/Gumroad listing ───────────────────

def generate_listing(niche,price,audience,pain_point,features,etsy_keywords,why_buy):
    """Generate complete Etsy and Gumroad listing copy."""
    log.info(f"Generating listing copy for: {niche}")

    prompt=f"""You are an expert Etsy seller specializing in Notion templates. Write complete listing copy.

Product: {niche} Notion Template
Price: ${price}
Target audience: {audience}
Pain point solved: {pain_point}
Key features: {', '.join(features[:6]) if features else 'core features'}
Why they buy: {why_buy}
SEO keywords: {', '.join(etsy_keywords[:5]) if etsy_keywords else niche}

Write:
    pass

1. ETSY TITLE (max 140 chars, include top keywords):
    pass

2. ETSY DESCRIPTION (400-600 words, conversational, include all keywords naturally, bullet points for features, include social proof language, end with clear CTA):
    pass

3. ETSY TAGS (13 tags, comma separated, mix of exact and broad):
    pass

4. GUMROAD DESCRIPTION (shorter, 150-200 words, punchy, conversion-focused):
    pass

5. PINTEREST CAPTION (for mockup pin, 150 chars, include keywords):
    pass

6. INSTAGRAM CAPTION (for mockup post, with hashtags):
    pass

Format clearly with numbered sections."""

    listing=gemini(prompt)

    # Parse sections
    sections={}
    current=""
    lines=listing.split('\n')
    for line in lines:
        if line.strip().startswith('1.'):current='etsy_title'
        elif line.strip().startswith('2.'):current='etsy_description'
        elif line.strip().startswith('3.'):current='etsy_tags'
        elif line.strip().startswith('4.'):current='gumroad_description'
        elif line.strip().startswith('5.'):current='pinterest_caption'
        elif line.strip().startswith('6.'):current='instagram_caption'
        elif current:sections[current]=sections.get(current,'')+line+'\n'

    return listing,sections

# ── STEP 5: PUBLISH to Gumroad ───────────────────────────────

def publish_to_gumroad(niche,price,description,preview_html_path):
    """Auto-publish the template to Gumroad."""
    if not GUMROAD_KEY:
        log.warning("No GUMROAD_API_KEY found")
        return None

    log.info(f"Publishing to Gumroad: {niche}")

    # Create product
    try:
        r=requests.post("https://api.gumroad.com/v2/products",
            data={
                "access_token":GUMROAD_KEY,
                "name":f"Ultimate {niche} — Notion Template",
                "price":int(price*100),
                "description":description[:2000],
                "published":False,  # draft first for review
                "tags":"notion,template,digital,planner,productivity"
            },timeout=30)
        data=r.json()
        if data.get("success"):
            product=data.get("product",{})
            product_id=product.get("id","")
            product_url=product.get("short_url","")
            log.info(f"Published to Gumroad: {product_url}")
            return {"id":product_id,"url":product_url,"status":"draft"}
        else:
            log.error(f"Gumroad error: {data.get('message','unknown')}")
    except Exception as e:
        log.error(f"Gumroad publish error: {e}")
    return None

# ── MAIN ORCHESTRATOR ────────────────────────────────────────

def run_notion_agent(niche,price=27,audience="",batch=False):
    """Build a complete Notion template product."""
    _tg_emergency_only(f"📋 *Notion Template Agent*\nBuilding: {niche} (${price})")

    # Research this specific niche if no audience
    if not audience:
        research_prompt=f"""For a Notion template called "{niche}", define:
            pass
target_audience, pain_point, key_features (list of 6), etsy_keywords (list of 5), why_buy
Return ONLY JSON: {{"target_audience":"","pain_point":"","key_features":[],"etsy_keywords":[],"why_buy":""}}"""
        try:
            niche_data=json.loads(clean_json(gemini(research_prompt)))
            audience=niche_data.get("target_audience","professionals and students")
            pain_point=niche_data.get("pain_point",f"Struggling to manage their {niche}")
            features=niche_data.get("key_features",[])
            etsy_keywords=niche_data.get("etsy_keywords",[])
            why_buy=niche_data.get("why_buy","")
        except:
            audience="productivity-focused professionals"
            pain_point=f"No organized system for {niche}"
            features=[f"Core {niche} tracking","Progress visualization","Summary dashboard","Transaction log","Auto-calculations","Beginner-friendly setup"]
            etsy_keywords=[niche,"notion template","digital planner","productivity","tracker"]
            why_buy="Save time and stay organized"
            niche_data={}
    else:
        pain_point=f"No organized system for {niche}"
        features=[f"Core {niche} tracking","Progress visualization","Summary dashboard","Transaction log","Auto-calculations","Beginner-friendly setup"]
        etsy_keywords=[niche,"notion template","digital planner","productivity","tracker"]
        why_buy="Save time and stay organized"

    # Step 1: Generate Notion AI prompt
    notion_prompt=generate_notion_prompt(niche,features,price,audience)
    prompt_file=OUTPUT_DIR/f"{niche.lower().replace(' ','_')}_notion_prompt.txt"
    prompt_file.write_text(notion_prompt)
    log.info(f"Notion prompt saved: {prompt_file}")

    # Step 2: Generate HTML preview
    preview_html=generate_preview_html(niche,notion_prompt,price,audience,features,etsy_keywords)
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    safe=niche.lower().replace(' ','_').replace('/','_')
    preview_path=OUTPUT_DIR/f"{safe}_{ts}_preview.html"
    preview_path.write_text(preview_html)
    log.info(f"Preview saved: {preview_path}")

    # Step 3: Generate listing copy
    listing_full,listing_sections=generate_listing(niche,price,audience,pain_point,features,etsy_keywords,why_buy)
    listing_file=OUTPUT_DIR/f"{safe}_{ts}_listing.txt"
    listing_file.write_text(listing_full)

    # Step 4: Publish to Gumroad (draft)
    gumroad_desc=listing_sections.get("gumroad_description","").strip() or listing_full[:500]
    gumroad_result=publish_to_gumroad(niche,price,gumroad_desc,preview_path)

    # Save project
    project={
        "niche":niche,"price":price,"audience":audience,
        "timestamp":datetime.now().isoformat(),
        "notion_prompt":str(prompt_file),
        "preview_html":str(preview_path),
        "listing_file":str(listing_file),
        "local_preview":f"http://206.81.5.241:9002/{preview_path.name}",
        "gumroad":gumroad_result
    }
    projects=[]
    if PROJECTS_LOG.exists():
        try:projects=json.loads(PROJECTS_LOG.read_text())
        except:pass
    projects.append(project)
    PROJECTS_LOG.write_text(json.dumps(projects,indent=2))

    etsy_title=listing_sections.get("etsy_title","").strip()[:80] or f"Ultimate {niche} Notion Template"
    _tg_emergency_only(
        f"✅ *Notion Template Complete!*\n\n"
        f"📋 {niche}\n"
        f"💰 Price: ${price}\n"
        f"🎯 Audience: {audience}\n\n"
        f"*Files generated:*\n"
        f"• Notion AI prompt: `{prompt_file.name}`\n"
        f"• Preview mockup: `{preview_path.name}`\n"
        f"• Etsy/Gumroad listing: `{listing_file.name}`\n"
        f"{'• Gumroad draft: '+gumroad_result['url'] if gumroad_result else '• Gumroad: add key to vault'}\n\n"
        f"*Etsy title:*\n{etsy_title}\n\n"
        f"🌐 Preview: http://206.81.5.241:9002/{preview_path.name}"
    )

    log.info(f"Complete: {niche} — http://206.81.5.241:9002/{preview_path.name}")
    return project

def run_batch(count=5):
    """Build multiple Notion templates autonomously."""
    _tg_emergency_only(f"🚀 *Notion Batch Mode*\nBuilding {count} templates autonomously...")
    templates=research_trending_templates(count)

    results=[]
    for i,t in enumerate(templates[:count]):
        log.info(f"Building {i+1}/{count}: {t['niche']}")
        _tg_emergency_only(f"⚙️ Building template {i+1}/{count}: {t['niche']}...")
        try:
            result=run_notion_agent(
                niche=t.get("niche",""),
                price=t.get("estimated_price",27),
                audience=t.get("target_audience","")
            )
            results.append(result)
            time.sleep(5)  # rate limit
        except Exception as e:
            log.error(f"Batch error on {t['niche']}: {e}")

    _tg_emergency_only(f"🎉 *Batch Complete!*\n{len(results)}/{count} templates built\nAll previews at http://206.81.5.241:9002")
    return results

# ── CLI ──────────────────────────────────────────────────────
if __name__=="__main__":
    p=argparse.ArgumentParser(description="Penelope Notion Template Agent")
    p.add_argument("--research",action="store_true",help="Research trending niches")
    p.add_argument("--count",type=int,default=10)
    p.add_argument("--niche",help="Template niche to build")
    p.add_argument("--price",type=float,default=27)
    p.add_argument("--audience",default="",help="Target audience")
    p.add_argument("--batch",type=int,help="Build N templates autonomously")
    p.add_argument("--list",action="store_true")
    a=p.parse_args()

    if a.list:
        if PROJECTS_LOG.exists():
            for x in json.loads(PROJECTS_LOG.read_text()):
                gr=x.get("gumroad",{}) or {}
                print(f"✅ {x['niche']} ${x['price']} — Preview: {x.get('local_preview','')} {'| Gumroad: '+gr.get('url','') if gr.get('url') else ''}")
        else:print("No templates built yet.")
    elif a.research:research_trending_templates(a.count)
    elif a.batch:run_batch(a.batch)
    elif a.niche:run_notion_agent(a.niche,a.price,a.audience)
    else:
        print("""Penelope Notion Template Agent

Examples:
  # Research trending niches:
      pass
  python3 notion_agent.py --research --count 10

  # Build specific template:
      pass
  python3 notion_agent.py --niche "monthly budget tracker" --price 27
  python3 notion_agent.py --niche "student study planner" --price 17
  python3 notion_agent.py --niche "second brain PKM system" --price 49

  # Build 5 templates autonomously:
      pass
  python3 notion_agent.py --batch 5

  # List all built:
      pass
  python3 notion_agent.py --list

Gallery: http://206.81.5.241:9002""")