#!/usr/bin/env python3
"""Session Issue Sync — Real-time GitHub issue comment synchronization.

Implements the v51-v52 protocol for maintaining a live GitHub issue as
the persistent audit trail of a Claude Code session. The issue becomes
the third persistence channel alongside Git (commits) and Notes (files).

Three-channel persistence model:
  Git    — batch (on save), survives crash if pushed
  Notes  — batch (on save), lost on compaction
  Issue  — REAL-TIME (on each exchange), survives all failure modes

Usage (as module):
    from scripts.session_issue_sync import SessionSync
    sync = SessionSync("packetqc/knowledge", issue_number=479)

    # Post user message
    sync.post_user("feature create agent ticket sync updater")

    # Start a todo step
    comment_id = sync.start_step("Add comment methods to gh_helper.py",
                                  "Adding POST/PATCH methods for issue comments")

    # Complete the step
    sync.complete_step(comment_id, "Add comment methods to gh_helper.py",
                       "Added issue_comment_post(), issue_comment_edit(), "
                       "issue_comments_list(), issue_close(). Tested on #479.")

    # Run integrity check before save
    report = sync.integrity_check(todos_completed=["step1", "step2"],
                                   todos_pending=["step3"])

    # Post session summary
    sync.post_summary(summary_text)

    # Close issue with closing report
    sync.close_with_report(deliveries=[("PR #480", "merged")])

Authors: Martin Paquet, Claude (Anthropic)
License: MIT
Knowledge version: v52
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Import GitHubHelper from same scripts/ folder
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gh_helper import GitHubHelper
except ImportError:
    GitHubHelper = None

# Import runtime cache writer (for auto-write on init)
try:
    from session_agent import write_runtime_cache, read_runtime_cache
except ImportError:
    write_runtime_cache = None
    read_runtime_cache = None



# Avatars for issue comments — Vicky Viking from knowledge repo
# Martin = Vicky (NPC), Claude = Vicky with sunglasses (AWARE)
_VICKY_BASE = 'https://raw.githubusercontent.com/packetqc/knowledge/main/references/Martin'
AVATAR_MARTIN = f'<img src="{_VICKY_BASE}/vicky.png" width="24" align="absmiddle">'
AVATAR_CLAUDE = f'<img src="{_VICKY_BASE}/vicky-sunglasses.png" width="24" align="absmiddle">'


class SessionSync:
    """Real-time session-to-issue synchronization handler.

    Manages the lifecycle of comments on a session's GitHub issue,
    implementing the v51-v52 protocol:
      - Post 🧑 user comments (verbatim or summarized)
      - Post 🤖 bot comments with ⏳→✅ lifecycle per todo step
      - Run integrity check comparing todos vs posted comments
      - Post session summary and closing report
    """

    def __init__(self, repo: str, issue_number: int,
                 token: Optional[str] = None):
        """Initialize sync handler for a session issue.

        Args:
            repo: owner/repo format (e.g., "packetqc/knowledge")
            issue_number: GitHub issue number for this session
            token: Optional PAT (defaults to GH_TOKEN env var)
        """
        self.repo = repo
        self.issue_number = issue_number
        self._comment_ids = {}  # step_name -> comment_id mapping
        self._posted_count = 0
        self._expected_count = 0

        if GitHubHelper is None:
            raise ImportError(
                "gh_helper.py not found. Ensure it exists in scripts/."
            )

        try:
            self.gh = GitHubHelper(token=token)
        except ValueError:
            # No token — sync is disabled
            self.gh = None

        # Auto-write runtime cache when sync is initialized with an issue
        # This ensures notes/session-runtime.json is always current
        if self.gh and write_runtime_cache:
            try:
                import subprocess
                branch = subprocess.check_output(
                    ["git", "branch", "--show-current"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                branch = ""
            # Only write if the issue changed (avoid unnecessary writes)
            existing = read_runtime_cache() if read_runtime_cache else None
            if not existing or existing.get("issue_number") != issue_number:
                write_runtime_cache(
                    repo=repo,
                    issue_number=issue_number,
                    branch=branch,
                    mode="burst",  # default — agent will update with actual mode
                )

    @property
    def enabled(self) -> bool:
        """Whether sync is active (token available)."""
        return self.gh is not None

    def post_user(self, message: str, short_desc: str = "Message") -> Optional[int]:
        """Post a 🧑 user comment with the user's message.

        Called when a user prompt is received, BEFORE processing begins.

        Args:
            message: The user's message (quoted in the comment)
            short_desc: Short description for the comment header

        Returns:
            Comment ID if posted, None if sync disabled.
        """
        if not self.enabled:
            return None

        body = (
            f"## {AVATAR_MARTIN} Martin — {short_desc}\n"
            f"> {message}\n"
        )
        result = self.gh.issue_comment_post(self.repo, self.issue_number, body)
        if result.get("posted"):
            self._posted_count += 1
            return result["id"]
        return None

    def start_step(self, step_name: str, description: str = "") -> Optional[int]:
        """Post a 🤖 ⏳ comment when a todo step starts.

        Creates a new comment that will be edited to ✅ when the step completes.
        The comment_id is stored internally for the subsequent complete_step() call.

        Args:
            step_name: Name of the todo step (matches TodoWrite content)
            description: What will be done in this step

        Returns:
            Comment ID for later editing, None if sync disabled.
        """
        if not self.enabled:
            return None

        self._expected_count += 1
        body = (
            f"## {AVATAR_CLAUDE} Claude — ⏳ {step_name}\n\n"
            f"{description}\n" if description else
            f"## {AVATAR_CLAUDE} Claude — ⏳ {step_name}\n"
        )
        result = self.gh.issue_comment_post(self.repo, self.issue_number, body)
        if result.get("posted"):
            comment_id = result["id"]
            self._comment_ids[step_name] = comment_id
            self._posted_count += 1
            return comment_id
        return None

    def complete_step(self, comment_id: int, step_name: str,
                      results: str = "") -> bool:
        """Edit existing ⏳ comment to ✅ when a step completes.

        The edit-in-place approach keeps the issue thread clean —
        one comment per step, not two. The ⏳→✅ transition is visible
        in the comment's edit history.

        Args:
            comment_id: Comment ID returned by start_step()
            step_name: Name of the completed step
            results: Summary of what was accomplished (files, decisions)

        Returns:
            True if edited successfully, False otherwise.
        """
        if not self.enabled or not comment_id:
            return False

        body = f"## {AVATAR_CLAUDE} Claude — ✅ {step_name}\n\n"
        if results:
            body += f"{results}\n"

        result = self.gh.issue_comment_edit(self.repo, comment_id, body)
        return result.get("edited", False)

    def post_bot(self, short_desc: str, content: str) -> Optional[int]:
        """Post a standalone 🤖 comment (not tied to a todo step).

        Used for analysis results, design decisions, or other
        significant exchanges that aren't todo steps.

        Args:
            short_desc: Short description for the header
            content: Comment body content

        Returns:
            Comment ID if posted, None if sync disabled.
        """
        if not self.enabled:
            return None

        body = f"## {AVATAR_CLAUDE} Claude — {short_desc}\n\n{content}\n"
        result = self.gh.issue_comment_post(self.repo, self.issue_number, body)
        if result.get("posted"):
            self._posted_count += 1
            return result["id"]
        return None

    def integrity_check(self, todos_completed: list,
                        todos_pending: list) -> dict:
        """Run issue comment integrity check before save.

        Compares session exchanges (todos, user messages) against
        actually posted comments. Reports gaps and posts missing
        comments retroactively.

        Args:
            todos_completed: List of completed todo step names
            todos_pending: List of pending todo step names

        Returns:
            Dict with 'total_expected', 'total_posted', 'gaps',
            'retroactive_posts', 'report_line'.
        """
        if not self.enabled:
            return {
                "total_expected": 0,
                "total_posted": 0,
                "gaps": [],
                "retroactive_posts": 0,
                "report_line": "Commentaires temps réel synchronisés | N/A (pas de token)",
            }

        # Fetch all comments on the issue
        comments = self.gh.issue_comments_list(self.repo, self.issue_number)

        # Parse comment types
        bot_step_comments = []
        user_comments = []
        for c in comments:
            body = c.get("body", "")
            if "🤖" in body and ("⏳" in body or "✅" in body):
                bot_step_comments.append(c)
            elif "🧑" in body:
                user_comments.append(c)

        # Check which todos have corresponding comments
        gaps = []
        for todo in todos_completed:
            has_comment = any(
                todo.lower() in c["body"].lower()
                for c in bot_step_comments
            )
            if not has_comment:
                gaps.append(todo)

        # Post retroactive comments for gaps
        retroactive = 0
        for gap in gaps:
            result = self.gh.issue_comment_post(
                self.repo, self.issue_number,
                f"## {AVATAR_CLAUDE} Claude — ✅ {gap}\n\n"
                f"*(commentaire rétroactif — posté lors de la vérification d'intégrité)*\n"
            )
            if result.get("posted"):
                retroactive += 1

        total_expected = len(todos_completed)
        total_posted = len(bot_step_comments) + retroactive

        if gaps:
            report_line = (
                f"Commentaires temps réel synchronisés | Non "
                f"({len(bot_step_comments)} postés / {total_expected} attendus) "
                f"— {retroactive} manquants rattrapés au save"
            )
        else:
            report_line = (
                f"Commentaires temps réel synchronisés | Oui "
                f"({total_posted}/{total_expected})"
            )

        return {
            "total_expected": total_expected,
            "total_posted": total_posted,
            "gaps": gaps,
            "retroactive_posts": retroactive,
            "report_line": report_line,
            "user_comments": len(user_comments),
            "bot_comments": len(bot_step_comments),
        }

    def post_summary(self, summary_text: str) -> Optional[int]:
        """Post the pre-save session summary as a 🤖 comment.

        This is the final structured comment before issue closure,
        containing metrics, time blocks, deliveries, and self-assessment.

        Args:
            summary_text: Full markdown summary (from save protocol step 0)

        Returns:
            Comment ID if posted, None if sync disabled.
        """
        if not self.enabled:
            return None

        body = f"## {AVATAR_CLAUDE} Claude — Résumé de session\n\n{summary_text}\n"
        result = self.gh.issue_comment_post(self.repo, self.issue_number, body)
        if result.get("posted"):
            self._posted_count += 1
            return result["id"]
        return None

    def close_with_report(self, deliveries: list,
                          summary_comment: Optional[str] = None) -> bool:
        """Close the issue with a closing report.

        Posts a closing report as the final comment, then closes the issue.
        The report indexes all comments on the issue for easy navigation.

        Args:
            deliveries: List of (item, status) tuples
                e.g., [("PR #480", "✅ fusionné"), ("Issue #479", "✅ fermée")]
            summary_comment: Optional summary to include

        Returns:
            True if closed successfully, False otherwise.
        """
        if not self.enabled:
            return False

        # Fetch all comments for the index
        comments = self.gh.issue_comments_list(self.repo, self.issue_number)

        # Build delivery table
        delivery_rows = ""
        for item, status in deliveries:
            delivery_rows += f"| {item} | {status} |\n"

        # Build comment index table
        comment_rows = ""
        for i, c in enumerate(comments, 1):
            body = c.get("body", "")
            if "🧑" in body:
                ctype = "🧑"
            elif "🤖" in body:
                ctype = "🤖"
            else:
                ctype = "—"

            # Extract content description from header
            import re
            m = re.search(r"##\s*[🧑🤖].*?[—–-]\s*(.+?)(?:\n|$)", body)
            content = m.group(1).strip() if m else body[:60].replace("\n", " ")
            comment_rows += f"| {i} | {ctype} | {content} |\n"

        # Add the closing report itself
        report_index = len(comments) + 1
        comment_rows += f"| {report_index} | 🤖 | **Ce rapport de clôture** |\n"

        body = (
            f"## {AVATAR_CLAUDE} Claude — Rapport de clôture\n\n"
            "### Statut final\n"
            "| Élément | Statut |\n"
            "|---------|--------|\n"
            f"{delivery_rows}\n"
            f"### Historique complet du billet ({report_index} commentaires)\n"
            "| # | Type | Contenu |\n"
            "|---|------|---------|\n"
            f"{comment_rows}\n"
            "*Session terminée — billet fermé.*\n"
        )

        # Post the report
        result = self.gh.issue_comment_post(self.repo, self.issue_number, body)
        if not result.get("posted"):
            return False

        # Close the issue
        close_result = self.gh.issue_close(self.repo, self.issue_number)

        # Invalidate runtime cache — mark agent_initialized as false
        if close_result.get("closed") and read_runtime_cache and write_runtime_cache:
            cache = read_runtime_cache()
            if cache and cache.get("issue_number") == self.issue_number:
                cache["agent_initialized"] = False
                cache["updated"] = datetime.now(timezone.utc).isoformat()
                cache_path = None
                try:
                    from scripts.session_agent import _find_runtime_cache
                    cache_path = _find_runtime_cache()
                except ImportError:
                    try:
                        import subprocess
                        root = subprocess.check_output(
                            ["git", "rev-parse", "--show-toplevel"],
                            stderr=subprocess.DEVNULL
                        ).decode().strip()
                        # Try branch-specific cache first
                        branch = subprocess.check_output(
                            ["git", "branch", "--show-current"],
                            stderr=subprocess.DEVNULL
                        ).decode().strip()
                        suffix = branch.rstrip('/').split('-')[-1] if branch else ""
                        suffix = ''.join(c for c in suffix if c.isalnum())
                        if suffix:
                            path = os.path.join(root, "notes", f"session-runtime-{suffix}.json")
                            if os.path.exists(path):
                                cache_path = path
                        if not cache_path:
                            cache_path = os.path.join(root, "notes", "session-runtime.json")
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass
                if cache_path:
                    try:
                        with open(cache_path, 'w') as f:
                            json.dump(cache, f, indent=2)
                    except OSError:
                        pass

        return close_result.get("closed", False)

    def get_stats(self) -> dict:
        """Return sync statistics for the session.

        Returns:
            Dict with posted/expected counts and step→comment_id mapping.
        """
        return {
            "posted": self._posted_count,
            "expected": self._expected_count,
            "comment_ids": dict(self._comment_ids),
            "enabled": self.enabled,
        }
