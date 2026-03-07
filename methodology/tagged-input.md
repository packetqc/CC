# Project Knowledge — `#` Call Alias Convention

The `#` prefix at the beginning of a prompt is a **call alias** — it triggers scoped knowledge input mode. Claude routes, classifies, and stores the content. The user feeds raw intelligence; Claude organizes it.

---

## The Call Alias

When a prompt starts with `#`, it's an invocation — not just a prefix. It signals: "this is project knowledge, route it."

| Prompt | Meaning |
|--------|---------|
| `#N: content` | Explicitly scoped to publication/project N |
| `#0: raw content` | Raw dump — Claude classifies using acquired + universal knowledge |
| No `#`, in a repo | Implicit main project of that repo (see below) |

**`#` is the trigger**. Everything after it is either a routing key (`#N:`) or raw content for the implicit main project.

---

## Implicit Main Project

Every repo has a **main project** — the primary subject of documentation work in that context.

| Repo | Main project | `#` equivalent |
|------|-------------|----------------|
| `packetqc/knowledge` | #0 Knowledge System | `#0:` |
| `packetqc/STM32N6570-DK_SQLITE` | #1 MPLIB Storage Pipeline | `#1:` |
| `packetqc/knowledge-live` | Documentation hub (multi-project) | Context-dependent |

**Rule**: When the user feeds information without a `#N:` prefix while working in a repo, Claude assumes it's for the repo's main project. The user doesn't need to say `#0:` every time in the knowledge core — the context is obvious.

**When `#N:` IS needed**: When the content is for a *different* project than the repo's main. In the knowledge core, `#7: branch-crawling needs retry logic` explicitly routes to Harvest Protocol, not to #0.

---

## Raw Dump Mode — `#0:`

The lowest-friction entry point. The user says whatever they have to say right now, without overthinking structure. Claude figures it out.

```
#0: i tell you whatever i have to output right now without too much thinking
    and you will figure out with that
```

Claude uses:
- **Acquired knowledge** — the full CLAUDE.md, publications, methodology, patterns, lessons
- **Universal knowledge** — Claude's own training, domain expertise, reasoning

To classify the content (spec, architecture, methodology, principle, idea, etc.), route it to the right storage, and acknowledge. The user's job is to provide the intelligence. Claude's job is to organize it.

**This applies to any `#N:`** — not just `#0:`. Any scoped raw dump gets the same treatment. `#7: the fix command should prepare locally not push cross-repo` — Claude classifies this as a principle for Harvest Protocol without the user needing to say `#7:principle:`.

---

## Commands

| Command | Action |
|---------|--------|
| `#N: <content>` | Scoped note for publication/project #N |
| `#N:methodology:<topic> <content>` | Methodology insight — flagged for doc harvesting |
| `#N:principle:<topic> <content>` | Design principle — flagged for doc harvesting |
| `#N:info` | Show all accumulated knowledge for #N |
| `#N:info:<topic>` | Show specific topic within #N |
| `#N:done` | End documentation focus, compile summary |

---

## Publication Numbers

| # | Publication |
|---|-------------|
| `#0` | Knowledge System |
| `#1` | MPLIB Storage Pipeline |
| `#2` | Live Session Analysis |
| `#3` | AI Session Persistence |
| `#4` | Distributed Minds |
| `#4a` | Knowledge Dashboard |
| `#5` | Webcards & Social Sharing |
| `#6` | Normalize |
| `#7` | Harvest Protocol |
| `#8` | Session Management |
| `#10` | Live Knowledge Network |

---

## Harvest Categories

Two special categories for when the user *knows* the content is documentation-grade:

| Category | Purpose | Example |
|----------|---------|---------|
| `methodology:` | How we work — process, workflow, protocol | `#7:methodology:incremental-cursors only scan commits after cursor` |
| `principle:` | Why we do it — design decisions, rules | `#4:principle:pull-based satellites read core, never push-based delivery` |

These are flagged for documentation harvesting. They surface during `harvest`, `doc review`, and `#N:info`.

General `#N:` notes (without a category) are still stored and compiled — Claude classifies them internally. The explicit categories are optional precision, not a requirement.

---

## Multi-Satellite Convergence

**The same project can be documented from multiple satellites.** An insight about `#7` (Harvest Protocol) can be discovered while working in:

- `packetqc/knowledge` (core) — direct `#7:` input
- `packetqc/STM32N6570-DK_SQLITE` — while debugging, a harvest pattern emerges
- `packetqc/MPLIB` — while working on modules, a methodology insight surfaces
- `packetqc/knowledge-live` — while documenting, a principle crystallizes

**`#N:` is the routing key, not the repo.** The insight goes where it belongs regardless of where it was discovered.

**Promotion is the convergence flow:**

```
Satellite A ──→ harvest ──→ minds/ ──→ promotion ──→ core knowledge
Satellite B ──→ harvest ──↗
Satellite C ──→ harvest ──↗
Core direct ──────────────────────────→ notes/ ──→ core knowledge
```

All `#N:` scoped notes from all satellites flow through harvest into `minds/`, then through promotion into the central consciousness (`patterns/`, `lessons/`, `methodology/`, publications). The distributed network converges into unified project knowledge.

**Practical flow:**
1. User works in satellite, discovers insight: `#7: fix command should prepare locally, satellite self-heals on wakeup`
2. `save` persists the note on the satellite's task branch
3. `harvest STM32N6570-DK_SQLITE` pulls the `#7:` note into `minds/`
4. `harvest --promote N` delivers it to core `patterns/` or the #7 publication source
5. Next `doc review #7` sees the new content and flags the publication for update

The user starts the same project documentation in multiple places. Promotion converges it all.

---

## Subconscious Detection

During normal conversation, Claude monitors for content that naturally relates to a publication's domain. When an insight clearly belongs to a specific publication, Claude suggests capture:

> *This looks relevant to #7 (Harvest Protocol). Capture it? (`#7:methodology:incremental-cursors` to confirm)*

**Rules:**
- Only suggest when the match is obvious — not on every message
- One suggestion at a time — never stack multiple
- User can ignore — no follow-up if not acted on
- Show the exact `#N:` command — user confirms by typing it or ignores

---

## `#N:info`

Shows all accumulated notes for a publication, organized by category:

```
=== #7 Harvest Protocol — Accumulated Knowledge ===

  Methodology (3 notes)
  - incremental-cursors: only scan commits after cursor
  - branch-crawling: enumerate all remote branches via ls-remote
  - cleanup: rm -rf temporary clones after extraction

  Principles (1 note)
  - pull-based: satellites self-heal by reading core

  General (2 notes)
  - dashboard should update all 5 files on every harvest
  - healthcheck should report unreachable satellites

  Sources: knowledge (2), STM32N6570-DK_SQLITE (3), MPLIB (1)
  3 sessions, 6 notes total
```

`#N:info:<topic>` filters to a specific topic (e.g., `#7:info:branch-crawling`).

---

## `#N:done`

Signals end of documentation focus. Claude compiles all accumulated `#N:` notes into a structured summary. The compilation can feed into:

- `doc review #N` — for checking if the publication needs updates
- `pub sync #N` — for propagating changes to web pages
- Direct editing — user takes the compiled summary and updates the source

---

## GitHub Board Item Extension — `g:<board>:<item>[:<action>]`

The `#N:` convention manages **knowledge** (publications, projects). The `g:` convention extends the same positional indexing pattern to manage **work** on GitHub Project boards.

| Convention | Layer | Scope |
|------------|-------|-------|
| `#N:` | Knowledge | Publications and projects |
| `g:<board>:<item>` | GitHub | Board items (issues, drafts) |

```
g:10:1          — reference board #10, item 1
g:10:2:done     — mark item 2 on board #10 as Done (compilation trigger)
g:10:3:progress — move item 3 to In Progress
g:10:1:info     — detailed view of item 1
```

The two conventions are complementary: `#N:` routes knowledge, `g:` addresses work items. A board item can reference a publication (`g:10:1` relates to `#6`), and a scoped note can reference a board item (`#6: see g:10:1 for the task`).

**Sync requirement**: `g:` refs resolve against `notes/board-state-<N>.json`. Sync board state before reading refs; re-sync after writing actions.

**Full specification**: `methodology/github-board-item-alias.md`

---

## Integration with Existing Commands

| Command | Relationship |
|---------|--------------|
| `remember ...` | Unchanged — general session notes, no scoping |
| `remember harvest: ...` | Unchanged — flags for harvest collection |
| `#N: ...` | Scoped to a publication — stored and compilable |
| `save` | Persists all notes including `#N:` scoped ones |
| `harvest` | Reads `#N:methodology:` and `#N:principle:` flags from all satellites |
| `doc review` | Uses accumulated `#N:` notes (all sources) to assess freshness |

---

## Design Rationale

The `#` call alias was chosen because:

- **1 character** to invoke — `#` at prompt start triggers the convention
- **3 characters** to scope a note — `#N:` routes to publication N
- **0 characters for main project** — implicit context from the repo
- **Raw dump mode** — `#0:` means "you figure it out," lowest friction possible
- **Location-independent routing** — `#N:` works in any repo, insight goes where it belongs
- **Multi-satellite convergence** — same project documented everywhere, promotion unifies
- **2 optional categories** instead of a tag taxonomy — Claude classifies the rest
- **Subconscious detection** replaces explicit tagging — Claude finds patterns the user misses
