---
name: profile-update
description: Refresh all 8 profile files with current stats — versions, publications, issues, stories.
user_invocable: true
---

# /profile-update — Profile Refresh

## When This Skill Fires

Triggered when `parse_prompt()` detects `profile update`.

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/profile-update.md`

### Profile Files (8 total)

| File | Language | Format |
|------|----------|--------|
| `profile/README.md` | EN | Source |
| `profile/README.fr.md` | FR | Source |
| `docs/profile/index.md` | EN | Web (summary) |
| `docs/fr/profile/index.md` | FR | Web (summary) |
| `docs/profile/resume/index.md` | EN | Web (resume) |
| `docs/fr/profile/resume/index.md` | FR | Web (resume) |
| `docs/profile/full/index.md` | EN | Web (full) |
| `docs/fr/profile/full/index.md` | FR | Web (full) |

### Update Flow

1. Read current stats: knowledge version, publication count, project count, issue count
2. Update all 8 files with current values
3. Maintain EN/FR concordance
4. Commit: `docs: refresh profile with current stats`

## Notes

- All 8 files must stay synchronized
- Version numbers, counts, and dates are the primary update targets
- Never change biographical content without explicit user request
