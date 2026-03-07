"""Session state persistence helpers — todos, phase, PRs, git, time, errors.

These functions persist live session state to the runtime cache
so it survives compaction, crash, and container restart.
Each function is a targeted write — minimal I/O, maximum recovery.

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .cache import (
    _find_runtime_cache, commit_cache, read_runtime_cache, update_session_data,
)

# Re-export from split modules for backward compatibility
from .notes import generate_session_notes  # noqa: F401
from .trimming import trim_session_cache, trim_all_session_caches  # noqa: F401


def load_session_todos() -> list:
    """Load pending todos from the session cache for restoration.

    Returns:
        List of dicts with {content, status, activeForm} ready for TodoWrite.
    """
    cache = read_runtime_cache()
    if not cache:
        return []

    session_data = cache.get("session_data", {})
    snapshot = session_data.get("todo_snapshot", [])
    if not snapshot:
        return []

    todos = []
    for t in snapshot:
        content = t.get("content", "")
        status = t.get("status", "pending")
        if not content:
            continue
        active = content
        if status != "completed":
            active = f"Working on: {content}"
        else:
            active = f"Completed: {content}"
        todos.append({
            "content": content,
            "status": status,
            "activeForm": active,
        })
    return todos


def update_todo_snapshot(todos: list) -> bool:
    """Persist the full todo list state to the session cache.

    Args:
        todos: List of dicts, each with {content, status}.

    Returns:
        True if update succeeded.
    """
    return update_session_data("todo_snapshot", [
        {"content": t.get("content", ""), "status": t.get("status", "pending")}
        for t in todos
    ])


def update_session_phase(phase: str) -> bool:
    """Persist the current session lifecycle phase.

    Args:
        phase: One of "wakeup", "planning", "executing", "saving", "delivered".

    Returns:
        True if update succeeded.
    """
    valid_phases = ("wakeup", "planning", "executing", "saving", "delivered")
    if phase not in valid_phases:
        return False
    return update_session_data("session_phase", phase)


def append_pr_number(number: int, title: str = "",
                     status: str = "open") -> bool:
    """Append a PR record to the session cache.

    Args:
        number: PR number.
        title: PR title.
        status: "open", "merged", or "closed".

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

    if "session_data" not in cache:
        cache["session_data"] = {}
    if "pr_numbers" not in cache["session_data"]:
        cache["session_data"]["pr_numbers"] = []

    # Don't duplicate — update status if PR already tracked
    for pr in cache["session_data"]["pr_numbers"]:
        if pr.get("number") == number:
            pr["status"] = status
            pr["title"] = title or pr.get("title", "")
            cache["updated"] = datetime.now(timezone.utc).isoformat()
            with open(cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
            commit_cache("data: update PR status in cache")
            return True

    cache["session_data"]["pr_numbers"].append({
        "number": number,
        "title": title,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        commit_cache("data: append PR number to cache")
        return True
    except OSError:
        return False


def update_git_state(last_commit_sha: str = "",
                     uncommitted_count: int = 0) -> bool:
    """Persist the last known git state.

    Args:
        last_commit_sha: SHA of the last commit.
        uncommitted_count: Number of uncommitted files.

    Returns:
        True if update succeeded.
    """
    return update_session_data("git_state", {
        "last_commit_sha": last_commit_sha,
        "uncommitted_count": uncommitted_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def append_time_marker(event: str) -> bool:
    """Append a timestamped event marker for time compilation.

    Args:
        event: Description of the event.

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

    if "session_data" not in cache:
        cache["session_data"] = {}
    if "time_markers" not in cache["session_data"]:
        cache["session_data"]["time_markers"] = []

    cache["session_data"]["time_markers"].append({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        commit_cache("data: append time marker to cache")
        return True
    except OSError:
        return False


def update_elevation_status(elevated: bool) -> bool:
    """Persist whether the session has a valid GH_TOKEN."""
    return update_session_data("elevation_status", elevated)


def update_default_branch(branch_name: str) -> bool:
    """Persist the detected default branch name."""
    return update_session_data("default_branch", branch_name)


def update_work_summary(summary: str) -> bool:
    """Persist a running summary of work accomplished so far."""
    return update_session_data("work_summary", summary)


def append_error(error: str) -> bool:
    """Append an error/failure record to the session cache.

    Args:
        error: Description of the error.

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

    if "session_data" not in cache:
        cache["session_data"] = {}
    if "errors_encountered" not in cache["session_data"]:
        cache["session_data"]["errors_encountered"] = []

    cache["session_data"]["errors_encountered"].append({
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    cache["updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
        commit_cache("data: append error to cache")
        return True
    except OSError:
        return False


def update_issue_comments_count(count: int) -> bool:
    """Persist the number of comments posted to the session issue."""
    return update_session_data("issue_comments_count", count)


def check_pending_todos() -> dict:
    """Check for pending/in_progress todos before save.

    Gate before doc check: if any todos are not completed, the user
    must decide for each one: complete now, or defer to next session.
    Deferred todos remain in the cache (todo_snapshot) and the startup
    hook displays them at next session start.

    Returns:
        Dict with:
          has_pending: bool — True if any todo is not completed
          pending: list — [{content, status}] of non-completed todos
          completed: list — [{content, status}] of completed todos
          summary: str — human-readable summary for AskUserQuestion
    """
    cache = read_runtime_cache()
    if not cache:
        return {"has_pending": False, "pending": [], "completed": [],
                "summary": "No cache found."}

    session_data = cache.get("session_data", {})
    snapshot = session_data.get("todo_snapshot", [])

    if not snapshot:
        return {"has_pending": False, "pending": [], "completed": [],
                "summary": "No todos tracked."}

    pending = [t for t in snapshot
               if t.get("status") in ("pending", "in_progress")]
    completed = [t for t in snapshot if t.get("status") == "completed"]

    if not pending:
        return {"has_pending": False, "pending": [], "completed": completed,
                "summary": f"All {len(completed)} todo(s) completed."}

    lines = [f"**{len(pending)} todo(s) not completed:**"]
    for i, t in enumerate(pending):
        status_icon = "⏳" if t["status"] == "in_progress" else "⬚"
        lines.append(f"  {i+1}. {status_icon} {t['content']}")
    lines.append("")
    lines.append("Options per todo: complete now, or defer to next session.")
    lines.append("Deferred todos appear at next session startup.")

    return {
        "has_pending": True,
        "pending": pending,
        "completed": completed,
        "summary": "\n".join(lines),
    }


def defer_todos_to_next_session(deferred_contents: list) -> bool:
    """Mark specified todos as deferred — they survive in the cache.

    The startup hook (startup-checklist.sh) scans recent session-runtime
    caches and displays pending todos. Deferred todos keep their status
    (pending/in_progress) so they appear at next session start.

    Args:
        deferred_contents: List of todo content strings to keep as-is.

    Returns:
        True if cache was updated.
    """
    cache = read_runtime_cache()
    if not cache:
        return False

    session_data = cache.get("session_data", {})
    snapshot = session_data.get("todo_snapshot", [])

    # Mark deferred todos explicitly
    for t in snapshot:
        if t.get("content") in deferred_contents:
            t["deferred"] = True
            t["deferred_at"] = datetime.now(timezone.utc).isoformat()

    return update_session_data("todo_snapshot", snapshot)


def compile_pre_save_summary(default_branch: str = "main") -> str:
    """Compile the pre-save summary automatically from cache and git.

    Generates the 7-section report (v50): résumé, metrics, time blocks,
    proportions, enterprise equivalent, deliveries, self-assessment.

    Returns:
        Formatted markdown string with the pre-save summary.
    """
    import subprocess

    cache = read_runtime_cache()
    session_data = cache.get("session_data", {}) if cache else {}

    # Gather metrics from git
    try:
        diff_stat = subprocess.check_output(
            ["git", "diff", "--stat", f"origin/{default_branch}...HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        diff_stat = "(unable to compute)"

    try:
        changed_files = subprocess.check_output(
            ["git", "diff", "--name-only", f"origin/{default_branch}...HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        changed_files = []

    try:
        commit_count = subprocess.check_output(
            ["git", "rev-list", "--count", f"origin/{default_branch}..HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit_count = "?"

    # PRs from cache
    prs = session_data.get("pr_numbers", [])
    pr_lines = []
    for pr in prs:
        pr_lines.append(
            f"| #{pr.get('number', '?')} | {pr.get('title', '')} "
            f"| {pr.get('status', '?')} |"
        )

    # Todos from cache
    todos = session_data.get("todo_snapshot", [])
    completed = [t for t in todos if t.get("status") == "completed"]
    pending = [t for t in todos if t.get("status") != "completed"]

    # Work summary
    work_summary = session_data.get("work_summary", "No summary recorded.")

    # Time markers
    time_markers = session_data.get("time_markers", [])
    time_lines = []
    for tm in time_markers:
        time_lines.append(f"| {tm.get('event', '')} | {tm.get('timestamp', '')[:19]} |")

    # Build summary
    sections = []

    sections.append("## Résumé")
    sections.append(work_summary)
    sections.append("")

    sections.append("## Métriques")
    sections.append(f"| Métrique | Valeur |")
    sections.append(f"|----------|--------|")
    sections.append(f"| Fichiers modifiés | {len(changed_files)} |")
    sections.append(f"| Commits | {commit_count} |")
    sections.append(f"| PRs | {len(prs)} |")
    sections.append(f"| Todos complétés | {len(completed)}/{len(todos)} |")
    sections.append("")

    if pr_lines:
        sections.append("## Livraisons")
        sections.append("| PR | Titre | Statut |")
        sections.append("|-----|-------|--------|")
        sections.extend(pr_lines)
        sections.append("")

    if time_lines:
        sections.append("## Blocs temporels")
        sections.append("| Événement | Timestamp |")
        sections.append("|-----------|-----------|")
        sections.extend(time_lines)
        sections.append("")

    if pending:
        sections.append("## Todos restants")
        for t in pending:
            sections.append(f"- {t.get('content', '')}")
        sections.append("")

    sections.append("## Auto-évaluation")
    sections.append("| Critère | Conforme |")
    sections.append("|---------|----------|")

    issue_num = cache.get("issue_number") if cache else None
    sections.append(
        f"| Issue créée au début | {'Oui (#' + str(issue_num) + ')' if issue_num else 'Non'} |"
    )
    sections.append(
        f"| Todos utilisés | {'Oui' if todos else 'Non'} |"
    )
    sections.append(
        f"| G7 exchanges postés | {'Oui' if session_data.get('issue_comments_count', 0) > 0 else 'À vérifier'} |"
    )

    # Integrity grid compliance (v59): include in auto-évaluation
    # so gaps are visible in every pre-save summary — never hidden.
    try:
        from .integrity import integrity_compliance
        compliance = integrity_compliance()
        sections.append(
            f"| Integrity grid | {compliance['report_line']} |"
        )
    except (ImportError, Exception):
        sections.append("| Integrity grid | N/A (module unavailable) |")

    # Autonomous integrity tracking (v58): auto-pass C.1
    try:
        from .integrity import _auto_pass
        _auto_pass("C.1")
    except (ImportError, Exception):
        pass

    return "\n".join(sections)


def check_doc_updates_needed(default_branch: str = "main") -> dict:
    """Analyze session changes and detect which docs may need updating.

    Gate G8 implementation: before save, check if session deliverables
    impact user-facing or system documentation. Returns a structured
    report that Claude presents via AskUserQuestion.

    Checks:
    - README.md — if new features, publications, interfaces, structural changes
    - CHANGELOG.md — if any issue/PR was created (always needs update)
    - NEWS.md — if significant new capability or quality change
    - CLAUDE.md — if methodology or protocol changed
    - methodology/ — if new patterns, lessons, or workflows
    - publications/ — if publication content changed

    Returns:
        Dict with:
          needs_update: bool — True if any doc needs attention
          docs: list of dicts — [{file, reason, priority}]
          summary: str — human-readable summary for AskUserQuestion
    """
    import subprocess

    result = {
        "needs_update": False,
        "docs": [],
        "summary": "",
    }

    # Get files changed in this session vs default branch
    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only", f"origin/{default_branch}...HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: check uncommitted + last 5 commits
        try:
            diff_output = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~5..HEAD"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return result

    if not diff_output:
        return result

    changed_files = set(diff_output.splitlines())

    # Detection rules
    checks = []

    # CHANGELOG.md — always if PRs were created
    cache = read_runtime_cache()
    session_data = cache.get("session_data", {}) if cache else {}
    prs = session_data.get("pr_numbers", [])
    if prs or any("CHANGELOG" not in f for f in changed_files):
        if "CHANGELOG.md" not in changed_files:
            checks.append({
                "file": "CHANGELOG.md",
                "reason": f"{len(prs)} PR(s) created — needs changelog entry",
                "priority": "high",
            })

    # README.md — if scripts/, hooks, or new features changed
    readme_triggers = [f for f in changed_files if any(
        f.startswith(p) for p in
        ("scripts/", ".claude/hooks/", "publications/", "docs/interfaces/")
    )]
    if readme_triggers and "README.md" not in changed_files:
        checks.append({
            "file": "README.md",
            "reason": f"{len(readme_triggers)} infrastructure file(s) changed",
            "priority": "medium",
        })

    # CLAUDE.md — if methodology or protocol changed
    claude_triggers = [f for f in changed_files if any(
        f.startswith(p) for p in
        ("methodology/", ".claude/hooks/", "scripts/session_agent/")
    )]
    if claude_triggers and "CLAUDE.md" not in changed_files:
        checks.append({
            "file": "CLAUDE.md",
            "reason": f"{len(claude_triggers)} methodology/protocol file(s) changed",
            "priority": "high",
        })

    # NEWS.md — if significant capability added
    news_triggers = [f for f in changed_files if any(
        f.startswith(p) for p in
        ("publications/", "docs/interfaces/", "scripts/")
    ) and f.endswith((".py", ".sh", ".md"))]
    if len(news_triggers) >= 3 and "NEWS.md" not in changed_files:
        checks.append({
            "file": "NEWS.md",
            "reason": f"{len(news_triggers)} significant file(s) changed — new capability?",
            "priority": "low",
        })

    if checks:
        result["needs_update"] = True
        result["docs"] = checks
        lines = ["Documentation check (Gate G8):"]
        for c in checks:
            lines.append(f"  [{c['priority'].upper()}] {c['file']} — {c['reason']}")
        result["summary"] = "\n".join(lines)

    # Autonomous integrity tracking (v58): auto-pass C.11
    # The function was called — that's what the checkpoint tracks
    try:
        from .integrity import _auto_pass
        _auto_pass("C.11")
    except (ImportError, Exception):
        pass

    return result


def save_session(
    pre_save_summary: str,
    branch: str = "",
    default_branch: str = "main",
    close_issue: bool = False,
) -> dict:
    """Execute the COMPLETE save protocol in one call.

    This function enforces the save protocol mechanically — no steps can
    be forgotten because they're all in this function. Claude calls
    save_session() and everything happens in the right order.

    Steps (in order):
    1. Generate session notes markdown (notes/session-YYYY-MM-DD-*.md)
    2. Finalize runtime cache (session_phase=complete)
    3. Post session notes + pre-save summary on the issue
    4. Regenerate sessions.json (for Session Viewer)
    5. Commit all files (notes + cache + sessions.json)
    6. Push to branch
    7. Create PR to default branch
    8. Merge PR (if elevated)
    9. Post closing report on issue
    10. Close issue (if requested)
    11. Post post-close final comment

    Args:
        pre_save_summary: The pre-save compilation (metrics, time, etc.)
        branch: Current branch name (auto-detected if empty)
        default_branch: Target branch for PR (default: main)
        close_issue: Whether to close the issue after save

    Returns:
        Dict with results of each step: {notes_path, cache_finalized,
        posted_to_issue, committed, pushed, pr_number, merged, closed}
    """
    import subprocess

    results = {
        "notes_path": None,
        "cache_finalized": False,
        "posted_to_issue": False,
        "committed": False,
        "pushed": False,
        "pr_number": None,
        "merged": False,
        "closed": False,
        "errors": [],
    }

    # ── Flush pending comments before save ──
    # If comments were queued (rate-limiting, skip mode, GitHub offline),
    # try to post them now. This is the last chance before session ends.
    from .cache import flush_pending_comments, pending_comments_count
    pending = pending_comments_count()
    if pending > 0:
        flush_result = flush_pending_comments()
        results["pending_comments_flushed"] = flush_result["posted"]
        results["pending_comments_remaining"] = flush_result["remaining"]

    # ── Pre-condition gates (v58) ──
    # These gates enforce the complete save protocol mechanically.
    # No session — regardless of duration or perceived importance — may
    # skip these steps. See methodology/agent-identity.md.
    gate_errors = []

    # v59.3: Validate pre-save summary has required sections, not just length.
    # A fake 20-char string shouldn't pass this gate.
    REQUIRED_SUMMARY_MARKERS = ["Résumé", "Métriques", "Auto-évaluation"]
    if not pre_save_summary or len(pre_save_summary.strip()) < 20:
        gate_errors.append(
            "GATE BLOCKED: pre_save_summary is missing or too short. "
            "Every session requires a pre-save summary with metrics, "
            "time blocks, and self-assessment — even 5-minute sessions. "
            "Call compile_pre_save_summary() first."
        )
    elif not all(marker in pre_save_summary for marker in REQUIRED_SUMMARY_MARKERS):
        missing = [m for m in REQUIRED_SUMMARY_MARKERS if m not in pre_save_summary]
        gate_errors.append(
            f"GATE BLOCKED: pre_save_summary is missing required sections: "
            f"{', '.join(missing)}. Use compile_pre_save_summary() to generate "
            f"a valid summary with all 7 sections."
        )

    cache = read_runtime_cache()
    if not cache:
        gate_errors.append(
            "GATE BLOCKED: No runtime cache found. "
            "write_runtime_cache() must be called at session start."
        )

    # Skip-tracking sessions can save without an issue — logs stay in
    # local queue for resync at next session. Tracked sessions require
    # an issue for the full save protocol (notes→issue, closing report).
    is_skip = (cache.get("session_data", {}).get("skip_tracking", False)
               if cache else False)
    if cache and not cache.get("issue_number") and not is_skip:
        gate_errors.append(
            "GATE BLOCKED: No issue_number in cache. "
            "A GitHub issue must be created before save. "
            "The protocol requires issue tracking for every session."
        )

    if gate_errors:
        results["errors"] = gate_errors
        results["gate_blocked"] = True
        return results

    repo = cache.get("repo", "")
    issue_number = cache.get("issue_number")
    if not branch:
        branch = cache.get("branch", "")

    # Lazy import for autonomous integrity tracking (v58)
    try:
        from .integrity import _auto_pass
        _integrity_available = True
    except (ImportError, Exception):
        _integrity_available = False

    # Step 1: Generate session notes markdown
    # v59.3: Notes are MANDATORY (Gate G5). If generation fails,
    # block the save — don't continue with partial output.
    notes_path = generate_session_notes()
    if notes_path:
        results["notes_path"] = notes_path
        if _integrity_available:
            _auto_pass("C.2")  # notes_generated
    else:
        results["errors"].append(
            "GATE BLOCKED (G5): generate_session_notes() returned None. "
            "Session notes are mandatory — write notes manually if needed."
        )
        results["gate_blocked"] = True
        return results

    # Step 2: Finalize runtime cache
    update_session_data("session_phase", "complete")
    update_session_data("pre_save_summary", pre_save_summary)
    results["cache_finalized"] = True
    if _integrity_available:
        _auto_pass("C.3")  # cache_finalized

    # Step 3: Post pre-save summary + notes on issue
    if issue_number and repo:
        try:
            from .cache import post_exchange
            post_exchange("claude", "Pre-save summary",
                          pre_save_summary)
            if notes_path and os.path.exists(notes_path):
                with open(notes_path, 'r') as f:
                    notes_content = f.read()
                post_exchange("claude", "Session notes",
                              notes_content[:60000])  # GitHub limit
            results["posted_to_issue"] = True
        except Exception as e:
            results["errors"].append(f"Post to issue failed: {e}")

    # Step 4: Regenerate sessions.json (incremental — only current session)
    try:
        scripts_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        import sys
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from generate_sessions import incremental_update
        incremental_update()
        results["sessions_json_regenerated"] = True
        if _integrity_available:
            _auto_pass("C.4")  # sessions_compiled
    except Exception as e:
        results["sessions_json_regenerated"] = False
        results["errors"].append(f"sessions.json regeneration failed: {e}")

    # Step 5: Commit all files (notes + cache + sessions.json)
    try:
        files_to_add = []
        cache_path = _find_runtime_cache()
        if cache_path and os.path.exists(cache_path):
            files_to_add.append(cache_path)
        if notes_path and os.path.exists(notes_path):
            files_to_add.append(notes_path)
        sessions_json = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))),
            "docs", "data", "sessions.json")
        if os.path.exists(sessions_json):
            files_to_add.append(sessions_json)
        # Include pending-comments file if it still exists (unflushed)
        from .cache import _pending_comments_path
        pending_path = _pending_comments_path()
        if pending_path and os.path.exists(pending_path):
            files_to_add.append(pending_path)

        if files_to_add:
            subprocess.run(["git", "add"] + files_to_add,
                           check=True, capture_output=True)
            result = subprocess.run(
                ["git", "commit", "-m",
                 "save: session notes + finalized cache + sessions.json"],
                capture_output=True
            )
            results["committed"] = result.returncode == 0
            if result.returncode == 0 and _integrity_available:
                # v59.3: C.6 requires BOTH files to actually exist — not just
                # a successful commit. Verify dual output before passing.
                has_notes = notes_path and os.path.exists(notes_path)
                has_cache = cache_path and os.path.exists(cache_path)
                if has_notes and has_cache:
                    _auto_pass("C.6")  # dual_output_verified
                else:
                    results["errors"].append(
                        f"C.6 FAILED: dual output incomplete — "
                        f"notes={'exists' if has_notes else 'MISSING'}, "
                        f"cache={'exists' if has_cache else 'MISSING'}"
                    )
                _auto_pass("C.7")  # committed_final
    except Exception as e:
        results["errors"].append(f"Commit failed: {e}")

    # Step 6: Push
    if branch:
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch],
                capture_output=True, timeout=30
            )
            results["pushed"] = result.returncode == 0
            if result.returncode == 0 and _integrity_available:
                _auto_pass("C.8")  # pushed_final
        except Exception as e:
            results["errors"].append(f"Push failed: {e}")

    # Step 7+8: Create PR and merge
    if branch and repo:
        try:
            import sys
            scripts_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            from gh_helper import GitHubHelper
            gh = GitHubHelper()

            pr_title = cache.get("issue_title", "Session save")
            pr_body = (f"Session save\n\n"
                       f"Closes #{issue_number}\n" if issue_number else "")
            pr_result = gh.pr_create_and_merge(
                repo, branch, default_branch,
                pr_title, body=pr_body
            )
            if pr_result.get("number"):
                results["pr_number"] = pr_result["number"]
                if _integrity_available:
                    _auto_pass("C.9")  # pr_created
            results["merged"] = pr_result.get("merged", False)
            if pr_result.get("merged") and _integrity_available:
                _auto_pass("C.10")  # pr_merged
        except Exception as e:
            results["errors"].append(f"PR create/merge failed: {e}")

    # Step 9+10+11: Closing report + close issue + post-close comment
    if issue_number and repo and close_issue:
        try:
            from gh_helper import GitHubHelper
            gh = GitHubHelper()

            # Closing report
            closing_body = (
                f"## Session Save Complete\n\n"
                f"- Notes: {results['notes_path'] or 'N/A'}\n"
                f"- PR: #{results['pr_number'] or 'N/A'}\n"
                f"- Merged: {results['merged']}\n"
            )
            gh.issue_comment_post(repo, issue_number, closing_body)

            # Close
            gh.issue_close(repo, issue_number)
            results["closed"] = True

            # Post-close final
            gh.issue_comment_post(repo, issue_number,
                                  "Session closed. Audit trail complete.")
            if _integrity_available:
                _auto_pass("C.12")  # post_close_comment
        except Exception as e:
            results["errors"].append(f"Close/report failed: {e}")

    return results
