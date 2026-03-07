# Task Workflow

The task workflow is an 8-stage state machine that tracks where a task/issue sits in its lifecycle, from initial prompt reception through completion. It persists in the session runtime cache and crosses session boundaries via the startup hook continuity layer.

## Two Workflow Levels

Two workflow levels coexist in the knowledge system:

| Level | Module | Scope | Stages |
|-------|--------|-------|--------|
| **Global workflow** | `engineering.py` | 10-stage engineering cycle — tracks where work is in the SDLC | analysis → planning → design → implementation → testing → validation → review → deployment → operations → improvement |
| **Task workflow** | `task_workflow.py` | 8-stage task lifecycle — tracks where a specific task/issue is in its progression | initial → plan → analyze → implement → validation → approval → documentation → completion |

Task workflow completion triggers advancement in the global engineering cycle. Most tasks require multiple sessions (workshops) to complete — this is the normal operating mode.

## Stages

```
INITIAL → PLAN → ANALYZE → IMPLEMENT → VALIDATION → APPROVAL → DOCUMENTATION → COMPLETION
   0        1       2          3            4            5            6              7
```

| # | Stage | Description | Status |
|---|-------|-------------|--------|
| 0 | **initial** | Prompt analysis, title/desc extraction, project detection, user confirmation | 9 steps implemented |
| 1 | **plan** | Work plan creation and approval | stub |
| 2 | **analyze** | Deep analysis of the request | stub |
| 3 | **implement** | Execution of the work plan | 8 steps implemented |
| 4 | **validation** | Verification and testing | stub |
| 5 | **approval** | User approval of deliverables | stub |
| 6 | **documentation** | Doc updates confirmation — project docs, knowledge, or both | rule defined |
| 7 | **completion** | Final delivery and closure | 10 steps implemented |

## Stage 1: Initial — 9 Steps

The initial stage handles everything from prompt reception to user approval before work begins.

| # | Step | Description |
|---|------|-------------|
| 1 | `analyze_prompt` | Analyze the user prompt for action words and structure |
| 2 | `extract_title` | Extract title from line 1 of the prompt |
| 3 | `extract_description` | Extract description from remaining lines |
| 4 | `confirm_title` | Confirm title with user via AskUserQuestion |
| 5 | `detect_project` | Detect project owner from **title and description** |
| 6 | `confirm_project` | Confirm project with user via AskUserQuestion (detected first + all available) |
| 7 | `persist_state` | Persist project + title + description in cache and GitHub |
| 8 | `output_details` | Output confirmed details to the user |
| 9 | `wait_approval` | Wait for user approval before proceeding to plan stage |

### Action Word Detection

The prompt parser detects action words and maps them to issue labels:

| Action word | Label |
|-------------|-------|
| review | REVIEW |
| create, add, implement, build | FEATURE |
| fix | BUG |
| update, refactor, optimize | ENHANCEMENT |
| design | DESIGN |
| investigate, diagnose, analyze | INVESTIGATION |
| document | DOCUMENTATION |
| deploy | DEPLOYMENT |
| test | TESTING |

### Project Detection

Step 5 scans **both title and description** for project references:
- Project names and aliases (weighted: title 3x, description 1x)
- Project IDs (weighted: title 3x, description 1x)
- P# references like P0, P1, P2 (weighted: 4x regardless of source)

Returns confidence level: high (score >= 3), medium (score >= 2), low (score < 2).

## Stage 3: Implement — 8 Steps (per todo)

The implement stage enforces a work cycle for **each todo item** in the plan. The cycle repeats until all todos are complete.

| # | Step | Description |
|---|------|-------------|
| 1 | `remote_check` | Strategic remote check before modifying shared files |
| 2 | `executing` | Execute the current todo item |
| 3 | `commit` | Progressive commit — each todo = own commit |
| 4 | `push` | Push committed changes to remote branch |
| 5 | `cache_update` | Update session cache (todo_snapshot, files_modified, work_summary) |
| 6 | `issue_comment` | Post todo start/completion as issue comment (Gate G7) |
| 7 | `mark_modifications` | Flag modifications for documentation cross-cut (auto-calls `mark_modifications_occurred()`) |
| 8 | `next_todo` | Advance to next todo or signal implement stage complete |

### Work Cycle Per Todo

```
For each todo in the plan:
  advance_task_step('remote_check')     → git fetch + diff check
  advance_task_step('executing')        → do the work
  advance_task_step('commit')           → git add + commit
  advance_task_step('push')             → git push
  advance_task_step('cache_update')     → update_session_data(todo_snapshot, files_modified)
  advance_task_step('issue_comment')    → post_exchange() with todo status
  advance_task_step('mark_modifications') → auto-triggers mark_modifications_occurred()
  advance_task_step('next_todo')        → loop or advance_task_stage('validation')
```

### Why This Matters

The implement stage was a stub (`executing` only). Validation quiz failures showed 3 recurring issues:
- **Progressive commits**: changes batched into one giant commit at the end
- **Cache updates (G4)**: todo_snapshot not updated after each step
- **Issue comments (G7)**: no per-todo lifecycle comments

The 8-step cycle makes each requirement an explicit step that is tracked in step_history and visible in the I3 Tasks Workflow Viewer.

## Stage 7: Completion — 10 Steps

The completion stage handles final delivery: data compilation, commit, push, PR, merge, and closure. The compiled data feeds the web interfaces (I1 Session Viewer, I3 Tasks Workflow Viewer).

| # | Step | Description |
|---|------|-------------|
| 1 | `pre_save_summary` | Compile pre-save summary (metrics, time blocks, self-assessment) |
| 2 | `generate_notes` | Generate session notes markdown for web pipeline |
| 3 | `finalize_cache` | Finalize runtime cache (session_phase → complete) |
| 4 | `compile_sessions` | Compile sessions.json for I1 Session Viewer |
| 5 | `compile_tasks` | Compile tasks.json for I3 Tasks Workflow Viewer |
| 6 | `commit_final` | Final commit with session notes, cache, and compiled data |
| 7 | `push_final` | Push all changes to remote branch |
| 8 | `create_pr` | Create PR to default branch |
| 9 | `merge_pr` | Merge PR (elevated) or guide user (semi-auto) |
| 10 | `post_close` | Post closing report and close issue |

### Completion Sequence

```
advance_task_step('pre_save_summary')  → compile_pre_save_summary()
advance_task_step('generate_notes')    → generate_session_notes()
advance_task_step('finalize_cache')    → update_session_data('session_phase', 'complete')
advance_task_step('compile_sessions')  → python3 scripts/generate_sessions.py --incremental
advance_task_step('compile_tasks')     → python3 scripts/compile_tasks.py
advance_task_step('commit_final')      → git add + commit (notes, cache, data)
advance_task_step('push_final')        → git push
advance_task_step('create_pr')         → gh_helper.py pr_create()
advance_task_step('merge_pr')          → gh_helper.py pr_merge() or ⏸ guide
advance_task_step('post_close')        → post closing report + close issue
```

### Why This Matters

The completion stage ensures compiled data (sessions.json, tasks.json) reaches the default branch BEFORE the session ends. Without this, the I1 Session Viewer and I3 Tasks Workflow Viewer show stale data until the next session compiles them. The 10-step sequence makes each delivery step explicit and tracked.

## Documentation Cross-Cut

At each stage boundary where modifications occurred to the system or project, the workflow triggers a documentation check via `check_documentation_needed()`. The user is asked via AskUserQuestion with **4 options**:

- **Update project documentation** — only the project's own docs now
- **Update knowledge only** — only the knowledge system docs now
- **Update both** — both project and knowledge docs now
- **Defer to documentation stage** — skip doc updates now, handle at stage 6 (documentation)

The defer option allows the user to postpone doc updates to the dedicated documentation stage. This is the normal flow when the implement stage is focused on code delivery and documentation will be handled systematically later.

The `modifications_occurred` flag is set via `mark_modifications_occurred()` during work. It resets at each stage transition.

## Validation Cross-Cut

At each stage completion, the workflow optionally triggers a **validation quiz** — a series of AskUserQuestion checkpoints confirming that expectations were met for that stage.

### Eligible Stages

Validation runs for stages **initial through validation** (indices 0–4). It does NOT run for approval, documentation, or completion stages.

```
INITIAL → PLAN → ANALYZE → IMPLEMENT → VALIDATION → [no validation after this]
  ✓         ✓       ✓          ✓           ✓       APPROVAL → DOCUMENTATION → COMPLETION
```

### Validation Quiz Flow

At stage completion, the session asks: "Would you like to run the validation report?"

Each validation check is an AskUserQuestion with **exactly 4 options** (mandatory format):
- **Passed** — this checkpoint was met
- **Failed** — this checkpoint was not met
- **Skip this** — skip this one validation point (recorded as `skip` with `skipped=True`)
- **Skip all** — skip all remaining checks for this stage (all remaining recorded as `skip`)

**Enforcement**: All 4 options MUST appear on every AskUserQuestion. Never present only 3 options (Pass/Fail/Skip). The "Skip this" and "Skip all" are distinct choices — the user decides granularity. AskUserQuestion groups up to 4 checks per popup (API limit: 4 questions per call), each with the same 4-option format.

Even when skipped (partially or entirely), the validation status is persisted in the task workflow report. A skip IS a status — it is never omitted.

**Skip all behavior**: When the user selects "Skip all" on any check, ALL remaining checks in that stage are immediately recorded as `skip` with `skipped=True`. No further AskUserQuestion popups for that stage. The `complete_stage_validation(stage, skipped=False)` is called (the stage was not entirely skipped — partial answers exist).

### Initial Stage Validation (9 checks)

| # | Check ID | Question |
|---|----------|----------|
| 1 | `analyze_prompt` | Was the prompt correctly analyzed for action words and structure? |
| 2 | `extract_title` | Was the title correctly extracted from line 1 of the prompt? |
| 3 | `extract_description` | Was the description correctly extracted from remaining lines? |
| 4 | `confirm_title` | Was the title confirmed with the user via AskUserQuestion? |
| 5 | `detect_project` | Was the project correctly detected from title and description? |
| 6 | `confirm_project` | Was the project confirmed with the user via AskUserQuestion? |
| 7 | `persist_state` | Was state persisted in cache and GitHub issue created? |
| 8 | `output_details` | Were the confirmed details output to the user? |
| 9 | `wait_approval` | Did the session wait for user approval before proceeding? |

### Unit Tests

Unit tests validate stage expectations from 3 sources:

| Source | When | How |
|--------|------|-----|
| **User prompt** | At task description parse time | Embedded in the prompt text |
| **User mid-session** | During work | User says "add unit test: stage / description / expected" |
| **Claude-generated** | If no user tests provided | Generated from task analysis |

Claude provides the test format on request via `get_unit_test_format()`. Each test targets a specific stage, describes what it verifies, and has an expected outcome. Tests are run during the validation quiz and results persist alongside validation checks.

### Report Persistence

Task workflow reports and dashboard updates are persisted to the remote default branch as soon as each one is generated — not batched at save time. This ensures real-time visibility in the I3 Tasks Workflow Viewer.

```
validation result → record in cache → compile tasks.json → commit → push → PR → merge
```

## Persistence

The task workflow state persists in the session runtime cache under `session_data.task_workflow`:

```json
{
  "current_stage": "initial",
  "current_stage_index": 0,
  "current_step": "analyze_prompt",
  "current_step_index": 0,
  "title": "...",
  "description": "...",
  "issue_number": 0,
  "project": null,
  "modifications_occurred": false,
  "validation_results": {},
  "validation_skipped_entirely": false,
  "unit_tests": [],
  "stage_history": [...],
  "step_history": [...]
}
```

**Dual persistence**: cache (local/fast) + GitHub issue (remote/durable). The task workflow state crosses session boundaries via the startup hook continuity layer — pending tasks are displayed at next session start.

## Relationship to Other Methodology

This file is the operational state machine within the 6 mandatory methodology files loaded at wakeup step 0.1:

- **session-protocol.md**: Stage 1 (initial) replaces the step sequence in `session-protocol.md` § "2. Task Received". The session protocol's enforcement gates (G1: issue before edits, G2: cache initialized) remain as checkpoints, but the step-by-step flow is driven by this task workflow.
- **agent-identity.md**: The identity's 5 principles are enforced through this workflow — the integrity grid (29 checkpoints) maps directly to task workflow stages and steps. Principle §2 (zero judgment) means every request type enters the same 8-stage pipeline.
- **engineering-taxonomy.md**: The 11 request types feed `parse_prompt()` for prompt classification; the 10 engineering cycle stages inform stage transitions and STAGE:/STEP: label sync on GitHub issues. The taxonomy is the classification layer, this workflow is the execution layer.
- **interactive-work-sessions.md**: Defines the 5 persistence channels and resilience patterns that this workflow writes to — cache, issue comments, session notes, git, startup hook.
- **working-style.md**: The user's bilingual, visual, rapid-iteration style shapes how this workflow presents confirmations (AskUserQuestion) and status updates.

```
session-protocol § 2 (pointer) → task_workflow Stage 1 (driver)
                                   ↓ parse_prompt() → engineering-taxonomy: 11 request types
                                   ↓ G1 checkpoint (issue created + type label)
                                   ↓ G2 checkpoint (cache initialized)
                                 → task_workflow Stage 2+ (execution)
                                   ↓ engineering-taxonomy: 10 stages → STAGE:/STEP: labels
                                   ↓ agent-identity: integrity grid tracks compliance
                                   ↓ interactive-work-sessions: 5 persistence channels
```

**The task moves through states in the global engineering cycle**: the task workflow's 8 stages (initial → completion) drive the work, while the engineering taxonomy's 10 stages (analysis → improvement) classify the nature of the work at each point. A task can be in task stage "implement" while the engineering activity is "testing" — the two taxonomies are complementary, not competing.

## API Reference

### Initialization
- `init_task_workflow(request_description, title, issue_number)` — Create workflow in cache
- `parse_prompt(prompt)` — Steps 1-3: analyze prompt, extract title and description

### Stage/Step Advancement
- `advance_task_stage(target_stage, reason)` — Transition to a new stage
- `advance_task_step(target_step)` — Advance to next step within current stage

### State Setters
- `set_task_title(title)` — Set confirmed title
- `set_task_description(description)` — Set extracted description
- `set_task_project(project)` — Set confirmed project
- `set_task_issue(issue_number)` — Set GitHub issue number
- `mark_modifications_occurred()` — Flag modifications for doc cross-cut

### Queries
- `get_task_workflow()` — Full workflow state dict
- `get_task_stage()` — Current stage name
- `get_task_step()` — Current step name
- `get_task_workflow_summary()` — Compact summary for display
- `format_workflow_status()` — Formatted status string with progress bar

### Detection
- `detect_project(title, description, available_projects)` — Step 5: project detection
- `check_documentation_needed()` — Documentation cross-cut check

### Validation Cross-Cut
- `check_validation_needed(stage)` — Check if validation should run for a stage
- `get_validation_checks(stage)` — Get checkpoints for a stage
- `record_validation_result(stage, check_id, result, skipped)` — Record one check result
- `complete_stage_validation(stage, skipped)` — Mark stage validation complete
- `skip_all_validation()` — Skip all validation for the task
- `get_validation_results()` — Get all validation results
- `get_stage_validation_report(stage)` — Get report for one stage
- `generate_task_report(stage)` — Generate full or stage-specific report

### Unit Tests
- `add_unit_test(stage, description, expected, source)` — Add a test (source: user_prompt/user_session/claude)
- `run_unit_test(test_id, result)` — Record test result (passed/failed)
- `get_unit_tests(stage)` — Get tests, optionally by stage
- `get_unit_test_format()` — Return format spec for user reference

### Data Pipeline
- `scripts/compile_tasks.py` — Compile task data → `docs/data/tasks.json`

## Web Interface — I3 Tasks Workflow Viewer

Interactive web interface for tracking task progression. Located at `/interfaces/task-workflow/`.

### Views

| View | Content |
|------|---------|
| **Overview** | Task list with stage progress bars, validation status, test counts. Filter by stage. |
| **Detail** | Selected task: timeline, stage history, step history, stats. |
| **Validation** | Stage validation cards, individual checks table, unit tests table. |
| **Progression** | Multi-task charts: stage distribution (bar), validation status (doughnut). Related tasks table. |

### Files
- `docs/interfaces/task-workflow/index.md` — EN markup
- `docs/interfaces/task-workflow/task-workflow.js` — Data loading + rendering
- `docs/interfaces/task-workflow/task-workflow.css` — Styling
- `docs/fr/interfaces/task-workflow/index.md` — FR mirror
- `docs/data/tasks.json` — Data source (compiled by `compile_tasks.py`)

### Integration
- Interface hub: `/interfaces/` (EN) and `/fr/interfaces/` (FR)
- Main Navigator: widget definition with `center:true` routing
- URL params: `?task=task-763` auto-selects a task

## STAGE:/STEP: Label Sync (v57)

Every `advance_task_stage()` and `advance_task_step()` call automatically syncs a GitHub issue label:

| Function | Label pattern | Example | Behavior |
|----------|--------------|---------|----------|
| `advance_task_stage()` | `STAGE:<name>` | `STAGE:implement` | Removes previous `STAGE:*`, adds new |
| `advance_task_step()` | `STEP:<name>` | `STEP:confirm_title` | Removes previous `STEP:*`, adds new |

Implementation: `_sync_stage_label()` and `_sync_step_label()` in `task_workflow.py`. Both are non-fatal — if the GitHub API is unavailable (no token, network error), the label sync silently fails and the workflow proceeds. Labels are created on-demand with stage-specific colors.

**Stage label colors**: initial=#6f42c1, plan=#0366d6, analyze=#0891b2, implement=#2ea44f, validation=#d29922, approval=#f97316, documentation=#8b5cf6, completion=#28a745.

## Task Continuation Protocol (v57)

A task can span multiple sessions. The "Continue issue #N" entry prompt resumes work from a previous session's last known state.

**Flow**:
1. User enters `Continue issue #766` (or similar pattern)
2. `parse_prompt()` detects "continue" action word
3. Session reads previous cache for task workflow state (via `compile_tasks.py` → `tasks.json`)
4. `AskUserQuestion` popup confirms the existing title
5. New session cache links to the same `issue_number`
6. Work resumes from last known stage/step

**Key rules**:
- Same issue, new session — continuity without duplication
- Task workflow state is inherited via the runtime cache chain
- All exchanges posted to the same issue — complete chronological record
- `compile_tasks.py` deduplicates by `issue_number` (keeps most recent `updated_at`)

## Known Issues & Session Learnings

Discovered during interactive review session (#763, 2026-03-05):

### detect_project scoring ambiguity

`detect_project()` uses weighted keyword scoring against project aliases. When the description contains generic terms (e.g., "implementation", "execution", "workflow"), **all projects score identically** because every project dict has `aliases` that partially match common words. Result: P0 wins by position, not relevance.

**Impact**: The `confidence: "high"` is misleading when all 10 projects tie at score 4. The confirm_project popup should display the tie explicitly so the user makes an informed choice.

**Fix needed**: Either (1) require minimum score differential for "high" confidence, (2) use repo context (current repo = P0) as tiebreaker, or (3) flag ties as `confidence: "ambiguous"` in the result.

### record_validation_result appends, doesn't replace

When validation is rerun for the same stage, `record_validation_result()` appends new entries to the `checks` array instead of replacing the previous run. This creates duplicate entries (old + new).

**Fix needed**: Either (1) clear previous checks for the stage before rerun, or (2) use a dict keyed by `check_id` instead of an array (last write wins).

### parse_prompt doesn't handle title:/description: prefix syntax

When the user structures their prompt as `title: X description: Y`, `parse_prompt()` returns the entire string as the title. The function does action word detection and label mapping but not structured prefix parsing.

**Current workaround**: Claude extracts title/description semantically at `advance_task_step('extract_title')` — the function assists but doesn't replace Claude's analysis.

### Emulation mode (dry-run)

The workflow state machine can be walked through without side effects (no issue, no PR, no file edits). This is valuable for:
- Reviewing the implementation interactively with the user
- Testing state transitions without consuming GitHub API calls
- Training new sessions on the expected flow

**Convention**: Use `init_task_workflow()` + step/stage advances without calling `set_task_issue()` or `write_runtime_cache()` for dry-run emulation.

## Command Detection & Sub-Task Lifecycle (v100)

Every methodology-backed command (`project create`, `harvest`, `normalize`, `pub`, `webcard`, `visual`, etc.) is a **Claude Code skill** with a **sub-task lifecycle** within the task workflow.

### Command Detection Layer

When `parse_prompt()` runs, it also calls `detect_command()` which matches the user's input against the `COMMAND_REGISTRY` — a dictionary of 42 command patterns covering 8 groups (session, harvest, content, project, live, visual, normalize, tagged-input).

**Longest-match-first**: The registry is sorted by key length descending before matching. This ensures `harvest --healthcheck` matches before `harvest`, and `normalize --fix` matches before `normalize`.

**Pattern-based matching**: Some commands use regex patterns (e.g., `#N:` tagged input, `g:board:item` board aliases) instead of literal string matching.

```python
from scripts.session_agent import detect_command

result = detect_command("project create Studio 54", "Create project Studio 54")
# → {"command": "project create", "skill": "project-create",
#    "label": "FEATURE", "methodology": "project-create.md",
#    "group": "project", "args": "Studio 54"}
```

**Return value**: Dict with `command`, `skill`, `label`, `methodology`, `description`, `group`, `args`. Returns `None` if no command matches.

### Sub-Task Lifecycle

When a command is detected, the task workflow creates a **sub-task** — a tracked child entity that mirrors the parent task structure with its own status, stage, todos, commits, and files_modified.

**Sub-task states**:

```
pending → in_progress → completed
                      → failed
```

**API**:

| Function | Purpose |
|----------|---------|
| `create_sub_task(command, skill, title, args, label, methodology, group)` | Create a sub-task entry in cache |
| `start_sub_task(sub_task_id)` | Mark sub-task as `in_progress`, set stage to `implement` |
| `complete_sub_task(sub_task_id, commits, files_modified)` | Mark sub-task as `completed`, record deliverables |
| `fail_sub_task(sub_task_id, reason)` | Mark sub-task as `failed` with error reason |
| `get_sub_tasks()` | Return list of all sub-tasks |
| `get_sub_task(sub_task_id)` | Return specific sub-task by ID |
| `get_sub_task_summary()` | Aggregated status: total, pending, in_progress, completed, failed |

**Persistence**: Sub-tasks are stored in `session_data.sub_tasks[]` in the runtime cache. Each sub-task has:

```json
{
  "id": 1,
  "command": "project create",
  "skill": "project-create",
  "title": "Create project: Studio 54",
  "args": "Studio 54",
  "label": "FEATURE",
  "methodology": "project-create.md",
  "group": "project",
  "stage": "implement",
  "status": "in_progress",
  "started_at": "2026-03-06T10:30:00Z",
  "completed_at": null,
  "todos": [],
  "commits": [],
  "files_modified": []
}
```

### Command-as-Sub-Task Flow

When a user's prompt matches a command, the execution follows this pattern:

```
parse_prompt() → detect_command() → create_sub_task()
    ↓
AskUserQuestion (title confirmation)
    ↓
create issue → write_runtime_cache()
    ↓
start_sub_task(id) → execute command skill → complete_sub_task(id)
    ↓
parent task continues
```

**Within the implement stage** (Stage 3), each command skill executes as a tracked sub-task:

```python
from scripts.session_agent import create_sub_task, start_sub_task, complete_sub_task

# 1. Create sub-task from detected command
sub = create_sub_task(
    command=cmd["command"],
    skill=cmd["skill"],
    title=f'{cmd["description"]}: {cmd.get("args", "")}',
    args=cmd.get("args", ""),
    label=cmd["label"],
    methodology=cmd.get("methodology", ""),
    group=cmd["group"],
)

# 2. Start execution
start_sub_task(sub["id"])

# 3. Execute the skill (e.g., /project-create, /harvest, /normalize)
# ... skill execution ...

# 4. Complete with deliverables
complete_sub_task(sub["id"], commits=["abc1234"], files_modified=["projects/studio-54.md"])
```

### Skill Hierarchy

The 21 skills form a hierarchy:

```
/task-received (orchestrator) → /plan-review (classifier) → /work-cycle (executor)
    ↓                                                              ↓
detect_command()                                          command skill (sub-task)
    ↓                                                     e.g., /project-create
create_sub_task()                                                  ↓
                                                          start_sub_task()
                                                          ... execute ...
                                                          complete_sub_task()
```

**The invariant**: Commands never bypass the task workflow — they are executed **within** it. A `project create X` command becomes a sub-task tracked under the parent task, with its own lifecycle, commits, and files_modified recorded in the cache.

### Failure Handling

When a sub-task fails:

1. Call `fail_sub_task(id, reason)` — records the failure with reason and timestamp
2. The parent task does NOT automatically halt — other sub-tasks can proceed
3. The failure is posted as an issue comment (G7 compliance)
4. At save time, the pre-save summary includes sub-task status in the auto-évaluation
5. The user can choose to retry, skip, or address the failure

### 14 Command Skills + 7 Orchestration Skills

| Category | Skills | Type |
|----------|--------|------|
| **Orchestration** (7) | task-received, plan-review, work-cycle, save-protocol, integrity-check, healthcheck, github | Workflow drivers |
| **Project** (2) | project-create, project-manage | Sub-task commands |
| **Knowledge** (2) | harvest, normalize | Sub-task commands |
| **Content** (4) | pub, pub-export, webcard, profile-update | Sub-task commands |
| **Session** (3) | wakeup, resume, recall | Sub-task commands |
| **Capture** (2) | live-session, visual | Sub-task commands |
| **Routing** (1) | tagged-input | Sub-task commands |

Each command skill is backed by a methodology file (e.g., `/project-create` → `methodology/project-create.md`) and stored in `.claude/skills/`.

## Related

- `scripts/session_agent/task_workflow.py` — Implementation (including `COMMAND_REGISTRY`, `detect_command()`, sub-task API)
- `scripts/session_agent/engineering.py` — Global engineering cycle
- `methodology/session-protocol.md` — Session lifecycle and enforcement gates
- `methodology/engineering-taxonomy.md` — Engineering cycle taxonomy
- `scripts/compile_tasks.py` — Task data compilation pipeline
- `docs/interfaces/task-workflow/` — I3 web interface
- `.claude/skills/` — All 21 skill files
