#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# .claude/hooks/post_tool_use.sh
# Penelope — Private PostToolUse Hook
#
# Runs automatically after Claude writes or edits a file.
# Fixes the last 10% of formatting issues so CI never fails
# and JSON writes are always valid before they hit feed.json.
#
# DO NOT COMMIT OR SHARE — personal workflow only.
# Place at: /root/workspace/Penelope/.claude/hooks/post_tool_use.sh
# Make executable: chmod +x .claude/hooks/post_tool_use.sh
# ─────────────────────────────────────────────────────────────

set -euo pipefail

# ── Parse Claude Code hook input from stdin ───────────────────
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('tool_input',{}); print(p.get('path', p.get('file_path','')))" 2>/dev/null || echo "")

# Only act on file-write tools
if [[ "$TOOL_NAME" != "write_file" && "$TOOL_NAME" != "str_replace_editor" && "$TOOL_NAME" != "create_file" ]]; then
    exit 0
fi

if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
    exit 0
fi

EXTENSION="${FILE_PATH##*.}"

# ── Python: auto-format with black ───────────────────────────
if [[ "$EXTENSION" == "py" ]]; then
    if command -v black &>/dev/null; then
        black --quiet "$FILE_PATH" 2>/dev/null && echo "[hook] black formatted: $FILE_PATH"
    elif command -v autopep8 &>/dev/null; then
        autopep8 --in-place "$FILE_PATH" 2>/dev/null && echo "[hook] autopep8 formatted: $FILE_PATH"
    fi

    # Check for syntax errors
    python3 -m py_compile "$FILE_PATH" 2>/dev/null \
        && echo "[hook] syntax OK: $FILE_PATH" \
        || echo "[hook] ⚠️  SYNTAX ERROR in $FILE_PATH — fix before running"
fi

# ── JSON: validate before it can corrupt feed.json ───────────
if [[ "$EXTENSION" == "json" ]]; then
    if python3 -m json.tool "$FILE_PATH" > /dev/null 2>&1; then
        echo "[hook] JSON valid: $FILE_PATH"
    else
        echo "[hook] ⚠️  INVALID JSON in $FILE_PATH — engine will reject this"
        # Don't exit 1 — let Claude know but don't block
    fi
fi

# ── Shell scripts: check syntax ───────────────────────────────
if [[ "$EXTENSION" == "sh" ]]; then
    bash -n "$FILE_PATH" 2>/dev/null \
        && echo "[hook] shell syntax OK: $FILE_PATH" \
        || echo "[hook] ⚠️  SHELL SYNTAX ERROR in $FILE_PATH"
fi

exit 0
