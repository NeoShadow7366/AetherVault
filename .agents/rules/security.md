---
description: Security rules for symlinks, subprocess management, API key handling, and path traversal prevention
---

# Security Rules

These rules are **non-negotiable** and apply to every code change in the project.

## 1. Path Traversal Prevention

All static file serving and file access operations must validate paths:

```python
# REQUIRED on every file-serving endpoint
if ".." in path:
    self.send_error(403, "Forbidden")
    return
```

Additionally, any user-provided path must be resolved to an absolute path and validated to be within the project root:

```python
resolved = os.path.abspath(user_path)
if not resolved.startswith(os.path.abspath(root_dir)):
    raise ValueError("Path outside project root")
```

## 2. Subprocess Injection Prevention

**NEVER** use `shell=True` with any user-controlled input:

```python
# ✅ CORRECT — list form
subprocess.run(["git", "clone", repo_url, target_dir], check=True)

# ❌ FORBIDDEN — shell form with user input
subprocess.run(f"git clone {repo_url}", shell=True)
```

The only exception is `start_manager.bat/sh` restart, which uses a controlled, hardcoded path.

## 3. API Key Protection

- API keys are stored in `.backend/settings.json` (gitignored)
- Keys must **never** appear in:
  - Log output (`logging.info/error`)
  - Error response bodies (`send_json_response`)
  - Exception messages surfaced to the UI
  - Git-committed files

```python
# ✅ CORRECT
logging.info(f"Fetching metadata for hash {file_hash[:8]}")

# ❌ FORBIDDEN
logging.info(f"Using API key: {api_key}")
```

## 4. SQLite Injection Prevention

**ALL** database queries must use parameterized placeholders:

```python
# ✅ CORRECT
cursor.execute('SELECT * FROM models WHERE file_hash = ?', (file_hash,))

# ❌ FORBIDDEN
cursor.execute(f'SELECT * FROM models WHERE file_hash = "{file_hash}"')
```

## 5. Symlink Target Validation

Before creating any symlink or junction:

```python
source_dir = os.path.abspath(source_dir)
target_link = os.path.abspath(target_link)
# Both must resolve to paths within or adjacent to project root
```

## 6. Download URL Validation

When downloading from CivitAI or HuggingFace:
- Only allow `https://` URLs
- Validate hostname against an allowlist (`civitai.com`, `huggingface.co`, `github.com`)
- Never follow redirects to `file://` or `ftp://` schemes

## 7. Process Isolation

- All spawned subprocesses must use `CREATE_NEW_PROCESS_GROUP` on Windows
- PIDs must be tracked in `AIWebServer.running_processes`
- Orphan processes must be detected and killed on server shutdown
