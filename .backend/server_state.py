"""Centralized server state container with thread-safe accessors.

Replaces the scattered module-level globals in server.py
(_settings_cache, _vault_size_cache, _batch_queue, _batch_lock,
_batch_worker_running, _civitai_search_cache, _server_stats_cache)
with a single, well-encapsulated state object.
"""
import time
import threading
import logging
from collections import OrderedDict


class CachedValue:
    """A thread-safe cached value with time-to-live expiration.
    
    Optionally accepts a loader function that is called to refresh
    the value when it expires or when force_refresh() is called.
    """

    def __init__(self, ttl: int = 60, loader=None):
        self._lock = threading.Lock()
        self._data = None
        self._expires = 0
        self._ttl = ttl
        self._loader = loader

    def get(self, default=None):
        """Get the cached value. Returns default if expired or unset."""
        with self._lock:
            if self._data is not None and time.time() < self._expires:
                return self._data
            if self._loader:
                try:
                    self._data = self._loader()
                    self._expires = time.time() + self._ttl
                    return self._data
                except Exception as e:
                    logging.warning(f"CachedValue loader failed: {e}")
            return default

    def set(self, value, ttl: int = None):
        """Set the cached value with optional custom TTL."""
        with self._lock:
            self._data = value
            self._expires = time.time() + (ttl if ttl is not None else self._ttl)

    def invalidate(self):
        """Force the cache to expire on next get()."""
        with self._lock:
            self._expires = 0

    @property
    def data(self):
        """Direct access to raw data (no expiry check). For backward compat."""
        with self._lock:
            return self._data

    @data.setter
    def data(self, value):
        with self._lock:
            self._data = value


class LRUCache:
    """Thread-safe Least Recently Used cache with TTL.
    
    Used for CivitAI search results, server stats, etc.
    Evicts oldest entries when max_size is exceeded.
    """

    def __init__(self, max_size: int = 50, ttl: int = 900):
        self._lock = threading.Lock()
        self._store: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key, default=None):
        """Get a cached value by key. Returns default if missing or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if time.time() > entry["expires"]:
                del self._store[key]
                return default
            # Move to end (most recently used)
            self._store.move_to_end(key)
            return entry["value"]

    def set(self, key, value, ttl: int = None):
        """Set a cached value. Evicts oldest if over max_size."""
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = {
                "value": value,
                "expires": time.time() + (ttl if ttl is not None else self._ttl)
            }
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    def __contains__(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None or time.time() > entry["expires"]:
                return False
            return True

    def __len__(self):
        with self._lock:
            return len(self._store)


class BatchQueue:
    """Thread-safe batch generation queue.
    
    Replaces the module-level _batch_queue list and _batch_lock
    with a properly encapsulated container.
    """

    def __init__(self, max_history: int = 50):
        self._lock = threading.Lock()
        self._queue: list = []
        self._max_history = max_history
        self._worker_running = False

    def add(self, item: dict) -> None:
        """Add an item to the queue."""
        with self._lock:
            self._queue.append(item)

    def add_many(self, items: list) -> None:
        """Add multiple items to the queue."""
        with self._lock:
            self._queue.extend(items)

    def get_pending(self) -> list:
        """Return items with status 'pending'."""
        with self._lock:
            return [i for i in self._queue if i.get("status") == "pending"]

    def get_all(self) -> list:
        """Return a copy of the entire queue (for status endpoints)."""
        with self._lock:
            return list(self._queue)

    def update_status(self, job_id: str, status: str, **extra) -> bool:
        """Update the status of a job by ID. Returns True if found."""
        with self._lock:
            for item in self._queue:
                if item.get("id") == job_id:
                    item["status"] = status
                    item.update(extra)
                    return True
            return False

    def trim_history(self) -> None:
        """Remove completed/failed items beyond max_history."""
        with self._lock:
            # Keep pending and running items, plus the most recent completed
            active = [i for i in self._queue if i.get("status") in ("pending", "running")]
            done = [i for i in self._queue if i.get("status") not in ("pending", "running")]
            if len(done) > self._max_history:
                done = done[-self._max_history:]
            self._queue = active + done

    @property
    def worker_running(self) -> bool:
        with self._lock:
            return self._worker_running

    @worker_running.setter
    def worker_running(self, value: bool):
        with self._lock:
            self._worker_running = value

    @property
    def lock(self):
        """Expose lock for backward-compatible use in _batch_worker."""
        return self._lock

    def __len__(self):
        with self._lock:
            return len(self._queue)
