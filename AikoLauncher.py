
import subprocess
import sys
import time
import os
import http.client
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.absolute()
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = sys.executable # Fallback

HUB_SCRIPT = PROJECT_ROOT / "core" / "neural_hub.py"
TAURI_DIR = PROJECT_ROOT / "aiko-app"

BANNER = """
    #######  ## ##  ##  ####### 
   ##    ## ## ## ##  ##     ##
   #######  ## ####   ##     ##
   ##    ## ## ## ##  ##     ##
   ##    ## ## ##  ##  ####### 
   >>> Unified Launcher v1.0 <<<
"""

def check_alive(host="127.0.0.1", port=8000, path="/api/status"):
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        conn.request("GET", path)
        resp = conn.getresponse()
        return resp.status == 200
    except:
        return False

def launch():
    os.system("cls" if os.name == "nt" else "clear")
    print(BANNER)
    
    NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

    print("[1/5] Cleaning up stale instances...")
    try:
        subprocess.run('taskkill /F /IM node.exe /T', shell=True, capture_output=True, creationflags=NO_WINDOW, check=False)
        # Avoid killing ourselves
        current_pid = os.getpid()
        subprocess.run(f'taskkill /F /IM python.exe /T /FI "PID ne {current_pid}"', shell=True, capture_output=True, creationflags=NO_WINDOW, check=False)
    except:
        pass

    print("[2/5] Starting Neural Hub (Brain)...")
    hub_log = open(PROJECT_ROOT / ".logs" / "launcher_hub.log", "w")
    subprocess.Popen(
        [str(PYTHON_EXE), str(HUB_SCRIPT)],
        stdout=hub_log, stderr=hub_log,
        creationflags=NO_WINDOW,
        cwd=str(PROJECT_ROOT)
    )

    print("[3/5] Syncing Local Voice Subsystem...")
    # Standalone TTS serve is no longer needed as Hub manages it.
    time.sleep(1)

    print("[4/5] Syncing Neural Link...")
    connected = False
    for i in range(60):
        if check_alive(port=8000):
            connected = True
            break
        time.sleep(1)
        if i % 5 == 0: print(f"      ...waiting for hub ({i}s)")

    if not connected:
        print("[!] ERROR: Neural Hub failed to respond. Check .logs/launcher_hub.log")
        input("Press Enter to exit...")
        return

    print("[5/5] Launching Aiko UI Portal...")
    # Launch Tauri
    subprocess.Popen(
        ["npm", "run", "tauri", "dev"],
        cwd=str(TAURI_DIR),
        shell=True,
        creationflags=NO_WINDOW
    )

    print("\n[SUCCESS] Aiko Ecosystem is now active.")
    print("This window will close in 5 seconds...")
    time.sleep(5)

if __name__ == "__main__":
    launch()
