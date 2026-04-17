#!/usr/bin/env python3
"""
Penelope Shell Bridge — port 5099
Gives Claude direct shell execution access to Penelope
"""
from flask import Flask, request, jsonify
import subprocess, os, hashlib, hmac

app = Flask(__name__)
SECRET = os.getenv("BRIDGE_SECRET", "sydney123")

def auth(req):
    return req.headers.get("X-Secret") == SECRET or \
           req.json.get("secret") == SECRET if req.is_json else False

@app.route("/health")
def health():
    return jsonify({"status": "bridge running"})

@app.route("/exec", methods=["POST"])
def execute():
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json
    cmd = data.get("cmd", "")
    if not cmd:
        return jsonify({"error": "no cmd"}), 400
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=30,
            cwd="/root/workspace/Penelope"
        )
        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/vault", methods=["POST"])
def vault():
    """Write key=value pairs to penelope vault"""
    if not auth(request):
        return jsonify({"error": "unauthorized"}), 401
    data = request.json
    entries = data.get("entries", {})
    vault_path = "/root/penelope_vault.env"
    written = []
    try:
        # Read existing
        existing = {}
        if os.path.exists(vault_path):
            with open(vault_path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip()
        # Update
        existing.update(entries)
        # Write back
        with open(vault_path, "w") as f:
            for k, v in existing.items():
                f.write(f"{k}={v}\n")
        written = list(entries.keys())
        return jsonify({"written": written, "total_entries": len(existing)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5099, debug=False)
