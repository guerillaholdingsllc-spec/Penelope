
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
