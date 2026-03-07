---
name: task-received
description: Enforces the On Task Received protocol — task-workflow 9-step Stage 1 (INITIAL) + engineering-taxonomy request classification. Fires on every new task before any file is touched.
user_invocable: true
---

# /task-received — On Task Received Protocol Enforcement

## When This Skill Fires

This skill MUST be invoked whenever a new work request is received — either as the session's entry message (step 11 of wakeup) or as a mid-session new request. It is the **mandatory entry point** for all work.

**Triggers**:
- Session entry message after wakeup completes
- User provides a new distinct request mid-session (not an add-on)
- "Continue issue #N" — task continuation from previous session

**Does NOT trigger for**: Add-ons to current task, user corrections/feedback on in-progress work.

**NOTE (v100)**: ALL prompts — including methodology-backed commands like `project create`, `harvest`, `normalize`, etc. — now go through this skill. Commands are detected by `parse_prompt()` via `detect_command()` and become **sub-tasks** within the task workflow. The command's dedicated skill (e.g., `/project-create`) executes as a sub-task during the implement stage.

## Command-as-SubTask Flow (v100)

When `parse_prompt()` returns a `detected_command`:

```python
from scripts.session_agent import (
    parse_prompt, create_sub_task, start_sub_task, complete_sub_task
)

parsed = parse_prompt(user_prompt)
cmd = parsed.get("detected_command")

if cmd:
    # The command becomes a sub-task within the parent task
    sub_task = create_sub_task(
        command=cmd["command"],
        skill=cmd["skill"],
        title=f'{cmd["description"]}: {cmd.get("args", "")}',
        args=cmd.get("args", ""),
        label=cmd["label"],
        methodology=cmd.get("methodology", ""),
        group=cmd["group"],
    )
    # During implement stage, the command skill executes:
    # start_sub_task(sub_task["id"])
    # ... execute skill ...
    # complete_sub_task(sub_task["id"], commits=[...], files_modified=[...])
```

The title confirmation popup adapts: it shows the command interpretation as the title, with the raw command as context. The user confirms or modifies.

For **multi-command prompts** (detected via `is_multi_request`), each command becomes its own sub-task, executed sequentially during the implement stage.

## The Protocol — Task Workflow Stage 1 (INITIAL)

9 mandatory steps. No step may be skipped. Gates G1 and G2 are enforced within step 7.

### Step 1: Analyze Prompt

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import init_task_workflow, parse_prompt, advance_task_step

# Initialize the task workflow state machine
init_task_workflow(request_description=user_prompt)

# Parse the prompt — extracts title, description, action word, label, multi-request flag
parsed = parse_prompt(user_prompt)
# Returns: {
#   "title": str,
#   "description": str,
#   "action_word": str,       # create, fix, update, review, investigate, etc.
#   "detected_label": str,    # FEATURE, BUG, ENHANCEMENT, REVIEW, etc.
#   "is_multi_request": bool, # 2+ distinct requests detected
#   "is_healthcheck": bool,   # engineering cycle healthcheck
#   "is_continuation": bool,  # "continue issue #N"
#   "continuation_issue": int # issue number if continuation
# }

advance_task_step('analyze_prompt')
```

### Step 2: Extract Title

```python
advance_task_step('extract_title')
```

Title comes from `parsed["title"]` — line 1 of the prompt, cleaned of command prefixes.

### Step 3: Extract Description

```python
advance_task_step('extract_description')
```

Description comes from `parsed["description"]` — lines 2+ of the prompt.

### Step 4: Confirm Title via AskUserQuestion

**CRITICAL**: NEVER create the GitHub issue before this step. The popup is the user's decision point.

Present an `AskUserQuestion` with:
- Option 1: The parsed title (default)
- Option 2: "Skip — no tracking" (creates local cache only, no GitHub issue)

```python
from scripts.session_agent import set_task_title
# After user confirms:
set_task_title(confirmed_title)
advance_task_step('confirm_title')
```

If user selects **Skip**:
```python
from scripts.session_agent import init_skip_cache
init_skip_cache(repo, branch, description)
# Session gets full cache without GitHub issue
# G7 is disabled (g7_skip=true)
# Exchanges queued locally in notes/pending-comments-*.json (never discarded)
```

**Reactivation path**: The user can re-enable tracking at any time by saying `sync` or `record`. Claude then calls `activate_tracking(issue_number)` which: (1) switches cache from skip→tracked, (2) reactivates G7, (3) flushes queued comments to the issue. Comments are never lost — they wait locally until GitHub becomes available.

### Step 5: Detect Project

```python
from scripts.session_agent import detect_project
advance_task_step('detect_project')

# Scans BOTH title and description for project references
# Weighted: title 3x, description 1x, P# references 4x
project_result = detect_project(title, description, available_projects)
# Returns: { "project": str, "confidence": "high"|"medium"|"low"|"ambiguous", "scores": dict }
```

**Known issue**: When all projects score identically (generic terms), P0 wins by position. If confidence is "ambiguous", flag the tie in the confirmation popup.

### Step 6: Confirm Project

```python
from scripts.session_agent import set_task_project
advance_task_step('confirm_project')
# AskUserQuestion: detected project first, then all available projects
set_task_project(confirmed_project)
```

### Step 7: Persist State (Gates G1 + G2)

```python
from scripts.session_agent import set_task_issue, write_runtime_cache
advance_task_step('persist_state')

# 1. Create GitHub issue: "SESSION: <title> (YYYY-MM-DD)", label: SESSION + detected_label
# 2. Link to project board, set "In Progress"
# 3. Post verbatim first comment (user's exact words, frozen)
# 4. Initialize runtime cache:
write_runtime_cache(...)  # Auto-unlocks Gate G2 + enforcement state

set_task_issue(issue_number)
```

**Gate G1**: No file may be created/edited until this step completes (issue exists).
**Gate G2**: Runtime cache initialized via `write_runtime_cache()` — auto-updates enforcement state.

**CRITICAL — Initialize G7 immediately**: After issue creation, `post_exchange()` MUST be called to initialize `last_post_time` in the enforcement state. Without this, the PreToolUse hook blocks all file edits (G7 treats null `last_post_time` as BLOCK).

```python
from scripts.session_agent import post_exchange, init_engineering_cycle

# Post the user's original request (frozen, verbatim)
post_exchange('user', 'Demande originale (verbatim)', user_prompt)

# Post Claude's initial analysis
post_exchange('claude', 'Analyse initiale', f'### Classification\n- Type: {parsed["detected_label"]}\n- Project: {confirmed_project}')

# Initialize the engineering cycle (10-stage SDLC alongside task workflow)
init_engineering_cycle()
```

This satisfies G7's `last_post_time` requirement and initializes the engineering cycle for `sync_engineering_stage_label()` on the issue.

### Step 8: Output Details

```python
advance_task_step('output_details')
```

Display confirmed title, project, issue number, and detected request type to the user.

### Step 9: Wait for Plan Approval

```python
from scripts.session_agent import advance_task_stage
advance_task_step('wait_approval')
# After user approves plan:
advance_task_stage('plan', reason='user approved')
```

## Engineering Taxonomy — Request Classification

The 11 request types classify every possible user prompt. No request escapes classification.

| # | Type | Nature | Action Words (EN) | Action Words (FR) |
|---|------|--------|-------------------|-------------------|
| 1 | `fix` | Repair | fix, bug, broken, error, crash, fail, wrong, repair, correct, patch, hotfix | résoudre, corriger, bogue, réparer |
| 2 | `feature` | Build | add, create, new, implement, build, feature, scaffold, introduce, enable | ajouter, créer, nouveau, implémenter, construire |
| 3 | `investigation` | Investigate | investigate, diagnose, analyze, root cause, why, troubleshoot, debug, trace, probe | diagnostiquer, analyser, pourquoi, enquêter |
| 4 | `enhancement` | Improve | refactor, optimize, simplify, restructure, reorganize, improve, upgrade, modernize, clean, performance | refactoriser, nettoyer, optimiser, améliorer |
| 5 | `testing` | Verify | test, qa, unit test, integration test, assert, coverage, regression, smoke test | tester |
| 6 | `validation` | Accept | validate, verify, acceptance, check, confirm, approve, sign off, demo | valider, vérifier, confirmer, approuver |
| 7 | `documentation` | Document | document, doc, write, describe, readme, publication, wiki, changelog, guide | documenter, décrire, rédiger |
| 8 | `deployment` | Deliver | deploy, release, push, ship, publish, deliver, merge, ci/cd, pipeline | déployer, publier, livrer |
| 9 | `conception` | Design | design, architect, conceive, prototype, wireframe, blueprint, spike, rfc, proposal, plan | conception, concevoir, architecturer, planifier |
| 10 | `review` | Assess | review, audit, assess, evaluate, inspect, survey, examine, peer review | réviser, auditer, évaluer, inspecter |
| 11 | `chore` | Sustain | chore, housekeeping, cleanup, maintenance, routine, admin, config, setup, infrastructure | ménage, entretien, configuration |

### Label Mapping

| Action Word | GitHub Label |
|-------------|-------------|
| review | REVIEW |
| create, add, implement, build | FEATURE |
| fix | BUG |
| update, refactor, optimize | ENHANCEMENT |
| design | DESIGN |
| investigate, diagnose, analyze | INVESTIGATION |
| document | DOCUMENTATION |
| deploy | DEPLOYMENT |
| test | TESTING |

### Prompt Interpretation — Three Layers

| Layer | What | How |
|-------|------|-----|
| **1. Keywords** | `parse_prompt()` pre-filter | Deterministic keyword matching at machine speed |
| **2. AI Synthesis** | Claude's reasoning on structured output | LLM interprets intent, context, ambiguity |
| **3. User Confirmation** | `AskUserQuestion` when not obvious | Present AI's synthesis for user approval |

**Rule**: `parse_prompt()` gives structured signals — it does NOT make the decision. Claude synthesizes meaning from keywords + context + conversation history. When unambiguous, act. When ambiguous, confirm.

## Multi-Request Detection

When the entry prompt contains 2+ distinct requests:
- Create separate issues for each
- Sequence them in the plan
- Each request → own issue, own todo group, own PR

Mid-session add-ons (supplementary instructions on current task) use `append_request_addon()` instead.

## Task Continuation

When user says "Continue issue #N":
1. `parse_prompt()` detects continuation pattern
2. Look up issue for title and context
3. Read previous session's runtime cache for workflow state
4. Present `AskUserQuestion` with existing title
5. Create new session cache linked to same issue
6. Resume from last known stage/step

## STAGE:/STEP: Label Sync

Every `advance_task_stage()` and `advance_task_step()` automatically syncs GitHub issue labels:

| Function | Label Pattern | Behavior |
|----------|--------------|----------|
| `advance_task_stage()` | `STAGE:<name>` | Removes previous `STAGE:*`, adds new |
| `advance_task_step()` | `STEP:<name>` | Removes previous `STEP:*`, adds new |

Stage colors: initial=#6f42c1, plan=#0366d6, analyze=#0891b2, implement=#2ea44f, validation=#d29922, approval=#f97316, documentation=#8b5cf6, completion=#28a745.

Non-fatal: if GitHub API is unavailable, workflow proceeds without labels.

## Five-Channel Persistence Model

| Channel | Survives Crash | Survives Compaction | Real-time |
|---------|---------------|--------------------| ----------|
| **Git** (commits) | Yes if pushed | Yes | No |
| **Notes** (`session-*.md`) | Yes if committed | No | No |
| **GitHub Issue** (comments) | Yes | Yes | **Yes** |
| **Cache** (`session-runtime-*.json`) | Yes (auto-committed) | Yes | **Yes** |
| **Startup Hook** | Yes | Yes | **Yes** |

## Identity Principle Enforcement

- **I1 (protocol non-negotiable)**: Every request, regardless of duration, runs this 9-step sequence
- **I2 (zero judgment)**: Claude never decides a request is "too trivial" for tracking — that judgment is the single most dangerous behavior
- **I5 (self-correction)**: If tempted to skip the AskUserQuestion popup — stop, that's NPC behavior

## After Completion

After Stage 1 completes, the task workflow advances through stages 2-8:
```
INITIAL → PLAN → ANALYZE → IMPLEMENT → VALIDATION → APPROVAL → DOCUMENTATION → COMPLETION
```

Proceed to plan creation and approval (Gate G3), then autonomous execution.

## Notes

- Import all functions from `scripts.session_agent` (not directly from sub-modules)
- The popup MUST include "Skip — no tracking" option on every session
- Never create the issue before user confirms the title
- Multi-request detection at parse time creates separate issues
- The verbatim first comment on the issue is FROZEN — never modified after posting
- Gate G1 (issue) and G2 (cache) are enforced by PreToolUse hook — file edits are blocked until both pass
