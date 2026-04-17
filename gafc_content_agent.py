#!/usr/bin/env python3
"""
Guerilla Holdings — GAFC Content Agent
Glocks and Fried Chicken — Minority-Owned Social Enterprise
Gun safety education, cartoon IP (Gloxsie 21 + Bobo Licious),
Church of Legacy partnership content, Printify merch triggers.
Trend-driven cadence: I (Claude) decide when to post based on signals.
"""

import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from google import genai

def _get_gemini_client():
    """Lazy Gemini client — loads key from vault at call time."""
    import os as _o
    key = _o.getenv("GOOGLE_API_KEY", "")
    if not key:
        try:
            for line in open("/root/penelope_vault.env"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip()
                    break
        except: pass
    if not key:
        return None
    from google import genai as _g
    return _g.Client(api_key=key)


log = logging.getLogger(__name__)

GAFC_OUTPUT_DIR  = Path("/root/workspace/Penelope/gafc_output")
GAFC_LOG         = Path("/root/workspace/Penelope/gafc_content.log")
GAFC_ASSETS_DIR  = Path("/root/workspace/Penelope/gafc_assets")
PRINTIFY_QUEUE   = Path("/root/workspace/Penelope/printify_queue.json")

GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY", "")
PRINTIFY_API_KEY = os.getenv("PRINTIFY_API_KEY", "")

# GAFC Brand Voice
GAFC_BRAND_VOICE = """
You are creating content for Glocks and Fried Chicken (GAFC) — a minority-owned social enterprise 
focused on gun safety education in marginalized communities, primarily Black and Brown communities.

Brand personality:
    pass
- Bold, unapologetic, community-first
- Educational but never preachy — speaks the language of the community
- Empowers rather than lectures
- Humor mixed with serious purpose
- References street culture authentically without exploitation
- Champions legal gun ownership + responsibility
- Celebrates minority entrepreneurship and community self-reliance

Cartoon characters:
    pass
- Gloxsie 21: A cool, streetwise character who takes gun safety seriously
- Bobo Licious: Gloxsie's partner, more comedic, learns through funny situations

Church of Legacy: Faith-based community partner — content should occasionally reference 
the intersection of faith, community, and safety.

NEVER: preachy, condescending, government-focused, stereotyping
ALWAYS: community-first, empowering, practical, authentic
"""

# Content templates by type
CONTENT_TYPES = {
    "education":   "Gun safety tip or educational content — practical, community-relevant",
    "story":       "Short story or scenario featuring Gloxsie 21 and/or Bobo Licious",
    "community":   "Community spotlight or empowerment message",
    "merch_promo": "Merchandise promotion for GAFC branded products",
    "church":      "Faith + community safety intersection — Church of Legacy partnership",
    "trending":    "Response to current events through GAFC brand lens",
    "quiz":        "Interactive safety quiz or poll for engagement",
}

# Trending gun safety topics to monitor
MONITOR_TOPICS = [
    "gun safety",
    "responsible gun ownership",
    "firearm education",
    "community gun violence prevention",
    "minority gun rights",
    "second amendment community",
    "gun safe storage",
]


def _gemini_generate(prompt: str, temperature: float = 0.8) -> str:
    """Generate content via Gemini."""
    try:
        from google import genai as _g
        import os
        key = os.getenv("GOOGLE_API_KEY","") or next(
            (l.split("=",1)[1].strip() for l in open("/root/penelope_vault.env")
             if l.strip().startswith("GOOGLE_API_KEY=")), "")
        c = _g.Client(api_key=key)
        return c.models.generate_content(model="gemini-2.5-flash", contents=prompt).text.strip()
    except Exception as e:
        return f"[Gemini error: {e}]"


def _log(message: str):
    GAFC_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().isoformat()
    with open(GAFC_LOG, "a") as f:
        f.write(f"[{ts}] {message}\n")


def check_trending_signals() -> dict:
    """
    Check if any gun safety / GAFC topics are trending.
    Returns {should_post: bool, topics: list, urgency: str}
    """
    from opencli_wrapper import opencli_run, opencli_search
    trending_topics = []
    urgency = "low"

    for topic in MONITOR_TOPICS[:3]:  # Check top 3 topics
        try:
            # Twitter trending check
            twitter_results = opencli_search("twitter", topic, limit=5)
            if twitter_results:
                total_engagement = sum(
                    int(t.get("likes", 0)) + int(t.get("retweets", 0))
                    for t in twitter_results
                    if isinstance(t, dict)
                )
                if total_engagement > 500:
                    trending_topics.append({"topic": topic, "platform": "twitter",
                                            "engagement": total_engagement})
                    if total_engagement > 5000:
                        urgency = "high"
                    elif total_engagement > 1000:
                        urgency = "medium"

            # Reddit check
            reddit_results = opencli_search("reddit", topic, limit=5)
            if reddit_results:
                top_score = max(
                    (int(r.get("score", 0)) for r in reddit_results if isinstance(r, dict)),
                    default=0
                )
                if top_score > 100:
                    trending_topics.append({"topic": topic, "platform": "reddit",
                                            "score": top_score})
        except Exception as e:
            log.debug(f"Trending check failed for '{topic}': {e}")

    should_post = len(trending_topics) > 0 or urgency in ["medium", "high"]
    return {
        "should_post":     should_post,
        "topics":          trending_topics,
        "urgency":         urgency,
        "checked_at":      datetime.utcnow().isoformat()
    }


def generate_content(
    content_type: str = "education",
    topic: str = "",
    platform: str = "instagram",
    trending_context: str = ""
) -> dict:
    """
    Generate GAFC-branded content for a given type and platform.
    Returns {title, body, hashtags, platform, type, score}
    """
    type_desc = CONTENT_TYPES.get(content_type, CONTENT_TYPES["education"])
    char_limit = {
        "instagram": 2200, "tiktok": 2200,
        "twitter": 280, "facebook": 1000
    }.get(platform, 1000)

    prompt = f"""{GAFC_BRAND_VOICE}

Content type: {type_desc}
Platform: {platform} (max {char_limit} characters)
Topic focus: {topic or 'gun safety education'}
{f'Trending context: {trending_context}' if trending_context else ''}

Write ONE piece of GAFC content for {platform}. Include:
    pass
1. Attention-grabbing opening line
2. Core message (educational, empowering, authentic)
3. Call to action or community prompt
4. Platform-appropriate length

Format response as JSON:
    pass
{{
  "title": "short title for filing",
  "body": "full post content",
  "hashtags": ["list", "of", "relevant", "hashtags"],
  "emoji_lead": "1-2 emojis for visual punch"
}}

Return ONLY valid JSON, no markdown.
"""
    try:
        raw   = _gemini_generate(prompt, temperature=0.85)
        # Clean JSON
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data     = json.loads(raw)
        body     = data.get("body", "")
        hashtags = data.get("hashtags", [])
        emoji    = data.get("emoji_lead", "")

        # Build final post
        post_text = f"{emoji} {body}" if emoji else body
        hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in hashtags[:8])
        if hashtag_str and len(post_text) + len(hashtag_str) + 2 <= char_limit:
            post_text = f"{post_text}\n\n{hashtag_str}"

        return {
            "title":        data.get("title", f"gafc_{content_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"),
            "body":         post_text,
            "raw_body":     body,
            "hashtags":     hashtags,
            "platform":     platform,
            "content_type": content_type,
            "topic":        topic,
            "generated_at": datetime.utcnow().isoformat(),
            "char_count":   len(post_text)
        }
    except Exception as e:
        log.error(f"GAFC content generation failed: {e}")
        # Fallback content
        return {
            "title":        "gafc_fallback",
            "body":         f"🔫🍗 Gun safety is community safety. #GAFC #GunSafety #CommunityFirst",
            "platform":     platform,
            "content_type": content_type,
            "error":        str(e),
            "generated_at": datetime.utcnow().isoformat()
        }


def save_content(content: dict) -> Path:
    """Save generated GAFC content to output directory."""
    GAFC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{content['title'].replace(' ', '_')[:50]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = GAFC_OUTPUT_DIR / filename
    filepath.write_text(json.dumps(content, indent=2))
    _log(f"Saved: {filename}")
    return filepath


def queue_printify_merch(concept: str, score: float, design_notes: str = ""):
    """
    Queue a merch concept for Printify when score >= 7.0.
    Sydney reviews and approves before publishing.
    """
    queue = []
    if PRINTIFY_QUEUE.exists():
        try:
            queue = json.loads(PRINTIFY_QUEUE.read_text())
        except Exception:
            pass

    item = {
        "concept":      concept,
        "score":        score,
        "design_notes": design_notes,
        "status":       "pending_review",
        "queued_at":    datetime.utcnow().isoformat(),
        "assets":       list_gafc_assets()
    }
    queue.append(item)
    PRINTIFY_QUEUE.write_text(json.dumps(queue, indent=2))

    from notification_hub import notify_all
    notify_all(
        f"🔫🍗 Printify Merch Concept Ready",
        f"Concept: {concept}\nScore: {score:.1f}/10\n{design_notes}",
        {"type": "gafc", "action": "review_merch", "score": score}
    )
    _log(f"Printify queued: {concept} (score: {score})")


def list_gafc_assets() -> list:
    """List available GAFC brand assets."""
    if not GAFC_ASSETS_DIR.exists():
        return []
    assets = []
    for ext in ["*.png", "*.jpg", "*.svg", "*.ai", "*.pdf"]:
        assets.extend([str(f.name) for f in GAFC_ASSETS_DIR.glob(ext)])
    return assets


def run_gafc_cycle(force: bool = False) -> dict:
    """
    Main GAFC content cycle. Called by autonomous_engine.py.
    Checks trends, decides whether to post, generates + distributes content.
    force=True bypasses trend check and always posts.
    """
    from social_agent import gafc_social

    _log("Starting GAFC content cycle...")

    # Check trends
    trend_data = check_trending_signals()
    _log(f"Trend check: should_post={trend_data['should_post']}, urgency={trend_data['urgency']}")

    if not force and not trend_data["should_post"]:
        _log("No trending signals — holding GAFC posts today")
        return {"posted": False, "reason": "No trending signals"}

    # Determine content type based on urgency
    if trend_data["urgency"] == "high":
        content_type = "trending"
        topic = trend_data["topics"][0]["topic"] if trend_data["topics"] else "gun safety"
    elif trend_data["urgency"] == "medium":
        content_type = random.choice(["education", "story", "community"])
        topic = trend_data["topics"][0]["topic"] if trend_data["topics"] else "gun safety"
    else:
        content_type = random.choice(list(CONTENT_TYPES.keys()))
        topic = "gun safety education"

    # Generate for primary platforms
    results = {}
    for platform in ["instagram", "tiktok", "facebook"]:
        content = generate_content(
            content_type=content_type,
            topic=topic,
            platform=platform,
            trending_context=str(trend_data["topics"][:2]) if trend_data["topics"] else ""
        )
        save_content(content)

        # Post via SocialAgent
        post_result = gafc_social.post_content(content["body"], platform, niche="gun safety")
        results[platform] = {
            "posted":  post_result["success"],
            "post_id": post_result.get("post_id", "")
        }
        _log(f"Posted to {platform}: {post_result['success']}")

    # Check if this content should trigger Printify merch concept
    if content_type in ["story", "merch_promo"] or trend_data["urgency"] == "high":
        merch_score = 7.5 if trend_data["urgency"] == "high" else 7.1
        queue_printify_merch(
            concept=f"GAFC × {topic} — {content_type} design",
            score=merch_score,
            design_notes=f"Based on trending '{topic}', content_type: {content_type}. Use Gloxsie 21 + Bobo Licious characters."
        )

    return {
        "posted":       True,
        "content_type": content_type,
        "topic":        topic,
        "urgency":      trend_data["urgency"],
        "platforms":    results
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if "--trends" in sys.argv:
        print("Checking trends...")
        signals = check_trending_signals()
        print(json.dumps(signals, indent=2))
    elif "--generate" in sys.argv:
        content = generate_content("education", "safe gun storage", "instagram")
        print(f"\nGenerated content:\n{content['body']}")
    else:
        # Run full cycle — force=True so it always produces content on schedule
        result = run_gafc_cycle(force=True)
        print(f"GAFC cycle complete: {result.get('content_type','?')} | urgency={result.get('urgency','?')}")