"""Unit tests for server_state module — CachedValue, LRUCache, BatchQueue.

Tests cover:
- CachedValue: TTL expiration, loader functions, invalidation, thread safety
- LRUCache: set/get, eviction, TTL expiry, max_size enforcement
- BatchQueue: add/get, status updates, worker_running flag, trim_history
"""
import os
import sys
import time
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.backend'))
from server_state import CachedValue, LRUCache, BatchQueue


class TestCachedValue(unittest.TestCase):

    def test_basic_set_get(self):
        """Set a value and retrieve it before expiry."""
        cv = CachedValue(ttl=10)
        cv.set("hello")
        self.assertEqual(cv.get(), "hello")

    def test_default_when_empty(self):
        """get() returns default when no value set."""
        cv = CachedValue(ttl=10)
        self.assertIsNone(cv.get())
        self.assertEqual(cv.get(default=42), 42)

    def test_ttl_expiration(self):
        """Value expires after TTL and get() returns default."""
        cv = CachedValue(ttl=0)  # 0 second TTL = expire immediately
        cv.set("ephemeral")
        # The set() uses time.time() + ttl, so with ttl=0 it expires instantly
        # Need a tiny sleep to ensure time has passed
        time.sleep(0.01)
        self.assertIsNone(cv.get())

    def test_custom_ttl_on_set(self):
        """set() with custom TTL overrides the default."""
        cv = CachedValue(ttl=100)
        cv.set("long-lived", ttl=0)
        time.sleep(0.01)
        self.assertIsNone(cv.get())

    def test_loader_function(self):
        """Loader function is called when value is expired or unset."""
        call_count = [0]
        def loader():
            call_count[0] += 1
            return f"loaded_{call_count[0]}"

        cv = CachedValue(ttl=10, loader=loader)
        result = cv.get()
        self.assertEqual(result, "loaded_1")
        # Second call should use cached value (not call loader again)
        result2 = cv.get()
        self.assertEqual(result2, "loaded_1")
        self.assertEqual(call_count[0], 1)

    def test_loader_exception(self):
        """If loader raises, get() returns default."""
        def bad_loader():
            raise RuntimeError("oops")

        cv = CachedValue(ttl=10, loader=bad_loader)
        self.assertEqual(cv.get(default="fallback"), "fallback")

    def test_invalidate(self):
        """invalidate() forces the next get() to refresh."""
        call_count = [0]
        def loader():
            call_count[0] += 1
            return call_count[0]

        cv = CachedValue(ttl=100, loader=loader)
        cv.get()
        self.assertEqual(call_count[0], 1)
        cv.invalidate()
        cv.get()
        self.assertEqual(call_count[0], 2)

    def test_data_property(self):
        """data property provides direct access without expiry check."""
        cv = CachedValue(ttl=0)
        cv.set("data_value")
        time.sleep(0.01)
        # get() would return None (expired), but data gives raw access
        self.assertIsNone(cv.get())
        self.assertEqual(cv.data, "data_value")

    def test_data_setter(self):
        """data setter allows direct assignment."""
        cv = CachedValue(ttl=10)
        cv.data = "direct"
        self.assertEqual(cv.data, "direct")

    def test_thread_safety(self):
        """Concurrent set/get should not raise or corrupt."""
        cv = CachedValue(ttl=10)
        errors = []

        def writer():
            try:
                for i in range(100):
                    cv.set(i)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    cv.get()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)


class TestLRUCache(unittest.TestCase):

    def test_basic_set_get(self):
        """Set and retrieve a keyed value."""
        cache = LRUCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")

    def test_get_missing(self):
        """Get returns default for missing keys."""
        cache = LRUCache()
        self.assertIsNone(cache.get("missing"))
        self.assertEqual(cache.get("missing", default="nope"), "nope")

    def test_ttl_expiration(self):
        """Expired entries return default."""
        cache = LRUCache(ttl=0)
        cache.set("k", "v")
        time.sleep(0.01)
        self.assertIsNone(cache.get("k"))

    def test_max_size_eviction(self):
        """Oldest entries are evicted when max_size is exceeded."""
        cache = LRUCache(max_size=3, ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict "a"
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("d"), 4)

    def test_lru_order(self):
        """Accessing an entry moves it to most-recently-used."""
        cache = LRUCache(max_size=3, ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access "a" to make it most-recently-used
        cache.get("a")
        cache.set("d", 4)  # Should evict "b" (least recently used), not "a"
        self.assertEqual(cache.get("a"), 1)
        self.assertIsNone(cache.get("b"))

    def test_overwrite_existing_key(self):
        """Setting an existing key updates the value."""
        cache = LRUCache(max_size=10, ttl=60)
        cache.set("k", "old")
        cache.set("k", "new")
        self.assertEqual(cache.get("k"), "new")

    def test_contains(self):
        """__contains__ checks for non-expired keys."""
        cache = LRUCache(ttl=60)
        cache.set("x", 1)
        self.assertIn("x", cache)
        self.assertNotIn("y", cache)

    def test_contains_expired(self):
        """__contains__ returns False for expired keys."""
        cache = LRUCache(ttl=0)
        cache.set("x", 1)
        time.sleep(0.01)
        self.assertNotIn("x", cache)

    def test_clear(self):
        """clear() removes all entries."""
        cache = LRUCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        self.assertEqual(len(cache), 0)

    def test_len(self):
        """__len__ returns entry count (including potentially expired)."""
        cache = LRUCache()
        cache.set("a", 1)
        cache.set("b", 2)
        self.assertEqual(len(cache), 2)

    def test_custom_ttl_per_entry(self):
        """set() with custom TTL overrides the default per-entry."""
        cache = LRUCache(ttl=100)
        cache.set("long", "lives", ttl=100)
        cache.set("short", "dies", ttl=0)
        time.sleep(0.01)
        self.assertEqual(cache.get("long"), "lives")
        self.assertIsNone(cache.get("short"))

    def test_thread_safety(self):
        """Concurrent operations should not raise or corrupt."""
        cache = LRUCache(max_size=50, ttl=60)
        errors = []

        def writer(start):
            try:
                for i in range(50):
                    cache.set(f"key_{start + i}", i)
            except Exception as e:
                errors.append(e)

        def reader(start):
            try:
                for i in range(50):
                    cache.get(f"key_{start + i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(4)]
        threads += [threading.Thread(target=reader, args=(i * 100,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)


class TestBatchQueue(unittest.TestCase):

    def test_add_and_get_all(self):
        """Items added should appear in get_all()."""
        bq = BatchQueue()
        bq.add({"id": "1", "status": "pending"})
        bq.add({"id": "2", "status": "pending"})
        self.assertEqual(len(bq.get_all()), 2)

    def test_add_many(self):
        """add_many adds multiple items at once."""
        bq = BatchQueue()
        bq.add_many([{"id": "1", "status": "pending"}, {"id": "2", "status": "pending"}])
        self.assertEqual(len(bq), 2)

    def test_get_pending(self):
        """get_pending returns only pending items."""
        bq = BatchQueue()
        bq.add({"id": "1", "status": "pending"})
        bq.add({"id": "2", "status": "running"})
        bq.add({"id": "3", "status": "done"})
        pending = bq.get_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], "1")

    def test_update_status(self):
        """update_status changes the status of a job."""
        bq = BatchQueue()
        bq.add({"id": "job1", "status": "pending"})
        self.assertTrue(bq.update_status("job1", "running"))
        jobs = bq.get_all()
        self.assertEqual(jobs[0]["status"], "running")

    def test_update_status_with_extra(self):
        """update_status can set additional fields."""
        bq = BatchQueue()
        bq.add({"id": "job1", "status": "pending"})
        bq.update_status("job1", "done", result={"images": 1})
        jobs = bq.get_all()
        self.assertEqual(jobs[0]["result"], {"images": 1})

    def test_update_status_not_found(self):
        """update_status returns False for unknown job ID."""
        bq = BatchQueue()
        self.assertFalse(bq.update_status("nonexistent", "done"))

    def test_worker_running_flag(self):
        """worker_running property getter/setter works."""
        bq = BatchQueue()
        self.assertFalse(bq.worker_running)
        bq.worker_running = True
        self.assertTrue(bq.worker_running)

    def test_trim_history(self):
        """trim_history removes old completed jobs beyond max_history."""
        bq = BatchQueue(max_history=2)
        bq.add({"id": "1", "status": "done"})
        bq.add({"id": "2", "status": "done"})
        bq.add({"id": "3", "status": "done"})
        bq.add({"id": "4", "status": "pending"})
        bq.trim_history()
        all_jobs = bq.get_all()
        # Should keep 1 pending + 2 most recent done
        self.assertEqual(len(all_jobs), 3)
        statuses = [j["status"] for j in all_jobs]
        self.assertIn("pending", statuses)

    def test_lock_exposed(self):
        """lock property exposes the internal threading.Lock."""
        bq = BatchQueue()
        self.assertIsInstance(bq.lock, type(threading.Lock()))

    def test_len(self):
        """__len__ returns total queue size."""
        bq = BatchQueue()
        bq.add({"id": "1", "status": "pending"})
        bq.add({"id": "2", "status": "done"})
        self.assertEqual(len(bq), 2)


if __name__ == '__main__':
    unittest.main()
