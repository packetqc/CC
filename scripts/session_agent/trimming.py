"""Session cache trimming — reduce cache size while preserving continuity.

Provides functions to trim individual or all session cache files by
removing completed todos, old addons, and bulky diagnostic data.

Authors: Martin Paquet, Claude (Anthropic)
"""

import glob
import json
import os
import subprocess
from datetime import datetime, timezone

from .cache import _find_runtime_cache


def trim_session_cache(cache_path: str = None, max_addons: int = 5,
                       strip_completed: bool = True) -> dict:
    """Trim a session cache file to reduce size while preserving continuity data.

    Args:
        cache_path: Path to cache file. If None, uses current session's cache.
        max_addons: Keep only the latest N addon entries (default 5).
        strip_completed: If True, remove completed todos from snapshot.

    Returns:
        Dict with {trimmed: bool, original_size: int, new_size: int, path: str}.
    """
    if cache_path is None:
        cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return {"trimmed": False, "error": "cache not found"}

    original_size = os.path.getsize(cache_path)

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"trimmed": False, "error": str(e)}

    sd = cache.get("session_data", {})
    changed = False

    # 1. Strip completed todos
    if strip_completed and "todo_snapshot" in sd:
        original_todos = sd["todo_snapshot"]
        sd["todo_snapshot"] = [
            t for t in original_todos
            if t.get("status") in ("pending", "in_progress")
        ]
        if len(sd["todo_snapshot"]) != len(original_todos):
            changed = True

    # 2. Trim addons to latest N
    if "request_addon" in sd and len(sd["request_addon"]) > max_addons:
        sd["request_addon"] = sd["request_addon"][-max_addons:]
        changed = True
    if "request_addon_synthesis" in sd and len(sd["request_addon_synthesis"]) > max_addons:
        sd["request_addon_synthesis"] = sd["request_addon_synthesis"][-max_addons:]
        changed = True

    # 3. Strip bulky diagnostic/history data
    bulky_keys = [
        "engineering_cycle_history", "errors_encountered",
        "time_markers", "files_modified",
    ]
    for key in bulky_keys:
        if key in sd and sd[key]:
            sd[key] = []
            changed = True

    if not changed:
        return {
            "trimmed": False,
            "original_size": original_size,
            "new_size": original_size,
            "path": cache_path,
            "reason": "nothing to trim",
        }

    cache["session_data"] = sd
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        new_size = os.path.getsize(cache_path)
        return {
            "trimmed": True,
            "original_size": original_size,
            "new_size": new_size,
            "saved_bytes": original_size - new_size,
            "path": cache_path,
        }
    except OSError as e:
        return {"trimmed": False, "error": str(e)}


def trim_all_session_caches(notes_dir: str = None, max_addons: int = 5,
                            skip_current: bool = True) -> list:
    """Trim all session cache files in the notes directory.

    Args:
        notes_dir: Path to notes/ directory. Auto-detected if None.
        max_addons: Keep only the latest N addon entries per cache.
        skip_current: If True, skip the current session's cache file.

    Returns:
        List of trim results, one per file processed.
    """
    if notes_dir is None:
        try:
            repo_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True
            ).stdout.strip()
            notes_dir = os.path.join(repo_root, "notes")
        except Exception:
            return []

    if not os.path.isdir(notes_dir):
        return []

    cache_files = sorted(
        glob.glob(os.path.join(notes_dir, "session-runtime-*.json")),
        key=os.path.getmtime,
    )

    current_cache = _find_runtime_cache() if skip_current else None
    results = []

    for fpath in cache_files:
        if skip_current and current_cache and os.path.abspath(fpath) == os.path.abspath(current_cache):
            results.append({
                "path": fpath,
                "trimmed": False,
                "reason": "current session — skipped",
            })
            continue
        result = trim_session_cache(fpath, max_addons=max_addons)
        results.append(result)

    return results
