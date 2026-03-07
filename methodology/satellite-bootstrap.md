# Satellite Bootstrap — Installing Knowledge in a New Project

How to onboard a satellite project into the knowledge network. **Single-session iterative staging** — one session does everything, user merges between rounds, no restarts.

---

## The Protocol

```
One session. Multiple rounds. One manual step per round: merge the PR.

  Round 1: wakeup → bootstrap scaffold → commit → push → PR
           ⏸ user merges → refresh → verify stage 1 ✓

  Round 2: normalize → trim to thin-wrapper → commit → push → PR
           ⏸ user merges → refresh → verify stage 2 ✓

  Round 3: project create (optional) → commit → push → PR
           ⏸ user merges → refresh → verify stage 3 ✓

  Final:   "Installation complete. Any new session will auto-wakeup."
```

**Why single-session**: Each Claude Code session gets one assigned `claude/<task-id>` branch. Starting a new session means a new branch, a new context load, and wasted time. The iterative staging protocol keeps the same session alive — it creates changes, pushes, waits for the user to merge, syncs `main` back, and continues to the next round.

---

## Console Guidance — Assisted Staging (The Human Bridge)

The session actively guides the user through every manual step. Never go silent between rounds — always print what the user needs to do next and what happens after.

**Why this is critical**: Claude knows the full protocol — proxy limitations, PR flow, merge requirements, branch scoping. The human doesn't carry this mental model at all times. If the session doesn't explicitly print "now create a PR and merge it", the human has no way to know that a manual step is required. The console output IS the bridge between the system's internal knowledge and the human's next action. Without it, work gets stranded on task branches and the user doesn't know why.

**Rule**: Every time the protocol reaches a point where the user must act, print a clear `⏸` block with: what just happened, what the user needs to do, and what will happen after they do it. This applies to `save`, bootstrap staging, `harvest --fix`, and any command that produces a PR.

### After commit + push (PR creation)

If `gh_helper.py` succeeds (elevated — has token):
```
=== Stage N — PR Created ===

  PR: https://github.com/packetqc/<repo>/pull/<N>
  Branch: claude/<task-id> → <default-branch>

  [ELEVATED] Auto-merging PR...
  ✓ PR merged. Syncing default branch back...
```

If elevated, auto-merge via `gh_helper.py pr merge` — no pause, no waiting.

If no token (semi-automatic):
```
=== Stage N — Push Complete ===

  Branch: claude/<task-id> (pushed)
  Create PR manually:

  https://github.com/packetqc/<repo>/pull/new/claude/<task-id>

  ⏸ Create the PR and merge it to continue staging.
  Say "merged" when done — I'll sync and verify Stage N.
```

### After user says "merged"

```
🔄 Syncing default branch...
```

Then run the merge sync, verify, and print the stage result:

```
=== Stage N Verified ✓ ===

  <checklist results>

  Proceeding to Stage N+1...
```

### Between rounds

Never leave the user wondering what's next. After each verification, immediately start the next round or print the final confirmation.

### On final round

```
=== Installation Complete ===

  <final summary>

  No more manual steps needed from this session.
  Any new session on this repo will auto-wakeup with v45.
```

### Error handling

If the user says "merged" but the merge sync shows the PR wasn't merged:
```
⚠ Default branch doesn't show the expected changes yet.
  Check: Is the PR merged? (not just approved)
  PR URL: <url>

  Say "merged" again when confirmed, or "skip" to proceed anyway.
```

---

**The merge sync**: After the user merges a PR, the session runs:
```bash
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
git fetch origin "$DEFAULT" && git merge "origin/$DEFAULT" --no-edit
```
This pulls the merged content back into the task branch. The session now sees the confirmed state of `main` — not just its own changes, but the merged result. Then it verifies.

---

## Autonomous Change Detection

After each wakeup step that creates or modifies files (step 0.5 scaffold, step 5 asset sync), run `git status -s`. If any untracked or modified files are detected, **automatically** enter the staging flow — commit, push, create PR, print the `⏸` block. Do not wait for the user to type `save`.

```bash
# After scaffold/asset creation
CHANGES=$(git status -s)
if [ -n "$CHANGES" ]; then
  # Enter staging flow: commit → push → PR → ⏸ block
  git add -A
  git commit -m "Bootstrap knowledge v45"
  git push -u origin claude/<task-branch>
  # ... create PR, print ⏸ guidance
fi
```

This ensures every file the wakeup produces gets delivered to the default branch — no changes silently stranded on the working tree.

---

## Self-Heal — Automatic CLAUDE.md Update on Drift

**Wakeup step 0.55** — after bootstrap scaffold (0.5), before beacon (0.6).

When a satellite's CLAUDE.md is behind core, the commands section is **automatically updated** during wakeup. No manual `harvest --fix` from core needed. The satellite self-heals.

### How it works

1. Compare `<!-- knowledge-version: vN -->` in satellite vs `<!-- template-version: vN -->` in `/tmp/knowledge/methodology/satellite-commands.md`
2. If satellite version < core version:
   - Extract content between `<!-- BEGIN COMMANDS -->` and `<!-- END COMMANDS -->` markers from `satellite-commands.md`
   - Replace satellite's `## Commands (from Knowledge)` section (up to next `---`) with extracted content
   - Update the version tag
   - Report drift and what changed
3. Changes flow through autonomous change detection: commit → push → PR → user merges

### What gets updated

| Updated | Not touched |
|---------|------------|
| `<!-- knowledge-version: vN -->` tag | `## Knowledge Base` section |
| `## Commands (from Knowledge)` section | `## Session Protocol` section |
| | `## Project Overview` section |
| | `## Quick Commands — Project-Specific` section |

The satellite's identity and customizations are preserved. Only the commands reference (which comes from core) is refreshed.

### The canonical source

`methodology/satellite-commands.md` is the single source of truth for the commands section. When core adds new commands:

1. Update `satellite-commands.md` (the canonical template)
2. Update `satellite-bootstrap.md` (the embedded template — for new scaffolds)
3. Existing satellites auto-update on their next wakeup via step 0.55

### Edge cases

| Scenario | Behavior |
|----------|----------|
| No `## Commands (from Knowledge)` header | Skip self-heal, report warning |
| Satellite ahead of core (version > core) | Skip — satellite may have local additions |
| No knowledge clone available | Skip — core not accessible |
| First bootstrap (fresh repo) | Step 0.5 creates CLAUDE.md with current commands; step 0.55 skips (no drift) |

---

## Round 1 — Bootstrap

The session's auto-wakeup creates the initial scaffold. **Autonomous change detection** triggers the staging flow automatically.

### What wakeup step 0.5 creates (if missing)

| File | Content |
|------|---------|
| `CLAUDE.md` | Knowledge pointer with `<!-- knowledge-version: vN -->` |
| `README.md` | Repo name, description, link to knowledge |
| `LICENSE` | MIT with current year |
| `.gitignore` | Standard ignores (`.env`, `*.pem`, `node_modules/`, `__pycache__/`, `.mp4`) |
| `notes/.gitkeep` | Session persistence folder |
| `PLAN.md` | Project roadmap (What's New + Ongoing sections) |
| `LINKS.md` | Essential URLs and web page inventory |
| `NEWS.md` | Changelog with dated entries |
| `VERSION.md` | Knowledge version tracking (`vN\|subversion\|suffix`) |

### The critical-subset CLAUDE.md

~180 lines. Knowledge pointer + essential behavioral DNA + full 7-group commands reference + project-specific content.

**Why critical-subset, not thin-wrapper**: In the core repo, CLAUDE.md is loaded as **system-level project instructions** — high authority, compaction-resilient, full behavioral fidelity. In satellites, the thin-wrapper CLAUDE.md (~30 lines) told Claude to "read knowledge," but that read landed in **conversation context** — lower authority, lost on first compaction. The critical-subset includes enough operational DNA (session protocol, save protocol, branch protocol, command reference) to drive correct behavior even after compaction, while still pointing to core for the deep stuff (harvest details, publication management, webcards, PQC, patterns, pitfalls).

```markdown
# CLAUDE.md — <Project Name>

## Knowledge Base
<!-- knowledge-version: v48 -->
On wakeup, ALWAYS read the knowledge CLAUDE.md first. Try in order:
1. git clone https://github.com/packetqc/knowledge /tmp/knowledge && read /tmp/knowledge/CLAUDE.md (FULL read — use limit: 3500, the file is 3000+ lines)
2. WebFetch https://raw.githubusercontent.com/packetqc/knowledge/main/CLAUDE.md (if 404, try /master/)
Never use gh. This gives you the sunglasses — without it, you're a stateless NPC.
**Plan mode**: If session starts in plan mode (Bash/Edit/Write blocked), use WebFetch (method 2) for Step 0. Skip write steps (bootstrap, self-heal, asset sync). Run deferred write steps after plan approval.

---

## Session Protocol

### Auto-Wakeup

Runs automatically on every session start — regardless of user's entry prompt. Print:
``⏳ Wakeup starting... (type "skip" to cancel)``
If user responds "skip" or "no", cancel. Otherwise proceed with full wakeup.

### Plan Mode Awareness (v48)

**Plan mode blocks**: Bash, Edit, Write, NotebookEdit. **Plan mode allows**: Read, Grep, Glob, WebFetch, WebSearch, TodoWrite, Task, AskUserQuestion.

When session starts in plan mode, auto-wakeup MUST adapt — the standard wakeup uses Bash (git clone) and Write (bootstrap) which are blocked. Without adaptation, the satellite gets NO sunglasses and behaves like an NPC.

**Plan mode wakeup protocol** (read-only — uses only allowed tools):

0. **Sunglasses via WebFetch** — Use WebFetch (allowed in plan mode) instead of git clone (Bash, blocked):
   ``WebFetch https://raw.githubusercontent.com/packetqc/knowledge/main/CLAUDE.md`` (if 404, try /master/)
   This gives the satellite core knowledge even in plan mode.
0.9. **Resume detection** — Read `notes/checkpoint.json` via Read tool (allowed).
1-8. **Read local state** — Read notes/, CLAUDE.md, git state via Read/Grep/Glob (all allowed).
9. **Print help** — Output help table (text output always allowed).

**Skipped in plan mode** (require blocked tools):
- Step 0.3: Elevation (Bash for env var check)
- Step 0.5: Bootstrap scaffold (Write for file creation)
- Step 0.55: Self-heal CLAUDE.md (Edit for commands update)
- Step 0.6: Beacon (Bash to start process)
- Step 0.7: Sync upstream (Bash for git fetch/merge)
- Step 5: Asset sync (Bash for file copy)

**After plan approval** — when the user exits plan mode and execution begins, the session now has Bash/Edit/Write tools available. Run the skipped write steps:
``🔧 Plan approved — running deferred wakeup steps (bootstrap, self-heal, asset sync)...``
Execute steps 0.5, 0.55, 0.7 that were skipped. This ensures the satellite is fully bootstrapped before any planned edits start.

**Detection**: Plan mode is detectable by attempting a Bash call — if it's rejected with a plan mode message, switch to read-only wakeup. Alternatively, if the system prompt contains plan mode instructions, adapt immediately.

### Session Lifecycle

``[auto-wakeup] → read knowledge → read notes/ → summarize → work → save → commit & push → PR``

### Wakeup Steps

0. Read packetqc/knowledge (sunglasses — non-negotiable). In plan mode: WebFetch instead of git clone.
0.5. Bootstrap scaffold (create missing files — non-destructive). Skipped in plan mode.
0.6. Start knowledge beacon (background). Skipped in plan mode.
0.7. Sync upstream (fetch + merge default branch). Skipped in plan mode.
0.9. Resume detection (check notes/checkpoint.json)
1-8. Read evolution, minds, notes, git state
9. Run refresh (re-read CLAUDE.md, reprint help)
11. Address user's entry message

### Save Protocol

Claude Code cannot push to the default branch — proxy restricts to the assigned task branch only.

``1. Write session notes → notes/session-YYYY-MM-DD.md``
``2. Commit on current branch (assigned claude/* task branch)``
``3. git push -u origin <assigned-task-branch>``
``4. Detect default branch: git remote show origin | grep 'HEAD branch'``
``5. Create PR via gh_helper.py: task-branch → default-branch``
``6. [ELEVATED] Merge PR via gh_helper.py → sync back → continue``
``   [SEMI-AUTO] User approves PR → merge lands on default branch``

**API method**: `gh` CLI is NOT installed. `curl` is blocked by proxy. Use `python3 scripts/gh_helper.py` (Python urllib) for ALL PR operations. Needs `GH_TOKEN` env var.
If PR creation fails, skip gracefully — report branch + manual PR URL.
Todo list for save MUST include all steps: write notes, commit, push, create PR, merge (elevated) or manual URL (semi-auto).

### Branch Protocol

| Branch | Role | Who writes |
|--------|------|------------|
| Default (`main`/`master`) | Convergence point | PR merges (user-approved) |
| `claude/<task-id>` | Task branch (per session) | Claude Code (proxy-authorized) |

- Push access: assigned task branch ONLY (403 on anything else)
- PR: task branch → default branch (user approves)
- Detect default: `git remote show origin | grep 'HEAD branch'`
- Never assume `main` or `master` — always detect dynamically

### Human Bridge

Every time the protocol needs user action, print a clear ⏸ block:

```
⏸ Pause — action required

  What just happened: <summary>
  What you need to do: <action>
  What happens next: <next>
```

UX priority: (1) AskUserQuestion popup for decisions, (2) isolated code block for commands/URLs, (3) fenced ⏸ block for context.

### Notification Format

All user-facing notifications wrapped in fenced code blocks. Session language applies inside.

### Language Awareness

Detect system locale + app language. Lock session language. No casual switching — explicit request only.
Command names stay English always. Output descriptions adapt to session language.

### Context Loss Recovery

After compaction: run `refresh` (re-read CLAUDE.md, git status, reprint help — ~5s).
After crash: `resume` (from notes/checkpoint.json — ~10s).
After PRs merged by others: `wakeup` (full re-sync — ~30-60s).

---

## Commands (from Knowledge)

Full command details and implementation come from core on wakeup (Step 0).
The `help` command outputs these 7 groups with publication links.

### Critical Behavioral Rules

- **`gh_helper.py` is the ONLY working API method** — `gh` CLI is NOT installed in Claude Code containers. `curl` to `api.github.com` is blocked by the proxy (strips auth headers, returns 401). Only Python `urllib` (used by `scripts/gh_helper.py`) bypasses the proxy. For ALL GitHub API operations (PR create, merge, branch ops): use `gh_helper.py` with `GH_TOKEN` env var.
- **Plan mode wakeup** — When session starts in plan mode (Bash/Edit/Write blocked), auto-wakeup MUST still run using read-only tools: WebFetch for Step 0 (sunglasses), Read for notes/CLAUDE.md, text output for help. Skip write steps (bootstrap, self-heal, asset sync). Run deferred write steps after plan approval. Without this adaptation, the satellite gets no sunglasses and behaves like an NPC.
- **Interactive Input Convention** — Commands requiring multiple parameters (like `project create`) MUST gather ALL inputs upfront via a single `AskUserQuestion` popup BEFORE any execution. Gather first, execute second. If the user provided a parameter on the command line (e.g., `project create "My Project"`), pre-fill it and skip that question.
- **3 project types** — `core`, `child`, `managed`. Every project links to a repo. Child → own repo. Managed → host repo (or core repo as fallback). No project exists without a repo link.
- **Auto-elevate** — Commands needing a token (`project create`, `harvest --fix`, etc.) check elevation state first. If not elevated, auto-trigger the elevation popup. User never needs to type `elevate` separately.
- **Auto-save** — Commands that produce files include delivery (commit → push → PR → merge/report) as their final step. User never needs to type `save` after a command that changed files.

**Session** — [#8 Session Management](https://packetqc.github.io/knowledge/publications/session-management/)

| Command | Action |
|---------|--------|
| `wakeup` | Session init — knowledge, evolution, notes, assets, commands |
| `refresh` | Mid-session context restore — re-read CLAUDE.md, git status, reprint help |
| `help` / `aide` / `?` | Print this command table |
| `status` | Summarize current project state |
| `save` | Save context, commit, push, create PR |
| `remember ...` | Append to session notes |
| `resume` | Resume interrupted session from checkpoint |
| `recover` | Search past branches for stranded work, cherry-pick/apply to current |
| `recall` | Deep memory search across all knowledge channels |
| `checkpoint` | Show current checkpoint state |
| `elevate` | Provide classic GitHub PAT for full autonomous mode (gh_helper.py) |
| `<cmd> ?` | Contextual help for any session command |

**Normalize** — [#6 Normalize & Structure Concordance](https://packetqc.github.io/knowledge/publications/normalize-structure-concordance/)

| Command | Action |
|---------|--------|
| `normalize` | Audit and fix knowledge structure concordance |
| `normalize --fix` | Apply fixes automatically |
| `normalize --check` | Report only, no changes |

**Harvest** — [#7 Harvest Protocol](https://packetqc.github.io/knowledge/publications/harvest-protocol/)

| Command | Action |
|---------|--------|
| `harvest <project>` | Pull distributed knowledge into minds/ |
| `harvest --list` | List all harvested projects with version + drift |
| `harvest --procedure` | Guided promotion walkthrough |
| `harvest --healthcheck` | Full network sweep, update dashboard, process auto-promotes |
| `harvest --review <N>` | Mark insight as reviewed (human validated) |
| `harvest --stage <N> <type>` | Stage for integration (lesson, pattern, methodology, docs) |
| `harvest --promote <N>` | Promote insight to core knowledge now |
| `harvest --auto <N>` | Queue for auto-promote on next healthcheck |
| `harvest --fix <project>` | Update satellite CLAUDE.md to latest version |
| `harvest <cmd> ?` | Contextual help for any harvest subcommand |

**Publications** — [#5 Webcards & Social Sharing](https://packetqc.github.io/knowledge/publications/webcards-social-sharing/)

| Command | Action |
|---------|--------|
| `pub list` | Publication inventory with status |
| `pub check <#>` | Validate one publication (source, docs, webcard, links) |
| `pub check --all` | Validate all publications |
| `pub new <slug>` | Scaffold new publication |
| `pub sync <#>` | Compare source vs docs, report differences |
| `doc review --list` | Quick freshness inventory per publication |
| `doc review <#>` | Review publication freshness against current knowledge |
| `doc review --all` | Review all publications for stale content |
| `docs check <path>` | Validate doc page (front matter, links, mirror, OG) |
| `docs check --all` | Validate all doc pages |
| `webcard <target>` | Generate OG GIFs (card, group, or pub number) |
| `weblinks` | Print all GitHub Pages URLs (webcards, pubs, docs, hubs) |
| `weblinks --admin` | Same with conformity status per link |
| `pub export <#> --pdf` | Export publication to PDF |
| `pub export <#> --docx` | Export publication to DOCX |

**Project Management** — [#0 Knowledge System](https://packetqc.github.io/knowledge/publications/knowledge-system/)

| Command | Action |
|---------|--------|
| `project list` | List all projects with P# index, type, status |
| `project info <P#>` | Show project details — identity, pubs, satellites, evolution |
| `project create <name>` | Full creation: register P# + scaffold + GitHub Project (elevated) |
| `project register <name>` | Register project with P# ID in core |
| `project review <P#>` | Review project state — docs, pubs, assets, freshness |
| `project review --all` | Review all projects |
| `#N: <content>` | Scoped note — `#` call alias routes to project N |
| `#N:methodology:<topic>` | Methodology insight — flagged for harvesting |
| `#N:principle:<topic>` | Design principle — flagged for harvesting |
| `#N:info` | Show accumulated knowledge for #N |
| `#N:done` | End documentation focus, compile summary |
| `<cmd> ?` | Contextual help for any project command |

**Live Session** — [#2 Live Session Analysis](https://packetqc.github.io/knowledge/publications/live-session-analysis/)

| Command | Action |
|---------|--------|
| `I'm live` | Pull latest clip, report UI state |
| `multi-live` | Monitor multiple streams |
| `deep <desc>` | Frame-by-frame anomaly analysis |
| `analyze <path>` | Static video analysis |
| `recipe` | Print capture quick recipe |

**Live Network** — [#10 Live Knowledge Network](https://packetqc.github.io/knowledge/publications/live-knowledge-network/)

| Command | Action |
|---------|--------|
| `beacon` | Knowledge beacon status and peer discovery |

---

## Project Overview

<1-2 sentence description>

### Hardware / Stack
- <key technology 1>
- <key technology 2>

### Architecture Decisions
1. <decision with brief rationale>

---

## Quick Commands — Project-Specific

| Command | Action |
|---------|--------|
| <project command> | <what it does> |

Knowledge commands come from core on wakeup.
```

### What NOT to add

These live in core and are inherited on `wakeup`. The critical-subset includes behavioral summaries (session protocol, save, branch, commands), but the **full implementations** stay in core:

| Do NOT duplicate | Why |
|------------------|-----|
| Harvest protocol details (branch crawling, incremental tracking, promotion workflow) | Core CLAUDE.md |
| Publication management (pub new, pub sync, pub check implementation) | Core CLAUDE.md |
| Webcard generation (themes, animations, specs) | Core CLAUDE.md |
| Normalize implementation (7 concordance checks) | Core CLAUDE.md |
| PQC envelope / ephemeral token protocol | Core CLAUDE.md |
| Proven Patterns (RTOS, SQLite, embedded debugging) | Core patterns/ |
| Known Pitfalls (MPU faults, WAL, stack overflow) | Core lessons/ |
| Knowledge Evolution table | Core-only history |
| Repo Access Protocol (full proxy boundary details) | Core CLAUDE.md |

**Rule**: The critical-subset carries enough DNA to drive correct behavior (auto-wakeup, save, branch protocol, commands, notifications). The deep implementation details come from core on wakeup. If it's a behavioral rule that affects every session, it's in the satellite. If it's a detailed implementation, it stays in core.

### Over-sync is expected

The first bootstrap often installs more than needed — the Claude instance reads core and mirrors detailed content. This is normal. Round 2 trims it to the critical-subset template.

### Deliver Round 1

```bash
git add CLAUDE.md README.md LICENSE .gitignore notes/
git commit -m "Bootstrap knowledge v45"
git push -u origin claude/<task-branch>
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
# Create PR via gh_helper.py (never use gh CLI — not installed)
python3 scripts/gh_helper.py pr create --repo packetqc/<repo> --head claude/<task-branch> --base "$DEFAULT" --title "Bootstrap knowledge v46" --body "Bootstrap scaffold" || \
  echo "Create PR manually: https://github.com/packetqc/<repo>/pull/new/claude/<task-branch>"
```

**Console output** — use the guided staging format (see Console Guidance above):
```
=== Stage 1 — Bootstrap ===

  PR: <url> (or manual creation URL)
  Files: CLAUDE.md, README.md, LICENSE, .gitignore, notes/

  ⏸ Please merge the PR to install Stage 1.
  Say "merged" when done — I'll sync and verify.
```

### Sync after merge

```bash
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
git fetch origin "$DEFAULT" && git merge "origin/$DEFAULT" --no-edit
```

### Verify Stage 1

| Check | Command | Expected |
|-------|---------|----------|
| Knowledge pointer | `grep 'knowledge-version' CLAUDE.md` | `<!-- knowledge-version: v45 -->` |
| Notes folder | `ls notes/` | `.gitkeep` exists |
| Gitignore | `cat .gitignore` | Standard rules present |
| License | `ls LICENSE` | File exists |
| Default branch has it | `git log origin/$DEFAULT --oneline -1` | Bootstrap commit visible |

**Console output**:
```
=== Stage 1 Verified ✓ ===

  ✓ Knowledge pointer: <!-- knowledge-version: v45 -->
  ✓ Notes folder: notes/.gitkeep
  ✓ Gitignore: standard rules
  ✓ License: MIT
  ✓ Default branch: bootstrap commit visible

  Proceeding to Stage 2 (normalize)...
```

---

## Round 2 — Normalize

Trim the satellite CLAUDE.md to critical-subset form. Remove any deep implementation content that was over-synced in Round 1, keeping the behavioral DNA.

### Steps

1. **Audit** — `normalize --check` reports over-synced content
2. **Trim** — Remove deep implementation details, keeping:
   - Knowledge Base pointer + version tag
   - Session Protocol (auto-wakeup, lifecycle, save, branch, human bridge, notifications, language, recovery)
   - Commands table (reference, not implementation)
   - Project overview
   - Project-specific commands (Part 2)
   - Project-specific patterns/pitfalls (if any)
3. **Verify size** — CLAUDE.md should be ~180 lines (critical-subset with full help), not ~300+ (over-synced)

### Deliver Round 2

```bash
git add CLAUDE.md
git commit -m "Normalize: trim satellite CLAUDE.md to critical-subset"
git push -u origin claude/<task-branch>
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
python3 scripts/gh_helper.py pr create --repo packetqc/<repo> --head claude/<task-branch> --base "$DEFAULT" --title "Normalize satellite CLAUDE.md" --body "Critical-subset trim" || \
  echo "Create PR manually: https://github.com/packetqc/<repo>/pull/new/claude/<task-branch>"
```

**Console output**:
```
=== Stage 2 — Normalize ===

  PR: <url> (or manual creation URL)
  Changes: CLAUDE.md trimmed to critical-subset (~200 lines)

  ⏸ Please merge the PR to confirm critical-subset.
  Say "merged" when done — I'll sync and verify.
```

### Sync + Verify Stage 2

```bash
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
git fetch origin "$DEFAULT" && git merge "origin/$DEFAULT" --no-edit
```

| Check | Expected |
|-------|----------|
| CLAUDE.md size | ~180 lines (critical-subset) |
| Session Protocol present | Auto-wakeup, lifecycle, save, branch sections |
| Commands table present | Reference table (not full implementation) |
| No harvest details | Branch crawling, promotion workflow not in file |
| No publication specs | Webcard animations, pub sync details not in file |
| No Knowledge Evolution | Not in file |
| Knowledge pointer present | `<!-- knowledge-version: v45 -->` |

**Console output**:
```
=== Stage 2 Verified ✓ ===

  ✓ CLAUDE.md: ~200 lines (critical-subset)
  ✓ Session Protocol: auto-wakeup, save, branch, human bridge
  ✓ Commands table: 7 groups, full command reference
  ✓ No harvest implementation details
  ✓ No publication specs
  ✓ No Knowledge Evolution table
  ✓ Knowledge pointer: <!-- knowledge-version: v45 -->

  Satellite is critical-subset. Proceeding to Stage 3 (optional)...
```

---

## Round 3 — Project Create (Optional)

Only needed if the satellite will produce documentation or publications.

```
project create "<Project Name>"
```

Creates: `docs/_config.yml`, layouts, bilingual landing pages, publications hub, asset placeholders.

### Prerequisites

- Wakeup completed (layouts sourced from `/tmp/knowledge/docs/_layouts/`)
- GitHub Pages enabled by user: Settings > Pages > Source: default branch, `/docs`

### Deliver Round 3

```bash
git add docs/ publications/
git commit -m "Project create: scaffold docs/publications/hub"
git push -u origin claude/<task-branch>
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
python3 scripts/gh_helper.py pr create --repo packetqc/<repo> --head claude/<task-branch> --base "$DEFAULT" --title "Scaffold project web presence" --body "Web presence scaffold" || \
  echo "Create PR manually: https://github.com/packetqc/<repo>/pull/new/claude/<task-branch>"
```

### Sync + Verify Stage 3

```bash
DEFAULT=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
git fetch origin "$DEFAULT" && git merge "origin/$DEFAULT" --no-edit
```

| Check | Expected |
|-------|----------|
| `docs/_config.yml` | Project-specific Jekyll config |
| `docs/_layouts/` | default.html + publication.html |
| `docs/index.md` | EN landing page |
| `docs/fr/index.md` | FR landing page |
| GitHub Pages | User confirms site accessible |

**Console output**:
```
=== Stage 3 Verified ✓ ===

  ✓ docs/_config.yml: project-specific Jekyll config
  ✓ docs/_layouts/: default.html + publication.html
  ✓ docs/index.md: EN landing page
  ✓ docs/fr/index.md: FR landing page
  ⏸ GitHub Pages: user confirms site accessible

  Web presence scaffolded.
```

---

## Final Confirmation

After all rounds complete:

```
=== Installation Complete ===

  Satellite: <repo-name>
  Knowledge version: v45
  CLAUDE.md: critical-subset (~200 lines)
  Default branch: <main|master>
  Web presence: <yes|no>

  Any new Claude Code session on this repo will:
  1. Auto-wakeup (step 0: read packetqc/knowledge)
  2. Inherit all methodology, commands, patterns
  3. Have session persistence (notes/)
  4. Use gh_helper.py for all API operations (not gh CLI)
  5. Be discoverable by harvest --healthcheck

  Next steps (from core):
    harvest --healthcheck    ← registers satellite in dashboard
```

---

## Stage 4 — Healthcheck (from Core)

From the **core knowledge repo** (`packetqc/knowledge`), not the satellite:

```
harvest --healthcheck
```

This scans all satellites including the new one. The dashboard updates with:
- Version: v36, Drift: 0, Bootstrap: active, Health: healthy

The satellite is now fully integrated into the knowledge network.

---

## Quick Checklist

| Check | Expected | Round |
|-------|----------|-------|
| `<!-- knowledge-version: vN -->` in CLAUDE.md | Present | 1 |
| CLAUDE.md size | ~180 lines (critical-subset) | 2 |
| No duplicated core content | Branch/Save Protocol, Part 1 commands removed | 2 |
| `notes/` folder exists | `.gitkeep` or session file | 1 |
| PRs merged to default branch | Bootstrap + normalize | 1-2 |
| `gh_helper.py` deployed | `scripts/gh_helper.py` exists | 1 |
| Dashboard row exists | Publication #4a with correct status | 4 |
| `minds/<project>.md` exists | In core knowledge repo | 4 |
| `docs/_config.yml` exists | Project-specific Jekyll config | 3 |
| GitHub Pages live | `https://packetqc.github.io/<repo>/` | 3 |

---

## Why Critical-Subset

```
                          ┌─────────────────────────┐
Core CLAUDE.md (2600+)    │ Full methodology,        │
                          │ all implementations,     │  ← source of truth
                          │ patterns, evolution...   │
                          └─────────────────────────┘
                                     ▲
                                     │ read on wakeup (Step 0)
                                     │
                          ┌─────────────────────────┐
Satellite CLAUDE.md (~180)│ Knowledge pointer        │
                          │ Session protocol DNA     │  ← critical-subset
                          │ Save + Branch protocol   │     (survives compaction)
                          │ Full 7-group commands    │
                          │ Project overview          │
                          │ Project-specific commands │
                          └─────────────────────────┘
```

**Why not thin-wrapper (~30 lines)**: In the core repo, CLAUDE.md is loaded as system-level project instructions — high authority, compaction-resilient. In satellites, the core's content arrives via a file read (conversation context) — lower authority, lost on first compaction. The thin-wrapper left satellites with no behavioral DNA after compaction: formatting broke, commands were forgotten, save protocol was lost. The critical-subset includes the essential operational rules that every session needs.

**Why not full mirror (2600+ lines)**: Duplicating the entire core creates massive version drift. Every core evolution (v31, v32...) would need propagation to every satellite. The critical-subset carries behavioral rules (stable, rarely change) but NOT implementation details (evolve frequently). The satellite still reads core on wakeup for the full picture.

**Benefits**:
- Core evolves — satellite inherits implementation details automatically on next wakeup
- Behavioral DNA survives compaction — auto-wakeup, save, branch protocol, commands stay loaded
- Clear separation: behavioral rules (satellite) vs implementation details (core)
- Single source of truth for deep implementations — core only

**When a satellite discovers something new** (a pattern, a pitfall, a methodology improvement):
1. Document it briefly in the satellite CLAUDE.md
2. Flag it with `remember harvest: <insight>`
3. Core's `harvest` command pulls it back on the next run
4. If validated across 2+ projects, it gets promoted to core `patterns/` or `lessons/`

---

## First Real Bootstrap — MPLIB_DEV_STAGING_WITH_CLAUDE (2026-02-19)

The three-stage lifecycle was discovered during the first v22 satellite bootstrap:

- **Stage 1**: Bootstrap session installed v22 pointer + over-synced ~60% core content (95 insertions). PR on `claude/setup-knowledge-v22-kDN01`, commit `15c3eb9`.
- **Discovery**: Items 3-6 of the bootstrap (Save Protocol, Part 1 commands, Branch Protocol, Session Lifecycle) duplicated core content — should be read on wakeup, not hardcoded.
- **Stage 2**: Pending — next wakeup + normalize will trim to thin-wrapper.
- **Stage 3**: Pending — harvest --healthcheck after Stage 2 merge.

This experience produced the thin-wrapper principle and the iterative staging protocol documented here.

---

*Authors: Martin Paquet & Claude (Anthropic, Opus 4.6)*
