---
name: normalize
description: Knowledge structure concordance — audit and fix EN/FR mirrors, front matter, webcards, links, assets, and essential files.
user_invocable: true
---

# /normalize — Knowledge Structure Concordance

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `normalize` — full audit with optional fixes
- `normalize --fix` — apply fixes automatically
- `normalize --check` — report only, no changes

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: Publication #6

### Concordance Checks (9 Categories)

| # | Category | What It Checks |
|---|----------|---------------|
| 1 | **Structure** | EN/FR mirrors, hub↔subpage links |
| 2 | **Layout** | Front matter, OG tags, version banner, table styling, print/export, language bar |
| 3 | **Webcards** | 1200×630 animated GIF per page, dual-theme |
| 4 | **Links** | Cross-references consistent |
| 5 | **Assets** | Social preview, OG GIFs, publication assets synced |
| 6 | **Mindset** | CLAUDE.md up to date |
| 7 | **Branch** | Default branch detection |
| 8 | **Essential files** | README.md, PLAN.md, LINKS.md, NEWS.md, CHANGELOG.md, VERSION.md |
| 9 | **Projects folder** | Flat `.md` files only |

### Modes

- **Audit** (`normalize`): Report all issues, suggest fixes
- **Fix** (`normalize --fix`): Apply fixes automatically (elevated for PR)
- **Check** (`normalize --check`): Report only, exit with status code

### Checkpoint-Aware

Checkpoints at each category boundary for crash recovery.

## Notes

- Severity icons: 🟢 pass, 🟡 minor, 🟠 moderate, 🔴 critical, ⚪ not applicable
- `--fix` creates a commit per category, then PR to merge
