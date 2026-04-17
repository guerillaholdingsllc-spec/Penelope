# ── TELEGRAM GATE (prepended by Penelope self-healer) ──────────────────────
import os as _tg_os, requests as _tg_req, datetime as _tg_dt
_tg_orig_post = _tg_req.post
def _tg_gated_post(url, *a, **kw):
    if "api.telegram.org" in str(url):
        _data = str(kw.get("json", kw.get("data", ""))).lower()
        _rev = any(x in _data for x in ["revenue confirmed","sale confirmed","payment received","paid $","new sale"])
        _crit = "🚨" in str(kw.get("json",{})) and any(x in _data for x in ["system down","cannot restart","disk full","out of memory"])
        if not _rev and not _crit:
            class _FakeResp:
                status_code=200
                def json(self): return {}
            return _FakeResp()
    return _tg_orig_post(url, *a, **kw)
_tg_req.post = _tg_gated_post
# ── END GATE ───────────────────────────────────────────────────────────────

"""
vessel_content_agent.py
Generates milestone cards, affirmation pools, community content
Uses WaveSpeed for images, Gemini for copy, verify_output QC gate
Runs Tuesday + Friday 9AM
"""
import os, json, requests, time, random
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
except:
    pass

GOOGLE_API_KEY   = VAULT.get("GOOGLE_API_KEY", "")
WAVESPEED_KEY    = VAULT.get("WAVESPEED_API_KEY", "91a8b92b3e6661054bc7a4f84ce02f117ee5cf329a1f7c204982d40b702db11a")
TELEGRAM_TOKEN   = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT    = "6183015901"
WAVESPEED_URL    = "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-dev"

GOAL_COLORS = {
    "wealth":  "#10b981",  # emerald
    "health":  "#f43f5e",  # rose
    "body":    "#f59e0b",  # amber
    "love":    "#ec4899",  # pink
    "purpose": "#8b5cf6",  # violet
    "peace":   "#14b8a6",  # teal
}

MILESTONE_DAYS = [7, 30, 66, 100, 180, 270, 365]

def gemini(prompt, temperature=0.7, max_tokens=2000):
    try:
        client = _get_client()
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r, "text", "") or ""
    except Exception as e:
        print(f"Gemini error: {e}")
        return ""

def generate_wavespeed_image(prompt_text):
    """Generate milestone card image via WaveSpeed"""
    try:
        r = requests.post(
            WAVESPEED_URL,
            headers={"Authorization": f"Bearer {WAVESPEED_KEY}",
                     "Content-Type": "application/json"},
            json={"prompt": prompt_text, "size": "1024x1024", "num_images": 1},
            timeout=30
        )
        if r.ok:
            data = r.json()
            job_id = data.get("id") or data.get("data", {}).get("id")
            if job_id:
                # Poll for result
                for _ in range(20):
                    time.sleep(3)
                    poll = requests.get(
                        f"https://api.wavespeed.ai/api/v3/predictions/{job_id}/result",
                        headers={"Authorization": f"Bearer {WAVESPEED_KEY}"},
                        timeout=15
                    )
                    if poll.ok:
                        result = poll.json()
                        status = result.get("data", {}).get("status", "")
                        if status == "completed":
                            outputs = result.get("data", {}).get("outputs", [])
                            return outputs[0] if outputs else None
                        elif status == "failed":
                            break
    except Exception as e:
        print(f"WaveSpeed error: {e}")
    return None

def generate_affirmation_pool(goal_type, count=30):
    """Generate 30 affirmations for a goal type"""
    prompt = f"""Generate {count} unique daily affirmations for someone manifesting {goal_type}.

Rules:
- Present tense, identity-based ("I am", "I have", "I create")
- Under 15 words each
- Varied — not repetitive
- Elevation language only
- No toxic positivity or hollow phrases
- Grounded and believable

Reply as JSON array of strings."""

    text = gemini(prompt, max_tokens=1000)
    try:
        start = text.find("[")
        end   = text.rfind("]") + 1
        return json.loads(text[start:end])
    except:
        return [f"I am aligned with my {goal_type} manifestation."] * count

def generate_milestone_content(day_number, goal_type):
    """Generate content package for a milestone day"""
    milestones_context = {
        7:   "First week complete. The protocol has begun.",
        30:  "30 days. Baseline shifting. First transformation snapshot.",
        66:  "66 days. Automaticity threshold crossed. This is now a habit.",
        100: "Day 100. Triple digits. The journey is undeniable.",
        180: "Halfway through the year. The activated self is visible.",
        270: "270 days. Three quarters. Legacy work begins.",
        365: "365 days. Year complete. A Vessel fully manifested."
    }

    context = milestones_context.get(day_number, f"Day {day_number} milestone")
    color   = GOAL_COLORS.get(goal_type, "#c9a84c")

    # Social caption
    caption_prompt = f"""Write a milestone social media post for the Vessel community.

Day: {day_number} | Goal: {goal_type} | Context: {context}

Rules:
- Anonymous (no personal details)
- Under 30 words
- Mysterious and magnetic — makes outsiders want to know what Vessel is
- No hashtags, no emojis in text
- Add one sacred symbol at the end: ✦
- Format: "Day [number]. [one powerful sentence]. ✦"

Reply with ONLY the post."""

    caption = gemini(caption_prompt, max_tokens=100, temp=0.8)
    if not caption:
        caption = f"Day {day_number}. {context} ✦"

    # Image prompt for WaveSpeed
    image_prompt = (
        f"Minimal sacred geometry art, dark cosmic background, gold sacred geometry, "
        f"the number {day_number} in elegant gold typography, "
        f"color accent {color}, mystical and premium aesthetic, "
        f"no text except the number, ultra minimalist"
    )

    # Generate image
    print(f"  Generating WaveSpeed image for Day {day_number}...")
    image_url = generate_wavespeed_image(image_prompt)

    return {
        "day":        day_number,
        "goal_type":  goal_type,
        "context":    context,
        "caption":    caption,
        "image_url":  image_url,
        "color":      color,
        "created_at": datetime.utcnow().isoformat()
    }

def generate_daily_action_prompts(goal_type, income_bracket, count=30):
    """Generate 30 daily action prompts calibrated to income"""
    free_constraint = income_bracket in ["Under $25k", "$25-50k"]
    cost_note = "All actions must be free or cost under $5." if free_constraint else "Actions can include small investments under $50."

    prompt = f"""Generate {count} daily micro-action prompts for someone manifesting {goal_type}.

{cost_note}
Income bracket: {income_bracket}

Each action should:
- Take under 7 minutes
- Be specific and doable today
- Build momentum toward {goal_type}
- Be varied across different life domains
- Use "Today:" prefix

Reply as JSON array of strings."""

    text = gemini(prompt, max_tokens=1500, temp=0.7)
    try:
        start = text.find("[")
        end   = text.rfind("]") + 1
        return json.loads(text[start:end])
    except:
        return [f"Today: Take one intentional step toward your {goal_type}."] * count

def run_content_generation(config):
    """
    Main runner
    config: {goal_types: [], milestone_days: [], income_brackets: []}
    """
    print(f"[{datetime.utcnow().isoformat()}] VesselContentAgent running")

    output = {
        "milestone_cards": [],
        "affirmation_pools": {},
        "action_prompts": {},
        "generated_at": datetime.utcnow().isoformat()
    }

    # Generate milestone cards
    goal_types     = config.get("goal_types", list(GOAL_COLORS.keys()))
    milestone_days = config.get("milestone_days", [66, 100, 180])

    for day in milestone_days:
        for goal in goal_types[:2]:  # limit for speed
            print(f"  Generating Day {day} card for {goal}...")
            card = generate_milestone_content(day, goal)
            output["milestone_cards"].append(card)
            time.sleep(1)

    # Generate affirmation pools
    for goal in goal_types:
        print(f"  Generating affirmations for {goal}...")
        output["affirmation_pools"][goal] = generate_affirmation_pool(goal, count=15)
        time.sleep(0.5)

    # Save output
    output_path = f"/root/workspace/Penelope/shipped/vessel_content_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Content saved: {output_path}")

    # Notify Sydney
    if TELEGRAM_TOKEN:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT,
                    "text": (
                        f"🎨 <b>Vessel Content Generated</b>\n"
                        f"Milestone cards: {len(output['milestone_cards'])}\n"
                        f"Affirmation pools: {len(output['affirmation_pools'])} goals\n"
                        f"Saved: {output_path}"
                    ),
                    "parse_mode": "HTML"
                },
                timeout=10
            )
        except:
            pass

    return output

if __name__ == "__main__":
    config = {
        "goal_types": ["wealth", "peace"],
        "milestone_days": [66],
        "income_brackets": ["$50-75k"]
    }
    result = run_content_generation(config)
    print(f"Done. Cards: {len(result['milestone_cards'])}")
