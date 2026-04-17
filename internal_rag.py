#!/usr/bin/env python3
"""
PENELOPE INTERNAL RAG SYSTEM
Queries Penelope's own business data before making decisions.
Answers: "Have we tried this before?" "What worked?" "What failed?"

Sources:
- SkillBank (110 blueprints) — what we've tried, what scored what
- Audit trail — every agent action and outcome
- Content performance — what content got engagement
- Attribution log — which channels drove actual clicks/leads
- Blog army — what topics the army has covered
"""
import json, re, math, glob, yaml
from collections import Counter
from pathlib import Path
from datetime import datetime

SKILLBANK = "/root/workspace/Penelope/skillbank"
AUDIT_LOG = "/root/workspace/Penelope/audit_trail.jsonl"
PERF_FILE = "/root/workspace/Penelope/leads/content_performance.json"
ATTR_LOG = "/root/workspace/Penelope/leads/attribution_log.jsonl"
VECTOR_MEM = "/root/workspace/Penelope/vector_memory.json"

def tokenize(text):
    return re.findall(r"\b[a-z]{3,}\b", str(text).lower())

def query_skillbank(question, top_k=5):
    """Find past skills relevant to a question."""
    if not Path(VECTOR_MEM).exists():
        return []
    
    with open(VECTOR_MEM) as f:
        memory = json.load(f)
    
    skills = memory["skills"]
    df = memory["df"]
    N = max(memory["skill_count"], 1)
    
    q_tokens = tokenize(question)
    q_tf = Counter(q_tokens)
    q_total = len(q_tokens) or 1
    q_vector = {w: (c/q_total) * math.log(N / (df.get(w, 1) + 1)) for w, c in q_tf.items()}
    
    scores = []
    for skill in skills:
        sv = skill.get("vector", {})
        all_words = set(list(q_vector.keys()) + list(sv.keys()))
        dot = sum(q_vector.get(w, 0) * sv.get(w, 0) for w in all_words)
        q_mag = math.sqrt(sum(v**2 for v in q_vector.values())) or 1
        s_mag = math.sqrt(sum(v**2 for v in sv.values())) or 1
        cosine = dot / (q_mag * s_mag)
        scores.append((cosine, skill))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    return [(score, s) for score, s in scores[:top_k] if score > 0.05]

def query_audit_trail(agent=None, last_n=50):
    """Get recent audit trail entries, optionally filtered by agent."""
    if not Path(AUDIT_LOG).exists():
        return []
    entries = []
    with open(AUDIT_LOG) as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                if agent is None or e.get("agent") == agent:
                    entries.append(e)
            except: pass
    return entries[-last_n:]

def query_performance():
    """Get content performance data."""
    if not Path(PERF_FILE).exists():
        return {}
    try:
        with open(PERF_FILE) as f:
            return json.load(f)
    except: return {}

def query_attribution():
    """Get revenue attribution data by channel."""
    if not Path(ATTR_LOG).exists():
        return {}
    events = []
    with open(ATTR_LOG) as f:
        for line in f:
            try: events.append(json.loads(line.strip()))
            except: pass
    
    by_source = {}
    for e in events:
        src = e.get("source", "unknown")
        if src not in by_source:
            by_source[src] = {"events": 0, "revenue": 0}
        by_source[src]["events"] += 1
        by_source[src]["revenue"] += e.get("amount", 0)
    return by_source

def rag_context_for_decision(question):
    """
    Build full RAG context for a decision question.
    This is what Penelope should call before evaluating any opportunity.
    """
    context_parts = []
    
    # 1. Similar past skills
    similar = query_skillbank(question, top_k=3)
    if similar:
        context_parts.append("PAST SKILLS (similar):")
        for score, skill in similar:
            status = skill.get("status", "?")
            rps = skill.get("score", 0)
            obj = skill.get("objective", "?")[:80]
            context_parts.append(f"  [{status}] RPS:{rps:.0f} | {obj}")
    
    # 2. Recent audit trail
    recent = query_audit_trail(last_n=10)
    if recent:
        context_parts.append("\nRECENT ACTIONS:")
        for e in recent[-5:]:
            context_parts.append(f"  {e.get('agent','?')} | {e.get('action','?')[:50]} | {e.get('result','?')[:40]}")
    
    # 3. What channels are working
    attr = query_attribution()
    if attr:
        context_parts.append("\nCHANNEL PERFORMANCE:")
        for src, data in sorted(attr.items(), key=lambda x: x[1]["revenue"], reverse=True):
            context_parts.append(f"  {src}: {data['events']} events, ${data['revenue']:.2f} revenue")
    
    # 4. Content performance
    perf = query_performance()
    if perf.get("bluesky", {}).get("top_post"):
        top = perf["bluesky"]["top_post"]
        context_parts.append(f"\nTOP CONTENT: {top.get('text','?')[:60]} (engagement: {top.get('engagement',0):.1f})")
    
    return "\n".join(context_parts) if context_parts else "No historical data yet."

if __name__ == "__main__":
    import sys
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "email marketing automation gumroad digital product"
    print(f"RAG query: {question}")
    print("=" * 50)
    print(rag_context_for_decision(question))
