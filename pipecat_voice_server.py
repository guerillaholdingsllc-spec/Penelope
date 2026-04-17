#!/usr/bin/env python3
"""Penelope Pipecat Voice Server - WebSocket full-duplex voice interface"""
import os, asyncio, json, logging, base64, requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

vault = {}
for line in open("/root/penelope_vault.env"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        vault[k.strip()] = v.strip()

GOOGLE_API_KEY = vault.get("GOOGLE_API_KEY","")
ELEVENLABS_KEY = vault.get("ELEVENLABS_API_KEY","")
ELEVENLABS_VOICE = vault.get("ELEVENLABS_VOICE_ID","EXAVITQu4vr4xnSDxMaL")
PENELOPE_URL = "http://127.0.0.1:5000/ask"
PORT = 8765

SYSTEM_PROMPT = """You are Penelope, Sydney's autonomous AI revenue engine for Guerilla Holdings LLC.
You have full knowledge of all active systems: trading engine, ebook agents, buffer social drip,
Vessel Protocol marketing, TrustChain Services, GAFC grant pipeline, and all Penelope infrastructure.
Be direct, confident, and action-oriented. Report revenue, status, and decisions concisely."""

async def transcribe_audio(audio_b64):
    """Transcribe audio using Gemini"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents":[{"parts":[
        {"inline_data":{"mime_type":"audio/webm","data":audio_b64}},
        {"text":"Transcribe this audio exactly. Return only the transcription, nothing else."}
    ]}]}
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code == 200:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return ""

async def get_penelope_response(text):
    """Get response from Penelope"""
    try:
        r = requests.post(PENELOPE_URL, json={"message":text,"secret":"sydney123"}, timeout=30)
        return r.json().get("response","")
    except:
        # Fallback to Gemini directly
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
        payload = {"system_instruction":{"parts":[{"text":SYSTEM_PROMPT}]},
                   "contents":[{"parts":[{"text":text}]}]}
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return "I encountered an error. Please try again."

async def tts(text):
    """Text to speech via ElevenLabs or Google TTS fallback"""
    if ELEVENLABS_KEY:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}"
        headers = {"xi-api-key":ELEVENLABS_KEY,"Content-Type":"application/json"}
        payload = {"text":text[:1000],"model_id":"eleven_turbo_v2","voice_settings":{"stability":0.5,"similarity_boost":0.75}}
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    return None

try:
    import websockets

    async def handle_client(websocket):
        log.info(f"Client connected: {websocket.remote_address}")
        await websocket.send(json.dumps({"type":"connected","message":"Penelope voice interface ready"}))
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type","")

                if msg_type == "audio":
                    audio_b64 = data.get("audio","")
                    transcript = await transcribe_audio(audio_b64)
                    if transcript:
                        await websocket.send(json.dumps({"type":"transcript","text":transcript}))
                        response = await get_penelope_response(transcript)
                        await websocket.send(json.dumps({"type":"response","text":response}))
                        audio = await tts(response)
                        if audio:
                            await websocket.send(json.dumps({"type":"audio","audio":audio}))

                elif msg_type == "text":
                    text = data.get("text","")
                    response = await get_penelope_response(text)
                    await websocket.send(json.dumps({"type":"response","text":response}))
                    audio = await tts(response)
                    if audio:
                        await websocket.send(json.dumps({"type":"audio","audio":audio}))

                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type":"pong"}))

            except Exception as e:
                log.error(f"Handler error: {e}")

    async def main():
        log.info(f"Pipecat voice server starting on port {PORT}")
        async with websockets.serve(handle_client, "0.0.0.0", PORT):
            await asyncio.Future()

    asyncio.run(main())

except ImportError:
    log.error("websockets not installed. Installing...")
    import subprocess
    subprocess.run(["/root/penelope_env/bin/pip","install","websockets","-q"])
    log.info("Installed websockets. Restarting...")
    os.execv("/root/penelope_env/bin/python3", ["/root/penelope_env/bin/python3"] + [__file__])

