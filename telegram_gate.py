#!/usr/bin/env python3
"""
PENELOPE TELEGRAM GATE v2 — Only two message types ever reach Sydney:
  1. REVENUE  — confirmed sale with $ amount
  2. CRITICAL — service down, self-healer failed, requires human action
All other calls are logged locally and dropped. No exceptions.
"""
import os, requests
from datetime import datetime
from pathlib import Path

_TOKEN = None
_CHAT  = "6183015901"
_LOG   = Path("/root/workspace/Penelope/conductor_logs/telegram_gate.log")
_LOG.parent.mkdir(parents=True, exist_ok=True)

def _load_token():
    global _TOKEN
    if _TOKEN: return _TOKEN
    try:
        with open("/root/penelope_vault.env") as f:
            for line in f:
                if line.startswith("TELEGRAM_GATE_TOKEN="):
                    _TOKEN = line.split("=",1)[1].strip()
                    return _TOKEN
    except: pass
    _TOKEN = os.getenv("TELEGRAM_GATE_TOKEN","")
    return _TOKEN

def _log_dropped(msg):
    try:
        _LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG,"a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M')}] DROPPED: {str(msg)[:100]}\n")
    except: pass

def _send_real(text):
    tok = _load_token()
    if not tok or tok == "DISABLED_USE_GATE_ONLY": return
    try:
        requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id":_CHAT,"text":text[:4000],"parse_mode":"Markdown"},
            timeout=8
        )
    except: pass

def send_revenue(amount, source, detail=""):
    """ONLY call when a real payment clears."""
    msg = f"\U0001f4b0 *REVENUE* ${float(amount):.2f} via {source}"
    if detail: msg += f"\n{detail}"
    _send_real(msg)

def send_critical(service, error):
    """ONLY call when service is down AND auto-fix has failed."""
    h = datetime.now().hour
    if h < 8 or h >= 22: return  # quiet hours — log only
    msg = f"\U0001f6a8 *CRITICAL* `{service}` needs manual fix\n{str(error)[:300]}"
    _send_real(msg)

# ── Everything below here = SILENT ───────────────────────────────────────────

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




def tg_critical(msg, *args, **kwargs): _log_dropped(msg)
def tg(msg, *args, **kwargs):        _log_dropped(msg)
def alert(msg, *args, **kwargs):     _log_dropped(msg)
def send(msg, *args, **kwargs):      _log_dropped(msg)
