# Interactive Conception — Methodology

**Ideating, prototyping, and validating new capabilities, architectures, and features** through interactive collaboration between Martin and Claude. The conception session type within the [Interactive Work Sessions](interactive-work-sessions.md) framework.

---

## When to Use

- Designing a new system capability (command, protocol, architecture)
- Exploring an idea that doesn't have a clear implementation path yet
- Prototyping features that need user validation before formalization
- Architecture exploration and pattern discovery
- Creating new methodologies from observed patterns

**Not needed for**: Implementing well-defined features (→ feature development), fixing bugs (→ diagnostic), or writing documentation for existing capabilities (→ documentation).

---

## Core Principles

All principles from `interactive-work-sessions.md` apply, plus conception-specific additions:

| Principle | Description |
|-----------|-------------|
| **Ideas before structure** | Let the concept form before forcing it into a publication structure |
| **User validation gates** | Present proposals to the user before building — they see the rendered output, you see code |
| **Capture before formalize** | Raw notes (`#N:`, `remember`) preserve the idea even if the session crashes before formalization |
| **Progressive crystallization** | idea → notes → methodology → publication. Each stage is a commit. Skip stages only when the user directs |
| **Meta-awareness** | Conception sessions often discover patterns about the process itself. Capture these recursively |

---

## Phase Pattern

| Phase | Action | Persistence | Commit point |
|-------|--------|-------------|-------------|
| **Anchor** | Session issue protocol (v51) — create issue, post verbatim demand | GitHub issue | — (persistence step 0) |
| **Ideate** | User shares raw idea, Claude expands and structures | Notes / issue comment (🧑/🤖) | — (input phase) |
| **Explore** | Read existing code, methodology, publications for context | — (read-only) | — |
| **Propose** | Present structured proposal to user | Issue comment (🤖) | — (user validates) |
| **Prototype** | Create initial files (methodology, source, scripts) | Commit per artifact | ✓ After each artifact |
| **Validate** | User reviews, provides corrections | Issue comment (🧑) | — |
| **Iterate** | Apply corrections, refine | Commit with fix | ✓ After each correction |
| **Formalize** | If validated, promote to publication | Commit publication | ✓ After formalization |
| **Deliver** | Pre-save summary (v50) + essential files + push + PR | All three channels | ✓ Final push |

---

## Session Protocol

### 0. Anchor the Session (v51)

The session issue protocol (v51) applies — **before any file is touched**:

1. **Extract title** from the user's idea (e.g., "Conception — protocole de harvest distribué")
2. **Confirm via `AskUserQuestion`** — proposed title + "Skip tracking" option
3. **Create GitHub issue** — `SESSION: <title> (YYYY-MM-DD)`, labels: `SESSION`
4. **Post verbatim first comment** — the user's exact original request, unmodified

The issue becomes the living record of the conception session — ideas, proposals, corrections, and validation all captured as chronological 🧑/🤖 comments. This is the **third persistence channel** that survives crashes, compaction, and session end.

### 1. Receive and Expand

The user shares a raw idea — often in French, sometimes voice-to-text, always unstructured. Claude's role:

1. **Listen completely** — don't interrupt or structure prematurely
2. **Extract the core insight** — what is the user really proposing?
3. **Map to existing knowledge** — does this relate to existing publications, methodologies, patterns?
4. **Identify the gap** — what doesn't exist yet that this idea would fill?

### 2. Explore the Landscape

Before proposing, understand what exists:

- Read relevant methodology files
- Check if similar patterns are documented elsewhere
- Identify which publications would be affected
- Note any conflicts with existing approaches

### 3. Propose to the User

Present a structured proposal:

```
What I understand: [core insight in 1-2 sentences]
What exists: [related methodologies, publications]
What's new: [the gap this fills]
Proposed approach: [how to implement it]
```

**Wait for user validation.** The user may redirect, expand, or simplify. Follow their direction.

### 4. Prototype Incrementally

Create artifacts one at a time, committing each:

1. **Methodology file** (if applicable) — the operational reference
2. **Publication source** (if warranted) — the formal documentation
3. **Scripts or tools** (if the idea is a capability) — the implementation
4. **Web pages** — if publishing to GitHub Pages

Each artifact is independently valuable. If the session crashes, whatever was committed survives.

### 5. User Correction Integration

Conception sessions have the highest correction rate — the idea is forming in real-time:

1. **Stop** — don't finish the wrong structure
2. **Acknowledge** — "you're right, the approach should be X not Y"
3. **Adapt** — restructure immediately
4. **Commit the correction** — capture the right approach before context overflow

**Real example**: "we have done 3 today, so we should have 3 interactive-session-<type>" — the user's correction mid-session reshaped the entire approach from one umbrella file to separate per-type files. Following this immediately saved significant rework.

### 6. Progressive Crystallization

Ideas mature through stages:

```
raw thought → #N: scoped note → remember harvest: flag
    → methodology/ file → publication source → web pages → essential files
```

Not every idea reaches publication. Some stop at methodology. Some stay as notes. The user decides the maturation path.

---

## Context Budget Rules (Conception-Specific)

| Do | Don't |
|----|-------|
| Capture the user's raw idea verbatim first | Restructure the idea before understanding it |
| Propose before building | Build a full publication from assumption |
| Commit each prototype artifact independently | Accumulate everything for one big delivery |
| Follow user corrections immediately | Engineering around what the user said |

---

## Anti-Patterns

| Anti-pattern | Fix |
|-------------|-----|
| Premature formalization | Let the idea form before writing the publication |
| Ignoring user's simpler approach | Try the user's suggestion first (Pitfall #22) |
| Building the full stack before validation | Propose → validate → then build |
| Single-commit conception | Commit each artifact: methodology → source → pages → essential files |
| Losing meta-insights | When the process reveals a pattern, capture it (conception is recursive) |

---

## The Recursive Nature

Conception sessions often discover patterns about themselves:

- **This methodology** was created during a conception session that applied the very patterns it describes
- The user's correction ("we should have 3 interactive-session-<type>") became a documented pattern in the methodology it was correcting
- The meta-methodology (#18) was discovered because the documentation session revealed missing essential files — a conception insight during a documentation session

**Rule**: When a conception session discovers something about the process itself, capture it immediately. These meta-insights are the most valuable output — they improve all future sessions.

---

## Relationship to Other Methodologies

| Methodology | Scope | Overlap |
|-------------|-------|---------|
| `interactive-work-sessions.md` | Parent — all interactive session types | This is one type within that framework |
| `interactive-diagnostic.md` | Debugging and problem investigation | Different trigger, same resilience patterns |
| `interactive-documentation.md` | Creating publications and web pages | Often the next step after conception |
| `documentation-generation.md` | Standards for documentation output | Applied when conception reaches publication stage |
| `session-protocol.md` | Session lifecycle (wakeup → task received → work → pre-save → save) | v51 session issue + v50 pre-save apply to all session types |
| `metrics-compilation.md` | Metrics format for pre-save summary | Applied at save time (v50) |
| `time-compilation.md` | Time format for pre-save summary | Applied at save time (v50) |

---

## Related

- Publication #19 — Interactive Work Sessions
- Publication #20 — Session Metrics & Time Compilation
- `methodology/interactive-work-sessions.md` — Parent methodology
- `methodology/interactive-documentation.md` — Documentation sessions
- `methodology/interactive-diagnostic.md` — Diagnostic sessions
- `methodology/session-protocol.md` — Session lifecycle (v50/v51)
