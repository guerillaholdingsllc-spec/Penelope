#!/usr/bin/env python3
import os,json,time,hashlib,requests,logging,base64
from pathlib import Path
from datetime import datetime
SHIPPED_DIR=Path("/root/workspace/Penelope/shipped")
POSTED_LOG=Path("/root/workspace/Penelope/wp_published.json")
WP_URL=os.getenv("WP_URL","http://206.81.5.241:8081")
WP_USER=os.getenv("WP_USERNAME","Penelope")
WP_PASS=os.getenv("WP_APP_PASSWORD","")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","6183015901")
CHECK_INTERVAL=600
logging.basicConfig(level=logging.INFO,format="%(asctime)s [WORDPRESS] %(message)s",handlers=[logging.FileHandler("/root/workspace/Penelope/wp_publisher.log"),logging.StreamHandler()])
log=logging.getLogger(__name__)
def auth():
    creds=base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    return {"Authorization":f"Basic {creds}","Content-Type":"application/json"}
def load_posted():
    return json.loads(POSTED_LOG.read_text()) if POSTED_LOG.exists() else {}
def save_posted(d): POSTED_LOG.write_text(json.dumps(d,indent=2))
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
    title=next((l.lstrip("#").strip() for l in lines if l.startswith("#")),path.stem.replace("_"," "))[:200]
    body_lines=[l for l in lines if not l.startswith("#")]
    content="<p>"+"</p><p>".join(l.strip() for l in body_lines if l.strip())[:50000]+"</p>"
    return {"title":title,"content":content}
def publish_wp(post):
    r=requests.post(f"{WP_URL}/wp-json/wp/v2/posts",headers=auth(),json={"title":post["title"],"content":post["content"],"status":"publish"},timeout=30)
    return r.json()
def run():
    posted=load_posted()
    if not SHIPPED_DIR.exists(): return
    # Post AI consulting and automation articles
    files=sorted(SHIPPED_DIR.glob("*.md"),reverse=True)[:50]
    for f in files:
        h=file_hash(f)
        if h in posted: continue
        # Skip pure Gumroad product files — those go to Gumroad, not WP
        if "Gumroad" in f.name: continue
        try:
            post=parse_md(f)
            result=publish_wp(post)
            if result.get("link"):
                posted[h]={"file":f.name,"title":post["title"],"url":result["link"],"at":datetime.utcnow().isoformat()}
                save_posted(posted)
                log.info(f"Published to WordPress: {post['title']} -> {result['link']}")
                _tg_emergency_only(f"📝 *New Blog Post Live!*\n{post['title']}\n{result['link']}")
            else:
                log.error(f"WP error: {result}")
        except Exception as e:
            log.error(f"Error: {e}")
        time.sleep(5)
if __name__=="__main__":
    log.info("WordPress publisher started")
    _tg_emergency_only("📝 *Penelope WordPress Auto-Publisher* is live.")
    while True:
        try: run()
        except Exception as e: log.error(e)
        log.info(f"Sleeping {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)
