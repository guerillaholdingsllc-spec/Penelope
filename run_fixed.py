import requests
from google import genai

# === YOUR CURRENT KEYS (TEMP) ===
TELEGRAM_BOT_TOKEN = "8671512106:AAEjGbSqf79q5vm9jnjVbQtcdEkDDEF6A30"
TELEGRAM_CHAT_ID = "6183015901"
GOOGLE_API_KEY = "AIzaSyBLQ6syk7q-bV21Naxwr6Mx_hPe-ehkYJM"

MODEL_NAME = "gemini-2.5-flash"

client = genai.Client(api_key=GOOGLE_API_KEY)


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


def main():
    prompt = "Give me 3 ClickBank niches, 3 offer angles, and 3 traffic ideas."

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = response.text if response.text else "No response"
    print(text)

    _tg_emergency_only(text)

if __name__ == "__main__":
    main()
