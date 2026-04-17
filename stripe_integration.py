#!/usr/bin/env python3
"""
Penelope Stripe Integration
Auto-creates Stripe products and payment links for:
- Notion templates sold outside Gumroad
- Cinematic website packages
- CALLUX driver certification fees
- CadaverCo transport deposits
"""
import os,json,requests,logging
from pathlib import Path

STRIPE_KEY=os.getenv("STRIPE_SECRET_KEY","")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")


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


def create_product(name,price_cents,description="",recurring=False):
    """Create Stripe product + price + payment link."""
    if not STRIPE_KEY:
        return {"error":"No STRIPE_SECRET_KEY in vault"}
    headers={"Authorization":f"Bearer {STRIPE_KEY}"}
    # Create product
    r=requests.post("https://api.stripe.com/v1/products",
        headers=headers,data={"name":name,"description":description},timeout=15)
    product=r.json()
    product_id=product.get("id","")
    if not product_id:return {"error":product.get("error",{})}
    # Create price
    price_data={"product":product_id,"unit_amount":price_cents,"currency":"usd"}
    if recurring:price_data.update({"recurring[interval]":"month"})
    r=requests.post("https://api.stripe.com/v1/prices",headers=headers,data=price_data,timeout=15)
    price=r.json()
    price_id=price.get("id","")
    # Create payment link
    r=requests.post("https://api.stripe.com/v1/payment_links",
        headers=headers,data={"line_items[0][price]":price_id,"line_items[0][quantity]":1},timeout=15)
    link=r.json()
    return {"product_id":product_id,"price_id":price_id,"payment_link":link.get("url","")}

# Default products for Guerilla Holdings
PRODUCTS=[
    {"name":"Notion Budget Tracker Template","price":2700,"desc":"Premium Notion template for monthly budget tracking"},
    {"name":"CadaverCo Transport Quote","price":0,"desc":"Request a transport quote — we'll invoice after service"},
    {"name":"Cinematic Website — Starter","price":250000,"desc":"Basic cinematic website build"},
    {"name":"CALLUX Driver Certification — Tier 1","price":9900,"desc":"Entry level CALLUX driver certification"},
]

if __name__=="__main__":
    if not STRIPE_KEY:
        print("Add STRIPE_SECRET_KEY to /root/penelope_vault.env to enable Stripe")
        print("Get it from dashboard.stripe.com/apikeys")
    else:
        for p in PRODUCTS:
            result=create_product(p["name"],p["price"],p["desc"])
            print(f"{'✅' if result.get('payment_link') else '❌'} {p['name']}: {result.get('payment_link','error')}")
