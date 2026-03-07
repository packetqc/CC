#!/usr/bin/env python3
"""
Test routine — validates knowledge system session infrastructure.

Checks:
  1. gh_helper.py is importable and has core functions
  2. session_agent.py is importable and cache functions work
  3. notes/ directory exists and is writable
  4. CLAUDE.md is present and contains knowledge version
  5. scripts/ core tools are present

Usage:
  python3 scripts/test_routine.py
"""

import os
import sys
import importlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        msg = f"  ❌ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def test_gh_helper_importable():
    """gh_helper.py imports and GitHubHelper has core methods."""
    print("\n1. gh_helper.py (GitHubHelper class)")
    try:
        mod = importlib.import_module("scripts.gh_helper")
        check("importable", True)
        check("has GitHubHelper class", hasattr(mod, "GitHubHelper"))
        cls = getattr(mod, "GitHubHelper", None)
        if cls:
            for method in ["issue_create", "pr_create", "pr_merge", "issue_comment_post"]:
                check(f"has {method}", hasattr(cls, method))
    except ImportError as e:
        check("importable", False, str(e))


def test_session_agent_importable():
    """session_agent.py imports and cache functions work."""
    print("\n2. session_agent.py")
    try:
        mod = importlib.import_module("scripts.session_agent")
        check("importable", True)
        for fn in ["write_runtime_cache", "read_runtime_cache", "update_session_data"]:
            check(f"has {fn}", hasattr(mod, fn))
    except ImportError as e:
        check("importable", False, str(e))


def test_notes_directory():
    """notes/ directory exists and is writable."""
    print("\n3. notes/ directory")
    notes = os.path.join(REPO_ROOT, "notes")
    check("exists", os.path.isdir(notes))
    check("writable", os.access(notes, os.W_OK))


def test_claude_md():
    """CLAUDE.md is present and contains knowledge version."""
    print("\n4. CLAUDE.md")
    path = os.path.join(REPO_ROOT, "CLAUDE.md")
    check("exists", os.path.isfile(path))
    if os.path.isfile(path):
        content = open(path, "r").read()
        check("has knowledge version", "knowledge-version:" in content or "Current version:" in content)
        check("non-trivial (>500 lines)", content.count("\n") > 500)


def test_core_scripts():
    """Core scripts are present."""
    print("\n5. Core scripts")
    for name in ["gh_helper.py", "session_agent.py", "sync_roadmap.py"]:
        path = os.path.join(REPO_ROOT, "scripts", name)
        check(f"{name} exists", os.path.isfile(path))


def main():
    print("=" * 50)
    print("  Knowledge System — Test Routine")
    print("=" * 50)

    test_gh_helper_importable()
    test_session_agent_importable()
    test_notes_directory()
    test_claude_md()
    test_core_scripts()

    print("\n" + "=" * 50)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed", end="")
    if FAIL:
        print(f", {FAIL} failed")
    else:
        print(" — all clear")
    print("=" * 50)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
