---
name: save-protocol
description: Enforces the complete save protocol — pre-save summary (7 sections), dual file output (Gate G6), session notes + cache finalization, PR creation, merge, closing report. Every step, every session.
user_invocable: true
---

# /save-protocol — Session Save Protocol Enforcement

## When This Skill Fires

This skill MUST be invoked when:
- User types `save`
- User confirms "Save now" or "Save + close issues" in the pre-save summary popup
- Session is ending and work was produced

**The cycle is complete or it didn't happen** (Identity Principle I4). A session without a save is a session that didn't exist. A save without a pre-save summary is an incomplete save.

## The Protocol — Complete Save Sequence

### Step 0: Todo Validation

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import check_pending_todos, defer_todos_to_next_session

todos = check_pending_todos()
if todos["has_pending"]:
    # AskUserQuestion per pending todo: "Complete now" / "Defer to next session"
    # Deferred todos survive in cache — startup hook displays them next session
    defer_todos_to_next_session(["todo1", "todo2"])
```

### Step 1: Issue Comment Integrity Check

**Before the summary** — compare session exchanges against posted issue comments. Post any missing comments to fill gaps. This ensures the G7 self-assessment in the summary is accurate.

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import post_exchange
# Compare session exchanges vs posted comments, fill gaps
```

### Step 2: Pre-Save Summary (7 Sections)

```python
from scripts.session_agent import compile_pre_save_summary

summary = compile_pre_save_summary()
# Auto-passes integrity checkpoint C.1
# Validates required section markers: Résumé, Métriques, Auto-évaluation
```

#### Section 1: Résumé
1-3 sentence description of work accomplished. What was delivered, why it matters.

#### Section 2: Métriques
Compile from **GitHub PR API** (primary) or `git diff --stat` (fallback). Never estimate when API data is available.

**Single-issue session**:
```markdown
**Totals: N todos · N PRs · N files · +X −Y lines · <deliverables>**

| Catégorie | Todos | PRs | Fichiers | Lignes+ | Lignes− | Livrables |
|-----------|-------|-----|----------|---------|---------|-----------|
| 📝 Documentation | N | N | N | N | N | N méthodologies |
| ⚙️ Collatéral | N | N | N | N | N | N issues |
```

**Multi-issue session** (2+ issues worked):
```markdown
**Session totals: N issues · N todos · N PRs · N files · +X −Y lines**

| Issue | Title | Todos | PRs | Fichiers | Lignes+ | Lignes− | Livrables |
|-------|-------|-------|-----|----------|---------|---------|-----------|
| #NNN | <title> | N | N | N | N | N | <deliverables> |
```

**Data collection per PR**:
```python
resp = gh._request("GET", f"/repos/{repo}/pulls/{pr_number}")
# resp["additions"], resp["deletions"], resp["changed_files"]
```

**Category grid**: 🔍 Diagnostic · 💡 Conception · 📝 Documentation · 📋 Doc Management · ⚙️ Collatéral

#### Section 3: Temps (Time Blocks)
Compile from **issue `created_at` timestamps** (primary) or **commit timestamps** (fallback).

```markdown
**Totals: N todos · ~Xh YYmin actif · N blocs · moy ~Nmin/todo**

| # | Todo | Début | Fin | Durée | Catégorie |
|---|------|-------|-----|-------|-----------|
| **T1** | **<task>** | HH:MM | HH:MM | ~Nmin | 📝 Documentation |
```

**Time blocks**: Morning (05:00–12:00), Afternoon (12:00–18:00), Evening (18:00–23:00).

#### Section 4: Proportions temporelles

```markdown
| Tranche | Durée | % du calendrier |
|---------|-------|-----------------|
| 🤖 Machine (Claude) | ~Xh YYmin | NN% |
| 🧑 Humain (utilisateur) | ~Xh YYmin | NN% |
| 🕐 Inactif / pauses | ~Xh YYmin | NN% |
| **Total calendrier** | **~Xh YYmin** | **100%** |
```

**Rules**: Machine ≤ Calendrier. Ratio > 80% = burst session. Ratio < 20% = significant user parallel work.

#### Section 5: Équivalent entreprise

```markdown
| Catégorie entreprise | Temps entreprise | Temps Knowledge | Ratio |
|---------------------|-----------------|-----------------|-------|
| 🔨 Réalisation | N–N semaines | ~Xh (inclus) | ~Nx |
| 📝 Documentation | N–N semaines | ~Xh (inclus) | ~Nx |
| 🎓 Formation | N–N semaines | ~0h (sous-produit) | ∞ |
```

#### Section 6: Livraisons

```markdown
| Livraison | Référence | Statut |
|-----------|-----------|--------|
| PR | #N → main | ✅ merged |
| Issue | #N | ✅ closed |
| Fichiers | file1, file2 | committed |
```

#### Section 7: Auto-évaluation

| Critère | Gate | Check |
|---------|------|-------|
| Issue créé avant premier fichier? | G1 | ✅/❌ |
| Cache initialisé après issue? | G2 | ✅/❌ |
| TodoWrite utilisé? | G3 | ✅/❌ |
| Cache mis à jour par todo? | G4 | ✅/❌ |
| Commentaires temps réel sur issue? | G7 | ✅/❌ |
| TOUS les échanges postés sur l'issue? | G7 | ✅/❌ |
| Remote check stratégique? | — | ✅/❌ |
| Métriques compilées avec données API? | — | ✅/❌ |
| Proportions temporelles? | — | ✅/❌ |
| Équivalent entreprise? | — | ✅/❌ |
| README.md vérifié et mis à jour si applicable? | G8 | ✅/❌ |

### Step 3: Documentation Check (Gate G8)

```python
from scripts.session_agent import check_doc_updates_needed

doc_check = check_doc_updates_needed()
if doc_check["needs_update"]:
    # AskUserQuestion: "Update docs now" / "Skip doc updates" / "I'll update manually"
    # Check covers: README.md, CHANGELOG.md, NEWS.md, CLAUDE.md, methodology/
```

**Gate G8 — README.md is the public front page**: Every session that produces visible deliverables MUST check and update README.md before save. This is an enforcement gate, not a suggestion.

### Step 4: Decision Point

`AskUserQuestion` with the **complete workflow visible in each label**:
- **"Save (pre-save summary + doc updates + session notes + cache + commit + push + PR + merge)"**
- **"Save + close issues (same + issue close + post-close comment)"**
- **"Continue working"**

Never use abbreviated labels like "Save minimal" — they hide steps and break informed consent.

### Step 5: Mechanical Save

```python
from scripts.session_agent import save_session

result = save_session(pre_save_summary=summary, branch="...", close_issue=True)
```

The mechanical save executes these sub-steps in order:

#### 5.0: Strategic Remote Check
```bash
git fetch origin <default-branch>
git diff origin/<default-branch>..HEAD -- <files>
# Merge if diverged
```

#### 5.1: Generate Session Notes (markdown)
```python
from scripts.session_agent import generate_session_notes
notes_path = generate_session_notes()
# Converts runtime cache (JSON) → markdown notes (session-YYYY-MM-DD-*.md)
# This feeds generate_sessions.py → sessions.json → Session Viewer (I1)
```

**Gate G5**: If `generate_session_notes()` returns `None`, write notes manually. Never proceed without a notes file.

#### 5.2: Post Session Notes on Issue
Post the full content of the generated notes as a comment on the session issue:
```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — Session notes
<full content of notes/session-YYYY-MM-DD-*.md>
```

#### 5.3: Finalize Runtime Cache
```python
from scripts.session_agent import update_session_data
update_session_data('session_phase', 'complete')
update_session_data('work_summary', '<final summary>')
```

#### 5.4: Gate G6 — Dual File Output Verification
Verify BOTH files exist before committing:
- `notes/session-YYYY-MM-DD-*.md` — session notes for web pipeline
- `notes/session-runtime-*.json` — runtime cache for session continuity

**If either is missing, generate it. Both files MUST be in the commit.**

#### 5.5: Regenerate sessions.json (core repo only)
```bash
python3 scripts/generate_sessions.py
```
Non-negotiable on core repo — updates Session Viewer (I1) data. Passes integrity checkpoint C.4.

#### 5.5b: Compile tasks.json (core repo only)
```bash
python3 scripts/compile_tasks.py
```
Non-negotiable on core repo — updates Tasks Workflow Viewer (I3) data. Passes integrity checkpoint C.5. Deduplicates by `issue_number`, keeps most recent `updated_at`.

#### 5.6: Commit
```bash
git add notes/session-*.md notes/session-runtime-*.json docs/data/sessions.json docs/data/tasks.json <other files>
git commit -m "docs: session save — <title>"
```

#### 5.7: Push
```bash
git push -u origin <task-branch>
```

#### 5.8: Create PR
Via `gh_helper.py` targeting default branch. Include `Closes #N` for auto-close.

#### 5.9: Merge (Elevated) or Guide (Semi-auto)
- **Elevated**: `gh_helper.py pr_merge()` — no pause, no waiting
- **Semi-auto**: Print manual PR URL, `⏸` guidance block

#### 5.10: Post-Save Closing Report
After PR merge, post delivery status + complete comment history index:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — Rapport de clôture

### Statut final
| Élément | Statut |
|---------|--------|
| PR #NNN — <title> | ✅ fusionné |
| Issue #NNN | ✅ fermée |
| Session notes | ✅ posted (comment #N) |
| CHANGELOG.md | ✅ updated |

### Historique complet du billet (N commentaires)
| # | Type | Contenu |
|---|------|---------|
| 1 | <img src=".../vicky.png" width="16"> | Demande originale (verbatim) |
| 2 | <img src=".../vicky-sunglasses.png" width="16"> | Analyse et plan |
| ... | ... | ... |
| N | <img src=".../vicky-sunglasses.png" width="16"> | **Ce rapport de clôture** |
```

#### 5.11: Close Issue
Auto-closed via `Closes #N` in PR, or manual close.

#### 5.12: Post-Close Final Comment
**After the issue is closed**, post one last comment confirming closure. The issue is never "done" until this post-close comment exists.

## Two Persistence Systems — Notes vs Cache

| System | File Pattern | Written When | Consumer | Purpose |
|--------|-------------|-------------|----------|---------|
| **Session notes** (markdown) | `notes/session-YYYY-MM-DD-*.md` | At save time | `generate_sessions.py` → Session Viewer (I1) | Human-readable session record |
| **Runtime cache** (JSON) | `notes/session-runtime-*.json` | During work (real-time) | Startup hook, crash recovery | Machine-readable operational state |

**The cache does NOT replace notes.** Both serve different consumers. Both MUST exist (Gate G6).

## Identity Principles in Save

- **I1 (protocol non-negotiable)**: A 5-minute session gets the same save as a 5-hour session
- **I3 (rigor over convenience)**: All 7 summary sections compiled, all sub-steps executed
- **I4 (cycle complete)**: All C-section integrity checkpoints must resolve before session ends
- **I5 (self-correction)**: If tempted to skip the pre-save summary — stop, that's protocol erosion

## Violation Recovery

If a gate was missed (detected at save time via auto-évaluation):
- Missing files → generate them now
- Missing comments → post them retroactively
- Missing cache updates → write them now
- **Never proceed to commit with known gate violations**

## Notes

- Import all functions from `scripts.session_agent`
- The pre-save summary is also posted as the final comment on the session issue
- Checkpoint at each step boundary — `resume` recovers if session crashes mid-save
- CHANGELOG.md is distinct from NEWS.md — CHANGELOG is factual audit trail, NEWS is editorial
- If PR creation fails, print manual URL and continue — the push is what matters
- Session language applies to summary labels (French sessions get French labels)
- **G7 timing during save**: The save sequence may take >5 min. The PreToolUse hook has exceptions for `*/notes/session-runtime-*` and `*/notes/checkpoint.json`, but regular files (e.g., `docs/data/sessions.json`) are not excepted. Call `post_exchange()` before long sub-steps to keep G7 satisfied. `save_session()` handles this internally when available.
- **Pre-save summary validation** (v59.3): `compile_pre_save_summary()` validates that required section markers (Résumé, Métriques, Auto-évaluation) are present. A minimal string passed to `save_session()` will fail this validation.
