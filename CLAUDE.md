# CLAUDE.md

## Project Overview

**CC** — Claude Code AI. This repository is in early-stage initialization and does not yet contain application source code.

## Repository Structure

```
CC/
├── .gitattributes   # Git line-ending normalization (LF)
├── CLAUDE.md        # AI assistant guidance (this file)
└── README.md        # Project description
```

## Git Configuration

- **Line endings:** Normalized to LF via `.gitattributes` (`* text=auto`)
- **Default branch:** `master`

## Development Conventions

### Branching

- Feature branches should use descriptive names (e.g., `feature/add-auth`, `fix/login-bug`)
- AI-generated branches use the `claude/` prefix

### Commits

- Write clear, concise commit messages describing **why** the change was made
- Use imperative mood (e.g., "Add user auth" not "Added user auth")
- Keep commits focused — one logical change per commit

### Code Style

- No linting or formatting tools are configured yet. When adding code, include appropriate linting/formatting configuration for the chosen language
- Prefer consistent style within files and across the project

## Commands

No build, test, or lint commands are configured yet. Update this section as tooling is added.

## Notes for AI Assistants

- This is a new repository — read existing files before making changes
- Do not introduce unnecessary dependencies or over-engineer solutions
- When adding the first source code, also set up appropriate tooling (package manager, linter, formatter, test framework) for the chosen language/framework
- Keep this CLAUDE.md updated as the project evolves
