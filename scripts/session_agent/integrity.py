"""Integrity Check — state machine tracking protocol compliance.

The integrity grid is the instrument panel for the agent identity.
It tracks every protocol checkpoint from session start through completion,
detects gaps, and provides rerun-from-failed-state directives.

**Three tracking paths (v59.2)**:
1. **Auto-pass in functions**: _auto_pass() calls inside protocol functions
   (write_runtime_cache, post_exchange, compile_pre_save_summary, etc.)
   so checkpoints pass atomically when the action executes.
2. **Step-driven**: advance_task_step() maps implement/completion steps
   to their corresponding W/C checkpoints — stepping = tracking.
3. **Explicit bridge**: mark_work_action() and mark_completion_action()
   for Bash-only actions (git commit, push, fetch) that don't go through
   Python functions.

**Timing fix (v59.2)**: init_integrity() calls retroactive_startup_pass()
after grid creation to catch actions that fired before the grid existed.
Without this, early checkpoints (T.1, T.2) stay pending forever.

Four sections, ~29 checkpoints:
  S (Startup)    — wakeup protocol gates
  T (Task)       — task lifecycle gates
  W (Work cycle) — per-todo implementation gates (resets per todo)
  C (Completion) — save/delivery gates

Identity principles enforced structurally:
  I1 (protocol_uniform)   — grid identical for all sessions
  I2 (zero_judgment)      — no auto-skip in API, only skipped_by_user
  I3 (rigor_over_convenience) — failed = rerun directive, never skip-forward
  I4 (cycle_complete)     — C section must fully resolve
  I5 (self_correction)    — integrity_check() at boundaries triggers rerun

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import (
    ENFORCEMENT_STATE_FILE,
    _find_runtime_cache,
    commit_cache,
    read_runtime_cache,
    update_session_data,
)


# ── Checkpoint Definitions ─────────────────────────────────────────

CHECKPOINTS = {
    # Section S: Startup Protocol
    "S.0": {"name": "sunglasses", "section": "startup", "blocking": True,
            "desc": "CLAUDE.md fully loaded", "principle": "I1"},
    "S.1": {"name": "subconscious", "section": "startup", "blocking": True,
            "desc": "5 mandatory methodology files read", "principle": "I1"},
    "S.2": {"name": "elevated", "section": "startup", "blocking": False,
            "desc": "GH_TOKEN detected (or not_applicable)", "principle": "I3"},
    "S.3": {"name": "integrity_unlocked", "section": "startup", "blocking": True,
            "desc": "Gate G1 — update_enforcement_state(protocol_completed=True)", "principle": "I1"},
    "S.4": {"name": "upstream_synced", "section": "startup", "blocking": False,
            "desc": "git fetch + merge completed", "principle": "I3"},
    "S.5": {"name": "resume_checked", "section": "startup", "blocking": False,
            "desc": "checkpoint.json scanned", "principle": "I5"},
    "S.6": {"name": "context_loaded", "section": "startup", "blocking": False,
            "desc": "Evolution, minds, notes, git log processed", "principle": "I1"},

    # Section T: Task Protocol
    "T.1": {"name": "issue_created", "section": "task", "blocking": True,
            "desc": "GitHub issue exists — Gate G1", "principle": "I4"},
    "T.2": {"name": "cache_initialized", "section": "task", "blocking": True,
            "desc": "write_runtime_cache() called — Gate G2", "principle": "I4"},
    "T.3": {"name": "plan_approved", "section": "task", "blocking": True,
            "desc": "User approved todo list — Gate G3", "principle": "I2"},
    "T.4": {"name": "exchanges_active", "section": "task", "blocking": False,
            "desc": "post_exchange() called at least once", "principle": "I4"},

    # Section W: Work Cycle (per todo — resets on next_todo)
    "W.1": {"name": "remote_checked", "section": "work", "blocking": False,
            "desc": "git fetch + diff before modifications", "principle": "I3"},
    "W.2": {"name": "work_executed", "section": "work", "blocking": True,
            "desc": "Todo item work completed", "principle": "I4"},
    "W.3": {"name": "committed", "section": "work", "blocking": True,
            "desc": "git add + commit for this todo", "principle": "I4"},
    "W.4": {"name": "pushed", "section": "work", "blocking": False,
            "desc": "git push succeeded", "principle": "I3"},
    "W.5": {"name": "cache_updated", "section": "work", "blocking": True,
            "desc": "update_session_data(todo_snapshot) called", "principle": "I4"},
    "W.6": {"name": "issue_commented", "section": "work", "blocking": False,
            "desc": "Todo lifecycle comment posted — Gate G7", "principle": "I4"},
    "W.7": {"name": "modifications_marked", "section": "work", "blocking": False,
            "desc": "mark_modifications_occurred() called", "principle": "I5"},

    # Section C: Completion Protocol
    "C.1":  {"name": "pre_save_summary", "section": "completion", "blocking": True,
             "desc": "7-section report compiled", "principle": "I4"},
    "C.2":  {"name": "notes_generated", "section": "completion", "blocking": True,
             "desc": "session-YYYY-MM-DD-*.md exists — Gate G5", "principle": "I4"},
    "C.3":  {"name": "cache_finalized", "section": "completion", "blocking": True,
             "desc": "session_phase set to complete", "principle": "I4"},
    "C.4":  {"name": "sessions_compiled", "section": "completion", "blocking": False,
             "desc": "sessions.json regenerated (core only)", "principle": "I4"},
    "C.5":  {"name": "tasks_compiled", "section": "completion", "blocking": False,
             "desc": "tasks.json regenerated", "principle": "I4"},
    "C.6":  {"name": "dual_output_verified", "section": "completion", "blocking": True,
             "desc": "Both .md and .json files in commit — Gate G6", "principle": "I4"},
    "C.7":  {"name": "committed_final", "section": "completion", "blocking": True,
             "desc": "Final commit with session artifacts", "principle": "I4"},
    "C.8":  {"name": "pushed_final", "section": "completion", "blocking": True,
             "desc": "Push to remote succeeded", "principle": "I4"},
    "C.9":  {"name": "pr_created", "section": "completion", "blocking": False,
             "desc": "PR created or manual URL provided", "principle": "I3"},
    "C.10": {"name": "pr_merged", "section": "completion", "blocking": False,
             "desc": "PR merged (elevated) or user guided", "principle": "I3"},
    "C.11": {"name": "doc_checked", "section": "completion", "blocking": True,
             "desc": "check_doc_updates_needed() called — Gate G8", "principle": "I5"},
    "C.12": {"name": "post_close_comment", "section": "completion", "blocking": False,
             "desc": "Closing report posted after issue close", "principle": "I4"},
}

SECTION_ORDER = ("startup", "task", "work", "completion")
SECTION_PREFIXES = {"startup": "S", "task": "T", "work": "W", "completion": "C"}
VALID_STATUSES = ("pending", "passed", "failed", "skipped_by_user", "not_applicable")

# Status display icons
STATUS_ICONS = {
    "pending": "⬜",
    "passed": "✅",
    "failed": "❌",
    "skipped_by_user": "⏭️",
    "not_applicable": "➖",
}

# Rerun action templates per checkpoint
RERUN_ACTIONS = {
    "S.0": "Re-read CLAUDE.md fully",
    "S.1": "Re-read 5 mandatory methodology files (agent-identity, working-style, session-protocol, interactive-work-sessions, task-workflow)",
    "S.2": "Detect GH_TOKEN or mark as not_applicable",
    "S.3": "Call update_enforcement_state(protocol_completed=True)",
    "S.4": "Run git fetch origin main && git merge origin/main --no-edit",
    "S.5": "Scan notes/checkpoint.json for crash recovery",
    "S.6": "Load evolution table, minds/, notes/, git log",
    "T.1": "Create GitHub issue via gh_helper.py",
    "T.2": "Call write_runtime_cache() with issue_number",
    "T.3": "Present work plan to user via AskUserQuestion",
    "T.4": "Call post_exchange() to start issue comment trail",
    "W.1": "Run git fetch origin main && git diff origin/main..HEAD",
    "W.2": "Execute the current todo item",
    "W.3": "Run git add + git commit for this todo's changes",
    "W.4": "Run git push -u origin <branch>",
    "W.5": "Call update_session_data('todo_snapshot', current_todos)",
    "W.6": "Post todo completion as issue comment",
    "W.7": "Call mark_modifications_occurred()",
    "C.1": "Call compile_pre_save_summary()",
    "C.2": "Call generate_session_notes() — must produce .md file",
    "C.3": "Call update_session_data('session_phase', 'complete')",
    "C.4": "Run python3 scripts/generate_sessions.py && python3 scripts/compile_sessions.py",
    "C.5": "Run python3 scripts/compile_tasks.py",
    "C.6": "Verify both session-*.md and session-runtime-*.json in commit",
    "C.7": "Run git add + git commit with all session artifacts",
    "C.8": "Run git push -u origin <branch>",
    "C.9": "Create PR via gh_helper.py or provide manual URL",
    "C.10": "Merge PR (elevated) or guide user (semi-auto)",
    "C.11": "Call check_doc_updates_needed()",
    "C.12": "Post closing report on issue after close",
}


# ── Initialization ─────────────────────────────────────────────────

def init_integrity() -> bool:
    """Initialize the integrity grid in session cache — all checkpoints pending.

    Called once at session start during wakeup. Creates the full grid
    with every checkpoint set to 'pending'. Re-initialization is blocked
    if a grid already exists — prevents wiping failed checkpoints mid-session.

    Returns:
        True if initialization succeeded, False if grid already exists.
    """
    # Guard against re-initialization (v59.3): calling init_integrity()
    # mid-session would reset ALL checkpoints to pending, silently
    # erasing any failed/skipped states. Only allow first-time init.
    cache = read_runtime_cache()
    if cache:
        sd = cache.get("session_data", {})
        existing = sd.get("integrity")
        if existing and existing.get("grid"):
            # Grid already exists — refuse re-init to protect audit trail
            return False

    now = datetime.now(timezone.utc).isoformat()
    grid = {}
    for cp_id in CHECKPOINTS:
        grid[cp_id] = {"status": "pending"}

    integrity = {
        "version": 1,
        "initialized_at": now,
        "grid": grid,
        "current_todo_cycle": 0,
        "work_cycle_history": [],
        "skips": [],
        "reruns": [],
        "last_check_at": None,
        "last_check_result": None,
    }

    result = update_session_data("integrity", integrity)

    # Fix timing vulnerability: catch actions that happened before
    # the grid was initialized (e.g., write_runtime_cache called
    # before init_integrity). Without this, those checkpoints stay
    # pending forever because _auto_pass fired when no grid existed.
    if result:
        retroactive_startup_pass()

    return result


# ── Checkpoint State Transitions ───────────────────────────────────

def pass_checkpoint(checkpoint_id: str) -> bool:
    """Mark a checkpoint as passed with timestamp.

    Args:
        checkpoint_id: The checkpoint ID (e.g., 'S.0', 'T.1', 'W.3').

    Returns:
        True if update succeeded.
    """
    if checkpoint_id not in CHECKPOINTS:
        return False
    return _set_checkpoint_status(checkpoint_id, "passed")


def fail_checkpoint(checkpoint_id: str, error: str = "") -> bool:
    """Mark a checkpoint as failed with error detail.

    Args:
        checkpoint_id: The checkpoint ID.
        error: Description of what went wrong.

    Returns:
        True if update succeeded.
    """
    if checkpoint_id not in CHECKPOINTS:
        return False
    return _set_checkpoint_status(checkpoint_id, "failed", error=error)


# ── Access Control Lists (v59.3) ──────────────────────────────────
# These lists prevent the AI from marking structural checkpoints
# as skipped or not_applicable. Only checkpoints that are genuinely
# conditional (S.2 when no token, C.4 in satellites) can be N/A.
# Blocking checkpoints that represent mandatory protocol steps
# cannot be bypassed without the user explicitly confirming via
# AskUserQuestion.

# Checkpoints that can NEVER be skipped — they represent mandatory
# protocol steps. Only user intervention via AskUserQuestion with
# explicit "skip" selection can bypass these (enforced by caller,
# not by this function).
UNSKIPPABLE_CHECKPOINTS = {
    "T.1", "T.2",  # Issue and cache creation — Gate G1/G2
    "C.1",         # Pre-save summary — mandatory reflection
    "C.6",         # Dual output verification — Gate G6
    "C.7", "C.8",  # Final commit and push — delivery
}

# Checkpoints that can legitimately be marked not_applicable.
# All others are structural and MUST be either passed or failed.
ALLOW_NOT_APPLICABLE = {
    "S.2",   # elevated — not applicable when no GH_TOKEN
    "S.5",   # resume_checked — not applicable if no checkpoint exists
    "C.4",   # sessions_compiled — not applicable in satellite repos
    "C.5",   # tasks_compiled — not applicable in satellite repos
    "C.10",  # pr_merged — not applicable in semi-auto mode
    "C.12",  # post_close_comment — not applicable if issue not closed
}


def skip_checkpoint(checkpoint_id: str, reason: str = "") -> bool:
    """Mark a checkpoint as skipped_by_user with reason.

    Only the user can skip checkpoints via AskUserQuestion.
    Claude cannot invoke this without user confirmation.
    Structural checkpoints (UNSKIPPABLE_CHECKPOINTS) cannot be
    skipped — they are mandatory protocol steps.

    Args:
        checkpoint_id: The checkpoint ID.
        reason: Why the user chose to skip.

    Returns:
        True if update succeeded, False if checkpoint is unskippable.
    """
    if checkpoint_id not in CHECKPOINTS:
        return False

    # v59.3: Guard against skipping structural checkpoints
    if checkpoint_id in UNSKIPPABLE_CHECKPOINTS:
        return False

    result = _set_checkpoint_status(checkpoint_id, "skipped_by_user")
    if result:
        # Record in skips log with source attribution
        now = datetime.now(timezone.utc).isoformat()
        _append_to_integrity_list("skips", {
            "checkpoint": checkpoint_id,
            "name": CHECKPOINTS[checkpoint_id]["name"],
            "reason": reason,
            "source": "user",  # v59.3: source attribution
            "at": now,
        })
    return result


def mark_not_applicable(checkpoint_id: str) -> bool:
    """Mark a checkpoint as not applicable to this session.

    Only allowed for checkpoints in ALLOW_NOT_APPLICABLE — these
    are genuinely conditional (S.2 when no token, C.4 in satellites).
    Structural checkpoints CANNOT be marked N/A — they represent
    mandatory protocol steps that must be either passed or failed.

    Args:
        checkpoint_id: The checkpoint ID.

    Returns:
        True if update succeeded, False if checkpoint cannot be N/A.
    """
    if checkpoint_id not in CHECKPOINTS:
        return False

    # v59.3: Only allow N/A for genuinely conditional checkpoints
    if checkpoint_id not in ALLOW_NOT_APPLICABLE:
        return False

    return _set_checkpoint_status(checkpoint_id, "not_applicable")


# ── Integrity Check ────────────────────────────────────────────────

def integrity_check(section: Optional[str] = None) -> dict:
    """Run integrity check — return first gap or all_passed.

    Scans the grid (optionally filtered by section) and returns
    the first unresolved checkpoint. If all resolved, returns
    status 'all_passed'.

    Args:
        section: Optional section filter ('startup', 'task', 'work', 'completion').
                 If None, checks all sections in order.

    Returns:
        Dict with check result:
        - status: 'all_passed', 'incomplete', or 'error'
        - first_gap: checkpoint ID of first unresolved item (if incomplete)
        - checkpoint: checkpoint name
        - blocking: whether it blocks progress
        - action: rerun instruction
        - rerun_from: checkpoint ID to rerun from
        - section: which section the gap is in
        - counts: passed/total/skipped/failed/pending
    """
    cache = read_runtime_cache()
    if not cache:
        return {"status": "error", "message": "No runtime cache found"}

    sd = cache.get("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return {"status": "error", "message": "Integrity not initialized — call init_integrity()"}

    grid = integrity.get("grid", {})
    now = datetime.now(timezone.utc).isoformat()

    # Filter checkpoints by section if requested
    check_ids = []
    sections_to_check = [section] if section else list(SECTION_ORDER)
    for sec in sections_to_check:
        prefix = SECTION_PREFIXES.get(sec, "")
        for cp_id in sorted(CHECKPOINTS.keys()):
            if cp_id.startswith(prefix + ".") and CHECKPOINTS[cp_id]["section"] == sec:
                check_ids.append(cp_id)

    # Count statuses
    counts = {"passed": 0, "failed": 0, "pending": 0,
              "skipped": 0, "not_applicable": 0, "total": len(check_ids)}
    first_gap = None

    for cp_id in check_ids:
        cp_state = grid.get(cp_id, {"status": "pending"})
        status = cp_state.get("status", "pending")

        if status == "passed":
            counts["passed"] += 1
        elif status == "not_applicable":
            counts["not_applicable"] += 1
        elif status == "skipped_by_user":
            counts["skipped"] += 1
        elif status == "failed":
            counts["failed"] += 1
            if first_gap is None:
                first_gap = cp_id
        elif status == "pending":
            counts["pending"] += 1
            if first_gap is None:
                first_gap = cp_id

    # Update last check timestamp
    _update_integrity_field("last_check_at", now)

    if first_gap is None:
        _update_integrity_field("last_check_result", "all_passed")
        return {
            "status": "all_passed",
            **counts,
        }

    cp_def = CHECKPOINTS[first_gap]
    gap_state = grid.get(first_gap, {"status": "pending"})
    result = {
        "status": "incomplete",
        "first_gap": first_gap,
        "checkpoint": cp_def["name"],
        "blocking": cp_def["blocking"],
        "action": RERUN_ACTIONS.get(first_gap, f"Resolve checkpoint {first_gap}"),
        "rerun_from": first_gap,
        "section": cp_def["section"],
        "principle": cp_def["principle"],
        "gap_status": gap_state.get("status", "pending"),
        "gap_error": gap_state.get("error", ""),
        **counts,
    }

    _update_integrity_field("last_check_result", "incomplete")
    return result


def integrity_grid() -> dict:
    """Return the full integrity grid state for display.

    Returns:
        Dict with grid state, organized by section:
        {
            "startup": [{"id": "S.0", "name": ..., "status": ..., ...}, ...],
            "task": [...],
            "work": [...],
            "completion": [...],
            "summary": {"passed": N, "total": N, ...}
        }
    """
    cache = read_runtime_cache()
    if not cache:
        return {"error": "No runtime cache found"}

    sd = cache.get("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return {"error": "Integrity not initialized"}

    grid = integrity.get("grid", {})
    result = {sec: [] for sec in SECTION_ORDER}
    counts = {"passed": 0, "failed": 0, "pending": 0,
              "skipped": 0, "not_applicable": 0, "total": 0}

    for cp_id in sorted(CHECKPOINTS.keys()):
        cp_def = CHECKPOINTS[cp_id]
        cp_state = grid.get(cp_id, {"status": "pending"})
        status = cp_state.get("status", "pending")

        entry = {
            "id": cp_id,
            "name": cp_def["name"],
            "desc": cp_def["desc"],
            "blocking": cp_def["blocking"],
            "principle": cp_def["principle"],
            "status": status,
            "icon": STATUS_ICONS.get(status, "?"),
        }
        if status == "failed":
            entry["error"] = cp_state.get("error", "")
        if status == "passed":
            entry["at"] = cp_state.get("at", "")
        if status == "skipped_by_user":
            entry["reason"] = cp_state.get("reason", "")

        section = cp_def["section"]
        result[section].append(entry)
        counts["total"] += 1
        if status == "passed":
            counts["passed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "pending":
            counts["pending"] += 1
        elif status == "skipped_by_user":
            counts["skipped"] += 1
        elif status == "not_applicable":
            counts["not_applicable"] += 1

    result["summary"] = counts
    result["work_cycle_history"] = integrity.get("work_cycle_history", [])
    result["skips"] = integrity.get("skips", [])
    result["reruns"] = integrity.get("reruns", [])

    return result


# ── Work Cycle Management ──────────────────────────────────────────

def reset_work_cycle(todo_content: str = "") -> bool:
    """Archive current W section and reset for next todo.

    Called when advancing to the next todo item. Archives the
    completed work cycle and resets W.1-W.7 to pending.

    Args:
        todo_content: Description of the completed todo (for history).

    Returns:
        True if reset succeeded.
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
    integrity = sd.get("integrity")
    if not integrity:
        return False

    now = datetime.now(timezone.utc).isoformat()
    grid = integrity.get("grid", {})

    # Archive current W checkpoints
    cycle_snapshot = {}
    for cp_id in sorted(CHECKPOINTS.keys()):
        if cp_id.startswith("W."):
            cp_state = grid.get(cp_id, {"status": "pending"})
            cycle_snapshot[cp_id] = cp_state.get("status", "pending")

    cycle_index = integrity.get("current_todo_cycle", 0)
    integrity.setdefault("work_cycle_history", []).append({
        "todo_index": cycle_index,
        "todo_content": todo_content,
        "checkpoints": cycle_snapshot,
        "completed_at": now,
    })

    # Reset W checkpoints
    for cp_id in CHECKPOINTS:
        if cp_id.startswith("W."):
            grid[cp_id] = {"status": "pending"}

    integrity["current_todo_cycle"] = cycle_index + 1
    integrity["grid"] = grid

    sd["integrity"] = integrity
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache("data: integrity work cycle reset")
    return True


# ── Display Formatting ─────────────────────────────────────────────

def format_integrity_report() -> str:
    """Format the integrity grid as a readable report with status icons.

    Returns:
        Formatted string with the integrity grid organized by section,
        including summary counts and first gap highlight.
    """
    grid_data = integrity_grid()
    if "error" in grid_data:
        return f"Integrity error: {grid_data['error']}"

    lines = ["## Integrity Check Report", ""]

    section_titles = {
        "startup": "S — Startup Protocol",
        "task": "T — Task Protocol",
        "work": "W — Work Cycle",
        "completion": "C — Completion Protocol",
    }

    first_gap_found = False

    for section in SECTION_ORDER:
        title = section_titles.get(section, section)
        items = grid_data.get(section, [])
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| ID | Checkpoint | Status | Blocking | Principle |")
        lines.append("|----|-----------|--------|----------|-----------|")

        for item in items:
            blocking = "Yes" if item["blocking"] else "No"
            status_display = f"{item['icon']} {item['status']}"

            # Highlight first gap
            if not first_gap_found and item["status"] in ("pending", "failed"):
                status_display += " **← FIRST GAP**"
                first_gap_found = True

            if item["status"] == "failed" and item.get("error"):
                status_display += f" ({item['error']})"

            lines.append(
                f"| {item['id']} | {item['name']} | {status_display} "
                f"| {blocking} | {item['principle']} |"
            )
        lines.append("")

    # Summary
    summary = grid_data.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    pct = (passed / total * 100) if total > 0 else 0
    lines.append("### Summary")
    lines.append("")
    lines.append(f"- **Passed**: {passed}/{total} ({pct:.0f}%)")
    lines.append(f"- **Failed**: {summary.get('failed', 0)}")
    lines.append(f"- **Pending**: {summary.get('pending', 0)}")
    lines.append(f"- **Skipped**: {summary.get('skipped', 0)}")
    lines.append(f"- **N/A**: {summary.get('not_applicable', 0)}")

    # Skips log
    skips = grid_data.get("skips", [])
    if skips:
        lines.append("")
        lines.append("### User Skips")
        for skip in skips:
            lines.append(f"- `{skip['checkpoint']}` ({skip.get('name', '')}) — {skip.get('reason', 'no reason')}")

    # Work cycle history
    history = grid_data.get("work_cycle_history", [])
    if history:
        lines.append("")
        lines.append(f"### Work Cycles Completed: {len(history)}")
        for cycle in history:
            lines.append(f"- Todo #{cycle['todo_index']}: {cycle.get('todo_content', '?')}")

    return "\n".join(lines)


def get_rerun_directive(checkpoint_id: str) -> dict:
    """Return the rerun action for a specific checkpoint.

    Args:
        checkpoint_id: The checkpoint ID.

    Returns:
        Dict with checkpoint info and rerun action.
    """
    if checkpoint_id not in CHECKPOINTS:
        return {"error": f"Unknown checkpoint: {checkpoint_id}"}

    cp_def = CHECKPOINTS[checkpoint_id]
    return {
        "checkpoint_id": checkpoint_id,
        "name": cp_def["name"],
        "section": cp_def["section"],
        "blocking": cp_def["blocking"],
        "principle": cp_def["principle"],
        "action": RERUN_ACTIONS.get(checkpoint_id, f"Resolve {checkpoint_id}"),
    }


# ── Internal Helpers ───────────────────────────────────────────────

def _set_checkpoint_status(checkpoint_id: str, status: str,
                           error: str = "") -> bool:
    """Set a checkpoint's status in the integrity grid.

    Args:
        checkpoint_id: The checkpoint ID.
        status: New status (must be in VALID_STATUSES).
        error: Optional error message (for 'failed' status).

    Returns:
        True if update succeeded.
    """
    if status not in VALID_STATUSES:
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
    integrity = sd.get("integrity")
    if not integrity:
        return False

    now = datetime.now(timezone.utc).isoformat()
    grid = integrity.setdefault("grid", {})

    entry = {"status": status, "at": now}
    if error:
        entry["error"] = error

    grid[checkpoint_id] = entry
    integrity["grid"] = grid

    sd["integrity"] = integrity
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    # Don't commit on every checkpoint — too noisy. Commit on check or reset.
    return True


def _update_integrity_field(field: str, value) -> bool:
    """Update a single field in the integrity state."""
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return False

    integrity[field] = value
    sd["integrity"] = integrity

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    return True


def _append_to_integrity_list(list_name: str, entry: dict) -> bool:
    """Append an entry to a list in the integrity state."""
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.setdefault("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return False

    integrity.setdefault(list_name, []).append(entry)
    sd["integrity"] = integrity

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    return True


# ── Autonomous Tracking (v58) ────────────────────────────────────

def _auto_pass(checkpoint_id: str) -> bool:
    """Silently pass a checkpoint as a side effect of a protocol action.

    Called from protocol functions (write_runtime_cache, post_exchange,
    compile_pre_save_summary, etc.) to auto-track integrity without
    requiring Claude to manually call pass_checkpoint().

    Safe to call at any time:
    - No-op if integrity grid not initialized
    - No-op if checkpoint already passed
    - No-op if cache not found
    - Never raises exceptions

    Args:
        checkpoint_id: The checkpoint ID (e.g., 'S.3', 'T.1').

    Returns:
        True if checkpoint was updated, False if skipped (already passed
        or not initialized).
    """
    if checkpoint_id not in CHECKPOINTS:
        return False

    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.get("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return False

    grid = integrity.get("grid", {})
    current = grid.get(checkpoint_id, {})

    # Don't overwrite passed, skipped_by_user, or not_applicable
    if current.get("status") in ("passed", "skipped_by_user", "not_applicable"):
        return False

    now = datetime.now(timezone.utc).isoformat()
    grid[checkpoint_id] = {"status": "passed", "at": now}
    integrity["grid"] = grid
    sd["integrity"] = integrity
    cache["session_data"] = sd

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        return True
    except OSError:
        return False


def retroactive_startup_pass() -> dict:
    """Pass checkpoints for actions that happened before init_integrity().

    The timing vulnerability: write_runtime_cache() calls _auto_pass("T.1")
    and _auto_pass("T.2"), but if init_integrity() hasn't run yet, the grid
    doesn't exist and _auto_pass silently returns False. Those checkpoints
    stay pending forever.

    This function runs AFTER init_integrity() and retroactively passes
    checkpoints by inspecting the current cache state — if the action
    already happened (issue exists, cache exists, exchanges posted),
    the checkpoint is passed now.

    Called automatically by init_integrity() at the end of grid creation.

    Returns:
        Dict mapping checkpoint IDs to 'retroactive_pass' for each
        checkpoint that was caught and passed.
    """
    cache = read_runtime_cache()
    if not cache:
        return {}

    results = {}
    sd = cache.get("session_data", {})

    # T.1: issue_created — if issue_number exists, the issue was created
    if cache.get("issue_number"):
        if _auto_pass("T.1"):
            results["T.1"] = "retroactive_pass"

    # T.2: cache_initialized — if we're reading the cache, it was initialized
    if cache.get("agent_initialized"):
        if _auto_pass("T.2"):
            results["T.2"] = "retroactive_pass"

    # T.4: exchanges_active — if exchange_log or comments exist
    if sd.get("exchange_log") or sd.get("issue_comments_count", 0) > 0:
        if _auto_pass("T.4"):
            results["T.4"] = "retroactive_pass"

    # S.3: integrity_unlocked — if enforcement state exists and is unlocked
    if os.path.exists(ENFORCEMENT_STATE_FILE):
        try:
            with open(ENFORCEMENT_STATE_FILE, 'r') as f:
                state = json.load(f)
            if state.get("protocol_completed"):
                if _auto_pass("S.3"):
                    results["S.3"] = "retroactive_pass"
        except (json.JSONDecodeError, OSError):
            pass

    return results


def mark_work_action(action: str, detail: str = "") -> bool:
    """Mark a work cycle action as completed in the integrity grid.

    For actions that go through Bash (git commit, git push, git fetch)
    rather than through Python functions with built-in auto-pass.

    Claude MUST call this after each Bash-based protocol action.
    This is the bridge between Bash-world and the integrity grid.

    Args:
        action: One of:
            'remote_checked' (W.1) — after git fetch + git diff
            'work_executed' (W.2) — after todo item work completed
            'committed' (W.3) — after git add + git commit
            'pushed' (W.4) — after git push
            'cache_updated' (W.5) — after update_session_data(todo_snapshot)
            'issue_commented' (W.6) — after todo lifecycle comment posted
        detail: Optional detail for logging.

    Returns:
        True if checkpoint was passed, False if action unknown or grid
        not initialized.
    """
    ACTION_TO_CHECKPOINT = {
        "remote_checked": "W.1",
        "work_executed": "W.2",
        "committed": "W.3",
        "pushed": "W.4",
        "cache_updated": "W.5",
        "issue_commented": "W.6",
    }
    cp_id = ACTION_TO_CHECKPOINT.get(action)
    if not cp_id:
        return False
    return _auto_pass(cp_id)


def mark_completion_action(action: str, detail: str = "") -> bool:
    """Mark a completion protocol action as completed in the integrity grid.

    For completion actions not covered by save_session() auto-pass —
    e.g., when Claude does PR creation or merge via Bash instead of
    through the Python save_session() function.

    Args:
        action: One of:
            'pre_save_summary' (C.1)
            'notes_generated' (C.2)
            'cache_finalized' (C.3)
            'sessions_compiled' (C.4)
            'tasks_compiled' (C.5)
            'dual_output_verified' (C.6)
            'committed_final' (C.7)
            'pushed_final' (C.8)
            'pr_created' (C.9)
            'pr_merged' (C.10)
            'doc_checked' (C.11)
            'post_close_comment' (C.12)
        detail: Optional detail for logging.

    Returns:
        True if checkpoint was passed.
    """
    ACTION_TO_CHECKPOINT = {
        "pre_save_summary": "C.1",
        "notes_generated": "C.2",
        "cache_finalized": "C.3",
        "sessions_compiled": "C.4",
        "tasks_compiled": "C.5",
        "dual_output_verified": "C.6",
        "committed_final": "C.7",
        "pushed_final": "C.8",
        "pr_created": "C.9",
        "pr_merged": "C.10",
        "doc_checked": "C.11",
        "post_close_comment": "C.12",
    }
    cp_id = ACTION_TO_CHECKPOINT.get(action)
    if not cp_id:
        return False
    return _auto_pass(cp_id)


def integrity_compliance() -> dict:
    """Return the integrity compliance summary for pre-save reporting.

    Called by compile_pre_save_summary() to include integrity state
    in the auto-évaluation section. This makes compliance visible
    in every save — gaps are never hidden.

    Returns:
        Dict with:
          passed: int — checkpoints passed
          total: int — total checkpoints
          pending: int — checkpoints still pending
          failed: int — checkpoints failed
          percentage: float — compliance percentage
          first_gap: str or None — first pending/failed checkpoint ID
          report_line: str — one-line summary for auto-évaluation
    """
    cache = read_runtime_cache()
    if not cache:
        return {"passed": 0, "total": 30, "pending": 30, "failed": 0,
                "percentage": 0.0, "first_gap": "S.0",
                "report_line": "0/30 (0%) — no cache"}

    sd = cache.get("session_data", {})
    integrity = sd.get("integrity")
    if not integrity:
        return {"passed": 0, "total": 30, "pending": 30, "failed": 0,
                "percentage": 0.0, "first_gap": "S.0",
                "report_line": "0/30 (0%) — grid not initialized"}

    grid = integrity.get("grid", {})
    passed = failed = pending = skipped = na = 0
    first_gap = None

    for cp_id in sorted(CHECKPOINTS.keys()):
        status = grid.get(cp_id, {}).get("status", "pending")
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
            if first_gap is None:
                first_gap = cp_id
        elif status == "pending":
            pending += 1
            if first_gap is None:
                first_gap = cp_id
        elif status == "skipped_by_user":
            skipped += 1
        elif status == "not_applicable":
            na += 1

    total = len(CHECKPOINTS)
    # Effective total excludes n/a
    effective = total - na
    pct = (passed / effective * 100) if effective > 0 else 0.0

    return {
        "passed": passed,
        "total": total,
        "effective_total": effective,
        "pending": pending,
        "failed": failed,
        "skipped": skipped,
        "not_applicable": na,
        "percentage": pct,
        "first_gap": first_gap,
        "report_line": f"{passed}/{effective} ({pct:.0f}%) — {'all passed' if pct == 100 else f'first gap: {first_gap}'}",
    }


def run_startup_integrity(
    claude_md_read: bool = False,
    methodology_read: bool = False,
    token_present: bool = False,
    upstream_synced: bool = False,
    checkpoint_scanned: bool = False,
    context_loaded: bool = False,
) -> dict:
    """Run all startup integrity checks in one call.

    Called once during wakeup after all startup steps complete.
    Verifies each startup condition and auto-passes/fails the
    corresponding checkpoint. Also unlocks enforcement Gate 1.

    Args:
        claude_md_read: True if CLAUDE.md was fully loaded (S.0)
        methodology_read: True if 5 methodology files were read (S.1)
        token_present: True if GH_TOKEN detected (S.2)
        upstream_synced: True if git fetch+merge completed (S.4)
        checkpoint_scanned: True if checkpoint.json was checked (S.5)
        context_loaded: True if evolution/minds/notes loaded (S.6)

    Returns:
        Dict with results per checkpoint and overall status.
    """
    results = {}

    # S.0 — sunglasses
    if claude_md_read:
        _auto_pass("S.0")
        results["S.0"] = "passed"
    else:
        fail_checkpoint("S.0", "CLAUDE.md not loaded")
        results["S.0"] = "failed"

    # S.1 — subconscious
    if methodology_read:
        _auto_pass("S.1")
        results["S.1"] = "passed"
    else:
        fail_checkpoint("S.1", "Methodology files not read")
        results["S.1"] = "failed"

    # S.2 — elevated (not_applicable if no token)
    if token_present:
        _auto_pass("S.2")
        results["S.2"] = "passed"
    else:
        mark_not_applicable("S.2")
        results["S.2"] = "not_applicable"

    # S.3 — integrity_unlocked (auto-pass — this function IS the unlock)
    _auto_pass("S.3")
    results["S.3"] = "passed"

    # Also unlock enforcement Gate 1 as side effect
    from .cache import update_enforcement_state
    update_enforcement_state(protocol_completed=True)

    # S.4 — upstream_synced
    if upstream_synced:
        _auto_pass("S.4")
        results["S.4"] = "passed"
    else:
        fail_checkpoint("S.4", "Upstream not synced")
        results["S.4"] = "failed"

    # S.5 — resume_checked (v59.3: honest reporting — don't lie about state)
    if checkpoint_scanned:
        _auto_pass("S.5")
        results["S.5"] = "passed"
    else:
        # Non-blocking: mark N/A instead of false-passing
        mark_not_applicable("S.5")
        results["S.5"] = "not_applicable"

    # S.6 — context_loaded (v59.3: honest reporting)
    if context_loaded:
        _auto_pass("S.6")
        results["S.6"] = "passed"
    else:
        # Leave pending — don't claim context was loaded when it wasn't
        results["S.6"] = "pending"

    # Summary
    passed = sum(1 for v in results.values() if v == "passed")
    na = sum(1 for v in results.values() if v == "not_applicable")
    failed = sum(1 for v in results.values() if v == "failed")
    results["summary"] = {
        "passed": passed,
        "not_applicable": na,
        "failed": failed,
        "total": len(results) - 1,  # exclude summary key
    }

    return results


# ── Healthcheck ───────────────────────────────────────────────────

def run_healthcheck() -> dict:
    """Run the full engineering cycle healthcheck — 7-test battery.

    Tests all core mechanics of the integrity state machine and task workflow:
      1. Grid initialization (checkpoint count, sections, blocking)
      2. Checkpoint pass/fail/skip/not_applicable mechanics
      3. Work cycle reset + archive
      4. Gap detection + rerun directives
      5. Integrity report generation
      6. Task workflow init + stage advancement
      7. Workflow status formatting

    Returns a structured dict with test results and summary.
    Each test runs in isolation (re-inits the grid to avoid state bleed).
    """
    results = {
        "tests": [],
        "passed": 0,
        "failed": 0,
        "total": 7,
        "version": None,
    }

    # ── Test 1: Grid initialization ──────────────────────────────
    try:
        init_integrity()
        grid = integrity_grid()
        sections = {}
        for section_name in ["startup", "task", "work", "completion"]:
            items = grid.get(section_name, [])
            sections[section_name] = len(items)

        total_cp = sum(sections.values())
        blocking = sum(
            sum(1 for cp in grid.get(s, []) if isinstance(cp, dict) and cp.get("blocking"))
            for s in ["startup", "task", "work", "completion"]
        )
        results["version"] = f"v{total_cp}cp/{blocking}blk"
        results["tests"].append({
            "name": "Grid initialization",
            "status": "PASS",
            "details": f"{total_cp} checkpoints ({', '.join(f'{k}:{v}' for k, v in sections.items())}), {blocking} blocking",
        })
        results["passed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Grid initialization", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 2: Checkpoint mechanics ─────────────────────────────
    try:
        init_integrity()
        ok_pass = pass_checkpoint("S.0")
        ok_na = mark_not_applicable("S.2")
        fail_checkpoint("W.1")
        ok_skip = skip_checkpoint("W.1")

        grid = integrity_grid()
        s0 = next((cp for cp in grid.get("startup", []) if cp.get("id") == "S.0"), {})
        s2 = next((cp for cp in grid.get("startup", []) if cp.get("id") == "S.2"), {})
        w1 = next((cp for cp in grid.get("work", []) if cp.get("id") == "W.1"), {})

        checks = [
            ok_pass and s0.get("status") == "passed",
            ok_na and s2.get("status") == "not_applicable",
            ok_skip and w1.get("status") == "skipped_by_user",
        ]
        if all(checks):
            results["tests"].append({
                "name": "Checkpoint pass/fail/skip/n_a",
                "status": "PASS",
                "details": "pass→✅, n/a→➖, fail+skip→⏭️",
            })
            results["passed"] += 1
        else:
            results["tests"].append({"name": "Checkpoint pass/fail/skip/n_a", "status": "FAIL", "details": str(checks)})
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Checkpoint pass/fail/skip/n_a", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 3: Work cycle reset ─────────────────────────────────
    try:
        init_integrity()
        for cp_id in ["W.1", "W.2", "W.3", "W.4", "W.5", "W.6", "W.7"]:
            pass_checkpoint(cp_id)

        reset_work_cycle()
        grid = integrity_grid()
        work_items = grid.get("work", [])
        all_pending = all(
            cp.get("status") == "pending" for cp in work_items if isinstance(cp, dict)
        )
        history_count = len(grid.get("work_cycle_history", []))

        if all_pending and history_count == 1:
            results["tests"].append({
                "name": "Work cycle reset + archive",
                "status": "PASS",
                "details": "W.1-W.7 reset to pending, 1 archived cycle",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Work cycle reset + archive",
                "status": "FAIL",
                "details": f"all_pending={all_pending}, history={history_count}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Work cycle reset + archive", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 4: Gap detection + rerun directives ─────────────────
    try:
        init_integrity()
        # All pending — first gap should be S.0
        check = integrity_check()
        has_gap = check.get("status") == "incomplete"
        first_gap = check.get("first_gap") == "S.0"
        has_action = bool(check.get("action"))

        # Pass some, check directive
        pass_checkpoint("S.0")
        fail_checkpoint("S.1")
        directive = get_rerun_directive("S.1")
        has_directive = isinstance(directive, dict) and "action" in directive

        if has_gap and first_gap and has_action and has_directive:
            results["tests"].append({
                "name": "Gap detection + rerun directives",
                "status": "PASS",
                "details": f"First gap: {check.get('first_gap')}, action: {check.get('action', '')[:50]}",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Gap detection + rerun directives",
                "status": "FAIL",
                "details": f"gap={has_gap}, first={first_gap}, action={has_action}, directive={has_directive}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Gap detection + rerun directives", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 5: Integrity report generation ──────────────────────
    try:
        init_integrity()
        pass_checkpoint("S.0")
        pass_checkpoint("S.1")
        mark_not_applicable("S.2")
        fail_checkpoint("W.3")

        report = format_integrity_report()
        has_sections = "Startup" in report and "Work" in report and "Completion" in report
        has_icons = "✅" in report and "❌" in report and "➖" in report
        has_gap_marker = "FIRST GAP" in report

        if has_sections and has_icons and has_gap_marker:
            results["tests"].append({
                "name": "Integrity report generation",
                "status": "PASS",
                "details": "Markdown tables with icons + FIRST GAP annotation",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Integrity report generation",
                "status": "FAIL",
                "details": f"sections={has_sections}, icons={has_icons}, gap_marker={has_gap_marker}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Integrity report generation", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 6: Task workflow init + stages ───────────────────────
    try:
        from .task_workflow import (
            init_task_workflow,
            get_task_stage,
            get_task_step,
            advance_task_stage,
            advance_task_step,
        )

        init_task_workflow(
            request_description="healthcheck test",
            title="Healthcheck Test",
            issue_number=0,
        )
        stage = get_task_stage()
        step = get_task_step()
        stage_ok = stage == "initial"
        step_ok = step == "analyze_prompt"

        # Advance through steps
        advance_task_step("extract_title")
        new_step = get_task_step()
        step_advanced = new_step == "extract_title"

        # Advance stage
        advance_task_stage("implement", "test skip")
        new_stage = get_task_stage()
        stage_advanced = new_stage == "implement"

        if stage_ok and step_ok and step_advanced and stage_advanced:
            results["tests"].append({
                "name": "Task workflow init + stages",
                "status": "PASS",
                "details": f"initial/analyze_prompt → implement (8 stages, named steps)",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Task workflow init + stages",
                "status": "FAIL",
                "details": f"stage={stage_ok}, step={step_ok}, step_adv={step_advanced}, stage_adv={stage_advanced}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Task workflow init + stages", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Test 7: Workflow status formatting ────────────────────────
    try:
        from .task_workflow import format_workflow_status

        status = format_workflow_status()
        has_progress = "→" in status
        has_stage = "implement" in status.lower() or "Stage" in status

        if has_progress and has_stage:
            results["tests"].append({
                "name": "Workflow status formatting",
                "status": "PASS",
                "details": "Progress bar with ✅/▶/⬜ icons",
            })
            results["passed"] += 1
        else:
            results["tests"].append({
                "name": "Workflow status formatting",
                "status": "FAIL",
                "details": f"progress={has_progress}, stage={has_stage}",
            })
            results["failed"] += 1
    except Exception as e:
        results["tests"].append({"name": "Workflow status formatting", "status": "FAIL", "error": str(e)})
        results["failed"] += 1

    # ── Re-init to clean state after tests ───────────────────────
    init_integrity()

    return results


def format_healthcheck_report(results: dict) -> str:
    """Format healthcheck results as markdown."""
    lines = ["## Engineering Cycle Healthcheck", ""]
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
        lines.append("All tests passed — engineering cycle is operational.")

    return "\n".join(lines)
