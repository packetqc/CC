#!/usr/bin/env python3
"""
compile_tasks.py — Parse session runtime caches and generate docs/data/tasks.json

Scans all notes/session-runtime-*.json files for task_workflow data,
enriches with validation results and unit test data, and writes a
structured JSON for the Tasks Workflow Viewer web interface (I3).

Usage:
    python3 scripts/compile_tasks.py
    python3 scripts/compile_tasks.py --output docs/data/tasks.json
"""

import os
import json
import glob
import sys
from datetime import datetime


def find_project_root():
    """Find the project root by looking for CLAUDE.md."""
    d = os.path.dirname(os.path.abspath(__file__))
    while d != '/':
        if os.path.exists(os.path.join(d, 'CLAUDE.md')):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def load_runtime_caches(notes_dir):
    """Load all session runtime cache files.

    Returns:
        List of (filename, cache_data) tuples.
    """
    pattern = os.path.join(notes_dir, "session-runtime-*.json")
    caches = []
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            caches.append((os.path.basename(path), data))
        except (json.JSONDecodeError, OSError):
            continue
    return caches


def extract_task_from_cache(filename, cache):
    """Extract task workflow data from a session runtime cache.

    Args:
        filename: Cache filename for reference.
        cache: Parsed cache dict.

    Returns:
        Task dict if task_workflow exists, None otherwise.
    """
    sd = cache.get("session_data", {})
    workflow = sd.get("task_workflow")
    if not workflow:
        return None

    # Extract session metadata
    session_id = cache.get("session_id", "")
    issue_number = workflow.get("issue_number") or cache.get("issue_number", 0)
    issue_title = workflow.get("title") or cache.get("issue_title", "")
    branch = cache.get("branch", "")
    repo = cache.get("repo", "")
    created = cache.get("created", "")
    updated = cache.get("updated", "")

    # Validation results
    validation_results = workflow.get("validation_results", {})
    validation_skipped = workflow.get("validation_skipped_entirely", False)

    # Unit tests
    unit_tests = workflow.get("unit_tests", [])

    # Stage history
    stage_history = workflow.get("stage_history", [])
    step_history = workflow.get("step_history", [])

    # Compute stage progression
    stages_visited = []
    seen = set()
    for entry in stage_history:
        s = entry.get("stage")
        if s and s not in seen:
            stages_visited.append(s)
            seen.add(s)

    # Compute validation summary per stage
    validation_summary = {}
    for stage_name, stage_val in validation_results.items():
        checks = stage_val.get("checks", [])
        validation_summary[stage_name] = {
            "status": stage_val.get("overall_status", "pending"),
            "skipped": stage_val.get("skipped", False),
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c.get("result") == "passed"),
            "failed": sum(1 for c in checks if c.get("result") == "failed"),
            "validated_at": stage_val.get("validated_at"),
        }

    # Compute unit test summary
    test_summary = {
        "total": len(unit_tests),
        "passed": sum(1 for t in unit_tests if t.get("result") == "passed"),
        "failed": sum(1 for t in unit_tests if t.get("result") == "failed"),
        "pending": sum(1 for t in unit_tests if t.get("result") is None),
        "by_source": {},
    }
    for t in unit_tests:
        src = t.get("source", "unknown")
        test_summary["by_source"].setdefault(src, 0)
        test_summary["by_source"][src] += 1

    # Compute timing
    started_at = workflow.get("started_at")
    updated_at = workflow.get("updated_at")

    task = {
        "id": f"task-{issue_number}" if issue_number else f"task-{session_id}",
        "issue_number": issue_number,
        "title": issue_title,
        "description": workflow.get("description", ""),
        "branch": branch,
        "repo": repo,
        "session_id": session_id,
        "source_file": filename,
        "current_stage": workflow.get("current_stage", "unknown"),
        "current_stage_index": workflow.get("current_stage_index", 0),
        "current_step": workflow.get("current_step"),
        "project": workflow.get("project"),
        "stages_visited": stages_visited,
        "stage_count": len(stages_visited),
        "total_transitions": len(stage_history),
        "started_at": started_at,
        "updated_at": updated_at,
        "modifications_occurred": workflow.get("modifications_occurred", False),
        "validation_skipped_entirely": validation_skipped,
        "validation_summary": validation_summary,
        "unit_test_summary": test_summary,
        "stage_history": stage_history,
        "step_history": step_history,
        "validation_results": validation_results,
        "unit_tests": unit_tests,
    }

    return task


def deduplicate_tasks(tasks):
    """Deduplicate tasks by issue_number, keeping the most recent.

    Tasks with issue_number=0 are kept as-is (session-only tasks).
    """
    by_issue = {}
    no_issue = []

    for task in tasks:
        issue = task.get("issue_number", 0)
        if not issue:
            no_issue.append(task)
            continue
        existing = by_issue.get(issue)
        if not existing:
            by_issue[issue] = task
        else:
            # Keep the one with the most recent updated_at
            if (task.get("updated_at") or "") > (existing.get("updated_at") or ""):
                by_issue[issue] = task

    return list(by_issue.values()) + no_issue


def compile_tasks(notes_dir, output_path):
    """Main compilation: scan caches → extract tasks → write JSON.

    Args:
        notes_dir: Path to notes/ directory.
        output_path: Path to write tasks.json.

    Returns:
        Number of tasks compiled.
    """
    caches = load_runtime_caches(notes_dir)

    tasks = []
    for filename, cache in caches:
        task = extract_task_from_cache(filename, cache)
        if task:
            tasks.append(task)

    # Deduplicate by issue number
    tasks = deduplicate_tasks(tasks)

    # Sort by updated_at descending (most recent first)
    tasks.sort(key=lambda t: t.get("updated_at") or "", reverse=True)

    # Compute meta
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "generated_at": now,
        "total_tasks": len(tasks),
        "with_issue": sum(1 for t in tasks if t.get("issue_number")),
        "with_validation": sum(1 for t in tasks if t.get("validation_summary")),
        "stages": [
            "initial", "plan", "analyze", "implement",
            "validation", "approval", "documentation", "completion",
        ],
        "sources": [
            "notes/session-runtime-*.json",
        ],
    }

    output = {
        "meta": meta,
        "tasks": tasks,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    return len(tasks)


def main():
    root = find_project_root()
    notes_dir = os.path.join(root, "notes")

    output = os.path.join(root, "docs", "data", "tasks.json")
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]

    count = compile_tasks(notes_dir, output)
    print(f"Compiled {count} tasks → {output}")


if __name__ == "__main__":
    main()
