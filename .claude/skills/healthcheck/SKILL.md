---
name: healthcheck
description: Run engineering cycle healthcheck — validates integrity grid, checkpoint mechanics, workflow stages, and report generation. Two scopes available (engineering / task workflow). Runs imperatively (no gates).
user_invocable: true
---

# /healthcheck — Engineering Cycle Healthcheck

## Imperative Mode

This is an **intrinsic agent operation**, not a user task. When triggered, execute immediately — no title confirmation, no plan approval, no gates. The healthcheck IS the plan.

**Reference**: `methodology/agent-identity.md` § "Autonomous Engineering Cycle Execution"

## Trigger Detection

`parse_prompt()` returns `is_healthcheck: true` and `healthcheck_scope` when the prompt matches:

| Trigger | Scope | Example |
|---------|-------|---------|
| Engineering cycle + healthcheck | `engineering` | "testing v59 engineering cycle healthcheck" |
| Engineering workflow + healthcheck | `engineering` | "engineering workflow healthcheck" |
| Task workflow + healthcheck | `task_workflow` | "task workflow healthcheck" |
| Standalone healthcheck | `engineering` | "healthcheck" (no API/service context) |
| Integrity + healthcheck | `engineering` | "integrity healthcheck" |

**Does NOT trigger**: "add healthcheck endpoint", "API healthcheck", "service health check"

## Execution

Run immediately on detection — no AskUserQuestion, no confirmation:

### Engineering Scope (default)

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import run_healthcheck, format_healthcheck_report

results = run_healthcheck()
report = format_healthcheck_report(results)
```

7-test battery: grid initialization, checkpoint mechanics, work cycle reset, gap detection, integrity report, task workflow stages, workflow status.

### Task Workflow Scope

```python
import sys; sys.path.insert(0, '.')
from scripts.session_agent import run_task_workflow_healthcheck, format_task_workflow_healthcheck_report

results = run_task_workflow_healthcheck()
report = format_task_workflow_healthcheck_report(results)
```

8-test battery: workflow init, stage advancement, step advancement, parse_prompt action words, multi-request detection, validation cross-cut, format_workflow_status, generate_task_report.

### Scope Selection

```python
parsed = parse_prompt(user_prompt)
if parsed["is_healthcheck"]:
    scope = parsed["healthcheck_scope"]  # "engineering" or "task_workflow"
    if scope == "task_workflow":
        results = run_task_workflow_healthcheck()
        report = format_task_workflow_healthcheck_report(results)
    else:
        results = run_healthcheck()
        report = format_healthcheck_report(results)
```

Display the `report` to the user.

## After Healthcheck

- **All pass** → print results, proceed with any remaining user request in the prompt
- **Any fail** → print results with failures, ask user how to proceed
- Grid is re-initialized to clean state after tests

## Notes

- Each test runs in isolation (re-inits to avoid state bleed)
- Import from `scripts.session_agent` (not directly from integrity.py or task_workflow.py)
- Pure diagnostic — does NOT modify any files
- The `/healthcheck` skill can also be invoked manually mid-session
