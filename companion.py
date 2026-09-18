"""NEXUS laptop companion — background me hamesha chalne wala operator.

Run:  python companion.py        (starts local server + opens dashboard)
Boot: schtasks logon entry "nexus-companion" (registered by installer step)

Local server = FULL power: apps, files, browser, gh, vercel.
URL: http://127.0.0.1:8777  (sirf is laptop se)
"""
import os
import subprocess
import sys
import time
import webbrowser

HOST, PORT = "127.0.0.1", 8777


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "nexus.server:app",
         "--host", HOST, "--port", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS,
    )
    time.sleep(4)
    webbrowser.open(f"http://{HOST}:{PORT}")
    print(f"NEXUS companion live: http://{HOST}:{PORT}")


if __name__ == "__main__":
    main()
