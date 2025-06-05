"""Data models for Claude Orchestrator"""

from dataclasses import dataclass, asdict, field
from typing import List, Optional
from datetime import datetime


@dataclass
class WorkStream:
    """Represents a single work stream for parallel execution"""
    id: int
    name: str
    description: str
    tasks: List[str]
    worktree_path: str
    branch_name: str
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_file: Optional[str] = None
    progress_file: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert WorkStream to dictionary"""
        return asdict(self)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if workstream is completed"""
        return self.status == "completed"
    
    @property
    def is_running(self) -> bool:
        """Check if workstream is currently running"""
        return self.status == "running"
    
    def format_duration(self) -> str:
        """Format duration as human-readable string"""
        duration = self.duration
        if duration is None:
            return "N/A"
        
        if duration < 60:
            return f"{duration:.1f}s"
        elif duration < 3600:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}h {minutes}m"


@dataclass
class ExecutionReport:
    """Report of the parallel execution"""
    timestamp: datetime = field(default_factory=datetime.now)
    workstreams: List[WorkStream] = field(default_factory=list)
    total_duration: Optional[float] = None
    opus_model: str = ""
    sonnet_model: str = ""
    
    @property
    def total_workstreams(self) -> int:
        """Total number of workstreams"""
        return len(self.workstreams)
    
    @property
    def successful_workstreams(self) -> int:
        """Number of successfully completed workstreams"""
        return sum(1 for ws in self.workstreams if ws.is_completed)
    
    @property
    def failed_workstreams(self) -> int:
        """Number of failed workstreams"""
        return sum(1 for ws in self.workstreams if ws.status in ["failed", "error"])
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_workstreams == 0:
            return 0.0
        return (self.successful_workstreams / self.total_workstreams) * 100
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = [
            "# Parallel Claude Code Execution Report",
            "",
            f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"- Total Workstreams: {self.total_workstreams}",
            f"- Successful: {self.successful_workstreams}",
            f"- Failed: {self.failed_workstreams}",
            f"- Success Rate: {self.success_rate:.1f}%",
            ""
        ]
        
        if self.total_duration:
            lines.append(f"- Total Duration: {self._format_duration(self.total_duration)}")
            lines.append("")
        
        lines.extend([
            "## Models Used",
            "",
            f"- Planning: Claude Opus 4 ({self.opus_model})",
            f"- Workstreams: Claude Sonnet 4 ({self.sonnet_model})",
            f"- Final Review: Claude Opus 4 ({self.opus_model})",
            "",
            "## Workstream Details",
            ""
        ])
        
        for ws in self.workstreams:
            lines.extend([
                f"### {ws.name}",
                f"- Status: {ws.status}",
                f"- Duration: {ws.format_duration()}",
                f"- Branch: {ws.branch_name}",
                f"- Tasks: {len(ws.tasks)}",
                ""
            ])
        
        return "\n".join(lines)
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes} minutes {secs} seconds"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours} hours {minutes} minutes"