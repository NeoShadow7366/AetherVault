"""Thread-safe process registry for subprocess lifecycle management.

Replaces the unprotected dict-based tracking in AIWebServer with a
properly-locked container that prevents race conditions between launch,
stop, restart, uninstall, and status-check handlers running on concurrent
ThreadingHTTPServer threads.
"""
import os
import sys
import signal
import subprocess
import threading
import logging


class ProcessRegistry:
    """Thread-safe registry for tracked subprocess lifecycle.

    All mutations are serialized via an internal lock to prevent races
    between concurrent HTTP handler threads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._processes: dict = {}

    def register(self, package_id: str, process, log_file=None, port: int = 7860) -> None:
        """Register a newly-launched process."""
        with self._lock:
            self._processes[package_id] = {
                "process": process,
                "log_file": log_file,
                "port": port
            }

    def get(self, package_id: str) -> dict | None:
        """Get a process entry by ID. Returns a copy to prevent mutation."""
        with self._lock:
            entry = self._processes.get(package_id)
            return dict(entry) if entry else None

    def is_running(self, package_id: str) -> bool:
        """Check if a process is tracked and alive."""
        with self._lock:
            entry = self._processes.get(package_id)
            if not entry:
                return False
            proc = entry.get("process")
            return proc is not None and proc.poll() is None

    def get_port(self, package_id: str) -> int | None:
        """Get the port of a tracked process."""
        with self._lock:
            entry = self._processes.get(package_id)
            if entry:
                return entry.get("port")
            return None

    def kill(self, package_id: str, remove: bool = True) -> bool:
        """Kill a tracked process. Returns True if something was killed.

        Handles both Windows (taskkill /T for process tree) and UNIX
        (SIGTERM with fallback to SIGKILL) termination patterns.
        """
        with self._lock:
            entry = self._processes.get(package_id)
            if not entry:
                return False

            proc = entry.get("process")
            log_file = entry.get("log_file")
            killed = False

            if proc and proc.poll() is None:
                try:
                    if os.name == 'nt':
                        subprocess.run(
                            ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                            check=False, capture_output=True
                        )
                    else:
                        proc.send_signal(signal.SIGTERM)
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                    killed = True
                except Exception as e:
                    logging.error(f"Error killing {package_id}: {e}")

            # Close log file handle
            if log_file:
                try:
                    log_file.close()
                except Exception:
                    pass

            if remove:
                self._processes.pop(package_id, None)

            return killed

    def kill_all(self) -> int:
        """Kill all tracked processes. Returns count killed.
        Used during graceful_teardown."""
        killed_count = 0
        with self._lock:
            for package_id in list(self._processes.keys()):
                entry = self._processes[package_id]
                proc = entry.get("process")
                if proc and proc.poll() is None:
                    try:
                        if os.name == 'nt':
                            subprocess.call(
                                ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                creationflags=0x08000000
                            )
                        else:
                            proc.kill()
                        killed_count += 1
                        logging.info(f"[TEARDOWN] Killed sandbox '{package_id}' (PID {proc.pid})")
                    except Exception as e:
                        logging.warning(f"[TEARDOWN] Failed to kill {package_id}: {e}")

                # Close log file
                log_file = entry.get("log_file")
                if log_file:
                    try:
                        log_file.close()
                    except Exception:
                        pass

            self._processes.clear()
        return killed_count

    def list_running(self) -> list:
        """Return list of (package_id, port) for all alive processes."""
        with self._lock:
            result = []
            for pid, entry in self._processes.items():
                proc = entry.get("process")
                if proc and proc.poll() is None:
                    result.append((pid, entry.get("port")))
            return result

    def count_running(self) -> int:
        """Count of currently-alive processes."""
        with self._lock:
            return sum(
                1 for entry in self._processes.values()
                if entry.get("process") and entry["process"].poll() is None
            )

    def cleanup_dead(self) -> list:
        """Remove entries for processes that have exited.
        Returns list of cleaned-up package_ids.
        Closes leaked log file handles."""
        cleaned = []
        with self._lock:
            for pid in list(self._processes.keys()):
                entry = self._processes[pid]
                proc = entry.get("process")
                if proc and proc.poll() is not None:
                    # Process is dead — clean up
                    log_file = entry.get("log_file")
                    if log_file:
                        try:
                            log_file.close()
                        except Exception:
                            pass
                    del self._processes[pid]
                    cleaned.append(pid)
        return cleaned

    def __contains__(self, package_id: str) -> bool:
        with self._lock:
            return package_id in self._processes

    def __len__(self) -> int:
        with self._lock:
            return len(self._processes)
