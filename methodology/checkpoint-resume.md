# Checkpoint/Resume — Crash Recovery for Interrupted Sessions

How to survive session crashes without losing multi-step protocol progress.

---

## The Problem

Claude Code sessions crash. API 400/500 errors, network failures, container restarts — they all kill the session abruptly. When this happens mid-protocol (during save, harvest, normalize, bootstrap deployment), all in-progress work and context is lost. The user starts a new session and manually re-explains what was happening.

Evidence from production sessions:
- `tool_use ids must be unique` API errors killing sessions mid-deployment
- Multiple 400 errors throughout a day — context loss as recurring battle
- Sessions dying before token extraction or PR creation
- Sessions questioning token protocol after losing context (NPC regression)

---

## The Solution: Auto-Checkpoint + Resume

```
[protocol start] → checkpoint → step 1 → checkpoint → step 2 → checkpoint → ...
                                                                    ↑ crash here
[new session] → wakeup → step 0.9 detect checkpoint → resume → step 2 continues → ... → done → delete checkpoint
```

Three components:
1. **Auto-checkpoint** — periodic JSON snapshots of in-flight activity state
2. **Resume detection** — wakeup step 0.9 scans for interrupted work
3. **`resume` command** — explicit recovery from last checkpoint

---

## Checkpoint File

**Location**: `notes/checkpoint.json`
**Lifecycle**: Created on protocol start → updated at each step boundary → deleted on successful completion
**Signal**: File exists = interrupted work. File absent = clean state.

### Schema (v1)

```json
{
  "version": 1,
  "session_id": "claude/implement-save-wxnpG",
  "created": "2026-02-21T14:30:00Z",
  "updated": "2026-02-21T14:35:22Z",
  "command": "harvest --healthcheck",
  "command_display": "Harvest healthcheck",
  "protocol_steps": [
    { "step": "Scan core", "status": "completed" },
    { "step": "Scan STM32N6570-DK_SQLITE", "status": "completed" },
    { "step": "Scan MPLIB", "status": "in_progress" },
    { "step": "Update dashboard", "status": "pending" },
    { "step": "Regenerate webcards", "status": "pending" },
    { "step": "Commit and push", "status": "pending" }
  ],
  "current_step_index": 2,
  "context": {
    "decisions": [
      "MPLIB satellite at v25, drift 3 from core v28",
      "STM32 harvested 2 new insights: cache sizing, printf latency"
    ],
    "key_data": {
      "satellites_scanned": ["STM32N6570-DK_SQLITE"],
      "satellites_remaining": ["MPLIB", "PQC"],
      "insights_found": 2
    }
  },
  "git_state": {
    "branch": "claude/implement-save-wxnpG",
    "uncommitted_files": [
      "minds/stm32n6570-dk-sqlite.md",
      "publications/distributed-knowledge-dashboard/v1/README.md"
    ],
    "last_commit": "abc1234"
  },
  "recovery_hint": "Resume by running: harvest --healthcheck (will skip already-scanned satellites)",
  "todo_state": [
    { "content": "Scan core", "status": "completed" },
    { "content": "Scan satellites", "status": "in_progress" },
    { "content": "Update dashboard", "status": "pending" },
    { "content": "Commit and push", "status": "pending" }
  ]
}
```

### Schema Fields

| Field | Type | Purpose |
|-------|------|---------|
| `version` | int | Schema version for forward compatibility |
| `session_id` | string | The `claude/<task-id>` branch name — identifies which branch has uncommitted work |
| `created` | ISO 8601 | When the checkpoint was first written |
| `updated` | ISO 8601 | When the checkpoint was last refreshed — the diff shows how long the operation ran |
| `command` | string | Exact command string that was running (e.g., `harvest --healthcheck`) |
| `command_display` | string | Human-readable name for reporting |
| `protocol_steps` | array | Ordered steps with statuses — resuming session skips completed, restarts from in_progress |
| `current_step_index` | int | Index into `protocol_steps` for quick lookup |
| `context.decisions` | array | Key decisions/findings — the "what did we learn so far" that would be lost |
| `context.key_data` | object | Command-specific state (satellites scanned, files created, etc.) |
| `git_state.branch` | string | Branch name — new session verifies it matches or warns |
| `git_state.uncommitted_files` | array | Files modified but not committed — new session checks they exist |
| `git_state.last_commit` | string | Short SHA — lets resuming session verify nothing was lost |
| `recovery_hint` | string | Human-readable instruction printed on wakeup |
| `todo_state` | array | Todo list snapshot — resuming session restores exact progress display |

---

## Checkpoint-Aware Commands

Checkpoints are written at **protocol boundaries** — not on a timer. This keeps them meaningful and lightweight.

| Command | Checkpoint points |
|---------|-------------------|
| `save` | Before pre-save summary (v50), before write notes, after commit, after push, after PR |
| `harvest <project>` | Before scan, after each branch scanned, after write to minds/ |
| `harvest --healthcheck` | Before scan, after each satellite, after dashboard update, after webcard regen |
| `harvest --fix <project>` | Before fix, after CLAUDE.md prepared, after commit |
| `normalize --fix` | Before scan, after each check category, after fixes applied |
| `pub new <slug>` | After each scaffold file created |
| `pub sync <#>` | After source comparison, after asset sync |
| `doc review <#> --apply` | Before review, after source update, after EN sync, after FR sync |
| `webcard --apply` | After each card generated, after commit |
| `wakeup` (bootstrap scaffold) | After each staging round |

### When NOT to Checkpoint

- Simple read-only commands (`status`, `help`, `weblinks`, `pub list`, `pub check`)
- Single-step operations that complete in seconds
- During `refresh` (it is itself a recovery command)

---

## Resume Protocol

### Automatic Detection (Wakeup Step 0.9)

After step 0.8 (re-read knowledge) and before step 1 (Knowledge Evolution check):

1. Check for `notes/checkpoint.json`
2. If exists, read and parse
3. Print structured resume prompt (command, progress, recovery hint)
4. `AskUserQuestion` with three choices:
   - **"Resume"** — runs `resume` command
   - **"Discard checkpoint"** — deletes file, continues normally
   - **"Skip (decide later)"** — leaves checkpoint, continues wakeup

### Manual Resume

Type `resume` at any point during a session. Same protocol as automatic detection.

### Git State Verification

| Scenario | Action |
|----------|--------|
| Same branch, uncommitted files match | Resume seamlessly |
| Same branch, some files missing | Warn, resume what remains |
| Different branch, checkpoint branch exists | Warn, offer to switch (user decision) |
| Different branch, checkpoint branch gone | Warn, offer to discard checkpoint |
| Checkpoint older than 24 hours | Warn about staleness, still offer resume |
| Checkpoint older than 7 days | Auto-delete with warning |

### Per-Command Resume Behavior

| Command | Resume behavior |
|---------|----------------|
| `save` | Skip completed steps (notes already written?), continue from failed step |
| `harvest --healthcheck` | Skip already-scanned satellites (using cursors in key_data), continue from interrupted satellite |
| `normalize --fix` | Skip already-checked categories, continue from interrupted category |
| `wakeup` (bootstrap) | Check which staging rounds completed via key_data, continue from next round |
| `pub new <slug>` | Check which scaffold files already exist, create remaining |
| `harvest --fix` | Check if CLAUDE.md was already updated, continue from commit step |

---

## RTOS Analogy

Sessions are threads. Notes are shared memory. Save is thread cleanup.
**Checkpoint is the watchdog timer** — it captures state at known-good
boundaries so that if the thread dies unexpectedly, the supervisor
(next wakeup) can restart from the last saved state rather than from zero.

The `notes/checkpoint.json` file is the equivalent of a watchdog recovery
register in embedded systems — it holds just enough state to restart the
operation without replaying the entire history.

---

## Edge Cases

### Cross-Branch Resume

When a session crashes, the checkpoint file is on the task branch's working tree. If the container recycles, the working tree may be gone — but if the checkpoint was committed (during a progressive commit), it survives on the branch. The new session fetches the branch and finds the checkpoint.

### Container Recycling

If the container is recycled between sessions:
- **Committed checkpoint** → survives (on the branch, fetched on wakeup)
- **Uncommitted checkpoint** → lost (working tree gone)

Mitigation: commit the checkpoint file during progressive commits (e.g., after each major step in multi-round protocols).

### Concurrent Sessions

Two sessions in the same repo could both write to `notes/checkpoint.json`. The `session_id` field identifies which session wrote it. On resume, verify the session_id. If two checkpoints conflict, the newer one wins (by `updated` timestamp).

### Stale Checkpoints

- **< 24 hours**: Normal — offer resume
- **24h–7d**: Stale warning — still offer resume, but warn about potential git divergence
- **> 7 days**: Auto-delete with warning

---

## Security

**Checkpoint safety rule**: Never include ephemeral tokens, PAT values, or authentication credentials in checkpoint data. The `context` and `key_data` fields capture protocol state only, never secrets. This is enforced by design — the checkpoint write function must actively exclude token references.

The token safety rules (CLAUDE.md) apply to checkpoints:
- No `github_pat_*` values in any field
- No API keys, passwords, or credentials
- If `save` captures session state, actively exclude token references

---

## Integration with Existing Recovery

| Recovery | Trigger | Recovers | Speed |
|----------|---------|----------|-------|
| `resume` | Session crash (checkpoint exists) | Protocol progress, decisions, git state | ~10s |
| `recover` | Session crash (no checkpoint, but work on dead branch) | Committed code + notes from stranded `claude/*` branches | ~15s |
| `recall` | Need to find past session work/decisions | Deep memory search across issues, notes, caches, commits, methodology | ~5-30s |
| `refresh` | Context compaction (session alive) | CLAUDE.md formatting, command definitions | ~5s |
| `wakeup` | Session start or deep re-sync needed | Full knowledge, upstream, beacon | ~30-60s |
| New session | Nuclear — nothing else works | Everything (fresh start) | ~60s |

**Recovery spectrum**: `resume` catches the crash at protocol level (checkpoint). `recover` catches it at git level (branches). `recall` searches across all memory channels for past work and decisions. `refresh` catches compaction at context level. Together they cover every failure mode.

Key distinction: `resume` handles **crashes** (session dies, checkpoint exists). `recover` handles **crashes** (session dies, no checkpoint but committed work exists on branches). `recall` handles **remembering** (search across issues, notes, caches, commits, methodology for past decisions and work). `refresh` handles **compaction** (session lives but shrinks). They are complementary, not alternatives.

---

## Related

- Publication #8 — Session Management
- `methodology/session-protocol.md` — Session lifecycle (v50/v51)
- `methodology/interactive-work-sessions.md` — Resilience patterns
- `methodology/client-disconnect-recovery.md` — Client disconnect handling

## Version History

| Version | Date | Change |
|---------|------|--------|
| v29 | 2026-02-21 | Initial implementation — checkpoint/resume protocol |
| v50 | 2026-02-27 | Added pre-save summary as checkpoint-aware step in `save` |
| v51 | 2026-02-27 | Added `recall` to recovery table (git branch-based recovery) |
| v57 | 2026-03-04 | Split `recall` into `recover` (branch recovery) + `recall` (deep memory search) |
