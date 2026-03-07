# Metrics Compilation — Session Productivity Measurement

**Routine for compiling what was produced during interactive work sessions.**

---

## Purpose

Every session generates measurable output: PRs merged, files changed, publications created, issues resolved. Without compilation, this evidence is scattered across git history and GitHub API. The metrics compilation sheet captures it in a structured, appendable format.

---

## Incremental Compilation Principles

Compile **at each task advancement**, not at session end. Three rules:

1. **Incremental** — compile at each task advancement (not batched to end)
2. **Anti-compaction** — commit compilation data regularly (progressive commits protect against context loss)
3. **Append-only** — continue from where you left off, never rebuild from scratch (unless data integrity requires it)

### Compilation Triggers

| Trigger | Action | Commit? |
|---------|--------|---------|
| User task confirmed (Phase 1) | Add metrics row + time row for completed task | Yes — progressive commit |
| 3+ tasks accumulated without compilation | Compile all pending rows | Yes — catch-up |
| Before risky operation | Compile current state | Yes — insurance |
| Session approaching compaction | Compile everything pending | Yes — anti-compaction |
| Session end (`save`) | Final compilation pass + summary row | Yes — delivery |

These principles apply equally to `time-compilation.md` — both sheets share the same triggers and rules.

---

## Category Grid

All metrics are organized by interaction category:

| Icon | Category | Description |
|------|----------|-------------|
| 🔍 | **Diagnostic** | Bug fixes, root cause analysis, troubleshooting |
| 💡 | **Conception** | Design sessions, architecture exploration, new ideas |
| 📝 | **Documentation** | Publication creation, methodology files, web pages |
| 📋 | **Doc Management** | Essential files, indexes, NEWS.md, metadata updates |
| ⚙️ | **Collateral** | GitHub issues/boards, infrastructure, tooling, diagrams |

---

## Metrics Fields

| Field | Source | How to collect |
|-------|--------|----------------|
| **Todo** | Issue title or user request | Bold row — primary deliverable |
| **Task** | Sub-issue or PR title | Indented row beneath todo |
| **Category** | Session interaction type | Assign icon from grid above |
| **PRs** | GitHub API | Count PRs linked to the todo |
| **Files** | `git diff --stat` or PR API | `changed_files` from PR response |
| **Lines+** | PR API | `additions` field |
| **Lines−** | PR API | `deletions` field |
| **Issues** | GitHub API | Count issues closed by the todo's PRs |
| **Deliverables** | Manual | Publications, methodologies, pitfalls, stories created |

---

## Summary Line Convention

**Every compilation table must have a summary line ABOVE the table** — a standalone line displaying column totals before the detail rows. This gives instant visibility on aggregated values without scrolling to the bottom.

```markdown
**Totals: 12 todos · 20 PRs · 288 files · +17,974 −6,049 lines · 6 pubs, 4 metho, 3 pitfalls**

| Category | Todos | PRs | Files | Lines+ | Lines− | Deliverables |
|----------|-------|-----|-------|--------|--------|--------------|
| 🔍 Diagnostic | 1 | 9 | 207 | 9,338 | 5,733 | 3 pitfalls |
| ...
```

The summary line format:
- **Bold** text, standalone paragraph above the table
- Separator: `·` (middle dot) between metrics
- Quantities: numbers with unit labels
- Time (for time tables): accumulated in hours/days/weeks as appropriate
- Must match the column sums of the table below exactly

---

## Summary Table Format

One row per category, aggregated. Summary line on top:

```markdown
**Totals: 12 todos · 20 PRs · 288 files · +17,974 −6,049 lines · 6 pubs, 4 metho, 3 pitfalls**

| Category | Todos | PRs | Files | Lines+ | Lines− | Deliverables |
|----------|-------|-----|-------|--------|--------|--------------|
| 🔍 Diagnostic | 1 | 9 | 207 | 9,338 | 5,733 | 3 pitfalls |
| 📝 Documentation | 4 | 4 | 43 | 4,358 | 240 | 6 publications |
| ...
```

---

## Detailed Table Format

Each category section, todos bold, tasks indented. Summary line on top of each section:

```markdown
### 🔍 Diagnostic

**Totals: 1 todo · 9 PRs · 207 files · +9,338 −5,733 lines · 3 pitfalls**

| # | Todo / Task | Issue | PRs | Files | Lines+ | Lines− | Deliverables |
|---|-------------|-------|-----|-------|--------|--------|--------------|
| **T3** | **Diagnostic diagrammes pages web** | #334 | 9 | 207 | 9,338 | 5,733 | 3 pitfalls |
| | → Replace Mermaid with PNG | — | #337 | 30 | 28 | 1,444 | — |
| | → Dual-theme diagrams | — | #338 | 62 | 245 | 161 | — |
| | → Theme switcher + Pub #16 | — | #340 | 23 | 3,354 | 3 | 1 pub |
| | → Re-render 28 PNGs | — | #341 | 80 | 3,373 | 5 | — |
```

---

## Multi-Issue Session Support

Sessions often work on multiple issues (fixing one thing leads to another, add-ons spawn new issues, or related issues are tackled together). When a session touches multiple issues, metrics MUST be grouped **per issue** with a session-level aggregate.

### Multi-Issue Summary Table

```markdown
**Session totals: 3 issues · 8 todos · 5 PRs · 42 files · +2,847 −391 lines**

| Issue | Title | Todos | PRs | Files | Lines+ | Lines− | Deliverables |
|-------|-------|-------|-----|-------|--------|--------|--------------|
| #607 | Fix session lifecycle | 4 | 2 | 3 | +116 | −13 | 6 gates |
| #609 | Add G7 enforcement | 2 | 1 | 2 | +44 | −19 | Gate G7 |
| #612 | Multi-issue metrics | 2 | 2 | 4 | +2,687 | −359 | 3 methodologies |
| **Total** | | **8** | **5** | **42** | **+2,847** | **−391** | |
```

### Per-Issue Detail Rows

Each issue section expands into its todo rows:

```markdown
### Issue #607 — Fix session lifecycle
**Totals: 4 todos · 2 PRs · 3 files · +116 −13 lines**

| # | Todo / Task | PRs | Files | Lines+ | Lines− | Category |
|---|-------------|-----|-------|--------|--------|----------|
| **T1** | **Restructure session-protocol.md** | #608 | 1 | +89 | −8 | 📝 Documentation |
| **T2** | **Add cache lifecycle** | #608 | 1 | +15 | −3 | ⚙️ Collateral |
| ...
```

### When to Use Multi-Issue Format

| Condition | Format |
|-----------|--------|
| Session worked on 1 issue | Standard single-issue format (category table) |
| Session worked on 2+ issues | Multi-issue format: issue summary table + per-issue detail |
| Related issues from same request | Group under parent issue, sub-issues as rows |

### Data Collection Per Issue

For each issue in the session:
1. Collect all PRs that reference the issue (`Closes #N`, linked PRs)
2. Query each PR's stats via GitHub API (`additions`, `deletions`, `changed_files`)
3. Sum per issue, then aggregate across all issues for session totals
4. Store issue list in runtime cache: `update_session_data('issues_worked', [607, 609, 612])`

---

## Collection Protocol

### After each task confirmation (Phase 1 gate)

1. Note the PR number(s) for the completed task
2. Query PR stats: `python3 -c "..." ` via gh_helper or GitHub API
3. Add one row to the metrics sheet (append, not rebuild)
4. Commit the updated compilation file

### At session end (`save`) — Pre-Save Summary (v50)

The pre-save summary (v50) automatically compiles metrics as part of its 5-section report. The metrics table uses the same summary line + category table format defined here:

```markdown
**Totals: N todos · N PRs · N files · +X −Y lines · <deliverables>**

| Catégorie | Todos | PRs | Fichiers | Lignes+ | Lignes− | Livrables |
|-----------|-------|-----|----------|---------|---------|-----------|
| 📝 Documentation | N | N | N | N | N | N méthodologies |
| ⚙️ Collatéral | N | N | N | N | N | N issues |
```

The summary is also posted as the final 🤖 comment on the session's GitHub issue — persisting the compilation in the three-channel model (v51).

**Steps at save time:**
1. Sum each category column
2. Add **Total** row
3. Display in pre-save summary (auto-compiled from git diff + PR API + todo count)
4. Post to session issue as final comment
5. Commit final compilation

### Cross-session append

When starting a new session, read the previous session's compilation from `notes/`. Append new data below the separator. Category totals accumulate.

---

## Data Sources Priority

| Priority | Source | Accuracy | When to use |
|----------|--------|----------|-------------|
| 1 | GitHub PR API (`additions`, `deletions`, `changed_files`) | Exact | Always — primary source |
| 2 | `git diff --stat` between commits | Exact | When PR not yet created |
| 3 | `git log --stat` | Good | Quick estimation during work |
| 4 | Manual count | Estimate | Last resort |

---

## Enterprise Equivalent — Output Ventilation

### Why Ventilate Enterprise Estimates

When comparing Knowledge system output to enterprise equivalent, the raw "2-4 months" estimate is powerful but incomplete. Splitting the enterprise estimate into **Réalisation / Documentation / Formation** reveals the true leverage:

1. **Enterprise teams rarely deliver all three** — implementation ships, documentation is deferred ("next sprint"), training is ad hoc
2. **Knowledge delivers all three simultaneously** — documentation and training artifacts are byproducts of the work itself
3. **The documentation debt is invisible** — without ventilation, a "2-month enterprise" estimate might only cover réalisation, hiding the 1-2 months of documentation that was never done

### Enterprise Output Categories

| Category | Icon | Enterprise reality | Knowledge reality |
|----------|------|-------------------|-------------------|
| 🔨 **Réalisation** | Code, config, deployment, QA | Primary deliverable — what gets tracked | Same session — committed progressively |
| 📝 **Documentation** | Technical docs, user guides, architecture, bilingual | Often deferred or outsourced to tech writers | Generated during work — publications, methodology, web pages |
| 🎓 **Formation** | Training materials, workshops, onboarding docs | Separate budget, separate timeline | Byproduct — methodology files, session issues, success stories ARE the training |

### Metrics Integration

In the metrics summary table, add an Enterprise Equivalent section when compiling session-level or story-level reports:

```markdown
**--- Équivalent entreprise / Enterprise Equivalent ---**

| Catégorie | Temps entreprise | Livrables Knowledge | Inclus dans session ? |
|-----------|-----------------|--------------------|-----------------------|
| 🔨 Réalisation | 3–6 sem. | 4 PRs, 288 files | ✅ Oui |
| 📝 Documentation | 2–4 sem. | 6 publications, 4 méthodologies | ✅ Oui |
| 🎓 Formation | 1–2 sem. | Session issues, success stories | ✅ Sous-produit |
| **Total** | **6–12 sem.** | **Tout livré** | **✅ Même session** |
```

The "Inclus dans session ?" column drives the message: everything enterprise treats as separate phases, Knowledge delivers as one integrated output.

### Cross-Reference

Enterprise ventilation is defined in detail in `methodology/time-compilation.md` (Enterprise Equivalent Ventilation section). The time file covers duration estimates; this file covers output/deliverable mapping. Both use the same 🔨/📝/🎓 icons for cross-referenceability.

---

## Related

- Publication #20 — Session Metrics & Time Compilation (full specification)
- `methodology/time-compilation.md` — Time compilation routine (parallel sheet)
- `methodology/documentation-generation.md` — Incremental compilation routine (parent principle)
