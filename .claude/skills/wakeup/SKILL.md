---
name: wakeup
description: Session initialization and context restore — wakeup (deep sync) and refresh (lightweight restore). Boot sequence skills.
user_invocable: true
---

# /wakeup — Session Init & Context Restore

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `wakeup` — deep re-sync (mid-session only; auto-wakeup handles session start)
- `refresh` — lightweight context restore (~5s)

## Sub-Task Integration

These are **infrastructure commands** — they modify the session state but still run within the task workflow for tracking purposes.

## Protocol

Full specification: `methodology/session-protocol.md`, `methodology/satellite-bootstrap.md`

### wakeup (Mid-Session Deep Sync)

Steps 0–11 of the boot sequence:
0. **Sunglasses** — read CLAUDE.md
0.1. **Subconscious** — read 6 mandatory methodology files
0.15. **Elevate** — detect GH_TOKEN
0.35. **Integrity check** — verify startup, unlock Gate 1
0.5. **Bootstrap scaffold** (satellites) — create missing files
0.7. **Sync upstream** — `git fetch origin <default> && git merge`
0.9. **Resume detection** — check `notes/checkpoint.json`
1-8. **Context load** — evolution, minds/, notes/, assets, git log
9. **Print help + ready**

### refresh (Lightweight Restore)

Re-read CLAUDE.md → re-read 6 methodology files → `read_runtime_cache()` → strategic remote check → git status → re-read session notes → reprint help.

No clone, no sync. ~5 seconds. Use after compaction.

## Notes

- `wakeup` auto-runs on session start — never type as entry prompt
- Mid-session: use `wakeup` only when deep re-sync needed (other sessions merged)
- `refresh` is the fast path — use after compaction recovery
- Deduplication: if entry message IS `wakeup`/`refresh`, auto-wakeup covers it
