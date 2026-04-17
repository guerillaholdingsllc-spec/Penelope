#!/usr/bin/env python3
"""
opencli_run — wrapper for opencli-rs binary.
Drop this into api.py or import as standalone.
Executes any opencli-rs command, returns structured dict.
"""

import subprocess
import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

# Path to opencli-rs binary — auto-detects common install locations
OPENCLI_BIN = os.getenv("OPENCLI_BIN", "opencli-rs")


def opencli_run(
    site: str,
    command: str,
    args: dict = None,
    output_format: str = "json",
    timeout: int = 60
) -> dict:
    """
    Execute an opencli-rs command and return structured output.

    Args:
        site:    Site name e.g. "twitter", "reddit", "linkedin"
        command: Command e.g. "trending", "hot", "search", "timeline"
        args:    Dict of additional args e.g. {"limit": 10, "subreddit": "entrepreneur"}
        output_format: Output format — always "json" for programmatic use
        timeout: Max seconds to wait

    Returns:
        {
            "success": bool,
            "data": list | dict,
            "raw": str,
            "error": str | None
        }

    Examples:
        opencli_run("twitter", "trending")
        opencli_run("reddit", "hot", {"subreddit": "personalfinance", "limit": 10})
        opencli_run("hackernews", "top", {"limit": 20})
        opencli_run("linkedin", "search", {"query": "gun safety nonprofit"})
        opencli_run("youtube", "search", {"query": "financial freedom", "limit": 5})
        opencli_run("twitter", "post", {"text": "Hello from Penelope!"})
    """
    if args is None:
        args = {}

    # Build command list
    cmd = [OPENCLI_BIN, site, command, "--format", output_format]
    for key, val in args.items():
        flag = f"--{key.replace('_', '-')}"
        cmd.extend([flag, str(val)])

    log.info(f"opencli_run: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
            log.warning(f"opencli_run failed [{site} {command}]: {error_msg}")
            return {
                "success": False,
                "data": [],
                "raw": result.stdout,
                "error": error_msg
            }

        raw = result.stdout.strip()
        if not raw:
            return {"success": True, "data": [], "raw": "", "error": None}

        # Parse JSON output
        try:
            parsed = json.loads(raw)
            # opencli-rs returns either a list or {"data": [...]} or {"rows": [...]}
            if isinstance(parsed, list):
                data = parsed
            elif isinstance(parsed, dict):
                data = parsed.get("data") or parsed.get("rows") or parsed.get("items") or parsed
            else:
                data = parsed
            return {"success": True, "data": data, "raw": raw, "error": None}
        except json.JSONDecodeError:
            # Non-JSON output — treat as plain text success
            return {"success": True, "data": raw, "raw": raw, "error": None}

    except subprocess.TimeoutExpired:
        log.error(f"opencli_run timeout [{site} {command}] after {timeout}s")
        return {"success": False, "data": [], "raw": "", "error": f"Timeout after {timeout}s"}
    except FileNotFoundError:
        log.error(f"opencli-rs binary not found at: {OPENCLI_BIN}")
        return {"success": False, "data": [], "raw": "", "error": "opencli-rs binary not found"}
    except Exception as e:
        log.error(f"opencli_run exception [{site} {command}]: {e}")
        return {"success": False, "data": [], "raw": "", "error": str(e)}


def opencli_post(site: str, text: str, extra_args: dict = None) -> dict:
    """Convenience wrapper for posting content to a platform."""
    args = {"text": text, **(extra_args or {})}
    return opencli_run(site, "post", args)


def opencli_trending(site: str, limit: int = 20) -> list:
    """Get trending content from a site. Returns list of items."""
    result = opencli_run(site, "trending" if site == "twitter" else "hot", {"limit": limit})
    if result["success"] and isinstance(result["data"], list):
        return result["data"]
    return []


def opencli_search(site: str, query: str, limit: int = 10) -> list:
    """Search a site for a query. Returns list of results."""
    result = opencli_run(site, "search", {"query": query, "limit": limit})
    if result["success"] and isinstance(result["data"], list):
        return result["data"]
    return []


def opencli_metrics(site: str, command: str = "timeline", limit: int = 20) -> dict:
    """
    Pull engagement metrics from a platform.
    Returns summary dict with engagement stats.
    """
    result = opencli_run(site, command, {"limit": limit})
    if not result["success"]:
        return {"platform": site, "error": result["error"], "items": 0}

    data = result["data"] if isinstance(result["data"], list) else []
    total_likes    = sum(int(item.get("likes", item.get("score", 0))) for item in data if isinstance(item, dict))
    total_comments = sum(int(item.get("comments", item.get("num_comments", 0))) for item in data if isinstance(item, dict))
    total_shares   = sum(int(item.get("retweets", item.get("shares", 0))) for item in data if isinstance(item, dict))

    return {
        "platform":       site,
        "items":          len(data),
        "total_likes":    total_likes,
        "total_comments": total_comments,
        "total_shares":   total_shares,
        "avg_engagement": round((total_likes + total_comments + total_shares) / max(len(data), 1), 1),
        "error":          None
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing opencli_run...")
    print("\n[HackerNews Top]")
    result = opencli_run("hackernews", "top", {"limit": 5})
    print(f"Success: {result['success']}, Items: {len(result['data']) if isinstance(result['data'], list) else 'N/A'}")
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        for item in (result["data"][:3] if isinstance(result["data"], list) else []):
            print(f"  - {item.get('title', item)[:80]}")
