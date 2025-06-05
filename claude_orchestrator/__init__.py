"""Claude Orchestrator - Parallel AI Development with Claude Code"""

__version__ = "0.1.3"
__author__ = "Kai Maurin Jones"
__email__ = "kmaurinjones@example.com"

from .orchestrator import ParallelClaudeOrchestrator
from .models import WorkStream, ExecutionReport

__all__ = ["ParallelClaudeOrchestrator", "WorkStream", "ExecutionReport"]