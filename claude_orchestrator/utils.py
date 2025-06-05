"""Utility functions for Claude Orchestrator"""

import os
import sys
import subprocess
import logging
import re
import threading
import queue
import time
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import PLAN_FILE, LOG_FILE


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def run_command(
    cmd: List[str], 
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    check: bool = False
) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory for command
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        
    Returns:
        Completed process result
    """
    cwd = cwd or Path.cwd()
    logger = logging.getLogger(__name__)
    logger.debug(f"Running command: {' '.join(cmd)} in {cwd}")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)
        else:
            result = subprocess.run(cmd, cwd=cwd, check=check)
    except FileNotFoundError:
        # Command not found
        logger.error(f"Command not found: {cmd[0]}")
        # Create a fake result to match subprocess behavior
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=127,  # Standard "command not found" exit code
            stdout="" if capture_output else None,
            stderr=f"Command not found: {cmd[0]}" if capture_output else None
        )
    except subprocess.CalledProcessError as e:
        # Command failed with non-zero exit
        result = e
        if capture_output:
            logger.error(f"Command failed: {e.stderr}")
    
    if result.returncode != 0 and capture_output and not check:
        logger.debug(f"Command exited with code {result.returncode}: {result.stderr}")
    
    return result


def check_prerequisites() -> None:
    """
    Check that all prerequisites are met
    
    Raises:
        RuntimeError: If any prerequisite is not met
    """
    logger = logging.getLogger(__name__)
    
    # Check if git is available first
    result = run_command(["git", "--version"])
    if result.returncode != 0:
        raise RuntimeError("Git is not installed or not in PATH")
    
    # Check git version for worktree support (2.5+)
    version_match = re.search(r'git version (\d+)\.(\d+)', result.stdout)
    if version_match:
        major, minor = int(version_match.group(1)), int(version_match.group(2))
        if major < 2 or (major == 2 and minor < 5):
            raise RuntimeError("Git version 2.5+ required for worktree support")
    
    # Check if we're in a git repository using git rev-parse
    result = run_command(["git", "rev-parse", "--git-dir"])
    if result.returncode != 0:
        logger.info("No git repository found. Initializing a new repository...")
        
        # Get the current directory name for the repo
        repo_name = Path.cwd().name
        
        # Initialize git repository
        result = run_command(["git", "init"])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to initialize git repository: {result.stderr}")
        
        # Configure git user if not already configured
        user_name = run_command(["git", "config", "user.name"])
        if not user_name.stdout.strip():
            run_command(["git", "config", "user.name", "Claude Orchestrator User"])
        
        user_email = run_command(["git", "config", "user.email"])
        if not user_email.stdout.strip():
            run_command(["git", "config", "user.email", "claude-orchestrator@example.com"])
        
        # Create an initial commit if there are files
        files_to_add = run_command(["git", "ls-files", "--others", "--exclude-standard"])
        if files_to_add.stdout.strip():
            # Add all files
            run_command(["git", "add", "."])
            # Create initial commit
            run_command(["git", "commit", "-m", f"Initial commit for {repo_name}"])
            logger.info(f"Git repository initialized with initial commit for project: {repo_name}")
        else:
            # Create an empty initial commit
            run_command(["git", "commit", "--allow-empty", "-m", f"Initial commit for {repo_name}"])
            logger.info(f"Git repository initialized with empty commit for project: {repo_name}")
    else:
        # We're in a git repo, check if we have any commits
        result = run_command(["git", "rev-list", "-n", "1", "--all"])
        if result.returncode != 0 or not result.stdout.strip():
            logger.info("Git repository exists but has no commits. Creating initial commit...")
            # Create an empty initial commit
            run_command(["git", "commit", "--allow-empty", "-m", "Initial commit"])
    
    # Check if claude is available
    claude_path = check_claude_cli()
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI is not installed or not in PATH.\n"
            "Please install it from: https://claude.ai/download\n"
            "Or ensure it's in your PATH if already installed."
        )
    
    # Store the claude path for later use
    os.environ['CLAUDE_ORCHESTRATOR_CLI_PATH'] = claude_path


def parse_workstream_section(content: str) -> List[Tuple[int, str, str, List[str]]]:
    """
    Parse workstream sections from PLAN.md content
    
    Args:
        content: The markdown content to parse
        
    Returns:
        List of tuples: (id, name, description, tasks)
    """
    # More flexible pattern that handles optional Dependencies and Provides fields
    workstream_pattern = (
        r'### Workstream (\d+): (.+?)\n'
        r'\*\*Description\*\*: (.+?)\n'
        r'(?:\*\*Dependencies\*\*: .+?\n)?'  # Optional dependencies
        r'(?:\*\*Provides\*\*: .+?\n)?'      # Optional provides
        r'\*\*Tasks\*\*:\n'
        r'((?:- .+\n)+)'
    )
    
    matches = re.finditer(workstream_pattern, content, re.MULTILINE)
    workstreams = []
    
    for match in matches:
        ws_id = int(match.group(1))
        ws_name = match.group(2).strip()
        ws_desc = match.group(3).strip()
        ws_tasks = [
            task.strip('- ').strip() 
            for task in match.group(4).strip().split('\n')
        ]
        
        workstreams.append((ws_id, ws_name, ws_desc, ws_tasks))
    
    return workstreams


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def ensure_clean_worktree(worktree_path: str, force: bool = True) -> None:
    """
    Ensure a worktree path is clean (remove if exists)
    
    Args:
        worktree_path: Path to the worktree
        force: Whether to force removal
    """
    if Path(worktree_path).exists():
        cmd = ["git", "worktree", "remove", worktree_path]
        if force:
            cmd.append("--force")
        run_command(cmd)


def create_timestamp_suffix() -> str:
    """Create a timestamp suffix for branch names"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_claude_command(cmd: List[str], cwd: str, logger: logging.Logger) -> subprocess.CompletedProcess:
    """
    Run Claude command with error filtering for non-critical MCP errors
    
    Args:
        cmd: Command list to execute
        cwd: Working directory
        logger: Logger instance
        
    Returns:
        CompletedProcess result
    """
    
    # Patterns to filter out
    non_critical_patterns = [
        "McpError: MCP error -32602",
        "Tool closeAllDiffTabs not found",
        "This error originated either by throwing inside of an async function"
    ]
    
    stderr_lines = []
    stderr_queue = queue.Queue()
    
    def read_stderr(pipe, queue):
        """Read stderr in a separate thread"""
        for line in iter(pipe.readline, ''):
            if line:
                queue.put(line)
        pipe.close()
    
    # Create process with pipes for stderr
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Start thread to read stderr
    stderr_thread = threading.Thread(target=read_stderr, args=(process.stderr, stderr_queue))
    stderr_thread.daemon = True
    stderr_thread.start()
    
    # Process stderr lines while the command runs
    while True:
        # Check if process is still running
        poll_status = process.poll()
        
        # Process any stderr lines
        try:
            while True:
                line = stderr_queue.get_nowait()
                
                # Check if this is a non-critical error
                is_non_critical = any(pattern in line for pattern in non_critical_patterns)
                
                if not is_non_critical:
                    # Print critical errors to stderr
                    sys.stderr.write(line)
                    sys.stderr.flush()
                
                stderr_lines.append(line)
        except queue.Empty:
            pass
        
        # If process has finished, break
        if poll_status is not None:
            # Give a bit of time for final output
            stderr_thread.join(timeout=0.5)
            
            # Process any remaining lines
            try:
                while True:
                    line = stderr_queue.get_nowait()
                    is_non_critical = any(pattern in line for pattern in non_critical_patterns)
                    if not is_non_critical:
                        sys.stderr.write(line)
                        sys.stderr.flush()
                    stderr_lines.append(line)
            except queue.Empty:
                pass
            
            break
        
        # Small sleep to avoid busy waiting
        time.sleep(0.01)
    
    # Create a CompletedProcess object
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout=None,
        stderr=''.join(stderr_lines)
    )


def is_git_clean() -> bool:
    """Check if the git working directory is clean"""
    result = run_command(["git", "status", "--porcelain"])
    return len(result.stdout.strip()) == 0


def get_current_branch() -> str:
    """Get the current git branch name"""
    result = run_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def get_git_status() -> dict:
    """
    Get comprehensive git repository status
    
    Returns:
        Dictionary with git status information
    """
    status = {
        'is_repo': False,
        'has_commits': False,
        'current_branch': None,
        'is_clean': True,
        'remotes': [],
        'worktrees': []
    }
    
    # Check if it's a git repo
    result = run_command(["git", "rev-parse", "--git-dir"])
    if result.returncode == 0:
        status['is_repo'] = True
        
        # Check for commits
        result = run_command(["git", "rev-list", "-n", "1", "--all"])
        if result.returncode == 0 and result.stdout.strip():
            status['has_commits'] = True
        
        # Get current branch
        result = run_command(["git", "branch", "--show-current"])
        if result.returncode == 0:
            status['current_branch'] = result.stdout.strip()
        
        # Check if working directory is clean
        result = run_command(["git", "status", "--porcelain"])
        if result.returncode == 0 and result.stdout.strip():
            status['is_clean'] = False
        
        # Get remotes
        result = run_command(["git", "remote", "-v"])
        if result.returncode == 0 and result.stdout.strip():
            status['remotes'] = list(set(line.split()[0] for line in result.stdout.strip().split('\n')))
        
        # Get worktrees
        result = run_command(["git", "worktree", "list"])
        if result.returncode == 0 and result.stdout.strip():
            status['worktrees'] = [line.split()[0] for line in result.stdout.strip().split('\n')]
    
    return status


def validate_plan_file(plan_path: Path) -> bool:
    """
    Validate that a PLAN.md file exists and contains workstreams
    
    Args:
        plan_path: Path to PLAN.md file
        
    Returns:
        True if valid, False otherwise
    """
    if not plan_path.exists():
        return False
    
    content = plan_path.read_text()
    workstreams = parse_workstream_section(content)
    
    return len(workstreams) > 0


def get_claude_command() -> List[str]:
    """
    Get the command to run Claude CLI
    
    Returns:
        List of command parts (e.g., ["claude"] or ["/path/to/claude"])
    """
    claude_path = os.environ.get('CLAUDE_ORCHESTRATOR_CLI_PATH', 'claude')
    return [claude_path]


def check_claude_cli() -> Optional[str]:
    """
    Check if Claude CLI is available and properly installed
    
    Returns:
        Path to claude CLI if found and working, None otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Try multiple ways to find claude
    # 1. Direct command
    result = run_command(["claude", "--version"])
    if result.returncode == 0:
        logger.debug("Found claude CLI via direct command")
        return "claude"  # In PATH, can use directly
    
    # 2. Check common installation paths
    common_paths = [
        "/usr/local/bin/claude",
        "/opt/homebrew/bin/claude",
        str(Path.home() / ".claude" / "local" / "node_modules" / ".bin" / "claude"),  # Claude Code default location
        str(Path.home() / ".local" / "bin" / "claude"),
        str(Path.home() / "bin" / "claude"),
    ]
    
    for path in common_paths:
        if Path(path).exists():
            result = run_command([path, "--version"])
            if result.returncode == 0:
                logger.debug(f"Found claude CLI at: {path}")
                logger.info(f"Claude CLI found at {path} but not in PATH. Will use full path.")
                return path  # Return the full path
    
    # 3. Try 'which' command on Unix-like systems
    if os.name != 'nt':  # Not Windows
        result = run_command(["which", "claude"])
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip()
            logger.debug(f"Found claude CLI via which: {path}")
            return path
    
    # 4. Try 'where' command on Windows
    else:
        result = run_command(["where", "claude"])
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split('\n')[0]  # Take first result
            logger.debug(f"Found claude CLI via where: {path}")
            return path
    
    return None