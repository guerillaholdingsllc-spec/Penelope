import os, json, glob, datetime, time, requests, subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE         = "/root/workspace/Penelope"
T_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN","8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
C_ID         = os.getenv("TELEGRAM_CHAT_ID","6183015901")
GUMROAD_KEY  = os.getenv("GUMROAD_API_KEY","2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4")
APPROVAL_LOG = f"{BASE}/approvals.json"
GUMROAD_BASE = "https://api.gumroad.com/v2"

def load_approvals():
    if os.path.exists(APPROVAL_LOG):
        with open(APPROVAL_LOG) as f: return json.load(f)
    return {}

def save_approvals(data):
    with open(APPROVAL_LOG,"w") as f: json.dump(data,f,indent=2)


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


def health():
    return jsonify({"status":"ok","service":"Penelope Command Center","version":"2.0"})

@app.route("/api/files")
def list_files():
    category = request.args.get("category","shipped")
    dirs = {
        "shipped":  f"{BASE}/shipped",
        "crypto":   f"{BASE}/crypto_reports",
        "briefs":   f"{BASE}/daily_briefs",
        "finance":  f"{BASE}/finance",
        "ideas":    f"{BASE}/ideas",
        "approved": f"{BASE}/approved",
        "building": f"{BASE}/building",
        "intel":    f"{BASE}/intel",
        "social":   f"{BASE}/shipped",
    }
    target = dirs.get(category, f"{BASE}/shipped")
    os.makedirs(target, exist_ok=True)
    approvals = load_approvals()
    files = []
    for fpath in sorted(glob.glob(f"{target}/*"), key=os.path.getmtime, reverse=True):
        if not os.path.isfile(fpath): continue
        fname = os.path.basename(fpath)
        mtime = os.path.getmtime(fpath)
        size  = os.path.getsize(fpath)
        files.append({
            "name": fname,
            "path": fpath,
            "category": category,
            "modified": datetime.datetime.fromtimestamp(mtime).isoformat(),
            "modified_human": datetime.datetime.fromtimestamp(mtime).strftime("%b %d %I:%M %p"),
            "size": size,
            "size_human": f"{size//1024}KB" if size > 1024 else f"{size}B",
            "approval_status": approvals.get(fpath,{}).get("status","pending"),
            "extension": fname.rsplit(".",1)[-1] if "." in fname else ""
        })
    return jsonify(files)

@app.route("/api/file/content")
def file_content():
    path = request.args.get("path","")
    if not path or not os.path.exists(path):
        return jsonify({"error":"File not found"}), 404
    if not path.startswith(BASE):
        return jsonify({"error":"Access denied"}), 403
    try:
        with open(path,"r",errors="replace") as f: content = f.read()
        return jsonify({"content":content,"path":path,"name":os.path.basename(path)})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/api/file/approve", methods=["POST"])
def approve_file():
    data = request.json
    path = data.get("path","")
    action = data.get("action","approved")
    notes = data.get("notes","")
    if not path or not os.path.exists(path):
        return jsonify({"error":"File not found"}), 404
    approvals = load_approvals()
    approvals[path] = {
        "status": action,
        "notes": notes,
        "timestamp": datetime.datetime.now().isoformat(),
        "file": os.path.basename(path)
    }
    save_approvals(approvals)
    if action == "approved":
        import shutil
        dest = f"{BASE}/approved/{os.path.basename(path)}"
        os.makedirs(f"{BASE}/approved", exist_ok=True)
        shutil.copy2(path, dest)
        _tg_emergency_only(f"✅ *APPROVED*\n{os.path.basename(path)}\n{notes}")
    elif action == "rejected":
        _tg_emergency_only(f"❌ *REJECTED*\n{os.path.basename(path)}\nReason: {notes}")
    elif action == "needs_revision":
        _tg_emergency_only(f"✏️ *NEEDS REVISION*\n{os.path.basename(path)}\nNotes: {notes}")
    return jsonify({"success":True,"status":action})

@app.route("/api/file/publish", methods=["POST"])
def publish_file():
    data = request.json
    path = data.get("path","")
    if not path or not os.path.exists(path):
        return jsonify({"error":"File not found"}), 404
    with open(path,"r",errors="replace") as f: content = f.read()
    name = os.path.basename(path).replace("_"," ").replace(".md","")
    try:
        res = requests.post(f"{GUMROAD_BASE}/products",
            headers={"Authorization":f"Bearer {GUMROAD_KEY}"},
            data={"name":name,"description":content[:5000],"price":2700,"published":"true"},
            timeout=20)
        result = res.json()
        if result.get("success"):
            url = result.get("product",{}).get("short_url","")
            _tg_emergency_only(f"🚀 *PUBLISHED TO GUMROAD*\n{name}\n{url}")
            return jsonify({"success":True,"url":url})
    except Exception as e:
        return jsonify({"error":str(e)}), 500
    return jsonify({"success":False})

@app.route("/api/stats")
def stats():
    def count(d):
        path = f"{BASE}/{d}"
        return len(glob.glob(f"{path}/*")) if os.path.exists(path) else 0
    approvals = load_approvals()
    pending = sum(1 for v in approvals.values() if v.get("status")=="pending")
    finance_state = {}
    fp = f"{BASE}/finance/finance_state.json"
    if os.path.exists(fp):
        with open(fp) as f: finance_state = json.load(f)
    services = []
    for s in ["autonomous_engine","gumroad_publisher","social_publisher","feedback_loop",
              "crypto_intelligence","daily_brief","financial_tracker","opportunity_radar",
              "agent_orchestrator","penelope_server"]:
        r = subprocess.run(["pgrep","-f",s],capture_output=True)
        services.append({"name":s,"running":r.returncode==0})
    return jsonify({
        "shipped": count("shipped"),
        "approved": count("approved"),
        "ideas": count("ideas"),
        "building": count("building"),
        "briefs": count("daily_briefs"),
        "pending_approval": pending,
        "deficit": finance_state.get("deficit",-50000),
        "revenue": finance_state.get("total_revenue",0),
        "autonomy_fund": finance_state.get("autonomy_fund",100),
        "services": services
    })

@app.route("/api/pipeline")
def pipeline():
    stages = ["ideas","approved","building","pr_raised","awaiting_review","shipped"]
    result = {}
    for stage in stages:
        d = f"{BASE}/{stage}"
        os.makedirs(d, exist_ok=True)
        files = []
        for fpath in sorted(glob.glob(f"{d}/*"),key=os.path.getmtime,reverse=True)[:10]:
            if os.path.isfile(fpath):
                files.append({
                    "name": os.path.basename(fpath),
                    "path": fpath,
                    "modified": datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%b %d %I:%M %p"),
                    "size_human": f"{os.path.getsize(fpath)//1024}KB" if os.path.getsize(fpath)>1024 else f"{os.path.getsize(fpath)}B"
                })
        result[stage] = files
    return jsonify(result)

@app.route("/api/agents/status")
def agents_status():
    af = f"{BASE}/agents_status.json"
    if os.path.exists(af):
        with open(af) as f: return jsonify(json.load(f))
    return jsonify({"agents":{},"last_updated":None})

@app.route("/api/feed")
def feed():
    ff = f"{BASE}/feed.json"
    if os.path.exists(ff):
        with open(ff) as f: return jsonify(json.load(f))
    return jsonify([])

@app.route("/api/tasks")
def agent_tasks():
    tf = f"{BASE}/agent_tasks.json"
    if os.path.exists(tf):
        with open(tf) as f: return jsonify(json.load(f))
    return jsonify({"tasks":[]})

if __name__ == "__main__":
    print("Penelope Server starting on port 5003")
    app.run(host="0.0.0.0", port=5003, debug=False)
