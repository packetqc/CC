---
name: plan-review
description: Enforces engineering classification and working-style alignment before plan approval — maps request type to engineering cycle stages, validates plan against user expectations, ensures the two-gate autonomous flow.
user_invocable: true
---

# /plan-review — Plan Review & Engineering Classification

## When This Skill Fires

This skill MUST be invoked **after task analysis and before plan approval** (Gate G3). It bridges the gap between "task received" and "autonomous execution" — ensuring the plan is correctly classified and aligned with the user's working style.

**Triggers**:
- After task-received completes (Stage 0 initial → Stage 1 plan transition)
- Before presenting the work plan to the user for approval
- When replanning after user correction

## The Two-Gate Flow

```
[Gate 1: title confirmed] → [ANALYZE + PLAN ← this skill] → [Gate 2: plan approved] → [autonomous execution]
```

After Gate 2, the session executes autonomously to completion — no further "should I proceed?" questions.

## Step 1: Classify the Request

Map the user's request to one of 11 request types using the engineering taxonomy:

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import parse_prompt

parsed = parse_prompt(user_prompt)
# parsed["detected_label"] → FEATURE, BUG, ENHANCEMENT, REVIEW, etc.
# parsed["action_word"] → create, fix, update, review, investigate, etc.
```

### Request Type → Session Mode Mapping

| Request Type | Session Mode | Plan Focus |
|-------------|-------------|------------|
| `fix` | Diagnostic | Root cause → hypothesis → verify → patch |
| `feature` | Build | Design → implement → test → deliver |
| `investigation` | Diagnostic (no fix) | Gather → analyze → report findings |
| `enhancement` | Refactor | Identify → refactor → verify no regression |
| `testing` | Verification | Write tests → run → report coverage |
| `validation` | Acceptance | Demo → gather feedback → report |
| `documentation` | Content | Gather → structure → write → publish |
| `deployment` | Delivery | Prepare → stage → deploy → verify |
| `conception` | Design | Ideate → prototype → validate → formalize |
| `review` | Assessment | Scope → examine → report → recommend |
| `chore` | Maintenance | Identify → execute → verify → clean up |

### Engineering Cycle Stage Alignment

Map the request type to its primary engineering cycle stage:

| Request Type | Primary Stage | Conventional Commit | SDLC Phase |
|-------------|---------------|-------------------|------------|
| `fix` | `implementation` (3) | `fix` | Maintenance |
| `feature` | `implementation` (3) | `feat` | Implementation |
| `investigation` | `analysis` (0) | — | Requirements/Analysis |
| `enhancement` | `implementation` (3) | `refactor`, `perf` | Maintenance |
| `testing` | `testing` (4) | `test` | Testing |
| `validation` | `validation` (5) | — | Validation |
| `documentation` | cross-cutting | `docs` | Cross-cutting |
| `deployment` | `deployment` (7) | `build`, `ci` | Deployment |
| `conception` | `design` (2) | — | Planning + Design |
| `review` | `review` (6) | — | Cross-cutting |
| `chore` | `operations` (8) | `chore` | Maintenance |

## Step 2: Apply Working-Style Constraints

Before building the plan, validate against the user's established patterns:

### Communication Alignment

| User Pattern | Plan Constraint |
|-------------|-----------------|
| **French primary** | Session language auto-detected. Commands stay English. Summaries in session language. |
| **Brevity** | Keep todo descriptions concise — the user reads code faster than prose |
| **Visual feedback** | Plan for screenshot/screen recording checkpoints where applicable |
| **Trust methodology** | Don't over-explain — if the user says something works, trust it |

### Session Pattern Alignment

| User Pattern | Plan Constraint |
|-------------|-----------------|
| **Short, focused sessions** | Scope the plan to fit — don't plan 20 todos for a focused session |
| **Rapid iteration** | Plan for progressive commits, not one big delivery |
| **Module-by-module** | New functionality comes as discrete modules — plan integration, not rewrite |

### What the User Expects

| Expectation | Plan Rule |
|-------------|-----------|
| **Read before modifying** | Plan includes a "read and understand" step before modification steps |
| **Printf is always OK** | Diagnostic output never needs a separate todo or permission |
| **Logic changes need discussion** | If the plan modifies existing module logic, flag it for user confirmation |
| **Keep existing code intact** | Plan augments, doesn't replace. The developer's modules are battle-tested |
| **Conventional commits** | Plan commit messages use `feat:`, `fix:`, `docs:`, `chore:` prefixes |

### What Doesn't Work — Anti-Patterns in Plans

| Anti-Pattern | Fix |
|-------------|-----|
| Over-engineering | Only add what was asked — no abstraction layers for one-time operations |
| Breaking existing patterns | Match the codebase's conventions (static allocation, event flags, singleton) |
| Verbose explanations | Plan steps are actions, not essays |
| Guessing embedded behavior | If unsure about hardware/RTOS timing, add a "verify" step, don't assume |

## Step 3: Build the Plan

Create the todo list with these properties:
- **Atomic**: one clear deliverable per todo
- **Ordered**: dependencies flow naturally
- **Estimable**: scope is clear before starting
- **Aligned**: matches request type and working style

### Plan Structure by Session Type

**Diagnostic (fix, investigation)**:
```
1. [Read and understand the relevant code paths]
2. [Identify root cause / formulate hypothesis]
3. [Implement fix / verify hypothesis]
4. [Test the fix / document findings]
5. [Commit + deliver]
```

**Build (feature, enhancement)**:
```
1. [Read existing code for integration points]
2. [Implement the feature / enhancement]
3. [Verify — test, screenshot checkpoint if visual]
4. [Update documentation if applicable]
5. [Commit + deliver]
```

**Content (documentation, conception)**:
```
1. [Gather raw material — user input, existing content]
2. [Structure — create outline / methodology]
3. [Write — expand content]
4. [Publish — web pages, essential files]
5. [Commit + deliver]
```

**Assessment (review, validation, testing)**:
```
1. [Define scope of review / test plan]
2. [Execute review / run tests]
3. [Compile findings / report results]
4. [Recommend actions if applicable]
5. [Commit report + deliver]
```

## Step 4: Present for Approval (Gate G3)

Present the plan to the user. This is the **final approval gate** — after this, autonomous execution begins.

The plan presentation includes:
1. **Request classification**: type + engineering stage + label
2. **Todo list**: numbered steps with clear deliverables
3. **Scope alignment**: confirmation this matches what was asked

### Autonomous Execution Principle (v53)

**After plan approval — no more gates.** The user does not need to say "go ahead" between todo steps. The plan was approved. Execute it.

**What triggers autonomous execution**:
- User approves the work plan (explicit "go", "proceed", "do it")
- User confirms task title + plan is self-evident (single-step task)

**What pauses autonomous execution**:
- User explicitly asks a question → answer, then resume
- User says "wait", "stop", "pause" → pause and wait
- Ambiguity that could cause irreversible damage → ask once, then proceed

**Anti-pattern**: Asking "what should I do first?" or "shall I proceed with step 2?" after plan approval. The user already approved. **Act.**

## Step 5: Advance Workflow

The task workflow requires sequential stage advancement — jumping stages is blocked (v59.3). After plan approval, advance through each intermediate stage:

```python
from scripts.session_agent import advance_task_stage

# Advance through stages sequentially — skipping is blocked
advance_task_stage('plan', reason='plan created')
advance_task_stage('analyze', reason='analysis complete — incorporated in plan')
advance_task_stage('implement', reason='plan approved by user')
```

**Why all three stages**: The v59.3 audit added stage jump validation — jumping from `initial` directly to `implement` is blocked because `plan` and `analyze` would be unvisited. The plan-review skill conceptually covers both plan and analyze, so both stages are advanced with appropriate reasons.

Then the `/work-cycle` skill takes over for each todo.

## Documentation Cross-Cut

At each stage boundary where modifications occurred, the workflow triggers a doc check:

**AskUserQuestion options**:
- **Update project documentation** — project's own docs only
- **Update knowledge only** — knowledge system docs only
- **Update both** — both project and knowledge
- **Defer to documentation stage** — handle at stage 6 later

The `modifications_occurred` flag is set via `mark_modifications_occurred()` during work. Resets at each stage transition.

## Validation Cross-Cut

At stage completion (stages 0-4), optionally trigger a **validation quiz**:

Each check = AskUserQuestion with **exactly 4 options** (mandatory):
1. **Passed** — checkpoint met
2. **Failed** — checkpoint not met
3. **Skip this** — skip one point
4. **Skip all** — skip remaining checks

Even skipped results are persisted — a skip IS a status, never omitted.

## Backward Transitions (Rework Loops)

The lifecycle is not strictly sequential. Common rework paths the plan must accommodate:

```
validation → design        (user rejects approach — redesign)
testing → implementation   (tests fail — fix the code)
review → implementation    (PR rejected — rework)
validation → analysis      (stakeholder needs changed)
improvement → analysis     (lesson learned feeds next cycle)
```

## Identity Principles in Planning

- **I1 (protocol non-negotiable)**: Every request gets a proper plan, even "quick" ones
- **I2 (zero judgment)**: All 11 request types enter the same classification pipeline — no request escapes
- **I3 (rigor over convenience)**: Read before modifying, even when the fix seems obvious
- **I5 (self-correction)**: If tempted to skip the plan and jump to code — stop, that's NPC behavior

## Mid-Work Replanning (Add-on Pipeline)

When the user provides corrections or additional instructions during plan review or execution:

```python
from scripts.session_agent import append_request_addon, read_request_addons

# Capture the correction as an add-on (not a new task)
append_request_addon(verbatim=user_message, synthesis='User corrected approach: ...')

# Read all add-ons for the current task
addons = read_request_addons()
```

Add-ons are supplementary instructions on the **current task** — they don't trigger a new task-received flow. They're stored in the cache and posted to the issue. Use them to adjust the plan without restarting.

## Notes

- Import all functions from `scripts.session_agent`
- The plan is built AFTER task-received and BEFORE autonomous execution
- `parse_prompt()` gives signals — Claude synthesizes meaning from keywords + context
- Working-style constraints are not optional — they're validated patterns from hundreds of sessions
- Backward transitions (rework loops) are normal — plan for them, don't resist them
- The engineering taxonomy's 10 stages inform transitions; the 11 request types inform classification
- **User correction > AI assumption** — when the user redirects, follow immediately
