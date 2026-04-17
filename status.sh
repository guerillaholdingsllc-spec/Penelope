#!/bin/bash
echo "============================================"
echo "PENELOPE SYSTEM STATUS"
echo "============================================"
echo ""

services=(
    "autonomous_engine.py:Revenue Engine"
    "gumroad_publisher.py:Gumroad Publisher"
    "social_publisher.py:Social Publisher"
    "feedback_loop.py:Feedback Loop"
    "crypto_intelligence.py:Crypto Intel"
    "daily_brief.py:Daily Brief"
    "financial_tracker.py:Financial Tracker"
    "opportunity_radar.py:Opportunity Radar"
)

for s in "${services[@]}"; do
    script="${s%%:*}"
    name="${s##*:}"
    if pgrep -f "$script" > /dev/null; then
        echo "✓ $name"
    else
        echo "✗ $name — NOT RUNNING"
    fi
done

echo ""
echo "PORT STATUS:"
echo "  :8080 (Mission Control HTML):"
if curl -s http://localhost:8080 > /dev/null 2>&1; then echo "  ✓ Running"; else echo "  ✗ Down"; fi
echo "  :5002 (CadaverCo API):"
if curl -s http://localhost:5002/api/health > /dev/null 2>&1; then echo "  ✓ Running"; else echo "  ✗ Down"; fi

echo ""
echo "RECENT SHIPPED FILES:"
ls -lt /root/workspace/Penelope/shipped/ | head -5

echo ""
echo "FINANCE:"
if [ -f "/root/workspace/Penelope/finance/finance_state.json" ]; then
    python3 -c "
import json
with open('/root/workspace/Penelope/finance/finance_state.json') as f:
    s = json.load(f)
print(f'  Deficit: \${s[\"deficit\"]:,.2f}')
print(f'  Revenue: \${s[\"total_revenue\"]:,.2f}')
print(f'  Fund: \${s[\"autonomy_fund\"]:.2f}')
"
else
    echo "  No financial data yet"
fi
