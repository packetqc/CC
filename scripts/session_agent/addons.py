"""Add-on pipeline — append, read, stage-tagged, and ticket sync.

Add-ons are supplementary instructions/updates/clarifications from
the user, stored in the session cache with engineering stage context.

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import _find_runtime_cache, commit_cache, read_runtime_cache, update_session_data
from .request_types import detect_request_type
from .helpers import _get_gh_helper


def append_request_addon(verbatim: str, synthesis: str) -> bool:
    """Append a user add-on comment and Claude's synthesis to the session cache.

    Legacy API — delegates to the staged pipeline so every add-on gets:
    stage tagging, request-type detection, and ticket sync.

    Args:
        verbatim: The user's exact words, unmodified.
        synthesis: Claude's interpretation of what the user meant/wants.

    Returns:
        True if append succeeded, False otherwise.
    """
    from .engineering import get_engineering_stage_name, get_engineering_stage_index

    stage = get_engineering_stage_name()
    stage_index = get_engineering_stage_index()

    return _append_staged_addon(
        verbatim=verbatim,
        synthesis=synthesis,
        stage=stage,
        stage_index=stage_index if stage_index >= 0 else -1,
        addon_type="addon",
    )


def read_request_addons() -> list:
    """Read all add-on entries from the session cache.

    Returns:
        List of paired add-on dicts with verbatim, synthesis, stage context.
    """
    cache = read_runtime_cache()
    if not cache:
        return []

    session_data = cache.get("session_data", {})
    addons = session_data.get("request_addon", [])
    syntheses = session_data.get("request_addon_synthesis", [])

    synth_by_index = {s["index"]: s for s in syntheses}

    result = []
    for addon in addons:
        idx = addon["index"]
        synth = synth_by_index.get(idx, {})
        result.append({
            "index": idx,
            "timestamp": addon.get("timestamp", ""),
            "verbatim": addon.get("verbatim", ""),
            "synthesis": synth.get("synthesis", ""),
            "stage": addon.get("stage", "unknown"),
            "stage_index": addon.get("stage_index", -1),
            "addon_type": addon.get("addon_type", "addon"),
            "request_type": addon.get("request_type"),
        })

    return result


def append_request_addon_staged(verbatim: str, synthesis: str) -> bool:
    """Append a user add-on tagged with the current engineering stage.

    Stage-aware replacement for append_request_addon().

    Args:
        verbatim: User's exact words, unmodified.
        synthesis: Claude's interpretation of the add-on.

    Returns:
        True if append succeeded.
    """
    from .engineering import get_engineering_stage_name, get_engineering_stage_index

    stage = get_engineering_stage_name()
    stage_index = get_engineering_stage_index()

    return _append_staged_addon(
        verbatim=verbatim,
        synthesis=synthesis,
        stage=stage,
        stage_index=stage_index if stage_index >= 0 else -1,
        addon_type="addon",
    )


def get_addons_by_stage(stage: str = None) -> list:
    """Get add-ons filtered by engineering stage.

    Args:
        stage: Filter to this stage only. None returns all add-ons.

    Returns:
        List of add-on dicts with stage context.
    """
    cache = read_runtime_cache()
    if not cache:
        return []

    sd = cache.get("session_data", {})
    addons = sd.get("request_addon", [])
    syntheses = sd.get("request_addon_synthesis", [])

    synth_by_index = {s["index"]: s for s in syntheses}

    result = []
    for addon in addons:
        idx = addon["index"]
        synth = synth_by_index.get(idx, {})

        entry = {
            "index": idx,
            "timestamp": addon.get("timestamp", ""),
            "verbatim": addon.get("verbatim", ""),
            "synthesis": synth.get("synthesis", ""),
            "stage": addon.get("stage", "unknown"),
            "stage_index": addon.get("stage_index", -1),
            "addon_type": addon.get("addon_type", "addon"),
            "request_type": addon.get("request_type"),
        }

        if stage is None or entry["stage"] == stage:
            result.append(entry)

    return result


def _append_staged_addon(verbatim: str, synthesis: str,
                         stage: str, stage_index: int,
                         addon_type: str = "addon") -> bool:
    """Internal: append an add-on with engineering stage tagging.

    Args:
        verbatim: User's exact words.
        synthesis: Claude's interpretation.
        stage: Engineering stage at time of add-on.
        stage_index: Numerical index of the stage.
        addon_type: "request_origin", "addon", or "stage_transition".

    Returns:
        True if append succeeded.
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

    if "request_addon" not in sd:
        sd["request_addon"] = []
    if "request_addon_synthesis" not in sd:
        sd["request_addon_synthesis"] = []

    # For request_origin, always index 0
    if addon_type == "request_origin":
        next_index = 0
    else:
        existing_indices = [a.get("index", 0) for a in sd["request_addon"]]
        next_index = (max(existing_indices) + 1) if existing_indices else 1

    now = datetime.now(timezone.utc).isoformat()

    sd["request_addon"].append({
        "index": next_index,
        "timestamp": now,
        "verbatim": verbatim,
        "stage": stage,
        "stage_index": stage_index,
        "addon_type": addon_type,
    })

    sd["request_addon_synthesis"].append({
        "index": next_index,
        "timestamp": now,
        "synthesis": synthesis,
        "stage": stage,
        "stage_index": stage_index,
        "addon_type": addon_type,
    })

    # Detect request type from content
    request_type = detect_request_type(verbatim) or detect_request_type(synthesis)

    # Store the request_type in the add-on entry
    sd["request_addon"][-1]["request_type"] = request_type
    sd["request_addon_synthesis"][-1]["request_type"] = request_type

    cache["updated"] = now

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except OSError:
        return False

    commit_cache("data: append request addon")

    # Sync the add-on to the GitHub ticket (non-blocking)
    sync_addon_to_ticket(
        addon_index=next_index,
        verbatim=verbatim,
        synthesis=synthesis,
        stage=stage,
        stage_index=stage_index,
        addon_type=addon_type,
        request_type=request_type,
    )

    return True


def sync_addon_to_ticket(addon_index: int, verbatim: str, synthesis: str,
                          stage: str, stage_index: int,
                          addon_type: str = "addon",
                          request_type: str = None) -> dict:
    """Post an add-on to the GitHub ticket as a comment and apply labels.

    Args:
        addon_index: Add-on index number.
        verbatim: User's exact words.
        synthesis: Claude's interpretation.
        stage: Engineering stage at time of add-on.
        stage_index: Numerical index of the stage.
        addon_type: "request_origin", "addon", "stage_transition".
        request_type: Detected request type label (optional).

    Returns:
        Dict with 'comment_id' and 'labels_applied' on success.
    """
    cache = read_runtime_cache()
    if not cache:
        return {"error": "No runtime cache"}

    repo = cache.get("repo", "")
    issue_number = cache.get("issue_number")
    if not repo or not issue_number:
        return {"error": "No repo or issue_number in cache"}

    gh = _get_gh_helper()
    if not gh:
        return {"error": "No GH_TOKEN — ticket sync skipped"}

    result = {"comment_id": None, "labels_applied": []}

    try:
        type_emoji = {
            "request_origin": "\U0001f4cc",
            "addon": "\U0001f4ce",
            "stage_transition": "\U0001f504",
        }.get(addon_type, "\U0001f4ce")

        body = f"## {type_emoji} Add-on #{addon_index} — `{stage}` ({stage_index})\n\n"

        if request_type:
            body += f"**Request type**: `{request_type}`\n\n"

        body += f"> {verbatim}\n\n"
        body += f"**Synthesis**: {synthesis}\n"

        comment_result = gh.issue_comment_post(repo, issue_number, body)
        if comment_result.get("posted"):
            result["comment_id"] = comment_result["id"]

            sd = cache.get("session_data", {})
            comment_ids = sd.get("comment_ids", {})
            comment_ids[f"addon_{addon_index}"] = comment_result["id"]
            update_session_data("comment_ids", comment_ids)

        if request_type:
            gh._request("POST", f"/repos/{repo}/labels", {
                "name": request_type,
                "color": "d4c5f9",
                "description": f"Request type: {request_type}",
            })
            label_result = gh.issue_labels_add(repo, issue_number, [request_type])
            if label_result.get("added"):
                result["labels_applied"].append(request_type)

    except Exception as e:
        result["error"] = str(e)

    return result
