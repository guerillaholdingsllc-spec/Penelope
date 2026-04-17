#!/usr/bin/env python3
"""Stitch Agent Preview Server — gallery of built apps with live preview"""
from flask import Flask,render_template_string,send_from_directory,jsonify
import os,json
from pathlib import Path

app=Flask(__name__)
OUTPUT_DIR=Path("/root/workspace/Penelope/stitch_output")
PROJECTS_LOG=Path("/root/workspace/Penelope/stitch_projects.json")

TEMPLATE="""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Penelope Stitch — App Gallery</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>:root{--bg:#0a0a14;--card:#12121e;--border:rgba(255,255,255,.07);--accent:#6366f1;--green:#00d68f;--text:#e0e0f0}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:var(--card);border-bottom:1px solid var(--border);padding:20px 30px;display:flex;align-items:center;justify-content:space-between}
.logo{font-family:'Sora',sans-serif;font-weight:800;font-size:1.2rem;color:var(--accent)}
.container{max-width:1200px;margin:0 auto;padding:30px 20px}
h2{font-family:'Sora',sans-serif;font-size:1.2rem;margin-bottom:20px;color:white}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px;margin-bottom:40px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:border-color .2s}
.card:hover{border-color:var(--accent)}
.card-preview{height:200px;background:#1a1a2e;position:relative;overflow:hidden}
.card-preview iframe{width:200%;height:200%;transform:scale(.5);transform-origin:top left;border:none;pointer-events:none}
.card-body{padding:16px}
.card-name{font-family:'Sora',sans-serif;font-weight:700;font-size:1rem;color:white;margin-bottom:6px}
.card-time{font-size:.75rem;color:#666;margin-bottom:12px}
.btn-row{display:flex;gap:8px}
.btn{padding:8px 14px;border-radius:6px;font-size:.8rem;font-weight:600;text-decoration:none;border:none;cursor:pointer}
.btn-primary{background:var(--accent);color:white}
.btn-secondary{background:rgba(255,255,255,.06);color:#ccc;border:1px solid var(--border)}
.empty{text-align:center;padding:60px;color:#555}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:30px}
.stat{background:var(--card);border-radius:10px;padding:20px;border:1px solid var(--border)}
.stat-val{font-family:'Sora',sans-serif;font-size:2rem;font-weight:800;color:var(--accent)}
.stat-label{font-size:.75rem;color:#666;text-transform:uppercase;letter-spacing:1px;margin-top:4px}
</style></head><body>
<header><div class="logo">✂️ PENELOPE STITCH</div><div style="font-size:.8rem;color:#666">App Builder Gallery</div></header>
<div class="container">
<div class="stats">
<div class="stat"><div class="stat-val">{{total}}</div><div class="stat-label">Apps Built</div></div>
<div class="stat"><div class="stat-val">{{deployed}}</div><div class="stat-label">Deployed Live</div></div>
<div class="stat"><div class="stat-val">$15K</div><div class="stat-label">Avg Value</div></div>
</div>
<h2>🗂️ Built Apps</h2>
{% if projects %}
<div class="grid">
{% for p in projects %}
<div class="card">
<div class="card-preview"><iframe src="/preview/{{p.main_file}}" loading="lazy"></iframe></div>
<div class="card-body">
<div class="card-name">{{p.name}}</div>
<div class="card-time">{{p.timestamp[:16]}}</div>
<div class="btn-row">
<a href="/preview/{{p.main_file}}" target="_blank" class="btn btn-primary">View App</a>
{% if p.vercel_url %}<a href="{{p.vercel_url}}" target="_blank" class="btn btn-secondary">Live 🚀</a>{% endif %}
{% if p.results_file %}<a href="/preview/{{p.results_file}}" target="_blank" class="btn btn-secondary">Results</a>{% endif %}
</div></div></div>
{% endfor %}
</div>
{% else %}
<div class="empty"><div style="font-size:3rem;margin-bottom:16px">✂️</div><div style="font-size:1.2rem;color:#444;margin-bottom:8px">No apps built yet</div>
<div style="color:#555;font-size:.9rem">Run: python3 stitch_agent.py --idea "your app idea" --niche "target audience"</div></div>
{% endif %}
</div></body></html>"""

@app.route('/')
def index():
    projects=[]
    total=deployed=0
    if PROJECTS_LOG.exists():
        try:
            raw=json.loads(PROJECTS_LOG.read_text())
            for p in reversed(raw):
                total+=1
                if p.get('vercel_url'):deployed+=1
                projects.append({
                    'name':p.get('name','App'),
                    'timestamp':p.get('timestamp',''),
                    'main_file':Path(p.get('main_html','')).name,
                    'results_file':Path(p.get('results_html','')).name if p.get('results_html') else '',
                    'vercel_url':p.get('vercel_url',''),
                    'source_url':p.get('source_url','')
                })
        except:pass
    return render_template_string(TEMPLATE,projects=projects,total=total,deployed=deployed)

@app.route('/preview/<filename>')
def preview(filename):
    return send_from_directory(str(OUTPUT_DIR),filename)

@app.route('/api/projects')
def api_projects():
    if PROJECTS_LOG.exists():
        return jsonify(json.loads(PROJECTS_LOG.read_text()))
    return jsonify([])

if __name__=='__main__':
    app.run(host='0.0.0.0',port=9001,debug=False)
