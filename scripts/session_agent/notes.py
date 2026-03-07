"""Session notes generation — convert runtime cache to markdown notes.

Generates the markdown notes file (notes/session-YYYY-MM-DD-*.md) from
the JSON runtime cache. These markdown notes feed generate_sessions.py
→ sessions.json → Session Viewer (I1).

Note: This is NOT the runtime cache. The cache (JSON) feeds crash recovery
and session continuity. The notes (markdown) feed the web interface pipeline.
Both must be produced at save time.

Multi-issue sessions (v56): When issues_worked contains 2+ issues, produces
one notes file per issue with per-issue metrics and time compilation.

Authors: Martin Paquet, Claude (Anthropic)
"""

import os
import re
from datetime import datetime, timezone
from typing import List, Optional

from .cache import read_runtime_cache


def _extract_date(cache: dict) -> str:
    """Extract date string from cache."""
    created = cache.get("created", "")
    if created:
        try:
            return created[:10]
        except (IndexError, TypeError):
            pass
    issue_title = cache.get("issue_title", "")
    m = re.search(r"\d{4}-\d{2}-\d{2}", issue_title)
    if m:
        return m.group(0)
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _clean_title(title: str) -> str:
    """Remove SESSION: prefix and date suffix from title."""
    if title:
        title = re.sub(r"^SESSION:\s*", "", title)
        title = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", title)
    return title


def _slugify(text: str, max_len: int = 60) -> str:
    """Convert text to filename-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_len]


def _build_single_issue_notes(
    cache: dict,
    issue_info: Optional[dict] = None,
) -> str:
    """Build markdown content for a single issue.

    Args:
        cache: The full runtime cache dict.
        issue_info: Optional issue dict from issues_worked. If provided,
            overrides cache-level issue_number/title. Keys: number, title,
            type, pr, status, files, lines_added, lines_deleted, time_minutes,
            time_phases, summary, todos, category, related_issues, session_kind.
    """
    branch = cache.get("branch", "")
    session_data = cache.get("session_data", {})
    date_str = _extract_date(cache)

    # Determine issue identity — from issue_info or cache top-level
    if issue_info:
        issue_number = issue_info.get("number")
        raw_title = issue_info.get("title", "")
        issue_type = issue_info.get("type", "")
        issue_pr = issue_info.get("pr")
        issue_summary = issue_info.get("summary", "")
        issue_files = issue_info.get("files", [])
        lines_added = issue_info.get("lines_added", 0)
        lines_deleted = issue_info.get("lines_deleted", 0)
        time_minutes = issue_info.get("time_minutes", 0)
        time_phases = issue_info.get("time_phases", [])
        issue_todos = issue_info.get("todos", [])
        issue_category = issue_info.get("category", "")
        related_issues = issue_info.get("related_issues", [])
        session_kind = issue_info.get("session_kind", "original")
    else:
        issue_number = cache.get("issue_number")
        raw_title = cache.get("issue_title", "")
        issue_type = ""
        issue_pr = None
        issue_summary = ""
        issue_files = []
        lines_added = 0
        lines_deleted = 0
        time_minutes = 0
        time_phases = []
        issue_todos = []
        issue_category = ""
        related_issues = []
        session_kind = ""

    title = _clean_title(raw_title)
    if not title:
        slug = branch.replace("claude/", "")
        slug = re.sub(r"-[A-Za-z0-9]{5}$", "", slug)
        title = slug.replace("-", " ").title()

    lines = []
    lines.append(f"# Session Notes — {date_str} — {title}")
    lines.append("")

    # Context
    lines.append("## Context")
    if issue_summary:
        lines.append(issue_summary)
    elif cache.get("request_description"):
        lines.append(cache["request_description"])
    lines.append(f"Branch: `{branch}`")
    if issue_number:
        lines.append(f"Issue: #{issue_number}")
    if issue_type:
        lines.append(f"Type: {issue_type}")
    if session_kind:
        lines.append(f"Session kind: {session_kind} (root tree)")
    if related_issues:
        rel_str = ", ".join(
            f"#{r}" if isinstance(r, int) else str(r) for r in related_issues
        )
        lines.append(f"Related issues: {rel_str}")
    lines.append("")

    # Work Done — PR(s)
    pr_numbers = session_data.get("pr_numbers", [])
    if issue_pr:
        # Single PR for this issue
        lines.append("## Work Done")
        lines.append("")
        pr_info = None
        for pr in pr_numbers:
            if isinstance(pr, dict) and pr.get("number") == issue_pr:
                pr_info = pr
                break
        if pr_info:
            lines.append(f"### PR #{pr_info['number']} — {pr_info.get('title', '')}")
            lines.append(f"- Status: {pr_info.get('status', 'unknown')}")
        else:
            lines.append(f"### PR #{issue_pr}")
        lines.append("")
    elif pr_numbers and not issue_info:
        # Fallback: show all PRs (single-issue session)
        lines.append("## Work Done")
        lines.append("")
        for pr in pr_numbers:
            if isinstance(pr, dict):
                lines.append(f"### PR #{pr.get('number', '')} — {pr.get('title', '')}")
                if pr.get("status"):
                    lines.append(f"- Status: {pr['status']}")
            else:
                lines.append(f"### PR #{pr}")
        lines.append("")

    # Completed Tasks
    todos = issue_todos or session_data.get("todo_snapshot", [])
    if todos:
        lines.append("## Completed Tasks")
        lines.append("")
        for todo in todos:
            if isinstance(todo, dict):
                content = todo.get("content", "")
                status = todo.get("status", "")
                marker = "\u2705" if status == "completed" else "\u25cb"
                lines.append(f"- {marker} {content}")
            else:
                lines.append(f"- {todo}")
        lines.append("")

    # Work summary (only if not already in Context via issue_summary)
    work_summary = session_data.get("work_summary", "")
    if work_summary and not issue_summary:
        lines.append("## Summary")
        lines.append(work_summary)
        lines.append("")

    # Files modified
    files = issue_files or session_data.get("files_modified", [])
    if files:
        lines.append("## Files Modified")
        lines.append("")
        for f in files:
            lines.append(f"- {f}")
        lines.append("")

    # Metrics
    lines.append("## Metrics")
    lines.append("")
    pr_count = 1 if issue_pr else len(pr_numbers)
    file_count = len(files) if files else "?"
    metrics_parts = [f"{pr_count} PR{'s' if pr_count != 1 else ''}"]
    metrics_parts.append(f"{file_count} files modified")
    if lines_added or lines_deleted:
        metrics_parts.append(f"+{lines_added} \u2212{lines_deleted} lines")
    lines.append(f"- {', '.join(metrics_parts)}")
    if time_minutes:
        lines.append(f"- Estimated active time: ~{time_minutes} min")
    lines.append("")

    # Time Compilation
    if time_phases:
        lines.append("## Time Blocks")
        lines.append("")
        lines.append("| Phase | Duration | Activity |")
        lines.append("|-------|----------|----------|")
        for phase in time_phases:
            if isinstance(phase, dict):
                name = phase.get("name", "")
                duration = phase.get("duration", "")
                activity = phase.get("activity", "")
                cat = phase.get("category", "")
                cat_str = f" {cat}" if cat else ""
                lines.append(f"| {name} | {duration} |{cat_str} {activity} |")
            elif isinstance(phase, str):
                lines.append(f"| {phase} | | |")
        lines.append("")

    # Errors encountered (only for single-issue / cache-level)
    errors = session_data.get("errors_encountered", [])
    if errors and not issue_info:
        lines.append("## Errors Encountered")
        lines.append("")
        for e in errors:
            if isinstance(e, dict):
                lines.append(f"- {e.get('error', '')} ({e.get('timestamp', '')})")
            else:
                lines.append(f"- {e}")
        lines.append("")

    return "\n".join(lines)


def generate_session_notes(output_dir: str = "notes") -> Optional[str]:
    """Generate session notes markdown file(s) from the runtime cache.

    Single-issue sessions produce one file. Multi-issue sessions (when
    issues_worked contains 2+ issues) produce one file per issue, each
    with its own metrics and time compilation.

    Returns:
        Path to the generated markdown file (first/only), or None if
        cache not found. For multi-issue sessions, all files are written
        but only the first path is returned.
    """
    cache = read_runtime_cache()
    if not cache:
        return None

    session_data = cache.get("session_data", {})
    issues_worked = session_data.get("issues_worked", [])

    # Multi-issue path: one file per issue
    if len(issues_worked) >= 2:
        return _generate_multi_issue_notes(cache, issues_worked, output_dir)

    # Single-issue path: one file
    return _generate_single_issue_notes(cache, output_dir)


def _generate_single_issue_notes(
    cache: dict, output_dir: str
) -> Optional[str]:
    """Generate one session notes file (single-issue session)."""
    branch = cache.get("branch", "")
    date_str = _extract_date(cache)

    slug = ""
    if branch:
        slug = branch.replace("claude/", "")
        slug = re.sub(r"-[A-Za-z0-9]{5}$", "", slug)
    if not slug:
        title = _clean_title(cache.get("issue_title", ""))
        slug = _slugify(title) if title else "session"

    content = _build_single_issue_notes(cache)

    filename = f"session-{date_str}-{slug}.md"
    filepath = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
    except OSError:
        return None


def _generate_multi_issue_notes(
    cache: dict, issues_worked: List[dict], output_dir: str
) -> Optional[str]:
    """Generate one session notes file per issue (multi-issue session).

    Each issue gets its own markdown file with per-issue metrics and time
    compilation, following the multi-issue format from metrics-compilation.md
    and time-compilation.md.

    Returns path to the first generated file.
    """
    date_str = _extract_date(cache)
    os.makedirs(output_dir, exist_ok=True)
    first_path = None

    for issue_info in issues_worked:
        title = issue_info.get("title", "")
        clean = _clean_title(title)
        slug = _slugify(clean) if clean else f"issue-{issue_info.get('number', 'unknown')}"

        content = _build_single_issue_notes(cache, issue_info=issue_info)

        filename = f"session-{date_str}-{slug}.md"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            if first_path is None:
                first_path = filepath
        except OSError:
            continue

    return first_path
