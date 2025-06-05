"""Basic tests for claude-orchestrator"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
import shutil
import os

from claude_orchestrator.models import WorkStream, ExecutionReport
from claude_orchestrator.utils import (
    parse_workstream_section, 
    format_duration, 
    create_timestamp_suffix,
    validate_plan_file
)
from claude_orchestrator import __version__


class TestModels(unittest.TestCase):
    """Test the data models"""
    
    def test_workstream_creation(self):
        """Test WorkStream model creation"""
        ws = WorkStream(
            id=1,
            name="Test Workstream",
            description="Test description",
            tasks=["Task 1", "Task 2"],
            worktree_path="/tmp/worktree_1",
            branch_name="workstream_1"
        )
        
        self.assertEqual(ws.id, 1)
        self.assertEqual(ws.name, "Test Workstream")
        self.assertEqual(ws.status, "pending")
        self.assertIsNone(ws.duration)
        self.assertFalse(ws.is_completed)
        self.assertFalse(ws.is_running)
    
    def test_workstream_duration(self):
        """Test WorkStream duration calculation"""
        ws = WorkStream(
            id=1,
            name="Test",
            description="Test",
            tasks=[],
            worktree_path="/tmp/test",
            branch_name="test"
        )
        
        ws.start_time = 100.0
        ws.end_time = 163.5
        
        self.assertEqual(ws.duration, 63.5)
        self.assertEqual(ws.format_duration(), "1m 3s")
    
    def test_execution_report(self):
        """Test ExecutionReport model"""
        ws1 = WorkStream(
            id=1, name="WS1", description="", tasks=[],
            worktree_path="", branch_name="", status="completed"
        )
        ws2 = WorkStream(
            id=2, name="WS2", description="", tasks=[],
            worktree_path="", branch_name="", status="failed"
        )
        
        report = ExecutionReport(
            workstreams=[ws1, ws2],
            opus_model="claude-opus-4",
            sonnet_model="claude-sonnet-4"
        )
        
        self.assertEqual(report.total_workstreams, 2)
        self.assertEqual(report.successful_workstreams, 1)
        self.assertEqual(report.failed_workstreams, 1)
        self.assertEqual(report.success_rate, 50.0)
        
        # Test markdown generation
        markdown = report.to_markdown()
        self.assertIn("# Parallel Claude Code Execution Report", markdown)
        self.assertIn("Total Workstreams: 2", markdown)
        self.assertIn("Success Rate: 50.0%", markdown)


class TestUtils(unittest.TestCase):
    """Test utility functions"""
    
    def test_parse_workstream_section(self):
        """Test parsing workstream sections from markdown"""
        content = """
### Workstream 1: Frontend Development
**Description**: Build the user interface
**Tasks**:
- Create React components
- Add styling
- Implement routing

### Workstream 2: Backend API
**Description**: Create REST API
**Tasks**:
- Setup Express server
- Create endpoints
"""
        
        workstreams = parse_workstream_section(content)
        
        self.assertEqual(len(workstreams), 2)
        
        # Check first workstream
        ws1_id, ws1_name, ws1_desc, ws1_tasks = workstreams[0]
        self.assertEqual(ws1_id, 1)
        self.assertEqual(ws1_name, "Frontend Development")
        self.assertEqual(ws1_desc, "Build the user interface")
        self.assertEqual(len(ws1_tasks), 3)
        self.assertEqual(ws1_tasks[0], "Create React components")
    
    def test_format_duration(self):
        """Test duration formatting"""
        self.assertEqual(format_duration(45.5), "45.5s")
        self.assertEqual(format_duration(90), "1m 30s")
        self.assertEqual(format_duration(3700), "1h 1m")
    
    def test_create_timestamp_suffix(self):
        """Test timestamp suffix creation"""
        suffix = create_timestamp_suffix()
        # Should be in format YYYYMMDD_HHMMSS
        self.assertEqual(len(suffix), 15)
        self.assertEqual(suffix[8], "_")
    
    def test_validate_plan_file(self):
        """Test plan file validation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""
### Workstream 1: Test
**Description**: Test workstream
**Tasks**:
- Task 1
""")
            temp_path = Path(f.name)
        
        try:
            # Valid plan file
            self.assertTrue(validate_plan_file(temp_path))
            
            # Empty file
            temp_path.write_text("")
            self.assertFalse(validate_plan_file(temp_path))
            
            # Non-existent file
            temp_path.unlink()
            self.assertFalse(validate_plan_file(temp_path))
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestVersion(unittest.TestCase):
    """Test package versioning"""
    
    def test_version_format(self):
        """Test that version follows semantic versioning"""
        parts = __version__.split('.')
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())


class TestGitInitialization(unittest.TestCase):
    """Test automatic git repository initialization"""
    
    def setUp(self):
        """Create a temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('claude_orchestrator.utils.check_claude_cli')
    @patch('claude_orchestrator.utils.run_command')
    def test_git_init_when_no_repo(self, mock_run_command, mock_check_claude):
        """Test that git repo is initialized when not present"""
        # Mock claude check to fail (returns None)
        mock_check_claude.return_value = None
        
        # Mock git version check
        mock_run_command.side_effect = [
            Mock(returncode=0, stdout="git version 2.30.0"),  # git --version
            Mock(returncode=128),  # git rev-parse --git-dir (fails, no repo)
            Mock(returncode=0),  # git init
            Mock(returncode=0, stdout=""),  # git config user.name
            Mock(returncode=0),  # git config user.name "..."
            Mock(returncode=0, stdout=""),  # git config user.email
            Mock(returncode=0),  # git config user.email "..."
            Mock(returncode=0, stdout="file1.txt\nfile2.py"),  # git ls-files
            Mock(returncode=0),  # git add .
            Mock(returncode=0),  # git commit
        ]
        
        from claude_orchestrator.utils import check_prerequisites
        
        # Should raise exception about missing claude
        with self.assertRaises(RuntimeError) as cm:
            check_prerequisites()
        
        self.assertIn("Claude Code CLI is not installed", str(cm.exception))
        
        # Verify git init was called
        init_call = [call for call in mock_run_command.call_args_list if call[0][0] == ["git", "init"]]
        self.assertEqual(len(init_call), 1)


if __name__ == '__main__':
    unittest.main()
