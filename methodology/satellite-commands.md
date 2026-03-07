# Satellite Commands Template
<!-- template-version: v54 -->

This file is the **canonical source** for the commands section of satellite CLAUDE.md files.
On wakeup, if a satellite detects version drift, it reads this file and injects the commands
section into its own CLAUDE.md — replacing the old commands section and updating the version tag.

**How it works**: The content between `<!-- BEGIN COMMANDS -->` and `<!-- END COMMANDS -->` markers
is extracted and injected into the satellite's CLAUDE.md between `## Commands (from Knowledge)`
and the next `---` separator. The version tag is updated to match `template-version` above.

**When to update this file**: Every time a command is added, removed, or renamed in core CLAUDE.md.
Keep this file in sync with the commands reference in `methodology/satellite-bootstrap.md`.

---

<!-- BEGIN COMMANDS -->
## Commands (from Knowledge)

Full command details and implementation come from core on wakeup (Step 0).
The `help` command outputs these 8 groups with publication links.

### Critical Behavioral Rules

- **`gh_helper.py` is the ONLY working API method** — `gh` CLI is NOT installed in Claude Code containers. `curl` to `api.github.com` is blocked by the proxy (strips auth headers, returns 401). Only Python `urllib` (used by `scripts/gh_helper.py`) bypasses the proxy. For ALL GitHub API operations (PR create, merge, branch ops): use `gh_helper.py` with `GH_TOKEN` env var.
- **Plan mode wakeup** — When session starts in plan mode, Bash/Edit/Write are blocked. Auto-wakeup MUST still run using read-only tools: WebFetch for Step 0 (sunglasses), Read for notes/CLAUDE.md, text output for help. Skip write steps (bootstrap, self-heal, asset sync). Run deferred write steps after plan approval. Without this adaptation, the satellite gets no sunglasses and behaves like an NPC.
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
| `harvest --stage <N> <type>` | Stage for integration (lesson, pattern, methodology, evolution, docs) |
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
| `project create <name>` | Full creation: register P# + scaffold + GitHub Project (elevated, linked to repo) |
| `project register <name>` | Register project with P# ID in core |
| `project review <P#>` | Review project state — docs, pubs, assets, freshness |
| `project review --all` | Review all projects |
| `#N: <content>` | Scoped note — `#` call alias routes to project N |
| `#N:methodology:<topic>` | Methodology insight — flagged for harvesting |
| `#N:principle:<topic>` | Design principle — flagged for harvesting |
| `#N:info` | Show accumulated knowledge for #N |
| `#N:done` | End documentation focus, compile summary |
| `g:<board>:<item>` | Reference a GitHub board item by position |
| `g:<board>:<item>:done` | Mark board item as Done (compilation trigger) |
| `g:<board>:<item>:progress` | Move board item to In Progress |
| `g:<board>:<item>:info` | Detailed board item view |
| `<cmd> ?` | Contextual help for any project command |

**Live Session** — [#2 Live Session Analysis](https://packetqc.github.io/knowledge/publications/live-session-analysis/)

| Command | Action |
|---------|--------|
| `I'm live` | Pull latest clip, report UI state |
| `multi-live` | Monitor multiple streams |
| `recipe` | Print capture quick recipe |

**Visuals** — [#22 Visual Documentation](https://packetqc.github.io/knowledge/publications/visual-documentation/)

| Command | Action |
|---------|--------|
| `visual <path>` | Extract evidence frames from video (default: detection mode) |
| `visual <path> --detect` | Scan video for significant frames automatically |
| `visual <path> --timestamps 10 30 60` | Extract frames at specific seconds |
| `visual --repo owner/repo --file path` | Fetch and process video from GitHub repo |
| `visual <path> --report --sheet --dedup` | Full pipeline: detect + dedup + report + contact sheet |
| `deep <desc>` | Frame-by-frame anomaly analysis |
| `analyze <path>` | Static video analysis |

**Live Network** — [#10 Live Knowledge Network](https://packetqc.github.io/knowledge/publications/live-knowledge-network/)

| Command | Action |
|---------|--------|
| `beacon` | Knowledge beacon status and peer discovery |
<!-- END COMMANDS -->
