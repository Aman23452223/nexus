"""Desktop companion slice (PRD §7): allow-listed filesystem + terminal.

Safety: confines file ops to workspace dirs, blocks destructive shell
operators unless policy gate passes, supports global STOP flag.
"""
import os
import subprocess

STOP_FLAG = {"stopped": False}

ALLOWED_ROOTS = [
    os.path.abspath(os.environ.get("NEXUS_DATA_DIR", "./nexus_data")),
    os.path.abspath(os.path.join(os.path.expanduser("~"), "Downloads")),
]

BLOCKED_TOKENS = ["rm -rf", "mkfs", "format ", ":(){", "shutdown", "del /f /s /q"]


def request_stop():
    STOP_FLAG["stopped"] = True


def _check(cmd: str):
    if STOP_FLAG["stopped"]:
        raise RuntimeError("STOP engaged — execution suspended.")
    low = cmd.lower()
    if any(t.lower() in low for t in BLOCKED_TOKENS):
        raise RuntimeError("Blocked by desktop policy: destructive pattern.")


def list_dir(path: str) -> dict:
    ap = os.path.abspath(path)
    if not any(ap.startswith(r) or ap == r for r in ALLOWED_ROOTS):
        raise RuntimeError(f"Path outside allowed roots: {ap}")
    return {"path": ap, "entries": sorted(os.listdir(ap)) if os.path.isdir(ap) else []}


def run_cmd(cmd: str, timeout: int = 60) -> dict:
    _check(cmd)
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "")[-4000:] + (("\n[stderr]\n" + p.stderr[-2000:]) if p.stderr else "")
    return {"exit": p.returncode, "output": out}
