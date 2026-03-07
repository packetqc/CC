# Interactive Diagnostic — Methodology

A structured, traceable methodology for diagnosing rendering, integration, or behavioral problems through interactive collaboration between Martin and Claude. Every step is documented in real-time on the GitHub issue, creating a complete audit trail. The diagnostic session type within the [Interactive Work Sessions](interactive-work-sessions.md) framework.

## When to Use

- Web page rendering problems (Mermaid, CSS, layout, JavaScript)
- Cross-language discrepancies (EN works, FR doesn't — or vice versa)
- Build pipeline issues (Jekyll, kramdown, GitHub Pages)
- Any problem requiring iterative elimination of hypotheses

## Core Principles

| Principle | Description |
|-----------|-------------|
| **Real-time documentation** | Every message (Martin's instructions + Claude's analysis) is posted as a sequential comment on the GitHub issue |
| **Comparative analysis** | Always compare the working version against the broken version — same structure, different behavior |
| **Iterative elimination** | Systematically eliminate hypotheses one by one, documenting each result |
| **User-driven pivots** | Martin observes the actual rendered output (browser, device); Claude sees only code. When Martin redirects the investigation, follow immediately |
| **Gradual isolation** | When the cause is unclear, progressively add/remove components to isolate the breaking change |

## Protocol

### 1. Create the diagnostic task (v51)

The session issue protocol (v51) applies — every diagnostic session creates a GitHub issue **before the first file is examined**:

1. **Extract title** from the user's problem description (e.g., "Diagnostic — diagrammes des pages web")
2. **Confirm via `AskUserQuestion`** — proposed title + "Skip tracking" option
3. **Create GitHub issue** — `SESSION: <title> (YYYY-MM-DD)`, labels: `SESSION` + relevant topic labels
4. **Link to project board** — set status to "In Progress"
5. **Post verbatim first comment** — the user's exact original request, unmodified:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="20"> Martin — Demande originale (verbatim)
> <user's EXACT words, copied character for character, no reformulation>
*Ce commentaire est la demande originale intégrale de l'utilisateur, non modifiée.*
```

This issue becomes the living document of the entire investigation and the **third persistence channel** — it survives crashes, compaction, and session end independently (see `methodology/interactive-work-sessions.md`).

### 2. Document initial context

Second comment (🤖) on the issue captures Claude's initial analysis:
- URLs or file paths under investigation
- Initial observations (what works, what doesn't)
- Suspected causes (from user's domain expertise)
- Planned investigation approach

### 3. Comparative analysis — section by section

For rendering problems, compare working vs broken versions:
- Extract the relevant sections from both versions
- Post both versions as a comment (side-by-side reference)
- Analyze structural differences (syntax, encoding, characters)
- Post diagnostic results as the next comment

### 4. Systematic hypothesis elimination

Each hypothesis gets tested and documented:

| # | Hypothesis | Test | Result |
|---|-----------|------|--------|
| 1 | Different encoding | `file` command, hex dump | Eliminated / Confirmed |
| 2 | Invisible characters | Unicode scan | Eliminated / Confirmed |
| 3 | ... | ... | ... |

Post the elimination table as a comment. Each iteration is numbered (Iteration 1, Iteration 2, ...).

### 5. User pivot points

When Martin provides new observations or redirects the approach:
- Post Martin's message verbatim (quoted) as a new comment
- Summarize the key insights extracted
- Adjust the investigation direction
- Document the new approach

### 6. Gradual isolation (when needed)

When systematic elimination isn't enough:
1. Start with a minimal version (e.g., one diagram only)
2. Add components one by one
3. Test after each addition
4. Identify the exact component that breaks the system
5. Document each step as a comment

### 7. Resolution

Once the root cause is identified:
1. Document the cause on the issue (🤖 comment)
2. Propose the fix
3. Apply the fix
4. Verify the fix works
5. Post the verification result (🤖 comment)
6. Run the pre-save summary (v50) — 5-section report with metrics, time blocks, self-assessment
7. Post the closing report on the issue (v51) — delivery status table + comment history index
8. Close the issue

## Comment Structure (v51)

Each comment follows the session issue convention (v51) — alternating 🧑 user / 🤖 Claude format, posted in real-time on the session's GitHub issue:

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky.png" width="20"> Martin — <short description>
> <quoted user message — verbatim>
*<optional context>*
```

```markdown
## <img src="https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin/vicky-sunglasses.png" width="20"> Claude — <short description>
### <section — e.g., Iteration 2, Comparative Analysis>
<content — findings, hypothesis elimination, results>
```

**What counts as "significant"** for posting: initial observations, hypothesis elimination results, user pivot points, gradual isolation steps, resolution findings. Not: acknowledgements, single-word confirmations.

**At save time**: The issue comment integrity check (v51) compares session exchanges against posted comments. Any missing diagnostic iterations are posted retroactively before the pre-save summary (v50).

## Interaction Flow

```
🧑 Martin: instruction/observation → posted as issue comment
  └─ 🤖 Claude: analysis + results → posted as issue comment
      └─ 🧑 Martin: new observation/pivot → posted as issue comment
          └─ 🤖 Claude: adjusted analysis → posted as issue comment
              └─ ... (repeat until resolved)
```

## Key Rules

1. **Never skip posting** — Every meaningful exchange becomes a comment on the issue
2. **User quotes are verbatim** — Don't paraphrase Martin's messages; quote them exactly
3. **Sequential numbering** — Comments form a chronological narrative
4. **Iterations are explicit** — When the approach changes, start a new numbered iteration
5. **Trust user observations** — Martin sees the actual rendered output; Claude sees code. When they conflict, trust the observation (see Known Pitfall #20)
6. **Pause when asked** — When Martin says "pause", stop and wait for the next instruction
7. **Document before resolving** — The full interaction must be recorded before applying fixes

## Benefits

- **Traceability** — Complete audit trail of the diagnostic process
- **Knowledge preservation** — Future sessions can read the issue to understand the investigation
- **Methodology validation** — The documented approach can be replicated for similar problems
- **User visibility** — Martin can review every step at any time from the GitHub issue

## First Application

- **Issue #334** — Diagnostic sur les diagrammes des pages web (Publication #15 Architecture Diagrams)
- **Problem** — FR Mermaid diagrams render as raw text, EN version works (except Section 4)
- **Iterations** — 2 iterations of systematic elimination + gradual isolation approach
- **Comments** — 10 sequential comments documenting the full interactive session

## Related

- Publication #19 — Interactive Work Sessions
- Publication #20 — Session Metrics & Time Compilation
- `methodology/interactive-work-sessions.md` — Parent methodology
- `methodology/interactive-documentation.md` — Documentation sessions
- `methodology/interactive-conception.md` — Conception sessions
- `methodology/session-protocol.md` — Session lifecycle (v50/v51)
- `methodology/metrics-compilation.md` — Metrics compilation routine
- `methodology/time-compilation.md` — Time compilation routine
- Known Pitfall #22: AI loop ignores user's simpler fix
