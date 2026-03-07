"""Context Budget — proactive compaction management for heavy operations.

Problem: Heavy operations (parallel agents, deep audits, large code generation)
consume massive context. When compaction hits mid-operation, results are lost.
The session spends tokens re-doing work that was already complete.

Solution: Before launching heavy operations, estimate context pressure and
either (a) checkpoint state + proceed if room exists, or (b) recommend
compaction-first so the heavy work runs with maximum available context.

The context budget is heuristic — we can't know exact token counts. But we
CAN track proxy signals: tool calls made, agent launches, cache size, elapsed
messages. Together these give a reliable "pressure" estimate.

Integration points:
  - Skill `/resilient-run` invokes pre_flight_check() before heavy work
  - startup-checklist.sh calls recover_interrupted() on boot
  - Any code can call checkpoint_operation() before risky work

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import (
    _find_runtime_cache,
    read_runtime_cache,
    update_session_data,
    commit_cache,
)


# ── Pressure thresholds (heuristic) ─────────────────────────────
# These are calibrated from observed compaction patterns:
# - A typical session compacts around 80-120 tool calls
# - Agent results are 5-20x heavier than regular tool calls
# - Each agent launch ≈ 10-15 equivalent tool calls in context

TOOL_CALL_WEIGHT = 1.0        # Base weight per tool call
AGENT_LAUNCH_WEIGHT = 12.0    # Each agent ≈ 12 tool calls of context
AGENT_RESULT_WEIGHT = 15.0    # Agent result (when received) ≈ 15 tool calls
FILE_READ_WEIGHT = 2.0        # Large file reads consume more
BASH_WEIGHT = 1.5             # Bash output varies but tends large

# Pressure zones (percentage of estimated budget)
ZONE_GREEN = 40    # 0-40%: plenty of room
ZONE_YELLOW = 65   # 40-65%: caution, plan accordingly
ZONE_ORANGE = 80   # 65-80%: compress before heavy work
ZONE_RED = 90      # 80-90%: compress immediately
                   # 90-100%: compaction imminent/happening

# Estimated total budget (in weighted tool call equivalents)
# Based on observation: ~120 tool calls fills context to compaction
ESTIMATED_BUDGET = 120.0

# Operation cost estimates (weighted tool call equivalents)
OPERATION_COSTS = {
    "single_agent": 15.0,
    "parallel_agents_2": 30.0,
    "parallel_agents_3": 45.0,
    "parallel_agents_4": 60.0,
    "deep_audit": 50.0,
    "heavy_code_gen": 25.0,
    "save_protocol": 20.0,
    "healthcheck": 15.0,
}


# ── Checkpoint file ──────────────────────────────────────────────
HEAVY_OP_CHECKPOINT = "/tmp/.claude-heavy-operation.json"


def estimate_context_pressure() -> dict:
    """Estimate current context pressure from session cache signals.

    Returns:
        Dict with:
          pressure_pct: float (0-100) — estimated context fill percentage
          zone: str — "green", "yellow", "orange", "red"
          budget_remaining: float — estimated remaining capacity (weighted units)
          signals: dict — individual signal values used
          recommendation: str — human-readable recommendation
    """
    cache = read_runtime_cache()
    if not cache:
        # No cache = fresh session = green zone
        return {
            "pressure_pct": 5.0,
            "zone": "green",
            "budget_remaining": ESTIMATED_BUDGET * 0.95,
            "signals": {},
            "recommendation": "Fresh session — full budget available.",
        }

    sd = cache.get("session_data", {})

    # Count signals from cache
    tool_calls = sd.get("tool_call_count", 0)
    agent_launches = sd.get("agent_launch_count", 0)
    agent_results = sd.get("agent_result_count", 0)
    file_reads = sd.get("file_read_count", 0)
    bash_calls = sd.get("bash_call_count", 0)
    comment_count = sd.get("issue_comments_count", 0)

    # Time markers give a rough sense of session length
    time_markers = sd.get("time_markers", [])
    marker_count = len(time_markers)

    # Todo snapshot size (large snapshots = more context used for state tracking)
    todo_snapshot = sd.get("todo_snapshot", [])
    todo_count = len(todo_snapshot)

    # Calculate weighted pressure
    weighted_used = (
        tool_calls * TOOL_CALL_WEIGHT
        + agent_launches * AGENT_LAUNCH_WEIGHT
        + agent_results * AGENT_RESULT_WEIGHT
        + file_reads * FILE_READ_WEIGHT
        + bash_calls * BASH_WEIGHT
        + comment_count * 1.0
        + marker_count * 0.5
        + todo_count * 0.5
    )

    pressure_pct = min(100.0, (weighted_used / ESTIMATED_BUDGET) * 100.0)
    budget_remaining = max(0.0, ESTIMATED_BUDGET - weighted_used)

    # Determine zone
    if pressure_pct < ZONE_GREEN:
        zone = "green"
    elif pressure_pct < ZONE_YELLOW:
        zone = "yellow"
    elif pressure_pct < ZONE_ORANGE:
        zone = "orange"
    elif pressure_pct < ZONE_RED:
        zone = "red"
    else:
        zone = "critical"

    # Recommendation
    recommendations = {
        "green": "Plenty of context budget. Heavy operations are safe.",
        "yellow": "Moderate usage. Single agents safe, parallel agents should checkpoint first.",
        "orange": "High pressure. Checkpoint state before any heavy operation. Consider compacting.",
        "red": "Near limit. Save state NOW. Compaction likely imminent.",
        "critical": "At limit. Compaction expected. Do not launch new agents.",
    }

    signals = {
        "tool_calls": tool_calls,
        "agent_launches": agent_launches,
        "agent_results": agent_results,
        "file_reads": file_reads,
        "bash_calls": bash_calls,
        "comment_count": comment_count,
        "time_markers": marker_count,
        "todos": todo_count,
        "weighted_used": round(weighted_used, 1),
    }

    return {
        "pressure_pct": round(pressure_pct, 1),
        "zone": zone,
        "budget_remaining": round(budget_remaining, 1),
        "signals": signals,
        "recommendation": recommendations[zone],
    }


def pre_flight_check(operation_type: str, agent_count: int = 1) -> dict:
    """Pre-flight check before launching a heavy operation.

    Call this BEFORE launching agents or heavy work. Returns a go/no-go
    decision with specific recommendations.

    Args:
        operation_type: Key from OPERATION_COSTS or description string.
        agent_count: Number of parallel agents (if applicable).

    Returns:
        Dict with:
          decision: "go" | "checkpoint_first" | "compress_first" | "abort"
          pressure_before: dict — current pressure estimate
          operation_cost: float — estimated cost of the operation
          pressure_after: float — estimated pressure after operation
          instructions: str — what to do based on the decision
    """
    pressure = estimate_context_pressure()
    current_pct = pressure["pressure_pct"]
    budget = pressure["budget_remaining"]

    # Estimate operation cost
    if operation_type in OPERATION_COSTS:
        cost = OPERATION_COSTS[operation_type]
    elif agent_count > 1:
        key = f"parallel_agents_{min(agent_count, 4)}"
        cost = OPERATION_COSTS.get(key, agent_count * 15.0)
    else:
        cost = 15.0  # Default: assume moderate

    estimated_after = min(100.0, current_pct + (cost / ESTIMATED_BUDGET) * 100.0)

    # Decision logic
    if estimated_after < ZONE_GREEN:
        decision = "go"
        instructions = "Safe to proceed. No checkpoint needed."
    elif estimated_after < ZONE_YELLOW:
        decision = "go"
        instructions = "Safe to proceed. Results will fit in context."
    elif estimated_after < ZONE_ORANGE:
        decision = "checkpoint_first"
        instructions = (
            "Checkpoint state before proceeding. The operation may trigger "
            "compaction. Save current progress to cache, then launch. "
            "On compaction recovery, read cache to resume."
        )
    elif estimated_after < ZONE_RED:
        decision = "compress_first"
        instructions = (
            "HIGH RISK: Operation will likely cause compaction mid-execution. "
            "Recommended: (1) Save ALL current state to cache, "
            "(2) Commit and push current work, (3) Summarize context for "
            "compaction survival, (4) THEN launch the heavy operation. "
            "This ensures maximum budget for the operation results."
        )
    else:
        decision = "abort"
        instructions = (
            "ABORT: Not enough context budget. The operation would trigger "
            "compaction and lose its own results. Options: (1) Save and start "
            "a new session, (2) Break the operation into smaller pieces, "
            "(3) Commit current work first, then run in the next turn."
        )

    return {
        "decision": decision,
        "pressure_before": pressure,
        "operation_cost": round(cost, 1),
        "pressure_after_pct": round(estimated_after, 1),
        "fits_in_budget": cost <= budget,
        "instructions": instructions,
    }


def checkpoint_operation(
    operation_id: str,
    operation_type: str,
    planned_work: list,
    current_state: dict = None,
) -> bool:
    """Checkpoint state before a heavy operation.

    Saves everything needed to resume if compaction interrupts the work.
    The checkpoint is read by recover_interrupted() on next boot or
    after compaction recovery.

    Args:
        operation_id: Unique identifier (e.g., "doctor-strange-audit")
        operation_type: Type of operation (from OPERATION_COSTS keys)
        planned_work: List of work items to execute
        current_state: Optional dict with current progress/context

    Returns:
        True if checkpoint saved successfully.
    """
    now = datetime.now(timezone.utc).isoformat()

    checkpoint = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "planned_work": planned_work,
        "completed_work": [],
        "current_state": current_state or {},
        "created_at": now,
        "updated_at": now,
        "status": "checkpointed",
        "pressure_at_checkpoint": estimate_context_pressure(),
    }

    try:
        with open(HEAVY_OP_CHECKPOINT, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        return True
    except OSError:
        return False


def update_operation_progress(
    completed_item: str,
    result_summary: str = "",
) -> bool:
    """Update the heavy operation checkpoint with progress.

    Call this after each sub-task completes (e.g., after each agent returns).
    If compaction hits, the next recovery knows what's done vs pending.

    Args:
        completed_item: Description of what just completed.
        result_summary: Brief summary of the result (NOT the full result —
                        just enough to avoid re-doing the work).

    Returns:
        True if updated successfully.
    """
    if not os.path.exists(HEAVY_OP_CHECKPOINT):
        return False

    try:
        with open(HEAVY_OP_CHECKPOINT, 'r') as f:
            checkpoint = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    now = datetime.now(timezone.utc).isoformat()
    checkpoint["completed_work"].append({
        "item": completed_item,
        "result_summary": result_summary,
        "completed_at": now,
    })
    checkpoint["updated_at"] = now
    checkpoint["status"] = "in_progress"

    # Remove from planned_work if it matches
    planned = checkpoint.get("planned_work", [])
    checkpoint["planned_work"] = [
        w for w in planned
        if (w if isinstance(w, str) else w.get("description", "")) != completed_item
    ]

    try:
        with open(HEAVY_OP_CHECKPOINT, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        return True
    except OSError:
        return False


def complete_operation() -> bool:
    """Mark the heavy operation as complete and clean up checkpoint.

    Returns:
        True if cleaned up successfully.
    """
    if os.path.exists(HEAVY_OP_CHECKPOINT):
        try:
            os.remove(HEAVY_OP_CHECKPOINT)
            return True
        except OSError:
            return False
    return True


def recover_interrupted() -> Optional[dict]:
    """Check for interrupted heavy operations and return recovery state.

    Called by the startup hook or on compaction recovery. If a checkpoint
    exists and status is not "complete", the operation was interrupted.

    Returns:
        Dict with checkpoint data if interrupted operation found, None otherwise.
        Includes remaining_work list for resumption.
    """
    if not os.path.exists(HEAVY_OP_CHECKPOINT):
        return None

    try:
        with open(HEAVY_OP_CHECKPOINT, 'r') as f:
            checkpoint = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if checkpoint.get("status") == "complete":
        complete_operation()  # Clean up
        return None

    # Calculate remaining work
    completed_items = {
        w.get("item", "") for w in checkpoint.get("completed_work", [])
    }
    planned = checkpoint.get("planned_work", [])
    remaining = [
        w for w in planned
        if (w if isinstance(w, str) else w.get("description", "")) not in completed_items
    ]

    return {
        "operation_id": checkpoint.get("operation_id", "unknown"),
        "operation_type": checkpoint.get("operation_type", "unknown"),
        "status": checkpoint.get("status", "unknown"),
        "created_at": checkpoint.get("created_at"),
        "completed_count": len(checkpoint.get("completed_work", [])),
        "remaining_count": len(remaining),
        "remaining_work": remaining,
        "completed_work": checkpoint.get("completed_work", []),
        "current_state": checkpoint.get("current_state", {}),
        "pressure_at_checkpoint": checkpoint.get("pressure_at_checkpoint", {}),
    }


def partition_work(items: list, max_per_phase: int = 2) -> list:
    """Split a list of work items into compaction-safe phases.

    Each phase should complete within the context budget. Between phases,
    Claude commits results and can survive compaction.

    Args:
        items: List of work items (strings or dicts).
        max_per_phase: Maximum items per phase (default: 2 agents).

    Returns:
        List of phases, each a list of items.
    """
    if not items:
        return []

    phases = []
    for i in range(0, len(items), max_per_phase):
        phases.append(items[i:i + max_per_phase])

    return phases


def increment_signal(signal_name: str, count: int = 1) -> bool:
    """Increment a context pressure signal in the session cache.

    Called by tool wrappers to track context consumption. Signals:
      tool_call_count, agent_launch_count, agent_result_count,
      file_read_count, bash_call_count

    Args:
        signal_name: The signal key to increment.
        count: Amount to increment by.

    Returns:
        True if incremented successfully.
    """
    valid_signals = {
        "tool_call_count", "agent_launch_count", "agent_result_count",
        "file_read_count", "bash_call_count",
    }
    if signal_name not in valid_signals:
        return False

    cache = read_runtime_cache()
    if not cache:
        return False

    sd = cache.get("session_data", {})
    current = sd.get(signal_name, 0)
    return update_session_data(signal_name, current + count)


def format_pressure_report(pressure: dict = None) -> str:
    """Format the context pressure estimate as a compact status line.

    Args:
        pressure: Result from estimate_context_pressure(). Auto-computed if None.

    Returns:
        Formatted string like: "Context: 45% [YELLOW] — 66.0 units remaining"
    """
    if pressure is None:
        pressure = estimate_context_pressure()

    zone = pressure["zone"].upper()
    pct = pressure["pressure_pct"]
    remaining = pressure["budget_remaining"]

    # Zone indicator
    zone_bars = {
        "GREEN": "[====------]",
        "YELLOW": "[======----]",
        "ORANGE": "[========--]",
        "RED": "[=========-]",
        "CRITICAL": "[==========]",
    }
    bar = zone_bars.get(zone, "[??????????]")

    return (
        f"Context: {pct:.0f}% {bar} {zone} — "
        f"{remaining:.0f} units remaining"
    )


def format_pre_flight_report(check: dict) -> str:
    """Format the pre-flight check result as a status block.

    Args:
        check: Result from pre_flight_check().

    Returns:
        Formatted markdown string.
    """
    decision = check["decision"].upper()
    cost = check["operation_cost"]
    before = check["pressure_before"]["pressure_pct"]
    after = check["pressure_after_pct"]
    fits = check["fits_in_budget"]

    lines = [
        f"## Pre-Flight Check — {decision}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Current pressure | {before:.0f}% |",
        f"| Operation cost | {cost:.0f} units |",
        f"| Estimated after | {after:.0f}% |",
        f"| Fits in budget | {'Yes' if fits else 'No'} |",
        "",
        f"**Decision**: {decision}",
        f"**Action**: {check['instructions']}",
    ]

    return "\n".join(lines)
