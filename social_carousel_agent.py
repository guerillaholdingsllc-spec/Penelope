import os,json,random
from datetime import datetime
from flask import Flask,jsonify,request
from google import genai
app=Flask(__name__)

def _carousel_ai(prompt):
    try:
        _env = {}
        [_env.update({l.split("=",1)[0].strip(): l.split("=",1)[1].strip()})
         for l in open("/root/penelope_vault.env") if "=" in l and not l.startswith("#")]
        import os; os.environ.setdefault("GOOGLE_API_KEY", _env.get("GOOGLE_API_KEY",""))
        from google import genai as _g
        return _g.Client(api_key=_env.get("GOOGLE_API_KEY","")).models.generate_content(
            model="gemini-2.5-flash", contents=str(prompt)).text
    except Exception as e:
        return f"[Error: {e}]"

# genai client initialized lazily in generate()
TOPICS=["AI automation for small business","How to start a transport business","Passive income with AI agents","Funeral home modernization","Gig economy driver tips","DEVVE crypto investing"]
@app.route("/health")
def health():return jsonify({"status":"ok","port":9003})
@app.route("/carousel/generate",methods=["POST"])
def generate():
 data=request.json or {}
 topic=data.get("topic",random.choice(TOPICS))
 level=int(data.get("level",1))
 slides=5+level*2
 r=__import__("os").environ.update({k:v for k,v in [l.strip().split("=",1) for l in open("/root/penelope_vault.env") if "=" in l and not l.startswith("#")]}) or __import__("google.genai", fromlist=["genai"]).genai.Client(api_key=__import__("os").getenv("GOOGLE_API_KEY","")).models.generate_content(model="gemini-2.5-flash", contents=f"Create a {slides}-slide carousel about: {topic}. Return JSON only: {{\"title\":\"...\",\"slides\":[{{\"slide\":1,\"headline\":\"...\",\"body\":\"...\",\"emoji\":\"...\"}}],\"caption\":\"...\",\"cta\":\"...\"}}")
 t=r.text.strip().replace("```json","").replace("```","").strip()
 result=json.loads(t)
 os.makedirs("/root/workspace/Penelope/carousels",exist_ok=True)
 fname=f"/root/workspace/Penelope/carousels/carousel_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
 open(fname,"w").write(json.dumps(result,indent=2))
 return jsonify({"success":True,"carousel":result})
@app.route("/")
def index():return jsonify({"service":"Penelope Carousel","port":9003})
if __name__=="__main__":app.run(host="0.0.0.0",port=9003)