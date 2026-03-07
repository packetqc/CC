# Client Disconnect Recovery — Resiliency Pattern

How to recover when the client interface disconnects mid-session, after work has been pushed but before PR creation completes.

---

## The Problem

Claude Code sessions run in a client-server architecture. The agent (server-side) executes code, commits, and pushes — but the client interface (browser tab, desktop app, VS Code) can disconnect independently. When the client disconnects mid-protocol, the server-side work may have completed (commits pushed to remote) but the final steps (PR creation, merge) are interrupted.

This is distinct from a full session crash (API 400/500, container restart) — in a client disconnect, the git state on the remote is intact, only the control flow was interrupted.

Evidence from production:
- Branch `claude/extract-image-text-0vJA3` on `packetqc/knowledge` — agent pushed commits successfully, client disconnected before PR creation (2026-02-24)

---

## Architecture Principle

```
Session work → git push (durable) → PR creation (ephemeral)
                  ↑                        ↑
              survives disconnect     may need re-execution
```

The **git push is the durability boundary**. Everything committed and pushed to the remote branch persists regardless of client state. PR creation is an idempotent API call that can always be re-executed without side effects.

---

## Recovery Paths

Four paths, ordered from fastest to slowest:

### Path A — Browser Refresh / Session Resume (Preferred)

1. **Refresh the browser tab** — the underlying session may still be alive server-side
2. If reconnected, the agent resumes with full context intact
3. Claude Code web sessions persist state across reconnects — the agent continues from where it left off
4. The `resume` command reads `notes/checkpoint.json` and restores state even if the agent process restarted

**When to use**: Immediately after disconnect. Always try this first.

### Path B — Manual PR Creation (Immediate)

When the client cannot reconnect:

1. Verify the branch exists on remote and has the expected commits:
   ```bash
   git fetch origin
   git log origin/<branch> --oneline -5
   ```
2. Detect the default branch:
   ```bash
   DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
   ```
3. Create the PR via one of:
   - **gh_helper.py** (if token available):
     ```bash
     python3 scripts/gh_helper.py pr create \
       --repo packetqc/<repo> \
       --head <branch> \
       --base "$DEFAULT" \
       --title "Session work — client disconnected before PR" \
       --body "Session disconnected before PR creation. Branch work is complete."
     ```
   - **GitHub web UI**: `https://github.com/packetqc/<repo>/compare/<default>...<branch>`

**When to use**: When Path A fails (session is dead, browser refresh doesn't reconnect).

### Path C — New Session + Resume

1. Start a new Claude Code session on the same repo
2. Run `resume` — reads checkpoint, restores context
3. The new session detects the orphan branch and can create the PR
4. No work is lost — git is the source of truth, not the session

**When to use**: When both A and B fail, or when you want the AI to handle PR creation.

### Path D — Wait for Harvest (Slowest — NOT recommended)

- Core's periodic `harvest --healthcheck` scans satellite branches
- Eventually discovers the orphan branch and its contents
- Latency: hours to days — should NOT be relied on for timely delivery

**When to use**: Never proactively. This is the passive fallback for work that slips through all other recovery paths.

---

## Resiliency Guarantees

| Layer | Survives Disconnect? | Recovery Method |
|-------|---------------------|-----------------|
| Local file edits (uncommitted) | No | Lost — must redo |
| Local commits (not pushed) | No | Lost — must redo |
| Pushed commits | **Yes** | Branch exists on remote |
| PR creation | Maybe | Re-execute via Path A, B, or C |
| Session notes (committed+pushed) | **Yes** | On remote branch |
| Session notes (uncommitted) | No | Lost — must redo |
| Checkpoint state (committed) | **Yes** | Detected by next `resume` |
| Checkpoint state (uncommitted) | No | Lost — use Path B instead |

---

## Relationship to Other Recovery Mechanisms

| Recovery | Trigger | What it handles | Speed |
|----------|---------|-----------------|-------|
| **Client disconnect recovery** (this doc) | Client UI disconnects | Pushed work missing PR | Instant (Path A) to minutes (Path B) |
| `resume` | Session crash (checkpoint exists) | Protocol progress, decisions, git state | ~10s |
| `recover` | Session crash (no checkpoint, commits exist) | Stranded branch work | ~15s |
| `recall` | Need to find past session work/decisions | Deep memory search across all channels | ~5-30s |
| `refresh` | Context compaction (session alive) | CLAUDE.md formatting, command definitions | ~5s |
| `wakeup` | Session start or deep re-sync | Full knowledge, upstream sync | ~30-60s |

Key distinction: Client disconnect recovery handles the case where **git work is safe but protocol completion was interrupted**. This is lighter than `resume` (which handles full session crashes) and different from `recover` (which handles orphan branches with no checkpoint). Use `recall` when you need to find past decisions or work across all knowledge channels.

---

## Recommendations

1. **Push early and often** — the save protocol's commit-push-PR sequence means even if PR creation fails, work is safe on the remote branch
2. **Use `checkpoint` before long-running operations** — persists state for cross-session recovery
3. **Recovery priority**: Path A (refresh) → Path B (manual PR) → Path C (new session + resume) → Path D (harvest, last resort)
4. **PR creation is idempotent** — re-running `gh_helper.py pr create` for a branch that already has a PR returns the existing PR URL, not a duplicate

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-02-24 | Initial — observed on `claude/extract-image-text-0vJA3`, documented in knowledge-live, promoted to core |
