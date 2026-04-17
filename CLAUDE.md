# Penelope — CLAUDE.md
> Living memory file. Update this any time Claude does something wrong, a new pattern is established, or architecture changes. Every mistake becomes a rule.

---

## 🏗️ Project Overview

**Penelope** is an autonomous content publishing and affiliate marketing system owned by **Guerilla Holdings, LLC** (Sydney). It runs continuously on a DigitalOcean server, uses a multi-agent architecture, and generates revenue through SEO content + affiliate links.

---

## 🖥️ Server & Environment

| Item | Value |
|------|-------|
| Server IP | `206.81.5.241` (DigitalOcean) |
| Working dir | `/root/workspace/Penelope/` |
| Python venv | `/root/penelope_env/` |
| Vault file | `/root/penelope_vault.env` |
| Load vault | `export $(cat /root/penelope_vault.env \| xargs)` |
| Activate venv | `source /root/penelope_env/bin/activate` |

**Always load the vault before running anything. Never hardcode credentials.**

---

## 🔑 Vault Keys (in `/root/penelope_vault.env`)

- `GOOGLE_API_KEY` — Gemini access
- `TELEGRAM_BOT_TOKEN` — Telegram notifications
- `GITHUB_TOKEN` — Repo access
- `FIRECRAWL_KEY` — Web scraping
- `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY`
- `PRINTIFY_API_KEY` (GAFC merch, JWT format)
- `WAVESPEED_API_KEY` (wavespeed.ai video gen)

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `autonomous_engine.py` | Main loop — orchestrates everything |
| `agent_army.py` | Agent definitions and dispatch |
| `api.py` | External API wrappers |
| `crypto_intelligence.py` | Crypto market analysis module |
| `verify_output.py` | **[NEW]** Post-generation quality gate |

### Output Directories

| Path | Contents |
|------|----------|
| `shipped/` | Published content ready for deployment |
| `crypto_reports/` | Crypto intelligence output |
| `feed.json` | Content feed consumed by downstream systems |

---

## 🤖 AI Model

- **Primary:** `gemini-2.5-flash` via `GOOGLE_API_KEY`
- Keep temperature low (≤ 0.3) for structured tasks, higher (0.7–0.9) for creative content
- Never switch to a different model without updating this file

---

## 🔗 GitHub

- **Repo:** `guerillaholdingsllc-spec/Penelope`
- **Token:** `GITHUB_TOKEN` from vault
- Commit messages: use conventional commits (`feat:`, `fix:`, `chore:`, etc.)
- Never push directly to `main` without testing locally first

---

## 📡 Telegram

- **Chat ID:** `6183015901`
- **Bot token:** in vault as `TELEGRAM_BOT_TOKEN`
- Penelope sends status updates via Telegram — don't remove these hooks
- Signal channel pattern: one channel for summaries, one for action alerts

---

## 🏛️ Architecture Rules

1. `autonomous_engine.py` is the **only** entry point. Do not create alternate mains.
2. All agents are defined in `agent_army.py`. New agents go there, nowhere else.
3. All API calls go through `api.py` wrappers — do not call external APIs directly from the engine.
4. `verify_output.py` runs **after** generation, **before** writing to `shipped/` or `feed.json`.
5. Vault variables must be loaded before any module is imported that needs them.

---

## ✅ Verification Gate Rules (`verify_output.py`)

- Every piece of content must pass quality check before being written to `shipped/`
- Minimum quality score: **7.0 / 10**
- Failed content gets logged to `failed_verification.log`, not deleted
- Verification uses a lightweight Gemini call — keep the prompt short and scoring numeric
- Do NOT block the main loop on slow verification — run async where possible

---

## 🪝 Hooks (`.claude/hooks/`)

- `post_tool_use.sh` — runs after every file write; auto-formats Python with `black` and validates JSON files
- This hook is **private** — do not share or commit to public repos
- Hook lives at `.claude/hooks/post_tool_use.sh` relative to the workspace

---

## ❌ Known Mistakes — Never Repeat These

> Add to this list any time Claude does something wrong during development.

- [ ] *(Add mistakes here as they happen)*

---

## 🧠 Coding Style

- Python only (no Node/JS in the core engine)
- Use `async/await` for all I/O — the engine is async-first
- Type hints on all new functions
- `logging` module only — no `print()` statements in production code
- Keep functions under 50 lines; extract helpers early
- All config values from vault env vars, never hardcoded

---

## 🚫 Do Not Touch Without Asking

- `autonomous_engine.py` main loop structure
- Vault file contents or format
- `feed.json` schema (downstream systems depend on it)
- Telegram notification hooks
- Deployed `shipped/` content (it may already be indexed)

---

## 📝 Plan Mode Protocol

**Always run `/plan` before starting any new feature, fix, or integration.**

The `/plan` command runs a structured interview:
1. Claude first states everything it already knows from this file + context
2. Claude interviews Sydney across 5 rounds: Goal → Scope → Integration → Edge Cases → Verification
3. Claude produces a locked plan with file-by-file breakdown
4. Sydney approves (or modifies) before a single line of code is written
5. Claude executes in order and confirms each step

**Never skip the interview. Never write code during planning. No exceptions.**

See `.claude/commands/plan.md` for the full protocol.

---

*Last updated: manually — update this file whenever the architecture changes or a new mistake is found.*

## MEDIA PRODUCTION — CONTENT-FIRST RULE (Added 2026-04-11)
CRITICAL: Before producing ANY media asset (audio, video, trailer, narration):
1. ALWAYS scan server for existing content files: /root/workspace/Penelope/ebooks/
2. ALWAYS read actual content before writing anything
3. NEVER invent content when real files exist
4. Pipeline: Read → Narrate (ElevenLabs George) → Image (WaveSpeed) → Video (ffmpeg) → Deploy → Email review

Ebook location: /root/workspace/Penelope/ebooks/Book1-Book6/Chapter_01-24.md
Media output: /root/workspace/Penelope/media/ → copy to /var/www/html/media/
ElevenLabs voice: George (JBFqnCBsd6RMkjVDRZzb) — Warm, Captivating Storyteller


## REVENUE INTELLIGENCE FRAMEWORK (Added 2026-04-11)

### CORRECTNESS GATES — ALWAYS RUN BEFORE ACTING:
- Before narrating: Read actual file from server
- Before posting: Verify URL returns 200
- Before reporting revenue: Pull actual API data
- Before claiming success: Verify action actually happened
- Speed means nothing if the output is wrong

### MONETIZATION REFLEX — ASK ON EVERY ASSET:
1. What do we have? (inventory)
2. Who needs it? (underserved market)
3. How do we deliver it digitally? (infinite scale)
4. How do we price it? (value-based)
5. How do we distribute it? (army)

### REVENUE PATTERNS TO SCAN EACH CYCLE:
- Existing content libraries not yet in audio/video → The Chronicles model
- Local specialty services with no digital marketplace → CALLUX model
- Underserved communities needing digital tools → GAFC model
- Offline industries not yet touched by AI SaaS → white-label model
- Creative IP not yet licensed → characters, curriculum, playbooks

### THE CHRONICLES REVENUE TIERS (replicate for every IP):
- Free Chapter 1 audio → lead magnet
- $4.99 single book → Gumroad
- $24.99 full series bundle → Gumroad
- $9.99/mo audiobook subscription → future
- Merchandise (Printify) → characters/quotes
- Licensing → animation/gaming studios

### STATIC FREQUENCY: Same pipeline when ready.
Scan server for music files FIRST. Never invent content.


## REVENUE INTELLIGENCE FRAMEWORK
Full framework at: /root/workspace/Penelope/REVENUE_INTELLIGENCE_FRAMEWORK.md
Core: Gap → Digital → Monetize → Scale. Always ask: does this fill a gap people pay for? Can it scale?
Optimize for CORRECTNESS not speed. Read actual content before producing anything.
Master pattern: Content IP → Narrate → Visualize → Package → Distribute → Market → Monetize
Applies to: Books (Chronicles), Music (Static Frequency), Courses, Tools, Reports, Licensing

## QC BEFORE PUBLISH — MANDATORY (Added 2026-04-11)

Penelope MUST verify ALL of these before publishing anything or sending to Sydney:

### CONTENT QC
1. Read actual source files — never invent or assume content
2. Verify all URLs return HTTP 200 before including in any output
3. Verify all audio/video files are >0 bytes and playable
4. Run verify_output.py (Gemini score gate ≥7.0/10) on all written content
5. Check character counts match expected (audio too short = wrong content)

### LINK QC  
Before including ANY URL in emails, Telegram, Notion, or blog posts:
- HEAD request must return 200
- File size must be >10KB for media, >0 for HTML
- If URL fails — fix it FIRST, then publish
- Never send a link that returns 404, 403, or 500

### PRE-SEND CHECKLIST (Telegram/Email to Sydney)
- [ ] Is this information correct and verified?
- [ ] Are all links live and working?
- [ ] Is revenue figure pulled from live API (not estimated)?
- [ ] Is this actionable — does Sydney need to do something?
- [ ] If not — does NOT send. Logs to Notion instead.

### PUBLISHING QC
Before WordPress publish:
- Title is not blank or generic ("Untitled", "Post 1")
- Content is >200 words of real content (not placeholder)
- At least 1 internal link or affiliate link included
- No broken image URLs

Before Bluesky/Instagram post:
- Post is under character limit (300 Bluesky, 2200 IG)
- No broken links in caption
- Image URL returns 200 with content-type image/*
- Post is not a duplicate of last 3 posts

Before Gumroad product:
- Description is >200 chars
- Price is set (not $0)
- Product file or URL is attached
- At least 1 cover image

### QC ENFORCEMENT
The verify_output.py Gemini gate (≥7.0) already exists at:
/root/workspace/Penelope/verify_output.py
— USE IT on all conductor output before marking skills "Live"
— If score <7.0: regenerate, don't publish

All URL checks use:
import requests
r = requests.head(url, timeout=8, allow_redirects=True)
assert r.status_code == 200, f"URL FAILED: {url}"
