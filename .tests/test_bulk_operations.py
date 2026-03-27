"""
Sprint 7 — Bulk Operations Unit Tests
Tests the batch model deletion logic in MetadataDB.
"""
import sys
import os
import tempfile
import shutil
import unittest

# Add backend to import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.backend'))
from metadata_db import MetadataDB

class TestBulkOperations(unittest.TestCase):
    """Tests for vault bulk deletion operations."""

    def setUp(self):
        """Create a temp-file database with seed models."""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, '.backend', 'metadata.sqlite')
        self.db = MetadataDB(self.db_path)
        # Insert several test models using the DB's own method
        for i in range(5):
            self.db.insert_or_update_model(
                filename=f"model_{i}.safetensors",
                vault_category="checkpoints",
                file_hash=f"hash_{i}",
                metadata_json=None,
                thumbnail_path=None
            )

    def tearDown(self):
        """Clean up temp files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _count_models(self):
        """Helper: count models in DB."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        conn.close()
        return count

    def test_seed_data(self):
        """Verify seed data was inserted."""
        self.assertEqual(self._count_models(), 5)

    def test_remove_models_by_filenames_basic(self):
        """Test removing a single model by filename."""
        result = self.db.remove_models_by_filenames(['model_0.safetensors'])
        self.assertEqual(result, 1)
        self.assertEqual(self._count_models(), 4)

    def test_remove_models_by_filenames_multiple(self):
        """Test removing multiple models."""
        result = self.db.remove_models_by_filenames([
            'model_0.safetensors',
            'model_2.safetensors',
            'model_4.safetensors'
        ])
        self.assertEqual(result, 3)
        self.assertEqual(self._count_models(), 2)

    def test_remove_models_by_filenames_none(self):
        """Test removing empty list returns zero."""
        result = self.db.remove_models_by_filenames([])
        self.assertEqual(result, 0)
        self.assertEqual(self._count_models(), 5)

    def test_remove_models_by_filenames_nonexistent(self):
        """Test removing nonexistent models returns zero deletes."""
        result = self.db.remove_models_by_filenames(['nonexistent.safetensors'])
        self.assertEqual(result, 0)
        self.assertEqual(self._count_models(), 5)

    def test_remove_models_by_filenames_mixed(self):
        """Test removing mix of existing and nonexistent models."""
        result = self.db.remove_models_by_filenames([
            'model_1.safetensors',
            'nonexistent.safetensors',
            'model_3.safetensors'
        ])
        self.assertEqual(result, 2)
        self.assertEqual(self._count_models(), 3)

    def test_remove_preserves_other_models(self):
        """Test that deletion doesn't affect unrelated models."""
        self.db.remove_models_by_filenames(['model_0.safetensors'])
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        for i in range(1, 5):
            count = conn.execute("SELECT COUNT(*) FROM models WHERE filename = ?", (f"model_{i}.safetensors",)).fetchone()[0]
            self.assertEqual(count, 1, f"model_{i}.safetensors should still exist")
        conn.close()

    def test_remove_all_models(self):
        """Test removing all models."""
        all_names = [f"model_{i}.safetensors" for i in range(5)]
        result = self.db.remove_models_by_filenames(all_names)
        self.assertEqual(result, 5)
        self.assertEqual(self._count_models(), 0)


if __name__ == '__main__':
    unittest.main()
