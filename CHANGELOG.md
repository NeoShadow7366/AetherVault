# Changelog

All notable changes to the **AetherVault** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.1.0] — 2026-04-10
*Sprint 12 — Inference Studio 2.0: Inpainting, Regional Prompting, Iteration Tools, and Full QA Coverage.*

### Added
- **Inpainting Canvas** — Full mask painting overlay on the Inference Studio canvas with brush/eraser tools, adjustable brush size, and undo/clear controls. Mask data injected into ComfyUI (`LoadImageMask` → `SetLatentNoiseMask`) and A1111 (`mask`, `inpainting_fill`, `mask_blur`, `inpaint_full_res`) payloads.
- **Regional Prompting** — Multi-zone prompt editor with visual zone layout. ComfyUI backend builds `CLIPTextEncode` → `FluxGuidance` (FLUX only) → `ConditioningSetArea` → `ConditioningCombine` chains with pixel-accurate coordinate math. A1111 backend joins zones with `BREAK` delimiters.
- **X/Y/Z Parameter Plot Grid** — Side panel for sweeping any generation parameter across axes, producing a visual comparison grid of outputs.
- **Wildcard Prompt Parser** — Inline `__wildcard__` syntax expansion with randomized selection from user-defined word lists.
- **Seed Variation Explorer** — Generate multiple outputs with incremental seed offsets from a base seed for rapid visual comparison.
- **Real-time Generation Progress Bar** — Live progress tracking with percentage, step count, and ETA estimation during inference.
- **Ollama Prompt Enhancement** — Integration with local Ollama LLM for prompt refinement and expansion (`/api/ollama/status`, `/api/ollama/enhance` endpoints).
- **Package Repair Pipeline** — Multi-strategy repair mechanism in `installer_engine.py` with streaming progress, handling corrupted `.git` directories and Windows file-lock bypass.
- **Server Route Table Refactor** — Centralized `ROUTE_TABLE` dict dispatch replacing scattered `if/elif` chains in `do_GET`/`do_POST`, improving maintainability across 70+ endpoints.
- Comprehensive `docs/` structure matching the agentic architecture (9 feature docs, 45+ endpoint API reference).
- Full `api-reference.md` mapping all dynamic JSON endpoints with request/response shapes.
- `database-schema.md` defining the SQLite `metadata_db` schema, WAL mode, and migration strategy.
- Four Mermaid architecture diagrams embedded in `architecture.md`, `deployment-and-setup.md`, `zero_friction_inference.md`, and `global_vault_system.md`.
- `docs/features/model_downloads.md` and `docs/features/model_imports.md` covering download and import engines.
- System Tray Launcher section in `deployment-and-setup.md` with mutex, bootstrap GUI, and shutdown sequence.

### Changed
- `agents.md` consolidated from ~640 lines of duplicated context to a streamlined 3-layer architecture document with explicit skill/rule tables.
- All 16 agent skills updated with standardized YAML frontmatter metadata (input/output contracts, authority levels).
- Agent rules extracted into dedicated `.agents/rules/` directory (security, cross-platform, data-safety, QA, model-switch, learning-and-memory).
- Agent workflows formalized in `.agents/workflows/` (7 workflows: `/start`, `/SW`, `/gitrelease`, QA runners, model router, doc generation).
- API contracts updated in `.agents/contracts/api_contracts.md` to reflect Sprint 12 endpoints.
- Recipe JSON files (`comfyui.json`, `forge.json`, `auto1111.json`, `fooocus.json`) updated with latest configuration fields.
- `installer_engine.py` refactored with streaming `Popen`-based git clone for real-time progress reporting.
- `metadata_db.py` hardened with proper connection lifecycle management and test isolation.
- Legacy test files relocated from `.backend/` root to `.tests/legacy/` for archival.

### Fixed
- Rebuilt `docs/README.md` to properly map to the AetherVault project instead of outdated `.NET` legacy references.
- Corrected 5 broken `file:///` URIs in `first-time-workflow.md`.
- Fixed typos across documentation ("Vanilia", "downloding", "system systems", duplicate "securely").
- Fixed `test_installer_engine` mock mismatch caused by Sprint 11's `Popen` migration — added `subprocess.Popen` mock alongside `subprocess.run`.
- Removed 7 orphaned dev/debug scripts from project root (`check_db.py`, `check_vaes.py`, `download_test_models.py`, `launch_and_test.py`, `test_combo2.py`, `test_flux_payload.py`, `test_proxy.py`).

### Tests
- **78/78 tests passing** — full regression suite including 15 Playwright E2E tests.
- Added 7 proxy translator tests covering FLUX/SDXL inpainting mask injection, regional prompting (multi-zone and single-zone), and A1111 payload generation.
- Added 2 server API tests for Ollama status and prompt enhancement endpoints.
- Coverage: `proxy_translators.py` 73%, `vault_crawler.py` 87%, `metadata_db.py` 53%, `installer_engine.py` 47%.

---

## [1.0.0-rc.1] — 2026-04-01
*V1 feature freeze — final QA hardening and release preparation.*

### Added
- 15-minute in-memory TTL cache for CivitAI search results, eliminating redundant API calls on repeat queries and pagination.
- CivitAI infinite scroll pagination via `?offset=N` forwarding to Meilisearch.
- HuggingFace search pagination and `filter_tags` support with dynamic type dropdown switching.
- Vault infinite scroll via `IntersectionObserver` on the "Load More" button with 400px rootMargin.
- External Directory Junction linking — users can point to Stability Matrix model directories without byte duplication.

### Changed
- Favorites state migrated from shared `localStorage` to backend-backed `window.appFavorites` in `settings.json`, preventing cross-port environment contamination.
- Vault indexing refactored from sequential micro-fetches to bulk `WHERE hash IN ()` queries for O(n) latency reduction.

### Fixed
- Img2Img proxy now forces `denoising_strength=1.0` for txt2img and honors the user's float for img2img, fixing gray outputs.
- CivitAI null/undefined image URL sanitization, resolving broken thumbnails for models like AutismMix SDXL.
- Resolved `renderGalleryGrid is not defined` error from duplicate gallery function triggers.
- Stabilized the full E2E Playwright test suite to 100% pass rate with regex-based text assertions.

### Security
- Added `settings.json` to `build.py` ignore list, preventing API keys from shipping in release zips.

---

## [0.6.0] — 2026-03-30
*Desktop application packaging, CI/CD automation, and agent governance.*

### Added
- Automated CI/CD release pipeline via GitHub Actions (`release.yml`) with cloud-based PyInstaller compilation.
- `/gitrelease` agent workflow for one-command semantic version tagging and release triggering.
- Accent Color selector in Global Settings with CSS custom property override (`--primary`), persisted in `settings.json`.
- Premium Tkinter bootstrap loading screen with real-time PyTorch download progress.
- Formal Agent Hierarchy and Chain of Command in `agents.md` with Conflict Resolution Matrix.
- Human-in-the-Loop Knowledge Review Process rule (`.agent/rules/learning_and_memory.md`).

### Changed
- `tray_launcher.py` refactored to abandon `.bat`/`.sh` scripts — PyInstaller executable is fully self-reliant.
- Cross-platform subprocess parameters wrapped in `os.name == 'nt'` guards, fixing `ValueError` on macOS/Linux CI runners.

### Fixed
- Single-instance mutex `ctypes.windll` calls now gated behind OS-level checks to prevent crashes on UNIX.

---

## [0.5.0] — 2026-03-29
*Guardian ecosystem, E2E testing stabilization, and desktop application lifecycle.*

### Added
- Architecture Guardian (Monolith Sentinel) with pre-change impact analysis and ADR generation.
- Runtime Health Doctor for pre-flight infrastructure checks (manifest, junctions, SQLite).
- API Contract Librarian with living endpoint contract documentation.
- Safe Test Runner with OS-level timeout envelope preventing orphaned test pipelines.
- Meilisearch-based CivitAI search proxy (`/api/civitai_search`) achieving 1:1 search parity with the official web UI.
- `/start` and `/SW` session handoff workflows for standardized context transitions.
- Aggressive `wmic`-based safety sweep for guaranteed orphan-free process teardown on Windows.

### Fixed
- Resolved zombie `embedding_engine.py` processes surviving application shutdown via system-level PID hunting.
- Fixed fatal `_enter_buffered_busy` thread lock crash during daemon thread stdout flushing at interpreter shutdown.
- Corrected `taskkill` usage — switched to `wmic process ... call terminate` for command-line string matching.

---

## [0.4.0] — 2026-03-28
*Inference Studio power-ups, gallery UX overhaul, and system stabilization.*

### Added
- Vault Import from Backup (`POST /api/vault/import`) restoring metadata from exported JSON manifests with upsert-or-skip logic.
- Batch Generation Queue with sequential background worker, payload translation per engine, and queue status API.
- Real-time Prompt Token Counter with CLIP-style approximation and model-aware limits (SD1.5=77, SDXL=154, FLUX=512).
- Dashboard Activity Feed merging recent generations (🎨) and downloads (📥) with clickable navigation.
- SVG Donut Chart for vault category distribution with hover tooltips and color-coded legend.
- Interactive inline SVG star rating system on My Creations gallery cards, persisted in SQLite.
- Dynamic tag filtering toolbar extracting unique tags from gallery metadata.
- A/B Comparison modal with draggable slider and side-by-side parameter display.
- Disk Space Warning alert when Global Vault breaches configurable threshold (default 50GB).

### Changed
- Vault size polling cached with 60-second TTL, eliminating `os.walk()` on every 3-second dashboard cycle.

---

## [0.3.0] — 2026-03-27
*Settings system, administrative tools, and production hardening.*

### Added
- Unified Settings panel (API keys, theme selection, auto-updates toggle, LAN sharing).
- Settings persistence via `settings.json` + `/api/settings` GET/POST endpoints.
- OTA Ghost Updater (`updater.py`) with live server-reboot polling and data-safe patching.
- Visual Recipe Builder with two-column layout and live JSON preview for custom engine templates.
- Persistent Prompt Library with SQLite CRUD and sliding panel UI.
- Bulk Vault Management with multi-select mode and batch delete.
- LAN Sharing toggle with runtime banner and `0.0.0.0` binding.
- Extension Install Progress Tracking (`ExtensionCloneTracker`) with real-time `git clone --progress` parsing.
- Vault Export & Backup — metadata-only JSON export and full ZIP archive via `POST /api/vault/export`.
- Command Palette (`Ctrl+K`) with 16-command registry, fuzzy filter, and glassmorphism overlay.
- Dashboard Analytics Widget with 6 real-time stat cards and gradient accents.
- Dynamic gradient SVG thumbnails for vault model cards.
- Playwright E2E test suite and GitHub Actions CI pipeline (`qa.yml`).

---

## [0.2.0] — 2026-03-26
*Agentic metadata system, App Store, and isolated runtime management.*

### Added
- Background vault crawler with async SHA-256 hashing and CivitAI metadata scraping.
- Sentence-transformer embedding engine (`all-MiniLM-L6-v2`) for semantic model search.
- HuggingFace Hub async headless search and download client.
- Model version update checker via CivitAI API with UI indicators.
- Recipe-driven App Store with JSON templates for ComfyUI, Forge, A1111, and Fooocus.
- `installer_engine.py` with isolated `.venv` creation per app, preventing PyTorch conflicts.
- Global Vault symlink routing on app install (NTFS junctions on Windows, `os.symlink()` on UNIX).
- Package lifecycle management — launch, stop, restart, uninstall with PID tracking.
- Log viewer terminal modal with live stdout streaming from managed packages.
- Extension/plugin management modal (git clone + remove).

---

## [0.1.0] — 2026-03-23
*Project genesis — core architecture, inference router, and live dashboard.*

### Added
- Python HTTP server (`server.py`) using stdlib `ThreadingHTTPServer` — zero external dependencies.
- SQLite database layer (`metadata_db.py`) with models, generations, embeddings, and user_tags tables.
- Monolithic `index.html` frontend with sidebar navigation, 9 tabs, and Apple Softness design system.
- CivitAI API integration for model search and metadata scraping (`civitai_client.py`).
- Cross-platform symlink/junction manager (`symlink_manager.py`) using NTFS junctions on Windows.
- Drag-and-drop model import pipeline (`import_engine.py`) with category inference.
- Download engine with chunked progress tracking and auth-header support (`download_engine.py`).
- ComfyUI proxy endpoint (`/api/comfy_proxy`) for transparent backend communication.
- Inference Studio UI with two-column layout (parameters panel + generation canvas).
- Model/LoRA/VAE/ControlNet dropdowns populated from Global Vault inventory.
- KSampler parameter controls (steps, CFG scale, sampler, scheduler).
- FLUX.1 model support with dedicated UNET/CLIP-L/T5-XXL dropdown selectors.
- Hires upscale pipeline (latent + ESRGAN variants) and refiner model support.
- ComfyUI JSON workflow topology builder (`proxy_translators.py`) translating unified payloads.
- Image drag-and-drop metadata restore from PNG `tEXt` chunks.
- Real-time sync toast system for background model indexing status.
- Download status popup with progress bars and retry support.
- My Creations gallery with SQLite persistence, lightbox display, and canvas restore.
- Portable Python bootstrapping via `install.bat` / `install.sh` using `python-build-standalone`.
