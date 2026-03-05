---
name: code-review
description: Comprehensive code review covering security, code quality, and performance. Use when reviewing files, pull requests, or code changes.
argument-hint: [file path or instruction]
context: fork
agent: Explore
allowed-tools: Read, Glob, Grep
---

## Code Review

Review the code specified by `$ARGUMENTS`. If no specific files are mentioned, review recently changed files using `git diff --name-only HEAD~1`.

### Review Checklist

#### 1. Security
- Injection vulnerabilities (SQL, command, XSS)
- Authentication and authorization issues
- Secrets or credentials in code
- Input validation and sanitization
- Insecure dependencies or configurations

#### 2. Code Quality
- Readability and naming conventions
- DRY violations (duplicated logic)
- Function/method complexity (cyclomatic complexity)
- Error handling coverage
- Consistent coding style

#### 3. Performance
- Algorithmic complexity (unnecessary O(n^2) or worse)
- Memory leaks or excessive allocations
- Unnecessary I/O or network calls
- Missing caching opportunities
- N+1 query patterns

### Output Format

For each finding, report:

**[SEVERITY] Category — File:Line**
> Description of the issue and why it matters.

**Suggested fix:**
```
code suggestion here
```

Severity levels:
- **CRITICAL** — Must fix before merge (security holes, data loss risks)
- **WARNING** — Should fix (bugs, performance issues, poor patterns)
- **INFO** — Consider improving (style, readability, minor optimizations)

### Summary

End with a summary table:

| Severity | Count |
|----------|-------|
| CRITICAL | N     |
| WARNING  | N     |
| INFO     | N     |

And a one-paragraph overall assessment.
