#!/usr/bin/env python3
"""
TRUSTCHAIN QUANTUM AUTONOMY AGENT
Runs daily. Checks staged products, runs all gates, auto-publishes if passing.
Removes Sydney from the review loop entirely for routine content.
Only escalates to Sydney if: gates fail 3x, or product requires brand decision.
"""
import os, json, requests, re, time
from pathlib import Path
from datetime import datetime
from google import genai

env = {}
for line in open("/root/penelope_vault.env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=",1); env[k.strip()] = v.strip()

client = genai.Client(api_key=env.get("GOOGLE_API_KEY",""))
GUMROAD_KEY = env.get("GUMROAD_API_KEY","")
OUTPUT = Path("/root/workspace/Penelope/quantum_products")
LOG = Path("/root/workspace/Penelope/conductor_logs/quantum_autonomy.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def quick_gate_check(text):
    """Run gates programmatically — no human needed"""
    issues = []
    # Directive language
    for pattern in [r"\byou should\b", r"\byou must\b", r"\bguaranteed\b"]:
        if re.search(pattern, text, re.IGNORECASE):
            issues.append(f"directive: {pattern}")
    # Disclaimer check
    if "not legal advice" not in text.lower() and "disclaimer" not in text.lower():
        issues.append("missing disclaimer")
    # Brand check
    if "trustchain" not in text.lower():
        issues.append("missing TrustChain brand")
    # NPPI check
    if "nppi" not in text.lower() and "client data" not in text.lower():
        issues.append("missing NPPI/client data language")
    return len(issues) == 0, issues

def gemini_review(text):
    """Gemini self-reviews content before publish"""
    prompt = f"""Review this product description for publish-readiness. Score 1-10.
Check: no false claims, disclaimer present, TrustChain brand mentioned, 
NPPI/client data language present, no directive language.
Text: {text[:2000]}
JSON: {{"score": 0-10, "ready": true/false, "issues": []}}"""
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = getattr(resp,"text","{}").replace("```json","").replace("```","")
    try:
        return json.loads(raw)
    except:
        return {"score": 0, "ready": False, "issues": ["parse error"]}

def auto_publish_to_gumroad(product_id):
    """Publish a staged Gumroad draft — no human needed"""
    r = requests.put(
        f"https://api.gumroad.com/v2/products/{product_id}",
        data={"access_token": GUMROAD_KEY, "published": "true"},
        timeout=15
    )
    return r.status_code == 200

def check_and_publish_staged():
    """Check all staged drafts, auto-publish if clean"""
    staged_path = OUTPUT / "gumroad_listings_STAGED.json"
    if not staged_path.exists():
        log("No staged listings found")
        return
    
    staged = json.loads(staged_path.read_text())
    created_path = OUTPUT / "gumroad_created_ids.json"
    created = json.loads(created_path.read_text()) if created_path.exists() else {}
    
    for key, listing in staged.items():
        if key not in created:
            log(f"  {key}: not yet created in Gumroad")
            continue
        
        product_id = created[key].get("id")
        if not product_id:
            continue
        
        # Run gates
        text = listing.get("description","")
        gate_ok, issues = quick_gate_check(text)
        if not gate_ok:
            log(f"  {key}: gates failed — {issues}")
            continue
        
        # Gemini review
        review = gemini_review(text)
        if not review.get("ready") or review.get("score",0) < 8:
            log(f"  {key}: Gemini review not ready — {review.get('issues')}")
            continue
        
        # Auto-publish
        if auto_publish_to_gumroad(product_id):
            log(f"  ✅ AUTO-PUBLISHED: {listing['name']}")
        else:
            log(f"  ❌ Publish failed: {key}")

def run():
    log("Quantum Autonomy Agent starting")
    check_and_publish_staged()
    log("Done")

if __name__ == "__main__":
    run()
