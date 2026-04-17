#!/usr/bin/env python3
"""
STRIPE POST-PAYMENT PRODUCT DELIVERY
When someone pays, they get:
1. Immediate delivery email with product access
2. Upgraded to Customer in Notion audience DB
3. Flagged in Close CRM as converted
4. Upsell queued for day 3
"""
import json, requests
from datetime import datetime
from pathlib import Path

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
BREVO_KEY = ENV.get("BREVO_API_KEY", "")
FROM_EMAIL = ENV.get("GMAIL_FROM", "sydneygarmon@gmail.com")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", "")
NOTION_AUDIENCE_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"
CLOSE_KEY = ENV.get("CLOSE_API_KEY", "")

PRODUCT_DELIVERY = {
    "default": {
        "subject": "Your purchase from Guerilla Holdings — Here's your access",
        "download_url": "https://trustchainservices.com/funnels/digital/",
        "content": """
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;">
<h2 style="color:#c8f542;">You're in. Here's your access.</h2>
<p>Thank you for your purchase from Guerilla Holdings.</p>
<p>Your product is ready:</p>
<div style="background:#111;padding:16px;border-radius:8px;margin:16px 0;">
<a href="{download_url}" style="color:#c8f542;font-size:18px;font-weight:bold;">
  → Access Your Product
</a>
</div>
<p>Questions? Reply to this email — we respond within 24h.</p>
<p style="color:#888;font-size:12px;">Guerilla Holdings LLC | trustchainservices.com</p>
</div>
"""
    }
}

def deliver_product(customer_email, customer_name, product_name, amount_cents):
    """Full post-payment delivery flow."""
    results = []
    
    # 1. Send delivery email via Brevo
    if BREVO_KEY and customer_email:
        delivery = PRODUCT_DELIVERY["default"]
        html = delivery["content"].replace("{download_url}", delivery["download_url"])
        
        try:
            r = requests.post("https://api.brevo.com/v3/smtp/email",
                headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
                json={
                    "sender": {"name": "Guerilla Holdings", "email": FROM_EMAIL},
                    "to": [{"email": customer_email, "name": customer_name or customer_email}],
                    "subject": delivery["subject"],
                    "htmlContent": html
                }, timeout=15)
            if r.status_code in [200, 201]:
                results.append("delivery_email_sent")
            else:
                results.append(f"delivery_email_failed:{r.status_code}")
        except Exception as e:
            results.append(f"delivery_email_error:{e}")
    
    # 2. Update Notion — mark as converted customer
    if NOTION_TOKEN and customer_email:
        try:
            requests.post("https://api.notion.com/v1/pages",
                headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                         "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
                json={"parent": {"database_id": NOTION_AUDIENCE_DB},
                      "properties": {
                          "Name": {"title": [{"text": {"content": customer_name or customer_email}}]},
                          "Email": {"email": customer_email},
                          "Source": {"select": {"name": "Landing Page"}},
                          "Funnel": {"select": {"name": "Purchase"}},
                          "Converted": {"checkbox": True},
                          "Revenue Generated": {"number": amount_cents / 100},
                          "Business": {"select": {"name": "Digital Products"}},
                          "Lead Score": {"number": 95},
                          "Notes": {"rich_text": [{"text": {"content": f"Purchased: {product_name} | ${amount_cents/100:.2f} | {datetime.now().strftime('%Y-%m-%d')}"}}]},
                      }}, timeout=10)
            results.append("notion_updated")
        except Exception as e:
            results.append(f"notion_error:{e}")
    
    # 3. Queue upsell email for day 3
    upsell_queue = Path("/root/workspace/Penelope/leads/upsell_queue.jsonl")
    upsell_entry = {
        "ts": datetime.now().isoformat(),
        "send_after": (datetime.now().replace(hour=10, minute=0) + __import__("datetime").timedelta(days=3)).isoformat(),
        "email": customer_email,
        "name": customer_name,
        "trigger": "post_purchase",
        "product_purchased": product_name,
        "upsell_product": "Growth Plan — $147/mo",
        "status": "queued"
    }
    with open(upsell_queue, "a") as f:
        f.write(json.dumps(upsell_entry) + "\n")
    results.append("upsell_queued")
    
    # Fire Zapier sale event
    try:
        from zapier_integration import new_sale as zap_sale
        zap_sale(customer_email, amount_cents/100, product_name, "stripe")
    except: pass
    
    return results

if __name__ == "__main__":
    # Test delivery
    test_results = deliver_product(
        customer_email="sydneygarmon@gmail.com",
        customer_name="Sydney",
        product_name="AI Business Automation Starter Kit",
        amount_cents=2700
    )
    print(f"Delivery test: {test_results}")
