#!/bin/bash
# PENELOPE FULL SYSTEM STARTUP
# Run: bash /root/workspace/Penelope/start_penelope.sh

BASE="/root/workspace/Penelope"
VAULT="/root/penelope_vault.env"
PYTHON="/root/penelope_env/bin/python3"

echo "============================================"
echo "PENELOPE ACTIVATION — GUERILLA HOLDINGS"
echo "============================================"

# Load environment
export $(cat $VAULT | xargs)

# Kill any existing instances
echo "Stopping existing processes..."
pkill -f autonomous_engine.py 2>/dev/null
pkill -f gumroad_publisher.py 2>/dev/null
pkill -f social_publisher.py 2>/dev/null
pkill -f feedback_loop.py 2>/dev/null
pkill -f crypto_intelligence.py 2>/dev/null
pkill -f daily_brief.py 2>/dev/null
pkill -f financial_tracker.py 2>/dev/null
pkill -f opportunity_radar.py 2>/dev/null
sleep 3

cd $BASE

# Start all services
echo "Starting Revenue Engine..."
nohup $PYTHON autonomous_engine.py > /root/logs/engine.log 2>&1 &
echo "  PID $! — autonomous_engine.py"
sleep 2

echo "Starting Gumroad Publisher..."
nohup $PYTHON gumroad_publisher.py > /root/logs/gumroad.log 2>&1 &
echo "  PID $! — gumroad_publisher.py"
sleep 1

echo "Starting Social Publisher..."
nohup $PYTHON social_publisher.py > /root/logs/social.log 2>&1 &
echo "  PID $! — social_publisher.py"
sleep 1

echo "Starting Feedback Loop..."
nohup $PYTHON feedback_loop.py > /root/logs/feedback.log 2>&1 &
echo "  PID $! — feedback_loop.py"
sleep 1

echo "Starting Crypto Intelligence..."
nohup $PYTHON crypto_intelligence.py > /root/logs/crypto.log 2>&1 &
echo "  PID $! — crypto_intelligence.py"
sleep 1

echo "Starting Daily Brief..."
nohup $PYTHON daily_brief.py > /root/logs/brief.log 2>&1 &
echo "  PID $! — daily_brief.py"
sleep 1

echo "Starting Financial Tracker..."
nohup $PYTHON financial_tracker.py > /root/logs/finance.log 2>&1 &
echo "  PID $! — financial_tracker.py"
sleep 1

echo "Starting Opportunity Radar..."
nohup $PYTHON opportunity_radar.py > /root/logs/radar.log 2>&1 &
echo "  PID $! — opportunity_radar.py"


echo "Starting Penelope Server (API for Mission Control)..."
nohup $PYTHON penelope_server.py > /root/logs/server.log 2>&1 &
echo "  PID $! — penelope_server.py"
sleep 1

echo "Starting Agent Orchestrator..."
nohup $PYTHON agent_orchestrator.py > /root/logs/orchestrator.log 2>&1 &
echo "  PID $! — agent_orchestrator.py"

echo ""
echo "============================================"
echo "ALL SYSTEMS ACTIVE"
echo "============================================"
echo ""
echo "Check status:"
echo "  ps aux | grep python | grep -v grep"
echo ""
echo "View logs:"
echo "  tail -f /root/logs/engine.log"
echo "  tail -f /root/logs/brief.log"
echo ""
echo "Penelope is now running the 6-month 50k strategy."
echo "Morning brief will arrive at 08:30 PST."
