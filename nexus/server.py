"""FastAPI control plane (PRD §27): auth-lite, tasks, policy, stop."""
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import orchestrator
from .tools import desktop

app = FastAPI(title="NEXUS MVP", version="0.1.0")

DASHBOARD = """<!doctype html><html><head><meta charset=utf-8>
<title>NEXUS MVP</title></head><body style="font-family:sans-serif;max-width:760px;margin:40px auto">
<h1>NEXUS MVP — permissioned operator</h1>
<p>Outcome in, verified report out. Policy-gated publish.</p>
<input id=q size=60 placeholder="e.g. whatsapp khol, ya health check https://...">
<button onclick="run()">Run</button>
<button onclick="mic()" title="bolke bolo 🎤">🎤</button>
<button onclick="voice=!voice;this.textContent=voice?'🔊':'🔇'" title="jawab sunna">🔊</button>
<label title="send/type wale kaam turant ho (bina roke)"><input type=checkbox id=arm> ✅ bhejne do</label>
<a href="/health">/health</a> <a href="/docs">/docs</a>
<div style="margin:8px 0">☁️ Cloud:
<button onclick="set('health check https://example.com')">example health</button>
</div>
<div style="margin:8px 0">💻 Laptop (mere laptop pe khulega — yahan dabane se sirf command milegi):
<button onclick="set('whatsapp khol')">WhatsApp khol</button>
<button onclick="set('antigravity me nexus khol C:\\Users\\amanc\\nexus')">Antigravity + nexus</button>
</div>
<div id=out></div>
<script>
let voice=true;
function set(v){document.getElementById('q').value=v;run();}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function speak(t){try{if(!voice)return;const u=new SpeechSynthesisUtterance(t);
u.lang='hi-IN';speechSynthesis.cancel();speechSynthesis.speak(u);}catch(e){}}
function mic(){
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
const out=document.getElementById('out');
if(!SR){out.innerHTML='<p>Mic sirf Chrome me chalta hai.</p>';return;}
const r=new SR();r.lang='hi-IN';r.interimResults=false;
out.innerHTML='<p>🎤 Sun raha hu… bolo.</p>';
r.onresult=e=>{document.getElementById('q').value=e.results[0][0].transcript;run();};
r.onerror=e=>{let m=e.error;
if(m==='network')m='Brave me mic nahi chalta (voice service blocked). Chrome me yehi site kholo — wahan chalega.';
else if(m==='not-allowed')m='Mic permission do (address bar ke lock icon me).';
out.innerHTML='<p>Mic error: '+esc(m)+'</p>';};
r.start();}
async function run(){
const q=document.getElementById('q').value.trim();
const out=document.getElementById('out');
if(!q){out.innerHTML='<p style=color:#a00>Intent likho pehle — khaali command nahi chalegi.</p>';return;}
out.innerHTML='<p>Working…</p>';
const r=await fetch('/tasks',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({intent:q,auto_approve:document.getElementById('arm').checked})});
if(!r.ok){out.innerHTML='<p style=color:#a00>Rejected: '+(await r.text()).slice(0,200)+'</p>';return;}
const d=await r.json();
let h='<h3>Status: '+esc(d.status)+' <small>('+esc(d.task_id)+' · '+esc(d.workspace)+')</small></h3>';
h+='<p><b>Intent:</b> '+esc(d.intent)+'<br><b>Plan:</b> '+esc(d.plan.join(' → '))+'</p>';
if(d.workflow_reused)h+='<p>♻ Known workflow (used '+d.prior_uses+'× before)</p>';
h+='<ul>'+d.results.map(x=>{
const lap=x.status==='needs-laptop';
return '<li>'+(lap?'💻 ':'')+'<b>'+esc(x.tool)+'</b> — '+esc(x.status)+
'<br><small>'+esc(typeof x.detail==='string'?x.detail:JSON.stringify(x.detail).slice(0,300))+'</small></li>';}).join('')+'</ul>';
if(d.needs_confirmation&&d.needs_confirmation.length)
h+='<p><b>Needs approval:</b><ul>'+d.needs_confirmation.map(c=>'<li>'+esc(c.tool)+': '+esc(c.reason)+'</li>').join('')+'</ul></p>';
out.innerHTML=h;
const say='Status '+d.status+'. '+d.results.map(x=>x.tool+' '+x.status).join('. ');
speak(say.slice(0,300));}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    mode = ("💻 LAPTOP MODE — haath-pair live (apps, files, browser, deploy)"
            if os.name == "nt" else
            "☁️ CLOUD MODE — dimaag only (health checks, reports)")
    return DASHBOARD.replace("Policy-gated publish.",
                             f"Policy-gated publish.<br><b>{mode}</b>", 1)


class TaskIn(BaseModel):
    intent: str = Field(min_length=3, max_length=500)
    workspace: str = ""
    dry_run: bool = False
    auto_approve: bool = False


@app.get("/health")
def health():
    return {"ok": True, "service": "nexus-mvp"}


@app.post("/tasks")
def run_task(t: TaskIn):
    # auto_approve defaults False → files.organize stays dry-run preview
    return orchestrator.execute(t.intent, workspace=t.workspace, dry_run=t.dry_run,
                                auto_approve=t.auto_approve)


@app.post("/stop")
def stop():
    desktop.request_stop()
    return {"stopped": True}
