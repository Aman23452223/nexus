"""FastAPI control plane (PRD §27): auth-lite, tasks, policy, stop."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import orchestrator
from .tools import desktop

app = FastAPI(title="NEXUS MVP", version="0.1.0")

DASHBOARD = """<!doctype html><html><head><meta charset=utf-8>
<title>NEXUS MVP</title></head><body style="font-family:sans-serif;max-width:720px;margin:40px auto">
<h1>NEXUS MVP — permissioned operator</h1>
<p>Outcome in, verified report out. Policy-gated publish.</p>
<input id=q size=60 placeholder="e.g. arbitrage-agent health check https://...">
<button onclick="run()">Run</button> <a href="/health">/health</a> <a href="/docs">/docs</a>
<pre id=out></pre>
<script>async function run(){const r=await fetch('/tasks',{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({intent:document.getElementById('q').value})});
document.getElementById('out').textContent=JSON.stringify(await r.json(),null,1);}</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD


class TaskIn(BaseModel):
    intent: str
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
