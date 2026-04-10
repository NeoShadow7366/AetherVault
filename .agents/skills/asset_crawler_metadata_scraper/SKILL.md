---
name: Asset Crawler & Metadata Scraper
description: Background pipeline that indexes Global_Vault files by computing SHA-256 hashes, queries CivitAI and HuggingFace APIs for model metadata and thumbnails, generates sentence-transformer embeddings for semantic search, and checks for version updates.
keywords:
  - crawler
  - hash
  - SHA-256
  - CivitAI
  - HuggingFace
  - metadata
  - thumbnail
  - embedding
  - semantic search
---

# Asset Crawler & Metadata Scraper

## Purpose

Automatically discover, hash, enrich, and index every model file in the Global Vault so the dashboard can display names, thumbnails, categories, tags, update status, and semantic search results — all without manual user input.

## When to Use

```
IF the task involves:
  ├── File discovery and SHA-256 hashing in Global_Vault  → USE THIS SKILL
  ├── CivitAI API integration (by-hash lookups)           → USE THIS SKILL
  ├── HuggingFace Hub search and download                 → USE THIS SKILL
  ├── Thumbnail downloading and caching                   → USE THIS SKILL
  ├── Semantic search embedding generation                → USE THIS SKILL
  ├── Model version update checking                       → USE THIS SKILL
  ├── Fixing metadata resolution or missing thumbnails    → USE THIS SKILL
  └── Anything else                                       → DO NOT USE THIS SKILL
```

## Pipeline Architecture

```
Global_Vault/
    │
    ▼ [1] VaultCrawler
    Hash new files → SQLite (filename, category, hash)
    │
    ▼ [2] CivitaiClient
    Query API by hash → metadata_json + thumbnail
    │
    ▼ [3] EmbeddingEngine
    Build text from metadata → sentence-transformers → vector_json
    │
    ▼ [4] UpdateChecker
    Compare installed version_id vs latest CivitAI version
```

## Component Details

### 1. VaultCrawler (`vault_crawler.py`)

**Input:** Global_Vault directory path  
**Output:** New rows in `models` table with `filename`, `vault_category`, `file_hash`

- Walks `Global_Vault/` recursively
- Filters for `.safetensors`, `.pt`, `.ckpt`, `.bin` extensions
- Skips files already in the database (by filename lookup)
- Hashes in 4MB chunks via `ThreadPoolExecutor(max_workers=4)`
- Uses `hashlib.sha256` for CivitAI compatibility

### 2. CivitaiClient (`civitai_client.py`)

**Input:** SHA-256 hash from database  
**Output:** `metadata_json` + `thumbnail_path` updated in `models` table

- Endpoint: `GET /api/v1/model-versions/by-hash/{hash}`
- Rate limited: `time.sleep(1)` between requests
- Downloads first preview image to `.backend/cache/thumbnails/{hash}.{ext}`
- Stores thumbnail path as relative (portable across installations)
- Handles 404 gracefully (model not on CivitAI)

### 3. EmbeddingEngine (`embedding_engine.py`)

**Input:** Models with metadata but no embeddings  
**Output:** 384-dimensional vectors in `embeddings` table

- Uses `sentence-transformers/all-MiniLM-L6-v2` (~80MB)
- Combines: filename + category + baseModel + tags + user_tags
- Runs as persistent background daemon (60s polling loop)
- Not thread-safe — single worker only

### 4. UpdateChecker (`update_checker.py`)

**Input:** Models with CivitAI metadata  
**Output:** `update_available` flag + `latest_version_id` in `models` table

- Groups models by `modelId` to minimize API calls
- Compares installed `version_id` against CivitAI's latest
- Rate limited: 1 req/sec

### 5. HFClient (`hf_client.py`)

**Input:** User search query  
**Output:** Formatted model list matching CivitAI-style response format

- Endpoint: `GET /api/models?search={query}&sort=downloads`
- Supports API key authentication via settings.json
- Infers base model from tags (SDXL, SD 1.5, Flux.1)

## Database Schema

```sql
-- Core model registry
CREATE TABLE models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    vault_category TEXT NOT NULL,
    file_hash TEXT UNIQUE,
    metadata_json TEXT,          -- Full CivitAI API response
    thumbnail_path TEXT,         -- Relative path to cached thumbnail
    last_scanned TIMESTAMP,
    update_available INTEGER DEFAULT 0,
    latest_version_id INTEGER
);

-- Semantic search vectors
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    vector_json TEXT,            -- JSON array of 384 floats
    last_embedded TIMESTAMP
);

-- User-defined organizational tags
CREATE TABLE user_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT,
    tag TEXT,
    UNIQUE(file_hash, tag)
);
```

## Key Implementation Files

| File | Role |
|------|------|
| `.backend/vault_crawler.py` | `VaultCrawler` class — file discovery + hashing |
| `.backend/civitai_client.py` | `CivitaiClient` class — API metadata + thumbnails |
| `.backend/hf_client.py` | `HFClient` class — HuggingFace search |
| `.backend/embedding_engine.py` | `EmbeddingEngine` class — semantic vectors |
| `.backend/update_checker.py` | Version comparison daemon |
| `.backend/metadata_db.py` | `MetadataDB` class — all SQLite operations |
| `.backend/import_engine.py` | Drag-drop import pipeline (hash + metadata in one shot) |
| `.backend/server.py` → `start_background_scanners()` | Orchestrates crawler + civitai on server boot |

## Startup Sequence

```python
def start_background_scanners():
    def _run_scanners():
        # 1. Index new files
        VaultCrawler(root_dir).crawl()
        # 2. Fetch metadata for unhashed models
        CivitaiClient(root_dir).process_unpopulated_models()
    
    threading.Thread(target=_run_scanners, daemon=True).start()
```

The `EmbeddingEngine` runs as a separate process launched by `start_manager.bat/sh`.

## Safety Checklist

- [ ] Never hash and write metadata for the same file concurrently
- [ ] CivitAI calls MUST have `time.sleep(1)` between requests
- [ ] All SQLite writes use parameterized queries
- [ ] Thumbnail downloads must validate file extension
- [ ] `SentenceTransformer` is not thread-safe — single worker only
- [ ] HuggingFace API key must never appear in logs or error responses
