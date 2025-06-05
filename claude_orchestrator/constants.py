"""Constants and configuration values for Claude Orchestrator"""

# Model identifiers
OPUS_MODEL = "opus" # alias to most recent Opus model
SONNET_MODEL = "sonnet" # alias to most recent Sonnet model

# File and directory names
PLAN_FILE = "PLAN.md"
PROGRESS_DIR = ".claude_progress"
LOG_FILE = "claude_orchestrator.log"
VISUALS_DIR = "visuals"

# Status values
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

# Prompts
PLAN_PROMPT = """IMPORTANT: You are about to help create a comprehensive work plan. 

STEP 1 - INTERVIEW THE USER (DO THIS FIRST!)
============================================
Before doing ANYTHING else (no file exploration, no commands, no analysis):

1. Greet the user and explain that you'll be conducting an interview to understand their project
2. Ask them about:
   - What they want to accomplish with this project
   - What the current state of the project is
   - Any specific constraints or things they DON'T want
   - Which files (if any) they'd like you to review
   - Any specific technologies or approaches they prefer
   - Timeline or urgency considerations

DO NOT explore files or run any commands until AFTER the interview is complete and you have a clear understanding of their goals.

STEP 2 - CREATE THE PLAN (ONLY AFTER INTERVIEW)
===============================================
Once you understand the user's needs, create a comprehensive work plan in PLAN.md that includes:

1. A clear understanding of what the user WANTS to accomplish
2. Important constraints and what the user does NOT want
3. Division of work into COHERENT WORKSTREAMS that group related tasks together

PACKAGE MANAGEMENT NOTE: Use `uv` as the default package manager for Python projects:
- Use `uv init` to create new projects with pyproject.toml
- Use `uv add` to add dependencies
- Use `uv sync` to install dependencies
- Use `uv run` to run scripts in the virtual environment
- Include requirements.txt only for backwards compatibility if needed

CRITICAL SEQUENCING - DO NOT USE GIT WORKTREES YET:
The orchestrator will handle git worktrees AFTER the plan is finalized. During planning:
1. Work in the main repository
2. Set up the virtual environment and install ALL dependencies
3. Create the base directory structure and framework files
4. Ensure .gitignore includes orchestrator files (PLAN.md, .claude_progress/, etc.)
5. ONLY THEN will the orchestrator create worktrees for parallel execution

IMPORTANT: Workstreams should NOT be completely independent silos. Instead:
- Each workstream should group related tasks that share context
- Workstreams can have dependencies on each other
- A workstream might need outputs or context from another workstream
- Think of workstreams as coherent phases or components that may build on each other

For example, don't create:
- Workstream 1: Build all of feature A
- Workstream 2: Build all of feature B (with no awareness of A)

Instead, create:
- Workstream 1: Design core architecture and interfaces
- Workstream 2: Implement data layer (uses interfaces from WS1)
- Workstream 3: Build API endpoints (depends on data layer from WS2)

4. Each workstream should have:
   - A unique identifier (workstream_1, workstream_2, etc.)
   - A clear name and description
   - A cohesive group of related tasks
   - Clear dependencies on other workstreams (which outputs it needs)
   - What context or information it provides to other workstreams

Format the plan as a markdown file with clear sections for each workstream.
Use the following structure:

# Project Plan

## Goals
- What we want to achieve

## Constraints
- What we must avoid

## Workstreams

### Workstream 1: [Name]
**Description**: [Brief description of this coherent group of work]
**Dependencies**: None (or list other workstreams this depends on)
**Provides**: [What context/outputs this provides to other workstreams]
**Tasks**:
- Task 1
- Task 2
- Task 3

### Workstream 2: [Name]
**Description**: [Brief description]
**Dependencies**: Workstream 1 (needs X from WS1)
**Provides**: [What this workstream produces for others]
**Tasks**:
- Task 1
- Task 2
...

## Pre-Execution Setup (DO THIS BEFORE PARALLEL WORK BEGINS)
Once the plan is approved, the setup phase will:

1. **Virtual Environment Setup**:
   - Create/activate virtual environment
   - Install ALL project dependencies
   - Ensure environment is fully configured

2. **Architecture Documentation**:
   - A detailed "## Project Architecture" section will be added to PLAN.md
   - This will include directory structure, file organization, and architectural decisions
   - Workstreams will follow this architecture when implementing

3. **Git Configuration**:
   - Ensure .gitignore includes:
     - PLAN.md
     - .claude_progress/
     - claude_orchestrator.log
     - Any other orchestrator-specific files

Note: The setup phase will NOT create any code files - it only sets up the environment
and documents the architecture for workstreams to follow.

IMPORTANT ROLE CLARIFICATION:
- During planning: You are the PLANNER - create the plan, don't implement
- During setup: You are the ARCHITECT - document architecture, don't create files  
- During execution: The WORKSTREAM INSTANCES do ALL implementation work

- During review: You are the INTEGRATOR - merge and polish, don't reimplement

Remember: Interview FIRST, explore SECOND, plan THIRD, setup FOURTH, THEN parallel execution.

CRITICAL - ENDING THE PLANNING PHASE:
When PLAN.md is complete and saved:
1. Type: /exit
2. Press: Enter
3. Do NOT provide summaries or explain next steps
Just type '/exit' to terminate this session and allow the orchestrator to proceed."""

WORKSTREAM_PROMPT_TEMPLATE = """You are working on Workstream {id}: {name}

Please check the PLAN.md file to understand the full project context and your specific workstream.

IMPORTANT: The PLAN.md file contains a "## Project Architecture" section that specifies:
- The exact directory structure to create
- File naming conventions to follow
- Module organization patterns
- Shared interfaces/base classes to implement
- Architectural decisions to respect

You MUST follow this architecture exactly when creating files and directories.

Your specific tasks are:
{tasks}

IMPORTANT:
1. Read PLAN.md FIRST to understand:
   - The overall project goals
   - What other workstreams are doing
   - Your dependencies (what you need from other workstreams)
   - What you need to provide to other workstreams
   
2. Focus on your assigned tasks, but keep in mind:
   - How your work fits into the larger project
   - What interfaces or outputs other workstreams will need from you
   - Any assumptions you're making that other workstreams should know about
   
3. Track your progress by updating the file: {progress_file}
   - Document any important decisions or discoveries
   - Note any interfaces or contracts you've established
   - Record what other workstreams need to know
   
4. Commit your changes frequently with descriptive messages

5. If you create something that other workstreams depend on, make it clear and well-documented

6. PACKAGE MANAGEMENT: Use `uv` for Python package management:
   - `uv sync` to install dependencies from pyproject.toml
   - `uv add <package>` to add new dependencies
   - `uv run <script>` to run Python scripts
   - Avoid using pip directly unless specifically required

7. VISUALIZATION BEST PRACTICES:
   - Save ALL plots/charts to the 'visuals/' directory
   - Use descriptive filenames: feature_comparison_chart.png, performance_metrics.png
   - After creating each visualization:
     - Save it first
     - Open and review it to ensure it's readable
     - Check that labels, legends, and titles are clear
     - Iterate if needed to improve clarity
   - Use matplotlib/seaborn for professional visualizations
   - Consider color-blind friendly palettes

Start by reading PLAN.md, then work through your tasks systematically.
When all tasks are complete, update the progress file with "Status: COMPLETED" and exit."""

REVIEW_PROMPT = """Review the merged work from all parallel workstreams.

Please:
1. Check the original PLAN.md file, paying special attention to:
   - The dependencies between workstreams
   - What each workstream was supposed to provide to others
   - The overall project goals

2. Verify that workstream dependencies were properly handled:
   - Did workstreams that depended on others get what they needed?
   - Are the interfaces between components working correctly?
   - Is there proper communication between the parts?

3. Ensure all workstream goals have been met:
   - Each workstream completed its tasks
   - The outputs match what was promised to other workstreams
   - The combined work achieves the overall project goals

4. Fix any integration issues:
   - Resolve any conflicts between workstreams
   - Add any necessary "glue code" to connect components
   - Ensure consistent interfaces and data flow

5. Run tests if available to verify everything works together
   - For Python projects, use `uv run pytest` or `uv run python -m pytest`
   - Not `pytest` directly unless in an activated environment

6. Create a final commit with message "Final integration and review"

When you're satisfied that everything works together properly, type /exit to complete the review."""

# Timing constants
THREAD_START_DELAY = 2  # seconds between starting threads
PROGRESS_CHECK_INTERVAL = 30  # seconds between progress checks

# Git configuration
DEFAULT_BASE_BRANCH = "main"
WORK_BRANCH_PREFIX = "parallel_work"
WORKSTREAM_BRANCH_PREFIX = "workstream"
WORKTREE_PREFIX = "worktree"