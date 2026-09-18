"""Morning operating brief (PRD §20 autopilot): read-only scan → priorities.

Covers: key production sites health, Downloads drift, nexus repo state,
memory stats. Writes nexus_data/brief-YYYY-MM-DD.md. Never mutates.
"""
import os
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WATCH_URLS = [
    "https://nexus-gamma-drab.vercel.app/health",
    "https://arbitrage-agent-gules.vercel.app",
    "https://www.tomorrow-land.in",
]


def section(name: str, fn) -> str:
    try:
        return f"\n## {name}\n{fn()}"
    except Exception as e:
        return f"\n## {name}\nUNAVAILABLE: {e}"


def health_lines() -> str:
    from nexus.tools import devops
    out = []
    for u in WATCH_URLS:
        try:
            r = devops.deployment_health(u)
            flag = "OK" if r["ok"] else f"HTTP {r['http_status']}"
            out.append(f"- {flag} {u} ({r['latency_ms']}ms)")
        except Exception as e:
            out.append(f"- DOWN {u} ({str(e)[:100]})")
    return "\n".join(out)


def downloads_line() -> str:
    from nexus.tools import files
    s = files.scan_downloads()
    dups = len(s["duplicate_groups"])
    return (f"- top-level files: {s['file_count']} ({s['total_mb']} MB), "
            f"duplicate groups: {dups}, free: {s['disk']['free_gb']} GB")


def repo_line() -> str:
    root = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.run(["git", "status", "--short"], capture_output=True,
                       text=True, cwd=root)
    body = (p.stdout or "").strip() or "clean"
    log = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True,
                         text=True, cwd=root).stdout.strip()
    return f"- status: {body}\n- recent:\n{log}"


def memory_line() -> str:
    from nexus import store
    t = store._exec(lambda c: c.cursor().execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    w = store._exec(lambda c: c.cursor().execute(
        "SELECT COUNT(*), COALESCE(SUM(uses),0) FROM workflows").fetchone())
    return f"- tasks by status: {t}\n- workflows: {w}"


def main():
    # Scheduler runs with cwd=System32 — anchor everything to repo dir.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    from nexus.config import settings
    data = os.path.abspath(settings.data_dir)
    os.makedirs(data, exist_ok=True)
    brief = f"# NEXUS morning brief — {date.today().isoformat()}"
    brief += section("Production health", health_lines)
    brief += section("Downloads", downloads_line)
    brief += section("Nexus repo", repo_line)
    brief += section("Memory", memory_line)
    brief += "\n\n_Next: duplicates review pending; deploy pipeline idle._\n"
    path = os.path.join(data, f"brief-{date.today().isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(brief)
    print(brief)
    print(f"\nsaved: {path}")


if __name__ == "__main__":
    main()
