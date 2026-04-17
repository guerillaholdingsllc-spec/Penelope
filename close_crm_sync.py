#!/usr/bin/env python3
"""Close CRM Sync — syncs leads from Penelope to Close CRM. Uses JSON state file."""
import json, requests, logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CRM] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/conductor_logs/close_crm_sync.log"),
              logging.StreamHandler()])
log = logging.getLogger("crm")

def load_vault():
    env = {}
    try:
        with open("/root/penelope_vault.env") as f:
            for l in f:
                if "=" in l and not l.startswith("#"):
                    k, v = l.strip().split("=", 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
CLOSE_KEY = ENV.get("CLOSE_API_KEY", "")
STATE_FILE = Path("/root/workspace/Penelope/conductor_logs/crm_sync_state.json")

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"synced_leads": [], "last_sync": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_close_leads():
    if not CLOSE_KEY: return []
    r = requests.get("https://api.close.com/api/v1/lead/?_limit=10",
        auth=(CLOSE_KEY, ""), timeout=10)
    if r.status_code == 200:
        return r.json().get("data", [])
    return []

def create_close_lead(name, email, source):
    if not CLOSE_KEY: return None
    r = requests.post("https://api.close.com/api/v1/lead/",
        auth=(CLOSE_KEY, ""),
        json={"name": name, "contacts": [{"name": name, "emails": [{"email": email}]}],
              "custom": {"source": source}},
        timeout=10)
    return r.json() if r.status_code in [200, 201] else None

def sync_leads():
    state = load_state()
    synced = 0
    
    # Get unsynced leads from email queue
    eq_path = Path("/root/workspace/Penelope/leads/email_queue.jsonl")
    if eq_path.exists():
        for line in eq_path.read_text().strip().split("\n"):
            if not line.strip(): continue
            try:
                lead = json.loads(line)
                email = lead.get("email", "")
                if not email or email in state.get("synced_leads", []):
                    continue
                name = lead.get("name", email.split("@")[0])
                result = create_close_lead(name, email, lead.get("source", "penelope"))
                if result:
                    state["synced_leads"].append(email)
                    synced += 1
                    log.info(f"Synced to Close: {email}")
            except: pass
    
    state["last_sync"] = datetime.now().isoformat()
    save_state(state)
    
    leads = get_close_leads()
    log.info(f"Sync complete: {synced} new leads | Close CRM total: {len(leads)}")
    return synced

if __name__ == "__main__":
    sync_leads()
