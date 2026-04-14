import os
import tempfile
import sqlite3
import unittest
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(PROJECT_ROOT, ".backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from metadata_db import MetadataDB

class TestMetadataDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_metadata.sqlite")
        self.db = MetadataDB(self.db_path)

    def tearDown(self):
        self.db.close()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Ensure tables are created upon initialization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        self.assertIn("models", tables)
        self.assertIn("generations", tables)
        self.assertIn("user_tags", tables)
        self.assertIn("embeddings", tables)

    def test_upsert_model(self):
        """Verify inserting and updating a model hash works cleanly."""
        self.db.insert_or_update_model(filename="test_model.safetensors", vault_category="checkpoints", file_hash="mock_hash123", metadata_json="{}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM models WHERE file_hash = ?", ("mock_hash123",))
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["filename"], "test_model.safetensors")
        self.assertEqual(row["vault_category"], "checkpoints")

    def test_save_generation(self):
        """Verify the generations gallery table functions correctly."""
        row_id = self.db.save_generation(
            image_path="test.png",
            prompt="A beautiful test",
            negative="",
            model="SD 1.5",
            seed=42,
            steps=20,
            cfg=7.0,
            sampler="Euler a",
            width=512,
            height=512
        )
        self.assertIsInstance(row_id, int)
        
        gens = self.db.list_generations()
        self.assertEqual(len(gens), 1)
        self.assertEqual(gens[0]["prompt"], "A beautiful test")

    def test_concurrent_writes(self):
        """S2-1: Concurrent writes should not raise 'database is locked'."""
        import threading
        errors = []

        def writer(start):
            try:
                for i in range(20):
                    self.db.insert_or_update_model(
                        filename=f"model_{start}_{i}.safetensors",
                        vault_category="checkpoints",
                        file_hash=f"hash_{start}_{i}"
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent write errors: {errors}")
        result = self.db.get_models_paginated(limit=200)
        self.assertEqual(result["total"], 80)

    def test_user_tags_no_row_factory_mutation(self):
        """S2-2: get_user_tags should not corrupt the shared row_factory."""
        self.db.insert_or_update_model("m.safetensors", "ckpt", "hash_a")
        self.db.add_user_tag("hash_a", "landscape")
        self.db.add_user_tag("hash_a", "portrait")

        tags = self.db.get_user_tags("hash_a")
        self.assertEqual(sorted(tags), ["landscape", "portrait"])

        # Verify row_factory is still sqlite3.Row (not corrupted)
        model = self.db.get_model_by_hash("hash_a")
        self.assertIsNotNone(model)
        self.assertEqual(model["filename"], "m.safetensors")

    def test_sort_allowlist_validation(self):
        """S2-7: list_generations with unknown sort defaults safely — no crash."""
        self.db.save_generation("a.png", "p1", "", "m", 1, 20, 7, "euler", 512, 512)
        self.db.save_generation("b.png", "p2", "", "m", 2, 20, 7, "euler", 512, 512)
        # Unknown sort value should not crash and should return all results
        gens = self.db.list_generations(sort="malicious; DROP TABLE--", limit=10)
        self.assertEqual(len(gens), 2)
        # Verify both entries exist (order may vary with same-timestamp inserts)
        prompts = {g["prompt"] for g in gens}
        self.assertEqual(prompts, {"p1", "p2"})

    def test_delete_generation(self):
        """Deletion under write_lock should work correctly."""
        row_id = self.db.save_generation("a.png", "p1", "", "m", 1, 20, 7, "euler", 512, 512)
        self.db.delete_generation(row_id)
        gens = self.db.list_generations()
        self.assertEqual(len(gens), 0)

    def test_favorites_crud(self):
        """Favorites add/remove with write_lock should work correctly."""
        self.db.add_favorite("12345", '{"name": "Test"}')
        favs = self.db.get_all_favorites()
        self.assertIn("12345", favs)
        self.assertEqual(favs["12345"]["name"], "Test")

        self.db.remove_favorite("12345")
        favs = self.db.get_all_favorites()
        self.assertNotIn("12345", favs)

if __name__ == '__main__':
    unittest.main()
