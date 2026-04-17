#!/usr/bin/env python3
"""
THE CHRONICLES — Media Production Agent
Generates trailers + audiobook samples for all 6 books.
Runs on Penelope's server.
"""
import os, json, requests, subprocess, time
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
VAULT_PATH = "/root/penelope_vault.env"

def load_vault():
    env = {}
    try:
        with open(VAULT_PATH) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except: pass
    return env

ENV = load_vault()
EL_KEY = ENV.get("ELEVENLABS_API_KEY", "sk_f3ae0d761e9b7b27ee8fff6c00731d795f2101a219fcae73")
WAVESPEED_KEY = ENV.get("WAVESPEED_API_KEY", "91a8b92b3e6661054bc7a4f84ce02f117ee5cf329a1f7c204982d40b702db11a")
GEORGE_VOICE = "JBFqnCBsd6RMkjVDRZzb"

OUTPUT_DIR = Path("/root/workspace/Penelope/media/chronicles")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Book Data ────────────────────────────────────────────────────────────────
BOOKS = [
    {
        "num": 1, "title": "The Awakening",
        "tagline": "In a dying world, one person discovers abilities that shouldn't exist.",
        "trailer_script": [
            "In a world where humanity clings to survival...",
            "Beneath a dying sun...",
            "One person awakens to something impossible.",
            "THE AWAKENING",
            "The Chronicles — Book One",
            "Available now on Gumroad."
        ],
        "narrator_hook": """In the shadow of a dying sun, where ash falls like snow and hope is rationed like water, 
Kael had learned one rule: survive. Never stand out. Never be noticed. 
But the night the lights went out across the Last City — the night something reached inside his chest 
and rewrote the rules of what was possible — surviving would no longer be enough.""",
        "image_prompt": "A lone silhouette standing in vast ash-covered ruins under a massive dying red sun, supernatural crackling energy emanating from their outstretched hands, apocalyptic atmosphere, epic cinematic lighting, dark fantasy sci-fi, 4K dramatic",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/bhkkf"
    },
    {
        "num": 2, "title": "The Fractured Worlds",
        "tagline": "The multiverse is breaking apart. The resistance is fractured. Everything escalates.",
        "trailer_script": [
            "The resistance thought they had won.",
            "They were wrong.",
            "Reality itself is fracturing.",
            "THE FRACTURED WORLDS",
            "The Chronicles — Book Two",
            "The saga continues."
        ],
        "narrator_hook": """The crack appeared in the sky on a Tuesday. 
Not a crack in the clouds — a crack in everything. A seam in the fabric of what was real, 
splitting the horizon like a broken mirror, showing something else on the other side. 
Something that shouldn't exist. Another world, identical to theirs, burning.""",
        "image_prompt": "Reality splitting apart like broken glass revealing multiple alternate dimensions, a figure at the center of fracturing space-time, cosmic horror sci-fi, blue and purple dimensional rifts, epic scale, cinematic 4K",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/phqjte"
    },
    {
        "num": 3, "title": "The Void Between",
        "tagline": "Between dimensions. Between choices. The haunting heart of The Chronicles.",
        "trailer_script": [
            "Some questions have no answer.",
            "Some doors open both ways.",
            "Between dimensions... between choices...",
            "THE VOID BETWEEN",
            "The Chronicles — Book Three",
            "Some journeys change you forever."
        ],
        "narrator_hook": """There is a place between worlds that has no name because no language has words for nothing. 
Not darkness — darkness is something. Not silence — silence is the absence of sound. 
This was the absence of absence. And Kael had been here for what felt like forever, 
and what felt like no time at all, and was beginning to understand that both were true.""",
        "image_prompt": "A solitary figure floating in infinite dark void between dimensions, ethereal impossible geometry surrounding them, haunting and philosophical atmosphere, deep space existential cosmic, teal and black color palette, cinematic 4K",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/idkwdr"
    },
    {
        "num": 4, "title": "The Architects of War",
        "tagline": "The enemy has a name. They've been moving since the beginning. The war has begun.",
        "trailer_script": [
            "Everything you've seen...",
            "Everything you've survived...",
            "Was planned.",
            "THE ARCHITECTS OF WAR",
            "The Chronicles — Book Four",
            "The truth changes everything."
        ],
        "narrator_hook": """They had a name. Three syllables spoken in boardrooms above the clouds, 
in bunkers beneath the ash, in the spaces between heartbeats where decisions are made 
that reshape centuries. The Architects. And they had been watching since the beginning. 
Since before the beginning. Since the moment they engineered it.""",
        "image_prompt": "Shadowy powerful figures in a high-tech war room above the clouds, holographic displays showing global manipulation, puppet masters in darkness, political conspiracy thriller sci-fi, dramatic chiaroscuro lighting, cinematic 4K",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/bxzkyz"
    },
    {
        "num": 5, "title": "The Last Covenant",
        "tagline": "Alliances built over four books shatter in one chapter. Tragedy is coming.",
        "trailer_script": [
            "Four books of trust.",
            "Four books of sacrifice.",
            "Shattered in a single moment.",
            "THE LAST COVENANT",
            "The Chronicles — Book Five",
            "Some betrayals you never see coming."
        ],
        "narrator_hook": """She had his back at the Battle of the Broken Gate. He had carried her through the Void. 
They had bled for each other across three worlds and a dozen impossible situations. 
Which made what happened in the war room, in front of everyone who had ever believed in them, 
so much worse. Some betrayals are accidents. This was a choice.""",
        "image_prompt": "Two former allies facing each other across a chasm in a destroyed war room, one in shadow with a weapon, the other in light with an expression of devastating betrayal, tragic dramatic cinematic sci-fi, deep emotional tension, 4K",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/cmmnjh"
    },
    {
        "num": 6, "title": "The Eternal Return",
        "tagline": "The final confrontation. Every thread resolved. The ending The Chronicles deserves.",
        "trailer_script": [
            "Every question...",
            "Every sacrifice...",
            "Every choice leads here.",
            "THE ETERNAL RETURN",
            "The Chronicles — Book Six",
            "The end of everything. The beginning of everything."
        ],
        "narrator_hook": """This is how it ends. This is how it has always ended, in every version, 
across every fracture, in every possible world that ever was or will be. 
One figure at the center of collapsing reality, holding the weight of six books 
and a thousand choices and the lives of everyone who ever believed this was worth fighting for. 
This is the moment. This is the only moment. Choose.""",
        "image_prompt": "A lone hero standing at the convergence point of collapsing reality, every thread of the story converging into blinding light, ultimate final confrontation, epic scale cosmic destruction and creation simultaneously, 4K cinematic masterpiece",
        "gumroad_url": "https://guerillaholdings.gumroad.com/l/iqydu"
    }
]

def generate_audio(text, filename, voice_id=GEORGE_VOICE):
    """Generate narration via ElevenLabs."""
    out_path = OUTPUT_DIR / filename
    if out_path.exists():
        print(f"  Audio exists: {filename}")
        return str(out_path)
    
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85,
                               "style": 0.4, "use_speaker_boost": True}
        }, timeout=60
    )
    
    if r.status_code == 200:
        out_path.write_bytes(r.content)
        print(f"  ✅ Audio: {filename} ({len(r.content)//1024}KB)")
        return str(out_path)
    else:
        print(f"  ❌ Audio failed: {r.status_code} {r.text[:100]}")
        return None

def generate_image_wavespeed(prompt, filename):
    """Generate scene image via WaveSpeed."""
    out_path = OUTPUT_DIR / filename
    if out_path.exists():
        print(f"  Image exists: {filename}")
        return str(out_path)
    
    # Submit job
    r = requests.post(
        "https://api.wavespeed.ai/api/v3/wavespeed-ai/flux-dev",
        headers={"Authorization": f"Bearer {WAVESPEED_KEY}",
                 "Content-Type": "application/json"},
        json={"prompt": prompt, "size": "1024*1792",  # Vertical for Reels/TikTok
              "num_inference_steps": 28, "guidance_scale": 3.5},
        timeout=30
    )
    
    if r.status_code not in [200, 201]:
        print(f"  ❌ Image submit failed: {r.status_code} {r.text[:100]}")
        return None
    
    job_id = r.json().get("data", {}).get("id", "")
    if not job_id:
        print(f"  ❌ No job ID returned")
        return None
    
    print(f"  Image job: {job_id[:20]}...")
    
    # Poll for result
    for i in range(30):
        time.sleep(4)
        r2 = requests.get(
            f"https://api.wavespeed.ai/api/v3/predictions/{job_id}/result",
            headers={"Authorization": f"Bearer {WAVESPEED_KEY}"},
            timeout=15
        )
        if r2.status_code == 200:
            result = r2.json().get("data", {})
            status = result.get("status", "")
            if status == "completed":
                outputs = result.get("outputs", [])
                if outputs:
                    img_url = outputs[0]
                    img_r = requests.get(img_url, timeout=30)
                    if img_r.status_code == 200:
                        out_path.write_bytes(img_r.content)
                        print(f"  ✅ Image: {filename} ({len(img_r.content)//1024}KB)")
                        return str(out_path)
            elif status == "failed":
                print(f"  ❌ Image generation failed")
                return None
    
    print(f"  ❌ Image timed out")
    return None

def create_video_trailer(book, audio_path, image_path):
    """Assemble trailer video using ffmpeg."""
    out_path = OUTPUT_DIR / f"book{book['num']}_trailer.mp4"
    if out_path.exists():
        print(f"  Video exists: {out_path.name}")
        return str(out_path)
    
    if not image_path or not audio_path:
        print(f"  ❌ Missing assets for video")
        return None
    
    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip() or "30")
    
    # Create text overlay filter for trailer script lines
    lines = book["trailer_script"]
    segment_duration = duration / len(lines)
    
    drawtext_filters = []
    for i, line in enumerate(lines):
        start = i * segment_duration + 0.5
        end = (i + 1) * segment_duration - 0.3
        # Different style for title vs other lines
        is_title = book["title"].upper() in line.upper() or "Book" in line
        fontsize = 72 if is_title else 48
        color = "white" if not is_title else "FFD700"  # Gold for title
        
        drawtext_filters.append(
            f"drawtext=text='{line.replace("'", "")}'"
            f":fontsize={fontsize}:fontcolor={color}@0.9"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
            f":enable='between(t,{start:.1f},{end:.1f})'"
            f":shadowcolor=black:shadowx=3:shadowy=3"
        )
    
    vf = ",".join(drawtext_filters)
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{vf}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(out_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  ✅ Video: {out_path.name} ({size_mb:.1f}MB)")
        return str(out_path)
    else:
        print(f"  ❌ ffmpeg error: {result.stderr[-200:]}")
        return None

def generate_rss_feed():
    """Generate podcast RSS feed for audiobook distribution."""
    rss_path = OUTPUT_DIR / "podcast_feed.xml"
    
    items = ""
    for book in BOOKS:
        audio_file = OUTPUT_DIR / f"book{book['num']}_hook.mp3"
        if audio_file.exists():
            size = audio_file.stat().st_size
            items += f"""
    <item>
      <title>The Chronicles Book {book['num']}: {book['title']} — Chapter 1 Preview</title>
      <description>{book['tagline']} Get the full book at {book['gumroad_url']}</description>
      <enclosure url="https://trustchainservices.com/media/chronicles/book{book['num']}_hook.mp3" 
                 length="{size}" type="audio/mpeg"/>
      <guid>chronicles-book{book['num']}-preview</guid>
      <pubDate>{datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
      <itunes:duration>60</itunes:duration>
      <itunes:episode>{book['num']}</itunes:episode>
    </item>"""
    
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>The Chronicles — by Guerilla Holdings</title>
    <description>A gripping sci-fi fantasy epic. Humanity's remnants survive beneath a dying sun. 
One person discovers abilities that shouldn't exist. Six books. One unforgettable saga.</description>
    <link>https://guerillaholdings.gumroad.com</link>
    <language>en-us</language>
    <itunes:author>Guerilla Holdings</itunes:author>
    <itunes:category text="Fiction"/>
    <itunes:explicit>no</itunes:explicit>
    <itunes:image href="https://trustchainservices.com/media/chronicles/series_cover.jpg"/>
    {items}
  </channel>
</rss>"""
    
    rss_path.write_text(rss)
    print(f"✅ RSS Feed: {rss_path}")
    return str(rss_path)

# ── MAIN PRODUCTION RUN ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"THE CHRONICLES — MEDIA PRODUCTION AGENT")
    print(f"{'='*60}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"ElevenLabs: {EL_KEY[:20]}...")
    print(f"Voice: George (JBFqnCBsd6RMkjVDRZzb) — Warm, Captivating Storyteller")
    print(f"\nProducing assets for {len(BOOKS)} books...\n")
    
    produced = []
    
    for book in BOOKS:
        print(f"\n📖 BOOK {book['num']}: {book['title'].upper()}")
        print(f"   {book['tagline']}")
        
        # 1. Generate hook narration (Chapter 1 opening ~60 sec)
        print(f"  🎙️ Generating narrator hook...")
        audio_hook = generate_audio(
            book["narrator_hook"],
            f"book{book['num']}_hook.mp3"
        )
        
        # 2. Generate trailer narration (shorter, punchy)
        trailer_narration = f"{book['tagline']} {book['title']}. The Chronicles, Book {book['num']}. Available now."
        print(f"  🎙️ Generating trailer narration...")
        audio_trailer = generate_audio(
            trailer_narration,
            f"book{book['num']}_trailer_narration.mp3"
        )
        
        # 3. Generate scene image
        print(f"  🎨 Generating scene image...")
        scene_image = generate_image_wavespeed(
            book["image_prompt"],
            f"book{book['num']}_scene.jpg"
        )
        
        # 4. Assemble video trailer
        if scene_image and audio_trailer:
            print(f"  🎬 Assembling video trailer...")
            video = create_video_trailer(book, audio_trailer, scene_image)
        else:
            video = None
            print(f"  ⚠️  Skipping video — missing assets")
        
        produced.append({
            "book": book["num"],
            "title": book["title"],
            "hook_audio": audio_hook,
            "trailer_audio": audio_trailer,
            "scene_image": scene_image,
            "video": video
        })
        
        time.sleep(2)  # Rate limit respect
    
    # 5. Generate RSS feed
    print(f"\n📡 Generating podcast RSS feed...")
    rss = generate_rss_feed()
    
    # 6. Summary
    print(f"\n{'='*60}")
    print(f"PRODUCTION COMPLETE")
    print(f"{'='*60}")
    for p in produced:
        print(f"\nBook {p['book']}: {p['title']}")
        print(f"  Hook audio:    {'✅' if p['hook_audio'] else '❌'}")
        print(f"  Trailer audio: {'✅' if p['trailer_audio'] else '❌'}")
        print(f"  Scene image:   {'✅' if p['scene_image'] else '❌'}")
        print(f"  Video trailer: {'✅' if p['video'] else '❌'}")
    
    print(f"\n📁 All assets: {OUTPUT_DIR}")
    print(f"📡 RSS Feed: {rss}")
    print(f"\nNext steps:")
    print(f"  1. Upload videos to TikTok, IG Reels, YouTube Shorts")
    print(f"  2. Submit RSS feed to Spotify, Apple Podcasts")
    print(f"  3. Upload hook audio to SoundCloud as free previews")
