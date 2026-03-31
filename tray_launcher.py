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
import tarfile
import platform
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
    if os.name != 'nt':
        log_msg("Mutex skipped (POSIX gracefully bypasses ctypes windll).")
        return

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
    if mutex_handle and os.name == 'nt':
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


def download_portable_python(base_path):
    import tkinter as tk
    from tkinter import ttk

    bin_dir = os.path.join(base_path, "bin")
    os_name = platform.system().lower()
    arch_name = platform.machine().lower()

    if os_name == "windows":
        url = "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-pc-windows-msvc-shared-install_only.tar.gz"
    elif os_name == "darwin":
        if arch_name in ["arm64", "aarch64"]:
            url = "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-apple-darwin-install_only.tar.gz"
        else:
            url = "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-apple-darwin-install_only.tar.gz"
    else:  # linux
        if arch_name in ["arm64", "aarch64"]:
            url = "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-unknown-linux-gnu-install_only.tar.gz"
        else:
            url = "https://github.com/indygreg/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-x86_64-unknown-linux-gnu-install_only.tar.gz"

    tar_path = os.path.join(bin_dir, "python.tar.gz")
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(os.path.join(base_path, "Global_Vault"), exist_ok=True)
    os.makedirs(os.path.join(base_path, "packages"), exist_ok=True)

    root = tk.Tk()
    root.title("Antigravity Toolkit Setup")
    root.geometry("480x280")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#1A1B26")  # Premium Dark Navy background
    
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (480 // 2)
    y = (root.winfo_screenheight() // 2) - (280 // 2)
    root.geometry(f"+{x}+{y}")

    status_var = tk.StringVar(root, value="Initializing first-time setup...")
    
    # Try rendering the Logo gracefully
    icon_path = get_bundled_resource("logo.ico")
    
    try:
        # Add the native window corner icon (can fail on POSIX)
        root.iconbitmap(icon_path)
    except Exception:
        pass

    try:
        from PIL import Image, ImageTk
        # Render the huge splash image prominently
        if os.path.exists(icon_path):
            img = Image.open(icon_path).resize((72, 72), Image.Resampling.LANCZOS)
            logo_img = ImageTk.PhotoImage(img)
            logo_lbl = tk.Label(root, image=logo_img, bg="#1A1B26")
            logo_lbl.image = logo_img  # Reference to prevent garbage collection
            logo_lbl.pack(pady=(25, 0))
    except Exception:
        pass
    
    # Text Titles and Status Elements
    tk.Label(
        root, text="Downloading Portable Architecture",
        font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg="#1A1B26"
    ).pack(pady=(15, 5))
    
    lbl_status = tk.Label(
        root, textvariable=status_var,
        font=("Segoe UI", 10), fg="#A9B1D6", bg="#1A1B26"
    )
    lbl_status.pack(pady=(0, 20))

    # Themed Progress Bar
    style = ttk.Style(root)
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    style.configure("TProgressbar", thickness=15, background="#9d4edd", troughcolor="#24283b")

    progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
    progress.pack(pady=(0, 20))

    def run_download():
        try:
            status_var.set("Connecting to remote architecture...")
            root.update_idletasks()
            root.update()
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(tar_path, 'wb') as out_file:
                total_size_str = response.getheader('Content-Length')
                total_size = int(total_size_str.strip()) if total_size_str else 0
                downloaded = 0
                chunk_size = 1024 * 64  # 64KB for ultra-smooth UI updates (guaranteed ticks)
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        progress['value'] = percent
                        # Lively updating string with dynamic decimals
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        status_var.set(f"Receiving Payload... {mb_down:.1f} MB / {mb_total:.1f} MB ({percent}%)")
                    else:
                        mb_down = downloaded / (1024 * 1024)
                        status_var.set(f"Receiving Payload... {mb_down:.1f} MB")
                    
                    root.update_idletasks()
                    root.update()

            status_var.set("Decompressing Engine... Please wait.")
            progress.config(mode="indeterminate")
            progress.start(12)
            root.update()
            
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=bin_dir)
            os.remove(tar_path)
            
            progress.stop()
            progress.config(mode="determinate")
            progress['value'] = 100
            
            status_var.set("Installing Base Dependencies... (1/3)")
            root.update()
            
            python_exe_path = os.path.join(bin_dir, "python", "python.exe") if os_name == "windows" else os.path.join(bin_dir, "python", "bin", "python3")
            if os_name != "windows":
                os.chmod(python_exe_path, 0o755)
            
            popen_kwargs = {'creationflags': 0x08000000} if os_name == "windows" else {}
            
            # Setup pip
            subprocess.run([python_exe_path, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=True, **popen_kwargs)
            
            status_var.set("Installing AI Engine PyTorch... (2/3)")
            root.update()
            subprocess.run([python_exe_path, "-m", "pip", "install", "torch", "torchvision", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True, **popen_kwargs)
            
            status_var.set("Installing Semantic Core... (3/3)")
            root.update()
            subprocess.run([python_exe_path, "-m", "pip", "install", "sentence-transformers"], check=True, **popen_kwargs)

            status_var.set("Setup Complete! Starting Server...")
            root.update()
            time.sleep(1.5)
            
        except Exception as e:
            log_msg(f"Downloader Error: {e}")
            status_var.set(f"Error: {e}")
            root.update()
            time.sleep(5)
        finally:
            root.destroy()
            
    root.after(500, run_download)
    root.mainloop()


def start_server():
    global server_process, server_log_file
    base_path = get_base_path()
    
    # Auto-bootstrap if python is missing
    python_exe_candidates = [
        os.path.join(base_path, "bin", "python", "python.exe"),
        os.path.join(base_path, "bin", "python", "bin", "python3")
    ]
    
    python_exe = next((p for p in python_exe_candidates if os.path.exists(p)), None)
    
    if not python_exe:
        log_msg("Portable python not found. Deploying Native UI Bootstrapper...")
        download_portable_python(base_path)
        
        # Check again after download
        python_exe = next((p for p in python_exe_candidates if os.path.exists(p)), None)
        
        if not python_exe:
            log_msg("CRITICAL WARNING: Auto-bootstrap failed. Yielding to extreme fallback.")
            if getattr(sys, 'frozen', False):
                python_exe = "python"
            else:
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

        popen_kwargs = {}
        if os.name == 'nt':
            popen_kwargs['creationflags'] = CREATE_NO_WINDOW

        server_process = subprocess.Popen(
            [python_exe, server_script],
            env=os.environ.copy(),
            stdout=server_log,
            stderr=subprocess.STDOUT,
            **popen_kwargs
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
            log_msg(f"Fallback kill on server PID {server_process.pid}")
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/T', '/F', '/PID', str(server_process.pid)],
                                    creationflags=0x08000000)
                else:
                    server_process.kill()
                time.sleep(1.5)
            except Exception as e:
                log_msg(f"Primary fallback kill failed: {e}")

        # === EXTRA SAFETY SWEEPS (run even after "graceful" exit) ===
        log_msg("Running final cleanup sweeps for orphaned python processes...")

        base_path = get_base_path()
        base_name = os.path.basename(base_path)

        # Sweep 1: Specific to embedding_engine.py (the stubborn one)
        try:
            if os.name == 'nt':
                log_msg("Sweeping for embedding_engine.py processes...")
                subprocess.call(
                    'wmic process where "name=\'python.exe\' and commandline like \'%embedding_engine.py%\'" call terminate',
                    creationflags=0x08000000,
                    shell=True
                )
            else:
                log_msg("Sweeping for embedding_engine.py processes (POSIX)...")
                subprocess.call(['pkill', '-f', 'embedding_engine.py'])
            time.sleep(1.0)
        except Exception as e:
            log_msg(f"Embedding sweep failed: {e}")

        # Sweep 2: Broad sweep using app folder name (catches embedding + any other detached children)
        try:
            if os.name == 'nt':
                log_msg(f"Sweeping for any python.exe containing '{base_name}'...")
                subprocess.call(
                    f'wmic process where "name=\'python.exe\' and commandline like \'%{base_name}%\'" call terminate',
                    creationflags=0x08000000,
                    shell=True
                )
            else:
                log_msg(f"Sweeping for any python.exe containing '{base_name}' (POSIX)...")
                subprocess.call(['pkill', '-f', base_name])
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