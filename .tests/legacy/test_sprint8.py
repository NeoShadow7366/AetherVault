"""Sprint 8 — Unit Tests for Production Hardening Features.

Tests cover:
  1. ExtensionCloneTracker — job CRUD, status polling, cancel
  2. MetadataDB — export_models_metadata, get_dashboard_stats
  3. Vault export endpoint response structure
"""
import os
import sys
import json
import sqlite3
import tempfile
import unittest

# Make .backend importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from installer_engine import ExtensionCloneTracker
from metadata_db import MetadataDB


class TestExtensionCloneTracker(unittest.TestCase):
    """Tests for the extension clone progress tracking system."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, ".backend", "cache"), exist_ok=True)
        self.tracker = ExtensionCloneTracker(self.tmpdir)

    def test_jobs_file_init(self):
        """Jobs file path is set correctly."""
        expected = os.path.join(self.tmpdir, ".backend", "cache", "extension_jobs.json")
        self.assertEqual(self.tracker.jobs_file, expected)

    def test_empty_jobs(self):
        """Reading jobs when no file exists returns empty dict."""
        result = self.tracker._read_jobs()
        self.assertEqual(result, {})

    def test_write_and_read_jobs(self):
        """Writing then reading jobs round-trips correctly."""
        jobs = {"test-123": {"status": "cloning", "percent": 42}}
        self.tracker._write_jobs(jobs)
        result = self.tracker._read_jobs()
        self.assertEqual(result["test-123"]["status"], "cloning")
        self.assertEqual(result["test-123"]["percent"], 42)

    def test_update_job_creates_new(self):
        """update_job creates a new entry if it doesn't exist."""
        self.tracker._update_job("new-job", {"status": "cloning", "percent": 0})
        job = self.tracker.get_job_status("new-job")
        self.assertEqual(job["status"], "cloning")

    def test_update_job_merges(self):
        """update_job merges new data into existing job."""
        self.tracker._update_job("j1", {"status": "cloning", "percent": 10})
        self.tracker._update_job("j1", {"percent": 75, "progress_text": "Receiving objects"})
        job = self.tracker.get_job_status("j1")
        self.assertEqual(job["status"], "cloning")
        self.assertEqual(job["percent"], 75)
        self.assertEqual(job["progress_text"], "Receiving objects")

    def test_get_nonexistent_job(self):
        """Getting a non-existent job returns empty dict."""
        result = self.tracker.get_job_status("nonexistent")
        self.assertEqual(result, {})

    def test_cancel_no_pid(self):
        """Cancelling a job with no PID returns False."""
        self.tracker._update_job("j2", {"status": "cloning", "pid": None})
        result = self.tracker.cancel_job("j2")
        self.assertFalse(result)

    def test_cancel_nonexistent(self):
        """Cancelling a non-existent job returns False."""
        result = self.tracker.cancel_job("does-not-exist")
        self.assertFalse(result)

    def test_progress_regex(self):
        """The progress regex correctly parses git clone output."""
        test_lines = [
            ("Receiving objects:  42% (100/238)", 42),
            ("Resolving deltas: 100% (50/50)", 100),
            ("Counting objects:   5% (1/20)", 5),
        ]
        for line, expected_pct in test_lines:
            match = self.tracker._PROGRESS_RE.search(line)
            self.assertIsNotNone(match, f"Failed to match: {line}")
            self.assertEqual(int(match.group(2)), expected_pct)


class TestMetadataDBExport(unittest.TestCase):
    """Tests for MetadataDB export and analytics methods."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "metadata.sqlite")
        self.db = MetadataDB(self.db_path)

        # Insert some test model data
        conn = sqlite3.connect(self.db_path)
        conn.execute("""INSERT INTO models (filename, file_hash, vault_category, metadata_json, thumbnail_path)
                        VALUES (?, ?, ?, ?, ?)""",
                     ("test_model.safetensors", "abc123", "checkpoints", '{"model": {"name": "TestModel"}}', ""))
        conn.execute("""INSERT INTO models (filename, file_hash, vault_category, metadata_json, thumbnail_path)
                        VALUES (?, ?, ?, ?, ?)""",
                     ("test_lora.safetensors", "def456", "loras", '{}', ""))
        conn.commit()
        conn.close()

    def test_export_models_metadata(self):
        """export_models_metadata returns correct data for given filenames."""
        result = self.db.export_models_metadata(["test_model.safetensors"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "test_model.safetensors")
        self.assertEqual(result[0]["vault_category"], "checkpoints")

    def test_export_empty_list(self):
        """Passing empty list returns empty result."""
        result = self.db.export_models_metadata([])
        self.assertEqual(result, [])

    def test_export_nonexistent(self):
        """Passing non-existent filename returns empty result."""
        result = self.db.export_models_metadata(["nonexistent.bin"])
        self.assertEqual(result, [])

    def test_export_multiple(self):
        """Exporting multiple models returns all matches."""
        result = self.db.export_models_metadata(["test_model.safetensors", "test_lora.safetensors"])
        self.assertEqual(len(result), 2)
        filenames = {r["filename"] for r in result}
        self.assertIn("test_model.safetensors", filenames)
        self.assertIn("test_lora.safetensors", filenames)

    def test_dashboard_stats(self):
        """get_dashboard_stats returns correct aggregate counts."""
        stats = self.db.get_dashboard_stats()
        self.assertIn("total_models", stats)
        self.assertIn("total_generations", stats)
        self.assertIn("prompts_saved", stats)
        self.assertEqual(stats["total_models"], 2)
        self.assertEqual(stats["total_generations"], 0)
        self.assertEqual(stats["prompts_saved"], 0)

    def test_dashboard_stats_with_generations(self):
        """Dashboard stats updates after adding generations."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""INSERT INTO generations (image_path, prompt, negative, model, seed, steps, cfg, width, height, extra_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     ("/img/test.png", "a cat", "", "TestModel", 42, 20, 7.0, 512, 512, "{}"))
        conn.commit()
        conn.close()
        stats = self.db.get_dashboard_stats()
        self.assertEqual(stats["total_generations"], 1)

    def test_dashboard_stats_with_prompts(self):
        """Dashboard stats updates after adding prompts."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO prompts (title, prompt, negative) VALUES (?, ?, ?)",
                     ("Test", "a cat", "blurry"))
        conn.commit()
        conn.close()
        stats = self.db.get_dashboard_stats()
        self.assertEqual(stats["prompts_saved"], 1)


class TestCommandPaletteHTML(unittest.TestCase):
    """Test that the command palette HTML structure exists in index.html."""

    def setUp(self):
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            self.html = f.read()

    def test_command_palette_overlay(self):
        """Command palette overlay div exists."""
        self.assertIn('id="command-palette"', self.html)
        self.assertIn('cmd-palette-overlay', self.html)

    def test_command_palette_input(self):
        """Command palette search input exists."""
        self.assertIn('id="cmd-search"', self.html)

    def test_keyboard_shortcut(self):
        """Ctrl+K keyboard shortcut is wired."""
        self.assertIn("e.key === 'k'", self.html)
        self.assertIn("e.ctrlKey || e.metaKey", self.html)

    def test_dashboard_view(self):
        """Dashboard tab and view exist."""
        self.assertIn('id="view-dashboard"', self.html)
        self.assertIn("switchTab('dashboard'", self.html)

    def test_dashboard_cards(self):
        """Dashboard analytics cards exist."""
        self.assertIn('id="dash-models"', self.html)
        self.assertIn('id="dash-generations"', self.html)
        self.assertIn('id="dash-vault-size"', self.html)
        self.assertIn('id="dash-packages"', self.html)

    def test_extension_progress_bar(self):
        """Extension progress bar elements exist."""
        self.assertIn('id="ext-progress-container"', self.html)
        self.assertIn('id="ext-progress-bar"', self.html)
        self.assertIn('id="ext-log-output"', self.html)

    def test_export_dialog(self):
        """Vault export dialog exists."""
        self.assertIn('id="export-dialog"', self.html)
        self.assertIn('id="export-include-files"', self.html)

    def test_export_button_in_action_bar(self):
        """Export button exists in vault action bar."""
        self.assertIn('executeVaultExport()', self.html)


if __name__ == "__main__":
    unittest.main()
