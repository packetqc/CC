"""Watchdog and SessionAgent — autonomous agent for GitHub issue sync.

Implements:
  1. WATCHDOG — classical feed-or-fire pattern
  2. AGENT — autonomous background process (state file based)
  3. TIMER — periodic tick that checks and posts
  4. ADAPTIVE FREQUENCY — adjusts tick rate based on session mode

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Optional

from .cache import write_runtime_cache, read_runtime_cache


# Paths
STATE_FILE = "/tmp/session_agent_state.json"
QUEUE_FILE = "/tmp/session_agent_queue.json"
LOCK_FILE = "/tmp/session_agent.lock"


class Watchdog:
    """Classical watchdog timer — feed it or it fires.

    The watchdog monitors session activity. Every significant action
    must call feed() to reset the timer. If the timer expires without
    a feed, the watchdog fires and runs an integrity check.
    """

    def __init__(self, timeout_sec: float = 120.0,
                 on_fire: Optional[callable] = None):
        self.timeout_sec = timeout_sec
        self.on_fire = on_fire
        self._last_feed = time.time()
        self._feed_count = 0
        self._fire_count = 0

    def feed(self):
        """Reset the watchdog timer."""
        self._last_feed = time.time()
        self._feed_count += 1

    def check(self) -> bool:
        """Check if watchdog should fire.

        Returns:
            True if fired (timeout expired), False if OK.
        """
        elapsed = time.time() - self._last_feed
        if elapsed > self.timeout_sec:
            self._fire_count += 1
            if self.on_fire:
                self.on_fire(elapsed)
            return True
        return False

    @property
    def seconds_since_feed(self) -> float:
        return time.time() - self._last_feed

    @property
    def stats(self) -> dict:
        return {
            "feed_count": self._feed_count,
            "fire_count": self._fire_count,
            "seconds_since_feed": round(self.seconds_since_feed, 1),
            "timeout_sec": self.timeout_sec,
            "healthy": self.seconds_since_feed < self.timeout_sec,
        }


# Import SessionSync (optional dependency)
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from session_issue_sync import SessionSync
except ImportError:
    SessionSync = None


class SessionAgent:
    """Autonomous agent for session-to-issue synchronization.

    Provides:
    1. Event queue — session writes events instantly (no API latency)
    2. Timer — periodic tick processes the queue and posts to GitHub
    3. Watchdog — detects silence, fires integrity check
    4. Adaptive frequency — adjusts tick rate based on session mode

    Modes:
        normal:  tick every 60s, watchdog timeout 120s
        live:    tick every 15s, watchdog timeout 30s
        burst:   tick every 10s, watchdog timeout 20s
    """

    MODES = {
        "normal":  (60,  120),
        "live":    (15,  30),
        "burst":   (10,  20),
    }

    def __init__(self, repo: str, issue_number: int,
                 mode: str = "normal", token: Optional[str] = None):
        self.repo = repo
        self.issue_number = issue_number
        self.mode = mode if mode in self.MODES else "normal"
        self._token = token

        tick_interval, wd_timeout = self.MODES[self.mode]
        self.tick_interval = tick_interval

        self.watchdog = Watchdog(
            timeout_sec=wd_timeout,
            on_fire=self._on_watchdog_fire
        )

        self._sync = None
        if SessionSync:
            try:
                self._sync = SessionSync(repo, issue_number, token=token)
            except (ImportError, ValueError):
                self._sync = None

        self._timer_thread = None
        self._running = False
        self._tick_count = 0

        self._load_state()

    @classmethod
    def init_from_cache(cls, mode: str = None,
                        token: Optional[str] = None) -> Optional['SessionAgent']:
        """Initialize agent from the runtime cache in notes/."""
        cache = read_runtime_cache()
        if not cache:
            return None

        repo = cache.get("repo")
        issue_number = cache.get("issue_number")
        if not repo or not issue_number:
            return None

        cached_mode = mode or cache.get("mode", "normal")
        agent = cls(repo, issue_number, mode=cached_mode, token=token)
        return agent

    @property
    def enabled(self) -> bool:
        return self._sync is not None and self._sync.enabled

    def _get_branch(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                if (state.get("repo") == self.repo and
                        state.get("issue_number") == self.issue_number):
                    self._tick_count = state.get("tick_count", 0)
                    self.mode = state.get("mode", self.mode)
                    tick_interval, wd_timeout = self.MODES[self.mode]
                    self.tick_interval = tick_interval
                    self.watchdog.timeout_sec = wd_timeout
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self):
        state = {
            "repo": self.repo,
            "issue_number": self.issue_number,
            "mode": self.mode,
            "tick_interval": self.tick_interval,
            "tick_count": self._tick_count,
            "running": self._running,
            "last_save": datetime.now(timezone.utc).isoformat(),
            "watchdog": self.watchdog.stats,
            "enabled": self.enabled,
            "queue_depth": self._queue_depth(),
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass

    def _queue_depth(self) -> int:
        if not os.path.exists(QUEUE_FILE):
            return 0
        try:
            with open(QUEUE_FILE, 'r') as f:
                events = json.load(f)
            return len(events)
        except (json.JSONDecodeError, OSError):
            return 0

    # ── Event Queue ──────────────────────────────────────────────

    def _enqueue(self, event: dict):
        event["timestamp"] = datetime.now(timezone.utc).isoformat()

        events = []
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r') as f:
                    events = json.load(f)
            except (json.JSONDecodeError, OSError):
                events = []

        events.append(event)

        try:
            with open(QUEUE_FILE, 'w') as f:
                json.dump(events, f, indent=2)
        except OSError:
            pass

        self.watchdog.feed()
        self._save_state()

    def _dequeue_all(self) -> list:
        if not os.path.exists(QUEUE_FILE):
            return []

        try:
            with open(QUEUE_FILE, 'r') as f:
                events = json.load(f)
            with open(QUEUE_FILE, 'w') as f:
                json.dump([], f)
            return events
        except (json.JSONDecodeError, OSError):
            return []

    # ── Feed Methods ─────────────────────────────────────────────

    def feed_user(self, message: str, short_desc: str = "Message"):
        self._enqueue({"type": "user", "message": message, "short_desc": short_desc})

    def feed_step_start(self, step_name: str, description: str = ""):
        self._enqueue({"type": "step_start", "step_name": step_name, "description": description})

    def feed_step_complete(self, step_name: str, results: str = ""):
        self._enqueue({"type": "step_complete", "step_name": step_name, "results": results})

    def feed_bot(self, short_desc: str, content: str):
        self._enqueue({"type": "bot", "short_desc": short_desc, "content": content})

    def feed_heartbeat(self, tool_name: str = ""):
        self.watchdog.feed()
        self._save_state()

    def feed_compaction(self):
        self._enqueue({"type": "compaction", "message": "Context compaction detected"})

    # ── Adaptive Frequency ───────────────────────────────────────

    def switch_issue(self, new_issue_number: int, new_issue_title: str = ""):
        old_issue = self.issue_number
        self.issue_number = new_issue_number

        self._sync = None
        if SessionSync:
            try:
                self._sync = SessionSync(
                    self.repo, new_issue_number, token=self._token)
            except (ImportError, ValueError):
                self._sync = None

        self._save_state()

        write_runtime_cache(
            repo=self.repo,
            issue_number=new_issue_number,
            issue_title=new_issue_title,
            branch=self._get_branch(),
            mode=self.mode,
        )

    def set_mode(self, mode: str):
        if mode not in self.MODES:
            return

        self.mode = mode
        tick_interval, wd_timeout = self.MODES[mode]
        self.tick_interval = tick_interval
        self.watchdog.timeout_sec = wd_timeout
        self._save_state()

    # ── Timer + Tick ─────────────────────────────────────────────

    def start(self):
        if self._running:
            return

        self._running = True
        self._save_state()
        self._timer_thread = threading.Thread(
            target=self._timer_loop,
            daemon=True,
            name="session-agent-watchdog"
        )
        self._timer_thread.start()

    def stop(self):
        self._running = False
        self._save_state()
        self.tick()

    def _timer_loop(self):
        while self._running:
            try:
                self.tick()
            except Exception as e:
                self._enqueue({
                    "type": "agent_error",
                    "message": f"Tick error: {str(e)}",
                })
            time.sleep(self.tick_interval)

    def tick(self) -> dict:
        self._tick_count += 1
        result = {
            "tick": self._tick_count,
            "events_processed": 0,
            "events_posted": 0,
            "watchdog_fired": False,
            "compaction_detected": False,
            "mode": self.mode,
        }

        if self.watchdog.check():
            result["watchdog_fired"] = True

        events = self._dequeue_all()
        result["events_processed"] = len(events)

        if not events:
            self._save_state()
            return result

        compaction_detected = False
        step_comment_ids = {}

        for event in events:
            etype = event.get("type")

            if etype == "compaction":
                compaction_detected = True
                result["compaction_detected"] = True
                continue

            if not self.enabled:
                continue

            if etype == "user":
                cid = self._sync.post_user(
                    event.get("message", ""),
                    event.get("short_desc", "Message")
                )
                if cid:
                    result["events_posted"] += 1

            elif etype == "step_start":
                step_name = event.get("step_name", "")
                cid = self._sync.start_step(
                    step_name,
                    event.get("description", "")
                )
                if cid:
                    step_comment_ids[step_name] = cid
                    result["events_posted"] += 1

            elif etype == "step_complete":
                step_name = event.get("step_name", "")
                cid = step_comment_ids.get(step_name) or \
                    self._sync._comment_ids.get(step_name)
                if cid:
                    self._sync.complete_step(
                        cid, step_name,
                        event.get("results", "")
                    )
                    result["events_posted"] += 1
                else:
                    self._sync.post_bot(
                        f"\u2705 {step_name}",
                        event.get("results", "*(no matching \u23f3 found)*")
                    )
                    result["events_posted"] += 1

            elif etype == "bot":
                cid = self._sync.post_bot(
                    event.get("short_desc", ""),
                    event.get("content", "")
                )
                if cid:
                    result["events_posted"] += 1

            elif etype == "agent_error":
                self._sync.post_bot(
                    "\u26a0\ufe0f Agent Error",
                    event.get("message", "Unknown error")
                )
                result["events_posted"] += 1

        if compaction_detected and self.enabled:
            self._run_integrity_after_compaction()

        self._save_state()
        return result

    # ── Watchdog Fire Handler ────────────────────────────────────

    def _on_watchdog_fire(self, elapsed_sec: float):
        if not self.enabled:
            return

        alert_body = (
            f"\u26a0\ufe0f Watchdog alert \u2014 no activity for "
            f"{int(elapsed_sec)}s (timeout: {int(self.watchdog.timeout_sec)}s, "
            f"mode: {self.mode})\n\n"
            f"Running integrity check..."
        )
        self._sync.post_bot("\U0001f415 Watchdog Alert", alert_body)
        self._run_integrity_after_compaction()

    def _run_integrity_after_compaction(self):
        if not self.enabled:
            return

        report = self._sync.integrity_check(
            todos_completed=list(self._sync._comment_ids.keys()),
            todos_pending=[]
        )

        if report.get("gaps"):
            self._sync.post_bot(
                "\U0001f50d Integrity sweep (post-watchdog)",
                f"Gaps found: {len(report['gaps'])}\n"
                f"Retroactive posts: {report['retroactive_posts']}\n"
                f"{report['report_line']}"
            )

    # ── Status ───────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "agent": {
                "running": self._running,
                "tick_count": self._tick_count,
                "mode": self.mode,
                "tick_interval_sec": self.tick_interval,
                "repo": self.repo,
                "issue_number": self.issue_number,
                "enabled": self.enabled,
            },
            "watchdog": self.watchdog.stats,
            "queue": {
                "depth": self._queue_depth(),
                "file": QUEUE_FILE,
            },
            "sync": self._sync.get_stats() if self._sync else {"enabled": False},
        }


# ── Static helpers (for CLI and hook integration) ────────────────

def load_agent() -> Optional[SessionAgent]:
    """Load agent from state file (for CLI commands after start)."""
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return SessionAgent(
            repo=state["repo"],
            issue_number=state["issue_number"],
            mode=state.get("mode", "normal"),
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def feed_event(event_type: str, *args):
    """Feed an event to the agent via queue file (no agent instance needed).

    Ultra-lightweight path: write directly to the queue file.
    """
    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if event_type == "user" and len(args) >= 1:
        event["message"] = args[0]
        event["short_desc"] = args[1] if len(args) > 1 else "Message"

    elif event_type == "step_start" and len(args) >= 1:
        event["step_name"] = args[0]
        event["description"] = args[1] if len(args) > 1 else ""

    elif event_type == "step_complete" and len(args) >= 1:
        event["step_name"] = args[0]
        event["results"] = args[1] if len(args) > 1 else ""

    elif event_type == "bot" and len(args) >= 2:
        event["short_desc"] = args[0]
        event["content"] = args[1]

    elif event_type == "heartbeat":
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                state["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
                state["heartbeat_tool"] = args[0] if args else ""
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)
            except (json.JSONDecodeError, OSError):
                pass
        return

    elif event_type == "compaction":
        event["message"] = "Context compaction detected"

    # Append to queue file
    events = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                events = json.load(f)
        except (json.JSONDecodeError, OSError):
            events = []

    events.append(event)

    try:
        with open(QUEUE_FILE, 'w') as f:
            json.dump(events, f, indent=2)
    except OSError:
        pass
