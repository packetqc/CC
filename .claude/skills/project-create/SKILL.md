---
name: project-create
description: Creates a new project with P# registration, GitHub Project board (elevated), and web presence. Methodology-backed command skill.
user_invocable: true
---

# /project-create — Project Creation Protocol

## When This Skill Fires

Triggered when `parse_prompt()` detects `detected_command.skill == "/project-create"`.
The command `project create <name>` is a **sub-task** within the task workflow — the task workflow orchestrates it.

## Prerequisites

- Session must be elevated (GH_TOKEN available) for full board creation
- Task workflow must be in implement stage (command runs as a sub-task)

## Protocol

Full specification: `methodology/project-create.md`

### Step 1: Parse Arguments

Extract project name from `detected_command.args`:
```
project create Studio 54  →  args = "Studio 54"
```

### Step 2: Register Project

1. Determine next P# index (scan `projects/*.md`)
2. Create `projects/<slug>.md` with project metadata
3. Update project registry in CLAUDE.md

### Step 3: Create GitHub Project Board (Elevated)

```python
import sys; sys.path.insert(0, '.')
from scripts.gh_helper import GitHubHelper

gh = GitHubHelper()
# Create board, link repo, set up columns
```

### Step 4: Create Web Presence

1. Create docs pages (EN + FR) under `/projects/<slug>/`
2. Generate webcard if applicable
3. Update project index

### Step 5: Commit & Deliver

Progressive commits per step, following the `/work-cycle` protocol.

## Sub-Task Integration

This skill executes within the task workflow's implement stage. The parent task tracks:
- Issue: the session issue
- Todo: "Execute project create <name>"
- Commit: conventional commit `feat: create project P<N> — <name>`

## Notes

- Import GitHubHelper with NO constructor args (Pitfall #23)
- Semi-auto mode: guide user through manual board creation
- The project name comes from the user's prompt, confirmed via AskUserQuestion
