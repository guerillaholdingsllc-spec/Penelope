
import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import keys_manager,superman_protocol,mc_client,tasks,groq_client

def boot(send_telegram_fn=None):
    print("Penelope autonomous systems booting...")
    for k,v in keys_manager.load().items():
        if v and k not in os.environ: os.environ[k]=v
    superman_protocol.start(send_fn=send_telegram_fn)
    mc_client.log("Penelope booted. Superman Protocol active.",topic="business",important=True)
    print("Penelope online")

def handle_message(text,send_fn=None):
    t=text.lower().strip()
    if any(w in t for w in ["revenue","how much","pipeline","earnings"]):
        rev=mc_client.get_revenue(); earned=rev.get("total_earned",0); goal=rev.get("monthly_goal",10000)
        pending=mc_client.get_pending_approvals()
        return f"Revenue: ${earned:,} / ${goal:,} ({round(earned/goal*100) if goal else 0}%)\nPipeline: ${rev.get('pipeline_value',0):,}\nPending approvals: {len(pending)}"
    if any(w in t for w in ["morning","briefing","good morning"]): return tasks.morning_briefing(None)
    if any(w in t for w in ["find leads","lead gen","funeral","mortuary","scrape"]):
        city="Sacramento"
        for c in ["sacramento","fresno","oakland","reno","san jose","bakersfield"]:
            if c in t: city=c.title()
        r=tasks.callux_lead_gen(city)
        if r.get("error"): return f"Lead gen error: {r['error']}"
        if r.get("skipped"): return "Already ran today. Check Approvals inbox."
        return f"CALLUX Lead Gen: {r.get('count',0)} leads in {r.get('city')}. Outreach queued for approval."
    if any(w in t for w in ["superman","protocol","status","autonomous"]):
        s=superman_protocol.get_status()
        last="\n".join([f"- {a['time']} {a['action']}" for a in s.get("last_actions",[])])
        return f"Superman Protocol\nRunning: {s['running']}\nCycles: {s['cycles']}\nLast actions:\n{last or 'None yet'}"
    if any(w in t for w in ["what should","next action","recommend","what now"]):
        rev=mc_client.get_revenue(); gap=rev.get("monthly_goal",10000)-rev.get("total_earned",0)
        return groq_client.complete("You are Penelope. One specific direct recommendation.",f"Revenue gap: ${gap:,}. Single highest-leverage action right now. Name it, tool to use, expected outcome. 3 sentences max.")
    return None
