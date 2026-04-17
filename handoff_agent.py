#!/usr/bin/env python3
"""
PENELOPE HANDOFF AGENT v1.0
The bridge between Penelope and Claude.

Knows exactly when to escalate vs handle itself.
Writes structured Session Briefs before Sydney opens Claude.
Parks decisions in Notion with full context so sessions are crisp.
Never escalates what it can solve. Never solves what needs Claude.
"""

import os, json, time, logging, requests
from datetime import datetime
from pathlib import Path
from google import genai as _g

VAULT = "/root/penelope_vault.env"
LOG_DIR = "/root/workspace/Penelope/conductor_logs"
DECISION_QUEUE_DB = "74988a7b-ff8b-4291-9fa7-c5812e33a955"
OPS_LOG_DB = "aaac5800-d381-48c0-b135-2af97fe9d188"

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

Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [HANDOFF] %(message)s',
    handlers=[logging.FileHandler(f"{LOG_DIR}/handoff.log"), logging.StreamHandler()]
)
log = logging.getLogger("handoff")

def ai(prompt, temp=0.3):
    if not GOOGLE_KEY: return "ERROR"
    try:
        client = _g.Client(api_key=GOOGLE_KEY)
        cfg = _g.types.GenerateContentConfig(temperature=temp)
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=cfg)
        return r.text
    except Exception as e:
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


def notion_add_decision(decision, type_, priority, status, context, tried,
                         question, options, revenue_impact, raised_by):
    if not NOTION_TOKEN: return None
    try:
        r = requests.post(
            "https://api.notion.com/v1/pages",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                     "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            json={
                "parent": {"database_id": DECISION_QUEUE_DB},
                "properties": {
                    "Decision": {"title": [{"text": {"content": decision[:100]}}]},
                    "Type": {"select": {"name": type_}},
                    "Priority": {"select": {"name": priority}},
                    "Type": {"select": {"name": status}},
                    "Context": {"rich_text": [{"text": {"content": context[:2000]}}]},
                    "What Penelope Tried": {"rich_text": [{"text": {"content": tried[:2000]}}]},
                    "The Specific Question": {"rich_text": [{"text": {"content": question[:1000]}}]},
                    "Options Penelope Sees": {"rich_text": [{"text": {"content": options[:2000]}}]},
                    "Revenue Impact": {"select": {"name": revenue_impact}},
                    "Raised By": {"select": {"name": raised_by}},
                }
            }, timeout=10
        )
        data = r.json()
        return data.get("url", "")
    except Exception as e:
        log.error(f"Notion decision add failed: {e}")
        return None

# ── ESCALATION CLASSIFIER ─────────────────────────────────────────────────────
class EscalationClassifier:
    """
    Determines whether a situation needs Claude or Penelope can handle it.
    
    Penelope handles: execution, retries, content generation, lead capture,
                     routine deployments, skill bank updates, monitoring
    
    Claude handles: strategy pivots, new architecture, ambiguous high-stakes
                   decisions, anything that changes the fundamental approach,
                   situations where being wrong costs significant money or time
    """
    
    PENELOPE_HANDLES = [
        "retry", "regenerate", "rerun", "same task different approach",
        "content creation", "social post", "email draft", "skill archived",
        "lead captured", "page deployed", "score below threshold",
        "routine monitoring", "daily report", "queue update"
    ]
    
    CLAUDE_HANDLES = [
        "strategy", "architecture", "pivot", "new business model",
        "spend over 200", "legal", "compliance", "partnership",
        "contradicts north star", "all 3 iterations failed",
        "supreme court deadlock", "revenue model change",
        "something never done before", "ambiguous", "risky"
    ]
    
    def classify(self, situation):
        prompt = f"""You are the escalation classifier for an autonomous AI revenue system.

SITUATION: {situation}

PENELOPE CAN HANDLE (no escalation needed):
- Retrying a failed task with a different approach
- Generating content, social posts, email drafts
- Archiving low-scoring opportunities
- Routine deployments and monitoring
- Updating skill bank with learnings
- Lead capture and funnel management
- Any task she has done before

CLAUDE MUST HANDLE (escalate):
- Strategy pivots or fundamental approach changes
- New architecture decisions
- Spend decisions over $200
- Legal or compliance questions
- Situations where all iterations have failed (3/3)
- Supreme Court deadlocks that don't resolve
- Revenue model changes
- Anything that could cost significant money if wrong
- Questions with no clear right answer
- Decisions that change the mission or direction

Return ONLY JSON:
{{
  "escalate": true/false,
  "confidence": 0-100,
  "reason": "one sentence",
  "type": "Strategy|Architecture|Unblock|New Build|Approve Deploy|Scrap or Keep",
  "priority": "P0 - Blocking Revenue|P1 - This Session|P2 - Next Session|P3 - Background",
  "revenue_impact": "Direct - makes money|Indirect - enables revenue|Operational - saves time|Unknown",
  "penelope_action": "what penelope should do while waiting if escalating, or what she should do instead if not"
}}"""
        
        response = ai(prompt, temp=0.0)
        try:
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"): response = response[4:]
            return json.loads(response.strip())
        except:
            return {"escalate": False, "confidence": 50, "reason": "parse error — defaulting to Penelope",
                    "type": "Unblock", "priority": "P2 - Next Session",
                    "revenue_impact": "Unknown", "penelope_action": "retry with variation"}

# ── SESSION BRIEF WRITER ──────────────────────────────────────────────────────
class SessionBriefWriter:
    """
    Writes a structured brief before every Sydney ↔ Claude session.
    Sydney walks in knowing exactly what's decided, what's pending, what made money.
    Claude walks in with full context, no re-explaining needed.
    """
    
    def generate_brief(self):
        # Gather current state
        conductor_log = ""
        try:
            with open(f"{LOG_DIR}/conductor.log") as f:
                lines = f.readlines()
                conductor_log = "".join(lines[-50:])
        except: pass
        
        skillbank_count = len(list(Path("/root/workspace/Penelope/skillbank").glob("*.yaml")))
        leads_files = list(Path("/root/workspace/Penelope/leads").glob("*.json"))
        agent_runs = len(list(Path("/root/workspace/Penelope/agent_registry").glob("*.json")))
        
        prompt = f"""You are writing a Session Brief for Sydney Garmon before she opens Claude.

PURPOSE: Sydney should be able to read this in 60 seconds and know exactly:
1. What Penelope accomplished since last session
2. What decisions are waiting for Claude right now
3. What to prioritize in this session
4. What NOT to waste Claude's time on (Penelope already handled it)

CURRENT STATE:
- Skills in bank: {skillbank_count}
- Agent runs logged: {agent_runs}
- Lead queue files: {len(leads_files)}

RECENT CONDUCTOR ACTIVITY (last 50 log lines):
{conductor_log[-2000:]}

Write a brief in this EXACT format:

---
SESSION BRIEF — {datetime.now().strftime('%B %d, %Y %I:%M %p')}
---

SINCE LAST SESSION:
[3-5 bullet points — what Penelope did, what got deployed, what got archived]

REVENUE STATUS:
[Current revenue across channels — be specific, use $0 if nothing yet]

DECISIONS WAITING FOR CLAUDE:
[List any P0/P1 items from the decision queue, or "None — Penelope is self-sufficient"]

THIS SESSION PRIORITY:
[The ONE most important thing to build or decide today, in one sentence]

WHAT NOT TO REPEAT:
[Things Penelope already tried so Claude doesn't suggest them again]

OPEN BLOCKERS:
[Anything that actually requires Sydney's hands — Stripe, DNS, legal, etc.]
---

Be direct. No fluff. Sydney is busy."""

        brief = ai(prompt, temp=0.5)
        
        # Save brief
        brief_path = Path("/root/workspace/Penelope/session_briefs")
        brief_path.mkdir(parents=True, exist_ok=True)
        fname = f"brief_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(brief_path / fname, "w") as f:
            f.write(brief)
        
        # Post to Notion ops log
        if NOTION_TOKEN:
            try:
                requests.post(
                    "https://api.notion.com/v1/pages",
                    headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                             "Notion-Version": "2022-06-28",
                             "Content-Type": "application/json"},
                    json={
                        "parent": {"database_id": OPS_LOG_DB},
                        "properties": {
                            "Event": {"title": [{"text": {"content": f"Session Brief — {datetime.now().strftime('%b %d %Y %I:%M%p')}"}}]},
                            "Status": {"select": {"name": "Completed"}},
                        },
                        "children": [{"object": "block", "type": "paragraph",
                                      "paragraph": {"rich_text": [{"text": {"content": brief[:2000]}}]}}]
                    }, timeout=10
                )
            except: pass
        
        log.info(f"Session brief generated: {fname}")
        return brief

# ── DECISION DETECTOR ─────────────────────────────────────────────────────────
class DecisionDetector:
    """
    Monitors conductor logs and skill bank for situations that need Claude.
    Runs every cycle alongside the conductor.
    """
    
    def __init__(self):
        self.classifier = EscalationClassifier()
        self.seen_situations = set()
    
    def scan_for_escalations(self):
        escalations = []
        
        # Check for skills that failed 3 iterations
        skillbank_path = Path("/root/workspace/Penelope/skillbank")
        for skill_file in skillbank_path.glob("*.yaml"):
            try:
                import yaml
                with open(skill_file) as f:
                    skill = yaml.safe_load(f)
                
                if skill.get("status") == "Failed":
                    sid = skill.get("skill_id", "")
                    if sid not in self.seen_situations:
                        situation = f"Skill '{skill.get('objective','?')}' failed Supreme Court after {skill.get('iterations',1)} iterations. Objective: {skill.get('objective')}. Business: {skill.get('business')}."
                        classification = self.classifier.classify(situation)
                        
                        if classification.get("escalate") and classification.get("confidence", 0) > 70:
                            escalations.append({
                                "situation": situation,
                                "classification": classification,
                                "skill": skill
                            })
                            self.seen_situations.add(sid)
            except: pass
        
        # Check for repeated scan failures (pipeline not filling)
        try:
            with open(f"{LOG_DIR}/conductor.log") as f:
                recent = "".join(f.readlines()[-100:])
            
            if recent.count("Pipeline below minimum") >= 3:
                situation = "Conductor pipeline has been below minimum 3+ times. Not finding enough Tier 1 opportunities. May need new opportunity sources or strategy adjustment."
                sid = "pipeline_failure"
                if sid not in self.seen_situations:
                    classification = self.classifier.classify(situation)
                    if classification.get("escalate"):
                        escalations.append({"situation": situation, "classification": classification, "skill": {}})
                        self.seen_situations.add(sid)
        except: pass
        
        return escalations
    
    def process_escalation(self, escalation):
        situation = escalation["situation"]
        cl = escalation["classification"]
        skill = escalation.get("skill", {})
        
        # Generate options for Claude
        options_prompt = f"""For this situation that needs a human decision, generate 3 clear options.

SITUATION: {situation}
TYPE: {cl.get('type')}

For each option provide:
- Option name (3 words max)
- What it means in practice
- Upside
- Downside
- Estimated revenue impact

Return as plain text, not JSON."""
        
        options = ai(options_prompt, temp=0.5)
        
        # Add to Notion Decision Queue
        notion_url = notion_add_decision(
            decision=situation[:100],
            type_=cl.get("type", "Unblock"),
            priority=cl.get("priority", "P1 - This Session"),
            status="Needs Claude",
            context=f"Skill ID: {skill.get('skill_id','?')}\nObjective: {skill.get('objective','?')}\nBusiness: {skill.get('business','?')}\n\nFull situation: {situation}",
            tried=f"Penelope attempted: {skill.get('iterations','?')} iterations. Supreme Court verdict: {json.dumps(skill.get('supreme_court_results',{}))[:500]}",
            question=f"Should Penelope: {cl.get('penelope_action','?')} OR does this need a different approach entirely?",
            options=options[:2000],
            revenue_impact=cl.get("revenue_impact", "Unknown"),
            raised_by="Penelope"
        )
        
        log.info(f"Escalation added to Decision Queue: {situation[:60]}")
        
        # Telegram alert if P0 or P1
        if "P0" in cl.get("priority", "") or "P1" in cl.get("priority", ""):
            telegram(
                f"Decision needed: {situation[:100]}\n\nPriority: {cl.get('priority')}\nType: {cl.get('type')}\nImpact: {cl.get('revenue_impact')}\n\nNotion: {notion_url or 'check Decision Queue'}",
                urgent="P0" in cl.get("priority", "")
            )
        
        return notion_url

# ── MAIN ───────────────────────────────────────────────────────────────────────
def run_handoff_cycle():
    log.info("Handoff agent cycle starting")
    
    detector = DecisionDetector()
    brief_writer = SessionBriefWriter()
    
    # 1. Scan for escalations
    escalations = detector.scan_for_escalations()
    log.info(f"Escalations found: {len(escalations)}")
    
    for e in escalations:
        detector.process_escalation(e)
    
    # 2. Generate session brief (every 12h = every 3 conductor cycles)
    cycle_file = "/root/workspace/Penelope/handoff_cycle.txt"
    cycle = 0
    try:
        if Path(cycle_file).exists():
            cycle = int(open(cycle_file).read().strip())
    except: pass
    cycle += 1
    with open(cycle_file, "w") as f:
        f.write(str(cycle))
    
    if cycle % 3 == 0:  # Every 12 hours
        log.info("Generating session brief...")
        brief = brief_writer.generate_brief()
        telegram(f"Session brief ready for your next Claude session:\n\n{brief[:800]}...")
    
    log.info(f"Handoff cycle complete. Escalations: {len(escalations)}")
    return len(escalations)

if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        log.info("Handoff agent daemon starting")
        while True:
            try:
                run_handoff_cycle()
            except Exception as e:
                log.error(f"Handoff cycle error: {e}")
            time.sleep(14400)  # Every 4h alongside conductor
    else:
        run_handoff_cycle()
