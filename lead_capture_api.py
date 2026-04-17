#!/usr/bin/env python3
"""Lead Capture API — receives form submissions from all landing pages."""
from flask import Flask, request, jsonify
import json, requests, logging, os
from datetime import datetime


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


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lead_api")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "6183015901")

SEGMENT_MAP = {
    "gafc": ["GAFC Fan", "Gun Safety"],
    "digital": ["Entrepreneur", "AI Enthusiast"],
    "guerilla": ["Entrepreneur", "Grant Seeker"],
    "callux": ["Transport Pro"],
    "cadaverco": ["Transport Pro"],
}

BUSINESS_MAP = {
    "gafc": "GAFC",
    "digital": "Digital Products",
    "guerilla": "Guerilla Holdings",
    "callux": "CALLUX",
    "cadaverco": "CadaverCo",
}

def score_lead(data):
    score = 10
    if data.get("email"): score += 20
    if data.get("phone"): score += 15
    if data.get("name") and data["name"] != "Anonymous": score += 10
    if data.get("message"): score += 15
    return min(score, 100)

def add_to_notion(data):
    if not NOTION_TOKEN: return
    brand = data.get("brand", "digital")
    segments = SEGMENT_MAP.get(brand, ["Digital Buyer"])
    business = BUSINESS_MAP.get(brand, "Digital Products")
    score = score_lead(data)
    
    props = {
        "Name": {"title": [{"text": {"content": data.get("name", "Anonymous")[:100]}}]},
        "Source": {"select": {"name": "Landing Page"}},
        "Segment": {"multi_select": [{"name": s} for s in segments]},
        "Business": {"select": {"name": business}},
        "Funnel": {"select": {"name": "Interest"}},
        "Lead Score": {"number": score},
        "date:Last Touch:start": datetime.now().strftime("%Y-%m-%d"),
        "date:Last Touch:is_datetime": 0,
        "Notes": {"rich_text": [{"text": {"content": f"Source: {data.get('source','landing_page')} | Page: {data.get('page','/')} | Message: {data.get('message','')}"[:500]}}]},
    }
    if data.get("email"):
        props["Email"] = {"email": data["email"]}
    if data.get("phone"):
        props["Phone"] = {"phone_number": data["phone"]}
    if data.get("page"):
        props["Landing Page"] = {"url": data["page"]}

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
        json={"parent": {"database_id": NOTION_DB}, "properties": props},
        timeout=10
    )
    log.info(f"Notion lead: {r.status_code} | {data.get('email')}")
    return r.status_code

def telegram_alert(data):
    msg = f"""🎯 NEW LEAD CAPTURED
Brand: {data.get('brand','?').upper()}
Name: {data.get('name','Anonymous')}
Email: {data.get('email','none')}
Phone: {data.get('phone','none')}
Source: {data.get('source','landing_page')}
Score: {score_lead(data)}/100"""
    _tg_emergency_only("[suppressed direct call]")

@app.route("/api/lead", methods=["POST", "GET"])
def capture_lead():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        data["brand"] = data.get("brand", request.args.get("brand", "digital"))
        data["source"] = data.get("source", request.args.get("source", "landing_page"))
        data["page"] = request.referrer or data.get("page", "")
        
        log.info(f"Lead captured: {data.get('email','?')} | {data.get('brand','?')}")
        
        # Store to Notion
        add_to_notion(data)
        
        # Telegram alert for every lead
        try: telegram_alert(data)
        except: pass
        
        return jsonify({"success": True, "message": "You're in! Check your email."}), 200
    except Exception as e:
        log.error(f"Lead capture error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({"status": "lead_capture_active", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)