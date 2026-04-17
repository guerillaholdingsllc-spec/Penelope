#!/usr/bin/env python3
"""Opportunity deduplication — prevents Penelope from repeating failed attempts."""
import json, hashlib
from datetime import datetime
from pathlib import Path

TRIED_FILE = "/root/workspace/Penelope/tried_opportunities.json"

def was_tried(opportunity_text, min_hours_ago=48):
    opp_hash = hashlib.md5(opportunity_text[:100].encode()).hexdigest()[:12]
    try:
        tried = json.loads(Path(TRIED_FILE).read_text())
        if opp_hash in tried:
            ts = datetime.fromisoformat(tried[opp_hash]["ts"])
            hours_ago = (datetime.now() - ts).total_seconds() / 3600
            if hours_ago < min_hours_ago:
                return True, tried[opp_hash]["score"], tried[opp_hash]["outcome"]
    except: pass
    return False, 0, ""

def mark_tried(opportunity_text, score, outcome):
    opp_hash = hashlib.md5(opportunity_text[:100].encode()).hexdigest()[:12]
    try:
        tried = json.loads(Path(TRIED_FILE).read_text()) if Path(TRIED_FILE).exists() else {}
    except: tried = {}
    tried[opp_hash] = {"score": score, "outcome": outcome, "ts": datetime.now().isoformat(), "text": opportunity_text[:80]}
    Path(TRIED_FILE).write_text(json.dumps(tried, indent=2))

def get_tried_count():
    try: return len(json.loads(Path(TRIED_FILE).read_text()))
    except: return 0
