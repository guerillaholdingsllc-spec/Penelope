#!/usr/bin/env python3
"""Notion Template Gallery & Dashboard"""
from flask import Flask,render_template_string,send_from_directory,jsonify,request
import json,os
from pathlib import Path

app=Flask(__name__)
OUTPUT_DIR=Path("/root/workspace/Penelope/notion_output")
PROJECTS_LOG=Path("/root/workspace/Penelope/notion_projects.json")

TEMPLATE="""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Penelope — Notion Template Factory</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a14;--card:#12121e;--border:rgba(255,255,255,.07);--accent:#10b981;--purple:#8b5cf6;--text:#e0e0f0}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:18px 30px;display:flex;align-items:center;justify-content:space-between}
.logo{font-family:'Sora',sans-serif;font-weight:800;font-size:1.2rem;color:var(--accent)}
.container{max-width:1200px;margin:0 auto;padding:30px 20px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:30px}
.stat{background:var(--card);border-radius:10px;padding:20px;border:1px solid var(--border)}
.stat-val{font-family:'Sora',sans-serif;font-size:2rem;font-weight:800;color:var(--accent)}
.stat-label{font-size:.75rem;color:#666;text-transform:uppercase;letter-spacing:1px;margin-top:4px}
h2{font-family:'Sora',sans-serif;font-size:1.1rem;color:white;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px;margin-bottom:40px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:border-color .2s}
.card:hover{border-color:var(--accent)}
.card-preview{height:200px;background:#f8f9fa;position:relative;overflow:hidden}
.card-preview iframe{width:200%;height:200%;transform:scale(.5);transform-origin:top left;border:none;pointer-events:none}
.card-body{padding:16px}
.card-niche{font-family:'Sora',sans-serif;font-weight:700;font-size:1rem;color:white;margin-bottom:4px}
.card-price{color:var(--accent);font-weight:700;font-size:.9rem;margin-bottom:4px}
.card-audience{font-size:.75rem;color:#666;margin-bottom:12px}
.btn-row{display:flex;gap:8px;flex-wrap:wrap}
.btn{padding:7px 12px;border-radius:6px;font-size:.78rem;font-weight:600;text-decoration:none;border:1px solid var(--border);color:#ccc;cursor:pointer;background:rgba(255,255,255,.04)}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn-green{background:var(--accent);color:#000;border-color:transparent}
.btn-green:hover{opacity:.85;color:#000}
.empty{text-align:center;padding:60px;color:#555}
.build-form{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:30px}
.form-row{display:grid;grid-template-columns:1fr 120px auto;gap:12px;align-items:end}
input,select{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-family:'Inter',sans-serif;font-size:.9rem;width:100%}
input:focus,select:focus{outline:none;border-color:var(--accent)}
.price-input{max-width:120px}
</style></head><body>
<header><div class="logo">📋 NOTION FACTORY</div><div style="font-size:.8rem;color:#666">Penelope Template Engine</div></header>
<div class="container">
<div class="stats">
<div class="stat"><div class="stat-val">{{total}}</div><div class="stat-label">Templates Built</div></div>
<div class="stat"><div class="stat-val">${{total_value}}</div><div class="stat-label">Total List Value</div></div>
<div class="stat"><div class="stat-val">{{gumroad_count}}</div><div class="stat-label">On Gumroad</div></div>
<div class="stat"><div class="stat-val">$21K</div><div class="stat-label">Top Earner/mo</div></div>
</div>
<div class="build-form">
<h2 style="margin-bottom:16px">⚡ Build New Template</h2>
<div class="form-row">
<div><label style="font-size:.75rem;color:#666;display:block;margin-bottom:6px">Template Niche</label>
<input type="text" id="nicheInput" placeholder="e.g. monthly budget tracker, student planner..."></div>
<div><label style="font-size:.75rem;color:#666;display:block;margin-bottom:6px">Price ($)</label>
<input type="number" id="priceInput" value="27" min="5" max="97"></div>
<div style="padding-bottom:2px"><button onclick="buildTemplate()" class="btn btn-green" style="padding:11px 20px;white-space:nowrap">Build Now →</button></div>
</div>
<div id="buildStatus" style="margin-top:12px;font-size:.8rem;color:#666"></div>
</div>
<h2>🗂️ Template Library</h2>
{% if projects %}
<div class="grid">
{% for p in projects %}
<div class="card">
<div class="card-preview"><iframe src="/preview/{{p.preview_file}}" loading="lazy"></iframe></div>
<div class="card-body">
<div class="card-niche">📋 {{p.niche}}</div>
<div class="card-price">${{p.price}} · {{p.audience[:40]}}</div>
<div class="card-audience">{{p.timestamp[:16]}}</div>
<div class="btn-row">
<a href="/preview/{{p.preview_file}}" target="_blank" class="btn btn-green">Preview</a>
<a href="/prompt/{{p.prompt_file}}" target="_blank" class="btn">Notion Prompt</a>
<a href="/listing/{{p.listing_file}}" target="_blank" class="btn">Etsy Listing</a>
{% if p.gumroad_url %}<a href="{{p.gumroad_url}}" target="_blank" class="btn">Gumroad 🚀</a>{% endif %}
</div></div></div>
{% endfor %}
</div>
{% else %}
<div class="empty"><div style="font-size:3rem;margin-bottom:16px">📋</div>
<div style="font-size:1.2rem;color:#444;margin-bottom:8px">No templates yet</div>
<div style="color:#555">Build your first template above or run: python3 notion_agent.py --batch 5</div></div>
{% endif %}
</div>
<script>
async function buildTemplate() {
  const niche=document.getElementById('nicheInput').value.trim();
  const price=document.getElementById('priceInput').value;
  if(!niche){alert('Enter a niche first');return;}
  document.getElementById('buildStatus').textContent='⏳ Building '+niche+'... This takes ~30 seconds. Check Telegram for updates.';
  try{
    const r=await fetch('/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({niche,price:parseFloat(price)})});
    const d=await r.json();
    if(d.success){document.getElementById('buildStatus').textContent='✅ Built! Refreshing...';setTimeout(()=>location.reload(),2000);}
    else{document.getElementById('buildStatus').textContent='Error: '+d.error;}
  }catch(e){document.getElementById('buildStatus').textContent='Error: '+e.message;}
}
</script>
</body></html>"""

@app.route('/')
def index():
    projects=[];total=0;total_value=0;gumroad_count=0
    if PROJECTS_LOG.exists():
        try:
            raw=json.loads(PROJECTS_LOG.read_text())
            for p in reversed(raw):
                total+=1;total_value+=p.get('price',0)
                gr=p.get('gumroad',{}) or {}
                if gr.get('url'):gumroad_count+=1
                projects.append({
                    'niche':p.get('niche','Template'),
                    'price':p.get('price',27),
                    'audience':p.get('audience',''),
                    'timestamp':p.get('timestamp',''),
                    'preview_file':Path(p.get('preview_html','')).name,
                    'prompt_file':Path(p.get('notion_prompt','')).name,
                    'listing_file':Path(p.get('listing_file','')).name,
                    'gumroad_url':gr.get('url','')
                })
        except:pass
    return render_template_string(TEMPLATE,projects=projects,total=total,
        total_value=int(total_value),gumroad_count=gumroad_count)

@app.route('/preview/<filename>')
def preview(filename):return send_from_directory(str(OUTPUT_DIR),filename)

@app.route('/prompt/<filename>')
def prompt_file(filename):
    f=OUTPUT_DIR/filename
    if f.exists():
        from flask import Response
        return Response(f.read_text(),mimetype='text/plain')
    return "Not found",404

@app.route('/listing/<filename>')
def listing_file(filename):
    f=OUTPUT_DIR/filename
    if f.exists():
        from flask import Response
        return Response(f.read_text(),mimetype='text/plain')
    return "Not found",404

@app.route('/build',methods=['POST'])
def build():
    import subprocess
    data=request.json
    niche=data.get('niche','')
    price=data.get('price',27)
    if not niche:return jsonify({'success':False,'error':'No niche'})
    try:
        subprocess.Popen([
            '/root/penelope_env/bin/python3',
            '/root/workspace/Penelope/notion_agent.py',
            '--niche',niche,'--price',str(price)
        ],env={**os.environ,'GOOGLE_API_KEY':os.getenv('GOOGLE_API_KEY',''),
              'TELEGRAM_BOT_TOKEN':os.getenv('TELEGRAM_BOT_TOKEN',''),
              'TELEGRAM_CHAT_ID':os.getenv('TELEGRAM_CHAT_ID','6183015901'),
              'GUMROAD_API_KEY':os.getenv('GUMROAD_API_KEY','')})
        return jsonify({'success':True})
    except Exception as e:return jsonify({'success':False,'error':str(e)})

@app.route('/api/projects')
def api():
    if PROJECTS_LOG.exists():return jsonify(json.loads(PROJECTS_LOG.read_text()))
    return jsonify([])

if __name__=='__main__':app.run(host='0.0.0.0',port=9002,debug=False)
