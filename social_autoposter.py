#!/usr/bin/env python3
import os,json,time,random,requests,logging
from pathlib import Path
from datetime import datetime
GUMROAD_LOG=Path("/root/workspace/Penelope/gumroad_published.json")
POSTED_LOG=Path("/root/workspace/Penelope/social_posted.json")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
TWITTER_API_KEY=os.getenv("TWITTER_API_KEY","")
TWITTER_API_SECRET=os.getenv("TWITTER_API_SECRET","")
TWITTER_ACCESS_TOKEN=os.getenv("TWITTER_ACCESS_TOKEN","")
TWITTER_ACCESS_SECRET=os.getenv("TWITTER_ACCESS_SECRET","")
logging.basicConfig(level=logging.INFO,format="%(asctime)s [SOCIAL] %(message)s",handlers=[logging.FileHandler("/root/workspace/Penelope/social_poster.log"),logging.StreamHandler()])
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


def load_posted():
    return json.loads(POSTED_LOG.read_text()) if POSTED_LOG.exists() else {"twitter":[]}
def save_posted(d):POSTED_LOG.write_text(json.dumps(d,indent=2))
def get_products():
    return list(json.loads(GUMROAD_LOG.read_text()).values()) if GUMROAD_LOG.exists() else []
def tweet(text):
    if not all([TWITTER_API_KEY,TWITTER_API_SECRET,TWITTER_ACCESS_TOKEN,TWITTER_ACCESS_SECRET]):
        log.warning("Twitter creds missing");return None
    try:
        from requests_oauthlib import OAuth1
        auth=OAuth1(TWITTER_API_KEY,TWITTER_API_SECRET,TWITTER_ACCESS_TOKEN,TWITTER_ACCESS_SECRET)
        r=requests.post("https://api.twitter.com/2/tweets",json={"text":text[:280]},auth=auth,timeout=15)
        d=r.json()
        if "data" in d:log.info(f"Tweeted: {d['data']['id']}");return d["data"]["id"]
        log.error(f"Twitter error: {d}");return None
    except Exception as e:log.error(f"Tweet failed: {e}");return None
def run():
    posted=load_posted()
    products=get_products()
    unposted=[p for p in products if p.get("url") and p["url"] not in posted["twitter"]]
    product=unposted[0] if unposted else None
    if product:
        templates=[
            f"Just published: {product['name']}\n\nBuilt for entrepreneurs automating their business.\n\n{product['url']}\n\n#AI #Automation #Business",
            f"New resource live on Gumroad: {product['name']}\n\n{product['url']}\n\n#PassiveIncome #AITools #Entrepreneur",
            f"If you're building with AI, this is for you:\n\n{product['name']}\n\n{product['url']}\n\n#AI #BusinessAutomation",
        ]
        text=random.choice(templates)
    else:
        generics=[
            "The businesses winning right now are automating first and scaling second. What are you automating? #AI #Business",
            "AI isn't replacing entrepreneurs. It's replacing the ones who refuse to adapt. #Automation #Entrepreneur",
            "Specialty transport is one of the most underserved markets in logistics. The opportunity is massive. #CadaverTransport",
            "Your competitors are using AI right now. The question is: are you? #AITools #BusinessGrowth",
            "Autonomous systems that generate revenue while you sleep. That's the goal. #PassiveIncome #AI",
        ]
        text=random.choice(generics)
    tid=tweet(text)
    if tid:
        if product:posted["twitter"].append(product["url"])
        save_posted(posted)
        _tg_emergency_only(f"🐦 *Tweeted:*\n{text[:200]}")
if __name__=="__main__":
    log.info("Social poster started")
    _tg_emergency_only("📱 *Penelope Social Auto-Poster* is live. Tweeting every 2 hours.")
    while True:
        try:run()
        except Exception as e:log.error(e)
        log.info("Sleeping 2 hours...")
        time.sleep(7200)
