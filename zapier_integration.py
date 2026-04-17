#!/usr/bin/env python3
"""
PENELOPE ZAPIER INTEGRATION
Fires Zapier webhook on key business events.
Unlocks 6,000+ app integrations (Slack, Sheets, SMS, HubSpot, etc.)

Events fired:
- new_lead: Every opt-in from landing pages
- new_sale: Every Stripe/Gumroad payment
- morning_brief: Daily 8AM summary
- skill_deployed: New skill passes Supreme Court
- hot_signal: Buying signal detected
- grant_drafted: GAFC grant application ready
- trade_executed: Alpaca paper trade placed
"""
import requests, json
from datetime import datetime

ZAPIER_URL = "https://hooks.zapier.com/hooks/catch/27163026/u7kdw8o/"

def fire(event_type, data=None):
    """Fire Zapier webhook with event data."""
    payload = {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
        "source": "penelope_autonomous_engine",
        **(data or {})
    }
    try:
        r = requests.post(ZAPIER_URL, json=payload, timeout=10)
        return r.status_code in [200, 201]
    except:
        return False

def new_lead(email, name, brand, source):
    return fire("new_lead", {
        "email": email, "name": name,
        "brand": brand, "source": source,
        "landing_page": f"https://trustchainservices.com/funnels/{brand}/",
        "crm": "https://app.close.com"
    })

def new_sale(email, amount, product, platform):
    return fire("new_sale", {
        "email": email,
        "amount_usd": amount,
        "product": product,
        "platform": platform,
        "stripe_dashboard": "https://dashboard.stripe.com",
        "gumroad_dashboard": "https://app.gumroad.com/dashboard"
    })

def morning_brief(revenue, leads, skills, top_action):
    return fire("morning_brief", {
        "revenue_today": revenue,
        "new_leads": leads,
        "skills_live": skills,
        "top_action": top_action,
        "notion_hq": "https://notion.so/3368bf86ffb181829402e2945c1e6a3c"
    })

def skill_deployed(skill_id, objective, rps_score):
    return fire("skill_deployed", {
        "skill_id": skill_id,
        "objective": objective,
        "rps_score": rps_score
    })

def hot_signal(signal_type, detail, engagement=0):
    return fire("hot_signal", {
        "signal_type": signal_type,
        "detail": detail,
        "engagement": engagement
    })

def grant_drafted(grant_name, amount, deadline):
    return fire("grant_drafted", {
        "grant_name": grant_name,
        "amount": amount,
        "deadline": deadline,
        "org": "GAFC — Glocks and Fried Chicken"
    })

def trade_executed(symbol, side, qty, strategy):
    return fire("trade_executed", {
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "strategy": strategy,
        "account": "PA3R2OZOWUHM",
        "type": "paper_trade"
    })

if __name__ == "__main__":
    print(fire("test", {"message": "Zapier webhook working"}))
