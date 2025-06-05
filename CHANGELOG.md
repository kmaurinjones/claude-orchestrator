# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[unreleased]: https://github.com/kmaurinjones/claude-orchestrator/compare/v0.1.0...HEAD