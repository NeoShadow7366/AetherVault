"""
Sprint 7 — Prompt Library Unit Tests
Tests CRUD operations for the prompts table in MetadataDB.
"""
import sys
import os
import tempfile
import unittest

# Add backend to import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.backend'))
from metadata_db import MetadataDB

class TestPromptLibrary(unittest.TestCase):
    """Tests for the prompts table CRUD operations."""

    def setUp(self):
        """Create a temp-file database for testing."""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, '.backend', 'metadata.sqlite')
        self.db = MetadataDB(self.db_path)

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_prompt_basic(self):
        """Test saving a basic prompt returns a row ID."""
        result = self.db.save_prompt(
            title='Test Prompt',
            prompt='a beautiful landscape, masterpiece',
            negative='ugly, blurry',
            model='sd_xl_base_1.0.safetensors'
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_save_prompt_minimal(self):
        """Test saving a prompt with only required fields."""
        result = self.db.save_prompt(
            title='Minimal Prompt',
            prompt='hello world'
        )
        self.assertIsNotNone(result)
        self.assertGreater(result, 0)

    def test_save_prompt_with_tags_and_extra(self):
        """Test saving a prompt with tags and extra_json."""
        self.db.save_prompt(
            title='Tagged Prompt',
            prompt='anime girl, cute',
            negative='bad anatomy',
            model='animagine-xl.safetensors',
            tags='anime,portrait,cute',
            extra_json='{"cfg": 7, "steps": 28}'
        )
        prompts = self.db.list_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]['tags'], 'anime,portrait,cute')

    def test_list_prompts_empty(self):
        """Test listing prompts when none exist."""
        prompts = self.db.list_prompts()
        self.assertEqual(len(prompts), 0)

    def test_list_prompts_multiple(self):
        """Test listing multiple prompts returns in order."""
        self.db.save_prompt(title='First', prompt='first prompt')
        self.db.save_prompt(title='Second', prompt='second prompt')
        self.db.save_prompt(title='Third', prompt='third prompt')
        prompts = self.db.list_prompts()
        self.assertEqual(len(prompts), 3)
        # Should be newest first (descending by created_at)
        self.assertEqual(prompts[0]['title'], 'Third')
        self.assertEqual(prompts[2]['title'], 'First')

    def test_list_prompts_search(self):
        """Test searching prompts by keyword."""
        self.db.save_prompt(title='Landscape', prompt='beautiful mountain landscape')
        self.db.save_prompt(title='Portrait', prompt='realistic portrait photo')
        self.db.save_prompt(title='Anime', prompt='anime girl cherry blossoms')
        
        results = self.db.list_prompts(search='landscape')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Landscape')

    def test_list_prompts_search_by_title(self):
        """Test searching prompts by title keyword."""
        self.db.save_prompt(title='My Landscape', prompt='generic prompt')
        self.db.save_prompt(title='My Portrait', prompt='generic prompt 2')
        
        results = self.db.list_prompts(search='Portrait')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'My Portrait')

    def test_list_prompts_search_no_results(self):
        """Test search with no matches returns empty."""
        self.db.save_prompt(title='Test', prompt='test prompt')
        results = self.db.list_prompts(search='nonexistent_query_xyz')
        self.assertEqual(len(results), 0)

    def test_delete_prompt(self):
        """Test deleting a prompt by ID."""
        row_id = self.db.save_prompt(title='To Delete', prompt='delete me')
        
        self.db.delete_prompt(row_id)
        prompts = self.db.list_prompts()
        self.assertEqual(len(prompts), 0)

    def test_delete_nonexistent_prompt(self):
        """Test deleting a prompt that doesn't exist doesn't crash."""
        # Should not raise
        self.db.delete_prompt(9999)

    def test_prompt_fields_persisted(self):
        """Test that all fields are correctly stored and retrieved."""
        self.db.save_prompt(
            title='Full Prompt',
            prompt='masterpiece, best quality, 1girl',
            negative='worst quality, low quality',
            model='animagine-xl-3.0.safetensors',
            tags='anime,girl',
            extra_json='{"sampler": "DPM++ 2M Karras"}'
        )
        
        prompts = self.db.list_prompts()
        p = prompts[0]
        self.assertEqual(p['title'], 'Full Prompt')
        self.assertEqual(p['prompt'], 'masterpiece, best quality, 1girl')
        self.assertEqual(p['negative'], 'worst quality, low quality')
        self.assertEqual(p['model'], 'animagine-xl-3.0.safetensors')
        self.assertEqual(p['tags'], 'anime,girl')

    def test_sequential_ids(self):
        """Test that IDs are assigned sequentially."""
        r1 = self.db.save_prompt(title='First', prompt='p1')
        r2 = self.db.save_prompt(title='Second', prompt='p2')
        self.assertEqual(r2, r1 + 1)


if __name__ == '__main__':
    unittest.main()
