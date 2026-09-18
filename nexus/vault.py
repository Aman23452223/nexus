"""Secret vault layer (PRD §9, §24).

Rules:
- Secrets load ONLY from env / OS keychain, never from chat, logs, or code.
- This module returns opaque refs; raw values are never logged.
- Redaction helper scrubs known secret patterns from any output.
"""
import os
import re

_SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"vcp_[A-Za-z0-9]+"),
    re.compile(r"sk-[A-Za-z0-9\-_]+"),
    re.compile(r"xox[bap]-[A-Za-z0-9\-_]+"),
]


def redact(text: str) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def get_secret_ref(name: str) -> dict:
    """Return metadata only: whether set, length, source. Never the value."""
    val = os.environ.get(name, "")
    return {
        "name": name,
        "configured": bool(val),
        "length": len(val) if val else 0,
        "source": "env" if val else "missing",
    }


def require_secret(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(
            f"{name} not configured. Set it in local .env (never in chat/code)."
        )
    return val
