"""Claude Orchestrator - Parallel AI Development with Claude Code"""

__version__ = "0.1.0"
__author__ = "K. Maurin Jones"
__email__ = "kmaurinjones@example.com"

from .orchestrator import ParallelClaudeOrchestrator
from .models import WorkStream, ExecutionReport

__all__ = ["ParallelClaudeOrchestrator", "WorkStream", "ExecutionReport"]