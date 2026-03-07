---
name: tagged-input
description: Scoped notes and board item references — #N:content for project knowledge, g:board:item for GitHub board operations.
user_invocable: true
---

# /tagged-input — Scoped Notes & Board References

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `#N: <content>` — scoped note for project/publication N
- `#N:methodology:<topic>` — methodology insight (flagged for harvesting)
- `#N:principle:<topic>` — design principle (flagged for harvesting)
- `#N:info` — show accumulated knowledge for N
- `#N:done` — end focus, compile summary
- `g:<board>:<item>` — reference board item by position
- `g:<board>:<item>:done` — mark board item as Done
- `g:<board>:<item>:progress` — move to In Progress
- `g:<board>:<item>:info` — detailed board item view

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/tagged-input.md`, `methodology/github-board-item-alias.md`

### # Call Alias

Routes content to project N. Claude classifies internally:
- Raw knowledge → session notes
- `methodology:` → flagged for doc harvesting
- `principle:` → flagged for doc harvesting
- `info` → display accumulated knowledge
- `done` → compile and summarize

### g: Board Item Alias

Resolves against `notes/board-state-<N>.json`:
- `g:1:3` → board 1, item at position 3
- `g:1:3:done` → mark that item Done via GraphQL
- `g:1:3:progress` → move to In Progress
- `g:1:3:info` → show item details

## Notes

- Implicit main project: no prefix needed for repo's main project
- Board state cached locally, refreshed on first use per session
