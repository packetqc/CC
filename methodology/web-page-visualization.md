# Web Page Visualization — Methodology

A local, self-contained pipeline for rendering web pages and Mermaid diagrams as images. No external services, no CDN, no API calls at runtime. Security-by-design compliant.

## When to Use

- **Diagnostic sessions** — Show the user how a web page actually renders (Mermaid diagrams, layout, CSS)
- **Design reviews** — Visual comparison of EN/FR page variants, before/after changes
- **DOCX export pipeline** — Convert Mermaid diagrams to images for Word documents (Mermaid is not supported in DOCX)
- **Documentation** — Generate page screenshots for publications, README files, or issue comments
- **Visual validation** — Verify rendering after changes without requiring the user to check in a browser

## Architecture

```
urllib (fetch HTML) → self-contained HTML → Playwright + Chromium → npm mermaid → screenshots
```

| Component | Role | Location | External? |
|-----------|------|----------|-----------|
| **urllib** | Fetch live page HTML | Python stdlib | No — bypasses container proxy via direct socket |
| **Playwright** | Headless browser automation | Python package (pre-installed) | No — local package |
| **Chromium** | DOM rendering engine | `/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome` | No — pre-installed binary |
| **npm mermaid** | Mermaid diagram rendering | `/tmp/mermaid-local-test/node_modules/mermaid/dist/mermaid.min.js` | No — local npm package |

**Zero network calls at rendering time.** The only network call is the initial HTML fetch via urllib (optional — can also render from local markdown files).

## Prerequisites

### Pre-installed (Claude Code environment)
- Python 3.11+ with `playwright` package
- Chromium binary in Playwright cache (`/root/.cache/ms-playwright/chromium-1194/`)

### Installed at session start
- npm `mermaid` package — install once per session:
  ```bash
  mkdir -p /tmp/mermaid-local-test && cd /tmp/mermaid-local-test && npm init -y --silent && npm install mermaid
  ```

### Environment startup automation (recommended)
When the user configures the Claude Code environment (VM/container), these can be pre-installed:
- `npm install mermaid` in a known location
- Token (GH_TOKEN) for GitHub API access

## Production Script

`scripts/render_web_page.py` — CLI tool implementing both pipelines. Knowledge asset synced to satellites via wakeup step 5.

```bash
# Full page screenshot (with Mermaid rendering)
python3 scripts/render_web_page.py --url https://packetqc.github.io/knowledge/publications/architecture-diagrams/full/

# Single Mermaid diagram to PNG
python3 scripts/render_web_page.py --mermaid diagram.mmd --output diagram.png

# Single Mermaid diagram to SVG
python3 scripts/render_web_page.py --mermaid diagram.mmd --output diagram.svg

# Batch: render all .mmd files in a directory
python3 scripts/render_web_page.py --mermaid-dir diagrams/ --output-dir rendered/
```

## Pipeline 1: Full Page Visualization

Render a complete web page as the user sees it, with all Mermaid diagrams rendered.

### Steps

1. **Fetch HTML** — via `urllib.request` (bypasses proxy, returns raw HTML)
2. **Extract body content** — strip external CSS/JS references that would hang in the container
3. **Build self-contained HTML** — inject GitHub-like CSS styling inline
4. **Launch Playwright** — Chromium with `--no-sandbox`, `--disable-gpu`
5. **Inject mermaid.js** — via `page.add_script_tag(path=...)` from local npm package
6. **Render Mermaid blocks** — programmatically convert `<code class="language-mermaid">` to SVG
7. **Capture screenshots** — full-page or viewport-by-viewport

### Code Pattern

```python
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.request

MERMAID_JS = "/tmp/mermaid-local-test/node_modules/mermaid/dist/mermaid.min.js"
CHROME = "/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome"

async def render_web_page(url, output_dir="/tmp"):
    """Render a web page with Mermaid diagrams as screenshots."""

    # 1. Fetch HTML
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    # 2. Extract body
    body_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
    body = body_match.group(1) if body_match else html

    # 3. Self-contained HTML with GitHub-like styling
    self_contained = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       max-width: 980px; margin: 0 auto; padding: 20px; line-height: 1.5; color: #24292f; }}
h1, h2 {{ border-bottom: 1px solid #d0d7de; padding-bottom: .3em; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #d0d7de; padding: 6px 13px; }}
th {{ background: #f6f8fa; font-weight: 600; }}
code {{ background: #f6f8fa; padding: 2px 6px; border-radius: 3px; font-size: 85%; }}
pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }}
.mermaid {{ text-align: center; margin: 16px 0; }}
blockquote {{ border-left: 4px solid #d0d7de; padding: 0 16px; color: #57606a; }}
</style>
</head><body>{body}</body></html>"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=CHROME,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # 4-5. Load page and inject mermaid.js
        await page.goto("about:blank")
        await page.add_script_tag(path=MERMAID_JS)
        await page.evaluate("""(html) => {
            document.open(); document.write(html); document.close();
        }""", self_contained)
        await page.wait_for_timeout(2000)

        # 6. Render Mermaid blocks
        result = await page.evaluate("""async () => {
            mermaid.initialize({startOnLoad: false, theme: 'default', securityLevel: 'loose'});
            const blocks = document.querySelectorAll('code.language-mermaid');
            let ok = 0, fail = 0;
            for (let i = 0; i < blocks.length; i++) {
                try {
                    const { svg } = await mermaid.render('mmd-' + i, blocks[i].textContent);
                    const div = document.createElement('div');
                    div.className = 'mermaid';
                    div.innerHTML = svg;
                    blocks[i].parentElement.replaceWith(div);
                    ok++;
                } catch(e) { fail++; }
            }
            return {total: blocks.length, ok, fail};
        }""")

        # 7. Screenshots
        await page.screenshot(path=f"{output_dir}/page-full.png", full_page=True)

        height = await page.evaluate("document.body.scrollHeight")
        pages = (height + 899) // 900
        for i in range(pages):
            await page.evaluate(f"window.scrollTo(0, {i * 900})")
            await page.wait_for_timeout(200)
            await page.screenshot(path=f"{output_dir}/page-{i+1}.png")

        await browser.close()
        return result
```

## Pipeline 2: Mermaid Diagram to Image

Render individual Mermaid diagrams as SVG or PNG with transparent background.

### Code Pattern

```python
async def render_mermaid_to_image(diagram_code, output_path, format="png"):
    """Render a single Mermaid diagram to SVG or PNG."""

    with open(MERMAID_JS, "r") as f:
        mermaid_js_content = f.read()

    html = f"""<!DOCTYPE html>
<html><head><script>{mermaid_js_content}</script>
<style>body {{ background: transparent; margin: 0; }}</style>
</head><body>
<div id="target"></div>
<div id="result" style="display:none"></div>
<script>
mermaid.initialize({{startOnLoad: false, theme: 'default', securityLevel: 'loose'}});
async function render() {{
    try {{
        const {{ svg }} = await mermaid.render('diagram', `{diagram_code}`);
        document.getElementById('target').innerHTML = svg;
        document.getElementById('result').textContent = 'OK';
    }} catch(e) {{
        document.getElementById('result').textContent = 'ERROR: ' + e.message;
    }}
}}
render();
</script>
</body></html>"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROME,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
        )
        page = await browser.new_page()
        await page.set_content(html)
        await page.wait_for_timeout(3000)

        result = await page.evaluate("document.getElementById('result').textContent")
        if result == 'OK':
            if format == "svg":
                svg = await page.evaluate("document.querySelector('#target svg').outerHTML")
                with open(output_path, "w") as f:
                    f.write(svg)
            else:  # png
                target = page.locator('#target svg')
                await target.screenshot(path=output_path, type="png")

        await browser.close()
        return result == 'OK'
```

## Constraints and Limitations

| Constraint | Impact | Workaround |
|-----------|--------|------------|
| **Proxy blocks `page.goto()` to external URLs** | Cannot navigate directly to GitHub Pages | Fetch HTML via urllib first, then load locally |
| **External CSS/JS references hang** | Page load timeouts if CDN resources referenced | Build self-contained HTML, strip external refs |
| **Chromium version mismatch** | Playwright 1.58.0 expects newer binary | Use `executable_path` to point to existing binary |
| **Large inline scripts timeout `set_content()`** | Mermaid.js is ~3MB, too large for inline injection | Use `page.add_script_tag(path=...)` or `page.goto("about:blank")` first |
| **Liquid `{{}}` conflict** | Mermaid hexagonal nodes stripped by Jekyll | Local rendering avoids Liquid entirely — diagrams render from source markdown |
| **kramdown `<details>` blank line gotcha** | Blank lines inside `<details>` blocks cause kramdown to exit HTML block mode — `</summary>` gets escaped as `&lt;/summary&gt;`, creating cascading nesting that swallows page content (PR #345) | Never leave blank lines inside `<details>` blocks in Jekyll-processed markdown. See `methodology/web-production-pipeline.md` for full kramdown gotchas |

## Key Discoveries (session 2026-02-26)

1. **Playwright + Chromium is pre-installed** in Claude Code environment but version-mismatched. Using `executable_path` to the existing binary bypasses the mismatch.

2. **npm mermaid works locally** when given a real DOM (Chromium). Previous attempt with jsdom failed because jsdom doesn't implement SVG DOM methods (`getBBox`). Chromium provides a complete DOM.

3. **urllib bypasses the container proxy** (Python opens direct sockets). This is the same mechanism `gh_helper.py` uses for GitHub API calls.

4. **Self-contained HTML is the key** — stripping external CSS/JS references and injecting content inline avoids the proxy blocking external resources.

5. **mermaid.ink was validated but excluded** — works as an external API but violates security-by-design (autosuffisant principle). The local npm approach is equivalent in capability.

## Validation Results

| Test | Result | Details |
|------|--------|---------|
| Simple Mermaid (graph TB) | OK | SVG 9.9 KB |
| Complex Mermaid (flowchart TD, 12 nodes, emojis) | OK | SVG 154 KB, PNG 55 KB |
| Full page (14 diagrams, FR) | 13/14 OK | 1 failed due to `{{}}` in source — not a rendering issue |
| Full page screenshot | OK | 18,080px height, 2.5 MB PNG |
| Viewport captures | OK | 10 pages at 1280×900 |

## Mermaid Source Preservation Principle

When Mermaid diagrams are pre-rendered to PNG images (for dual-theme support, faster loading, or export compatibility), the **original Mermaid source must be preserved** in the same page alongside the rendered image.

**Why this matters**:

| Concern | Without source | With source |
|---------|---------------|-------------|
| **Maintainability** | Cannot update diagram — must redraw from scratch | Edit source, re-render |
| **AI assimilation** | Claude sees only pixels — no semantic understanding | Claude reads Mermaid source and understands the architecture |
| **Documentation chain** | Broken — the source was the only place the diagram definition existed | Complete — source travels with the rendered output |
| **Multi-recipe reuse** | Cannot generate different formats (SVG, PDF, different themes) | Source feeds any rendering pipeline |

**Implementation**: Use HTML `<details class="mermaid-source">` collapsible sections to keep source in the git markdown while excluding it from web rendering:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagram-midnight.png">
  <img src="diagram-cayman.png" alt="Diagram" style="max-width:100%;height:auto;">
</picture>

<details class="mermaid-source">
<summary>Mermaid source</summary>

```mermaid
graph TB
    A --> B
```

</details>
```

**Rules**:
1. Every pre-rendered diagram MUST retain its Mermaid source in a `<details class="mermaid-source">` block immediately after the `<picture>` element
2. The `<details>` summary is "Mermaid source" (EN) or "Source Mermaid" (FR)
3. The source block uses standard ` ```mermaid ` fencing — GitHub renders it on source view if the `<details>` is opened
4. When updating a diagram, edit the Mermaid source first, then re-render the PNG
5. The Mermaid source is the **single source of truth** — the PNG is a derived artifact

**Rendering pipeline**: Mermaid source → Playwright + Chromium + npm mermaid → PNG (Cayman + Midnight themes) → `<picture>` dual-theme display. The source block in `<details>` is the input to this pipeline.

### Web Pipeline Exclusion

The `<details class="mermaid-source">` blocks are **excluded from web page rendering** (Jekyll/GitHub Pages). This is critical — without exclusion, the Mermaid fenced code blocks inside `<details>` are processed by kramdown into `<code class="language-mermaid">` elements, which the layout's `mermaid.js` then attempts to render. This causes:

1. **Double rendering** — mermaid.js tries to render diagrams that already exist as pre-rendered PNGs
2. **Parse errors** — some Mermaid syntax works in standalone rendering but fails in the live mermaid.js parser, causing cascade failures that can break ALL diagrams on the page
3. **Export contamination** — PDF and DOCX export pipelines pick up the raw Mermaid blocks, producing broken output

**Exclusion mechanism** (two layers of defense):

| Layer | What it does | Where |
|-------|-------------|-------|
| **CSS** | `display: none !important` on `.mermaid-source` | Both layouts (`publication.html`, `default.html`) |
| **JS** | `if (el.closest('.mermaid-source')) return;` skips blocks inside `.mermaid-source` | `renderMermaid()` function in both layouts |

The CSS layer hides the `<details>` blocks from the rendered page. The JS layer prevents mermaid.js from processing any `language-mermaid` code blocks that happen to be inside a `.mermaid-source` container — defense in depth in case CSS is stripped or delayed.

**Where the source IS visible**:

| Context | Visible? | Why |
|---------|----------|-----|
| **GitHub source view** (markdown) | Yes | GitHub renders `<details>` natively — click to expand |
| **Git diff / PR review** | Yes | Raw markdown shows the full source |
| **Claude / AI reading** | Yes | The markdown source file contains the Mermaid code |
| **GitHub Pages web** | No | CSS hides `.mermaid-source`, JS skips rendering |
| **PDF export** | No | `@media print` rule + elements are `display: none` |
| **DOCX export** | No | Export strips hidden elements |

**Convention for future pages**: Any page that uses pre-rendered Mermaid PNGs with preserved source MUST use `class="mermaid-source"` on the `<details>` wrapper. Without the class, the Mermaid source will be processed by mermaid.js and cause rendering conflicts.

## Related

- Issue #335 — Feature design and implementation tracking
- Issue #334 — Origin diagnostic session (Mermaid FR rendering)
- Issue #347 — Publication #17 documentation generation
- Issue #351 — Production rendering script creation and deployment
- `methodology/interactive-diagnostic.md` — Diagnostic methodology used during discovery
- `methodology/web-pagination-export.md` — PDF/DOCX export pipeline (integration target)
- `methodology/web-production-pipeline.md` — Jekyll production pipeline (source → web page)
- Publication #13 — Web Pagination & Export
- Publication #15 — Architecture Diagrams (test subject)
- Publication #16 — Web Page Visualization (this methodology's publication)
- Publication #17 — Web Production Pipeline (Jekyll processing chain, exclusion mechanisms)

## First Application

- **Issue #334** — Diagnostic sur les diagrammes des pages web (Publication #15 Architecture Diagrams)
- **Discovery** — While exploring whether Claude could show the user a rendered web page
- **Validation** — FR Architecture Diagrams page, 14 Mermaid diagrams, full page rendering confirmed by user
- **User confirmation** — "ca semble fonctionner le visual d'une page web"
