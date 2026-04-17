
import os,json,datetime,httpx
from pathlib import Path
import groq_client,mc_client,keys_manager
PROJECTS_DIR=Path("/home/penelope/app/projects")
DEMOS_DIR=Path("/home/penelope/app/website_demos")
PROJECTS_DIR.mkdir(parents=True,exist_ok=True)
DEMOS_DIR.mkdir(parents=True,exist_ok=True)
CITIES=["Sacramento CA","Fresno CA","Oakland CA","San Jose CA","Reno NV","Bakersfield CA","Stockton CA","Modesto CA","Santa Rosa CA","Redding CA","Chico CA","Visalia CA"]
def _city(): return CITIES[datetime.date.today().timetuple().tm_yday % len(CITIES)]

def callux_lead_gen(city=None):
    city=city or _city()
    if mc_client.already_ran_today(f"callux lead gen {city.split()[0].lower()}"): return {"skipped":True,"city":city}
    apify_key=keys_manager.get("APIFY_API_KEY")
    if not apify_key: mc_client.log("CALLUX: APIFY_KEY missing",topic="callux"); return {"error":"APIFY_API_KEY missing"}
    mc_client.log(f"CALLUX lead gen: {city}",topic="callux")
    try:
        resp=httpx.post("https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items",headers={"Authorization":f"Bearer {apify_key}"},json={"searchStringsArray":[f"funeral home {city}",f"mortuary {city}"],"maxCrawledPlaces":25,"language":"en"},params={"maxItems":25},timeout=120)
        results=resp.json() if resp.status_code==200 else []
    except Exception as e: mc_client.log(f"Apify error: {e}",topic="callux"); return {"error":str(e)}
    if not results: return {"count":0,"city":city}
    for biz in results: mc_client.add_pipeline_lead(biz.get("title","Unknown"),"apify_google_maps",299)
    names=[r.get("title","") for r in results[:5]]
    outreach=groq_client.complete("You write effective B2B cold outreach. Concise. No buzzwords.",f"Write 3 outreach messages for CALLUX dispatch software. Targets: {chr(44).join(names)} in {city}. CALLUX: AI dispatch for cadaver transport. Cuts time 60%. $299/month. Write: [LinkedIn] [Email] [SMS]. Max 3 sentences each. Pain first. End with question.",max_tokens=600)
    leads="\n".join([f"- {r.get(chr(116)+chr(105)+chr(116)+chr(108)+chr(101),chr(63))} | {r.get(chr(112)+chr(104)+chr(111)+chr(110)+chr(101),chr(45))} | {r.get(chr(119)+chr(101)+chr(98)+chr(115)+chr(105)+chr(116)+chr(101),chr(45))}" for r in results[:15]])
    mc_client.queue_approval(f"CALLUX Leads {city} ({len(results)} found)","outreach",f"Scraped {len(results)} funeral homes in {city}. Outreach ready.",f"LEADS:\n{leads}\n\nOUTREACH:\n{outreach}",0,"$299/month per client")
    mc_client.log(f"CALLUX complete: {len(results)} leads in {city}",topic="callux",important=True)
    return {"count":len(results),"city":city,"queued":True}

def morning_briefing(send_fn=None):
    rev=mc_client.get_revenue(); earned=rev.get("total_earned",0); goal=rev.get("monthly_goal",10000)
    pending=mc_client.get_pending_approvals(); today=datetime.date.today().strftime("%A %B %d")
    msg=groq_client.complete("You are Penelope. Sharp data-first morning briefing.",f"Today: {today}\nRevenue: ${earned:,}/${goal:,}\nPending approvals: {len(pending)}\nToday city: {_city()}\n5 lines: 1.Revenue snapshot 2.Overnight work 3.Approvals waiting 4.Todays action 5.Flag or No blockers",max_tokens=250)
    out=f"\u2600\ufe0f Morning Briefing {today}\n\n{msg}"
    if send_fn:
        try: send_fn(out)
        except: pass
    mc_client.log(f"Briefing: {msg}",topic="business",important=True)
    return out

def evening_summary(send_fn=None):
    today=datetime.date.today().isoformat(); entries=mc_client.get_today_journal()
    text="\n".join([e.get("content","")[:200] for e in entries])
    summary=groq_client.complete("You are Penelope. Executive day-end summary.",f"Journal entries:\n{text}\n\nFormat: Completed/Revenue impact/Awaiting approval/Tomorrow. Max 8 lines.",max_tokens=300)
    mc_client.patch(f"/api/journal/{today}",{"summary":summary})
    out=f"\U0001f319 Day Complete {today}\n\n{summary}"
    if send_fn:
        try: send_fn(out)
        except: pass
    mc_client.log(f"Evening summary: {summary}",topic="business",important=True)
    return out

def app_factory_cycle():
    if mc_client.already_ran_today("app factory"): return {"skipped":True}
    if datetime.date.today().day % 3 != 0: return {"skipped":True,"reason":"Not scheduled"}
    idea=groq_client.complete_json("App store analyst. JSON only.",'{"name":"string","tagline":"string","pattern":"string","monetization":"freemium","estimated_monthly":"$300-600/mo","seo_keyword":"string"}')
    if not idea.get("name"): idea={"name":"PlantID Pro","tagline":"Identify any plant instantly","pattern":"ID App","monetization":"freemium","estimated_monthly":"$300-600/mo","seo_keyword":"plant identifier"}
    html=groq_client.complete("Build complete functional single-file HTML web apps. Return ONLY raw HTML.",f"Build: {idea['name']} - {idea['tagline']}. Pattern: {idea['pattern']}. All features working with localStorage. Premium mobile UI. Smooth animations.",max_tokens=4096)
    fpath=PROJECTS_DIR/f"{idea['name'].lower().replace(chr(32),chr(95))}.html"; fpath.write_text(html)
    mc_client.queue_approval(f"App Ready: {idea['name']}","launch",f"Built {idea['name']} ({idea['tagline']}). Est {idea.get('estimated_monthly','')}. Approve to deploy.",f"FILE: {fpath}\nRevenue: {idea.get('estimated_monthly','')}",0,idea.get("estimated_monthly","$300/mo"))
    mc_client.log(f"App Factory: {idea['name']} built",topic="business",important=True)
    return {"app":idea["name"],"file":str(fpath),"queued":True}
