#!/usr/bin/env python3
"""Sync GitHub Project board → static JSON for board widget

Pulls all items from a GitHub Projects v2 board, enriches them with
status emojis, sort priorities, and action metadata, then writes a
per-board JSON file that the client-side board widget fetches directly.

Usage:
  # Sync board #4 (default — Knowledge System P0)
  python3 scripts/sync_roadmap.py

  # Sync a specific board
  python3 scripts/sync_roadmap.py --board 37 --project "Knowledge Live (P3)"

  # GitHub Actions (token injected by workflow)
  python3 scripts/sync_roadmap.py --board 4

Output:
  docs/data/board-{number}.json — fetched by client-side board widget

Design:
  Board is the single source of truth. This script bridges GitHub's live
  state and the static docs site. Per-board JSON files provide security
  isolation and independent caching. Run on schedule via GitHub Actions
  or manually.

Authors: Martin Paquet, Claude (Anthropic)
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

# --- Configuration ---

OWNER = "packetqc"
DEFAULT_BOARD = 4
DEFAULT_PROJECT = "Knowledge System (P0)"

# Status → tier mapping (backwards compatible)
TIER_MAP = {
    "Done": "ongoing",
    "In Progress": "ongoing",
    "Todo": "planned",
}
DEFAULT_TIER = "forecast"

# Status → emoji mapping
STATUS_EMOJI = {
    "In Progress": "\U0001f527",  # 🔧
    "Todo": "\U0001f4cb",         # 📋
    "Done": "\u2705",             # ✅
}
DEFAULT_EMOJI = "\U0001f52e"      # 🔮

# Status → sort priority (lower = higher priority)
STATUS_PRIORITY = {
    "In Progress": 1,
    "Todo": 2,
    "Done": 3,
}
DEFAULT_PRIORITY = 4

# Tag → PLAN section mapping
TAG_SECTION = {
    "FIX": "fixes",
    "FORECAST": "forecast",
    "RECALL": "recalls",
    "TASK": "planned",
}
# Fallback: status-based section when tag is empty
STATUS_SECTION = {
    "In Progress": "ongoing",
    "Done": "done",
    "Todo": "planned",
}
DEFAULT_SECTION = "planned"


def graphql(query: str, variables: dict) -> dict:
    """Execute a GraphQL query against the GitHub API."""
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("Error: GH_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    data = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def fetch_board_items(board_number: int) -> list[dict]:
    """Fetch all items from the project board with status and actions."""
    query = """
    query($owner: String!, $number: Int!) {
      user(login: $owner) {
        projectV2(number: $number) {
          title
          url
          items(first: 100) {
            nodes {
              id
              fieldValueByName(name: "Status") {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                }
              }
              content {
                ... on DraftIssue {
                  title
                  body
                }
                ... on Issue {
                  title
                  body
                  number
                  url
                  state
                  labels(first: 10) {
                    nodes {
                      name
                      color
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    result = graphql(query, {"owner": OWNER, "number": board_number})

    project = result.get("data", {}).get("user", {}).get("projectV2")
    if not project:
        print("Error: Project not found", file=sys.stderr)
        sys.exit(1)

    board_url = f"https://github.com/users/{OWNER}/projects/{board_number}"
    items = []
    for node in project["items"]["nodes"]:
        content = node.get("content", {}) or {}
        title = content.get("title", "(untitled)")
        status_field = node.get("fieldValueByName") or {}
        status = status_field.get("name", "Todo")
        issue_number = content.get("number")
        issue_url = content.get("url")
        issue_state = content.get("state", "").upper()

        # Parse TAG: prefix
        tag = ""
        display_title = title
        if ": " in title:
            parts = title.split(": ", 1)
            tag = parts[0]
            display_title = parts[1]

        # Determine item type
        item_type = "issue" if issue_number else "draft"

        # Extract labels (issues only)
        labels = []
        if item_type == "issue":
            label_nodes = content.get("labels", {}) or {}
            for lbl in (label_nodes.get("nodes") or []):
                labels.append({
                    "name": lbl.get("name", ""),
                    "color": lbl.get("color", ""),
                })

        # Determine PLAN section from tag or status
        # Done items always go to "done" section regardless of tag
        if status == "Done":
            section = "done"
        else:
            section = TAG_SECTION.get(tag.upper(), "")
            if not section:
                # Check labels for section override
                for lbl in labels:
                    lbl_name = lbl["name"].lower()
                    if lbl_name in ("ongoing", "fixes", "planned", "forecast", "recalls", "done"):
                        section = lbl_name
                        break
                if not section:
                    section = STATUS_SECTION.get(status, DEFAULT_SECTION)

        # Build actions list based on type and state
        actions = ["view"]
        if item_type == "issue":
            if issue_state == "OPEN":
                actions.append("close")
            elif issue_state == "CLOSED":
                actions.append("reopen")

        items.append({
            "id": node["id"],
            "title": display_title,
            "full_title": title,
            "tag": tag,
            "status": status,
            "status_emoji": STATUS_EMOJI.get(status, DEFAULT_EMOJI),
            "status_priority": STATUS_PRIORITY.get(status, DEFAULT_PRIORITY),
            "tier": TIER_MAP.get(status, DEFAULT_TIER),
            "section": section,
            "type": item_type,
            "issue_number": issue_number,
            "issue_url": issue_url,
            "labels": labels,
            "actions": actions,
            "board_url": board_url,
            "body": (content.get("body", "") or "")[:500],  # Truncate for size
        })

    return items


def build_output(items: list[dict], board_number: int, project_name: str) -> dict:
    """Structure items into the widget JSON format."""
    board_url = f"https://github.com/users/{OWNER}/projects/{board_number}"
    return {
        "meta": {
            "project": project_name,
            "board_number": board_number,
            "board_url": board_url,
            "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_items": len(items),
        },
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(description="Sync GitHub Project board to static JSON")
    parser.add_argument("--board", type=int, default=DEFAULT_BOARD,
                        help=f"Board number (default: {DEFAULT_BOARD})")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT,
                        help=f"Project name (default: {DEFAULT_PROJECT})")
    args = parser.parse_args()

    output_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "data", f"board-{args.board}.json"
    )

    print(f"Syncing board #{args.board} → {output_path}")
    items = fetch_board_items(args.board)
    output = build_output(items, args.board, args.project)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    status_counts = {}
    for item in items:
        s = item["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"  {output['meta']['total_items']} items synced")
    for status, count in sorted(status_counts.items()):
        print(f"  {STATUS_EMOJI.get(status, DEFAULT_EMOJI)} {status}: {count}")
    print(f"  Written to: {output_path}")


if __name__ == "__main__":
    main()
