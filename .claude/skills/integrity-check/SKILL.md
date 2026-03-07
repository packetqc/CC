---
name: integrity
description: Run the integrity check state machine — show protocol compliance grid and handle rerun/skip for gaps
user_invocable: true
---

# /integrity — Protocol Compliance Check

When the user invokes `/integrity`, execute the following:

## Step 1: Ensure integrity is initialized

```python
from scripts.session_agent import integrity_check, integrity_grid, format_integrity_report, init_integrity

# Check if integrity exists in cache
grid = integrity_grid()
if "error" in grid and "not initialized" in grid["error"]:
    init_integrity()
```

## Step 2: Run the check and display the report

```python
report = format_integrity_report()
```

Display the formatted report to the user. The report shows all 29 checkpoints organized by section (Startup, Task, Work, Completion) with status icons.

## Step 3: Handle gaps

Run `integrity_check()` to get the first gap:

```python
result = integrity_check()
```

If `result["status"] == "all_passed"`:
- Display: "All checkpoints passed."

If `result["status"] == "incomplete"`:
- The gap is at `result["first_gap"]` (e.g., `T.1`)
- The action to fix it is in `result["action"]`
- Whether it blocks progress is in `result["blocking"]`

If the gap is **blocking**, present an `AskUserQuestion` with 3 options:
1. **"Rerun from {checkpoint}"** — Execute the action described in `result["action"]`
2. **"Skip this checkpoint"** — Call `skip_checkpoint(result["first_gap"], reason)` where reason comes from user
3. **"Continue without fixing"** — Only for non-blocking gaps

If the user chooses "Rerun", execute the action and then call `pass_checkpoint(result["first_gap"])` on success, or `fail_checkpoint(result["first_gap"], error)` on failure.

## Step 4: Re-check after action

After any rerun or skip, run `integrity_check()` again to see if there are more gaps. Repeat Step 3 until all blocking checkpoints are resolved or skipped.

## Notes

- The integrity grid persists in `session_data.integrity` in the runtime cache
- Work cycle checkpoints (W.1-W.7) reset on each new todo via `reset_work_cycle()`
- Import all functions from `scripts.session_agent` (not directly from `integrity.py`)
- Never auto-skip a checkpoint — only `skipped_by_user` via AskUserQuestion is valid
