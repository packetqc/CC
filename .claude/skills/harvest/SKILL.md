---
name: harvest
description: Distributed knowledge harvesting — pull satellite insights, promote to core, healthcheck network. All harvest sub-commands in one skill.
user_invocable: true
---

# /harvest — Distributed Knowledge Harvesting

## When This Skill Fires

Triggered when `parse_prompt()` detects any harvest command:
- `harvest <project>` — pull knowledge from satellite
- `harvest --list` — list harvested projects
- `harvest --healthcheck` — full network sweep
- `harvest --fix <project>` — update satellite CLAUDE.md
- `harvest --review <N>` — mark insight reviewed
- `harvest --stage <N> <type>` — stage for integration
- `harvest --promote <N>` — promote to core
- `harvest --auto <N>` — queue auto-promote
- `harvest --procedure` — guided promotion walkthrough

## Sub-Task Integration

Harvest commands execute as sub-tasks within the task workflow. The specific sub-command is in `detected_command.args`.

## Protocol

Full specification: `methodology/production-development-minds.md`, Publication #7

### Core Flow

1. Enumerate satellite branches via `git ls-remote`
2. Check cursors for incremental scan
3. Scan new content since last harvest
4. Version check (satellite vs core knowledge version)
5. Extract insights into `minds/<project>/`
6. Update all 5 dashboard files (source → EN docs → FR docs)
7. Regenerate webcards
8. Cleanup `/tmp/`

### Healthcheck (`--healthcheck`)

Full network sweep:
1. Scan core first
2. Crawl each satellite (incremental)
3. Update FR dashboard
4. Update severity icons (🟢🟡🟠🔴⚪)
5. Process auto-promote queue
6. Regenerate webcards
7. Commit + PR

### Promotion Pipeline

```
🔍 review → 📦 stage → ✅ promote → 🔄 auto
```

### Elevation

- **Elevated**: autonomous — commit → push → PR → merge
- **Semi-auto**: guide user through PR merge

## Notes

- All satellite access via public HTTPS: `https://github.com/packetqc/<project>`
- `harvest --fix` updates satellite's `<!-- knowledge-version: vN -->` tag
- Checkpoint-aware: checkpoints at step boundaries for crash recovery
