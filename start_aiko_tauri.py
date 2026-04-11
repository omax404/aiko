import subprocess
import sys
import time
import os
import http.client

def check_llm_alive(host="127.0.0.1", port=11434):
    """Pings the LLM API (Ollama or LM Studio) to confirm it's ready."""
    try:
        # Check Ollama default
        conn = http.client.HTTPConnection(host, 11434, timeout=2)
        conn.request("GET", "/api/tags")
        if conn.getresponse().status == 200: return True
    except: pass
    
    try:
        # Check LM Studio default
        conn = http.client.HTTPConnection(host, 1234, timeout=2)
        conn.request("GET", "/v1/models")
        if conn.getresponse().status == 200: return True
    except: pass
    
    return False

def check_hub_alive(host="127.0.0.1", port=8000):
    """Pings the Neural Hub status endpoint."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/api/status")
        resp = conn.getresponse()
        return resp.status == 200
    except:
        return False

def start_aiko_tauri():
    print("LAUNCHING AIKO TAURI ECOSYSTEM (HERO v3.0)...")

    # Windows: CREATE_NO_WINDOW hides console windows completely
    NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

    # 1. Kill old processes safely
    print(" Cleaning up old instances...")
    try:
        current_pid = os.getpid()
        # Kill python, node, and specific dev ports - check=False to ignore if none exist
        subprocess.run('taskkill /F /IM node.exe /T', shell=True, capture_output=True, creationflags=NO_WINDOW, check=False)
        subprocess.run(f'taskkill /F /IM python.exe /T /FI "PID ne {current_pid}"', shell=True, capture_output=True, creationflags=NO_WINDOW, check=False)
        subprocess.run('taskkill /F /IM ollama.exe /T', shell=True, capture_output=True, creationflags=NO_WINDOW, check=False)
        
        # Kill whatever is on port 1422 (Vite) and 8000 (Unified Hub)
        for port in [1422, 1420, 8000, 8765]:
            cmd = f'powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force -ErrorAction SilentlyContinue"'
            subprocess.run(cmd, shell=True, creationflags=NO_WINDOW, check=False)
            
    except Exception as e:
        print(f" [!] Cleanup warning: {e}")
    time.sleep(2)

    os.makedirs(".logs", exist_ok=True)

    # 1. Start Ollama Serve — ONLY if no LLM is alive yet
    print(" Checking for LLM availability...")
    if check_llm_alive():
        print(" [OK] LLM detected (Ollama or LM Studio). Skipping native serve.")
    else:
        print(" Starting Ollama Serve...")
        ollama_log = open(".logs/ollama.log", "w")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=ollama_log, stderr=ollama_log,
            creationflags=NO_WINDOW
        )
        # Wait for Ollama to be actually ready
        print(" Waiting for Ollama to wake up...")
        ready = False
        for i in range(30):
            if check_llm_alive():
                ready = True
                break
            time.sleep(1)
        if not ready:
            print(" [!] WARNING: No LLM responded in 30s. Neural Hub may fail.")
        else:
            print(" [OK] LLM is now ready.")

    # 2. Start Unified Neural Hub (Port 8000) — hidden, logs to file
    print(" Starting Neural Hub (Brain + Voice)...")
    hub_log = open(".logs/neural_hub.log", "w")
    subprocess.Popen(
        [sys.executable, "core/neural_hub.py"],
        stdout=hub_log, stderr=hub_log,
        creationflags=NO_WINDOW
    )

    # 3. Pocket-TTS is now managed INTERNALLY by the Hub for better stability and pre-warming.
    print(" Syncing Internal Voice Subsystem...")
    time.sleep(1)

    # Wait for Hub to be warm with active polling
    print(" Warming up the neural link (this might take a Few Seconds)...")
    hub_ready = False
    for i in range(120):
        if check_hub_alive(port=8080):
            hub_ready = True
            break
        time.sleep(1)
        # SILENT WAIT

    if not hub_ready:
        print(" [ERROR] CRITICAL: Neural Hub failed to start. Aborting.")
        print(" TIP: Check logs: .logs/neural_hub.log")
        return

    print(" [OK] Neural Link Established.")

    # 3. Start OpenClaw Bridge — hidden
    print(" Starting OpenClaw Bridge (PC Control)...")
    claw_log = open(".logs/openclaw_bridge.log", "w")
    subprocess.Popen(
        [sys.executable, "-m", "core.openclaw_bridge_enhanced"],
        stdout=claw_log, stderr=claw_log,
        creationflags=NO_WINDOW
    )
    time.sleep(1)

    # 4. Satellites are now handled internally by Neural Hub startup.
    # No need to launch them separately here.
    print(" Satellites (Discord/Telegram) managed by Neural Hub.")

    # 5. Launch Tauri — this one gets a visible window (it IS the UI)
    print(" Opening Tauri Hero Dashboard UI...")
    tauri_log = open(".logs/tauri_dev.log", "w")
    subprocess.Popen(
        ["npm", "run", "tauri", "dev"],
        cwd="aiko-app",
        shell=True,
        stdout=tauri_log, stderr=tauri_log,
        creationflags=NO_WINDOW  # npm/vite log to file, Tauri window handles itself
    )

    print("\nALL SYSTEMS GO. (TAURI MODE)")
    print("All background processes are running silently.")
    print("Logs available in .logs/ folder.")
    print("Tauri window will appear shortly (first compile ~3-5 min).")

if __name__ == "__main__":
    start_aiko_tauri()
