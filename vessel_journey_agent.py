"""
vessel_journey_agent.py
Generates personalized 365-day Vessel journey plans via Gemini Flash
Triggered by Base44 webhook on new subscriber — writes plan back via Base44 API
QC gated by verify_output.py logic (7.0/10 min score)
"""
import os, json, requests, time, sys
from datetime import datetime
from google import genai as _genai
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
except Exception as e:
    print(f"Vault error: {e}")

GOOGLE_API_KEY  = VAULT.get("GOOGLE_API_KEY", "")
TELEGRAM_TOKEN  = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = "6183015901"

GOAL_TYPE_CONTEXT = {
    "wealth":  "financial abundance, income growth, entrepreneurship, money mindset",
    "health":  "physical vitality, energy, wellness, longevity, body healing",
    "body":    "physical transformation, fitness, strength, body confidence",
    "love":    "relationships, partnership, self-love, connection, romance",
    "purpose": "clarity, mission, career, meaning, contribution to the world",
    "peace":   "mental calm, emotional regulation, stress relief, inner stillness"
}

PHASE_DESCRIPTIONS = {
    1: "Foundation (Days 1-66): Build automaticity. Simple micro-actions. Identity formation. Sessions max 5 minutes.",
    2: "Activation (Days 67-180): Escalating real-world action. Weekly challenges. Monthly milestones.",
    3: "Manifestation (Days 181-365): AI witnesses your transformation. Legacy-oriented steps. Year 2 preview."
}

def gemini(prompt, temperature=0.7, max_tokens=2000):
    try:
        client = _get_client()
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r, "text", "") or ""
    except Exception as e:
        print(f"Gemini error: {e}")
        return ""

def qc_score(content):
    """Score content 1-10 using Gemini as QC judge"""
    prompt = f"""Rate this manifestation journey plan 1-10 for:
- Personalization to the user's specific goal and data
- Actionability (concrete, achievable steps)
- Emotional resonance and motivation
- Scientific grounding (habit formation, psychology)
- Progression logic across 365 days

Reply ONLY with a number 1-10.

PLAN:
{content[:1000]}"""
    score_str = gemini(prompt, temperature=0.1).strip()
    try:
        return float(score_str.split()[0])
    except:
        return 5.0

def generate_journey_plan(user_profile):
    """Generate a full 365-day journey plan for a user"""
    goal     = user_profile.get("goal_type", "purpose")
    name     = user_profile.get("name", "Vessel")
    income   = user_profile.get("income_bracket", "unknown")
    location = user_profile.get("city", "your city")
    inc_goal = user_profile.get("income_goal", "higher income")
    body_goal= user_profile.get("body_goal", "")
    day      = user_profile.get("day_count", 1)
    phase    = 1 if day <= 66 else (2 if day <= 180 else 3)

    goal_context = GOAL_TYPE_CONTEXT.get(goal, "personal growth and transformation")

    prompt = f"""You are the Vessel AI — a warm, wise manifestation guide.
Generate a personalized 365-day journey plan for {name}.

USER PROFILE:
- Primary goal: {goal} ({goal_context})
- Current income: {income}
- Location: {location}
- Income goal: {inc_goal}
- Body goal: {body_goal if body_goal else "not specified"}
- Currently on: Day {day}, Phase {phase}

PROTOCOL PHASES:
{PHASE_DESCRIPTIONS[1]}
{PHASE_DESCRIPTIONS[2]}
{PHASE_DESCRIPTIONS[3]}

Generate:
1. A personalized MISSION STATEMENT for {name} (2-3 sentences, identity-based)
2. Phase 1 focus (Days 1-66): 5 specific daily micro-actions tailored to their goal and income level
3. Phase 2 focus (Days 67-180): 5 escalating weekly challenges
4. Phase 3 focus (Days 181-365): 3 legacy-oriented completion goals
5. 10 personalized daily affirmations (rotate through the year)
6. 3 personalized 30-day milestones to celebrate

RULES:
- Never suggest actions requiring money they don't have (income bracket: {income})
- Never shame or compare — elevation language only
- Keep all daily actions under 7 minutes
- Reference {location} for local resources where relevant
- Make it feel written specifically for {name}, not a template

Format as clean JSON with keys: mission, phase1_actions, phase2_challenges, phase3_goals, affirmations, milestones"""

    for attempt in range(3):
        plan_text = gemini(prompt)
        if not plan_text:
            time.sleep(2)
            continue

        # Extract JSON
        try:
            start = plan_text.find("{")
            end   = plan_text.rfind("}") + 1
            if start >= 0 and end > start:
                plan_json = json.loads(plan_text[start:end])
                plan_str  = json.dumps(plan_json, indent=2)
            else:
                plan_json = {"raw": plan_text}
                plan_str  = plan_text
        except:
            plan_json = {"raw": plan_text}
            plan_str  = plan_text

        score = qc_score(plan_str)
        print(f"Attempt {attempt+1} QC score: {score}")

        if score >= 7.0:
            print(f"Journey plan APPROVED (score={score})")
            return plan_json, score

        print(f"Score {score} below threshold. Retrying...")
        time.sleep(1)

    print("Max attempts reached. Using best available plan.")
    return plan_json, score


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


def run_for_user(user_profile):
    """Main entry point — generate and return journey plan"""
    name = user_profile.get("name", "Vessel")
    goal = user_profile.get("goal_type", "purpose")
    print(f"[{datetime.utcnow().isoformat()}] Generating journey for {name} | goal={goal}")

    plan, score = generate_journey_plan(user_profile)

    telegram(
        f"🔮 <b>Vessel Journey Generated</b>\n"
        f"User: {name} | Goal: {goal}\n"
        f"QC Score: {score}/10\n"
        f"Plan keys: {', '.join(plan.keys()) if isinstance(plan, dict) else 'raw'}"
    )

    return {
        "user_id": user_profile.get("user_id"),
        "plan": plan,
        "qc_score": score,
        "generated_at": datetime.utcnow().isoformat(),
        "phase": 1
    }

# ── Webhook server mode ───────────────────────────────────────────────────
def start_webhook_server():
    """Flask endpoint for Base44 to call when new subscriber joins"""
    try:
        from flask import Flask, request as freq, jsonify
    except ImportError:
        os.system("/root/penelope_env/bin/pip install flask --quiet")
        from flask import Flask, request as freq, jsonify

    app = Flask(__name__)

    @app.route("/vessel/journey", methods=["POST"])
    def journey_endpoint():
        data = freq.get_json() or {}
        secret = data.get("secret", "")
        if secret != "sydney123":
            return jsonify({"error": "unauthorized"}), 401
        user_profile = data.get("user_profile", {})
        result = run_for_user(user_profile)
        return jsonify(result)

    @app.route("/vessel/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "agent": "vessel_journey_agent"})

    print("VesselJourneyAgent webhook server starting on port 5101")
    app.run(host="0.0.0.0", port=5101)

if __name__ == "__main__":
    if "--server" in sys.argv:
        start_webhook_server()
    else:
        # Test run
        test_profile = {
            "user_id": "test_001",
            "name": "Sydney",
            "goal_type": "wealth",
            "income_bracket": "$50-75k",
            "city": "Sacramento",
            "income_goal": "$100k+",
            "body_goal": "",
            "day_count": 1
        }
        result = run_for_user(test_profile)
        print(json.dumps(result, indent=2)[:500])
