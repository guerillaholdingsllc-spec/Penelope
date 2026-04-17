#!/usr/bin/env python3
"""
Guerilla Holdings — Social Agent
Handles all social media posting and metrics via opencli-rs.
Add this class to agent_army.py.
Operates across both Penelope track and GAFC track.
"""

import logging
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

POST_LOG   = Path("/root/workspace/Penelope/social_posts.log")
QUEUE_FILE = Path("/root/workspace/Penelope/social_queue.json")

# Platform configs: post command args per platform
PLATFORM_CONFIG = {
    "twitter": {
        "post_cmd":  "post",
        "max_chars": 280,
        "track":     ["penelope", "gafc"],
        "hashtags":  {"penelope": ["#PassiveIncome", "#AI", "#Automation"],
                      "gafc":     ["#GunSafety", "#CommunityFirst", "#GAFC"]},
    },
    "linkedin": {
        "post_cmd":  "post",
        "max_chars": 3000,
        "track":     ["penelope"],
        "hashtags":  {"penelope": ["#BusinessAutomation", "#AI", "#Entrepreneurship"]},
    },
    "reddit": {
        "post_cmd":  "comment",   # Reddit uses comment/post on subreddit
        "max_chars": 10000,
        "track":     ["penelope"],
        "subreddits": {
            "personal finance":    "personalfinance",
            "AI automation":       "artificial",
            "transport logistics": "Truckers",
            "gun safety":          "guns",
            "passive income":      "passive_income",
        },
    },
    "medium": {
        "post_cmd":  "publish",
        "max_chars": 50000,
        "track":     ["penelope"],
        "hashtags":  {"penelope": ["AI", "Automation", "Business"]},
    },
    "instagram": {
        "post_cmd":  "publish",
        "max_chars": 2200,
        "track":     ["gafc"],
        "hashtags":  {"gafc": ["#GunSafety", "#GAFC", "#GlocksAndFriedChicken",
                                "#CommunityFirst", "#MinorityOwned"]},
    },
    "tiktok": {
        "post_cmd":  "publish",
        "max_chars": 2200,
        "track":     ["gafc"],
        "hashtags":  {"gafc": ["#GunSafety", "#GAFC", "#CommunityEducation"]},
    },
    "facebook": {
        "post_cmd":  "post",
        "max_chars": 63206,
        "track":     ["penelope", "gafc"],
        "hashtags":  {"penelope": ["#BusinessTips", "#Entrepreneurship"],
                      "gafc":     ["#GunSafety", "#GAFC"]},
    },
    "substack": {
        "post_cmd":  "publish",
        "max_chars": 100000,
        "track":     ["penelope"],
        "hashtags":  {},
    },
}


class SocialAgent:
    """
    Handles all social media operations via opencli-rs.
    Respects platform health stops.
    Logs all posts. Records engagement for platform_health.py.
    """

    def __init__(self, track: str = "penelope"):
        self.track = track  # "penelope" or "gafc"

    def _get_platforms_for_track(self) -> list:
        """Return platforms active for this track."""
        return [p for p, cfg in PLATFORM_CONFIG.items()
                if self.track in cfg.get("track", [])]

    def _add_hashtags(self, text: str, platform: str) -> str:
        """Append relevant hashtags to content."""
        cfg = PLATFORM_CONFIG.get(platform, {})
        tags = cfg.get("hashtags", {}).get(self.track, [])
        if not tags:
            return text
        hashtag_str = " ".join(tags[:5])  # Max 5 hashtags
        # Don't exceed platform char limit
        max_chars = cfg.get("max_chars", 280)
        combined  = f"{text}\n\n{hashtag_str}"
        return combined if len(combined) <= max_chars else text

    def _truncate(self, text: str, platform: str) -> str:
        """Truncate content to platform character limit."""
        max_chars = PLATFORM_CONFIG.get(platform, {}).get("max_chars", 280)
        if len(text) <= max_chars:
            return text
        return text[:max_chars - 3] + "..."

    def _log_post(self, platform: str, content: str, success: bool, post_id: str = ""):
        POST_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().isoformat()
        with open(POST_LOG, "a") as f:
            status = "✅" if success else "❌"
            f.write(f"[{ts}] {status} [{self.track}] [{platform}] {content[:80]}...\n")

    def post_content(self, content: str, platform: str, niche: str = "") -> dict:
        """
        Post content to a single platform via opencli-rs.
        Returns {success, platform, post_id, error}
        """
        from opencli_wrapper import opencli_run
        from platform_health import is_platform_active, record_post_result

        if not is_platform_active(platform):
            log.warning(f"[{platform}] is stopped — skipping post")
            return {"success": False, "platform": platform,
                    "post_id": "", "error": "Platform stopped"}

        # Prepare content
        text = self._truncate(self._add_hashtags(content, platform), platform)
        cfg  = PLATFORM_CONFIG.get(platform, {})

        # Build opencli-rs args
        args = {"text": text}
        if platform == "reddit" and niche:
            subreddit = cfg.get("subreddits", {}).get(niche, "entrepreneur")
            args["subreddit"] = subreddit

        cmd    = cfg.get("post_cmd", "post")
        result = opencli_run(platform, cmd, args)

        success  = result.get("success", False)
        post_id  = ""
        if success and isinstance(result.get("data"), dict):
            post_id = str(result["data"].get("id", result["data"].get("post_id", "")))

        self._log_post(platform, content, success, post_id)

        if success:
            from notification_hub import post_success
            post_success(platform, content[:60], self.track)
        else:
            log.warning(f"Post failed [{platform}]: {result.get('error')}")

        # Record engagement placeholder (0 immediately, updated later)
        record_post_result(platform, 0.0, post_id)

        return {
            "success":  success,
            "platform": platform,
            "post_id":  post_id,
            "error":    result.get("error")
        }

    def distribute(self, content: str, niche: str = "", platforms: list = None) -> dict:
        """
        Distribute content across all active platforms for this track.
        Returns summary dict.
        """
        if platforms is None:
            platforms = self._get_platforms_for_track()

        results    = {}
        successes  = 0
        failures   = 0

        for platform in platforms:
            result = self.post_content(content, platform, niche)
            results[platform] = result
            if result["success"]:
                successes += 1
            else:
                failures += 1
            time.sleep(2)  # Brief delay between platforms

        log.info(f"distribute [{self.track}]: {successes} succeeded, {failures} failed")
        return {
            "track":     self.track,
            "niche":     niche,
            "successes": successes,
            "failures":  failures,
            "platforms": results
        }

    def pull_trending(self, platform: str = "twitter", limit: int = 20) -> list:
        """Pull trending topics from a platform for research."""
        from opencli_wrapper import opencli_run
        if platform == "twitter":
            result = opencli_run("twitter", "trending", {"limit": limit})
        elif platform == "reddit":
            result = opencli_run("reddit", "hot", {"subreddit": "all", "limit": limit})
        elif platform == "hackernews":
            result = opencli_run("hackernews", "top", {"limit": limit})
        else:
            result = opencli_run(platform, "hot", {"limit": limit})

        if result["success"] and isinstance(result["data"], list):
            return result["data"]
        return []

    def research_niche(self, niche: str) -> dict:
        """
        Pull cross-platform data for a niche.
        Returns aggregated research dict for Claude to analyze.
        """
        from opencli_wrapper import opencli_search
        research = {
            "niche":    niche,
            "pulled_at": datetime.utcnow().isoformat(),
            "platforms": {}
        }
        for platform in ["twitter", "reddit", "hackernews", "linkedin", "youtube"]:
            try:
                results = opencli_search(platform, niche, limit=5)
                research["platforms"][platform] = results[:5]
            except Exception as e:
                research["platforms"][platform] = []
                log.debug(f"Research failed [{platform}]: {e}")

        return research

    def schedule_post(self, content: str, platform: str,
                      post_at: datetime, niche: str = ""):
        """Queue a post for future delivery."""
        queue = []
        if QUEUE_FILE.exists():
            try:
                queue = json.loads(QUEUE_FILE.read_text())
            except Exception:
                pass
        queue.append({
            "content":  content,
            "platform": platform,
            "niche":    niche,
            "track":    self.track,
            "post_at":  post_at.isoformat(),
            "status":   "scheduled"
        })
        QUEUE_FILE.write_text(json.dumps(queue, indent=2))
        log.info(f"Scheduled post to {platform} at {post_at}")

    def process_queue(self):
        """Process any scheduled posts that are due. Call from main loop."""
        if not QUEUE_FILE.exists():
            return
        try:
            queue = json.loads(QUEUE_FILE.read_text())
            now = datetime.utcnow()
            updated = False
            for item in queue:
                if item.get("status") != "scheduled":
                    continue
                post_at = datetime.fromisoformat(item["post_at"])
                if now >= post_at:
                    result = self.post_content(
                        item["content"],
                        item["platform"],
                        item.get("niche", "")
                    )
                    item["status"]       = "sent" if result["success"] else "failed"
                    item["sent_at"]      = now.isoformat()
                    item["post_id"]      = result.get("post_id", "")
                    updated = True
            if updated:
                QUEUE_FILE.write_text(json.dumps(queue, indent=2))
        except Exception as e:
            log.error(f"Queue processing failed: {e}")


# Convenience instantiations
penelope_social = SocialAgent(track="penelope")
gafc_social     = SocialAgent(track="gafc")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing SocialAgent...")
    agent = SocialAgent(track="penelope")
    trending = agent.pull_trending("hackernews", limit=5)
    print(f"HackerNews trending: {len(trending)} items")
    for item in trending[:3]:
        title = item.get("title", str(item)[:60]) if isinstance(item, dict) else str(item)[:60]
        print(f"  - {title}")
