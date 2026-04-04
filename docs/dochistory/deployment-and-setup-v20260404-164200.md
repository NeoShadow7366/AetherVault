# Antigravity Manager: Deployment and Setup

## Overview
This document outlines the zero-friction installation and deployment process for the Antigravity Manager. Designed around the *Anti-Gravity* principle of zero-dependency bloat, the manager self-bootstraps using a portable, standalone Python installation. It requires no administrator privileges, no Node.js installations, and no system-wide Python modifications.

## Prerequisites
- **Operating System:** Windows 10/11, macOS (Intel/Silicon), or Linux (x86_64, aarch64)
- **Disk Space:** ~200MB for the manager core + additional space for downloaded generative models.
- **Git** (Optional, but recommended for OTA updates and App Store repository cloning).
- **Network Connection:** Required for the first run to download the portable Python binary and `sentence-transformers` dependencies.

## Installation Process

The installation scripts automatically download `python-build-standalone`, extract it locally to the `bin/` directory, create necessary system folders, and install minimal semantic search dependencies within an isolated space. 

### Windows Setup
Open a command prompt or double-click the included batch script from the project root:
```batch
install.bat
```
This script handles the `curl` download of the Windows MSVC x86_64 Python binary, extracts it natively using `tar`, installs Torch (CPU only), `sentence-transformers`, and automatically triggers `.backend/bootstrap.py` for finalizing setups.

### macOS & Linux (UNIX) Setup
Open your terminal and run the shell script:
```bash
chmod +x install.sh
./install.sh
```
The script dynamically detects your OS (Darwin vs. Linux) and Architecture (`arm64`/`aarch64` vs. `x86_64`) via `uname -m`, requesting the precise `python-build-standalone` tarball matching your hardware.

## Launching the Manager

Once installed, use the start scripts to initialize the web dashboard and its background services. 

### Windows
```batch
start_manager.bat
```

### macOS & Linux
```bash
./start_manager.sh
```

**Boot Sequence Details:**
1. **Python Path Resolution:** Checks if the local portable Python exists in `bin/python/`. If not, it gracefully degrades to using the system `python/python3` installation.
2. **Background Scanner:** Spawns `.backend/embedding_engine.py` as an asynchronous background task (`start /B` or `nohup`) to handle high-speed semantic searches for models.
3. **Web UI Launch:** Opens `http://localhost:8080` in your default browser natively.
4. **Server Initialization:** Binds the zero-dependency `http.server.ThreadingHTTPServer` component found in `.backend/server.py` to the foreground shell to print live access logs.

> [!WARNING]
> Keep the terminal window open while using the application. Closing it will terminate the backend HTTP server and halt any generation proxies in the UI.

## Directory Initialization Defaults

During the first run of `install`, the system ensures three critical infrastructure directories exist safely at the root:
- `bin/` - Houses the standalone Python runtime, preventing PyTorch conflicts with other tools.
- `Global_Vault/` - The master storage folder where you place all your models (Safetensors, LoRAs).
- `packages/` - Sandboxed destination for underlying inference engines downloaded via the App Store.
