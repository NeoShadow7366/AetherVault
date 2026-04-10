---
name: OTA Ghost Updater
description: Self-healing over-the-air update system that kills the running server process, applies code patches via git pull or zip extraction while preserving all user data (Global_Vault, packages, settings, database), and restarts the dashboard automatically.
keywords:
  - update
  - OTA
  - git pull
  - self-healing
  - restart
  - sacred files
---

# OTA Ghost Updater

## Purpose

Apply codebase updates to the AI Manager without touching user data. The updater "ghosts" the running server — kills it, patches files, and relaunches — all in a single automated sequence triggered by one button click.

## When to Use

```
IF the task involves:
  ├── Implementing the "Update System" button logic       → USE THIS SKILL
  ├── Modifying the git pull or zip patch pipeline         → USE THIS SKILL
  ├── Changing which files are preserved vs. overwritten   → USE THIS SKILL
  ├── Fixing auto-restart after update                     → USE THIS SKILL
  ├── Adding pre/post update hooks                         → USE THIS SKILL
  └── Anything else                                        → DO NOT USE THIS SKILL
```

## Update Pipeline

```
[1] User clicks "Update System" in Settings tab
    │
    ▼
[2] POST /api/system/update → spawns updater.py as detached subprocess
    │
    ▼
[3] updater.py receives --pid of the parent server process
    │
    ▼
[4] force_kill_pid() → taskkill /F /PID (Windows) or SIGTERM (UNIX)
    │    Wait 2s for file lock release
    ▼
[5] Detect update source:
    ├── .git/ exists → git pull
    └── No .git/    → Download + extract zip from GitHub Release
    │
    ▼
[6] SACRED FILES (NEVER OVERWRITE):
    ├── Global_Vault/       ← All user model files
    ├── packages/           ← All installed apps + venvs
    ├── .backend/cache/     ← Thumbnails + download progress
    ├── metadata.sqlite     ← Complete model database
    ├── settings.json       ← User preferences + API keys
    └── bin/                ← Portable Python binaries
    │
    ▼
[7] Auto-restart:
    ├── Windows → start_manager.bat via Popen(shell=True)
    └── UNIX    → start_manager.sh via Popen
    │
    ▼
[8] Updater daemon exits cleanly
```

## Input Contract

### API Trigger
```
POST /api/system/update
Body: {} (empty)
```

### Updater CLI
```bash
python updater.py --pid <server_process_id>
```

## Output Contract

### API Response (immediate)
```json
{
  "status": "success",
  "message": "Applying System Update. The server may restart..."
}
```

### Updater Exit
- Logs all steps to stdout
- Returns exit code 0 on success
- The server will be briefly unavailable (< 10s) during the patch

## Key Implementation Files

| File | Role |
|------|------|
| `.backend/updater.py` | Core update daemon — kill, patch, restart |
| `.backend/server.py` → `handle_system_update()` | API endpoint that spawns updater |
| `start_manager.bat` | Windows restart target |
| `start_manager.sh` | UNIX restart target |
| `build.py` | Creates the release zip with proper exclusions |

## Sacred File Protection

The update system uses an **explicit ignore list**. Files NOT on this list are candidates for overwrite. This is a critical security boundary.

```python
ignore_dirs = {"Global_Vault", "packages", "cache", "metadata.sqlite", "settings.json"}
```

> **WARNING:** If a new user-data directory is added to the project, it MUST be added to this ignore list in BOTH `updater.py` AND `build.py`.

## Safety Checklist

- [ ] `force_kill_pid()` must validate PID > 0 before killing
- [ ] Never run git commands with user-controlled input
- [ ] Zip extraction must verify file paths for zip-slip vulnerabilities
- [ ] The ignore list in `updater.py` and `build.py` must stay in sync
- [ ] Always use `CREATE_NEW_PROCESS_GROUP` for the updater subprocess on Windows
- [ ] If restart fails, log clearly and instruct user to restart manually
- [ ] Temporary download/extraction files must be cleaned up in `finally` blocks
