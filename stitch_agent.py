#!/usr/bin/env python3
"""
Penelope Stitch Agent
Google Stitch equivalent — scrape any web app, redesign it with Gemini,
build a functional prototype, deploy it.

Usage:
  python3 stitch_agent.py --url https://example.com --prompt "Redesign for 2026, niche for Amazon sellers"
  python3 stitch_agent.py --idea "Import duty calculator for ecommerce" --niche "Amazon/eBay/Shopify sellers"
  python3 stitch_agent.py --research "ecommerce" --count 10
  python3 stitch_agent.py --list
"""

import os,json,time,requests,logging,argparse,base64
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
FIRECRAWL_KEY=os.getenv("FIRECRAWL_KEY","")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
VERCEL_TOKEN=os.getenv("VERCEL_TOKEN","")
OUTPUT_DIR=Path("/root/workspace/Penelope/stitch_output")
PROJECTS_LOG=Path("/root/workspace/Penelope/stitch_projects.json")
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

logging.basicConfig(level=logging.INFO,format="%(asctime)s [STITCH] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/stitch_agent.log"),logging.StreamHandler()])
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


def gemini_text(prompt,model="gemini-2.5-flash"):
    m=genai.GenerativeModel(model)
    return m.generate_content(prompt).text

def gemini_vision(prompt,image_path=None,image_url=None,model="gemini-2.5-flash"):
    """Analyze image with Gemini vision."""
    m=genai.GenerativeModel(model)
    parts=[prompt]
    if image_path and Path(image_path).exists():
        import PIL.Image
        img=PIL.Image.open(image_path)
        parts.append(img)
    elif image_url:
        r=requests.get(image_url,timeout=30)
        import PIL.Image
        from io import BytesIO
        img=PIL.Image.open(BytesIO(r.content))
        parts.append(img)
    return m.generate_content(parts).text

def clean_html(t):
    t=t.strip()
    if "```html" in t:t=t.split("```html")[1].split("```")[0].strip()
    elif "```" in t:t=t.split("```")[1].split("```")[0].strip()
    return t

def clean_json(t):
    t=t.strip()
    if "```json" in t:t=t.split("```json")[1].split("```")[0].strip()
    elif "```" in t:t=t.split("```")[1].split("```")[0].strip()
    return t

# ── STEP 1: RESEARCH — Find apps due for redesign ────────────────────────────

def research_app_ideas(niche,count=10):
    """Find existing web apps in a niche that are due for redesign."""
    log.info(f"Researching app ideas in: {niche}")
    _tg_emergency_only(f"🔍 *Stitch Agent: Research Mode*\nFinding {count} web apps in '{niche}' due for redesign...")

    prompt=f"""You are a digital product strategist. Find {count} real web apps/tools in the '{niche}' niche 
that exist today but have outdated designs and could benefit from a 2026 redesign.

For each provide:
    pass
- name: app name
- url: actual URL
- what_it_does: 1 sentence description
- why_redesign: why it needs updating
- monetization: how it could make money
- niche_angle: how to niche it down for a specific audience

Focus on: calculators, tools, dashboards, marketplaces, lookup tools, converters.
These should be REAL existing tools with functional value but poor UI.

Return ONLY valid JSON:
    pass
{{"apps":[{{"name":"","url":"","what_it_does":"","why_redesign":"","monetization":"","niche_angle":""}}]}}"""

    result=gemini_text(prompt)
    try:
        data=json.loads(clean_json(result))
        apps=data.get("apps",[])
        summary="\n".join([f"• *{a['name']}*: {a['what_it_does'][:60]}\n  URL: {a.get('url','')}" for a in apps[:5]])
        _tg_emergency_only(f"✅ *Research Complete — {len(apps)} apps found*\n\n{summary}\n\nTop picks saved to stitch_research.json")
        research_file=OUTPUT_DIR/f"research_{niche.lower().replace(' ','_')}.json"
        research_file.write_text(json.dumps(data,indent=2))
        log.info(f"Research saved: {research_file}")
        return apps
    except Exception as e:
        log.error(f"Research parse error: {e}")
        _tg_emergency_only(f"❌ Research error: {e}")
        return []

# ── STEP 2: SCRAPE & ANALYZE existing app ───────────────────────────────────

def scrape_existing_app(url):
    """Scrape an existing web app to understand its structure and design."""
    log.info(f"Scraping: {url}")
    content=""
    screenshot_path=None

    if FIRECRAWL_KEY:
        try:
            r=requests.post("https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization":f"Bearer {FIRECRAWL_KEY}"},
                json={"url":url,"formats":["markdown","screenshot"],"onlyMainContent":True},timeout=30)
            data=r.json().get("data",{})
            content=data.get("markdown","")[:4000]
            screenshot_b64=data.get("screenshot","")
            if screenshot_b64:
                ss_path=OUTPUT_DIR/f"screenshot_{int(time.time())}.png"
                ss_path.write_bytes(base64.b64decode(screenshot_b64))
                screenshot_path=ss_path
                log.info(f"Screenshot saved: {ss_path}")
        except Exception as e:
            log.error(f"Firecrawl error: {e}")

    # Fallback: basic requests scrape
    if not content:
        try:
            r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
            from html.parser import HTMLParser
            class P(HTMLParser):
                def __init__(self):self.text=[]
                def handle_data(self,d):self.text.append(d)
            p=P();p.feed(r.text)
            content=" ".join(p.text)[:4000]
        except Exception as e:
            log.error(f"Scrape fallback error: {e}")
            content=f"App at {url}"

    return content,screenshot_path

def analyze_existing_app(url=None,content="",screenshot_path=None,niche_prompt=""):
    """Analyze the existing app and create a redesign brief."""
    log.info("Analyzing existing app...")

    if screenshot_path and Path(screenshot_path).exists():
        analysis=gemini_vision(
            f"""Analyze this web app screenshot. Identify:
                pass
1. What the app does
2. Current design problems (outdated UI, poor UX, etc.)
3. Color scheme and typography
4. Key features and sections
5. Target audience
{f"Niche context: {niche_prompt}" if niche_prompt else ""}

Be specific and detailed. This will be used to redesign the app.""",
            image_path=str(screenshot_path)
        )
    else:
        analysis=gemini_text(f"""Analyze this web app content from {url or 'unknown URL'}:
            pass

{content[:3000]}

Identify:
    pass
1. What the app does and its core functionality
2. Current design issues
3. Key features and sections
4. Target audience
5. How to niche it down: {niche_prompt or 'general audience'}

Be specific about what needs redesigning.""")

    log.info(f"Analysis complete: {analysis[:200]}")
    return analysis

# ── STEP 3: GENERATE new design ──────────────────────────────────────────────

def generate_app_design(analysis,prompt,niche="",app_type="web_app"):
    """Generate a complete functional web app design."""
    log.info("Generating app design...")
    _tg_emergency_only("🎨 *Step 2: Generating 2026 Design*\nBuilding functional prototype...")

    prompt_full=f"""You are a world-class UI/UX designer and developer. Build a COMPLETE, functional web app.

EXISTING APP ANALYSIS:
    pass
{analysis}

REDESIGN REQUIREMENTS:
    pass
{prompt}
{f"Target niche: {niche}" if niche else ""}

BUILD REQUIREMENTS:
    pass
1. Complete single-file HTML — fully functional, not just a mockup
2. 2026 modern design: dark/glass theme, smooth animations, professional
3. All interactive elements must ACTUALLY WORK with JavaScript
4. If it's a calculator/tool — implement the actual calculation logic
5. Mobile responsive
6. Include ALL sections: hero, main tool/functionality, how it works, features, CTA
7. Use CSS variables for theming
8. Smooth scroll animations with IntersectionObserver
9. Professional typography with Google Fonts
10. NO external JS libraries — pure vanilla JS only

FUNCTIONAL REQUIREMENTS:
    pass
- If it's a calculator: implement real formulas
- If it's a lookup tool: implement search/filter logic  
- If it's a dashboard: implement dynamic charts using Canvas API
- If it's a form tool: implement validation and results display
- Make it genuinely useful, not just pretty

COLOR SCHEME: Dark premium — deep navy/slate backgrounds, vibrant accent (pick one: #6366f1, #10b981, #f59e0b, #ef4444, #06b6d4 based on niche)

Return ONLY complete HTML starting with <!DOCTYPE html>. No explanation."""

    result=gemini_text(prompt_full,"gemini-2.5-flash")
    html=clean_html(result)

    if not html.startswith("<!DOCTYPE") and not html.startswith("<html"):
        log.warning("HTML not clean, retrying...")
        result=gemini_text(f"Return ONLY the HTML code for this app, starting with <!DOCTYPE html>:\n\n{result[:500]}\n\nProvide the full functional implementation.")
        html=clean_html(result)

    return html

# ── STEP 4: BUILD RESULTS PAGE ───────────────────────────────────────────────

def generate_results_page(main_html,prompt):
    """Generate a results/output page to complement the main page."""
    log.info("Generating results page...")

    result=gemini_text(f"""Based on this main web app:
        pass
{main_html[:2000]}

Build a COMPLETE results/output page that shows the calculation results or output.
Requirements:
    pass
- Match the exact same design system (colors, fonts, style)
- Show detailed results with visual breakdown
- Include charts or visual representations using Canvas API
- Back button to main page
- Download/share results functionality
- Mobile responsive

Return ONLY complete HTML starting with <!DOCTYPE html>.""")

    return clean_html(result)

# ── STEP 5: SAVE & DEPLOY ────────────────────────────────────────────────────

def save_and_deploy(main_html,results_html,app_name,url_source=""):
    """Save files and deploy."""
    log.info("Saving and deploying...")
    safe=app_name.lower().replace(" ","_").replace("'","").replace("/","_")[:40]
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save main page
    main_path=OUTPUT_DIR/f"{safe}_{ts}.html"
    main_path.write_text(main_html)

    # Save results page
    results_path=OUTPUT_DIR/f"{safe}_{ts}_results.html"
    if results_html:results_path.write_text(results_html)

    local_main=f"http://206.81.5.241:9001/{main_path.name}"
    local_results=f"http://206.81.5.241:9001/{results_path.name}" if results_html else ""

    # Deploy to Vercel if token available
    vercel_url=None
    if VERCEL_TOKEN:
        import subprocess,shutil,tempfile
        try:
            d=Path(tempfile.mkdtemp())
            shutil.copy(main_path,d/"index.html")
            if results_html:shutil.copy(results_path,d/"results.html")
            r=subprocess.run(["vercel","--yes","--name",f"guerilla-{safe[:20]}","--token",VERCEL_TOKEN,str(d)],
                capture_output=True,text=True,timeout=120)
            if r.returncode==0:
                vercel_url=r.stdout.strip().split('\n')[-1]
                log.info(f"Deployed: {vercel_url}")
        except Exception as e:log.error(f"Vercel: {e}")

    # Save project record
    projects=[]
    if PROJECTS_LOG.exists():
        try:projects=json.loads(PROJECTS_LOG.read_text())
        except:pass
    project={
        "name":app_name,"source_url":url_source,
        "timestamp":datetime.now().isoformat(),
        "main_html":str(main_path),"results_html":str(results_path),
        "local_main":local_main,"local_results":local_results,
        "vercel_url":vercel_url,"status":"complete"
    }
    projects.append(project)
    PROJECTS_LOG.write_text(json.dumps(projects,indent=2))

    return main_path,results_path,local_main,local_results,vercel_url

# ── MAIN ORCHESTRATOR ────────────────────────────────────────────────────────

def run_stitch(url=None,prompt="",idea=None,niche="",app_type="web_app"):
    """Full Stitch pipeline."""
    _tg_emergency_only(f"✂️ *Penelope Stitch Agent*\nTarget: {url or idea}\nBuilding 2026 redesign...")

    # Get source content
    content=""
    screenshot_path=None
    app_name=""

    if url:
        log.info(f"Scraping existing app: {url}")
        _tg_emergency_only(f"🔍 *Step 1: Analyzing Existing App*\n{url}")
        content,screenshot_path=scrape_existing_app(url)
        app_name=url.split("//")[-1].split("/")[0].replace("www.","").split(".")[0].title()
    elif idea:
        app_name=idea[:40]
        content=f"Building new app: {idea}"
        _tg_emergency_only(f"💡 *Step 1: New App Design*\n{idea}")

    # Analyze
    analysis=analyze_existing_app(url=url,content=content,screenshot_path=screenshot_path,niche_prompt=niche)

    # Generate design
    full_prompt=prompt or f"Complete 2026 redesign{f', niched for: {niche}' if niche else ''}"
    main_html=generate_app_design(analysis,full_prompt,niche=niche,app_type=app_type)

    # Generate results page
    results_html=None
    if any(w in (prompt+idea+analysis).lower() for w in ["calculator","tool","lookup","checker","converter","finder"]):
        results_html=generate_results_page(main_html,full_prompt)

    # Save and deploy
    main_path,results_path,local_main,local_results,vercel_url=save_and_deploy(
        main_html,results_html,app_name,url_source=url or idea)

    _tg_emergency_only(
        f"✅ *Stitch Complete — App Built!*\n\n"
        f"📱 {app_name}\n"
        f"🌐 Preview: {local_main}\n"
        f"{'📄 Results: '+local_results if local_results else ''}\n"
        f"{'🚀 Live: '+vercel_url if vercel_url else '⚡ Add VERCEL_TOKEN for live deploy'}\n\n"
        f"Files in: `/root/workspace/Penelope/stitch_output/`\n"
        f"💰 Ready to sell or launch!"
    )

    log.info(f"Complete: {app_name} — {local_main}")
    return {"name":app_name,"main":str(main_path),"local":local_main,"vercel":vercel_url}

# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Penelope Stitch Agent — Google Stitch equivalent")
    p.add_argument("--url",help="URL of existing app to redesign")
    p.add_argument("--prompt",help="Redesign instructions",default="")
    p.add_argument("--idea",help="New app idea to build from scratch")
    p.add_argument("--niche",help="Target niche e.g. 'Amazon/eBay sellers'",default="")
    p.add_argument("--research",help="Research app ideas in a niche")
    p.add_argument("--count",help="Number of ideas to research",default="10",type=int)
    p.add_argument("--list",action="store_true",help="List all built apps")
    a=p.parse_args()

    if a.list:
        if PROJECTS_LOG.exists():
            for x in json.loads(PROJECTS_LOG.read_text()):
                print(f"✅ {x['name']} — {x.get('local_main','')} {'| '+x['vercel_url'] if x.get('vercel_url') else ''}")
        else:print("No apps built yet.")
    elif a.research:
        research_app_ideas(a.research,a.count)
    elif a.url or a.idea:
        run_stitch(url=a.url,prompt=a.prompt,idea=a.idea,niche=a.niche)
    else:
        print("""Penelope Stitch Agent — Google Stitch equivalent

Examples:
  # Redesign an existing app:
      pass
  python3 stitch_agent.py --url https://www.simplyduty.com --prompt "Redesign for 2026, niche for Amazon/eBay sellers" --niche "ecommerce sellers"

  # Build new app from idea:
      pass
  python3 stitch_agent.py --idea "Import duty calculator for ecommerce" --niche "Amazon/Shopify/eBay sellers"

  # Research app ideas in a niche:
      pass
  python3 stitch_agent.py --research "ecommerce" --count 10

  # List all built apps:
      pass
  python3 stitch_agent.py --list

Preview: http://206.81.5.241:9001""")