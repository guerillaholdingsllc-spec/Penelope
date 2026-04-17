#!/usr/bin/env python3
"""
Penelope Email Sender — Brevo (Sendinblue) API
300 emails/day free. Proper deliverability. Open tracking.
Replaces Gmail SMTP entirely.
"""
import os, json, requests, logging
from datetime import datetime
from pathlib import Path

BREVO_KEY = os.getenv("BREVO_API_KEY", "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")
FROM_EMAIL = "guerillaholdingsllc@gmail.com"
FROM_NAME = "Guerilla Holdings"
LEADS_DIR = "/root/workspace/Penelope/leads"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [EMAIL] %(message)s",
    handlers=[logging.FileHandler(f"{LOG_DIR}/email_sender.log"), logging.StreamHandler()])
log = logging.getLogger("email")

HEADERS = {"api-key": BREVO_KEY, "Content-Type": "application/json"}

BRAND_SEQUENCES = {
    "gafc": {
        "sender_name": "GAFC — Glocks & Fried Chicken",
        "welcome_subject": "Welcome to the Movement",
        "welcome_body": """<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#111;color:#eee">
<h2 style="color:#FF6B00">Welcome to GAFC</h2>
<p>Real talk. Real safety. Real community.</p>
<p>You just joined something different — a gun safety movement built BY the community, FOR the community. No judgment. No politics. Just real education that saves lives.</p>
<p><strong style="color:#FF6B00">Here's what you get as a member:</strong></p>
<ul><li>Free gun safety guides and resources</li><li>Community events in Sacramento and NorCal</li><li>Education content that actually speaks to your experience</li></ul>
<p>Stay locked in. More coming your way.</p>
<p style="color:#FF6B00">— The GAFC Team</p>
<p style="font-size:11px;color:#555">Guerilla Holdings LLC | <a href="https://trustchainservices.com/funnels/gafc/" style="color:#FF6B00">Visit GAFC</a> | <a href="https://trustchainservices.com/unsubscribe" style="color:#555">Unsubscribe</a></p>
</div>"""
    },
    "digital": {
        "sender_name": "Guerilla Holdings Digital",
        "welcome_subject": "Your Free AI Business Starter Kit",
        "welcome_body": """<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#0a0a0a;color:#eee">
<h2 style="color:#00FF88">You're In. Let's Build.</h2>
<p>Welcome to the Guerilla Holdings ecosystem — where AI does the work and you collect the revenue.</p>
<p><strong style="color:#00FF88">What's coming your way:</strong></p>
<ul><li>AI automation playbooks for entrepreneurs</li><li>Revenue stream ideas you can deploy this week</li><li>Real case studies from operators who build different</li></ul>
<p>First lesson: the fastest businesses in 2026 aren't the biggest — they're the most automated.</p>
<a href="https://trustchainservices.com/funnels/digital/" style="background:#00FF88;color:#000;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:bold;display:inline-block;margin-top:16px">Get Your Free Starter Kit</a>
<p style="font-size:11px;color:#555;margin-top:24px">Guerilla Holdings LLC | <a href="https://trustchainservices.com/unsubscribe" style="color:#555">Unsubscribe</a></p>
</div>"""
    },
    "guerilla": {
        "sender_name": "Guerilla Holdings LLC",
        "welcome_subject": "Partnership Inquiry Received",
        "welcome_body": """<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#0a0a0a;color:#eee">
<h2 style="color:#FFD700">Guerilla Holdings — We Build Different</h2>
<p>Thanks for connecting. You're on the radar of an AI-native holding company building real revenue engines.</p>
<p>We operate across specialty transport, community education, and digital products — all powered by autonomous AI infrastructure.</p>
<p><strong style="color:#FFD700">What we're looking for:</strong></p>
<ul><li>Strategic partners who move fast</li><li>Grant organizations aligned with community impact</li><li>Investors who understand AI-native business models</li></ul>
<p>Expect to hear more from us with specifics shortly.</p>
<p style="color:#FFD700">— Sydney Garmon, Founder | Guerilla Holdings LLC</p>
<p style="font-size:11px;color:#555;margin-top:24px"><a href="https://trustchainservices.com/unsubscribe" style="color:#555">Unsubscribe</a></p>
</div>"""
    }
}

def send_email(to_email, to_name, subject, html_body, sender_name=None):
    """Send a single email via Brevo."""
    if not BREVO_KEY:
        log.warning("BREVO_API_KEY not set")
        return False
    try:
        r = requests.post("https://api.brevo.com/v3/smtp/email",
            headers=HEADERS,
            json={
                "sender": {"name": sender_name or FROM_NAME, "email": FROM_EMAIL},
                "to": [{"email": to_email, "name": to_name or "Friend"}],
                "subject": subject,
                "htmlContent": html_body,
                "tags": ["penelope", "automated"],
            }, timeout=15)
        if r.status_code == 201:
            log.info(f"Email sent: {to_email} | {subject}")
            return True
        else:
            log.error(f"Email failed {to_email}: {r.status_code} {r.text[:150]}")
            return False
    except Exception as e:
        log.error(f"Email error: {e}")
        return False

def send_welcome(lead_data):
    """Send welcome email to a new lead based on their brand."""
    email = lead_data.get("email", "")
    name = lead_data.get("name", "Friend")
    brand = lead_data.get("brand", lead_data.get("Business", "digital")).lower()
    
    if not email:
        return False
    
    # Map brand names
    brand_map = {"gafc": "gafc", "digital products": "digital", 
                 "guerilla holdings": "guerilla", "callux": "digital", "cadaverco": "digital"}
    brand_key = brand_map.get(brand, "digital")
    seq = BRAND_SEQUENCES.get(brand_key, BRAND_SEQUENCES["digital"])
    
    return send_email(
        to_email=email,
        to_name=name,
        subject=seq["welcome_subject"],
        html_body=seq["welcome_body"],
        sender_name=seq["sender_name"]
    )

def send_nurture_batch(limit=50):
    """Send nurture emails to leads who haven't been emailed yet."""
    import glob
    
    # Track who's been emailed
    emailed_log = Path(LEADS_DIR) / "emailed.json"
    try:
        emailed = set(json.loads(emailed_log.read_text()))
    except:
        emailed = set()
    
    # Pull from attribution log (leads captured via API)
    attr_file = Path(LEADS_DIR) / "attribution_log.jsonl"
    if not attr_file.exists():
        log.info("No attribution log found")
        return 0
    
    sent = 0
    with open(attr_file) as f:
        for line in f:
            if sent >= limit:
                break
            try:
                lead = json.loads(line.strip())
                email = lead.get("lead_id", "")  # lead_id may contain email
                if not email or "@" not in str(email):
                    continue
                if email in emailed:
                    continue
                
                if send_welcome({"email": email, "name": "Friend", "brand": lead.get("brand","digital")}):
                    emailed.add(email)
                    sent += 1
            except:
                pass
    
    emailed_log.write_text(json.dumps(list(emailed)))
    log.info(f"Nurture batch complete: {sent} emails sent")
    return sent

def get_stats():
    """Get email sending stats from Brevo."""
    try:
        r = requests.get("https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
            headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        print("Testing Brevo connection...")
        r = requests.get("https://api.brevo.com/v3/account", headers=HEADERS, timeout=10)
        d = r.json()
        print(f"Account: {d.get('email')} | Plan: {d.get('plan',[{}])[0].get('type','?') if d.get('plan') else '?'}")
        stats = get_stats()
        print(f"Stats: {stats}")
    elif "--nurture" in sys.argv:
        sent = send_nurture_batch()
        print(f"Sent {sent} nurture emails")
