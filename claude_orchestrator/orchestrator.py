"""Main orchestrator class for parallel Claude Code execution"""

import os
import time
import subprocess
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import shutil

from .models import WorkStream, ExecutionReport
from .constants import (
    OPUS_MODEL, SONNET_MODEL, PLAN_FILE, PROGRESS_DIR, VISUALS_DIR,
    STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_ERROR,
    PLAN_PROMPT, WORKSTREAM_PROMPT_TEMPLATE, REVIEW_PROMPT,
    THREAD_START_DELAY, PROGRESS_CHECK_INTERVAL,
    DEFAULT_BASE_BRANCH, WORK_BRANCH_PREFIX, WORKSTREAM_BRANCH_PREFIX, WORKTREE_PREFIX
)
from .utils import (
    run_command, parse_workstream_section, ensure_clean_worktree,
    create_timestamp_suffix, format_duration, get_claude_command
)


class ParallelClaudeOrchestrator:
    """Orchestrates multiple Claude Code instances working in parallel"""
    
    def __init__(self, base_branch: str = DEFAULT_BASE_BRANCH, require_permissions: bool = False):
        self.logger = logging.getLogger(__name__)
        self.repo_path = Path.cwd()
        self.base_branch = base_branch
        self.require_permissions = require_permissions
        self.work_branch = None
        self.workstreams: List[WorkStream] = []
        self.threads: List[threading.Thread] = []
        self.plan_file = self.repo_path / PLAN_FILE
        self.progress_dir = self.repo_path / PROGRESS_DIR
        self.start_time = None
        self.end_time = None
        
        # Create progress tracking directory
        self.progress_dir.mkdir(exist_ok=True)
        
        # Create visuals directory
        self.visuals_dir = self.repo_path / VISUALS_DIR
        self.visuals_dir.mkdir(exist_ok=True)
    
    def create_work_plan(self) -> None:
        """Step 1: Use Claude Opus to create a comprehensive work plan"""
        self.logger.info("Creating work plan with Claude Opus 4...")
        
        # Run Claude Opus interactively to create the plan
        # Don't use -p flag as that makes it non-interactive
        cmd = get_claude_command() + [
            "--model", OPUS_MODEL
        ]
        
        # Add skip permissions flag unless user wants to supervise
        if not self.require_permissions:
            cmd.append("--dangerously-skip-permissions")
        
        # Add the initial prompt
        cmd.append(PLAN_PROMPT)
        
        self.logger.info("Launching Claude Opus 4 for interactive planning session...")
        self.logger.info("Please work with Claude to create your project plan.")
        self.logger.info("When done, ensure PLAN.md is created and exit Claude.")
        
        # Run interactively - use subprocess with proper stdin/stdout/stderr
        try:
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run with inherited stdin/stdout/stderr for proper interaction
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                stdin=None,  # Use parent's stdin
                stdout=None, # Use parent's stdout
                stderr=None  # Use parent's stderr
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Claude exited with code {result.returncode}")
        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI command not found.\n"
                "Please ensure Claude Code is installed and available.\n"
                "You can download it from: https://claude.ai/download"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to launch Claude CLI: {e}\n"
                "Please ensure Claude Code is installed and available.\n"
                "You can download it from: https://claude.ai/download"
            )
        
        if not self.plan_file.exists():
            raise ValueError("PLAN.md was not created. Please run again and ensure the plan is saved.")
        
        self.logger.info("Work plan created successfully!")
    
    def parse_work_plan(self) -> None:
        """Parse the PLAN.md file to extract workstreams"""
        self.logger.info("Parsing work plan...")
        
        if not self.plan_file.exists():
            raise ValueError("PLAN.md not found. Run create_work_plan first.")
        
        content = self.plan_file.read_text()
        workstream_data = parse_workstream_section(content)
        
        for ws_id, ws_name, ws_desc, ws_tasks in workstream_data:
            workstream = WorkStream(
                id=ws_id,
                name=ws_name,
                description=ws_desc,
                tasks=ws_tasks,
                worktree_path=str(self.repo_path.parent / f"{WORKTREE_PREFIX}_{ws_id}"),
                branch_name=f"{WORKSTREAM_BRANCH_PREFIX}_{ws_id}",
                progress_file=str(self.progress_dir / f"workstream_{ws_id}_progress.md")
            )
            
            self.workstreams.append(workstream)
        
        if not self.workstreams:
            raise ValueError("No workstreams found in PLAN.md. Please check the format.")
        
        self.logger.info(f"Found {len(self.workstreams)} workstreams")
    
    def ensure_gitignore(self) -> None:
        """Ensure .gitignore includes orchestrator files"""
        gitignore_path = self.repo_path / ".gitignore"
        orchestrator_patterns = [
            "# Claude Orchestrator files",
            "PLAN.md",
            ".claude_progress/",
            "claude_orchestrator.log",
            "worktree_*/",
            "visuals/",
            "*.pyc",
            "__pycache__/",
            ".pytest_cache/",
            ""  # Empty line for separation
        ]
        
        # Read existing .gitignore or create new content
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            lines = content.strip().split('\n')
        else:
            lines = []
            
        # Check which patterns are missing
        missing_patterns = []
        for pattern in orchestrator_patterns:
            if pattern and pattern not in lines and not any(pattern in line for line in lines):
                missing_patterns.append(pattern)
        
        if missing_patterns:
            self.logger.info("Updating .gitignore with orchestrator patterns...")
            
            # Add a newline if file doesn't end with one
            if lines and lines[-1]:
                lines.append("")
                
            # Add missing patterns
            if "# Claude Orchestrator files" in missing_patterns:
                lines.extend(missing_patterns)
            else:
                # Just add the missing patterns (skip the comment)
                lines.extend([p for p in missing_patterns if p != "# Claude Orchestrator files"])
            
            # Write updated content
            gitignore_path.write_text('\n'.join(lines) + '\n')
            
            # Stage the .gitignore changes
            run_command(["git", "add", ".gitignore"])
            self.logger.info(".gitignore updated with orchestrator patterns")
    
    def create_work_branch(self) -> None:
        """Step 2: Create a new branch for all work"""
        self.logger.info("Creating work branch...")
        
        # Ensure .gitignore is set up first
        self.ensure_gitignore()
        
        # First, ensure we're on a valid branch
        current_branch = run_command(["git", "branch", "--show-current"])
        if current_branch.returncode != 0 or not current_branch.stdout.strip():
            # We might be in a detached HEAD state, try to get on main/master
            self.logger.warning("Not on a branch, attempting to checkout base branch...")
            result = run_command(["git", "checkout", self.base_branch])
            if result.returncode != 0:
                # Try master if main doesn't exist
                if self.base_branch == "main":
                    result = run_command(["git", "checkout", "master"])
                    if result.returncode == 0:
                        self.base_branch = "master"
                        self.logger.info("Using 'master' as base branch")
                    else:
                        # Create the base branch if it doesn't exist
                        result = run_command(["git", "checkout", "-b", self.base_branch])
                        if result.returncode != 0:
                            raise RuntimeError(
                                f"Failed to create or checkout base branch '{self.base_branch}'.\n"
                                f"Error: {result.stderr}\n"
                                "Please ensure you have at least one commit in your repository."
                            )
        
        timestamp = create_timestamp_suffix()
        self.work_branch = f"{WORK_BRANCH_PREFIX}_{timestamp}"
        
        # Create and checkout new branch
        result = run_command(["git", "checkout", "-b", self.work_branch])
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create work branch '{self.work_branch}'.\n"
                f"Error: {result.stderr}\n"
                "Please check your git repository status and try again."
            )
        
        self.logger.info(f"Created and checked out branch: {self.work_branch}")
    
    def setup_base_framework(self) -> None:
        """Setup base framework and dependencies before parallel execution"""
        self.logger.info("Setting up base framework and dependencies...")
        
        # Give Claude a chance to set up the base framework
        cmd = get_claude_command() + [
            "--model", OPUS_MODEL
        ]
        
        if not self.require_permissions:
            cmd.append("--dangerously-skip-permissions")
        
        setup_prompt = """Review the PLAN.md and set up ONLY the base framework:

CRITICAL: You are the SUPERVISOR - DO NOT implement any features from the workstreams!
Your ONLY job is to create the foundation that workstreams will build upon.

1. Create/activate virtual environment (using uv preferably)
2. Install ALL project dependencies
3. Create the base directory structure including:
   - visuals/ directory for all plots and charts
   - Any other needed directories
4. Set up initial configuration files
5. Create base classes/interfaces that workstreams will use
6. Establish shared utilities or helpers
7. If visualization is needed, install matplotlib/seaborn
8. Commit these base framework changes

DO NOT:
- Implement any features listed in workstreams
- Write any business logic
- Create any functionality beyond base framework
- Do any tasks assigned to workstreams

The workstream instances will handle ALL implementation work in parallel.
You are ONLY setting up the skeleton/framework.

Type 'exit' when the base setup is complete."""
        
        cmd.append(setup_prompt)
        
        self.logger.info("Launching Claude Opus 4 to set up base framework...")
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                stdin=None,
                stdout=None,
                stderr=None
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Claude exited with code {result.returncode}")
        except Exception as e:
            raise RuntimeError(f"Failed to set up base framework: {e}")
        
        self.logger.info("Base framework setup complete!")
    
    def setup_worktrees(self) -> None:
        """Step 3: Create git worktrees for each workstream"""
        self.logger.info("Setting up worktrees...")
        
        for ws in self.workstreams:
            # Remove worktree if it already exists
            ensure_clean_worktree(ws.worktree_path)
            
            # Create new worktree with a branch
            result = run_command([
                "git", "worktree", "add", 
                "-b", ws.branch_name,
                ws.worktree_path,
                self.work_branch
            ])
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to create worktree for {ws.name}: {result.stderr}")
            
            # Copy PLAN.md to each worktree
            shutil.copy(self.plan_file, Path(ws.worktree_path) / PLAN_FILE)
            
            # Create progress tracking file
            Path(ws.progress_file).write_text(f"# Progress for {ws.name}\n\nStatus: Starting...\n")
            
            self.logger.info(f"Created worktree for {ws.name} at {ws.worktree_path}")
    
    def execute_workstream(self, workstream: WorkStream) -> None:
        """Execute Claude Sonnet for a single workstream"""
        self.logger.info(f"Starting execution of {workstream.name} with Claude Sonnet 4")
        workstream.status = STATUS_RUNNING
        workstream.start_time = time.time()
        
        # Update progress
        self.update_progress(workstream, "Starting execution...")
        
        # Prepare the prompt for this workstream
        prompt = WORKSTREAM_PROMPT_TEMPLATE.format(
            id=workstream.id,
            name=workstream.name,
            tasks='\n'.join(f'- {task}' for task in workstream.tasks),
            progress_file=Path(workstream.progress_file).name
        )
        
        # Set up output file for this workstream
        output_file = self.progress_dir / f"workstream_{workstream.id}_output.log"
        workstream.output_file = str(output_file)
        
        # Run Claude Sonnet with dangerous permissions in non-interactive mode
        cmd = get_claude_command() + [
            "--dangerously-skip-permissions",
            "--model", SONNET_MODEL,
            "-p", prompt
        ]
        
        try:
            with open(output_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    cwd=Path(workstream.worktree_path),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False
                )
            
            if result.returncode == 0:
                workstream.status = STATUS_COMPLETED
                self.update_progress(workstream, "Completed successfully!")
            else:
                workstream.status = STATUS_FAILED
                self.update_progress(workstream, f"Failed with return code: {result.returncode}")
                
        except Exception as e:
            workstream.status = STATUS_ERROR
            self.update_progress(workstream, f"Error: {str(e)}")
            self.logger.error(f"Error executing workstream {workstream.name}: {e}")
        
        workstream.end_time = time.time()
        duration = workstream.end_time - workstream.start_time
        self.logger.info(f"Completed {workstream.name} in {duration:.2f} seconds")
    
    def update_progress(self, workstream: WorkStream, message: str) -> None:
        """Update progress tracking for a workstream"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(workstream.progress_file, 'a') as f:
            f.write(f"\n[{timestamp}] {message}\n")
    
    def execute_parallel_work(self) -> None:
        """Step 4: Execute all workstreams in parallel"""
        self.logger.info(f"Starting parallel execution of {len(self.workstreams)} workstreams using Claude Sonnet 4")
        
        # Create threads for each workstream
        for ws in self.workstreams:
            thread = threading.Thread(
                target=self.execute_workstream,
                args=(ws,),
                name=f"WorkStream_{ws.id}"
            )
            self.threads.append(thread)
            thread.start()
            time.sleep(THREAD_START_DELAY)  # Small delay to avoid overwhelming the system
        
        # Monitor progress
        self.monitor_progress()
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()
        
        self.logger.info("All workstreams completed")
    
    def monitor_progress(self) -> None:
        """Monitor progress of all workstreams"""
        self.logger.info(f"Monitoring progress (checking every {PROGRESS_CHECK_INTERVAL} seconds)...")
        
        while any(thread.is_alive() for thread in self.threads):
            time.sleep(PROGRESS_CHECK_INTERVAL)
            
            # Print status update
            self.logger.info("\n=== Progress Update ===")
            for ws in self.workstreams:
                duration = ""
                if ws.start_time:
                    elapsed = time.time() - ws.start_time
                    duration = f" ({elapsed:.1f}s)"
                self.logger.info(f"{ws.name}: {ws.status}{duration}")
            
            # Check progress files for completion
            for ws in self.workstreams:
                if ws.status == STATUS_RUNNING and Path(ws.progress_file).exists():
                    content = Path(ws.progress_file).read_text()
                    if "Status: COMPLETED" in content:
                        ws.status = STATUS_COMPLETED
    
    def merge_work(self) -> None:
        """Step 5: Merge all worktree changes back together"""
        self.logger.info("Merging all work together...")
        
        # First, go back to the main work branch
        run_command(["git", "checkout", self.work_branch])
        
        # Merge each workstream branch
        for ws in self.workstreams:
            if ws.status == STATUS_COMPLETED:
                self.logger.info(f"Merging {ws.name} from {ws.branch_name}")
                result = run_command(["git", "merge", "--no-ff", ws.branch_name, "-m", f"Merge {ws.name}"])
                if result.returncode != 0:
                    self.logger.error(f"Merge conflict in {ws.name}. Manual resolution required.")
    
    def final_review(self) -> None:
        """Use Claude Opus to review and finalize the merged work"""
        self.logger.info("Running final review with Claude Opus 4...")
        
        cmd = get_claude_command() + [
            "--model", OPUS_MODEL
        ]
        
        # Add skip permissions flag unless user wants to supervise
        if not self.require_permissions:
            cmd.append("--dangerously-skip-permissions")
        
        # Add the review prompt
        cmd.append(REVIEW_PROMPT)
        
        # Run interactively for final review - use subprocess with proper stdin/stdout/stderr
        try:
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run with inherited stdin/stdout/stderr for proper interaction
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                stdin=None,  # Use parent's stdin
                stdout=None, # Use parent's stdout
                stderr=None  # Use parent's stderr
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Claude exited with code {result.returncode}")
        except FileNotFoundError:
            self.logger.error(
                "Claude CLI command not found. Skipping final review.\n"
                "Please install Claude Code to enable the review step."
            )
        except Exception as e:
            self.logger.error(
                f"Claude CLI failed for final review: {e}\n"
                "Please install Claude Code to enable the review step."
            )
        
        self.logger.info("Final review completed!")
    
    def cleanup_worktrees(self) -> None:
        """Clean up worktrees after completion"""
        self.logger.info("Cleaning up worktrees...")
        
        for ws in self.workstreams:
            if Path(ws.worktree_path).exists():
                run_command(["git", "worktree", "remove", ws.worktree_path, "--force"])
                self.logger.info(f"Removed worktree: {ws.worktree_path}")
    
    def generate_report(self) -> ExecutionReport:
        """Generate a final report of the parallel execution"""
        report = ExecutionReport(
            workstreams=self.workstreams,
            opus_model=OPUS_MODEL,
            sonnet_model=SONNET_MODEL
        )
        
        if self.start_time and self.end_time:
            report.total_duration = self.end_time - self.start_time
        
        # Save report to file
        report_path = self.progress_dir / "execution_report.md"
        report_path.write_text(report.to_markdown())
        
        self.logger.info(f"Report generated: {report_path}")
        return report
    
    def run(self, skip_cleanup: bool = False) -> None:
        """Run the complete parallel orchestration workflow"""
        try:
            self.start_time = time.time()
            
            # Step 1: Create work plan with Opus
            self.create_work_plan()
            
            # Parse the work plan
            self.parse_work_plan()
            
            # Step 2: Create work branch
            self.create_work_branch()
            
            # Step 3: Setup base framework BEFORE creating worktrees
            self.setup_base_framework()
            
            # Step 4: Setup worktrees (now that base framework is ready)
            self.setup_worktrees()
            
            # Step 5: Execute parallel work with Sonnet
            self.execute_parallel_work()
            
            # Step 6: Merge and review with Opus
            self.merge_work()
            self.final_review()
            
            self.end_time = time.time()
            
            # Generate report
            self.generate_report()
            
            # Optional: Cleanup
            if not skip_cleanup:
                cleanup = input("\nClean up worktrees? (y/n): ")
                if cleanup.lower() == 'y':
                    self.cleanup_worktrees()
            
            self.logger.info("Parallel orchestration completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Orchestration failed: {e}")
            raise