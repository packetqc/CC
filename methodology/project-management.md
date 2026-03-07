# Project Management — Methodology

<!-- knowledge-version: v47 -->

---

## Overview

A **project** is a first-class entity in Knowledge. It is not a repository — it **has** repositories. It is not a publication — it **has** publications. It is not a satellite — it **has** satellites. The project entity ties everything together: identity, documentation, publications, evolution, stories, and platform presence.

**v35 introduces** the project entity model: hierarchical indexing (P#/S#/D#), platform integration (GitHub Project), URL-preserving restructure, and MPLIB decoupling from core to child.

---

## Project Relationships

Projects have three relationship types to repositories:

| Relationship | Meaning | Example |
|-------------|---------|---------|
| **owns** | The project's primary repository | P0 owns `packetqc/knowledge` |
| **child-of** | A sub-project of a parent project | P1 (MPLIB) is child-of P0 |
| **managed** | No dedicated repository — lives in a host repo (defaults to knowledge) | P6 (Export Documentation) managed in P3 (knowledge-live) |

**Every project links to a repo** — child projects link to their own repo, managed projects link to their host repo. No project exists without a repo link.

### Managed Projects

A **managed** project has no dedicated repository. It lives in a host repo — typically the knowledge core repo, or another project's repo. All content is authored and maintained in the host repo's working tree.

**Use cases**:
- Documentation initiatives spanning multiple child projects
- Process and standards tracking
- Cross-cutting concerns with no dedicated codebase
- Features or tools prototyped in an existing repo before getting their own
- Publications written in a satellite but documenting something unrelated

**Managed vs child**: A child project has its own repository with code, CLAUDE.md, session notes, and live tooling. A managed project has none of these — it lives inside a host repo with its own P# ID but no dedicated repo.

**Lifecycle differences**:

| Phase | Child | Managed |
|-------|-------|---------|
| Bootstrap (CLAUDE.md, notes/, live/) | Yes — wakeup step 0.5 | N/A — no dedicated repo |
| Harvest (knowledge flows back) | Yes — `harvest <project>` | N/A — already in host repo |
| Publications | Core and/or satellite | Core only |
| GitHub Project board | Yes — linked to own repo | Yes — linked to host repo |
| `project review` | Checks repo assets + docs | Checks docs + management status only |

**The `hosted-in` field** — specifies which repo a managed project lives in:
- `hosted-in: packetqc/knowledge` — lives in core (default)
- `hosted-in: packetqc/knowledge-live` — lives in another project's repo

The managed project:
- Is developed in the host repo's working tree
- Does NOT inherit the host repo's main project identity
- Gets its own P# ID in the registry
- On `harvest`, its content is routed to the correct project, not the host's main
- Its GitHub Project board links to the host repo

**Project metadata markers** for `managed`:

```markdown
<!-- project-id: P<n> -->
<!-- project-type: managed -->
<!-- project-status: active -->
<!-- hosted-in-repo: packetqc/knowledge-live -->
```

### Promotion-Based Import and Normalization

When a hosted project or new asset matures, the **promotion cycle** handles import and normalization:

1. **Discover** — `harvest` detects content in satellite that belongs to a different project (or a new project entirely)
2. **Route** — content is routed to the correct project's `minds/` entry (not the satellite's)
3. **Register** — if the project doesn't exist yet, `project register` assigns a P# ID
4. **Review** — `harvest --review` validates the content belongs to the target project
5. **Stage** — `harvest --stage N <type>` prepares for integration
6. **Promote** — `harvest --promote N` writes to the project's core assets (publications, patterns, methodology, docs)
7. **Normalize** — `normalize` ensures the promoted content follows project structure conventions (EN/FR mirrors, front matter, webcards, links)

This cycle works for any content: publications, patterns, methodology, documentation, project metadata. The promotion workflow is the **universal import mechanism** — it normalizes new projects and assets regardless of where they were discovered. A hosted project starts as a harvested insight, gets promoted through the pipeline, and emerges as a registered project with proper structure.

---

## Satellite Origin Tag — `(S#)` in GitHub Project Board Titles

When a project is created from a satellite, its **GitHub Project board title** carries an `(S#)` suffix to indicate the satellite of origin. This tag appears **only in the board title** — nowhere else.

| Origin | Board title example |
|--------|---------------------|
| Core | `Export Documentation` |
| Satellite (P3) | `Export Documentation (S3)` |

**Rules**:

1. **Core-created**: Board title is just the project name — no prefix, no tag
2. **Satellite-created**: Board title is `<Project Name> (S#)` where `S#` = satellite project number (e.g., `S3` for a project born on P3)
3. **Promotion drops the tag**: When a satellite project is promoted to core, update the board title to remove `(S#)`
4. **No tags elsewhere**: The `(S#)` convention applies only to GitHub Project board titles — not to project metadata files, registries, display conventions, or CLAUDE.md

The GitHub Project's returned `id` and `number` are stored in `projects/<slug>.md` metadata for code-level differentiation between core and satellite origins.

---

## Project Indexing Scheme

### Three-Level Hierarchy

```
Level 1: P<n>                    ← Project identifier
Level 2: P<n>/S<m>              ← Satellite (repository instance)
Level 3: P<n>/#<pub>            ← Publication or document
         P<n>/S<m>/D<k>         ← Satellite-local document
```

### Current Registry

| ID | Project | Type | Status |
|----|---------|------|--------|
| P0 | Knowledge System | core | 🟢 active |
| P1 | MPLIB | child | 🟢 active |
| P2 | STM32 PoC | child | 🟢 active |
| P3 | knowledge-live | child | 🟢 active |
| P4 | MPLIB Dev Staging | child (of P1) | 🟢 active |
| P5 | PQC | child | 🔴 pre-bootstrap |

### Display Convention

In all inventories, dashboards, and command output, the project index appears **left of the status tag**:

```
P0/#0    🟢  Knowledge
P0/#1    🟢  MPLIB Storage Pipeline           →P1
P0/#10   🟢  Live Knowledge Network           →P3
P1/S1    🟢  MPLIB (v31)
P5/S1    🔴  PQC (v0, pre-bootstrap)
```

The `→P<n>` cross-reference marker indicates a publication that documents a different project than where it's published.

### Machine-Parseable Markers

Every project metadata file carries markers for automated processing:

```markdown
<!-- project-id: P<n> -->
<!-- project-type: core|child|managed -->
<!-- project-status: active|pre-bootstrap|archived -->
<!-- github-project: <url or X> -->
<!-- parent-project: P<n> -->
```

Every document can carry provenance markers:

```markdown
<!-- project-index: P0/#7 -->
<!-- last-updated-by: knowledge/claude/<task-id> -->
<!-- last-updated: YYYY-MM-DD -->
```

---

## Project Commands

### Enhanced Command Table

| Command | Action |
|---------|--------|
| `project list` | List all projects with P# index, type, status, satellite count |
| `project info <P#>` | Show project details — identity, publications, satellites, evolution, stories, assets |
| `project create <name>` | Full project creation: register P# + GitHub Project board (elevated, linked to repo) + web presence |
| `project register <name>` | Register a new project with P# ID — creates `projects/<slug>.md` in core |
| `project review <P#>` | Review project state — documentation, publications, required assets, freshness |
| `project review --all` | Review all projects |
| `#N: <content>` | Scoped note routed to publication N (existing — unchanged) |
| `#N:info` | Show accumulated knowledge for publication N (existing — unchanged) |
| `#N:done` | End documentation focus, compile summary (existing — unchanged) |

### `project list` Output

```
=== Projects ===

  ID   Name                    Type      Status           Sats  Pubs  Health
  ───  ──────────────────────  ────────  ───────────────  ────  ────  ──────
  P0   Knowledge System        core      🟢 active        5     14    🟢
  P1   MPLIB                   child     🟢 active        2     1     🟢
  P2   STM32 PoC              child     🟢 active        1     1     🟢
  P3   knowledge-live          child     🟢 active        1     1     🟢
  P4   MPLIB Dev Staging       child     🟢 active        1     0     🟢
  P5   PQC                     child     🔴 pre-bootstrap 1     0     🔴
  P6   (example)               managed   🟢 active        —     2     🟢

  Total: 7 projects (6 active, 1 pre-bootstrap)
  Types: 1 core, 5 child, 1 managed
```

**Managed projects** show `—` in the Sats column (no dedicated satellites). Their Health is determined by documentation completeness and management status. Their board links to the host repo.

### `project info <P#>` Output

Reads the project's `projects/<slug>.md` file and displays identity, publications, satellites, evolution, stories, and required assets status. For child projects, also shows the parent relationship and cross-project publications.

### `project review <P#>` Output

Audits the project against the required assets checklist:

```
=== Project Review: P1 (MPLIB) ===

  Identity:      🟢 registered (projects/mplib.md)
  CLAUDE.md:     🟢 active (v31, critical-subset)
  notes/:        🟢 present (2 sessions in P1/S1, 5 sessions in P1/S2)
  live/:         🟢 deployed
  Publications:  🟡 1 in core (P0/#1), 0 local
  Docs:          🔴 web presence not created
  GitHub Project: 🔴 not created
  Evolution:     🟡 6 entries (last: 2026-02-22)
  Stories:       🟡 3 entries (2 undated)

  Recommended actions:
  1. Create web presence: project create MPLIB --docs-only
  2. Create GitHub Project (requires elevated access)
  3. Review undated stories — add dates from git history
  4. Consider local publications for MPLIB-specific content
```

**Managed project review** — checks documentation and management status, board linked to host repo:

```
=== Project Review: P6 (Export Documentation) ===

  Identity:      🟢 registered (projects/export-documentation.md)
  Type:          managed (hosted in packetqc/knowledge-live)
  Publications:  🟡 0 yet
  Docs:          🟢 web presence active
  GitHub Project: 🟢 #10 (linked to knowledge-live)
  Evolution:     🟡 4 entries (last: 2026-02-22)
  Stories:       🟡 1 entry

  Recommended actions:
  1. Review evolution entries for completeness
```

---

## Project Creation Protocol

### `project create <name>` — Enhanced

The enhanced `project create` now handles the full project entity lifecycle:

```
1. Gather inputs:         Interactive popup (type, description, parent, board)
2. Register project:      Assign P# ID, create projects/<slug>.md
3. Create GitHub Project:  If elevated, create GitHub Project board via API (gh_helper.py / urllib)
4. Link project to repo:  If elevated, link GitHub Project to default repository via API
5. Bootstrap satellite:   wakeup step 0.5 (CLAUDE.md, notes/, live/, etc.)
6. Scaffold web presence: docs/, layouts, hubs, publications/ (existing project create)
7. Register in core:      Update projects/README.md index table
8. Update dashboard:      Add satellite to harvest dashboard
9. Commit & deliver:      Commit, push, PR
```

**Repository creation is manual** — the user creates the repo via GitHub web UI (`https://github.com/new`) or CLI before running `project create`. This command operates on an existing repo. Repo creation via API is not automated because it requires decisions about visibility (public/private), initialization options, and team access that are better handled through the GitHub UI.

**When elevated** (PAT available): Steps 3 and 4 use GitHub GraphQL API via Python `urllib` (NOT `curl` — proxy intercepts auth headers) to create the GitHub Project board and link it to the repository.

**When not elevated**: Steps 3 and 4 are skipped with guidance:

```
⏸ Pause — manual steps required

  Created: projects/<slug>.md (P# registered)
  Skipped: GitHub Project board creation (no token)

  What you need to do:
  1. Create a GitHub Project: https://github.com/packetqc?tab=projects
  2. Link it to the repo in the Projects tab
  3. Or type: elevate — to provide a token and auto-create
```

### `project register <name>` — Lightweight

Just creates the project metadata file without full creation. Used when:
- The repo already exists
- You want to register a discovered project (from harvest)
- You're documenting an existing satellite as a formal project
- A managed project is being tracked (no repo)

```
project register MPLIB
project register --type managed "Standards Documentation"
```

Creates `projects/mplib.md` with P# ID auto-assigned (next available), populates from `minds/<slug>.md` if available (auto-populate with existing content). For managed projects, use `--type managed` — the host repo defaults to the current repo.

### GitHub Project Creation — Two Entry Points

GitHub Project boards are created through two distinct paths:

| Path | Trigger | Guard | When |
|------|---------|-------|------|
| **`project create`** | Direct command | User intent | Explicit project creation — creates GitHub Project immediately |
| **`harvest --promote`** | Promoted insight warrants a project | Full promotion pipeline (review → stage → promote) | Intel matured through harvest, staged as project-grade, promoted to core |

**Harvest-driven project creation** — when a harvested insight is promoted and the insight represents a new project (not just a pattern or lesson):

```
harvest <satellite>                    # Discover intel
harvest --review N                     # Validate intel
harvest --stage N project              # Stage as project-grade (new stage type)
harvest --promote N                    # Promote → auto-registers P# + creates GitHub Project (if elevated)
```

The `project` stage type (alongside `lesson`, `pattern`, `methodology`, `evolution`, `docs`) triggers:
1. `project register` — assigns P# ID, creates `projects/<slug>.md`
2. GitHub Project creation — if elevated (L2+ token), creates the board via API
3. Project metadata population — from `minds/<slug>.md` harvested data

**Guard**: The promotion pipeline is the quality gate. Intel must pass review and staging before it can trigger project creation. This prevents premature projects from harvested noise — only intel that has been human-validated and explicitly staged as `project` reaches this point.

**Managed projects via harvest**: When harvest discovers documentation-grade intel from satellites that doesn't belong to any existing child project, the promotion path creates a **managed** project — hosted in the satellite's repo (or in core). The satellite is the source of discovery, and the managed project's board links to that host repo.

---

## Multi-Instance Concurrent Updates

Multiple Claude Code instances can update the same project's content. The convergence protocol ensures no data loss:

### Indexation Rules

1. **Append-only indexing**: Each instance appends to the project index — never overwrites
2. **Provenance tracking**: Each document carries `<!-- last-updated-by -->` marker
3. **Harvest concatenation**: `harvest --healthcheck` merges indexes from all satellites
4. **Conflict resolution**: Most recent `last-updated` timestamp wins for duplicate entries

### Three-Level Index Convergence

```
Core index (P0):       Master registry — all projects, all publications
  ↑ harvest
Satellite index (S#):  Local registry — satellite-specific documents
  ↑ session
Session notes:         Ephemeral — accumulated during work, saved on commit
```

On harvest, the satellite index is concatenated with the core index. Duplicates are resolved by timestamp. New entries are appended. The combined index is the complete view.

### Display: Index Tag Left of Status

In all dashboards, inventories, and command outputs, the hierarchical index tag appears **to the left** of the status indicator:

```
P0/#0    🟢  Knowledge
P1/S1    🟢  MPLIB (v31)
P2/S1/D1 X   STM32 local doc (not yet promoted)
```

This convention makes the hierarchy immediately visible at a glance.

---

## URL Preservation Strategy

The project tree restructure is **additive** — no existing URLs change.

### What Stays

| Structure | URL pattern | Change |
|-----------|-------------|--------|
| Publications | `/publications/<slug>/` | **None** — permalinks unchanged |
| Complete pages | `/publications/<slug>/full/` | **None** |
| FR publications | `/fr/publications/<slug>/` | **None** |
| Profile pages | `/profile/`, `/profile/resume/`, `/profile/full/` | **None** |
| Webcards | `/assets/og/<card>-<lang>-<theme>.gif` | **None** |
| Landing page | `/` | **None** |

### What's New

| Structure | URL pattern | Content |
|-----------|-------------|---------|
| Project hub EN | `/projects/` | Project-centric navigation |
| Project hub FR | `/fr/projects/` | French mirror |

### Creative Preservation

Publications stay at `/publications/<slug>/` — they are NOT moved to `/projects/<P#>/publications/`. Instead, the project hub pages (`/projects/`) provide a **navigation overlay** that links to existing publication URLs, organized by project. The project hierarchy is metadata, not file structure.

```
/projects/                       ← NEW: "View by project" navigation
  ├── Links to /publications/knowledge-system/     (P0)
  ├── Links to /publications/mplib-storage-pipeline/ (P1)
  └── Links to /publications/live-knowledge-network/ (P3)

/publications/                   ← UNCHANGED: flat list, all publications
  ├── knowledge-system/
  ├── mplib-storage-pipeline/
  └── live-knowledge-network/
```

Two navigation paths to the same content: by publication number (existing) and by project (new).

---

## Dual-Origin Link System

Publications and documentation can exist across multiple repositories, each with its own GitHub Pages site. The **link origin** indicates provenance and review status:

### Origin Badges

| Origin | Badge | Base URL | Meaning |
|--------|-------|----------|---------|
| **Core** | **core** | `packetqc.github.io/knowledge/` | Reviewed, published, canonical version |
| **Satellite** | *satellite* | `packetqc.github.io/<repo>/` | Development, staging, local documentation |

### URL Resolution

Same publication, different origin:

| Context | URL | Badge |
|---------|-----|-------|
| Core publication #1 | `packetqc.github.io/knowledge/publications/mplib-storage-pipeline/` | **core** |
| Satellite local doc | `packetqc.github.io/MPLIB/publications/<slug>/` | *satellite* |
| Satellite dev doc | `packetqc.github.io/MPLIB_DEV_STAGING_WITH_CLAUDE/docs/<slug>/` | *satellite* |

### Why This Matters

1. **Core links are stable** — published, reviewed, canonical. Safe to share externally.
2. **Satellite links are evolving** — local to the development environment. May change or disappear.
3. **Both are valid** — same GitHub Pages technology, different review stage.
4. **Cross-referencing** — core publications can reference satellite docs for "latest development" state, and satellite docs can reference core publications for "official" state.

### Display Convention

In project hub pages and publication inventories, the origin badge appears in the **Origin** column:

```
P0/#1    MPLIB Storage Pipeline     core       packetqc.github.io/knowledge/publications/...
P1/S1/D1 MPLIB local doc            satellite  packetqc.github.io/MPLIB/publications/...
```

### Configuring GitHub Pages on Satellites

Each satellite repo can independently enable GitHub Pages:

1. GitHub → Settings → Pages → Source: default branch, `/docs`
2. Use `project create <name>` to scaffold `docs/`, layouts, and hubs
3. Satellite publications are served at `packetqc.github.io/<repo>/`
4. Core knowledge links are **never affected** — different base URL entirely

This independence means satellite teams can iterate on documentation without touching core productivity. When satellite content matures, it gets promoted to core via `harvest` + `pub sync`.

---

## MPLIB Decoupling

MPLIB is reclassified from core asset to child project:

| Before (v34) | After (v35) |
|--------------|-------------|
| Publications index titled "MPLIB Knowledge" | Titled "Knowledge System" |
| `_config.yml` title: "MPLIB Knowledge" | Title: "Knowledge System" |
| About section references MPLIB as primary | About section references Knowledge System as primary |
| MPLIB patterns in core `patterns/` | Stay in core (they generalize) — tagged as originating from P1 |
| Publication #1 = core publication | P0/#1 with cross-ref `→P1` |

**What doesn't change**: Publication #1 stays at its current URL. MPLIB patterns stay in core `patterns/` (they are proven general patterns). The minds/ files stay. The satellite dashboard rows stay.

**What changes**: Identity — MPLIB is no longer part of the core's name, just its most successful child.

---

## Satellite Deployment Procedure

When a satellite has not yet been restructured to v35:

### Automatic (next wakeup)

1. Satellite instance runs `wakeup`
2. Step 0 reads core CLAUDE.md (now v35) → gains project awareness
3. Project commands become available
4. No file changes needed on satellite — project metadata lives in core

### Manual (on-demand)

For users who want to explicitly activate project management:

```bash
# In the satellite's Claude Code session:
wakeup                                  # Reads v35 core
project register                        # Creates project entry in local notes
save                                    # Delivers to satellite's default branch
```

Then, from core:
```bash
harvest <satellite>                     # Pulls project registration to core
# OR
harvest --healthcheck                   # Full sweep picks it up
```

### Migration Guide

When a Claude Code instance detects it's running in an environment that predates v35:

```
ℹ️ Project management (v35) not yet active in this environment.

  This session has project awareness (read from core v35), but the
  local environment doesn't have the project structure yet.

  To activate:
  1. Type: project register
  2. This creates your project entry and registers it for harvest
  3. On next harvest from core, your project appears in the registry

  No existing files are moved or renamed. Project metadata is additive.
```

---

## Integration with Existing Commands

### `harvest` Integration

`harvest --healthcheck` now includes project status (managed projects show `—` for satellite columns):

```
=== Harvest Healthcheck 2026-02-22 ===

  Projects: 6 (5 active, 1 pre-bootstrap)
  Satellites: 6 (5 healthy, 1 pre-bootstrap)

  P0  Knowledge System     🟢 core      14 pubs, 5 children
  P1  MPLIB                🟢 child     1 pub,   2 sats
  P2  STM32 PoC           🟢 child     1 pub,   1 sat
  P3  knowledge-live       🟢 child     1 pub,   1 sat
  P4  MPLIB Dev Staging    🟢 child     0 pubs,  1 sat
  P5  PQC                  🔴 pre-boot  0 pubs,  1 sat
  P6  (example)            🟢 managed   2 pubs,  — sats
```

### `normalize` Integration

`normalize` now checks project concordance:

| Check | What it verifies |
|-------|------------------|
| Project registry | Every satellite in dashboard has a corresponding `projects/<slug>.md` |
| Index consistency | P# assignments are unique and sequential |
| Cross-references | `→P<n>` markers point to valid projects |
| Required assets | Each project's asset checklist is accurate |
| GitHub Project | Platform entity exists (if elevated) |

### `pub list` Integration

`pub list` now shows project index:

```
=== Publication Inventory ===

  Index    #   Slug                          Source  EN   FR   Full  Card  →Proj
  ───────  ──  ────────────────────────────  ──────  ───  ───  ────  ────  ─────
  P0/#0    0   knowledge-system              ✓       ✓    ✓    ✓     ✓     —
  P0/#1    1   mplib-storage-pipeline        ✓       ✓    ✓    ✓     ✓     →P1
  P0/#2    2   live-session-analysis         ✓       ✓    ✓    ✓     ✓     —
  ...
  P0/#10   10  live-knowledge-network        ✓       ✓    ✓    ✓     ✓     →P3
  P0/#11   11  success-stories               ✓       ✓    ✓    ✓     —     —
```

### `doc review` Integration

`doc review --list` now includes project index:

```
=== Doc Review — Freshness Inventory ===

  Index    #   Publication                        Version  Freshness
  ───────  ──  ──────────────────────────────────  ───────  ─────────
  P0/#0    0   Knowledge System                   v35      🟢 current
  P0/#1    1   MPLIB Storage Pipeline              v20      🔴 stale (15 versions)  →P1
  ...
```

---

## GitHub Project Integration

When elevated with a **classic PAT (L3)** that has the `project` scope, `project create` creates a GitHub Project board.

**Platform requirement**: GitHub Projects v2 boards exist at the **user/account level**, not the repository level. Fine-grained PATs (L2) are repo-scoped and **cannot** create or even read Projects v2 boards — they return `FORBIDDEN: Resource not accessible by personal access token`. A classic PAT with `project` scope (L3) is required. This is the only operation in Knowledge that requires L3. The `project create` command handles this gracefully: knowledge structure (`projects/*.md`) is always created (no token needed), GitHub board creation is attempted only when L3 is available and skipped otherwise.

**API channel**: All GitHub API calls (REST + GraphQL) go through `gh_helper.py` which uses Python `urllib` (direct). Never `curl` (proxy-intercepted — strips auth headers, returns 401). The token is read from `GH_TOKEN` environment variable internally — never on the command line.

### API Calls

**One-command pipeline** — create board + link to repo:

```bash
# Create GitHub Project + link to repo (full pipeline)
python3 scripts/gh_helper.py project ensure \
  --title "<Project Name>" --owner packetqc --repo <repo-name>
```

**Step-by-step** — when you need the intermediate IDs:

```bash
# Step 1+2: Create board (gets viewer ID internally)
python3 scripts/gh_helper.py project create-board --title "<Project Name>"
# Output: Board #N created: https://github.com/users/packetqc/projects/N
#         Project ID: PVT_xxx

# Step 3+4: Link board to repo
python3 scripts/gh_helper.py project link-repo \
  --project-id PVT_xxx --owner packetqc --repo <repo-name>
# Output: Linked to repository: <repo-name>
```

**Programmatic usage** (Python module):

```python
from scripts.gh_helper import GitHubHelper
gh = GitHubHelper()  # Reads GH_TOKEN from os.environ
result = gh.project_ensure("My Project", "packetqc", "my-repo")
print(f'Board #{result["number"]} created and linked: {result["url"]}')
```

**Security**: Token is read from `GH_TOKEN` env var (set in Claude Code cloud environment config) — never appears on any command line, never in Bash tool output, never in session transcript. See v46 evolution entry.

**GraphQL mutations used internally** by `gh_helper.py`:
- `query { viewer { id login } }` — get owner node ID
- `createProjectV2(input: {ownerId, title})` — create board
- `query { repository(owner, name) { id } }` — get repo node ID
- `linkProjectV2ToRepository(input: {projectId, repositoryId})` — link board to repo

### Project Board Fields

| Field | Value |
|-------|-------|
| Title (core) | `<Project Name>` |
| Title (satellite) | `<Project Name> (S#)` — where `S#` = satellite project number |
| Description | From project metadata |
| Columns | Backlog, In Progress, Done |
| Labels | `knowledge`, `satellite`, `publication`, `harvest` |

### Linking

The GitHub Project `id` and `number` are stored in `projects/<slug>.md` for code-level differentiation:

```markdown
<!-- github-project: <N> -->
<!-- github-project-id: <node_id> -->
```

URL pattern: `https://github.com/users/packetqc/projects/<N>`

When `project review` runs, it checks if the GitHub Project exists and is linked. The stored `id`/`number` allow programmatic access to the board without parsing titles.

**Repository linking** — After creating a GitHub Project board, it must be linked to the project's default repository using the `linkProjectV2ToRepository` GraphQL mutation. Without this step, the project board exists at the user level but does not appear in the repository's "Projects" tab.

| Step | Mutation | What it does |
|------|----------|-------------|
| Create | `createProjectV2` | Creates board at user level — visible at `github.com/users/<owner>/projects/<N>` |
| Link | `linkProjectV2ToRepository` | Links board to repo — visible in repo's Projects tab |

**Linking rules** — every project links to a repo:
- For core (P0), link to `packetqc/knowledge`
- For child projects, link to their primary satellite repo
- For managed projects, link to their host repo (e.g., P6 links to `packetqc/knowledge-live`)

**Required inputs**: `projectId` (from `createProjectV2` response) + `repositoryId` (from `repository(owner, name)` query). Both are GraphQL node IDs.

### GitHub Projects as Human Bridge

Knowledge operates AI-to-AI (Claude instances communicating via git, harvest, beacon). The GitHub Project board is the **human interface layer** — where the AI-native knowledge system meets human-native project management:

| Knowledge system (AI-native) | GitHub Project (human-native) |
|------------------------------|-------------------------------|
| `projects/<slug>.md` metadata | Project board with cards |
| Evolution entries (v#) | Milestones |
| Harvest insights | Issues (auto-created from promotion candidates) |
| Project stories | Discussion threads |
| `project review` findings | Issue labels (stale, missing, drift) |
| Session notes | Activity timeline |

**External connectors** — GitHub Projects integrates with third-party tools that Knowledge cannot reach directly:

| Connector | What it enables |
|-----------|----------------|
| **Human collaborators** | Assign tasks, comment on issues, review milestones — no Claude Code needed |
| **CI/CD pipelines** | GitHub Actions triggered by project card moves, label changes |
| **Slack/Teams bots** | Notifications when project status changes, new issues created |
| **Jira/Linear sync** | Two-way sync for teams using external PM tools |
| **Email notifications** | GitHub's built-in notification for issue/milestone updates |
| **Mobile apps** | GitHub mobile — project status check from anywhere |

**Why this matters**: Knowledge is powerful but opaque to non-AI participants. A manager, a collaborator, or an auditor cannot read `minds/stm32n6570-dk-sqlite.md` and get actionable status. A GitHub Project board with labeled issues, milestones, and assignees is immediately comprehensible. The board is the **human-readable projection** of the AI-native project state.

**Automation potential** (when elevated):
- `harvest --healthcheck` creates issues for 🔴 findings (unreachable satellites, critical drift)
- `project review` creates issues for missing assets (no docs, no webcard, no GitHub Project)
- `doc review --apply` updates milestone progress when publications are refreshed
- `harvest --promote` moves project board cards from "Backlog" to "Done"

This makes the GitHub Project a **living board** that reflects Knowledge's actual state — updated by AI sessions, consumed by humans and external tools.

---

## Evolution & Stories Tracking

Each project has its own evolution log and stories section in `projects/<slug>.md`. These are populated from:

1. **Git commit history** — `git log` on the project's repositories
2. **PR descriptions and merge history** — `gh pr list --state merged` or API
3. **Session notes** — `notes/` files across all satellites
4. **Harvest data** — `minds/<slug>.md` insights
5. **Manual entries** — via `#N:` scoped notes or direct edits

### Git History as Content Source

When generating or updating project metadata, publication content, or documentation, **git commit history and PR descriptions are primary data sources** — not just references but actual content generators:

| Git artifact | What it feeds | How |
|-------------|---------------|-----|
| **Commit messages** | Evolution entries, version history | `git log --oneline --since=<date>` → dated entries with descriptions |
| **PR titles + bodies** | Stories, milestone summaries | `gh pr list --state merged` or API → structured narrative |
| **Commit diffs** | Publication version sections, changelogs | `git diff <v1>..<v2>` → what changed between versions |
| **Branch history** | Session timeline, project activity | `git for-each-ref --sort=-committerdate` → activity map |
| **Merge dates** | Accurate timestamps for evolution | PR merge date = when the work landed, not when it was committed |
| **Tag history** | Version milestones | `git tag -l --sort=-version:refname` → release progression |

### Content Generation Protocol

When `project register`, `project review`, `doc review --apply`, or `pub sync` runs, it **merges git-sourced content with the current version** of the document:

```
1. Read current document content (project.md, publication, or doc page)
2. Read git history for the project's repositories:
   - git log --oneline --since=<last-updated> <repo>
   - gh pr list --state merged --json title,body,mergedAt (if elevated)
3. Extract structured content:
   - Commits with feat/fix/refactor prefixes → evolution entries
   - PR descriptions with ## Summary sections → stories
   - Dated changes → version history updates
4. Merge with existing content:
   - Append new evolution entries (don't overwrite existing)
   - Add new stories (append-only, deduplicate by date+topic)
   - Update version references to current
   - Fill X placeholders with actual data
5. Write updated document
```

**Merge, not replace** — existing manually-written entries are preserved. Git-sourced entries are added alongside them. The merge is additive: new data fills gaps, existing content stays.

**Date accuracy** — use PR merge dates (when available) rather than commit dates for evolution entries. PR merge = when the work reached the default branch = the meaningful timestamp. Commit dates can be hours or days earlier (work-in-progress on task branches).

### Auto-Population on `project register`

When registering a project that already has harvested data (`minds/<slug>.md`) AND git history, the registration auto-populates from both:

| Source | Populates |
|--------|-----------|
| `git log --oneline -20 <repo>` | Evolution entries (dated, from commit messages) |
| `gh pr list --state merged` | Stories (from PR descriptions) |
| `minds/<slug>.md` version data | Knowledge Version, Drift |
| `minds/<slug>.md` branch cursors | Last harvest date |
| `minds/<slug>.md` patterns | Additional evolution entries |
| `minds/<slug>.md` pitfalls | Additional stories |
| Dashboard satellite table | Status, health, sessions, assets |

This ensures `project register` generates **actual content** from existing data — not empty placeholders. The combination of git history + minds/ data gives a comprehensive initial population.

---

## Relationship to Other Methodologies

| Methodology | Scope | Project management adds |
|-------------|-------|------------------------|
| `satellite-bootstrap.md` | First-time satellite onboarding | Project registration as part of bootstrap |
| `project-create.md` | Web presence scaffolding (docs/) | Full entity creation (P# + repo + GitHub Project + web) |
| `tagged-input.md` | Scoped notes (`#N:`) | Notes route to project-indexed publications |
| `session-protocol.md` | Session lifecycle | Project context in session state |
| `checkpoint-resume.md` | Crash recovery | Project state in checkpoint data |
