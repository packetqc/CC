"""CLI entry point for session_agent — hook and manual use.

Usage:
    python -m scripts.session_agent <command> [args...]

Commands: start, init, stop, tick, feed, status, mode, switch, addon, addons, cycle

Authors: Martin Paquet, Claude (Anthropic)
"""

import json
import os
import sys
import time

from .cache import write_runtime_cache, read_runtime_cache
from .addons import append_request_addon, read_request_addons, get_addons_by_stage
from .engineering import (
    ENGINEERING_STAGES, ENGINEERING_STAGE_INDEX,
    init_engineering_cycle, advance_engineering_stage,
    get_engineering_stage, get_engineering_stage_name,
    get_engineering_stage_index, get_engineering_cycle_summary,
    sync_engineering_stage_label,
)
from .helpers import _get_gh_helper
from .watchdog import (
    STATE_FILE, QUEUE_FILE, LOCK_FILE,
    SessionAgent, load_agent, feed_event,
)


def main():
    """CLI entry point for hook and manual use."""
    if len(sys.argv) < 2:
        print("Usage: session_agent.py <command> [args...]")
        print("Commands: start, init, stop, tick, feed, status, mode, switch, addon, addons, cycle")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        if len(sys.argv) < 4:
            agent = SessionAgent.init_from_cache()
            if agent:
                agent.start()
                write_runtime_cache(
                    agent.repo, agent.issue_number,
                    branch=agent._get_branch(),
                    mode=agent.mode)
                print(f"Agent auto-started from cache: {agent.repo}"
                      f"#{agent.issue_number} mode={agent.mode} "
                      f"tick={agent.tick_interval}s enabled={agent.enabled}")
            else:
                print("Usage: session_agent.py start <owner/repo> <issue_number> [mode]")
                print("  Or: ensure notes/session-runtime.json exists for auto-start")
                sys.exit(1)
        else:
            repo = sys.argv[2]
            issue_num = int(sys.argv[3])
            mode = sys.argv[4] if len(sys.argv) > 4 else "normal"
            agent = SessionAgent(repo, issue_num, mode=mode)
            agent.start()
            write_runtime_cache(
                repo, issue_num,
                branch=agent._get_branch(),
                mode=mode)
            print(f"Agent started: {repo}#{issue_num} mode={mode} "
                  f"tick={agent.tick_interval}s enabled={agent.enabled}")
        # Keep alive for background use
        try:
            while agent._running:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop()
            print("Agent stopped.")

    elif cmd == "init":
        agent = SessionAgent.init_from_cache()
        if agent:
            agent._save_state()
            print(f"Agent initialized from cache: {agent.repo}"
                  f"#{agent.issue_number} mode={agent.mode} "
                  f"enabled={agent.enabled}")
        else:
            print("No runtime cache found (notes/session-runtime.json).")
            sys.exit(1)

    elif cmd == "stop":
        agent = load_agent()
        if agent:
            agent.stop()
            for f in [STATE_FILE, QUEUE_FILE, LOCK_FILE]:
                if os.path.exists(f):
                    os.remove(f)
            print("Agent stopped and cleaned up.")
        else:
            print("No agent running.")

    elif cmd == "tick":
        agent = load_agent()
        if agent:
            result = agent.tick()
            print(json.dumps(result, indent=2))
        else:
            print("No agent running. Use 'start' first.")

    elif cmd == "feed":
        if len(sys.argv) < 4:
            print("Usage: session_agent.py feed <type> <arg1> [arg2]")
            print("Types: user, step_start, step_complete, bot, compaction")
            sys.exit(1)
        event_type = sys.argv[2]
        args = sys.argv[3:]
        feed_event(event_type, *args)
        print(f"Event queued: {event_type}")

    elif cmd == "status":
        agent = load_agent()
        if agent:
            print(json.dumps(agent.status(), indent=2))
        else:
            if os.path.exists(QUEUE_FILE):
                try:
                    with open(QUEUE_FILE, 'r') as f:
                        events = json.load(f)
                    print(f"No agent running. Orphaned queue: {len(events)} events.")
                except (json.JSONDecodeError, OSError):
                    print("No agent running.")
            else:
                print("No agent running. No queue.")

    elif cmd == "mode":
        if len(sys.argv) < 3:
            print("Usage: session_agent.py mode <normal|live|burst>")
            sys.exit(1)
        agent = load_agent()
        if agent:
            old_mode = agent.mode
            agent.set_mode(sys.argv[2])
            print(f"Mode changed: {old_mode} \u2192 {agent.mode} "
                  f"(tick={agent.tick_interval}s, "
                  f"watchdog={agent.watchdog.timeout_sec}s)")
        else:
            print("No agent running.")

    elif cmd == "switch":
        if len(sys.argv) < 3:
            print("Usage: session_agent.py switch <issue_number> [title]")
            sys.exit(1)
        agent = load_agent()
        if agent:
            new_issue = int(sys.argv[2])
            new_title = sys.argv[3] if len(sys.argv) > 3 else ""
            old_issue = agent.issue_number
            agent.switch_issue(new_issue, new_title)
            print(f"Issue switched: #{old_issue} \u2192 #{new_issue} "
                  f"(cache + state updated)")
        else:
            print("No agent running.")

    elif cmd == "addon":
        if len(sys.argv) < 4:
            print("Usage: session_agent.py addon <verbatim> <synthesis>")
            sys.exit(1)
        verbatim = sys.argv[2]
        synthesis = sys.argv[3]
        ok = append_request_addon(verbatim, synthesis)
        if ok:
            addons = read_request_addons()
            print(f"Add-on #{len(addons)} appended to session cache.")
        else:
            print("Failed to append add-on (no runtime cache?).")
            sys.exit(1)

    elif cmd == "addons":
        addons = read_request_addons()
        if not addons:
            print("No add-ons recorded.")
        else:
            print(f"=== Request Add-ons ({len(addons)}) ===")
            for a in addons:
                print(f"\n  #{a['index']} ({a['timestamp']})")
                print(f"  Verbatim:  {a['verbatim'][:120]}")
                print(f"  Synthesis: {a['synthesis'][:120]}")

    elif cmd == "cycle":
        _handle_cycle_command()

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: start, init, stop, tick, feed, status, mode, switch, addon, addons, cycle")
        print("Cycle sub: init, advance, stage, summary, history, addons, labels-setup, label-sync")
        sys.exit(1)


def _handle_cycle_command():
    """Handle the 'cycle' subcommand and its sub-subcommands."""
    if len(sys.argv) < 3:
        print("Usage: session_agent.py cycle <subcommand> [args...]")
        print("Subcommands:")
        print("  init [request_description]  \u2014 Initialize cycle at 'analysis' stage")
        print("  advance <stage> [reason]    \u2014 Transition to a new stage")
        print("  stage                       \u2014 Show current stage name + index")
        print("  summary                     \u2014 Show cycle summary with add-on counts")
        print("  history                     \u2014 Show full stage transition history")
        print("  addons [stage]              \u2014 Show add-ons (optionally filtered by stage)")
        print("  labels-setup                \u2014 Create all 9 stage labels on the repo")
        print("  label-sync [stage]          \u2014 Manually sync a label on the issue")
        print()
        print("Stages (0-9):")
        for i, s in enumerate(ENGINEERING_STAGES):
            marker = " \u2190" if s == get_engineering_stage_name() else ""
            print(f"  {i}: {s}{marker}")
        sys.exit(0)

    subcmd = sys.argv[2]

    if subcmd == "init":
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        ok = init_engineering_cycle(desc)
        if ok:
            print("Engineering cycle initialized \u2014 stage: analysis (0)")
            if desc:
                print(f"Request seeded as add-on #0: {desc[:100]}")
        else:
            print("Failed to initialize cycle (no runtime cache?).")
            sys.exit(1)

    elif subcmd == "advance":
        if len(sys.argv) < 4:
            print("Usage: session_agent.py cycle advance <stage> [reason]")
            print(f"Valid stages: {', '.join(ENGINEERING_STAGES)}")
            sys.exit(1)
        target = sys.argv[3]
        reason = sys.argv[4] if len(sys.argv) > 4 else ""
        old = get_engineering_stage_name()
        ok = advance_engineering_stage(target, reason)
        if ok:
            idx = ENGINEERING_STAGE_INDEX.get(target, -1)
            print(f"Stage transition: {old} \u2192 {target} ({idx})")
            if reason:
                print(f"Reason: {reason}")
        else:
            print(f"Failed to advance. Valid stages: {', '.join(ENGINEERING_STAGES)}")
            sys.exit(1)

    elif subcmd == "stage":
        stage = get_engineering_stage_name()
        idx = get_engineering_stage_index()
        print(f"{stage} ({idx})")

    elif subcmd == "summary":
        summary = get_engineering_cycle_summary()
        if not summary.get("initialized"):
            print("Engineering cycle not initialized.")
            print("Run: session_agent.py cycle init [request_description]")
            sys.exit(0)

        print("=== Engineering Cycle Summary ===")
        print(f"  Current stage: {summary['current_stage']} "
              f"({summary['current_stage_index']})")
        visited = " \u2192 ".join(summary["stages_visited"])
        print(f"  Stages visited: {visited}")
        print(f"  Total transitions: {summary['total_transitions']}")
        print(f"  Started: {summary['started_at']}")
        if summary.get("addons_per_stage"):
            print("  Add-ons per stage:")
            for s, count in sorted(summary["addons_per_stage"].items(),
                                   key=lambda x: ENGINEERING_STAGE_INDEX.get(x[0], 99)):
                idx = ENGINEERING_STAGE_INDEX.get(s, -1)
                print(f"    {s} ({idx}): {count}")

    elif subcmd == "history":
        cycle = get_engineering_stage()
        if not cycle:
            print("Engineering cycle not initialized.")
            sys.exit(0)

        history = cycle.get("stage_history", [])
        print(f"=== Engineering Cycle History ({len(history)} entries) ===")
        for i, entry in enumerate(history):
            direction = entry.get("direction", "")
            dir_marker = {"forward": "\u2192", "backward": "\u2190",
                          "re-enter": "\u21ba"}.get(direction, "\u00b7")
            exited = entry.get("exited_at", "active")
            if exited and exited != "active":
                exited = exited[:19]
            print(f"\n  [{i}] {dir_marker} {entry['stage']} ({entry['index']})")
            print(f"      Entered: {entry['entered_at'][:19]}")
            print(f"      Exited:  {exited}")
            if entry.get("reason"):
                print(f"      Reason:  {entry['reason']}")
            if entry.get("from_stage"):
                print(f"      From:    {entry['from_stage']}")

    elif subcmd == "addons":
        stage_filter = sys.argv[3] if len(sys.argv) > 3 else None
        addons = get_addons_by_stage(stage_filter)
        if not addons:
            if stage_filter:
                print(f"No add-ons at stage '{stage_filter}'.")
            else:
                print("No add-ons recorded.")
            sys.exit(0)

        header = f"stage={stage_filter}" if stage_filter else "all stages"
        print(f"=== Staged Add-ons ({len(addons)}, {header}) ===")
        for a in addons:
            type_marker = {"request_origin": "\U0001f4cc",
                           "addon": "\U0001f4ce",
                           "stage_transition": "\U0001f504"
                           }.get(a.get("addon_type", ""), "\u00b7")
            rtype = a.get("request_type")
            rtype_tag = f"  [{rtype}]" if rtype else ""
            print(f"\n  {type_marker} #{a['index']} \u2014 "
                  f"{a['stage']} ({a['stage_index']}){rtype_tag}")
            print(f"     Verbatim:  {a['verbatim'][:120]}")
            print(f"     Synthesis: {a['synthesis'][:120]}")

    elif subcmd == "labels-setup":
        cache = read_runtime_cache()
        repo = cache.get("repo", "") if cache else ""
        if not repo:
            print("No repo in runtime cache.")
            sys.exit(1)
        gh = _get_gh_helper()
        if not gh:
            print("No GH_TOKEN \u2014 cannot create labels (semi-automatic mode).")
            sys.exit(1)
        try:
            results = gh.engineering_labels_setup(repo)
            for r in results:
                print(f"  {r['name']}: {r['status']}")
            print(f"\n{len(results)} engineering stage labels provisioned on {repo}.")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif subcmd == "label-sync":
        stage = sys.argv[3] if len(sys.argv) > 3 else get_engineering_stage_name()
        if stage == "unknown":
            print("No active stage and no stage argument provided.")
            sys.exit(1)
        if stage not in ENGINEERING_STAGE_INDEX:
            print(f"Invalid stage: {stage}")
            print(f"Valid stages: {', '.join(ENGINEERING_STAGES)}")
            sys.exit(1)
        result = sync_engineering_stage_label(stage)
        if result.get("synced"):
            print(f"Label synced on issue: {result.get('added', stage)}")
            if result.get("removed"):
                print(f"  Removed: {result['removed']}")
        elif result.get("error"):
            print(f"Label sync: {result['error']}")
        else:
            print(f"Label sync result: {result}")

    else:
        print(f"Unknown cycle subcommand: {subcmd}")
        print("Subcommands: init, advance, stage, summary, history, addons, labels-setup, label-sync")
        sys.exit(1)
