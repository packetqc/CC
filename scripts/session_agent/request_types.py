"""Request-type detection — taxonomy and keyword matching.

Detects the nature of an add-on (fix, feature, documentation, etc.)
and returns a label suitable for GitHub issue tagging.

Consolidated from 4 industry frameworks:
  - SDLC phases (AWS, IBM, GeeksforGeeks)
  - ITIL ticket types (BMC Helix, Cornell IT)
  - Agile work items (Atlassian, Azure DevOps)
  - Conventional Commits (conventionalcommits.org)

Authors: Martin Paquet, Claude (Anthropic)
"""

from typing import Optional


# ── Request Type Taxonomy ────────────────────────────────────────
# 11 types covering all development activities. Each maps to:
#   - A GitHub issue label (for tracking)
#   - One or more Conventional Commit types (for git history)
#   - SDLC phase(s) and ITIL category (for industry alignment)

REQUEST_TYPE_KEYWORDS = {
    "fix": {
        "keywords": ["fix", "bug", "broken", "error", "crash", "fail", "wrong",
                     "repair", "correct", "patch", "hotfix",
                     "résoudre", "corriger", "bogue", "réparer"],
        "label": "fix",
        "commit_type": "fix",
        "sdlc": "Maintenance",
        "itil": "Incident",
    },
    "feature": {
        "keywords": ["add", "create", "new", "implement", "build", "feature",
                     "scaffold", "introduce", "enable",
                     "ajouter", "créer", "nouveau", "implémenter", "construire"],
        "label": "feature",
        "commit_type": "feat",
        "sdlc": "Implementation",
        "itil": "Change Request",
    },
    "investigation": {
        "keywords": ["investigate", "diagnose", "analyze", "root cause", "why",
                     "troubleshoot", "debug", "trace", "inspect", "probe",
                     "diagnostiquer", "analyser", "pourquoi", "enquêter"],
        "label": "investigation",
        "commit_type": None,
        "sdlc": "Requirements/Analysis",
        "itil": "Problem",
    },
    "enhancement": {
        "keywords": ["refactor", "optimize", "simplify", "restructure", "reorganize",
                     "improve", "upgrade", "modernize", "clean", "performance",
                     "refactoriser", "nettoyer", "optimiser", "améliorer"],
        "label": "enhancement",
        "commit_type": "refactor",
        "sdlc": "Maintenance",
        "itil": "Change Request",
    },
    "testing": {
        "keywords": ["test", "qa", "unit test", "integration test", "assert",
                     "coverage", "regression", "smoke test",
                     "tester"],
        "label": "testing",
        "commit_type": "test",
        "sdlc": "Testing",
        "itil": None,
    },
    "validation": {
        "keywords": ["validate", "validation", "verify", "acceptance", "check",
                     "confirm", "approve", "sign off", "demo",
                     "valider", "vérifier", "confirmer", "approuver"],
        "label": "validation",
        "commit_type": None,
        "sdlc": "Validation (ISO 12207)",
        "itil": None,
    },
    "documentation": {
        "keywords": ["document", "doc", "write", "describe", "readme",
                     "publication", "wiki", "changelog", "guide",
                     "documenter", "décrire", "rédiger"],
        "label": "documentation",
        "commit_type": "docs",
        "sdlc": "Cross-cutting (ISO 12207)",
        "itil": None,
    },
    "deployment": {
        "keywords": ["deploy", "release", "push", "ship", "publish",
                     "deliver", "merge", "ci/cd", "pipeline",
                     "déployer", "publier", "livrer"],
        "label": "deployment",
        "commit_type": "build",
        "sdlc": "Deployment",
        "itil": None,
    },
    "conception": {
        "keywords": ["design", "architect", "conceive", "prototype", "wireframe",
                     "blueprint", "spike", "rfc", "proposal", "plan",
                     "conception", "concevoir", "architecturer", "planifier"],
        "label": "conception",
        "commit_type": None,
        "sdlc": "Planning + Design",
        "itil": None,
    },
    "review": {
        "keywords": ["review", "audit", "assess", "evaluate", "inspect",
                     "survey", "examine", "peer review",
                     "réviser", "auditer", "évaluer", "inspecter"],
        "label": "review",
        "commit_type": None,
        "sdlc": "Cross-cutting",
        "itil": None,
    },
    "chore": {
        "keywords": ["chore", "housekeeping", "cleanup", "maintenance", "routine",
                     "admin", "config", "setup", "infrastructure",
                     "ménage", "entretien", "configuration"],
        "label": "chore",
        "commit_type": "chore",
        "sdlc": "Maintenance",
        "itil": "Service Request",
    },
}


def detect_request_type(text: str) -> Optional[str]:
    """Detect the request type from a text snippet.

    Scans the text for keywords and returns the best-matching
    request type label. Used to auto-tag add-ons with their nature.

    Args:
        text: Text to analyze (verbatim add-on or synthesis).

    Returns:
        Request type label string (e.g., "fix", "feature"), or None.
    """
    if not text:
        return None

    text_lower = text.lower()
    scores = {}

    for rtype, config in REQUEST_TYPE_KEYWORDS.items():
        count = sum(1 for kw in config["keywords"] if kw in text_lower)
        if count > 0:
            scores[rtype] = count

    if not scores:
        return None

    # Return the type with the highest keyword match count
    return max(scores, key=scores.get)
