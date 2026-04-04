# Model Download Pipeline

## Overview
The Model Download Pipeline provides a background-safe mechanism for downloading generative AI model files from external sources (CivitAI, HuggingFace) directly into the `Global_Vault/`. It features real-time progress tracking via a JSON status file, automatic auth-header stripping on redirects to prevent credential leaks to CDN servers, and post-download vault crawler spawning to immediately register new assets in the SQLite database.

## Key Features / User Flows
- **One-Click Downloads**: Users browse models in the CivitAI Explorer or HuggingFace search panel, select a model version, and click "Download." The system handles everything in the background.
- **Real-Time Progress**: Download progress (percentage, bytes received, total size) is persisted to `.backend/cache/downloads.json` every 500ms and polled by the frontend for live progress bars.
- **Automatic Vault Registration**: Upon completion, the download engine automatically spawns the `vault_crawler.py` as a background subprocess to hash and register the new file in SQLite.
- **Retry Support**: Failed downloads can be retried via a dedicated endpoint without re-entering URLs or parameters.
- **Batch Management**: Users can view all active/completed/failed downloads and clear the history.

## Architecture & Modules
- **`download_engine.py`** (`.backend/download_engine.py`): The `Downloader` class that manages the full download lifecycle. It is spawned as a subprocess by `server.py`, isolating it from the main HTTP thread to prevent blocking.
- **Server Endpoints** (`server.py`):
  - `POST /api/download` — Initiates a new download job in a background subprocess.
  - `POST /api/download/retry` — Retries a failed download using its stored parameters.
  - `POST /api/downloads/clear` — Clears completed/failed entries from the status file.
  - `GET /api/downloads` — Returns current download status for all jobs.

## Data & Logic Flow
1. **Initiation**: The frontend sends a POST request to `/api/download` with the model URL, destination category folder, filename, and optional CivitAI API key.
2. **Subprocess Spawn**: `server.py` spawns `download_engine.py` as a detached subprocess using `CREATE_NEW_PROCESS_GROUP` (Windows) to prevent the main server from blocking.
3. **URL Safety**: The download URL is encoded via `urllib.parse.quote()` to safely handle spaces and special characters that would otherwise cause HTTP 400 errors.
4. **Auth-Header Stripping**: A custom `NoAuthRedirectHandler` intercepts HTTP redirects and strips the `Authorization` header before following them. This prevents Bearer tokens from leaking to CDN redirect targets (e.g., Cloudflare R2 storage).
5. **Chunked Write**: Data is read in 32KB chunks and written directly to disk. Every 500ms (throttled to prevent disk thrashing), progress is flushed to `downloads.json`.
6. **Post-Download Hook**: On success, the engine spawns `vault_crawler.py` silently to hash and register the new file in `metadata.sqlite`.
7. **Error Handling**: On failure, the job status is set to `"error"` with a descriptive message. The frontend displays this and offers a "Retry" button.

## Configuration Options
- **API Key**: The CivitAI API key from `settings.json` is passed as a CLI argument (`--api_key`) to enable authenticated downloads of gated models.
- **Destination Folder**: The target Global Vault subfolder (e.g., `Global_Vault/checkpoints/`) is specified per-download. Relative paths are resolved against the project root.

## Business Rules & Edge Cases
- **Redirect Security**: Auth headers are stripped on ALL redirects to prevent credential leakage. CivitAI's download URLs frequently redirect through multiple CDN layers.
- **Throttled Status Writes**: The JSON status file is only updated every 500ms to prevent excessive disk I/O during large multi-GB downloads that generate thousands of chunk events.
- **Subprocess Isolation**: Downloads run as fully independent processes. Killing the main server does NOT abort active downloads.
- **CLI Interface**: `download_engine.py` can be run standalone via `python download_engine.py --job_id X --url ... --dest_folder ... --filename ... --model_name ... --root_dir ...`.

## Related Files & Functions
- `.backend/download_engine.py` → `Downloader.download()`, `Downloader.update_job()`
- `.backend/server.py` → `handle_download()`, `handle_retry_download()`, `handle_clear_downloads()`, `handle_get_downloads()`
- `.backend/cache/downloads.json` → Persistent job status store
- `.backend/vault_crawler.py` → Auto-spawned post-download for DB registration

## Observations / Notes
- The `User-Agent` header is set to `AIManager/1.0` for all download requests to identify traffic patterns to model hosting providers.
- The download engine is intentionally minimal (143 lines) and stateless beyond JSON file persistence, making it robust against crashes — a restart simply re-reads `downloads.json`.
