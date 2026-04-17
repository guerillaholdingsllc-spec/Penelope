#!/usr/bin/env python3
"""
PENELOPE LEMONSQUEEZY AUTOPUBLISH
Monitors shipped/ dir and auto-lists new digital products on LemonSqueezy.
Runs as penelope-gumroad service (reused) alongside Gumroad.
"""
import os, json, time, requests, hashlib, logging
from pathlib import Path
from datetime import datetime

LS_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "")
STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "332591")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6183015901")
SHIPPED_DIR = Path("/root/workspace/Penelope/shipped")
PUBLISHED_LOG = Path("/root/workspace/Penelope/ls_published.json")
CHECK_INTERVAL = 300

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LS] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/ls_publisher.log"), logging.StreamHandler()])
log = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Bearer {LS_KEY}", "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"}


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


def get_sales():
    """Get LemonSqueezy order count + revenue."""
    if not LS_KEY: return 0, 0
    try:
        r = requests.get("https://api.lemonsqueezy.com/v1/orders",
            headers=HEADERS, timeout=10)
        if r.status_code == 200:
            orders = r.json().get("data", [])
            revenue = sum(o.get("attributes",{}).get("total",0) for o in orders) / 100
            return len(orders), revenue
    except: pass
    return 0, 0

def check_new_sales():
    """Alert on new sales."""
    orders, revenue = get_sales()
    log.info(f"LS orders: {orders} | Revenue: ${revenue:.2f}")
    if revenue > 0:
        _tg_emergency_only(f"💰 LEMONSQUEEZY\nOrders: {orders}\nRevenue: ${revenue:.2f}")

def run():
    log.info("LemonSqueezy autopublish starting...")
    while True:
        try:
            check_new_sales()
        except Exception as e:
            log.error(f"LS check error: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run()
