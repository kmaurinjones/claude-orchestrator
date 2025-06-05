# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4] - 2025-06-06

### Fixed
- Made exit instructions more explicit in planning and setup phases to prevent Claude from explaining next steps instead of exiting
- Added clearer "CRITICAL" instructions to ensure Claude types 'exit' to complete each phase
- This fixes the issue where orchestrator would hang waiting for phase completion

## [0.1.3] - 2025-06-06

### Added
- Setup phase now installs claude-orchestrator itself in the project's virtual environment
- This enables recursive usage - projects can call claude-orchestrator from within their own environment without needing global installation

## [0.1.2] - 2025-06-06

### Fixed
- Fixed non-critical MCP error messages (like "Tool closeAllDiffTabs not found") from appearing in output
- Implemented cross-platform error filtering to suppress harmless Claude Code internal errors while preserving important error messages

## [0.1.1] - 2025-06-06

### Changed
- Updated author name from "K. Maurin Jones" to "Kai Maurin-Jones" across all project files
- Updated README to reflect PyPI availability as primary installation method

## [0.1.0] - 2025-06-05

### Added
- Automatic git repository initialization when running in a non-git directory
- Git user configuration during auto-initialization if not already configured
- Better error handling for missing Claude CLI with helpful installation instructions
- Improved git repository detection using `git rev-parse` instead of `.git` directory check
- Support for detached HEAD state and missing base branches
- `--require-permissions` flag to enable permission prompts during planning/review (default is automatic)
- Base framework setup phase between planning and parallel execution to avoid merge conflicts
- Automatic .gitignore configuration to exclude orchestrator files (PLAN.md, .claude_progress/, etc.)
- Visualization support with dedicated visuals/ directory and best practices in prompts
- Clear role separation to prevent supervisor from duplicating workstream tasks

### Changed
- Model identifiers now use aliases: "opus" and "sonnet" for latest models
- Error messages now include emoji indicators for better visual feedback
- Enhanced branch creation logic to handle edge cases
- Planning prompt now explicitly requires interviewing the user FIRST before any exploration
- Planning and review phases now use `--dangerously-skip-permissions` by default for hands-off operation
- Workstreams are now conceptualized as coherent groups of related tasks with dependencies, not isolated features
- Updated prompts to emphasize context-sharing and dependency management between workstreams
- Prompts now encourage using `uv` as the default Python package manager instead of `pip`

### Deprecated

### Removed

### Fixed
- Fixed git repository detection to work with all git configurations including worktrees
- Fixed "No such file or directory" error when Claude CLI is not installed
- Fixed git initialization to only occur when actually not in a git repository

### Security

[unreleased]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kmaurinjones/claude-orchestrator/releases/tag/v0.1.0