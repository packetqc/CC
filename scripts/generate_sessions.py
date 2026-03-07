#!/usr/bin/env python3
"""
Generate sessions.json from three data sources:
1. GitHub PRs grouped by claude/* branches (covers ALL sessions)
2. GitHub SESSION-labeled issues (enriched data for v51+ sessions)
3. notes/session-*.md files (extra context when available)

Usage:
    python3 scripts/generate_sessions.py
    python3 scripts/generate_sessions.py --output docs/data/sessions.json
"""

import json
import os
import re
import sys
import glob
from datetime import datetime, timezone
from collections import defaultdict

# Try to use gh_helper if available
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gh_helper import GitHubHelper
    HAS_GH_HELPER = True
except ImportError:
    HAS_GH_HELPER = False

# Import engineering taxonomy from session_agent
try:
    from session_agent import (
        REQUEST_TYPE_KEYWORDS,
        ENGINEERING_STAGES,
        ENGINEERING_CROSS_CUTTING,
        detect_request_type,
    )
    HAS_TAXONOMY = True
except ImportError:
    HAS_TAXONOMY = False

# Request type → display emoji mapping (11 types from engineering taxonomy)
REQUEST_TYPE_EMOJI = {
    "fix":            "🔧",
    "feature":        "🚀",
    "investigation":  "🔍",
    "enhancement":    "🔄",
    "testing":        "🧪",
    "validation":     "✅",
    "documentation":  "📝",
    "deployment":     "📦",
    "conception":     "💡",
    "review":         "👁️",
    "chore":          "⚙️",
}

# Fallback type detection when session_agent is not importable
FALLBACK_TYPE_KEYWORDS = {
    "fix":           ["fix:", "fix(", "bugfix", "bug ", "error ", "crash", "hotfix", "broken"],
    "feature":       ["feat:", "feat(", "feature", "implement", "create", "develop", "add ", "new ", "build", "enrich", "scaffold"],
    "investigation": ["investigate", "diagnose", "debug", "root cause", "troubleshoot", "probe"],
    "enhancement":   ["refactor", "optimize", "simplify", "restructure", "improve", "upgrade", "modernize", "clean", "performance"],
    "testing":       ["test:", "test(", "testing", "qa ", "unit test", "coverage", "regression"],
    "validation":    ["validate", "validation", "acceptance", "demo", "sign off", "approve"],
    "documentation": ["doc:", "docs:", "publication", "doc review", "documentation", "methodology", "readme", "changelog"],
    "deployment":    ["deploy", "release", "ship", "publish", "deliver", "ci/cd", "pipeline"],
    "conception":    ["design", "architect", "prototype", "wireframe", "spike", "rfc", "proposal", "plan "],
    "review":        ["review", "audit", "assess", "evaluate", "inspect", "peer review"],
    "chore":         ["chore:", "chore(", "housekeeping", "cleanup", "maintenance", "routine", "config", "setup", "infrastructure", "sync ", "regenerat", "merge"],
}

# Legacy type mapping — map old 5-type emoji names to new taxonomy
LEGACY_TYPE_MAP = {
    "🚀 Feature":       "feature",
    "🔍 Diagnostic":    "investigation",
    "📝 Documentation": "documentation",
    "⚙️ Collateral":    "chore",
    "💡 Conception":    "conception",
}

REPO = "packetqc/knowledge"
OWNER = "packetqc"
REPO_NAME = "knowledge"


def detect_session_type_from_text(text):
    """Detect session request type from text using the engineering taxonomy.

    Uses REQUEST_TYPE_KEYWORDS from session_agent.py when available,
    falls back to FALLBACK_TYPE_KEYWORDS otherwise.

    Returns: (type_key, emoji_label) tuple, e.g. ("feature", "🚀 Feature")
    """
    if not text:
        return "feature", f"{REQUEST_TYPE_EMOJI['feature']} Feature"

    text_lower = text.lower()

    # Use session_agent's detect_request_type if available
    if HAS_TAXONOMY:
        result = detect_request_type(text)
        if result:
            emoji = REQUEST_TYPE_EMOJI.get(result, "🚀")
            return result, f"{emoji} {result.capitalize()}"

    # Fallback: score-based detection with local keywords
    scores = {}
    keywords_source = FALLBACK_TYPE_KEYWORDS
    for rtype, keywords in keywords_source.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[rtype] = count

    if scores:
        best = max(scores, key=scores.get)
        emoji = REQUEST_TYPE_EMOJI.get(best, "🚀")
        return best, f"{emoji} {best.capitalize()}"

    return "feature", f"{REQUEST_TYPE_EMOJI['feature']} Feature"


def detect_pr_sub_type(title):
    """Detect per-PR sub-type from title using the new taxonomy.

    Maps PR titles to Conventional Commit types aligned with the
    engineering taxonomy: fix, feat, test, doc, refactor, chore,
    plus the new types: validation, investigation, deployment, review.

    Returns: sub_type string (e.g., "feat", "fix", "doc")
    """
    title_lower = (title or "").lower()

    # Conventional Commit prefix detection (highest priority)
    prefix_map = {
        "fix:": "fix", "fix(": "fix",
        "feat:": "feat", "feat(": "feat",
        "test:": "test", "test(": "test",
        "docs:": "doc", "doc:": "doc",
        "refactor:": "refactor", "refactor(": "refactor",
        "perf:": "refactor",
        "chore:": "chore", "chore(": "chore",
        "build:": "chore", "ci:": "chore",
        "style:": "chore",
    }
    for prefix, sub in prefix_map.items():
        if title_lower.startswith(prefix):
            return sub

    # Keyword-based detection (lower priority)
    keyword_map = [
        (["bugfix", "hotfix", "fix ", "broken", "error ", "crash"], "fix"),
        (["feature", "implement", "create", "add ", "enrich", "new ", "build", "scaffold"], "feat"),
        (["test", "qa ", "testing", "coverage", "regression"], "test"),
        (["publication", "documentation", "methodology", "readme", "doc review"], "doc"),
        (["refactor", "optimize", "simplify", "restructure", "clean", "improve", "upgrade"], "refactor"),
        (["validate", "validation", "acceptance", "demo", "approve"], "validation"),
        (["investigate", "diagnose", "debug", "root cause", "troubleshoot"], "investigation"),
        (["deploy", "release", "ship", "publish", "deliver"], "deployment"),
        (["review", "audit", "assess", "evaluate", "inspect"], "review"),
        (["sync ", "regenerat", "merge", "cleanup", "maintenance", "config", "setup"], "chore"),
    ]
    for keywords, sub in keyword_map:
        if any(kw in title_lower for kw in keywords):
            return sub

    return "feat"  # default


def infer_engineering_stage(session):
    """Infer the dominant engineering stage for a session.

    Uses the distribution of PR sub_types, issue labels, and session
    type to determine which engineering stage the session primarily
    operated in.

    Returns: stage string from ENGINEERING_STAGES (e.g., "implementation")
    """
    # Count sub_types across all PRs
    sub_counts = defaultdict(int)
    for pr in session.get("prs", []):
        sub = pr.get("sub_type", "feat")
        sub_counts[sub] += 1

    # Map sub_types to stages
    sub_to_stage = {
        "feat": "implementation",
        "fix": "implementation",
        "test": "testing",
        "validation": "validation",
        "doc": "implementation",  # docs written during implementation
        "refactor": "improvement",
        "chore": "operations",
        "investigation": "analysis",
        "deployment": "deployment",
        "review": "review",
    }

    # Score stages
    stage_scores = defaultdict(int)
    for sub, count in sub_counts.items():
        stage = sub_to_stage.get(sub, "implementation")
        stage_scores[stage] += count

    # Session type can influence stage
    sess_type = session.get("request_type", "")
    type_to_stage = {
        "fix": "implementation",
        "feature": "implementation",
        "investigation": "analysis",
        "enhancement": "improvement",
        "testing": "testing",
        "validation": "validation",
        "documentation": "implementation",
        "deployment": "deployment",
        "conception": "design",
        "review": "review",
        "chore": "operations",
    }
    if sess_type in type_to_stage:
        stage_scores[type_to_stage[sess_type]] += 2  # weight session type

    if stage_scores:
        return max(stage_scores, key=stage_scores.get)

    return "implementation"  # default


def github_api(endpoint, token=None):
    """Make a GitHub API request."""
    import urllib.request
    url = f"https://api.github.com{endpoint}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  [warn] API call failed: {endpoint} — {e}", file=sys.stderr)
        return None


def fetch_all_prs(token=None):
    """Fetch all closed+merged PRs from the repo."""
    all_prs = []
    page = 1
    while True:
        data = github_api(
            f"/repos/{REPO}/pulls?state=closed&per_page=100&page={page}&sort=created&direction=desc",
            token
        )
        if not data:
            break
        all_prs.extend(data)
        if len(data) < 100:
            break
        page += 1
    print(f"  Fetched {len(all_prs)} PRs from GitHub API")
    return all_prs


def fetch_session_issues(token=None):
    """Fetch all SESSION-labeled issues."""
    issues = github_api(
        f"/repos/{REPO}/issues?labels=SESSION&state=all&per_page=100&sort=created&direction=desc",
        token
    )
    if issues:
        print(f"  Fetched {len(issues)} SESSION issues from GitHub API")
    return issues or []


def fetch_issue_detail(issue_number, token=None):
    """Fetch a single issue's details (title, labels, state).

    Returns None for pull requests (detected via pull_request key).
    """
    data = github_api(f"/repos/{REPO}/issues/{issue_number}", token)
    if data:
        # Skip pull requests — they have a pull_request key
        if data.get("pull_request"):
            return None
        return {
            "number": data["number"],
            "title": data.get("title", ""),
            "state": data.get("state", ""),
            "labels": [l.get("name", "") for l in data.get("labels", [])],
            "created_at": data.get("created_at"),
        }
    return None


def fetch_issue_comments(issue_number, token=None):
    """Fetch all comments for an issue and parse them into structured data."""
    data = github_api(
        f"/repos/{REPO}/issues/{issue_number}/comments?per_page=100",
        token
    )
    if not data:
        return []

    comments = []
    for c in data:
        body = c.get("body", "") or ""
        # Parse comment type from body pattern
        # Legacy: 🧑 = user, 🤖 = bot
        # v55+: vicky.png = user (Martin), vicky-sunglasses.png = bot (Claude)
        ctype = "other"
        status = None
        step_name = ""
        if "\U0001f9d1" in body or "🧑" in body or "vicky.png" in body:
            ctype = "user"
            # Exclude vicky-sunglasses (Claude) from user match
            if "vicky-sunglasses" in body:
                ctype = "bot"
        elif "\U0001f916" in body or "🤖" in body or "vicky-sunglasses" in body:
            ctype = "bot"
        if ctype == "bot":
            if "⏳" in body:
                status = "in_progress"
            elif "✅" in body:
                status = "completed"

        # Extract step name from "## 🤖/Claude — ⏳ Step name" (legacy + v55 avatar format)
        m = re.search(r"##\s*(?:🤖|<img[^>]*>)\s*Claude\s*[—–-]\s*(?:⏳|✅)\s*(.+?)(?:\n|$)", body)
        if m:
            step_name = m.group(1).strip()

        # Body preview — first meaningful text line (skip headers, HTML, empty lines)
        preview = ""
        for line in body.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("*Ce commentaire"):
                continue
            # Strip blockquote prefixes
            while line.startswith(">"):
                line = line[1:].strip()
            if not line:
                continue
            # Strip HTML tags
            cleaned = re.sub(r"<[^>]+>", "", line).strip()
            if not cleaned:
                continue
            # Strip markdown bold/links for cleaner preview
            cleaned = re.sub(r"\*\*", "", cleaned)
            cleaned = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cleaned)
            preview = cleaned[:200]
            break

        # Body lines for expandable content (skip avatar headers, keep meaningful lines)
        body_lines = []
        for line in body.split("\n"):
            stripped = line.strip()
            # Skip empty lines, avatar img headers, and auto-generated disclaimers
            if not stripped:
                continue
            if stripped.startswith("## <img") or stripped.startswith("## 🤖") or stripped.startswith("## 🧑"):
                continue
            if stripped.startswith("*Ce commentaire"):
                continue
            # Strip markdown blockquote prefix
            while stripped.startswith(">"):
                stripped = stripped[1:].strip()
            if not stripped:
                continue
            # Strip HTML tags (raw HTML in comments)
            stripped = re.sub(r"<[^>]+>", "", stripped).strip()
            if not stripped:
                continue
            body_lines.append(stripped)
        # Cap at 20 lines to keep sessions.json manageable
        if len(body_lines) > 20:
            body_lines = body_lines[:20] + ["..."]

        comments.append({
            "author": c.get("user", {}).get("login", ""),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "type": ctype,
            "status": status,
            "step_name": step_name,
            "preview": preview,
            "body_lines": body_lines,
        })
    return comments


def fetch_pr_details(pr_number, token=None):
    """Fetch individual PR to get additions/deletions/changed_files/commits."""
    data = github_api(f"/repos/{REPO}/pulls/{pr_number}", token)
    if data:
        return {
            "additions": data.get("additions", 0),
            "deletions": data.get("deletions", 0),
            "changed_files": data.get("changed_files", 0),
            "commits": data.get("commits", 0),
        }
    return None


def enrich_prs_with_stats(prs, token=None):
    """Enrich PR list with additions/deletions/changed_files/commits from individual endpoints."""
    enriched = 0
    total = len([p for p in prs if p.get("head", {}).get("ref", "").startswith("claude/")])
    print(f"  Enriching {total} claude/* PRs with velocity stats...")
    for pr in prs:
        branch = pr.get("head", {}).get("ref", "")
        if not branch.startswith("claude/"):
            continue
        details = fetch_pr_details(pr["number"], token)
        if details:
            pr["additions"] = details["additions"]
            pr["deletions"] = details["deletions"]
            pr["changed_files"] = details["changed_files"]
            pr["commits"] = details["commits"]
            enriched += 1
            if enriched % 50 == 0:
                print(f"    ... {enriched}/{total} enriched")
    print(f"  → {enriched}/{total} PRs enriched with velocity stats")
    return prs


def group_prs_by_branch(prs):
    """Group PRs by their claude/* source branch and date."""
    sessions = defaultdict(lambda: {"prs": [], "dates": set(), "branch": None})
    for pr in prs:
        branch = pr.get("head", {}).get("ref", "")
        if not branch.startswith("claude/"):
            continue
        date = pr["created_at"][:10]
        key = f"{date}_{branch}"
        sessions[key]["prs"].append({
            "number": pr["number"],
            "title": pr.get("title", ""),
            "merged": pr.get("merged_at") is not None,
            "created_at": pr["created_at"],
            "merged_at": pr.get("merged_at"),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
            "commits": pr.get("commits", 0),
        })
        sessions[key]["dates"].add(date)
        sessions[key]["branch"] = branch
    return sessions


def parse_notes_file(filepath):
    """Parse a notes/session-*.md file for metadata."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    result = {
        "source_file": os.path.basename(filepath),
        "title": None,
        "branch": None,
        "type": None,
        "summary": None,
        "lessons": [],
        "issues": [],
    }

    # Extract title from first heading
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if m:
        result["title"] = m.group(1).strip()

    # Extract branch — supports both inline (Branch: `name`) and heading (## Branch\nname) formats
    m = re.search(r"[Bb]ranch:\s*`?([^\s`]+)`?", content)
    if not m:
        # Fallback: ## Branch heading followed by branch name on next line
        m = re.search(r"^##\s*[Bb]ranch\s*\n\s*`?([^\s`]+)`?", content, re.MULTILINE)
    if m:
        result["branch"] = m.group(1).strip()

    # Detect type from content using the engineering taxonomy (11 types)
    request_type, type_label = detect_session_type_from_text(content)
    result["type"] = type_label
    result["request_type"] = request_type

    # Extract summary (first paragraph after heading)
    lines = content.split("\n")
    summary_lines = []
    past_heading = False
    for line in lines:
        if line.startswith("# "):
            past_heading = True
            continue
        if past_heading:
            if line.strip() == "":
                if summary_lines:
                    break
                continue
            if line.startswith("#"):
                break
            summary_lines.append(line.strip())
    if summary_lines:
        result["summary"] = " ".join(summary_lines)[:300]

    # Extract lessons
    lesson_section = False
    for line in lines:
        if re.match(r"^##.*[Ll]esson|^##.*[Dd]ecision|^##.*[Pp]itfall|^##.*[Rr]etrospective", line):
            lesson_section = True
            continue
        if lesson_section:
            if line.startswith("## "):
                lesson_section = False
                continue
            m = re.match(r"^\s*[-*]\s+(.+)", line)
            if m:
                result["lessons"].append(m.group(1).strip())

    # Extract issue references
    for m in re.finditer(r"#(\d+)", content):
        num = int(m.group(1))
        if 1 < num < 10000:  # reasonable issue number range
            result["issues"].append(num)
    result["issues"] = sorted(set(result["issues"]))

    return result


def parse_all_notes(notes_dir):
    """Parse all session notes files."""
    notes = {}
    pattern = os.path.join(notes_dir, "session-*.md")
    files = sorted(glob.glob(pattern))
    print(f"  Found {len(files)} session notes files")
    for f in files:
        basename = os.path.basename(f)
        # Extract date from filename: session-YYYY-MM-DD[-suffix].md
        m = re.match(r"session-(\d{4}-\d{2}-\d{2})(.*)\.md", basename)
        if m:
            date = m.group(1)
            suffix = m.group(2)
            note_id = f"session-{date}{suffix}"
            parsed = parse_notes_file(f)
            if parsed:
                parsed["id"] = note_id
                parsed["date"] = date
                notes[note_id] = parsed
    return notes


def parse_runtime_caches(notes_dir):
    """Parse all session runtime cache files (4th data source).

    Runtime cache files (notes/session-runtime-*.json) contain the
    definitive branch ↔ issue_number mapping written by session_agent.py
    at session creation time. This is more reliable than checking if the
    branch name appears in the issue body.

    Returns: dict mapping branch → cache data (issue_number, issue_title, etc.)
    """
    caches = {}
    pattern = os.path.join(notes_dir, "session-runtime-*.json")
    files = sorted(glob.glob(pattern))
    print(f"  Found {len(files)} runtime cache files")
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            branch = data.get("branch", "")
            if branch:
                caches[branch] = {
                    "issue_number": data.get("issue_number"),
                    "issue_title": data.get("issue_title", ""),
                    "request_description": data.get("request_description", ""),
                    "session_id": data.get("session_id", ""),
                    "created": data.get("created", ""),
                    "source_file": os.path.basename(f),
                }
        except (json.JSONDecodeError, OSError):
            continue
    return caches


def merge_sources(pr_sessions, session_issues, notes, token=None, caches=None):
    """Merge all data sources into unified session list.

    Matching strategy (priority order for SESSION issue matching):
    1. Runtime cache: branch → issue_number (definitive, written at session start)
    2. Issue body: branch name appears in issue body text
    - Notes → PR sessions: match by BRANCH only (exact match). Never match by date alone.
    - Unmatched notes become standalone sessions.
    - Unmatched SESSION issues become standalone sessions.
    """
    if caches is None:
        caches = {}

    sessions = []
    seen_branches = set()
    used_notes = set()       # Track which notes were consumed
    used_issues = set()      # Track which issues were consumed

    # Build branch→issue index from runtime caches (most reliable source)
    cache_branch_to_issue = {}
    for branch, cache_data in caches.items():
        issue_num = cache_data.get("issue_number")
        if issue_num:
            cache_branch_to_issue[branch] = issue_num

    # Build issue number→issue object index for fast lookup
    issue_by_number = {}
    for issue in session_issues:
        issue_by_number[issue["number"]] = issue

    # Build branch→note index for fast lookup
    branch_to_note = {}
    for nid, note in notes.items():
        if note.get("branch"):
            branch_to_note[note["branch"]] = (nid, note)

    # Source 1: PR-based sessions (most complete coverage)
    for key, data in sorted(pr_sessions.items(), reverse=True):
        branch = data["branch"]
        date = min(data["dates"]) if data["dates"] else "unknown"
        session_id = f"{date}_{branch.replace('claude/', '').replace('/', '-')}"

        # Find matching notes file — BRANCH MATCH ONLY
        matching_note = None
        if branch in branch_to_note:
            nid, matching_note = branch_to_note[branch]
            used_notes.add(nid)

        # Find matching SESSION issue — priority: (1) runtime cache, (2) branch in body
        matching_issue = None
        # Priority 1: runtime cache provides definitive branch→issue mapping
        if branch in cache_branch_to_issue:
            cached_issue_num = cache_branch_to_issue[branch]
            if cached_issue_num in issue_by_number and cached_issue_num not in used_issues:
                matching_issue = issue_by_number[cached_issue_num]
                used_issues.add(cached_issue_num)
        # Priority 2: branch name in issue body (legacy matching)
        if not matching_issue:
            for issue in session_issues:
                if issue["number"] in used_issues:
                    continue
                body = issue.get("body", "") or ""
                if branch in body:
                    matching_issue = issue
                    used_issues.add(issue["number"])
                    break

        # Build session entry
        prs_sorted = sorted(data["prs"], key=lambda p: p["number"])
        pr_list = []
        for p in prs_sorted:
            # Detect per-PR sub-type using the engineering taxonomy
            sub = detect_pr_sub_type(p.get("title", ""))
            pr_list.append({
                "number": p["number"],
                "title": p["title"],
                "created_at": p.get("created_at"),
                "merged_at": p.get("merged_at"),
                "additions": p.get("additions", 0),
                "deletions": p.get("deletions", 0),
                "changed_files": p.get("changed_files", 0),
                "commits": p.get("commits", 0),
                "sub_type": sub,
            })

        # Compute time aggregates from PR timestamps
        first_pr_time = None
        last_pr_time = None
        active_minutes = 0
        for p in prs_sorted:
            ca = p.get("created_at")
            ma = p.get("merged_at")
            if ca:
                if first_pr_time is None or ca < first_pr_time:
                    first_pr_time = ca
            end_ts = ma or ca
            if end_ts:
                if last_pr_time is None or end_ts > last_pr_time:
                    last_pr_time = end_ts
            # Estimate active time per PR: created → merged
            if ca and ma:
                try:
                    t_start = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                    t_end = datetime.fromisoformat(ma.replace("Z", "+00:00"))
                    delta = (t_end - t_start).total_seconds() / 60
                    if 0 < delta < 480:  # cap at 8h per PR (sanity)
                        active_minutes += int(delta)
                except (ValueError, TypeError):
                    pass

        # Compute velocity aggregates from PRs
        total_additions = sum(p.get("additions", 0) for p in prs_sorted)
        total_deletions = sum(p.get("deletions", 0) for p in prs_sorted)
        total_files_changed = sum(p.get("changed_files", 0) for p in prs_sorted)
        total_commits = sum(p.get("commits", 0) for p in prs_sorted)
        total_lines = total_additions + total_deletions

        # Calendar minutes (first PR created → last PR merged/created)
        calendar_minutes = 0
        if first_pr_time and last_pr_time:
            try:
                t_first = datetime.fromisoformat(first_pr_time.replace("Z", "+00:00"))
                t_last = datetime.fromisoformat(last_pr_time.replace("Z", "+00:00"))
                calendar_minutes = int((t_last - t_first).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        # Velocity rates (per hour)
        active_hours = active_minutes / 60 if active_minutes > 0 else None
        lines_per_hour = round(total_lines / active_hours) if active_hours and active_hours > 0 else None
        commits_per_hour = round(total_commits / active_hours, 1) if active_hours and active_hours > 0 else None
        files_per_hour = round(total_files_changed / active_hours, 1) if active_hours and active_hours > 0 else None

        # Time block classification (based on first PR timestamp)
        time_block = None
        if first_pr_time:
            try:
                t = datetime.fromisoformat(first_pr_time.replace("Z", "+00:00"))
                h = t.hour
                if 5 <= h < 12:
                    time_block = "morning"
                elif 12 <= h < 18:
                    time_block = "afternoon"
                else:
                    time_block = "evening"
            except (ValueError, TypeError):
                pass

        # Determine title — priority: SESSION issue > notes > PR title > branch name
        title = None
        if matching_issue:
            raw = matching_issue["title"]
            # Strip "SESSION: " prefix and date suffix
            raw = re.sub(r"^SESSION:\s*", "", raw)
            raw = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", raw)
            title = raw.strip()
        if not title and matching_note and matching_note.get("title"):
            raw = matching_note["title"]
            # Don't use raw filename as title
            if not raw.startswith("session-"):
                title = raw
        if not title:
            # Derive from first PR title (or most descriptive PR title)
            best_title = ""
            for p in prs_sorted:
                if p["title"] and len(p["title"]) > len(best_title):
                    best_title = p["title"]
            if best_title:
                title = best_title
        if not title:
            # Derive from branch name
            slug = branch.replace("claude/", "")
            # Remove trailing session ID (e.g., -QM5Sk)
            slug = re.sub(r"-[A-Za-z0-9]{5}$", "", slug)
            title = slug.replace("-", " ").title()

        # Determine type using the engineering taxonomy (11 types)
        sess_type = None
        request_type = None
        if matching_note and matching_note.get("type"):
            sess_type = matching_note["type"]
            request_type = matching_note.get("request_type")
        if not sess_type:
            # Infer from all available text: PR titles + issue title + issue body
            text_parts = [p["title"] for p in prs_sorted]
            if matching_issue:
                text_parts.append(matching_issue.get("title", ""))
                text_parts.append(matching_issue.get("body", "") or "")
            combined_text = " ".join(text_parts)
            request_type, sess_type = detect_session_type_from_text(combined_text)

        # Summary
        summary = ""
        if matching_note and matching_note.get("summary"):
            summary = matching_note["summary"]
        elif matching_issue and matching_issue.get("body"):
            body = matching_issue["body"] or ""
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("*") and not line.startswith("-") and len(line) > 10:
                    summary = line[:300]
                    break

        # Lessons
        lessons = []
        if matching_note and matching_note.get("lessons"):
            lessons = matching_note["lessons"]

        # Issues
        issues = []
        if matching_note and matching_note.get("issues"):
            issues = matching_note["issues"]
        if matching_issue:
            if matching_issue["number"] not in issues:
                issues.append(matching_issue["number"])

        # Fetch issue comments if session has a tracked issue
        comments = []
        sync_score = None
        if matching_issue:
            comments = fetch_issue_comments(matching_issue["number"], token)
            # Compute sync score: ratio of completed bot step comments
            # to total PRs (a rough proxy for expected steps)
            bot_completed = sum(1 for c in comments if c["status"] == "completed")
            bot_in_progress = sum(1 for c in comments if c["status"] == "in_progress")
            user_comments_count = sum(1 for c in comments if c["type"] == "user")
            total_steps = bot_completed + bot_in_progress
            if total_steps > 0:
                sync_score = round(bot_completed / total_steps, 2)

        issue_created_at = matching_issue.get("created_at") if matching_issue else None
        first_activity_time = first_pr_time or issue_created_at
        last_activity_time = last_pr_time or issue_created_at
        session = {
            "id": session_id,
            "date": date,
            "title": title,
            "branch": branch,
            "type": sess_type,
            "request_type": request_type,
            "summary": summary,
            "prs": pr_list,
            "issues": sorted(set(issues)),
            "lessons": lessons,
            "comments": comments,
            "pr_count": len(pr_list),
            "has_notes": matching_note is not None,
            "has_issue": matching_issue is not None,
            "sync_score": sync_score,
            "source_file": matching_note.get("source_file") if matching_note else None,
            "issue_number": matching_issue["number"] if matching_issue else None,
            "issue_created_at": issue_created_at,
            "first_activity_time": first_activity_time,
            "last_activity_time": last_activity_time,
            "first_pr_time": first_pr_time,
            "last_pr_time": last_pr_time,
            "active_minutes": active_minutes,
            "calendar_minutes": calendar_minutes,
            "time_block": time_block,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_lines": total_lines,
            "total_files_changed": total_files_changed,
            "total_commits": total_commits,
            "lines_per_hour": lines_per_hour,
            "commits_per_hour": commits_per_hour,
            "files_per_hour": files_per_hour,
        }
        # Infer engineering stage from PR sub_types and session type
        session["engineering_stage"] = infer_engineering_stage(session)
        sessions.append(session)
        seen_branches.add(branch)

    # Source 2: Notes files that were NOT matched to any PR session
    for nid, note in sorted(notes.items(), key=lambda x: x[1]["date"], reverse=True):
        if nid in used_notes:
            continue

        note_type = note.get("type", f"{REQUEST_TYPE_EMOJI['documentation']} Documentation")
        note_request_type = note.get("request_type", "documentation")
        session = {
            "id": nid,
            "date": note["date"],
            "title": note.get("title") or nid,
            "branch": note.get("branch"),
            "type": note_type,
            "request_type": note_request_type,
            "summary": note.get("summary", ""),
            "prs": [],
            "issues": note.get("issues", []),
            "lessons": note.get("lessons", []),
            "comments": [],
            "pr_count": 0,
            "has_notes": True,
            "has_issue": False,
            "source_file": note.get("source_file"),
            "issue_number": None,
        }
        session["engineering_stage"] = infer_engineering_stage(session)
        sessions.append(session)

    # Source 3: SESSION issues that were NOT matched to any PR session
    for issue in session_issues:
        if issue["number"] in used_issues:
            continue

        issue_date = issue["created_at"][:10]
        raw = issue["title"]
        raw = re.sub(r"^SESSION:\s*", "", raw)
        raw = re.sub(r"^ANALYSIS:\s*", "", raw)
        raw = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", raw)
        title = raw.strip()

        # Fetch comments for standalone issue sessions too
        issue_comments = fetch_issue_comments(issue["number"], token)

        # Detect type from issue title + body
        issue_text = f"{title} {issue.get('body', '') or ''}"
        issue_request_type, issue_type_label = detect_session_type_from_text(issue_text)

        issue_created_at = issue.get("created_at")
        # Last activity = last comment time or issue creation
        last_comment_time = issue_comments[-1]["created_at"] if issue_comments else None
        last_activity_time = last_comment_time or issue_created_at
        session = {
            "id": f"issue-{issue['number']}",
            "date": issue_date,
            "title": title,
            "branch": None,
            "type": issue_type_label,
            "request_type": issue_request_type,
            "summary": "",
            "prs": [],
            "issues": [issue["number"]],
            "lessons": [],
            "comments": issue_comments,
            "pr_count": 0,
            "has_notes": False,
            "has_issue": True,
            "source_file": None,
            "issue_number": issue["number"],
            "issue_created_at": issue_created_at,
            "first_activity_time": issue_created_at,
            "last_activity_time": last_activity_time,
        }
        session["engineering_stage"] = infer_engineering_stage(session)
        sessions.append(session)

    # Sort by date descending, then by last activity time descending (most recent first)
    sessions.sort(key=lambda s: (s["date"], s.get("last_activity_time") or s.get("last_pr_time") or s.get("first_activity_time") or "", s["pr_count"]), reverse=True)

    return sessions


def main():
    output_path = "docs/data/sessions.json"
    if len(sys.argv) > 2 and sys.argv[1] == "--output":
        output_path = sys.argv[2]

    token = os.environ.get("GH_TOKEN", "")

    print("=== Generating sessions.json ===")
    print()

    # Source 1: GitHub PRs
    print("Source 1: GitHub PRs...")
    prs = fetch_all_prs(token)
    if token:
        prs = enrich_prs_with_stats(prs, token)
    else:
        print("  [info] No GH_TOKEN — skipping PR velocity enrichment (additions/deletions/files/commits)")
    pr_sessions = group_prs_by_branch(prs)
    print(f"  → {len(pr_sessions)} distinct claude/* sessions from PRs")
    print()

    # Source 2: SESSION issues
    print("Source 2: SESSION issues...")
    session_issues = fetch_session_issues(token)
    print(f"  → {len(session_issues)} SESSION issues")
    print()

    # Source 3: notes/session-*.md
    print("Source 3: Session notes files...")
    notes = parse_all_notes("notes")
    print(f"  → {len(notes)} session notes files")
    print()

    # Source 4: Runtime caches (branch→issue mapping)
    print("Source 4: Runtime cache files...")
    caches = parse_runtime_caches("notes")
    print(f"  → {len(caches)} runtime cache entries")
    print()

    # Safety gate: detect API degradation before overwriting existing data
    # If existing sessions.json has issue data but this run got 0 issues,
    # the API was likely unreachable — refuse to overwrite and lose data
    existing_issue_count = 0
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_issue_count = sum(
                1 for s in existing.get("sessions", []) if s.get("has_issue")
            )
        except (json.JSONDecodeError, OSError):
            pass

    if existing_issue_count > 0 and len(session_issues) == 0:
        print(f"  ⚠️  SAFETY GATE: existing sessions.json has {existing_issue_count} sessions with issue data")
        print(f"     but this run fetched 0 SESSION issues (API unreachable?)")
        print(f"     Refusing to overwrite — existing data preserved.")
        print(f"     Re-run with GH_TOKEN and working API to regenerate.")
        sys.exit(1)

    if existing_issue_count > 0 and len(prs) == 0:
        print(f"  ⚠️  SAFETY GATE: existing sessions.json has data but this run fetched 0 PRs")
        print(f"     Refusing to overwrite — existing data preserved.")
        sys.exit(1)

    # Merge
    print("Merging all sources...")
    sessions = merge_sources(pr_sessions, session_issues, notes, token, caches)
    print(f"  → {len(sessions)} total sessions")
    print()

    # Enrich related issues with title and labels
    # Build a cache of known issues from SESSION issues fetch
    known_issues = {}
    for iss in session_issues:
        num = iss.get("number")
        raw_title = iss.get("title", "")
        # Strip SESSION prefix and date suffix for display
        clean = re.sub(r"^SESSION:\s*", "", raw_title)
        clean = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", clean)
        labels = [l.get("name", "") for l in iss.get("labels", [])]
        known_issues[num] = {
            "number": num,
            "title": clean.strip(),
            "state": iss.get("state", ""),
            "labels": labels,
        }

    # Build set of known PR numbers to exclude from related issues
    all_pr_numbers = set()
    for s in sessions:
        for pr in s.get("prs", []):
            all_pr_numbers.add(pr["number"])

    # Collect all related issue numbers that need enrichment
    needed = set()
    for s in sessions:
        session_num = s.get("issue_number")
        for n in s.get("issues", []):
            if n != session_num and n not in known_issues and n not in all_pr_numbers:
                needed.add(n)

    if needed and token:
        print(f"Enriching {len(needed)} related issues with titles...")
        for n in sorted(needed):
            detail = fetch_issue_detail(n, token)
            if detail:
                known_issues[n] = detail
        print(f"  → {len(known_issues)} total issues in cache")

    # Build related_issues array for each session (exclude PRs and session's own issue)
    for s in sessions:
        session_num = s.get("issue_number")
        related = []
        for n in s.get("issues", []):
            if n == session_num or n in all_pr_numbers:
                continue
            info = known_issues.get(n, {})
            if not info:
                continue  # Unknown and not enrichable — skip
            related.append({
                "number": n,
                "title": info.get("title", ""),
                "state": info.get("state", ""),
                "labels": info.get("labels", []),
            })
        s["related_issues"] = related

    # Bidirectional linking: if session A references issue B as related,
    # then session B (if it exists as standalone) should reference A as related (parent)
    # Build reverse index: issue_number → parent session issue_numbers
    issue_to_parents = defaultdict(set)
    for s in sessions:
        parent_num = s.get("issue_number")
        if not parent_num:
            continue
        for ri in s.get("related_issues", []):
            issue_to_parents[ri["number"]].add(parent_num)

    # Apply reverse links to standalone sessions
    for s in sessions:
        session_num = s.get("issue_number")
        if not session_num or session_num not in issue_to_parents:
            continue
        existing_nums = {ri["number"] for ri in s.get("related_issues", [])}
        for parent_num in sorted(issue_to_parents[session_num]):
            if parent_num == session_num or parent_num in existing_nums:
                continue
            info = known_issues.get(parent_num, {})
            s["related_issues"].insert(0, {
                "number": parent_num,
                "title": info.get("title", ""),
                "state": info.get("state", ""),
                "labels": info.get("labels", []),
            })
    print()

    # ── Session tree detection ──
    # Build parent/child relationships from related_issues + creation timestamps.
    # A session is a "continuation" if it has a parent SESSION issue created before it.
    # A session is "original" (root) if it has no parent — only children or no links.
    # Tree fields: session_kind, parent_issue, children_issues, tree_root, tree_depth

    # Index sessions by issue_number for fast lookup
    sessions_by_issue = {}
    for s in sessions:
        n = s.get("issue_number")
        if n:
            sessions_by_issue[n] = s

    # Step 1: For each session, classify related issues as parent or child
    # based on SESSION label + creation order
    for s in sessions:
        s_num = s.get("issue_number")
        s_created = s.get("issue_created_at", "")
        parents = []
        children = []
        for ri in s.get("related_issues", []):
            ri_labels = [l.lower() for l in ri.get("labels", [])]
            if "session" not in ri_labels:
                continue  # Not a session issue — skip for tree
            peer = sessions_by_issue.get(ri["number"])
            if not peer:
                continue
            peer_created = peer.get("issue_created_at", "")
            if peer_created and s_created and peer_created < s_created:
                parents.append(ri["number"])
            elif peer_created and s_created and peer_created > s_created:
                children.append(ri["number"])
        s["parent_issues"] = sorted(parents)
        s["children_issues"] = sorted(children)

    # Step 1b: Date-based grouping — consolidate all sessions per date under one root
    # The earliest session (by issue creation time) on each date becomes the day's root.
    # All other sessions on that date become direct children of the root (depth 1),
    # even if they already have their own children (sub-trees are preserved).
    # This reflects the user's reality: one conversation window per day, multiple
    # system-level sessions that are continuations from the user's perspective.
    date_groups = defaultdict(list)
    for s in sessions:
        created = s.get("issue_created_at", "")
        if not created or not s.get("issue_number"):
            continue
        date_key = created[:10]  # YYYY-MM-DD
        date_groups[date_key].append(s)

    for date_key, group in date_groups.items():
        if len(group) < 2:
            continue  # Single session on this date — nothing to group
        # Sort by creation time (earliest first)
        group.sort(key=lambda x: x.get("issue_created_at", ""))
        root = group[0]
        root_num = root.get("issue_number")
        for s in group[1:]:
            s_num = s.get("issue_number")
            if not s_num:
                continue
            # Skip if already a direct child of the root
            if root_num in (s.get("parent_issues") or []):
                continue
            # Make this session a child of the date root
            if root_num not in (s.get("parent_issues") or []):
                s["parent_issues"] = sorted((s.get("parent_issues") or []) + [root_num])
            if s_num not in (root.get("children_issues") or []):
                root["children_issues"] = sorted((root.get("children_issues") or []) + [s_num])

    # Step 2: Find tree roots and compute depth via BFS
    # Root = session with no parents (but may have children)
    for s in sessions:
        if not s.get("parent_issues"):
            s["tree_root"] = s.get("issue_number")
            s["tree_depth"] = 0
        else:
            s["tree_root"] = None
            s["tree_depth"] = None

    # Propagate root + depth from parents to children
    changed = True
    max_iter = 20
    while changed and max_iter > 0:
        changed = False
        max_iter -= 1
        for s in sessions:
            if s.get("tree_root") is not None:
                continue
            # Try to inherit from a parent that already has a root
            for p_num in s.get("parent_issues", []):
                parent = sessions_by_issue.get(p_num)
                if parent and parent.get("tree_root") is not None:
                    s["tree_root"] = parent["tree_root"]
                    s["tree_depth"] = (parent.get("tree_depth") or 0) + 1
                    changed = True
                    break

    # Step 2b: Sync related_issues with tree relationships
    # The tree builder (steps 1 + 1b) may add children/parents that were not
    # in the original related_issues array (e.g. date-based grouping).
    # Ensure related_issues includes all tree-linked sessions for display.
    for s in sessions:
        existing_nums = {ri["number"] for ri in s.get("related_issues", [])}
        session_num = s.get("issue_number")
        all_linked = set()
        all_linked.update(s.get("children_issues") or [])
        all_linked.update(s.get("parent_issues") or [])
        for linked_num in sorted(all_linked):
            if linked_num == session_num or linked_num in existing_nums:
                continue
            info = known_issues.get(linked_num, {})
            if not info:
                # Try to get info from the session itself
                peer = sessions_by_issue.get(linked_num)
                if peer:
                    info = {
                        "title": peer.get("title", ""),
                        "state": "closed" if peer.get("session_kind") else "open",
                        "labels": ["SESSION"],
                    }
            if info:
                s["related_issues"].append({
                    "number": linked_num,
                    "title": info.get("title", ""),
                    "state": info.get("state", ""),
                    "labels": info.get("labels", []),
                })
                existing_nums.add(linked_num)

    # Step 3: Assign session_kind based on tree position
    for s in sessions:
        if s.get("parent_issues"):
            s["session_kind"] = "continuation"
        else:
            s["session_kind"] = "original"

    # Step 4: Aggregate child session data into parent sessions
    # Parent sessions collect PRs, comments, and metrics from all children
    # This enables the Session Viewer to show a complete picture for parent sessions
    def collect_descendants(issue_num, visited=None):
        """Recursively collect all descendant sessions (children, grandchildren, etc.)."""
        if visited is None:
            visited = set()
        if issue_num in visited:
            return []
        visited.add(issue_num)
        result = []
        parent = sessions_by_issue.get(issue_num)
        if not parent:
            return result
        for child_num in parent.get("children_issues", []):
            child = sessions_by_issue.get(child_num)
            if child:
                result.append(child)
                result.extend(collect_descendants(child_num, visited))
        return result

    aggregated_count = 0
    for s in sessions:
        if not s.get("children_issues"):
            continue
        descendants = collect_descendants(s.get("issue_number"))
        if not descendants:
            continue

        # Collect child PRs grouped by child issue
        child_prs_by_issue = []
        for desc in descendants:
            if desc.get("prs"):
                child_prs_by_issue.append({
                    "issue_number": desc.get("issue_number"),
                    "issue_title": desc.get("title", ""),
                    "prs": desc["prs"],
                })

        # Collect child comments grouped by child issue
        child_comments_by_issue = []
        for desc in descendants:
            if desc.get("comments"):
                child_comments_by_issue.append({
                    "issue_number": desc.get("issue_number"),
                    "issue_title": desc.get("title", ""),
                    "comments": desc["comments"],
                })

        # Aggregate all PRs (parent's own + all children's)
        all_prs = list(s.get("prs", []))
        for group in child_prs_by_issue:
            all_prs.extend(group["prs"])

        # Aggregate all comments (parent's own + all children's)
        all_comments = []
        # Parent's own comments first (tagged with parent issue)
        if s.get("comments"):
            all_comments.append({
                "issue_number": s.get("issue_number"),
                "issue_title": s.get("title", ""),
                "comments": s["comments"],
            })
        # Then children's comments
        all_comments.extend(child_comments_by_issue)

        # Compute aggregated metrics
        agg_additions = s.get("total_additions", 0) + sum(d.get("total_additions", 0) for d in descendants)
        agg_deletions = s.get("total_deletions", 0) + sum(d.get("total_deletions", 0) for d in descendants)
        agg_files = s.get("total_files_changed", 0) + sum(d.get("total_files_changed", 0) for d in descendants)
        agg_commits = s.get("total_commits", 0) + sum(d.get("total_commits", 0) for d in descendants)
        agg_active = s.get("active_minutes", 0) + sum(d.get("active_minutes", 0) for d in descendants)
        agg_pr_count = s.get("pr_count", 0) + sum(d.get("pr_count", 0) for d in descendants)

        # Compute aggregated time span (earliest first_activity → latest last_activity)
        all_times = []
        for sess in [s] + descendants:
            fa = sess.get("first_activity_time")
            la = sess.get("last_activity_time")
            if fa:
                all_times.append(fa)
            if la:
                all_times.append(la)
        agg_first = min(all_times) if all_times else s.get("first_activity_time")
        agg_last = max(all_times) if all_times else s.get("last_activity_time")

        agg_calendar = 0
        if agg_first and agg_last:
            try:
                t_f = datetime.fromisoformat(agg_first.replace("Z", "+00:00"))
                t_l = datetime.fromisoformat(agg_last.replace("Z", "+00:00"))
                agg_calendar = int((t_l - t_f).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        s["aggregated"] = {
            "prs": all_prs,
            "prs_by_issue": child_prs_by_issue,
            "comments_by_issue": all_comments,
            "total_additions": agg_additions,
            "total_deletions": agg_deletions,
            "total_files_changed": agg_files,
            "total_commits": agg_commits,
            "total_lines": agg_additions + agg_deletions,
            "active_minutes": agg_active,
            "calendar_minutes": agg_calendar,
            "pr_count": agg_pr_count,
            "first_activity_time": agg_first,
            "last_activity_time": agg_last,
            "children_count": len(descendants),
            "children_issue_numbers": [d.get("issue_number") for d in descendants if d.get("issue_number")],
        }
        aggregated_count += 1

    # Stats
    cont_count = sum(1 for s in sessions if s.get("session_kind") == "continuation")
    tree_roots = sum(1 for s in sessions if s.get("tree_depth") == 0 and s.get("children_issues"))
    if cont_count or tree_roots:
        print(f"Session tree: {len(sessions) - cont_count} original, {cont_count} continuation, {tree_roots} trees")
    if aggregated_count:
        print(f"  → {aggregated_count} parent sessions enriched with child aggregation")

    # Count sessions with/without compilation data
    with_notes = sum(1 for s in sessions if s["has_notes"])
    with_issue = sum(1 for s in sessions if s["has_issue"])
    without_notes = sum(1 for s in sessions if not s["has_notes"])

    # Determine compilation cutoff date
    # v50 (pre-save summary) was introduced around 2026-02-27
    compilation_cutoff = "2026-02-27"

    # Build issue label map from all fetched SESSION issues + enriched related issues
    issue_labels = {}
    for num, info in known_issues.items():
        labels = info.get("labels", [])
        primary = "SESSION"
        for name in labels:
            if name and name != "SESSION":
                primary = name
                break
        issue_labels[str(num)] = {
            "label": primary,
            "color": ""
        }
    # Overlay with original format (preserves color data from SESSION issues)
    for iss in session_issues:
        num = iss.get("number")
        labels = iss.get("labels", [])
        # Primary label = first non-SESSION label, fallback to SESSION
        primary = "SESSION"
        for lbl in labels:
            name = lbl.get("name", "")
            if name and name != "SESSION":
                primary = name
                break
        issue_labels[str(num)] = {
            "label": primary,
            "color": next((lbl.get("color", "") for lbl in labels if lbl.get("name") == primary), "")
        }

    # Build output
    output = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_sessions": len(sessions),
            "with_notes": with_notes,
            "with_issue": with_issue,
            "without_notes": without_notes,
            "compilation_available_from": compilation_cutoff,
            "sources": [
                "GitHub PRs (claude/* branches)",
                "GitHub SESSION issues",
                "notes/session-*.md files",
                "notes/session-runtime-*.json caches"
            ]
        },
        "issue_labels": issue_labels,
        "sessions": sessions
    }

    # Write
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written to {output_path}")
    print()
    print("Summary:")
    print(f"  Total sessions:     {len(sessions)}")
    print(f"  With notes files:   {with_notes}")
    print(f"  With SESSION issue: {with_issue}")
    print(f"  PR-only (no notes): {without_notes}")
    print()

    # Date distribution
    dates = defaultdict(int)
    for s in sessions:
        dates[s["date"]] += 1
    print("Sessions by date:")
    for date in sorted(dates.keys(), reverse=True)[:15]:
        print(f"  {date}: {dates[date]} session(s)")


def incremental_update(output_path="docs/data/sessions.json"):
    """Fast incremental update — add/update ONLY the current session.

    Instead of re-fetching 600+ PRs, this:
    1. Loads existing sessions.json
    2. Reads the current session's runtime cache
    3. Fetches ONLY that session's issue + PRs from GitHub
    4. Updates/adds the entry in the existing data
    5. Writes back

    ~5 seconds vs ~120 seconds for full regen.
    """
    from session_agent import read_runtime_cache, _find_runtime_cache

    cache = read_runtime_cache()
    if not cache:
        print("  [incremental] No runtime cache — falling back to full regen")
        return main()

    issue_number = cache.get("issue_number")
    branch = cache.get("branch", "")
    if not issue_number or not branch:
        print("  [incremental] Missing issue/branch — falling back to full regen")
        return main()

    token = os.environ.get("GH_TOKEN", "")
    print(f"=== Incremental sessions.json update (issue #{issue_number}, branch {branch}) ===")

    # Load existing data
    existing = {"meta": {}, "sessions": [], "issue_labels": {}}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("  [incremental] Cannot read existing file — falling back to full regen")
            return main()

    # Fetch only this session's issue from GitHub
    issue_data = github_api(f"/repos/{REPO}/issues/{issue_number}", token)
    if not issue_data:
        print(f"  [warn] Could not fetch issue #{issue_number}")

    # Fetch PRs for this branch only
    branch_prs = []
    prs_data = github_api(
        f"/repos/{REPO}/pulls?state=closed&head=packetqc:{branch}&per_page=20",
        token
    )
    if prs_data:
        branch_prs = [p for p in prs_data if p.get("merged_at")]
    # Also check open PRs
    open_prs = github_api(
        f"/repos/{REPO}/pulls?state=open&head=packetqc:{branch}&per_page=10",
        token
    )
    if open_prs:
        branch_prs.extend(open_prs)

    print(f"  Fetched {len(branch_prs)} PRs for branch {branch}")

    # Parse notes file for this session
    notes = parse_all_notes("notes")
    matching_note = None
    for nid, note in notes.items():
        if note.get("branch") == branch:
            matching_note = note
            break

    # Build the session entry
    date = cache.get("created", "")[:10] if cache.get("created") else "unknown"
    if not date or date == "unknown":
        if branch_prs:
            date = branch_prs[0].get("created_at", "")[:10]

    pr_list = []
    total_additions = 0
    total_deletions = 0
    total_files = 0
    for pr in branch_prs:
        pr_entry = {
            "number": pr["number"],
            "title": pr.get("title", ""),
            "state": pr.get("state", ""),
            "merged": bool(pr.get("merged_at")),
            "created_at": pr.get("created_at", ""),
            "merged_at": pr.get("merged_at", ""),
        }
        # Enrich with stats if token available
        if token:
            detail = github_api(f"/repos/{REPO}/pulls/{pr['number']}", token)
            if detail:
                pr_entry["additions"] = detail.get("additions", 0)
                pr_entry["deletions"] = detail.get("deletions", 0)
                pr_entry["changed_files"] = detail.get("changed_files", 0)
                pr_entry["commits"] = detail.get("commits", 0)
                total_additions += pr_entry.get("additions", 0)
                total_deletions += pr_entry.get("deletions", 0)
                total_files += pr_entry.get("changed_files", 0)
        pr_list.append(pr_entry)

    session_entry = {
        "id": f"{date}_{branch.replace('claude/', '').replace('/', '-')}",
        "date": date,
        "branch": branch,
        "prs": pr_list,
        "total_prs": len(pr_list),
        "has_notes": matching_note is not None,
        "has_issue": issue_data is not None,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "total_files_changed": total_files,
    }

    # Add issue data
    if issue_data:
        raw_title = issue_data.get("title", "")
        clean = re.sub(r"^SESSION:\s*", "", raw_title)
        clean = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)\s*$", "", clean)
        session_entry["issue_number"] = issue_data["number"]
        session_entry["issue_title"] = clean.strip()
        session_entry["issue_state"] = issue_data.get("state", "")
        session_entry["issue_created_at"] = issue_data.get("created_at", "")
        session_entry["issue_labels"] = [
            l.get("name", "") for l in issue_data.get("labels", [])
        ]
        session_entry["issue_comments"] = issue_data.get("comments", 0)

    # Add notes data
    if matching_note:
        session_entry["notes_title"] = matching_note.get("title", "")
        session_entry["notes_summary"] = matching_note.get("summary", "")

    # Add runtime cache data
    session_entry["request_type"] = cache.get("request_type", "")
    session_entry["engineering_stage"] = cache.get("engineering_stage", "")
    session_entry["work_summary"] = cache.get("work_summary", "")

    # Related issues from cache
    issues_list = cache.get("related_issues", [])
    if isinstance(issues_list, list):
        session_entry["issues"] = issues_list

    # Update or add in existing sessions
    sessions = existing.get("sessions", [])
    updated = False
    for i, s in enumerate(sessions):
        if s.get("branch") == branch or s.get("issue_number") == issue_number:
            # Merge: keep existing fields, update with new
            sessions[i].update(session_entry)
            updated = True
            print(f"  Updated existing session entry (index {i})")
            break
    if not updated:
        sessions.insert(0, session_entry)
        print(f"  Added new session entry")

    # Update meta
    existing["meta"]["generated_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    existing["meta"]["total_sessions"] = len(sessions)
    existing["meta"]["last_incremental"] = True
    existing["sessions"] = sessions

    # Write
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"  Written to {output_path} ({len(sessions)} sessions)")


if __name__ == "__main__":
    if "--incremental" in sys.argv:
        output = "docs/data/sessions.json"
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output = sys.argv[i + 1]
        incremental_update(output)
    else:
        main()
