#!/usr/bin/env python3
"""
PENELOPE WATCHDOG
Self-healing service monitor. Restarts crashed services automatically.
Runs every 15 minutes via cron.
"""
import subprocess, requests, json
from datetime import datetime
from pathlib import Path

CRITICAL_SERVICES = [
    "penelope-conductor",
    "penelope-commander", 
    "lead-capture",
    "penelope-army",
    "penelope-handoff",
    "penelope-webhooks",
]

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT = "6183015901"

def load_vault():
    env = {}
    try:
        with open("/root/penelope_vault.env") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")


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


def is_active(service):
    r = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True)
    return r.stdout.strip() == "active"

def restart_service(service):
    r = subprocess.run(["systemctl", "restart", service], capture_output=True, text=True)
    return r.returncode == 0

def run_watchdog():
    restarted = []
    failed = []
    
    for service in CRITICAL_SERVICES:
        if not is_active(service):
            print(f"Service down: {service} — attempting restart...")
            success = restart_service(service)
            if success:
                import time; time.sleep(2)
                if is_active(service):
                    restarted.append(service)
                    print(f"Restarted: {service}")
                else:
                    failed.append(service)
                    print(f"Restart failed: {service}")
            else:
                failed.append(service)
    
    # Log watchdog run
    log_path = Path("/root/workspace/Penelope/conductor_logs/watchdog.log")
    with open(log_path, "a") as f:
        f.write(f"{datetime.now().isoformat()} | restarted: {restarted} | failed: {failed}\n")
    
    # Alert Sydney only if something was restarted or failed
    if restarted:
        telegram(f"Auto-restarted: {", ".join(restarted)}")
    if failed:
        telegram(f"CRITICAL — Failed to restart: {", ".join(failed)}\nManual intervention needed.")
    
    return restarted, failed

if __name__ == "__main__":
    restarted, failed = run_watchdog()
    print(f"Watchdog complete | Restarted: {restarted} | Failed: {failed}")
