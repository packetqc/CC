"""Documentation debt detection — inline and final-sweep checks.

Two-layer documentation debt detection:
  1. Inline: check_todo_documentation() at each todo completion
  2. Final: evaluate_documentation_debt() at save time

Authors: Martin Paquet, Claude (Anthropic)
"""

from datetime import datetime, timezone

from .cache import read_runtime_cache, update_session_data
from .addons import read_request_addons


def check_todo_documentation(todo_content: str, files_changed: list = None) -> dict:
    """Check if a completed todo requires documentation updates.

    Called at each todo completion — lightweight, inline check.

    Args:
        todo_content: The completed todo's description
        files_changed: List of files modified by this todo

    Returns:
        Dict with:
          - needs_doc (bool): True if documentation update recommended
          - reason (str): Why documentation is needed
          - targets (list): Suggested files/publications to update
    """
    files_changed = files_changed or []
    needs_doc = False
    reason = ""
    targets = []

    # Feature/infrastructure changes almost always need doc updates
    infra_keywords = ["claude.md", "methodology", "session_agent", "gh_helper",
                      "generate_sessions", "generate_og", "layout", "interface"]
    feature_keywords = ["implement", "add", "create", "new", "feat", "refactor",
                        "deprecat", "taxonomy", "badge", "banner"]

    content_lower = todo_content.lower()
    files_lower = " ".join(f.lower() for f in files_changed)

    # Check if infrastructure was touched
    infra_hit = any(kw in files_lower for kw in infra_keywords)
    feature_hit = any(kw in content_lower for kw in feature_keywords)

    if infra_hit:
        needs_doc = True
        reason = "Infrastructure files modified — publications/methodology may need update"
        if "session_agent" in files_lower:
            targets.append("publications/agent-ticket-sync/")
        if "claude.md" in files_lower:
            targets.append("publications/knowledge-system/")
        if "interface" in files_lower:
            targets.append("publications/main-interface/")
        if "methodology" in files_lower:
            targets.append("methodology/ (already self-documenting)")

    elif feature_hit:
        needs_doc = True
        reason = "Feature work completed — verify documentation coverage"
        targets.append("NEWS.md")
        targets.append("relevant publication")

    # Store evaluation in session cache for tracking
    cache = read_runtime_cache()
    if cache:
        sd = cache.get("session_data", {})
        doc_checks = sd.get("doc_checks", [])
        doc_checks.append({
            "todo": todo_content,
            "needs_doc": needs_doc,
            "reason": reason,
            "targets": targets,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        update_session_data("doc_checks", doc_checks)

    return {"needs_doc": needs_doc, "reason": reason, "targets": targets}


def evaluate_documentation_debt() -> dict:
    """Final documentation debt evaluation at save time.

    Scans the session cache for deliverables and compares against
    documentation state. This is the FINAL SWEEP backstop.

    Returns:
        Dict with:
          - needs_update (bool): True if documentation debt detected
          - items (list): Each item is {category, description, target, priority}
          - inline_checks (list): Results from per-todo checks during session
          - summary (str): One-line summary for AskUserQuestion
    """
    cache = read_runtime_cache()
    if not cache:
        return {"needs_update": False, "items": [], "summary": "No session cache"}

    sd = cache.get("session_data", {})
    items = []

    # 1. Check if PRs were merged
    prs = sd.get("pr_numbers", [])
    if prs:
        merged_prs = [p for p in prs if p.get("status") == "merged"]
        if len(merged_prs) > 0:
            items.append({
                "category": "publications",
                "description": f"{len(merged_prs)} PR(s) merged — verify affected publications reflect changes",
                "target": "docs/publications/",
                "priority": "medium"
            })

    # 2. Check add-ons for features
    addons = read_request_addons()
    feature_addons = [a for a in addons if any(kw in a.get("synthesis", "").lower()
                      for kw in ["implement", "add", "create", "new feature", "new function"])]
    if feature_addons:
        items.append({
            "category": "methodology",
            "description": f"{len(feature_addons)} feature add-on(s) — check if methodology/ or CLAUDE.md needs update",
            "target": "methodology/",
            "priority": "medium"
        })

    # 3. Check if infrastructure files were modified
    files_modified = sd.get("files_modified", [])
    infra_files = [f for f in files_modified if any(p in f for p in
                   ["scripts/", "methodology/", "CLAUDE.md"])]
    if infra_files:
        items.append({
            "category": "infrastructure",
            "description": f"{len(infra_files)} infrastructure file(s) modified — verify documentation reflects changes",
            "target": ", ".join(infra_files[:3]),
            "priority": "high" if "CLAUDE.md" in str(infra_files) else "medium"
        })

    # 4. Check interface files
    interface_files = [f for f in files_modified if "interfaces/" in f]
    if interface_files:
        items.append({
            "category": "interfaces",
            "description": f"{len(interface_files)} interface file(s) modified — verify Pub #21 reflects changes",
            "target": "docs/publications/main-interface/",
            "priority": "low"
        })

    # 5. Check NEWS.md coverage
    news_updated = any("NEWS.md" in f for f in files_modified)
    if prs and not news_updated:
        items.append({
            "category": "changelog",
            "description": "PRs merged but NEWS.md not updated this session",
            "target": "NEWS.md",
            "priority": "low"
        })

    # 6. Check work_summary exists
    if not sd.get("work_summary"):
        items.append({
            "category": "session",
            "description": "No work_summary in session cache — add before save",
            "target": "session cache",
            "priority": "low"
        })

    # 7. Include inline doc checks from per-todo evaluations
    inline_checks = sd.get("doc_checks", [])
    unresolved_inline = [c for c in inline_checks if c.get("needs_doc") and
                         not c.get("resolved")]

    if unresolved_inline:
        items.append({
            "category": "inline",
            "description": f"{len(unresolved_inline)} inline doc check(s) flagged during work but not resolved",
            "target": ", ".join(set(t for c in unresolved_inline for t in c.get("targets", []))),
            "priority": "medium"
        })

    needs_update = len(items) > 0
    high_count = len([i for i in items if i["priority"] == "high"])

    summary = f"{len(items)} documentation item(s) detected"
    if high_count:
        summary += f" ({high_count} high priority)"

    # Persist to session cache for next session inheritance
    result = {
        "needs_update": needs_update,
        "items": items,
        "inline_checks": inline_checks,
        "summary": summary,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
    update_session_data("documentation_debt", result)

    return result
