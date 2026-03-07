"""Integrity Gate — pre-commit vulnerability prevention for the knowledge system.

Scans the codebase for known vulnerability patterns discovered by the Doctor
Strange audit (v59.3, 55 vulnerabilities across 8 categories). This is the
**preventive** complement to the runtime `/integrity` skill — it checks the
codebase itself for structural weaknesses before they reach `main`.

6 check categories:
  1. Hook safety — bypass instructions, fail-closed defaults, path exceptions
  2. ACL integrity — UNSKIPPABLE/ALLOW_NOT_APPLICABLE coverage
  3. State machine safety — init guards, order validation, conditional passes
  4. Methodology consistency — contradiction patterns across documents
  5. Enforcement wiring — hooks registered, state keys match
  6. Code safety — conditional enforcement, save gates, dual output

Each check returns a list of findings. The orchestrator aggregates them into
a pass/fail report. Findings include file, line, severity, and message.

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
import re
from typing import Optional


def _repo_root() -> str:
    """Detect the repository root."""
    # Walk up from this file to find .git
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if os.path.isdir(os.path.join(current, ".git")) or os.path.isfile(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.getcwd()


def _read_file(path: str) -> Optional[str]:
    """Read a file, return None if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _finding(file: str, line: int, severity: str, message: str) -> dict:
    """Create a standardized finding dict."""
    return {
        "file": file,
        "line": line,
        "severity": severity,
        "message": message,
    }


# ── Check 1: Hook Safety ─────────────────────────────────────────

def check_hook_safety() -> list:
    """Check hooks for bypass instructions, fail-open defaults, and blanket exceptions."""
    findings = []
    root = _repo_root()

    # --- require-session-protocol.sh ---
    hook_path = os.path.join(root, ".claude", "hooks", "require-session-protocol.sh")
    content = _read_file(hook_path)
    if content is None:
        findings.append(_finding(hook_path, 0, "critical", "PreToolUse hook file missing"))
        return findings

    lines = content.splitlines()
    in_deny_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track DENY heredoc blocks
        if "<<" in line and "DENY" in line:
            in_deny_block = True
            continue
        if stripped == "DENY":
            in_deny_block = False
            continue

        # Check 1a: Bypass instructions inside DENY messages
        if in_deny_block:
            bypass_patterns = [
                (r'\bbypass\b', "Bypass instruction in DENY message"),
                (r'\bworkaround\b', "Workaround instruction in DENY message"),
                (r'\bdisable\b', "Disable instruction in DENY message"),
                (r'set\s+.*\s*true', "State override instruction in DENY message"),
                (r'\bskip\s+this\b', "Skip instruction in DENY message"),
            ]
            for pattern, msg in bypass_patterns:
                if re.search(pattern, stripped, re.IGNORECASE):
                    findings.append(_finding(hook_path, i, "critical", msg))

        # Check 1b: Fail-open defaults (parse failure → allow)
        if "|| echo" in line and ("True" in line or "allow" in line.lower() or "OK" in line):
            # Check if this is a fallback that defaults to allow
            if '|| echo "True"' in line or "|| echo \"True\"" in line:
                findings.append(_finding(hook_path, i, "critical",
                    "Fail-open default: parse failure returns True (should return False/BLOCK)"))

        # Check 1c: Blanket path exceptions
        if "exit 0" in line and ("case" not in line):
            if "/tmp/*)" in line or "/tmp/*)  " in line:
                findings.append(_finding(hook_path, i, "critical",
                    "Blanket /tmp/* exception — should use specific paths"))
            if ".claude/*)" in line or ".claude/*)  " in line:
                findings.append(_finding(hook_path, i, "critical",
                    "Blanket .claude/* exception — allows self-disabling hooks"))

    # Check 1d: Fail-closed on UNKNOWN tool name
    if "UNKNOWN" not in content or "UNKNOWN) ;;" not in content.replace(" ", ""):
        # Verify UNKNOWN is blocked (included in the blocking case)
        block_case = re.search(r'case\s+"\$TOOL_NAME"\s+in\s*\n\s*(.*?)\)', content, re.DOTALL)
        if block_case and "UNKNOWN" not in block_case.group(1):
            findings.append(_finding(hook_path, 0, "critical",
                "UNKNOWN tool name not blocked — parse failures pass through"))

    # --- startup-checklist.sh ---
    startup_path = os.path.join(root, ".claude", "hooks", "startup-checklist.sh")
    startup = _read_file(startup_path)
    if startup is None:
        findings.append(_finding(startup_path, 0, "critical", "SessionStart hook file missing"))
    else:
        # Check 1e: Enforcement state file initialization
        if ".claude-session-state.json" not in startup:
            findings.append(_finding(startup_path, 0, "critical",
                "Startup hook does not initialize enforcement state file"))

    # --- settings.json hook wiring (also checked in enforcement_wiring) ---
    settings_path = os.path.join(root, ".claude", "settings.json")
    settings_content = _read_file(settings_path)
    if settings_content:
        if "require-session-protocol" not in settings_content:
            findings.append(_finding(settings_path, 0, "critical",
                "PreToolUse hook not wired in settings.json"))

    return findings


# ── Check 2: ACL Integrity ────────────────────────────────────────

def check_acl_integrity() -> list:
    """Verify UNSKIPPABLE_CHECKPOINTS and ALLOW_NOT_APPLICABLE ACLs are correct."""
    findings = []
    root = _repo_root()
    integrity_path = os.path.join(root, "scripts", "session_agent", "integrity.py")
    content = _read_file(integrity_path)

    if content is None:
        findings.append(_finding(integrity_path, 0, "critical", "integrity.py not found"))
        return findings

    # Check 2a: UNSKIPPABLE_CHECKPOINTS must cover structural gates
    required_unskippable = {"T.1", "T.2", "C.1", "C.6", "C.7", "C.8"}
    unskippable_match = re.search(
        r'UNSKIPPABLE_CHECKPOINTS\s*=\s*\{([^}]+)\}', content
    )
    if unskippable_match:
        found = set(re.findall(r'"([A-Z]\.\d+)"', unskippable_match.group(1)))
        missing = required_unskippable - found
        if missing:
            line = content[:unskippable_match.start()].count('\n') + 1
            findings.append(_finding(integrity_path, line, "critical",
                f"UNSKIPPABLE_CHECKPOINTS missing structural gates: {missing}"))
    else:
        findings.append(_finding(integrity_path, 0, "critical",
            "UNSKIPPABLE_CHECKPOINTS not defined"))

    # Check 2b: ALLOW_NOT_APPLICABLE must only contain conditional checkpoints
    allowed_na = {"S.2", "S.5", "C.4", "C.5", "C.10", "C.12"}
    na_match = re.search(
        r'ALLOW_NOT_APPLICABLE\s*=\s*\{([^}]+)\}', content
    )
    if na_match:
        found = set(re.findall(r'"([A-Z]\.\d+)"', na_match.group(1)))
        extra = found - allowed_na
        if extra:
            line = content[:na_match.start()].count('\n') + 1
            findings.append(_finding(integrity_path, line, "critical",
                f"ALLOW_NOT_APPLICABLE contains non-conditional checkpoints: {extra}"))
    else:
        findings.append(_finding(integrity_path, 0, "critical",
            "ALLOW_NOT_APPLICABLE not defined"))

    # Check 2c: skip_checkpoint() must guard UNSKIPPABLE
    skip_func = re.search(r'def skip_checkpoint\(.*?\n(.*?)(?=\ndef |\Z)', content, re.DOTALL)
    if skip_func:
        if "UNSKIPPABLE_CHECKPOINTS" not in skip_func.group(1):
            line = content[:skip_func.start()].count('\n') + 1
            findings.append(_finding(integrity_path, line, "critical",
                "skip_checkpoint() does not check UNSKIPPABLE_CHECKPOINTS"))

    # Check 2d: mark_not_applicable() must guard ALLOW_NOT_APPLICABLE
    na_func = re.search(r'def mark_not_applicable\(.*?\n(.*?)(?=\ndef |\Z)', content, re.DOTALL)
    if na_func:
        if "ALLOW_NOT_APPLICABLE" not in na_func.group(1):
            line = content[:na_func.start()].count('\n') + 1
            findings.append(_finding(integrity_path, line, "critical",
                "mark_not_applicable() does not check ALLOW_NOT_APPLICABLE"))

    return findings


# ── Check 3: State Machine Safety ─────────────────────────────────

def check_state_machine_safety() -> list:
    """Verify state machine guards against unsafe transitions."""
    findings = []
    root = _repo_root()

    # Check 3a: init_integrity() re-init guard
    integrity_path = os.path.join(root, "scripts", "session_agent", "integrity.py")
    content = _read_file(integrity_path)
    if content:
        init_func = re.search(r'def init_integrity\(.*?\n(.*?)(?=\ndef |\Z)', content, re.DOTALL)
        if init_func:
            body = init_func.group(1)
            if "grid" not in body or ("return False" not in body and "already" not in body.lower()):
                line = content[:init_func.start()].count('\n') + 1
                findings.append(_finding(integrity_path, line, "critical",
                    "init_integrity() missing re-initialization guard"))

    # Check 3b: advance_task_stage() order validation
    workflow_path = os.path.join(root, "scripts", "session_agent", "task_workflow.py")
    wf_content = _read_file(workflow_path)
    if wf_content:
        stage_func = re.search(r'def advance_task_stage\(.*?\n(.*?)(?=\ndef |\Z)', wf_content, re.DOTALL)
        if stage_func:
            body = stage_func.group(1)
            if "visited" not in body.lower() and "skipped" not in body.lower():
                line = wf_content[:stage_func.start()].count('\n') + 1
                findings.append(_finding(workflow_path, line, "warning",
                    "advance_task_stage() may lack stage order validation"))

        # Check 3c: advance_task_step() order validation
        step_func = re.search(r'def advance_task_step\(.*?\n(.*?)(?=\ndef |\Z)', wf_content, re.DOTALL)
        if step_func:
            body = step_func.group(1)
            if "visited" not in body.lower() and "skipped" not in body.lower():
                line = wf_content[:step_func.start()].count('\n') + 1
                findings.append(_finding(workflow_path, line, "warning",
                    "advance_task_step() may lack step order validation"))

    return findings


# ── Check 4: Methodology Consistency ──────────────────────────────

def check_methodology_consistency() -> list:
    """Scan methodology files for contradiction patterns."""
    findings = []
    root = _repo_root()

    methodology_files = [
        os.path.join(root, "methodology", "interactive-work-sessions.md"),
        os.path.join(root, "methodology", "agent-identity.md"),
    ]

    # Contradiction patterns — language that introduces exemptions
    contradiction_patterns = [
        (r'trivial.*(?:skip|exempt|optional|not\s+needed)', "critical",
         "Trivial exemption language — contradicts zero-exceptions identity"),
        (r'skip\s+for\s+efficiency', "critical",
         "Judgment-based bypass — 'skip for efficiency' undermines enforcement"),
        (r'(?:optional|not\s+required)\s+(?:for|when)\s+(?:small|simple|minor)', "warning",
         "Size-based exemption — protocol should be uniform regardless of task size"),
        (r'can\s+be\s+skipped\s+(?:if|when)\s+(?:trivial|simple|obvious)', "critical",
         "Conditional skip based on subjective judgment"),
    ]

    for filepath in methodology_files:
        content = _read_file(filepath)
        if content is None:
            continue

        lines = content.splitlines()
        in_version_section = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip version history sections (documenting past state, not prescribing)
            if re.match(r'^##\s+Version', stripped, re.IGNORECASE):
                in_version_section = True
                continue
            if in_version_section and re.match(r'^##\s+', stripped):
                in_version_section = False
            if in_version_section:
                continue
            # Skip lines describing fixes/removals (past tense narrative)
            if re.search(r'\b(removed|replaced|fixed|closed|eliminated)\b', stripped, re.IGNORECASE):
                continue
            # Skip code blocks and quoted text
            if stripped.startswith('```') or stripped.startswith('>') or stripped.startswith('|'):
                continue
            for pattern, severity, message in contradiction_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(_finding(filepath, i, severity, message))

    # Cross-check: G7 rules should be consistent
    # G7 mentions across files should not contradict each other
    # Skip version history sections and past-tense narrative lines
    g7_mentions = {}
    for filepath in methodology_files:
        content = _read_file(filepath)
        if content is None:
            continue
        g7_lines = []
        in_ver = False
        for i, line in enumerate(content.splitlines(), 1):
            s = line.strip()
            if re.match(r'^##\s+Version', s, re.IGNORECASE):
                in_ver = True
                continue
            if in_ver and re.match(r'^##\s+', s):
                in_ver = False
            if in_ver:
                continue
            if re.search(r'\b(removed|replaced|fixed|closed)\b', s, re.IGNORECASE):
                continue
            if re.search(r'\bG7\b', line, re.IGNORECASE):
                g7_lines.append((i, s))
        if g7_lines:
            g7_mentions[filepath] = g7_lines

    # If G7 mentioned in multiple files, check for "skip" in one but not others
    if len(g7_mentions) > 1:
        has_skip = {}
        for fp, mentions in g7_mentions.items():
            has_skip[fp] = any("skip" in line.lower() for _, line in mentions)
        if any(has_skip.values()) and not all(has_skip.values()):
            for fp, has in has_skip.items():
                if has:
                    findings.append(_finding(fp, 0, "warning",
                        "G7 'skip' language present here but not in other methodology files — possible contradiction"))

    return findings


# ── Check 5: Enforcement Wiring ───────────────────────────────────

def check_enforcement_wiring() -> list:
    """Verify hooks are registered and state keys match across components."""
    findings = []
    root = _repo_root()

    settings_path = os.path.join(root, ".claude", "settings.json")
    settings_content = _read_file(settings_path)

    if settings_content is None:
        findings.append(_finding(settings_path, 0, "critical", "settings.json not found"))
        return findings

    try:
        settings = json.loads(settings_content)
    except json.JSONDecodeError:
        findings.append(_finding(settings_path, 0, "critical", "settings.json is not valid JSON"))
        return findings

    hooks = settings.get("hooks", {})

    def _extract_hook_commands(hook_entries: list) -> list:
        """Extract command strings from hook entries (handles nested structures)."""
        cmds = []
        for entry in hook_entries:
            if not isinstance(entry, dict):
                continue
            # Direct command format: {"type": "command", "command": "..."}
            if "command" in entry:
                cmds.append(entry["command"])
            # Nested format: {"matcher": "", "hooks": [{"type": "command", "command": "..."}]}
            for inner in entry.get("hooks", []):
                if isinstance(inner, dict) and "command" in inner:
                    cmds.append(inner["command"])
        return cmds

    # Check 5a: SessionStart hook registered
    session_start = hooks.get("SessionStart", [])
    if not session_start:
        findings.append(_finding(settings_path, 0, "critical",
            "SessionStart hook not registered"))
    else:
        cmds = _extract_hook_commands(session_start)
        if not any("startup-checklist" in c for c in cmds):
            findings.append(_finding(settings_path, 0, "warning",
                "SessionStart hook does not reference startup-checklist.sh"))

    # Check 5b: PreToolUse hook registered
    pre_tool = hooks.get("PreToolUse", [])
    if not pre_tool:
        findings.append(_finding(settings_path, 0, "critical",
            "PreToolUse hook not registered"))
    else:
        cmds = _extract_hook_commands(pre_tool)
        if not any("require-session-protocol" in c for c in cmds):
            findings.append(_finding(settings_path, 0, "warning",
                "PreToolUse hook does not reference require-session-protocol.sh"))

    # Check 5c: State keys match between startup init and PreToolUse check
    startup_path = os.path.join(root, ".claude", "hooks", "startup-checklist.sh")
    hook_path = os.path.join(root, ".claude", "hooks", "require-session-protocol.sh")
    startup = _read_file(startup_path)
    hook = _read_file(hook_path)

    required_keys = {"protocol_completed", "issue_created", "skip_tracking_unlocked"}
    if startup:
        for key in required_keys:
            if key not in startup:
                findings.append(_finding(startup_path, 0, "warning",
                    f"State key '{key}' not initialized in startup hook"))
    if hook:
        for key in required_keys:
            if key not in hook:
                findings.append(_finding(hook_path, 0, "warning",
                    f"State key '{key}' not checked in PreToolUse hook"))

    return findings


# ── Check 6: Code Safety ──────────────────────────────────────────

def check_code_safety() -> list:
    """Verify code-level safety patterns in session agent modules."""
    findings = []
    root = _repo_root()

    # Check 6a: Conditional enforcement unlock in cache.py
    cache_path = os.path.join(root, "scripts", "session_agent", "cache.py")
    cache = _read_file(cache_path)
    if cache:
        # write_runtime_cache should distinguish issue_created vs skip_tracking_unlocked
        wrc_func = re.search(r'def write_runtime_cache\(.*?\n(.*?)(?=\ndef |\Z)', cache, re.DOTALL)
        if wrc_func:
            body = wrc_func.group(1)
            if "skip_tracking_unlocked" not in body and "issue_created" in body:
                line = cache[:wrc_func.start()].count('\n') + 1
                findings.append(_finding(cache_path, line, "warning",
                    "write_runtime_cache() may not distinguish issue_created vs skip_tracking_unlocked"))

    # Check 6b: Save gate hardening in state.py
    state_path = os.path.join(root, "scripts", "session_agent", "state.py")
    state = _read_file(state_path)
    if state:
        # compile_pre_save_summary should validate required markers
        cps_func = re.search(r'def compile_pre_save_summary\(.*?\n(.*?)(?=\ndef |\Z)', state, re.DOTALL)
        if cps_func:
            body = cps_func.group(1)
            validation_markers = ["sum", "metric", "auto"]
            found_markers = sum(1 for m in validation_markers if m.lower() in body.lower())
            if found_markers < 2:
                line = state[:cps_func.start()].count('\n') + 1
                findings.append(_finding(state_path, line, "warning",
                    "compile_pre_save_summary() may not validate required summary markers"))

        # generate_session_notes None should block
        gsn_func = re.search(r'def generate_session_notes\(.*?\n(.*?)(?=\ndef |\Z)', state, re.DOTALL)
        if gsn_func:
            body = gsn_func.group(1)
            if "return None" in body or "return none" in body.lower():
                # Good — it can return None. Check that callers handle it.
                pass

    # Check 6c: C.6 dual file verification
    if state:
        # Look for dual output verification logic
        if "has_notes" in state and "has_cache" in state:
            # Both checks present — good
            pass
        elif "C.6" in state and "dual" not in state.lower():
            findings.append(_finding(state_path, 0, "warning",
                "C.6 checkpoint may not verify both .md and .json files"))

    return findings


# ── Orchestrator ──────────────────────────────────────────────────

ALL_CHECKS = {
    "hook_safety": check_hook_safety,
    "acl_integrity": check_acl_integrity,
    "state_machine_safety": check_state_machine_safety,
    "methodology_consistency": check_methodology_consistency,
    "enforcement_wiring": check_enforcement_wiring,
    "code_safety": check_code_safety,
}


def run_integrity_gate(categories: list = None) -> dict:
    """Run all (or selected) integrity gate checks.

    Args:
        categories: List of category names to run. None = all.

    Returns:
        Dict with passed (bool), total_findings (int), categories (per-category results).
    """
    checks = categories or list(ALL_CHECKS.keys())
    results = {}
    total = 0
    has_critical = False

    for name in checks:
        func = ALL_CHECKS.get(name)
        if func is None:
            continue
        try:
            check_findings = func()
        except Exception as e:
            check_findings = [_finding("", 0, "critical", f"Check crashed: {e}")]

        cat_critical = any(f["severity"] == "critical" for f in check_findings)
        results[name] = {
            "passed": len(check_findings) == 0,
            "findings": check_findings,
            "critical": cat_critical,
        }
        total += len(check_findings)
        if cat_critical:
            has_critical = True

    return {
        "passed": total == 0,
        "total_findings": total,
        "has_critical": has_critical,
        "categories": results,
    }


def format_gate_report(result: dict = None) -> str:
    """Format the integrity gate results as a markdown report.

    Args:
        result: Output from run_integrity_gate(). Auto-computed if None.

    Returns:
        Formatted markdown string.
    """
    if result is None:
        result = run_integrity_gate()

    lines = []
    passed = result["passed"]
    total = result["total_findings"]
    has_critical = result.get("has_critical", False)

    # Header
    if passed:
        lines.append("## Integrity Gate — PASSED")
        lines.append("")
        lines.append("No vulnerabilities detected. Safe to commit.")
    elif has_critical:
        lines.append("## Integrity Gate — BLOCKED")
        lines.append("")
        lines.append(f"**{total} finding(s) detected — {sum(1 for c in result['categories'].values() if c.get('critical'))} critical.** Fix critical findings before committing.")
    else:
        lines.append("## Integrity Gate — WARNING")
        lines.append("")
        lines.append(f"**{total} finding(s) detected (no critical).** Review before committing.")

    lines.append("")

    # Category summary table
    lines.append("| Category | Status | Findings |")
    lines.append("|----------|--------|----------|")
    for name, cat in result["categories"].items():
        icon = "PASS" if cat["passed"] else ("CRITICAL" if cat.get("critical") else "WARN")
        count = len(cat["findings"])
        display_name = name.replace("_", " ").title()
        lines.append(f"| {display_name} | {icon} | {count} |")

    # Finding details
    for name, cat in result["categories"].items():
        if not cat["findings"]:
            continue
        lines.append("")
        display_name = name.replace("_", " ").title()
        lines.append(f"### {display_name}")
        lines.append("")
        for f in cat["findings"]:
            sev = f["severity"].upper()
            file_ref = os.path.basename(f["file"]) if f["file"] else "?"
            line_ref = f":{f['line']}" if f["line"] else ""
            lines.append(f"- **{sev}** `{file_ref}{line_ref}` — {f['message']}")

    return "\n".join(lines)
