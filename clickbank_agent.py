#!/usr/bin/env python3
"""Penelope ClickBank Research Agent — finds best no-interview affiliate offers"""
import os,json,time,requests,logging
from datetime import datetime
from pathlib import Path

TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY","")
OUTPUT=Path("/root/workspace/guerilla-data/clickbank_offers.json")

logging.basicConfig(level=logging.INFO,format="%(asctime)s [CB] %(message)s",
    handlers=[logging.FileHandler("/root/workspace/Penelope/clickbank_research.log"),
              logging.StreamHandler()])
log=logging.getLogger(__name__)


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


def load_vault():
    env={}
    try:
        with open("/root/penelope_vault.env") as f:
            for line in f:
                line=line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k,v=line.split("=",1); env[k.strip()]=v.strip()
    except: pass
    return env

ENV=load_vault()
FIRECRAWL_KEY=ENV.get("FIRECRAWL_KEY","")

OFFERS_TO_FIND=[
    {"niche":"health","keywords":["weight loss","keto","diabetes","blood sugar"]},
    {"niche":"finance","keywords":["crypto","passive income","trading","forex"]},
    {"niche":"relationships","keywords":["dating","marriage","attraction"]},
    {"niche":"self-help","keywords":["manifestation","confidence","productivity"]},
]

def scrape_offers():
    """Scrape ClickBank marketplace for high-gravity no-interview offers."""
    offers=[]
    try:
        from google import genai
        client=genai.Client(api_key=GOOGLE_API_KEY)
        prompt="""You are a ClickBank affiliate researcher. List 10 current high-gravity ClickBank products
that: 1) have gravity 50+, 2) pay 50%+ commission, 3) require NO interview or approval.
Categories: health, finance, self-help, relationships.
Return JSON array: [{"name":"","gravity":0,"commission_pct":0,"url":"","niche":"","why_good":""}]
Only JSON, no explanation."""
        resp=client.models.generate_content(model="gemini-2.5-flash",contents=prompt)
        txt=getattr(resp,"text","[]").strip().replace("```json","").replace("```","").strip()
        offers=json.loads(txt)
        log.info(f"Found {len(offers)} offers via Gemini research")
    except Exception as e:
        log.error(f"Scrape error: {e}")
    return offers

def save_offers(offers):
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    existing=[]
    if OUTPUT.exists():
        try: existing=json.loads(OUTPUT.read_text())
        except: pass
    # Merge, dedupe by name
    names={o["name"] for o in existing}
    new=[o for o in offers if o.get("name") not in names]
    merged=new+existing
    merged=merged[:50]
    OUTPUT.write_text(json.dumps(merged,indent=2))
    log.info(f"Saved {len(new)} new offers ({len(merged)} total)")
    return new

def run():
    log.info("ClickBank Research Agent starting")
    offers=scrape_offers()
    if not offers:
        log.info("No offers found this cycle")
        return
    new=save_offers(offers)
    if new:
        summary="\n".join([f"• {o['name']} | {o.get('commission_pct',0)}% | gravity {o.get('gravity',0)}" for o in new[:5]])
        _tg_emergency_only(f"*ClickBank: {len(new)} new offers*\n{summary}")
    log.info("ClickBank Research Agent complete")

if __name__=="__main__":
    run()
