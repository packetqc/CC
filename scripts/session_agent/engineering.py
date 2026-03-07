"""Engineering cycle state machine — stage tracking and transitions.

The engineering cycle is the prime discipline — a universal state
machine that tracks where any piece of work is in its lifecycle.

Aligned with 8 industry frameworks: Classical SDLC (IEEE/ISO),
Agile/Scrum, DevOps CI/CD, ITIL v4, SAFe, GitHub Flow,
ISO/IEC 12207:2017, and the V-Model.

Stages (ordered, 0-indexed):
  0: analysis        — Requirements, stakeholder needs, investigation
  1: planning        — Sprint/iteration planning, task breakdown, scheduling
  2: design          — Architecture, system design, solution conception
  3: implementation  — Coding, building, integration of components
  4: testing         — Unit/integration/system tests
  5: validation      — User acceptance, stakeholder review
  6: review          — Code review, PR review, peer inspection
  7: deployment      — Release preparation, staging, production push
  8: operations      — Production runtime, monitoring, incident response
  9: improvement     — Retrospective, lessons learned, optimization

Cross-cutting concern (not a sequential stage):
  documentation      — Generated as byproduct at all stages (ISO 12207 model)

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import _find_runtime_cache, commit_cache, read_runtime_cache, update_session_data
from .helpers import _get_gh_helper


ENGINEERING_STAGES = (
    "analysis",
    "planning",
    "design",
    "implementation",
    "testing",
    "validation",
    "review",
    "deployment",
    "operations",
    "improvement",
)

# Documentation is a cross-cutting concern, not a sequential stage.
ENGINEERING_CROSS_CUTTING = ("documentation",)

ENGINEERING_STAGE_INDEX = {stage: i for i, stage in enumerate(ENGINEERING_STAGES)}


def init_engineering_cycle(request_description: str = "") -> bool:
    """Initialize the engineering cycle state machine in the session cache.

    Called at session start after issue creation. Sets the initial stage
    to 'analysis' and seeds the request_description as add-on #0.

    Args:
        request_description: The original session request (verbatim).

    Returns:
        True if initialization succeeded.
    """
    now = datetime.now(timezone.utc).isoformat()

    cycle = {
        "current_stage": "analysis",
        "current_stage_index": 0,
        "started_at": now,
        "updated_at": now,
        "stage_history": [
            {
                "stage": "analysis",
                "index": 0,
                "entered_at": now,
                "exited_at": None,
                "reason": "session_start",
            }
        ],
    }

    ok = update_session_data("engineering_cycle", cycle)
    if not ok:
        return False

    # Seed the request_description as add-on #0, tagged with 'analysis'
    if request_description:
        from .addons import _append_staged_addon
        _append_staged_addon(
            verbatim=request_description,
            synthesis="Original session request — analysis stage entry point.",
            stage="analysis",
            stage_index=0,
            addon_type="request_origin",
        )

    # Apply the 'analysis' label on the GitHub issue
    sync_engineering_stage_label("analysis")

    return True


def advance_engineering_stage(target_stage: str,
                              reason: str = "") -> bool:
    """Transition the engineering cycle to a new stage.

    Supports forward, backward, and re-enter transitions.

    Args:
        target_stage: The stage to transition to.
        reason: Why the transition is happening.

    Returns:
        True if transition succeeded, False if invalid stage.
    """
    if target_stage not in ENGINEERING_STAGE_INDEX:
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
    cycle = sd.get("engineering_cycle")

    if not cycle:
        now = datetime.now(timezone.utc).isoformat()
        cycle = {
            "current_stage": "analysis",
            "current_stage_index": 0,
            "started_at": now,
            "updated_at": now,
            "stage_history": [],
        }

    now = datetime.now(timezone.utc).isoformat()
    old_stage = cycle.get("current_stage", "analysis")

    # Close current stage in history
    if cycle.get("stage_history"):
        last_entry = cycle["stage_history"][-1]
        if last_entry.get("exited_at") is None:
            last_entry["exited_at"] = now

    target_index = ENGINEERING_STAGE_INDEX[target_stage]
    old_index = cycle.get("current_stage_index", 0)

    if target_index > old_index:
        direction = "forward"
    elif target_index < old_index:
        direction = "backward"
    else:
        direction = "re-enter"

    cycle["stage_history"].append({
        "stage": target_stage,
        "index": target_index,
        "entered_at": now,
        "exited_at": None,
        "reason": reason or f"{direction}: {old_stage} → {target_stage}",
        "direction": direction,
        "from_stage": old_stage,
    })

    cycle["current_stage"] = target_stage
    cycle["current_stage_index"] = target_index
    cycle["updated_at"] = now

    sd["engineering_cycle"] = cycle
    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache("data: advance engineering stage")

    # Sync label on GitHub issue
    sync_engineering_stage_label(target_stage, old_stage)

    return True


def get_engineering_stage() -> Optional[dict]:
    """Get the current engineering cycle state.

    Returns:
        Dict with cycle state, or None if not initialized.
    """
    cache = read_runtime_cache()
    if not cache:
        return None
    return cache.get("session_data", {}).get("engineering_cycle")


def get_engineering_stage_name() -> str:
    """Get just the current stage name.

    Returns:
        Stage name string, or "unknown" if not set.
    """
    cycle = get_engineering_stage()
    if not cycle:
        return "unknown"
    return cycle.get("current_stage", "unknown")


def get_engineering_stage_index() -> int:
    """Get the current stage's numerical index (0-9).

    Returns:
        Stage index, or -1 if not initialized.
    """
    cycle = get_engineering_stage()
    if not cycle:
        return -1
    return cycle.get("current_stage_index", -1)


def get_engineering_cycle_summary() -> dict:
    """Get a compact summary of the engineering cycle for display.

    Returns a dict with current_stage, stages_visited, total_transitions,
    addons_per_stage, and duration info.
    """
    cycle = get_engineering_stage()
    if not cycle:
        return {"initialized": False}

    # Unique stages visited
    stages_visited = []
    seen = set()
    for entry in cycle.get("stage_history", []):
        s = entry.get("stage")
        if s and s not in seen:
            stages_visited.append(s)
            seen.add(s)

    # Add-ons per stage
    from .addons import get_addons_by_stage
    all_addons = get_addons_by_stage()
    addons_per_stage = {}
    for a in all_addons:
        s = a.get("stage", "unknown")
        addons_per_stage[s] = addons_per_stage.get(s, 0) + 1

    return {
        "initialized": True,
        "current_stage": cycle.get("current_stage"),
        "current_stage_index": cycle.get("current_stage_index"),
        "stages_visited": stages_visited,
        "total_transitions": len(cycle.get("stage_history", [])),
        "addons_per_stage": addons_per_stage,
        "started_at": cycle.get("started_at"),
        "updated_at": cycle.get("updated_at"),
    }


def sync_engineering_stage_label(new_stage: str, old_stage: str = "") -> dict:
    """Sync the engineering cycle stage label on the session's GitHub issue.

    Args:
        new_stage: The new stage name to apply as a label.
        old_stage: The previous stage name to remove (optional).

    Returns:
        Dict with sync result, or error info if unavailable.
    """
    cache = read_runtime_cache()
    if not cache:
        return {"error": "No runtime cache available"}

    repo = cache.get("repo", "")
    issue_number = cache.get("issue_number")
    if not repo or not issue_number:
        return {"error": "No repo or issue_number in cache"}

    gh = _get_gh_helper()
    if not gh:
        return {"error": "No GH_TOKEN — label sync skipped (semi-automatic mode)"}

    try:
        result = gh.issue_engineering_stage_sync(repo, issue_number, new_stage, old_stage)
        return result
    except Exception as e:
        return {"error": f"Label sync failed: {e}"}
