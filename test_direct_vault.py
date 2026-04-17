from pathlib import Path
import requests
from google import genai

VAULT = "/root/penelope_vault.env"

def read_env_file(path):
    data = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data

env = read_env_file(VAULT)

telegram_token = env.get("TELEGRAM_BOT_TOKEN", "")
telegram_chat_id = env.get("TELEGRAM_CHAT_ID", "6183015901")
google_api_key = env.get("GOOGLE_API_KEY", "")

print("TOKEN FOUND:", bool(telegram_token), "LEN:", len(telegram_token))
print("CHAT ID:", telegram_chat_id)
print("GOOGLE KEY FOUND:", bool(google_api_key), "LEN:", len(google_api_key))

print("\n--- TELEGRAM TEST ---")
tg = requests.get(f"https://api.telegram.org/bot{telegram_token}/getMe", timeout=30)
print(tg.status_code, tg.text[:500])

print("\n--- GEMINI TEST ---")
try:
    client = genai.Client(api_key=google_api_key)
    r = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Reply with only: OK"
    )
    print("GEMINI OK:", repr(getattr(r, "text", None)))
except Exception as e:
    print("GEMINI ERROR:", e)
