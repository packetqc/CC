---
name: pub-export
description: Export publications to PDF or DOCX using browser-native CSS Paged Media and client-side HTML-to-Word.
user_invocable: true
---

# /pub-export — Publication Export

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `pub export <#> --pdf` — export to PDF
- `pub export <#> --docx` — export to DOCX

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/web-pagination-export.md`, Publication #13

### PDF Export

Uses Playwright + Chromium with CSS `@page` rules:
1. Render the publication HTML
2. Apply print-specific CSS (page breaks, margins, headers/footers)
3. Generate PDF via Chromium's print-to-PDF

### DOCX Export

Client-side HTML-to-Word conversion:
1. Render publication HTML
2. Convert Mermaid diagrams to images (Mermaid not supported in Word)
3. Generate DOCX with proper styling

### Common Pipeline

- No language panel in export (filtered out)
- Webcard not displayed in export
- Same `publication.html` layout as web version

## Notes

- Playwright + Chromium must be pre-installed
- Mermaid-to-image rendering via `scripts/render_web_page.py`
- Export filenames follow publication slug convention
