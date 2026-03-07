"""Recover — branch-based work recovery from stranded claude/* branches.

Searches all claude/* branches for committed work that was never merged.
Shows unmerged commits, file diffs, PR status. Offers cherry-pick or
diff-apply recovery. Category: resiliency.

Previously named 'recall' — renamed in v57 to distinguish from the new
'recall' command (deep memory search).

Authors: Martin Paquet, Claude (Anthropic)
License: MIT
Knowledge version: v57
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional

from .helpers import _get_gh_helper


def _get_default_branch() -> str:
    """Detect the default branch name."""
    try:
        result = subprocess.run(
            ["git", "remote", "show", "origin"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.splitlines():
            if "HEAD branch" in line:
                return line.split(":")[-1].strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    return "main"


def _get_current_branch() -> str:
    """Get the current git branch name."""
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _list_recoverable_branches(remote: bool = True,
                                patterns: list = None) -> list:
    """List all recoverable branches (claude/* and backup-* by default).

    Args:
        remote: Whether to include remote branches.
        patterns: Branch name patterns to match. Default: ["claude/", "backup-"].

    Returns list of dicts with branch info:
        name, is_remote, last_commit_date, last_commit_msg, branch_type
    """
    if patterns is None:
        patterns = ["claude/", "backup-"]

    def _matches(name):
        return any(p in name for p in patterns)

    def _branch_type(name):
        if "backup-" in name:
            return "backup"
        if "claude/" in name:
            return "claude"
        return "other"

    branches = []

    if remote:
        try:
            result = subprocess.run(
                ["git", "branch", "-r", "--format",
                 "%(refname:short)\t%(committerdate:iso)\t%(subject)"],
                capture_output=True, text=True, timeout=15
            )
            for line in result.stdout.strip().splitlines():
                if not line:
                    continue
                parts = line.split("\t", 2)
                name = parts[0]
                if _matches(name):
                    # Strip origin/ prefix
                    short_name = name.replace("origin/", "")
                    branches.append({
                        "name": short_name,
                        "ref": name,
                        "is_remote": True,
                        "branch_type": _branch_type(short_name),
                        "last_commit_date": parts[1] if len(parts) > 1 else "",
                        "last_commit_msg": parts[2] if len(parts) > 2 else "",
                    })
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # Also check local branches
    try:
        result = subprocess.run(
            ["git", "branch", "--format",
             "%(refname:short)\t%(committerdate:iso)\t%(subject)"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 2)
            name = parts[0]
            if _matches(name):
                # Skip if already found as remote
                if not any(b["name"] == name for b in branches):
                    branches.append({
                        "name": name,
                        "ref": name,
                        "is_remote": False,
                        "branch_type": _branch_type(name),
                        "last_commit_date": parts[1] if len(parts) > 1 else "",
                        "last_commit_msg": parts[2] if len(parts) > 2 else "",
                    })
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return branches


def _get_unmerged_commits(branch_ref: str, default_branch: str) -> list:
    """Get commits on branch that are not in default branch.

    Returns list of dicts: hash, date, subject
    """
    commits = []
    try:
        result = subprocess.run(
            ["git", "log", f"{default_branch}..{branch_ref}",
             "--format=%H\t%ci\t%s", "--no-merges"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 2)
            commits.append({
                "hash": parts[0][:8],
                "full_hash": parts[0],
                "date": parts[1] if len(parts) > 1 else "",
                "subject": parts[2] if len(parts) > 2 else "",
            })
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    return commits


def _get_changed_files(branch_ref: str, default_branch: str) -> list:
    """Get files changed on branch vs default branch."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status",
             f"{default_branch}...{branch_ref}"],
            capture_output=True, text=True, timeout=15
        )
        files = []
        for line in result.stdout.strip().splitlines():
            if line:
                parts = line.split("\t", 1)
                files.append({
                    "status": parts[0],
                    "path": parts[1] if len(parts) > 1 else "",
                })
        return files
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


def _check_pr_status(repo: str, branch_name: str) -> Optional[dict]:
    """Check if a PR exists for this branch. Requires elevation."""
    gh = _get_gh_helper()
    if not gh:
        return None
    try:
        prs = gh.pr_list(repo, head=branch_name, state="all")
        if prs:
            pr = prs[0]
            return {
                "number": pr.get("number"),
                "state": pr.get("state"),
                "merged": pr.get("merged_at") is not None,
                "url": pr.get("html_url", ""),
            }
    except Exception:
        pass
    return None


def scan_stranded_branches(repo: str = "packetqc/knowledge",
                           fetch_first: bool = True,
                           patterns: list = None) -> list:
    """Scan claude/* and backup-* branches for stranded/recoverable work.

    Returns list of branch reports, each containing:
        name, commits (unmerged), files (changed), pr_status, is_current,
        branch_type ('claude' or 'backup')

    Args:
        repo: GitHub repo identifier for PR status checks.
        fetch_first: Whether to fetch remote refs before scanning.
        patterns: Branch name patterns to match. Default: ["claude/", "backup-"].

    Returns:
        List of branch report dicts, sorted by most recent first.
    """
    default_branch = _get_default_branch()
    current_branch = _get_current_branch()

    if fetch_first:
        try:
            subprocess.run(
                ["git", "fetch", "--all", "--prune"],
                capture_output=True, timeout=30
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    branches = _list_recoverable_branches(patterns=patterns)
    reports = []

    for branch in branches:
        ref = branch["ref"]
        if branch["is_remote"]:
            ref = f"origin/{branch['name']}"

        commits = _get_unmerged_commits(ref, default_branch)
        if not commits:
            continue  # Skip branches with no unmerged work

        files = _get_changed_files(ref, default_branch)
        pr_status = _check_pr_status(repo, branch["name"])

        reports.append({
            "name": branch["name"],
            "ref": ref,
            "is_remote": branch["is_remote"],
            "is_current": branch["name"] == current_branch,
            "branch_type": branch.get("branch_type", "claude"),
            "last_commit_date": branch["last_commit_date"],
            "commits": commits,
            "files": files,
            "pr_status": pr_status,
            "commit_count": len(commits),
            "file_count": len(files),
        })

    # Sort by last commit date (most recent first)
    reports.sort(key=lambda r: r["last_commit_date"], reverse=True)
    return reports


def cherry_pick_commits(commit_hashes: list) -> dict:
    """Cherry-pick specific commits to the current branch.

    Args:
        commit_hashes: List of full commit hashes to cherry-pick.

    Returns:
        Dict with results: succeeded (list), failed (list), errors (list).
    """
    succeeded = []
    failed = []
    errors = []

    for h in commit_hashes:
        try:
            result = subprocess.run(
                ["git", "cherry-pick", h, "--no-edit"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                succeeded.append(h[:8])
            else:
                # Abort the failed cherry-pick
                subprocess.run(
                    ["git", "cherry-pick", "--abort"],
                    capture_output=True, timeout=10
                )
                failed.append(h[:8])
                errors.append(result.stderr.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            failed.append(h[:8])
            errors.append(str(e))

    return {"succeeded": succeeded, "failed": failed, "errors": errors}


def apply_diff_from_branch(branch_ref: str, default_branch: str) -> dict:
    """Apply the diff from a branch as a patch (alternative to cherry-pick).

    Args:
        branch_ref: The branch ref to get the diff from.
        default_branch: The base branch to diff against.

    Returns:
        Dict with success bool and message.
    """
    try:
        # Generate patch
        diff_result = subprocess.run(
            ["git", "diff", f"{default_branch}...{branch_ref}"],
            capture_output=True, text=True, timeout=30
        )
        if not diff_result.stdout.strip():
            return {"success": False, "message": "No diff to apply"}

        # Apply patch
        apply_result = subprocess.run(
            ["git", "apply", "--3way"],
            input=diff_result.stdout,
            capture_output=True, text=True, timeout=30
        )
        if apply_result.returncode == 0:
            return {"success": True, "message": "Diff applied successfully"}
        else:
            return {"success": False, "message": apply_result.stderr.strip()}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        return {"success": False, "message": str(e)}


def format_recovery_report(reports: list) -> str:
    """Format the scan results as a readable report.

    Args:
        reports: List of branch reports from scan_stranded_branches().

    Returns:
        Formatted string for display.
    """
    if not reports:
        return "No stranded work found on any claude/* or backup-* branch."

    lines = [f"Found {len(reports)} branch(es) with unmerged work:\n"]

    for i, r in enumerate(reports, 1):
        current = " (CURRENT)" if r["is_current"] else ""
        btype = r.get("branch_type", "claude")
        type_badge = " [BACKUP]" if btype == "backup" else ""
        lines.append(f"### {i}. `{r['name']}`{current}{type_badge}")
        lines.append(f"   Commits: {r['commit_count']} | "
                      f"Files: {r['file_count']} | "
                      f"Last: {r['last_commit_date'][:10] if r['last_commit_date'] else 'unknown'}")

        # PR status
        pr = r.get("pr_status")
        if pr:
            state = "merged" if pr["merged"] else pr["state"]
            lines.append(f"   PR: #{pr['number']} ({state}) — {pr['url']}")
        else:
            lines.append("   PR: none")

        # Recent commits (max 5)
        lines.append("   Recent commits:")
        for c in r["commits"][:5]:
            lines.append(f"     {c['hash']} {c['subject']}")
        if len(r["commits"]) > 5:
            lines.append(f"     ... and {len(r['commits']) - 5} more")

        # Changed files (max 10)
        lines.append("   Changed files:")
        for f in r["files"][:10]:
            lines.append(f"     {f['status']} {f['path']}")
        if len(r["files"]) > 10:
            lines.append(f"     ... and {len(r['files']) - 10} more")

        lines.append("")

    lines.append("**Recovery options**: cherry-pick specific commits, "
                 "or apply branch diff as patch.")
    return "\n".join(lines)
