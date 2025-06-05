#!/usr/bin/env python3
"""Command-line entry point for claude-orchestrator."""

import sys
import argparse
from pathlib import Path

from . import __version__
from .orchestrator import ParallelClaudeOrchestrator
from .utils import check_prerequisites, setup_logging
from .constants import OPUS_MODEL, SONNET_MODEL


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Orchestrate multiple Claude Code instances in parallel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claude-orchestrator                   # Run with automatic permissions (default)
  claude-orchestrator --verbose         # Enable verbose logging
  claude-orchestrator --no-cleanup      # Skip worktree cleanup after completion
  claude-orchestrator --require-permissions  # Ask for permission during planning/review
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"claude-orchestrator {__version__}"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip worktree cleanup after completion"
    )
    
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch to create work from (default: main)"
    )
    
    parser.add_argument(
        "--require-permissions",
        action="store_true",
        help="Require permission prompts during planning and review phases (default: skip permissions)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Check prerequisites
    try:
        check_prerequisites()
    except RuntimeError as e:
        print("\n⚠️  Prerequisites Check Failed\n", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        print("\nPlease fix the above issue and try again.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during prerequisites check: {e}", file=sys.stderr)
        return 1
    
    # Print header
    print("=== Claude Orchestrator ===")
    print(f"Version: {__version__}")
    print(f"Working in: {Path.cwd()}")
    print(f"Planning Model: Claude Opus 4 ({OPUS_MODEL})")
    print(f"Workstream Model: Claude Sonnet 4 ({SONNET_MODEL})")
    print(f"Review Model: Claude Opus 4 ({OPUS_MODEL})")
    print(f"Base Branch: {args.base_branch}")
    print("===========================\n")
    
    try:
        # Create and run orchestrator
        orchestrator = ParallelClaudeOrchestrator(
            base_branch=args.base_branch,
            require_permissions=args.require_permissions
        )
        orchestrator.run(skip_cleanup=args.no_cleanup)
        print("\n✅ Orchestration completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 130
    except RuntimeError as e:
        print(f"\n❌ Runtime Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}", file=sys.stderr)
        if args.verbose:
            import logging
            logging.getLogger().exception("Detailed traceback:")
        else:
            print("\nRun with --verbose flag for detailed error information.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())