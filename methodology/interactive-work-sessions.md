# Interactive Work Sessions — Methodology

**Resilient, multi-delivery interactive sessions** — How to run productive work sessions that survive crashes, produce progressive deliverables, and persist knowledge through multiple channels.

---

## When to Use

Any session where the user requests multiple deliverables or the work naturally spans several steps:

| Session type | Examples |
|-------------|----------|
| **Interactive design** | Designing new features, architectures, webcards, UI layouts |
| **Interactive documentation** | Creating publications, methodologies, success stories |
| **Interactive feature development** | Building commands, scripts, pipelines |
| **Interactive diagnostic** | Debugging rendering, integration, behavioral problems (see also `methodology/interactive-diagnostic.md`) |

**Not needed for**: Single-file edits, quick lookups, status checks, one-shot commands.

---

## Core Principles

| # | Principle | Why |
|---|-----------|-----|
| 1 | **GitHub Issue as session anchor** | External persistence — survives session crashes, captures context that files don't |
| 2 | **Progressive commits** | Each completed step is committed — no "big bang" commit at session end |
| 3 | **Push as savepoint** | Push to branch at each major milestone — `recover` can retrieve stranded work if session dies |
| 4 | **Todo-driven execution** | TodoWrite tracks all steps — one `in_progress` at a time, mark `completed` immediately |
| 5 | **User correction > AI assumption** | When the user redirects, follow immediately — they see the rendered output, you see code. **Never reinterpret what the user said and build on a wrong assumption.** When the user flags a concern (e.g., "X can grow"), ask what they mean before engineering a solution. Misunderstanding + autonomous execution = wasted time, compute, and user energy to course-correct. After compaction, this risk multiplies — shared understanding is lost, verify before building. |
| 6 | **Essential files are memory** | Universal inheritance — every deliverable triggers NEWS/PLAN/LINKS/CLAUDE.md/STORIES.md check |
| 7 | **Context budget awareness** | Avoid unbounded searches — focus on essential files, not exhaustive scans |
| 8 | **GitHub Issues as secondary persistence** | Issue comments capture what wasn't committed yet — precious source of methodology |

---

## Session Protocol

### 1. Anchor the Session (v51 — On Task Received)

**Every session entry message is presumed to be a work request.** After wakeup completes, **before the first file is touched**, the session issue protocol runs automatically:

1. **Extract title** from the user's message (heuristics: strip command prefixes, capitalize, keep concise)
2. **Confirm via `AskUserQuestion`** — proposed title + "Skip tracking" option. **NEVER create the issue before this confirmation step.** The popup is the user's decision point — skip it and you violate the user's control over what gets tracked.
3. **Create GitHub issue** — `SESSION: <title> (YYYY-MM-DD)`, `SESSION` label (only after step 2 confirmation)
4. **Link to project board** — set status to "In Progress"
5. **Post verbatim first comment** — the user's exact original request, unmodified:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="20"> Martin — Demande originale (verbatim)
> <user's EXACT words, copied character for character, no reformulation>
*Ce commentaire est la demande originale intégrale de l'utilisateur, non modifiée.*
```

**Verbatim rule**: The first comment is frozen — never modified after posting. Claude's analysis comes in the second comment (🤖), not the first.

**When to create an issue** — the trigger is **"the user provides a work request"**, not "the session will modify files":
- Feature development, bug fixes, refactoring (code changes)
- Reviews, validations, audits (read-only analysis)
- Diagnostics, root cause analysis (investigation)
- Documentation generation, publication updates (content)

**When NOT to create**: Only when the user explicitly says "skip tracking" or "no issue." Infrastructure commands (`wakeup`, `refresh`, `help`) are not tasks. The session never judges a request as "too trivial" — every work request gets tracked (v59.3).

Or if a GitHub Issue already exists (e.g., from the project board):

```
g:<board>:<item>:progress
```

### 2. Plan with TodoWrite

Break the user's request into concrete, deliverable steps. Each todo should be:
- **Atomic**: one clear deliverable per todo
- **Ordered**: dependencies flow naturally
- **Estimable**: the scope is clear before starting

```
TodoWrite:
1. [in_progress] First deliverable
2. [pending] Second deliverable
3. [pending] Third deliverable
...
```

**Rule**: Exactly one todo `in_progress` at a time. Mark `completed` immediately on finish — don't batch completions.

### 3. Execute with Progressive Commits

For each todo:

```
[start todo] → do the work → commit → push → [mark completed] → [post issue comment] → [next todo]
```

**The full cycle**: Each completed todo triggers THREE actions: (1) commit the deliverable, (2) mark the todo completed in TodoWrite, (3) post a 🤖 comment on the session issue summarizing what was done. This creates a 1:1 correspondence between todos, commits, and issue comments — the complete audit trail.

**Progressive commit rules**:

| When | What to commit | Issue comment? | Why |
|------|---------------|----------------|-----|
| After each todo completion | All files from that deliverable | **Yes** — step name + summary | Savepoint — recoverable via `recover` |
| After discovering new files to update | The discovery itself (e.g., stale index) | Optional | Capture the insight before context overflow |
| Before a risky operation | Everything so far | Optional | Insurance — the branch has the latest state |
| After user correction | The corrected approach | **Yes** — document the correction | Prevents repeating the same mistake |

**Push cadence**: Push after each major commit. The branch is the safety net — `recover` retrieves stranded work from branches. Uncommitted work dies with the session.

**Issue comment format for todo completion**:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — Todo N complété : <step name>
### Livrable
- <files modified/created>
- <brief summary of what was done>
```

### 3.1. Command Sub-Tasks in Work Cycle (v100)

When a todo step involves a methodology-backed command (e.g., `project create X`, `harvest --healthcheck`, `normalize --fix`), the command executes as a **tracked sub-task** within the work cycle:

```
[todo: execute command] →
  create_sub_task(command, skill, title, args, ...) →
  start_sub_task(id) →
  execute command skill (.claude/skills/<name>.md) →
  complete_sub_task(id, commits, files_modified) →
  post issue comment (G7) →
[next todo]
```

**Persistence**: Sub-tasks are stored in `session_data.sub_tasks[]` in the runtime cache — the 4th persistence channel. Each sub-task records its own status, commits, and files_modified independently from the parent task.

**Issue comments**: Sub-task start and completion are posted as issue comments, following the same G7 real-time posting rules as regular todo steps. Format:

```markdown
## <img src=".../vicky-sunglasses.png" width="20"> Claude — Sub-task: project create Studio 54
### Livrable
- Created `projects/studio-54.md` (P13)
- GitHub Project board created and linked
- Status: ✅ completed
```

**Failure handling**: If a sub-task fails, call `fail_sub_task(id, reason)`. The parent task does NOT halt — other sub-tasks and todos can proceed. The failure is posted on the issue and the user decides next steps.

**Full specification**: `methodology/task-workflow.md` § "Command Detection & Sub-Task Lifecycle (v100)"

### 4. Integrate User Corrections

When the user says "you're looking at the wrong place" or "try this instead":

1. **Stop immediately** — don't finish the current wrong approach
2. **Acknowledge** — "you're right, the essential file is X not Y"
3. **Adapt** — switch to the correct approach
4. **Learn** — if the correction reveals a pattern, capture it (e.g., "profile pages are low priority, essential files are what matter")

**Anti-pattern**: Ignoring the user's simpler fix and engineering alternatives (Pitfall #22). The person observing the output has information you don't.

### 5. Deliver with Universal Inheritance

After the last todo, before committing the final deliverable:

1. **Check essential files** — per `methodology/documentation-generation.md`:

| File | Check |
|------|-------|
| `README.md` | Project description, badges, or feature summary current? |
| `NEWS.md` | New entries for all deliverables? |
| `CHANGELOG.md` | New issue/PR entries for all changes? |
| `PLAN.md` | What's New updated? Ongoing items resolved? |
| `LINKS.md` | New URLs added? Page counts updated? |
| `VERSION.md` | Version/subversion updated if evolution entry? |
| `CLAUDE.md` | Publications table current? |
| `STORIES.md` | New success story captured? |
| `publications/README.md` | Master index updated? |
| EN/FR publication indexes | New publications listed? |

2. **Commit + push + report** — the final delivery includes all essential files

### 6. Close the Loop (v50/v51/v55)

At session end, the pre-save summary (v50) triggers the closing sequence:

1. **Issue comment integrity check** — compare session exchanges vs posted comments, fill gaps
2. **Pre-save summary** — compile and display 7-section report (résumé, métriques, temps, proportions, entreprise, livraisons, auto-évaluation)
3. **`AskUserQuestion`** — "Save now" / "Continue working" / "Save + close issue"
4. **Post session notes on issue** (v55) — read generated session notes markdown and post as 🤖 comment on the session issue. The issue becomes the complete session record.
5. **Commit + push + PR** — deliver to default branch
6. **Post-save closing report** — final 🤖 comment with delivery status table + complete comment history index
7. **Close issue** — if all work is delivered
8. **Post-close final comment** (v55) — after issue is closed, post one last 🤖 comment confirming closure. This is the audit trail endpoint — the very last comment on the issue.

**Rule**: All user and Claude exchanges MUST be in the issue. Session notes posted on the issue make it the single source of truth.

The closing report is the bookend:

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

---

## Resilience Patterns

### The Five Persistence Channels

Knowledge from an interactive session persists through **five independent channels**:

| Channel | Survives crash? | Survives compaction? | Survives session end? | Real-time? |
|---------|----------------|---------------------|----------------------|-----------|
| **Git** (commits, branches) | Yes if pushed | Yes | Yes | No (batch on save) |
| **Notes** (`notes/session-*.md`) | Yes if committed | No (context-level) | Yes if committed | No (written on save) |
| **GitHub Issue** (comments) | Yes (API-persisted) | Yes (external to session) | Yes (external to session) | **Yes** (posted per exchange) |
| **Cache** (`notes/session-runtime-<suffix>.json`) | Yes (auto-committed) | Yes (persisted) | Yes (committed) | **Yes** (each state change) |
| **Startup Hook** (`.claude/hooks/startup-checklist.sh`) | Yes (code on disk) | Yes (runs pre-context) | Yes (runs every start) | **Yes** (injects at boot) |

The issue is the **only** channel that persists in real-time and survives all failure modes independently of the local environment. The cache is the **only** channel providing structured, queryable session state — surviving compaction locally with 18 typed data keys managed by `scripts/session_agent.py`. **Every cache write auto-commits to git** — all 9 write paths in `session_agent.py` call `commit_cache()` immediately after disk write. The startup hook is the **continuity layer** — it scans cache files at session boot (before Claude's context loads) and prints pending todos from previous sessions, ensuring unfinished work is visible immediately.

**During work — real-time comments**: After each significant exchange (task clarifications, design decisions, intermediate results, user feedback), post a comment:
- 🧑 for user messages (quoted, with context)
- 🤖 for Claude responses (summarized actions, findings, decisions)

**At save time — integrity check**: Before the pre-save summary, compare session exchanges against posted comments. Post any missing ones to fill gaps. This is the safety net — even if real-time posting was missed, save catches the gap.

**Maximum resilience**: All five channels active — issue anchored with real-time comments, commits progressive, essential files updated, cache auto-committing structured state, startup hook injecting continuity. Even a catastrophic session crash loses at most the current in-progress todo — the issue captures interaction, the cache captures operational state, and the startup hook feeds it to the next session.

**Minimum resilience**: No issue, no cache, no intermediate commits, all work in one final commit. A session crash loses everything.

### Recovery Matrix

| Failure | Channel 1 (Git) | Channel 2 (Issue) | Channel 3 (Files) | Channel 4 (Cache) | Channel 5 (Hook) | Recovery |
|---------|-----------------|-------------------|-------------------|--------------------|-------------------|----------|
| Context overflow | Branch intact | Issue intact | Committed files safe | **Intact** — `read_runtime_cache()` | **Active** (runs on resume) | `read_runtime_cache()` → `refresh` |
| Session crash (with checkpoint) | Branch intact | Issue intact | Checkpoint saved | **Intact** (auto-committed) | **Active** (shows pending todos) | `resume` in new session |
| Session crash (no checkpoint) | Branch intact if pushed | Issue intact | Committed files safe | **Intact** (auto-committed) | **Active** (shows pending todos) | `recover` + cache in new session |
| Container restart | Branch intact if pushed | Issue intact | Lost if not committed | **Intact** (auto-committed to git) | **Active** (shows pending todos) | New session sees pending todos |
| API 400 (unrecoverable) | Branch intact if pushed | Issue intact | Lost if not committed | **Intact** (auto-committed to git) | **Active** (shows pending todos) | New session + `recover` + hook shows state |

### Progressive Commit Safety Net

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

**The gap that progressive commits close**: Without intermediate pushes, a session crash after completing 4 of 5 todos loses ALL work — not just todo 5. With progressive pushes, only the in-progress todo is at risk.

---

## Session Type Patterns

Each session type has its own dedicated methodology file with detailed protocols. The summaries below provide the phase pattern at a glance — see the linked files for full operational details.

### Interactive Diagnostic → `methodology/interactive-diagnostic.md`

Debugging rendering, integration, or behavioral problems.

| Phase | Action | Persistence |
|-------|--------|-------------|
| **Document** | Create diagnostic task on GitHub issue | Issue |
| **Compare** | Working vs broken versions side-by-side | Issue comment |
| **Eliminate** | Systematic hypothesis testing | Issue comment per iteration |
| **Pivot** | Follow user observations (they see the output) | Issue comment |
| **Isolate** | Gradual component isolation if needed | Issue comment |
| **Resolve** | Apply fix, verify, close issue | Commit + issue |

### Interactive Documentation → `methodology/interactive-documentation.md`

Creating publications, methodologies, or web pages.

| Phase | Action | Persistence |
|-------|--------|-------------|
| **Gather** | User provides raw intelligence (`#N:` scoped notes) | Notes file |
| **Structure** | Create methodology file and/or source with mind map | Commit methodology |
| **Expand** | Write full publication source | Commit source |
| **Web pages** | Create 4 pages (EN/FR summary + complete) | Commit pages |
| **Essential files** | Universal inheritance — README/NEWS/PLAN/LINKS/VERSION/CLAUDE/STORIES | Commit essential files |
| **Deliver** | Push + PR + issue update | All four channels |

### Interactive Conception → `methodology/interactive-conception.md`

Ideating, prototyping, and validating new capabilities.

| Phase | Action | Persistence |
|-------|--------|-------------|
| **Ideate** | User shares raw idea, Claude expands | Notes / issue |
| **Explore** | Read existing code, methodology for context | — (read-only) |
| **Propose** | Present structured proposal to user | Issue comment |
| **Prototype** | Create initial artifacts (methodology, source, scripts) | Commit per artifact |
| **Validate** | User reviews, provides corrections | Issue comment |
| **Formalize** | If validated, promote to publication | Commit publication |
| **Deliver** | Essential files + push + PR | All four channels |

### Interactive Design

Building new features, architectures, or visual assets.

| Phase | Action | Persistence |
|-------|--------|-------------|
| **Explore** | Read existing code, understand constraints | — (read-only) |
| **Propose** | Present options to user | Issue comment |
| **Build** | Create files, write code | Commit per component |
| **Validate** | User reviews rendered output | Issue comment with user feedback |
| **Iterate** | Apply user corrections | Commit with fix |
| **Deliver** | Essential files + push + PR | All four channels |

### Interactive Feature Development

Building commands, scripts, or pipeline improvements.

| Phase | Action | Persistence |
|-------|--------|-------------|
| **Analyze** | Understand requirements, check existing code | — (read-only) |
| **Implement** | Write the feature | Commit per module |
| **Test** | Validate the feature works | Issue comment with results |
| **Document** | Methodology file if new pattern | Commit docs |
| **Integrate** | Update essential files, cross-references | Commit essential files |
| **Deliver** | Push + PR + issue update | All four channels |

---

## Context Budget Management

Interactive sessions consume context tokens rapidly. Manage the budget:

### Do

- **Focus on essential files** — README.md, NEWS.md, PLAN.md, LINKS.md, VERSION.md, CLAUDE.md are the priority
- **Read files once** — don't re-read a file already in context
- **Commit often** — smaller commits = less context wasted on re-reading
- **Use TodoWrite** — tracks progress without consuming context on status conversations
- **Batch related edits** — update all 4 web pages in one pass, not 4 separate passes

### Don't

- **Don't scan unbounded file sets** — "check all 6 profile pages" consumed the context in a prior session
- **Don't re-read CLAUDE.md** — it's already loaded as system instructions
- **Don't loop on failing approaches** — if attempt 2 fails the same way as attempt 1, step back
- **Don't batch completions** — mark todos done immediately, not at the end

### Context Overflow Prevention

| Warning sign | Action |
|-------------|--------|
| Reading files > 500 lines repeatedly | Stop — use targeted line ranges |
| Searching across > 5 files for the same thing | Stop — use grep, not sequential reads |
| Third attempt at the same approach | Stop — ask user or try their suggestion |
| Profile pages or secondary indexes | Skip — update essential files first, batch the rest |

---

## GitHub Issue as Knowledge Persistence

GitHub Issues serve as a **secondary persistence channel** that captures session intelligence beyond what goes into files:

### What Issues Capture

| Content | Example |
|---------|---------|
| **User intent** | "I need a methodology for interactive work sessions" |
| **Decisions made** | "STORIES.md added to essential files" |
| **Corrections applied** | "Profile pages are low priority — focus on essential files" |
| **Discoveries** | "publications/README.md was stale since #4a" |
| **Methodology insights** | "The meta-methodology's own files were missing from its own checklist" |

### Why This Matters

Even when session notes aren't written and essential files aren't updated, the GitHub issue preserves:
- **What was asked** (the original task description)
- **What was discovered** (findings posted as comments)
- **What was decided** (recorded in the issue thread)
- **What was delivered** (PR linked to the issue via `Closes #N`)

This makes issues a **precious source of methodology** — they capture the messy, iterative reality of interactive work that polished publications and clean methodology files don't.

### Universal Inheritance Extension

GitHub Issues extend the universal inheritance principle to the platform layer:

```
[methodology-specific steps]
    → produce deliverable (files, PRs, publications)
    → THEN: evaluate essential files for update
    → THEN: update GitHub Issue with outcome
    → THEN: commit and deliver all changes together
```

---

## Anti-Patterns

| Anti-pattern | Description | Fix |
|-------------|-------------|-----|
| **Big bang commit** | All work in one commit at session end | Progressive commits at each todo |
| **Push at end only** | Branch not pushed until save | Push at each major milestone |
| **No issue anchor** | Session work not tracked externally | Open/reference issue at session start |
| **Issue before popup** | Creating the GitHub issue before AskUserQuestion title confirmation | Popup FIRST, then create issue after user confirms |
| **Silent todo completion** | Marking todos done without posting issue comment | Each completed todo = one issue comment |
| **Ignoring user corrections** | Engineering around what user says | Try user's suggestion first (Pitfall #22) |
| **Unbounded file scanning** | Reading every file in a directory | Target essential files only |
| **Batched todo completions** | Marking 3 todos done at once | Mark each done immediately |
| **Re-reading loaded files** | Reading CLAUDE.md again after compaction | Use `refresh` instead |
| **Missing essential files** | Forgetting NEWS.md or STORIES.md | Universal inheritance checklist |

---

## Relationship to Other Methodologies

**6 mandatory methodology files** (loaded together at step 0.1 — the runtime unit):

| Methodology | Scope | Overlap |
|-------------|-------|---------|
| `agent-identity.md` | WHO handles sessions — 5 identity principles | The identity ensures every session type follows the same complete cycle |
| `working-style.md` | The USER's communication patterns | Bilingual, visual, rapid-iteration — shapes session interaction style |
| `session-protocol.md` | Session lifecycle (wakeup → work → save) | This methodology details what happens during "work" |
| `task-workflow.md` | 8-stage task state machine | Drives task progression; this methodology defines the persistence channels that survive across stages |
| `engineering-taxonomy.md` | 10 engineering stages + 11 request types | Request types determine the session mode (diagnostic, build, document); engineering stages track progress |

**On-demand methodologies** (loaded when their command is invoked):

| Methodology | Scope | Overlap |
|-------------|-------|---------|
| `interactive-diagnostic.md` | Diagnostic session type | Hypothesis elimination, gradual isolation |
| `interactive-documentation.md` | Documentation session type | Three-tier publications, bilingual mirroring |
| `interactive-conception.md` | Conception session type | Ideation, prototyping, progressive crystallization |
| `documentation-generation.md` | Publication creation standards | Applied during documentation and conception sessions |
| `checkpoint-resume.md` | Crash recovery mechanics | The technical mechanism behind resilience patterns |
| `client-disconnect-recovery.md` | Client disconnect handling | One failure mode in the recovery matrix |

---

## Related

- Publication #19 — Interactive Work Sessions (this methodology's publication)
- Publication #8 — Session Management (lifecycle commands)
- Publication #3 — AI Session Persistence (foundational persistence)
- Publication #11 — Success Stories (validated session outcomes)
- Publication #18 — Documentation Generation (universal inheritance)
- `methodology/session-protocol.md` — Session lifecycle
- `methodology/interactive-diagnostic.md` — Diagnostic session type
- `methodology/interactive-documentation.md` — Documentation session type
- `methodology/interactive-conception.md` — Conception session type
- `methodology/checkpoint-resume.md` — Crash recovery mechanics
