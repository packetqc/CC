---
name: work-cycle
description: Enforces the per-todo work cycle — strategic remote check (v54), progressive commits, cache updates (Gate G4), issue comments (Gate G7), and push-as-savepoint. The heartbeat of every implementation session.
user_invocable: true
---

# /work-cycle — Per-Todo Work Cycle Enforcement

## When This Skill Fires

This skill MUST be active during **every todo execution** in the implement stage. It defines the mandatory cycle that repeats for each todo item in the plan.

**Triggers**:
- Starting work on a todo item
- Mid-session when the work cycle feels incomplete (missing commits, stale cache)
- After compaction recovery — re-read this to restore the work discipline

## The Work Cycle — 8 Steps Per Todo

Task Workflow Stage 3 (IMPLEMENT) enforces this cycle for **each todo**:

```
For each todo in the plan:
  [1. Remote Check] → [2. Execute] → [3. Commit] → [4. Push] →
  [5. Cache Update] → [6. Issue Comment] → [7. Mark Modifications] → [8. Next Todo]
```

### Step 1: Strategic Remote Check (v54)

**Before modifying ANY shared file**, check for upstream divergence:

```bash
# 1. Lightweight fetch (refs only, fast)
git fetch origin <default-branch>

# 2. Check divergence on specific files being touched
git diff origin/<default-branch>..HEAD -- <file1> <file2> ...

# 3. If divergence detected → merge upstream FIRST
git merge origin/<default-branch> --no-edit

# 4. If no divergence → proceed safely
```

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import advance_task_step, mark_work_action

advance_task_step('remote_check')
# After git fetch + diff:
mark_work_action("remote_checked")  # Passes integrity checkpoint W.1
```

**Mandatory triggers — MUST run**:

| Trigger | Why |
|---------|-----|
| Before starting a new todo step that modifies files | Catch concurrent session merges between steps |
| Before reading files for analysis leading to edits | Ensure analysis is based on current code |
| Before editing shared infrastructure (CLAUDE.md, scripts/, methodology/) | Highest conflict risk |
| After compaction recovery | Session may have been idle long enough for other PRs to merge |
| Before `save` protocol | Final sync before committing |

**Skip for efficiency — no check needed**:

| Scenario | Why skip |
|----------|----------|
| Read-only operations (analysis, review, validation) | No edit risk |
| Files created by this session only (new files) | No upstream version exists |
| Rapid sequential edits to the same file within one todo step | One check at step start is sufficient |
| Non-shared files (session notes, runtime cache) | Session-scoped |

**Conflict resolution**: If `git merge` produces conflicts, **STOP and report** to the user. Never force-resolve automatically on shared files. The user decides which version to keep.

### Step 2: Execute

Do the actual work for this todo item.

```python
advance_task_step('executing')
```

- Follow user-approved plan
- No scope creep — only do what this todo specifies
- If blocked, create a new todo for the blocker

### Step 3: Progressive Commit

Each completed todo gets its **own commit** — no big-bang commits at session end.

```bash
git add <specific files from this todo>
git commit -m "<type>: <description>"
```

```python
advance_task_step('commit')
mark_work_action("committed")  # Passes integrity checkpoint W.3
```

**Commit rules**:
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- Add specific files by name — never `git add -A` or `git add .`
- Each todo = one commit (1:1 correspondence)

### Step 4: Push as Savepoint

Push after each major commit. The branch is the safety net — `recover` retrieves stranded work.

```bash
git push -u origin <task-branch>
```

```python
advance_task_step('push')
mark_work_action("pushed")  # Passes integrity checkpoint W.4
```

**Why push matters**: Uncommitted work dies with the session. Unpushed commits die with the container. Only pushed commits survive all failure modes.

### Step 5: Cache Update (Gate G4)

**Mandatory after every todo completion.** The cache must reflect live working state.

```python
from scripts.session_agent import update_session_data

advance_task_step('cache_update')

# Required cache updates:
update_session_data('todo_snapshot', current_todo_list_with_statuses)
update_session_data('files_modified', list_of_file_paths)
update_session_data('work_summary', 'Updated summary of work done so far')
update_session_data('session_phase', 'executing')
```

**Full cache update table — mandatory events**:

| Event | Cache Key | Value |
|-------|-----------|-------|
| Todo started | `todo_snapshot` | Current todo list with statuses |
| Todo completed | `todo_snapshot` | Updated todo list |
| File modified | `files_modified` | Append file path |
| Decision made | `decisions` | Append decision text |
| PR created | `pr_numbers` | Append PR number |
| Phase change | `session_phase` | `executing` / `saving` / `complete` |
| Work summary | `work_summary` | Updated summary text |

**Every cache write auto-commits to git** — all write paths call `commit_cache()` immediately. The cache is recoverable via `recover` or `recall` even after crashes.

### Step 6: Issue Comment (Gate G7)

Post todo completion as a comment on the session issue:

```python
from scripts.session_agent import post_exchange

advance_task_step('issue_comment')

# Post todo completion
post_exchange('claude', f'Todo N complété: {step_name}', f'''### Livrable
- {files_modified}
- {brief_summary}''')
```

**What MUST be posted** (non-negotiable):

| Exchange type | Role | When |
|---------------|------|------|
| User's original request | `user` | After issue creation |
| User instructions / add-ons | `user` | As received |
| User corrections / feedback | `user` | As received |
| Claude analysis / plan | `claude` | After plan built |
| Todo step started | `claude` | At step start (⏳) |
| Todo step completed | `claude` | At completion (✅) |
| Significant decisions | `claude` | When decided |

**Comment format — avatars, not emojis**:
```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="20"> Martin — <description>
> <quoted user message>

## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — <description>
### <section>
<content>
```

**What NOT to post** (technical exclusions, not judgment calls):
- Raw tool output (git diff, grep results) — post the analysis, not the dump
- Internal reasoning chains — post the conclusion, not the process
- Duplicate content already posted in the same turn

**Anti-pattern**: Posting comments retroactively at save time instead of in real-time. The issue trail must reflect WHEN things happened.

### Step 7: Mark Modifications

```python
advance_task_step('mark_modifications')
# Auto-triggers mark_modifications_occurred() for documentation cross-cut
```

This flags that files were modified — the documentation cross-cut at stage boundaries will check if docs need updating.

### Step 8: Next Todo

```python
advance_task_step('next_todo')
# If more todos: reset_work_cycle() → loop back to Step 1
# If all done: documentation cross-cut → advance_task_stage('validation')
```

```python
from scripts.session_agent import reset_work_cycle

if more_todos:
    # Reset W.1-W.7 integrity checkpoints for next todo
    reset_work_cycle()
    # Loop back to Step 1
else:
    # All todos complete — documentation cross-cut BEFORE advancing
    from scripts.session_agent import check_documentation_needed
    doc_check = check_documentation_needed()
    if doc_check:
        # AskUserQuestion: "Update project docs" / "Update knowledge" / "Update both" / "Defer to doc stage"
        pass
    advance_task_stage('validation', reason='all todos complete')
```

**CRITICAL**: The documentation cross-cut MUST fire at the stage boundary before advancing to validation. Without it, doc updates are silently skipped. The `modifications_occurred` flag (set by `mark_modifications_occurred()` in Step 7) triggers the check.

## Progressive Commit Safety Net

```
Todo 1: commit A → push ✓ (savepoint 1)
Todo 2: commit B → push ✓ (savepoint 2)
Todo 3: commit C → [CRASH]
                     ↓
              New session:
              recover → retrieves commits A + B + C (if C was pushed)
              issue → shows what Todo 3 was doing
              resume → if checkpoint exists, restarts Todo 3
```

**Without intermediate pushes**, a crash after 4 of 5 todos loses ALL work. **With progressive pushes**, only the in-progress todo is at risk.

## Integrity Checkpoint Mapping

| Work Step | Checkpoint | Auto-pass via |
|-----------|------------|---------------|
| Remote check | W.1 | `mark_work_action("remote_checked")` |
| Execute | W.2 | `advance_task_step('executing')` |
| Commit | W.3 | `mark_work_action("committed")` |
| Push | W.4 | `mark_work_action("pushed")` |
| Cache update | W.5 | `update_session_data()` auto-passes |
| Issue comment | W.6 | `post_exchange()` auto-passes |
| Modifications | W.7 | `mark_modifications_occurred()` auto-passes |

## User Correction Integration

When the user redirects mid-work:
1. **Stop immediately** — don't finish the wrong approach
2. **Acknowledge** — "you're right, the essential file is X not Y"
3. **Adapt** — switch to the correct approach
4. **Post on issue** — document the correction via `post_exchange('user', ...)`

**Anti-pattern** (Pitfall #22): Ignoring the user's simpler fix and engineering alternatives. The person observing the output has information you don't.

## Identity Principles in Work

- **I1 (protocol non-negotiable)**: Every todo, even "trivial" ones, runs the full 8-step cycle
- **I2 (zero judgment)**: No todo is "too small" for a commit or issue comment
- **I3 (rigor over convenience)**: Remote check before editing, even if "nothing changed"
- **I4 (cycle complete)**: A todo without all 8 steps (including commit and issue comment) is a todo that didn't happen
- **I5 (self-correction)**: If tempted to batch commits at the end — stop, that's NPC behavior

## Context Budget Awareness

| Warning Sign | Action |
|-------------|--------|
| Reading files > 500 lines repeatedly | Stop — use targeted line ranges |
| Searching across > 5 files for the same thing | Stop — use grep, not sequential reads |
| Third attempt at the same approach | Stop — ask user or try their suggestion |
| Profile pages or secondary indexes | Skip — update essential files first |

## Notes

- Import all functions from `scripts.session_agent`
- `reset_work_cycle()` archives W section and resets for next todo — call between todos
- The work cycle is the implement stage's heartbeat — it runs as many times as there are todos
- Cache auto-commits to git on every write — no explicit `commit_cache()` needed
- `mark_work_action()` and `mark_completion_action()` bridge Bash-only actions to integrity grid
- Push cadence: push after each major commit, not just at session end
