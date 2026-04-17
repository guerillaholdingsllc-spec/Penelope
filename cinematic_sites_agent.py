#!/usr/bin/env python3
"""Penelope Cinematic Sites Agent - 4 step pipeline"""
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
WAVESPEED_API_KEY=os.getenv("WAVESPEED_API_KEY","")
FIRECRAWL_KEY=os.getenv("FIRECRAWL_KEY","")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
VERCEL_TOKEN=os.getenv("VERCEL_TOKEN","")
OUTPUT_DIR=Path("/root/workspace/Penelope/cinematic_output")
PROJECTS_LOG=Path("/root/workspace/Penelope/cinematic_projects.json")
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

logging.basicConfig(level=logging.INFO,format="%(asctime)s [CINEMATIC] %(message)s",
  handlers=[logging.FileHandler("/root/workspace/Penelope/cinematic_sites.log"),logging.StreamHandler()])
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

def analyze_brand(url=None,desc=None):
    log.info("Step 1: Brand Analysis")
    _tg_emergency_only("🎨 *Step 1: Brand Analysis*\nExtracting brand identity...")
    ctx=""
    if url:ctx+=f"Website URL: {url}\n"
    if desc:ctx+=f"Business: {desc}\n"
    if url and FIRECRAWL_KEY:
        try:
            r=requests.post("https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization":f"Bearer {FIRECRAWL_KEY}"},
                json={"url":url,"formats":["markdown"],"onlyMainContent":True},timeout=30)
            md=r.json().get("data",{}).get("markdown","")
            ctx+=f"Website content:\n{md[:3000]}\n"
        except Exception as e:log.error(f"Firecrawl: {e}")
    prompt=f"""Analyze this business and return ONLY valid JSON brand profile:
        pass
{ctx}
Return JSON:
    pass
{{"business_name":"","industry":"","tagline":"5-7 word tagline","hero_headline":"3-5 word headline",
"brand_story":"2 sentence story","products_services":[],"colors":{{"primary":"#hex","secondary":"#hex","accent":"#hex","background":"#hex"}},"fonts":{{"heading":"Google Font","body":"Google Font"}},"theme_direction":"e.g. Dark cinematic luxury","mood_words":[],"hero_concepts":[{{"id":1,"emoji":"","description":"detailed scene","animation":"how to animate"}},{{"id":2,"emoji":"","description":"","animation":""}},{{"id":3,"emoji":"","description":"","animation":""}}],"sections_needed":[]}}"""
    result=gemini(prompt)
    try:return json.loads(clean_json(result))
    except:return {"business_name":desc or "Business","industry":"Business","colors":{"primary":"#1a1a2e","secondary":"#16213e","accent":"#f5a623","background":"#0a0a14"},"fonts":{"heading":"Sora","body":"Inter"},"theme_direction":"Dark cinematic","hero_concepts":[{"id":1,"emoji":"🎬","description":f"Cinematic hero shot for {desc or 'business'}","animation":"slow zoom"}]}

def generate_brand_card(bd):
    name=bd.get("business_name","Brand")
    c=bd.get("colors",{})
    f=bd.get("fonts",{})
    p=c.get("primary","#1a1a2e");a=c.get("accent","#f5a623")
    concepts="".join([f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:16px;margin-bottom:12px;"><div style="font-size:1.5rem">{x.get("emoji","🎬")}</div><div style="color:{a};font-weight:700">Option {x.get("id",1)}</div><div style="color:#ccc;font-size:.85rem">{x.get("description","")}</div><div style="color:#888;font-size:.75rem">Animation: {x.get("animation","")}</div></div>' for x in bd.get("hero_concepts",[])])
    html=f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Brand Card - {name}</title><link href="https://fonts.googleapis.com/css2?family={f.get("heading","Sora").replace(" ","+")}:wght@700;800&family={f.get("body","Inter")}:wght@400;500&display=swap" rel="stylesheet"><style>body{{font-family:"{f.get("body","Inter")}",sans-serif;background:#0a0a14;color:#e0e0f0;margin:0;padding:40px 20px}}h1{{font-family:"{f.get("heading","Sora")}",sans-serif;color:white;font-size:2.5rem}}.swatch{{border-radius:8px;padding:16px;font-size:.8rem;font-weight:700;display:inline-block;margin:6px}}</style></head><body><h1>{name}</h1><p style="color:#888">{bd.get("industry","")}</p><div style="margin:20px 0"><div class="swatch" style="background:{p};color:white">Primary {p}</div><div class="swatch" style="background:{c.get("secondary","#16213e")};color:white">Secondary</div><div class="swatch" style="background:{a};color:#000">Accent {a}</div></div><div style="padding:20px;background:rgba(255,255,255,.04);border-radius:10px;margin:20px 0"><div style="font-family:{f.get("heading","Sora")};font-size:2rem;color:{a}">{bd.get("hero_headline","Headline")}</div><p style="color:#ccc">{bd.get("brand_story","")}</p></div><div style="border-left:3px solid {a};padding:16px;margin:20px 0;background:rgba(255,255,255,.03)"><div style="color:{a};font-size:1.2rem;font-weight:700">"{bd.get("tagline","Tagline")}"</div><div style="color:#888">{bd.get("theme_direction","")}</div></div><h3 style="color:#888;font-size:.8rem;text-transform:uppercase;letter-spacing:2px">Hero Scene Concepts</h3>{concepts}</body></html>'
    p2=OUTPUT_DIR/f"{name.lower().replace(' ','_')}_brand_card.html"
    p2.write_text(html)
    return p2

def generate_image(prompt,bd):
    if not WAVESPEED_API_KEY:return None
    c=bd.get("colors",{})
    ep=f"{prompt}, {bd.get('theme_direction','cinematic')}, color palette {c.get('primary','')} and {c.get('accent','')}, professional photography, 8K, cinematic lighting"
    try:
        r=requests.post("https://api.wavespeed.ai/api/v3/google/nano-banana-2/text-to-image",
            headers={"Authorization":f"Bearer {WAVESPEED_API_KEY}","Content-Type":"application/json"},
            json={"prompt":ep,"size":"1920x1080","num_images":2},timeout=60)
        d=r.json()
        if d.get("id"):return poll_wavespeed(d["id"])
        outputs=d.get("data",{}).get("outputs",[])
        return [o.get("url") for o in outputs if o.get("url")]
    except Exception as e:log.error(f"Image gen: {e}");return None

def generate_video(img_url,anim,bd):
    if not WAVESPEED_API_KEY:return None
    try:
        r=requests.post("https://api.wavespeed.ai/api/v3/kwaivgi/kling-v3.0-pro/image-to-video",
            headers={"Authorization":f"Bearer {WAVESPEED_API_KEY}","Content-Type":"application/json"},
            json={"image":img_url,"prompt":f"{anim}, cinematic, smooth camera movement, professional","duration":5,"aspect_ratio":"16:9"},timeout=30)
        d=r.json()
        if d.get("id"):return poll_wavespeed(d["id"])
        return d.get("data",{}).get("url")
    except Exception as e:log.error(f"Video gen: {e}");return None

def poll_wavespeed(task_id,max_wait=300):
    start=time.time()
    while time.time()-start<max_wait:
        try:
            r=requests.get(f"https://api.wavespeed.ai/api/v3/predictions/{task_id}",
                headers={"Authorization":f"Bearer {WAVESPEED_API_KEY}"},timeout=15)
            d=r.json();status=d.get("status","")
            if status=="succeeded":
                outputs=d.get("data",{}).get("outputs",[])
                if outputs:return [o.get("url") for o in outputs if o.get("url")]
                return d.get("data",{}).get("url")
            elif status=="failed":log.error("WaveSpeed failed");return None
            log.info(f"Polling: {status}");time.sleep(10)
        except Exception as e:log.error(f"Poll: {e}");time.sleep(5)
    return None

def download_asset(url,fname):
    try:
        r=requests.get(url,timeout=60)
        p=OUTPUT_DIR/fname;p.write_bytes(r.content);return p
    except Exception as e:log.error(f"Download: {e}");return None

def build_website(bd,video_path=None):
    log.info("Step 3: Building website")
    _tg_emergency_only("🏗️ *Step 3: Building Cinematic Website*...")
    name=bd.get("business_name","Business")
    c=bd.get("colors",{});f=bd.get("fonts",{})
    video_js=""
    if video_path:
        video_js=f"""<video id="heroVid" src="{video_path}" muted playsinline preload="auto" style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;opacity:.6;z-index:0"></video>
<script>const v=document.getElementById('heroVid');v.pause();window.addEventListener('scroll',()=>{{if(v.duration)v.currentTime=(window.scrollY/(document.body.scrollHeight-window.innerHeight))*v.duration;}},{{passive:true}});</script>"""
    sections=bd.get("sections_needed",["Hero","Story","Products","Contact"])
    products=bd.get("products_services",[])
    prompt=f"""Build a COMPLETE, single-file cinematic HTML website. Return ONLY HTML starting with <!DOCTYPE html>.

Business: {name}
Industry: {bd.get('industry','')}
Tagline: {bd.get('tagline','')}
Hero Headline: {bd.get('hero_headline','')}
Brand Story: {bd.get('brand_story','')}
Products/Services: {', '.join(products[:5])}
Theme: {bd.get('theme_direction','')}

Colors - Primary: {c.get('primary','#1a1a2e')} Secondary: {c.get('secondary','#16213e')} Accent: {c.get('accent','#f5a623')} Background: {c.get('background','#0a0a14')}
Fonts - Heading: {f.get('heading','Sora')} Body: {f.get('body','Inter')}

Sections: {', '.join(sections)}

REQUIREMENTS:
    pass
- Dark cinematic theme, premium $15K quality
- Google Fonts import only (no other external JS)
- Full viewport hero with animated text reveal
- Accordion hover-expand cards for products/menu
- IntersectionObserver scroll animations (fade up, blur reveal)
- Parallax on images
- Mobile responsive
- Professional footer
- Pure vanilla JS only
- Include placeholder content appropriate for {bd.get('industry','this business')}

Return ONLY the complete HTML, nothing else."""
    result=gemini(prompt,"gemini-2.5-flash")
    html=result.strip()
    if "```html" in html:html=html.split("```html")[1].split("```")[0].strip()
    elif "```" in html:html=html.split("```")[1].split("```")[0].strip()
    if video_path and video_js and "<video" not in html:
        html=html.replace("</body>",f"\n{video_js}\n</body>")
    safe=name.lower().replace(" ","_").replace("'","")
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    out=OUTPUT_DIR/f"{safe}_{ts}.html"
    out.write_text(html)
    log.info(f"Website: {out}")
    return out

def deploy(html_path,name):
    local=f"http://206.81.5.241:9000/{html_path.name}"
    if VERCEL_TOKEN:
        import subprocess,shutil
        safe=name.lower().replace(" ","-").replace("'","")[:30]
        d=OUTPUT_DIR/f"deploy_{safe}";d.mkdir(exist_ok=True)
        shutil.copy(html_path,d/"index.html")
        try:
            r=subprocess.run(["vercel","--yes","--name",f"guerilla-{safe}","--token",VERCEL_TOKEN,str(d)],
                capture_output=True,text=True,timeout=120)
            if r.returncode==0:
                url=r.stdout.strip().split('\n')[-1]
                return url,local
        except Exception as e:log.error(f"Vercel: {e}")
    return None,local

def run(url=None,desc=None,concept=None,auto=False):
    _tg_emergency_only(f"🎬 *Cinematic Sites Agent*\nTarget: {url or desc}\nStarting 4-step pipeline...")
    bd=analyze_brand(url=url,desc=desc)
    card=generate_brand_card(bd)
    name=bd.get("business_name","Business")
    concepts=bd.get("hero_concepts",[])
    _tg_emergency_only(f"✅ *Brand Card Ready*\n{name}\nTheme: {bd.get('theme_direction','')}\n\nConcepts:\n"+"\n".join([f"{c.get('emoji','')} Option {c.get('id',i+1)}: {c.get('description','')[:60]}" for i,c in enumerate(concepts[:3])])+f"\n\nBrand card: `{card.name}`\nReply with 1,2,3 or continue automatically.")
    if not auto and not concept:
        log.info(f"Waiting for approval. Brand card: {card}")
        return {"status":"waiting","brand_card":str(card)}
    idx=int(concept)-1 if concept else 0
    chosen=concepts[idx] if idx<len(concepts) else {"description":f"Cinematic shot of {name}","animation":"slow zoom"}
    _tg_emergency_only(f"🎨 *Step 2: Scene Generation*\n{chosen.get('emoji','')} {chosen.get('description','')[:80]}")
    imgs=None;video_path=None
    if WAVESPEED_API_KEY:
        imgs=generate_image(chosen.get("description",""),bd)
        if imgs:
            urls=imgs if isinstance(imgs,list) else [imgs]
            img_path=download_asset(urls[0],f"{name.lower().replace(' ','_')}_hero.jpg")
            _tg_emergency_only("✅ Hero image generated! Animating...")
            vid=generate_video(urls[0],chosen.get("animation","slow cinematic zoom"),bd)
            if vid:
                v=vid if isinstance(vid,str) else (vid[0] if isinstance(vid,list) and vid else None)
                if v:video_path=download_asset(v,f"{name.lower().replace(' ','_')}_hero.mp4")
    else:_tg_emergency_only("⚠️ No WAVESPEED_API_KEY — building CSS-only site. Add key for video.")
    html_path=build_website(bd,video_path=video_path)
    vercel_url,local_url=deploy(html_path,name)
    import subprocess
    try:subprocess.Popen(["python3","-m","http.server","9000","--directory",str(OUTPUT_DIR)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except:pass
    projects=[]
    if PROJECTS_LOG.exists():projects=json.loads(PROJECTS_LOG.read_text())
    projects.append({"name":name,"timestamp":datetime.now().isoformat(),"html":str(html_path),"local":local_url,"vercel":vercel_url})
    PROJECTS_LOG.write_text(json.dumps(projects,indent=2))
    _tg_emergency_only(f"🎉 *Cinematic Website Complete!*\n\n🏢 {name}\n📁 `{html_path.name}`\n🌐 Preview: {local_url}\n{'🚀 Live: '+vercel_url if vercel_url else '⚡ Add VERCEL_TOKEN to auto-deploy'}\n\n💰 This is a $15K cinematic website!")
    return {"name":name,"html":str(html_path),"local":local_url,"vercel":vercel_url}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--url",help="Website URL to rebuild")
    p.add_argument("--business",help="Business description")
    p.add_argument("--concept",help="Hero concept 1,2,3")
    p.add_argument("--auto",action="store_true")
    p.add_argument("--list",action="store_true")
    a=p.parse_args()
    if a.list:
        if PROJECTS_LOG.exists():
            [print(f"✅ {x['name']} — {x.get('local','')}") for x in json.loads(PROJECTS_LOG.read_text())]
        else:print("No projects yet.")
    elif a.url or a.business:
        run(url=a.url,desc=a.business,concept=a.concept,auto=a.auto)
    else:
        print("Usage:\n  python3 cinematic_sites_agent.py --url https://example.com --auto\n  python3 cinematic_sites_agent.py --business 'Pizza shop NYC' --auto")