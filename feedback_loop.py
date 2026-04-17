import os, json, time, requests, datetime
from google import genai


import os as _fb_os
try:
    for _fb_line in open("/root/penelope_vault.env"):
        if "=" in _fb_line and not _fb_line.startswith("#"):
            _k, _v = _fb_line.strip().split("=", 1)
            _fb_os.environ.setdefault(_k.strip(), _v.strip())
except: pass


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
T_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k").strip()
C_ID           = os.getenv("TELEGRAM_CHAT_ID", "6183015901").strip()
GUMROAD_KEY    = os.getenv("GUMROAD_API_KEY", "2v9GyYHc9fvA0svgEpCICDKjBfenz_Tep8JHpXKDKU4").strip()
FEED_FILE      = "/root/workspace/Penelope/feed.json"
SALES_LOG      = "/root/workspace/Penelope/sales_log.json"
GUMROAD_BASE   = "https://api.gumroad.com/v2"

client = genai.Client(api_key=GOOGLE_API_KEY)

def log(msg):
    print(f"[FEEDBACK {datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


import requests as _tg_requests
from datetime import datetime as _tg_dt

# ── Vault loader ──────────────────────────────────────────────────────────────
def _load_vault():
    env = {}
    try:
        for line in open("/root/penelope_vault.env"):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    except: pass
    return env
_VAULT = _load_vault()
import os as _os
for _k, _v in _VAULT.items():
    if _k not in _os.environ: _os.environ[_k] = _v




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


def post_to_feed(title, content, status="info"):
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            with open(FEED_FILE, "r") as f: feed = json.load(f)
        feed.insert(0, {"id": int(time.time()), "title": title, "content": content,
                        "status": status, "agent": "FeedbackLoop",
                        "timestamp": datetime.datetime.now().isoformat()})
        with open(FEED_FILE, "w") as f: json.dump(feed[:100], f, indent=2)
    except Exception as e: log(f"Feed error: {e}")

def get_sales_data():
    try:
        # Get all sales from last 30 days
        after = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        res = requests.get(f"{GUMROAD_BASE}/sales",
            headers={"Authorization": f"Bearer {GUMROAD_KEY}"},
            params={"after": after}, timeout=20)
        data = res.json()
        if data.get("success"):
            return data.get("sales", [])
        return []
    except Exception as e:
        log(f"Sales fetch error: {e}")
        return []

def get_products():
    try:
        res = requests.get(f"{GUMROAD_BASE}/products",
            headers={"Authorization": f"Bearer {GUMROAD_KEY}"}, timeout=20)
        data = res.json()
        return {p["id"]: p for p in data.get("products", [])} if data.get("success") else {}
    except Exception as e:
        log(f"Products fetch error: {e}")
        return {}

def analyze_and_optimize(products, sales):
    today = datetime.datetime.now().strftime("%B %d, %Y")

    # Build sales summary
    sales_by_product = {}
    total_revenue = 0
    for sale in sales:
        pid = sale.get("product_id", "")
        amount = float(sale.get("price", 0))
        if pid not in sales_by_product:
            sales_by_product[pid] = {"count": 0, "revenue": 0}
        sales_by_product[pid]["count"] += 1
        sales_by_product[pid]["revenue"] += amount
        total_revenue += amount

    product_summary = []
    for pid, product in products.items():
        sales_info = sales_by_product.get(pid, {"count": 0, "revenue": 0})
        product_summary.append({
            "name": product.get("name", ""),
            "price": product.get("price", 0) / 100,
            "sales": sales_info["count"],
            "revenue": sales_info["revenue"] / 100,
            "url": product.get("short_url", ""),
            "published": product.get("published", False)
        })

    # Sort by revenue
    product_summary.sort(key=lambda x: x["revenue"], reverse=True)

    prompt = f"""You are the business intelligence analyst for Guerilla Holdings.
Analyze these Gumroad sales results and provide specific, actionable optimization recommendations.

SALES DATA (Last 30 days) — {today}:
Total Revenue: ${total_revenue/100:.2f}
Total Sales: {len(sales)}

PRODUCT PERFORMANCE:
{json.dumps(product_summary, indent=2)}

Provide a COMPLETE analysis:

## REVENUE REPORT
- Total revenue this month
- Best performing product (why it works)
- Worst performing products (what to change)
- Revenue trend assessment

## IMMEDIATE ACTIONS (Do this week)
For each product with 0 sales, give ONE specific change:
- Title change suggestion (more specific, benefit-focused)
- Price adjustment recommendation
- Description improvement
- Should it be kept, improved, or removed?

## WHAT'S WORKING
- Which product/category shows the most promise
- What the successful products have in common

## NEXT PRODUCT TO BUILD
Based on the data, what product should Penelope build next?
Be specific — give the exact title, price point, and target audience.

## 30-DAY GROWTH PLAN
3 specific actions to double revenue next month.
Be direct and specific. No vague advice."""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(response, "text", ""), product_summary, total_revenue/100
    except Exception as e:
        log(f"Analysis error: {e}")
        return "", product_summary, total_revenue/100

def run_feedback_loop():
    log("="*50)
    log("FEEDBACK LOOP RUNNING")
    log("="*50)

    products = get_products()
    sales = get_sales_data()
    log(f"Found {len(products)} products, {len(sales)} sales in last 30 days")

    analysis, product_summary, total_revenue = analyze_and_optimize(products, sales)

    # Save analysis
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    fname = f"/root/workspace/Penelope/shipped/{date_str}_sales_analysis.md"
    with open(fname, "w") as f:
        f.write(f"# Guerilla Holdings Sales Analysis\n")
        f.write(f"Date: {datetime.datetime.now().isoformat()}\n\n")
        f.write(analysis)
    log(f"Analysis saved: {fname}")

    # Send to Telegram
    today = datetime.datetime.now().strftime("%B %d, %Y")
    msg = f"*GUERILLA HOLDINGS — DAILY SALES REPORT*\n{today}\n\n"
    msg += f"💰 *30-Day Revenue: ${total_revenue:.2f}*\n"
    msg += f"📦 Total Sales: {len(sales)}\n"
    msg += f"🏪 Active Products: {sum(1 for p in product_summary if p['published'])}\n\n"

    if product_summary:
        msg += "*TOP PRODUCTS:*\n"
        for p in product_summary[:5]:
            emoji = "🔥" if p["sales"] > 0 else "⚪"
            msg += f"{emoji} {p['name']}\n   ${p['price']} · {p['sales']} sales · ${p['revenue']:.2f}\n\n"

    msg += "_Full analysis and optimization recommendations saved to shipped/ folder._\n— Penelope"
    _tg_emergency_only(msg)

    # Send key recommendations
    if analysis:
        _tg_emergency_only(f"*OPTIMIZATION RECOMMENDATIONS:*\n\n{analysis[:3000]}")

    post_to_feed("Daily Sales Report",
        f"30-day revenue: ${total_revenue:.2f} | {len(sales)} sales | Analysis complete", "success")

    log(f"DONE — Revenue: ${total_revenue:.2f}")

if __name__ == "__main__":
    log("Feedback Loop starting")
    while True:
        try:
            run_feedback_loop()
        except Exception as e:
            log(f"CRITICAL ERROR: {e}")
            try: _tg_emergency_only(f"Feedback Loop Error: {e}")
            except: pass
        log("Sleeping 24 hours...")
        time.sleep(24 * 60 * 60)