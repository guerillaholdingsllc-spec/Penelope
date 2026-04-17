#!/usr/bin/env python3
"""
Guerilla Holdings — Affiliate Link Injector
Maps content niches to affiliate programs.
Injects appropriate links into content before shipping to shipped/ directory.
Never blocks the content pipeline — fails silently if links unavailable.

Supported networks (instant approval, browser-based):
- Amazon Associates
- ClickBank
- Digistore24
- WarriorPlus
- JVZoo
- PartnerStack (SaaS)
- Gumroad (creator affiliates)
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

LINKS_FILE = Path("/root/workspace/Penelope/affiliate_links.json")

# Niche → affiliate program mapping
# Populated when you add your affiliate IDs to vault
NICHE_MAP = {
    # Finance niches → ClickBank / Digistore24 financial products
    "personal finance":     ["clickbank_finance", "digistore_finance"],
    "financial freedom":    ["clickbank_finance", "digistore_finance"],
    "passive income":       ["clickbank_business", "amazon_books"],
    "investing":            ["clickbank_finance", "partnerstack_fintech"],

    # Business / AI niches → PartnerStack SaaS tools
    "AI automation":        ["partnerstack_ai_tools", "amazon_ai_books"],
    "business automation":  ["partnerstack_saas", "clickbank_business"],
    "entrepreneurship":     ["clickbank_business", "amazon_business"],
    "affiliate marketing":  ["clickbank_marketing", "digistore_marketing"],
    "digital products":     ["gumroad_creators", "clickbank_digital"],

    # Transport / Logistics niches → Amazon
    "transport logistics":  ["amazon_transport", "amazon_books"],
    "freight trucking":     ["amazon_trucking", "clickbank_business"],

    # GAFC / Community niches → Amazon (safety products, books)
    "gun safety":           ["amazon_gun_safety"],
    "community safety":     ["amazon_safety", "amazon_books"],
    "minority business":    ["amazon_books", "clickbank_business"],

    # Print on demand → none (Penelope IS the product)
    "print on demand":      [],
}

# Affiliate link templates — fill in your IDs after signing up
# Format: {tag} gets replaced with your affiliate ID
AFFILIATE_PROGRAMS = {
    "clickbank_finance":     {
        "name":     "ClickBank Finance",
        "base_url": "https://hop.clickbank.net/?affiliate={CB_ID}&vendor=finprod",
        "env_key":  "CLICKBANK_ID",
        "cta":      "Check out this financial resource →",
    },
    "clickbank_business":    {
        "name":     "ClickBank Business",
        "base_url": "https://hop.clickbank.net/?affiliate={CB_ID}&vendor=bizprod",
        "env_key":  "CLICKBANK_ID",
        "cta":      "Grow your business →",
    },
    "clickbank_marketing":   {
        "name":     "ClickBank Marketing",
        "base_url": "https://hop.clickbank.net/?affiliate={CB_ID}&vendor=mktprod",
        "env_key":  "CLICKBANK_ID",
        "cta":      "Level up your marketing →",
    },
    "clickbank_digital":     {
        "name":     "ClickBank Digital",
        "base_url": "https://hop.clickbank.net/?affiliate={CB_ID}&vendor=digprod",
        "env_key":  "CLICKBANK_ID",
        "cta":      "Get instant digital access →",
    },
    "digistore_finance":     {
        "name":     "Digistore24 Finance",
        "base_url": "https://www.digistore24.com/redir/{DS_ID}/finance",
        "env_key":  "DIGISTORE24_ID",
        "cta":      "Financial freedom starts here →",
    },
    "digistore_marketing":   {
        "name":     "Digistore24 Marketing",
        "base_url": "https://www.digistore24.com/redir/{DS_ID}/marketing",
        "env_key":  "DIGISTORE24_ID",
        "cta":      "Transform your marketing →",
    },
    "amazon_books":          {
        "name":     "Amazon Books",
        "base_url": "https://www.amazon.com/s?k={SEARCH_TERM}&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Get the book →",
    },
    "amazon_business":       {
        "name":     "Amazon Business",
        "base_url": "https://www.amazon.com/s?k=business+automation&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Shop business tools →",
    },
    "amazon_gun_safety":     {
        "name":     "Amazon Gun Safety",
        "base_url": "https://www.amazon.com/s?k=gun+safe+storage&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Safe storage solutions →",
    },
    "amazon_safety":         {
        "name":     "Amazon Safety",
        "base_url": "https://www.amazon.com/s?k=home+safety&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Safety essentials →",
    },
    "amazon_transport":      {
        "name":     "Amazon Transport",
        "base_url": "https://www.amazon.com/s?k=trucking+equipment&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Transport gear →",
    },
    "amazon_trucking":       {
        "name":     "Amazon Trucking",
        "base_url": "https://www.amazon.com/s?k=trucking+tools&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Trucking essentials →",
    },
    "amazon_ai_books":       {
        "name":     "Amazon AI Books",
        "base_url": "https://www.amazon.com/s?k=AI+automation+business&tag={AMAZON_TAG}",
        "env_key":  "AMAZON_ASSOCIATES_TAG",
        "cta":      "Learn AI automation →",
    },
    "partnerstack_saas":     {
        "name":     "PartnerStack SaaS",
        "base_url": "https://partnerstack.com/ref/{PS_ID}",
        "env_key":  "PARTNERSTACK_ID",
        "cta":      "Try this tool free →",
    },
    "partnerstack_ai_tools": {
        "name":     "PartnerStack AI Tools",
        "base_url": "https://partnerstack.com/ref/{PS_ID}/ai",
        "env_key":  "PARTNERSTACK_ID",
        "cta":      "Automate with AI →",
    },
    "partnerstack_fintech":  {
        "name":     "PartnerStack Fintech",
        "base_url": "https://partnerstack.com/ref/{PS_ID}/finance",
        "env_key":  "PARTNERSTACK_ID",
        "cta":      "Modern finance tools →",
    },
    "gumroad_creators":      {
        "name":     "Gumroad Creators",
        "base_url": "https://gumroad.com/l/{GUMROAD_ID}",
        "env_key":  "GUMROAD_AFFILIATE_ID",
        "cta":      "Get instant access →",
    },
}


def _build_link(program_key: str, search_term: str = "") -> Optional[str]:
    """Build a live affiliate link for a program."""
    prog = AFFILIATE_PROGRAMS.get(program_key)
    if not prog:
        return None

    env_key = prog["env_key"]
    aff_id  = os.getenv(env_key, "")
    if not aff_id:
        return None  # Not signed up yet

    url = prog["base_url"]
    url = url.replace("{AMAZON_TAG}", aff_id)
    url = url.replace("{CB_ID}", aff_id)
    url = url.replace("{DS_ID}", aff_id)
    url = url.replace("{PS_ID}", aff_id)
    url = url.replace("{GUMROAD_ID}", aff_id)
    url = url.replace("{SEARCH_TERM}", search_term.replace(" ", "+"))
    return url


def get_links_for_niche(niche: str) -> list:
    """
    Return list of affiliate link dicts for a niche.
    [{program, name, url, cta}]
    Only returns programs where you have an affiliate ID configured.
    """
    niche_lower = niche.lower()
    programs    = []

    # Find matching niche key
    for niche_key, program_keys in NICHE_MAP.items():
        if niche_key in niche_lower or niche_lower in niche_key:
            for prog_key in program_keys:
                url = _build_link(prog_key, search_term=niche)
                if url:
                    prog = AFFILIATE_PROGRAMS.get(prog_key, {})
                    programs.append({
                        "program": prog_key,
                        "name":    prog.get("name", prog_key),
                        "url":     url,
                        "cta":     prog.get("cta", "Learn more →")
                    })

    return programs[:2]  # Max 2 affiliate links per piece of content


def inject_links(content: str, niche: str, platform: str = "blog") -> str:
    """
    Inject affiliate links into content.
    Returns content with links appended.
    Never throws — returns original content on any error.
    """
    try:
        links = get_links_for_niche(niche)
        if not links:
            return content  # No links available — return as-is

        # Don't inject links into short social posts (Twitter, etc.)
        short_platforms = ["twitter", "tiktok", "instagram"]
        if platform.lower() in short_platforms:
            return content

        # Append links section
        link_section = "\n\n---\n**Recommended Resources:**\n"
        for link in links:
            link_section += f"• [{link['cta']}]({link['url']})\n"

        return content + link_section

    except Exception as e:
        log.debug(f"inject_links failed silently: {e}")
        return content  # Never block content pipeline


def save_custom_link(name: str, url: str, niche: str, cta: str = "Learn more →"):
    """
    Save a custom affiliate link (e.g., from ClickBank product you've joined).
    Persisted to affiliate_links.json for use across content.
    """
    links = {}
    if LINKS_FILE.exists():
        try:
            links = json.loads(LINKS_FILE.read_text())
        except Exception:
            pass

    if niche not in links:
        links[niche] = []

    links[niche].append({"name": name, "url": url, "cta": cta})
    LINKS_FILE.write_text(json.dumps(links, indent=2))
    log.info(f"Saved custom link: {name} for niche: {niche}")


def get_configured_programs() -> list:
    """Return list of affiliate programs you've signed up for (have env vars set)."""
    configured = []
    for prog_key, prog in AFFILIATE_PROGRAMS.items():
        env_key = prog["env_key"]
        if os.getenv(env_key):
            configured.append({"key": prog_key, "name": prog["name"], "env": env_key})
    return configured


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    configured = get_configured_programs()
    print(f"\nConfigured affiliate programs: {len(configured)}")
    for prog in configured:
        print(f"  ✅ {prog['name']} ({prog['env']})")

    unconfigured = [p for p in AFFILIATE_PROGRAMS if p not in [c["key"] for c in configured]]
    if unconfigured:
        print(f"\nNot yet configured ({len(unconfigured)}):")
        needed_envs = set()
        for prog_key in unconfigured:
            env = AFFILIATE_PROGRAMS[prog_key]["env_key"]
            needed_envs.add(env)
        for env in sorted(needed_envs):
            print(f"  ⬜ Add to vault: {env}=your_id")

    if "--test" in sys.argv:
        test_niche = "personal finance"
        links = get_links_for_niche(test_niche)
        print(f"\nLinks for '{test_niche}': {len(links)}")
        for link in links:
            print(f"  {link['name']}: {link['url']}")
