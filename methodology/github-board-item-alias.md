# GitHub Board Item Alias — `g:<board>:<item>[:<action>]`

> Discovered: knowledge-live (P3) session 2026-02-25
> Promoted to core: 2026-02-25

---

## Overview

The `g:` prefix is a **board item alias** — a positional shorthand for referencing and acting on GitHub Project board items from within Claude Code sessions. It extends the `#N:` project alias convention to the GitHub platform layer.

| Convention | Layer | Scope |
|------------|-------|-------|
| `#N:` | Knowledge | Publications and projects |
| `g:<board>:<item>` | GitHub | Board items (issues, drafts) |
| `TAG:` | GitHub | Issue title prefixes (typing) |

The three conventions are complementary:
- **`#N:`** routes knowledge to publications/projects
- **`TAG:`** types issues by knowledge origin (METHODOLOGY:, PATTERN:, etc.)
- **`g:`** addresses board items by position for quick reference and action

---

## Syntax

```
g:<board>:<item>              — reference a board item
g:<board>:<item>:<action>     — perform an action on a board item
```

| Part | Type | Meaning | Example |
|------|------|---------|---------|
| `g` | Prefix | GitHub board scope — distinguishes from `#N:` project scope | — |
| `<board>` | Integer | GitHub Project board number (from URL: `github.com/users/<owner>/projects/<N>`) | `10` |
| `<item>` | Integer | Item index — 1-based, creation order within the board | `1` |
| `:<action>` | Optional | Action suffix — triggers a state change or compilation | `done`, `info`, `progress` |

---

## Actions

| Action | Meaning | Effect |
|--------|---------|--------|
| *(none)* | Reference only | Show item title, status, type, labels |
| `:info` | Detailed view | Show item with description, linked issues, history |
| `:progress` | Move to In Progress | Update board item status to "In Progress" |
| `:done` | Mark as Done | Update board item status to "Done" + compile summary |
| `:todo` | Move to Todo | Update board item status to "Todo" (reset) |

### `:done` — Compilation Trigger

The `:done` action parallels `#N:done`. When a board item is marked done:

1. Item status moves to "Done" on the board
2. If the item has a linked repo issue, the issue is closed with a summary comment
3. A compilation of session work related to the item is generated
4. The compilation can feed into `doc review`, `pub sync`, or `harvest`

---

## Board-State Sync Protocol

The `g:` convention resolves item references against a local board-state cache. The index is positional (1-based, creation order) — it is only correct when the cache is current.

### Sync Rules

| Moment | Action | Why |
|--------|--------|-----|
| **Before reading `g:` refs** | Sync board state from GitHub | Ensure index positions are current |
| **After writing `g:` actions** | Re-sync board state | Reflect state changes in local cache |

### Cache Location

```
notes/board-state-<N>.json       — per-board state cache (session-scoped)
```

Example `notes/board-state-10.json`:
```json
{
  "board": 10,
  "synced": "2026-02-25T14:30:00Z",
  "items": [
    {"index": 1, "title": "DOC: Formalize page layout convention", "status": "Done", "type": "draft"},
    {"index": 2, "title": "TASK: Universal layout pagination", "status": "In Progress", "type": "draft"},
    {"index": 3, "title": "HARVEST: Sync roadmap pipeline", "status": "Todo", "type": "issue", "issue": 42}
  ]
}
```

### Sync Implementation

Sync uses `gh_helper.py` to pull board items:

```python
from scripts.gh_helper import GitHubHelper
gh = GitHubHelper()

# Fetch board items
items = gh.project_items_list("packetqc", board_number)

# Build indexed state
state = {
    "board": board_number,
    "synced": datetime.utcnow().isoformat() + "Z",
    "items": [
        {"index": i+1, "title": item["title"], "status": item["status"], "type": item.get("type", "draft")}
        for i, item in enumerate(items["items"])
    ]
}
```

---

## Examples

### Reference

```
g:10:1          → "DOC: Formalize page layout convention" (Done, draft)
g:10:2          → "TASK: Universal layout pagination" (In Progress, draft)
g:4:3           → Board #4, item 3 — resolves against board-state-4.json
```

### Actions

```
g:10:1:done     → Mark item 1 on board #10 as Done + compile summary
g:10:2:progress → Move item 2 on board #10 to In Progress
g:4:5:info      → Show detailed view of item 5 on board #4
g:10:3:todo     → Reset item 3 on board #10 to Todo
```

### In Conversation

```
User: g:10:1
Claude: Board #10, item 1: "DOC: Formalize page layout convention" — Status: Done (draft)

User: g:10:2:done
Claude: ✅ Board #10, item 2: "TASK: Universal layout pagination" moved to Done.
        Linked issue: none (draft item)
        Compilation: 3 session notes, 2 methodology insights captured.
```

---

## Relationship to `#N:` Convention

| Feature | `#N:` | `g:<board>:<item>` |
|---------|-------|-------------------|
| Scope | Knowledge (publications, projects) | GitHub (board items) |
| Routing | By publication/project number | By board number + item index |
| Categories | `methodology:`, `principle:` | Inherited from TAG: prefix |
| Compilation | `#N:done` | `g:B:I:done` |
| Info view | `#N:info` | `g:B:I:info` |
| Storage | Session notes → `minds/` → core | Board state (GitHub) + local cache |
| Convergence | Multi-satellite via harvest | Board is single source of truth |

The two conventions are complementary layers:
- `#N:` manages **knowledge** (what we know)
- `g:` manages **work** (what we're doing)

A board item can reference a publication (`g:10:1` might be about documentation for `#6`), and a scoped note can reference a board item (`#6: see g:10:1 for the layout task`).

---

## Design Rationale

- **2 characters** to invoke — `g:` at prompt start
- **Positional indexing** — same pattern as `#N:`, intuitive for users already using the knowledge system
- **Board-anchored** — the board number is explicit because items exist at the board level, not the repo level
- **Action suffix** — consistent with `#N:done` pattern, extensible
- **Sync-gated** — explicit sync requirement prevents stale references from causing incorrect actions
- **Cache is session-scoped** — `notes/board-state-<N>.json` lives in session notes, not in core knowledge

---

*Source: knowledge-live session 2026-02-25, branch claude/add-pagination-task-6rZ7p*
*GitHub issue: packetqc/knowledge#266*
