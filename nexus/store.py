"""Persistent memory (PRD §21): SQLite locally, Postgres-ready.

- Local: NEXUS_DATA_DIR/nexus.db (zero deps, stdlib sqlite3).
- Later: set DATABASE_URL to a Supabase Postgres string and install
  psycopg — same functions, no code change needed elsewhere.
- Serverless (Vercel read-only disk): best-effort, never breaks execution.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone

from .config import settings

DB_PATH = os.path.join(os.path.abspath(settings.data_dir), "nexus.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, actor TEXT,
  tool TEXT, result TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  task_id TEXT PRIMARY KEY, intent TEXT, workspace TEXT,
  status TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS workflows(
  signature TEXT PRIMARY KEY, plan TEXT, uses INTEGER DEFAULT 1,
  last_ok TEXT);
"""


def _connect():
    if DATABASE_URL.startswith("postgresql"):
        import psycopg  # pip install psycopg[binary]; string stays in local .env
        return psycopg.connect(DATABASE_URL)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _exec(fn):
    try:
        conn = _connect()
        try:
            out = fn(conn)
            conn.commit()
            return out
        finally:
            conn.close()
    except Exception as e:  # memory never breaks execution
        print(f"[memory-fallback] {e}")
        return None


def init():
    def _run(conn):
        cur = conn.cursor()
        for stmt in _SCHEMA.strip().split(";"):
            if stmt.strip():
                cur.execute(stmt)
    _exec(_run)


def signature_of(intent: str) -> str:
    words = sorted(set(re.findall(r"[a-z]{3,}", intent.lower())))
    return " ".join(words[:8])


def record_event(task_id: str, actor: str, tool: str, result: str):
    def _run(conn):
        conn.cursor().execute(
            "INSERT INTO events(task_id,actor,tool,result,ts) VALUES(?,?,?,?,?)",
            (task_id, actor, tool, result[:500],
             datetime.now(timezone.utc).isoformat()))
    _exec(_run)


def record_task(task_id: str, intent: str, workspace: str, status: str):
    def _run(conn):
        conn.cursor().execute(
            "INSERT OR REPLACE INTO tasks(task_id,intent,workspace,status,ts)"
            " VALUES(?,?,?,?,?)", (task_id, intent[:500], workspace, status,
             datetime.now(timezone.utc).isoformat()))
    _exec(_run)


def learn(intent: str, plan: list) -> int:
    """Save successful plan. Returns prior use count (0 = brand new)."""
    sig = signature_of(intent)
    uses = _exec(lambda conn: _get_uses(conn, sig)) or 0

    def _run(conn):
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO workflows(signature,plan,uses,last_ok) VALUES(?,?,1,?)"
            " ON CONFLICT(signature) DO UPDATE SET plan=excluded.plan,"
            " uses=workflows.uses+1, last_ok=excluded.last_ok",
            (sig, ",".join(plan), datetime.now(timezone.utc).isoformat()))
    _exec(_run)
    return uses


def _get_uses(conn, sig: str) -> int:
    init_sentinel(conn)
    cur = conn.cursor()
    cur.execute("SELECT uses FROM workflows WHERE signature=?", (sig,))
    row = cur.fetchone()
    return row[0] if row else 0


def init_sentinel(conn):
    cur = conn.cursor()
    for stmt in _SCHEMA.strip().split(";"):
        if stmt.strip():
            try:
                cur.execute(stmt)
            except Exception:
                pass


init()
