#!/usr/bin/env python3
"""
PENELOPE EMAIL SENDER — Brevo (Sendinblue) HTTPS API
No SMTP ports needed. Works immediately on any server.
300 emails/day free tier.

Drop-in replacement for Gmail SMTP sender.
Activated the moment BREVO_API_KEY is in vault.
Falls back to queue file if no key yet.
"""
import os, json, requests, logging
from datetime import datetime
from pathlib import Path

VAULT = "/root/penelope_vault.env"
QUEUE_FILE = "/root/workspace/Penelope/leads/email_queue.jsonl"
LOG = "/root/workspace/Penelope/conductor_logs/email_sender.log"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EMAIL] %(message)s",
    handlers=[logging.FileHandler(LOG), logging.StreamHandler()])
log = logging.getLogger("email")

def load_vault():
    env = {}
    try:
        with open(VAULT) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
BREVO_KEY = ENV.get("BREVO_API_KEY", "")
GMAIL_FROM = ENV.get("GMAIL_FROM", "sydneygarmon@gmail.com")
FROM_NAME = "Guerilla Holdings"

class BrevoSender:
    """Send emails via Brevo HTTPS API — no SMTP ports needed."""
    
    BASE = "https://api.brevo.com/v3"
    
    def __init__(self, api_key):
        self.key = api_key
        self.headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def send(self, to_email, to_name, subject, html_body, reply_to=None):
        payload = {
            "sender": {"name": FROM_NAME, "email": GMAIL_FROM},
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "htmlContent": html_body,
        }
        if reply_to:
            payload["replyTo"] = {"email": reply_to}
        
        try:
            r = requests.post(f"{self.BASE}/smtp/email",
                headers=self.headers, json=payload, timeout=15)
            if r.status_code in [200, 201]:
                log.info(f"Email sent via Brevo: {to_email} | {subject[:40]}")
                return True
            else:
                log.error(f"Brevo send failed: {r.status_code} | {r.text[:200]}")
                return False
        except Exception as e:
            log.error(f"Brevo error: {e}")
            return False
    
    def get_account(self):
        """Test API key validity."""
        r = requests.get(f"{self.BASE}/account", headers=self.headers, timeout=10)
        return r.status_code == 200, r.json() if r.status_code == 200 else r.text

class EmailQueue:
    """Queue emails when no sender available. Drain when sender comes online."""
    
    def queue(self, to_email, to_name, subject, html_body, brand="digital"):
        entry = {
            "ts": datetime.now().isoformat(),
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "html_body": html_body,
            "brand": brand,
            "status": "queued"
        }
        Path(QUEUE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log.info(f"Email queued: {to_email} | {subject[:40]}")
    
    def drain(self, sender):
        """Send all queued emails."""
        if not Path(QUEUE_FILE).exists():
            return 0
        
        lines = Path(QUEUE_FILE).read_text().strip().split("\n")
        sent = 0
        remaining = []
        
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("status") == "queued":
                    success = sender.send(
                        entry["to_email"], entry.get("to_name",""),
                        entry["subject"], entry["html_body"]
                    )
                    if success:
                        entry["status"] = "sent"
                        entry["sent_at"] = datetime.now().isoformat()
                        sent += 1
                    else:
                        remaining.append(line)
                        continue
            except:
                pass
            remaining.append(json.dumps(entry) if isinstance(entry, dict) else line)
        
        Path(QUEUE_FILE).write_text("\n".join(remaining) + "\n")
        log.info(f"Queue drained: {sent} emails sent")
        return sent

def get_nurture_email(brand, sequence_day, lead_name):
    """Get email from nurture sequence."""
    seq_file = f"/root/workspace/Penelope/leads/email_sequence_{brand}.json"
    if not Path(seq_file).exists():
        return None
    
    try:
        with open(seq_file) as f:
            sequence = json.load(f)
        for email in sequence:
            if email.get("day", 0) == sequence_day:
                body = email.get("body","").replace("{name}", lead_name)
                cta_url = email.get("cta_url", "https://trustchainservices.com")
                cta = email.get("cta", "Learn More")
                
                html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#fff;">
<p style="font-size:16px;line-height:1.7;color:#333;">Hey {lead_name},</p>
<div style="font-size:15px;line-height:1.8;color:#444;">{body.replace(chr(10),'<br>')}</div>
<br>
<a href="{cta_url}" style="display:inline-block;background:#c8f542;color:#000;padding:12px 24px;
   text-decoration:none;border-radius:4px;font-weight:bold;font-size:14px;">{cta}</a>
<br><br>
<p style="color:#999;font-size:12px;border-top:1px solid #eee;padding-top:12px;">
Guerilla Holdings LLC | Sacramento, CA<br>
<a href="https://trustchainservices.com" style="color:#999;">trustchainservices.com</a> | 
<a href="https://trustchainservices.com/unsubscribe" style="color:#999;">Unsubscribe</a>
</p>
</div>"""
                return email.get("subject",""), html
    except:
        pass
    return None

def send_welcome(lead_data):
    """Send welcome email to new lead. Queue if no sender available."""
    email = lead_data.get("email","")
    name = lead_data.get("name","Friend")
    brand = lead_data.get("brand","digital")
    
    if not email:
        return False
    
    result = get_nurture_email(brand, 0, name)
    if not result:
        subject = f"Welcome to Guerilla Holdings 🔥"
        html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;">
<h2 style="color:#c8f542;">Welcome, {name}!</h2>
<p>You're in. Guerilla Holdings builds AI-powered revenue engines for people who move differently.</p>
<p>Check out what we're building: <a href="https://trustchainservices.com">trustchainservices.com</a></p>
<p>— Sydney & the Guerilla Holdings team</p>
</div>"""
    else:
        subject, html = result
    
    # Try Brevo first
    if BREVO_KEY:
        sender = BrevoSender(BREVO_KEY)
        return sender.send(email, name, subject, html)
    else:
        # Queue for when key is available
        q = EmailQueue()
        q.queue(email, name, subject, html, brand)
        return False  # Not sent yet, queued

def run_queue():
    """Drain email queue — called by conductor every cycle."""
    if not BREVO_KEY:
        log.warning("No BREVO_API_KEY — emails staying queued")
        return 0
    
    sender = BrevoSender(BREVO_KEY)
    valid, info = sender.get_account()
    if not valid:
        log.error(f"Brevo auth failed: {info}")
        return 0
    
    q = EmailQueue()
    return q.drain(sender)

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        if BREVO_KEY:
            sender = BrevoSender(BREVO_KEY)
            valid, info = sender.get_account()
            print(f"Brevo auth: {'OK' if valid else 'FAIL'}")
            if valid:
                print(f"Plan: {info.get('plan',{}).get('type','?')}")
                print(f"Email credits: {info.get('plan',{}).get('credits','?')}")
        else:
            print("No BREVO_API_KEY in vault yet")
            print("Sign up free at brevo.com → SMTP & API → API Keys → Create")
            print("Then: echo 'BREVO_API_KEY=your_key' >> /root/penelope_vault.env")
    
    elif "--drain" in sys.argv:
        sent = run_queue()
        print(f"Drained {sent} queued emails")
    
    else:
        # Show queue status
        if Path(QUEUE_FILE).exists():
            lines = [l for l in Path(QUEUE_FILE).read_text().strip().split("\n") if l.strip()]
            queued = sum(1 for l in lines if '"status": "queued"' in l)
            sent = sum(1 for l in lines if '"status": "sent"' in l)
            print(f"Email queue: {queued} queued, {sent} sent")
        else:
            print("Email queue: empty")
        
        if BREVO_KEY:
            print("Brevo: CONFIGURED")
        else:
            print("Brevo: NOT CONFIGURED (add BREVO_API_KEY to vault)")
