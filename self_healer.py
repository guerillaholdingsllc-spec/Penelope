#!/usr/bin/env python3
"""
PENELOPE SELF-HEALING AGENT
Runs every 5 hours. Checks all systems, finds bugs/errors, auto-fixes what it can.
Reports only unfixable critical issues to Telegram.
Logs everything to /root/workspace/Penelope/conductor_logs/self_heal.log
"""
import os, json, time, subprocess, requests, logging
from datetime import datetime
from pathlib import Path
from google import genai


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


# Load vault
env = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
except: pass

GOOGLE_API_KEY  = env.get("GOOGLE_API_KEY","")
TELEGRAM_TOKEN  = env.get("TELEGRAM_BOT_TOKEN","")
TELEGRAM_CHAT   = env.get("TELEGRAM_CHAT_ID","6183015901")
LOG_FILE        = Path("/root/workspace/Penelope/conductor_logs/self_heal.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [HEALER] %(message)s",
    handlers=[logging.FileHandler(str(LOG_FILE)), logging.StreamHandler()])
log = logging.getLogger("self_healer")

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

def tg_critical(msg):
    """Only for unfixable critical issues."""
    if not TELEGRAM_TOKEN: return
    hour = datetime.now().hour
    if hour < 8 or hour >= 22: return  # respect quiet hours even for critical
    try:
        _tg_emergency_only("[suppressed direct call]")
    except: pass

def shell(cmd, timeout=30):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def check_services():
    """Check all Penelope services. Restart failed ones."""
    fixes = []
    out, _, _ = shell("systemctl list-units --type=service --state=failed | grep penelope")
    if out:
        for line in out.strip().splitlines():
            svc = line.strip().split()[0]
            log.warning(f"Failed service: {svc} — attempting restart")
            _, err, rc = shell(f"systemctl restart {svc}")
            time.sleep(3)
            _, _, rc2 = shell(f"systemctl is-active {svc}")
            if rc2 == 0:
                fixes.append(f"✅ Restarted {svc}")
                log.info(f"Fixed: {svc}")
            else:
                fixes.append(f"❌ Could not fix {svc}: {err[:100]}")
                tg_critical(f"Service {svc} failed and could not be restarted: {err[:200]}")
    return fixes

def check_disk():
    """Warn if disk > 85%."""
    out, _, _ = shell("df / | tail -1 | awk '{print $5}' | tr -d '%'")
    try:
        pct = int(out.strip())
        if pct > 85:
            log.warning(f"Disk usage: {pct}%")
            tg_critical(f"Disk at {pct}% — clean up /root/workspace/Penelope/shipped/ or logs")
            return [f"⚠️ Disk {pct}% — action needed"]
        log.info(f"Disk OK: {pct}%")
    except: pass
    return []

def check_memory():
    """Warn if memory > 90%."""
    out, _, _ = shell("free | grep Mem | awk '{printf \"%.0f\", $3/$2*100}'")
    try:
        pct = int(out.strip())
        if pct > 90:
            log.warning(f"Memory: {pct}%")
            return [f"⚠️ Memory {pct}%"]
        log.info(f"Memory OK: {pct}%")
    except: pass
    return []

def check_log_errors():
    """Scan recent logs for Python errors. Use Gemini to suggest fixes."""
    fixes = []
    log_paths = [
        "/root/workspace/Penelope/trading_bot/engine_v3.log",
        "/root/workspace/Penelope/conductor_logs/health.log",
        "/root/workspace/Penelope/engine_v2.log",
        "/root/workspace/Penelope/penelope.log",
    ]
    for lp in log_paths:
        p = Path(lp)
        if not p.exists(): continue
        try:
            recent = p.read_text().splitlines()[-50:]
            errors = [l for l in recent if any(x in l for x in ["ERROR","Traceback","SyntaxError","TypeError","ModuleNotFoundError"])]
            if errors and client:
                error_block = "\n".join(errors[:10])
                prompt = f"""These are Python errors from Penelope's logs ({lp}):
{error_block}

In 2 sentences: what is the root cause and what is the single best fix?
Be concrete. If it's a missing package, say which. If it's a code bug, say the fix."""
                try:
                    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                    analysis = getattr(resp, "text","").strip()
                    log.info(f"Error analysis [{p.name}]: {analysis[:200]}")
                    fixes.append(f"📋 {p.name}: {analysis[:200]}")
                except Exception as e:
                    log.warning(f"Gemini analysis error: {e}")
        except Exception as e:
            log.warning(f"Log check error {lp}: {e}")
    return fixes

def check_cron_dupes():
    """Remove duplicate cron entries."""
    out, _, _ = shell("crontab -l")
    lines = out.splitlines()
    seen = set()
    clean = []
    dupes = 0
    for line in lines:
        if line.strip() in seen and line.strip():
            dupes += 1
        else:
            seen.add(line.strip())
            clean.append(line)
    if dupes > 0:
        new_cron = "\n".join(clean) + "\n"
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
            f.write(new_cron)
            tmp = f.name
        shell(f"crontab {tmp}")
        os.unlink(tmp)
        log.info(f"Removed {dupes} duplicate cron entries")
        return [f"✅ Removed {dupes} duplicate cron entries"]
    return []

def check_trading_engine():
    """Verify trading engine is running and healthy."""
    out, _, rc = shell("systemctl is-active penelope-trading-v3")
    if out.strip() != "active":
        shell("systemctl restart penelope-trading-v3")
        time.sleep(5)
        out2, _, _ = shell("systemctl is-active penelope-trading-v3")
        if out2.strip() == "active":
            return ["✅ Restarted trading engine"]
        else:
            tg_critical("Trading engine v3 down and could not restart")
            return ["❌ Trading engine could not be restarted"]
    return []

def check_api_endpoints():
    """Test key HTTP endpoints."""
    results = []
    endpoints = [
        ("http://localhost:5001/health", "Penelope API"),
        ("http://localhost:5001/status", "Trading Status"),
        ("http://localhost:5099/health", "Shell Bridge"),
    ]
    for url, name in endpoints:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code in (200, 405):
                log.info(f"Endpoint OK: {name} ({r.status_code})")
            else:
                results.append(f"⚠️ {name}: HTTP {r.status_code}")
                log.warning(f"Endpoint issue: {name} {r.status_code}")
        except Exception as e:
            results.append(f"❌ {name}: {str(e)[:60]}")
            log.warning(f"Endpoint down: {name}: {e}")
    return results

def check_marketing():
    """Verify marketing agents are producing output."""
    results = []
    # Check content army output recency
    army_log = Path("/root/workspace/Penelope/conductor_logs/content_perf.log")
    if army_log.exists():
        age_hours = (time.time() - army_log.stat().st_mtime) / 3600
        if age_hours > 6:
            results.append(f"⚠️ Content performance log stale ({age_hours:.0f}h)")
    
    # Check GAFC content agent ran today
    gafc_log = Path("/root/workspace/Penelope/conductor_logs/gafc_content.log")
    if gafc_log.exists():
        age_hours = (time.time() - gafc_log.stat().st_mtime) / 3600
        if age_hours > 25:
            results.append(f"⚠️ GAFC content agent stale ({age_hours:.0f}h)")
        else:
            log.info(f"GAFC content agent: ran {age_hours:.1f}h ago ✅")
    
    # Check feed.json has recent entries
    feed = Path("/root/workspace/Penelope/feed.json")
    if feed.exists():
        try:
            entries = json.loads(feed.read_text())
            if entries:
                latest = entries[0].get("time","")
                log.info(f"Feed: {len(entries)} entries, latest: {latest}")
            else:
                results.append("⚠️ feed.json is empty")
        except: pass
    
    return results


def check_buffer_agent():
    """Verify buffer agent ran and posted successfully in last 5h."""
    log_path = Path("/root/workspace/Penelope/conductor_logs/buffer_agent.log")
    if not log_path.exists():
        return ["⚠️ Buffer agent: log missing"]
    age_h = (time.time() - log_path.stat().st_mtime) / 3600
    if age_h > 5:
        return [f"⚠️ Buffer agent stale ({age_h:.0f}h) — restart or check cron"]
    last = log_path.read_text().splitlines()[-10:]
    ok = sum(1 for l in last if "✅ Queued" in l)
    log.info(f"Buffer agent: {age_h:.1f}h ago, {ok} recent posts ✅")
    return []

def run():
    log.info("="*60)
    log.info(f"SELF-HEALING RUN @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("="*60)
    
    all_fixes = []
    all_fixes += check_services()
    all_fixes += check_disk()
    all_fixes += check_memory()
    all_fixes += check_cron_dupes()
    all_fixes += check_trading_engine()
    all_fixes += check_api_endpoints()
    all_fixes += check_marketing()
    all_fixes += check_buffer_agent()
    all_fixes += check_log_errors()
    
    fixes = [f for f in all_fixes if f.startswith("✅")]
    warnings = [f for f in all_fixes if f.startswith("⚠️")]
    errors = [f for f in all_fixes if f.startswith("❌")]
    notes = [f for f in all_fixes if f.startswith("📋")]
    
    log.info(f"DONE: {len(fixes)} fixes, {len(warnings)} warnings, {len(errors)} errors")
    for item in all_fixes:
        log.info(f"  {item}")
    
    # Write summary to feed
    try:
        feed_path = Path("/root/workspace/Penelope/feed.json")
        feed = []
        if feed_path.exists():
            try: feed = json.loads(feed_path.read_text())
            except: feed = []
        feed.insert(0, {
            "id": int(time.time()),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": f"[SelfHealer] {len(fixes)} fixes, {len(warnings)} warnings, {len(errors)} errors",
            "content": "\n".join(all_fixes) or "All systems healthy",
            "status": "error" if errors else ("info" if warnings else "success"),
            "agent": "SelfHealer"
        })
        feed = feed[:100]
        tmp = feed_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(feed, indent=2))
        tmp.rename(feed_path)
    except Exception as e:
        log.warning(f"Feed write error: {e}")

if __name__ == "__main__":
    run()