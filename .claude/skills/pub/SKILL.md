---
name: pub
description: Publication and documentation management — list, check, new, sync, doc review, docs check. Full content management skill.
user_invocable: true
---

# /pub — Publication & Documentation Management

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `pub list` — publication inventory
- `pub check <#>` / `pub check --all` — validate publication(s)
- `pub new <slug>` — scaffold new publication
- `pub sync <#>` — sync source to docs
- `doc review` / `doc review --list` / `doc review --all` — freshness review
- `docs check <path>` / `docs check --all` — validate doc page(s)

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/documentation-generation.md`, Publication #18

### Three-Tier Publication Structure

```
Source (publications/<slug>/v1/README.md)
  → Summary (docs/publications/<slug>/index.md)
  → Complete (docs/publications/<slug>/full/index.md)
```

Each tier bilingual (EN + FR).

### pub new <slug>

1. Create source: `publications/<slug>/v1/README.md`
2. Create docs EN: summary + full
3. Create docs FR: summary + full
4. Generate front matter with OG metadata
5. Create webcard placeholder
6. Register in publication index

### pub check

Validates: source exists, docs EN/FR exist, front matter complete, webcards present, links valid, language mirrors consistent.

### doc review

Reviews publication freshness against current knowledge version. Severity: 🟢 current, 🟡 minor drift, 🟠 moderate, 🔴 critical.

### docs check

Validates individual doc pages: front matter, links, language mirror, OG image.

## Notes

- Checkpoint-aware for `pub new` (multi-step scaffold)
- Webcards generated separately via `/webcard` skill
