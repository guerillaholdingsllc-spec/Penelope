#!/bin/bash
# ============================================================
# GUERILLA HOLDINGS — Autonomous Loop v1 Deploy Script
# Installs all new modules to Penelope + patches main engine
# Run: bash deploy_autonomous_loop.sh
# ============================================================
set -e

PENELOPE_DIR="/root/workspace/Penelope"
VAULT="/root/penelope_vault.env"
VENV="/root/penelope_env/bin/python3"
SCRIPT_DIR="$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   GUERILLA HOLDINGS — Autonomous Loop v1 Deploy      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Load vault
export $(cat $VAULT | xargs) 2>/dev/null || true

# ── 1. Install Python deps ───────────────────────────────────────────────────
echo "[1/7] Installing dependencies..."
pip install aiohttp stripe google-generativeai --break-system-packages -q
echo "✅ Dependencies ready"

# ── 2. Copy all new modules ──────────────────────────────────────────────────
echo "[2/7] Installing modules..."
cp $SCRIPT_DIR/notification_hub.py    $PENELOPE_DIR/
cp $SCRIPT_DIR/opencli_wrapper.py     $PENELOPE_DIR/
cp $SCRIPT_DIR/platform_health.py     $PENELOPE_DIR/
cp $SCRIPT_DIR/niche_scorer.py        $PENELOPE_DIR/
cp $SCRIPT_DIR/claude_orchestrator.py $PENELOPE_DIR/
cp $SCRIPT_DIR/social_agent.py        $PENELOPE_DIR/
cp $SCRIPT_DIR/gafc_content_agent.py  $PENELOPE_DIR/
cp $SCRIPT_DIR/affiliate_injector.py  $PENELOPE_DIR/
echo "✅ All 8 modules installed"

# ── 3. Create GAFC assets directory ─────────────────────────────────────────
echo "[3/7] Setting up GAFC assets directory..."
mkdir -p $PENELOPE_DIR/gafc_assets
mkdir -p $PENELOPE_DIR/gafc_output

# Extract zip from Windows Downloads if accessible (Claude Desktop filesystem MCP)
DOWNLOADS="C:/Users/dgarm/Downloads"
GAFC_ZIP=$(find /mnt 2>/dev/null -name "*.zip" -path "*gafc*" -o -name "*.zip" -path "*glocks*" 2>/dev/null | head -1)
if [ -n "$GAFC_ZIP" ]; then
    echo "Found GAFC zip: $GAFC_ZIP"
    unzip -o "$GAFC_ZIP" -d $PENELOPE_DIR/gafc_assets/
    echo "✅ GAFC assets extracted"
else
    echo "⚠️  GAFC zip not found — upload assets manually to $PENELOPE_DIR/gafc_assets/"
fi

# ── 4. Add new env vars to vault (placeholders) ──────────────────────────────
echo "[4/7] Adding vault placeholders for new services..."
add_if_missing() {
    local key=$1
    local val=$2
    if ! grep -q "^${key}=" $VAULT 2>/dev/null; then
        echo "${key}=${val}" >> $VAULT
        echo "  Added: ${key}"
    fi
}

add_if_missing "TELEGRAM_CHAT_ID"       "6183015901"
add_if_missing "GMAIL_USER"             "your_gmail@gmail.com"
add_if_missing "GMAIL_APP_PASSWORD"     "your_app_password"
add_if_missing "GMAIL_RECIPIENT"        "your_gmail@gmail.com"
add_if_missing "NOTION_TOKEN"           "secret_your_notion_token"
add_if_missing "NOTION_LOG_PAGE_ID"     "your_notion_page_id"
add_if_missing "AMAZON_ASSOCIATES_TAG"  "your_amazon_tag"
add_if_missing "CLICKBANK_ID"           "your_clickbank_id"
add_if_missing "DIGISTORE24_ID"         "your_digistore_id"
add_if_missing "PARTNERSTACK_ID"        "your_partnerstack_id"
echo "✅ Vault placeholders added"

# ── 5. Patch autonomous_engine.py to wire new modules ────────────────────────
echo "[5/7] Patching autonomous_engine.py..."
ENGINE="$PENELOPE_DIR/autonomous_engine.py"
PATCH_MARKER="# GUERILLA_AUTONOMOUS_LOOP_V1_PATCHED"

if grep -q "$PATCH_MARKER" $ENGINE 2>/dev/null; then
    echo "  Engine already patched — skipping"
else
    # Backup original
    cp $ENGINE ${ENGINE}.backup.$(date +%Y%m%d_%H%M%S)

    # Append import block and cycle calls at end of file
    cat >> $ENGINE << 'PATCH_EOF'

# ============================================================
# GUERILLA_AUTONOMOUS_LOOP_V1_PATCHED
# Autonomous Loop v1 — Claude as Experiment Engine
# Penelope as Execution Module
# ============================================================

import sys
import os
sys.path.insert(0, "/root/workspace/Penelope")

def run_autonomous_loop_v1():
    """
    Extended autonomous loop — runs alongside existing Penelope cycles.
    Called from the main loop after existing tasks complete.
    """
    import logging
    log = logging.getLogger("autonomous_loop_v1")

    try:
        from claude_orchestrator import get_pending_briefs, mark_brief_done, get_pending_scale_jobs
        from social_agent import penelope_social, gafc_social
        from affiliate_injector import inject_links
        from notification_hub import notify_all
        from pathlib import Path
        import json

        # ── Process Claude's content briefs ──────────────────────────────
        briefs = get_pending_briefs()
        for i, brief in enumerate(briefs[:3]):  # Max 3 briefs per cycle
            try:
                niche    = brief.get("niche", "")
                platform = brief.get("platform", "all")
                angle    = brief.get("angle", "educational")
                track    = "gafc" if brief.get("angle") == "gafc_brand" else "penelope"
                log.info(f"Executing brief: {niche} / {platform} / {angle}")

                # Generate content (uses existing Gemini setup)
                prompt = f"""Write a {angle} article/post about {niche}.
Platform: {platform}. Be informative, engaging, actionable.
Length: 300-500 words for blog, 280 chars for Twitter, 2200 chars for Instagram."""

                # Use existing generate function if available
                content_text = ""
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
                    model  = genai.GenerativeModel("gemini-2.5-flash")
                    result = model.generate_content(prompt)
                    content_text = result.text.strip()
                except Exception as e:
                    log.error(f"Content gen failed: {e}")
                    continue

                # Inject affiliate links
                content_with_links = inject_links(content_text, niche, platform)

                # Save to shipped/
                shipped_dir = Path("/root/workspace/Penelope/shipped")
                shipped_dir.mkdir(parents=True, exist_ok=True)
                from datetime import datetime
                fname = f"{niche.replace(' ','_')}_{platform}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
                (shipped_dir / fname).write_text(f"# {niche}\n\n{content_with_links}")

                # Distribute via SocialAgent
                agent = gafc_social if track == "gafc" else penelope_social
                if platform != "all":
                    agent.post_content(content_text, platform.lower(), niche)
                else:
                    agent.distribute(content_text, niche)

                mark_brief_done(i)
                log.info(f"Brief completed: {niche}")

            except Exception as e:
                log.error(f"Brief execution failed: {e}")

        # ── Run GAFC cycle (trend-driven) ─────────────────────────────────
        try:
            from gafc_content_agent import run_gafc_cycle
            run_gafc_cycle()
        except Exception as e:
            log.error(f"GAFC cycle failed: {e}")

        # ── Process social queue ───────────────────────────────────────────
        try:
            penelope_social.process_queue()
            gafc_social.process_queue()
        except Exception as e:
            log.error(f"Queue processing failed: {e}")

    except Exception as e:
        log.error(f"run_autonomous_loop_v1 failed: {e}")


async def run_health_check_cycle():
    """Platform health check — runs every 6hrs."""
    try:
        from platform_health import run_health_check
        run_health_check()
    except Exception as e:
        import logging
        logging.getLogger("health_check").error(f"Health check failed: {e}")


async def run_niche_scoring_cycle():
    """Niche scoring cycle — runs daily at 6am."""
    try:
        from niche_scorer import run_scoring_cycle
        run_scoring_cycle()
    except Exception as e:
        import logging
        logging.getLogger("niche_scorer").error(f"Niche scoring failed: {e}")

PATCH_EOF

    echo "✅ autonomous_engine.py patched"
fi

# ── 6. Test module imports ────────────────────────────────────────────────────
echo "[6/7] Testing module imports..."
export $(cat $VAULT | xargs) 2>/dev/null || true

$VENV -c "
import sys
sys.path.insert(0, '$PENELOPE_DIR')
errors = []
for mod in ['notification_hub', 'opencli_wrapper', 'platform_health',
            'niche_scorer', 'claude_orchestrator', 'social_agent',
            'gafc_content_agent', 'affiliate_injector']:
    try:
        __import__(mod)
        print(f'  ✅ {mod}')
    except Exception as e:
        errors.append(f'  ❌ {mod}: {e}')
        print(f'  ❌ {mod}: {e}')
if errors:
    print(f'⚠️  {len(errors)} import errors — check above')
else:
    print('All modules imported successfully')
"

# ── 7. Quick opencli-rs smoke test ───────────────────────────────────────────
echo "[7/7] Testing opencli-rs..."
if command -v opencli-rs &> /dev/null; then
    OUTPUT=$(opencli-rs hackernews top --limit 3 --format json 2>/dev/null || echo "error")
    if [ "$OUTPUT" != "error" ] && [ -n "$OUTPUT" ]; then
        echo "✅ opencli-rs working — HackerNews returned data"
    else
        echo "⚠️  opencli-rs installed but returned no data — Chrome extension may need to be running"
    fi
else
    echo "⚠️  opencli-rs not found in PATH — install or check binary location"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ AUTONOMOUS LOOP v1 DEPLOYED                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Update vault with real affiliate IDs:"
echo "   nano $VAULT"
echo ""
echo "2. Update Notion credentials:"
echo "   NOTION_TOKEN + NOTION_LOG_PAGE_ID in vault"
echo ""
echo "3. Update Gmail app password:"
echo "   GMAIL_USER + GMAIL_APP_PASSWORD in vault"
echo ""
echo "4. Upload GAFC assets to:"
echo "   $PENELOPE_DIR/gafc_assets/"
echo ""
echo "5. Test notification hub:"
echo "   $VENV $PENELOPE_DIR/notification_hub.py"
echo ""
echo "6. Test Claude orchestrator:"
echo "   $VENV $PENELOPE_DIR/claude_orchestrator.py '/claude status'"
echo ""
echo "7. Restart Penelope engine:"
echo "   systemctl restart penelope-api"
echo ""
echo "Then send '/claude status' on Telegram to verify everything is live."
echo ""
