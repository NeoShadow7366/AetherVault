"""Unit tests for ProcessRegistry — thread-safe subprocess lifecycle manager.

Tests cover:
- Registration and retrieval
- is_running / count_running with mock processes
- kill() with process tree termination
- kill_all() for graceful teardown
- cleanup_dead() for stale process removal
- Thread safety under concurrent access
"""
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.backend'))
from process_registry import ProcessRegistry


class MockProcess:
    """Simulates subprocess.Popen for testing."""
    def __init__(self, alive=True, pid=12345):
        self.pid = pid
        self._alive = alive
        self._killed = False

    def poll(self):
        if self._killed or not self._alive:
            return 0  # process exited
        return None  # still running

    def send_signal(self, sig):
        self._killed = True

    def kill(self):
        self._killed = True

    def wait(self, timeout=None):
        self._killed = True
        return 0


class TestProcessRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ProcessRegistry()

    def test_register_and_get(self):
        """Registered process should be retrievable."""
        proc = MockProcess()
        self.registry.register("comfyui", proc, port=8188)
        entry = self.registry.get("comfyui")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["port"], 8188)
        self.assertEqual(entry["process"], proc)

    def test_get_nonexistent(self):
        """Getting a non-existent entry returns None."""
        self.assertIsNone(self.registry.get("nonexistent"))

    def test_is_running_alive(self):
        """is_running returns True for a living process."""
        proc = MockProcess(alive=True)
        self.registry.register("forge", proc)
        self.assertTrue(self.registry.is_running("forge"))

    def test_is_running_dead(self):
        """is_running returns False for a dead process."""
        proc = MockProcess(alive=False)
        self.registry.register("forge", proc)
        self.assertFalse(self.registry.is_running("forge"))

    def test_is_running_not_tracked(self):
        """is_running returns False for untracked package."""
        self.assertFalse(self.registry.is_running("unknown"))

    def test_get_port(self):
        """get_port returns the registered port."""
        proc = MockProcess()
        self.registry.register("a1111", proc, port=7861)
        self.assertEqual(self.registry.get_port("a1111"), 7861)

    def test_get_port_missing(self):
        """get_port returns None for untracked package."""
        self.assertIsNone(self.registry.get_port("unknown"))

    def test_count_running(self):
        """count_running reflects only alive processes."""
        self.registry.register("a", MockProcess(alive=True))
        self.registry.register("b", MockProcess(alive=False))
        self.registry.register("c", MockProcess(alive=True))
        self.assertEqual(self.registry.count_running(), 2)

    def test_list_running(self):
        """list_running returns (id, port) tuples for alive processes."""
        self.registry.register("a", MockProcess(alive=True), port=8000)
        self.registry.register("b", MockProcess(alive=False), port=8001)
        running = self.registry.list_running()
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0], ("a", 8000))

    @patch('process_registry.subprocess')
    def test_kill_on_windows(self, mock_subprocess):
        """kill() uses taskkill /T on Windows."""
        proc = MockProcess(alive=True, pid=9999)
        self.registry.register("comfyui", proc)
        with patch('process_registry.os.name', 'nt'):
            result = self.registry.kill("comfyui")
        self.assertTrue(result)
        mock_subprocess.run.assert_called_once()
        args = mock_subprocess.run.call_args[0][0]
        self.assertIn('/PID', args)
        self.assertIn('9999', args)

    def test_kill_removes_entry(self):
        """kill() removes the entry from the registry."""
        proc = MockProcess(alive=True)
        self.registry.register("comfyui", proc)
        self.registry.kill("comfyui")
        self.assertIsNone(self.registry.get("comfyui"))

    def test_kill_nonexistent(self):
        """kill() returns False for untracked package."""
        self.assertFalse(self.registry.kill("nonexistent"))

    def test_kill_closes_log_file(self):
        """kill() closes the associated log file handle."""
        proc = MockProcess(alive=True)
        log_file = MagicMock()
        self.registry.register("comfyui", proc, log_file=log_file)
        with patch('process_registry.os.name', 'posix'):
            self.registry.kill("comfyui")
        log_file.close.assert_called_once()

    def test_kill_all(self):
        """kill_all() kills all processes and clears registry."""
        self.registry.register("a", MockProcess(alive=True))
        self.registry.register("b", MockProcess(alive=True))
        self.registry.register("c", MockProcess(alive=False))
        with patch('process_registry.os.name', 'posix'):
            killed = self.registry.kill_all()
        self.assertEqual(killed, 2)
        self.assertEqual(len(self.registry), 0)

    def test_cleanup_dead(self):
        """cleanup_dead() removes dead processes, keeps alive ones."""
        self.registry.register("alive", MockProcess(alive=True))
        self.registry.register("dead", MockProcess(alive=False))
        cleaned = self.registry.cleanup_dead()
        self.assertEqual(cleaned, ["dead"])
        self.assertTrue(self.registry.is_running("alive"))
        self.assertIsNone(self.registry.get("dead"))

    def test_contains(self):
        """__contains__ works for tracked packages."""
        self.registry.register("x", MockProcess())
        self.assertIn("x", self.registry)
        self.assertNotIn("y", self.registry)

    def test_len(self):
        """__len__ returns total tracked entries (alive + dead)."""
        self.registry.register("a", MockProcess(alive=True))
        self.registry.register("b", MockProcess(alive=False))
        self.assertEqual(len(self.registry), 2)

    def test_thread_safety_concurrent_register(self):
        """Concurrent registrations should not corrupt the registry."""
        errors = []

        def register_batch(start, count):
            try:
                for i in range(count):
                    self.registry.register(f"pkg_{start + i}", MockProcess(), port=start + i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_batch, args=(i * 100, 50)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(self.registry), 200)

    def test_get_returns_copy(self):
        """get() returns a copy — mutations don't affect the registry."""
        proc = MockProcess()
        self.registry.register("x", proc, port=8000)
        entry = self.registry.get("x")
        entry["port"] = 9999
        self.assertEqual(self.registry.get_port("x"), 8000)


if __name__ == '__main__':
    unittest.main()
