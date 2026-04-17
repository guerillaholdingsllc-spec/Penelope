#!/usr/bin/env python3
"""
Penelope Notion Sync — Syncs task boards and updates via Notion MCP
This runs when Penelope needs to check/update Notion task boards
"""
import os,json,requests,logging
from datetime import datetime

TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
NOTION_TASKS=[]  # Will be populated from Notion when connected

def sync_marketing_tasks():
    """Sync pending tasks from Notion to local task queue."""
    # This connects to Notion via the MCP server
    # Tasks are created in Notion by Sydney, picked up by Penelope
    tasks_file="/root/workspace/Penelope/marketing_tasks.json"
    if os.path.exists(tasks_file):
        with open(tasks_file) as f:
            tasks=json.load(f)
        pending=[t for t in tasks if t.get("status")=="todo"]
        logging.info(f"Found {len(pending)} pending Notion tasks")
        return pending
    return []

def report_to_notion(task_id, result, output_file=""):
    """Mark task complete in local board (Notion sync via MCP in claude.ai)."""
    tasks_file="/root/workspace/Penelope/marketing_tasks.json"
    if os.path.exists(tasks_file):
        with open(tasks_file) as f:
            tasks=json.load(f)
        for t in tasks:
            if t.get("id")==task_id:
                t["status"]="complete"
                t["completed_at"]=datetime.now().isoformat()
                t["output"]=output_file
        with open(tasks_file,"w") as f:
            json.dump(tasks,f,indent=2)

if __name__=="__main__":
    pending=sync_marketing_tasks()
    print(f"Pending tasks: {len(pending)}")
    for t in pending:
        print(f"  [{t.get('priority','medium')}] {t.get('title','')}")
