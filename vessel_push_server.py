"""
vessel_push_server.py
Flask server to handle push subscription registration + send push notifications
Runs on port 5070
"""
from flask import Flask, request, jsonify
import json, os, subprocess
from datetime import datetime

app = Flask(__name__)
SUBS_FILE = "/root/workspace/Penelope/vessel_push_subscriptions.json"

def load_subs():
    try:
        with open(SUBS_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_subs(subs):
    with open(SUBS_FILE, 'w') as f:
        json.dump(subs, f, indent=2)

@app.route('/vessel-push-register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('userId', 'anonymous')
    subscription = data.get('subscription')
    if not subscription:
        return jsonify({'error': 'no subscription'}), 400
    subs = load_subs()
    subs[user_id] = {
        'subscription': subscription,
        'registered_at': datetime.now().isoformat()
    }
    save_subs(subs)
    print(f"Registered push for user: {user_id}")
    return jsonify({'ok': True})

@app.route('/vessel-push-send', methods=['POST'])
def send_push():
    """Called by Penelope to send a push to a specific user or all users"""
    data = request.json
    secret = data.get('secret')
    if secret != 'sydney123':
        return jsonify({'error': 'unauthorized'}), 403
    
    user_id = data.get('userId', 'all')
    payload = data.get('payload', {})
    subs = load_subs()
    
    targets = subs.items() if user_id == 'all' else [(user_id, subs.get(user_id, {}))]
    sent = 0
    
    for uid, sub_data in targets:
        if not sub_data:
            continue
        sub = sub_data.get('subscription')
        if not sub:
            continue
        try:
            from pywebpush import webpush, WebPushException
            VAULT = {}
            try:
                with open("/root/penelope_vault.env") as f:
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            k, _, v = line.partition("=")
                            VAULT[k.strip()] = v.strip()
            except: pass
            
            webpush(
                subscription_info=sub,
                data=json.dumps(payload),
                vapid_private_key=VAULT.get('VAPID_PRIVATE_KEY', ''),
                vapid_claims={"sub": "mailto:guerillaholdingsllc@gmail.com"}
            )
            sent += 1
        except Exception as e:
            print(f"Push error for {uid}: {e}")
    
    return jsonify({'sent': sent})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5070)
