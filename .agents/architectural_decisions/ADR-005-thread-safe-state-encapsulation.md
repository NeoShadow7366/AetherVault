# ADR-005: Thread-Safe State Encapsulation & Unified Error Contract

**Status:** Accepted  
**Date:** 2026-04-10  
**Author:** Architectural Audit Session  

## Context

The AetherVault backend (`server.py`) grew organically over 12 sprints into a 2,540-line monolithic handler with:
- 8 module-level mutable globals shared across 70+ handlers with no thread safety
- 4 different error response shapes across API handlers
- Direct dict-based subprocess tracking with no locking
- Non-atomic settings file writes vulnerable to corruption

## Decision

### 1. ProcessRegistry (`process_registry.py`)
Replace `AIWebServer.running_processes` / `running_installs` (plain dicts) with a
thread-safe `ProcessRegistry` class that serializes all mutations via an internal lock.

### 2. api_handler Decorator
A `@api_handler` decorator wraps route handlers to catch Python exceptions and emit
consistent `{"status": "error", "message": ...}` JSON responses. Applied to 20 high-risk handlers.

### 3. ServerState Primitives (`server_state.py`)
New module providing:
- `CachedValue` — thread-safe single-value cache with TTL and optional loader function
- `LRUCache` — ordered dict with automatic eviction and per-entry TTL
- `BatchQueue` — (available for future migration of `_batch_queue`)

Migrated caches:
- `_vault_size_cache` → `CachedValue(ttl=300)`
- `_civitai_search_cache` → `LRUCache(max_size=50, ttl=900)`
- `_server_stats_cache` → `CachedValue(ttl=30)`

### 4. Atomic Settings Writes
Settings saves now write to `.tmp` then `os.replace()` (atomic on NTFS and POSIX).

### 5. Frontend API Wrapper
`apiCall()` function and `ApiError` class added to `index.html` for consistent
client-side error handling. Can be adopted incrementally by individual fetch() calls.

## Consequences

- **Thread safety**: All shared mutable state now has proper locking. Eliminates race conditions between concurrent HTTP handler threads.
- **Error consistency**: Frontend can rely on a single error shape (`{status, message}`) from all endpoints.
- **Backward compatible**: The batch queue (`_batch_queue`, `_batch_lock`) is intentionally left as-is due to deep coupling with `_batch_worker`. Future work can migrate it to `BatchQueue`.
- **Performance**: LRUCache auto-evicts stale CivitAI search results instead of manual cleanup.
- **Zero-dependency**: All changes use Python stdlib only.

## Verification

Full QA suite: **78/78 tests passed** after both Phase 1 and Phase 2 changes.
