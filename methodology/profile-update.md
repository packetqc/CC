# Profile Update — Periodic Resume Refresh

## Purpose

Keep profile pages (hub, resume, full) current as the Knowledge project evolves. Profile files contain dynamic data (publication counts, knowledge versions, issue counts, success stories) that drift as the system grows.

## Files Managed

| File | Type | Language |
|------|------|----------|
| `profile/README.md` | Source | EN |
| `profile/README.fr.md` | Source | FR |
| `docs/profile/index.md` | Web hub | EN |
| `docs/fr/profile/index.md` | Web hub | FR |
| `docs/profile/resume/index.md` | Web resume | EN |
| `docs/fr/profile/resume/index.md` | Web resume | FR |
| `docs/profile/full/index.md` | Web full | EN |
| `docs/fr/profile/full/index.md` | Web full | FR |

## Section Order (all pages)

The standard section order for profile pages:

**Hub**: Contact → Resume link → Full Profile link → **Top 5** → **Recommendation** → Publications

**Resume**: Contact → Profile → Current Focus → Technical Domains → **Top 5** → **Recommendation** → Publications → Full Profile link

**Full**: Contact → Education → Current Focus → Earlier Projects → Technical Domains → Profile → **Top 5** → **Recommendation** → Publications

## Dynamic Fields

Fields that should be refreshed on update:

| Field | Source | Example |
|-------|--------|---------|
| Knowledge versions | `VERSION.md` | "55 knowledge versions" |
| Publication count | Count in `publications/` | "23+ publications" |
| Issue count | GitHub API via `gh_helper.py` | "550+ tracked issues" |
| Success stories | Count in Publication #11 | "13 success stories" |
| Active hours | Session metrics aggregate | "46 hours" |
| Enterprise comparison | Derived from hours | "8–16 months" |

## When to Update

| Trigger | Priority | Reason |
|---------|----------|--------|
| `profile update` command (on-demand) | User-initiated | Explicit refresh request |
| Project completion (in `save` protocol) | Suggested | Natural checkpoint after delivering work |
| New publication created | Suggested | Publication count and list changed |
| Major knowledge version milestone | Suggested | Version number in descriptions outdated |
| Quarterly review | Recommended | Catch accumulated drift |

**Not on every save** — profile updates are meaningful at milestones, not on every commit.

## Command: `profile update`

**Action**: Review all 8 profile files, refresh dynamic fields with current values, ensure EN/FR concordance, commit changes.

**Steps**:
1. Read `VERSION.md` for current knowledge version
2. Count publications in `publications/` directory
3. Query issue count via `gh_helper.py` (if elevated)
4. Update all 8 files with current values
5. Verify EN/FR concordance (same numbers in both languages)
6. Commit and include in current session's delivery

## Integration with Save Protocol

When a session completes a significant project milestone (new publication, major feature), the pre-save summary (v50) can suggest a profile update. This is a suggestion, not a gate — the user decides.

## Concordance Rules

- All 8 files must show the same counts (publications, versions, issues, stories)
- EN/FR mirrors must have identical structure and section order
- Top 5 content must be identical across all pages (same 5 items)
- Recommendation link text must reference current statistics
