#!/usr/bin/env python3
"""
Penelope AI Marketing Team
5 specialized agents, 12 skills, CLAUDE.md routing
Agents: Content Creator, Data Analyst, Market Researcher,
        Creative Designer, Campaign Strategist

Usage:
  python3 marketing_team.py --agent content --task "Write blog post about CadaverCo compliance"
  python3 marketing_team.py --agent researcher --task "Research funeral home AI automation market"
  python3 marketing_team.py --agent strategist --task "Campaign for CALLUX Q2 driver recruitment"
  python3 marketing_team.py --campaign "Full marketing package for CALLUX launch"
  python3 marketing_team.py --task-board  # Check Notion-style task queue
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


def run_agent(agent_id,task,skill=None):
    """Run a specific agent on a task."""
    agent=AGENTS.get(agent_id,AGENTS["content"])
    skill_info=SKILLS.get(skill,"") if skill else ""

    log.info(f"Running {agent['name']}: {task[:60]}")
    _tg_emergency_only(f"🤖 *{agent['name']}*\nTask: {task[:80]}...")

    m=genai.GenerativeModel("gemini-2.5-flash")
    prompt=f"""{agent['prompt_prefix']}

YOUR TASK:
    pass
{task}

{f"SKILL TO USE: {skill}" if skill else ""}
{f"OUTPUT FORMAT: {skill_info.get('format','')}" if skill_info else ""}

Execute this task completely. Produce high-quality, ready-to-use output.
Do not summarize what you're about to do — just do it."""

    result=m.generate_content(prompt).text

    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_task=task[:30].lower().replace(" ","_").replace("/","")
    out_file=OUTPUT_DIR/f"{agent_id}_{safe_task}_{ts}.md"
    out_file.write_text(f"# {agent['name']}\n**Task:** {task}\n**Date:** {datetime.now()}\n\n---\n\n{result}")

    _tg_emergency_only(f"✅ *{agent['name']} Complete*\n\n{result[:1200]}\n\nFile: `{out_file.name}`")
    log.info(f"Output: {out_file}")
    return result,out_file

def run_full_campaign(campaign_brief):
    """Orchestrate all 5 agents on a complex campaign task."""
    log.info(f"Running full campaign: {campaign_brief[:60]}")
    _tg_emergency_only(f"🚀 *AI Marketing Team — Full Campaign*\n{campaign_brief[:100]}\n\nOrchestrating 5 agents...")

    results={}

    # Step 1: Market Research
    _tg_emergency_only("🔍 Step 1/5: Market Research...")
    r1,f1=run_agent("researcher",f"Research the market for this campaign: {campaign_brief}")
    results["research"]=(r1,f1)
    time.sleep(3)

    # Step 2: Campaign Strategy
    _tg_emergency_only("📋 Step 2/5: Campaign Strategy...")
    r2,f2=run_agent("strategist",
        f"Build full campaign strategy for: {campaign_brief}\nBased on research: {r1[:500]}")
    results["strategy"]=(r2,f2)
    time.sleep(3)

    # Step 3: Content
    _tg_emergency_only("✍️ Step 3/5: Content Creation...")
    r3,f3=run_agent("content",
        f"Create content package for: {campaign_brief}\nStrategy: {r2[:300]}","social_post")
    results["content"]=(r3,f3)
    time.sleep(3)

    # Step 4: Ad Copy
    _tg_emergency_only("📢 Step 4/5: Ad Copy...")
    r4,f4=run_agent("content",f"Write ad copy for: {campaign_brief}","ad_copy")
    results["ads"]=(r4,f4)
    time.sleep(3)

    # Step 5: Landing Page
    _tg_emergency_only("🏠 Step 5/5: Landing Page...")
    r5,f5=run_agent("designer",f"Create landing page copy for: {campaign_brief}","landing_page_copy")
    results["landing_page"]=(r5,f5)

    summary=f"""✅ *Full Campaign Package Complete!*

📋 Campaign: {campaign_brief[:60]}
📁 5 deliverables created:
    pass
• Market Research: `{f1.name}`
• Campaign Strategy: `{f2.name}`
• Social Content: `{f3.name}`
• Ad Copy: `{f4.name}`
• Landing Page: `{f5.name}`

All files in: `/root/workspace/Penelope/marketing_output/`"""

    _tg_emergency_only(summary)
    return results

def check_task_board():
    """Check marketing task queue and execute pending tasks."""
    if not TASKS_FILE.exists():
        sample_tasks=[
            {"id":1,"title":"Write blog about CadaverCo compliance","agent":"content","skill":"blog_writer","priority":"high","status":"todo"},
            {"id":2,"title":"Research competitor funeral transport companies","agent":"researcher","skill":"market_research","priority":"medium","status":"todo"},
            {"id":3,"title":"Campaign strategy for CALLUX driver recruitment Q2","agent":"strategist","skill":"campaign_strategy","priority":"high","status":"todo"}
        ]
        TASKS_FILE.write_text(json.dumps(sample_tasks,indent=2))
        _tg_emergency_only("📋 *Task Board Created*\nSample tasks added. Edit: `/root/workspace/Penelope/marketing_tasks.json`")
        return

    tasks=json.loads(TASKS_FILE.read_text())
    pending=[t for t in tasks if t.get("status")=="todo"]

    if not pending:
        _tg_emergency_only("✅ All marketing tasks complete!")
        return

    # Sort by priority
    priority_order={"high":0,"medium":1,"low":2}
    pending.sort(key=lambda x:priority_order.get(x.get("priority","medium"),1))

    _tg_emergency_only(f"📋 *Task Board — {len(pending)} Pending*\nExecuting by priority...")

    for task in pending[:3]:  # Execute top 3
        result,f=run_agent(task.get("agent","content"),task["title"],task.get("skill"))
        task["status"]="complete"
        task["output_file"]=str(f)
        task["completed_at"]=datetime.now().isoformat()

    TASKS_FILE.write_text(json.dumps(tasks,indent=2))
    _tg_emergency_only("✅ Task board updated — check marketing_output/")

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Penelope AI Marketing Team")
    p.add_argument("--agent",choices=["content","analyst","researcher","designer","strategist"])
    p.add_argument("--task",help="Task for the agent",default="")
    p.add_argument("--skill",help="Specific skill to use",default=None)
    p.add_argument("--campaign",help="Full campaign brief (uses all 5 agents)")
    p.add_argument("--task-board",action="store_true",help="Check and execute task board")
    p.add_argument("--list-agents",action="store_true")
    a=p.parse_args()

    if a.list_agents:
        for k,v in AGENTS.items():print(f"  {k}: {v['name']} — {v['role']}")
    elif a.campaign:run_full_campaign(a.campaign)
    elif a.task_board:check_task_board()
    elif a.agent and a.task:run_agent(a.agent,a.task,a.skill)
    else:
        # Default: autonomous run — execute pending task board + generate one campaign per venture
        print("Marketing Team: autonomous run starting...")
        check_task_board()
        for campaign in [
            "Generate this week's social content for CALLUX gig transport marketplace",
            "Create GAFC gun safety education content for Instagram and Twitter",
            "Write CadaverCo professional outreach content for funeral home directors",
        ]:
            try:
                run_full_campaign(campaign)
            except Exception as e:
                print(f"Campaign failed: {e}")
        print("Marketing Team: autonomous run complete")