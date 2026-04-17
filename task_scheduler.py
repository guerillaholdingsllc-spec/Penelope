#!/usr/bin/env python3
"""
Penelope Task Scheduler + Automation Engine
Computer Use equivalent for server-side automation:
    pass
- Scheduled tasks (cron-style)
- File organization
- Daily briefings
- Client deliverable assembly
- Telegram dispatch (phone → server)

Usage:
  python3 task_scheduler.py --daemon        # Run all scheduled tasks
  python3 task_scheduler.py --run briefing  # Run specific task now
  python3 task_scheduler.py --organize /path/to/folder
  python3 task_scheduler.py --assemble-client "ClientName"
  python3 task_scheduler.py --add-task "Task description" --schedule "09:00"
"""

import os,json,time,requests,logging,argparse,shutil,glob
from pathlib import Path
from datetime import datetime,timedelta
import threading
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
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")

TASKS_FILE=Path("/root/workspace/Penelope/scheduled_tasks.json")
WORK_DIR=Path("/root/workspace")
LOG_FILE=Path("/root/workspace/Penelope/task_scheduler.log")

logging.basicConfig(level=logging.INFO,format="%(asctime)s [SCHEDULER] %(message)s",
    handlers=[logging.FileHandler(str(LOG_FILE)),logging.StreamHandler()])
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


def gemini(prompt):
    if not GOOGLE_API_KEY:return "Gemini not configured"
    m=genai.GenerativeModel("gemini-2.5-flash")
    return m.generate_content(prompt).text

# ── DEFAULT SCHEDULED TASKS ───────────────────────────────────
DEFAULT_TASKS=[
    {"id":"daily_briefing","name":"Daily Crypto Briefing","schedule":"08:00",
     "command":"python3 /root/workspace/Penelope/crypto_trading_agent.py --briefing",
     "enabled":True,"last_run":None,"description":"Morning crypto + DEVVE briefing"},
    {"id":"devve_monitor","name":"DEVVE Price Monitor","schedule":"12:00",
     "command":"python3 /root/workspace/Penelope/crypto_trading_agent.py --monitor-devve",
     "enabled":True,"last_run":None,"description":"Midday DEVVE check"},
    {"id":"marketing_tasks","name":"Execute Marketing Tasks","schedule":"09:30",
     "command":"python3 /root/workspace/Penelope/marketing_team.py --task-board",
     "enabled":True,"last_run":None,"description":"Auto-execute pending marketing tasks"},
    {"id":"weekly_research","name":"Weekly ClickBank Research","schedule":"MON-08:00",
     "command":"python3 /root/workspace/Penelope/clickbank_agent.py",
     "enabled":True,"last_run":None,"description":"Weekly affiliate research"},
    {"id":"file_organize","name":"Organize Output Files","schedule":"18:00",
     "command":"ORGANIZE:/root/workspace/Penelope",
     "enabled":True,"last_run":None,"description":"Daily file organization"},
    {"id":"service_health","name":"Service Health Check","schedule":"*/30",
     "command":"HEALTH_CHECK",
     "enabled":True,"last_run":None,"description":"Check all Penelope services every 30min"}
]

def load_tasks():
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    TASKS_FILE.write_text(json.dumps(DEFAULT_TASKS,indent=2))
    return DEFAULT_TASKS

def save_tasks(tasks):
    TASKS_FILE.write_text(json.dumps(tasks,indent=2))

# ── FILE ORGANIZATION ─────────────────────────────────────────
def organize_folder(folder_path):
    """Organize files in a folder by type and date."""
    folder=Path(folder_path)
    if not folder.exists():
        log.error(f"Folder not found: {folder_path}")
        return

    log.info(f"Organizing: {folder_path}")
    _tg_emergency_only(f"🗂️ *Organizing Files*\n{folder_path}")

    categories={
        "reports":["_report_","_briefing_","_analysis_"],
        "content":["_blog_","_social_","_email_","_ad_","_carousel_"],
        "marketing":["marketing_","campaign_","_listing_"],
        "crypto":["devve_","_btc_","crypto_","briefing_"],
        "notion":["notion_","_notion"],
        "cinematic":["cinematic_","_brand_card"],
        "stitch":["stitch_","_preview_"],
        "leads":["lead_","leads_"],
        "research":["research_","clickbank_"]
    }

    moved=0
    for file in folder.glob("*.*"):
        if file.is_dir():continue
        category="misc"
        fname=file.name.lower()
        for cat,patterns in categories.items():
            if any(p in fname for p in patterns):
                category=cat;break
        dest=folder/category
        dest.mkdir(exist_ok=True)
        if file.parent!=dest:
            shutil.move(str(file),str(dest/file.name))
            moved+=1

    _tg_emergency_only(f"✅ *Organization Complete*\n{moved} files organized in {folder_path}")
    log.info(f"Organized {moved} files in {folder_path}")

# ── CLIENT DELIVERABLE ASSEMBLY ────────────────────────────────
def assemble_client_deliverables(client_name,source_dir=None):
    """Assemble all deliverables for a client into one folder."""
    ts=datetime.now().strftime("%Y%m%d")
    delivery_dir=WORK_DIR/f"deliverables/{client_name}_{ts}"
    delivery_dir.mkdir(parents=True,exist_ok=True)

    log.info(f"Assembling deliverables for: {client_name}")
    _tg_emergency_only(f"📦 *Assembling Deliverables*\nClient: {client_name}")

    # Search all output directories for client-related files
    search_dirs=[
        WORK_DIR/"Penelope/marketing_output",
        WORK_DIR/"Penelope/notion_output",
        WORK_DIR/"Penelope/stitch_output",
        WORK_DIR/"Penelope/cinematic_output",
        WORK_DIR/"Penelope/carousel_output"
    ]

    assembled=[]
    for search_dir in search_dirs:
        if not search_dir.exists():continue
        for file in search_dir.glob("*.*"):
            if client_name.lower() in file.name.lower():
                shutil.copy2(str(file),str(delivery_dir/file.name))
                assembled.append(file.name)

    # Generate delivery summary
    summary_prompt=f"""Generate a professional client delivery summary for {client_name}.

Deliverables assembled:
    pass
{chr(10).join(['- '+f for f in assembled]) if assembled else 'Custom deliverable package'}

Date: {datetime.now().strftime('%B %d, %Y')}

Write a brief 3-paragraph delivery email from Guerilla Holdings to the client:
    pass
1. What was delivered and why it matters
2. How to use each deliverable
3. Next steps and CTA

Keep it professional but not corporate."""

    summary=gemini(summary_prompt)
    summary_file=delivery_dir/"DELIVERY_SUMMARY.md"
    summary_file.write_text(f"# Deliverables for {client_name}\n**Date:** {datetime.now()}\n\n{summary}\n\n## Files\n"+"\n".join([f"- {f}" for f in assembled]))

    _tg_emergency_only(f"✅ *Deliverables Ready*\nClient: {client_name}\nFiles: {len(assembled)}\nLocation: `{delivery_dir}`")
    log.info(f"Assembled {len(assembled)} files for {client_name}")
    return delivery_dir

# ── SERVICE HEALTH CHECK ───────────────────────────────────────
def check_services():
    """Check all Penelope services are running."""
    services={
        "penelope-api":5001,"guerilla-data":5010,"penelope-chat":5011,
        "penelope-stitch":9001,"penelope-notion":9002,"penelope-carousel":9003,
        "penelope-preview":9000
    }
    down=[]
    for svc,port in services.items():
        try:
            r=requests.get(f"http://localhost:{port}",timeout=3)
            if r.status_code>=500:down.append(f"{svc}(error)")
        except:down.append(svc)

    if down:
        _tg_emergency_only(f"⚠️ *Service Alert*\nDown services: {', '.join(down)}\nRestarting...")
        import subprocess
        for svc in down:
            try:subprocess.run(["systemctl","restart",svc],timeout=10)
            except:pass

# ── TELEGRAM DISPATCH HANDLER ─────────────────────────────────
def handle_dispatch_command(text):
    """Handle commands sent via Telegram (phone → server)."""
    text_lower=text.lower()

    if "briefing" in text_lower or "brief" in text_lower:
        import subprocess
        subprocess.Popen(["/root/penelope_env/bin/python3",
            "/root/workspace/Penelope/crypto_trading_agent.py","--briefing"])
        return "Generating daily briefing... Check Telegram in 30s 📊"

    elif "devve" in text_lower:
        import subprocess
        subprocess.Popen(["/root/penelope_env/bin/python3",
            "/root/workspace/Penelope/crypto_trading_agent.py","--monitor-devve"])
        return "Running DEVVE analysis... 💎"

    elif "marketing" in text_lower or "task" in text_lower:
        import subprocess
        subprocess.Popen(["/root/penelope_env/bin/python3",
            "/root/workspace/Penelope/marketing_team.py","--task-board"])
        return "Executing marketing tasks... 🤖"

    elif "status" in text_lower or "services" in text_lower:
        check_services()
        return "Service health check running... ✅"

    elif "organize" in text_lower:
        organize_folder("/root/workspace/Penelope")
        return "Organizing Penelope files... 🗂️"

    elif "price" in text_lower:
        import subprocess
        tokens=text_lower.split()
        symbol="BTC"
        for t in tokens:
            if t.upper() in ["BTC","ETH","SOL","DEVVE","BNB","XRP"]:symbol=t.upper();break
        subprocess.Popen(["/root/penelope_env/bin/python3",
            "/root/workspace/Penelope/crypto_trading_agent.py","--price",symbol])
        return f"Fetching {symbol} price... 💰"

    else:
        # General AI response
        response=gemini(f"""You are Penelope, Sydney's AI revenue engine for Guerilla Holdings.
Sydney sent this via Telegram from her phone: "{text}"

Respond helpfully and tell her what you can do. Available commands:
    pass
- "briefing" — daily crypto briefing
- "devve" — DEVVE price analysis
- "marketing tasks" — execute pending tasks
- "status" — check all services
- "price BTC/ETH/etc" — get crypto price
- "organize" — organize files""")
        return response[:500]

# ── TASK RUNNER ────────────────────────────────────────────────
def run_task(task_id):
    """Run a specific scheduled task."""
    tasks=load_tasks()
    task=next((t for t in tasks if t["id"]==task_id),None)
    if not task:
        log.error(f"Task not found: {task_id}")
        return

    log.info(f"Running task: {task['name']}")
    cmd=task["command"]

    if cmd=="HEALTH_CHECK":
        check_services()
    elif cmd.startswith("ORGANIZE:"):
        organize_folder(cmd.split(":",1)[1])
    else:
        import subprocess
        result=subprocess.run(cmd.split(),capture_output=True,text=True,timeout=300)
        if result.returncode!=0:log.error(f"Task failed: {result.stderr[:200]}")

    # Update last run
    for t in tasks:
        if t["id"]==task_id:t["last_run"]=datetime.now().isoformat()
    save_tasks(tasks)

# ── DAEMON MODE ────────────────────────────────────────────────
def run_daemon():
    """Run as daemon, executing scheduled tasks."""
    log.info("Penelope Task Scheduler DAEMON starting...")
    _tg_emergency_only("⏰ *Task Scheduler Started*\nMonitoring all scheduled tasks...")

    while True:
        now=datetime.now()
        current_time=now.strftime("%H:%M")
        tasks=load_tasks()

        for task in tasks:
            if not task.get("enabled"):continue
            schedule=task.get("schedule","")

            # Every 30 min tasks
            if schedule=="*/30" and now.minute%30==0:
                threading.Thread(target=run_task,args=(task["id"],),daemon=True).start()

            # Daily time-based tasks
            elif ":" in schedule and "-" not in schedule:
                if schedule==current_time:
                    last=task.get("last_run","")
                    if last[:10]!=now.strftime("%Y-%m-%d"):  # hasn't run today
                        threading.Thread(target=run_task,args=(task["id"],),daemon=True).start()

        time.sleep(60)  # Check every minute

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Penelope Task Scheduler")
    p.add_argument("--daemon",action="store_true",help="Run as background daemon")
    p.add_argument("--run",help="Run specific task by ID now")
    p.add_argument("--organize",help="Organize files in folder")
    p.add_argument("--assemble-client",help="Assemble client deliverables")
    p.add_argument("--dispatch",help="Handle a dispatch command from phone")
    p.add_argument("--list",action="store_true",help="List all scheduled tasks")
    p.add_argument("--health",action="store_true",help="Check service health")
    a=p.parse_args()

    if a.daemon:run_daemon()
    elif a.run:run_task(a.run)
    elif a.organize:organize_folder(a.organize)
    elif a.assemble_client:assemble_client_deliverables(a.assemble_client)
    elif a.dispatch:print(handle_dispatch_command(a.dispatch))
    elif a.health:check_services()
    elif a.list:
        tasks=load_tasks()
        for t in tasks:print(f"{'✅' if t['enabled'] else '⏸️'} [{t['schedule']}] {t['name']}: {t['description']}")
    else:
        print("""Penelope Task Scheduler + Automation

  --daemon                          # Run all scheduled tasks (background)
  --run daily_briefing              # Run specific task now
  --run devve_monitor
  --organize /root/workspace/Penelope
  --assemble-client "ClientName"
  --dispatch "check my devve price" # Phone → server command
  --health                          # Service health check
  --list                            # Show all scheduled tasks""")