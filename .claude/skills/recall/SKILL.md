---
name: recall
description: Deep memory search across all knowledge channels — session caches, git history, GitHub issues, publications, methodology.
user_invocable: true
---

# /recall — Deep Memory Search

## When This Skill Fires

Triggered when `parse_prompt()` detects `recall <keyword or question>`.

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

### Search Layers (Progressive)

| Layer | Time | Source |
|-------|------|--------|
| 1. **Near memory** | ~5s | Current cache, recent `notes/session-runtime-*.json`, recent `notes/session-*.md` |
| 2. **Git memory** | ~10s | Commit messages, branch names, file diffs across `claude/*` and `backup-*` branches |
| 3. **GitHub memory** | ~15s | Issue titles/comments, PR descriptions, board items (requires elevation) |
| 4. **Deep memory** | ~30s | Full-text across publications, methodology, patterns, lessons, minds/ |

### Flow

1. Search near memory first (fast)
2. If not found, AskUserQuestion: "Search deeper?"
3. Progress through layers until answer found or all exhausted
4. If stranded branch work found → suggest `recover`

### API

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import recall, format_recall_report

results = recall(query="keyword or question")
report = format_recall_report(results)
```

## Notes

- `recall` finds, `recover` acts
- Near memory is always searched without confirmation
- Deep memory requires user confirmation (AskUserQuestion)
- Stops as soon as answer is found — no unnecessary deep search
