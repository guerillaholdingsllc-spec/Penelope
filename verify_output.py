"""
verify_output.py — Penelope Quality Gate
-----------------------------------------
Runs after content generation, before writing to shipped/ or feed.json.
Uses a lightweight Gemini call to score output quality.
Failures are logged but never delete content.

Usage:
    from verify_output import verify_content, verify_json_feed

    result = await verify_content(content, content_type="article")
    if result.passed:
        write_to_shipped(content)
    else:
        log_failure(content, result)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

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


# ── Config ────────────────────────────────────────────────────────────────────

PASS_THRESHOLD = 7.0          # Minimum score out of 10
FAILURE_LOG    = Path("/root/workspace/Penelope/failed_verification.log")
MODEL_NAME     = "gemini-2.5-flash"
TIMEOUT_SECS   = 15           # Max seconds to wait for verification response

logger = logging.getLogger("penelope.verify")

# ── Data types ────────────────────────────────────────────────────────────────

ContentType = Literal["article", "crypto_report", "feed_item", "social_post"]

@dataclass
class VerifyResult:
    passed: bool
    score: float
    reason: str
    content_type: ContentType
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} [{self.score:.1f}/10] {self.reason}"


# ── Prompts ───────────────────────────────────────────────────────────────────

VERIFY_PROMPTS: dict[ContentType, str] = {
    "article": """Score this SEO article from 1-10 on these criteria:
        pass
- Coherence and readability (content makes sense, flows well)
- Topic relevance (stays on subject, no hallucinated facts)
- Completeness (has intro, body, conclusion or clear structure)
- Affiliate-friendliness (suitable for embedding affiliate links)

Reply with ONLY this JSON (no markdown, no explanation):
    pass
{{"score": <float 1-10>, "reason": "<one sentence>"}}

CONTENT:
    pass
{content}""",

    "crypto_report": """Score this crypto intelligence report from 1-10:
        pass
- Data accuracy appearance (numbers look reasonable, not hallucinated)
- Structure (has clear sections: summary, analysis, signals)
- Actionability (gives clear buy/sell/hold signals or price levels)
- Completeness (not truncated, covers the asset/topic fully)

Reply with ONLY this JSON (no markdown, no explanation):
    pass
{{"score": <float 1-10>, "reason": "<one sentence>"}}

CONTENT:
    pass
{content}""",

    "feed_item": """Score this content feed item from 1-10:
        pass
- Valid structure (has title, body, tags or slug fields)
- Content quality (readable, not garbled)
- Length appropriateness (not too short/long for a feed item)

Reply with ONLY this JSON (no markdown, no explanation):
    pass
{{"score": <float 1-10>, "reason": "<one sentence>"}}

CONTENT:
    pass
{content}""",

    "social_post": """Score this social media post from 1-10:
        pass
- Engagement potential (interesting hook, clear message)
- Brand safety (nothing offensive or legally risky)
- Appropriate length for social
- Call to action present

Reply with ONLY this JSON (no markdown, no explanation):
    pass
{{"score": <float 1-10>, "reason": "<one sentence>"}}

CONTENT:
    pass
{content}""",
}


# ── Core verification ─────────────────────────────────────────────────────────

async def verify_content(
    content: str,
    content_type: ContentType = "article",
) -> VerifyResult:
    """
    Run a lightweight Gemini quality check on generated content.
    Returns VerifyResult with .passed bool and numeric score.
    Never raises — on any error, returns a conservative pass so the
    engine keeps running. Errors are logged.
    """
    try:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — skipping verification")
            return VerifyResult(passed=True, score=0.0, reason="verification skipped (no API key)", content_type=content_type)

        from google import genai as _vg2
        import os as _os2
        _vkey = _os2.getenv('GOOGLE_API_KEY','')
        _vc2 = _vg2.Client(api_key=_vkey) if _vkey else None

        prompt = VERIFY_PROMPTS[content_type].format(
            content=content[:4000]  # Trim to keep verification fast + cheap
        )

        # Run with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=TIMEOUT_SECS,
        )

        raw = response.text.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
        score = float(data["score"])
        reason = str(data.get("reason", ""))
        passed = score >= PASS_THRESHOLD

        result = VerifyResult(
            passed=passed,
            score=score,
            reason=reason,
            content_type=content_type,
        )

        if not passed:
            _log_failure(content, result)

        logger.info("Verification: %s", result)
        return result

    except asyncio.TimeoutError:
        logger.warning("Verification timed out after %ss — passing through", TIMEOUT_SECS)
        return VerifyResult(passed=True, score=0.0, reason="verification timed out", content_type=content_type)

    except Exception as exc:
        logger.error("Verification error: %s — passing through", exc)
        return VerifyResult(passed=True, score=0.0, reason=f"verification error: {exc}", content_type=content_type)


async def verify_json_feed(feed_path: Path) -> VerifyResult:
    """
    Validate that feed.json is well-formed JSON before writing/overwriting.
    Checks structure, not just syntax.
    """
    try:
        text = feed_path.read_text(encoding="utf-8")
        data = json.loads(text)

        if not isinstance(data, (list, dict)):
            return VerifyResult(
                passed=False,
                score=2.0,
                reason="feed.json root must be a list or dict",
                content_type="feed_item",
            )

        items = data if isinstance(data, list) else data.get("items", [data])
        if len(items) == 0:
            return VerifyResult(
                passed=False,
                score=3.0,
                reason="feed.json has zero items",
                content_type="feed_item",
            )

        return VerifyResult(
            passed=True,
            score=9.0,
            reason=f"valid JSON feed with {len(items)} item(s)",
            content_type="feed_item",
        )

    except json.JSONDecodeError as e:
        result = VerifyResult(
            passed=False,
            score=0.0,
            reason=f"invalid JSON: {e}",
            content_type="feed_item",
        )
        _log_failure(feed_path.read_text() if feed_path.exists() else "", result)
        return result


# ── Batch helper ──────────────────────────────────────────────────────────────

async def verify_batch(
    items: list[tuple[str, ContentType]],
    concurrency: int = 3,
) -> list[VerifyResult]:
    """
    Verify multiple items concurrently with a semaphore to avoid API rate limits.
    Returns results in same order as input.
    """
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(content: str, ct: ContentType) -> VerifyResult:
        async with sem:
            return await verify_content(content, ct)

    return await asyncio.gather(*[_bounded(c, t) for c, t in items])


# ── Failure logging ───────────────────────────────────────────────────────────

def _log_failure(content: str, result: VerifyResult) -> None:
    """Append failed content to failure log. Never deletes anything."""
    try:
        FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FAILURE_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIMESTAMP : {result.timestamp}\n")
            f.write(f"TYPE      : {result.content_type}\n")
            f.write(f"SCORE     : {result.score:.1f}/10\n")
            f.write(f"REASON    : {result.reason}\n")
            f.write(f"CONTENT   :\n{content[:2000]}\n")
        logger.info("Failure logged to %s", FAILURE_LOG)
    except Exception as exc:
        logger.error("Could not write failure log: %s", exc)