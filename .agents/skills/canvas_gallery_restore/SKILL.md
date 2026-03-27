---
name: Canvas Gallery Restore
description: Manages the My Creations gallery backed by SQLite, including saving generation results with full parameter metadata, browsing with sort/filter, lightbox display, rating, deletion, and drag-and-drop canvas restore that rehydrates all generation parameters back into the Inference Studio.
---

# Canvas Gallery Restore

## Purpose

Provide a persistent, searchable gallery of all AI-generated images with complete parameter metadata. Enable one-click restoration of any past generation's full configuration (prompt, seed, model, steps, CFG, sampler, dimensions) back into the Inference Studio canvas.

## When to Use

```
IF the task involves:
  ├── Saving a generation result to the gallery          → USE THIS SKILL
  ├── Listing/browsing past generations                  → USE THIS SKILL
  ├── Restoring generation params to the studio canvas   → USE THIS SKILL
  ├── Rating or deleting gallery entries                 → USE THIS SKILL
  ├── Modifying the lightbox or gallery UI               → USE THIS SKILL
  └── Anything else                                      → DO NOT USE THIS SKILL
```

## Data Model

### Generations Table
```sql
CREATE TABLE generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT,         -- URL or file path to the generated image
    prompt TEXT,
    negative TEXT,
    model TEXT,              -- Checkpoint filename used
    seed INTEGER,
    steps INTEGER,
    cfg REAL,
    sampler TEXT,
    width INTEGER,
    height INTEGER,
    rating INTEGER DEFAULT 0,
    tags TEXT,
    extra_json TEXT,         -- LoRAs, ControlNet, denoising_strength, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/gallery/save` | Save a new generation with all parameters |
| GET | `/api/gallery?sort=newest` | List generations (newest, oldest, top_rated) |
| POST | `/api/gallery/delete` | Delete a generation by ID |
| POST | `/api/gallery/rate` | Set rating (0-5) for a generation |

## Save Payload (Input)

```json
{
  "image_path": "/api/comfy_image?filename=ComfyUI_00042_.png",
  "prompt": "a serene mountain landscape, photorealistic",
  "negative": "blurry, low quality",
  "model": "dreamshaper_8.safetensors",
  "seed": 12345,
  "steps": 30,
  "cfg": 7.5,
  "sampler": "euler_ancestral",
  "width": 1024,
  "height": 1024,
  "extra": {
    "loras": [{"name": "detail_tweaker", "weight": 0.6}],
    "denoising_strength": null,
    "engine": "comfyui"
  }
}
```

## Canvas Restore Flow

```
Gallery Thumbnail Click
    │
    ▼
Lightbox opens with full image + metadata display
    │
    ▼ [User clicks "Send to Studio"]
Read generation record from SQLite
    │
    ▼
Populate Inference Studio fields:
  - Prompt textarea ← prompt
  - Negative textarea ← negative
  - Model dropdown ← model
  - Seed input ← seed
  - Steps slider ← steps
  - CFG slider ← cfg
  - Sampler dropdown ← sampler
  - Width/Height inputs ← width, height
  - LoRA panel ← extra.loras
    │
    ▼
Switch to Inference Studio tab
```

## Key Implementation Files

| File | Role |
|------|------|
| `.backend/metadata_db.py` → `save_generation()` | Insert generation record |
| `.backend/metadata_db.py` → `list_generations()` | Query with sort/limit/offset |
| `.backend/metadata_db.py` → `delete_generation()` | Remove by ID |
| `.backend/metadata_db.py` → `rate_generation()` | Update rating |
| `.backend/server.py` → `handle_gallery_*()` | API handlers |
| `.backend/static/index.html` | Gallery UI, lightbox, restore logic |

## Safety Checklist

- [ ] Never delete the actual image file — only remove the DB record
- [ ] Validate `id` parameter is an integer before SQL operations
- [ ] Use parameterized queries for all database operations
- [ ] Gallery sort order must use allowlisted column names (prevent SQL injection)
- [ ] `extra_json` must be valid JSON; wrap parsing in try/except
