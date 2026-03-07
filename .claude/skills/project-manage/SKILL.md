---
name: project-manage
description: Project management operations — list, info, register, review. Methodology-backed command skill covering all non-create project commands.
user_invocable: true
---

# /project-manage — Project Management Operations

## When This Skill Fires

Triggered when `parse_prompt()` detects commands:
- `project list` → list all projects
- `project info <P#>` → show project details
- `project register <name>` → register with P# ID
- `project review <P#>` → review project state
- `project review --all` → review all projects

## Sub-Task Integration

These commands execute as sub-tasks within the task workflow. The detected command determines which operation runs.

## Protocol

Full specification: `methodology/project-management.md`

### project list

List all projects with P# index, type (core/child/managed), status, satellite count.
Read `projects/*.md` metadata files.

### project info <P#>

Show full project details: identity, publications, satellites, evolution, stories.
Parse the P# from `detected_command.args`.

### project register <name>

1. Determine next P# index
2. Create `projects/<slug>.md` with metadata
3. Update CLAUDE.md project registry
4. Commit: `feat: register project P<N> — <name>`

### project review <P#>

Review: documentation completeness, publication status, required assets, freshness.
`--all` flag reviews every project in sequence.

## Notes

- All project data lives in `projects/*.md` — flat files only
- Three project types: core (P0), child (repo-backed), managed (in host repo)
- Hierarchical indexing: `P<n>/S<m>/D<k>`
