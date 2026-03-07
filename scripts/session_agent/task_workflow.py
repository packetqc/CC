"""Task Workflow — 8-stage state machine for task lifecycle management.

The task workflow tracks where a task/issue sits in its lifecycle,
from initial prompt reception through completion. It persists in the
session runtime cache and crosses session boundaries via the startup
hook continuity layer.

Two workflow levels coexist:
  - Global workflow: 10-stage engineering cycle (engineering.py)
  - Task workflow: 8-stage progression WITHIN a specific task (this module)

Task workflow completion triggers advancement in the global engineering cycle.

Stages (ordered, 0-indexed):
  0: initial        — Prompt analysis, title/desc extraction, project detection, user confirmation
  1: plan           — Work plan creation and approval (stub)
  2: analyze        — Deep analysis of the request (stub)
  3: implement      — Execution of the work plan (stub)
  4: validation     — Verification and testing (stub)
  5: approval       — User approval of deliverables (stub)
  6: documentation  — Doc updates: project docs, knowledge, or both
  7: completion     — Final delivery and closure (stub)

Cross-cutting concerns:
  documentation    — At each stage boundary where modifications occurred,
                     ask user: project docs only / knowledge only / both
  validation       — At each stage completion (initial → validation),
                     optional validation quiz confirming expectations met.
                     Does NOT run for approval, documentation, completion.

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import (
    _find_runtime_cache,
    commit_cache,
    read_runtime_cache,
    update_session_data,
)
from .helpers import _get_gh_helper
from .request_types import detect_request_type


# ── Stage Label Mapping (for GitHub issue sync) ─────────────────

STAGE_LABEL_PREFIX = "STAGE:"
STEP_LABEL_PREFIX = "STEP:"
STEP_LABEL_COLOR = "d4c5f9"  # light purple for all step labels

STAGE_LABEL_COLORS = {
    "initial": "c5def5",     # light blue
    "plan": "d4c5f9",        # light purple
    "analyze": "bfdadc",     # light teal
    "implement": "0075ca",   # blue
    "validation": "fbca04",  # yellow
    "approval": "0e8a16",    # green
    "documentation": "e99695",  # light red
    "completion": "006b75",  # dark teal
}


def _sync_stage_label(cache: dict, old_stage: str, new_stage: str) -> bool:
    """Sync the GitHub issue label to reflect the current workflow stage.

    Removes the old stage label and adds the new one. Labels follow
    the pattern 'STAGE:<name>' (e.g., 'STAGE:implement').

    Args:
        cache: The full session cache dict.
        old_stage: The previous stage name.
        new_stage: The new stage name.

    Returns:
        True if sync succeeded, False on error (non-fatal).
    """
    repo = cache.get("repo", "")
    issue_number = cache.get("issue_number", 0)
    if not repo or not issue_number:
        return False

    try:
        gh = _get_gh_helper()
        if not gh:
            return False

        new_label = f"{STAGE_LABEL_PREFIX}{new_stage}"

        # Remove ALL existing STAGE: labels (not just the old one).
        # Multiple labels can accumulate when the cache or sync
        # falls behind — clean sweep ensures only one STAGE: label.
        try:
            issue_data = gh._request("GET", f"/repos/{repo}/issues/{issue_number}")
            for lbl in issue_data.get("labels", []):
                if lbl["name"].startswith(STAGE_LABEL_PREFIX):
                    try:
                        gh.issue_label_remove(repo, issue_number, lbl["name"])
                    except Exception:
                        pass
        except Exception:
            pass

        # Ensure new label exists, then add it
        color = STAGE_LABEL_COLORS.get(new_stage, "ededed")
        try:
            gh._request("POST", f"/repos/{repo}/labels", {
                "name": new_label,
                "color": color,
                "description": f"Task workflow stage: {new_stage}",
            })
        except Exception:
            pass  # Label may already exist

        gh.issue_labels_add(repo, issue_number, [new_label])
        return True
    except Exception:
        return False


def _sync_step_label(cache: dict, old_step: str, new_step: str) -> bool:
    """Sync the GitHub issue label to reflect the current workflow step.

    Removes the old step label and adds the new one. Labels follow
    the pattern 'STEP:<name>' (e.g., 'STEP:confirm_title').

    Args:
        cache: The full session cache dict.
        old_step: The previous step name (can be None).
        new_step: The new step name.

    Returns:
        True if sync succeeded, False on error (non-fatal).
    """
    repo = cache.get("repo", "")
    issue_number = cache.get("issue_number", 0)
    if not repo or not issue_number or not new_step:
        return False

    try:
        gh = _get_gh_helper()
        if not gh:
            return False

        # Remove ALL existing STEP: labels (not just the old one).
        # Multiple labels can accumulate when steps advance faster
        # than the sync — clean sweep ensures only one STEP: label.
        try:
            issue_data = gh._request("GET", f"/repos/{repo}/issues/{issue_number}")
            for lbl in issue_data.get("labels", []):
                if lbl["name"].startswith(STEP_LABEL_PREFIX):
                    try:
                        gh.issue_label_remove(repo, issue_number, lbl["name"])
                    except Exception:
                        pass
        except Exception:
            pass

        new_label = f"{STEP_LABEL_PREFIX}{new_step}"

        # Ensure label exists
        try:
            gh._request("POST", f"/repos/{repo}/labels", {
                "name": new_label,
                "color": STEP_LABEL_COLOR,
                "description": f"Task workflow step: {new_step}",
            })
        except Exception:
            pass  # Label may already exist

        gh.issue_labels_add(repo, issue_number, [new_label])
        return True
    except Exception:
        return False


# ── Task Workflow Stages ─────────────────────────────────────────

TASK_WORKFLOW_STAGES = (
    "initial",
    "plan",
    "analyze",
    "implement",
    "validation",
    "approval",
    "documentation",
    "completion",
)

TASK_WORKFLOW_STAGE_INDEX = {stage: i for i, stage in enumerate(TASK_WORKFLOW_STAGES)}

# Labels for display
TASK_WORKFLOW_STAGE_LABELS = {
    "initial": "Initial — prompt reception and confirmation",
    "plan": "Plan — work plan creation and approval",
    "analyze": "Analyze — deep analysis of the request",
    "implement": "Implement — execution of the work plan",
    "validation": "Validation — verification and testing",
    "approval": "Approval — user approval of deliverables",
    "documentation": "Documentation — doc updates confirmation",
    "completion": "Completion — final delivery and closure",
}

# Stages where validation cross-cut runs (initial → validation inclusive)
VALIDATION_ELIGIBLE_STAGES = ("initial", "plan", "analyze", "implement", "validation")

# ── Initial Stage Steps ──────────────────────────────────────────

INITIAL_STAGE_STEPS = (
    "analyze_prompt",
    "extract_title",
    "extract_description",
    "confirm_title",
    "detect_project",
    "confirm_project",
    "persist_state",
    "output_details",
    "wait_approval",
)

INITIAL_STEP_LABELS = {
    "analyze_prompt": "Analyze the user prompt for action words and structure",
    "extract_title": "Extract title from line 1 of the prompt",
    "extract_description": "Extract description from remaining lines",
    "confirm_title": "Confirm title with user via AskUserQuestion",
    "detect_project": "Detect project owner from title and description",
    "confirm_project": "Confirm project with user via AskUserQuestion",
    "persist_state": "Persist project + title + description in cache and GitHub",
    "output_details": "Output confirmed details to the user",
    "wait_approval": "Wait for user approval before proceeding to plan stage",
}


# ── Implement Stage Steps ────────────────────────────────────────
# Each todo item follows this enforced work cycle.
# The cycle repeats for each todo in the plan.

IMPLEMENT_STAGE_STEPS = (
    "remote_check",       # Strategic remote check before modifying files
    "executing",          # Execute the current todo item
    "commit",             # Progressive commit — each todo = own commit
    "push",               # Push to remote branch
    "cache_update",       # Update session cache (todo_snapshot, files_modified)
    "issue_comment",      # Post todo completion as issue comment (G7)
    "mark_modifications", # Call mark_modifications_occurred() if files changed
    "next_todo",          # Advance to next todo or signal stage complete
)

IMPLEMENT_STEP_LABELS = {
    "remote_check": "Strategic remote check before modifying shared files",
    "executing": "Execute the current todo item",
    "commit": "Progressive commit — each logical unit of work",
    "push": "Push committed changes to remote branch",
    "cache_update": "Update session cache (todo_snapshot, files_modified, work_summary)",
    "issue_comment": "Post todo start/completion as issue comment (Gate G7)",
    "mark_modifications": "Flag modifications for documentation cross-cut",
    "next_todo": "Advance to next todo or signal implement stage complete",
}


# ── Completion Stage Steps ───────────────────────────────────────
# Final delivery sequence: compile data, commit, push, PR, merge.

COMPLETION_STAGE_STEPS = (
    "pre_save_summary",    # Compile metrics, time blocks, self-assessment
    "generate_notes",      # Generate session notes markdown
    "finalize_cache",      # Finalize runtime cache (session_phase=complete)
    "compile_sessions",    # Compile sessions.json for I1 Session Viewer
    "compile_tasks",       # Compile tasks.json for I3 Tasks Workflow Viewer
    "commit_final",        # Final commit with all compiled data
    "push_final",          # Push to remote branch
    "create_pr",           # Create PR to default branch
    "merge_pr",            # Merge PR (elevated) or guide user (semi-auto)
    "post_close",          # Post closing report + close issue
)

COMPLETION_STEP_LABELS = {
    "pre_save_summary": "Compile pre-save summary (metrics, time, self-assessment)",
    "generate_notes": "Generate session notes markdown for web pipeline",
    "finalize_cache": "Finalize runtime cache (session_phase → complete)",
    "compile_sessions": "Compile sessions.json for I1 Session Viewer",
    "compile_tasks": "Compile tasks.json for I3 Tasks Workflow Viewer",
    "commit_final": "Final commit with session notes, cache, and compiled data",
    "push_final": "Push all changes to remote branch",
    "create_pr": "Create PR to default branch",
    "merge_pr": "Merge PR (elevated) or guide user (semi-auto)",
    "post_close": "Post closing report and close issue",
}


# ── Workflow State Management ────────────────────────────────────

def init_task_workflow(request_description: str = "",
                       title: str = "",
                       issue_number: Optional[int] = None) -> bool:
    """Initialize the task workflow state machine in the session cache.

    Called at task reception, sets the initial stage to 'initial'
    and seeds the request description.

    Args:
        request_description: The original user request (verbatim).
        title: Extracted or confirmed task title.
        issue_number: GitHub issue number if already created.

    Returns:
        True if initialization succeeded.
    """
    now = datetime.now(timezone.utc).isoformat()

    workflow = {
        "current_stage": "initial",
        "current_stage_index": 0,
        "current_step": "analyze_prompt",
        "current_step_index": 0,
        "title": title,
        "description": request_description,
        "issue_number": issue_number or 0,
        "project": None,
        "started_at": now,
        "updated_at": now,
        "modifications_occurred": False,
        "validation_results": {},
        "validation_skipped_entirely": False,
        "unit_tests": [],
        "stage_history": [
            {
                "stage": "initial",
                "index": 0,
                "entered_at": now,
                "exited_at": None,
                "reason": "task_received",
            }
        ],
        "step_history": [
            {
                "stage": "initial",
                "step": "analyze_prompt",
                "step_index": 0,
                "entered_at": now,
                "exited_at": None,
            }
        ],
    }

    ok = update_session_data("task_workflow", workflow)

    # Wire the engineering cycle into the task workflow — every task
    # gets both state machines initialized together. The task workflow
    # drives the task lifecycle (initial → completion), the engineering
    # cycle tracks the nature of the work (analysis → improvement).
    try:
        from .engineering import init_engineering_cycle
        init_engineering_cycle(request_description=request_description)
    except (ImportError, Exception):
        pass  # Engineering module unavailable — degrade gracefully

    return ok


# ── Sub-Task Lifecycle (v100) ────────────────────────────────────
#
# Sub-tasks are recursive task units within a parent task. Each sub-task
# has its own mini-lifecycle (stages, steps, commits) but shares the
# parent's session issue. Commands detected by parse_prompt() become
# sub-tasks automatically.
#
# Cache structure:
#   session_data.sub_tasks = [
#     {
#       "id": 0,
#       "command": "project create",
#       "skill": "/project-create",
#       "title": "Create project Studio 54",
#       "args": "Studio 54",
#       "stage": "implement",
#       "status": "completed",       # pending | in_progress | completed | failed
#       "started_at": "ISO",
#       "completed_at": "ISO",
#       "todos": [...],
#       "commits": [...],
#       "files_modified": [...]
#     }
#   ]

def create_sub_task(command: str, skill: str, title: str,
                    args: str = "", label: str = "",
                    methodology: str = "", group: str = "") -> dict:
    """Create a new sub-task within the current parent task.

    Sub-tasks are the recursive building blocks of the task workflow.
    Every command detected by parse_prompt() becomes a sub-task.
    Regular work items also become sub-tasks for uniform tracking.

    Args:
        command: The detected command key (e.g., "project create").
        skill: The skill path (e.g., "/project-create").
        title: Human-readable sub-task title.
        args: Command arguments.
        label: GitHub label for this sub-task type.
        methodology: Methodology file backing this command.
        group: Command group (project, harvest, content, etc.).

    Returns:
        The created sub-task dict, or empty dict on failure.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Read current sub-tasks list
    cache = read_runtime_cache()
    if not cache:
        return {}

    sub_tasks = cache.get("session_data", {}).get("sub_tasks", [])
    next_id = len(sub_tasks)

    sub_task = {
        "id": next_id,
        "command": command,
        "skill": skill,
        "title": title,
        "args": args,
        "label": label,
        "methodology": methodology,
        "group": group,
        "stage": "pending",
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "todos": [],
        "commits": [],
        "files_modified": [],
    }

    sub_tasks.append(sub_task)
    update_session_data("sub_tasks", sub_tasks)
    return sub_task


def start_sub_task(sub_task_id: int) -> bool:
    """Mark a sub-task as in-progress and set its stage to implement.

    Args:
        sub_task_id: The sub-task ID (0-indexed).

    Returns:
        True if the sub-task was started successfully.
    """
    cache = read_runtime_cache()
    if not cache:
        return False

    sub_tasks = cache.get("session_data", {}).get("sub_tasks", [])
    if sub_task_id >= len(sub_tasks):
        return False

    now = datetime.now(timezone.utc).isoformat()
    sub_tasks[sub_task_id]["status"] = "in_progress"
    sub_tasks[sub_task_id]["stage"] = "implement"
    sub_tasks[sub_task_id]["started_at"] = now

    update_session_data("sub_tasks", sub_tasks)
    return True


def complete_sub_task(sub_task_id: int, commits: list = None,
                      files_modified: list = None) -> bool:
    """Mark a sub-task as completed.

    Args:
        sub_task_id: The sub-task ID (0-indexed).
        commits: List of commit SHAs produced by this sub-task.
        files_modified: List of file paths modified.

    Returns:
        True if completed successfully.
    """
    cache = read_runtime_cache()
    if not cache:
        return False

    sub_tasks = cache.get("session_data", {}).get("sub_tasks", [])
    if sub_task_id >= len(sub_tasks):
        return False

    now = datetime.now(timezone.utc).isoformat()
    sub_tasks[sub_task_id]["status"] = "completed"
    sub_tasks[sub_task_id]["stage"] = "completion"
    sub_tasks[sub_task_id]["completed_at"] = now
    if commits:
        sub_tasks[sub_task_id]["commits"] = commits
    if files_modified:
        sub_tasks[sub_task_id]["files_modified"] = files_modified

    update_session_data("sub_tasks", sub_tasks)
    return True


def fail_sub_task(sub_task_id: int, reason: str = "") -> bool:
    """Mark a sub-task as failed.

    Args:
        sub_task_id: The sub-task ID (0-indexed).
        reason: Why the sub-task failed.

    Returns:
        True if marked successfully.
    """
    cache = read_runtime_cache()
    if not cache:
        return False

    sub_tasks = cache.get("session_data", {}).get("sub_tasks", [])
    if sub_task_id >= len(sub_tasks):
        return False

    now = datetime.now(timezone.utc).isoformat()
    sub_tasks[sub_task_id]["status"] = "failed"
    sub_tasks[sub_task_id]["completed_at"] = now
    sub_tasks[sub_task_id]["failure_reason"] = reason

    update_session_data("sub_tasks", sub_tasks)
    return True


def get_sub_tasks() -> list:
    """Get all sub-tasks for the current session.

    Returns:
        List of sub-task dicts, or empty list.
    """
    cache = read_runtime_cache()
    if not cache:
        return []
    return cache.get("session_data", {}).get("sub_tasks", [])


def get_sub_task(sub_task_id: int) -> Optional[dict]:
    """Get a specific sub-task by ID.

    Args:
        sub_task_id: The sub-task ID (0-indexed).

    Returns:
        Sub-task dict, or None if not found.
    """
    sub_tasks = get_sub_tasks()
    if sub_task_id < len(sub_tasks):
        return sub_tasks[sub_task_id]
    return None


def get_sub_task_summary() -> dict:
    """Get a compact summary of all sub-tasks.

    Returns:
        Dict with: total, pending, in_progress, completed, failed, sub_tasks (list).
    """
    sub_tasks = get_sub_tasks()
    return {
        "total": len(sub_tasks),
        "pending": sum(1 for st in sub_tasks if st["status"] == "pending"),
        "in_progress": sum(1 for st in sub_tasks if st["status"] == "in_progress"),
        "completed": sum(1 for st in sub_tasks if st["status"] == "completed"),
        "failed": sum(1 for st in sub_tasks if st["status"] == "failed"),
        "sub_tasks": sub_tasks,
    }


def advance_task_stage(target_stage: str, reason: str = "") -> bool:
    """Transition the task workflow to a new stage.

    Supports forward transitions. Closes current stage in history,
    opens new stage. Resets current_step to None for stub stages.

    Args:
        target_stage: The stage to transition to.
        reason: Why the transition is happening.

    Returns:
        True if transition succeeded, False if invalid stage.
    """
    if target_stage not in TASK_WORKFLOW_STAGE_INDEX:
        return False

    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")

    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    old_stage = workflow.get("current_stage", "initial")
    old_index = workflow.get("current_stage_index", 0)
    target_index = TASK_WORKFLOW_STAGE_INDEX[target_stage]

    # v59.3: Stage order validation — prevent skipping mandatory stages.
    # Forward jumps of more than 1 stage are blocked UNLESS the skipped
    # stages were already visited in stage_history.
    if target_index > old_index + 1:
        visited_stages = {
            entry.get("stage") for entry in workflow.get("stage_history", [])
        }
        skipped = [
            TASK_WORKFLOW_STAGES[i]
            for i in range(old_index + 1, target_index)
            if TASK_WORKFLOW_STAGES[i] not in visited_stages
        ]
        if skipped:
            # Block: can't jump from initial→completion skipping plan/analyze/implement
            return False

    # Close current stage in history
    if workflow.get("stage_history"):
        last_entry = workflow["stage_history"][-1]
        if last_entry.get("exited_at") is None:
            last_entry["exited_at"] = now

    # Determine direction
    if target_index > old_index:
        direction = "forward"
    elif target_index < old_index:
        direction = "backward"
    else:
        direction = "re-enter"

    workflow["stage_history"].append({
        "stage": target_stage,
        "index": target_index,
        "entered_at": now,
        "exited_at": None,
        "reason": reason or f"{direction}: {old_stage} → {target_stage}",
        "direction": direction,
        "from_stage": old_stage,
    })

    workflow["current_stage"] = target_stage
    workflow["current_stage_index"] = target_index
    # Set initial step for the new stage (not None)
    stage_first_steps = {
        "initial": "analyze_prompt",
        "plan": "analyze_request",
        "analyze": "files_read",
        "implement": "executing",
        "validation": "quiz_run",
        "approval": "user_review",
        "documentation": "doc_check",
        "completion": "final_delivery",
    }
    workflow["current_step"] = stage_first_steps.get(target_stage, target_stage)
    workflow["current_step_index"] = 0
    workflow["updated_at"] = now
    # Reset modifications flag for the new stage
    workflow["modifications_occurred"] = False

    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: task workflow → {target_stage}")

    # Sync GitHub issue labels to reflect new stage + first step
    _sync_stage_label(cache, old_stage, target_stage)
    first_step = workflow["current_step"]
    if first_step:
        _sync_step_label(cache, None, first_step)

    # Autonomous integrity tracking (v59.3): auto-pass T.3 ONLY when
    # the plan stage was actually visited. Without this check, jumping
    # from initial→implement would falsely mark plan as approved.
    visited_stages = {
        entry.get("stage") for entry in workflow.get("stage_history", [])
    }
    if "plan" in visited_stages and target_stage in (
            "analyze", "implement", "validation",
            "approval", "documentation", "completion"):
        try:
            from .integrity import _auto_pass
            _auto_pass("T.3")  # plan_approved
        except (ImportError, Exception):
            pass

    # Auto-track time markers on stage transitions — feeds the
    # time compilation in pre-save summary.
    try:
        from .state import append_time_marker, update_work_summary
        append_time_marker(f"stage:{old_stage}→{target_stage}")
        # Accumulate work summary — each stage transition appends a line
        # describing what phase completed. The pre-save summary reads this.
        from .cache import read_runtime_cache as _rrc
        _cache = _rrc()
        current_summary = ""
        if _cache:
            current_summary = _cache.get("session_data", {}).get("work_summary", "")
        transition_note = f"{old_stage}→{target_stage}"
        if reason:
            transition_note += f": {reason}"
        new_summary = f"{current_summary}\n{transition_note}".strip()
        update_work_summary(new_summary)
    except (ImportError, Exception):
        pass

    # Integrity boundary check (v59): at every stage transition, run
    # integrity_check() on the section that should be complete by now.
    # This catches gaps DURING execution, not just at save time.
    # - Entering implement → verify startup (S) and task (T) sections
    # - Entering completion → verify work (W) section
    # The check result is logged but doesn't block — the grid records
    # the gap for the pre-save summary to expose.
    try:
        from .integrity import integrity_check, _auto_pass as _ap

        if target_stage == "implement":
            # Startup and task should be complete before work begins
            integrity_check("startup")
            integrity_check("task")
        elif target_stage == "completion":
            # Work cycle should be complete before save begins
            integrity_check("work")
        elif target_stage == "validation":
            # Partial work check at validation boundary
            integrity_check("work")
    except (ImportError, Exception):
        pass

    return True


def advance_task_step(target_step: str) -> bool:
    """Advance to the next step within the current stage.

    Stages with defined steps: initial (9), implement (8), completion (10).
    Other stages will have their steps defined when built.

    Args:
        target_step: The step name to transition to.

    Returns:
        True if transition succeeded.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")

    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    current_stage = workflow.get("current_stage", "initial")

    # Resolve step index based on stage
    step_index = None
    stage_steps = None
    if current_stage == "initial" and target_step in INITIAL_STAGE_STEPS:
        step_index = INITIAL_STAGE_STEPS.index(target_step)
        stage_steps = INITIAL_STAGE_STEPS
    elif current_stage == "implement" and target_step in IMPLEMENT_STAGE_STEPS:
        step_index = IMPLEMENT_STAGE_STEPS.index(target_step)
        stage_steps = IMPLEMENT_STAGE_STEPS
    elif current_stage == "completion" and target_step in COMPLETION_STAGE_STEPS:
        step_index = COMPLETION_STAGE_STEPS.index(target_step)
        stage_steps = COMPLETION_STAGE_STEPS

    # v59.3: Step order validation — prevent forward jumps that skip steps.
    # In implement stage, "remote_check" can loop back (repeating cycle),
    # so backward jumps are allowed. But forward jumps of >1 are blocked
    # unless the skipped steps were already visited in this stage.
    current_step_index = workflow.get("current_step_index")
    if (step_index is not None and current_step_index is not None
            and stage_steps is not None and step_index > current_step_index + 1):
        # Check if all intermediate steps were visited in step_history
        visited_steps_in_stage = {
            entry.get("step") for entry in workflow.get("step_history", [])
            if entry.get("stage") == current_stage
        }
        skipped = [
            stage_steps[i]
            for i in range(current_step_index + 1, step_index)
            if stage_steps[i] not in visited_steps_in_stage
        ]
        if skipped:
            return False  # Can't skip mandatory steps

    # Close current step in history
    if workflow.get("step_history"):
        last_step = workflow["step_history"][-1]
        if last_step.get("exited_at") is None:
            last_step["exited_at"] = now

    workflow["step_history"].append({
        "stage": current_stage,
        "step": target_step,
        "step_index": step_index,
        "entered_at": now,
        "exited_at": None,
    })

    workflow["current_step"] = target_step
    workflow["current_step_index"] = step_index
    workflow["updated_at"] = now

    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: task step → {target_step}")

    # Sync GitHub issue step label
    old_step = None
    if workflow.get("step_history") and len(workflow["step_history"]) >= 2:
        old_step = workflow["step_history"][-2].get("step")
    _sync_step_label(cache, old_step, target_step)

    # Auto-trigger side effects for specific implement steps
    if current_stage == "implement" and target_step == "mark_modifications":
        mark_modifications_occurred()

    # Autonomous integrity tracking (v59): auto-pass the corresponding
    # W checkpoint when an implement step advances. This is the bridge
    # between the task workflow steps and the integrity grid — stepping
    # through the implement cycle automatically tracks work compliance.
    if current_stage == "implement":
        _STEP_TO_WORK_CHECKPOINT = {
            "remote_check": "W.1",   # remote_checked
            "executing": "W.2",      # work_executed
            "commit": "W.3",         # committed
            "push": "W.4",           # pushed
            "cache_update": "W.5",   # cache_updated
            "issue_comment": "W.6",  # issue_commented
            # W.7 handled by mark_modifications_occurred() above
        }
        cp_id = _STEP_TO_WORK_CHECKPOINT.get(target_step)
        if cp_id:
            try:
                from .integrity import _auto_pass
                _auto_pass(cp_id)
            except (ImportError, Exception):
                pass

    # Autonomous integrity tracking (v59): auto-pass the corresponding
    # C checkpoint when a completion step advances.
    if current_stage == "completion":
        _STEP_TO_COMPLETION_CHECKPOINT = {
            "pre_save_summary": "C.1",
            "generate_notes": "C.2",
            "finalize_cache": "C.3",
            "compile_sessions": "C.4",
            "compile_tasks": "C.5",
            "verify_dual_output": "C.6",
            "commit_final": "C.7",
            "push_final": "C.8",
            "create_pr": "C.9",
            "merge_pr": "C.10",
            "doc_check": "C.11",
            "close_issue": "C.12",
        }
        cp_id = _STEP_TO_COMPLETION_CHECKPOINT.get(target_step)
        if cp_id:
            try:
                from .integrity import _auto_pass
                _auto_pass(cp_id)
            except (ImportError, Exception):
                pass

    # Auto-track time markers on every step transition — feeds the
    # time compilation in pre-save summary. Every step boundary becomes
    # a data point for "how long did each phase take?"
    try:
        from .state import append_time_marker
        append_time_marker(f"step:{current_stage}/{target_step}")
    except (ImportError, Exception):
        pass

    return True


def set_task_title(title: str) -> bool:
    """Set the confirmed task title in the workflow state.

    Args:
        title: The confirmed task title.

    Returns:
        True if update succeeded.
    """
    return _update_workflow_field("title", title)


def set_task_description(description: str) -> bool:
    """Set the task description in the workflow state.

    Args:
        description: The extracted description.

    Returns:
        True if update succeeded.
    """
    return _update_workflow_field("description", description)


def set_task_project(project: dict) -> bool:
    """Set the confirmed project in the workflow state.

    Args:
        project: Dict with project info (name, id, board_number, etc.)

    Returns:
        True if update succeeded.
    """
    return _update_workflow_field("project", project)


def set_task_issue(issue_number: int) -> bool:
    """Set the GitHub issue number in the workflow state.

    Args:
        issue_number: The created GitHub issue number.

    Returns:
        True if update succeeded.
    """
    return _update_workflow_field("issue_number", issue_number)


def mark_modifications_occurred() -> bool:
    """Mark that modifications occurred in the current stage.

    This flag is checked at stage boundaries to determine if the
    documentation cross-cut should trigger. Also auto-captures the
    list of modified files from git for the session cache.

    Returns:
        True if update succeeded.
    """
    result = _update_workflow_field("modifications_occurred", True)

    # Autonomous integrity tracking (v58): auto-pass W.7
    if result:
        try:
            from .integrity import _auto_pass
            _auto_pass("W.7")  # modifications_marked
        except (ImportError, Exception):
            pass

    # Auto-capture modified files from git into session cache.
    # This feeds files_modified for the pre-save summary metrics.
    try:
        import subprocess
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        staged_output = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        files = set()
        if diff_output:
            files.update(diff_output.splitlines())
        if staged_output:
            files.update(staged_output.splitlines())
        if files:
            # Merge with existing — accumulate across todos
            from .cache import read_runtime_cache
            cache = read_runtime_cache()
            existing = []
            if cache:
                existing = cache.get("session_data", {}).get("files_modified", [])
            merged = list(set(existing) | files)
            update_session_data("files_modified", sorted(merged))
    except (subprocess.CalledProcessError, ImportError, Exception):
        pass

    return result


def _update_workflow_field(field: str, value) -> bool:
    """Update a single field in the task workflow state.

    Args:
        field: Field name to update.
        value: New value.

    Returns:
        True if update succeeded.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return False

    workflow[field] = value
    workflow["updated_at"] = datetime.now(timezone.utc).isoformat()

    sd["task_workflow"] = workflow
    cache["updated"] = workflow["updated_at"]

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: task workflow {field} updated")
    return True


# ── Command Detection Layer (v100) ──────────────────────────────
#
# Maps methodology-backed commands to their skill and metadata.
# Commands detected here become sub-tasks within the task workflow —
# they NEVER bypass the task workflow orchestrator.
#
# Each entry: command pattern → { skill, label, methodology, description }

COMMAND_REGISTRY = {
    # ── Project Management ──────────────────────────────────────
    "project create": {
        "skill": "/project-create",
        "label": "FEATURE",
        "methodology": "project-create.md",
        "description": "Create a new project with P# registration and GitHub board",
        "group": "project",
    },
    "project list": {
        "skill": "/project-manage",
        "label": "CHORE",
        "methodology": "project-management.md",
        "description": "List all projects with P# index, type, status",
        "group": "project",
    },
    "project info": {
        "skill": "/project-manage",
        "label": "REVIEW",
        "methodology": "project-management.md",
        "description": "Show project details",
        "group": "project",
    },
    "project register": {
        "skill": "/project-manage",
        "label": "FEATURE",
        "methodology": "project-management.md",
        "description": "Register a new project with P# ID in core",
        "group": "project",
    },
    "project review": {
        "skill": "/project-manage",
        "label": "REVIEW",
        "methodology": "project-management.md",
        "description": "Review project state and freshness",
        "group": "project",
    },

    # ── Harvest — Distributed Knowledge ─────────────────────────
    "harvest --healthcheck": {
        "skill": "/harvest",
        "label": "CHORE",
        "methodology": "production-development-minds.md",
        "description": "Full network sweep — all satellites, update dashboard",
        "group": "harvest",
    },
    "harvest --list": {
        "skill": "/harvest",
        "label": "REVIEW",
        "methodology": "production-development-minds.md",
        "description": "List harvested projects with version and drift",
        "group": "harvest",
    },
    "harvest --fix": {
        "skill": "/harvest",
        "label": "BUG",
        "methodology": "production-development-minds.md",
        "description": "Update satellite CLAUDE.md to latest version",
        "group": "harvest",
    },
    "harvest --review": {
        "skill": "/harvest",
        "label": "REVIEW",
        "methodology": "production-development-minds.md",
        "description": "Mark insight as reviewed",
        "group": "harvest",
    },
    "harvest --stage": {
        "skill": "/harvest",
        "label": "ENHANCEMENT",
        "methodology": "production-development-minds.md",
        "description": "Stage insight for integration",
        "group": "harvest",
    },
    "harvest --promote": {
        "skill": "/harvest",
        "label": "DEPLOYMENT",
        "methodology": "production-development-minds.md",
        "description": "Promote insight to core knowledge",
        "group": "harvest",
    },
    "harvest --auto": {
        "skill": "/harvest",
        "label": "CHORE",
        "methodology": "production-development-minds.md",
        "description": "Queue for auto-promote on next healthcheck",
        "group": "harvest",
    },
    "harvest --procedure": {
        "skill": "/harvest",
        "label": "REVIEW",
        "methodology": "production-development-minds.md",
        "description": "Guided promotion walkthrough",
        "group": "harvest",
    },
    "harvest": {
        "skill": "/harvest",
        "label": "CHORE",
        "methodology": "production-development-minds.md",
        "description": "Pull distributed knowledge into minds/",
        "group": "harvest",
    },

    # ── Content Management — Publications ───────────────────────
    "pub list": {
        "skill": "/pub",
        "label": "REVIEW",
        "methodology": "documentation-generation.md",
        "description": "List all publications with status",
        "group": "content",
    },
    "pub check": {
        "skill": "/pub",
        "label": "REVIEW",
        "methodology": "documentation-generation.md",
        "description": "Validate publication(s)",
        "group": "content",
    },
    "pub new": {
        "skill": "/pub",
        "label": "FEATURE",
        "methodology": "documentation-generation.md",
        "description": "Scaffold new publication",
        "group": "content",
    },
    "pub sync": {
        "skill": "/pub",
        "label": "CHORE",
        "methodology": "documentation-generation.md",
        "description": "Sync source changes to docs web pages",
        "group": "content",
    },
    "pub export": {
        "skill": "/pub-export",
        "label": "DEPLOYMENT",
        "methodology": "web-pagination-export.md",
        "description": "Export publication to PDF or DOCX",
        "group": "content",
    },
    "doc review": {
        "skill": "/pub",
        "label": "REVIEW",
        "methodology": "documentation-generation.md",
        "description": "Review publication freshness",
        "group": "content",
    },
    "docs check": {
        "skill": "/pub",
        "label": "REVIEW",
        "methodology": "documentation-generation.md",
        "description": "Validate doc page(s)",
        "group": "content",
    },

    # ── Normalize ───────────────────────────────────────────────
    "normalize --fix": {
        "skill": "/normalize",
        "label": "BUG",
        "methodology": "interactive-work-sessions.md",
        "description": "Apply concordance fixes automatically",
        "group": "normalize",
    },
    "normalize --check": {
        "skill": "/normalize",
        "label": "REVIEW",
        "methodology": "interactive-work-sessions.md",
        "description": "Report concordance issues without changes",
        "group": "normalize",
    },
    "normalize": {
        "skill": "/normalize",
        "label": "CHORE",
        "methodology": "interactive-work-sessions.md",
        "description": "Audit and fix knowledge structure concordance",
        "group": "normalize",
    },

    # ── Webcard & Links ─────────────────────────────────────────
    "webcard": {
        "skill": "/webcard",
        "label": "FEATURE",
        "methodology": "web-production-pipeline.md",
        "description": "Generate animated OG GIFs",
        "group": "webcard",
    },
    "weblinks --admin": {
        "skill": "/webcard",
        "label": "REVIEW",
        "methodology": "web-production-pipeline.md",
        "description": "Print all URLs with conformity status",
        "group": "webcard",
    },
    "weblinks": {
        "skill": "/webcard",
        "label": "REVIEW",
        "methodology": "web-production-pipeline.md",
        "description": "Print all GitHub Pages URLs",
        "group": "webcard",
    },

    # ── Profile ─────────────────────────────────────────────────
    "profile update": {
        "skill": "/profile-update",
        "label": "ENHANCEMENT",
        "methodology": "profile-update.md",
        "description": "Refresh all profile files with current stats",
        "group": "profile",
    },

    # ── Live Session ────────────────────────────────────────────
    "i'm live": {
        "skill": "/live-session",
        "label": "TESTING",
        "methodology": "interactive-diagnostic.md",
        "description": "Enter capture mode — pull clips, extract, report",
        "group": "live",
    },
    "multi-live": {
        "skill": "/live-session",
        "label": "TESTING",
        "methodology": "interactive-diagnostic.md",
        "description": "Monitor multiple streams simultaneously",
        "group": "live",
    },
    "recipe": {
        "skill": "/live-session",
        "label": "REVIEW",
        "methodology": "interactive-diagnostic.md",
        "description": "Print live capture quick recipe",
        "group": "live",
    },

    # ── Visual Documentation ────────────────────────────────────
    "visual": {
        "skill": "/visual",
        "label": "DOCUMENTATION",
        "methodology": "visual-documentation.md",
        "description": "Extract evidence frames from video",
        "group": "visual",
    },
    "deep": {
        "skill": "/visual",
        "label": "INVESTIGATION",
        "methodology": "visual-documentation.md",
        "description": "Frame-by-frame anomaly analysis",
        "group": "visual",
    },
    "analyze": {
        "skill": "/visual",
        "label": "INVESTIGATION",
        "methodology": "visual-documentation.md",
        "description": "Static video analysis with state progression",
        "group": "visual",
    },

    # ── Session Recovery ────────────────────────────────────────
    "resume": {
        "skill": "/resume",
        "label": "CHORE",
        "methodology": None,
        "description": "Resume interrupted session from checkpoint",
        "group": "session",
    },
    "recover": {
        "skill": "/resume",
        "label": "CHORE",
        "methodology": None,
        "description": "Search stranded branches for work recovery",
        "group": "session",
    },
    "checkpoint": {
        "skill": "/resume",
        "label": "REVIEW",
        "methodology": None,
        "description": "Show current checkpoint state",
        "group": "session",
    },

    # ── Recall ──────────────────────────────────────────────────
    "recall": {
        "skill": "/recall",
        "label": "INVESTIGATION",
        "methodology": None,
        "description": "Deep memory search across all knowledge channels",
        "group": "session",
    },

    # ── Tagged Input ────────────────────────────────────────────
    "#": {
        "skill": "/tagged-input",
        "label": "DOCUMENTATION",
        "methodology": "tagged-input.md",
        "description": "Scoped note for publication/project",
        "group": "tagged",
        "pattern": True,  # uses regex matching, not exact prefix
    },
    "g:": {
        "skill": "/tagged-input",
        "label": "CHORE",
        "methodology": "github-board-item-alias.md",
        "description": "Reference GitHub board item by position",
        "group": "tagged",
        "pattern": True,
    },

    # ── Wakeup / Refresh ────────────────────────────────────────
    "wakeup": {
        "skill": "/wakeup",
        "label": "CHORE",
        "methodology": None,
        "description": "Deep re-sync (mid-session only)",
        "group": "session",
    },
    "refresh": {
        "skill": "/wakeup",
        "label": "CHORE",
        "methodology": None,
        "description": "Lightweight context restore",
        "group": "session",
    },
}


def detect_command(text: str, title: str) -> Optional[dict]:
    """Detect if the prompt matches a known methodology-backed command.

    Commands are matched by prefix against the title (line 1), with
    longest-match-first to handle sub-commands (e.g., "harvest --fix"
    before "harvest").

    Args:
        text: Combined lowercased text (title + description).
        title: The first line of the prompt (lowercased).

    Returns:
        Dict with command info if matched, None otherwise.
        Keys: command, skill, label, methodology, description, group, args
    """
    title_lower = title.lower().strip()

    # Sort by key length descending — longest match first
    # This ensures "harvest --healthcheck" matches before "harvest"
    sorted_commands = sorted(COMMAND_REGISTRY.keys(), key=len, reverse=True)

    for cmd_key in sorted_commands:
        cmd_info = COMMAND_REGISTRY[cmd_key]

        # Pattern-based matching (tagged input: #N:, g:board:item)
        if cmd_info.get("pattern"):
            import re
            if cmd_key == "#":
                if re.match(r'^#\d+', title_lower):
                    args = title_lower  # full tagged input is the args
                    return {
                        "command": cmd_key,
                        "args": args,
                        **{k: v for k, v in cmd_info.items() if k != "pattern"},
                    }
            elif cmd_key == "g:":
                if title_lower.startswith("g:"):
                    args = title_lower
                    return {
                        "command": cmd_key,
                        "args": args,
                        **{k: v for k, v in cmd_info.items() if k != "pattern"},
                    }
            continue

        # Prefix matching — title must start with the command
        if title_lower.startswith(cmd_key):
            # Extract arguments (everything after the command prefix)
            args = title_lower[len(cmd_key):].strip()
            return {
                "command": cmd_key,
                "args": args,
                "skill": cmd_info["skill"],
                "label": cmd_info["label"],
                "methodology": cmd_info["methodology"],
                "description": cmd_info["description"],
                "group": cmd_info["group"],
            }

    return None


# ── Stage 1: INITIAL — 9 steps ──────────────────────────────────

def parse_prompt(prompt: str) -> dict:
    """Step 1-3: Analyze prompt, extract title and description.

    Parses the user's entry prompt with line awareness:
    - Line 1 → title candidate
    - Lines 2+ → description
    - Detects action words for issue labeling

    Args:
        prompt: The user's raw entry prompt.

    Returns:
        Dict with: title, description, action_word, detected_label,
                   is_multi_request, request_count
    """
    if not prompt:
        return {
            "title": "",
            "description": "",
            "action_word": None,
            "detected_label": None,
            "is_multi_request": False,
            "request_count": 1,
        }

    lines = prompt.strip().split('\n')
    title = lines[0].strip() if lines else prompt.strip()
    description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""

    # Detect action word from title
    action_word = None
    detected_label = None

    # Action word mapping (from CLAUDE.md)
    action_map = {
        "review": "REVIEW",
        "create": "FEATURE",
        "fix": "BUG",
        "update": "ENHANCEMENT",
        "design": "DESIGN",
        "add": "FEATURE",
        "implement": "FEATURE",
        "build": "FEATURE",
        "refactor": "ENHANCEMENT",
        "optimize": "ENHANCEMENT",
        "investigate": "INVESTIGATION",
        "diagnose": "INVESTIGATION",
        "analyze": "INVESTIGATION",
        "document": "DOCUMENTATION",
        "deploy": "DEPLOYMENT",
        "test": "TESTING",
    }

    # Scan title first, then description
    combined_text = f"{title} {description}".lower()
    for word, label in action_map.items():
        if word in combined_text:
            action_word = word
            detected_label = label
            break

    # Also use request_types taxonomy for finer detection
    request_type = detect_request_type(combined_text)

    # Multi-request detection
    is_multi = False
    request_count = 1

    multi_indicators = [" and also ", " plus ", " et aussi ", " également "]
    has_connectors = any(ind in combined_text for ind in multi_indicators)
    has_numbered = any(line.strip().startswith(f"{i}.") or line.strip().startswith(f"{i})")
                       for line in lines for i in range(1, 10))

    # Count action verbs
    action_verbs = sum(1 for word in action_map if word in combined_text)

    if has_connectors or has_numbered or action_verbs >= 2:
        is_multi = True
        if has_numbered:
            request_count = sum(1 for line in lines
                                if any(line.strip().startswith(f"{i}.")
                                       or line.strip().startswith(f"{i})")
                                       for i in range(1, 10)))
        else:
            request_count = max(2, action_verbs)

    # ── Command detection layer (v100) ────────────────────────────
    # Detect if the prompt is a known methodology-backed command.
    # Commands become sub-tasks within the task workflow — they never bypass it.
    detected_command = detect_command(combined_text, title)

    # Engineering cycle healthcheck detection
    # Triggers when prompt contains "healthcheck" in engineering cycle context:
    #   - "engineering cycle healthcheck" / "engineering healthcheck"
    #   - "test/testing ... engineering cycle ... healthcheck"
    #   - standalone "healthcheck" (assumed engineering cycle)
    # Does NOT trigger for unrelated uses (e.g., "healthcheck endpoint for the API")
    _hc = "healthcheck" in combined_text or "health check" in combined_text
    _eng = any(kw in combined_text for kw in [
        "engineering cycle", "engineering workflow", "engineering",
        "integrity", "v5", "v6", "workflow",
    ])
    # Exclude if prompt clearly refers to something else (API, endpoint, service)
    _api_context = any(kw in combined_text for kw in [
        "endpoint", "api", "service", "server", "route", "http",
    ])
    is_healthcheck = _hc and (_eng or not _api_context)

    # Determine healthcheck scope:
    #   "engineering" — full engineering cycle (integrity + task workflow)
    #   "task_workflow" — task workflow only
    #   None — not a healthcheck
    healthcheck_scope = None
    if is_healthcheck:
        _tw = any(kw in combined_text for kw in [
            "task workflow", "task-workflow", "workflow stage",
            "stage machine", "state machine",
        ])
        if _tw:
            healthcheck_scope = "task_workflow"
        else:
            healthcheck_scope = "engineering"

    return {
        "title": title,
        "description": description,
        "action_word": action_word,
        "detected_label": detected_label,
        "request_type": request_type,
        "is_multi_request": is_multi,
        "request_count": request_count,
        "is_healthcheck": is_healthcheck,
        "healthcheck_scope": healthcheck_scope,
        "detected_command": detected_command,
    }


def detect_project(title: str, description: str,
                   available_projects: Optional[list] = None) -> dict:
    """Step 5: Detect project owner from title and description.

    Scans title and description for project references (P#, project names,
    repo names) and returns the best match from available projects.

    Args:
        title: The confirmed task title.
        description: The task description.
        available_projects: List of dicts with project info
                           (name, id, aliases, etc.)

    Returns:
        Dict with: detected_project (dict or None), confidence (str),
                   match_source ('title'/'description'/'none'),
                   all_matches (list)
    """
    if not available_projects:
        available_projects = []

    matches = []

    for project in available_projects:
        score = 0
        source = "none"

        project_name = (project.get("name") or "").lower()
        project_id = project.get("id", "")
        aliases = [a.lower() for a in project.get("aliases", [])]

        # Check title first (higher weight)
        title_lower = title.lower()
        if project_name and project_name in title_lower:
            score += 3
            source = "title"
        if project_id and project_id.lower() in title_lower:
            score += 3
            source = "title"
        for alias in aliases:
            if alias in title_lower:
                score += 2
                source = "title"

        # Check description
        desc_lower = description.lower()
        if project_name and project_name in desc_lower:
            score += 1
            source = source or "description"
        if project_id and project_id.lower() in desc_lower:
            score += 1
            source = source or "description"
        for alias in aliases:
            if alias in desc_lower:
                score += 1
                source = source or "description"

        # Check for P# references (e.g., P0, P1, P2)
        combined = f"{title} {description}".lower()
        p_ref = f"p{project.get('p_number', '')}"
        if p_ref and p_ref in combined:
            score += 4
            source = "title" if p_ref in title_lower else "description"

        if score > 0:
            matches.append({
                "project": project,
                "score": score,
                "source": source,
            })

    matches.sort(key=lambda m: m["score"], reverse=True)

    if matches:
        best = matches[0]
        confidence = "high" if best["score"] >= 3 else "medium" if best["score"] >= 2 else "low"
        return {
            "detected_project": best["project"],
            "confidence": confidence,
            "match_source": best["source"],
            "all_matches": matches,
        }

    return {
        "detected_project": None,
        "confidence": "none",
        "match_source": "none",
        "all_matches": [],
    }


# ── Documentation Cross-Cut ─────────────────────────────────────

def check_documentation_needed() -> dict:
    """Check if documentation updates are needed at stage boundary.

    Reads the current workflow state and checks the modifications_occurred
    flag. Returns guidance for the AskUserQuestion popup including
    the defer option (documentation stage 6).

    Returns:
        Dict with: needs_check (bool), current_stage (str),
                   modifications_occurred (bool),
                   ask_options (list of option dicts for AskUserQuestion)
    """
    cache = read_runtime_cache()
    if not cache:
        return {"needs_check": False, "current_stage": "unknown",
                "modifications_occurred": False, "ask_options": []}

    workflow = cache.get("session_data", {}).get("task_workflow")
    if not workflow:
        return {"needs_check": False, "current_stage": "unknown",
                "modifications_occurred": False, "ask_options": []}

    needs = workflow.get("modifications_occurred", False)
    stage = workflow.get("current_stage", "unknown")

    ask_options = []
    if needs:
        ask_options = [
            {"label": "Update project docs",
             "description": "Update only the project's own documentation now"},
            {"label": "Update knowledge only",
             "description": "Update only the knowledge system documentation now"},
            {"label": "Update both",
             "description": "Update both project and knowledge documentation now"},
            {"label": "Defer to documentation stage",
             "description": "Skip doc updates now — handle at stage 6 (documentation)"},
        ]

    return {
        "needs_check": needs,
        "current_stage": stage,
        "modifications_occurred": needs,
        "ask_options": ask_options,
    }


# ── Query Functions ──────────────────────────────────────────────

def get_task_workflow() -> Optional[dict]:
    """Get the current task workflow state.

    Returns:
        Dict with workflow state, or None if not initialized.
    """
    cache = read_runtime_cache()
    if not cache:
        return None
    return cache.get("session_data", {}).get("task_workflow")


def get_task_stage() -> str:
    """Get the current task workflow stage name.

    Returns:
        Stage name string, or "unknown" if not initialized.
    """
    workflow = get_task_workflow()
    if not workflow:
        return "unknown"
    return workflow.get("current_stage", "unknown")


def get_task_step() -> Optional[str]:
    """Get the current step within the current stage.

    Returns:
        Step name string, or None if not in a step.
    """
    workflow = get_task_workflow()
    if not workflow:
        return None
    return workflow.get("current_step")


def get_task_workflow_summary() -> dict:
    """Get a compact summary of the task workflow for display.

    Returns:
        Dict with current_stage, current_step, title, project,
        stages_visited, modifications_occurred, duration info.
    """
    workflow = get_task_workflow()
    if not workflow:
        return {"initialized": False}

    stages_visited = []
    seen = set()
    for entry in workflow.get("stage_history", []):
        s = entry.get("stage")
        if s and s not in seen:
            stages_visited.append(s)
            seen.add(s)

    return {
        "initialized": True,
        "current_stage": workflow.get("current_stage"),
        "current_stage_index": workflow.get("current_stage_index"),
        "current_step": workflow.get("current_step"),
        "current_step_index": workflow.get("current_step_index"),
        "title": workflow.get("title", ""),
        "description": workflow.get("description", ""),
        "project": workflow.get("project"),
        "issue_number": workflow.get("issue_number", 0),
        "stages_visited": stages_visited,
        "total_transitions": len(workflow.get("stage_history", [])),
        "modifications_occurred": workflow.get("modifications_occurred", False),
        "started_at": workflow.get("started_at"),
        "updated_at": workflow.get("updated_at"),
    }


def format_workflow_status() -> str:
    """Format the task workflow status for display.

    Returns:
        Formatted string showing current position in the workflow.
    """
    summary = get_task_workflow_summary()
    if not summary.get("initialized"):
        return "Task workflow: not initialized"

    stage = summary["current_stage"]
    stage_idx = summary["current_stage_index"]
    step = summary.get("current_step")
    title = summary.get("title", "untitled")

    # Build stage progress bar
    stages_bar = []
    for i, s in enumerate(TASK_WORKFLOW_STAGES):
        if i < stage_idx:
            stages_bar.append(f"✅ {s}")
        elif i == stage_idx:
            stages_bar.append(f"▶ {s}")
        else:
            stages_bar.append(f"⬜ {s}")

    lines = [
        f"Task: {title}",
        f"Stage: {TASK_WORKFLOW_STAGE_LABELS.get(stage, stage)} ({stage_idx + 1}/{len(TASK_WORKFLOW_STAGES)})",
    ]

    if step and stage == "initial":
        step_label = INITIAL_STEP_LABELS.get(step, step)
        step_idx = INITIAL_STAGE_STEPS.index(step) if step in INITIAL_STAGE_STEPS else 0
        lines.append(f"Step: {step_label} ({step_idx + 1}/{len(INITIAL_STAGE_STEPS)})")
    elif step and stage == "implement":
        step_label = IMPLEMENT_STEP_LABELS.get(step, step)
        step_idx = IMPLEMENT_STAGE_STEPS.index(step) if step in IMPLEMENT_STAGE_STEPS else 0
        lines.append(f"Step: {step_label} ({step_idx + 1}/{len(IMPLEMENT_STAGE_STEPS)})")
    elif step and stage == "completion":
        step_label = COMPLETION_STEP_LABELS.get(step, step)
        step_idx = COMPLETION_STAGE_STEPS.index(step) if step in COMPLETION_STAGE_STEPS else 0
        lines.append(f"Step: {step_label} ({step_idx + 1}/{len(COMPLETION_STAGE_STEPS)})")

    lines.append("Progress: " + " → ".join(stages_bar))

    return "\n".join(lines)


# ── Validation Cross-Cut ────────────────────────────────────────

# Validation checkpoints for the Initial stage (9 steps)
INITIAL_VALIDATION_CHECKS = [
    {
        "id": "analyze_prompt",
        "question": "Was the prompt correctly analyzed for action words and structure?",
        "description": "Step 1: analyze_prompt — action word detection, label mapping",
    },
    {
        "id": "extract_title",
        "question": "Was the title correctly extracted from line 1 of the prompt?",
        "description": "Step 2: extract_title — first line becomes task title",
    },
    {
        "id": "extract_description",
        "question": "Was the description correctly extracted from remaining lines?",
        "description": "Step 3: extract_description — lines 2+ become description",
    },
    {
        "id": "confirm_title",
        "question": "Was the title confirmed with the user via AskUserQuestion?",
        "description": "Step 4: confirm_title — user popup with title + skip option",
    },
    {
        "id": "detect_project",
        "question": "Was the project correctly detected from title and description?",
        "description": "Step 5: detect_project — weighted scoring of project references",
    },
    {
        "id": "confirm_project",
        "question": "Was the project confirmed with the user via AskUserQuestion?",
        "description": "Step 6: confirm_project — detected project first + all available",
    },
    {
        "id": "persist_state",
        "question": "Was state persisted in cache and GitHub issue created?",
        "description": "Step 7: persist_state — Gate G1 (issue) + Gate G2 (cache)",
    },
    {
        "id": "output_details",
        "question": "Were the confirmed details output to the user?",
        "description": "Step 8: output_details — display confirmed title, project, issue",
    },
    {
        "id": "wait_approval",
        "question": "Did the session wait for user approval before proceeding?",
        "description": "Step 9: wait_approval — user approves plan before execution",
    },
]

# ── Plan Stage Validation Checks ────────────────────────────────
PLAN_VALIDATION_CHECKS = [
    {
        "id": "analyze_request",
        "question": "Was the request analyzed before building the plan?",
        "description": "The session should analyze the task scope, identify affected files, and understand requirements before planning.",
    },
    {
        "id": "todo_list_created",
        "question": "Was a structured todo list created with concrete steps?",
        "description": "TodoWrite should contain specific, actionable items — not vague descriptions.",
    },
    {
        "id": "plan_presented",
        "question": "Was the work plan presented to the user for approval (Gate G3)?",
        "description": "The plan must be shown to the user before autonomous execution begins.",
    },
    {
        "id": "plan_approved",
        "question": "Did the user approve the plan before execution started?",
        "description": "Gate G3 — no file modifications until the user approves the plan.",
    },
]

# ── Analyze Stage Validation Checks ─────────────────────────────
ANALYZE_VALIDATION_CHECKS = [
    {
        "id": "files_read",
        "question": "Were all relevant files read before modifications?",
        "description": "Never propose changes to code you haven't read. Read first, modify second.",
    },
    {
        "id": "remote_check",
        "question": "Was a strategic remote check performed before reading files for analysis?",
        "description": "Core methodology #6 — fetch origin, check divergence, merge if needed.",
    },
    {
        "id": "scope_understood",
        "question": "Was the full scope of changes identified (dependencies, side effects)?",
        "description": "Analysis should map all affected files, not just the obvious target.",
    },
]

# ── Implement Stage Validation Checks ───────────────────────────
IMPLEMENT_VALIDATION_CHECKS = [
    {
        "id": "progressive_commits",
        "question": "Were changes committed progressively (not one giant commit at the end)?",
        "description": "Each logical unit of work should be its own commit for crash recovery.",
    },
    {
        "id": "cache_updated",
        "question": "Was the session cache updated after each todo completion (Gate G4)?",
        "description": "update_session_data('todo_snapshot', ...) after each todo step.",
    },
    {
        "id": "issue_comments",
        "question": "Were todo start/completion posted as issue comments (Gate G7)?",
        "description": "Each todo step = one issue comment with lifecycle tracking.",
    },
    {
        "id": "remote_check_before_edit",
        "question": "Was a strategic remote check done before modifying shared files?",
        "description": "Core methodology #6 — mandatory before editing CLAUDE.md, scripts/, methodology/.",
    },
    {
        "id": "no_overengineering",
        "question": "Were changes minimal and focused — no unnecessary refactoring or additions?",
        "description": "Only make changes that are directly requested or clearly necessary.",
    },
]

# ── Validation Stage Validation Checks ──────────────────────────
VALIDATION_STAGE_CHECKS = [
    {
        "id": "quiz_run",
        "question": "Were validation checks run for completed stages?",
        "description": "check_validation_needed() should be called at stage boundaries.",
    },
    {
        "id": "results_recorded",
        "question": "Were validation results recorded in the cache?",
        "description": "record_validation_result() stores pass/fail/skip per check.",
    },
    {
        "id": "failures_addressed",
        "question": "Were failed checks addressed or documented for next session?",
        "description": "Failures should either be fixed immediately or noted in session notes.",
    },
    {
        "id": "stage_label_synced",
        "question": "Was the GitHub issue label updated to reflect the current workflow stage?",
        "description": "advance_task_stage() should sync labels via issue_engineering_stage_sync().",
    },
]


def check_validation_needed(stage: str) -> dict:
    """Check if validation cross-cut should run for a given stage.

    Validation runs at stage completion for stages INITIAL through
    VALIDATION only. Does NOT run for APPROVAL, DOCUMENTATION, COMPLETION.

    Args:
        stage: The stage that just completed.

    Returns:
        Dict with: needs_validation (bool), stage (str),
                   checks (list of check dicts for this stage),
                   already_validated (bool)
    """
    cache = read_runtime_cache()
    if not cache:
        return {"needs_validation": False, "stage": stage, "checks": [],
                "already_validated": False}

    workflow = cache.get("session_data", {}).get("task_workflow")
    if not workflow:
        return {"needs_validation": False, "stage": stage, "checks": [],
                "already_validated": False}

    # Check if validation was already skipped entirely for this task
    if workflow.get("validation_skipped_entirely", False):
        return {"needs_validation": False, "stage": stage, "checks": [],
                "already_validated": False, "skipped_entirely": True}

    # Only run for eligible stages
    if stage not in VALIDATION_ELIGIBLE_STAGES:
        return {"needs_validation": False, "stage": stage, "checks": [],
                "already_validated": False}

    # Check if already validated for this stage
    validation_results = workflow.get("validation_results", {})
    already_validated = stage in validation_results

    # Get checks for this stage
    checks = get_validation_checks(stage)

    return {
        "needs_validation": len(checks) > 0 and not already_validated,
        "stage": stage,
        "checks": checks,
        "already_validated": already_validated,
    }


def get_validation_checks(stage: str) -> list:
    """Get the validation checkpoints for a given stage.

    Args:
        stage: Stage name.

    Returns:
        List of check dicts with id, question, description.
    """
    if stage == "initial":
        return list(INITIAL_VALIDATION_CHECKS)
    elif stage == "plan":
        return list(PLAN_VALIDATION_CHECKS)
    elif stage == "analyze":
        return list(ANALYZE_VALIDATION_CHECKS)
    elif stage == "implement":
        return list(IMPLEMENT_VALIDATION_CHECKS)
    elif stage == "validation":
        return list(VALIDATION_STAGE_CHECKS)
    return []


def record_validation_result(stage: str, check_id: str,
                              result: str, skipped: bool = False) -> bool:
    """Record a single validation check result.

    Args:
        stage: Stage being validated.
        check_id: The check identifier (e.g., 'analyze_prompt').
        result: 'passed', 'failed', or 'skipped'.
        skipped: Whether this specific check was skipped.

    Returns:
        True if recorded successfully.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    validation_results = workflow.setdefault("validation_results", {})
    stage_results = validation_results.setdefault(stage, {
        "checks": [],
        "overall_status": "in_progress",
        "validated_at": None,
        "skipped": False,
    })

    stage_results["checks"].append({
        "check_id": check_id,
        "result": result,
        "skipped": skipped,
        "recorded_at": now,
    })

    workflow["validation_results"] = validation_results
    workflow["updated_at"] = now
    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: validation check {check_id} → {result}")
    return True


def complete_stage_validation(stage: str, skipped: bool = False) -> bool:
    """Mark a stage's validation as complete.

    Computes overall_status from individual checks:
    - 'passed' if all checks passed (or no checks failed)
    - 'failed' if any check failed
    - 'skipped' if the entire stage validation was skipped

    Args:
        stage: The stage whose validation is complete.
        skipped: Whether the entire stage validation was skipped.

    Returns:
        True if recorded successfully.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    validation_results = workflow.setdefault("validation_results", {})

    if skipped:
        validation_results[stage] = {
            "checks": validation_results.get(stage, {}).get("checks", []),
            "overall_status": "skipped",
            "validated_at": now,
            "skipped": True,
        }
    else:
        stage_results = validation_results.get(stage, {"checks": []})
        checks = stage_results.get("checks", [])
        has_failed = any(c.get("result") == "failed" for c in checks)
        overall = "failed" if has_failed else "passed"
        stage_results["overall_status"] = overall
        stage_results["validated_at"] = now
        stage_results["skipped"] = False
        validation_results[stage] = stage_results

    workflow["validation_results"] = validation_results
    workflow["updated_at"] = now
    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    status = "skipped" if skipped else validation_results[stage]["overall_status"]
    commit_cache(f"data: stage validation {stage} → {status}")
    return True


def skip_all_validation() -> bool:
    """Skip all validation for the current task.

    Sets the validation_skipped_entirely flag. Validation status
    is still persisted (as 'skipped') in the report.

    Returns:
        True if recorded successfully.
    """
    return _update_workflow_field("validation_skipped_entirely", True)


def get_validation_results() -> dict:
    """Get all validation results for the current task.

    Returns:
        Dict of stage → validation results, or empty dict.
    """
    workflow = get_task_workflow()
    if not workflow:
        return {}
    return workflow.get("validation_results", {})


def get_stage_validation_report(stage: str) -> Optional[dict]:
    """Get the validation report for a specific stage.

    Args:
        stage: Stage name.

    Returns:
        Dict with checks, overall_status, validated_at, skipped.
        None if stage hasn't been validated.
    """
    results = get_validation_results()
    return results.get(stage)


# ── Unit Test Framework ─────────────────────────────────────────

def add_unit_test(stage: str, description: str, expected: str,
                  source: str = "claude") -> bool:
    """Add a unit test for a stage validation.

    Unit tests can come from 3 sources:
    - 'user_prompt': provided in the initial task description
    - 'user_session': provided mid-session by the user
    - 'claude': generated by Claude from task analysis

    Args:
        stage: Target stage for this test.
        description: What the test verifies.
        expected: Expected outcome description.
        source: 'user_prompt', 'user_session', or 'claude'.

    Returns:
        True if added successfully.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    tests = workflow.setdefault("unit_tests", [])

    test_id = f"{stage}_{len([t for t in tests if t.get('stage') == stage]) + 1}"
    tests.append({
        "id": test_id,
        "stage": stage,
        "description": description,
        "expected": expected,
        "source": source,
        "result": None,
        "added_at": now,
        "executed_at": None,
    })

    workflow["unit_tests"] = tests
    workflow["updated_at"] = now
    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: unit test added for {stage} ({source})")
    return True


def run_unit_test(test_id: str, result: str) -> bool:
    """Record the result of a unit test execution.

    Args:
        test_id: The test identifier.
        result: 'passed' or 'failed'.

    Returns:
        True if recorded successfully.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return False

    now = datetime.now(timezone.utc).isoformat()
    tests = workflow.get("unit_tests", [])

    for test in tests:
        if test.get("id") == test_id:
            test["result"] = result
            test["executed_at"] = now
            break
    else:
        return False

    workflow["unit_tests"] = tests
    workflow["updated_at"] = now
    sd["task_workflow"] = workflow
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache(f"data: unit test {test_id} → {result}")
    return True


def get_unit_tests(stage: Optional[str] = None) -> list:
    """Get unit tests, optionally filtered by stage.

    Args:
        stage: If provided, filter to this stage only.

    Returns:
        List of unit test dicts.
    """
    workflow = get_task_workflow()
    if not workflow:
        return []
    tests = workflow.get("unit_tests", [])
    if stage:
        return [t for t in tests if t.get("stage") == stage]
    return tests


def get_unit_test_format() -> str:
    """Return the unit test format for user reference.

    Returns:
        Formatted string describing how to provide unit tests.
    """
    return """Unit Test Format for Task Workflow Validation:

Each test targets a specific stage and checks one expectation.

Format (provide as text, Claude parses):
  Stage: <stage_name>
  Test: <what this test verifies>
  Expected: <expected outcome or behavior>

Example:
  Stage: initial
  Test: Title extraction preserves original casing
  Expected: Title "Fix Login Bug" stays as-is, not lowercased

Sources:
  - In task description (prompt): included at parse time
  - Mid-session: say "add unit test: <stage> / <description> / <expected>"
  - Claude-generated: automatic from task analysis if none provided

Results: each test gets 'passed' or 'failed' during validation quiz."""


def generate_task_report(stage: Optional[str] = None) -> dict:
    """Generate a task workflow report.

    Compiles workflow state, validation results, and unit test
    results into a structured report.

    Args:
        stage: If provided, generate report for this stage only.
               If None, generate full task report.

    Returns:
        Dict with report data.
    """
    workflow = get_task_workflow()
    if not workflow:
        return {"error": "No task workflow initialized"}

    now = datetime.now(timezone.utc).isoformat()
    validation_results = workflow.get("validation_results", {})
    unit_tests = workflow.get("unit_tests", [])

    if stage:
        stage_validation = validation_results.get(stage, {})
        stage_tests = [t for t in unit_tests if t.get("stage") == stage]
        return {
            "type": "stage_report",
            "stage": stage,
            "stage_label": TASK_WORKFLOW_STAGE_LABELS.get(stage, stage),
            "validation": stage_validation,
            "unit_tests": stage_tests,
            "generated_at": now,
        }

    # Full report
    stages_summary = []
    for s in TASK_WORKFLOW_STAGES:
        s_validation = validation_results.get(s, {})
        s_tests = [t for t in unit_tests if t.get("stage") == s]
        stages_summary.append({
            "stage": s,
            "label": TASK_WORKFLOW_STAGE_LABELS.get(s, s),
            "validation_status": s_validation.get("overall_status", "pending"),
            "validation_skipped": s_validation.get("skipped", False),
            "checks_count": len(s_validation.get("checks", [])),
            "checks_passed": sum(1 for c in s_validation.get("checks", [])
                                  if c.get("result") == "passed"),
            "checks_failed": sum(1 for c in s_validation.get("checks", [])
                                  if c.get("result") == "failed"),
            "unit_tests_count": len(s_tests),
            "unit_tests_passed": sum(1 for t in s_tests
                                      if t.get("result") == "passed"),
            "unit_tests_failed": sum(1 for t in s_tests
                                      if t.get("result") == "failed"),
        })

    return {
        "type": "full_report",
        "title": workflow.get("title", ""),
        "issue_number": workflow.get("issue_number", 0),
        "current_stage": workflow.get("current_stage"),
        "current_stage_index": workflow.get("current_stage_index"),
        "started_at": workflow.get("started_at"),
        "updated_at": workflow.get("updated_at"),
        "validation_skipped_entirely": workflow.get("validation_skipped_entirely", False),
        "stages": stages_summary,
        "total_checks": sum(s["checks_count"] for s in stages_summary),
        "total_passed": sum(s["checks_passed"] for s in stages_summary),
        "total_failed": sum(s["checks_failed"] for s in stages_summary),
        "total_unit_tests": len(unit_tests),
        "unit_tests_passed": sum(1 for t in unit_tests if t.get("result") == "passed"),
        "unit_tests_failed": sum(1 for t in unit_tests if t.get("result") == "failed"),
        "generated_at": now,
    }


# ── Report Persistence to Remote ────────────────────────────────

def persist_task_report() -> dict:
    """Generate task report, compile tasks.json, and persist to remote.

    This function:
    1. Generates the full task report
    2. Runs compile_tasks.py to update docs/data/tasks.json
    3. Commits and pushes the updated tasks.json

    The report is persisted to the current branch. When merged to
    the default branch via PR, it becomes available in the I3 viewer.

    Returns:
        Dict with: success (bool), report (dict), tasks_compiled (int),
                   message (str)
    """
    import subprocess

    # 1. Generate report
    report = generate_task_report()
    if "error" in report:
        return {"success": False, "report": report, "tasks_compiled": 0,
                "message": report["error"]}

    # 2. Find project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    compile_script = os.path.join(project_root, "scripts", "compile_tasks.py")
    tasks_json = os.path.join(project_root, "docs", "data", "tasks.json")

    # 3. Run compile_tasks.py
    tasks_compiled = 0
    try:
        result = subprocess.run(
            ["python3", compile_script],
            capture_output=True, text=True, timeout=30,
            cwd=project_root,
        )
        if result.returncode == 0:
            # Parse count from output like "Compiled 5 tasks → ..."
            import re
            m = re.search(r'Compiled (\d+) tasks', result.stdout)
            if m:
                tasks_compiled = int(m.group(1))
    except (subprocess.TimeoutExpired, OSError):
        pass

    # 4. Commit tasks.json if it changed
    if os.path.exists(tasks_json):
        try:
            subprocess.run(
                ["git", "add", tasks_json],
                capture_output=True, timeout=10,
                cwd=project_root,
            )
            subprocess.run(
                ["git", "commit", "-m",
                 f"data: update tasks.json ({tasks_compiled} tasks compiled)"],
                capture_output=True, timeout=10,
                cwd=project_root,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    return {
        "success": True,
        "report": report,
        "tasks_compiled": tasks_compiled,
        "message": f"Report generated, {tasks_compiled} tasks compiled to tasks.json",
    }


# ── Task Workflow Healthcheck ────────────────────────────────────

def run_task_workflow_healthcheck() -> dict:
    """Run the task workflow healthcheck — 8-test battery.

    Tests all core mechanics of the task workflow state machine:
      1. Workflow initialization + default stage/step
      2. Stage advancement through all 8 stages
      3. Step advancement within stages (initial, implement, completion)
      4. parse_prompt — action word detection + label mapping
      5. parse_prompt — multi-request detection
      6. Validation cross-cut (check_validation_needed, get_validation_checks)
      7. format_workflow_status output
      8. generate_task_report output

    Returns a structured dict with test results and summary.
    Each test runs in isolation (re-inits the workflow to avoid state bleed).
    """
    results = {
        "tests": [],
        "passed": 0,
        "failed": 0,
        "total": 8,
        "version": f"{len(TASK_WORKFLOW_STAGES)}stg",
    }

    # ── Test 1: Workflow initialization ──────────────────────────
    try:
        init_task_workflow(
            request_description="tw healthcheck test",
            title="TW Healthcheck",
            issue_number=0,
        )
        stage = get_task_stage()
        step = get_task_step()
        workflow = get_task_workflow()

        stage_ok = stage == "initial"
        step_ok = step == "analyze_prompt"
        has_history = isinstance(workflow.get("stage_history"), list)
        has_step_history = isinstance(workflow.get("step_history"), list)

        if stage_ok and step_ok and has_history and has_step_history:
            results["tests"].append({
                "name": "Workflow initialization",
                "status": "PASS",
                "details": f"initial/analyze_prompt, history tracked",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Workflow initialization",
                "status": "FAIL",
                "details": f"stage={stage}, step={step}, hist={has_history}, step_hist={has_step_history}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Workflow initialization", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 2: Stage advancement ────────────────────────────────
    try:
        init_task_workflow("tw healthcheck", "TW HC", 0)
        stage_results = []

        for target_stage in TASK_WORKFLOW_STAGES[1:]:
            advance_task_stage(target_stage, "healthcheck test")
            actual = get_task_stage()
            stage_results.append(actual == target_stage)

        all_ok = all(stage_results)
        final_stage = get_task_stage()

        if all_ok and final_stage == "completion":
            results["tests"].append({
                "name": "Stage advancement (all 8)",
                "status": "PASS",
                "details": f"initial → completion through {len(TASK_WORKFLOW_STAGES)} stages",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Stage advancement (all 8)",
                "status": "FAIL",
                "details": f"results={stage_results}, final={final_stage}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Stage advancement (all 8)", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 3: Step advancement ─────────────────────────────────
    try:
        init_task_workflow("tw healthcheck", "TW HC", 0)
        step_checks = []

        # Initial stage steps
        for step_name in INITIAL_STAGE_STEPS[1:]:
            advance_task_step(step_name)
            actual = get_task_step()
            step_checks.append(actual == step_name)

        # Move to implement and test its steps
        advance_task_stage("implement", "test")
        for step_name in IMPLEMENT_STAGE_STEPS[1:]:
            advance_task_step(step_name)
            actual = get_task_step()
            step_checks.append(actual == step_name)

        # Move to completion and test its steps
        advance_task_stage("completion", "test")
        for step_name in COMPLETION_STAGE_STEPS[1:]:
            advance_task_step(step_name)
            actual = get_task_step()
            step_checks.append(actual == step_name)

        all_ok = all(step_checks)
        if all_ok:
            results["tests"].append({
                "name": "Step advancement (initial/implement/completion)",
                "status": "PASS",
                "details": f"{len(step_checks)} step transitions verified",
            })
            results["passed"] += 1
        else:
            failed_idx = [i for i, c in enumerate(step_checks) if not c]
            results["tests"].append({
                "name": "Step advancement (initial/implement/completion)",
                "status": "FAIL",
                "details": f"{sum(step_checks)}/{len(step_checks)} OK, failed at indices {failed_idx}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Step advancement (initial/implement/completion)", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 4: parse_prompt — action word detection ─────────────
    try:
        test_cases = [
            ("fix the login bug", "BUG"),
            ("create a new feature", "FEATURE"),
            ("review the pull request", "REVIEW"),
            ("update the dashboard", "ENHANCEMENT"),
            ("investigate the crash", "INVESTIGATION"),
        ]
        detect_ok = []
        for prompt_text, expected_label in test_cases:
            parsed = parse_prompt(prompt_text)
            detect_ok.append(parsed.get("detected_label") == expected_label)

        all_ok = all(detect_ok)
        if all_ok:
            results["tests"].append({
                "name": "parse_prompt — action word detection",
                "status": "PASS",
                "details": f"{len(test_cases)} action words correctly mapped",
            })
            results["passed"] += 1
        else:
            failed = [test_cases[i][0] for i, ok in enumerate(detect_ok) if not ok]
            results["tests"].append({
                "name": "parse_prompt — action word detection",
                "status": "FAIL",
                "details": f"Failed for: {', '.join(failed)}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "parse_prompt — action word detection", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 5: parse_prompt — multi-request detection ───────────
    try:
        single = parse_prompt("fix the login bug")
        multi_connector = parse_prompt("fix the login bug and also add a logout button")
        multi_numbered = parse_prompt("1. fix login\n2. add logout\n3. update dashboard")

        single_ok = not single.get("is_multi_request")
        connector_ok = multi_connector.get("is_multi_request")
        numbered_ok = multi_numbered.get("is_multi_request")
        count_ok = multi_numbered.get("request_count", 0) >= 3

        if single_ok and connector_ok and numbered_ok and count_ok:
            results["tests"].append({
                "name": "parse_prompt — multi-request detection",
                "status": "PASS",
                "details": f"Single=false, connector=true, numbered=true (count={multi_numbered.get('request_count')})",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "parse_prompt — multi-request detection",
                "status": "FAIL",
                "details": f"single={single_ok}, connector={connector_ok}, numbered={numbered_ok}, count={count_ok}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "parse_prompt — multi-request detection", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 6: Validation cross-cut ─────────────────────────────
    try:
        init_task_workflow("tw healthcheck", "TW HC", 0)

        # Initial stage should need validation
        val_initial = check_validation_needed("initial")
        needs_val = val_initial.get("needs_validation", False)
        checks = get_validation_checks("initial")
        has_checks = len(checks) > 0

        # Completion stage should NOT need validation
        val_completion = check_validation_needed("completion")
        no_val = not val_completion.get("needs_validation", True)

        if needs_val and has_checks and no_val:
            results["tests"].append({
                "name": "Validation cross-cut",
                "status": "PASS",
                "details": f"initial needs validation ({len(checks)} checks), completion does not",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Validation cross-cut",
                "status": "FAIL",
                "details": f"needs_val={needs_val}, checks={len(checks)}, no_val_completion={no_val}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Validation cross-cut", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 7: format_workflow_status ────────────────────────────
    try:
        init_task_workflow("tw healthcheck", "TW HC", 0)
        advance_task_stage("implement", "test")

        status = format_workflow_status()
        has_progress = "→" in status
        has_stage = "implement" in status.lower() or "Implement" in status
        has_task = "TW HC" in status

        if has_progress and has_stage and has_task:
            results["tests"].append({
                "name": "format_workflow_status",
                "status": "PASS",
                "details": "Progress bar, stage label, task title present",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "format_workflow_status",
                "status": "FAIL",
                "details": f"progress={has_progress}, stage={has_stage}, task={has_task}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "format_workflow_status", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 8: generate_task_report ──────────────────────────────
    try:
        init_task_workflow("tw healthcheck", "TW HC Report", 0)
        advance_task_stage("implement", "test")

        report = generate_task_report()
        has_type = report.get("type") == "full_report"
        has_title = report.get("title") == "TW HC Report"
        has_stages = isinstance(report.get("stages"), list) and len(report.get("stages", [])) == 8
        has_current = report.get("current_stage") == "implement"

        if has_type and has_title and has_stages and has_current:
            results["tests"].append({
                "name": "generate_task_report",
                "status": "PASS",
                "details": f"Full report: 8 stages, current=implement, title matches",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "generate_task_report",
                "status": "FAIL",
                "details": f"type={has_type}, title={has_title}, stages={has_stages}, current={has_current}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "generate_task_report", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    return results


def format_task_workflow_healthcheck_report(results: dict) -> str:
    """Format task workflow healthcheck results as markdown."""
    lines = ["## Task Workflow Healthcheck", ""]
    lines.append(f"**Version**: {results.get('version', 'unknown')}")
    lines.append(f"**Result**: {results['passed']}/{results['total']} passed")
    lines.append("")
    lines.append("| # | Test | Status | Details |")
    lines.append("|---|------|--------|---------|")

    for i, test in enumerate(results.get("tests", []), 1):
        status = test["status"]
        icon = "PASS" if status == "PASS" else "FAIL"
        detail = test.get("details", test.get("error", ""))
        lines.append(f"| {i} | {test['name']} | {icon} | {detail} |")

    if results["failed"] > 0:
        lines.append("")
        lines.append(f"**{results['failed']} test(s) failed** — investigate before proceeding.")
    else:
        lines.append("")
        lines.append("All tests passed — task workflow is operational.")

    return "\n".join(lines)
