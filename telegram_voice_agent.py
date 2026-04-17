#!/usr/bin/env python3
"""Penelope Telegram Voice Agent - receives voice notes, transcribes via Gemini, routes to Penelope"""
import os, sys, logging, subprocess, tempfile, json, requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Load vault
vault = {}
vault_path = "/root/penelope_vault.env"
if os.path.exists(vault_path):
    for line in open(vault_path):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vault[k.strip()] = v.strip()

TELEGRAM_TOKEN = vault.get("TELEGRAM_BOT_TOKEN", "8671512106:AAGTFoK5W_60gruZvo3Qh_SElRijTB9FF1k")
GOOGLE_API_KEY = vault.get("GOOGLE_API_KEY", "")
PENELOPE_URL = "http://127.0.0.1:5000/ask"
ALLOWED_CHAT_IDS = {int(vault.get("TELEGRAM_CHAT_ID", "6183015901"))}

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  json={"chat_id": chat_id, "text": text[:4096]}, timeout=10)

def download_file(file_id):
    r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
                     params={"file_id": file_id}, timeout=10).json()
    file_path = r["result"]["file_path"]
    content = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}", timeout=30).content
    return content

def transcribe_audio(audio_bytes, mime="audio/ogg"):
    """Transcribe audio using Gemini"""
    import base64
    b64 = base64.b64encode(audio_bytes).decode()
    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": b64}},
            {"text": "Transcribe this audio exactly. Return only the transcription text, nothing else."}
        ]}]
    }
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}",
        json=payload, timeout=30
    )
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    log.error(f"Gemini transcription failed: {r.text[:200]}")
    return None

def ask_penelope(text):
    try:
        r = requests.post(PENELOPE_URL, json={"message": text, "secret": "sydney123"}, timeout=30)
        return r.json().get("response", "")
    except Exception as e:
        return f"Penelope unavailable: {e}"

def poll():
    offset = 0
    log.info("Telegram voice agent started, polling...")
    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=40
            ).json()
            for update in r.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                if chat_id not in ALLOWED_CHAT_IDS:
                    continue
                # Handle voice messages
                if "voice" in msg:
                    send_message(chat_id, "🎙️ Transcribing...")
                    audio = download_file(msg["voice"]["file_id"])
                    text = transcribe_audio(audio, "audio/ogg")
                    if text:
                        send_message(chat_id, f"📝 *You said:* {text}")
                        response = ask_penelope(text)
                        if response:
                            send_message(chat_id, f"🤖 {response}")
                    else:
                        send_message(chat_id, "❌ Could not transcribe audio.")
                # Handle text as fallback
                elif "text" in msg:
                    text = msg["text"]
                    if text.startswith("/"):
                        if text == "/status":
                            send_message(chat_id, "✅ Voice agent active")
                        continue
        except Exception as e:
            log.error(f"Poll error: {e}")
            import time; time.sleep(5)

if __name__ == "__main__":
    poll()

