# Project Create — Scaffolding a Satellite's Web Presence

How to create a complete GitHub Pages + publication structure on a satellite project. The `project create` command runs on the satellite, uses knowledge's layouts and conventions, and produces a ready-to-publish website.

---

## What It Creates

```
<satellite-repo>/
  docs/
    _config.yml                    ← Jekyll config for GitHub Pages
    _layouts/
      default.html                 ← Copied from knowledge (Cayman/Midnight themes)
      publication.html             ← Copied from knowledge (banner, keywords, cross-refs)
    index.md                       ← Project landing page (EN)
    publications/
      index.md                     ← Publications hub (EN)
    fr/
      index.md                     ← Project landing page (FR)
      publications/
        index.md                   ← Publications hub (FR)
    assets/
      og/.gitkeep                  ← Webcard GIFs placeholder
  publications/                    ← Source publications (versioned)
    .gitkeep
```

**Total: 10 files, 6 directories.** Everything needed for a bilingual GitHub Pages site with publication support.

---

## Prerequisites

Before running `project create`:

1. **Wakeup completed** — knowledge is read, `/tmp/knowledge/` clone is available
2. **Bootstrap done** — satellite CLAUDE.md exists with knowledge pointer (`<!-- knowledge-version: vN -->`)
3. **GitHub Pages enabled** — user has enabled Pages for the repo (Settings > Pages > Source: default branch, `/docs` folder)

---

## Command

```
project create <name>
```

Where `<name>` is the human-readable project name (e.g., "Knowledge Live", "MPLIB Dev Staging"). The name can also be omitted — the interactive input gathering will ask for it.

---

## Interactive Input Gathering (Universal Convention)

`project create` follows the **Interactive Input Convention** — all required parameters are gathered upfront via `AskUserQuestion` popups BEFORE any execution begins. This is a universal convention that applies to all multi-parameter commands in Knowledge.

### Why Gather First, Execute Second

1. **Error prevention** — validating all inputs before execution prevents half-completed states that require manual cleanup
2. **UX consistency** — the user sees all decisions upfront, can make informed choices, and knows what will happen
3. **API 400 prevention** — gathering inputs in a single popup reduces the number of API round-trips, preventing `tool_use ids must be unique` collisions that occur when multiple sequential tool calls generate identical patterns (see Pitfall #15)
4. **Idempotency** — once all inputs are gathered, the execution phase is a single deterministic pass with no back-and-forth

### Interactive Questions — `AskUserQuestion` Specification

**Single popup, 3 questions** — all gathered in ONE `AskUserQuestion` call to minimize API round-trips:

```json
{
  "questions": [
    {
      "question": "What type of project is this?",
      "header": "Type",
      "options": [
        {"label": "child", "description": "Repository-backed satellite project with its own code, CLAUDE.md, sessions, and live tooling"},
        {"label": "managed", "description": "No dedicated repository — lives in a host repo (defaults to current repo). Board links to host repo."}
      ],
      "multiSelect": false
    },
    {
      "question": "Provide a short description (1-2 sentences) for the project.",
      "header": "Description",
      "options": [
        {"label": "Auto-generate", "description": "Claude generates a description based on the project name and type"}
      ],
      "multiSelect": false
    },
    {
      "question": "Create a GitHub Project board? (requires classic PAT with repo + project scopes)",
      "header": "Board",
      "options": [
        {"label": "Yes (Recommended)", "description": "Create GitHub Project board + link to repository. Auto-elevates if needed."},
        {"label": "Skip", "description": "No board — can be created later with project review"}
      ],
      "multiSelect": false
    }
  ]
}
```

**After gathering**: Print a confirmation summary before executing:

```
=== Project Create: Summary ===

  Name:        Knowledge Live
  Type:        child
  Parent:      P0 (Knowledge System)
  Description: Live knowledge network tooling and beacon infrastructure
  P# ID:       P7 (next available)
  Repository:  packetqc/knowledge-live
  Board:       Yes (will auto-elevate)

  Proceeding with creation...
```

Then execute all steps sequentially — no more interactive questions during execution.

### Adaptation Rules

- **If `<name>` is provided as argument**: Skip the name question, still ask the other 2
- **If type is `managed`**: Board links to the current/host repo (not skipped — every project links to a repo)
- **If already elevated**: Skip the board question — always create (the user already authorized API access)

---

## Execution Protocol

After all inputs are gathered and confirmed, execute in order:

1. **Read layouts** from `/tmp/knowledge/docs/_layouts/` (cloned during wakeup)
2. **Copy layouts** to satellite's `docs/_layouts/`, adapting `og:site_name` to the project name
3. **Create `_config.yml`** with satellite-specific values (title, baseurl, description)
4. **Create landing pages** (EN + FR) with project name, links to knowledge and publications
5. **Create publications hubs** (EN + FR) — empty, ready for `pub new`
6. **Create asset folders** — `docs/assets/og/` for future webcards
7. **Create source folder** — `publications/` for source publication documents
8. **Create GitHub Project + link to repo** (if elevated) — see [CLI Reference](#cli-reference--ghhelperpy-exact-syntax) for exact syntax
9. **Report** what was created and next steps

---

## File Specifications

### `docs/_config.yml`

```yaml
title: "<Project Name>"
description: "<project description>"
url: "https://packetqc.github.io"
baseurl: "/<repo-name>"

# No remote theme — layouts are self-contained (copied from knowledge)
plugins:
  - jekyll-seo-tag

# SEO defaults
author: "Martin Paquet & Claude (Anthropic)"
locale: "en_US"

# Default front matter
defaults:
  - scope:
      path: "docs/publications"
      type: "pages"
    values:
      layout: "publication"

# Markdown rendering
markdown: kramdown
kramdown:
  input: GFM
```

**Key differences from knowledge's config**:
- `title` and `description` are project-specific
- `baseurl` uses the satellite repo name (e.g., `/knowledge-live`)
- No `remote_theme` — layouts are local copies, self-contained with inline CSS
- Plugins minimal — only `jekyll-seo-tag`

### `docs/_layouts/default.html`

**Copied from knowledge** — the exact same file with one adaptation:

| What changes | From | To |
|-------------|------|-----|
| `og:site_name` | `MPLIB Knowledge` | `<Project Name>` |

Everything else is identical: Cayman/Midnight CSS variables, webcard header, mermaid support, cache-bust JS. The satellite's pages look visually identical to knowledge's pages.

### `docs/_layouts/publication.html`

**Copied from knowledge** — the exact same file with one adaptation:

| What changes | From | To |
|-------------|------|-----|
| `og:site_name` | `MPLIB Knowledge` | `<Project Name>` |

The keyword cross-reference map stays as-is — it links to knowledge publications (external URLs). As the satellite creates its own publications, their keywords get added to the map.

### `docs/index.md` (EN Landing Page)

```markdown
---
layout: default
title: "<Project Name>"
description: "<project description>"
permalink: /
---

# <Project Name>

<project description>

[**View Publications →**]({{ '/publications/' | relative_url }})

[**Knowledge Base →**](https://packetqc.github.io/knowledge/) | [**Base de connaissances →**](https://packetqc.github.io/knowledge/fr/publications/)

[**View on GitHub →**](https://github.com/packetqc/<repo-name>)

---

*Part of the [packetqc/knowledge](https://github.com/packetqc/knowledge) network.*
```

### `docs/fr/index.md` (FR Landing Page)

```markdown
---
layout: default
title: "<Nom du Projet>"
description: "<description du projet>"
permalink: /fr/
---

# <Nom du Projet>

<description du projet>

[**Voir les publications →**]({{ '/fr/publications/' | relative_url }})

[**Knowledge Base →**](https://packetqc.github.io/knowledge/) | [**Base de connaissances →**](https://packetqc.github.io/knowledge/fr/publications/)

[**Voir sur GitHub →**](https://github.com/packetqc/<repo-name>)

---

*Membre du réseau [packetqc/knowledge](https://github.com/packetqc/knowledge).*
```

### `docs/publications/index.md` (EN Publications Hub)

```markdown
---
layout: default
title: "<Project Name> — Publications"
description: "Technical publications from <Project Name>."
permalink: /publications/
---

# Publications

Technical publications from **<Project Name>**.

*By Martin Paquet & Claude (Anthropic)*

**Languages / Langues**: English (this page) | [Français]({{ '/fr/publications/' | relative_url }})

---

*No publications yet. Use `pub new <slug>` to create the first one.*

---

## About

| | |
|---|---|
| **Knowledge Base** | [packetqc/knowledge](https://github.com/packetqc/knowledge) |
| **Project** | [packetqc/<repo-name>](https://github.com/packetqc/<repo-name>) |
| **Contact** | packetqcca@gmail.com |
```

### `docs/fr/publications/index.md` (FR Publications Hub)

```markdown
---
layout: default
title: "<Nom du Projet> — Publications"
description: "Publications techniques de <Nom du Projet>."
permalink: /fr/publications/
---

# Publications

Publications techniques de **<Nom du Projet>**.

*Par Martin Paquet & Claude (Anthropic)*

**Languages / Langues**: [English]({{ '/publications/' | relative_url }}) | Français (cette page)

---

*Aucune publication pour le moment. Utilisez `pub new <slug>` pour créer la première.*

---

## À propos

| | |
|---|---|
| **Base de connaissances** | [packetqc/knowledge](https://github.com/packetqc/knowledge) |
| **Projet** | [packetqc/<repo-name>](https://github.com/packetqc/<repo-name>) |
| **Contact** | packetqcca@gmail.com |
```

---

## Layout Adaptation Rules

When copying layouts from knowledge to a satellite:

1. **Replace `og:site_name`** — change `MPLIB Knowledge` to the project name
2. **Keep everything else** — CSS, JS, webcard header, mermaid, cache-bust, all identical
3. **Keyword map** — leave as-is (points to knowledge publications). Satellite pubs add entries later
4. **Version banner** — works automatically (reads from front matter)
5. **Theme detection** — works automatically (Cayman/Midnight via `prefers-color-scheme`)

**Why copy, not reference?** The layouts are self-contained — all CSS is inline, no external theme dependency. Copying ensures the satellite's GitHub Pages works independently. If knowledge updates layouts, the satellite picks up changes on next `project update` (future command) or manual copy.

---

## CLI Reference — `gh_helper.py` Exact Syntax

These are the **proven working commands** — use exactly this syntax to avoid trial-and-error errors. All commands read `GH_TOKEN` from the environment variable internally (never passed on the command line).

### Create GitHub Project Board + Link to Repo

```bash
python3 scripts/gh_helper.py project ensure --title "<Project Name>" --owner packetqc --repo <repo-name>
```

**Important**: `--owner` and `--repo` are **separate flags**. Do NOT combine them as `--repo packetqc/<repo-name>` — that will fail with "required parameter missing".

Example:
```bash
python3 scripts/gh_helper.py project ensure --title "Project test 400" --owner packetqc --repo knowledge
```

### Create Pull Request

```bash
python3 scripts/gh_helper.py pr create --repo packetqc/<repo-name> --base <default-branch> --head <task-branch> --title "<title>" --body "<body>"
```

**Important**: `--repo` is **required** and uses `owner/repo` format (combined). Do NOT omit it — that will fail with "required parameter missing".

Example:
```bash
python3 scripts/gh_helper.py pr create --repo packetqc/knowledge --base main --head claude/create-new-project-E02VB --title "Register P7" --body "Summary of changes"
```

### Merge Pull Request

```bash
python3 scripts/gh_helper.py pr merge --repo packetqc/<repo-name> --number <pr-number>
```

Example:
```bash
python3 scripts/gh_helper.py pr merge --repo packetqc/knowledge --number 193
```

### Parameter Format Summary

| Command | `--owner` | `--repo` | Notes |
|---------|-----------|----------|-------|
| `project ensure` | `packetqc` (separate) | `knowledge` (repo name only) | Owner and repo are **separate** flags |
| `pr create` | N/A | `packetqc/knowledge` (combined) | Uses `owner/repo` format |
| `pr merge` | N/A | `packetqc/knowledge` (combined) | Uses `owner/repo` format |

**Why this matters**: The `project ensure` command uses GraphQL (which needs owner and repo separately for the `repository()` query), while `pr create/merge` use REST API (which expects the `owner/repo` path format). The inconsistency is an API-level difference — document it once, avoid errors forever.

### Token Zero-Display Compliance (v46)

All `gh_helper.py` commands read `GH_TOKEN` from the environment variable internally. The `--token` CLI flag has been **removed** — passing a token on the command line would expose it in Bash tool output (visible in session transcript). If `GH_TOKEN` is not set, all commands refuse to execute and print setup guidance.

**Rule**: Never pass tokens as CLI arguments. Environment variable is the only delivery path. This applies to `gh_helper.py` and any future scripts that call GitHub APIs.

---

## Post-Create Checklist

After `project create` completes:

| Step | Who | Action |
|------|-----|--------|
| 1 | Claude | Create GitHub Project board (if elevated) |
| 2 | Claude | Link project board to repository (if elevated) — `linkProjectV2ToRepository` |
| 3 | Claude | Commit all created files to task branch |
| 4 | Claude | Push to task branch, create PR |
| 5 | User | Enable GitHub Pages: Settings > Pages > Source: default branch, `/docs` folder |
| 6 | User | Approve PR to merge docs structure to default branch |
| 7 | User | Visit `https://packetqc.github.io/<repo-name>/` to verify |

**GitHub Pages activation** must happen once, manually in repo Settings. After that, every PR merge auto-deploys.

---

## Creating Publications

Once the project structure exists, use the standard `pub new <slug>` command to create publications:

```
pub new <slug>
```

This creates:
- Source: `publications/<slug>/v1/README.md`
- Docs EN: `docs/publications/<slug>/index.md` (summary) + `full/index.md` (complete)
- Docs FR: `docs/fr/publications/<slug>/index.md` (summary) + `full/index.md` (complete)
- Updates publications index pages (EN + FR)

The satellite's publications use the same three-tier structure as knowledge: source → summary → complete, bilingual.

---

## Relationship to Bootstrap

`project create` is the **fourth stage** of satellite integration — it builds on the three bootstrap stages:

```
Stage 1: Bootstrap      → Install knowledge pointer in CLAUDE.md
Stage 2: Normalize       → Trim to thin-wrapper
Stage 3: Healthcheck     → Verify network integration
Stage 4: Project Create  → Scaffold docs/publications/hub structure
```

Stages 1-3 are about connecting the satellite to the knowledge network. Stage 4 is about giving the satellite its own web presence — its own GitHub Pages site, its own publications, its own identity within the network.

Not every satellite needs Stage 4. Simple projects (libraries, experiments) may only need Stages 1-3. Projects that produce documentation, publications, or public-facing content need Stage 4.

---

## How Harvest Discovers Satellite Publications

Once a satellite has publications:

1. `harvest <project>` scans the satellite's `publications/` folder
2. Discovered publications are referenced in `minds/<project>.md`
3. Core can then link to satellite publications from the knowledge website
4. The satellite's publications appear in the dashboard alongside core publications

This is publication discovery — the satellite produces knowledge, harvest detects it, the network indexes it.

---

## Example: knowledge-live

```
project create "Knowledge Live"
```

Creates:
```
knowledge-live/
  docs/
    _config.yml                    ← title: "Knowledge Live", baseurl: "/knowledge-live"
    _layouts/
      default.html                 ← og:site_name: "Knowledge Live"
      publication.html             ← og:site_name: "Knowledge Live"
    index.md                       ← "# Knowledge Live" landing page
    publications/
      index.md                     ← Empty publications hub
    fr/
      index.md                     ← "# Knowledge Live" page FR
      publications/
        index.md                   ← Hub publications vide
    assets/
      og/.gitkeep                  ← Ready for webcards
  publications/
    .gitkeep                       ← Ready for source publications
```

After PR merge + GitHub Pages enable:
- `https://packetqc.github.io/knowledge-live/` — live
- `https://packetqc.github.io/knowledge-live/publications/` — ready for content

---

*Authors: Martin Paquet & Claude (Anthropic, Opus 4.6)*
