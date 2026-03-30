import os
import sys
import time
import ctypes
import subprocess
import webbrowser
import urllib.request
import urllib.error
import threading
import atexit
from PIL import Image
import pystray
from pystray import MenuItem as item

SERVER_URL = "http://localhost:8080"
SHUTDOWN_URL = f"{SERVER_URL}/api/shutdown"
LOG_FILE = "launcher.log"

# Globals
server_process = None
server_log_file = None
mutex_handle = None


def log_msg(msg: str):
    try:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass


def acquire_mutex():
    global mutex_handle
    mutex_name = "AntigravityLauncherMutex_Prod_v1"
    mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        log_msg("Instance already running. Opening dashboard.")
        try:
            webbrowser.open(SERVER_URL)
        except Exception:
            pass
        sys.exit(0)
    log_msg("Mutex acquired successfully.")


def release_mutex():
    global mutex_handle
    if mutex_handle:
        try:
            ctypes.windll.kernel32.CloseHandle(mutex_handle)
        except Exception:
            pass
        mutex_handle = None


atexit.register(release_mutex)


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_bundled_resource(relative_path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def start_server():
    global server_process, server_log_file
    base_path = get_base_path()
    python_exe = os.path.join(base_path, "bin", "python", "python.exe")
    if not os.path.exists(python_exe):
        log_msg("WARNING: Portable python not found. Using system python.")
        python_exe = sys.executable

    CREATE_NO_WINDOW = 0x08000000
    server_script = os.path.join(base_path, ".backend", "server.py")

    if not os.path.exists(server_script):
        log_msg("CRITICAL ERROR: server.py not found!")
        sys.exit(1)

    log_msg(f"Launching server.py from {server_script}")

    # Create logs directory
    log_dir = os.path.join(base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "server.log")

    try:
        # Open log with line buffering
        server_log = open(log_path, "a", encoding="utf-8", buffering=1)

        server_process = subprocess.Popen(
            [python_exe, server_script],
            creationflags=CREATE_NO_WINDOW,
            env=os.environ.copy(),
            stdout=server_log,
            stderr=subprocess.STDOUT
        )

        log_msg(f"Server started with PID {server_process.pid} (logging to {log_path})")
        server_log_file = server_log

    except Exception as e:
        log_msg(f"Failed to start server or open log: {e}")
        if 'server_log' in locals() and not server_log.closed:
            server_log.close()
        sys.exit(1)


def wait_and_open_browser():
    log_msg("Waiting for Antigravity server to start on http://localhost:8080...")
    max_wait_seconds = 30
    start_time = time.time()
    time.sleep(1.5)

    while time.time() - start_time < max_wait_seconds:
        try:
            response = urllib.request.urlopen(SERVER_URL, timeout=2.0)
            if response.getcode() == 200:
                log_msg("Server is ready. Opening browser.")
                webbrowser.open(SERVER_URL)
                return
        except urllib.error.URLError:
            pass  # normal during startup
        except Exception as e:
            log_msg(f"Polling warning: {e}")

        time.sleep(1.0)

    log_msg("Server took longer than expected. Opening browser anyway.")
    webbrowser.open(SERVER_URL)


def open_dashboard(icon, item):
    webbrowser.open(SERVER_URL)

def quit_app(icon, item):
    global server_process, server_log_file
    log_msg("Quit requested from tray.")
    icon.stop()

    # Close server log handle cleanly
    if server_log_file:
        try:
            server_log_file.close()
            log_msg("Server log file closed.")
        except Exception as e:
            log_msg(f"Warning closing server log: {e}")
        server_log_file = None

    if server_process and server_process.poll() is None:
        try:
            log_msg("Sending /api/shutdown request to server...")
            req = urllib.request.Request(SHUTDOWN_URL, method="POST")
            urllib.request.urlopen(req, timeout=5)
            log_msg("Shutdown request sent successfully. Waiting for graceful exit...")

            # Wait for server graceful shutdown (including embedding kill inside teardown)
            try:
                server_process.wait(timeout=22)
                log_msg("Server exited gracefully.")
            except subprocess.TimeoutExpired:
                log_msg("Graceful wait timed out after 22s. Proceeding to fallback kill.")

        except Exception as e:
            log_msg(f"Shutdown request failed: {e}")

        # === PRIMARY FALLBACK: Kill main server process tree ===
        if server_process.poll() is None:
            log_msg(f"Fallback taskkill on server PID {server_process.pid}")
            try:
                subprocess.call(['taskkill', '/T', '/F', '/PID', str(server_process.pid)],
                                creationflags=0x08000000)
                time.sleep(1.5)
            except Exception as e:
                log_msg(f"Primary taskkill failed: {e}")

        # === EXTRA SAFETY SWEEPS (run even after "graceful" exit) ===
        log_msg("Running final cleanup sweeps for orphaned python processes...")

        base_path = get_base_path()
        base_name = os.path.basename(base_path)

        # Sweep 1: Specific to embedding_engine.py (the stubborn one)
        try:
            log_msg("Sweeping for embedding_engine.py processes...")
            subprocess.call(
                'wmic process where "name=\'python.exe\' and commandline like \'%embedding_engine.py%\'" call terminate',
                creationflags=0x08000000,
                shell=True
            )
            time.sleep(1.0)
        except Exception as e:
            log_msg(f"Embedding sweep failed: {e}")

        # Sweep 2: Broad sweep using app folder name (catches embedding + any other detached children)
        try:
            log_msg(f"Sweeping for any python.exe containing '{base_name}'...")
            subprocess.call(
                f'wmic process where "name=\'python.exe\' and commandline like \'%{base_name}%\'" call terminate',
                creationflags=0x08000000,
                shell=True
            )
            time.sleep(1.0)
        except Exception as e:
            log_msg(f"Broad base-path sweep failed: {e}")

        # Sweep 3: Final force kill on server process if still alive
        if server_process.poll() is None:
            try:
                log_msg("Final force kill on server process...")
                server_process.kill()
            except Exception:
                pass

    sys.exit(0)

if __name__ == "__main__":
    acquire_mutex()
    log_msg("=== Antigravity Launcher Started ===")

    start_server()
    threading.Thread(target=wait_and_open_browser, daemon=True).start()

    menu = pystray.Menu(
        item('Open Antigravity Dashboard', open_dashboard, default=True),
        item('Quit Application', quit_app)
    )

    icon_path = get_bundled_resource("logo.ico")
    if os.path.exists(icon_path):
        target_img = Image.open(icon_path)
    else:
        log_msg("logo.ico not found - using generic icon")
        target_img = Image.new('RGB', (64, 64), color=(43, 43, 43))

    icon = pystray.Icon("Antigravity", target_img, "Antigravity AI Manager", menu)
    icon.run()