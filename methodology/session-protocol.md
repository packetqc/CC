# Session Protocol

The session lifecycle is the backbone of persistent AI-assisted development. Every session follows the same cycle, ensuring no context is lost between incarnations.

## The Cycle

```
wakeup → task received → plan approved → autonomous execution → pre-save summary → save → dormancy
```

## Mandatory Enforcement Gates

**These gates are non-negotiable.** Every session MUST pass through each gate in order. Skipping a gate violates the session contract and produces incomplete persistence artifacts.

| Gate | When | Enforcement | Blocks |
|------|------|-------------|--------|
| **G1: Issue before edits** | After title confirmation, before first file touch | No file may be created/edited until GitHub issue exists | All file operations |
| **G2: Cache initialized** | Immediately after issue creation | `write_runtime_cache()` with issue number, title, branch, request | Focused work |
| **G3: Plan approved** | After analysis, before autonomous execution | User confirms todo plan via approval or "go" signal | Execution of todo steps |
| **G4: Cache updated per todo** | After each todo completion | `update_session_data('todo_snapshot', ...)` with current todo state | Next todo step |
| **G5: Pre-save verification** | Before save commit | Verify: (1) session notes generated, (2) cache updated with final state, (3) issue comments complete | Save commit |
| **G6: Dual file output** | During save | Both `session-YYYY-MM-DD-*.md` AND `session-runtime-*.json` committed and pushed | PR creation |
| **G7: Issue is complete record** | From issue creation to post-close | ALL user and Claude exchanges posted as issue comments. Final comment posted AFTER issue close. | Session end |
| **G8: README.md updated** | Before save commit | Verify README.md reflects session deliverables — new features, new publications, structural changes. README.md is the public front page. | Save commit |

**G8 — README.md is the public front page**: README.md is the first thing users see on GitHub. It MUST reflect the current state of the project. Every session that produces visible deliverables (new publications, new features, structural changes, new interfaces) MUST check and update README.md before save. This is not a suggestion — it is an enforcement gate. The auto-évaluation flags non-compliance.

**G7 — Issue as complete session record**: The GitHub issue is the **single source of truth** for the entire session interaction. Every user message and every Claude response that constitutes a significant exchange MUST be posted as an issue comment. This is not optional, not "best effort" — it is mandatory. The issue must be readable as a complete chronological transcript of the session's work. After the issue is closed, the session posts one final comment: the closing report with delivery status and comment history index. The issue is never "done" until this post-close comment exists.

**Violation recovery**: If a gate was missed (detected at save time via auto-évaluation), the session MUST retroactively satisfy it before completing the save. Missing files are generated, missing comments are posted, missing cache updates are written.

---

### 1. Wakeup (Session Start)

**Auto-runs on every session start** — the user does not need to type `wakeup`. The full protocol (steps 0–11 in CLAUDE.md) runs automatically:

1. **Step 0: Sunglasses** — Read `packetqc/knowledge` CLAUDE.md first (non-negotiable)
2. **Step 0.3: Elevation** — Detect `GH_TOKEN` for full autonomous mode
3. **Step 0.5: Bootstrap scaffold** — Create missing essential files on fresh repos
4. **Step 0.55: Self-heal** — Update satellite CLAUDE.md commands section if drifted
5. **Step 0.7: Sync upstream** — Fetch and merge default branch into task branch
6. **Step 0.9: Resume detection** — Check for `notes/checkpoint.json` from crashed sessions
7. **Steps 1-8: Context recovery** — Read evolution, minds/, notes/, sync assets, git log, branches. **Do NOT read NEWS.md or PLAN.md** — these are essential files for documentation updates, not startup context. Reading them wastes context window on content that is not needed for session work.
7.5. **Step 5.5: Session data regeneration** (core repo only, elevated) — Regenerate `docs/data/sessions.json` → commit → push → PR → merge to `main`. Makes the Session Review viewer current immediately. Skip if not elevated or not core repo.
8. **Step 9: Print help** — Full multipart command table
9. **Step 10: Harvest prompt** — Core repo only, opt-in
10. **Step 11: Address user's entry message** — Start working on the user's request

This guarantees full context recovery before any work begins. No guessing, no stale assumptions.

### 2. Task Received (v51, v58)

**Trigger**: Every session entry message is presumed to be a work request by default. After wakeup completes, **before the first file is touched**, the **Task Workflow Stage 1 (INITIAL)** runs — see `methodology/task-workflow.md` for the authoritative 9-step sequence.

**Task Workflow Stage 1 — INITIAL (9 steps)**:

| # | Step | Description |
|---|------|-------------|
| 1 | `analyze_prompt` | Analyze prompt for action words, structure, multi-request indicators |
| 2 | `extract_title` | Extract title from line 1 |
| 3 | `extract_description` | Extract description from remaining lines |
| 4 | `confirm_title` | Confirm via AskUserQuestion + "Skip tracking" option |
| 5 | `detect_project` | Detect project owner from **title and description** |
| 6 | `confirm_project` | Confirm project via AskUserQuestion (detected first + all available) |
| 7 | `persist_state` | Create issue, link board, persist in cache + GitHub |
| 8 | `output_details` | Output confirmed details to user |
| 9 | `wait_approval` | Wait for user approval before proceeding to plan stage |

Steps 1-3 use `parse_prompt()` (which also calls `detect_command()` for command matching — see v100), step 5 uses `detect_project()`, step 7 creates issue(s) and initializes cache. Gates G1 (issue before edits) and G2 (cache initialized) are enforced within step 7. When a command is detected, a sub-task is created via `create_sub_task()` and tracked in `session_data.sub_tasks[]`.

**Multi-request detection**: When the entry prompt contains 2+ distinct requests, the session creates separate issues and sequences them in the plan. Each request gets its own issue, its own todo group, and its own PR. Mid-session add-ons (v53) remain for supplementary instructions — multi-request detection is for distinct tasks at parse time.

**After Stage 1 completes**, the task workflow advances through stages 2-8 (plan → analyze → implement → validation → approval → documentation → completion). See `methodology/task-workflow.md`.

**API**: `from scripts.session_agent import init_task_workflow, parse_prompt, detect_project, advance_task_stage, advance_task_step`

**Five-channel persistence model** — the issue is the third channel, the session cache is the fourth, the startup hook is the fifth:

| Channel | Survives crash? | Survives compaction? | Survives session end? | Real-time? |
|---------|----------------|---------------------|----------------------|-----------|
| **Git** (commits, branches) | Yes if pushed | Yes | Yes | No (batch) |
| **Notes** (`notes/session-*.md`) | Yes if committed | No (context-level) | Yes if committed | No (batch) |
| **GitHub Issue** (comments) | Yes (API-persisted) | Yes (external) | Yes (external) | **Yes** |
| **Cache** (`notes/session-runtime-<suffix>.json`) | Yes (auto-committed) | Yes (persisted) | Yes (committed) | **Yes** |
| **Startup Hook** (`.claude/hooks/startup-checklist.sh`) | Yes (code on disk) | Yes (runs pre-context) | Yes (runs every start) | **Yes** (at boot) |

The issue is the **only** channel that persists in real-time and survives all failure modes independently of the local environment. The cache is the **only** channel providing structured, queryable session state — surviving compaction locally with 18 typed data keys (comment IDs, decisions, todo snapshots, PR numbers, time markers, and more). **Every cache write auto-commits to git** — all 9 cache write paths call `commit_cache()` immediately after writing to disk: `write_runtime_cache()`, `update_session_data()`, `_append_staged_addon()`, `advance_engineering_stage()`, `append_pr_number()` (both new and update paths), `append_time_marker()`, and `append_error()`. The 7 helper functions that route through `update_session_data()` also auto-commit via that path. Only `trim_session_cache()` (maintenance) writes without committing. This ensures the cache is recoverable via `recover` (branch recovery) or `recall` (deep memory search) even if the session crashes before a manual commit.

**Session continuity hook** — The startup hook (`.claude/hooks/startup-checklist.sh`) scans the last 10 cache files on every session start, prints pending/in-progress todos in Claude's initial context. This is the **5th persistence channel** — running code that injects previous session state into the new session BEFORE Claude's context loads. Combined with auto-commit-on-cache-write, todo state survives crashes, compaction, and container restarts automatically.

**When NOT to create an issue**: Only when the user explicitly says "skip tracking" or "no issue." Infrastructure commands (`wakeup`, `refresh`, `help`) are not tasks and don't trigger issue creation. The session never judges a request as "too trivial" for tracking — that judgment is the single most dangerous behavior in the system (v59.3).

**Gate G1 + G2 checkpoint**: After issue creation, verify both gates passed:
```
✓ G1: Issue #N created before any file touched
✓ G2: Runtime cache initialized (session-runtime-<suffix>.json committed)
```

**Reference**: CLAUDE.md "On Task Received — Session Issue Protocol (v52)"

### 2.5. Plan Approval → Autonomous Execution (v53)

**Trigger**: After the issue is created and the user's request is understood, the session analyzes the request and builds a work plan.

**Two-gate flow**:

```
[title confirmed → issue created] → [analyze + plan] → [plan approved by user] → [autonomous execution to delivery]
```

1. **Gate 3 — Plan approval**: The session presents its analysis and todo list to the user. The user reviews and approves (or corrects). This is the **final approval gate**.
2. **After approval**: The session executes every step autonomously — no further "should I proceed?" questions, no waiting for instruction between steps. The plan was approved. Execute it.

**What triggers autonomous execution**:
- User approves the work plan (explicit approval or "go"/"proceed"/"do it")
- User confirms task title + plan is self-evident (single-step task)

**What pauses autonomous execution**:
- User explicitly asks a question → answer, then resume
- User says "wait", "stop", "pause" → pause and wait
- Ambiguity that could cause irreversible damage → ask once, then proceed

**Anti-pattern**: Asking "what should I do first?" or "shall I proceed with step 2?" after the plan was approved. The user already approved. Act.

**Reference**: CLAUDE.md "Autonomous Execution Principle (v53)"

### 3. Focused Work

During the session, follow the **todo-driven work cycle** with mandatory cache updates:

```
start todo → strategic remote check → do the work → commit → push →
mark completed → update cache (G4) → post issue comment → next todo
```

- **Post significant exchanges as issue comments** — alternating 🧑 user / 🤖 Claude in real-time
- **Post each completed todo step** as a 🤖 issue comment — the step name + brief summary of deliverables. This creates a 1:1 correspondence between the todo list and the issue trail
- **Commit after each completed todo** — progressive commits at each deliverable, not one big-bang commit at session end
- **Push after each major commit** — the branch is the safety net for `recover` recovery
- **Update runtime cache after each todo** (Gate G4) — `update_session_data('todo_snapshot', current_todos)` + `update_session_data('session_phase', 'executing')`. This ensures the cache reflects live working state, not just the initial creation state
- **Append to session notes** as work progresses — decisions made, bugs found, modules integrated, status changes
- **Screenshots are data** — when the user shares screen captures, extract every detail

**Cache update points during work** (mandatory):

| Event | Cache key | Value |
|-------|-----------|-------|
| Todo started | `todo_snapshot` | Current todo list with statuses |
| Todo completed | `todo_snapshot` | Updated todo list |
| File modified | `files_modified` | Append file path |
| Decision made | `decisions` | Append decision text |
| PR created | `pr_numbers` | Append PR number |
| Phase change | `session_phase` | `executing` / `saving` / `complete` |
| Work summary | `work_summary` | Updated summary text |

**Real-time issue comments (Gate G7)**: ALL user and Claude exchanges MUST be posted as issue comments. This is the complete session record — not a selective summary. The issue must be readable as a chronological transcript of the session's work.

**What MUST be posted** (non-negotiable):

| Exchange type | Post as | When |
|---------------|---------|------|
| User's original request | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="16"> verbatim (frozen, never modified) | Immediately after issue creation |
| User instructions / add-ons | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="16"> quoted + context | As received |
| User corrections / feedback | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="16"> quoted + context | As received |
| Claude analysis / plan | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> analysis + todo list | After plan built |
| Todo step started | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> ⏳ step name | At step start |
| Todo step completed | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> ✅ step name + deliverables | At step completion |
| Significant decisions | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> decision + rationale | When decided |
| Pre-save summary | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> full 7-section report | Before save |
| Post-close final report | <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="16"> delivery status + comment index | **After issue closed** |

**Format**:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="20"> Martin — <short description>
> <quoted user message>
*<optional context>*
```

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — <short description>
### <section>
<content — actions taken, findings, decisions>
```

**Anti-pattern**: Posting comments retroactively at save time instead of in real-time. The issue trail must reflect WHEN things happened, not batch everything at the end.

**Enforcement — `post_exchange()` one-liner** (v57):

The `post_exchange()` function in `scripts/session_agent` is the primary API for G7 compliance. It reads the runtime cache, gets the repo/issue, posts the comment via `SessionSync`, and updates the enforcement state's `last_post_time`. The PreToolUse hook warns (stderr, does NOT block) if >5 minutes have elapsed since the last post.

```python
from scripts.session_agent import post_exchange

# After each user message
post_exchange('user', 'Question about feature X', 'the verbatim user message')

# After each significant Claude response
post_exchange('claude', 'Analysis of root cause', '### Root cause\nThe issue is...')
```

**When to call** (mandatory):
- After each user message → `post_exchange('user', ...)`
- After presenting analysis/plan → `post_exchange('claude', ...)`
- After answering a question → `post_exchange('claude', ...)`
- Todo steps use `SessionSync.start_step()`/`complete_step()` instead (richer lifecycle)

**What NOT to post** (technical exclusions, not judgment calls):
- Raw tool output (git diff, grep results) — post the analysis, not the dump
- Internal reasoning chains — post the conclusion, not the process
- Duplicate content already posted in the same turn

### 3.1. Command-as-Sub-Task Execution (v100)

When a todo step involves executing a methodology-backed command (e.g., `project create`, `harvest`, `normalize`), the command runs as a **tracked sub-task** within the work cycle:

```
[todo step: execute command] →
  detect_command(prompt, title) →
  create_sub_task(command, skill, ...) →
  start_sub_task(id) →
  execute command skill →
  complete_sub_task(id, commits, files_modified) →
[continue work cycle]
```

**Sub-tasks are children of the parent task** — they share the same GitHub issue and are tracked in `session_data.sub_tasks[]` in the runtime cache. Each sub-task records its own status, commits, and files_modified independently.

**G7 compliance for sub-tasks**: Sub-task start/completion is posted as an issue comment, just like regular todo steps. The comment includes the sub-task command, skill, and deliverables.

**Failure handling**: If a sub-task fails (`fail_sub_task(id, reason)`), the parent task does NOT halt automatically. The failure is posted as an issue comment and the user decides whether to retry, skip, or abort.

**API**: `from scripts.session_agent import create_sub_task, start_sub_task, complete_sub_task, fail_sub_task, get_sub_tasks, get_sub_task_summary`

**Full specification**: `methodology/task-workflow.md` § "Command Detection & Sub-Task Lifecycle (v100)"

### 4. Pre-Save Summary (v50)

Before executing any save operation, compile and display a structured session report with **7 sections**. This is the operational checklist — self-contained, not dependent on reading methodology files at save time.

#### Step 0: Issue comment integrity check

Before the summary, compare session exchanges against posted issue comments. Post any missing comments to fill gaps.

#### Section 1: Résumé

1-3 sentence description of work accomplished. What was delivered, why it matters.

#### Section 2: Métriques

Compile from **GitHub PR API** (primary) or `git diff --stat` (fallback). Never estimate when API data is available.

**Single-issue session**:
```markdown
**Totals: N todos · N PRs · N files · +X −Y lines · <deliverables>**

| Catégorie | Todos | PRs | Fichiers | Lignes+ | Lignes− | Livrables |
|-----------|-------|-----|----------|---------|---------|-----------|
| 📝 Documentation | N | N | N | N | N | N méthodologies |
| ⚙️ Collatéral | N | N | N | N | N | N issues |
```

**Multi-issue session** (2+ issues worked):
```markdown
**Session totals: N issues · N todos · N PRs · N files · +X −Y lines**

| Issue | Title | Todos | PRs | Fichiers | Lignes+ | Lignes− | Livrables |
|-------|-------|-------|-----|----------|---------|---------|-----------|
| #NNN | <title> | N | N | N | N | N | <deliverables> |
| #NNN | <title> | N | N | N | N | N | <deliverables> |
| **Total** | | **N** | **N** | **N** | **+X** | **−Y** | |
```

**Category grid**: 🔍 Diagnostic · 💡 Conception · 📝 Documentation · 📋 Doc Management · ⚙️ Collatéral

**Data collection**: For each PR, query `additions`, `deletions`, `changed_files` from GitHub API:
```python
resp = gh._request("GET", f"/repos/{repo}/pulls/{pr_number}")
# resp["additions"], resp["deletions"], resp["changed_files"]
```

**Full specification**: `methodology/metrics-compilation.md`

#### Section 3: Temps (Time Blocks)

Compile from **issue `created_at` timestamps** (primary) or **commit timestamps** (fallback). Each todo gets a row with start/end/duration.

**Single-issue session**:
```markdown
**Totals: N todos · ~Xh YYmin actif · N blocs · moy ~Nmin/todo**

| # | Todo | Début | Fin | Durée | Catégorie |
|---|------|-------|-----|-------|-----------|
| **T1** | **<task>** | HH:MM | HH:MM | ~Nmin | 📝 Documentation |
| **T2** | **<task>** | HH:MM | HH:MM | ~Nmin | ⚙️ Collatéral |
```

**Multi-issue session** (2+ issues worked):
```markdown
**Session totals: N issues · N todos · ~Xh YYmin actif · N blocs**

| Issue | Title | Todos | Durée | Début | Fin | Catégorie |
|-------|-------|-------|-------|-------|-----|-----------|
| #NNN | <title> | N | ~Xh YYmin | HH:MM | HH:MM | 📝 Documentation |
| #NNN | <title> | N | ~Xh YYmin | HH:MM | HH:MM | ⚙️ Collatéral |
| **Total** | | **N** | **~Xh YYmin** | **HH:MM** | **HH:MM** | |
```

**Time blocks**: Morning (05:00–12:00), Afternoon (12:00–18:00), Evening (18:00–23:00). Group todos by block.

**Full specification**: `methodology/time-compilation.md`

#### Section 4: Proportions temporelles

Decompose session time into three measurable slices:

```markdown
**--- Proportions temporelles / Time Proportions ---**

| Tranche | Durée | % du calendrier |
|---------|-------|-----------------|
| 🤖 Machine (Claude) | ~Xh YYmin | NN% |
| 🧑 Humain (utilisateur) | ~Xh YYmin | NN% |
| 🕐 Inactif / pauses | ~Xh YYmin | NN% |
| **Total calendrier** | **~Xh YYmin** | **100%** |
```

**Rules**: Machine ≤ Calendrier (always). Ratio > 80% = burst session (flag it). Ratio < 20% = significant user parallel work.

#### Section 5: Équivalent entreprise

Ventilate the enterprise equivalent into three effort categories:

```markdown
**--- Équivalent entreprise / Enterprise Equivalent ---**

| Catégorie entreprise | Temps entreprise | Temps Knowledge | Ratio |
|---------------------|-----------------|-----------------|-------|
| 🔨 Réalisation | N–N semaines | ~Xh (inclus) | ~Nx |
| 📝 Documentation | N–N semaines | ~Xh (inclus) | ~Nx |
| 🎓 Formation | N–N semaines | ~0h (sous-produit) | ∞ |
| **Total** | **N–N semaines** | **~Xh** | **~Nx** |
```

**Key insight**: Documentation and training are simultaneous byproducts in Knowledge — not separate phases.

#### Section 6: Livraisons

Quick-reference delivery table:

```markdown
| Livraison | Référence | Statut |
|-----------|-----------|--------|
| PR | #N → main | ✅ merged |
| Issue | #N | ✅ closed |
| Fichiers | file1, file2 | committed |
```

#### Section 7: Auto-évaluation

Honest self-assessment of methodology compliance:

| Critère | Gate | Check |
|---------|------|-------|
| Issue créé avant premier fichier? | G1 | ✅/❌ |
| Cache initialisé après issue? | G2 | ✅/❌ |
| TodoWrite utilisé? | G3 | ✅/❌ |
| Cache mis à jour par todo? | G4 | ✅/❌ |
| Commentaires temps réel sur issue? | G7 | ✅/❌ |
| TOUS les échanges postés sur l'issue? | G7 | ✅/❌ |
| Remote check stratégique? | — | ✅/❌ |
| Métriques compilées avec données API? | — | ✅/❌ |
| Proportions temporelles? | — | ✅/❌ |
| Équivalent entreprise? | — | ✅/❌ |
| README.md vérifié et mis à jour si applicable? | G8 | ✅/❌ |

#### Decision point

`AskUserQuestion` popup with "Save now", "Continue working", "Save + close issue".

The complete summary is also posted as the final 🤖 comment on the session's GitHub issue — persisting the compilation in the five-channel model (v51).

**Reference**: `methodology/metrics-compilation.md`, `methodology/time-compilation.md`

### 5. Save (Session End)

Triggered by the user confirming "Save now" in the pre-save summary, or by typing `save`:

0.5. Strategic remote check — `git fetch origin <default>` + merge if diverged
1. **Generate session notes** (markdown) — call `generate_session_notes()` from `scripts/session_agent.py`. This converts the runtime cache (JSON) into the markdown notes format (`notes/session-YYYY-MM-DD-<slug>.md`) that `generate_sessions.py` parses for the Session Viewer (I1). **This is NOT the same as the runtime cache** — see "Two Persistence Systems" below.
1.1. **Gate G5 — Verify session notes** — Check that step 1 produced a file. If `generate_session_notes()` returned `None`, write the notes manually following the format in `parse_notes_file()` from `generate_sessions.py`. **Never proceed to commit without a session notes file.**
1.2. **Finalize runtime cache** — `update_session_data('session_phase', 'complete')` + `update_session_data('work_summary', '<final summary>')`. The cache must reflect the session's final state before being committed.
1.5. **Regenerate `docs/data/sessions.json`** (core repo only, **mandatory**) — Run `python3 scripts/generate_sessions.py`. This updates the Session Viewer (I1) data so the current session appears in the selection immediately after merge. **Non-negotiable**: every save on the core repo MUST include this step. The regenerated `sessions.json` is committed together with the session notes and cache in the same save commit.
1.95. **Post session notes as issue comment** — Read the generated session notes markdown file and post its full content as a 🤖 comment on the session issue. This makes the issue the **complete session record** — all exchanges, decisions, and the final notes in one place. Format:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — Session notes
<full content of notes/session-YYYY-MM-DD-*.md>
```

1.9. **Gate G6 — Dual file output verification** — Before committing, verify BOTH files exist:
    - `notes/session-YYYY-MM-DD-*.md` (session notes for web pipeline)
    - `notes/session-runtime-*.json` (runtime cache for session continuity)
    If either is missing, generate it. **Both files MUST be in the commit.**
2. Commit on current task branch
3. `git push -u origin <task-branch>`
4. Detect default branch: `git remote show origin | grep 'HEAD branch'`
5. Create PR via `gh_helper.py` targeting default branch
6. **[Elevated]** Merge PR + sync back (autonomous)
7. **[Semi-auto]** Print `⏸` pause — user merges manually
8. **Close issue** — If all work is delivered (auto-closed via `Closes #N` in PR, or manual close)
9. **Gate G7 — Post-close final comment** — After the issue is closed, post the closing report. This is the **last comment on the issue** and it MUST be posted after close, not before:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — Rapport de clôture

### Statut final
| Élément | Statut |
|---------|--------|
| PR #NNN — <title> | ✅ fusionné |
| Issue #NNN | ✅ fermée |
| Session notes | ✅ posted (comment #N) |
| CHANGELOG.md | ✅ updated |

### Historique complet du billet (N commentaires)
| # | Type | Contenu |
|---|------|---------|
| 1 | <img src=".../vicky.png" width="16"> | Demande originale (verbatim) |
| 2 | <img src=".../vicky-sunglasses.png" width="16"> | Analyse et plan |
| ... | ... | ... |
| N | <img src=".../vicky-sunglasses.png" width="16"> | **Ce rapport de clôture** |
```

**The issue is never "done" until this post-close comment exists.** This ensures every issue has a complete record of what happened, what was delivered, and what the final state is. The comment history index lets anyone reconstruct the session by reading the issue alone.

**Rule**: All user and Claude exchanges MUST be in the issue. The issue is the complete, self-contained session record. Session notes posted on the issue make it the single source of truth — even if the notes file is lost, the issue preserves everything.

#### Two Persistence Systems — Session Notes vs Runtime Cache

These are **two distinct systems** that serve different purposes and **must both exist**:

| System | File pattern | Written when | Consumer | Purpose |
|--------|-------------|-------------|----------|---------|
| **Session notes** (markdown) | `notes/session-YYYY-MM-DD-*.md` | At save time (step 1) | `generate_sessions.py` → `sessions.json` → Session Viewer (I1) | Human-readable session record for web interface |
| **Runtime cache** (JSON) | `notes/session-runtime-<suffix>.json` | During work (real-time) | Startup hook, `session_agent.py`, crash recovery | Machine-readable operational state for session continuity |

**The runtime cache does NOT replace session notes.** The JSON cache is written continuously during work for crash recovery and session continuity. The markdown notes are written once at save time for the web interface pipeline. Both files live in `notes/` but serve completely different consumers.

**Guard**: The `save` protocol MUST verify that `generate_session_notes()` produced a markdown file. If it returns `None`, write the notes manually following the format in `parse_notes_file()` from `generate_sessions.py`.

#### Session Tree — Parent/Child Relationships

Sessions form **trees** when they share `related_issues` with the `SESSION` label. The tree is built by `generate_sessions.py` using issue creation timestamps to determine parent (created before) vs child (created after) relationships.

**Tree fields** added to each session in `sessions.json`:

| Field | Type | Description |
|-------|------|-------------|
| `session_kind` | `"original"` / `"continuation"` | Original = no parents (root or standalone). Continuation = has parent sessions. |
| `parent_issues` | `[int]` | Issue numbers of SESSION-labeled related issues created **before** this session |
| `children_issues` | `[int]` | Issue numbers of SESSION-labeled related issues created **after** this session |
| `tree_root` | `int\|null` | Issue number of the root session in this tree (propagated via BFS) |
| `tree_depth` | `int\|null` | Depth in the tree (0 = root, 1 = first child, 2 = grandchild, etc.) |

**Detection logic**:
1. For each session, scan `related_issues` for entries with `SESSION` label
2. Compare `issue_created_at` timestamps: earlier = parent, later = child
3. BFS propagation: root sessions (no parents) set `tree_root` to their own issue number, depth 0
4. Children inherit `tree_root` from their parent and increment `tree_depth`

**Session Viewer emojis** (dropdown + Related Issues table):
- 💬 Original session (root or standalone — no parent in tree)
- 🔁 Continuation session (has at least one parent in tree)
- 🔗 Non-session related issue (no SESSION label)

**Session-scoped time compilation** (I1): The time compilation table in the Session Viewer shows only activities from the active user session — the session's own issue and child SESSION issues created on the same date. Pre-existing related issues (different dates) and work tickets (non-SESSION) are excluded from the time table. Duration calculations (calendar start → end) are recomputed from the scoped activities only. Users navigate to excluded issues via the related issues table or session selector. See `methodology/time-compilation.md` § "Session-Scoped Time Compilation".

**Example tree**:
```
💬 #617 (root, depth=0) "Fix file gaps & sessions viewer"
  └─ 🔁 #649 (depth=1) "Update Related Issues table"
       ├─ 🔁 #664 (depth=2) "Multi-request detection"
       └─ 🔁 #665 (depth=2) "README.md essential file"
```

### 6. Context Loss Recovery (Mid-Session)

When a session hits the context window limit, the conversation gets **compacted** — prior messages are summarized and the session continues with a fresh context. The mind is lost, but git and the session cache survive.

**Recovery protocol** — cache-first, then git:

1. **Read session cache** — `read_runtime_cache()` from `scripts/session_agent.py` recovers: issue number, request description, all `session_data` (decisions, comment IDs, todo state, add-ons, phase, PR numbers, time markers, elevation status, work summary). This is the **first recovery action** — it restores session-specific state that no other source has.
2. **Run `refresh`** — re-reads CLAUDE.md, quick git status, reprints help. Restores formatting rules, command syntax, and methodology.
3. **Run the git recovery line**:

```bash
git branch --show-current && git status -s && git log --oneline -10
```

This tells you: branch (task assignment), uncommitted work (survived compaction), recent commits (what was pushed).

Cache + branch + uncommitted work + recent commits = complete state recovery in ~10 seconds. The session cache provides the **structured operational state** (18 typed data keys) that git status alone cannot — who asked for what, what decisions were made, which issue comments were posted, what phase the work is in.

### 5. Crash Recovery (Cross-Session)

When a session dies abruptly (API 400/500 errors, network failures, container restarts), multi-step protocol progress is lost. The checkpoint/resume system handles this:

1. **During work**: Multi-step commands (save, harvest, normalize, bootstrap) write progress to `notes/checkpoint.json` at step boundaries
2. **On crash**: The checkpoint file persists on the branch's working tree (or committed during progressive commits)
3. **On next wakeup**: Step 0.9 detects `notes/checkpoint.json` and offers resume
4. **On resume**: The interrupted protocol restarts from the last completed step

This closes the gap between compaction recovery (session alive, `refresh`) and crash recovery (session dead, `resume`). See `methodology/checkpoint-resume.md` for the full protocol.

### 6. Client Disconnect Recovery

When the client interface (browser, desktop app) disconnects mid-session — distinct from a full crash — the server-side work may have completed (commits pushed) but the final PR creation step was interrupted. The **git push is the durability boundary**: everything pushed to the remote branch survives the disconnect.

Recovery paths (fastest first):
1. **Browser refresh** — session may still be alive server-side (instant)
2. **Manual PR creation** — from the orphan branch via `gh_helper.py` or GitHub web UI (minutes)
3. **New session + `resume`** — checkpoint-based recovery creates the missing PR (~10s)
4. **Wait for harvest** — passive discovery of orphan branches (hours/days — not recommended)

PR creation is idempotent — re-running it for a branch that already has a PR returns the existing URL. See `methodology/client-disconnect-recovery.md` for the full protocol and resiliency guarantees.

## Why This Works

- **Zero ramp-up cost** — next session starts exactly where this one left off
- **No repeated explanations** — Claude reads notes, not the user's patience
- **Compounding knowledge** — each session builds on all previous sessions
- **Five-channel audit trail** — Git (code), Notes (context), Issue (complete session record with notes), Cache (structured session state), Startup Hook (continuity)
- **Structured reflection** — pre-save summary forces honest self-assessment of methodology compliance

## Notes File Format

```markdown
# Session Notes — YYYY-MM-DD

## Context
[What was the state at session start]

## Work Done
- [Decision or action with context]
- [Bug found and how it was resolved]
- [Module integrated and configuration details]

## Current State
[What works, what doesn't, what's in progress]

## Next Steps
- [What's queued]
- [What's blocked and why]
```

## Related

**6 mandatory methodology files** (the runtime unit loaded at step 0.1):
- `methodology/agent-identity.md` — WHO executes the protocol and WHY no step is ever skipped
- `methodology/working-style.md` — The USER's communication patterns (bilingual, visual, rapid)
- `methodology/interactive-work-sessions.md` — HOW sessions flow (5 persistence channels, resilience)
- `methodology/task-workflow.md` — 8-stage task state machine (drives the "task received" phase)
- `methodology/engineering-taxonomy.md` — 10 engineering stages + 11 request types (classification layer)

**Publications and on-demand methodologies**:
- Publication #8 — Session Management (lifecycle commands)
- Publication #3 — AI Session Persistence (foundational persistence)
- Publication #19 — Interactive Work Sessions (resilience patterns)
- `methodology/checkpoint-resume.md` — Crash recovery mechanics
- `methodology/metrics-compilation.md` — Metrics compilation routine
- `methodology/time-compilation.md` — Time compilation routine
