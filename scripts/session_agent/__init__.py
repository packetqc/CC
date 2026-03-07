"""Session Agent — modular package for session persistence and GitHub sync.

This package was refactored from the monolithic session_agent.py (3169 lines)
into focused sub-modules. All public APIs are re-exported here for backward
compatibility — existing imports like `from scripts.session_agent import X`
continue to work unchanged.

Sub-modules:
    cache.py          — Runtime cache core (read/write/find/commit/sync)
    request_types.py  — REQUEST_TYPE_KEYWORDS taxonomy + detect_request_type
    documentation.py  — Doc debt detection (check_todo, evaluate_debt)
    engineering.py    — Engineering cycle state machine + stage labels
    addons.py         — Add-on pipeline (append, read, staged, ticket sync)
    state.py          — Session state helpers (todos, phase, PRs, git, time, notes)
    helpers.py        — Shared utilities (_get_gh_helper)
    recover.py        — Branch-based work recovery from stranded claude/* branches
    recall.py         — Deep memory search across all knowledge channels
    integrity.py      — Integrity check state machine (29 checkpoints, 4 sections)
    context_budget.py — Context pressure estimation, pre-flight checks, heavy op recovery
    integrity_gate.py — Pre-commit vulnerability prevention (6 check categories)
    watchdog.py       — Watchdog + SessionAgent classes
    cli.py            — CLI entry point (main())

Authors: Martin Paquet, Claude (Anthropic)
License: MIT
Knowledge version: v100
"""

# ── Cache core ───────────────────────────────────────────────────
from .cache import (
    RUNTIME_CACHE_LEGACY,
    ENFORCEMENT_STATE_FILE,
    FLUSH_DELAY_SECONDS,
    update_enforcement_state,
    _session_id_to_suffix,
    _runtime_cache_filename,
    _find_runtime_cache,
    commit_cache,
    write_runtime_cache,
    init_skip_cache,
    update_session_data,
    read_runtime_cache,
    post_exchange,
    queue_pending_comment,
    flush_pending_comments,
    pending_comments_count,
    resync_to_issue,
    activate_tracking,
    sync_remote_caches,
)

# ── Request types ────────────────────────────────────────────────
from .request_types import (
    REQUEST_TYPE_KEYWORDS,
    detect_request_type,
)

# ── Documentation debt ───────────────────────────────────────────
from .documentation import (
    check_todo_documentation,
    evaluate_documentation_debt,
)

# ── Engineering cycle ────────────────────────────────────────────
from .engineering import (
    ENGINEERING_STAGES,
    ENGINEERING_CROSS_CUTTING,
    ENGINEERING_STAGE_INDEX,
    init_engineering_cycle,
    advance_engineering_stage,
    get_engineering_stage,
    get_engineering_stage_name,
    get_engineering_stage_index,
    get_engineering_cycle_summary,
    sync_engineering_stage_label,
)

# ── Add-ons ──────────────────────────────────────────────────────
from .addons import (
    append_request_addon,
    read_request_addons,
    append_request_addon_staged,
    get_addons_by_stage,
    _append_staged_addon,
    sync_addon_to_ticket,
)

# ── Session state persistence ────────────────────────────────────
from .state import (
    load_session_todos,
    trim_session_cache,
    trim_all_session_caches,
    update_todo_snapshot,
    update_session_phase,
    append_pr_number,
    update_git_state,
    append_time_marker,
    update_elevation_status,
    update_default_branch,
    update_work_summary,
    append_error,
    update_issue_comments_count,
    generate_session_notes,
    check_pending_todos,
    defer_todos_to_next_session,
    compile_pre_save_summary,
    check_doc_updates_needed,
    save_session,
)

# ── Helpers ──────────────────────────────────────────────────────
from .helpers import _get_gh_helper

# ── Recover — branch-based work recovery ────────────────────────
from .recover import (
    scan_stranded_branches,
    cherry_pick_commits,
    apply_diff_from_branch,
    format_recovery_report,
)

# ── Recall — deep memory search ─────────────────────────────────
from .recall import (
    search_session_caches,
    search_session_notes,
    search_commit_messages,
    search_file_content,
    search_github_issues,
    search_github_issue_comments,
    search_methodology,
    search_publications,
    search_patterns_lessons,
    search_minds,
    recall,
    format_recall_report,
)

# ── Task Workflow ────────────────────────────────────────────────
from .task_workflow import (
    TASK_WORKFLOW_STAGES,
    TASK_WORKFLOW_STAGE_INDEX,
    TASK_WORKFLOW_STAGE_LABELS,
    INITIAL_STAGE_STEPS,
    INITIAL_STEP_LABELS,
    IMPLEMENT_STAGE_STEPS,
    IMPLEMENT_STEP_LABELS,
    COMPLETION_STAGE_STEPS,
    COMPLETION_STEP_LABELS,
    VALIDATION_ELIGIBLE_STAGES,
    INITIAL_VALIDATION_CHECKS,
    COMMAND_REGISTRY,
    detect_command,
    init_task_workflow,
    advance_task_stage,
    advance_task_step,
    set_task_title,
    set_task_description,
    set_task_project,
    set_task_issue,
    mark_modifications_occurred,
    create_sub_task,
    start_sub_task,
    complete_sub_task,
    fail_sub_task,
    get_sub_tasks,
    get_sub_task,
    get_sub_task_summary,
    parse_prompt,
    detect_project,
    check_documentation_needed,
    check_validation_needed,
    get_validation_checks,
    record_validation_result,
    complete_stage_validation,
    skip_all_validation,
    get_validation_results,
    get_stage_validation_report,
    add_unit_test,
    run_unit_test,
    get_unit_tests,
    get_unit_test_format,
    generate_task_report,
    persist_task_report,
    get_task_workflow,
    get_task_stage,
    get_task_step,
    get_task_workflow_summary,
    format_workflow_status,
    run_task_workflow_healthcheck,
    format_task_workflow_healthcheck_report,
)

# ── Integrity Check ────────────────────────────────────────────────
from .integrity import (
    CHECKPOINTS as INTEGRITY_CHECKPOINTS,
    SECTION_ORDER as INTEGRITY_SECTIONS,
    STATUS_ICONS as INTEGRITY_STATUS_ICONS,
    init_integrity,
    pass_checkpoint,
    fail_checkpoint,
    skip_checkpoint,
    mark_not_applicable,
    integrity_check,
    integrity_grid,
    reset_work_cycle,
    format_integrity_report,
    get_rerun_directive,
    _auto_pass,
    run_startup_integrity,
    retroactive_startup_pass,
    mark_work_action,
    mark_completion_action,
    integrity_compliance,
    run_healthcheck,
    format_healthcheck_report,
)

# ── Context Budget ──────────────────────────────────────────────
from .context_budget import (
    estimate_context_pressure,
    pre_flight_check,
    checkpoint_operation,
    update_operation_progress,
    complete_operation,
    recover_interrupted,
    partition_work,
    increment_signal,
    format_pressure_report,
    format_pre_flight_report,
)

# ── Integrity Gate — pre-commit vulnerability prevention ─────────
from .integrity_gate import (
    check_hook_safety,
    check_acl_integrity,
    check_state_machine_safety,
    check_methodology_consistency,
    check_enforcement_wiring,
    check_code_safety,
    run_integrity_gate,
    format_gate_report,
)

# ── Watchdog + Agent ─────────────────────────────────────────────
from .watchdog import (
    STATE_FILE,
    QUEUE_FILE,
    LOCK_FILE,
    Watchdog,
    SessionAgent,
    load_agent,
    feed_event,
)

# ── CLI ──────────────────────────────────────────────────────────
from .cli import main

# Allow `python -m scripts.session_agent`
__all__ = [
    # Cache
    "RUNTIME_CACHE_LEGACY", "ENFORCEMENT_STATE_FILE", "FLUSH_DELAY_SECONDS",
    "update_enforcement_state",
    "_session_id_to_suffix", "_runtime_cache_filename", "_find_runtime_cache",
    "commit_cache", "write_runtime_cache", "init_skip_cache", "update_session_data",
    "read_runtime_cache", "post_exchange",
    "queue_pending_comment", "flush_pending_comments", "pending_comments_count",
    "resync_to_issue", "activate_tracking", "sync_remote_caches",
    # Request types
    "REQUEST_TYPE_KEYWORDS", "detect_request_type",
    # Documentation
    "check_todo_documentation", "evaluate_documentation_debt",
    # Engineering cycle
    "ENGINEERING_STAGES", "ENGINEERING_CROSS_CUTTING", "ENGINEERING_STAGE_INDEX",
    "init_engineering_cycle", "advance_engineering_stage",
    "get_engineering_stage", "get_engineering_stage_name",
    "get_engineering_stage_index", "get_engineering_cycle_summary",
    "sync_engineering_stage_label",
    # Add-ons
    "append_request_addon", "read_request_addons",
    "append_request_addon_staged", "get_addons_by_stage",
    "_append_staged_addon", "sync_addon_to_ticket",
    # State
    "load_session_todos", "trim_session_cache", "trim_all_session_caches",
    "update_todo_snapshot", "update_session_phase", "append_pr_number",
    "update_git_state", "append_time_marker", "update_elevation_status",
    "update_default_branch", "update_work_summary", "append_error",
    "update_issue_comments_count", "generate_session_notes",
    "check_pending_todos", "defer_todos_to_next_session",
    "compile_pre_save_summary", "check_doc_updates_needed", "save_session",
    # Helpers
    "_get_gh_helper",
    # Recover
    "scan_stranded_branches", "cherry_pick_commits",
    "apply_diff_from_branch", "format_recovery_report",
    # Recall
    "search_session_caches", "search_session_notes",
    "search_commit_messages", "search_file_content",
    "search_github_issues", "search_github_issue_comments",
    "search_methodology", "search_publications",
    "search_patterns_lessons", "search_minds",
    "recall", "format_recall_report",
    # Task Workflow
    "TASK_WORKFLOW_STAGES", "TASK_WORKFLOW_STAGE_INDEX", "TASK_WORKFLOW_STAGE_LABELS",
    "INITIAL_STAGE_STEPS", "INITIAL_STEP_LABELS",
    "IMPLEMENT_STAGE_STEPS", "IMPLEMENT_STEP_LABELS",
    "COMPLETION_STAGE_STEPS", "COMPLETION_STEP_LABELS",
    "COMMAND_REGISTRY", "detect_command",
    "init_task_workflow", "advance_task_stage", "advance_task_step",
    "set_task_title", "set_task_description", "set_task_project", "set_task_issue",
    "mark_modifications_occurred",
    "create_sub_task", "start_sub_task", "complete_sub_task",
    "fail_sub_task", "get_sub_tasks", "get_sub_task", "get_sub_task_summary",
    "parse_prompt", "detect_project",
    "check_documentation_needed", "get_task_workflow", "get_task_stage",
    "get_task_step", "get_task_workflow_summary", "format_workflow_status",
    "run_task_workflow_healthcheck", "format_task_workflow_healthcheck_report",
    # Integrity Check
    "INTEGRITY_CHECKPOINTS", "INTEGRITY_SECTIONS", "INTEGRITY_STATUS_ICONS",
    "init_integrity", "pass_checkpoint", "fail_checkpoint",
    "skip_checkpoint", "mark_not_applicable",
    "integrity_check", "integrity_grid", "reset_work_cycle",
    "format_integrity_report", "get_rerun_directive",
    "_auto_pass", "run_startup_integrity",
    "retroactive_startup_pass", "mark_work_action",
    "mark_completion_action", "integrity_compliance",
    "run_healthcheck", "format_healthcheck_report",
    # Integrity Gate
    "check_hook_safety", "check_acl_integrity",
    "check_state_machine_safety", "check_methodology_consistency",
    "check_enforcement_wiring", "check_code_safety",
    "run_integrity_gate", "format_gate_report",
    # Watchdog + Agent
    "STATE_FILE", "QUEUE_FILE", "LOCK_FILE",
    "Watchdog", "SessionAgent", "load_agent", "feed_event",
    # CLI
    "main",
]
