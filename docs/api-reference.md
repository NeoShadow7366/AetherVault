# API Operations & Reference

## Overview
The AetherVault utilizes a lightweight, zero-dependency `http.server` backend to handle all routing between the monolithic Vanilla JS frontend (`index.html`) and the various underlying systems (SQLite, subprocesses, and AI Engines).

This document serves as the official facing documentation for the system's endpoints. All endpoints are served from `http://localhost:8080` by default.

> [!NOTE]
> The exact structural definitions and JSON payload limits are continuously monitored and validated by the **API Contract Librarian** agent. For the absolute latest living contract file, see [`.agents/contracts/api_contracts.md`](../.agents/contracts/api_contracts.md).

---

## 1. Zero-Friction Engine Proxies

Because the Generative AI ecosystem is fragmented—with ComfyUI relying on JSON Workflow Topologies and Automatic1111/Forge using RESTful `sdapi`—the AetherVault homogenizes these differences using the **Universal Inference Router**. 

The frontend sends *only one* unified payload configuration to the proxy endpoints, and the router translates it natively into the target engine's expected format.

### Proxy Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/comfy_proxy` | `POST` | Routes generation to ComfyUI (port 8188). Translates to JSON node graph via `build_comfy_workflow()`. |
| `/api/forge_proxy` | `POST` | Routes generation to SD WebUI Forge (port 7860). Translates to sdapi REST payload. |
| `/api/a1111_proxy` | `POST` | Routes generation to Automatic1111 (port 7860). Translates to sdapi REST payload. |
| `/api/fooocus_proxy` | `POST` | Routes generation to Fooocus (port 8888). Translates to Fooocus-native format with aspect ratio mapping. |
| `/api/generate/batch` | `POST` | Enqueues a generation job in the in-memory batch queue for sequential processing. |
| `/api/generate/queue` | `GET` | Returns the current batch queue status (pending, active, completed jobs). |

### The Universal Generator Payload
When the frontend submits a generation request, it sends the following stabilized JSON structure:

```json
{
  "prompt": "string",
  "negative_prompt": "string",
  "seed": "integer (-1 for random)",
  "steps": "integer (default: 20)",
  "cfg_scale": "float (default: 7.0)",
  "width": "integer",
  "height": "integer",
  "sampler_name": "string",
  "scheduler": "string",
  "model_type": "string (sdxl | flux-dev | flux-schnell)",
  "override_settings": {
    "sd_model_checkpoint": "string (filename)"
  },
  "loras": [
    {"name": "string", "weight": "float"}
  ],
  "vae": "string",
  "init_image_name": "string (for comfyui)",
  "init_image_b64": "string (for forge/a1111)",
  "denoising_strength": "float",
  "controlnet": {
    "enable": "boolean",
    "model": "string",
    "strength": "float",
    "image": "string (filepath)",
    "image_b64": "string (base64)"
  },
  "hires": {
    "enable": "boolean",
    "factor": "float",
    "denoise": "float",
    "steps": "integer",
    "upscaler": "string"
  }
}
```

---

## 2. Vault Operations

Endpoints for managing the Global Vault model inventory, metadata, tags, health checks, exports, and imports.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/models` | `GET` | `?limit=N&offset=N` | `{status, models: [...], total, limit, offset}` | Paginated list of all vault models with parsed metadata and user tags. |
| `/api/vault/search` | `GET` | `?query=...&type=...` | `{status, results: [...]}` | Semantic vector search across vault model descriptions. |
| `/api/vault/tags` | `GET` | — | `{status, tags: [...]}` | Returns all distinct user-created tags across the vault. |
| `/api/vault/tag/add` | `POST` | `{file_hash, tag}` | `{status}` | Attaches a user tag to a model identified by its SHA-256 hash. |
| `/api/vault/tag/remove` | `POST` | `{file_hash, tag}` | `{status}` | Removes a specific user tag from a model. |
| `/api/vault/export` | `POST` | `{filenames: [...]}` | `{status, manifest: [...]}` | Exports metadata for selected models as a portable JSON manifest. |
| `/api/vault/import` | `POST` | `{manifest: [...]}` | `{status, imported, skipped, failed}` | Imports model metadata from a previously exported manifest. |
| `/api/vault/import_scan` | `POST` | `{path}` | `{status, files: [...]}` | Scans an external directory for importable model files. |
| `/api/vault/updates` | `POST` | `{}` | `{status, message}` | Spawns the `update_checker.py` background process to check CivitAI for newer model versions. |
| `/api/vault/repair` | `POST` | `{}` | `{status, message}` | Repairs vault integrity (re-creates broken symlinks, re-hashes files). |
| `/api/vault/health_check` | `POST` | `{}` | `{status, message}` | Quick health check: scans `packages/` for broken symlinks and removes them. |
| `/api/vault/bulk_delete` | `POST` | `{filenames: [...]}` | `{status, deleted}` | Batch-deletes model files from disk and removes their SQLite records. |
| `/api/delete_model` | `POST` | `{filename}` | `{status}` | Deletes a single model file from Global Vault and its database record. |

---

## 3. Gallery & Creations

Endpoints backing the "My Creations" gallery, including save, browse, rate, delete, and tag operations.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/gallery` | `GET` | `?sort=newest\|oldest\|top_rated&limit=N&offset=N` | `{status, generations: [...]}` | Paginated list of saved generations with all canvas parameters. |
| `/api/gallery/save` | `POST` | `{image_path, prompt, negative, model, seed, steps, cfg, sampler, width, height, extra_json}` | `{status, id}` | Saves a new generation to the gallery with full parameter metadata. |
| `/api/gallery/delete` | `POST` | `{id}` | `{status}` | Deletes a gallery entry by ID. |
| `/api/gallery/rate` | `POST` | `{id, rating}` | `{status}` | Sets a 0-5 star rating on a gallery entry. |
| `/api/gallery/tags` | `GET` | — | `{status, tags: [...]}` | Returns all distinct tags across gallery generations. |

---

## 4. Downloads & Imports

Endpoints for downloading models from external sources and importing local model files into the vault.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/download` | `POST` | `{url, filename, model_name, dest_folder, api_key?}` | `{status, job_id}` | Spawns a background download subprocess. Progress tracked in `downloads.json`. |
| `/api/download/retry` | `POST` | `{job_id, api_key?}` | `{status, job_id}` | Retries a failed download using stored parameters. |
| `/api/downloads/clear` | `POST` | `{}` | `{status}` | Clears the download history/status file. |
| `/api/downloads` | `GET` | — | `{status, downloads: {...}}` | Returns all active/completed/failed download job statuses. |
| `/api/import` | `POST` | `{src_path, category?, api_key?}` | `{status, import_id}` | Starts a background import: copy → hash → register → CivitAI lookup → dependencies. |
| `/api/import/external` | `POST` | `{src_path, category?, api_key?}` | `{status, import_id}` | Same as `/api/import` but for files outside the project directory. |
| `/api/import/status` | `GET` | `?import_id=X` | `{status, progress, deps, metadata, thumbnail}` | Polls the current status of a specific import job. |
| `/api/import/jobs` | `GET` | — | `{jobs: {...}}` | Returns all active and completed import jobs. |

---

## 5. Package Management

Endpoints for the App Store lifecycle — installing, launching, stopping, uninstalling engines, and managing extensions.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/packages` | `GET` | — | `{status, packages: [...]}` | Lists all installed packages with running status. |
| `/api/recipes` | `GET` | — | `{status, recipes: [...]}` | Lists all available installation recipe templates. |
| `/api/recipes/build` | `POST` | `{app_id, name, repository, launch, pip_packages, symlink_targets, ...}` | `{status, recipe_id}` | Creates a new custom installation recipe JSON file. |
| `/api/install` | `POST` | `{recipe_id}` | `{status, message}` | Triggers the App Store Installer to clone and sandbox a new engine. |
| `/api/launch` | `POST` | `{package_id}` | `{status, message, url}` | Spawns a subprocess to start an installed engine. Includes 3 pre-flight checks. |
| `/api/stop` | `GET/POST` | `{package_id}` or `?package_id=X` | `{status, message}` | Terminates a running engine subprocess (taskkill on Windows, SIGTERM on UNIX). |
| `/api/uninstall` | `POST` | `{package_id}` | `{status, message}` | Removes an installed package and its isolated venv. |
| `/api/repair_dependency` | `POST` | `{package_id}` | `{status, message}` | Re-installs pip dependencies from `requirements.txt` for a broken engine venv. |
| `/api/open_folder` | `POST` | `{path}` | `{status}` | Opens a filesystem path in the OS file explorer. |

---

## 6. Extensions

Endpoints for managing ComfyUI custom nodes and similar engine extensions.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/extensions` | `GET` | `?package_id=X` | `{status, extensions: [...]}` | Lists installed custom nodes for a specific engine. |
| `/api/extensions/status` | `GET` | `?job_id=X` | `{status, progress, ...}` | Polls real-time progress of an extension clone operation. |
| `/api/extensions/install` | `POST` | `{package_id, repo_url}` | `{status, job_id, message}` | Clones a Git repository into the engine's `custom_nodes/` directory. |
| `/api/extensions/remove` | `POST` | `{package_id, ext_name}` | `{status, message}` | Deletes an extension folder from the engine's `custom_nodes/`. |
| `/api/extensions/cancel` | `POST` | `{job_id}` | `{status, message}` | Cancels a running extension clone operation. |

---

## 7. Prompt Library

Endpoints for the saved prompt collection accessible via the Command Palette (`Ctrl+K`).

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/prompts` | `GET` | `?search=...&limit=N` | `{status, prompts: [...]}` | Lists saved prompts with optional substring search across title/content. |
| `/api/prompts/save` | `POST` | `{title, prompt, negative, model, tags, extra_json}` | `{status, id}` | Saves a new prompt to the library. |
| `/api/prompts/delete` | `POST` | `{id}` | `{status}` | Deletes a saved prompt by ID. |

---

## 8. System & Configuration

Endpoints for settings, server status, logs, shutdown, and updates.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/settings` | `GET` | — | Full `settings.json` contents | Returns current application settings. Falls back to defaults if file is missing/corrupt. |
| `/api/settings` | `POST` | Partial JSON payload | `{status}` | Merges incoming settings with existing via `dict.update()` to prevent data loss. |
| `/api/server_status` | `GET` | — | `{status, packages, stats, ...}` | Returns comprehensive server health: running packages, dashboard stats, vault size. |
| `/api/logs` | `GET` | `?package_id=X` | `{status, logs}` | Returns the last 150 lines of a package's `runtime.log`. |
| `/api/shutdown` | `POST` | — | `{status}` | Triggers graceful teardown: stops HTTP server, kills sandbox engines, sweeps orphans, exits. |
| `/api/system/update` | `POST` | `{}` | `{status, message}` | Spawns the OTA updater to apply code patches via `git pull` or zip extraction. |
| `/api/dashboard/clear_history` | `POST` | `{}` | `{status}` | Clears the dashboard activity history by updating the `activity_cleared_at` timestamp. |

---

## 9. External Service Proxies

Endpoints that proxy requests to external APIs (CivitAI, HuggingFace) from the frontend to avoid CORS issues.

| Endpoint | Method | Request | Response | Purpose |
|----------|--------|---------|----------|---------|
| `/api/civitai_search` | `GET` | `?query=...&type=...&offset=N` | `{items: [...]}` | Proxies search to CivitAI's MeiliSearch backend. Results cached for 15 minutes. |
| `/api/hf/search` | `GET` | `?query=...` | `{status, results: [...]}` | Proxies search to HuggingFace Hub API. |
| `/api/comfy_image` | `GET` | `?filename=...&subfolder=...&type=...` | Binary image data | Proxies image retrieval from a running ComfyUI instance. |
| `/api/comfy_upload` | `GET` | Multipart FormData | `{status, ...}` | Proxies file uploads to a running ComfyUI instance (e.g., init images for img2img). |

> [!WARNING]
> `/api/comfy_upload` uses multipart FormData rather than JSON. The API Contract Librarian has a special exception noted for this endpoint.

---

## Modifying API Contracts

If you are modifying the Python `server.py` or the JavaScript `index.html` `fetch()` handlers, you must ensure the payloads match. 

The **API Contract Librarian** runs asynchronously during codebase changes to analyze drift. If a payload mismatch is found, it will throw an alert up to the **Architecture Guardian**. 
