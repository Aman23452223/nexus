"""Planning/Execution/Verification engine (PRD §19):
Intent → Discovery → Plan → Policy → Execute → Verify → Recover → Report → Learn.
MVP: explicit phase state + verification gate + bounded retry, no blind success.
"""
from dataclasses import dataclass, field
import re

from .audit import log_event, new_task_id
from .config import settings
from .policy import RiskClass, evaluate
from .tools import REGISTRY
from .tools import desktop, browser, devops, files, computer


@dataclass
class Task:
    intent: str
    workspace: str = ""
    task_id: str = ""
    plan: list = field(default_factory=list)
    status: str = "planned"


def extract_computer_target(intent: str) -> str:
    url = devops.extract_url(intent)
    if url:
        return url
    m = re.search(r"[A-Za-z]:\\[^\s\"']+", intent)
    if m:
        return m.group(0).rstrip(".,;)")
    m = re.search(r'"([^"]+)"', intent)
    if m:
        return m.group(1)
    return ""


def extract_app(intent: str) -> str:
    low = intent.lower()
    return next((a for a in computer.APPS if a in low), "")


def plan_for(intent: str) -> list:
    low = intent.lower()
    if any(k in low for k in ["deploy", "vercel", "release", "live ", "health"]):
        steps = ["devops.gh_status", "devops.vercel_inspect"]
        if devops.extract_url(intent):
            steps.append("devops.health_check")
        else:
            steps.append("devops.vercel_deploy")  # PUBLISH: gated, preview/approval
        return steps
    if any(k in low for k in ["screenshot", "screen dikha", "screen shot"]):
        return ["computer.screenshot"]
    if any(k in low for k in ["open", "khol", "launch", "start "]):
        if extract_app(intent):
            return ["computer.open"]
    if "type" in low or "likh" in low:
        return ["computer.type"]
    if "press" in low or "dabaa" in low:
        return ["computer.hotkey"]
    if any(k in low for k in ["website", "site", "audit", "hotel"]):
        return ["browser.open", "desktop.list_dir"]
    if any(k in low for k in ["download", "organize", "cleanup", "folder"]):
        return ["files.scan", "files.organize"]
    return ["desktop.list_dir"]


def execute(intent: str, workspace: str = "", dry_run: bool = False,
            auto_approve: bool = False) -> dict:
    ws = workspace or settings.workspace
    low = intent.lower()
    task_id = new_task_id()
    steps = plan_for(intent)
    task = Task(intent=intent, workspace=ws, task_id=task_id, plan=steps)
    results, confirmations = [], []

    for name in steps:
        spec = REGISTRY[name]
        if name in ("computer.type", "computer.hotkey") and not auto_approve:
            reason = "typing/keypress needs explicit approval (CLI --yes)"
            confirmations.append({"tool": name, "reason": reason})
            log_event(task_id, "orchestrator", name, "awaiting-confirmation", {"risk": spec.risk.value})
            results.append({"tool": name, "status": "awaiting-confirmation", "detail": reason})
            continue
        gate = evaluate(spec.risk, ws, dry_run=dry_run or settings.dry_run)
        if gate.needs_confirmation:
            confirmations.append({"tool": name, "reason": gate.reason})
            log_event(task_id, "orchestrator", name, "awaiting-confirmation", {"risk": spec.risk.value})
            results.append({"tool": name, "status": "awaiting-confirmation", "detail": gate.reason})
            continue
        try:
            if name == "desktop.list_dir":
                out = desktop.list_dir("./nexus_data")
            elif name == "desktop.run_cmd":
                out = {"note": "run_cmd needs explicit command — skipped in plan mode"}
            elif name == "files.scan":
                out = files.scan_downloads()
            elif name == "files.organize":
                scan = files.scan_downloads()
                moves = files.plan_moves(scan)
                preview = not auto_approve  # default dry-run; --yes to apply
                out = files.apply_moves(moves, dry_run=preview)
                out["disk_before_gb_free"] = scan["disk"]["free_gb"]
            elif name == "browser.open":
                out = browser.open_url("https://example.com")
            elif name == "devops.gh_status":
                out = devops.gh_status()
            elif name == "devops.vercel_inspect":
                out = devops.vercel_projects()
            elif name == "devops.health_check":
                url = devops.extract_url(intent)
                if not url:
                    raise RuntimeError("health_check needs a URL in the intent")
                out = devops.deployment_health(url)
            elif name == "devops.vercel_deploy":
                out = {"status": "needs-approval", "detail": "publish class: preview required"}
            elif name == "computer.open":
                app = extract_app(intent)
                if not app:
                    raise RuntimeError("no known app in intent")
                out = computer.open_app(app, extract_computer_target(intent))
            elif name == "computer.screenshot":
                out = computer.screenshot()
            elif name == "computer.windows":
                out = computer.list_windows()
            elif name == "computer.type":
                m = re.search(r'"([^"]+)"', intent)
                text = m.group(1) if m else ""
                if not text:
                    raise RuntimeError("computer.type needs quoted text")
                out = computer.type_text(text)
            elif name == "computer.hotkey":
                m = re.search(r"(ctrl|alt|shift|win|enter|esc|tab)[+,\s]*(\w+)?", low)
                keys = [k for k in m.groups() if k] if m else []
                if not keys:
                    raise RuntimeError("computer.hotkey needs keys like ctrl+s")
                out = computer.hotkey(*keys)
            else:
                out = {"status": "unknown-tool"}
            log_event(task_id, "orchestrator", name, "ok", {"spec": spec.verification})
            results.append({"tool": name, "status": "ok", "detail": out})
        except Exception as e:  # bounded recovery: record, don't claim success
            log_event(task_id, "orchestrator", name, f"failed: {e}")
            results.append({"tool": name, "status": "failed", "detail": str(e)})

    preview_pending = any(
        r["tool"] == "files.organize" and r["status"] == "ok"
        and isinstance(r["detail"], dict) and r["detail"].get("mode") == "dry-run"
        and r["detail"].get("pending_moves")
        for r in results
    )
    if preview_pending:
        task.status = "preview"
    else:
        task.status = "done" if all(r["status"] in ("ok",) for r in results) else "partial"
    report = {
        "task_id": task_id,
        "workspace": ws,
        "intent": intent,
        "plan": steps,
        "results": results,
        "needs_confirmation": confirmations,
        "status": task.status,
    }
    log_event(task_id, "orchestrator", "report", task.status, {"plan": steps})
    try:
        from . import store
        store.record_task(task_id, intent, ws, task.status)
        prior = store.learn(intent, steps) if task.status == "done" else 0
    except Exception:
        prior = 0
    report["workflow_reused"] = prior > 0
    report["prior_uses"] = prior
    return report
