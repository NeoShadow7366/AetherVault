# Troubleshooting Guide & Operational Runbook

## Overview
This document covers the built-in error recovery mechanisms and manual troubleshooting steps for the **AetherVault**. Because this system orchestrates multiple heavy external engines (ComfyUI, Forge, etc.) and background threads through a unified UI, failures generally fall into three categories: **Engine Subprocess Failures**, **Database Contention**, or **Filesystem Integrity**.

## The First Step: The Runtime Health Doctor 🩺
Before diving into manual logs, always rely on the built-in AI diagnostics. The system includes a proactive **Runtime Health Doctor** designed to securely observe live operational states.

You can trigger a full infrastructure diagnostic report manually via the chat block or command palette using:
```text
/run_health_check
```
Or simply by asking an agent: *"Doctor, check system health."*

The Doctor will automatically check for:
- Defunct or zombie processes consuming VRAM.
- Broken NTFS Junctions or UNIX symlinks.
- Missing `manifest.json` tracker files for installed engines.
- Database locks blocking the UI.

---

## Common Engine & Subprocess Failures

### 1. The UI Hangs / Proxy Connection Refused
**Symptom:** You clicked "Generate" in the dashboard, but the loading spinner spins indefinitely, or a Toast alert says `URLError: connection refused`.
**Cause:** The target engine you're proxying (e.g., ComfyUI) either crashed silently or failed to boot its internal HTTP server.
**Resolution:**
- If the process died, trigger an auto-detection. The UI polling should recognize the dead app and present a **Repair 🛠️** button.
- Check the engine's `runtime.log` inside `packages/<engine_name>/`. Look specifically for a `ModuleNotFoundError` or `ImportError`.
- If missing dependencies are found, clicking "Repair" or engaging the App Store Installer will run `/api/repair_dependency` to fix the isolated `.venv`.

### 2. Zombie Processes (Out of VRAM Errors)
**Symptom:** You try to launch an engine, but CUDA immediately throws an "Out of Memory" (OOM) error, even though you closed the application.
**Cause:** A previously launched subprocess was orphaned and is still holding onto GPU memory in the background.
**Resolution:**
- Run `/run_health_check`. The Doctor will flag the PID.
- **Windows:** Run `taskkill /F /FI "IMAGENAME eq python.exe"` (careful not to kill the Manager itself, look for the engine's specific `.venv` Python path).
- **macOS/Linux:** Find the PID with `ps aux | grep python` and terminate it natively using `kill -9 <PID>`.

### 3. Missing Models in the App (Junction Failure)
**Symptom:** Your models are in `Global_Vault/` but the engine (like Fooocus) says "Model not found."
**Cause:** The zero-byte NTFS Junction (or symlink) mapping `Global_Vault` down into the `packages/<engine_name>/models/` directory was broken or deleted.
**Resolution:**
- Restart the Manager via `start_manager.bat/sh`. The bootstrap script and **Global Vault Symlinker** natively perform a pre-flight check and will auto-recreate missing junctions.

---

## Database & Locking Failures

The `metadata.sqlite` database handles caching CivitAI text, storing the inference gallery, and background thread logic.

### 1. SQLite "database is locked"
**Symptom:** The terminal prints `sqlite3.OperationalError: database is locked`.
**Cause:** The background `vault_crawler.py` is hashing a massive 6GB checkpoint and locked the write thread while the UI tried to save a generation parameter.
**Resolution:**
- The backend features an automatic 500ms backoff-retry loop (up to 5 attempts).
- If it persists infinitely, restart the manager. Do not try to write to the DB externally.

### 2. Database Schema Mismatches
**Symptom:** Errors trying to track new variables natively inside the My Creations Gallery.
**Cause:** Software updates modified the tables. 
**Resolution:**
- The OTA Ghost Updater uses safe `ALTER TABLE` commands. Do not delete the database. Use `python check_db.py` to print existing schema rows and verify data integrity safely.

---

## Log Checkpoints
If you need to investigate further manually, log files are located natively in the following spots:
- `launcher.log` - Base OS bootstrap and startup logs.
- `packages/<engine_name>/runtime.log` - The standard output from the individual engines. 
- Terminal Window - Holds the real-time Python HTTP routing events.

---

## Download & Import Failures

### 1. Download Stalls at 0% or Fails Immediately
**Symptom:** You initiate a model download from CivitAI, but progress stays at 0% or the Toast shows an error immediately.
**Cause:** The CivitAI API key is missing or expired, the model requires authentication, or the URL contains special characters that weren't encoded.
**Resolution:**
- Verify your CivitAI API key is set in **Settings → API Keys**.
- Check `.backend/cache/downloads.json` for the exact error message.
- For gated models (early access), ensure your API key has the required permissions on CivitAI.

### 2. Import Fails During Hashing
**Symptom:** A drag-and-drop import gets stuck at "Computing SHA-256 hash..." or fails with a file access error.
**Cause:** The source file is locked by another process, or the destination vault directory doesn't exist.
**Resolution:**
- Ensure no other application (Finder/Explorer preview, antivirus scan) has the file locked.
- Verify the target `Global_Vault/<category>/` directory exists and is writable.
- Check the server terminal for `Hash failed for <path>` log entries.

### 3. Import Succeeds but No CivitAI Metadata Found
**Symptom:** The import completes with "Import complete (no metadata). Model not found on CivitAI."
**Cause:** The model was never uploaded to CivitAI, or the file was modified post-download (changing the hash).
**Resolution:** This is expected for local-only models. The model is still fully functional — it simply won't have a thumbnail, description, or version tracking.

---

## Extension & Installation Failures

### 1. Extension Installation Hangs
**Symptom:** An extension install progress bar appears infinite, or the status never changes from "installing."
**Cause:** The Git clone or pip install subprocess may have stalled waiting for user input (SSH key prompt, large repository).
**Resolution:**
- Check `packages/<engine>/runtime.log` for Git or pip output.
- Ensure Git is installed and configured for HTTPS (not SSH) cloning.
- Cancel the install via `POST /api/extensions/cancel` and retry.

---

## Network & Port Failures

### 1. Port 8080 Already In Use
**Symptom:** The server fails to start with `OSError: [Errno 98] Address already in use` (Linux/macOS) or `OSError: [WinError 10048]` (Windows).
**Cause:** Another instance of the manager, or a different application, is already bound to port 8080.
**Resolution:**
- **Windows:** `netstat -aon | findstr :8080` to find the conflicting PID, then `taskkill /PID <PID> /F`.
- **macOS/Linux:** `lsof -i :8080` to identify the process, then `kill -9 <PID>`.
- If running the tray launcher, the singleton mutex should prevent duplicate instances automatically.

### 2. CORS Issues Behind a Reverse Proxy
**Symptom:** API calls fail with CORS errors when accessing the dashboard through a reverse proxy (e.g., nginx, Caddy).
**Cause:** The reverse proxy may strip or override the `Access-Control-Allow-Origin` headers that `server.py` sets automatically.
**Resolution:**
- Ensure your reverse proxy passes through the CORS headers set by the backend.
- The backend already sends `Access-Control-Allow-Origin: *` on all API responses. If your proxy adds its own CORS headers, they may conflict.

---

## Update & Maintenance Failures

### 1. OTA Update Fails Mid-Patch
**Symptom:** The dashboard shows "Update available" but clicking "Update" results in an error or partial update.
**Cause:** Git is not installed, the `.git` directory was removed, or the network dropped during the patch.
**Resolution:**
- Verify Git is installed: `git --version`.
- Ensure the project directory is a valid Git repository: `git status`.
- If the `.git` directory was lost (e.g., from a ZIP distribution), OTA updates cannot function. Re-clone the repository.
- User data (`Global_Vault/`, `packages/`, `settings.json`, `metadata.sqlite`) is never touched by updates.

### 2. Embedding Engine Crash Recovery
**Symptom:** Semantic search returns no results, or the embedding engine process crashes on startup with a `ModuleNotFoundError`.
**Cause:** The `sentence-transformers` package or its PyTorch dependency may be corrupted.
**Resolution:**
- Re-install the base dependencies: `bin/python/python -m pip install --force-reinstall sentence-transformers torch`.
- Check if the embedding model cache is corrupted by deleting `~/.cache/huggingface/` and restarting.
- The embedding engine runs as a daemon process — restarting the manager will automatically respawn it.
