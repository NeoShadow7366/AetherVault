import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add .backend to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(PROJECT_ROOT, ".backend") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, ".backend"))

import updater

class TestOTAUpdater(unittest.TestCase):
    
    @patch('updater.subprocess.run')
    @patch('updater.os.path.exists')
    @patch('updater.subprocess.Popen')
    def test_git_pull_branch(self, mock_popen, mock_exists, mock_run):
        """Test that updater triggers 'git pull' if .git exists."""
        # Setup mocks
        def exists_side_effect(path):
            if path.endswith('.git'):
                return True
            if path.endswith('start_manager.sh') or path.endswith('start_manager.bat'):
                return True
            return False
            
        mock_exists.side_effect = exists_side_effect
        mock_run.return_value = MagicMock(returncode=0, stdout="Mock pull", stderr="")
        
        # We don't want to actually try and kill a pid, so patch it
        with patch('updater.force_kill_pid'):
            updater.run_update(999999)
            
        # Assert git pull was called
        mock_run.assert_called_with(["git", "pull"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        # Assert restart script was called
        mock_popen.assert_called_once()
    
    @patch('updater.fetch_and_extract_release')
    @patch('updater.os.path.exists')
    @patch('updater.subprocess.Popen')
    def test_standalone_zip_branch(self, mock_popen, mock_exists, mock_fetch):
        """Test that updater falls back to ZIP extraction if .git is missing."""
        def exists_side_effect(path):
            if path.endswith('.git'):
                return False
            if path.endswith('start_manager.sh') or path.endswith('start_manager.bat'):
                return True
            return False
            
        mock_exists.side_effect = exists_side_effect
        
        with patch('updater.force_kill_pid'):
            updater.run_update(999999)
            
        mock_fetch.assert_called_once_with(PROJECT_ROOT)
        mock_popen.assert_called_once()

    @patch('updater.subprocess.run')
    def test_force_kill_pid_windows(self, mock_run):
        """Test the process termination behavior on Windows."""
        with patch('updater.os.name', 'nt'):
            with patch('updater.time.sleep'): # skip sleep
                updater.force_kill_pid(1234)
                mock_run.assert_called_with(["taskkill", "/F", "/PID", "1234"], capture_output=True)

    @patch('updater.os.kill')
    def test_force_kill_pid_unix(self, mock_kill):
        """Test the process termination behavior on UNIX."""
        with patch('updater.os.name', 'posix'):
            with patch('updater.time.sleep'): # skip sleep
                import signal
                updater.force_kill_pid(1234)
                mock_kill.assert_called_with(1234, signal.SIGTERM)

if __name__ == '__main__':
    unittest.main()
