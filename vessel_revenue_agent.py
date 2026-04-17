"""
vessel_revenue_agent.py
Vessel Revenue Intelligence Agent
Monitors Stripe for Vessel subscriptions, logs to Notion, Telegrams Sydney daily 8AM brief
"""
import os, json, requests, time
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────────────────────────
VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except Exception as e:
    print(f"Vault load error: {e}")

STRIPE_KEY      = VAULT.get("STRIPE_SECRET_KEY", "")
TELEGRAM_TOKEN  = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = VAULT.get("TELEGRAM_CHAT_ID", "6183015901")
NOTION_TOKEN    = VAULT.get("NOTION_TOKEN", "")
NOTION_OPS_DB   = "f9094ce8-4cff-40cd-9d6c-323072627263"
GOOGLE_API_KEY  = VAULT.get("GOOGLE_API_KEY", "")

VESSEL_PRODUCT_TAG = "vessel"  # Stripe metadata tag to identify Vessel subs

# ── Stripe helpers ───────────────────────────────────────────────────────
def stripe_get(endpoint, params=None):
    r = requests.get(
        f"https://api.stripe.com/v1/{endpoint}",
        auth=(STRIPE_KEY, ""),
        params=params or {},
        timeout=15
    )
    return r.json() if r.ok else {}

def get_vessel_subscriptions():
    """Pull all active Vessel subscriptions from Stripe"""
    data = stripe_get("subscriptions", {"limit": 100, "status": "active"})
    subs = data.get("data", [])
    vessel_subs = []
    for s in subs:
        meta = s.get("metadata", {})
        desc = str(s.get("description", "")).lower()
        if meta.get("product") == VESSEL_PRODUCT_TAG or "vessel" in desc:
            vessel_subs.append(s)
    return vessel_subs

def get_recent_vessel_events(hours=24):
    """Get Stripe events for Vessel in last N hours"""
    since = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    data = stripe_get("events", {
        "limit": 100,
        "created[gte]": since,
        "types[]": ["customer.subscription.created",
                    "customer.subscription.deleted",
                    "invoice.payment_succeeded"]
    })
    events = data.get("data", [])
    vessel_events = []
    for e in events:
        obj = e.get("data", {}).get("object", {})
        meta = obj.get("metadata", {})
        if meta.get("product") == VESSEL_PRODUCT_TAG or "vessel" in str(obj).lower():
            vessel_events.append(e)
    return vessel_events

def calculate_mrr(subs):
    """Calculate MRR from active subscriptions"""
    mrr = 0
    for s in subs:
        items = s.get("items", {}).get("data", [])
        for item in items:
            price = item.get("price", {})
            amount = price.get("unit_amount", 0) / 100
            interval = price.get("recurring", {}).get("interval", "month")
            if interval == "year":
                amount = amount / 12
            mrr += amount
    return round(mrr, 2)

# ── Notion logging ───────────────────────────────────────────────────────
def log_to_notion(title, content, status="info"):
    if not NOTION_TOKEN:
        return
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_OPS_DB},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": status}},
            "Date": {"date": {"start": datetime.utcnow().isoformat()}}
        },
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}
        }]
    }
    try:
        requests.post("https://api.notion.com/v1/pages",
                      headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"Notion log error: {e}")

# ── Telegram ─────────────────────────────────────────────────────────────

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


def run_revenue_brief():
    print(f"[{datetime.utcnow().isoformat()}] VesselRevenueAgent running...")

    subs      = get_vessel_subscriptions()
    events    = get_recent_vessel_events(24)
    mrr       = calculate_mrr(subs)
    total     = len(subs)

    new_subs  = [e for e in events if e.get("type") == "customer.subscription.created"]
    cancelled = [e for e in events if e.get("type") == "customer.subscription.deleted"]
    revenue   = sum(
        e.get("data", {}).get("object", {}).get("amount_paid", 0) / 100
        for e in events if e.get("type") == "invoice.payment_succeeded"
    )

    breakeven_monthly = 40.00
    breakeven_subs    = 9
    subs_to_break     = max(0, breakeven_subs - total)
    profitable        = total >= breakeven_subs

    brief = (
        f"🔮 <b>VESSEL Daily Revenue Brief</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📊 Active Subscribers: <b>{total}</b>\n"
        f"💰 MRR: <b>${mrr:.2f}</b>\n"
        f"📈 Last 24h Revenue: <b>${revenue:.2f}</b>\n"
        f"✨ New Subs (24h): <b>{len(new_subs)}</b>\n"
        f"❌ Cancelled (24h): <b>{len(cancelled)}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{'✅ PROFITABLE' if profitable else f'⚡ {subs_to_break} subs to break even'}\n"
        f"Base44 cost: $40/mo | Net: ${max(0, mrr-40):.2f}/mo\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
    )

    telegram(brief)
    log_to_notion(
        f"Vessel Revenue Brief — {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"MRR: ${mrr} | Subs: {total} | New: {len(new_subs)} | Cancelled: {len(cancelled)} | 24h Revenue: ${revenue}",
        "info"
    )

    print(f"Brief sent. MRR=${mrr} Subs={total}")
    return {"mrr": mrr, "total_subs": total, "new": len(new_subs), "cancelled": len(cancelled)}

if __name__ == "__main__":
    run_revenue_brief()
