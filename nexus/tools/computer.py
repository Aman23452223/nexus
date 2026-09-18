"""Computer control (PRD §7): open apps, focus windows, screenshot.

Real control of THIS laptop. Rules:
- open/focus/screenshot/list = safe, auto-runnable.
- type/hotkey = act on the focused window → need auto_approve (CLI --yes),
  otherwise orchestrator holds them for confirmation. Never blind-type.
- Every action verifies: window title observed, or it didn't happen.
"""
import os
import subprocess
import time

WHATSAPP_UWP = r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"
ANTIGRAVITY = r"C:\Users\amanc\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe"
VSCODE = r"C:\Users\amanc\AppData\Local\Programs\Microsoft VS Code\Code.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


class NeedsLaptop(Exception):
    """Raised when a hands-action runs in the cloud. Carries the fix."""
    def __init__(self, intent_hint: str):
        self.intent_hint = intent_hint
        super().__init__(
            "Ye kaam cloud me nahi hota — laptop pe chalao: "
            f'python C:\\Users\\amanc\\nexus\\cli.py "{intent_hint}" --yes')


def _require_laptop(intent_hint: str = ""):
    if os.name != "nt":
        raise NeedsLaptop(intent_hint)

APPS = {
    "whatsapp": {"launch": ["explorer.exe", WHATSAPP_UWP], "window_hint": "WhatsApp"},
    "antigravity": {"launch": [ANTIGRAVITY], "window_hint": "Antigravity", "takes_folder": True, "new_window": "--new-window"},
    "vscode": {"launch": [VSCODE], "window_hint": "Visual Studio Code", "takes_folder": True, "new_window": "--new-window"},
    "code": {"launch": [VSCODE], "window_hint": "Visual Studio Code", "takes_folder": True, "new_window": "--new-window"},
    "chrome": {"launch": [CHROME], "window_hint": "Chrome", "takes_url": True},
    "terminal": {"launch": ["wt.exe"], "window_hint": "Windows Terminal"},
    "explorer": {"launch": ["explorer.exe"], "window_hint": "File Explorer", "takes_folder": True},
}


def _windows():
    import pygetwindow as gw
    return gw.getAllTitles()


def list_windows() -> dict:
    _require_laptop()
    titles = [t for t in _windows() if t]
    return {"count": len(titles), "windows": titles[:40]}


def find_window(hint: str) -> str:
    for t in _windows():
        if t and hint.lower() in t.lower():
            return t
    return ""


def open_app(name: str, target: str = "") -> dict:
    _require_laptop(f"open {name} {target}".strip())
    key = (name or "").lower().strip()
    if key not in APPS:
        raise RuntimeError(f"Unknown app '{name}'. Known: {sorted(APPS)}")
    spec = APPS[key]
    cmd = list(spec["launch"])
    if target and spec.get("takes_folder") and os.path.exists(target):
        if spec.get("new_window"):
            cmd.append(spec["new_window"])
        cmd.append(target)
    elif target and spec.get("takes_url") and target.startswith("http"):
        cmd.append(target)
    elif target:
        cmd.append(target)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL)
    # Verify the RIGHT window: folder name when a folder was requested.
    if target and os.path.isdir(target):
        need = os.path.basename(os.path.normpath(target))
    else:
        need = spec["window_hint"]
    found = ""
    for _ in range(20):  # ~10s for window to appear
        time.sleep(0.5)
        found = find_window(need)
        if found:
            break
    if not found:
        raise RuntimeError(f"Launched {key} but no '{need}' window seen in 10s")
    return {"app": key, "window": found,
            "verification": f"window '{found}' observed on screen"}


def focus_window(hint: str) -> dict:
    _require_laptop()
    import pygetwindow as gw
    for t in _windows():
        if t and hint.lower() in t.lower():
            for w in gw.getAllWindows():
                if w.title == t:
                    if w.isMinimized:
                        w.restore()
                    w.activate()
                    time.sleep(0.5)
                    return {"window": t, "verification": f"focused '{t}'"}
    raise RuntimeError(f"No window matching '{hint}' on screen")


def screenshot(name: str = "") -> dict:
    _require_laptop()
    import pyautogui
    data_dir = os.path.abspath(os.environ.get("NEXUS_DATA_DIR", "./nexus_data"))
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, name or f"screen-{int(time.time())}.png")
    pyautogui.screenshot(path)
    return {"screenshot": path, "active_window": active_title(),
            "verification": "screenshot saved + active window observed"}


def active_title() -> str:
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        return w.title if w else ""
    except Exception:
        return ""


def type_text(text: str, window_hint: str = "") -> dict:
    """Type into the focused (or hinted) window. Caller must hold approval."""
    _require_laptop()
    import pyautogui
    if window_hint:
        focus_window(window_hint)
    before = active_title()
    pyautogui.write(text, interval=0.02)
    return {"typed_chars": len(text), "window": before,
            "verification": f"typed into '{before}'"}


def hotkey(*keys: str, window_hint: str = "") -> dict:
    """Press a key combo (e.g. ctrl,s). Caller must hold approval."""
    _require_laptop()
    import pyautogui
    if window_hint:
        focus_window(window_hint)
    before = active_title()
    pyautogui.hotkey(*keys)
    return {"keys": "+".join(keys), "window": before,
            "verification": f"sent to '{before}'"}
