# Interactive Documentation — Methodology

**Creating publications, methodologies, success stories, and web pages** through interactive collaboration between Martin and Claude. The documentation session type within the [Interactive Work Sessions](interactive-work-sessions.md) framework.

---

## When to Use

- Creating a new publication (source + web pages EN/FR)
- Writing a new methodology file
- Adding success stories to STORIES.md
- Updating existing publications for freshness
- Creating or updating web page content (landing pages, hubs, indexes)

**Not needed for**: Single-file README updates, quick changelog entries, or non-interactive `pub sync` operations.

---

## Core Principles

All principles from `interactive-work-sessions.md` apply, plus documentation-specific additions:

| Principle | Description |
|-----------|-------------|
| **Three-tier awareness** | Every publication has source → summary → complete. All three must be created/updated |
| **Bilingual mirroring** | Every web page has EN + FR. Create both in the same pass — never leave one language behind |
| **Mind map first** | The visual overview is the reader's entry point. Write it before expanding content |
| **Universal inheritance** | After creating content, evaluate all essential files: README.md, NEWS.md, PLAN.md, LINKS.md, VERSION.md, CLAUDE.md, STORIES.md, publications/README.md, indexes |
| **Source is truth** | `publications/<slug>/v1/README.md` drives everything downstream |

---

## Phase Pattern

| Phase | Action | Persistence | Commit point |
|-------|--------|-------------|-------------|
| **Anchor** | Session issue protocol (v51) — create issue, post verbatim demand | GitHub issue | — (persistence step 0) |
| **Gather** | User provides raw intelligence via `#N:` scoped notes or conversation | Notes file / issue comment (🧑/🤖) | — (input phase) |
| **Structure** | Create methodology file and/or source document with mind map | Commit methodology file | ✓ After methodology file |
| **Expand** | Write full publication source (abstract → problem → solution → impact) | Commit source | ✓ After source complete |
| **Web pages** | Create 4 web pages (EN/FR summary + complete) with front matter | Commit web pages | ✓ After all 4 pages |
| **Mirror** | Verify bilingual mirrors are complete and consistent | — (verification) | — |
| **Essential files** | Universal inheritance — README/NEWS/PLAN/LINKS/VERSION/CLAUDE/STORIES/indexes | Commit essential files | ✓ After all updates |
| **Deliver** | Pre-save summary (v50) + push + PR + issue closing report | All three channels | ✓ Final push |

---

## Session Protocol

### 0. Anchor the Session (v51)

The session issue protocol (v51) applies — **before any file is touched**:

1. **Extract title** from the user's request (e.g., "Documentation — Publication #19 Interactive Work Sessions")
2. **Confirm via `AskUserQuestion`** — proposed title + "Skip tracking" option
3. **Create GitHub issue** — `SESSION: <title> (YYYY-MM-DD)`, labels: `SESSION`
4. **Post verbatim first comment** — the user's exact original request, unmodified

The issue becomes the living record of the documentation session — content gathering, structure decisions, review feedback, all captured as chronological 🧑/🤖 comments. This is the **third persistence channel** that survives crashes, compaction, and session end.

### 1. Gather Raw Intelligence

The user feeds content through various channels:
- `#N: <content>` — scoped notes routed to the publication
- `#N:methodology:<topic>` — methodology-grade insights
- `#N:principle:<topic>` — design principles
- Direct conversation — Martin explains what needs to be documented

Claude classifies and organizes internally. The user provides raw intelligence; Claude structures it.

### 2. Create Methodology File First

If the publication documents a new methodology:
1. Write `methodology/<slug>.md` — the operational reference
2. Commit immediately — this file has value independent of the publication

**Why methodology first**: The methodology file is the practitioner's guide. The publication wraps it with context, analysis, and narrative. If the session crashes after the methodology file but before the publication, the operational knowledge is already captured.

### 3. Write Publication Source

Create `publications/<slug>/v1/README.md` following `methodology/documentation-generation.md`:

1. Title block with publication number, version, date
2. Authors with role descriptions for this specific publication
3. Abstract (200–400 words) — "why" before "what"
4. Mind map diagram — visual summary after abstract
5. Problem section — the engineering need
6. Solution section — how it works
7. Impact section — before/after, design principles
8. Related publications — cross-references

Commit after the source document is complete.

### 4. Create Web Pages (Batch)

Create all 4 web pages in one pass to minimize context consumption:

| # | File | Content |
|---|------|---------|
| 1 | `docs/publications/<slug>/index.md` | EN summary — abstract + mind map + key highlights |
| 2 | `docs/publications/<slug>/full/index.md` | EN complete — full documentation |
| 3 | `docs/fr/publications/<slug>/index.md` | FR summary — translated |
| 4 | `docs/fr/publications/<slug>/full/index.md` | FR complete — translated |

**Front matter contract**: `layout`, `title`, `description`, `pub_id`, `version`, `date`, `permalink`, `og_image`, `keywords`.

Commit after all 4 pages are created.

### 5. Universal Inheritance Pass

Evaluate and update all essential files:

| File | What to update |
|------|---------------|
| `README.md` | Project description or feature summary if impacted |
| `NEWS.md` | New entry for the publication |
| `PLAN.md` | What's New entry |
| `LINKS.md` | New web page URLs |
| `VERSION.md` | Version/subversion if evolution entry |
| `CLAUDE.md` | Publications table entry |
| `STORIES.md` | Success story if applicable |
| `publications/README.md` | Master index entry |
| EN/FR publication indexes | Add to both |

Commit essential files together.

### 6. Deliver (v50/v51)

Before pushing:
1. **Issue comment integrity check** (v51) — compare session exchanges vs posted comments, fill gaps
2. **Pre-save summary** (v50) — compile and display 5-section report (résumé, métriques, temps, livraisons, auto-évaluation)
3. **`AskUserQuestion`** — "Save now" / "Continue working" / "Save + close issue"

Then: push + PR + post closing report on issue (delivery status table + comment history index).

---

## Context Budget Rules (Documentation-Specific)

| Do | Don't |
|----|-------|
| Create all 4 web pages in one pass | Create EN, commit, then FR, commit separately |
| Read source once, adapt for each page | Re-read source for each web page |
| Batch essential files updates | Update NEWS.md, commit, PLAN.md, commit, separately |
| Use mind map from source across all tiers | Rewrite mind map differently per tier |

---

## Anti-Patterns

| Anti-pattern | Fix |
|-------------|-----|
| Creating EN pages but forgetting FR | Create all 4 in one pass |
| Skipping essential files after content creation | Universal inheritance checklist before final commit |
| Writing the publication without a methodology file | Methodology first — it has independent value |
| Updating summary but not complete page | Source drives both — sync from source |
| One giant commit with everything | Progressive commits: methodology → source → web pages → essential files |

---

## Real Example: This Session

Publication #19 (Interactive Work Sessions) followed this exact pattern:

1. **Gather**: User described session resilience patterns from experience
2. **Structure**: Created `methodology/interactive-work-sessions.md` (umbrella)
3. **Expand**: Created `publications/interactive-work-sessions/v1/README.md`
4. **Web pages**: Created 4 pages (EN/FR summary + complete)
5. **Essential files**: Updated NEWS, PLAN, LINKS, CLAUDE, STORIES, README, indexes
6. **Deliver**: Push + PR

---

## Relationship to Other Methodologies

| Methodology | Scope | Overlap |
|-------------|-------|---------|
| `interactive-work-sessions.md` | Parent — all interactive session types | This is one type within that framework |
| `documentation-generation.md` | Standards for all documentation | Applied during this session type |
| `interactive-diagnostic.md` | Debugging sessions | Different type, same resilience patterns |
| `interactive-conception.md` | Ideation and prototyping sessions | Different type, same resilience patterns |
| `session-protocol.md` | Session lifecycle (wakeup → task received → work → pre-save → save) | v51 session issue + v50 pre-save apply to all session types |
| `metrics-compilation.md` | Metrics format for pre-save summary | Applied at save time (v50) |
| `time-compilation.md` | Time format for pre-save summary | Applied at save time (v50) |

---

## Related

- Publication #19 — Interactive Work Sessions
- Publication #18 — Documentation Generation (standards applied here)
- Publication #20 — Session Metrics & Time Compilation
- `methodology/interactive-work-sessions.md` — Parent methodology
- `methodology/documentation-generation.md` — Documentation standards
- `methodology/session-protocol.md` — Session lifecycle (v50/v51)
