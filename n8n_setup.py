#!/usr/bin/env python3
"""
Penelope n8n Workflow Setup
Creates n8n workflows that connect Penelope's agents to real tools:
- Image generation
- Content publishing
- Lead routing
- Social posting
- Revenue tracking
"""

import requests, json, os, time, logging


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


N8N_BASE = "http://localhost:5678"
N8N_USER = "penelope"
N8N_PASS = "guerilla2024"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [n8n] %(message)s")
log = logging.getLogger(__name__)


def get_n8n_token():
    """Get n8n API token."""
    try:
        r = requests.post(
            f"{N8N_BASE}/api/v1/login",
            json={"email": "penelope@guerillaholdings.com", "password": N8N_PASS},
            timeout=10
        )
        return r.json().get("data", {}).get("token")
    except Exception as e:
        log.error(f"n8n login failed: {e}")
        return None


def create_workflow(token, workflow_data):
    """Create a workflow in n8n."""
    try:
        headers = {"X-N8N-API-KEY": token} if token else {}
        r = requests.post(
            f"{N8N_BASE}/api/v1/workflows",
            headers=headers,
            json=workflow_data,
            timeout=15
        )
        return r.json()
    except Exception as e:
        log.error(f"Create workflow failed: {e}")
        return None


# Workflow definitions
WORKFLOWS = {
    "penelope_content_publisher": {
        "name": "Penelope Content Auto-Publisher",
        "active": True,
        "nodes": [
            {
                "id": "webhook-1",
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "position": [100, 200],
                "parameters": {
                    "path": "publish-content",
                    "httpMethod": "POST",
                    "responseMode": "onReceived"
                }
            },
            {
                "id": "code-1",
                "name": "Process Content",
                "type": "n8n-nodes-base.code",
                "position": [300, 200],
                "parameters": {
                    "jsCode": """
const data = $input.first().json;
const category = data.category || 'general';
const content = data.content || '';
const title = data.title || 'New Post';

return [{
  json: {
    title: title,
    content: content,
    category: category,
    timestamp: new Date().toISOString(),
    status: 'processed'
  }
}];
"""
                }
            }
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [[{"node": "Process Content", "type": "main", "index": 0}]]
            }
        }
    },
    "penelope_lead_router": {
        "name": "Penelope Lead Router",
        "active": True,
        "nodes": [
            {
                "id": "webhook-leads",
                "name": "Lead Webhook",
                "type": "n8n-nodes-base.webhook",
                "position": [100, 200],
                "parameters": {
                    "path": "route-lead",
                    "httpMethod": "POST",
                    "responseMode": "lastNode"
                }
            },
            {
                "id": "code-leads",
                "name": "Score Lead",
                "type": "n8n-nodes-base.code",
                "position": [300, 200],
                "parameters": {
                    "jsCode": """
const lead = $input.first().json;
const category = lead.category || 'personal_loan';
const credit = lead.credit_range || 'fair';
const income = lead.income_range || '$35k-$50k';

// Score lead quality
let score = 50;
if (credit === 'excellent') score += 40;
else if (credit === 'good') score += 25;
else if (credit === 'fair') score += 10;

if (income === '$100k+') score += 30;
else if (income === '$75k-$100k') score += 20;
else if (income === '$50k-$75k') score += 10;

const payout_estimates = {
  mortgage: 85, debt: 40, auto: 25, personal_loan: 35,
  insurance: 45, solar: 65, student_loan: 30, legal: 120,
  home_services: 25, credit_repair: 28, business_loan: 75, travel: 18
};

const estimated_value = (payout_estimates[category] || 30) * (score / 100);

return [{
  json: {
    ...lead,
    quality_score: score,
    estimated_value: estimated_value.toFixed(2),
    routed_at: new Date().toISOString(),
    status: score > 70 ? 'premium' : score > 40 ? 'standard' : 'basic'
  }
}];
"""
                }
            }
        ],
        "connections": {
            "Lead Webhook": {
                "main": [[{"node": "Score Lead", "type": "main", "index": 0}]]
            }
        }
    },
    "penelope_daily_report": {
        "name": "Penelope Daily Revenue Report",
        "active": True,
        "nodes": [
            {
                "id": "schedule-1",
                "name": "Daily Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "position": [100, 200],
                "parameters": {
                    "rule": {
                        "interval": [{"field": "hours", "hoursInterval": 24}]
                    }
                }
            },
            {
                "id": "http-stats",
                "name": "Get Stats",
                "type": "n8n-nodes-base.httpRequest",
                "position": [300, 200],
                "parameters": {
                    "url": "http://localhost:5010/api/stats",
                    "method": "GET"
                }
            },
            {
                "id": "telegram-report",
                "name": "Send Telegram Report",
                "type": "n8n-nodes-base.httpRequest",
                "position": [500, 200],
                "parameters": {
                    "url": f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN', '')}/sendMessage",
                    "method": "POST",
                    "bodyParametersUi": {
                        "parameter": [
                            {"name": "chat_id", "value": os.getenv("TELEGRAM_CHAT_ID", "6183015901")},
                            {"name": "text", "value": "=`📊 *Daily Report*\n\nLeads: ${$node['Get Stats'].json.total_leads}\nRevenue: $${$node['Get Stats'].json.total_revenue}\nConversion: ${$node['Get Stats'].json.conversion_rate}%`"},
                            {"name": "parse_mode", "value": "Markdown"}
                        ]
                    }
                }
            }
        ],
        "connections": {
            "Daily Schedule": {
                "main": [[{"node": "Get Stats", "type": "main", "index": 0}]]
            },
            "Get Stats": {
                "main": [[{"node": "Send Telegram Report", "type": "main", "index": 0}]]
            }
        }
    }
}


def setup_n8n_workflows():
    """Set up all n8n workflows."""
    log.info("Setting up n8n workflows...")

    # Check if n8n is running
    try:
        r = requests.get(f"{N8N_BASE}/healthz", timeout=5)
        log.info(f"n8n status: {r.status_code}")
    except:
        log.error("n8n is not running on port 5678. Start it first.")
        return False

    token = get_n8n_token()

    for name, workflow in WORKFLOWS.items():
        log.info(f"Creating workflow: {workflow['name']}")
        result = create_workflow(token, workflow)
        if result:
            log.info(f"✅ Created: {workflow['name']}")
        else:
            log.warning(f"⚠️ Could not create: {workflow['name']}")
        time.sleep(1)

    log.info("n8n workflow setup complete!")
    return True


if __name__ == "__main__":
    setup_n8n_workflows()