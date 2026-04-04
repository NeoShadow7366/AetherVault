# Troubleshooting Guide & Operational Runbook

## Overview
This document covers the built-in error recovery mechanisms and manual troubleshooting steps for the **Antigravity Manager**. Because this system orchestrates multiple heavy external engines (ComfyUI, Forge, etc.) and background threads through a unified UI, failures generally fall into three categories: **Engine Subprocess Failures**, **Database Contention**, or **Filesystem Integrity**.

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
