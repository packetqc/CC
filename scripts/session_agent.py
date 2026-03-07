#!/usr/bin/env python3
"""Session Agent — backward-compatible shim.

This file exists for CLI backward compatibility:
    python3 scripts/session_agent.py <command> [args...]

All functionality has been refactored into the session_agent/ package.
Import from the package directly:
    from scripts.session_agent import write_runtime_cache, read_runtime_cache

The package (scripts/session_agent/) takes precedence for Python imports.
This file is only executed when called directly as a script.

Authors: Martin Paquet, Claude (Anthropic)
License: MIT
Knowledge version: v54
"""

import os
import sys

# Ensure the scripts directory is on the path so the package can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_agent.cli import main

if __name__ == "__main__":
    main()
