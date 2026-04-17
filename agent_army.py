import os, json, time, requests, base64, datetime, threading, random
from google import genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
REPO = "guerillaholdingsllc-spec/Penelope"
FEED_FILE = "/root/workspace/Penelope/feed.json"
BLOG_DIR = "/root/workspace/Penelope/blog/posts"
EBOOK_DIR = "/root/workspace/Penelope/ebooks"
os.makedirs(BLOG_DIR, exist_ok=True)
os.makedirs(EBOOK_DIR, exist_ok=True)
client = genai.Client(api_key=GOOGLE_API_KEY)

def log(agent, msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}][{agent}] {msg}", flush=True)

def post_to_feed(title, content, status="success", agent="Penelope"):
    try:
        feed = []
        if os.path.exists(FEED_FILE):
            feed = json.loads(open(FEED_FILE).read())
        feed.insert(0, {"id": int(time.time()*1000)+random.randint(1,999), "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "title": f"[{agent}] {title}", "content": content, "status": status})
        feed = feed[:200]
        open(FEED_FILE, "w").write(json.dumps(feed))
    except Exception as e:
        print(f"Feed error: {e}")

def gemini(prompt, agent="agent"):
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return getattr(response, "text", None) or "No output."
    except Exception as e:
        log(agent, f"Gemini error: {e}")
        return f"Error: {e}"

def save_blog_post(title, content, agent):
    fname = f"{BLOG_DIR}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent.replace(' ','_')}.json"
    open(fname, "w").write(json.dumps({"title": title, "content": content, "agent": agent, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}))

def fetch_github_docs():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    docs = []
    try:
        res = requests.get(f"https://api.github.com/repos/{REPO}/contents/", headers=headers)
        for f in res.json():
            if f["name"].endswith(".docx") or f["name"].endswith(".md"):
                cr = requests.get(f["url"], headers=headers).json()
                if "content" in cr:
                    try:
                        decoded = base64.b64decode(cr["content"]).decode("utf-8", errors="ignore")
                        docs.append(f"=== {f['name']} ===\n{decoded[:2000]}")
                    except Exception:
                        pass
    except Exception:
        pass
    return "\n\n".join(docs)

BLOG_NICHES = [
    ("Tech and AI", "artificial intelligence, automation, future of work"),
    ("Personal Finance", "passive income, investing, financial freedom"),
    ("Sci-Fi Culture", "science fiction books, movies, world building"),
    ("Small Business", "entrepreneurship, startups, business automation"),
    ("Future Tech", "space travel, robotics, quantum computing"),
    ("Digital Nomad", "remote work, location independence, online income"),
    ("Self Development", "productivity, mindset, high performance"),
    ("Crypto and Web3", "blockchain, decentralized finance, digital assets"),
]

def blog_writer_agent(niche_name, keywords, agent_id):
    agent = f"BlogAgent-{agent_id}"
    log(agent, f"Starting: {niche_name}")
    while True:
        try:
            result = gemini(f"Write a complete 1200-word SEO blog article for niche: {niche_name}. Keywords: {keywords}. Include H1, meta description, intro, 4 H2s, conclusion with CTA, and 3 affiliate product recommendations.", agent)
            title = result.split('\n')[0].replace('#','').strip()[:80]
            save_blog_post(title, result, agent)
            post_to_feed(f"Blog: {title}", result, "success", agent)
            log(agent, f"Published: {title}")
            time.sleep(3600)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

AFFILIATE_NICHES = [
    ("AI Tools", "best AI writing tools, ChatGPT alternatives"),
    ("Sci-Fi Books", "best science fiction books, space opera novels"),
    ("Online Business Tools", "best email marketing, automation tools"),
    ("Passive Income", "best dividend stocks, passive income apps"),
    ("Gaming and Tech", "best gaming laptops, VR headsets"),
    ("Home Office", "best standing desks, monitors, ergonomic chairs"),
]

def affiliate_agent(niche_name, keywords, agent_id):
    agent = f"AffiliateAgent-{agent_id}"
    log(agent, f"Starting: {niche_name}")
    while True:
        try:
            result = gemini(f"Write a complete affiliate review article for: {niche_name}. Keywords: {keywords}. Include title, meta description, top 5 products with pros/cons/pricing, comparison table, buying guide, FAQ, conclusion. List affiliate programs for each.", agent)
            save_blog_post(f"Affiliate Review: {niche_name}", result, agent)
            post_to_feed(f"Affiliate Review: {niche_name}", result, "success", agent)
            log(agent, f"Published: {niche_name}")
            time.sleep(4200)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

BOOK_STRUCTURES = {
    1: ("The Awakening", "Hero discovers abilities in dystopian sci-fi world. Dark hopeful tone."),
    2: ("The Fractured Worlds", "Hero joins resistance as multiverse breaks apart. Action mystery."),
    3: ("The Void Between", "Journey through collapsed dimensions. Tense philosophical."),
    4: ("The Architects of War", "Enemy revealed, cosmic war. Epic political."),
    5: ("The Last Covenant", "Alliances shatter, hero chooses between worlds. Tragic urgent."),
    6: ("The Eternal Return", "Final confrontation, resolution. Triumphant bittersweet."),
}

def ebook_agent(book_num, github_docs):
    agent = f"EbookAgent-Book{book_num}"
    title, description = BOOK_STRUCTURES[book_num]
    log(agent, f"Starting: {title}")
    chapters_written = []
    while True:
        try:
            chapter_num = len(chapters_written) + 1
            if chapter_num > 24:
                post_to_feed(f"BOOK {book_num} COMPLETE: {title}", f"All 24 chapters written. Upload to kdp.amazon.com from /root/workspace/Penelope/ebooks/Book{book_num}/", "success", agent)
                time.sleep(86400)
                chapters_written = []
                continue
            prev = chapters_written[-1][:500] if chapters_written else "This is the first chapter."
            result = gemini(f"Write Chapter {chapter_num} of 24 for sci-fi fantasy book '{title}'. Description: {description}. Previous ending: {prev}. Requirements: 2500 words, vivid world-building, strong dialogue, professional quality. Start with 'Chapter {chapter_num}: [Title]'. End with a hook.", agent)
            chapters_written.append(result)
            chapter_dir = f"{EBOOK_DIR}/Book{book_num}"
            os.makedirs(chapter_dir, exist_ok=True)
            open(f"{chapter_dir}/Chapter_{chapter_num:02d}.md", "w").write(result)
            post_to_feed(f"Book {book_num} Ch.{chapter_num}", result[:600]+"...", "success", agent)
            log(agent, f"Wrote Chapter {chapter_num}")
            time.sleep(1800)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

SEO_TARGETS = [
    ("Sci-Fi and Fantasy", ["best sci fi books", "fantasy series 2024"]),
    ("AI and Automation", ["best ai tools 2024", "automate my business"]),
    ("Online Business", ["make money online 2024", "passive income ideas"]),
]

def seo_agent(niche, seeds, agent_id):
    agent = f"SEOAgent-{agent_id}"
    while True:
        try:
            result = gemini(f"Create complete SEO strategy for: {niche}. Seeds: {', '.join(seeds)}. Include top 20 keywords with difficulty/intent, top 10 article ideas, 30-day calendar, affiliate programs, 3 quick wins.", agent)
            post_to_feed(f"SEO Strategy: {niche}", result, "success", agent)
            time.sleep(7200)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

def publishing_agent(agent_id):
    agent = f"PublishingAgent-{agent_id}"
    while True:
        try:
            import glob
            posts = glob.glob(f"{BLOG_DIR}/*.json")
            ebooks = glob.glob(f"{EBOOK_DIR}/**/*.md", recursive=True)
            post_to_feed("Publishing Status", f"Blog posts: {len(posts)}\nEbook chapters: {len(ebooks)}\n\nNext steps:\n1. Upload ebooks to kdp.amazon.com\n2. Apply for Google AdSense\n3. Join Amazon Associates\n4. Join ShareASale", "info", agent)
            time.sleep(10800)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

def main():
    print("LAUNCHING PENELOPE 25-AGENT ARMY")
    post_to_feed("25-Agent Army Online", "All 25 agents launching:\n8 Blog Writers\n6 Affiliate Agents\n6 Ebook Writers\n3 SEO Agents\n2 Publishing Agents\n\nRunning 24/7.", "success", "Commander")
    github_docs = fetch_github_docs()
    threads = []
    for i, (niche, kw) in enumerate(BLOG_NICHES):
        t = threading.Thread(target=blog_writer_agent, args=(niche, kw, i+1), daemon=True)
        t.start(); threads.append(t); time.sleep(3)
    for i, (niche, kw) in enumerate(AFFILIATE_NICHES):
        t = threading.Thread(target=affiliate_agent, args=(niche, kw, i+1), daemon=True)
        t.start(); threads.append(t); time.sleep(3)
    for book_num in range(1, 7):
        t = threading.Thread(target=ebook_agent, args=(book_num, github_docs), daemon=True)
        t.start(); threads.append(t); time.sleep(3)
    for i, (niche, seeds) in enumerate(SEO_TARGETS):
        t = threading.Thread(target=seo_agent, args=(niche, seeds, i+1), daemon=True)
        t.start(); threads.append(t); time.sleep(3)
    for i in range(2):
        t = threading.Thread(target=publishing_agent, args=(i+1,), daemon=True)
        t.start(); threads.append(t); time.sleep(3)
    print(f"All {len(threads)} agents launched!")
    while True:
        alive = sum(1 for t in threads if t.is_alive())
        print(f"[{datetime.datetime.now().strftime('%H:%M')}] {alive}/25 agents running", flush=True)
        time.sleep(300)

if __name__ == "__main__":
    main()

def screenplay_agent():
    agent = "ScreenplayAgent"
    log(agent, "Starting — converting book chapters to video prompts")
    while True:
        try:
            import glob
            chapters = glob.glob(f"{EBOOK_DIR}/**/*.md", recursive=True)
            if not chapters:
                log(agent, "No chapters yet, waiting...")
                time.sleep(1800)
                continue
            chapter_file = random.choice(chapters)
            chapter_text = open(chapter_file).read()[:2000]
            book_num = chapter_file.split('Book')[1][0]
            chapter_num = chapter_file.split('Chapter_')[1][:2]
            prompt = gemini(f"""You are a cinematic director creating a TikTok/Reels trailer for a sci-fi fantasy book.

Read this chapter excerpt and create 3 SHORT VIDEO SCENE PROMPTS optimized for AI video generation.

CHAPTER:
{chapter_text}

For each scene write:
SCENE [N]: [10-second cinematic shot description, very specific visual details, camera angle, lighting, mood]
STYLE: cinematic, dark sci-fi fantasy, dramatic lighting, photorealistic
DURATION: 8 seconds

Write 3 scenes that would make an epic 30-second TikTok trailer. Be extremely specific about visuals.""", agent)

            save_dir = f"{EBOOK_DIR}/trailers"
            os.makedirs(save_dir, exist_ok=True)
            fname = f"{save_dir}/Book{book_num}_Ch{chapter_num}_prompts.txt"
            open(fname, "w").write(prompt)
            post_to_feed(f"Screenplay: Book {book_num} Ch.{chapter_num} trailer prompts", prompt, "success", agent)
            log(agent, f"Wrote trailer prompts for Book {book_num} Ch.{chapter_num}")
            time.sleep(3600)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(300)

def video_agent():
    import replicate as rep
    agent = "VideoAgent"
    log(agent, "Starting — generating video clips from screenplay prompts")
    while True:
        try:
            import glob
            prompt_files = glob.glob(f"{EBOOK_DIR}/trailers/*.txt")
            if not prompt_files:
                log(agent, "No screenplay prompts yet, waiting...")
                time.sleep(1800)
                continue
            prompt_file = random.choice(prompt_files)
            content = open(prompt_file).read()
            scenes = [l.replace('SCENE 1:','').replace('SCENE 2:','').replace('SCENE 3:','').strip()
                     for l in content.split('\n') if l.strip().startswith('SCENE')]
            if not scenes:
                time.sleep(1800)
                continue
            scene_prompt = scenes[0][:500]
            log(agent, f"Generating video: {scene_prompt[:80]}...")
            output = rep.run(
                "wan-video/wan-2.2-t2v-fast",
                input={
                    "prompt": f"cinematic sci-fi fantasy, {scene_prompt}, dramatic lighting, photorealistic",
                    "num_frames": 49,
                    "resolution": "480p",
                }
            )
            video_url = str(output)
            save_dir = f"{EBOOK_DIR}/trailers/videos"
            os.makedirs(save_dir, exist_ok=True)
            fname = f"{save_dir}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            import urllib.request
            urllib.request.urlretrieve(video_url, fname)
            post_to_feed(
                f"VIDEO CLIP GENERATED",
                f"Clip saved to: {fname}\nPrompt: {scene_prompt[:200]}\n\nSYDNEY ACTION: Download from droplet and post to TikTok/Reels immediately!",
                "success", agent
            )
            log(agent, f"Video saved: {fname}")
            time.sleep(3600)
        except Exception as e:
            log(agent, f"Error: {e}")
            time.sleep(600)
