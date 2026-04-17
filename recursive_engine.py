#!/usr/bin/env python3
"""
PENELOPE RECURSIVE ENGINE v1.0
Self-improving. Self-creating. Revenue-centric.

Capabilities:
- Self-Improving Prompts (evaluator loop)
- Autonomous Skill Creation (writes its own tools)
- Iterative Synthesis (sub-agent delegation + report generation)
- 4 Revenue Models: Outcome-Based, Foot-in-Door Flywheel, Agent Rental, SaaS Tiers
"""

import os, json, time, logging, requests, hashlib
from datetime import datetime
from pathlib import Path
from google import genai as _g

# ── Config ────────────────────────────────────────────────────────────────────
VAULT = "/root/penelope_vault.env"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"
SKILLBANK = "/root/workspace/Penelope/skillbank"
AGENT_REGISTRY = "/root/workspace/Penelope/agent_registry"
REPORTS_DIR = "/root/workspace/Penelope/reports"
LEADS_DIR = "/root/workspace/Penelope/leads"

def load_vault():
    env = {}
    try:
        with open(VAULT) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
GOOGLE_KEY = ENV.get("GOOGLE_API_KEY", "")
TELEGRAM_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
TELEGRAM_CHAT = ENV.get("TELEGRAM_CHAT_ID", "6183015901")
NOTION_TOKEN = ENV.get("NOTION_TOKEN", ENV.get("NOTION_API_KEY", ""))
NOTION_OPS_DB = "aaac5800-d381-48c0-b135-2af97fe9d188"
NOTION_AUDIENCE_DB = "1d64e8db-eae2-4732-8cc9-50d2ad0c0081"

for d in [LOG_DIR, SKILLBANK, AGENT_REGISTRY, REPORTS_DIR, LEADS_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [RECURSIVE] %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/recursive.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("recursive")

# ── Core AI ───────────────────────────────────────────────────────────────────
def ai(prompt, temp=0.7, model="gemini-2.5-flash"):
    if not GOOGLE_KEY:
        return "ERROR: no key"
    try:
        client = _g.Client(api_key=GOOGLE_KEY)
        cfg = _g.types.GenerateContentConfig(temperature=temp)
        r = client.models.generate_content(model=model, contents=prompt, config=cfg)
        return r.text
    except Exception as e:
        log.error(f"AI call failed: {e}")
        return f"ERROR: {e}"


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


def notion_log(title, body, status="Info"):
    if not NOTION_TOKEN: return
    try:
        requests.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"},
            json={
                "parent": {"database_id": NOTION_OPS_DB},
                "properties": {
                    "Event": {"title": [{"text": {"content": f"[RECURSIVE] {title}"[:100]}}]},
                    "Type": {"select": {"name": status}},
                },
                "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": body[:2000]}}]}}]
            }, timeout=10
        )
    except Exception as e:
        log.error(f"Notion log failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1: SELF-IMPROVING PROMPT LOOP
# Agent executes → Evaluator scores → If <perfect, rewrite prompt → Retry
# ═══════════════════════════════════════════════════════════════════════════════
class SelfImprovingLoop:
    def __init__(self, max_iterations=3, target_score=85):
        self.max_iterations = max_iterations
        self.target_score = target_score

    def evaluate(self, task, output, context="revenue generation"):
        prompt = f"""You are a strict Revenue Output Evaluator. Temperature: 0.0.

TASK: {task}
OUTPUT TO EVALUATE: {output[:2000]}
CONTEXT: {context}

Score this output 0-100 on:
1. Accuracy & completeness (0-25): Does it fully address the task?
2. Revenue potential (0-25): Will this actually make money?
3. Actionability (0-25): Can an AI agent execute this without human help?
4. Quality (0-25): Is it professional and compelling?

Return ONLY JSON:
{{"score": 0-100, "passed": true/false, "weaknesses": ["...", "..."], "rewrite_instruction": "specific instruction to improve the prompt"}}"""
        
        response = ai(prompt, temp=0.0)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"): response = response[4:]
            result = json.loads(response.strip())
            result["passed"] = result.get("score", 0) >= self.target_score
            return result
        except:
            return {"score": 60, "passed": False, "weaknesses": ["parse error"], "rewrite_instruction": "Be more specific and actionable"}

    def rewrite_prompt(self, original_prompt, evaluation):
        weaknesses = evaluation.get("weaknesses", [])
        instruction = evaluation.get("rewrite_instruction", "Improve quality")
        score = evaluation.get("score", 0)
        
        prompt = f"""You are a Prompt Engineer. Rewrite this prompt to score higher (current: {score}/100).

ORIGINAL PROMPT: {original_prompt}

WEAKNESSES TO FIX:
{chr(10).join(f"- {w}" for w in weaknesses)}

REWRITE INSTRUCTION: {instruction}

Rules:
- Keep the same core objective
- Make it more specific, actionable, and revenue-focused
- Add concrete examples if needed
- Remove vague language

Return ONLY the improved prompt, nothing else."""
        
        return ai(prompt, temp=0.5)

    def run(self, task_prompt, task_context="revenue generation"):
        log.info(f"Self-improving loop: {task_prompt[:60]}...")
        
        current_prompt = task_prompt
        best_output = None
        best_score = 0
        history = []
        
        for iteration in range(self.max_iterations):
            log.info(f"Iteration {iteration + 1}/{self.max_iterations}")
            
            # Execute task
            output = ai(current_prompt, temp=0.7)
            
            # Evaluate
            evaluation = self.evaluate(task_prompt, output, task_context)
            score = evaluation.get("score", 0)
            log.info(f"Score: {score}/100 | Passed: {evaluation.get('passed')}")
            
            history.append({
                "iteration": iteration + 1,
                "prompt_hash": hashlib.md5(current_prompt.encode()).hexdigest()[:8],
                "score": score,
                "passed": evaluation.get("passed"),
                "output_length": len(output)
            })
            
            if score > best_score:
                best_score = score
                best_output = output
            
            # If passed target, stop
            if evaluation.get("passed"):
                log.info(f"✅ Target score reached at iteration {iteration + 1}")
                break
            
            # Rewrite prompt for next iteration
            if iteration < self.max_iterations - 1:
                current_prompt = self.rewrite_prompt(current_prompt, evaluation)
                log.info(f"Prompt rewritten for iteration {iteration + 2}")
                time.sleep(1)
        
        return {
            "final_output": best_output,
            "best_score": best_score,
            "iterations": len(history),
            "history": history,
            "converged": best_score >= self.target_score
        }

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2: AUTONOMOUS SKILL CREATION
# If Penelope lacks a tool, she codes it, tests it, stores it
# ═══════════════════════════════════════════════════════════════════════════════
class AutonomousSkillCreator:
    def __init__(self):
        self.registry_path = Path(AGENT_REGISTRY)

    def detect_skill_gap(self, task):
        """Identify if a task requires a skill Penelope doesn't have."""
        existing_skills = list(Path(SKILLBANK).glob("*.yaml"))
        skill_names = [s.stem for s in existing_skills]
        
        prompt = f"""You are analyzing whether an AI agent has the right skills for a task.

TASK: {task}
EXISTING SKILLS: {skill_names}

Does the agent have what it needs? If not, what specific new skill/tool/script needs to be created?

Return ONLY JSON:
{{"has_skill": true/false, "missing_skill": "name or null", "skill_description": "what it needs to do", "priority": "high/medium/low"}}"""
        
        response = ai(prompt, temp=0.0)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"): response = response[4:]
            return json.loads(response.strip())
        except:
            return {"has_skill": True, "missing_skill": None}

    def create_skill(self, skill_name, skill_description, use_case):
        """Autonomously write a Python skill module."""
        log.info(f"Creating skill: {skill_name}")
        
        # Use self-improving loop for code generation
        loop = SelfImprovingLoop(max_iterations=2, target_score=75)
        
        code_prompt = f"""Write a Python function/module for this skill:

SKILL NAME: {skill_name}
DESCRIPTION: {skill_description}
USE CASE: {use_case}

Requirements:
- Pure Python, no external deps except requests, json, os
- Function signature: def execute(params: dict) -> dict
- Returns: {{"success": bool, "result": any, "error": str}}
- Include error handling
- Add a brief docstring
- Must be immediately executable
- Focused on revenue generation for a small business

Write clean, working Python code only. No markdown."""

        result = loop.run(code_prompt, "autonomous skill code generation")
        code = result["final_output"]
        
        # Clean code
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        
        # Save skill
        skill_path = self.registry_path / f"{skill_name}.py"
        with open(skill_path, "w") as f:
            f.write(f"# Auto-generated skill: {skill_name}\n")
            f.write(f"# Created: {datetime.now().isoformat()}\n")
            f.write(f"# Description: {skill_description}\n\n")
            f.write(code)
        
        # Save to skillbank as YAML
        import yaml
        skill_yaml = {
            "skill_id": skill_name,
            "created": datetime.now().isoformat(),
            "status": "Verified",
            "type": "auto_generated_code",
            "description": skill_description,
            "use_case": use_case,
            "code_path": str(skill_path),
            "generation_score": result["best_score"],
            "iterations": result["iterations"]
        }
        yaml_path = Path(SKILLBANK) / f"{skill_name}.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)
        
        log.info(f"Skill created: {skill_name} (score: {result['best_score']})")
        return {"skill_name": skill_name, "path": str(skill_path), "score": result["best_score"]}

    def spawn_sub_agent(self, role, task, tools=None, budget=10.0):
        """Dynamically spawn a sub-agent for a specific task."""
        log.info(f"Spawning sub-agent: {role}")
        
        system_prompt = f"""You are a specialized {role} agent for Guerilla Holdings LLC.
Budget: ${budget}. Be efficient.
Task focus: Revenue generation only.
Return structured JSON results always."""

        full_prompt = f"{system_prompt}\n\nTASK: {task}"
        result = ai(full_prompt, temp=0.6)
        
        # Register this agent run
        agent_log = {
            "role": role,
            "task": task[:200],
            "timestamp": datetime.now().isoformat(),
            "output_length": len(result),
            "budget": budget
        }
        
        log_path = Path(AGENT_REGISTRY) / f"agent_run_{int(time.time())}.json"
        with open(log_path, "w") as f:
            json.dump(agent_log, f)
        
        return result

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: ITERATIVE SYNTHESIS ENGINE
# Scan data → Delegate to sub-agents → Synthesize → Premium report
# ═══════════════════════════════════════════════════════════════════════════════
class IterativeSynthesisEngine:
    def __init__(self):
        self.creator = AutonomousSkillCreator()

    def synthesize_market_report(self, topic, depth=3):
        """Generate a premium market intelligence report via iterative sub-agent delegation."""
        log.info(f"Synthesizing report: {topic}")
        
        # Phase 1: Research agents gather raw data
        research_agents = [
            ("Market Analyst", f"Research market size, trends, and growth rate for: {topic}. Focus on 2025-2026 data. Be specific with numbers."),
            ("Competitor Scout", f"Identify top 5 competitors in: {topic}. For each: pricing, weakness, market share. Focus on gaps Guerilla Holdings can exploit."),
            ("Revenue Modeler", f"Model 3 revenue scenarios (conservative/base/optimistic) for entering the {topic} market. Include monthly projections for months 1-6."),
        ]
        
        raw_findings = []
        for role, task in research_agents:
            finding = self.creator.spawn_sub_agent(role, task, budget=5.0)
            raw_findings.append({"role": role, "finding": finding})
            time.sleep(1)
        
        # Phase 2: Synthesis agent combines everything
        synthesis_prompt = f"""You are a Senior Strategy Analyst for Guerilla Holdings LLC.

TOPIC: {topic}
RAW RESEARCH FROM 3 SPECIALIST AGENTS:

{chr(10).join(f"=== {r['role'].upper()} ==={chr(10)}{r['finding'][:800]}" for r in raw_findings)}

Synthesize this into a premium intelligence report with:
1. Executive Summary (3 sentences max)
2. Market Opportunity Score (0-100) with reasoning
3. Top 3 Revenue Actions ranked by speed-to-money
4. Risk factors (2-3 bullets)
5. Recommended first move for Penelope to execute THIS WEEK

Format as a clean, professional report. Include specific dollar figures."""

        # Run through self-improving loop for quality
        loop = SelfImprovingLoop(max_iterations=2, target_score=80)
        result = loop.run(synthesis_prompt, "premium market intelligence report")
        
        report = {
            "topic": topic,
            "generated": datetime.now().isoformat(),
            "report": result["final_output"],
            "quality_score": result["best_score"],
            "raw_findings": raw_findings,
            "iterations": result["iterations"]
        }
        
        # Save report
        report_id = hashlib.md5(topic.encode()).hexdigest()[:8]
        report_path = Path(REPORTS_DIR) / f"report_{report_id}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        log.info(f"Report synthesized: {topic} (quality: {result['best_score']})")
        return report

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: REVENUE MODELS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
class RevenueModelsEngine:

    # ── Model 1: Outcome-Based Pricing ──────────────────────────────────────
    class OutcomePricingAgent:
        """Bills only on results. Booked meetings, resolved tickets, closed leads."""
        
        OUTCOMES = {
            "booked_meeting": {"price": 150, "trigger": "calendar_invite_sent"},
            "qualified_lead": {"price": 50, "trigger": "lead_score_above_70"},
            "grant_submitted": {"price": 200, "trigger": "application_confirmed"},
            "product_sale": {"price": None, "trigger": "stripe_payment", "pct": 0.15},
            "email_open_chain": {"price": 25, "trigger": "3_consecutive_opens"},
        }
        
        def track_outcome(self, outcome_type, lead_data):
            outcome = self.OUTCOMES.get(outcome_type, {})
            price = outcome.get("price") or (lead_data.get("value", 0) * outcome.get("pct", 0))
            
            log.info(f"Outcome tracked: {outcome_type} | Value: ${price} | Lead: {lead_data.get('email','?')}")
            
            result = {
                "outcome": outcome_type,
                "value": price,
                "lead": lead_data,
                "timestamp": datetime.now().isoformat(),
                "trigger": outcome.get("trigger")
            }
            
            # Log to file
            path = Path(LEADS_DIR) / "outcome_log.jsonl"
            with open(path, "a") as f:
                f.write(json.dumps(result) + "\n")
            
            return result

    # ── Model 2: Foot-in-Door Flywheel ──────────────────────────────────────
    class FootInDoorFlywheel:
        """Start low-cost → capture lead → recursively upsell to higher tiers."""
        
        FUNNEL_TIERS = {
            "awareness": {
                "product": "Free Gun Safety Guide / Free AI Starter Kit",
                "price": 0,
                "next_tier": "interest",
                "conversion_action": "email_opt_in"
            },
            "interest": {
                "product": "GAFC Community Membership / AI Business Toolkit ($27)",
                "price": 27,
                "next_tier": "decision",
                "conversion_action": "purchase_entry_product"
            },
            "decision": {
                "product": "Done-For-You AI Setup / GAFC Education Pack ($97)",
                "price": 97,
                "next_tier": "purchase",
                "conversion_action": "book_consultation"
            },
            "purchase": {
                "product": "AI Revenue Engine License / Full Consulting ($497/mo)",
                "price": 497,
                "next_tier": "repeat",
                "conversion_action": "subscription_created"
            },
            "repeat": {
                "product": "Enterprise Partnership / White-Label Agent ($2000/mo)",
                "price": 2000,
                "next_tier": "ambassador",
                "conversion_action": "contract_signed"
            },
            "ambassador": {
                "product": "Referral Commission Program (20% recurring)",
                "price": None,
                "commission_pct": 0.20,
                "next_tier": None,
                "conversion_action": "referral_sent"
            }
        }
        
        def get_next_offer(self, current_funnel_stage, lead_data):
            """Generate personalized next offer based on where lead is in funnel."""
            current = self.FUNNEL_TIERS.get(current_funnel_stage, self.FUNNEL_TIERS["awareness"])
            next_stage = current.get("next_tier")
            
            if not next_stage:
                return {"message": "Lead is an ambassador — activate referral program", "action": "send_referral_invite"}
            
            next_tier = self.FUNNEL_TIERS[next_stage]
            
            prompt = f"""Write a personalized upgrade offer for this lead.

CURRENT STAGE: {current_funnel_stage}
CURRENT PRODUCT: {current['product']}
NEXT OFFER: {next_tier['product']} at ${next_tier['price']}
LEAD DATA: {json.dumps(lead_data, default=str)[:500]}

Write a 3-sentence personalized pitch that:
1. Acknowledges what they already have
2. Explains what they're missing
3. Creates urgency for the next step

Keep it conversational, not salesy. Under 100 words."""

            pitch = ai(prompt, temp=0.7)
            
            return {
                "current_stage": current_funnel_stage,
                "next_stage": next_stage,
                "next_product": next_tier["product"],
                "next_price": next_tier["price"],
                "pitch": pitch,
                "action_required": next_tier["conversion_action"]
            }
        
        def run_flywheel(self, leads_batch):
            """Process a batch of leads and generate personalized upgrade paths."""
            results = []
            for lead in leads_batch:
                stage = lead.get("Funnel", "awareness").lower()
                offer = self.get_next_offer(stage, lead)
                results.append({"lead": lead.get("Email", "?"), "offer": offer})
                time.sleep(0.5)
            return results

    # ── Model 3: Agent Rental (P2P Marketplace) ─────────────────────────────
    class AgentRentalMarketplace:
        """Build specialized agents → license to others → take revenue %."""
        
        RENTAL_CATALOG = {
            "grant_hunter_agent": {
                "name": "GAFC Grant Hunter",
                "description": "Finds and applies to grants for nonprofits and social enterprises. Runs daily.",
                "monthly_price": 297,
                "commission_pct": 0.35,
                "target_buyer": "nonprofits, social enterprises, community orgs",
                "unique_value": "Specializes in minority-owned and community safety orgs"
            },
            "lead_gen_agent": {
                "name": "Guerilla Lead Machine",
                "description": "24/7 demographic building, landing pages, and funnel management for local businesses.",
                "monthly_price": 497,
                "commission_pct": 0.35,
                "target_buyer": "local businesses, restaurants, service providers",
                "unique_value": "Sacramento/NorCal specialist with cultural competency"
            },
            "content_agent": {
                "name": "Content Conductor",
                "description": "AI content creation for social media, email, and blog. Posts daily across channels.",
                "monthly_price": 197,
                "commission_pct": 0.35,
                "target_buyer": "small business owners who lack content teams",
                "unique_value": "Authentic voice, not corporate — built for real communities"
            },
            "revenue_scout_agent": {
                "name": "Revenue Scout",
                "description": "Identifies and scores revenue opportunities weekly. Delivers actionable reports.",
                "monthly_price": 397,
                "commission_pct": 0.35,
                "target_buyer": "entrepreneurs, startups, side hustlers",
                "unique_value": "75% probability threshold — only recommends high-confidence plays"
            }
        }
        
        def generate_agent_listing(self, agent_key):
            """Generate a marketplace listing for an agent."""
            agent = self.RENTAL_CATALOG.get(agent_key, {})
            
            prompt = f"""Write a compelling marketplace listing for this AI agent product.

AGENT: {agent.get('name')}
DESCRIPTION: {agent.get('description')}
PRICE: ${agent.get('monthly_price')}/month
TARGET BUYER: {agent.get('target_buyer')}
UNIQUE VALUE: {agent.get('unique_value')}

Write:
1. Headline (under 10 words, outcome-focused)
2. Subheadline (under 20 words)
3. 3 bullet benefits (problem → solution format)
4. Social proof placeholder
5. CTA

Format for a Gumroad/marketplace listing. Authentic, not hype."""

            listing = ai(prompt, temp=0.8)
            return {
                "agent": agent,
                "listing": listing,
                "monthly_revenue_potential": agent.get("monthly_price", 0),
                "url": f"https://trustchainservices.com/agents/{agent_key}"
            }
        
        def generate_all_listings(self):
            listings = {}
            for key in self.RENTAL_CATALOG:
                listings[key] = self.generate_agent_listing(key)
                time.sleep(1)
            
            # Save listings
            path = Path(REPORTS_DIR) / "agent_rental_catalog.json"
            with open(path, "w") as f:
                json.dump(listings, f, indent=2)
            
            log.info(f"Agent rental catalog generated: {len(listings)} agents")
            return listings

    # ── Model 4: SaaS Tiers ──────────────────────────────────────────────────
    class SaaSTierEngine:
        """Tiered AI product pricing. Specialized > general = +35% revenue."""
        
        TIERS = {
            "starter": {
                "name": "Starter",
                "price_monthly": 47,
                "price_annual": 397,
                "features": [
                    "1 landing page (AI-generated)",
                    "Lead capture + Notion database",
                    "5 social posts/week",
                    "Weekly revenue report",
                    "Email support"
                ],
                "target": "Solopreneurs, side hustlers",
                "stripe_price_id": None
            },
            "growth": {
                "name": "Growth",
                "price_monthly": 147,
                "price_annual": 1197,
                "features": [
                    "3 landing pages + A/B testing",
                    "Full funnel (awareness → purchase)",
                    "20 social posts/week across 3 platforms",
                    "Daily revenue monitoring",
                    "Email nurture sequences (5-step)",
                    "Lead scoring + prioritization",
                    "Telegram alerts for hot leads"
                ],
                "target": "Growing businesses, content creators",
                "stripe_price_id": None
            },
            "conductor": {
                "name": "Conductor (Full Penelope)",
                "price_monthly": 497,
                "price_annual": 3997,
                "features": [
                    "Unlimited landing pages",
                    "Full Penelope conductor brain",
                    "Supreme Court skill verification",
                    "Autonomous revenue testing (75% threshold)",
                    "Agent rental marketplace access",
                    "Custom skill creation",
                    "White-label ready",
                    "Priority support + monthly strategy call"
                ],
                "target": "Serious entrepreneurs, agencies, holding companies",
                "stripe_price_id": None
            },
            "enterprise": {
                "name": "Enterprise (Bespoke)",
                "price_monthly": 2000,
                "price_annual": 18000,
                "features": [
                    "Everything in Conductor",
                    "Dedicated agent army (10+ workers)",
                    "Custom integrations (CRM, ERP, etc.)",
                    "Outcome-based billing option",
                    "Revenue share partnership available",
                    "On-call Claude synthesis sessions",
                    "Full white-label + reseller rights"
                ],
                "target": "Agencies, enterprise teams, holding companies",
                "stripe_price_id": None
            }
        }
        
        def generate_pricing_page(self):
            """Generate HTML pricing page for all tiers."""
            tiers_html = ""
            for key, tier in self.TIERS.items():
                features_html = "\n".join(f"<li>✓ {f}</li>" for f in tier["features"])
                is_featured = key == "growth"
                tiers_html += f"""
<div class="tier {'featured' if is_featured else ''}">
    {'<div class="badge">Most Popular</div>' if is_featured else ''}
    <h3>{tier['name']}</h3>
    <div class="price">${tier['price_monthly']}<span>/mo</span></div>
    <div class="annual">or ${tier['price_annual']}/year (save {round((1 - tier['price_annual']/(tier['price_monthly']*12))*100)}%)</div>
    <p class="target">{tier['target']}</p>
    <ul>{features_html}</ul>
    <a href="/api/lead?brand=digital&tier={key}" class="cta-btn">Get Started</a>
</div>"""
            
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Guerilla Holdings — AI Revenue Engine Pricing</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #0a0a0a; color: #fff; font-family: 'Segoe UI', sans-serif; }}
.header {{ text-align: center; padding: 60px 20px 40px; }}
.header h1 {{ font-size: 2.5rem; color: #00FF88; margin-bottom: 10px; }}
.header p {{ color: #999; font-size: 1.1rem; max-width: 600px; margin: 0 auto; }}
.tiers {{ display: flex; gap: 20px; padding: 40px 20px; max-width: 1200px; margin: 0 auto; flex-wrap: wrap; justify-content: center; }}
.tier {{ background: #111; border: 1px solid #222; border-radius: 12px; padding: 30px; flex: 1; min-width: 250px; max-width: 300px; position: relative; }}
.tier.featured {{ border-color: #00FF88; transform: scale(1.03); }}
.badge {{ background: #00FF88; color: #000; font-size: 0.75rem; font-weight: 700; padding: 4px 12px; border-radius: 20px; position: absolute; top: -12px; left: 50%; transform: translateX(-50%); }}
.tier h3 {{ font-size: 1.3rem; margin-bottom: 10px; color: #00FF88; }}
.price {{ font-size: 2.5rem; font-weight: 700; margin: 15px 0 5px; }}
.price span {{ font-size: 1rem; color: #999; }}
.annual {{ font-size: 0.8rem; color: #666; margin-bottom: 10px; }}
.target {{ font-size: 0.85rem; color: #888; margin-bottom: 20px; font-style: italic; }}
ul {{ list-style: none; margin-bottom: 25px; }}
li {{ padding: 6px 0; font-size: 0.9rem; color: #ccc; border-bottom: 1px solid #1a1a1a; }}
.cta-btn {{ display: block; background: #00FF88; color: #000; text-decoration: none; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; transition: opacity 0.2s; }}
.cta-btn:hover {{ opacity: 0.9; }}
.tier.featured .cta-btn {{ background: #00FF88; }}
@media(max-width:768px) {{ .tiers {{ flex-direction: column; align-items: center; }} .tier {{ max-width: 100%; }} }}
</style>
</head>
<body>
<div class="header">
    <h1>Revenue Autopilot</h1>
    <p>AI agents that find, test, and deploy revenue streams 24/7. You wake up to money.</p>
</div>
<div class="tiers">{tiers_html}</div>
</body>
</html>"""
            
            # Deploy pricing page
            pricing_path = Path("/var/www/html/funnels/pricing/index.html")
            pricing_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pricing_path, "w") as f:
                f.write(html)
            
            log.info("Pricing page deployed: /funnels/pricing/")
            return html

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: RECURSIVE SELF-MONITORING & IMPROVEMENT
# Penelope audits herself weekly — kills weak agents, upgrades strong ones
# ═══════════════════════════════════════════════════════════════════════════════
class SelfMonitor:
    def audit(self):
        """Weekly self-audit — what's working, what's dead weight."""
        log.info("Running self-audit...")
        
        # Count agent runs
        runs = list(Path(AGENT_REGISTRY).glob("*.json"))
        reports = list(Path(REPORTS_DIR).glob("*.json"))
        skills = list(Path(SKILLBANK).glob("*.yaml"))
        leads_files = list(Path(LEADS_DIR).glob("*.json"))
        
        total_leads = 0
        for lf in leads_files:
            try:
                with open(lf) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        total_leads += len(data)
            except: pass
        
        audit = {
            "timestamp": datetime.now().isoformat(),
            "agent_runs": len(runs),
            "reports_generated": len(reports),
            "skills_in_bank": len(skills),
            "leads_captured": total_leads,
            "status": "healthy" if len(skills) > 0 else "needs_attention"
        }
        
        # Generate improvement recommendations
        prompt = f"""You are Penelope auditing your own performance.

STATS:
- Agent runs: {audit['agent_runs']}
- Reports generated: {audit['reports_generated']}
- Skills in bank: {audit['skills_in_bank']}
- Leads captured: {audit['leads_captured']}

Based on these numbers, what are the 3 most important things to improve next week?
Focus only on actions that will directly increase revenue.
Return as JSON array of strings."""

        recs = ai(prompt, temp=0.5)
        try:
            if "```" in recs:
                recs = recs.split("```")[1]
                if recs.startswith("json"): recs = recs[4:]
            audit["recommendations"] = json.loads(recs.strip())
        except:
            audit["recommendations"] = ["Generate more content", "Increase landing page traffic", "Follow up on leads"]
        
        # Save audit
        audit_path = Path(REPORTS_DIR) / f"self_audit_{datetime.now().strftime('%Y%m%d')}.json"
        with open(audit_path, "w") as f:
            json.dump(audit, f, indent=2)
        
        notion_log("Weekly Self-Audit", json.dumps(audit, indent=2)[:2000], "Completed")
        log.info(f"Self-audit complete: {audit['status']}")
        return audit

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════
def run_recursive_engine():
    log.info("=" * 60)
    log.info("RECURSIVE ENGINE INITIALIZING")
    log.info("=" * 60)
    results = []

    # 1. Generate agent rental catalog
    log.info("Phase 1: Building agent rental catalog...")
    try:
        rme = RevenueModelsEngine()
        rental = rme.AgentRentalMarketplace()
        listings = rental.generate_all_listings()
        results.append(f"Agent rental catalog: {len(listings)} agents listed")
    except Exception as e:
        log.error(f"Rental catalog failed: {e}")
        results.append(f"Rental catalog: ERROR - {e}")

    time.sleep(2)

    # 2. Deploy SaaS pricing page
    log.info("Phase 2: Deploying SaaS pricing page...")
    try:
        saas = rme.SaaSTierEngine()
        saas.generate_pricing_page()
        results.append("SaaS pricing page: deployed at /funnels/pricing/")
    except Exception as e:
        log.error(f"Pricing page failed: {e}")
        results.append(f"Pricing page: ERROR - {e}")

    time.sleep(2)

    # 3. Synthesize first market report
    log.info("Phase 3: Generating market intelligence report...")
    try:
        synthesis = IterativeSynthesisEngine()
        report = synthesis.synthesize_market_report("AI automation services for Sacramento small businesses")
        results.append(f"Market report: quality score {report['quality_score']}/100")
    except Exception as e:
        log.error(f"Market report failed: {e}")
        results.append(f"Market report: ERROR - {e}")

    time.sleep(2)

    # 4. Self-audit
    log.info("Phase 4: Running self-audit...")
    try:
        monitor = SelfMonitor()
        audit = monitor.audit()
        results.append(f"Self-audit: {audit['status']} | {audit['skills_in_bank']} skills | {audit['leads_captured']} leads")
    except Exception as e:
        log.error(f"Self-audit failed: {e}")

    # 5. Test self-improving loop on a revenue task
    log.info("Phase 5: Testing self-improving loop...")
    try:
        loop = SelfImprovingLoop(max_iterations=2, target_score=80)
        test_result = loop.run(
            "Write a compelling Gumroad product description for 'The AI Business Automation Starter Kit' targeting entrepreneurs who want to automate their revenue generation using AI agents. Price: $27.",
            "product copywriting for digital revenue"
        )
        results.append(f"Self-improving loop: score {test_result['best_score']}/100 in {test_result['iterations']} iterations")
        
        # Save the winning copy
        copy_path = Path(REPORTS_DIR) / "gumroad_product_copy.txt"
        with open(copy_path, "w") as f:
            f.write(test_result["final_output"])
        log.info("Gumroad copy saved for Sydney to review")
    except Exception as e:
        log.error(f"Self-improving loop failed: {e}")

    summary = "RECURSIVE ENGINE COMPLETE\n" + "\n".join(f"✅ {r}" for r in results)
    log.info(summary)
    telegram(summary)
    return results

if __name__ == "__main__":
    run_recursive_engine()
