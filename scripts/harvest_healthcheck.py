#!/usr/bin/env python3
"""Harvest healthcheck — probe satellite repos and update dashboard.

Runs `git ls-remote` against each satellite to check accessibility,
updates the health column and last-harvest date in:
  - publications/distributed-knowledge-dashboard/v1/README.md
  - docs/publications/distributed-knowledge-dashboard/index.md
  - docs/fr/publications/distributed-knowledge-dashboard/index.md

Then regenerates the dashboard webcard GIFs with fresh data.

Usage:
  python3 scripts/harvest_healthcheck.py           # probe and update
  python3 scripts/harvest_healthcheck.py --dry-run  # probe only, no writes
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(SCRIPT_DIR, '..')

README_PATH = os.path.join(
    REPO_ROOT, 'publications', 'distributed-knowledge-dashboard',
    'v1', 'README.md')
DOCS_EN_PATH = os.path.join(
    REPO_ROOT, 'docs', 'publications',
    'distributed-knowledge-dashboard', 'index.md')
DOCS_FR_PATH = os.path.join(
    REPO_ROOT, 'docs', 'fr', 'publications',
    'distributed-knowledge-dashboard', 'index.md')

# Known satellites — extend this list as projects are added
SATELLITES = [
    {
        'name': 'knowledge',
        'url': 'https://github.com/packetqc/knowledge.git',
        'is_self': True,
    },
    {
        'name': 'STM32N6570-DK_SQLITE',
        'url': 'https://github.com/packetqc/STM32N6570-DK_SQLITE.git',
        'is_self': False,
    },
    {
        'name': 'MPLIB',
        'url': 'https://github.com/packetqc/MPLIB.git',
        'is_self': False,
    },
    {
        'name': 'PQC',
        'url': 'https://github.com/packetqc/PQC.git',
        'is_self': False,
    },
]


def probe_satellite(url, timeout=15):
    """Probe a satellite repo with git ls-remote. Returns True if reachable."""
    try:
        result = subprocess.run(
            ['git', 'ls-remote', '--exit-code', '--heads', url],
            capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def determine_health(name, is_reachable, previous_health):
    """Determine health status based on current probe + previous state."""
    if is_reachable:
        return 'healthy'
    elif previous_health == 'healthy':
        return 'stale'  # was reachable, now failing
    elif previous_health == 'pending':
        return 'unreachable'
    else:
        return 'unreachable'


def parse_existing_health(content):
    """Parse existing health values from a markdown table."""
    health_map = {}
    # Match rows in the satellite table
    for m in re.finditer(
            r'\|\s*\[?(\w[\w-]*)\]?.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|.*?\|'
            r'\s*(healthy|unreachable|stale|pending|sain|inaccessible|'
            r'obsolète|en attente)',
            content):
        name = m.group(1)
        h = m.group(2)
        # Normalize French health labels
        fr_to_en = {'sain': 'healthy', 'inaccessible': 'unreachable',
                     'obsolète': 'stale', 'en attente': 'pending'}
        health_map[name] = fr_to_en.get(h, h)
    return health_map


def update_readme_table(content, health_results, today):
    """Update the satellite table in README.md with fresh health + date."""
    lines = content.split('\n')
    updated = []
    in_table = False

    for line in lines:
        # Detect satellite table rows (contain | Satellite | or actual data)
        if re.match(r'\|\s*\[', line) and '|' in line:
            cells = [c.strip() for c in line.split('|')]
            # Find satellite name from link [name](url)
            name_m = re.search(r'\[(\w[\w-]*)\]', cells[1] if len(cells) > 1 else '')
            if name_m and name_m.group(1) in health_results:
                name = name_m.group(1)
                health, reachable = health_results[name]
                # Update health column (8th data column = cells[8])
                # and last harvest date (9th data column = cells[9])
                if len(cells) >= 10:
                    cells[8] = f' {health} '
                    cells[9] = f' {today} '
                    line = '|'.join(cells)
        updated.append(line)

    # Also update the "Last updated" field in master status
    result = '\n'.join(updated)
    result = re.sub(
        r'(Last updated\s*\|\s*)\d{4}-\d{2}-\d{2}',
        f'\\g<1>{today}', result)
    return result


def update_docs_table(content, health_results, today, lang='en'):
    """Update the satellite table in docs pages with fresh health + date."""
    lines = content.split('\n')
    updated = []
    health_labels = {
        'en': {'healthy': 'healthy', 'unreachable': 'unreachable',
               'stale': 'stale', 'pending': 'pending'},
        'fr': {'healthy': 'sain', 'unreachable': 'inaccessible',
               'stale': 'obsolète', 'pending': 'en attente'},
    }
    labels = health_labels.get(lang, health_labels['en'])

    for line in lines:
        if re.match(r'\|\s*\[', line) and '|' in line:
            cells = [c.strip() for c in line.split('|')]
            name_m = re.search(r'\[(\w[\w-]*)\]', cells[1] if len(cells) > 1 else '')
            if name_m and name_m.group(1) in health_results:
                name = name_m.group(1)
                health, _ = health_results[name]
                h_label = labels.get(health, health)
                if len(cells) >= 10:
                    cells[8] = f' {h_label} '
                    cells[9] = f' {today} '
                    line = '|'.join(cells)
        updated.append(line)

    return '\n'.join(updated)


def run_healthcheck(dry_run=False):
    """Main healthcheck: probe satellites, update dashboard, regenerate GIFs."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f"=== Harvest Healthcheck — {today} ===\n")

    # Read existing README for previous health values
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Dashboard README not found at {README_PATH}")
        sys.exit(1)

    existing_health = parse_existing_health(readme_content)

    # Probe each satellite
    health_results = {}
    for sat in SATELLITES:
        name = sat['name']
        is_self = sat.get('is_self', False)

        if is_self:
            # Core repo is always healthy if we're running here
            health = 'healthy'
            reachable = True
            print(f"  {name:30s}  (self)  → healthy")
        else:
            print(f"  {name:30s}  probing...", end='', flush=True)
            reachable = probe_satellite(sat['url'])
            previous = existing_health.get(name, 'pending')
            health = determine_health(name, reachable, previous)
            status_icon = '✓' if reachable else '✗'
            print(f"  {status_icon}  → {health}")

        health_results[name] = (health, reachable)

    print()

    # Summary
    total = len([s for s in SATELLITES if not s.get('is_self')])
    healthy = sum(1 for n, (h, _) in health_results.items()
                  if h == 'healthy' and n != 'knowledge')
    print(f"Summary: {healthy}/{total} satellites reachable")
    print()

    if dry_run:
        print("DRY RUN — no files modified.")
        return health_results

    # Update README
    print("Updating dashboard files...")
    updated_readme = update_readme_table(readme_content, health_results, today)
    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(updated_readme)
    print(f"  ✓ {README_PATH}")

    # Update docs EN
    try:
        with open(DOCS_EN_PATH, 'r', encoding='utf-8') as f:
            en_content = f.read()
        updated_en = update_docs_table(en_content, health_results, today, 'en')
        with open(DOCS_EN_PATH, 'w', encoding='utf-8') as f:
            f.write(updated_en)
        print(f"  ✓ {DOCS_EN_PATH}")
    except FileNotFoundError:
        print(f"  ✗ {DOCS_EN_PATH} not found, skipping")

    # Update docs FR
    try:
        with open(DOCS_FR_PATH, 'r', encoding='utf-8') as f:
            fr_content = f.read()
        updated_fr = update_docs_table(fr_content, health_results, today, 'fr')
        with open(DOCS_FR_PATH, 'w', encoding='utf-8') as f:
            f.write(updated_fr)
        print(f"  ✓ {DOCS_FR_PATH}")
    except FileNotFoundError:
        print(f"  ✗ {DOCS_FR_PATH} not found, skipping")

    # Regenerate dashboard webcards
    print("\nRegenerating dashboard webcards...")
    try:
        # Reset the dashboard data cache so it re-reads the updated README
        gen_script = os.path.join(SCRIPT_DIR, 'generate_og_gifs.py')
        result = subprocess.run(
            [sys.executable, gen_script],
            capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("  ✓ All GIFs regenerated")
        else:
            print(f"  ✗ GIF generation failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ✗ GIF generation error: {e}")

    print(f"\nHealthcheck complete — {today}")
    return health_results


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    run_healthcheck(dry_run=dry_run)
