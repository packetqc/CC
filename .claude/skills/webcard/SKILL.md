---
name: webcard
description: Animated OG social preview generation and GitHub Pages URL management — webcards, weblinks, weblinks --admin.
user_invocable: true
---

# /webcard — Webcards & Web Links

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `webcard <target>` — generate animated OG GIFs
- `weblinks` — print all GitHub Pages URLs
- `weblinks --admin` — URLs with conformity status

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/web-production-pipeline.md`, Publication #5

### Webcard Generation

1200×630 animated GIF, dual-theme (Cayman light + Midnight dark).
Generator: `scripts/generate_og_gifs.py`

Six animation types: corporate, diagram, split-panel, cartoon, index.
Assets: portrait (`references/Martin/me3.JPG`), Vicky avatar (`references/Martin/vicky.png`).

### Targets

- `webcard <slug>` — single page
- `webcard <group>` — all pages in group (publications, interfaces, profiles)
- `webcard <#>` — publication by number

### weblinks

Print all GitHub Pages URLs as code block. `--admin` adds conformity status per link.

## Notes

- Content-specific animations based on page type
- Dual-theme ensures visibility on both light and dark backgrounds
