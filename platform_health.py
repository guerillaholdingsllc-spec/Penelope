#!/usr/bin/env python3
"""
Guerilla Holdings — Platform Health Monitor
Checks engagement ratio per platform every 6hrs.
Hard stops posting if red flags detected. Alerts all 3 notification channels.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

HEALTH_LOG    = Path("/root/workspace/Penelope/platform_health.log")
HEALTH_STATE  = Path("/root/workspace/Penelope/platform_health.json")
STOPPED_FILE  = Path("/root/workspace/Penelope/platforms_stopped.json")

# Thresholds — tune based on real data after first week
THRESHOLDS = {
    "engagement_drop_pct":    50,   # Hard stop if engagement drops >50% vs 7-day avg
    "consecutive_zero_posts": 3,    # Hard stop after 3 consecutive zero-engagement posts
    "min_avg_engagement":     1.0,  # Minimum average engagement to stay active
}

# Platforms being monitored
MONITORED_PLATFORMS = [
    "twitter", "linkedin", "instagram", "reddit",
    "medium", "substack", "tiktok", "facebook", "youtube"
]


def _load_state() -> dict:
    """Load current health state from disk."""
    if HEALTH_STATE.exists():
        try:
            return json.loads(HEALTH_STATE.read_text())
        except Exception:
            pass
    return {p: {
        "active": True,
        "seven_day_avg": None,
        "consecutive_zeros": 0,
        "last_check": None,
        "stop_reason": None,
        "history": []
    } for p in MONITORED_PLATFORMS}


def _save_state(state: dict):
    """Persist health state to disk."""
    HEALTH_STATE.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_STATE.write_text(json.dumps(state, indent=2))


def _load_stopped() -> list:
    """Return list of currently stopped platforms."""
    if STOPPED_FILE.exists():
        try:
            return json.loads(STOPPED_FILE.read_text())
        except Exception:
            pass
    return []


def _save_stopped(stopped: list):
    STOPPED_FILE.write_text(json.dumps(stopped))


def _log(message: str):
    HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with open(HEALTH_LOG, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    log.info(message)


def is_platform_active(platform: str) -> bool:
    """Check if a platform is currently active (not hard-stopped)."""
    stopped = _load_stopped()
    return platform not in stopped


def hard_stop(platform: str, reason: str, metrics: dict = None):
    """
    Hard stop a platform. Adds to stopped list, logs, alerts all channels.
    """
    from notification_hub import red_flag
    stopped = _load_stopped()
    if platform not in stopped:
        stopped.append(platform)
        _save_stopped(stopped)

    state = _load_state()
    if platform in state:
        state[platform]["active"]      = False
        state[platform]["stop_reason"] = reason
        state[platform]["stopped_at"]  = datetime.utcnow().isoformat()
        _save_state(state)

    msg = f"HARD STOP [{platform}]: {reason}"
    _log(msg)
    red_flag(platform, reason, metrics or {})


def resume_platform(platform: str):
    """Manually resume a stopped platform."""
    stopped = _load_stopped()
    if platform in stopped:
        stopped.remove(platform)
        _save_stopped(stopped)

    state = _load_state()
    if platform in state:
        state[platform]["active"]      = True
        state[platform]["stop_reason"] = None
        state[platform]["consecutive_zeros"] = 0
        _save_state(state)

    _log(f"RESUMED [{platform}]: manually re-activated")


def record_post_result(platform: str, engagement: float, post_id: str = ""):
    """
    Record the engagement result of a post and check thresholds.
    Call this after each post with the measured engagement score.
    engagement = likes + comments + shares + (reposts * 2)
    """
    state = _load_state()
    if platform not in state:
        state[platform] = {
            "active": True, "seven_day_avg": None,
            "consecutive_zeros": 0, "last_check": None,
            "stop_reason": None, "history": []
        }

    entry = {
        "timestamp":  datetime.utcnow().isoformat(),
        "engagement": engagement,
        "post_id":    post_id
    }
    state[platform]["history"].append(entry)

    # Keep only last 30 entries
    state[platform]["history"] = state[platform]["history"][-30:]

    # Update 7-day average (last 21 posts assuming 3x/day)
    recent = state[platform]["history"][-21:]
    avg = sum(e["engagement"] for e in recent) / max(len(recent), 1)
    old_avg = state[platform]["seven_day_avg"]
    state[platform]["seven_day_avg"] = avg

    # Track consecutive zeros
    if engagement == 0:
        state[platform]["consecutive_zeros"] += 1
    else:
        state[platform]["consecutive_zeros"] = 0

    state[platform]["last_check"] = datetime.utcnow().isoformat()
    _save_state(state)

    # ── Check thresholds ──────────────────────────────────────────────────────
    if not state[platform]["active"]:
        return  # Already stopped

    zeros = state[platform]["consecutive_zeros"]
    if zeros >= THRESHOLDS["consecutive_zero_posts"]:
        hard_stop(
            platform,
            f"{zeros} consecutive zero-engagement posts",
            {"consecutive_zeros": zeros, "platform": platform}
        )
        return

    if old_avg and avg < old_avg * (1 - THRESHOLDS["engagement_drop_pct"] / 100):
        drop_pct = round((1 - avg / old_avg) * 100, 1)
        hard_stop(
            platform,
            f"Engagement dropped {drop_pct}% vs 7-day average ({old_avg:.1f} → {avg:.1f})",
            {"old_avg": round(old_avg, 1), "new_avg": round(avg, 1), "drop_pct": drop_pct}
        )
        return


def run_health_check():
    """
    Full health check across all monitored platforms using opencli-rs.
    Called every 6 hours by autonomous_engine.py.
    """
    from opencli_wrapper import opencli_metrics
    from notification_hub import notify_all

    _log("Starting platform health check...")
    state   = _load_state()
    stopped = _load_stopped()
    issues  = []

    for platform in MONITORED_PLATFORMS:
        if platform in stopped:
            _log(f"[{platform}] STOPPED — skipping metrics pull")
            continue

        try:
            metrics = opencli_metrics(platform)
            if metrics.get("error"):
                _log(f"[{platform}] metrics error: {metrics['error']}")
                continue

            avg = metrics.get("avg_engagement", 0)
            _log(f"[{platform}] avg_engagement={avg}, items={metrics.get('items', 0)}")

            # Update state with live metrics
            if platform not in state:
                state[platform] = {
                    "active": True, "seven_day_avg": None,
                    "consecutive_zeros": 0, "last_check": None,
                    "stop_reason": None, "history": []
                }
            state[platform]["last_check"] = datetime.utcnow().isoformat()

            if avg < THRESHOLDS["min_avg_engagement"] and metrics.get("items", 0) > 5:
                issues.append(f"{platform}: avg engagement {avg:.1f} below minimum")

        except Exception as e:
            _log(f"[{platform}] check exception: {e}")

    _save_state(state)

    if issues:
        notify_all(
            "⚠️ Platform Health Issues",
            "\n".join(issues),
            {"type": "info", "issues": len(issues)}
        )
    else:
        _log("All platforms healthy ✓")


def get_status() -> dict:
    """Return current status of all platforms — used by /claude status command."""
    state   = _load_state()
    stopped = _load_stopped()
    return {
        "active_platforms":  [p for p in MONITORED_PLATFORMS if p not in stopped],
        "stopped_platforms": stopped,
        "per_platform": {
            p: {
                "active":      p not in stopped,
                "avg_7d":      round(state.get(p, {}).get("seven_day_avg", 0) or 0, 1),
                "consec_zero": state.get(p, {}).get("consecutive_zeros", 0),
                "stop_reason": state.get(p, {}).get("stop_reason"),
            }
            for p in MONITORED_PLATFORMS
        }
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Platform health status:")
    status = get_status()
    print(f"Active:  {status['active_platforms']}")
    print(f"Stopped: {status['stopped_platforms']}")
