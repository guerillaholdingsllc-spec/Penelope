"""
vessel_intelligence_agent.py
Market intelligence — competitor monitoring, App Store trends, wellness market signals
Uses Firecrawl for scraping, Gemini for analysis
Runs weekly Sunday 6AM, reports to Notion + Telegram
"""
import os, json, requests, time
from datetime import datetime
from google import genai as _genai

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


_vessel_client = None

def _get_client():
    global _vessel_client
    if _vessel_client is None:
        _vessel_client = _genai.Client(api_key=GOOGLE_API_KEY)
    return _vessel_client

VAULT = {}
try:
    with open("/root/penelope_vault.env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                VAULT[k.strip()] = v.strip()
except:
    pass

GOOGLE_API_KEY = VAULT.get("GOOGLE_API_KEY", "")
FIRECRAWL_KEY  = VAULT.get("FIRECRAWL_KEY", "")
TELEGRAM_TOKEN = VAULT.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = "6183015901"
NOTION_TOKEN   = VAULT.get("NOTION_TOKEN", "")
NOTION_OPS_DB  = "f9094ce8-4cff-40cd-9d6c-323072627263"
COMPETITOR_URLS = [
    "https://www.headspace.com",
    "https://www.calm.com",
    "https://www.noom.com",
]

INTEL_TOPICS = [
    "manifestation app 2025 2026 trends",
    "law of attraction app subscription",
    "spiritual wellness app growth",
    "habit formation app market",
]

def gemini(prompt, temperature=0.7, max_tokens=2000):
    try:
        client = _get_client()
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(r, "text", "") or ""
    except Exception as e:
        print(f"Gemini error: {e}")
        return ""

def firecrawl_search(query):
    """Search via Firecrawl"""
    if not FIRECRAWL_KEY:
        return []
    try:
        r = requests.post(
            "https://api.firecrawl.dev/v1/search",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}",
                     "Content-Type": "application/json"},
            json={"query": query, "limit": 5},
            timeout=30
        )
        if r.ok:
            return r.json().get("data", [])
    except Exception as e:
        print(f"Firecrawl search error: {e}")
    return []

def firecrawl_scrape(url):
    """Scrape a URL via Firecrawl"""
    if not FIRECRAWL_KEY:
        return ""
    try:
        r = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}",
                     "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30
        )
        if r.ok:
            return r.json().get("data", {}).get("markdown", "")[:3000]
    except Exception as e:
        print(f"Firecrawl scrape error: {e}")
    return ""

def analyze_competitor(url, content):
    """Analyze a competitor's current positioning"""
    prompt = f"""Analyze this wellness/manifestation app competitor for strategic insights.

URL: {url}
Content: {content[:2000]}

Provide:
1. Pricing model (what they charge)
2. Key differentiator (what makes them unique)
3. Weakness (what they're NOT doing that Vessel does)
4. Threat level to Vessel (low/medium/high) with reason

Keep response under 150 words. Be specific."""

    return gemini(prompt, max_tokens=300)

def analyze_market_trends(search_results):
    """Synthesize market trends from search results"""
    combined = "\n\n".join([
        f"Source: {r.get('url', '')}\n{r.get('markdown', r.get('description', ''))[:500]}"
        for r in search_results[:5]
    ])

    prompt = f"""Analyze these market research results for the manifestation/wellness app space.

DATA:
{combined}

Identify:
1. Top 3 emerging trends Vessel should act on
2. Underserved audience segment Vessel could target
3. Content angle getting most engagement
4. One specific tactical opportunity for Vessel in the next 30 days

Be specific and actionable. Under 200 words."""

    return gemini(prompt, max_tokens=400)

def log_to_notion(title, content):
    if not NOTION_TOKEN:
        return
    try:
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        payload = {
            "parent": {"database_id": NOTION_OPS_DB},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": "intelligence"}},
                "Date": {"date": {"start": datetime.utcnow().isoformat()}}
            },
            "children": [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}
            }]
        }
        requests.post("https://api.notion.com/v1/pages",
                      headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"Notion error: {e}")

def run_intelligence_report():
    """Main runner — full market intelligence sweep"""
    print(f"[{datetime.utcnow().isoformat()}] VesselIntelAgent running weekly sweep")

    report = {
        "competitors": {},
        "market_trends": {},
        "opportunities": [],
        "generated_at": datetime.utcnow().isoformat()
    }

    # Competitor analysis
    print("Analyzing competitors...")
    for url in COMPETITOR_URLS:
        name = url.split("//")[1].split(".")[1]
        print(f"  Scraping {name}...")
        content = firecrawl_scrape(url)
        if content:
            analysis = analyze_competitor(url, content)
            report["competitors"][name] = analysis
            print(f"  {name}: {analysis[:80]}...")
        time.sleep(2)

    # Market trend research
    print("Researching market trends...")
    all_results = []
    for topic in INTEL_TOPICS[:2]:  # limit for speed
        results = firecrawl_search(topic)
        all_results.extend(results)
        time.sleep(1)

    if all_results:
        trend_analysis = analyze_market_trends(all_results)
        report["market_trends"] = trend_analysis
        print(f"Trends: {trend_analysis[:100]}...")

    # Synthesize opportunities
    synth_prompt = f"""Based on this competitor and market analysis, give Sydney (founder of Vessel) 
3 specific opportunities she should act on THIS WEEK.

Competitor insights: {json.dumps(report['competitors'])[:500]}
Market trends: {str(report.get('market_trends', ''))[:500]}

Format as numbered list. Be tactical, not theoretical."""

    opportunities = gemini(synth_prompt, max_tokens=300)
    report["opportunities"] = opportunities

    # Save report
    report_path = f"/root/workspace/Penelope/shipped/vessel_intel_{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Log to Notion
    summary = f"Vessel Intel Report — {datetime.utcnow().strftime('%Y-%m-%d')}\n\nOpportunities:\n{opportunities}"
    log_to_notion(f"Vessel Intel — {datetime.utcnow().strftime('%Y-%m-%d')}", summary)

    # Telegram Sydney
    if TELEGRAM_TOKEN:
        try:
            msg = (
                f"🔍 <b>Vessel Weekly Intel</b>\n"
                f"Competitors analyzed: {len(report['competitors'])}\n\n"
                f"<b>Top Opportunities:</b>\n{opportunities[:500]}"
            )
            _tg_emergency_only("[suppressed direct call]")
        except:
            pass

    print(f"Intel report saved: {report_path}")
    return report

if __name__ == "__main__":
    result = run_intelligence_report()
    print(f"Done. Competitors: {list(result['competitors'].keys())}")