#!/usr/bin/env python3
"""
PENELOPE WEBHOOK RECEIVER v1.0
Receives real-time events and triggers immediate agent actions.
Events: Stripe payments, Gumroad sales, Lead opt-ins
Port: 5060
"""
import os, json, logging, requests, hashlib, hmac
from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [WEBHOOK] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/conductor_logs/webhook.log"), logging.StreamHandler()])
log = logging.getLogger("webhook")

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
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", "")
STRIPE_WEBHOOK_SECRET = ENV.get("STRIPE_WEBHOOK_SECRET", "")
CLOSE_API_KEY = ENV.get("CLOSE_API_KEY", "")


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


def notion_log_event(event_type, details):
    if not NOTION_TOKEN: return
    try:
        requests.post("https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", 
                     "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={"parent": {"database_id": "aaac5800-d381-48c0-b135-2af97fe9d188"},
                  "properties": {"Event": {"title": [{"text": {"content": f"[WEBHOOK] {event_type}"[:100]}}]}}},
            timeout=10)
    except: pass

def trigger_post_payment_flow(customer_email, amount, product_name):
    """What happens the moment someone pays."""
    # 1. Log to Notion audience DB as converted lead
    if NOTION_TOKEN:
        try:
            requests.post("https://api.notion.com/v1/pages",
                headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                         "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
                json={"parent": {"database_id": "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"},
                      "properties": {
                          "Name": {"title": [{"text": {"content": customer_email}}]},
                          "Email": {"email": customer_email},
                          "Source": {"select": {"name": "Landing Page"}},
                          "Funnel": {"select": {"name": "Purchase"}},
                          "Converted": {"checkbox": True},
                          "Revenue Generated": {"number": amount/100},
                          "Business": {"select": {"name": "Digital Products"}},
                          "Lead Score": {"number": 90},
                      }}, timeout=10)
        except: pass
    
    # 2. Create Close CRM lead as customer
    if CLOSE_API_KEY:
        try:
            requests.post("https://api.close.com/api/v1/lead/",
                auth=(CLOSE_API_KEY, ""),
                json={"name": customer_email,
                      "contacts": [{"emails": [{"email": customer_email}]}],
                      "custom": {"Product": product_name, "Amount": f"${amount/100:.2f}", "Status": "Customer"}},
                timeout=10)
        except: pass
    
    # 3. Telegram revenue alert
    telegram(f"💰 PAYMENT RECEIVED\n\nProduct: {product_name}\nAmount: ${amount/100:.2f}\nCustomer: {customer_email}\n\nLead upgraded to Customer in Notion + Close CRM")
    
    log.info(f"Post-payment flow triggered: {customer_email} | ${amount/100:.2f}")

@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    
    try:
        data = json.loads(payload)
        event_type = data.get("type", "")
        log.info(f"Stripe event: {event_type}")
        
        if event_type == "payment_intent.succeeded":
            pi = data["data"]["object"]
            amount = pi.get("amount", 0)
            customer_email = pi.get("receipt_email") or pi.get("metadata", {}).get("email", "unknown")
            product_name = pi.get("description", "Guerilla Holdings Product")
            trigger_post_payment_flow(customer_email, amount, product_name)
        
        elif event_type == "checkout.session.completed":
            session = data["data"]["object"]
            amount = session.get("amount_total", 0)
            customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email", "unknown")
            product_name = "Digital Product"
            trigger_post_payment_flow(customer_email, amount, product_name)
        
        notion_log_event(event_type, str(data.get("data", {}))[:200])
        return jsonify({"received": True}), 200
    except Exception as e:
        log.error(f"Stripe webhook error: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/webhook/gumroad", methods=["POST"])
def gumroad_webhook():
    try:
        data = request.form.to_dict() or request.get_json(silent=True) or {}
        sale_id = data.get("sale_id", "?")
        amount = float(data.get("price", 0))
        email = data.get("email", "unknown")
        product = data.get("product_name", "Gumroad Product")
        
        log.info(f"Gumroad sale: {email} | ${amount} | {product}")
        trigger_post_payment_flow(email, int(amount*100), product)
        notion_log_event("gumroad.sale", f"Sale {sale_id}: {email} ${amount}")
        return jsonify({"received": True}), 200
    except Exception as e:
        log.error(f"Gumroad webhook error: {e}")
        return jsonify({"error": str(e)}), 400

@app.route("/webhook/lead", methods=["POST"])
def lead_webhook():
    """Real-time lead processing — fires when any landing page form submitted."""
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        email = data.get("email", "")
        name = data.get("name", "Anonymous")
        brand = data.get("brand", "digital")
        source = data.get("source", "landing_page")
        
        log.info(f"Lead webhook: {email} | {brand} | {source}")
        
        # Immediately queue welcome email
        lead_queue = Path("/root/workspace/Penelope/leads/welcome_queue.jsonl")
        with open(lead_queue, "a") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(), "email": email, 
                                "name": name, "brand": brand, "source": source}) + "\n")
        
        notion_log_event("lead.captured", f"{email} | {brand} | {source}")
        return jsonify({"queued": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/webhook/health")
def health():
    return jsonify({"status": "webhook_receiver_active", "ts": datetime.now().isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5060, debug=False)
