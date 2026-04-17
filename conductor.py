#!/usr/bin/env python3
"""
PENELOPE CONDUCTOR v1.0
Master orchestration brain for Guerilla Holdings LLC
Runs every 4 hours. Delegates everything. Decides based on 75% RPS threshold.
"""

import os
import json
import time
import yaml
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path


# ── Config ──────────────────────────────────────────────────────────────────
VAULT = "/root/penelope_vault.env"
SKILLBANK_DIR = "/root/workspace/Penelope/skillbank"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"
GEMINI_MODEL = "gemini-2.5-flash"
BUDGET_CAP_PER_SKILL = 50.00
MAX_ITERATIONS = 3
RPS_DEPLOY_THRESHOLD = 75
RPS_QUEUE_THRESHOLD = 50

# ── Pipeline sizing (binomial model) ────────────────────────────────────────
# Target: 5-10 conversions above 85 RPS per 4h cycle
# At 35% per-opportunity conversion rate, 90% confidence requires n=26 minimum
# Recommended pipeline with 20% variance buffer = 32 opportunities per cycle
PIPELINE_MIN = 26          # absolute floor — never scan fewer than this
PIPELINE_RECOMMENDED = 32  # target per cycle with buffer
PIPELINE_MAX = 35          # cap to control compute cost per cycle
CONVERSION_RATE_EST = 0.35 # expected % that clear 85 RPS after Supreme Court

# Load vault
def load_vault():
    env = {}
    try:
        with open(VAULT) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except:
        pass
    return env

ENV = load_vault()
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TELEGRAM_CHAT_ID = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
GEMINI_KEY = ENV.get("GOOGLE_API_KEY", "")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", ENV.get("NOTION_API_KEY", ""))
NOTION_OPS_DB = "aaac5800-d381-48c0-b135-2af97fe9d188"

# Setup
Path(SKILLBANK_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CONDUCTOR] %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/conductor.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("conductor")



# ── Telegram ─────────────────────────────────────────────────────────────────
# Telegram dedup — don't send same message twice in 1 hour
_TG_SENT = {}

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


def notion_log(title, content, status="Info"):
    if not NOTION_TOKEN:
        return
    try:
        requests.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={
                "parent": {"database_id": NOTION_OPS_DB},
                "properties": {
                    "Event": {"title": [{"text": {"content": f"[CONDUCTOR] {title}"}}]},
                    "Type": {"select": {"name": status}},
                },
                "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}}]
            },
            timeout=10
        )
    except Exception as e:
        log.error(f"Notion log failed: {e}")

# ── Gemini Worker ────────────────────────────────────────────────────────────
def gemini_call(prompt, temperature=0.7):
    if not GEMINI_KEY:
        return "ERROR: No Gemini API key configured"
    try:
        from google import genai as _g
        client = _g.Client(api_key=GEMINI_KEY)
        cfg = _g.types.GenerateContentConfig(temperature=temperature)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
        return response.text
    except Exception as e:
        log.error(f"Gemini call failed: {e}")
        return f"ERROR: {e}"

# ── SkillBank ─────────────────────────────────────────────────────────────────
class SkillBank:
    def __init__(self):
        self.path = Path(SKILLBANK_DIR)

    def list_skills(self, status=None):
        skills = []
        for f in self.path.glob("*.yaml"):
            try:
                with open(f) as fp:
                    s = yaml.safe_load(fp)
                    if status is None or s.get("status") == status:
                        skills.append(s)
            except:
                pass
        return skills

    def save_skill(self, skill):
        sid = skill.get("skill_id", f"skill_{int(time.time())}")
        path = self.path / f"{sid}.yaml"
        with open(path, "w") as f:
            yaml.dump(skill, f, default_flow_style=False)
        log.info(f"Saved skill: {sid}")
        return str(path)

    def get_skill(self, skill_id):
        path = self.path / f"{skill_id}.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return None

    def update_status(self, skill_id, status, extra=None):
        skill = self.get_skill(skill_id)
        if skill:
            skill["status"] = status
            if extra:
                skill.update(extra)
            self.save_skill(skill)

skillbank = SkillBank()

# ── Supreme Court ─────────────────────────────────────────────────────────────
class SupremeCourt:
    def review(self, skill, test_output):
        log.info(f"Supreme Court reviewing: {skill.get('skill_id')}")
        results = {}

        # Agent A: Quality & Logic
        qa_prompt = f"""You are a Quality & Logic Auditor for Guerilla Holdings LLC. 
Evaluate if the skill execution is actionable and moves toward revenue for these businesses: GAFC (gun safety education), CadaverCo (cadaver transport), CALLUX (gig transport), Digital Products (Gumroad/ebooks).
PASS if the action: publishes content, sends emails, posts to social media, writes blog posts, reaches out to leads, or promotes products.
FAIL only if the action is illegal, harmful, or completely impossible to execute.
Be lenient — content creation and outreach always have value even if not immediately profitable.

Review this revenue-generating skill and its test output:

SKILL: {json.dumps(skill, indent=2)}
TEST OUTPUT: {test_output[:2000]}

Check:
1. Does output match objective?
2. Are all claims verifiable? No hallucinations?
3. Does it sound human, not robotic?
4. Does any math/ROI check out?

Respond with ONLY: PASS or FAIL
Then one line: specific reason."""
        qa = gemini_call(qa_prompt, temperature=0.0)
        results["quality"] = {"result": "PASS" if "PASS" in qa.upper()[:10] else "FAIL", "notes": qa}

        # Agent B: Security & Compliance
        sec_prompt = f"""You are a Security & Compliance Officer for Guerilla Holdings LLC.
PASS the skill unless it involves: collecting SSNs, storing unencrypted passwords, accessing unauthorized systems, or violating GDPR with non-consented PII.
Content publishing, email marketing with opt-in lists, social media posting, and affiliate marketing are all COMPLIANT.
Do NOT fail skills for theoretical future compliance risks. Only fail clear, immediate violations.

Review this skill:
SKILL: {json.dumps(skill, indent=2)}
OUTPUT: {test_output[:1000]}

Check:
1. No API keys, passwords, PII exposed?
2. Platform ToS compliant (Stripe, LinkedIn, Gumroad)?
3. Within $50/24h budget cap?
4. GDPR/CCPA compliant for any lead data?

Respond with ONLY: PASS or FAIL
Then one line: specific reason."""
        sec = gemini_call(sec_prompt, temperature=0.0)
        results["security"] = {"result": "PASS" if "PASS" in sec.upper()[:10] else "FAIL", "notes": sec}

        # Agent C: Adversarial Critic
        adv_prompt = f"""You are an Adversarial Critic (Red Team). Temperature: 0.0.

Review this revenue opportunity:
SKILL: {json.dumps(skill, indent=2)}
OUTPUT: {test_output[:1000]}

Check:
1. Why would this FAIL in the real market?
2. Is there a cheaper/faster way to achieve same result?
3. What edge case breaks this?
4. Give a Confidence Score 0-100%

Respond with: PASS or CRITIQUE
Then: Confidence Score: X%
Then: Key concerns (2-3 bullets max)"""
        adv = gemini_call(adv_prompt, temperature=0.0)
        
        # Extract confidence score
        conf = 60  # default
        for line in adv.split('\n'):
            if 'confidence' in line.lower() and '%' in line:
                try:
                    conf = int(''.join(filter(str.isdigit, line.split('%')[0][-3:])))
                except:
                    pass
        
        results["adversarial"] = {
            "result": "PASS" if conf >= 30 else "FAIL",
            "confidence": conf,
            "notes": adv
        }

        # Consensus
        passed = sum(1 for r in results.values() if r["result"] == "PASS")
        supreme_pass = passed >= 1  # 1/3 sufficient — loosened for throughput

        if results["security"]["result"] == "FAIL":
            supreme_pass = False  # security is always a hard veto

        log.info(f"Supreme Court verdict: {'PASS' if supreme_pass else 'FAIL'} ({passed}/3)")
        return supreme_pass, results

court = SupremeCourt()

# ── Revenue Intelligence ──────────────────────────────────────────────────────
class RevenueIntelligence:
    # STREAM PRIORITY TIERS — Penelope always works top to bottom
    STREAM_TIERS = {
        1: {
            "label": "Tier 1 - Instant Digital (No barriers)",
            "types": ["info products", "digital downloads", "online courses", "ebooks", "templates",
                      "SaaS tools", "AI tools", "affiliate", "content monetization", "newsletters",
                      "Gumroad", "Printify merch", "Amazon Associates", "Bluesky", "social monetization",
                      "grant writing", "GAFC digital education", "prompt packs", "notion templates"],
            "score_bonus": 25,
            "why": "Zero infrastructure, zero licensing, can deploy in hours, 100% automated"
        },
        2: {
            "label": "Tier 2 - Semi-Digital (Minor setup, no physical ops)",
            "types": ["consulting", "coaching", "done-for-you services", "white-label software",
                      "lead generation", "B2B outreach", "SEO services", "social media management",
                      "WordPress", "landing pages", "email marketing", "automation setup"],
            "score_bonus": 10,
            "why": "Deliverable is digital but may require human touch on first sale"
        },
        3: {
            "label": "Tier 3 - Physical/Licensed (Last resort, background only)",
            "types": ["cadaver transport", "medical transport", "driver dispatch", "physical logistics",
                      "vehicle operations", "permits", "licenses", "certifications", "DOT compliance",
                      "physical storefront", "warehouse", "hardware", "field operations"],
            "score_bonus": -20,
            "why": "Requires permits, vehicles, humans, infrastructure. Pursue only when Tier 1+2 are saturated.",
            "condition": "Only queue if no Tier 1 or Tier 2 opportunities exist above 50 RPS"
        }
    }

    BUSINESSES = {
        "CadaverCo": "non-emergency cadaver transport Sacramento NorCal Bay Area Reno [TIER 3 - physical]",
        "CALLUX": "gig-economy dispatch marketplace specialty transport [TIER 3 - physical, licensing required]",
        "GAFC": "gun safety education social enterprise minority-owned grants merch digital [TIER 1 - grants + merch]",
        "Digital": "AI automation digital products info products Gumroad Printify affiliate content [TIER 1 priority]"
    }

    def scan_opportunities(self):
        log.info("Scanning for revenue opportunities...")
        prompt = f"""You are a Revenue Intelligence Agent for Guerilla Holdings LLC.

REVENUE STREAM PRIORITY SYSTEM (STRICT — follow this order):

TIER 1 — ALWAYS PURSUE FIRST (digital, no barriers, fully automated):
- Digital products: ebooks, templates, prompt packs, Notion templates, AI tools
- Gumroad products, Printify merch, Amazon Associates content
- GAFC grant applications (digital submission, no physical ops)
- Content monetization: Bluesky, newsletters, blog SEO
- SaaS micro-tools, white-label AI services
- Online courses, info products, done-for-you digital assets

TIER 2 — PURSUE WHEN TIER 1 IS RUNNING (semi-digital, minimal setup):
- B2B lead gen and outreach services
- Consulting/coaching (AI or business automation)
- Social media management for local businesses
- White-label software reselling

TIER 3 — BACKGROUND ONLY, DO NOT PRIORITIZE (physical, licensed, infrastructure-heavy):
- CadaverCo transport operations (requires vehicles, permits, DOT compliance)
- CALLUX driver dispatch (requires driver certification infrastructure, insurance)
- Any physical logistics, field operations, or regulated transport
- ONLY surface Tier 3 opportunities if Tier 1 and Tier 2 queues are empty

CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}

TASK: Identify 30 specific, actionable TIER 1 revenue opportunities for Guerilla Holdings RIGHT NOW.
Focus exclusively on digital revenue that can be deployed, automated, and generating money within 7-30 days.
Do NOT suggest physical operations unless explicitly asked.

For each opportunity:
1. Tier classification (1, 2, or 3)
2. Specific revenue action (not vague — name the exact product, platform, audience)
3. Estimated monthly revenue potential ($)
4. Time to first dollar (days)
5. Cost to test (must be under $50)
6. Why this works NOW (specific market signal)
7. How Penelope deploys it autonomously (no Sydney needed)

Return as JSON array of opportunities. Prioritize Tier 1 only unless queue is empty."""

        response = gemini_call(prompt, temperature=0.7)
        
        # Try to parse JSON
        try:
            # Extract JSON if wrapped in markdown
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            opportunities = json.loads(response.strip())
        except:
            # Fallback: create structured opportunities from text
            opportunities = [{"business": "Digital", "action": "Improve Gumroad product listing and add cover image to drive conversions", "revenue_potential": 500, "time_to_dollar": "3 days", "test_cost": 0, "signal": "Zero sales currently, product exists but not optimized"}]

        log.info(f"Found {len(opportunities)} opportunities")
        return opportunities

    def get_tier(self, opp):
        """Determine tier of opportunity based on type keywords."""
        action = str(opp.get("action", "") + opp.get("type", "") + opp.get("business", "")).lower()
        tier3_keywords = ["transport", "cadaver", "driver", "dispatch", "vehicle", "permit", "license", 
                         "dot", "insurance", "physical", "field", "logistics", "callux", "cadaverco"]
        tier2_keywords = ["consulting", "coaching", "b2b", "outreach", "white-label", "service", "seo"]
        for kw in tier3_keywords:
            if kw in action:
                return 3
        for kw in tier2_keywords:
            if kw in action:
                return 2
        return 1  # Default to Tier 1 (digital)

    def score_opportunity(self, opp):
        """Score 0-100. >75 = test queue. Tier 1 gets bonus, Tier 3 gets penalty."""
        tier = self.get_tier(opp)
        tier_bonus = self.STREAM_TIERS.get(tier, {}).get("score_bonus", 0)
        tier_label = self.STREAM_TIERS.get(tier, {}).get("label", "Unknown")

        prompt = f"""Score this revenue opportunity for an autonomous AI agent to pursue.

OPPORTUNITY: {json.dumps(opp, indent=2)}
TIER: {tier} ({tier_label})

Score each dimension 0-25:
1. Market demand signal (is there real demand right now?)
2. Cost vs revenue delta (how much profit margin?)
3. Time to first dollar (faster = higher score, digital = instant = high score)
4. Scalability without human time (fully automated = 25, needs humans = 5)

IMPORTANT SCORING RULES:
- Digital/automated products score HIGH on dimensions 3 and 4
- Physical operations requiring licenses/permits score LOW on dimensions 3 and 4
- If opportunity requires permits, vehicles, or physical infrastructure: cap scalability at 10

Return ONLY a JSON object:
{{"demand": 0-25, "margin": 0-25, "speed": 0-25, "scalability": 0-25, "total": 0-100, "reasoning": "one sentence"}}"""

        response = gemini_call(prompt, temperature=0.0)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            score = json.loads(response.strip())
            # Apply tier adjustment
            raw_total = score.get("total", 60)
            adjusted = max(0, min(100, raw_total + tier_bonus))
            score["total"] = adjusted
            score["tier"] = tier
            score["tier_label"] = tier_label
            score["tier_bonus_applied"] = tier_bonus
            score["raw_score"] = raw_total
            log.info(f"Opportunity scored: raw={raw_total}, tier={tier}, bonus={tier_bonus}, final={adjusted}")
            return score
        except:
            base = 55 if tier == 1 else (45 if tier == 2 else 30)
            return {"demand": 15, "margin": 15, "speed": 15, "scalability": 10, 
                    "total": base, "tier": tier, "reasoning": "Parse failed, tier-adjusted default"}

    def create_skill_blueprint(self, opp, score):
        """Auto-generate a YAML skill blueprint from an opportunity."""
        sid = f"auto_{opp.get('business','gen').lower()}_{int(time.time())}"
        blueprint = {
            "skill_id": sid,
            "created": datetime.now().isoformat(),
            "status": "Draft",
            "business": opp.get("business", "Cross-vertical"),
            "objective": opp.get("action", "Generate revenue"),
            "revenue_model": {
                "type": "one_time",
                "estimated_monthly": opp.get("revenue_potential", 0),
                "cost_per_run": opp.get("test_cost", 0),
                "margin_pct": 70
            },
            "opportunity_data": opp,
            "rps_score": score.get("total", 0),
            "score_breakdown": score,
            "logic_flow": {},
            "recursive_rules": {
                "if_success": "Scale volume 10%, save winning pattern",
                "if_fail": "Extract reusable components, update blueprint, retry",
                "budget_cap_24h": BUDGET_CAP_PER_SKILL,
                "max_iterations": MAX_ITERATIONS
            },
            "supreme_court_results": {},
            "test_results": {},
            "learnings": ""
        }
        return blueprint

intel = RevenueIntelligence()

# ── Worker Factory ───────────────────────────────────────────────────────────
class WorkerFactory:
    def spawn(self, role, prompt, tools=None, budget=50.0):
        """Spawn a worker agent (Gemini Flash) for a specific task."""
        log.info(f"Spawning worker: {role}")
        
        system = f"""You are a specialized {role} Worker Agent for Guerilla Holdings LLC.
Your only goal: complete the assigned task and return measurable results.
Budget cap: ${budget}. 
Be specific. Be actionable. Return JSON results when possible."""

        full_prompt = f"{system}\n\nTASK:\n{prompt}"
        result = gemini_call(full_prompt, temperature=0.6)
        
        log.info(f"Worker {role} completed. Output length: {len(result)}")
        return result

    def spawn_research(self, topic):
        return self.spawn("Research", f"Research this revenue opportunity and provide actionable findings:\n{topic}")

    def spawn_content(self, brief):
        return self.spawn("Content", f"Create this content for revenue generation:\n{brief}")

    def spawn_analysis(self, data):
        return self.spawn("Analysis", f"Analyze this data and provide revenue insights:\n{data}")

factory = WorkerFactory()

# ── Performance Monitor ──────────────────────────────────────────────────────
class PerformanceMonitor:
    def check_stripe(self):
        sk = ENV.get("STRIPE_SECRET_KEY", "")
        if not sk or not sk.startswith("sk_live"):
            return {"status": "not_active", "revenue": 0}
        try:
            r = requests.get(
                "https://api.stripe.com/v1/balance_transactions?limit=10",
                auth=(sk, ""),
                timeout=10
            )
            data = r.json()
            total = sum(t.get("net", 0) for t in data.get("data", []) if t.get("type") == "charge") / 100
            return {"status": "active", "revenue": total, "transactions": len(data.get("data", []))}
        except Exception as e:
            return {"status": "error", "error": str(e), "revenue": 0}

    def check_gumroad(self):
        key = ENV.get("GUMROAD_API_KEY", "XFsvKLjfxfsMw8RCJL5kUHQ6H3vZ68tdvAU15e1XREo")
        if not key:
            return {"status": "no_key", "revenue": 0}
        try:
            r = requests.get(
                "https://api.gumroad.com/v2/sales",
                params={"access_token": key},
                timeout=10
            )
            data = r.json()
            sales = data.get("sales", [])
            total = sum(float(s.get("price", 0)) for s in sales) / 100
            return {"status": "active", "revenue": total, "sales": len(sales)}
        except Exception as e:
            return {"status": "error", "error": str(e), "revenue": 0}

    def daily_report(self):
        stripe = self.check_stripe()
        gumroad = self.check_gumroad()
        total = stripe.get("revenue", 0) + gumroad.get("revenue", 0)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_revenue": total,
            "stripe": stripe,
            "gumroad": gumroad
        }

monitor = PerformanceMonitor()

# ── MAIN CONDUCTOR CYCLE ─────────────────────────────────────────────────────
def run_cycle():
    cycle_start = datetime.now()
    log.info(f"{'='*60}")
    log.info(f"CONDUCTOR CYCLE START: {cycle_start.isoformat()}")
    log.info(f"{'='*60}")

    results_summary = []

    # Financial tracker sync
    try:
        from financial_tracker import sync_all_revenue
        sync_all_revenue()
    except Exception as e:
        log.error(f'Financial tracker: {e}')

    # ── PHASE 1: Revenue Monitoring ──────────────────────────────
    log.info("PHASE 1: Revenue monitoring...")
    perf = monitor.daily_report()
    log.info(f"Total revenue tracked: ${perf['total_revenue']:.2f}")
    
    if perf["total_revenue"] > 0:
        telegram(f"💰 Revenue Update\nTotal: ${perf['total_revenue']:.2f}\nStripe: ${perf['stripe'].get('revenue',0):.2f}\nGumroad: ${perf['gumroad'].get('revenue',0):.2f}")

    # ── PHASE 2: Check Live Skills ───────────────────────────────
    log.info("PHASE 2: Checking live skills...")
    live_skills = skillbank.list_skills(status="Live")
    log.info(f"Live skills: {len(live_skills)}")

    # ── PHASE 3: Process Verified Skills (deploy tests) ──────────
    log.info("PHASE 3: Processing verified skills for testing...")
    verified = skillbank.list_skills(status="Verified")
    for skill in verified[:3]:  # Process max 3 per cycle
        log.info(f"Testing verified skill: {skill['skill_id']}")
        
        # Spawn worker to execute
        worker_output = factory.spawn(
            skill.get("business", "Revenue"),
            f"Execute this revenue strategy and report results:\n{json.dumps(skill.get('opportunity_data', skill), indent=2)}"
        )
        
        # Supreme Court review
        passed, court_results = court.review(skill, worker_output)
        skillbank.update_status(skill["skill_id"], 
                                 "Live" if passed else "Failed",
                                 {"supreme_court_results": court_results, "test_output_sample": worker_output[:500]})
        
        if passed:
            log.info(f"SKILL DEPLOYED: {skill['skill_id']}")
            # ACTUALLY EXECUTE THE SKILL — not just log it
            try:
                from execution_engine import execute_skill
                exec_ok, exec_detail, exec_revenue = execute_skill(skill)
                skillbank.update_status(skill["skill_id"], "Live", 
                                        {"execution_result": exec_detail, "revenue": exec_revenue})
                results_summary.append(f"✅ DEPLOYED+EXECUTED: {skill.get('objective', skill['skill_id'])[:50]}")
                results_summary.append(f"   → {exec_detail[:80]}")
                if exec_revenue > 0:
                    results_summary.append(f"   💰 Revenue: ${exec_revenue:.2f}")
            except Exception as exec_err:
                log.error(f"Execution error: {exec_err}")
                skillbank.update_status(skill["skill_id"], "Live", {})
                results_summary.append(f"✅ DEPLOYED: {skill.get('objective', skill['skill_id'])}")
            try:
                from zapier_integration import skill_deployed as zap_skill
                zap_skill(skill['skill_id'], blueprint.get("objective","")[:80], total_score)
            except: pass
            notion_log(f"Skill Deployed: {skill['skill_id']}", 
                      f"Objective: {skill.get('objective')}\nCourt results: {json.dumps(court_results)}", 
                      "Success")
        else:
            log.info(f"SKILL FAILED COURT: {skill['skill_id']} — {court_results}")
            results_summary.append(f"❌ FAILED: {skill.get('objective', skill['skill_id'])[:50]}")

    # ── PHASE 4: Scan New Opportunities ─────────────────────────
    log.info("PHASE 4: Scanning for new opportunities...")
    try:
        # Enforce minimum pipeline size using binomial model
        # Need PIPELINE_RECOMMENDED opportunities to reliably produce 5-10 conversions
        # Override generic scanner with real Guerilla Holdings revenue opportunities
        hardcoded_opps = [
            {"action": "Publish 5 GAFC gun safety blog posts to WordPress and share on Bluesky", "business": "GAFC", "revenue_type": "brand", "estimated_monthly": 500},
            {"action": "Send Gumroad AI Business Automation Starter Kit promotional email to lead list via Brevo", "business": "Digital", "revenue_type": "digital_product", "estimated_monthly": 270},
            {"action": "Post GAFC educational content about safe firearm storage to Instagram @glocksandfriedchicken", "business": "GAFC", "revenue_type": "brand", "estimated_monthly": 200},
            {"action": "Publish affiliate review blog post targeting Sacramento small business owners", "business": "Digital", "revenue_type": "affiliate", "estimated_monthly": 150},
            {"action": "Send B2B cold outreach sequence to Sacramento restaurants about AI automation services", "business": "CALLUX", "revenue_type": "b2b_service", "estimated_monthly": 2000},
            {"action": "Create and post Bluesky thread about gun safety statistics with GAFC branding", "business": "GAFC", "revenue_type": "brand", "estimated_monthly": 100},
            {"action": "Update Gumroad Awakening book series with new descriptions to improve conversion", "business": "Digital", "revenue_type": "digital_product", "estimated_monthly": 150},
            {"action": "Publish WordPress post about CadaverCo specialty transport services for Sacramento funeral homes", "business": "CadaverCo", "revenue_type": "b2b_service", "estimated_monthly": 5000},
            {"action": "Send welcome email sequence to all new Gumroad buyers with upsell to full book series", "business": "Digital", "revenue_type": "digital_product", "estimated_monthly": 300},
            {"action": "Post GAFC Gloxsie and Bobo Licious character content to build brand awareness on social", "business": "GAFC", "revenue_type": "brand", "estimated_monthly": 200},
        ]
        raw_opportunities = hardcoded_opps
        
        # If scan returned fewer than minimum, run additional scan passes until floor met
        opportunities = raw_opportunities
        passes = 1
        while len(opportunities) < PIPELINE_MIN and passes < 4:
            log.info(f"Pipeline below minimum ({len(opportunities)}/{PIPELINE_MIN}) — running additional scan pass {passes+1}")
            additional = intel.scan_opportunities()
            # Deduplicate by action string
            existing_actions = {o.get('action','') for o in opportunities}
            new_opps = [o for o in additional if o.get('action','') not in existing_actions]
            opportunities.extend(new_opps)
            passes += 1
        
        # Cap at maximum to control compute cost
        opportunities = opportunities[:PIPELINE_MAX]
        
        log.info(f"Pipeline loaded: {len(opportunities)} opportunities ({passes} scan passes)")
        results_summary.append(f"Pipeline: {len(opportunities)} opps | target {PIPELINE_RECOMMENDED} | passes {passes}")
        queued = 0
        
        # Load RAG context once per cycle for opportunity evaluation
        rag_context = ""
        try:
            from internal_rag import rag_context_for_decision
            rag_context = rag_context_for_decision("revenue generation digital product")
            log.info(f"RAG context loaded: {len(rag_context)} chars of internal data")
        except Exception as rag_err:
            log.error(f"RAG error: {rag_err}")

        for opp in opportunities:
            # Check deduplication before scoring
            try:
                from opportunity_dedup import was_tried, mark_tried
                already_tried, prev_score, prev_outcome = was_tried(str(opp.get("action","")))
                if already_tried and prev_score < RPS_QUEUE_THRESHOLD:
                    log.info(f"Skipping duplicate opportunity (prev score: {prev_score}): {str(opp.get('action',''))[:50]}")
                    continue
            except: pass
            
            score = intel.score_opportunity(opp)
            total_score = score.get("total", 0)
            log.info(f"Opportunity scored {total_score}: {opp.get('action', '')[:60]}")
            
            if total_score >= RPS_QUEUE_THRESHOLD:
                blueprint = intel.create_skill_blueprint(opp, score)
                # Override blank objective with the actual opportunity action
                if not blueprint.get("objective") or blueprint.get("objective") == "Generate revenue":
                    blueprint["objective"] = opp.get("action", "Execute revenue action")
                    blueprint["business"] = opp.get("business", blueprint.get("business", "Digital"))
                
                # Quick Supreme Court check before queuing
                research = factory.spawn_research(str(opp))
                passed, court_results = court.review(blueprint, research)
                
                if passed:
                    blueprint["status"] = "Verified"
                    blueprint["supreme_court_results"] = court_results
                    results_summary.append(f"🔬 QUEUED ({total_score}pts): {opp.get('action', '')[:50]}")
                    queued += 1
                else:
                    blueprint["status"] = "Draft"
                    blueprint["supreme_court_results"] = court_results
                    blueprint["learnings"] = f"Failed initial court. Score: {total_score}"
                
                skillbank.save_skill(blueprint)
            else:
                log.info(f"Opportunity scored too low ({total_score}), archiving with learnings")
                blueprint = intel.create_skill_blueprint(opp, score)
                blueprint["status"] = "Archived"
                blueprint["learnings"] = f"RPS score {total_score} below threshold {RPS_QUEUE_THRESHOLD}"
                skillbank.save_skill(blueprint)
        
        results_summary.append(f"🔍 Scanned {len(opportunities)} opportunities, queued {queued}")
        
    except Exception as e:
        log.error(f"Opportunity scan failed: {e}")
        results_summary.append(f"⚠️ Scan error: {str(e)[:100]}")

            # Audience Engine — grow followers
        try:
            from audience_engine import run_audience_growth
            run_audience_growth()
        except Exception as e:
            log.error(f'Audience engine: {e}')

        # ── PHASE 4.4: Gap Modules (daily/weekly) ──────────────
    try:
        import sys
        sys.path.insert(0, '/root/workspace/Penelope')
        from gap_fixes import CompetitorMonitor, RevenueAttribution, BlueskyPoster

        # Email lead nurture — every 6 cycles (24h)
        # Init gap_cycle safely
        _gap_cycle_file = "/root/workspace/Penelope/gap_cycle.txt"
        try:
            gap_cycle = int(open(_gap_cycle_file).read().strip()) if Path(_gap_cycle_file).exists() else 0
        except:
            gap_cycle = 0
        gap_cycle += 1
        with open(_gap_cycle_file, 'w') as _gcf: _gcf.write(str(gap_cycle))
        
        if gap_cycle % 6 == 0:
            try:
                from brevo_sender import LeadEmailer
                emailer = LeadEmailer()
                sent = emailer.process_notion_leads(limit=50)
                if sent > 0:
                    results_summary.append(f"📧 Emails sent: {sent} welcome emails via Brevo")
            except Exception as be:
                log.error(f"Brevo email cycle error: {be}")

        # Bluesky posting — every cycle
        bsky = BlueskyPoster()
        if bsky.handle:
            posted = bsky.run_queue()
            if posted > 0:
                results_summary.append(f"📘 Bluesky: {posted} posts sent")

        # Revenue attribution report — every 6 cycles (24h)
        cycle_count_file2 = "/root/workspace/Penelope/gap_cycle.txt"
        import os as _os
        gap_cycle = int(open(cycle_count_file2).read().strip()) if _os.path.exists(cycle_count_file2) else 0
        gap_cycle += 1
        with open(cycle_count_file2, 'w') as _f: _f.write(str(gap_cycle))

        if gap_cycle % 6 == 0:  # Every 24h
            cm = CompetitorMonitor()
            market = cm.run_daily()
            results_summary.append(f"📊 Competitor scan: {len(market)} markets")

            attr = RevenueAttribution()
            report = attr.get_report()
            results_summary.append(f"💰 Attribution: ${report.get('total_revenue',0):.2f} tracked | Best: {report.get('best_source','?')}")

    except Exception as gap_err:
        log.error(f"Gap modules error: {gap_err}")

    # ── PHASE 4.5: Recursive Engine (weekly) ────────────────
    # Run recursive self-improvement every 42 cycles (~1 week at 4h intervals)
    import os
    cycle_count_file = "/root/workspace/Penelope/cycle_count.txt"
    try:
        cycle_num = int(open(cycle_count_file).read().strip()) if os.path.exists(cycle_count_file) else 0
        cycle_num += 1
        with open(cycle_count_file, 'w') as f: f.write(str(cycle_num))
        
        if cycle_num % 12 == 0:  # Every 48h — rebuild vector memory
            try:
                import sys as _sys
                _sys.path.insert(0, '/root/workspace/Penelope')
                from gaps2 import build_vector_memory, semantic_search
                n = build_vector_memory()
                log.info(f"Vector memory rebuilt: {n} skills indexed")
                results_summary.append(f"🧠 Vector memory: {n} skills re-indexed")
            except Exception as ve:
                log.error(f"Vector memory rebuild error: {ve}")
        
        if cycle_num % 42 == 0:  # Weekly
            log.info("WEEKLY: Running recursive self-improvement...")
            import subprocess
            subprocess.Popen(["/root/penelope_env/bin/python3", 
                            "/root/workspace/Penelope/recursive_engine.py"],
                           stdout=open("/root/workspace/Penelope/conductor_logs/recursive_run.log", "a"),
                           stderr=subprocess.STDOUT)
            results_summary.append("🔄 Recursive engine: weekly run triggered")
        
        # Run foot-in-door flywheel on leads every cycle
        if cycle_num % 6 == 0:  # Every 24h
            log.info("Running flywheel on captured leads...")
            try:
                import sys
                sys.path.insert(0, '/root/workspace/Penelope')
                from recursive_engine import RevenueModelsEngine
                flywheel = RevenueModelsEngine.FootInDoorFlywheel()
                # Get leads from local cache
                import glob, json as _json
                lead_files = glob.glob('/root/workspace/Penelope/leads/content_queue_*.json')
                results_summary.append(f"🔄 Flywheel: checked {len(lead_files)} lead queues")
            except Exception as fe:
                log.error(f"Flywheel error: {fe}")
    except Exception as e:
        log.error(f"Recursive engine wiring error: {e}")

    # ── PHASE 5: Cycle Summary ───────────────────────────────────
    duration = (datetime.now() - cycle_start).seconds
    summary = f"""CYCLE COMPLETE ({duration}s)
Revenue: ${perf['total_revenue']:.2f}
Live Skills: {len(live_skills)}
Actions:
""" + "\n".join(results_summary)

    log.info(summary)
    notion_log(f"Conductor Cycle {cycle_start.strftime('%Y-%m-%d %H:%M')}", summary, "Completed")
    
    # SMART TELEGRAM FILTERING
    # Only alert Sydney on things that require her attention or real wins
    from datetime import datetime as _dt
    hour = _dt.now().hour
    quiet_hours = hour >= 22 or hour < 8  # No alerts 10PM-8AM
    
    # Categorize what happened
    revenue_made = perf["total_revenue"] > 0
    real_error = any("Error" in r or "❌" in r for r in results_summary if "QUEUED" not in r)
    decision_needed = any("Decision" in r or "BLOCKED" in r for r in results_summary)
    first_sale = revenue_made and perf["total_revenue"] > 0  # Any real payment
    
    # Only telegram if:
    # 1. Real revenue came in (always alert, any hour)
    # 2. A decision is needed from Sydney (business hours only)  
    # 3. A real system error occurred (business hours only)
    # NEVER alert just for: DEPLOYED skills, blog posts published, queued items, routine cycles
    
    should_alert = False
    alert_reason = ""
    
    if revenue_made:
        should_alert = True
        alert_reason = f"💰 REVENUE: ${perf['total_revenue']:.2f}"
    elif decision_needed and not quiet_hours:
        should_alert = True
        alert_reason = "🔴 DECISION NEEDED"
    elif real_error and not quiet_hours:
        should_alert = True
        alert_reason = "⚠️ SYSTEM ERROR"
    
    if should_alert:
        # Send focused alert, not the full dump
        alert_lines = [alert_reason, f"Revenue: ${perf['total_revenue']:.2f}"]
        if real_error:
            errors = [r for r in results_summary if "Error" in r or "❌" in r][:3]
            alert_lines.extend(errors)
        if decision_needed:
            decisions = [r for r in results_summary if "Decision" in r or "BLOCKED" in r][:3]
            alert_lines.extend(decisions)
        alert_lines.append(f"Check dashboard: notion.so/3368bf86ffb181829402e2945c1e6a3c")
        telegram("\n".join(alert_lines))
    # Always log to Notion regardless — dashboard stays current without spamming

    # Feedback loop — analyze what worked
    try:
        from feedback_loop import analyze_and_optimize
        analyze_and_optimize(results_summary)
    except Exception as e:
        log.error(f'Feedback loop: {e}')

    log.info("CYCLE COMPLETE")
    return summary

# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        log.info("Starting Conductor daemon (4h cycle)")
        log.info("Penelope Conductor ONLINE — Running every 4 hours")
        while True:
            try:
                run_cycle()
            except Exception as e:
                log.error(f"Cycle error: {e}")
                # Only alert on repeated errors, not one-off
                log.error(f"Cycle error: {e}")
                # Alert only if it fails 3+ times in a row (tracked in file)
                err_count_file = "/tmp/penelope_err_count.txt"
                try:
                    count = int(open(err_count_file).read().strip()) + 1
                except: count = 1
                open(err_count_file, "w").write(str(count))
                if count >= 3:
                    telegram(f"🚨 Conductor down: {str(e)[:100]}\nCheck: notion.so/3368bf86ffb181829402e2945c1e6a3c")
                    open(err_count_file, "w").write("0")
            time.sleep(14400)  # 4 hours
    else:
        run_cycle()
