# GitHub Project Integration — Methodology

> Promoted from knowledge-live (P3) harvest — insights #5, #6, #7, #8, #9, #10, #11
> Source: Publication #1 (knowledge-live), sessions 2026-02-23-b, 2026-02-24

## Core Principle

GitHub Projects are a **live, browsable index** of the knowledge structure. The knowledge system replicates its internal taxonomy into GitHub using issues with labels and TAG: title prefixes. Harvest reads them back. Neither system replaces the other:

- **GitHub** = collaboration layer (human decisions, reviews, tracking)
- **Knowledge** = intelligence layer (methodology, patterns, documentation)

## TAG: Convention

Every issue title is prefixed with a `TAG:` that identifies the knowledge structure type. Combined with matching GitHub labels, this creates a visual taxonomy on the board.

| TAG: prefix | Knowledge origin | GitHub label | Label color |
|-------------|-----------------|--------------|-------------|
| `SESSION:` | Session issue protocol (v51) — every work session | `SESSION` | `#1d4ed8` (blue) |
| `METHODOLOGY:` | `#N:methodology:<topic>` | `methodology` | `#0075ca` (blue) |
| `PATTERN:` | `patterns/` | `pattern` | `#2da44e` (green) |
| `LESSON:` | `lessons/` | `lesson` | `#e11d48` (red) |
| `EVOLUTION:` | CLAUDE.md evolution table | `evolution` | `#7c3aed` (purple) |
| `STORY:` | `#N:story:<title>` | `story` | `#0d9488` (teal) |
| `TASK:` | `#N:task:<title>` | `task` | `#6b7280` (gray) |
| `BUG:` | `#N:bug:<title>` | `bug` | `#ea580c` (orange) |
| `PUB:` | `publications/` | `publication` | `#ca8a04` (gold) |
| `HARVEST:` | `minds/` harvest flags | `harvest` | `#06b6d4` (cyan) |

### Label Deployment

Labels are deployed to repositories via `gh_helper.py`:

```bash
# Single repo
python3 scripts/gh_helper.py labels setup --repo packetqc/<repo>

# Batch deployment across multiple repos
python3 scripts/gh_helper.py labels setup-all --repos packetqc/repo1,packetqc/repo2
```

## Entity Convention

Scoped notes and session events map to GitHub issues with TAG: prefixes:

| Input | GitHub issue title | Label |
|-------|-------------------|-------|
| Session task received (v51) | `SESSION: <title> (YYYY-MM-DD)` | `SESSION` |
| `#N:story:<title>` | `STORY: <title>` | `story` |
| `#N:task:<title>` | `TASK: <title>` | `task` |
| `#N:bug:<title>` | `BUG: <title>` | `bug` |
| `#N:methodology:<topic>` | `METHODOLOGY: <topic>` | `methodology` |
| `#N:principle:<topic>` | `PATTERN: <topic>` | `pattern` |

### SESSION Issues (v51)

The `SESSION:` tag is unique — it is created automatically by the session issue protocol (v51) rather than via `#N:` scoped notes. Every work session creates a `SESSION:` issue **before the first file is touched**:

1. Title extracted from user's request + confirmed via `AskUserQuestion`
2. Issue created with `SESSION` label + relevant topic labels
3. First comment is the user's verbatim request (frozen, never modified)
4. During work: chronological 🧑/🤖 comments posted in real-time
5. At save: pre-save summary (v50) posted as final 🤖 comment
6. On close: closing report with delivery status table + comment history index

SESSION issues form the **third persistence channel** — they survive crashes, compaction, and session end independently of git and notes. See `methodology/session-protocol.md` for the full protocol.

## Board Item Alias — `g:<board>:<item>[:<action>]`

The `g:` prefix provides a positional shorthand for referencing and acting on board items from within Claude Code sessions. It extends the `#N:` project alias to the GitHub platform layer.

```
g:10:1          — reference board #10, item 1
g:10:2:done     — mark item 2 as Done (compilation trigger)
g:10:3:progress — move item 3 to In Progress
g:10:1:info     — detailed view of item 1
```

| Action | Effect |
|--------|--------|
| *(none)* | Show item title, status, type |
| `:info` | Detailed view with description, linked issues |
| `:progress` | Move to In Progress |
| `:done` | Move to Done + compile summary + close linked issue |
| `:todo` | Reset to Todo |

**Sync rule**: `g:` refs resolve against `notes/board-state-<N>.json`. Sync before reading; re-sync after writing.

**Full specification**: `methodology/github-board-item-alias.md`

---

## Bidirectional Flow

### Knowledge → GitHub (outbound)

```
#15:methodology:auth           →  Issue: "METHODOLOGY: auth"      (label: methodology)
#15:story:build-item-commands  →  Issue: "STORY: build item cmds" (label: story)
#15:bug:token-leak             →  Issue: "BUG: token leak"        (label: bug)
remember harvest: <insight>    →  Issue: "HARVEST: <insight>"     (label: harvest)
save (creates PR)              →  PR auto-linked to Project board
```

### GitHub → Knowledge (inbound — via harvest)

```
Issue "METHODOLOGY: auth"      →  methodology/ or minds/<project>.md
Issue "PATTERN: caching"       →  patterns/ (after promotion)
Issue "LESSON: race condition" →  lessons/ (after promotion)
Issue "STORY: add auth"        →  notes/ + publication content
PR comments                    →  methodology insights
Closed issue + merged PR       →  doc review trigger
```

## Three Touch Points

| Touch point | Layer | API | Knowledge role |
|-------------|-------|-----|---------------|
| **Board issues** | Planning | `addProjectV2DraftIssue` | Claude creates draft items for planning, methodology notes |
| **Repo issues** | Tracking | `addProjectV2Item` | Human creates issues; harvest reads them back |
| **Repo PRs** | Delivery | Auto-linked on `save` | Session work as reviewable PRs; harvest reads comments |

## gh_helper.py Commands for Project Integration

| Command | Type | Description |
|---------|------|-------------|
| `labels setup --repo` | REST | Creates all 9 TAG: labels (idempotent) |
| `labels setup-all --repos` | REST | Batch setup across multiple repos |
| `issue create --repo --title --labels` | REST | Creates repo issue with TAG: prefix + label |
| `project item-add --project-id --title` | GraphQL | Adds draft items to board |
| `project get-id --owner --number` | GraphQL | Retrieves board node ID |
| `project item-update --item-id --status` | GraphQL | Updates board item status field |
| `project fields --project-id` | GraphQL | Lists board fields and option values |
| `project items-list --owner --number` | GraphQL | Paginated board reader with TAG: parsing |
| `project sync --owner --number` | GraphQL + local | Bidirectional reconciliation |

## Dynamic Roadmap Pipeline

```
GitHub Project board (source of truth)
    → sync_roadmap.py (pulls items via GraphQL)
    → docs/_data/roadmap.json (Jekyll data file)
    → Liquid templates render live roadmap page
    → GitHub Actions automates the sync cycle
```

Script: `scripts/sync_roadmap.py` — deploys to satellites alongside `gh_helper.py`.

## Proven in Practice

Autonomous proof from knowledge-live (P3), 2026-02-23:
- 9 TAG: labels created across 5 repos
- 19 board items populated (16 Done, 1 In Progress, 1 Todo)
- 1 repo issue (#30) linked to board
- Publication #1 created (6 pages, three-tier bilingual)
- 13 PRs merged autonomously
- Board reader + bidirectional sync operational
- Zero manual GitHub UI intervention required

## Related

- `methodology/session-protocol.md` — Session lifecycle (v50/v51 — SESSION issue protocol)
- `methodology/interactive-work-sessions.md` — Three-channel persistence model
- `methodology/tagged-input.md` — `#N:` scoped note convention
- `methodology/github-board-item-alias.md` — `g:<board>:<item>` convention

---

*Promoted to core: 2026-02-24*
*Source: knowledge-live Publication #1, sessions 2026-02-23-b + 2026-02-24*
*Updated: 2026-02-27 — SESSION label added (v51)*
