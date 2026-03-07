"""Shared helpers — GitHub helper initialization and common utilities.

Authors: Martin Paquet, Claude (Anthropic)
"""

import os
import sys
from typing import Optional


def _get_gh_helper():
    """Get an initialized GitHubHelper instance.

    Consolidates the repeated pattern of sys.path.insert + import + instantiate.
    Returns None if GH_TOKEN is missing or if gh_helper is not available.

    Returns:
        GitHubHelper instance, or None if unavailable.
    """
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        return None
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        from gh_helper import GitHubHelper
        return GitHubHelper()
    except ImportError:
        return None
