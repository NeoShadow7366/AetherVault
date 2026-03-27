---
description: Data safety rules protecting user files, database integrity, and settings from corruption or loss
---

# Data Safety Rules

User data is **sacred**. These rules protect against accidental deletion, corruption, or overwrite.

## Sacred Files (NEVER delete without explicit user consent)

| Path | Contains | Protected By |
|------|----------|-------------|
| `Global_Vault/` | All user model files (safetensors, ckpt, pt) | Gitignored, excluded from OTA updates |
| `packages/` | Installed apps + isolated venvs | Gitignored, excluded from OTA updates |
| `.backend/metadata.sqlite` | Model registry, gallery, embeddings, tags | Gitignored, excluded from OTA updates |
| `.backend/settings.json` | API keys, theme preference, user config | Gitignored, excluded from OTA updates |
| `.backend/cache/thumbnails/` | Cached CivitAI preview images | Gitignored |
| `bin/python/` | Portable Python installation | Gitignored |

## Database Safety

### Transaction Boundaries
```python
# ✅ CORRECT — atomic operations
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('INSERT INTO ...', params)
conn.commit()  # Explicit commit
conn.close()   # Always close

# ❌ FORBIDDEN — no commit, leaked connection
conn = sqlite3.connect(db_path)
conn.execute('UPDATE ...', params)
# Missing: conn.commit() and conn.close()
```

### Schema Migration
```python
# ✅ CORRECT — backward-compatible ALTER TABLE
try:
    cursor.execute("ALTER TABLE models ADD COLUMN update_available INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass  # Column already exists — safe to ignore
```

### Concurrent Access
- SQLite is single-writer. Multiple readers are safe.
- If "database is locked" errors occur, retry with 500ms backoff, max 5 attempts.
- Consider enabling WAL mode for concurrent read/write patterns.

## File Deletion Rules

| Operation | Requires User Intent? | Implementation |
|-----------|-----------------------|----------------|
| Delete model from Vault | ✅ Yes — via `/api/delete_model` | `os.remove()` + DB cleanup |
| Delete gallery entry | ✅ Yes — via `/api/gallery/delete` | DB record only, NOT the image file |
| Uninstall package | ✅ Yes — via `/api/uninstall` | `shutil.rmtree()` on package dir |
| Clear downloads | ✅ Yes — via `/api/downloads/clear` | Removes `downloads.json` only |
| Repair broken symlinks | ⚠️ Automatic | `os.unlink()` on broken links only |

## OTA Update Protection

The update pipeline in `updater.py` and `build.py` maintains an explicit ignore list. Any new user-data directory **MUST** be added to both:

```python
# updater.py — fetch_and_extract_release()
ignore_dirs = {"Global_Vault", "packages", "cache", "metadata.sqlite", "settings.json"}

# build.py — create_release_build()
ignore_dirs = {"bin", "packages", "dist", ".git", "__pycache__", "cache", ".gemini"}
# + Global_Vault is added as empty skeleton stubs
```

## Backup Strategy

Currently not implemented. Future consideration:
- Daily SQLite backup to `.backend/cache/metadata_backup.sqlite`
- Settings snapshot before OTA updates
- Never backup Global_Vault (too large) — rely on user's own backup strategy
