"""Files workflow (PRD §16): scan → categorize → move → report.

Safety rules (PRD destructive-file rule):
- Operates ONLY on top-level files inside root (default ~/Downloads).
  Subfolders are never touched. Nothing is ever deleted in MVP —
  duplicates are REPORTED, not removed.
- Default mode is dry-run preview. Real moves need auto_approve=True
  (CLI --yes). Every move is logged for audit.
"""
import hashlib
import os
import shutil

CATEGORIES = {
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".apk"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Audio": {".mp3", ".wav", ".ogg", ".flac"},
    "Documents": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".md"},
}

HASH_CAP_BYTES = 500 * 1024 * 1024  # skip hashing beyond this size
TOP_LEVEL_ONLY = True


def default_root() -> str:
    return os.path.join(os.path.expanduser("~"), "Downloads")


def disk_report(path: str) -> dict:
    total, used, free = shutil.disk_usage(path)
    return {"total_gb": round(total / 1e9, 2), "used_gb": round(used / 1e9, 2),
            "free_gb": round(free / 1e9, 2)}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_downloads(root: str = "") -> dict:
    root = os.path.abspath(root or default_root())
    entries = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        entries.append({"name": name, "path": p,
                        "bytes": os.path.getsize(p),
                        "ext": os.path.splitext(name)[1].lower()})
    # duplicates: hash only same-size groups (fast), skip giant files
    by_size: dict[int, list] = {}
    for e in entries:
        by_size.setdefault(e["bytes"], []).append(e)
    dup_groups: list[list[str]] = []
    for size, group in by_size.items():
        if len(group) < 2 or size == 0:
            continue
        by_hash: dict[str, list[str]] = {}
        for e in group:
            if size > HASH_CAP_BYTES:
                e["hash"] = "skipped-too-large"
                continue
            try:
                e["hash"] = _sha256(e["path"])
            except OSError:
                e["hash"] = "unreadable"
                continue
            by_hash.setdefault(e["hash"], []).append(e["name"])
        dup_groups.extend(names for names in by_hash.values() if len(names) > 1)
    installers = [e["name"] for e in entries if e["ext"] in CATEGORIES["Installers"]]
    return {"root": root, "file_count": len(entries),
            "total_mb": round(sum(e["bytes"] for e in entries) / 1e6, 1),
            "installers": installers, "duplicate_groups": dup_groups,
            "disk": disk_report(root)}


def _dest_folder(root: str, ext: str) -> str:
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return os.path.join(root, cat)
    return os.path.join(root, "Others")


def plan_moves(scan: dict) -> list[dict]:
    root = scan["root"]
    moves = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        dest_dir = _dest_folder(root, os.path.splitext(name)[1].lower())
        dest = os.path.join(dest_dir, name)
        if os.path.abspath(p) != os.path.abspath(dest) and not os.path.exists(dest):
            moves.append({"src": p, "dst": dest, "category": os.path.basename(dest_dir)})
    return moves


def apply_moves(moves: list[dict], dry_run: bool = True) -> dict:
    if dry_run:
        by_cat: dict[str, int] = {}
        for m in moves:
            by_cat[m["category"]] = by_cat.get(m["category"], 0) + 1
        return {"mode": "dry-run", "pending_moves": len(moves), "by_category": by_cat,
                "preview": moves[:20],
                "note": "Nothing moved. Re-run with --yes to apply."}
    moved, failed = [], []
    for m in moves:
        try:
            os.makedirs(os.path.dirname(m["dst"]), exist_ok=True)
            shutil.move(m["src"], m["dst"])
            moved.append(m)
        except OSError as e:
            failed.append({"move": m, "error": str(e)})
    return {"mode": "applied", "moved": len(moved), "failed": failed}
