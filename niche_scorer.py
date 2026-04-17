#!/usr/bin/env python3
"""
Guerilla Holdings — Niche Scorer
Scores niches 0-100 based on:
- Social engagement signals pulled via opencli-rs (Twitter, Reddit, HackerNews)
- Content volume in niche (demand signal)
- Revenue signals from Stripe (if any sales linked to niche)
Writes scores to niche_scores.json. Used by Claude as Experiment Engine.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

SCORES_FILE = Path("/root/workspace/Penelope/niche_scores.json")
HISTORY_FILE = Path("/root/workspace/Penelope/niche_history.json")

# Penelope's active niches — expand as experiments run
DEFAULT_NICHES = [
    "personal finance",
    "financial freedom",
    "passive income",
    "AI automation",
    "business automation",
    "transport logistics",
    "freight trucking",
    "gun safety",
    "community safety",
    "minority business",
    "small business grants",
    "affiliate marketing",
    "digital products",
    "print on demand",
]

# Weight factors for scoring
WEIGHTS = {
    "reddit_engagement":   0.25,
    "twitter_mentions":    0.25,
    "hackernews_presence": 0.10,
    "search_volume_proxy": 0.20,
    "stripe_revenue":      0.20,
}


def _load_scores() -> dict:
    if SCORES_FILE.exists():
        try:
            return json.loads(SCORES_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_scores(scores: dict):
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCORES_FILE.write_text(json.dumps(scores, indent=2))


def _reddit_score(niche: str) -> float:
    """Pull Reddit engagement for niche. Returns 0-100 signal."""
    from opencli_wrapper import opencli_run
    result = opencli_run("reddit", "search", {"query": niche, "limit": 10})
    if not result["success"] or not isinstance(result["data"], list):
        return 0.0
    posts = result["data"]
    if not posts:
        return 0.0
    total_score = sum(int(p.get("score", p.get("ups", 0))) for p in posts if isinstance(p, dict))
    total_comments = sum(int(p.get("num_comments", p.get("comments", 0))) for p in posts if isinstance(p, dict))
    engagement = total_score + (total_comments * 2)
    # Normalize to 0-100 (cap at 10,000 engagement = 100)
    return min(engagement / 100, 100)


def _twitter_score(niche: str) -> float:
    """Pull Twitter search results for niche. Returns 0-100 signal."""
    from opencli_wrapper import opencli_run
    result = opencli_run("twitter", "search", {"query": niche, "limit": 10})
    if not result["success"] or not isinstance(result["data"], list):
        return 0.0
    tweets = result["data"]
    if not tweets:
        return 0.0
    total_likes = sum(int(t.get("likes", t.get("favorite_count", 0))) for t in tweets if isinstance(t, dict))
    total_rt = sum(int(t.get("retweets", t.get("retweet_count", 0))) for t in tweets if isinstance(t, dict))
    engagement = total_likes + (total_rt * 3)
    return min(engagement / 100, 100)


def _hackernews_score(niche: str) -> float:
    """Check HackerNews presence for niche. Returns 0-100 signal."""
    from opencli_wrapper import opencli_run
    result = opencli_run("hackernews", "search", {"query": niche, "limit": 10})
    if not result["success"] or not isinstance(result["data"], list):
        return 0.0
    items = result["data"]
    if not items:
        return 0.0
    total_score = sum(int(i.get("score", i.get("points", 0))) for i in items if isinstance(i, dict))
    return min(total_score / 10, 100)


def _stripe_revenue_score(niche: str) -> float:
    """
    Check Stripe for revenue linked to niche keyword in product names.
    Returns 0-100 signal based on revenue amount.
    """
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        if not stripe.api_key or not stripe.api_key.startswith("sk_"):
            return 0.0
        products = stripe.Product.list(limit=100, active=True)
        niche_lower = niche.lower()
        matching = [p for p in products.get("data", [])
                    if niche_lower in p.get("name", "").lower()
                    or niche_lower in p.get("description", "").lower()]
        if not matching:
            return 0.0
        # Get payment intents for matching products in last 30 days
        product_ids = [p["id"] for p in matching]
        total_revenue = 0
        for pid in product_ids:
            prices = stripe.Price.list(product=pid, limit=10)
            for price in prices.get("data", []):
                charges = stripe.PaymentIntent.list(
                    limit=50,
                    created={"gte": int((datetime.utcnow().timestamp() - 2592000))}
                )
                for c in charges.get("data", []):
                    if c.get("status") == "succeeded":
                        total_revenue += c.get("amount", 0) / 100
        # Normalize: $100 revenue = 50 points, $500 = 100 points
        return min(total_revenue / 5, 100)
    except Exception as e:
        log.debug(f"Stripe score error for '{niche}': {e}")
        return 0.0


def _search_volume_proxy(niche: str) -> float:
    """
    Use Google Trends via opencli-rs as search volume proxy.
    Falls back to Reddit post count if unavailable.
    """
    from opencli_wrapper import opencli_run
    result = opencli_run("google", "trends", {"query": niche})
    if result["success"] and isinstance(result["data"], (list, dict)):
        data = result["data"]
        if isinstance(data, dict):
            value = data.get("value", data.get("interest", 0))
            return min(float(value), 100)
        elif isinstance(data, list) and data:
            vals = [float(d.get("value", 0)) for d in data if isinstance(d, dict)]
            return min(sum(vals) / max(len(vals), 1), 100)
    # Fallback: Reddit post volume
    result2 = opencli_run("reddit", "search", {"query": niche, "limit": 25})
    if result2["success"] and isinstance(result2["data"], list):
        return min(len(result2["data"]) * 4, 100)
    return 0.0


def score_niche(niche: str, verbose: bool = False) -> float:
    """
    Score a single niche. Returns 0-100 float.
    Pulls live data from all signal sources.
    """
    log.info(f"Scoring niche: '{niche}'")
    signals = {}

    try:
        signals["reddit_engagement"]   = _reddit_score(niche)
    except Exception as e:
        signals["reddit_engagement"]   = 0.0
        log.debug(f"Reddit signal failed: {e}")

    try:
        signals["twitter_mentions"]    = _twitter_score(niche)
    except Exception as e:
        signals["twitter_mentions"]    = 0.0
        log.debug(f"Twitter signal failed: {e}")

    try:
        signals["hackernews_presence"] = _hackernews_score(niche)
    except Exception as e:
        signals["hackernews_presence"] = 0.0
        log.debug(f"HN signal failed: {e}")

    try:
        signals["search_volume_proxy"] = _search_volume_proxy(niche)
    except Exception as e:
        signals["search_volume_proxy"] = 0.0
        log.debug(f"Search volume signal failed: {e}")

    try:
        signals["stripe_revenue"]      = _stripe_revenue_score(niche)
    except Exception as e:
        signals["stripe_revenue"]      = 0.0
        log.debug(f"Stripe signal failed: {e}")

    # Weighted average
    score = sum(signals[k] * WEIGHTS[k] for k in WEIGHTS)
    score = round(score, 1)

    if verbose:
        print(f"\n{'='*50}")
        print(f"NICHE: {niche}")
        print(f"{'='*50}")
        for k, v in signals.items():
            weight = WEIGHTS[k]
            print(f"  {k:<25} {v:>6.1f} × {weight:.2f} = {v*weight:.1f}")
        print(f"  {'TOTAL SCORE':<25} {score:>6.1f}")
        print(f"{'='*50}\n")

    return score


def run_scoring_cycle(niches: list = None, notify: bool = True) -> dict:
    """
    Score all niches, save to niche_scores.json.
    Called daily at 6am by autonomous_engine.py.
    Returns dict of {niche: score}.
    """
    if niches is None:
        niches = DEFAULT_NICHES

    scores_data = _load_scores()
    new_scores  = {}
    winners     = []  # Niches scoring 70+
    scalers     = []  # Niches scoring 85+ (recommend scaling)

    for niche in niches:
        try:
            score = score_niche(niche)
            prev  = scores_data.get(niche, {}).get("score", None)
            new_scores[niche] = {
                "score":        score,
                "prev_score":   prev,
                "delta":        round(score - prev, 1) if prev else None,
                "last_scored":  datetime.utcnow().isoformat(),
                "action":       _recommend_action(score, prev)
            }
            log.info(f"  {niche}: {score:.1f}")

            if score >= 85:
                scalers.append((niche, score))
            elif score >= 70:
                winners.append((niche, score))

        except Exception as e:
            log.error(f"Scoring failed for '{niche}': {e}")
            new_scores[niche] = {
                "score": 0, "error": str(e),
                "last_scored": datetime.utcnow().isoformat()
            }

    _save_scores(new_scores)

    if notify:
        from notification_hub import notify_all, scale_alert
        top3 = sorted(new_scores.items(), key=lambda x: x[1].get("score", 0), reverse=True)[:3]
        summary = "\n".join(f"• {n}: {d['score']:.0f}/100 ({d.get('action', '')})" for n, d in top3)
        notify_all(
            "📊 Daily Niche Scores",
            f"Top performers today:\n{summary}",
            {"type": "info", "total_niches": len(niches), "winners": len(winners), "scalers": len(scalers)}
        )
        for niche, score in scalers:
            scale_alert(niche, score, f"Scale: generate 20+ content variations, expand to all platforms")

    return {n: d["score"] for n, d in new_scores.items()}


def _recommend_action(score: float, prev_score: Optional[float]) -> str:
    """Generate action recommendation based on score."""
    if score >= 85:
        return "SCALE — generate 20+ variations, expand platforms"
    elif score >= 70:
        return "GROW — increase posting frequency, try new angles"
    elif score >= 50:
        return "MAINTAIN — continue current cadence, monitor"
    elif score >= 30:
        return "TEST — run 3 experiment posts, evaluate"
    else:
        return "PAUSE — low signal, deprioritize"


def get_top_niches(n: int = 5) -> list:
    """Return top N niches by current score. Used by content agents."""
    scores = _load_scores()
    sorted_niches = sorted(
        [(niche, data.get("score", 0)) for niche, data in scores.items()],
        key=lambda x: x[1],
        reverse=True
    )
    return [(niche, score) for niche, score in sorted_niches[:n]]


def get_niches_for_track(track: str) -> list:
    """Return relevant niches for a content track."""
    track_map = {
        "penelope": ["personal finance", "financial freedom", "passive income",
                     "AI automation", "business automation", "transport logistics",
                     "freight trucking", "affiliate marketing", "digital products"],
        "gafc":     ["gun safety", "community safety", "minority business",
                     "small business grants", "print on demand"],
    }
    return track_map.get(track, DEFAULT_NICHES)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if "--score" in sys.argv:
        niche = " ".join(sys.argv[sys.argv.index("--score") + 1:])
        score = score_niche(niche, verbose=True)
        print(f"Score: {score}")
    else:
        print("Running full scoring cycle...")
        scores = run_scoring_cycle(notify=False)
        for niche, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {niche:<30} {score:.1f}")
