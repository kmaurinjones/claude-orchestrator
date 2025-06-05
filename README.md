# Claude Orchestrator

A powerful command-line tool that orchestrates multiple Claude Code instances to work in parallel on complex development tasks using git worktrees.

## Overview

Claude Orchestrator uses a divide-and-conquer strategy to tackle complex projects by:
1. Planning work with Claude Opus 4 (highest intelligence model)
2. Executing parallel workstreams with Claude Sonnet 4 (faster/cheaper model)
3. Merging and reviewing the results with Claude Opus 4

This approach allows you to leverage AI assistance at scale while maintaining code quality and consistency.

## Features

- **Intelligent Work Planning**: Uses Claude Opus 4 to create comprehensive project plans
- **Parallel Execution**: Runs multiple Claude Sonnet 4 instances simultaneously on different workstreams
- **Git Worktree Isolation**: Each workstream operates in its own git worktree to prevent conflicts
- **Progress Tracking**: Real-time monitoring of all parallel workstreams
- **Automatic Merging**: Intelligently merges all work back together
- **Final Review**: Claude Opus 4 reviews and integrates all work
- **Detailed Reporting**: Generates execution reports with timing and status information
- **Clear Role Separation**: Supervisor focuses on planning/architecture, workstreams handle implementation
- **Visualization Support**: Built-in support for charts and plots with quality checks

## Prerequisites

### Required
- **Python 3.8 or higher**
- **Git 2.5+** (with worktree support)
- **Claude Code CLI** - Must be installed and authenticated
  - Install from: https://claude.ai/download
  - After installation, run `claude login` to authenticate

### Automatic Setup
- **Git Repository**: The tool will automatically initialize a git repository if you run it in a directory without one. The repository will be named after your project directory.

## Installation

### From PyPI

```bash
# Using pip
pip install claude-orchestrator

# Using uv (recommended)
uv pip install claude-orchestrator
```

### From Source

```bash
# Clone the repository
git clone https://github.com/kmaurinjones/claude-orchestrator.git
cd claude-orchestrator

# Install in development mode
pip install -e .
```

## Usage

Navigate to your git repository and run:

```bash
# Basic usage
claude-orchestrator

# With verbose logging
claude-orchestrator --verbose

# Skip worktree cleanup after completion
claude-orchestrator --no-cleanup

# Use a different base branch
claude-orchestrator --base-branch develop

# Require permission prompts during planning/review (default is automatic)
claude-orchestrator --require-permissions
```

**Note**: By default, the orchestrator runs with `--dangerously-skip-permissions` for a hands-off experience. Use the `--require-permissions` flag if you want to approve tool usage during planning and review phases.

## How It Works

1. **Planning Phase**: Claude Opus 4 interactively works with you to create a comprehensive project plan (`PLAN.md`) that divides the work into parallel workstreams.

2. **Setup Phase**: After the plan is approved, Claude Opus 4 sets up the base framework:
   - Creates/configures the virtual environment
   - Installs all project dependencies
   - Creates the base directory structure and shared components
   - Ensures `.gitignore` includes orchestrator files
   - Commits the base framework to avoid merge conflicts

3. **Execution Phase**: Only after setup is complete, the tool creates separate git worktrees for each workstream and launches Claude Sonnet 4 instances to work on them simultaneously.

4. **Integration Phase**: All workstream branches are merged back together, and Claude Opus 4 performs a final review to ensure everything works cohesively.

## Example Workflow

```bash
# Navigate to your project
cd my-project

# Run the orchestrator
claude-orchestrator

# Claude Opus 4 will help you create a plan
# Then multiple Claude Sonnet 4 instances work in parallel
# Finally, Claude Opus 4 reviews and integrates everything
```

## Important Notes

1. **Git Worktrees**: The tool creates worktrees as siblings to your current directory, so ensure you have write permissions in the parent directory.

2. **Model Names**: The tool uses specific model identifiers:
   - `opus` (alias for the latest Opus model for planning and review)
   - `sonnet` (alias to the latest Sonnet model for parallel execution)
   
   These may need updating as new models are released.

3. **Safety**: The tool uses `--dangerously-skip-permissions` for autonomous operation during parallel execution. This means Claude can execute commands without asking. Use with caution.

4. **Branch Strategy**: All work happens on a new branch (`parallel_work_TIMESTAMP`), keeping your main branch safe.

## Package Management

Claude Orchestrator prompts encourage the use of `uv` as the default package manager for Python projects:
- Claude instances will use `uv sync`, `uv add`, and `uv run` commands
- Projects will use `pyproject.toml` for dependency management
- `requirements.txt` files are only created for backwards compatibility when needed

## Architecture

The package is organized into several modules:

- `orchestrator.py` - Main orchestration logic
- `models.py` - Data models (WorkStream, ExecutionReport)
- `utils.py` - Utility functions for git, logging, and parsing
- `constants.py` - Configuration constants and prompts
- `__main__.py` - CLI entry point

## Troubleshooting

- **"Claude Code not found"**: Ensure `claude` is in your PATH and authenticated
- **"Git worktree not supported"**: Upgrade to Git 2.5+
- **Merge conflicts**: The tool will notify you but won't resolve automatically
- **Git repository issues**: The tool now automatically initializes a git repo if needed

## Development

To contribute to this project:

```bash
# Clone the repository
git clone https://github.com/kmaurinjones/claude-orchestrator.git
cd claude-orchestrator

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black claude_orchestrator
isort claude_orchestrator
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
