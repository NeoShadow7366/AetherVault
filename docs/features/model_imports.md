# Model Import Pipeline

## Overview
The Model Import Pipeline handles drag-and-drop model file imports into the `Global_Vault/` with a full six-stage processing chain: file copy → SHA-256 hash → SQLite registration → CivitAI metadata lookup → thumbnail download → dependency extraction. It runs entirely in background threads, provides real-time status polling, and automatically infers model categories from filenames when the user doesn't specify one.

## Key Features / User Flows
- **Drag-and-Drop Import**: Users drag a model file (`.safetensors`, `.ckpt`, `.pt`) onto the dashboard. The system copies it to the correct `Global_Vault/<category>/` subdirectory and processes it entirely in the background.
- **Automatic Category Inference**: If the user doesn't specify a model type, the engine infers it from the filename using keyword matching (e.g., "lora" → `loras/`, "vae" → `vaes/`, "controlnet" → `controlnet/`). Defaults to `checkpoints/` for unrecognized patterns.
- **CivitAI Metadata Enrichment**: After hashing, the engine queries CivitAI's by-hash API to automatically populate the model's name, description, tags, and preview thumbnail.
- **Dependency Resolution**: The engine parses CivitAI metadata to extract recommended companion resources (e.g., "This SDXL LoRA works best with sdxl-vae-fp16-fix") and returns them to the frontend for one-click follow-up downloads.
- **External Path Imports**: Support for importing models from external filesystem paths (e.g., from `D:\old_models\`) via a separate API endpoint.
- **Multi-Job Tracking**: Multiple imports can run concurrently, each with an independent status that the frontend polls.

## Architecture & Modules
- **`import_engine.py`** (`.backend/import_engine.py`): The core module containing the `_run_import()` background worker, `start_import()` entry point, `get_import_status()` poller, and `list_import_jobs()` for batch visibility.
- **Category Map**: A comprehensive mapping (`CATEGORY_MAP`) translating 18+ CivitAI model types to the correct `Global_Vault/` subdirectory names. Covers checkpoints, LoRAs, LoCoNs, DoRAs, VAEs, ControlNets, embeddings, upscalers, UNET, CLIP, text encoders, motion modules, and more.
- **Server Endpoints** (`server.py`):
  - `POST /api/import` — Starts a new import job from a local file path.
  - `POST /api/import/external` — Starts an import from an external filesystem path.
  - `GET /api/import/status` — Returns the current status of a specific import job by ID.
  - `GET /api/import/jobs` — Returns all active and completed import jobs.

## Data & Logic Flow
1. **Initiation**: `start_import()` is called with a source file path, optional category, and the project root directory.
2. **Category Inference**: `_infer_category()` examines the filename for keywords (`lora`, `vae`, `controlnet`, `unet`, `clip`, `t5`, `embed`, `upscal`). If the user provided a valid category, it is used directly.
3. **File Copy**: The file is copied to `Global_Vault/<category>/` using `shutil.copy2()`, preserving timestamps. If source and destination are identical (file already in vault), the copy is skipped.
4. **SHA-256 Hashing**: The file is hashed in 4MB chunks via `hashlib.sha256()` to handle multi-GB files without memory exhaustion.
5. **SQLite Registration**: The file is inserted or updated in the `models` table via `MetadataDB.insert_or_update_model()`.
6. **CivitAI Lookup**: `CivitaiClient.fetch_model_by_hash()` queries the CivitAI API. If found, full metadata JSON is stored and the first preview image is downloaded as a thumbnail.
7. **Dependency Extraction**: `_extract_dependencies()` parses the CivitAI response for `recommendedResources` and base model indicators. For SDXL models, it automatically recommends `sdxl-vae-fp16-fix`; for SD 1.5 models, it recommends `vae-ft-mse-840000-ema-pruned`.
8. **Completion**: The job status is set to `"done"` with the resolved model name, dependencies list, metadata, and thumbnail path.

## Configuration Options
- **CivitAI API Key**: Passed from `settings.json` to enable authenticated lookups for gated or early-access models.
- **Category Override**: The frontend can explicitly set the target category to bypass automatic inference.

## Business Rules & Edge Cases
- **Thread Safety**: All job state mutations are protected by a `threading.Lock()` to prevent race conditions during concurrent imports.
- **Idempotent Copy**: If `os.path.abspath(src_path) == os.path.abspath(dest_path)`, the copy step is skipped entirely. This handles the case where a user "imports" a file that is already inside the vault.
- **Graceful CivitAI Failures**: If the model is not found on CivitAI, the import still completes successfully — it is marked as a "local-only model" with empty metadata.
- **UUID Job IDs**: Each import generates a unique 8-character UUID prefix as its job identifier for frontend polling.
- **Daemon Threads**: Import workers run as daemon threads and will be terminated if the server shuts down. In-progress imports are not resumable.

## Related Files & Functions
- `.backend/import_engine.py` → `start_import()`, `_run_import()`, `get_import_status()`, `list_import_jobs()`, `_infer_category()`, `_extract_dependencies()`, `_hash_file()`
- `.backend/server.py` → `handle_import_file()`, `handle_import_external()`, `handle_import_status()`, `handle_import_jobs()`
- `.backend/metadata_db.py` → `MetadataDB.insert_or_update_model()`, `MetadataDB.update_model_metadata()`
- `.backend/civitai_client.py` → `CivitaiClient.fetch_model_by_hash()`, `CivitaiClient.download_thumbnail()`

## Observations / Notes
- The `CATEGORY_MAP` supports both CivitAI type names (e.g., `"textualinversion"`) and common naming conventions (e.g., `"embedding"`), ensuring broad compatibility with files sourced from different platforms.
- The dependency extraction feature is a highly user-friendly touch — importing a LoRA automatically tells the user which VAE they should also install, with direct CivitAI links for one-click follow-up.
