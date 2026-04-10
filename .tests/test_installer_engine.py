import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import shutil
import sys
import json

# Allow import of backend module
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(current_dir), ".backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from installer_engine import RecipeInstaller

class TestInstallerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.installer = RecipeInstaller(self.temp_dir)
        
        # Write dummy recipe
        self.recipe_path = os.path.join(self.temp_dir, "test_recipe.json")
        self.recipe_data = {
            "app_id": "comfyui_test",
            "name": "ComfyUI Mock",
            "repository": "https://github.com/mock/comfyui",
            "install_commands": [
                "pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121"
            ],
            "model_symlinks": {
                "checkpoints": "models/checkpoints"
            }
        }
        with open(self.recipe_path, 'w') as f:
            json.dump(self.recipe_data, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("installer_engine.subprocess.Popen")
    @patch("installer_engine.subprocess.run")
    def test_installation_pipeline(self, mock_subprocess_run, mock_popen):
        """Verify the entire installer parsing creates the requested directory tree and mock subprocess cmds."""
        # Mock subprocess.run for git --version pre-flight, venv creation, pip upgrade, and pip install
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        # Mock subprocess.Popen for the streaming git clone (_run_git_clone_with_progress)
        mock_proc = MagicMock()
        mock_proc.stderr = MagicMock()
        # Simulate git progress output ending immediately (empty read)
        mock_proc.stderr.read = MagicMock(return_value=b"")
        mock_proc.stdout = MagicMock()
        mock_proc.stdout.read = MagicMock(return_value=b"")
        mock_proc.wait = MagicMock(return_value=0)
        mock_proc.returncode = 0
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc
        
        result = self.installer.install(self.recipe_path)
        self.assertTrue(result)
        
        # Verify folder generation
        app_base = os.path.join(self.temp_dir, "packages", "comfyui_test")
        self.assertTrue(os.path.exists(app_base))
        
        # Verify Vault created the checkpoint dir natively before mapping
        source_vault = os.path.join(self.temp_dir, "Global_Vault", "checkpoints")
        self.assertTrue(os.path.exists(source_vault))
        
        # Verify Manifest
        manifest_path = os.path.join(app_base, "manifest.json")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, 'r') as f:
            manifest_json = json.load(f)
            self.assertEqual(manifest_json["name"], "ComfyUI Mock")
            
        # Verify Popen was called for the clone phase
        self.assertGreaterEqual(mock_popen.call_count, 1)
        clone_cmd = mock_popen.call_args_list[0][0][0]
        self.assertIn("clone", clone_cmd)
        self.assertIn("https://github.com/mock/comfyui", clone_cmd)
        
        # Verify subprocess.run was called for venv + pip phases
        # Calls: git --version (pre-flight), venv creation, pip upgrade, pip install
        self.assertGreaterEqual(mock_subprocess_run.call_count, 2)
        run_calls = mock_subprocess_run.call_args_list
        
        # First run call is git --version pre-flight check
        self.assertIn("git", run_calls[0][0][0])
        
        # Second run call is venv creation
        self.assertIn("venv", run_calls[1][0][0])

    def test_uninstallation_wipes_isolated_environment(self):
        """Verify `rmtree` removes the virtual environment wrapper securely."""
        app_base = os.path.join(self.temp_dir, "packages", "comfyui_test")
        os.makedirs(app_base, exist_ok=True)
        # Dummy file
        with open(os.path.join(app_base, "manifest.json"), 'w') as f:
            f.write("{}")
            
        result = self.installer.uninstall("comfyui_test")
        self.assertTrue(result)
        self.assertFalse(os.path.exists(app_base))

    def test_uninstallation_wipes_readonly_environment(self):
        """Verify `rmtree` removes read-only files dynamically via the onerror chmod override."""
        import stat
        app_base = os.path.join(self.temp_dir, "packages", "readonly_test")
        os.makedirs(app_base, exist_ok=True)
        # Dummy file lock
        filepath = os.path.join(app_base, "readonly_file.txt")
        with open(filepath, 'w') as f:
            f.write("strict")
        # Ensure it is locked
        os.chmod(filepath, stat.S_IREAD)
        
        result = self.installer.uninstall("readonly_test")
        self.assertTrue(result)
        self.assertFalse(os.path.exists(app_base))

if __name__ == '__main__':
    unittest.main()
