# Engineering Taxonomy — Stages, Request Types & Industry Alignment

This document defines the two core taxonomies used across the knowledge system:
the **Engineering Cycle Stages** (lifecycle state machine) and the **Request Type
Taxonomy** (work classification). Both are aligned with established industry
frameworks and mapped to GitHub labels, Conventional Commits, and platform tooling.

---

## Engineering Cycle Stages

10 sequential stages + 1 cross-cutting concern. Every piece of work moves
through this lifecycle. The state machine supports forward transitions (normal
progression), backward transitions (rework/iteration), and stage skipping.

### Stage Definitions

| # | Stage | Description | GitHub Label Color |
|---|-------|-------------|--------------------|
| 0 | `analysis` | Requirements gathering, stakeholder needs, investigation, problem definition | `#6366f1` (indigo) |
| 1 | `planning` | Sprint/iteration planning, task breakdown, work estimation, scheduling | `#8b5cf6` (violet) |
| 2 | `design` | Architecture, system design, detailed design, solution conception, prototyping | `#a855f7` (purple) |
| 3 | `implementation` | Coding, building, integration of components | `#3b82f6` (blue) |
| 4 | `testing` | Unit tests, integration tests, system tests, automated QA — **"did we build it right?"** (verification) | `#f59e0b` (amber) |
| 5 | `validation` | User acceptance, stakeholder review, demo — **"did we build the right thing?"** (acceptance) | `#eab308` (yellow) |
| 6 | `review` | Code review, PR review, peer inspection, approval gates | `#10b981` (emerald) |
| 7 | `deployment` | Release preparation, staging, production push, delivery | `#f97316` (orange) |
| 8 | `operations` | Production runtime, monitoring, incident response, feedback loop | `#ef4444` (red) |
| 9 | `improvement` | Retrospective, lessons learned, optimization, rework trigger | `#06b6d4` (cyan) |

### Cross-Cutting Concern

| Concern | Description |
|---------|-------------|
| `documentation` | Generated as a byproduct at all stages — not a sequential phase. Matches ISO/IEC 12207 model where documentation is a supporting process that runs alongside every lifecycle process. |

### Industry Framework Cross-Reference

| Stage | Classical SDLC | Agile/Scrum | DevOps CI/CD | ITIL v4 | SAFe | GitHub Flow | ISO 12207 | V-Model |
|-------|---------------|-------------|--------------|---------|------|-------------|-----------|---------|
| `analysis` | Requirements Analysis | Backlog Refinement | Plan | Service Strategy | Strategic Themes | — | Stakeholder Needs + Req Analysis | Requirements Analysis |
| `planning` | (implicit) | Sprint Planning | Plan | Service Strategy | PI Planning (scheduling) | Create Branch | — | (implicit) |
| `design` | System Design | (within Sprint) | — | Service Design | PI Planning (feature design) | — | Architecture + Detailed Design | System + Architecture + Detailed Design |
| `implementation` | Implementation | Sprint Execution | Code + Build | — | Iteration Execution | Develop (Commits) | Implementation + Integration | Implementation |
| `testing` | Integration & Testing | Sprint Execution (TDD) | Test | Service Transition | Iteration Testing | CI Checks | **Verification** | Unit + Component + Integration + System |
| `validation` | (within Testing) | Sprint Review | — | — | System Demo + I&A | Review & Discuss | **Validation** | Acceptance Testing |
| `review` | — | Sprint Review | — | — | System Demo | **PR Review + Merge** | — | — |
| `deployment` | Deployment | Release | Release + Deploy | Service Transition | Release on Demand | Deploy | Transition | — |
| `operations` | Maintenance | — | Operate + Monitor | Service Operation | — | — | Operation + Maintenance | — |
| `improvement` | — | **Retrospective** | Monitor (feedback) | **Continual Improvement** | **Inspect & Adapt** | — | Maintenance (perfective) | — |
| `documentation` | Per phase artifact | Definition of Done | — | Per phase artifact | — | In PR body | **Cross-cutting process** | Per phase artifact |

### Key Design Decisions

**Why `design` replaces `conception`**: Every international framework uses "design" (system design,
architecture design, detailed design). The French `conception` maps naturally to `design` in
international standards. The GitHub label `design` is universally understood.

**Why `testing` ≠ `validation`**: ISO 12207 and V-Model make the sharpest distinction.
Testing (verification) confirms the build matches specifications — automated, repeatable.
Validation confirms the product meets stakeholder needs — human, subjective. In practice:
`testing` = Claude runs tests; `validation` = Martin reviews the actual rendered result.

**Why `review` is separate from `validation`**: Review is a process gate (code review, PR approval).
Validation is a product gate (does this solve the user's problem?). A PR can pass code review
but fail user validation — different failure modes.

**Why `documentation` is cross-cutting**: Making it a phase creates the enterprise antipattern
where documentation is "at the end" — always deferred, never completed. As a cross-cutting
concern, it can be active alongside any stage.

**Why `improvement` replaces `production`/`maintenance`**: Traditional "maintenance" is passive.
The consolidated stage absorbs Agile retrospectives, DevOps monitoring feedback, ITIL continual
improvement, and SAFe Inspect & Adapt — the active loop back to analysis.

### Backward Transitions (Rework Loops)

The lifecycle is not strictly sequential. Common rework paths:

```
validation → design        (user rejects approach — redesign needed)
testing → implementation   (tests fail — fix the code)
review → implementation    (PR rejected — rework needed)
validation → analysis      (stakeholder needs changed — re-analyze)
operations → improvement   (production issue — retrospective)
improvement → analysis     (lesson learned feeds next cycle)
deployment → testing       (staging failure — retest)
```

---

## Request Type Taxonomy

11 types covering all development activities. Each type maps to a GitHub issue
label, one or more Conventional Commit types, an SDLC phase, and an ITIL category.

### Type Definitions

| # | Type | Nature | Keywords (EN) | Keywords (FR) |
|---|------|--------|---------------|---------------|
| 1 | `fix` | Repair | fix, bug, broken, error, crash, fail, wrong, repair, correct, patch, hotfix | résoudre, corriger, bogue, réparer |
| 2 | `feature` | Build | add, create, new, implement, build, feature, scaffold, introduce, enable | ajouter, créer, nouveau, implémenter, construire |
| 3 | `investigation` | Investigate | investigate, diagnose, analyze, root cause, why, troubleshoot, debug, trace, probe | diagnostiquer, analyser, pourquoi, enquêter |
| 4 | `enhancement` | Improve | refactor, optimize, simplify, restructure, reorganize, improve, upgrade, modernize, clean, performance | refactoriser, nettoyer, optimiser, améliorer |
| 5 | `testing` | Verify | test, qa, unit test, integration test, assert, coverage, regression, smoke test | tester |
| 6 | `validation` | Accept | validate, validation, verify, acceptance, check, confirm, approve, sign off, demo | valider, vérifier, confirmer, approuver |
| 7 | `documentation` | Document | document, doc, write, describe, readme, publication, wiki, changelog, guide | documenter, décrire, rédiger |
| 8 | `deployment` | Deliver | deploy, release, push, ship, publish, deliver, merge, ci/cd, pipeline | déployer, publier, livrer |
| 9 | `conception` | Design | design, architect, conceive, prototype, wireframe, blueprint, spike, rfc, proposal, plan | conception, concevoir, architecturer, planifier |
| 10 | `review` | Assess | review, audit, assess, evaluate, inspect, survey, examine, peer review | réviser, auditer, évaluer, inspecter |
| 11 | `chore` | Sustain | chore, housekeeping, cleanup, maintenance, routine, admin, config, setup, infrastructure | ménage, entretien, configuration |

### Industry Alignment Matrix

| Type | Conventional Commit | SDLC Phase | ITIL Category | Agile Work Item |
|------|-------------------|------------|---------------|-----------------|
| `fix` | `fix` | Maintenance | Incident | Bug |
| `feature` | `feat` | Implementation | Change Request | User Story |
| `investigation` | — | Requirements/Analysis | Problem | Spike |
| `enhancement` | `refactor`, `perf` | Maintenance | Change Request | Task (improvement) |
| `testing` | `test` | Testing | — | Task (QA) |
| `validation` | — | Validation (ISO 12207) | — | Sprint Review |
| `documentation` | `docs` | Cross-cutting (ISO 12207) | — | Task (docs) |
| `deployment` | `build`, `ci` | Deployment | — | Task (DevOps) |
| `conception` | — | Planning + Design | — | Spike / Epic |
| `review` | — | Cross-cutting | — | Sprint Review |
| `chore` | `chore` | Maintenance | Service Request | Task (housekeeping) |

### Key Changes from Previous Taxonomy (8 types → 11 types)

| Previous | Current | Change |
|----------|---------|--------|
| `troubleshooting` | `investigation` | Renamed — ITIL Problem terminology. Diagnostic part split from fix-it part. |
| `refactor` | `enhancement` | Broadened — includes optimize, upgrade, modernize, not just structural refactoring. |
| — | `validation` | **Added** — distinct from testing: user acceptance vs automated verification. |
| — | `conception` | **Added** — design work, architecture, prototyping, spikes. |
| — | `chore` | **Added** — ITIL Service Request, Conventional Commits `chore`, housekeeping. |

---

## GitHub Label Deployment

Both taxonomies are deployed as GitHub labels on every knowledge system repository.

**Engineering stage labels** (mutually exclusive on issues — only one active at a time):
- Deployed via `gh_helper.py engineering_labels_setup(repo)`
- Synced on stage transitions via `session_agent.py sync_engineering_stage_label()`
- Old stage label removed, new one added — atomic swap

**Request type labels** (can coexist — an issue may have multiple types):
- Detected automatically via `session_agent.py detect_request_type(text)`
- Applied to issues via `session_agent.py sync_addon_to_ticket()`

**Deprecated labels** (removed from repos):
- `conception` → replaced by `design` (engineering stage)
- `testing_qa` → replaced by `testing` (engineering stage)
- `approval` → replaced by `review` (engineering stage)
- `production` → replaced by `operations` (engineering stage)
- `troubleshooting` → replaced by `investigation` (request type)
- `refactor` → replaced by `enhancement` (request type)

---

## Relationship to Other Methodology

This file is one of the 6 mandatory methodology files loaded at wakeup step 0.1. Together they form the complete runtime unit for handling ANY work request:

| File | Role in request handling | This file's relationship |
|------|-------------------------|-------------------------|
| **agent-identity.md** | WHO handles it — the engineer identity, 5 principles | The taxonomy is the "no way out" proof of principle §2 (zero judgment): every request type has a classification, so no request escapes the protocol |
| **working-style.md** | HOW the user communicates — French, visual, rapid | The taxonomy's keyword detection (EN+FR) adapts to the user's bilingual working style |
| **session-protocol.md** | WHAT the lifecycle is — wakeup → task → work → save | The 10 engineering stages map to the session lifecycle phases; request types map to GitHub labels applied at task creation |
| **interactive-work-sessions.md** | HOW sessions flow — 5 persistence channels, resilience | The engineering stages (testing, validation, review) correspond to the session's work patterns; request types drive the session's diagnostic vs build vs document modes |
| **task-workflow.md** | WHEN stages advance — 8-stage task state machine | The task workflow's `parse_prompt()` uses the 11 request types to classify the entry prompt; the engineering stages inform stage transitions and label sync |

**The pipeline**: User prompt → `parse_prompt()` classifies using **request type taxonomy** (11 types) → `detect_command()` matches against **COMMAND_REGISTRY** (42 commands, v100) → task workflow creates issue with type label → work advances through **engineering cycle stages** (10 stages) → commands execute as **tracked sub-tasks** with own lifecycle → integrity grid tracks compliance → save delivers. Every request type, every command, every stage, every checkpoint — one pipeline, no exceptions.

### Command Detection in the Pipeline (v100)

The `parse_prompt()` function now includes a `detect_command()` call that matches the user's input against the `COMMAND_REGISTRY`. When a command is detected, the result includes `detected_command` with the skill name, methodology file, and group. This feeds the task workflow's sub-task creation:

```
User prompt
  ↓
parse_prompt() → request type (11 types) + detected_command (42 patterns)
  ↓
task workflow → create issue (type label) + create_sub_task (command lifecycle)
  ↓
engineering cycle → 10 stages with STAGE:/STEP: labels
  ↓
sub-task lifecycle → pending → in_progress → completed/failed
  ↓
integrity grid → 29 checkpoints track compliance
```

The command detection layer ensures that methodology-backed commands (project, harvest, normalize, pub, etc.) are classified and routed through the same engineering pipeline as any other request type. No command escapes tracking — the taxonomy's "no way out" guarantee (agent-identity.md §2) extends to command execution.

---

## Implementation

**Source files**:
- `scripts/session_agent.py` — `ENGINEERING_STAGES`, `ENGINEERING_CROSS_CUTTING`, `REQUEST_TYPE_KEYWORDS`, `detect_request_type()`
- `scripts/gh_helper.py` — `ENGINEERING_STAGE_LABELS` (colors, descriptions)

**References**:
- [Classical SDLC — AWS](https://aws.amazon.com/what-is/sdlc/)
- [Agile/Scrum Sprints — Atlassian](https://www.atlassian.com/agile/scrum/sprints)
- [DevOps Pipeline — Octopus Deploy](https://octopus.com/devops/ci-cd/devops-pipeline/)
- [GitHub Projects Best Practices — GitHub Docs](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects)
- [IssueOps State Machine — GitHub Blog](https://github.blog/engineering/issueops-automate-ci-cd-and-more-with-github-issues-and-actions/)
- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- [ISO/IEC 12207:2017](https://www.iso.org/standard/63712.html) — Software lifecycle processes
