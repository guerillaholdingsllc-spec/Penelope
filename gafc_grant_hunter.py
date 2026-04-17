#!/usr/bin/env python3
import os,json,requests
from datetime import datetime
from pathlib import Path
import google.generativeai as genai

def _get_gemini_client():
    """Lazy Gemini client — loads key from vault at call time."""
    import os as _o
    key = _o.getenv("GOOGLE_API_KEY", "")
    if not key:
        try:
            for line in open("/root/penelope_vault.env"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip()
                    break
        except: pass
    if not key:
        return None
    import google.generativeai as genai as _g
    return _g.Client(api_key=key)

GOOGLE_API_KEY=os.environ.get("GOOGLE_API_KEY")
TELEGRAM_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID="6183015901"
OUTPUT_DIR=Path("/root/workspace/Penelope/gafc_grants")
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
GRANTS=[
{"name":"CalVIP","amount":"Up to 500000","type":"State"},
{"name":"Everytown Safety Fund","amount":"50k-200k","type":"Private"},
{"name":"Sacramento Stockton Blvd Grant","amount":"5k-25k","type":"Local"},
{"name":"CA Emerging Minority Business Fund","amount":"Up to 50000","type":"State-Minority"},
{"name":"MBDA Federal Grants","amount":"Varies","type":"Federal"},
]
def gemini(prompt):
    try:
        import google.generativeai as genai as _g
        import os
        key = os.getenv("GOOGLE_API_KEY","") or next(
            (l.split("=",1)[1].strip() for l in open("/root/penelope_vault.env")
             if l.strip().startswith("GOOGLE_API_KEY=")), "")
        c = _g.Client(api_key=key)
        return c.models.generate_content(model="gemini-2.5-flash", contents=prompt).text.strip()
    except Exception as e:
        print(f"Gemini error: {e}"); return ""

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


def draft(grant):
 p=f"""Write a 250-word grant application for a minority-owned social enterprise.
Org: Glocks and Fried Chicken (GAFC)
Mission: Gun safety education in communities of color in Sacramento CA
Partner: Church of Legacy
Programs: Gloxsie 21 cartoon IP, AI education, community workshops
Grant: {grant[chr(110)+chr(97)+chr(109)+chr(101)]} | Amount: {grant[chr(97)+chr(109)+chr(111)+chr(117)+chr(110)+chr(116)]}
Cover: need, programs, outcomes, why GAFC is qualified."""
 return gemini(p)
def run():
 print("GAFC Grant Hunter running...")
 drafted=[]
 for g in GRANTS[:3]:
  print(f"Drafting: {g[chr(110)+chr(97)+chr(109)+chr(101)]}")
  try:
   d=draft(g)
   data={"grant":g,"draft":d,"at":datetime.utcnow().isoformat()}
   drafted.append(data)
   fn=OUTPUT_DIR/f"draft_{g[chr(110)+chr(97)+chr(109)+chr(101)][:30].replace(chr(32),chr(95))}_{datetime.utcnow().strftime(chr(37)+chr(89)+chr(37)+chr(109)+chr(37)+chr(100))}.json"
   open(fn,"w").write(json.dumps(data,indent=2))
   print(f"Saved: {fn.name}")
  except Exception as e:
   print(f"Error: {e}")
 telegram(f"GAFC Grant Hunter: {len(drafted)} applications drafted. Check /gafc_grants/ on server.")
 print(f"Done: {len(drafted)} drafts saved")
run()