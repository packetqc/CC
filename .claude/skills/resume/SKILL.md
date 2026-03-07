---
name: resume
description: Session recovery — resume from checkpoint, recover stranded branch work, show checkpoint state. Crash recovery and resiliency.
user_invocable: true
---

# /resume — Session Recovery

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `resume` — resume interrupted session from checkpoint
- `recover` — search stranded branches for work recovery
- `checkpoint` — show current checkpoint state

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/checkpoint-resume.md`

### resume

1. Read `notes/checkpoint.json`
2. Verify git state matches checkpoint
3. Restore todo list from checkpoint
4. Restart protocol from last completed step
5. Auto-delete checkpoint on success

### recover

1. Search `claude/*` and `backup-*` branches
2. Show unmerged commits and file diffs
3. Show PR status for each branch
4. Offer: cherry-pick or diff-apply recovery

### checkpoint

Show current checkpoint state, or "no active checkpoint" if none.

### Checkpoint-Aware Commands

These commands create checkpoints at step boundaries:
`save`, `harvest`, `harvest --healthcheck`, `harvest --fix`, `normalize --fix`, `pub new`, `wakeup`

## Notes

- `recover` complements `resume` (checkpoint-based) with branch-based recovery
- Backup branches are user-created snapshots for resiliency
- Offered automatically at wakeup step 0.9
