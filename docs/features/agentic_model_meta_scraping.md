# Agentic Model Meta-Scraping

## Overview
The Agentic Model Meta-Scraping system is an intelligent background pipeline that automatically discovers, hashes, and enriches every AI model file placed in the Generative AI Manager's Global Vault. It seamlessly bridges local file storage with remote metadata repositories (CivitAI and HuggingFace) to populate the dashboard with names, thumbnails, tags, category hierarchies, update statuses, and semantic search capabilities—all without requiring manual user intervention.

## Key Features / User Flows
- **Zero-Touch Indexing:** Users drop `.safetensors`, `.pt`, `.ckpt`, or `.bin` files into the `Global_Vault`. The system automatically detects new additions, hashes them, and updates the local SQLite library.
- **Smart Metadata Enrichment:** Utilizing the computed SHA-256 hash, the system queries CivitAI to retrieve comprehensive metadata including base models, authors, parameters, and tags.
- **Automated Thumbnail Caching:** Previews are seamlessly downloaded and stored locally for lightning-fast gallery loading, even completely offline.
- **Semantic Text Search:** Models are embedded using local NLP models (`sentence-transformers/all-MiniLM-L6-v2`) to let users find models via natural language concepts, not just exact filenames.
- **Continuous Update Detection:** Background workers periodically check for model version updates by pinging the CivitAI API and applying flags to outdated local models.

## Architecture & Modules
The architecture uses a pipeline of decoupled, single-responsibility modules coordinated by the overarching backend framework.

- **VaultCrawler (`vault_crawler.py`):** Deep-scans the repository for models, ignoring invalid files, and processes hashing in a parallel (multi-threaded pool) but memory-safe (4MB chunked) manner.
- **CivitaiClient (`civitai_client.py`):** Dedicated API worker that queries `civitai.com` utilizing SHA-256 hash lookups to download model stats and save image assets.
- **HFClient (`hf_client.py`):** Acts as a bridge to HuggingFace, abstracting search queries, and inferring base model types (SDXL, SD 1.5, Flux.1) dynamically based on sibling tag sets.
- **EmbeddingEngine (`embedding_engine.py`):** Uses an ~80MB PyTorch-based model daemon loop that creates 384-dimensional vector embeddings of text properties (tags, categories, and filenames) and performs cosine similarity queries to return top matches. 
- **UpdateChecker (`update_checker.py`):** A daemon tasked with matching local versions against external sources by using pooled API queries (to mitigate rate-limiting).

## Data & Logic Flow
1. **File Detection:** Foreground or boot operations trigger the `start_background_scanners()`.
2. **Hashing:** `VaultCrawler` reads chunks of massive files (preventing out-of-memory errors) and issues SHA-256 digests.
3. **Database Registration:** The hash is injected into SQLite's `models` table along with the filename and base folder category. 
4. **Metadata Polling:** `CivitaiClient` polls the DB for unpopulated records. Unpopulated hashes are requested against the `/api/v1/model-versions/by-hash/{hash}` API.
5. **Asset Caching:** On response, thumbnails are pulled into `.backend/cache/thumbnails` and JSON paths are written for cross-platform relativity. 
6. **Vectorizing:** `EmbeddingEngine` collects any model missing JSON vector data. It generates an embedding from combined string properties (e.g., filename + category + baseModel + tags) and computes the arrays into `embeddings` SQLite table.
7. **Version Checking:** `UpdateChecker` batches `modelId` queries to see if newer `latest_version_id` values exist on CivitAI.

## Configuration Options
- **Concurrency Rate:** `VaultCrawler` operates via a `ThreadPoolExecutor` (currently capped at 4 max workers for parallel NVMe SSD reads).
- **API Rate Limiting:** Hardcoded `time.sleep(1.0)` thresholds are enforced for CivitAIClient to prevent API bans.
- **Semantic Engine Execution Frequency:** Triggered perpetually on a daemon thread every 60 seconds.
- **HuggingFace Settings:** Supported authentication token handling `self.api_key` located in `settings.json`.

## Business Rules & Edge Cases
- **Duplicate Prevention:** Before chunking a massive file, `VaultCrawler` cross-checks against registered DB file names or files residing near `.manager_ignore`.
- **Fault-Tolerant Resolution:** Unmatched models (404s like missing HuggingFace native ones) or network drops are flagged silently—ignoring them for future runs until manual repair is triggered via `repair_model_metadata()`.
- **Portable Storage Links:** Metadata image paths are converted via `os.path.relpath()` to operate agnostically whether run on Windows, Mac, or Linux systems.
- **Thread Safety Constraint:** Crucially, `EmbeddingEngine` model instances are single-threaded to prevent catastrophic overlapping and DB lock overlaps. 

## Related Files & Functions
- **Core Crawlers:** 
  - `.backend/vault_crawler.py` -> `VaultCrawler.crawl()`
  - `.backend/civitai_client.py` -> `process_unpopulated_models()`
  - `.backend/embedding_engine.py` -> `generate_missing_embeddings()`, `search()`
  - `.backend/update_checker.py` -> `check_for_updates()`
  - `.backend/hf_client.py` -> `search_models()`
- **Database & Agents:** 
  - `.backend/metadata_db.py`
  - `.agents/skills/asset_crawler_metadata_scraper/SKILL.md`

## Observations / Notes
- The multi-stage scraping is designed completely asynchronously so the UI dashboard is never blocked, allowing users zero-friction boot times (starting in under 2 seconds) even if metadata mapping lags initially.
- The use of chunks (`4096 * 1024` byte size) when reading models is critical because Flux.1 models and SD weights regularly exceed 6-12 GB each in local setups.
