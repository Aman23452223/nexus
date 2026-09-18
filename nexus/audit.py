"""Audit log (PRD §26). Every material action → task trace + evidence ref."""
import json
import os
import uuid
from datetime import datetime, timezone

from .vault import redact

AUDIT_FILE = os.environ.get("NEXUS_AUDIT_FILE", "./nexus_data/audit_log.jsonl")


def new_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:8]}"


def log_event(task_id: str, actor: str, tool: str, result: str, evidence: dict | None = None):
    event = {
        "task_id": task_id,
        "actor": actor,
        "tool": redact(tool),
        "result": redact(result),
        "evidence": evidence or {},
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        # Best-effort: serverless disks (Vercel /tmp only) are read-only —
        # never let audit break execution, fall back to stderr.
        os.makedirs(os.path.dirname(os.path.abspath(AUDIT_FILE)), exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as e:
        print(f"[audit-fallback] {json.dumps(event)} (file unavailable: {e})")
    return event
