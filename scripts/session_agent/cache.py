"""Runtime cache — core read/write/find operations for session persistence.

The runtime cache is a JSON file in notes/ that persists session issue info
across compaction, crash, and container restart. Each session has its own
cache file: notes/session-runtime-<suffix>.json.

Also manages the PreToolUse enforcement state file
(/tmp/.claude-session-state.json) — write_runtime_cache() auto-unlocks
the issue gate when called, so the existing protocol step (Gate G2)
automatically enables Edit/Write without extra manual steps.

Authors: Martin Paquet, Claude (Anthropic)
"""

import glob
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional, List


# ── Pending comments queue ──────────────────────────────────────────
# When GitHub API is unavailable (rate-limit, network error), comments
# are queued locally in notes/pending-comments-<suffix>.json and
# flushed automatically when the API recovers.
PENDING_COMMENTS_PREFIX = "pending-comments-"
FLUSH_DELAY_SECONDS = 2  # Anti-flood: seconds between each queued post


# Runtime cache — persists session issue info across compaction/restart
# Written to notes/ (git-tracked) and mirrored to /tmp/ (fast access for hooks)
# Naming: session-runtime-<suffix>.json where <suffix> is derived from the
# branch name (e.g., claude/session-cache-qa-0o1sQ → session-runtime-0o1sQ.json).
# This supports multi-session persistence — each session has its own cache file.
RUNTIME_CACHE_LEGACY = "session-runtime.json"

# PreToolUse enforcement state file — ephemeral, per-container
# Created by SessionStart hook, checked by PreToolUse hook,
# updated by write_runtime_cache() and update_enforcement_state()
ENFORCEMENT_STATE_FILE = "/tmp/.claude-session-state.json"


def update_enforcement_state(**kwargs) -> bool:
    """Update the PreToolUse enforcement state file.

    The state file (/tmp/.claude-session-state.json) controls whether
    Edit/Write/NotebookEdit are allowed. Two gates must pass:
      - protocol_completed: wakeup through integrity check done
      - issue_created: GitHub session issue exists

    **Hardened (v100.1)**: Gate unlocks are validated, not blindly accepted.
      - protocol_completed=True requires integrity grid with S.0+S.1 passed
      - g7_skip=True requires _g7_skip_authorized flag (set by init_skip_cache)

    Args:
        **kwargs: Keys to update in the state file.

    Returns:
        True if update succeeded, False otherwise.
    """
    if not os.path.exists(ENFORCEMENT_STATE_FILE):
        return False

    # ── Hardened validation (v100.1) ──────────────────────────────
    # Prevent bypass: protocol_completed=True requires PROOF that
    # the wakeup actually happened (integrity grid with S.0+S.1 passed).
    if kwargs.get("protocol_completed") is True:
        if not _validate_protocol_prerequisites():
            return False

    # Prevent bypass: g7_skip=True requires authorization from
    # init_skip_cache() — not a direct one-liner call.
    if kwargs.get("g7_skip") is True:
        if not kwargs.pop("_g7_skip_authorized", False):
            # Check if caller is init_skip_cache (via authorized flag in state)
            try:
                with open(ENFORCEMENT_STATE_FILE, 'r') as f:
                    current = json.load(f)
                if not current.get("_g7_skip_authorized"):
                    return False
            except (json.JSONDecodeError, OSError):
                return False
    # Clean up internal flag — never persist it
    kwargs.pop("_g7_skip_authorized", None)

    try:
        with open(ENFORCEMENT_STATE_FILE, 'r') as f:
            state = json.load(f)
        state.update(kwargs)
        with open(ENFORCEMENT_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

        # Autonomous integrity tracking (v58): auto-pass S.3
        # when protocol_completed is set to True.
        if kwargs.get("protocol_completed"):
            try:
                from .integrity import _auto_pass
                _auto_pass("S.3")
            except (ImportError, Exception):
                pass

        return True
    except (json.JSONDecodeError, OSError):
        return False


def _validate_protocol_prerequisites() -> bool:
    """Verify that wakeup actually happened before allowing Gate 1 unlock.

    Checks the integrity grid in the runtime cache for evidence that
    S.0 (CLAUDE.md read) and S.1 (methodology read) were passed.
    Without these, protocol_completed=True is rejected.

    This prevents the bypass where a session calls
    update_enforcement_state(protocol_completed=True) without
    completing the wakeup protocol.

    Returns:
        True if prerequisites are met, False otherwise.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        with open(cache_path, 'r') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    sd = cache.get("session_data", {})
    integrity = sd.get("integrity", {})
    grid = integrity.get("grid", {})

    if not grid:
        return False

    # Require S.0 (sunglasses/CLAUDE.md) and S.1 (methodology) to be passed
    s0 = grid.get("S.0", {})
    s1 = grid.get("S.1", {})

    s0_ok = s0.get("status") in ("passed", "skipped_by_user")
    s1_ok = s1.get("status") in ("passed", "skipped_by_user")

    return s0_ok and s1_ok


def _session_id_to_suffix(session_id: str) -> str:
    """Extract a short unique suffix from a session/branch ID.

    Takes a branch name like 'claude/session-cache-qa-0o1sQ' and extracts
    the unique trailing identifier (e.g., '0o1sQ'). Falls back to sanitizing
    the full ID if no standard pattern is found.
    """
    if not session_id:
        return ""
    # Extract the last segment after the final '-' in the branch name
    # claude/session-cache-qa-0o1sQ → 0o1sQ
    parts = session_id.rstrip('/').split('-')
    if len(parts) > 1:
        suffix = parts[-1]
        # Sanitize: only alphanumeric chars
        suffix = ''.join(c for c in suffix if c.isalnum())
        if suffix:
            return suffix
    # Fallback: sanitize the full ID
    sanitized = session_id.replace('/', '-').replace(' ', '-')
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '-')
    return sanitized[-20:] if len(sanitized) > 20 else sanitized


def _runtime_cache_filename(session_id: str = "") -> str:
    """Get the cache filename for a session.

    Returns 'session-runtime-<suffix>.json' for identified sessions,
    or the legacy 'session-runtime.json' when no session ID is available.
    """
    suffix = _session_id_to_suffix(session_id)
    if suffix:
        return f"session-runtime-{suffix}.json"
    return RUNTIME_CACHE_LEGACY


def _find_runtime_cache(session_id: str = "") -> Optional[str]:
    """Find the runtime cache file in notes/ directory.

    When session_id is provided, looks for the session-specific cache file.
    When not provided, looks for the current branch's cache, then falls back
    to finding any existing session-runtime*.json (latest by mtime).
    Returns the full path if found, None otherwise.
    """
    # Try git root
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        notes_dir = os.path.join(root, "notes")

        # If session_id provided, use it directly
        if session_id:
            filename = _runtime_cache_filename(session_id)
            return os.path.join(notes_dir, filename)

        # Try to detect session from current git branch
        branch = ""
        try:
            branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            if branch and branch.startswith("claude/"):
                filename = _runtime_cache_filename(branch)
                path = os.path.join(notes_dir, filename)
                # Always return the branch-based path, even if file
                # doesn't exist yet. Falling through to the mtime
                # fallback returns a DIFFERENT session's cache file,
                # causing task_workflow data to be written to the wrong
                # file and lost when write_runtime_cache() creates the
                # correct file fresh.
                return path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback: check for legacy single-file cache
        legacy_path = os.path.join(notes_dir, RUNTIME_CACHE_LEGACY)
        if os.path.exists(legacy_path):
            return legacy_path

        # Fallback: find any session-runtime-*.json (latest by mtime)
        pattern = os.path.join(notes_dir, "session-runtime-*.json")
        matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if matches:
            return matches[0]

        # No cache found — return path for current branch (will be created)
        if branch and branch.startswith("claude/"):
            filename = _runtime_cache_filename(branch)
            return os.path.join(notes_dir, filename)

        # Ultimate fallback: legacy name
        return os.path.join(notes_dir, RUNTIME_CACHE_LEGACY)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def commit_cache(message: str = "data: persist session cache") -> bool:
    """Commit the current session's cache file to git.

    Convenience function that finds the active cache file,
    stages it, and commits. Non-blocking: if commit fails
    (nothing to commit, git issues), returns False silently.

    Args:
        message: Commit message. Defaults to generic cache persist message.

    Returns:
        True if commit succeeded, False otherwise.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return False

    try:
        subprocess.run(
            ["git", "add", cache_path],
            check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def write_runtime_cache(repo: str, issue_number: Optional[int] = None,
                        issue_title: str = "", branch: str = "",
                        mode: str = "normal",
                        request_description: str = "",
                        clip_mode: str = "discard",
                        session_data: Optional[dict] = None):
    """Write the session runtime cache to notes/.

    This cache persists the session's metadata so the agent can
    auto-reconnect after compaction or container restart. Works with
    or without a GitHub issue — skip-tracking sessions still get a
    local cache for identity, todos, and continuity.

    Args:
        repo: owner/repo format
        issue_number: GitHub issue number (None for skip-tracking sessions)
        issue_title: Issue title for display
        branch: Current branch name
        mode: Agent frequency mode
        request_description: Session goal description (survives compaction)
        clip_mode: Current clip lifecycle mode ('capture' or 'discard')
        session_data: Flexible dict of session state that must survive compaction
    """
    cache_path = _find_runtime_cache(session_id=branch)
    if not cache_path:
        return

    # Preserve existing fields that callers may not provide
    existing = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Seed the full session_data skeleton on first creation.
    # Every cache — tracked or skip — starts with the complete structure.
    # This ensures engineering_cycle, agent_identity, todo_snapshot, etc.
    # are always present, not just for skip-tracking sessions.
    default_session_data = {
        "agent_identity": {
            "role": "systems engineer",
            "source": "methodology/agent-identity.md",
            "principles": [
                "Protocol is non-negotiable — every session, full cycle, no exceptions",
                "Zero judgment on task importance — protocol decides, not perception",
                "Engineering rigor over convenience — always choose right over fast",
                "The cycle is complete or it did not happen",
                "Self-correction, not self-permission — instinct to skip = execute the step"
            ],
            "cycle": "wakeup → issue → plan → execute → pre-save summary → doc check → save → PR → merge → close",
            "recovery_instruction": "After compaction: re-read methodology/agent-identity.md BEFORE any action"
        },
        "session_phase": "active",
        "todo_snapshot": [],
        "files_modified": [],
        "work_summary": "",
        "pr_numbers": [],
        "comment_ids": [],
        "engineering_cycle": {},
        "time_markers": [],
        "errors_encountered": [],
        "issue_comments_count": 0,
        "elevation_status": None,
        "default_branch": "",
        "git_state": {},
        "decisions": [],
        "issues_worked": [],
    }

    # Merge: defaults → existing → caller-provided (each layer wins over the previous)
    merged_session_data = {**default_session_data}
    merged_session_data.update(existing.get("session_data", {}))
    if session_data:
        merged_session_data.update(session_data)

    cache = {
        "version": 3,
        "session_id": branch or "",
        "repo": repo,
        "issue_number": issue_number or 0,
        "issue_title": issue_title,
        "branch": branch,
        "mode": mode,
        "created": existing.get("created", datetime.now(timezone.utc).isoformat()),
        "updated": datetime.now(timezone.utc).isoformat(),
        "agent_initialized": True,
        "request_description": request_description or existing.get("request_description", ""),
        "clip_mode": clip_mode or existing.get("clip_mode", "discard"),
        "session_data": merged_session_data,
    }

    # Ensure notes/ directory exists
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        commit_cache("data: persist session cache")
    except OSError:
        pass

    # Auto-unlock PreToolUse enforcement gate (v59.3: conditional unlock).
    # For tracked sessions: issue_number is set, gate unlocks normally.
    # For skip-tracking sessions: issue_created stays False but a separate
    # skip_tracking_unlocked flag allows edits. This prevents the bypass
    # where write_runtime_cache(issue_number=None) falsely sets
    # issue_created=True, making the grid think Gate G1 passed.
    if issue_number and issue_number > 0:
        update_enforcement_state(
            issue_created=True,
            issue_number=issue_number
        )
    else:
        # Skip-tracking: unlock editing via separate flag, NOT issue_created
        update_enforcement_state(
            skip_tracking_unlocked=True,
            issue_number=0
        )

    # Autonomous integrity tracking (v58): auto-pass T.1 and T.2
    # when write_runtime_cache is called with an issue.
    try:
        from .integrity import _auto_pass
        if issue_number:
            _auto_pass("T.1")  # issue_created
        _auto_pass("T.2")  # cache_initialized
    except (ImportError, Exception):
        pass  # Integrity module not available — no-op


def init_skip_cache(repo: str, branch: str,
                    request_description: str = "") -> bool:
    """Initialize a local session cache for skip-tracking sessions.

    Called when the user selects "Skip — no tracking" at the session
    popup. Creates a full cache with agent identity, branch, and
    session metadata — everything needed for todo tracking, identity
    recovery post-compaction, and session continuity via startup hook.

    **Hardened (v100.1)**: This is the ONLY authorized path to set
    g7_skip=True. Direct calls to update_enforcement_state(g7_skip=True)
    are rejected without the authorization flag.

    Args:
        repo: owner/repo format
        branch: Current branch name
        request_description: Session goal description

    Returns:
        True if cache was created successfully.
    """
    # Authorize g7_skip BEFORE write_runtime_cache (which may trigger
    # enforcement state updates). The _g7_skip_authorized flag in the
    # state file signals that init_skip_cache was called legitimately.
    try:
        if os.path.exists(ENFORCEMENT_STATE_FILE):
            with open(ENFORCEMENT_STATE_FILE, 'r') as f:
                state = json.load(f)
            state["_g7_skip_authorized"] = True
            with open(ENFORCEMENT_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass

    # agent_identity, session_phase, and other defaults are now seeded
    # automatically by write_runtime_cache() — no need to duplicate here.
    write_runtime_cache(
        repo=repo,
        issue_number=None,
        issue_title=f"SKIP: {request_description[:60]}" if request_description else "SKIP: untracked session",
        branch=branch,
        mode="skip",
        request_description=request_description,
        session_data={
            "skip_tracking": True,
        }
    )

    # Now set g7_skip with authorization
    update_enforcement_state(g7_skip=True, _g7_skip_authorized=True)

    # Clean up authorization flag — one-time use
    try:
        if os.path.exists(ENFORCEMENT_STATE_FILE):
            with open(ENFORCEMENT_STATE_FILE, 'r') as f:
                state = json.load(f)
            state.pop("_g7_skip_authorized", None)
            with open(ENFORCEMENT_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass

    cache_path = _find_runtime_cache(session_id=branch)
    return cache_path is not None and os.path.exists(cache_path)


def update_session_data(key: str, value) -> bool:
    """Update a single key in the session_data store.

    Convenience method for incrementally persisting session state
    without rewriting the full cache. Reads current cache, updates
    the key in session_data, writes back.

    Supports dot-notation for nested updates:
        update_session_data('task_workflow.current_stage', 'implement')
    sets session_data['task_workflow']['current_stage'] = 'implement'.

    Args:
        key: The key to set in session_data. Dot-separated for nested paths.
        value: The value (must be JSON-serializable)

    Returns:
        True if update succeeded, False otherwise.
    """
    cache_path = _find_runtime_cache()
    if not cache_path:
        return False

    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False
    else:
        # Cache file doesn't exist yet — create minimal structure.
        # This handles the race where init_task_workflow() runs before
        # write_runtime_cache() creates the file. Data written here
        # is preserved by write_runtime_cache()'s merge logic.
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        cache = {
            "version": 3,
            "session_data": {},
            "created": datetime.now(timezone.utc).isoformat(),
        }

    if "session_data" not in cache:
        cache["session_data"] = {}

    # Dot-notation: traverse nested dicts
    parts = key.split('.')
    if len(parts) > 1:
        target = cache["session_data"]
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        leaf = parts[-1]
        existing_val = target.get(leaf)
        if isinstance(existing_val, dict) and isinstance(value, dict):
            existing_val.update(value)
        else:
            target[leaf] = value
    else:
        # Simple key — deep-merge dicts if both old and new values are dicts
        existing_val = cache["session_data"].get(key)
        if isinstance(existing_val, dict) and isinstance(value, dict):
            existing_val.update(value)
        else:
            cache["session_data"][key] = value
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        commit_cache("data: update session cache")

        # Autonomous integrity tracking (v59): auto-pass W.5 (cache_updated)
        # when the todo_snapshot is updated — this is the per-todo cache
        # update required by the work cycle protocol.
        if key == "todo_snapshot":
            try:
                from .integrity import _auto_pass
                _auto_pass("W.5")
            except (ImportError, Exception):
                pass

        return True
    except OSError:
        return False


def read_runtime_cache() -> Optional[dict]:
    """Read the session runtime cache from notes/.

    Returns:
        Dict with session metadata if cache exists, None otherwise.
    """
    cache_path = _find_runtime_cache()
    if not cache_path or not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def post_exchange(role: str, short_desc: str, content: str) -> Optional[int]:
    """Post a user or Claude exchange to the session's GitHub issue.

    One-liner wrapper that reads the runtime cache to get repo/issue,
    creates a SessionSync instance, and posts the comment. Also updates
    the enforcement state with last_post_time for G7 tracking.

    **Resilient**: On rate-limit or network failure, queues the comment
    locally in notes/pending-comments-<suffix>.json. Attempts to flush
    any previously queued comments before posting the new one.

    This is the primary API for G7 compliance — every user message and
    every significant Claude response should be posted via this function.

    Args:
        role: 'user' or 'claude' — determines avatar and format
        short_desc: Short header description (e.g., "Question about G7")
        content: The message content (user's text or Claude's response)

    Returns:
        Comment ID if posted, None if queued locally or no cache/token/issue.

    Usage:
        from scripts.session_agent import post_exchange
        post_exchange('user', 'Question about enforcement', 'Will this fix it?')
        post_exchange('claude', 'Analysis of G7 gap', '### Root cause\\n...')
    """
    cache = read_runtime_cache()
    if not cache:
        return None

    repo = cache.get("repo", "")
    # Ensure repo has owner/ prefix
    if repo and "/" not in repo:
        repo = f"packetqc/{repo}"
    issue_number = cache.get("issue_number", 0)

    # Skip-tracking / offline mode: no issue to post to — queue locally
    # for later resync when an issue becomes available
    session_data = cache.get("session_data", {})
    if not issue_number or session_data.get("skip_tracking"):
        queue_pending_comment(repo, issue_number, role, short_desc, content)
        update_enforcement_state(
            last_post_time=datetime.now(timezone.utc).isoformat()
        )
        return None

    # Try to flush any previously queued comments first
    pending = pending_comments_count()
    if pending > 0:
        flush_result = flush_pending_comments()
        if flush_result["stopped_reason"] in ("rate_limited", "post_failed"):
            # API still unavailable — queue this comment too
            queue_pending_comment(repo, issue_number, role, short_desc, content)
            # Still update G7 enforcement to prevent blocking
            update_enforcement_state(
                last_post_time=datetime.now(timezone.utc).isoformat()
            )
            return None

    try:
        # Import SessionSync lazily to avoid circular imports
        import sys
        import os as _os
        scripts_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from session_issue_sync import SessionSync

        sync = SessionSync(repo, issue_number)
        if not sync.enabled:
            # GitHub unavailable (no token, API down) — queue locally
            queue_pending_comment(repo, issue_number, role, short_desc, content)
            update_enforcement_state(
                last_post_time=datetime.now(timezone.utc).isoformat()
            )
            return None

        if role.lower() == 'user':
            comment_id = sync.post_user(content, short_desc)
        else:
            comment_id = sync.post_bot(short_desc, content)

        # Update enforcement state with last_post_time for G7 tracking
        if comment_id:
            update_enforcement_state(
                last_post_time=datetime.now(timezone.utc).isoformat()
            )
            # Autonomous integrity tracking (v58→v59): auto-pass T.4
            # (exchanges_active) AND W.6 (issue_commented).
            # T.4 fires once (first exchange). W.6 fires per work cycle
            # (resets with reset_work_cycle). Both are safe to call
            # repeatedly — _auto_pass is idempotent.
            # Auto-increment issue_comments_count in cache
            try:
                from .state import update_issue_comments_count
                current = session_data.get("issue_comments_count", 0)
                update_issue_comments_count(current + 1)
            except (ImportError, Exception):
                pass

            try:
                from .integrity import _auto_pass
                _auto_pass("T.4")
                _auto_pass("W.6")
            except (ImportError, Exception):
                pass
            return comment_id

        # Post returned None — likely rate-limited, queue locally
        queue_pending_comment(repo, issue_number, role, short_desc, content)
        update_enforcement_state(
            last_post_time=datetime.now(timezone.utc).isoformat()
        )
        return None

    except Exception as exc:
        # Network/API failure — queue locally instead of losing the comment
        queue_pending_comment(repo, issue_number, role, short_desc, content)
        update_enforcement_state(
            last_post_time=datetime.now(timezone.utc).isoformat()
        )
        # Track the error in session cache for pre-save summary
        try:
            from .state import append_error
            append_error(f"post_exchange failed: {type(exc).__name__}: {str(exc)[:100]}")
        except (ImportError, Exception):
            pass
        return None


def _pending_comments_path() -> Optional[str]:
    """Get the path for the pending comments queue file.

    Returns notes/pending-comments-<suffix>.json based on current branch.
    """
    cache_path = _find_runtime_cache()
    if not cache_path:
        return None
    notes_dir = os.path.dirname(cache_path)
    # Derive suffix from cache filename: session-runtime-XYZ.json → XYZ
    basename = os.path.basename(cache_path)
    suffix = basename.replace("session-runtime-", "").replace(".json", "")
    if not suffix or suffix == RUNTIME_CACHE_LEGACY.replace(".json", ""):
        suffix = "default"
    return os.path.join(notes_dir, f"{PENDING_COMMENTS_PREFIX}{suffix}.json")


def _read_pending_comments() -> List[dict]:
    """Read the pending comments queue from disk."""
    path = _pending_comments_path()
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_pending_comments(comments: List[dict]):
    """Write the pending comments queue to disk and commit to git.

    Pending comments are precious session logs — they must survive
    crashes by being committed immediately. Same pattern as
    write_runtime_cache() auto-commit.
    """
    path = _pending_comments_path()
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, 'w') as f:
            json.dump(comments, f, indent=2)
        # Auto-commit to git — logs must survive crashes
        subprocess.run(["git", "add", path],
                       check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m",
                        "data: persist pending comments queue"],
                       capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        pass


def queue_pending_comment(repo: str, issue_number: int,
                          role: str, short_desc: str, content: str):
    """Queue a comment locally when GitHub API is unavailable.

    Double persistence: writes to pending-comments-*.json AND mirrors
    into the runtime cache (session_data.exchange_log). The cache is
    auto-committed to git — if the pending file is lost (container
    restart, failed push), the logs survive in the cache on the branch.

    Args:
        repo: owner/repo format
        issue_number: GitHub issue number
        role: 'user' or 'claude'
        short_desc: Short header description
        content: The message content
    """
    entry = {
        "repo": repo,
        "issue_number": issue_number,
        "role": role,
        "short_desc": short_desc,
        "content": content,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
    }

    # Primary: pending comments queue file
    comments = _read_pending_comments()
    comments.append(entry)
    _write_pending_comments(comments)

    # Secondary: mirror FULL content in runtime cache.
    # Integrity > performance. If the queue file is lost (container
    # restart, failed push), the complete exchange content survives
    # in the cache on the branch — ready for reconstruction.
    cache = read_runtime_cache()
    if cache:
        sd = cache.get("session_data", {})
        exchange_log = sd.get("exchange_log", [])
        exchange_log.append({
            "role": role,
            "desc": short_desc,
            "content": content,
            "at": entry["queued_at"],
        })
        update_session_data("exchange_log", exchange_log)


def flush_pending_comments(max_batch: int = 10) -> dict:
    """Flush queued comments to GitHub with anti-flood spacing.

    Attempts to post each pending comment. On success, removes from queue.
    On rate-limit/network failure, stops flushing (API still unavailable).
    Spaces posts by FLUSH_DELAY_SECONDS to avoid re-triggering rate limits.

    Args:
        max_batch: Maximum comments to flush in one call (default 10).

    Returns:
        Dict with 'posted' (count), 'remaining' (count), 'stopped_reason' (str or None).
    """
    comments = _read_pending_comments()
    if not comments:
        return {"posted": 0, "remaining": 0, "stopped_reason": None}

    try:
        import sys
        scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from session_issue_sync import SessionSync
    except ImportError:
        return {"posted": 0, "remaining": len(comments), "stopped_reason": "import_error"}

    posted = 0
    stop_reason = None

    for i, comment in enumerate(comments[:max_batch]):
        if posted > 0:
            time.sleep(FLUSH_DELAY_SECONDS)

        repo = comment["repo"]
        issue_number = comment["issue_number"]

        try:
            sync = SessionSync(repo, issue_number)
            if not sync.enabled:
                stop_reason = "sync_disabled"
                break

            if comment["role"].lower() == 'user':
                comment_id = sync.post_user(comment["content"], comment["short_desc"])
            else:
                comment_id = sync.post_bot(comment["short_desc"], comment["content"])

            if comment_id:
                posted += 1
                comment["_posted"] = True
                update_enforcement_state(
                    last_post_time=datetime.now(timezone.utc).isoformat()
                )
            else:
                # post returned None — likely rate-limited or error
                comment["attempts"] = comment.get("attempts", 0) + 1
                stop_reason = "post_failed"
                break
        except Exception as exc:
            exc_str = str(exc).lower()
            comment["attempts"] = comment.get("attempts", 0) + 1
            if "403" in exc_str or "429" in exc_str or "rate" in exc_str:
                stop_reason = "rate_limited"
            else:
                stop_reason = "error"
            break

    # Remove posted comments from queue
    remaining = [c for c in comments if not c.get("_posted")]
    # Clean up internal marker
    for c in remaining:
        c.pop("_posted", None)

    if remaining:
        _write_pending_comments(remaining)
    else:
        # Delete the file when queue is empty
        path = _pending_comments_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    return {
        "posted": posted,
        "remaining": len(remaining),
        "stopped_reason": stop_reason,
    }


def pending_comments_count() -> int:
    """Return the number of pending comments in the queue."""
    return len(_read_pending_comments())


def resync_to_issue(issue_number: int, repo: str = "") -> dict:
    """Resync queued comments to a GitHub issue.

    Used when a skip-tracking session's logs need to be pushed to an
    issue created after the fact, or when GitHub was offline and is now
    available. Rewrites all queued comments' issue_number to the target
    issue, then flushes.

    Args:
        issue_number: Target GitHub issue number to post comments to.
        repo: owner/repo format. If empty, reads from runtime cache.

    Returns:
        Dict with 'posted', 'remaining', 'total', 'stopped_reason'.
    """
    if not issue_number:
        return {"posted": 0, "remaining": 0, "total": 0,
                "stopped_reason": "no_issue_number"}

    comments = _read_pending_comments()
    if not comments:
        return {"posted": 0, "remaining": 0, "total": 0,
                "stopped_reason": None}

    # Resolve repo from cache if not provided
    if not repo:
        cache = read_runtime_cache()
        repo = cache.get("repo", "") if cache else ""
    if repo and "/" not in repo:
        repo = f"packetqc/{repo}"

    # Rewrite all comments to target issue
    for c in comments:
        c["issue_number"] = issue_number
        if repo:
            c["repo"] = repo

    _write_pending_comments(comments)

    total = len(comments)
    result = flush_pending_comments(max_batch=50)
    result["total"] = total

    # If all flushed, update cache to tracked mode
    if result["remaining"] == 0:
        cache = read_runtime_cache()
        if cache:
            update_session_data("skip_tracking", False)
            update_session_data("resynced_to_issue", issue_number)

    return result


def activate_tracking(issue_number: int, issue_title: str = "",
                      repo: str = "") -> dict:
    """Activate GitHub tracking mid-session after a skip.

    Full workflow: update cache with issue number → disable skip mode →
    reactivate G7 enforcement → resync queued comments to the issue.

    Called when the user says 'sync' or 'record' during a skip-tracking
    session. The issue must already exist (created by Claude before
    calling this function).

    Args:
        issue_number: The newly created GitHub issue number.
        issue_title: Issue title for cache metadata.
        repo: owner/repo format. If empty, reads from cache.

    Returns:
        Dict with 'activated' (bool), 'comments_synced' (int),
        'comments_remaining' (int).
    """
    cache = read_runtime_cache()
    if not cache:
        return {"activated": False, "comments_synced": 0,
                "comments_remaining": 0, "error": "no_cache"}

    if not repo:
        repo = cache.get("repo", "")

    # Update cache: switch from skip to tracked
    cache["issue_number"] = issue_number
    if issue_title:
        cache["issue_title"] = issue_title
    cache["mode"] = "normal"
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    sd = cache.get("session_data", {})
    sd["skip_tracking"] = False
    sd["activated_tracking_at"] = datetime.now(timezone.utc).isoformat()
    cache["session_data"] = sd

    # Write updated cache
    cache_path = _find_runtime_cache()
    if cache_path:
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
            commit_cache("data: activate tracking — skip→tracked")
        except OSError:
            pass

    # Unlock enforcement gates
    update_enforcement_state(
        issue_created=True,
        issue_number=issue_number,
        g7_skip=False
    )

    # Resync queued comments
    resync_result = resync_to_issue(issue_number, repo)

    return {
        "activated": True,
        "comments_synced": resync_result.get("posted", 0),
        "comments_remaining": resync_result.get("remaining", 0),
    }


def sync_remote_caches(default_branch: str = "main") -> list:
    """Fetch and read session cache files from the remote default branch.

    On wakeup, this function checks the remote default branch for session
    cache files committed by previous sessions. It reads each one and
    returns a summary list so the new session inherits context from
    past work.

    Args:
        default_branch: The repo's default branch name (main or master).

    Returns:
        List of dicts with session summaries, or empty list.
    """
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        notes_dir = os.path.join(root, "notes")

        # Get current branch to exclude own cache
        try:
            current_branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            current_branch = ""

        current_suffix = _session_id_to_suffix(current_branch) if current_branch else ""

        # List session-runtime-*.json files on the remote default branch
        try:
            remote_files_raw = subprocess.check_output(
                ["git", "ls-tree", "--name-only",
                 f"origin/{default_branch}", "notes/"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

        remote_caches = [
            f for f in remote_files_raw.splitlines()
            if f.startswith("notes/session-runtime-") and f.endswith(".json")
        ]

        if not remote_caches:
            return []

        results = []
        for remote_path in remote_caches:
            filename = os.path.basename(remote_path)

            # Skip the current session's own cache
            if current_suffix and current_suffix in filename:
                continue

            # Read the file content from the remote branch
            try:
                content = subprocess.check_output(
                    ["git", "show", f"origin/{default_branch}:{remote_path}"],
                    stderr=subprocess.DEVNULL
                ).decode()
                cache = json.loads(content)
            except (subprocess.CalledProcessError, json.JSONDecodeError,
                    FileNotFoundError):
                continue

            # Also copy to local notes/ if not present
            local_path = os.path.join(root, remote_path)
            if not os.path.exists(local_path):
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                try:
                    with open(local_path, 'w') as f:
                        json.dump(cache, f, indent=2)
                except OSError:
                    pass

            session_data = cache.get("session_data", {})
            addon_list = session_data.get("request_addon", [])
            results.append({
                "filename": filename,
                "session_id": cache.get("session_id", ""),
                "issue_number": cache.get("issue_number"),
                "issue_title": cache.get("issue_title", ""),
                "request_description": cache.get("request_description", ""),
                "work_summary": session_data.get("work_summary", ""),
                "addon_count": len(addon_list) if isinstance(addon_list, list) else 0,
                "updated": cache.get("updated", ""),
                "branch": cache.get("branch", ""),
                "phase": session_data.get("session_phase", "unknown"),
            })

        return sorted(results, key=lambda x: x.get("updated", ""), reverse=True)
    except Exception:
        return []
