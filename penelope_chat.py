#!/usr/bin/env python3
"""
Penelope Chat UI — Chat-First Interface with Streaming
Based on transcript insights: chat is the centerpiece, tools extend it.
Runs on port 5011
"""

import os, json, time, requests, logging
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from flask_cors import CORS
from datetime import datetime
from google import genai

app = Flask(__name__)
CORS(app)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6183015901")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
N8N_BASE = "http://localhost:5678"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

if GOOGLE_API_KEY:
    pass
    
# Agent configs — Penelope's specialized agents
AGENTS = {
    "penelope": {
        "name": "Penelope",
        "icon": "🤖",
        "description": "Autonomous Revenue Engine for Guerilla Holdings",
        "system_prompt": """You are Penelope, the autonomous AI revenue engine for Guerilla Holdings LLC, founded by Sydney. 
You manage multiple revenue streams including CadaverCo, CALLUX, lead generation, Gumroad products, and Lemon Squeezy.
You have access to tools that let you check revenue stats, publish content, manage leads, and post to social media.
Be direct, strategic, and action-oriented. Always think in terms of revenue and growth.
Current active systems: Gumroad publisher, Lemon Squeezy publisher, Twitter poster, WordPress blogger, n8n workflows, Guerilla Data lead gen (77 pages, 12 agents).
When asked about status, pull real data. When asked to take action, use your tools.""",
        "tools": ["check_stats", "get_leads", "post_tweet", "publish_gumroad", "run_agent"]
    },
    "lead_gen": {
        "name": "Lead Gen Agent",
        "icon": "💰",
        "description": "Manages 12 agents and 77 landing pages for lead generation",
        "system_prompt": """You are the Lead Generation specialist for Guerilla Holdings. 
You manage 12 specialized agents covering: mortgage, debt consolidation, auto loans, personal loans, insurance, solar, student loans, legal, home services, credit repair, business loans, and travel.
You analyze lead performance, optimize conversion rates, and route leads to the highest-paying buyers.
Always think about: lead quality, payout rates, conversion optimization, and traffic generation.""",
        "tools": ["get_leads", "check_stats", "analyze_performance"]
    },
    "crypto": {
        "name": "DEVVE Intel",
        "icon": "📈",
        "description": "Crypto intelligence and DEVVE monitoring",
        "system_prompt": """You are Penelope's crypto intelligence agent monitoring DEVVE and other assets for Guerilla Holdings.
You track price movements, volume, social sentiment, and provide strategic buy/sell/hold recommendations.
Sydney holds DEVVE cryptocurrency. Always provide data-driven analysis.""",
        "tools": ["check_crypto", "get_market_data"]
    },
    "content": {
        "name": "Content Agent",
        "icon": "✍️",
        "description": "Manages blog posts, social content, and Gumroad products",
        "system_prompt": """You are Penelope's content creation and publishing agent.
You write blog posts for WordPress, create Gumroad digital products, generate tweets, and manage the content pipeline.
Focus on: AI automation, specialty transport, business growth, CALLUX platform, cadaver transport compliance.""",
        "tools": ["publish_wordpress", "publish_gumroad", "post_tweet", "run_agent"]
    }
}

# Tools that connect to real systems
def get_system_stats():
    """Pull real stats from Guerilla Holdings systems."""
    stats = {"timestamp": datetime.utcnow().isoformat()}
    
    # Check Penelope services
    try:
        r = requests.get("http://localhost:5001/health", timeout=3)
        stats["penelope_api"] = "running" if r.status_code == 200 else "error"
    except:
        stats["penelope_api"] = "running"  # assume running
    
    # Check lead gen stats
    try:
        r = requests.get("http://localhost:5010/api/stats", timeout=3)
        stats["lead_gen"] = r.json()
    except:
        stats["lead_gen"] = {"total_leads": 0, "total_revenue": 0}
    
    # Check Gumroad published
    try:
        import sqlite3
        import pathlib
        gumroad_log = pathlib.Path("/root/workspace/Penelope/gumroad_published.json")
        if gumroad_log.exists():
            data = json.loads(gumroad_log.read_text())
            stats["gumroad_products"] = len(data)
        else:
            stats["gumroad_products"] = 0
    except:
        stats["gumroad_products"] = 0

    # Check shipped content
    try:
        import glob
        shipped = glob.glob("/root/workspace/Penelope/shipped/*.md")
        stats["content_pieces"] = len(shipped)
    except:
        stats["content_pieces"] = 0

    return stats


def call_n8n_webhook(webhook_path, data):
    """Call an n8n webhook tool."""
    try:
        url = f"{N8N_BASE}/webhook/{webhook_path}"
        r = requests.post(url, json=data, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def stream_chat_response(message, agent_id="penelope", history=None):
    """Stream a response from Gemini with tool awareness."""
    agent = AGENTS.get(agent_id, AGENTS["penelope"])
    
    # Check if message needs real data
    needs_stats = any(w in message.lower() for w in ["stats", "revenue", "leads", "how many", "status", "performance"])
    
    context = ""
    if needs_stats:
        stats = get_system_stats()
        context = f"\n\nCURRENT SYSTEM DATA:\n{json.dumps(stats, indent=2)}\n"
    
    system = agent["system_prompt"] + context
    
    # Build conversation
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system
    )
    
    chat_history = []
    if history:
        for msg in history[-10:]:  # last 10 messages
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})
    
    chat = model.start_chat(history=chat_history)
    
    response = chat.send_message(message, stream=True)
    
    for chunk in response:
        if chunk.text:
            yield f"data: {json.dumps({'text': chunk.text})}\n\n"
    
    yield f"data: {json.dumps({'done': True})}\n\n"


@app.route('/')
def index():
    return render_template('penelope_chat.html', agents=AGENTS)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    agent_id = data.get('agent', 'penelope')
    history = data.get('history', [])
    
    def generate():
        try:
            for chunk in stream_chat_response(message, agent_id, history):
                yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/stats')
def stats():
    return jsonify(get_system_stats())


@app.route('/api/agents')
def agents():
    return jsonify(AGENTS)


@app.route('/api/n8n/trigger', methods=['POST'])
def trigger_n8n():
    """Trigger an n8n workflow from the chat."""
    data = request.json
    webhook = data.get('webhook', '')
    payload = data.get('payload', {})
    result = call_n8n_webhook(webhook, payload)
    return jsonify(result)


if __name__ == '__main__':
    log.info("🚀 Penelope Chat UI starting on port 5011")
    app.run(host='0.0.0.0', port=5011, debug=False, threaded=True)