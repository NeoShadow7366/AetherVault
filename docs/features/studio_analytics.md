# Studio Analytics & My Creations

## Overview
The **Studio Analytics** feature acts as the persistent memory and gallery for all inferences generated across any supported engine (ComfyUI, Forge, Fooocus, A1111). It provides a high-performance, SQLite-backed visual lightbox that retains full parameter metadata (Seed, Steps, Prompt, CFG, Model, etc.) and allows users to seamlessly restore generation configurations natively via the **Drag-And-Drop Canvas Restore**.

## Key Features / User Flows
- **My Creations Gallery**: A visual library sorting and displaying all generated images. Supports pagination, infinite scrolling (implicit via chunked loading), and dynamic layout handling for different aspect ratios.
- **Lightbox Overlay**: A distraction-free viewing modal enabling close-up inspection of generated images alongside their generation metadata (Seed, Prompt, Model, Sampler, CFG, etc.).
- **Drag-And-Drop Canvas Restore**: By dragging an image thumbnail from the gallery over the Inference Studio's canvas, all parameters that originally produced the image are parsed and immediately injected back into the active dashboard settings.
- **Star Rating & Tagging**: Generative outputs can be rated via an interactive SVG star system and filtered by dynamically extracted multi-tags.
- **A/B Comparison Tool**: Deep side-by-side inspection of two generated images with a draggable visual divider to evaluate differences between generations vividly.
- **Disk Space Monitoring**: Provides proactive capacity warnings evaluating `generations/` media output size to prevent stealth storage exhaustion.

## Architecture & Modules
- **Database Architecture**: Resides under the `generations` and `user_tags` tables within `.backend/metadata.sqlite`. Leveraging SQLite WAL (Write-Ahead Logging) to allow concurrent asynchronous writes from generative backends without locking the main thread.
- **API Endpoints**: 
  - `GET /api/gallery`: Fetches the generation history, filtering logic optionally applied.
  - `POST /api/gallery/save`: Ingests an image output with JSON payload containing properties.
  - `POST /api/gallery/rate`: Exposes state manipulation to modify generation metrics.
  - `POST /api/gallery/delete`: Truncates SQLite records and asynchronously cleans disk files.
  - `GET /api/gallery/tags`: Yields unique descriptors assigned to images for filtering toolbar components.

## Data & Logic Flow
1. **Creation**: Upon a backend finishing generation, proxy routers hook the inference result and proxy the image binaries directly via HTTP. Simultaneously, `server.py` invokes `MetadataDB.save_generation` to snapshot the engine parameters.
2. **Indexing & Surfacing**: `metadata_db.py` injects rows efficiently. The monolithic UI (`index.html`) fires fetch requests to `/api/gallery`, binding JSON results iteratively.
3. **Canvas Restore Logic**: A frontend event listener detects dragging originating from a gallery image class. `ondrop` logic identifies the source DB element ID, extracting the bound generation struct, and injects payload items directly into respective standard DOM fields orchestrating the prompt/seed/model.
4. **Clean Ups**: Bulk removal via `/api/dashboard/clear_history` truncates records, guaranteeing aligned local storage cleanliness matching the local SQLite state.

## Business Rules & Edge Cases
- **Non-Destructive UI Behavior**: Existent database logic ensures failed API interactions (e.g., deleted files manually off disk) won't crash rendering; missing image paths elegantly fall back to placeholder elements or display empty states.
- **Orphan Prevention**: On manual image deletion, if an image file remains locked by OS processes, the SQLite transaction operates safely or schedules asynchronous garbage collection without impeding user interface threads.
- **Concurrent DB Access**: SQLite WAL mode allows generation tasks from multiple queues or engines (e.g., bulk generation running concurrently) without DB block locking UI fetches.

## Related Files & Functions
- **`.backend/metadata_db.py`**:
  - `save_generation`, `list_generations`, `delete_generation`, `rate_generation`, `get_gallery_tags`, `list_generations_by_tag`
- **`.backend/server.py`**:
  - Contains API route mapping specifically targeting endpoints such as `handle_gallery_save`, `handle_gallery_delete`, `handle_gallery_list`.
- **`static/index.html`**:
  - Implements DOM containers like `<div class="lightbox-overlay">`, `.gallery-star-bar`, `.tag-filter-bar`, and the logic orchestrating `function restore()` or A/B dragging mechanics.
- **`.agents/skills/canvas_gallery_restore/SKILL.md`**:
  - Maintains domain instructions regarding standard logic guarantees and drag-drop DOM integrity.
