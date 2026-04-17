"""
vessel_referral_agent.py
Milestone detection, badge grants, reward processing via Stripe
Polls Base44 Referral DB every 6 hours, fires rewards, logs to Close CRM
"""
import os, json, requests, time
from datetime import datetime
from google import genai as _genai

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


_vessel_client = None

def _get_client():
    global _vessel_client
    if _vessel_client is None:
        _vessel_client = _genai.Client(api_key=GOOGLE_API_KEY)
    return _vessel_client

VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except:
    pass

STRIPE_KEY     = VAULT.get("STRIPE_SECRET_KEY", "")
TELEGRAM_TOKEN = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = "6183015901"
CLOSE_API_KEY  = VAULT.get("CLOSE_API_KEY", "api_4EnW1vfizUUZRXOM2HtX0Y.4GvNXLbhIeOo7ZPb6RY5Bv")
GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY", "")
# Milestone ladder
MILESTONES = [
    {"count": 1,  "badge": "Guide",          "reward_months": 1,  "reward_label": "1 month free"},
    {"count": 3,  "badge": "Aligned",        "reward_months": 3,  "reward_label": "3 months free"},
    {"count": 5,  "badge": "Aligned+",       "reward_months": 6,  "reward_label": "6 months free"},
    {"count": 10, "badge": "Vessel Elder",   "reward_months": 12, "reward_label": "1 year free + Elder Circle"},
    {"count": 25, "badge": "Founding Member","reward_months": 12, "reward_label": "1 year free + Permanent recognition"},
]

def get_milestone_for_count(referral_count, previous_count=0):
    """Return milestone if user just crossed a threshold"""
    for m in reversed(MILESTONES):
        if referral_count >= m["count"] and previous_count < m["count"]:
            return m
    return None

def grant_stripe_credit(stripe_customer_id, months, reason):
    """Apply credit to Stripe customer account"""
    if not STRIPE_KEY or not stripe_customer_id:
        print(f"[MOCK] Would grant {months} months to {stripe_customer_id}: {reason}")
        return True

    # Calculate credit amount: $4.99 * months
    amount_cents = int(4.99 * months * 100)
    try:
        r = requests.post(
            f"https://api.stripe.com/v1/customers/{stripe_customer_id}/balance_transactions",
            auth=(STRIPE_KEY, ""),
            data={
                "amount": -amount_cents,  # negative = credit
                "currency": "usd",
                "description": f"Vessel referral reward: {reason}"
            },
            timeout=15
        )
        if r.ok:
            print(f"Stripe credit granted: ${amount_cents/100} to {stripe_customer_id}")
            return True
        else:
            print(f"Stripe credit failed: {r.text}")
            return False
    except Exception as e:
        print(f"Stripe error: {e}")
        return False

def generate_congrats_message(user_name, badge, reward_label, referral_count, goal_type):
    """Personalized congratulations via Gemini"""
    prompt = f"""Write a short congratulations message for a Vessel user who just earned a badge.

User: {user_name} | Badge earned: {badge} | Referrals: {referral_count} | Goal: {goal_type}
Reward: {reward_label}

The message should:
- Feel personal and celebratory
- Reference the badge name meaningfully
- Mention what they unlocked
- Be under 50 words
- Sound like a wise guide, not a marketing email
- No exclamation marks

Reply with ONLY the message."""

    try:
        r = requests.post(
            f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.8, "maxOutputTokens": 100}},
            timeout=20
        )
        if r.ok:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except:
        pass
    return f"{user_name}, you've earned {badge}. {reward_label} has been applied to your account."

def sync_to_close_crm(user):
    """Create/update Close CRM contact for high-value referrers (Elder+)"""
    if not CLOSE_API_KEY:
        return
    try:
        headers = {"Authorization": f"Basic {CLOSE_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "name": user.get("name", ""),
            "emails": [{"email": user.get("email", ""), "type": "office"}],
            "custom": {
                "Vessel Badge": user.get("badge", ""),
                "Referral Count": user.get("referral_count", 0),
                "Goal Type": user.get("goal_type", ""),
                "Day Count": user.get("day_count", 0)
            }
        }
        r = requests.post(
            "https://api.close.com/api/v1/contact/",
            headers=headers, json=payload, timeout=15
        )
        if r.ok:
            print(f"Close CRM: Added {user.get('name')} as Vessel Elder")
    except Exception as e:
        print(f"Close CRM error: {e}")

def notify_sydney(msg):
    if not TELEGRAM_TOKEN:
        return
    try:
        _tg_emergency_only("[suppressed direct call]")
    except:
        pass

def run_referral_check(referral_events):
    """
    Main runner
    referral_events: list of {user_id, name, email, goal_type, day_count,
                               referral_count, previous_referral_count,
                               stripe_customer_id, current_badges}
    """
    print(f"[{datetime.utcnow().isoformat()}] VesselReferralAgent running for {len(referral_events)} users")

    processed = []
    milestone_hits = 0

    for user in referral_events:
        uid     = user.get("user_id")
        name    = user.get("name", "Vessel")
        count   = user.get("referral_count", 0)
        prev    = user.get("previous_referral_count", 0)
        stripe_id = user.get("stripe_customer_id", "")
        goal    = user.get("goal_type", "purpose")

        milestone = get_milestone_for_count(count, prev)
        if not milestone:
            continue

        badge        = milestone["badge"]
        months       = milestone["reward_months"]
        reward_label = milestone["reward_label"]

        print(f"  MILESTONE: {name} hit {count} referrals → {badge}")

        # Grant Stripe credit
        credit_ok = grant_stripe_credit(stripe_id, months, f"{badge} badge — {count} referrals")

        # Generate message
        congrats = generate_congrats_message(name, badge, reward_label, count, goal)

        # Sync to Close CRM for Elder+
        if badge in ["Vessel Elder", "Founding Member"]:
            sync_to_close_crm({**user, "badge": badge})

        result = {
            "user_id":      uid,
            "name":         name,
            "badge":        badge,
            "referral_count": count,
            "reward_label": reward_label,
            "credit_granted": credit_ok,
            "congrats_message": congrats,
            "processed_at": datetime.utcnow().isoformat()
        }
        processed.append(result)
        milestone_hits += 1

        # Notify Sydney on Elder/Founding
        if badge in ["Vessel Elder", "Founding Member"]:
            notify_sydney(
                f"🏆 <b>Vessel {badge} Unlocked</b>\n"
                f"User: {name}\n"
                f"Referrals: {count}\n"
                f"Reward: {reward_label}\n"
                f"CRM: Synced to Close"
            )

        time.sleep(0.3)

    print(f"Referral check complete: {milestone_hits} milestones processed")
    return processed

def start_webhook_server():
    try:
        from flask import Flask, request as freq, jsonify
    except ImportError:
        os.system("/root/penelope_env/bin/pip install flask --quiet")
        from flask import Flask, request as freq, jsonify

    app = Flask(__name__)

    @app.route("/vessel/referral", methods=["POST"])
    def referral_endpoint():
        data = freq.get_json() or {}
        if data.get("secret") != "sydney123":
            return jsonify({"error": "unauthorized"}), 401
        events = data.get("referral_events", [])
        results = run_referral_check(events)
        return jsonify({"processed": results, "count": len(results)})

    print("VesselReferralAgent webhook server starting on port 5104")
    app.run(host="0.0.0.0", port=5104)

if __name__ == "__main__":
    import sys
    if "--server" in sys.argv:
        start_webhook_server()
    else:
        test = [{
            "user_id": "u1", "name": "Maya", "email": "maya@test.com",
            "goal_type": "wealth", "day_count": 89,
            "referral_count": 3, "previous_referral_count": 2,
            "stripe_customer_id": "cus_test123"
        }]
        results = run_referral_check(test)
        print(json.dumps(results, indent=2))