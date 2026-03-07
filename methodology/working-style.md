# Working Style — The User

Understanding how the user works is essential for effective collaboration. This document captures working patterns observed across hundreds of sessions.

## Communication Style

- **Language**: French is the user's primary language. Messages may arrive in French. Project documentation stays in English.
- **Brevity**: The user communicates in short, focused phrases. Don't over-explain — match the pace.
- **Visual feedback**: Screenshots and screen recordings are the user's primary feedback mechanism. When shared, it IS the bug report / status update / question.
- **Trust the methodology**: When the user says something works or is proven, trust it. The domain expertise is deep.

## Session Patterns

- **Short, focused sessions**: Multiple sessions per day. Each targets a specific module or issue.
- **Rapid iteration**: Flash → test → screenshot → analyze → fix → flash. The cycle is fast.
- **Module-by-module**: New functionality comes as discrete modules from the developer's personal library (MPLIB-CODE). Each module is self-contained with `#if` directives for multi-platform support.

## What the User Expects

1. **Read before modifying** — Always understand existing code before suggesting changes
2. **Printf is always OK** — Adding diagnostic output never needs permission
3. **Logic changes need discussion** — Don't alter module behavior without talking about it
4. **Keep existing code intact** — Augment, don't replace. The developer's modules are battle-tested.
5. **Conventional commits** — `feat:`, `fix:`, `docs:`, `chore:` prefixes
6. **English docs** — All project documentation, comments in code, and commit messages in English

## What Works

- **Printf diagnostics**: Adding UART trace output to understand runtime behavior without touching logic. This has resolved hundreds of bugs.
- **Screenshots as data**: Frame-by-frame analysis of screen captures reveals timing issues, state machine bugs, and rendering problems that logs alone cannot show.
- **Autonomous investigation**: When a bug is spotted, Claude can independently trace the code path, add diagnostics, and propose fixes — the developer validates with a flash+screenshot cycle.
- **Ultra-rapid cycle**: The combination of domain expertise + visual feedback + AI code analysis compresses days of debugging into hours.

## Autonomous Completion After Approval

When the user has approved work — whether by exiting plan mode, confirming an interactive instruction ("fusionne !", "merged?", "go"), or accepting a task popup — **always elevate and complete the full pipeline autonomously**. This means:

- **Auto-elevate**: Use `GH_TOKEN` if available. Don't ask, don't pause.
- **Full pipeline**: commit → push → create PR → merge PR → sync main back. Every step, no stopping.
- **No confirmation loops**: The approval IS the green light. Don't ask "merged?" or print `⏸` blocks after the user already said to proceed.
- **Applies to**: plan mode approval, interactive commands ("fusionne !"), task confirmation popups, any explicit "go ahead" signal.

The user's approval is a single event that authorizes the entire delivery chain. Splitting it into multiple confirmation steps wastes time and breaks flow.

## What Doesn't Work

- **Over-engineering**: Don't add abstraction layers, error handling for impossible cases, or "improvements" beyond what was asked.
- **Breaking existing patterns**: The developer's modules follow specific conventions (static allocation, event flags, singleton pattern). Don't suggest architectural changes unless asked.
- **Verbose explanations**: Keep responses concise. The user reads code faster than prose.
- **Guessing**: If unsure about hardware behavior or RTOS timing, say so. Don't hallucinate embedded systems knowledge.
