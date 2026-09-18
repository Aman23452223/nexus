"""Developer connectors (PRD §15): gh + vercel CLI wrappers + deploy health.

Auth: uses your local CLI logins (gh keyring / vercel session).
No tokens in code/chat — only opaque refs via vault.
Publish actions (vercel deploy) stay behind the policy gate.
"""
import re
import subprocess
import time

from ..vault import get_secret_ref

URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def extract_url(intent: str) -> str:
    m = URL_RE.search(intent or "")
    return m.group(0).rstrip(".,;)") if m else ""


def _run(cmd: list[str], timeout: int = 60) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        # Windows npm shims (.ps1/.cmd) aren't direct executables —
        # retry through PowerShell which resolves them via PATH.
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", " ".join(cmd)],
            capture_output=True, text=True, timeout=timeout,
        )
    return {"exit": p.returncode, "output": (p.stdout + p.stderr)[-3000:]}


def gh_status() -> dict:
    out = _run(["gh", "auth", "status"])
    out["token_ref"] = get_secret_ref("GITHUB_TOKEN")
    return out


def vercel_whoami() -> dict:
    out = _run(["vercel", "whoami"])
    out["token_ref"] = get_secret_ref("VERCEL_TOKEN")
    return out


def vercel_projects() -> dict:
    """Read-only: list projects under current scope (PRD verify-before-act)."""
    return _run(["vercel", "project", "ls"])


def deployment_health(url: str, timeout: int = 25) -> dict:
    """Live health verify: HTTP status + latency + title marker.

    Raises on network failure or 5xx so orchestrator never
    claims success without an observable signal (PRD §19).
    """
    import httpx

    t0 = time.time()
    r = httpx.get(url, follow_redirects=True, timeout=timeout,
                  headers={"User-Agent": "NEXUS-health/0.1"})
    ms = int((time.time() - t0) * 1000)
    m = _TITLE_RE.search(r.text or "")
    title = re.sub(r"\s+", " ", m.group(1)).strip()[:200] if m else ""
    ok = 200 <= r.status_code < 400
    result = {
        "url": url,
        "final_url": str(r.url),
        "http_status": r.status_code,
        "latency_ms": ms,
        "title": title,
        "ok": ok,
        "verification": "HTTP 2xx/3xx + title marker captured",
    }
    if r.status_code >= 500:
        raise RuntimeError(f"Health verify failed: {url} -> {r.status_code}")
    return result
