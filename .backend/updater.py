import os
import sys
import subprocess
import time
import logging
import argparse
import signal

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def force_kill_pid(pid):
    """Attempt to force-terminate the parent server process to release OS file locks."""
    if pid <= 0: return
    logging.info(f"Attempting to terminate Server PID: {pid}")
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        time.sleep(2) # Give OS time to drop file locks
        logging.info("Parent process terminated successfully.")
    except Exception as e:
        logging.warning(f"Failed to kill PID {pid}: {e}. OS file locks may still persist.")

def fetch_and_extract_release(root_dir):
    """Fallback logic to download from a GitHub Release Zip explicitly omitting user directories."""
    import urllib.request
    import zipfile
    import shutil
    
    # Placeholder repo logic. In production this would be: 
    # repo_url = "https://github.com/YourOwner/AIManager/archive/refs/heads/main.zip"
    repo_url = "https://github.com/mock-ai-manager/archive/refs/heads/main.zip"
    tmp_zip = os.path.join(root_dir, ".backend", "latest_update.zip")
    extract_dir = os.path.join(root_dir, ".backend", "update_stage")
    
    logging.info(f"Downloading latest standalone release from {repo_url}...")
    try:
        # Mocking the download since this is a local project without a remote yet
        # urllib.request.urlretrieve(repo_url, tmp_zip)
        logging.info("[MOCK] Download complete. Simulating extraction...")
        
        # MOCK EXTRACTION LOGIC
        # with zipfile.ZipFile(tmp_zip, 'r') as zip_ref:
        #     zip_ref.extractall(extract_dir)
            
        # MOCK COPY OVER: We explicitly ignore replacing these core user-persistent directories
        ignore_dirs = {"Global_Vault", "packages", "cache", "metadata.sqlite", "settings.json"}
        
        # for item in os.listdir(extract_dir):
        #    if item in ignore_dirs: continue
        #    src = os.path.join(extract_dir, item)
        #    dst = os.path.join(root_dir, item)
        #    if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True)
        #    else: shutil.copy2(src, dst)
            
        logging.info("[MOCK] Codebase patch applied successfully!")
    except Exception as e:
        logging.error(f"Standalone update extraction failed: {e}")
    finally:
        if os.path.exists(tmp_zip): os.remove(tmp_zip)
        if os.path.exists(extract_dir): shutil.rmtree(extract_dir, ignore_errors=True)


def run_update(pid):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging.info(f"Applying System Updates in {root_dir}...")
    
    force_kill_pid(pid)
    
    try:
        git_dir = os.path.join(root_dir, ".git")
        if os.path.exists(git_dir):
            logging.info("Git repository detected. Executing 'git pull'...")
            res = subprocess.run(["git", "pull"], cwd=root_dir, capture_output=True, text=True)
            if res.returncode != 0:
                logging.error(f"Git pull failed: {res.stderr}")
            else:
                logging.info(res.stdout)
                logging.info("Git patch applied successfully!")
        else:
            logging.info("Standalone installation detected. Executing Zip patching...")
            fetch_and_extract_release(root_dir)
    except Exception as e:
        logging.error(f"System update failed: {e}")

    logging.info("Update logic finished gracefully. Re-launching AI Manager...")
    
    # OS-Agnostic restart mechanics
    try:
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
            bootstrapper = os.path.join(root_dir, "start_manager.bat")
        else:
            bootstrapper = os.path.join(root_dir, "start_manager.sh")
            
        if os.path.exists(bootstrapper):
            # Unhook completely from the current context and fire the dash
            subprocess.Popen([bootstrapper], cwd=root_dir, shell=True, **kwargs)
        else:
            logging.error("Bootstrapper not found! Please restart the server manually.")
    except Exception as e:
         logging.error(f"Failed to auto-restart: {e}")

    logging.info("Updater daemon terminating cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Manager System Updater")
    parser.add_argument("--pid", type=int, default=0, help="Process ID of the parent server to terminate")
    args = parser.parse_args()
    
    run_update(args.pid)
