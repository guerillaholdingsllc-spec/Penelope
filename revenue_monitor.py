# ── TELEGRAM GATE (prepended by Penelope self-healer) ──────────────────────
import os as _tg_os, requests as _tg_req, datetime as _tg_dt
_tg_orig_post = _tg_req.post
def _tg_gated_post(url, *a, **kw):
    if "api.telegram.org" in str(url):
        _data = str(kw.get("json", kw.get("data", ""))).lower()
        _rev = any(x in _data for x in ["revenue confirmed","sale confirmed","payment received","paid $","new sale"])
        _crit = "🚨" in str(kw.get("json",{})) and any(x in _data for x in ["system down","cannot restart","disk full","out of memory"])
        if not _rev and not _crit:
            class _FakeResp:
                status_code=200
                def json(self): return {}
            return _FakeResp()
    return _tg_orig_post(url, *a, **kw)
_tg_req.post = _tg_gated_post
# ── END GATE ───────────────────────────────────────────────────────────────

#!/usr/bin/env python3
"""Revenue monitor — checks Gumroad + Stripe hourly, logs to Notion."""
import requests, json, os
from datetime import datetime
from pathlib import Path

from telegram_gate import send_revenue

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
GUMROAD_KEY = ENV.get("GUMROAD_API_KEY", "")
STRIPE_SK = ENV.get("STRIPE_SECRET_KEY", "")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")

def get_gumroad_revenue():
    if not GUMROAD_KEY: return 0, 0
    try:
        r = requests.get("https://api.gumroad.com/v2/sales",
            headers={"Authorization": f"Bearer {GUMROAD_KEY}"}, timeout=10)
        if r.status_code == 200:
            sales = r.json().get("sales", [])
            total = sum(float(s.get("price", 0)) for s in sales) / 100
            return total, len(sales)
    except: pass
    return 0, 0

def get_stripe_revenue():
    if not STRIPE_SK: return 0, 0
    try:
        r = requests.get("https://api.stripe.com/v1/balance_transactions",
            auth=(STRIPE_SK, ""),
            params={"limit": 100, "type": "charge"},
            timeout=10)
        if r.status_code == 200:
            txns = r.json().get("data", [])
            total = sum(t.get("net", 0) for t in txns) / 100
            return total, len(txns)
    except: pass
    return 0, 0

def run():
    gumroad_rev, gumroad_sales = get_gumroad_revenue()
    stripe_rev, stripe_txns = get_stripe_revenue()
    total = gumroad_rev + stripe_rev
    
    report = {
        "ts": datetime.now().isoformat(),
        "gumroad": {"revenue": gumroad_rev, "sales": gumroad_sales},
        "stripe": {"revenue": stripe_rev, "transactions": stripe_txns},
        "total": total
    }
    
    # Save report
    Path("/root/workspace/Penelope/reports/revenue_current.json").write_text(
        json.dumps(report, indent=2))
    
    # Alert on first sale
    if total > 0:
        last_file = Path("/root/workspace/Penelope/reports/revenue_last_total.txt")
        last = float(last_file.read_text()) if last_file.exists() else 0
        if total > last:
            try:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": TELEGRAM_CHAT,
                          "text": f"💰 REVENUE UPDATE\nGumroad: ${gumroad_rev:.2f} ({gumroad_sales} sales)\nStripe: ${stripe_rev:.2f} ({stripe_txns} txns)\nTotal: ${total:.2f}"},
                    timeout=10)
            except: pass
        last_file.write_text(str(total))
    
    print(json.dumps(report))
    return report

if __name__ == "__main__":
    run()
