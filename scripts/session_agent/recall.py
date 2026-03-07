"""Recall — deep memory search across all knowledge channels.

Hybrid command: searches near memory first (fast), then deeper layers
with progressive escalation. If stranded branch work is found, suggests
`recover` to cherry-pick/apply it.

Search layers (in order):
  1. Near memory (~5s): current session cache, recent runtime caches, recent notes
  2. Git memory (~10s): commit messages, branch names across claude/* branches
  3. GitHub memory (~15s, requires elevation): issue titles/comments, PR descriptions
  4. Deep memory (~30s): publications, methodology, patterns, lessons, minds/

Authors: Martin Paquet, Claude (Anthropic)
License: MIT
Knowledge version: v57
"""

import glob
import json
import os
import re
import subprocess
from datetime import datetime
from typing import Optional

from .helpers import _get_gh_helper


# ── Layer 1: Near Memory ────────────────────────────────────────────

def search_session_caches(query: str, max_results: int = 10) -> list:
    """Search across all session runtime caches (JSON).

    Searches issue_title, request_description, work_summary,
    todo_snapshot, decisions, and errors_encountered fields.

    Args:
        query: Search string (case-insensitive substring match).
        max_results: Maximum results to return.

    Returns:
        List of dicts: cache_file, issue_number, issue_title, field, match_text
    """
    results = []
    query_lower = query.lower()

    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        notes_dir = os.path.join(root, "notes")
        pattern = os.path.join(notes_dir, "session-runtime-*.json")
        cache_files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        for cache_file in cache_files:
            if len(results) >= max_results:
                break
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)

                filename = os.path.basename(cache_file)
                issue_num = data.get("issue_number", "?")
                issue_title = data.get("issue_title", "")

                # Search top-level fields
                searchable_top = {
                    "issue_title": issue_title,
                    "request_description": data.get("request_description", ""),
                    "branch": data.get("branch", ""),
                }
                for field, value in searchable_top.items():
                    if query_lower in str(value).lower():
                        results.append({
                            "source": "cache",
                            "file": filename,
                            "issue_number": issue_num,
                            "issue_title": issue_title,
                            "field": field,
                            "match_text": _truncate(str(value), 200),
                        })

                # Search session_data fields
                sd = data.get("session_data", {})
                searchable_sd = {
                    "work_summary": sd.get("work_summary", ""),
                    "decisions": json.dumps(sd.get("decisions", [])),
                    "errors_encountered": json.dumps(sd.get("errors_encountered", [])),
                }
                # Search todos
                todos = sd.get("todo_snapshot", [])
                if isinstance(todos, list):
                    for todo in todos:
                        content = todo.get("content", "") if isinstance(todo, dict) else str(todo)
                        if query_lower in content.lower():
                            results.append({
                                "source": "cache",
                                "file": filename,
                                "issue_number": issue_num,
                                "issue_title": issue_title,
                                "field": "todo",
                                "match_text": _truncate(content, 200),
                            })

                for field, value in searchable_sd.items():
                    if query_lower in str(value).lower():
                        results.append({
                            "source": "cache",
                            "file": filename,
                            "issue_number": issue_num,
                            "issue_title": issue_title,
                            "field": field,
                            "match_text": _truncate(str(value), 200),
                        })

            except (json.JSONDecodeError, IOError):
                continue

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return results[:max_results]


def search_session_notes(query: str, max_results: int = 10) -> list:
    """Search across session notes markdown files.

    Args:
        query: Search string (case-insensitive).
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    results = []
    query_lower = query.lower()

    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        notes_dir = os.path.join(root, "notes")
        pattern = os.path.join(notes_dir, "session-*.md")
        note_files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        for note_file in note_files:
            if len(results) >= max_results:
                break
            try:
                with open(note_file, "r") as f:
                    for line_num, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            results.append({
                                "source": "notes",
                                "file": os.path.basename(note_file),
                                "line_number": line_num,
                                "match_text": _truncate(line.strip(), 200),
                            })
                            if len(results) >= max_results:
                                break
            except IOError:
                continue

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return results[:max_results]


# ── Layer 2: Git Memory ─────────────────────────────────────────────

def search_commit_messages(query: str, max_results: int = 10) -> list:
    """Search git commit messages across all branches.

    Args:
        query: Search string (case-insensitive grep).
        max_results: Maximum results to return.

    Returns:
        List of dicts: hash, date, branch, subject
    """
    results = []
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--grep", query, "-i",
             "--format=%H\t%ci\t%D\t%s",
             f"-{max_results}"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 3)
            branch_refs = parts[2] if len(parts) > 2 else ""
            results.append({
                "source": "git_commit",
                "hash": parts[0][:8],
                "full_hash": parts[0],
                "date": parts[1][:10] if len(parts) > 1 else "",
                "branch": _extract_branch(branch_refs),
                "subject": parts[3] if len(parts) > 3 else "",
            })
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return results[:max_results]


def search_file_content(query: str, paths: list = None,
                        max_results: int = 10) -> list:
    """Search file content using git grep (works across branches too).

    Args:
        query: Search string.
        paths: Optional list of path patterns to search.
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    results = []
    cmd = ["git", "grep", "-i", "-n", "--max-count", "3", query]
    if paths:
        cmd.append("--")
        cmd.extend(paths)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        for line in result.stdout.strip().splitlines():
            if not line or len(results) >= max_results:
                break
            # Format: file:line:content
            match = re.match(r"^(.+?):(\d+):(.*)$", line)
            if match:
                results.append({
                    "source": "file_content",
                    "file": match.group(1),
                    "line_number": int(match.group(2)),
                    "match_text": _truncate(match.group(3).strip(), 200),
                })
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return results[:max_results]


# ── Layer 3: GitHub Memory ──────────────────────────────────────────

def search_github_issues(query: str, repo: str = "packetqc/knowledge",
                         max_results: int = 10) -> list:
    """Search GitHub issues by title and body. Requires elevation.

    Args:
        query: Search string.
        repo: GitHub repo identifier.
        max_results: Maximum results to return.

    Returns:
        List of dicts: number, title, state, labels, url
    """
    gh = _get_gh_helper()
    if not gh:
        return []

    results = []
    try:
        # Use GitHub search API
        owner, name = repo.split("/")
        search_query = f"{query} repo:{repo} is:issue"
        response = gh._request(
            "GET",
            f"/search/issues?q={_url_encode(search_query)}&per_page={max_results}"
        )
        items = response.get("items", [])
        for item in items[:max_results]:
            labels = [l.get("name", "") for l in item.get("labels", [])]
            results.append({
                "source": "github_issue",
                "number": item.get("number"),
                "title": item.get("title", ""),
                "state": item.get("state", ""),
                "labels": labels,
                "url": item.get("html_url", ""),
                "created": item.get("created_at", "")[:10],
            })
    except Exception:
        pass

    return results[:max_results]


def search_github_issue_comments(query: str, repo: str = "packetqc/knowledge",
                                  issue_number: int = None,
                                  max_results: int = 10) -> list:
    """Search GitHub issue comments. Requires elevation.

    If issue_number provided, searches only that issue's comments.
    Otherwise searches across recent issues.

    Args:
        query: Search string.
        repo: GitHub repo identifier.
        issue_number: Optional specific issue to search.
        max_results: Maximum results to return.

    Returns:
        List of dicts: issue_number, comment_id, match_text, url
    """
    gh = _get_gh_helper()
    if not gh:
        return []

    results = []
    query_lower = query.lower()

    if issue_number:
        # Search specific issue
        try:
            comments = gh.issue_comments_list(repo, issue_number)
            for comment in comments:
                body = comment.get("body", "")
                if query_lower in body.lower():
                    results.append({
                        "source": "github_comment",
                        "issue_number": issue_number,
                        "comment_id": comment.get("id"),
                        "match_text": _truncate(
                            _find_matching_line(body, query_lower), 200
                        ),
                        "url": comment.get("html_url", ""),
                        "created": comment.get("created_at", "")[:10],
                    })
                    if len(results) >= max_results:
                        break
        except Exception:
            pass
    else:
        # Search via GitHub search API (comments)
        try:
            owner, name = repo.split("/")
            search_query = f"{query} repo:{repo} is:issue in:comments"
            response = gh._request(
                "GET",
                f"/search/issues?q={_url_encode(search_query)}&per_page={max_results}"
            )
            for item in response.get("items", [])[:max_results]:
                results.append({
                    "source": "github_comment_search",
                    "issue_number": item.get("number"),
                    "title": item.get("title", ""),
                    "state": item.get("state", ""),
                    "url": item.get("html_url", ""),
                    "created": item.get("created_at", "")[:10],
                })
        except Exception:
            pass

    return results[:max_results]


# ── Layer 4: Deep Memory ────────────────────────────────────────────

def search_methodology(query: str, max_results: int = 10) -> list:
    """Search methodology files for patterns and procedures.

    Args:
        query: Search string.
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    return search_file_content(
        query,
        paths=["methodology/"],
        max_results=max_results
    )


def search_publications(query: str, max_results: int = 10) -> list:
    """Search publication source files.

    Args:
        query: Search string.
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    return search_file_content(
        query,
        paths=["publications/"],
        max_results=max_results
    )


def search_patterns_lessons(query: str, max_results: int = 10) -> list:
    """Search patterns and lessons directories.

    Args:
        query: Search string.
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    return search_file_content(
        query,
        paths=["patterns/", "lessons/"],
        max_results=max_results
    )


def search_minds(query: str, max_results: int = 10) -> list:
    """Search harvested minds (distributed knowledge).

    Args:
        query: Search string.
        max_results: Maximum results to return.

    Returns:
        List of dicts: file, line_number, match_text
    """
    return search_file_content(
        query,
        paths=["minds/"],
        max_results=max_results
    )


# ── Full Recall (Progressive Search) ───────────────────────────────

def recall(query: str, repo: str = "packetqc/knowledge",
           layers: list = None, max_per_layer: int = 5) -> dict:
    """Execute a progressive deep memory search.

    Searches through layers in order, collecting results.
    Each layer is only searched if previous layers didn't find enough.

    Args:
        query: The search query.
        repo: GitHub repo for API searches.
        layers: Optional list of layer names to search.
                Default: ["near", "git", "github", "deep"]
        max_per_layer: Max results per search function.

    Returns:
        Dict with layer results and metadata:
            query, layers_searched, total_results, results (by layer)
    """
    if layers is None:
        layers = ["near", "git", "github", "deep"]

    all_results = {}
    total = 0

    # Layer 1: Near memory
    if "near" in layers:
        near = {}
        caches = search_session_caches(query, max_per_layer)
        if caches:
            near["caches"] = caches
            total += len(caches)
        notes = search_session_notes(query, max_per_layer)
        if notes:
            near["notes"] = notes
            total += len(notes)
        if near:
            all_results["near"] = near

    # Layer 2: Git memory
    if "git" in layers:
        git = {}
        commits = search_commit_messages(query, max_per_layer)
        if commits:
            git["commits"] = commits
            total += len(commits)
        if git:
            all_results["git"] = git

    # Layer 3: GitHub memory (requires elevation)
    if "github" in layers:
        github = {}
        issues = search_github_issues(query, repo, max_per_layer)
        if issues:
            github["issues"] = issues
            total += len(issues)
        comments = search_github_issue_comments(query, repo,
                                                 max_results=max_per_layer)
        if comments:
            github["comments"] = comments
            total += len(comments)
        if github:
            all_results["github"] = github

    # Layer 4: Deep memory
    if "deep" in layers:
        deep = {}
        methodology = search_methodology(query, max_per_layer)
        if methodology:
            deep["methodology"] = methodology
            total += len(methodology)
        pubs = search_publications(query, max_per_layer)
        if pubs:
            deep["publications"] = pubs
            total += len(pubs)
        patterns = search_patterns_lessons(query, max_per_layer)
        if patterns:
            deep["patterns_lessons"] = patterns
            total += len(patterns)
        minds = search_minds(query, max_per_layer)
        if minds:
            deep["minds"] = minds
            total += len(minds)
        if deep:
            all_results["deep"] = deep

    return {
        "query": query,
        "layers_searched": layers,
        "total_results": total,
        "results": all_results,
    }


def format_recall_report(recall_result: dict) -> str:
    """Format recall results as a readable report.

    Args:
        recall_result: Output from recall().

    Returns:
        Formatted string for display.
    """
    q = recall_result["query"]
    total = recall_result["total_results"]
    results = recall_result["results"]

    if total == 0:
        return f'No results found for "{q}" across {len(recall_result["layers_searched"])} layer(s).'

    lines = [f'Found {total} result(s) for "{q}":\n']

    layer_names = {
        "near": "Near Memory (caches + notes)",
        "git": "Git Memory (commits)",
        "github": "GitHub Memory (issues + comments)",
        "deep": "Deep Memory (methodology + publications + patterns + minds)",
    }

    for layer, layer_data in results.items():
        lines.append(f"### {layer_names.get(layer, layer)}")

        for category, items in layer_data.items():
            lines.append(f"  **{category}** ({len(items)} match{'es' if len(items) != 1 else ''}):")

            for item in items:
                source = item.get("source", "")
                if source == "cache":
                    lines.append(
                        f"    - #{item['issue_number']} "
                        f"({item['file']}) [{item['field']}]: "
                        f"{item['match_text']}"
                    )
                elif source == "notes":
                    lines.append(
                        f"    - {item['file']}:{item['line_number']}: "
                        f"{item['match_text']}"
                    )
                elif source == "git_commit":
                    lines.append(
                        f"    - {item['hash']} ({item['date']}) "
                        f"{item['subject']}"
                    )
                elif source in ("github_issue", "github_comment_search"):
                    labels_str = ", ".join(item.get("labels", []))
                    num = item.get("number") or item.get("issue_number", "?")
                    lines.append(
                        f"    - #{num} [{item.get('state', '')}] "
                        f"{item.get('title', '')} "
                        f"({labels_str})" if labels_str else
                        f"    - #{num} [{item.get('state', '')}] "
                        f"{item.get('title', '')}"
                    )
                elif source == "github_comment":
                    lines.append(
                        f"    - #{item['issue_number']} comment "
                        f"({item['created']}): {item['match_text']}"
                    )
                elif source == "file_content":
                    lines.append(
                        f"    - {item['file']}:{item['line_number']}: "
                        f"{item['match_text']}"
                    )

        lines.append("")

    # Check if any branch work was found → suggest recover
    git_results = results.get("git", {})
    if git_results.get("commits"):
        branch_commits = [c for c in git_results["commits"]
                          if "claude/" in c.get("branch", "")
                          or "backup-" in c.get("branch", "")]
        if branch_commits:
            lines.append(
                "**Stranded branch work detected** — use `recover` "
                "to cherry-pick/apply commits from claude/* or backup-* branches."
            )

    return "\n".join(lines)


# ── Helpers ─────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _extract_branch(ref_string: str) -> str:
    """Extract the most relevant branch name from git ref decoration."""
    if not ref_string:
        return ""
    # Look for claude/ or backup-* branches first
    for ref in ref_string.split(","):
        ref = ref.strip()
        if "claude/" in ref or "backup-" in ref:
            return ref.replace("origin/", "")
    # Return first non-HEAD ref
    for ref in ref_string.split(","):
        ref = ref.strip()
        if ref and "HEAD" not in ref:
            return ref.replace("origin/", "")
    return ""


def _find_matching_line(text: str, query_lower: str) -> str:
    """Find the first line containing the query in a multiline text."""
    for line in text.splitlines():
        if query_lower in line.lower():
            return line.strip()
    return text[:200]


def _url_encode(text: str) -> str:
    """Simple URL encoding for search queries."""
    import urllib.parse
    return urllib.parse.quote(text, safe="")
