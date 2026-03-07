# Web Production Pipeline — Methodology

How source markdown becomes a live web page on GitHub Pages. Operational companion to Publication #17.

> See also: `methodology/web-page-visualization.md` (post-pipeline rendering) and `methodology/web-pagination-export.md` (PDF/DOCX export)

---

## Pipeline Overview

```
Markdown source (author writes once)
    ↓ pub new (scaffold)
Three-tier split (source → summary → complete)
    ↓ front matter injection
Bilingual mirrors (EN + FR per web tier)
    ↓ Jekyll processing
Liquid → kramdown → HTML
    ↓ layout wrapping
publication.html or default.html
    ↓ client-side enhancements
Mermaid, themes, cross-references, export
    ↓ GitHub Pages deployment
Live web page (dual-theme, bilingual, exportable)
```

**Principle**: The source document is written once. Everything downstream is derived. The pipeline is deterministic — same source always produces the same output.

---

## Three-Tier Publication Structure

Each publication exists at three levels, bilingual (5 files per publication):

| Tier | Location | Purpose |
|------|----------|---------|
| **Source** | `publications/<slug>/v1/README.md` | Canonical document, English only |
| **Summary** (web) | `docs/publications/<slug>/index.md` | Quick overview, links to complete |
| **Complete** (web) | `docs/publications/<slug>/full/index.md` | Full documentation on GitHub Pages |

Bilingual: each web tier has EN + FR mirrors (`docs/fr/publications/<slug>/...`).

---

## Jekyll Processing — Three Ordered Passes

| Pass | Engine | What it does |
|------|--------|-------------|
| 1 | **Liquid** | Template processing — `{{ }}` variables, `{% %}` logic, `relative_url` filter |
| 2 | **kramdown** | Markdown → HTML — GFM dialect with `parse_block_html: true` |
| 3 | **Layout** | Wrapping — injects CSS, JS, OG tags, version banner |

**Critical**: Liquid runs first. Any `{{ }}` in markdown content (including Mermaid hexagonal nodes) is interpreted by Liquid before kramdown sees it.

---

## Front Matter Contract

Required fields for every web page:

| Field | Required by | Example |
|-------|-------------|---------|
| `layout` | Jekyll | `publication` or `default` |
| `title` | SEO, OG tags | `"Web Production Pipeline"` |
| `description` | SEO, OG tags | `"Complete production pipeline..."` |
| `permalink` | URL routing | `/publications/web-production-pipeline/` |
| `og_image` | Social sharing | `/assets/og/knowledge-system-en-cayman.gif` |

Publication pages add: `pub_id`, `version`, `date`, `keywords`.

---

## kramdown Gotchas

Operational knowledge — things that break the pipeline silently.

### 1. `<details>` blank line parsing (PR #345)

Blank lines inside `<details>` blocks cause kramdown to exit HTML block mode. `</summary>` gets escaped as `&lt;/summary&gt;`, creating cascading nesting that swallows all subsequent page content.

**Rule**: Never leave blank lines inside `<details>` blocks in Jekyll-processed markdown.

```markdown
<!-- WRONG — blank line causes kramdown to exit HTML mode -->
<details>
<summary>Title</summary>

Content here
</details>

<!-- CORRECT — no blank lines inside the block -->
<details>
<summary>Title</summary>
Content here
</details>
```

### 2. Liquid `{{ }}` stripping

Any `{{ }}` in content is interpreted by Liquid before kramdown processes it. Mermaid hexagonal nodes (`{{ }}` syntax) are silently stripped.

**Workaround**: Use `{% raw %}...{% endraw %}` around Mermaid blocks that use hexagonal nodes, or avoid `{{ }}` syntax in Mermaid diagrams.

### 3. `parse_block_html: true`

The `_config.yml` setting `parse_block_html: true` lets kramdown process markdown inside HTML blocks. This is required for `<div>` wrappers but interacts with `<details>` parsing (see gotcha #1).

---

## Exclusion Mechanisms

Not everything in source appears on the live web page:

| Layer | What is excluded | Why |
|-------|-----------------|-----|
| **CSS** | `.mermaid-source` blocks | Source preservation — visible in git, hidden on web |
| **CSS** (`@media print`) | Toolbar, language bar, webcard, navigation | Clean PDF output |
| **JavaScript** | Mermaid blocks inside `.mermaid-source` | Prevents double-rendering |
| **kramdown** | `{{ }}` in code blocks | Liquid processes before kramdown |
| **kramdown** | `</tags>` in `<details>` with blank lines | HTML block mode exits on blank line |

These exclusions are architectural — they reflect Jekyll processing chain constraints, not bugs.

---

## Pipeline Commands

| Command | Action |
|---------|--------|
| `pub new <slug>` | Scaffold new publication (source + docs EN/FR + front matter) |
| `pub sync <#>` | Sync source changes to docs web pages |
| `pub check <#>` | Validate publication structure, links, front matter |
| `normalize` | Audit full knowledge structure concordance |
| `docs check <path>` | Validate individual doc page |

---

## Related

- Publication #17 — Web Production Pipeline (full documentation)
- Issue #347 — Documentation generation session
- Issue #351 — Production rendering script creation and deployment
- `scripts/render_web_page.py` — Production rendering script (Playwright + Chromium + npm mermaid)
- `methodology/web-page-visualization.md` — Local rendering pipeline (post-pipeline)
- `methodology/web-pagination-export.md` — PDF/DOCX export pipeline
- Publication #13 — Web Pagination & Export
- Publication #16 — Web Page Visualization
