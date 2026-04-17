#!/usr/bin/env python3
import os,re,json,time,hashlib,requests,logging
from pathlib import Path
from datetime import datetime
SHIPPED_DIR=Path("/root/workspace/Penelope/shipped")
PUBLISHED_LOG=Path("/root/workspace/Penelope/gumroad_published.json")
GUMROAD_API_KEY=os.getenv("GUMROAD_API_KEY","XFsvKLjfxfsMw8RCJL5kUHQ6H3vZ68tdvAU15e1XREo")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
PRODUCT_ID="vniej"
PRODUCT_URL="https://guerillaholdings.gumroad.com/l/vniej"
CHECK_INTERVAL=300
logging.basicConfig(level=logging.INFO,format="%(asctime)s [GUMROAD] %(message)s",handlers=[logging.FileHandler("/root/workspace/Penelope/gumroad_publisher.log"),logging.StreamHandler()])
log=logging.getLogger(__name__)
def load_published():
    return json.loads(PUBLISHED_LOG.read_text()) if PUBLISHED_LOG.exists() else {}
def save_published(d): PUBLISHED_LOG.write_text(json.dumps(d,indent=2))
def file_hash(p): return hashlib.md5(p.read_bytes()).hexdigest()

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


def parse_md(path):
    text=path.read_text(errors="ignore")
    lines=text.split("\n")
    name=next((l.lstrip("#").strip() for l in lines if l.startswith("#")),path.stem.replace("_"," "))[:100]
    m=re.search(r"(?:price|cost):\s*\$?([\d.]+)",text,re.I)
    price=int(float(m.group(1))*100) if m else 2700
    body=[l for l in lines if not l.startswith("#") and l.strip()]
    desc="\n".join(body[:40])[:1500] or "Premium digital product from Guerilla Holdings."
    return {"name":name,"price":price,"description":desc}
def update_product(p):
    r=requests.put(
        f"https://api.gumroad.com/v2/products/{PRODUCT_ID}",
        data={"access_token":GUMROAD_API_KEY,"name":p["name"],"price":p["price"],"description":p["description"]},
        timeout=30
    )
    return r.json()
def run():
    pub=load_published()
    if not SHIPPED_DIR.exists(): return
    files=sorted(SHIPPED_DIR.glob("*Gumroad_Digital_Product*.md"),reverse=True)
    if not files:
        log.info("No Gumroad product files found yet.")
        return
    # Process only the newest unprocessed file
    for f in files:
        h=file_hash(f)
        if h in pub: continue
        try:
            p=parse_md(f)
            r=update_product(p)
            if r.get("success"):
                pub[h]={"file":f.name,"name":p["name"],"price":p["price"],"url":PRODUCT_URL,"at":datetime.utcnow().isoformat()}
                save_published(pub)
                log.info(f"Updated Gumroad: {p['name']} @ ${p['price']/100:.2f}")
                _tg_emergency_only(f"💰 *Gumroad Updated!*\n📦 {p['name']}\n💵 ${p['price']/100:.2f}\n🔗 {PRODUCT_URL}")
            else:
                log.error(f"Gumroad error: {r.get('message','unknown')}")
        except Exception as e:
            log.error(f"Error: {e}")
        break  # only update one at a time
if __name__=="__main__":
    log.info("Gumroad publisher started")
    _tg_emergency_only("🤖 *Gumroad Auto-Publisher* is live. Updating listing automatically.")
    while True:
        try: run()
        except Exception as e: log.error(e)
        time.sleep(CHECK_INTERVAL)
