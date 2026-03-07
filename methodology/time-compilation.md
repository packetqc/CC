# Time Compilation — Session Duration Measurement

**Routine for compiling how long each task took during interactive work sessions.**

---

## Purpose

Demonstrating productivity requires time evidence alongside metrics. The time compilation sheet tracks session blocks, per-task durations, and category breakdowns — appendable across sessions for weekly/monthly aggregation.

---

## Category Grid

Same grid as metrics compilation — identical categories ensure both sheets are cross-referenceable:

| Icon | Category | Description |
|------|----------|-------------|
| 🔍 | **Diagnostic** | Bug fixes, root cause analysis, troubleshooting |
| 💡 | **Conception** | Design sessions, architecture exploration, new ideas |
| 📝 | **Documentation** | Publication creation, methodology files, web pages |
| 📋 | **Doc Management** | Essential files, indexes, NEWS.md, metadata updates |
| ⚙️ | **Collateral** | GitHub issues/boards, infrastructure, tooling, diagrams |

---

## Time Fields

| Field | Source | How to collect |
|-------|--------|----------------|
| **Todo** | Issue title or user request | Bold row — primary deliverable |
| **Start** | Issue creation timestamp | `created_at` from GitHub API |
| **End** | Next todo start or session end | Inferred from next issue timestamp |
| **Duration** | End − Start | Calculated (format: `Xh YYmin`) |
| **Category** | Session interaction type | Assign icon from grid above |
| **Block** | Session time block | Morning / Afternoon / Evening |

---

## Summary Line Convention

**Same convention as metrics compilation**: every time table must have a **summary line ABOVE the table** — a standalone bold line displaying column totals. Instant visibility on total hours without scrolling.

```markdown
**Totals: 12 todos · ~10h04 active · 3 blocks · avg ~50min/todo**

| Category | Todos | Total Time | Avg per Todo |
|----------|-------|------------|--------------|
| 🔍 Diagnostic | 1 | 1h16 | 1h16 |
| ...
```

Time accumulation units adapt to the period:
- Session: hours + minutes (`~10h04`)
- Week: hours (`42h`)
- Month: hours or days (`168h` or `~21 days`)

---

## Summary Table Format

One row per category, aggregated. Summary line on top:

```markdown
**Totals: 12 todos · ~10h04 active · 3 blocks · avg ~50min/todo**

| Category | Todos | Total Time | Avg per Todo |
|----------|-------|------------|--------------|
| 🔍 Diagnostic | 1 | 1h16 | 1h16 |
| 💡 Conception | 4 | 1h43 | 26min |
| 📝 Documentation | 4 | 6h46 | 1h42 |
| 📋 Doc Management | 2 | 19min | 10min |
```

---

## Detailed Table Format

Each todo with start/end/duration, grouped by session block. Summary line on top of each block:

```markdown
### Block: Morning (06:07–08:30)

**Totals: 2 todos · ~2h23 active**

| # | Todo | Start | End | Duration | Category |
|---|------|-------|-----|----------|----------|
| **T1** | **Revue documentaire** | 06:07 | 07:57 | 1h50 | 📝 Documentation |
| **T2** | **Enrichissement iteration 2** | 07:57 | ~08:30 | ~33min | 📝 Documentation |
```

---

## Multi-Issue Session Support

When a session works on multiple issues, time MUST be tracked **per issue** with a session-level aggregate. Each issue gets its own time rows, and the session summary shows total time per issue.

### Multi-Issue Time Summary

```markdown
**Session totals: 3 issues · 8 todos · ~2h15 actif · 2 blocs**

| Issue | Title | Todos | Durée | Début | Fin | Catégorie dominante |
|-------|-------|-------|-------|-------|-----|---------------------|
| #607 | Fix session lifecycle | 4 | ~1h05 | 14:30 | 15:35 | 📝 Documentation |
| #609 | Add G7 enforcement | 2 | ~0h35 | 15:35 | 16:10 | 📝 Documentation |
| #612 | Multi-issue metrics | 2 | ~0h35 | 16:10 | 16:45 | ⚙️ Collateral |
| **Total** | | **8** | **~2h15** | **14:30** | **16:45** | |
```

### Per-Issue Time Detail

Each issue expands into its todo time rows:

```markdown
### Issue #607 — Fix session lifecycle (~1h05)

| # | Todo | Début | Fin | Durée | Catégorie |
|---|------|-------|-----|-------|-----------|
| **T1** | **Restructure session-protocol.md** | 14:30 | 14:55 | ~25min | 📝 Documentation |
| **T2** | **Add cache lifecycle** | 14:55 | 15:10 | ~15min | ⚙️ Collateral |
| ...
```

### Issue Transition Timestamps

When the session transitions from one issue to another, the **end time of the last todo on issue N** = **start time of the first todo on issue N+1**. Gaps between issues (user reading, thinking, new request) are captured as idle time in the proportions model.

### When to Use Multi-Issue Format

| Condition | Format |
|-----------|--------|
| Session worked on 1 issue | Standard single-issue format (time block table) |
| Session worked on 2+ issues | Multi-issue format: issue time summary + per-issue detail |
| Issues worked sequentially | Ordered by start time, no overlap |
| Issues worked interleaved | Group by issue, note interleaving in comments |

---

## Session-Scoped Time Compilation

### Principle

The time compilation table shows **only activities from the active user session** — the session's own issue and child session issues created on the same date. Pre-existing related issues (created on different dates, referenced but not spawned by this session) are **excluded** from the time table.

### Rationale

A session represents a bounded work period at a specific date and time. Including activities from related issues created on different dates pollutes the timeline with out-of-context entries — durations that don't correspond to the session's active period. The user expects to see a coherent timeline of what happened during *this* session.

### Navigation to excluded issues

Activities from related issues not shown in the time table are accessible via:
1. **Related issues table** — click the issue link to view its own session page
2. **Session selector dropdown** — select the related issue's session directly

### Scoping rules

| Issue type | Included in time table? | Why |
|------------|------------------------|-----|
| Session's own issue | Always (all comments) | It IS the session |
| Child/related issue — comments on session date | Yes (session-date comments only) | Activities the session interacted with |
| Child/related issue — comments on other dates | No | Different work period — view separately |

### Impact on duration calculations

When the time table is session-scoped, the calendar time span (start → end) is recomputed from only the included comments and PRs. This ensures the duration reflects the actual active session period, not a span inflated by activities on other dates.

---

## Inactive Time

**Definition**: Inactive time is the gap between consecutive task activities within a session. It represents the time the user spends on reflections, decisions, and short pauses between interactions with the system.

**What inactive time includes**:
- Reading and analyzing Claude's output before responding
- Thinking about the next instruction or decision
- Brief context switches (checking another tab, reviewing output)
- Short breaks between prompts (coffee, bio)
- Reviewing screenshots, logs, or rendered output

**What inactive time does NOT include**:
- Extended breaks (lunch, end-of-day) — these are excluded from session scope
- Parallel work on other systems — log as sub-tasks (see Time Proportion Model)
- Machine processing time — this is active time

**Display**: The Session Viewer (I1) shows a bilingual note under every time compilation table: *"Inactive time reflects reflections, decisions, and short pauses between user–system interactions."*

**Calculation**: `Inactive = Calendar time − Active time`. Per-row: gap between the end of one comment/PR activity and the start of the next. Session total: calendar span minus sum of active durations.

---

## Collection Protocol

### Timestamp sources (priority order)

| Priority | Source | Accuracy | When to use |
|----------|--------|----------|-------------|
| 1 | GitHub issue `created_at` | Exact | Always — primary (issue created at request time) |
| 2 | Commit timestamps | Good | When issue not created at request time |
| 3 | Session conversation markers | Estimate | When neither above available |
| 4 | Video frame timestamps | Good | Reconciliation from recorded sessions |

### After each task confirmation (Phase 1 gate)

1. Note the issue number and creation time
2. Calculate duration: current time − issue creation time
3. Add one row to the time sheet (append, not rebuild)
4. Commit the updated compilation file

### At session end (`save`) — Pre-Save Summary (v50)

The pre-save summary (v50) automatically compiles time data as part of its 5-section report. The time table uses the same summary line + time block table format defined here:

```markdown
**Totals: N todos · ~Xh YYmin actif · N blocs · moy ~Nmin/todo**

| # | Todo | Début | Fin | Durée | Catégorie |
|---|------|-------|-----|-------|-----------|
| **T1** | **<task>** | HH:MM | HH:MM | ~Nmin | 📝 Documentation |
```

Time fields in the pre-save summary:
- **Temps actif / Active time**: sum of task durations (work time only)
- **Temps calendrier / Calendar time**: wall clock from first to last action
- **Blocs / Blocks**: Morning (05:00–12:00), Afternoon (12:00–18:00), Evening (18:00–23:00)

The summary is also posted as the final 🤖 comment on the session's GitHub issue — persisting the compilation in the three-channel model (v51).

**Steps at save time:**
1. Sum each category duration
2. Add **Total** row with session total
3. Display in pre-save summary (auto-compiled from issue timestamps + commit timestamps)
4. Post to session issue as final comment
5. Commit final compilation

### Cross-session append

When starting a new session, read the previous session's time compilation from `notes/`. Append new data below the separator. Category totals accumulate. Week/month summaries computed from appended data.

---

## Time Block Convention

Sessions are divided into named blocks based on natural breaks:

| Block | Typical hours | Notes |
|-------|---------------|-------|
| Morning | 05:00–12:00 | First work block |
| Afternoon | 12:00–18:00 | Post-lunch block |
| Evening | 18:00–23:00 | Final block |

Breaks between blocks (lunch, pauses) are NOT counted in work time. Only active task time is compiled.

---

## Aggregation

### Weekly summary

```markdown
| Date | Session Hours | Todos | Category Breakdown |
|------|---------------|-------|--------------------|
| 2026-02-26 | 10h04 | 12 | 🔍 1h16, 💡 1h43, 📝 6h46, 📋 19min |
| 2026-02-27 | ... | ... | ... |
| **Week Total** | **...** | **...** | ... |
```

### Monthly rollup

Same format, one row per week. Category breakdowns show trends (more diagnostic? more documentation?) over time.

---

## Time Proportion Model — Pie Chart à 3 Pointes

### The Problem with Current Presentation

Session reports historically presented proportions as "95% execution, 5% calendar" — which is **inverted and misleading**. The reality: active machine time is a **small fraction** of total calendar time, not the other way around. A 2-hour session spread across a full workday is ~25% execution vs ~75% calendar, not 95%/5%.

### The 3-Slice Model

Every session's time decomposes into three measurable slices:

| Slice | Icon | Description | How to measure |
|-------|------|-------------|----------------|
| **Machine** | 🤖 | Claude execution time — from prompt receipt to response completion | Sum of all tool execution + generation durations. Starts when Claude receives a prompt, ends when the response is complete. |
| **Humain** | 🧑 | User active work time — between Claude instructions | Gap time where the user is working: reading output, manual tasks, other systems, sub-tasks outside this session. Measurable when user logs sub-tasks. |
| **Calendrier** | 🕐 | Total wall clock — session start to session end | First prompt timestamp to last action timestamp. Includes all gaps, breaks, context switches. |

**Relationship**: Machine + Humain + Idle = Calendrier

Where **Idle** is truly inactive time (breaks, interruptions, end-of-day). In practice:
- **Machine** is directly measurable (Claude knows when it starts and stops processing)
- **Calendrier** is directly measurable (first action to last action)
- **Humain** is the gap: Calendrier − Machine − Idle (estimated or user-reported)

### Proportion Integrity Rules

1. **Machine ≤ Calendrier** — always. Machine time is a fraction of calendar time, never the inverse
2. **Realistic ratios**: A focused 2-hour session over 4 calendar hours = 50% machine. A distributed session over a full day = 10-25% machine. Never 95%.
3. **When Machine ≈ Calendrier** (ratio > 80%): the session was an uninterrupted burst — rare, flag as such
4. **When Machine << Calendrier** (ratio < 20%): the user had significant parallel work — document what they were doing if known
5. **The pie chart tells the story**: a large Machine slice = Claude did most of the work. A large Humain slice = significant user parallel activity. A large Idle slice = distributed work over many days (like Story #8's 3h over 23 days)

### Compilation Format

In the pre-save summary, add after the time block table:

```markdown
**--- Proportions temporelles / Time Proportions ---**

| Tranche | Durée | % du calendrier |
|---------|-------|-----------------|
| 🤖 Machine (Claude) | ~1h45 | 44% |
| 🧑 Humain (utilisateur) | ~0h15 | 6% |
| 🕐 Inactif / pauses | ~2h00 | 50% |
| **Total calendrier** | **~4h00** | **100%** |
```

### User Sub-Task Integration

The **Humain** slice is often empty or estimated ("the user was probably doing something between prompts"). To make it compilable:

1. **User creates sub-tasks**: When the user is working on a manual task, a task in another system, or a non-computerized task alongside the Claude session, they can log it:
   ```
   remember sub-task: 15min — tested LED hardware manually on bench
   remember sub-task: 30min — reviewed PR comments on GitHub web UI
   remember sub-task: 1h — soldering prototype board
   ```

2. **Compilation**: At save time, sub-tasks are summed into the Humain slice. The pie becomes a true three-way split: Machine work + Human work + Idle/gaps.

3. **The insight**: When the Humain slice is empty (no sub-tasks logged), it means **Claude did everything** — the user was the conductor, not the performer. This is the data point that demonstrates system autonomy.

---

## Enterprise Equivalent Ventilation — Réalisation / Documentation / Formation

### The 3-Category Model

Enterprise time estimates must be split into three distinct effort categories:

| Category | Icon | Description | Enterprise reality |
|----------|------|-------------|-------------------|
| **Réalisation** | 🔨 | Implementation — coding, configuration, deployment, testing, QA | The "visible" work. What managers track. Typically 40-60% of total enterprise effort. |
| **Documentation** | 📝 | Documentation — user docs, technical docs, architecture docs, runbooks, training materials, bilingual translations | The "invisible" work. Often deferred, incomplete, or never done. When done: 20-40% of total enterprise effort. Requires separate team or dedicated sprints. |
| **Formation** | 🎓 | Training — personnel training, knowledge transfer, onboarding, workshops, certification | The "forgotten" work. Critical for adoption but rarely budgeted. When done: 10-30% of total enterprise effort depending on team size and subject complexity. |

### Why This Split Matters

In the Knowledge system, all three categories are **simultaneous byproducts** of the same session:
- **Réalisation**: Claude codes, configures, deploys
- **Documentation**: Publications, methodology files, bilingual web pages are generated during the work — not after
- **Formation**: The session itself IS the training material. Issue comments, methodology docs, and success stories are the knowledge transfer artifacts

In enterprise, these are **sequential, expensive, and often incomplete**:
1. Team implements (3-6 weeks)
2. Technical writer documents (2-4 weeks, often deferred to "next sprint")
3. Training team prepares materials (1-2 weeks)
4. Training sessions delivered (1-2 weeks per cohort)
5. Total: 7-14 weeks for what Knowledge delivers in one session

### Compilation Format

In the pre-save summary and in success stories, the Enterprise Equivalent section becomes:

```markdown
**--- Équivalent entreprise / Enterprise Equivalent ---**

| Catégorie entreprise | Temps entreprise | Temps Knowledge | Ratio |
|---------------------|-----------------|-----------------|-------|
| 🔨 Réalisation | 3–6 semaines | ~4h (inclus) | ~40-60x |
| 📝 Documentation | 2–4 semaines | ~1h30 (inclus) | ~50-80x |
| 🎓 Formation | 1–2 semaines | ~0h (sous-produit) | ∞ |
| **Total** | **6–12 semaines** | **~5h30** | **~50-80x** |

*Documentation et formation sont des sous-produits naturels du travail — non des phases séparées.*
```

### Enterprise Category Estimation Guidelines

| Subject nature | Réalisation | Documentation | Formation | Notes |
|---------------|-------------|---------------|-----------|-------|
| Simple feature | 60% | 30% | 10% | Docs may be skipped — add "undocumented" flag |
| Complex feature | 40% | 30% | 30% | Training critical for adoption |
| Infrastructure | 50% | 40% | 10% | Runbooks essential, training minimal |
| Security audit | 30% | 50% | 20% | Compliance docs dominate |
| Architecture change | 30% | 30% | 40% | Everyone needs to understand the change |
| New technology | 20% | 30% | 50% | Training dominates — new skills required |

### Formation — When Training Is Non-Negligible

The user identified training as a critical but often invisible cost. Enterprise examples:

| Scenario | Formation time | Why non-negligible |
|----------|---------------|-------------------|
| New security protocol | 2-4 weeks per team | Every developer must understand and comply |
| Database migration | 1-2 weeks per DBA | New query patterns, backup procedures |
| Architecture overhaul | 3-6 weeks | All teams retrained on new patterns |
| New tooling (CI/CD) | 1-2 weeks | Pipeline changes affect every developer |
| Compliance framework | 2-4 weeks | Legal + technical + management alignment |
| Embedded RTOS migration | 4-8 weeks | Concurrency model, debugging, toolchain |

In the Knowledge system, training artifacts are **generated during work**:
- Methodology files (`methodology/*.md`) = training materials
- Success stories = case studies for onboarding
- Publication series = reference documentation
- Session issues with 🧑/🤖 comments = interactive tutorials
- The system IS the training — reading `packetqc/knowledge` bootstraps understanding

---

## Related

- Publication #20 — Session Metrics & Time Compilation (full specification)
- `methodology/metrics-compilation.md` — Metrics compilation routine (parallel sheet)
- `methodology/documentation-generation.md` — Incremental compilation routine (parent principle)
