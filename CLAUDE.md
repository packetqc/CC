# CLAUDE.md

## Project Overview

**CC** — Claude Code AI. This is the root repository for the CC project.

## Repository Structure

```
.
├── .gitattributes   # Git line-ending normalization (LF)
├── README.md        # Project description
└── CLAUDE.md        # AI assistant guidelines (this file)
```

## Development Workflow

### Branching

- Default branch: `master`
- Feature branches should be created off `master`
- Use descriptive branch names that reflect the work being done

### Commits

- Write clear, concise commit messages describing **why** the change was made
- Keep commits focused — one logical change per commit
- Do not commit secrets, credentials, or environment files

### Git Conventions

- Line endings are normalized to LF via `.gitattributes`
- Always pull/rebase before pushing to avoid unnecessary merge commits

## Coding Conventions

- Prefer simplicity and readability over cleverness
- Do not over-engineer — solve the current problem, not hypothetical future ones
- Keep files focused and small; split when responsibilities diverge
- Add comments only where the logic is non-obvious

## AI Assistant Guidelines

When working in this repository:

1. **Read before writing** — always read existing files before modifying them
2. **Minimize file creation** — prefer editing existing files over creating new ones
3. **No unnecessary changes** — do not refactor, add docstrings, or "improve" code beyond what was requested
4. **Security first** — never commit secrets or credentials; avoid introducing OWASP top-10 vulnerabilities
5. **Test changes** — run any available linters or test suites before considering work complete
6. **Update this file** — when adding significant project structure (new directories, build tools, frameworks), update CLAUDE.md to reflect the changes
