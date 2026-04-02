# /plan — Penelope Feature Planning Interview

> Invoke with: `/plan` before starting any new feature, module, or significant change.
> Claude interviews Sydney first, then produces a locked plan. No code is written until approval.

---

## Step 1 — Claude Declares What It Already Knows

Before asking anything, Claude must open by stating everything it already knows about the project context from CLAUDE.md and prior conversation. Format:

```
📋 Here's what I already know about this project:

SYSTEM:
- [list key architecture facts relevant to this feature]
- [list any related existing files/modules]
- [list any constraints already documented]

GAPS I need to fill before planning:
- [numbered list of unknowns]
```

This prevents asking questions that are already answered and shows Sydney exactly what context Claude is working from.

---

## Step 2 — The Interview

Claude asks questions in this exact order, **one category at a time**, waiting for answers before moving to the next. Never dump all questions at once.

### Round 1 — The Goal
Ask:
1. What problem does this solve, or what outcome do you want?
2. Is this a new feature, a fix, a refactor, or an integration?
3. What does "done" look like to you — what's the simplest version that works?

### Round 2 — Scope & Boundaries
Ask (after Round 1 answers):
1. What files or modules will this touch? What should it absolutely NOT touch?
2. Are there any existing behaviors that must stay exactly the same?
3. Is there a deadline or "good enough for now" threshold?

### Round 3 — Integration & Dependencies
Ask (after Round 2 answers):
1. Does this need to talk to any external APIs, the vault, Telegram, or GitHub?
2. Does it plug into the main loop, run standalone, or get called by an agent?
3. Any new credentials or environment variables needed?

### Round 4 — Edge Cases & Failure Modes
Ask (after Round 3 answers):
1. What should happen if this fails — silent log, Telegram alert, or stop the engine?
2. Any rate limits, quotas, or cost concerns I should know about?
3. Is there anything you've tried before that didn't work?

### Round 5 — Verification
Ask (after Round 4 answers):
1. How will we know it's working correctly?
2. Can I verify it automatically (run a test, check a file, hit an endpoint)?
3. Is there a staging/test mode or does it go straight to production?

---

## Step 3 — Plan Output

After all rounds are complete, Claude produces a structured plan in this exact format:

```
## 📝 PLAN — [Feature Name]
**Status: DRAFT — awaiting approval**

### Goal
[One paragraph summary of what we're building and why]

### Files Changing
| File | Change Type | Notes |
|------|-------------|-------|
| file.py | modify | reason |
| new_file.py | create | reason |

### Files NOT Touching
- [explicit list of files that must not change]

### Implementation Steps
1. [step] — [which file] — [what specifically changes]
2. ...

### Verification Strategy
- [ ] [how we confirm it works]
- [ ] [automated check if applicable]

### Failure Handling
- [what happens on error]
- [where it gets logged]
- [any alerts]

### Open Questions
- [anything still unclear that Sydney needs to decide]

---
✋ WAITING FOR APPROVAL
Reply "approved" or "approved with changes: [changes]" to begin execution.
No code will be written until this plan is approved.
```

---

## Step 4 — Execution

Only after Sydney types **"approved"** (or approved with modifications):
- Switch to auto-accept edits mode
- Execute steps in order
- After each file change, note completion: `✅ Step N done`
- Run verification at the end
- Report result to Sydney

---

## Rules

- **Never write code during the interview** — planning only
- **Never skip rounds** — all 5 rounds must complete before the plan
- **Always number open questions** — don't leave ambiguity buried in prose
- **If a question is already answered by CLAUDE.md**, skip it and note why
- **If Sydney says "just do it"**, acknowledge but still produce a 1-paragraph mini-plan and ask for a quick confirm before proceeding
